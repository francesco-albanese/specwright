#!/usr/bin/env python3
"""Validator for `references/review-format.md` finding schema and tabular output.

Runnable two ways:

    python tests/review_format_validator.py
    python -m pytest tests/review_format_validator.py -v

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

SEVERITY_ORDER = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITY_ORDER)}
REQUIRED_FIELDS = ("severity", "file", "line", "concern", "why", "recommended_fix")
ALLOWED_FIELDS = frozenset(REQUIRED_FIELDS)

CONCERN_MAX = 80

LINE_RANGE_RE = re.compile(r"^(\d+)-(\d+)$")

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "review-format"

AUTO_FIX_PROMPT = (
    "What next?\n"
    "[1] auto-fix all CRITICAL\n"
    "[2] CRITICAL + HIGH\n"
    "[3] pick individually\n"
    "[4] file as new beads tasks\n"
    "[5] skip\n"
)


class ValidationError(ValueError):
    """Raised when a finding (or document) violates the review-format contract."""


def validate_finding(finding: Any) -> None:
    """Raise ValidationError if `finding` does not conform to the schema.

    Pure: no IO, no globals beyond constants.
    """
    if not isinstance(finding, dict):
        raise ValidationError(f"finding must be a JSON object, got {type(finding).__name__}")

    keys = set(finding.keys())
    missing = [f for f in REQUIRED_FIELDS if f not in keys]
    if missing:
        raise ValidationError(f"missing required field(s): {', '.join(missing)}")
    extra = keys - ALLOWED_FIELDS
    if extra:
        raise ValidationError(f"unexpected field(s): {', '.join(sorted(extra))}")

    sev = finding["severity"]
    if not isinstance(sev, str) or sev not in SEVERITY_RANK:
        raise ValidationError(
            f"severity must be one of {SEVERITY_ORDER}, got {sev!r}"
        )

    f = finding["file"]
    if not isinstance(f, str) or not f.strip():
        raise ValidationError("file must be a non-empty string")
    if f.startswith("/"):
        raise ValidationError(f"file must be repo-relative (no leading '/'): {f!r}")
    if any(part == ".." for part in f.split("/")):
        raise ValidationError(f"file must not contain '..' segments: {f!r}")

    line = finding["line"]
    _validate_line(line)

    for txt_field in ("concern", "why", "recommended_fix"):
        v = finding[txt_field]
        if not isinstance(v, str) or not v:
            raise ValidationError(f"{txt_field} must be a non-empty string")

    if "\n" in finding["concern"] or "\r" in finding["concern"]:
        raise ValidationError("concern must not contain newlines")
    if len(finding["concern"]) > CONCERN_MAX:
        raise ValidationError(
            f"concern exceeds {CONCERN_MAX} chars: {len(finding['concern'])}"
        )


def _validate_line(line: Any) -> None:
    # bool is a subclass of int — reject explicitly.
    if isinstance(line, bool):
        raise ValidationError(f"line must not be a bool, got {line!r}")
    if isinstance(line, int):
        if line < 1:
            raise ValidationError(f"line integer must be >= 1, got {line}")
        return
    if isinstance(line, str):
        m = LINE_RANGE_RE.match(line)
        if not m:
            raise ValidationError(
                f"line string must match 'N-M' (decimal ints, no spaces), got {line!r}"
            )
        start, end = int(m.group(1)), int(m.group(2))
        if start < 1 or end < 1:
            raise ValidationError(f"line range parts must be >= 1: {line!r}")
        if start > end:
            raise ValidationError(f"line range start must be <= end: {line!r}")
        return
    raise ValidationError(
        f"line must be int or 'N-M' string, got {type(line).__name__}"
    )


def load_findings(path: Path | str) -> list[dict]:
    """Load and validate a review-output JSON file. Returns the list of findings."""
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "findings" not in raw:
        raise ValidationError("document must be an object with a 'findings' array")
    findings = raw["findings"]
    if not isinstance(findings, list):
        raise ValidationError("'findings' must be a JSON array")
    for i, f in enumerate(findings):
        try:
            validate_finding(f)
        except ValidationError as e:
            raise ValidationError(f"finding[{i}]: {e}") from None
    return findings


def _line_sort_key(line: Any) -> int:
    if isinstance(line, int) and not isinstance(line, bool):
        return line
    if isinstance(line, str):
        m = LINE_RANGE_RE.match(line)
        if m:
            return int(m.group(1))
    return 0  # validated earlier; unreachable in practice


def sort_findings(findings: Iterable[dict]) -> list[dict]:
    """Sort findings per the contract: severity → file → line (start) → concern."""
    return sorted(
        findings,
        key=lambda f: (
            SEVERITY_RANK[f["severity"]],
            f["file"],
            _line_sort_key(f["line"]),
            f["concern"],
        ),
    )


def _escape_cell(text: str) -> str:
    # Collapse newlines to spaces, then escape pipes.
    collapsed = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", " ")
    return collapsed.replace("|", "\\|")


def _format_location(file: str, line: Any) -> str:
    return f"{file}:{line}"


def render_table(findings: Iterable[dict]) -> str:
    """Render the canonical markdown table + auto-fix prompt.

    Output ends with a single trailing newline.
    """
    sorted_findings = sort_findings(findings)
    lines = [
        "| Severity | Concern | Location | Why | Fix |",
        "| --- | --- | --- | --- | --- |",
    ]
    for f in sorted_findings:
        row = "| " + " | ".join(
            [
                f["severity"],
                _escape_cell(f["concern"]),
                _escape_cell(_format_location(f["file"], f["line"])),
                _escape_cell(f["why"]),
                _escape_cell(f["recommended_fix"]),
            ]
        ) + " |"
        lines.append(row)
    return "\n".join(lines) + "\n\n" + AUTO_FIX_PROMPT


# ---------------------------------------------------------------------------
# Tests (pytest-discoverable; also runnable via __main__).
# ---------------------------------------------------------------------------

POSITIVE_FIXTURES = (
    "valid_single_critical.json",
    "valid_mixed_severities.json",
    "valid_line_range.json",
    "valid_pipe_in_text.json",
    "valid_newline_in_text.json",
    "valid_empty.json",
    "canonical_input.json",
)

NEGATIVE_FIXTURES = (
    ("invalid_severity_enum.json", "severity"),
    ("invalid_missing_field.json", "missing required field"),
    ("invalid_line_non_numeric.json", "line string"),
    ("invalid_line_range_inverted.json", "start must be <="),
    ("invalid_line_wrong_type.json", "line must be int or"),
    ("invalid_extra_field.json", "unexpected field"),
    ("invalid_file_absolute.json", "repo-relative"),
)


def test_positive_fixtures_load_and_validate():
    for name in POSITIVE_FIXTURES:
        path = FIXTURES_DIR / name
        findings = load_findings(path)
        # Renders without raising.
        out = render_table(findings)
        assert out.endswith(AUTO_FIX_PROMPT), f"{name}: output missing auto-fix prompt"
        assert "| Severity | Concern | Location | Why | Fix |" in out, name


def test_negative_fixtures_reject():
    for name, expected_substr in NEGATIVE_FIXTURES:
        path = FIXTURES_DIR / name
        try:
            load_findings(path)
        except ValidationError as e:
            msg = str(e)
            assert expected_substr.lower() in msg.lower(), (
                f"{name}: expected substring {expected_substr!r} in error, got {msg!r}"
            )
            continue
        raise AssertionError(f"{name}: expected ValidationError, none raised")


def test_severity_sort_order():
    findings = [
        {"severity": "LOW", "file": "a", "line": 1, "concern": "x", "why": "w", "recommended_fix": "f"},
        {"severity": "CRITICAL", "file": "b", "line": 1, "concern": "x", "why": "w", "recommended_fix": "f"},
        {"severity": "MEDIUM", "file": "a", "line": 1, "concern": "x", "why": "w", "recommended_fix": "f"},
        {"severity": "HIGH", "file": "a", "line": 1, "concern": "x", "why": "w", "recommended_fix": "f"},
    ]
    ordered = [f["severity"] for f in sort_findings(findings)]
    assert ordered == ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


def test_sort_tiebreaker_by_file_then_line_then_concern():
    findings = [
        {"severity": "HIGH", "file": "src/b.py", "line": 10, "concern": "z", "why": "w", "recommended_fix": "f"},
        {"severity": "HIGH", "file": "src/a.py", "line": 20, "concern": "y", "why": "w", "recommended_fix": "f"},
        {"severity": "HIGH", "file": "src/a.py", "line": 10, "concern": "a", "why": "w", "recommended_fix": "f"},
        {"severity": "HIGH", "file": "src/a.py", "line": 10, "concern": "b", "why": "w", "recommended_fix": "f"},
    ]
    out = sort_findings(findings)
    assert [(f["file"], f["line"], f["concern"]) for f in out] == [
        ("src/a.py", 10, "a"),
        ("src/a.py", 10, "b"),
        ("src/a.py", 20, "y"),
        ("src/b.py", 10, "z"),
    ]


def test_line_range_sort_uses_start():
    findings = [
        {"severity": "LOW", "file": "f", "line": "50-60", "concern": "x", "why": "w", "recommended_fix": "f"},
        {"severity": "LOW", "file": "f", "line": "10-100", "concern": "x", "why": "w", "recommended_fix": "f"},
    ]
    out = sort_findings(findings)
    assert [f["line"] for f in out] == ["10-100", "50-60"]


def test_render_escapes_pipe_in_cells():
    findings = [
        {
            "severity": "LOW",
            "file": "src/x.py",
            "line": 1,
            "concern": "naming",
            "why": "a | b in why",
            "recommended_fix": "fix it",
        }
    ]
    out = render_table(findings)
    assert "a \\| b in why" in out
    assert "| a | b in why |" not in out


def test_render_collapses_newlines_in_cells():
    findings = [
        {
            "severity": "LOW",
            "file": "src/x.py",
            "line": 1,
            "concern": "naming",
            "why": "line1\nline2",
            "recommended_fix": "fix\r\nit",
        }
    ]
    out = render_table(findings)
    assert "line1 line2" in out
    assert "fix it" in out
    # Body of the rendered table should contain no raw newline within a row.
    table_section = out.split("\n\n", 1)[0]
    rows = table_section.splitlines()
    assert all(not r.startswith("line") for r in rows), "newline leaked into table rows"


def test_render_empty_findings_emits_header_only():
    out = render_table([])
    lines = out.splitlines()
    assert lines[0] == "| Severity | Concern | Location | Why | Fix |"
    assert lines[1] == "| --- | --- | --- | --- | --- |"
    # No data rows between header and blank line.
    assert lines[2] == ""
    # Auto-fix prompt follows.
    assert "[1] auto-fix all CRITICAL" in out


def test_auto_fix_prompt_verbatim_in_output():
    out = render_table([])
    assert out.endswith(AUTO_FIX_PROMPT)
    assert AUTO_FIX_PROMPT == (
        "What next?\n"
        "[1] auto-fix all CRITICAL\n"
        "[2] CRITICAL + HIGH\n"
        "[3] pick individually\n"
        "[4] file as new beads tasks\n"
        "[5] skip\n"
    )


def test_canonical_input_renders_byte_identical_to_expected():
    findings = load_findings(FIXTURES_DIR / "canonical_input.json")
    rendered = render_table(findings)
    expected = (FIXTURES_DIR / "expected_table.md").read_text(encoding="utf-8")
    assert rendered == expected, (
        "rendered output is not byte-identical to expected_table.md\n"
        f"---rendered---\n{rendered!r}\n---expected---\n{expected!r}"
    )


def test_validate_finding_rejects_bool_line():
    bad = {
        "severity": "LOW",
        "file": "f",
        "line": True,
        "concern": "c",
        "why": "w",
        "recommended_fix": "r",
    }
    try:
        validate_finding(bad)
    except ValidationError as e:
        assert "bool" in str(e).lower()
        return
    raise AssertionError("expected ValidationError for bool line")


def test_validate_finding_rejects_dotdot_in_file():
    bad = {
        "severity": "LOW",
        "file": "src/../secrets",
        "line": 1,
        "concern": "c",
        "why": "w",
        "recommended_fix": "r",
    }
    try:
        validate_finding(bad)
    except ValidationError as e:
        assert ".." in str(e)
        return
    raise AssertionError("expected ValidationError for .. in file")


def test_validate_finding_rejects_concern_too_long():
    bad = {
        "severity": "LOW",
        "file": "f",
        "line": 1,
        "concern": "x" * (CONCERN_MAX + 1),
        "why": "w",
        "recommended_fix": "r",
    }
    try:
        validate_finding(bad)
    except ValidationError as e:
        assert "concern" in str(e).lower()
        return
    raise AssertionError("expected ValidationError for over-long concern")


# ---------------------------------------------------------------------------
# CLI entry point.
# ---------------------------------------------------------------------------

ALL_TESTS = [
    test_positive_fixtures_load_and_validate,
    test_negative_fixtures_reject,
    test_severity_sort_order,
    test_sort_tiebreaker_by_file_then_line_then_concern,
    test_line_range_sort_uses_start,
    test_render_escapes_pipe_in_cells,
    test_render_collapses_newlines_in_cells,
    test_render_empty_findings_emits_header_only,
    test_auto_fix_prompt_verbatim_in_output,
    test_canonical_input_renders_byte_identical_to_expected,
    test_validate_finding_rejects_bool_line,
    test_validate_finding_rejects_dotdot_in_file,
    test_validate_finding_rejects_concern_too_long,
]


def _run_all_tests() -> int:
    failures = 0
    for t in ALL_TESTS:
        name = t.__name__
        try:
            t()
        except AssertionError as e:
            failures += 1
            print(f"FAIL {name}: {e}", file=sys.stderr)
        except ValidationError as e:
            failures += 1
            print(f"FAIL {name} (unexpected ValidationError): {e}", file=sys.stderr)
        except Exception as e:  # pragma: no cover - defensive
            failures += 1
            print(f"ERROR {name}: {type(e).__name__}: {e}", file=sys.stderr)
        else:
            print(f"PASS {name}")
    if failures:
        print(f"\n{failures} test(s) failed.", file=sys.stderr)
        return 1
    print(f"\nAll {len(ALL_TESTS)} test(s) passed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        help="Validate a single fixture file and exit.",
    )
    parser.add_argument(
        "--render",
        type=Path,
        help="Render the table for a single fixture file to stdout.",
    )
    args = parser.parse_args(argv)

    if args.fixture:
        try:
            load_findings(args.fixture)
        except ValidationError as e:
            print(f"INVALID: {e}", file=sys.stderr)
            return 1
        print(f"OK: {args.fixture}")
        return 0
    if args.render:
        findings = load_findings(args.render)
        sys.stdout.write(render_table(findings))
        return 0
    return _run_all_tests()


if __name__ == "__main__":
    sys.exit(main())
