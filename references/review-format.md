# review-format.md — Canonical Review Findings Contract

This is the canonical contract for findings emitted by `/specwright:review` and its subagents. Both the lightweight (tiny-flow) single-reviewer path and the four-subagent (feature / bugfix / quick) review path emit findings that conform to this schema. `/specwright:review` merges them, sorts them, and renders the tabular report below.

This document is the source of truth. Reviewer subagents, the merger, and the validator MUST agree with it byte-for-byte.

---

## 1. Finding schema

Each finding is a JSON object with exactly these six required fields and no others (extra fields are a validation error — keep the contract tight; new metadata is added by amending this doc, not by extending fixtures in the wild).

| Field             | Type             | Constraints                                                                |
|-------------------|------------------|----------------------------------------------------------------------------|
| `severity`        | string           | One of `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` (uppercase, exact match)         |
| `file`            | string           | Repo-relative POSIX path, non-empty, no leading `/`, no `..` segments       |
| `line`            | integer OR string| Integer >= 1, OR a range string `"N-M"` where `N` and `M` are ints, `N <= M`|
| `concern`         | string           | Short tag, non-empty, max 80 chars (e.g. `"spec drift"`)                    |
| `why`             | string           | Free-text explanation, non-empty                                            |
| `recommended_fix` | string           | Free-text actionable fix proposal, non-empty                                |

A review-output JSON document is an object with a single top-level `findings` array of these objects:

```json
{
  "findings": [
    {
      "severity": "CRITICAL",
      "file": "src/auth/login.ts",
      "line": 42,
      "concern": "secret leak",
      "why": "API key hardcoded in source.",
      "recommended_fix": "Move key to env var ANTHROPIC_API_KEY; rotate the leaked key."
    }
  ]
}
```

### Line field — wire format

- An integer `N` (Python/JSON `int`) for a single line; MUST be `>= 1`.
- A string `"N-M"` for a range, where `N` and `M` are decimal integers, `N <= M`, both `>= 1`. No whitespace, no other characters. (e.g. `"42-58"` is valid; `" 42 - 58 "`, `"42-"`, `"42-abc"`, `"58-42"` are invalid.)
- Any other type (float, list, boolean, null) is invalid.

### File field

- POSIX-style forward slashes only.
- MUST NOT start with `/`.
- MUST NOT contain `..` path segments.
- Trimmed; empty string invalid.

### Concern field

A short categorical tag. Examples: `"spec drift"`, `"test couples to internals"`, `"OWASP A03 injection"`, `"complexity"`, `"naming"`. Max 80 characters so the table renders without wrapping. Newlines forbidden.

### Why / recommended_fix

Free-text. Internal newlines are collapsed to a single space at render time (see "Table escaping" below). Pipe characters `|` are escaped as `\|` at render time. Empty strings are invalid.

---

## 2. Severity rules

Reviewer subagents MUST assign one of four buckets per finding:

- **CRITICAL** — security vulnerability (exploitable RCE, secret leak, auth bypass), data loss (destructive migration, dropped writes), or scope drift large enough that PRD acceptance fails.
- **HIGH** — missing acceptance criterion in the implementation, a test that does not actually verify the intended behavior (e.g. asserts on a mock it just configured), or an OWASP Top-10 issue that is not directly exploitable (validation hole, missing authz check on a non-critical path).
- **MEDIUM** — code-quality concerns, pattern divergence from established codebase conventions, complexity above project threshold, missing error handling on non-critical paths.
- **LOW** — nits, naming preferences, optional improvements, doc typos.

Severities are uppercase string enums. Anything else (`"critical"`, `"Crit"`, `"P0"`, `1`) is a validation error.

---

## 3. Merge & sort rules

`/specwright:review` collects findings from all reviewer subagents into a single array, then sorts deterministically:

1. **Severity** in fixed order: `CRITICAL` → `HIGH` → `MEDIUM` → `LOW`.
2. **File path** lexicographically ascending (byte order).
3. **Line** numerically ascending. For range strings `"N-M"`, sort by the start `N`.
4. **Concern** lexicographically ascending (tiebreaker; same severity + same file + same line is rare but must be deterministic).

