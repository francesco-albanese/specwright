"""Validator for specwright slice-schema fixtures.

Public surface:

    validate_slice(data, *, known_ids=None) -> list[str]
    validate_corpus(slices) -> list[str]

CLI entry point walks ``tests/fixtures/slice-schema/{positive,negative}/`` and
exits non-zero on any mismatch between expected and actual validation result.

Stdlib-only: re, json, sys, argparse, fnmatch, pathlib.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

# Per the slice-schema contract, every slice carries exactly these required
# fields. The tiny-flow discriminator is `spec_path is None`; when null, the
# slice MUST additionally carry a non-empty `inline_spec` field carrying the
# whole spec body.
REQUIRED_FIELDS = (
    "title",
    "acceptance_criteria",
    "depends_on",
    "estimated_touched_paths",
    "spec_path",
)
GLOB_FORBIDDEN_SEGMENTS = ("..",)
GLOB_CHAR_RE = re.compile(r"^[A-Za-z0-9_./*?\[\]\-{},!]+$")
SPEC_PATH_RE = re.compile(r"^\.specs/[^/]+/$")


def validate_slice(data, *, known_ids=None):
    """Validate a single slice dict. Returns a list of error strings."""
    if not isinstance(data, dict):
        return [f"slice must be a JSON object, got {type(data).__name__}"]

    slice_id = data.get("id", "<no-id>")
    errors = []

    # 1. required fields present (short-circuit on missing; type checks need them)
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    for field in missing:
        errors.append(f"{slice_id}: missing required field '{field}'")
    if missing:
        return errors

    # 2. title
    if not isinstance(data["title"], str) or not data["title"].strip():
        errors.append(f"{slice_id}: title must be a non-empty string")

    # 3. acceptance_criteria — verbatim EARS string lifted from requirements.md
    if not isinstance(data["acceptance_criteria"], str) or not data["acceptance_criteria"].strip():
        errors.append(f"{slice_id}: acceptance_criteria must be a non-empty string")

    # 4. depends_on: list[str], no self-reference, known if corpus context given
    depends_on = data["depends_on"]
    if not isinstance(depends_on, list):
        errors.append(f"{slice_id}: depends_on must be a list")
    else:
        for dep in depends_on:
            if not isinstance(dep, str) or not dep.strip():
                errors.append(f"{slice_id}: depends_on entries must be non-empty strings")
                continue
            if dep == slice_id:
                errors.append(f"{slice_id}: depends_on contains self-reference '{dep}'")
            if known_ids is not None and dep not in known_ids:
                errors.append(f"{slice_id}: depends_on references unknown id '{dep}'")

    # 5. estimated_touched_paths: non-empty list of well-formed globs
    paths = data["estimated_touched_paths"]
    if not isinstance(paths, list) or len(paths) == 0:
        errors.append(f"{slice_id}: estimated_touched_paths must be a non-empty list")
    else:
        for p in paths:
            errors.extend(_validate_glob(slice_id, p))

    # 6. spec_path / inline_spec consistency (tiny-flow discriminator)
    spec_path = data["spec_path"]
    inline_spec = data.get("inline_spec")
    if spec_path is None:
        # tiny flow
        if not isinstance(inline_spec, str) or not inline_spec.strip():
            errors.append(
                f"{slice_id}: tiny slice (spec_path is null) must carry a non-empty 'inline_spec'"
            )
    else:
        # feature / bugfix / quick — spec lives on disk
        if not isinstance(spec_path, str) or not spec_path.strip():
            errors.append(
                f"{slice_id}: spec_path must be a string ending in '/' or null (got {spec_path!r})"
            )
        elif not SPEC_PATH_RE.match(spec_path):
            errors.append(
                f"{slice_id}: spec_path must match '.specs/<slug>/' (got '{spec_path}')"
            )
        if inline_spec is not None:
            errors.append(
                f"{slice_id}: 'inline_spec' is only allowed when spec_path is null (tiny flow)"
            )

    return errors


def _validate_glob(slice_id, glob):
    errs = []
    if not isinstance(glob, str) or not glob.strip():
        return [f"{slice_id}: glob entries must be non-empty strings"]
    if glob.startswith("/"):
        errs.append(f"{slice_id}: glob '{glob}' must be repo-relative (no leading '/')")
    for seg in glob.split("/"):
        if seg in GLOB_FORBIDDEN_SEGMENTS:
            errs.append(f"{slice_id}: glob '{glob}' must not contain '..' segments")
            break
    if not GLOB_CHAR_RE.match(glob):
        errs.append(f"{slice_id}: glob '{glob}' contains disallowed characters")
    # Stdlib `fnmatch.translate` accepts everything fnmatch accepts; if it
    # raises, the glob is unparseable as a shell-style pattern.
    try:
        fnmatch.translate(glob)
    except Exception as exc:  # pragma: no cover — fnmatch.translate is permissive
        errs.append(f"{slice_id}: glob '{glob}' not parseable by fnmatch: {exc}")
    return errs


def validate_corpus(slices):
    """Validate a list of slices together. Cross-slice checks: id uniqueness,
    cycle detection in the depends_on graph."""
    errors = []
    by_id = {}
    for s in slices:
        if not isinstance(s, dict):
            errors.append("corpus contains a non-object entry")
            continue
        sid = s.get("id")
        if not sid:
            errors.append("corpus entry is missing 'id'")
            continue
        if sid in by_id:
            errors.append(f"duplicate slice id '{sid}'")
        by_id[sid] = s

    known = set(by_id)
    for sid, s in by_id.items():
        errors.extend(validate_slice(s, known_ids=known))

    # cycle detection (DFS, 3-colour)
    WHITE, GRAY, BLACK = 0, 1, 2
    colour = {sid: WHITE for sid in by_id}

    def visit(node, stack):
        colour[node] = GRAY
        for dep in by_id[node].get("depends_on", []):
            if dep not in by_id:
                continue
            if colour[dep] == GRAY:
                cycle = " -> ".join(stack + [node, dep])
                errors.append(f"depends_on cycle detected: {cycle}")
                return
            if colour[dep] == WHITE:
                visit(dep, stack + [node])
        colour[node] = BLACK

    for sid in by_id:
        if colour[sid] == WHITE:
            visit(sid, [])

    return errors


# ---------------------------------------------------------------------------
# Fixture discovery + pytest entry points
# ---------------------------------------------------------------------------

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "slice-schema"


def _load_fixture(path):
    with path.open() as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return [data]


def _discover(kind):
    folder = FIXTURE_ROOT / kind
    if not folder.is_dir():
        return []
    return sorted(folder.glob("*.json"))


def _check_fixture(path, expected_valid):
    slices = _load_fixture(path)
    errors = validate_corpus(slices)
    actual_valid = not errors
    if expected_valid and not actual_valid:
        return f"{path.name}: expected valid, got errors: {errors}"
    if not expected_valid and actual_valid:
        return f"{path.name}: expected invalid, but validation passed"
    return None


def iter_positive_fixtures():
    return _discover("positive")


def iter_negative_fixtures():
    return _discover("negative")


def _make_pytest_tests():
    """Generate one test_* function per fixture file at import time so pytest
    discovers them."""
    g = globals()
    for path in iter_positive_fixtures():
        name = f"test_positive_{path.stem.replace('-', '_')}"

        def _t(p=path):
            err = _check_fixture(p, expected_valid=True)
            assert err is None, err

        _t.__name__ = name
        g[name] = _t

    for path in iter_negative_fixtures():
        name = f"test_negative_{path.stem.replace('-', '_')}"

        def _t(p=path):
            err = _check_fixture(p, expected_valid=False)
            assert err is None, err

        _t.__name__ = name
        g[name] = _t


_make_pytest_tests()


# ---------------------------------------------------------------------------
# Always-on unit checks (independent of fixtures on disk)
# ---------------------------------------------------------------------------


def test_well_formed_feature_slice_passes():
    slice_ = {
        "id": "x-1",
        "title": "well-formed",
        "acceptance_criteria": "WHEN x THE SYSTEM SHALL y",
        "depends_on": [],
        "estimated_touched_paths": ["src/a.py", "tests/**"],
        "spec_path": ".specs/x/",
    }
    assert validate_slice(slice_) == []


def test_well_formed_tiny_slice_passes():
    slice_ = {
        "id": "x-1",
        "title": "tiny passes",
        "acceptance_criteria": "WHEN x THE SYSTEM SHALL y",
        "depends_on": [],
        "estimated_touched_paths": ["src/a.py"],
        "spec_path": None,
        "inline_spec": "## Intent\n...\n## AC\nWHEN x THE SYSTEM SHALL y",
    }
    assert validate_slice(slice_) == []


def test_missing_required_field_caught():
    slice_ = {
        "id": "x-1",
        "title": "no spec_path",
        "acceptance_criteria": "WHEN x THE SYSTEM SHALL y",
        "depends_on": [],
        "estimated_touched_paths": ["src/a.py"],
        # 'spec_path' missing
    }
    errors = validate_slice(slice_)
    assert any("missing required field 'spec_path'" in e for e in errors), errors


def test_self_referential_depends_on_caught():
    slice_ = {
        "id": "x-1",
        "title": "self ref",
        "acceptance_criteria": "WHEN x THE SYSTEM SHALL y",
        "depends_on": ["x-1"],
        "estimated_touched_paths": ["src/a.py"],
        "spec_path": ".specs/x/",
    }
    errors = validate_slice(slice_)
    assert any("self-reference" in e for e in errors), errors


def test_bad_glob_absolute_caught():
    slice_ = {
        "id": "x-1",
        "title": "bad glob",
        "acceptance_criteria": "WHEN x THE SYSTEM SHALL y",
        "depends_on": [],
        "estimated_touched_paths": ["/abs/path.py"],
        "spec_path": ".specs/x/",
    }
    errors = validate_slice(slice_)
    assert any("repo-relative" in e for e in errors), errors


def test_bad_glob_with_dotdot_caught():
    slice_ = {
        "id": "x-1",
        "title": "escape",
        "acceptance_criteria": "WHEN x THE SYSTEM SHALL y",
        "depends_on": [],
        "estimated_touched_paths": ["../etc/passwd"],
        "spec_path": ".specs/x/",
    }
    errors = validate_slice(slice_)
    assert any("'..' segments" in e for e in errors), errors


def test_cycle_caught_across_slices():
    a = {
        "id": "x-1", "title": "a", "acceptance_criteria": "WHEN a THE SYSTEM SHALL b",
        "depends_on": ["x-2"], "estimated_touched_paths": ["src/a.py"],
        "spec_path": ".specs/x/",
    }
    b = {
        "id": "x-2", "title": "b", "acceptance_criteria": "WHEN c THE SYSTEM SHALL d",
        "depends_on": ["x-1"], "estimated_touched_paths": ["src/b.py"],
        "spec_path": ".specs/x/",
    }
    errors = validate_corpus([a, b])
    assert any("cycle" in e for e in errors), errors


def test_tiny_without_inline_spec_caught():
    slice_ = {
        "id": "x-1",
        "title": "tiny no inline",
        "acceptance_criteria": "WHEN x THE SYSTEM SHALL y",
        "depends_on": [],
        "estimated_touched_paths": ["README.md"],
        "spec_path": None,
        # inline_spec missing
    }
    errors = validate_slice(slice_)
    assert any("inline_spec" in e for e in errors), errors


def test_inline_spec_forbidden_when_spec_path_set():
    slice_ = {
        "id": "x-1",
        "title": "feature with inline spec",
        "acceptance_criteria": "WHEN x THE SYSTEM SHALL y",
        "depends_on": [],
        "estimated_touched_paths": ["src/a.py"],
        "spec_path": ".specs/x/",
        "inline_spec": "should not be here",
    }
    errors = validate_slice(slice_)
    assert any("only allowed when spec_path is null" in e for e in errors), errors


def test_unknown_depends_on_caught_in_corpus():
    a = {
        "id": "x-1", "title": "a", "acceptance_criteria": "WHEN a THE SYSTEM SHALL b",
        "depends_on": ["x-missing"], "estimated_touched_paths": ["src/a.py"],
        "spec_path": ".specs/x/",
    }
    errors = validate_corpus([a])
    assert any("unknown id 'x-missing'" in e for e in errors), errors


# ---------------------------------------------------------------------------
# CLI: walk fixtures, fail loudly on mismatch
# ---------------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate slice-schema fixtures.")
    parser.add_argument(
        "--fixtures",
        default=str(FIXTURE_ROOT),
        help="Path to fixtures root containing positive/ and negative/ subfolders.",
    )
    args = parser.parse_args(argv)

    root = Path(args.fixtures)
    failures = []

    positives = sorted((root / "positive").glob("*.json")) if (root / "positive").is_dir() else []
    negatives = sorted((root / "negative").glob("*.json")) if (root / "negative").is_dir() else []

    if len(positives) < 4:
        failures.append(f"need at least 4 positive fixtures, found {len(positives)}")
    if len(negatives) < 4:
        failures.append(f"need at least 4 negative fixtures, found {len(negatives)}")

    for p in positives:
        err = _check_fixture(p, expected_valid=True)
        if err:
            failures.append(err)
        else:
            print(f"OK   positive/{p.name}")
    for p in negatives:
        err = _check_fixture(p, expected_valid=False)
        if err:
            failures.append(err)
        else:
            print(f"OK   negative/{p.name}")

    if failures:
        print("\nFAILURES:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print(f"\nAll {len(positives) + len(negatives)} fixtures pass schema expectations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
