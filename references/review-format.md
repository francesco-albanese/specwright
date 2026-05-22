# review-format.md — Review Findings Contract

Contract for findings emitted by `/specwright:review` subagents. Both the four-subagent fan-out (feature / bugfix / quick flows) and the single-reviewer path (tiny flow) produce findings in this schema. `/specwright:review` merges, sorts, and renders the tabular report, then presents the auto-fix prompt.

---

## 1. Finding schema

Each finding has exactly these six fields:

| Field | Type | Constraints |
| --- | --- | --- |
| `severity` | string | One of `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` (uppercase exact match) |
| `file` | string | Repo-relative POSIX path; no leading `/`, no `..` segments, non-empty |
| `line` | integer or string | Integer >= 1, or range string `"N-M"` where N <= M, both >= 1 |
| `concern` | string | Short tag, max 80 chars, no newlines (e.g. `"spec drift"`) |
| `why` | string | Free-text explanation, non-empty |
| `recommended_fix` | string | Actionable fix proposal, non-empty |

---

## 2. Severity rules

- **CRITICAL** — security vulnerability (exploitable RCE, secret leak, auth bypass), data loss (destructive migration, dropped writes), or scope drift large enough that PRD acceptance fails.
- **HIGH** — missing acceptance criterion in the implementation, a test that does not verify intended behavior (e.g. asserts only on a mock it just configured), or an OWASP Top-10 issue not directly exploitable (validation hole, missing authz check on a non-critical path).
- **MEDIUM** — code-quality concerns, pattern divergence from codebase conventions, complexity above project threshold, missing error handling on non-critical paths.
- **LOW** — nits, naming preferences, optional improvements, doc typos.

---

## 3. Reviewer roles

`/specwright:review` fans out to four subagents, each in isolated context:

| Subagent | Concern |
| --- | --- |
| Spec alignment | PR diff vs `requirements.md` + `design.md`; drift, missing ACs, scope creep |
| Test quality | intent vs implementation tests, vertical-slice coverage, mocks at boundaries only |
| Code quality + security | codebase patterns, complexity, OWASP top 10, secret leaks |
| Vertical-slice adherence | did the PR stay inside slice scope? PR reviewable in <30 min? |

Tiny flow uses a single combined reviewer subagent covering all four concerns.

---

## 4. Merge and sort

`/specwright:review` collects all findings into one array sorted by:

1. Severity: `CRITICAL` → `HIGH` → `MEDIUM` → `LOW`
2. File path lexicographically ascending
3. Line numerically ascending (range `"N-M"` sorts by N)
4. Concern lexicographically ascending (tiebreaker)

---

## 5. Tabular output

Findings render as a markdown table with this exact header:

```markdown
| Severity | Concern | Location | Why | Fix |
| --- | --- | --- | --- | --- |
```

Columns:

- **Severity** — enum literal (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`)
- **Concern** — the finding's `concern` tag
- **Location** — `<file>:<line>` (e.g. `src/auth/login.ts:42` or `src/auth/login.ts:42-58`)
- **Why** — the finding's `why`; internal newlines collapse to a single space
- **Fix** — the finding's `recommended_fix`; same collapsing

Pipe characters in cell content escape as `\|`.

### Example

| Severity | Concern | Location | Why | Fix |
| --- | --- | --- | --- | --- |
| CRITICAL | secret leak | src/auth/login.ts:42 | API key hardcoded in source. | Move to env var `ANTHROPIC_API_KEY`; rotate the leaked key. |
| HIGH | missing AC | src/orders/create.ts:88-95 | AC "WHEN order submitted THE SYSTEM SHALL send confirmation email" has no corresponding test or implementation. | Add email dispatch call and a test asserting the email is sent on successful order creation. |
| MEDIUM | complexity | src/pipeline/runner.ts:120 | Function `buildPipeline` has cyclomatic complexity 18; project threshold is 10. | Extract the branch-handling logic into a dedicated `resolveBranch` helper. |

If findings is empty the table header is still emitted with no data rows.

---

## 6. Auto-fix prompt

Immediately after the table, one blank line, then this prompt verbatim:

```text
What next?
[1] auto-fix all CRITICAL
[2] CRITICAL + HIGH
[3] pick individually
[4] file as new beads tasks
[5] skip
```

The five choices are fixed. Subagents and the merger must not alter, reorder, or extend them. `/specwright:review` reads the user's reply (`1`–`5`) and dispatches: selected items run as `/specwright:execute` mini-runs in the same worktree, or become follow-up beads slices linked to the original (choice `[4]`).

---

## 7. Related references

- `spec-format.md` — EARS AC notation and `requirements.md` structure
- `slice-schema.md` — beads slice metadata fields (`acceptance_criteria`, `depends_on`, `estimated_touched_paths`)
- `verify-discovery.md` — how the execute pipeline discovers test / lint commands
- `stacking-rules.md` — stacked PR conventions and conflict resolution
