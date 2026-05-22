---
name: specwright-review
description: Multi-subagent code-review skill for specwright — four-subagent fan-out for feature/bugfix/quick flows, single-subagent lightweight mode for tiny flow, merged severity-sorted tabular report, and numbered auto-fix prompt.
---

# /specwright:review

**Invocation:** `/specwright:review <pr|slice>`

`<pr|slice>` is the PR number or beads slice ID being reviewed.

---

## Mode selection

| Flow that produced the PR | Mode to use |
| --- | --- |
| `/specwright:feature`, `/specwright:bugfix`, `/specwright:quick` | Mode 1 — four-subagent fan-out |
| `/specwright:tiny` | Mode 2 — single-subagent lightweight |

Detect the originating flow from the beads slice metadata (`spec_path` field): if `spec_path` is `null`, use Mode 2; otherwise use Mode 1. When the PR's slice ID cannot be determined, default to Mode 1.

---

## Mode 1 — four-subagent fan-out

### Setup

Before spawning subagents, load:

1. The beads slice body for `<slice>` — acceptance criteria, `estimated_touched_paths`, `spec_path`, `depends_on`.
2. `<spec_path>/requirements.md` and `<spec_path>/design.md` from disk.
3. The PR diff: `gh pr diff <pr>`.
4. Whether this is a bugfix flow: check if the slice has a `depends_on` parent whose title starts with "failing regression test" or if `bugfix.md` exists at `<spec_path>/bugfix.md`.

### Spawn four subagents IN PARALLEL

Each subagent receives its own isolated context with only the data it needs. Each emits a list of findings conforming to the schema in §Finding schema below.

**Subagent 1 — Spec alignment**

Context to provide: PR diff, `requirements.md`, `design.md`.

Task:
- Compare every acceptance criterion in `requirements.md` against the PR diff.
- Flag ACs present in `requirements.md` that have no corresponding implementation or test in the diff (missing AC — severity HIGH).
- Flag changes in the diff that implement behavior not described in any AC (scope creep — severity MEDIUM or CRITICAL depending on size; CRITICAL if scope drift is large enough that PRD acceptance would fail).
- Flag divergence between `design.md` architecture (sequences, data flows, module boundaries) and the implementation visible in the diff (spec drift — severity MEDIUM or HIGH based on impact).
- EARS keyword casing in `requirements.md` is canonical; if the diff introduces user-visible behavior that would require an AC rewrite to describe, flag it.

**Subagent 2 — Test quality**

Context to provide: PR diff, `requirements.md`, acceptance criteria list.

Task:
- Verify tests assert user-visible behavior, not internal implementation details (a test that only asserts on a mock it just configured is HIGH).
- Verify mocks are placed at system boundaries only (external services, databases, filesystems, clocks) — mocking internal collaborators is HIGH.
- Verify test coverage maps to each AC in the slice: every acceptance criterion must have at least one corresponding test.
- Vertical-slice coverage: tests should exercise the full path from the user-visible entry point through to the persistence/response layer where applicable.

**Bugfix extra check (run only when bugfix flow detected):**

The test-quality subagent runs the following additional step after the standard checks above:

