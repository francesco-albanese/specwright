# slice-schema — beads slice contract

Canonical schema for every beads issue produced by `/specwright:slice`.

**Writer:** `/specwright:slice`
**Readers:** `/specwright:fanout` (cohort grouping via touched-path overlap); `/specwright:execute` (PR base resolution for stacking)

Drift here breaks parallelism and stacking.

---

## Fields

Every slice carries five required fields.

| Field                     | Type           | Semantics                                                                                                    |
| ------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------ |
| `title`                   | string         | Short descriptive name; single line, used in PR title.                                                       |
| `acceptance_criteria`     | string         | Verbatim EARS text lifted from `requirements.md`. One AC per slice (the cut rule). UPPERCASE — `WHEN ... THE SYSTEM SHALL ...`. |
| `depends_on`              | list[id]       | Slice IDs that must reach `done` before this slice enters the ready set. Empty = parallel-ready.             |
| `estimated_touched_paths` | list[glob]     | Best-effort repo-relative globs. Used by `:fanout` for cohort grouping only; not enforced at execute time.   |
| `spec_path`               | string \| null | `.specs/<slug>/` directory pointer. `null` for tiny flow — spec body lives inline in the beads issue body.  |

EARS casing must match `requirements.md` exactly. Lowercase AC text is incorrect.

---

## Flow variants

Feature and quick slices are structurally identical. Bugfix adds a mandatory 2-slice split. Tiny drops the on-disk spec.

| Flow      | `spec_path`       | Notes                                                                                                    |
| --------- | ----------------- | -------------------------------------------------------------------------------------------------------- |
| `feature` | `.specs/<slug>/`  | Full PRD on disk; slices are AC fan-out children.                                                        |
| `quick`   | `.specs/<slug>/`  | One-pass auto-gen; `requirements.md` carries an `## Assumptions` section. Same slice shape as feature.  |
| `bugfix`  | `.specs/<slug>/`  | Mandatory 2-slice split: slice 1 = failing regression test only (RED); slice 2 = fix, depends_on slice 1. Slice 2's PR auto-stacks on slice 1. |
| `tiny`    | `null`            | No `.specs/<slug>/` dir. Spec body lives inline in the beads issue description. See [Tiny-flow body](#tiny-flow-body). |

---

## Beads mapping

`:slice` persists each field in beads as follows. Post-creation dependency edges are wired with a separate `bd dep add` call.

| Schema field              | Beads expression                                                         |
| ------------------------- | ------------------------------------------------------------------------ |
| `title`                   | `bd create --title`                                                      |
| `acceptance_criteria`     | `## Acceptance criterion` subsection in the issue description body       |
| `depends_on` (each entry) | `bd dep add <new-id> --blocked-by <parent-id>` (one call per parent)     |
| `estimated_touched_paths` | `## Estimated touched paths` markdown list in the issue description body |
| `spec_path`               | `## Spec` subsection in the issue description body; omitted when null    |

The full `bd create` / `bd dep add` invocation sequence is the responsibility of the `/specwright:slice` SKILL.md, not documented here.

---

## depends_on and PR base

`:fanout` computes the ready set by querying slices whose entire `depends_on` list is in `done` status.

`:execute` uses `depends_on` to set the PR base branch for stacking:

- `len(depends_on) == 0` — PR base is `main`.
- `len(depends_on) == 1` — PR base is the parent slice's branch (`gh pr create --base <parent-slice-branch>`).
- `len(depends_on) > 1` — PR base is `depends_on[0]` (the first declared parent). Rationale: chains are almost always linear; multi-parent slices are rare edge cases. When the auto-pick is wrong, the user overrides at PR-open time. This rule is canonical; see also `stacking-rules.md`.

Self-references and cycles across the slice set are forbidden; `:slice` is responsible for detecting these before writing.

---

## Touched paths

Globs must be:

- Repo-relative (no leading `/`, no `..` segments).
- Non-empty strings containing only path characters and shell glob metacharacters.

`:fanout` checks path overlap between every pair of ready slices. Any overlap serializes the later slice into the next cohort. Touched paths are estimates — they do not constrain what `:execute` actually modifies.

---

## Tiny-flow body

When `spec_path` is `null`, the entire spec lives in the beads issue description using the compact inline format defined in `spec-format.md` (tiny-flow section). `:execute` loads tiny slices purely from beads — no on-disk spec read. `:review` runs the lightweight single-reviewer path for tiny slices; see `review-format.md`.

---

## Examples

### Feature slice

```
title:                  "Apply discount code on checkout"
acceptance_criteria:    "WHEN the user submits a valid discount code on /checkout
                         THE SYSTEM SHALL recompute the order total and display
                         the updated summary."
depends_on:             [<parent-slice-id>]
estimated_touched_paths: ["src/checkout/DiscountField.tsx",
                          "src/checkout/discount_service.ts"]
spec_path:              ".specs/checkout-redesign/"
```

### Tiny slice

```
title:                  "Fix typo in README install snippet"
acceptance_criteria:    "WHEN a user copies the install command from README.md
                         THE SYSTEM SHALL produce a syntactically correct command."
depends_on:             []
estimated_touched_paths: ["README.md"]
spec_path:              null
```

Beads issue body for the tiny slice follows the inline format from `spec-format.md`.
