"""Validator for specwright spec-format artifacts (requirements.md, design.md, bugfix.md).

This module is the executable form of the contract documented in
``references/spec-format.md``. It is intentionally stdlib-only (re, pathlib,
json, sys, argparse) so that it runs in any environment without extra
dependencies.

Usage as a CLI::

    python tests/spec_format_validator.py <path-to-file> [<more paths>]
    python tests/spec_format_validator.py --type requirements <file>
    python tests/spec_format_validator.py --json <file>

Usage under pytest::

    python -m pytest tests/spec_format_validator.py -v

Pytest collects the ``test_*`` functions at the bottom of the file. They walk
``tests/fixtures/spec-format/`` and assert that every positive fixture passes
and every negative fixture is rejected with the rule named in its filename.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    """A single rule violation discovered by the validator."""

    rule: str
    message: str

    def format(self, path: Path) -> str:
        return f"{path}: rule '{self.rule}' failed: {self.message}"


@dataclass
class Result:
    """The outcome of validating one document."""

    path: Path
    artifact_type: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings

    def add(self, rule: str, message: str) -> None:
        self.findings.append(Finding(rule=rule, message=message))

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "artifact_type": self.artifact_type,
            "ok": self.ok,
            "findings": [
                {"rule": f.rule, "message": f.message} for f in self.findings
            ],
        }


# ---------------------------------------------------------------------------
# Markdown parsing helpers (stdlib only)
# ---------------------------------------------------------------------------


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_FENCE_RE = re.compile(r"^```\s*([A-Za-z0-9_-]*)\s*$")


@dataclass
class Section:
    level: int
    title: str
    start_line: int  # 0-indexed line containing the heading
    body_lines: list[str] = field(default_factory=list)


def _strip_code_fences(lines: list[str]) -> list[str]:
    """Return ``lines`` with fenced code blocks removed.

    Used so that headings or list bullets that appear *inside* a fenced block
    are not mistaken for structural elements of the document.
    """
    out: list[str] = []
    in_fence = False
    for line in lines:
        if _FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            out.append("")  # keep line count stable
            continue
        if in_fence:
            out.append("")
        else:
            out.append(line)
    return out


def _parse_sections(text: str) -> tuple[list[Section], str | None]:
    """Split ``text`` into sections by H2 heading.

    Returns ``(sections, h1_title)``. ``h1_title`` is ``None`` if the doc has
    no H1. Code-fenced content is preserved inside section bodies but is
    ignored for heading detection.
    """
    raw_lines = text.splitlines()
    structural_lines = _strip_code_fences(raw_lines)

    h1: str | None = None
    sections: list[Section] = []
    current: Section | None = None

    for idx, line in enumerate(structural_lines):
        match = _HEADING_RE.match(line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            if level == 1 and h1 is None:
                h1 = title
                continue
            if level == 2:
                if current is not None:
                    sections.append(current)
                current = Section(level=2, title=title, start_line=idx)
                continue
        if current is not None:
            # Preserve the original (un-stripped) line for body inspection so
            # that fenced code blocks are still visible to rule functions.
            current.body_lines.append(raw_lines[idx])
    if current is not None:
        sections.append(current)
    return sections, h1


def _find_section(sections: list[Section], titles: Iterable[str]) -> Section | None:
    """Return the first section whose title matches (case-insensitive)."""
    normalized = {t.lower() for t in titles}
    for section in sections:
        if section.title.lower() in normalized:
            return section
    return None


def _section_index(sections: list[Section], titles: Iterable[str]) -> int:
    """Return the index of the first section matching ``titles``, or -1."""
    normalized = {t.lower() for t in titles}
    for i, section in enumerate(sections):
        if section.title.lower() in normalized:
            return i
    return -1


def _list_items(body_lines: list[str]) -> list[str]:
    """Extract markdown list items (``-`` or ``*``) from ``body_lines``."""
    items: list[str] = []
    in_fence = False
    for line in body_lines:
        if _FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        stripped = line.lstrip()
        if stripped.startswith(("- ", "* ")):
            items.append(stripped[2:].strip())
    return items


def _has_mermaid_block(body_lines: list[str], required_keyword: str) -> bool:
    """Return True if ``body_lines`` contains a ```` ```mermaid ```` fence
    whose first non-blank inner line starts with ``required_keyword``."""
    in_mermaid = False
    for line in body_lines:
        fence = _FENCE_RE.match(line.strip())
        if fence:
            lang = fence.group(1).lower()
            if not in_mermaid and lang == "mermaid":
                in_mermaid = True
                continue
            if in_mermaid:
                in_mermaid = False
                continue
        if in_mermaid:
            stripped = line.strip()
            if not stripped:
                continue
            return stripped.lower().startswith(required_keyword.lower())
    return False


# ---------------------------------------------------------------------------
# EARS notation
# ---------------------------------------------------------------------------

# Canonical EARS variants. The "shall" verb is mandatory in all four. Patterns
# are anchored at the start and tolerate trailing punctuation / clauses.

_EARS_PATTERNS: dict[str, re.Pattern[str]] = {
    "ubiquitous": re.compile(
        r"^The\s+.+?\s+shall\s+.+?[.!?]?\s*$",
        re.IGNORECASE,
    ),
    "event_driven": re.compile(
        r"^When\s+.+?,\s*the\s+.+?\s+shall\s+.+?[.!?]?\s*$",
        re.IGNORECASE,
    ),
    "state_driven": re.compile(
        r"^While\s+.+?,\s*the\s+.+?\s+shall\s+.+?[.!?]?\s*$",
        re.IGNORECASE,
    ),
    "optional": re.compile(
        r"^Where\s+.+?,\s*the\s+.+?\s+shall\s+.+?[.!?]?\s*$",
        re.IGNORECASE,
    ),
}

_EARS_TRIGGER_WORDS = ("when ", "while ", "where ")


def classify_ears(text: str) -> str | None:
    """Return the EARS variant name for ``text`` or ``None`` if invalid."""
    candidate = text.strip()
    for variant, pattern in _EARS_PATTERNS.items():
        if pattern.match(candidate):
            return variant
    return None


def ears_failure_reason(text: str) -> str:
    """Explain why ``text`` is not valid EARS — used in error messages."""
    candidate = text.strip()
    lowered = candidate.lower()
    if " shall " not in f" {lowered} ":
        return "missing 'shall' verb"
    if lowered.startswith(_EARS_TRIGGER_WORDS):
        # Has a trigger keyword but didn't match any pattern — likely missing
        # the comma + "the <system>" structure.
        return "trigger clause is malformed (expected 'When/While/Where <trigger>, the <system> shall <response>')"
    if lowered.startswith("if "):
        return "unsupported EARS variant 'if/then' — use When/While/Where or ubiquitous form"
    if not lowered.startswith("the "):
        return "ubiquitous statement must start with 'The'"
    return "does not match any of the four canonical EARS variants"


# ---------------------------------------------------------------------------
# Rules: requirements.md
# ---------------------------------------------------------------------------

_USER_STORIES_TITLES = ("User Stories", "User Story")
_ACCEPTANCE_TITLES = ("Acceptance Criteria", "Acceptance Criterion")


def _rule_has_h1(text: str, sections: list[Section], h1: str | None, result: Result) -> None:
    if not h1:
        result.add("has_h1", "document must start with a single '#' H1 heading")


def _rule_requirements_has_user_stories(
    text: str, sections: list[Section], h1: str | None, result: Result
) -> None:
    if _find_section(sections, _USER_STORIES_TITLES) is None:
        result.add(
            "requirements_has_user_stories",
            "missing required '## User Stories' section",
        )


def _rule_requirements_has_acceptance_criteria(
    text: str, sections: list[Section], h1: str | None, result: Result
) -> None:
    if _find_section(sections, _ACCEPTANCE_TITLES) is None:
        result.add(
            "requirements_has_acceptance_criteria",
            "missing required '## Acceptance Criteria' section",
        )


def _rule_requirements_acceptance_criteria_use_ears(
    text: str, sections: list[Section], h1: str | None, result: Result
) -> None:
    section = _find_section(sections, _ACCEPTANCE_TITLES)
    if section is None:
        return  # covered by another rule
    items = _list_items(section.body_lines)
    if not items:
        result.add(
            "requirements_acceptance_criteria_use_ears",
            "'## Acceptance Criteria' must contain at least one markdown list item",
        )
        return
    for item in items:
        if classify_ears(item) is None:
            result.add(
                "requirements_acceptance_criteria_use_ears",
                f"acceptance criterion is not valid EARS: {item!r} ({ears_failure_reason(item)})",
            )


# ---------------------------------------------------------------------------
# Rules: design.md
# ---------------------------------------------------------------------------

_OVERVIEW_TITLES = ("Overview",)
_SEQUENCE_TITLES = ("Sequence", "Sequence Diagram")
_DATA_FLOW_TITLES = ("Data Flow", "Data-Flow")


def _rule_design_has_overview(
    text: str, sections: list[Section], h1: str | None, result: Result
) -> None:
    if _find_section(sections, _OVERVIEW_TITLES) is None:
        result.add(
            "design_has_overview",
            "missing required '## Overview' section",
        )


def _rule_design_has_sequence(
    text: str, sections: list[Section], h1: str | None, result: Result
) -> None:
    section = _find_section(sections, _SEQUENCE_TITLES)
    if section is None:
        result.add(
            "design_has_sequence",
            "missing required '## Sequence' (or '## Sequence Diagram') section",
        )
        return
    if not _has_mermaid_block(section.body_lines, "sequenceDiagram"):
        result.add(
            "design_has_sequence",
            "'## Sequence' section must contain a ```mermaid``` block starting with 'sequenceDiagram'",
        )


def _rule_design_has_data_flow(
    text: str, sections: list[Section], h1: str | None, result: Result
) -> None:
    section = _find_section(sections, _DATA_FLOW_TITLES)
    if section is None:
        result.add(
            "design_has_data_flow",
            "missing required '## Data Flow' section",
        )
        return
    if not (
        _has_mermaid_block(section.body_lines, "flowchart")
        or _has_mermaid_block(section.body_lines, "graph")
    ):
        result.add(
            "design_has_data_flow",
            "'## Data Flow' section must contain a ```mermaid``` block starting with 'flowchart' or 'graph'",
        )


def _rule_design_section_order(
    text: str, sections: list[Section], h1: str | None, result: Result
) -> None:
    overview_idx = _section_index(sections, _OVERVIEW_TITLES)
    sequence_idx = _section_index(sections, _SEQUENCE_TITLES)
    data_flow_idx = _section_index(sections, _DATA_FLOW_TITLES)
    if -1 in (overview_idx, sequence_idx, data_flow_idx):
        return  # covered by individual presence rules
    if not (overview_idx < sequence_idx < data_flow_idx):
        result.add(
            "design_section_order",
            "required sections must appear in order: Overview -> Sequence -> Data Flow",
        )


# ---------------------------------------------------------------------------
# Rules: bugfix.md
# ---------------------------------------------------------------------------

_CURRENT_BEHAVIOR_TITLES = ("Current Behavior", "Current Behaviour")
_EXPECTED_BEHAVIOR_TITLES = ("Expected Behavior", "Expected Behaviour")
_UNCHANGED_BEHAVIOR_TITLES = ("Unchanged Behavior", "Unchanged Behaviour")


def _rule_bugfix_has_current_behavior(
    text: str, sections: list[Section], h1: str | None, result: Result
) -> None:
    if _find_section(sections, _CURRENT_BEHAVIOR_TITLES) is None:
        result.add(
            "bugfix_has_current_behavior",
            "missing required '## Current Behavior' section",
        )


def _rule_bugfix_has_expected_behavior(
    text: str, sections: list[Section], h1: str | None, result: Result
) -> None:
    if _find_section(sections, _EXPECTED_BEHAVIOR_TITLES) is None:
        result.add(
            "bugfix_has_expected_behavior",
            "missing required '## Expected Behavior' section",
        )


def _rule_bugfix_has_unchanged_behavior(
    text: str, sections: list[Section], h1: str | None, result: Result
) -> None:
    if _find_section(sections, _UNCHANGED_BEHAVIOR_TITLES) is None:
        result.add(
            "bugfix_has_unchanged_behavior",
            "missing required '## Unchanged Behavior' section",
        )


def _rule_bugfix_expected_uses_ears(
    text: str, sections: list[Section], h1: str | None, result: Result
) -> None:
    section = _find_section(sections, _EXPECTED_BEHAVIOR_TITLES)
    if section is None:
        return  # covered by another rule
    items = _list_items(section.body_lines)
    if not items:
        result.add(
            "bugfix_expected_uses_ears",
            "'## Expected Behavior' must contain at least one EARS list item",
        )
        return
    for item in items:
        if classify_ears(item) is None:
            result.add(
                "bugfix_expected_uses_ears",
                f"expected-behavior item is not valid EARS: {item!r} ({ears_failure_reason(item)})",
            )


def _rule_bugfix_section_order(
    text: str, sections: list[Section], h1: str | None, result: Result
) -> None:
    cur_idx = _section_index(sections, _CURRENT_BEHAVIOR_TITLES)
    exp_idx = _section_index(sections, _EXPECTED_BEHAVIOR_TITLES)
    unc_idx = _section_index(sections, _UNCHANGED_BEHAVIOR_TITLES)
    if -1 in (cur_idx, exp_idx, unc_idx):
        return  # presence rules handle missing sections
    if not (cur_idx < exp_idx < unc_idx):
        result.add(
            "bugfix_section_order",
            "required sections must appear in order: Current Behavior -> Expected Behavior -> Unchanged Behavior",
        )


# ---------------------------------------------------------------------------
# Rule registry per artifact type
# ---------------------------------------------------------------------------

RuleFn = Callable[[str, list[Section], "str | None", Result], None]

_RULES: dict[str, list[RuleFn]] = {
    "requirements": [
        _rule_has_h1,
        _rule_requirements_has_user_stories,
        _rule_requirements_has_acceptance_criteria,
        _rule_requirements_acceptance_criteria_use_ears,
    ],
    "design": [
        _rule_has_h1,
        _rule_design_has_overview,
        _rule_design_has_sequence,
        _rule_design_has_data_flow,
        _rule_design_section_order,
    ],
    "bugfix": [
        _rule_has_h1,
        _rule_bugfix_has_current_behavior,
        _rule_bugfix_has_expected_behavior,
        _rule_bugfix_has_unchanged_behavior,
        _rule_bugfix_expected_uses_ears,
        _rule_bugfix_section_order,
    ],
}

KNOWN_ARTIFACT_TYPES = tuple(_RULES.keys())


# ---------------------------------------------------------------------------
# Top-level validation
# ---------------------------------------------------------------------------


def infer_artifact_type(path: Path) -> str | None:
    """Best-effort: pick the artifact type from path components or filename."""
    parts_lower = [p.lower() for p in path.parts]
    for artifact in KNOWN_ARTIFACT_TYPES:
        if artifact in parts_lower:
            return artifact
    stem = path.stem.lower()
    for artifact in KNOWN_ARTIFACT_TYPES:
        if artifact in stem:
            return artifact
    return None


def validate_text(text: str, artifact_type: str, path: Path | None = None) -> Result:
    """Run all rules for ``artifact_type`` against ``text``."""
    if artifact_type not in _RULES:
        raise ValueError(
            f"unknown artifact_type {artifact_type!r}; expected one of {KNOWN_ARTIFACT_TYPES}"
        )
    sections, h1 = _parse_sections(text)
    result = Result(path=path or Path("<memory>"), artifact_type=artifact_type)
    for rule in _RULES[artifact_type]:
        rule(text, sections, h1, result)
    return result


def validate_file(path: Path, artifact_type: str | None = None) -> Result:
    """Validate the markdown file at ``path``."""
    artifact_type = artifact_type or infer_artifact_type(path)
    if artifact_type is None:
        raise ValueError(
            f"cannot infer artifact_type for {path}; pass --type explicitly"
        )
    text = path.read_text(encoding="utf-8")
    return validate_text(text, artifact_type, path=path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_human(results: list[Result]) -> str:
    lines: list[str] = []
    for result in results:
        if result.ok:
            lines.append(f"OK  {result.path} ({result.artifact_type})")
        else:
            lines.append(f"FAIL {result.path} ({result.artifact_type})")
            for finding in result.findings:
                lines.append(f"  - {finding.format(result.path)}")
    return "\n".join(lines)


def _cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="spec_format_validator",
        description="Validate specwright spec-format markdown artifacts.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="markdown files to validate; defaults to the fixtures tree",
    )
    parser.add_argument(
        "--type",
        choices=KNOWN_ARTIFACT_TYPES,
        help="force the artifact type instead of inferring from the path",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON instead of human-readable text",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the fixture suite and exit non-zero on any unexpected outcome",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    if not args.paths:
        parser.error("at least one path is required (or pass --self-test)")

    results: list[Result] = []
    for path in args.paths:
        results.append(validate_file(path, args.type))

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        print(_format_human(results))

    return 0 if all(r.ok for r in results) else 1


# ---------------------------------------------------------------------------
# Self-test (also used by pytest)
# ---------------------------------------------------------------------------


_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "spec-format"


# Map negative fixture filenames (stem) to the rule name they MUST trigger.
# This is what the advisor recommended: encode the violation in the name so
# tests assert a *specific* rule fired, not just "something failed".
_NEGATIVE_EXPECTATIONS: dict[str, dict[str, str]] = {
    "requirements": {
        "missing_h1": "has_h1",
        "missing_user_stories": "requirements_has_user_stories",
        "missing_acceptance_criteria": "requirements_has_acceptance_criteria",
        "ears_no_shall": "requirements_acceptance_criteria_use_ears",
        "ears_unknown_variant": "requirements_acceptance_criteria_use_ears",
    },
    "design": {
        "missing_overview": "design_has_overview",
        "missing_sequence": "design_has_sequence",
        "missing_data_flow": "design_has_data_flow",
        "sequence_not_mermaid": "design_has_sequence",
        "wrong_section_order": "design_section_order",
    },
    "bugfix": {
        "missing_current_behavior": "bugfix_has_current_behavior",
        "missing_expected_behavior": "bugfix_has_expected_behavior",
        "missing_unchanged_behavior": "bugfix_has_unchanged_behavior",
        "expected_no_ears": "bugfix_expected_uses_ears",
        "wrong_section_order": "bugfix_section_order",
    },
}


def _iter_fixtures(artifact: str, polarity: str) -> Iterable[Path]:
    folder = _FIXTURE_ROOT / artifact / polarity
    if not folder.exists():
        return []
    return sorted(folder.glob("*.md"))


def _self_test() -> int:
    failures: list[str] = []
    for artifact in KNOWN_ARTIFACT_TYPES:
        for path in _iter_fixtures(artifact, "positive"):
            result = validate_file(path, artifact)
            if not result.ok:
                failures.append(
                    f"positive fixture should have passed: {path}\n  "
                    + "\n  ".join(f.format(path) for f in result.findings)
                )
        for path in _iter_fixtures(artifact, "negative"):
            result = validate_file(path, artifact)
            if result.ok:
                failures.append(f"negative fixture should have failed: {path}")
                continue
            expected_rule = _NEGATIVE_EXPECTATIONS.get(artifact, {}).get(path.stem)
            if expected_rule is None:
                failures.append(
                    f"negative fixture {path} has no expected rule registered "
                    f"in _NEGATIVE_EXPECTATIONS[{artifact!r}]"
                )
                continue
            triggered = {f.rule for f in result.findings}
            if expected_rule not in triggered:
                failures.append(
                    f"negative fixture {path} expected rule {expected_rule!r} "
                    f"to fire; got {sorted(triggered)}"
                )
    if failures:
        print("FAIL", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        return 1
    print(
        f"OK — {sum(1 for a in KNOWN_ARTIFACT_TYPES for _ in _iter_fixtures(a, 'positive'))}"
        f" positive + {sum(1 for a in KNOWN_ARTIFACT_TYPES for _ in _iter_fixtures(a, 'negative'))}"
        f" negative fixtures across {len(KNOWN_ARTIFACT_TYPES)} artifact types validated."
    )
    return 0


# ---------------------------------------------------------------------------
# Pytest hooks
# ---------------------------------------------------------------------------


def test_positive_fixtures_pass() -> None:
    """Every positive fixture must produce zero findings."""
    failures: list[str] = []
    total = 0
    for artifact in KNOWN_ARTIFACT_TYPES:
        for path in _iter_fixtures(artifact, "positive"):
            total += 1
            result = validate_file(path, artifact)
            if not result.ok:
                failures.append(
                    f"{path}: " + "; ".join(f.format(path) for f in result.findings)
                )
    assert not failures, "positive fixtures failed:\n" + "\n".join(failures)
    assert total >= 9, f"expected >= 9 positive fixtures (3 per artifact), found {total}"


def test_negative_fixtures_fail_with_expected_rule() -> None:
    """Every negative fixture must trigger the rule encoded in its filename."""
    failures: list[str] = []
    total = 0
    for artifact in KNOWN_ARTIFACT_TYPES:
        for path in _iter_fixtures(artifact, "negative"):
            total += 1
            result = validate_file(path, artifact)
            if result.ok:
                failures.append(f"{path}: expected to fail but passed")
                continue
            expected_rule = _NEGATIVE_EXPECTATIONS.get(artifact, {}).get(path.stem)
            if expected_rule is None:
                failures.append(
                    f"{path}: no expected rule registered in _NEGATIVE_EXPECTATIONS"
                )
                continue
            triggered = {f.rule for f in result.findings}
            if expected_rule not in triggered:
                failures.append(
                    f"{path}: expected rule {expected_rule!r}, got {sorted(triggered)}"
                )
    assert not failures, "negative fixtures failed:\n" + "\n".join(failures)
    assert total >= 9, f"expected >= 9 negative fixtures (3 per artifact), found {total}"


def test_minimum_fixture_counts() -> None:
    """The acceptance criterion mandates >= 3 positive and >= 3 negative per type."""
    for artifact in KNOWN_ARTIFACT_TYPES:
        positives = list(_iter_fixtures(artifact, "positive"))
        negatives = list(_iter_fixtures(artifact, "negative"))
        assert len(positives) >= 3, (
            f"artifact {artifact!r} has {len(positives)} positive fixtures, need >= 3"
        )
        assert len(negatives) >= 3, (
            f"artifact {artifact!r} has {len(negatives)} negative fixtures, need >= 3"
        )


def test_all_four_ears_variants_are_covered() -> None:
    """The positive requirements fixtures must collectively exercise all four
    canonical EARS variants."""
    seen: set[str] = set()
    for path in _iter_fixtures("requirements", "positive"):
        sections, _ = _parse_sections(path.read_text(encoding="utf-8"))
        section = _find_section(sections, _ACCEPTANCE_TITLES)
        if section is None:
            continue
        for item in _list_items(section.body_lines):
            variant = classify_ears(item)
            if variant is not None:
                seen.add(variant)
    expected = {"ubiquitous", "event_driven", "state_driven", "optional"}
    missing = expected - seen
    assert not missing, f"positive fixtures do not cover EARS variants: {missing}"


def test_ears_classifier_recognises_each_variant() -> None:
    """Unit-level sanity check for the EARS classifier."""
    assert classify_ears("The system shall log every request.") == "ubiquitous"
    assert (
        classify_ears(
            "When the user submits valid credentials, the system shall issue a token."
        )
        == "event_driven"
    )
    assert (
        classify_ears(
            "While the queue is full, the system shall reject incoming requests."
        )
        == "state_driven"
    )
    assert (
        classify_ears(
            "Where loyalty mode is enabled, the system shall deduct points on order completion."
        )
        == "optional"
    )
    # Negative: missing 'shall'
    assert classify_ears("When X happens, the system returns 200.") is None
    # Negative: unsupported variant
    assert classify_ears("If the user cancels, then the system shall refund.") is None


def test_cli_exits_nonzero_for_invalid_doc(tmp_path) -> None:
    """CLI mode must exit with status 1 when any input is invalid."""
    bad = tmp_path / "requirements.md"
    bad.write_text("# Title\n\n## Acceptance Criteria\n\n- Not EARS at all.\n")
    exit_code = _cli([str(bad)])
    assert exit_code == 1


def test_cli_exits_zero_for_valid_doc(tmp_path) -> None:
    good = tmp_path / "requirements.md"
    good.write_text(
        "# Title\n\n## User Stories\n\n- As a user, I want X so that Y.\n\n"
        "## Acceptance Criteria\n\n- The system shall do Z.\n"
    )
    exit_code = _cli([str(good)])
    assert exit_code == 0


def test_cli_self_test_runs_clean() -> None:
    """The bundled --self-test sweep must succeed against the fixture tree."""
    assert _self_test() == 0


if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.exit(_self_test())
    sys.exit(_cli(sys.argv[1:]))
