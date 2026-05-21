"""Validator for the specwright stacking-rules contract.

Pure function `expected_base(slice_id, slices, pr_state)` returns the
base branch that `gh pr create` should target for a given slice, given
the slice graph (beads `depends_on` edges) and the current state of
PRs (`open` / `merged`).

Runnable two ways:
    python tests/stacking_rules_validator.py
    python -m pytest tests/stacking_rules_validator.py -v

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Pure function: PR base-branch resolution
# ---------------------------------------------------------------------------

DEFAULT_BASE = "main"
BRANCH_REGEX = re.compile(r"^slice/[a-z0-9][a-z0-9.\-]*-[a-z0-9][a-z0-9\-]*$")


def expected_base(
    slice_id: str,
    slices: list[dict],
    pr_state: dict[str, str],
) -> str:
    """Return the base branch a PR for `slice_id` should target.

    Rules (total — every input has exactly one answer):

    1. If the slice has no `depends_on` entries → `main`.
    2. Else, look at the FIRST parent in `depends_on` (linear-chain rule;
       multi-parent fork falls back to first parent — see stacking-rules.md):
       a. If first parent's PR state is `open` → parent's branch.
       b. If first parent's PR state is `merged` → `main`
          (post-merge: GitHub already auto-retargeted the open child PR).
       c. Otherwise (no PR yet / unknown) → `main` (defensive default;
          the child should wait until the parent has a PR).
    """
    index = {s["id"]: s for s in slices}
    if slice_id not in index:
        raise KeyError(f"slice {slice_id!r} not in slice graph")

    parents = index[slice_id].get("depends_on", [])
    if not parents:
        return DEFAULT_BASE

    first_parent_id = parents[0]
    first_parent = index.get(first_parent_id)
    if first_parent is None:
        # Dangling dep — defensive default.
        return DEFAULT_BASE

    state = pr_state.get(first_parent_id)
    if state == "open":
        return first_parent["branch"]
    # merged, missing, or unknown all collapse to main.
    return DEFAULT_BASE


# ---------------------------------------------------------------------------
# Fixture loading + assertions
# ---------------------------------------------------------------------------

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "stacking-rules"


def load_fixture(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def check_fixture(fixture: dict) -> list[str]:
    """Return list of error strings; empty list on success."""
    errors: list[str] = []
    slices = fixture["slices"]
    pr_state = fixture.get("pr_state", {})
    expected = fixture["expected_base"]

    for slice_id, want in expected.items():
        got = expected_base(slice_id, slices, pr_state)
        if got != want:
            errors.append(
                f"  slice {slice_id!r}: expected base {want!r}, got {got!r}"
            )

    # Sanity-check branch naming convention.
    for s in slices:
        branch = s.get("branch", "")
        if not BRANCH_REGEX.match(branch):
            errors.append(
                f"  slice {s['id']!r}: branch {branch!r} violates "
                f"naming convention {BRANCH_REGEX.pattern!r}"
            )
    return errors


def iter_fixtures(fixture_dir: Path = FIXTURE_DIR) -> list[Path]:
    return sorted(p for p in fixture_dir.glob("*.json"))


# ---------------------------------------------------------------------------
# Pytest entry points — one test per fixture so pytest -v lists them.
# ---------------------------------------------------------------------------


def _run(fixture_name: str) -> None:
    path = FIXTURE_DIR / f"{fixture_name}.json"
    errors = check_fixture(load_fixture(path))
    assert not errors, f"{fixture_name}.json failed:\n" + "\n".join(errors)


def test_no_deps() -> None:
    _run("no-deps")


def test_linear_chain() -> None:
    _run("linear-chain")


def test_fork_multi_parent() -> None:
    _run("fork-multi-parent")


def test_post_merge_retarget() -> None:
    _run("post-merge-retarget")


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=FIXTURE_DIR,
        help="Directory containing fixture .json files.",
    )
    args = parser.parse_args(argv)

    fixtures = iter_fixtures(args.fixtures)
    if not fixtures:
        print(f"no fixtures found in {args.fixtures}", file=sys.stderr)
        return 2

    failed = 0
    for path in fixtures:
        errors = check_fixture(load_fixture(path))
        if errors:
            failed += 1
            print(f"FAIL {path.name}")
            for e in errors:
                print(e)
        else:
            print(f"PASS {path.name}")

    print(f"\n{len(fixtures) - failed}/{len(fixtures)} fixtures passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