The sort MUST be stable so the byte-identity property holds across runs given the same input set.

---

## 4. Tabular output spec

After merge + sort, `/specwright:review` renders the findings as a markdown table with this exact header line:

```
| Severity | Concern | Location | Why | Fix |
| --- | --- | --- | --- | --- |
```

One row per finding. Columns:

- **Severity** — the enum literal (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
- **Concern** — the finding's `concern`.
- **Location** — `"<file>:<line>"`. For range lines, `"<file>:N-M"`.
- **Why** — the finding's `why`, escaped (see below).
- **Fix** — the finding's `recommended_fix`, escaped.

### Table escaping

- Pipe `|` in any cell becomes `\|`.
- Any internal newline (`\r`, `\n`, `\r\n`) is collapsed to a single space `" "`.
- Multiple consecutive spaces produced by escaping are preserved as-is (no further collapsing) so escaping is reversible.

### Padding & whitespace

- Columns are separated by `" | "` (single space, pipe, single space).
- Each row starts with `"| "` and ends with `" |"`.
- No column padding to fixed widths. Use the literal cell text only.

### Empty findings table

If the findings list is empty, the table renderer still emits the two header lines, followed by no data rows.

---

## 5. Auto-fix prompt (verbatim)

Immediately after the table, the renderer emits one blank line, then this exact prompt, character-for-character:

```
What next?
[1] auto-fix all CRITICAL
[2] CRITICAL + HIGH
[3] pick individually
[4] file as new beads tasks
[5] skip
```

These five choices are quoted verbatim from `PLAN.md` §7. `[1]` establishes the auto-fix action; `[2]` inherits it. Do not normalise or pad them.

The five choices are fixed. Reviewer subagents and the merger MUST NOT alter, reorder, or extend them. The `/specwright:review` skill reads the user's reply (`1`–`5`) and dispatches.

The rendered document ends with a single trailing newline (`\n`) after the `[5] skip` line.

---

## 6. Validation

`tests/review_format_validator.py` enforces this contract. It:

- Loads each fixture from `tests/fixtures/review-format/`.
- For positive fixtures (`valid_*.json`), validates every finding and renders the table; asserts no validation errors.
- For negative fixtures (`invalid_*.json`), asserts validation rejects with the specific error documented in the fixture filename / description below.
- Renders the canonical input fixture (`canonical_input.json`) and asserts byte-identity against `expected_table.md`.

### Negative fixtures (each fails for one distinct, documented reason)

1. `invalid_severity_enum.json` — `severity` is `"Critical"` (wrong case).
2. `invalid_missing_field.json` — finding is missing `recommended_fix`.
3. `invalid_line_non_numeric.json` — `line` is the string `"abc"`.
4. `invalid_line_range_inverted.json` — `line` is `"58-42"` (start > end).
5. `invalid_line_wrong_type.json` — `line` is `null`.
6. `invalid_extra_field.json` — finding has an extra `priority` field not in the schema.
7. `invalid_file_absolute.json` — `file` starts with `/`.

### Positive fixtures

1. `valid_single_critical.json` — one CRITICAL with integer line.
2. `valid_mixed_severities.json` — one of each severity, integer lines.
3. `valid_line_range.json` — uses `"N-M"` range form.
4. `valid_pipe_in_text.json` — `why` contains a literal `|` that must be escaped at render time.
5. `valid_newline_in_text.json` — `recommended_fix` contains an internal newline that must collapse to a space.
6. `valid_empty.json` — empty `findings` array (renders the bare header).
7. `canonical_input.json` — the byte-identity input that pairs with `expected_table.md`.

### Runnable both ways

```
python tests/review_format_validator.py        # exits 0 on success, non-zero on failure
python -m pytest tests/review_format_validator.py -v
```

The validator uses stdlib only (`json`, `re`, `pathlib`, `sys`, `argparse`).