1. Identify the slice-1 commit: the slice referenced by slice 2's `depends_on[0]`. Retrieve its branch tip commit hash with `gh pr view <slice-1-pr> --json headRefOid -q .headRefOid` or equivalently from the beads slice metadata.
2. Check out that commit in the current worktree: `git checkout <slice-1-commit>`.
3. Discover the test command via verify-discovery Stage 1 then Stage 2 (check `CLAUDE.md` for `## Specwright — Verify Commands`, then ecosystem defaults).
4. Run the test command. Capture exit code and output.
5. Locate the regression test added in slice 1 by name (from the diff of slice 1's PR).
6. Assert that the regression test was **present** at that commit AND **failed** (non-zero exit, test name appears in failure output).
   - If the regression test passed at slice-1's commit: emit a HIGH finding — `concern: "regression test did not fail pre-fix"`, `file` pointing to the test file, `why` explaining the test passed before the fix was applied, `recommended_fix` telling the developer to confirm the test truly captures the bug condition.
   - If the regression test was absent: emit a HIGH finding — `concern: "regression test missing in slice 1"`.
7. Return to the original ref: `git checkout -`.

**Subagent 3 — Code quality and security**

Context to provide: PR diff, list of languages/frameworks detected from the diff.

Task:
- Check for secret leaks: hardcoded API keys, tokens, passwords, private keys in any diff line not prefixed with `//` comment or similar (CRITICAL if confirmed; use regex patterns `[A-Za-z0-9_]{20,}` adjacent to assignment of key/token/secret/password names).
- OWASP Top-10 issues:
  - A01 Broken Access Control — missing authz check on mutating endpoints (HIGH if exploitable path; MEDIUM otherwise).
  - A02 Cryptographic Failures — plaintext storage, weak hash (MD5/SHA1 for passwords), missing TLS enforcement (CRITICAL for plaintext passwords; HIGH otherwise).
  - A03 Injection — unsanitized user input in SQL, shell, HTML (CRITICAL for SQL injection without parameterization; HIGH for XSS without escaping).
  - A04 Insecure Design — missing rate limiting, missing input validation on critical paths (MEDIUM).
  - A07 Identification and Authentication — weak session handling (HIGH).
  - A09 Security Logging and Monitoring — sensitive data in logs (MEDIUM).
- Code quality:
  - Cyclomatic complexity above project threshold (10 by default if not overridden in `CLAUDE.md`) — MEDIUM.
  - Pattern divergence from surrounding codebase conventions (naming, error-handling style, import style) — MEDIUM.
  - Missing error handling on non-critical paths — MEDIUM.
  - Nits, naming preferences, optional improvements — LOW.

**Subagent 4 — Vertical-slice adherence**

Context to provide: PR diff (file list), `estimated_touched_paths` from slice metadata.

Task:
- List every file in the PR diff.
- Compare against `estimated_touched_paths` globs. Files not matching any glob are out-of-scope candidates.
  - If an out-of-scope file represents a structural architectural change (new module, schema migration, dependency addition) not described in `design.md`, emit MEDIUM.
  - If an out-of-scope file is trivially incidental (config comment, unrelated typo fix in a touched file), emit LOW.
- Estimate PR reviewability: count changed lines. If the PR diff exceeds roughly 300 LOC of substantive changes (excluding generated files, lock files, `TASKS.md`), emit MEDIUM: `concern: "PR size"`, recommending the user consider splitting into smaller slices.
- If the PR is clearly reviewable in under 30 minutes (few files, <150 LOC), emit no finding for this dimension.

### Merge findings

After all four subagents complete, collect their finding lists into a single array. Sort:

1. Severity descending: `CRITICAL` → `HIGH` → `MEDIUM` → `LOW`
2. File path lexicographically ascending
3. Line numerically ascending (for range `"N-M"` sort by N)
4. Concern lexicographically ascending (tiebreaker)

---

## Mode 2 — single-subagent lightweight (tiny flow)

Spawn one subagent with isolated context.

Context to provide: PR diff, the beads slice body (inline spec in the issue description — user story + acceptance criteria + unchanged behavior).

Task — single pass covering all four concerns:
- **Spec alignment:** compare every acceptance criterion from the inline beads spec against the diff. Flag missing ACs (HIGH) and scope creep (MEDIUM or CRITICAL).
- **Test quality:** verify tests assert user-visible behavior, mocks only at boundaries. Flag implementation-detail tests (HIGH). Verify each AC has a corresponding test.
- **Code quality and security:** apply the same OWASP Top-10 and secret-leak checks as Subagent 3 above. Flag complexity, pattern divergence, missing error handling (MEDIUM). Flag nits (LOW).
- **Slice scope:** compare diff file list to slice's `estimated_touched_paths`. Flag out-of-scope structural files (MEDIUM). Flag oversized PR (MEDIUM if >300 LOC substantive change).

Emit findings using the same six-field schema as Mode 1.

---

## Finding schema

Each finding has exactly these six fields:

| Field | Type | Constraints |
| --- | --- | --- |
| `severity` | string | One of `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` (uppercase exact match) |
| `file` | string | Repo-relative POSIX path; no leading `/`, no `..` segments, non-empty |
| `line` | integer or string | Integer >= 1, or range string `"N-M"` where N <= M, both >= 1 |
| `concern` | string | Short tag, max 80 chars, no newlines |
| `why` | string | Free-text explanation, non-empty |
| `recommended_fix` | string | Actionable fix proposal, non-empty |

---

## Tabular report (both modes)

Render all findings as a markdown table with this exact header and separator row:

```markdown
| Severity | Concern | Location | Why | Fix |
| --- | --- | --- | --- | --- |
```

Columns:
- **Severity** — the finding's `severity` enum literal
- **Concern** — the finding's `concern` tag
- **Location** — `<file>:<line>` (e.g. `src/auth/login.ts:42` or `src/auth/login.ts:42-58`)
- **Why** — the finding's `why`; internal newlines collapse to a single space
- **Fix** — the finding's `recommended_fix`; internal newlines collapse to a single space

Pipe characters inside any cell content escape as `\|`.

If findings is empty, emit the table header and separator row with no data rows.

---

## Auto-fix prompt

Immediately after the table, one blank line, then this text verbatim:

```
What next?
[1] auto-fix all CRITICAL
[2] CRITICAL + HIGH
[3] pick individually
[4] file as new beads tasks
[5] skip
```

---

## Dispatch on user reply

Read the user's reply (`1`–`5`) and dispatch as follows:

| Choice | Action |
| --- | --- |
| `1` | Run inline `/specwright:execute` mini-runs for every CRITICAL finding in the same worktree, one at a time, applying the `recommended_fix`. |
| `2` | Run inline `/specwright:execute` mini-runs for every CRITICAL and HIGH finding. |
| `3` | Present the numbered finding list; ask the user to enter finding numbers to fix. Run `/specwright:execute` mini-runs for selected findings. |
| `4` | Create a new beads slice for each finding group (related findings may be batched into one slice). Each slice body contains the finding details and a `depends_on` pointing to the reviewed PR's slice ID. Use `bd create` then `bd dep add <new-id> --blocked-by <reviewed-slice-id>`. |
| `5` | No action. Acknowledge and stop. |

For inline runs (choices 1–3): the mini-run treats `recommended_fix` as its task description, operates in the current worktree on the current branch, then commits and pushes.

---

## Severity rules (reference)

- **CRITICAL** — security vulnerability (exploitable RCE, secret leak, auth bypass), data loss (destructive migration, dropped writes), or scope drift large enough that PRD acceptance fails.
- **HIGH** — missing acceptance criterion in the implementation, a test that does not verify intended behavior (e.g. asserts only on a mock it just configured), or an OWASP Top-10 issue not directly exploitable (validation hole, missing authz check on a non-critical path).
- **MEDIUM** — code-quality concerns, pattern divergence from codebase conventions, complexity above project threshold, missing error handling on non-critical paths.
- **LOW** — nits, naming preferences, optional improvements, doc typos.
