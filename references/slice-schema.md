# slice-schema — beads slice contract

Canonical schema each beads issue produced by `/specwright:slice` must carry so
`/specwright:fanout` can compute the ready set, group cohorts by touched-path
overlap, and resolve PR stacks; and so `/specwright:execute` can hydrate slice
context without scraping markdown.

This file is the **contract between `:slice` (writer) and `:fanout` /
`:execute` (readers)**. Drift here breaks parallelism and stacking. Every change
must keep the fixture validator at `tests/slice_schema_validator.py` green.

---

## 1. Per-slice fields

Every slice carries the same set of required fields. The **tiny-flow
discriminator is `spec_path is null`** — when null, the slice MUST additionally
carry a non-empty `inline_spec` field; otherwise `inline_spec` is forbidden.

| Field                      | Type             | Required          | Semantics                                                                                          |
| -------------------------- | ---------------- | ----------------- | -------------------------------------------------------------------------------------------------- |
| `id`                       | string           | yes               | Beads issue id (e.g. `specwright-bi2.3`). Assigned by `bd create`.                                  |
| `title`                    | string           | yes               | Short descriptive name. Single line; <80 chars. Used in PR title.                                  |
| `acceptance_criteria`      | string           | yes               | Verbatim EARS text lifted from `requirements.md` (or from the inline spec for tiny). One AC per slice — the cut rule. |
| `depends_on`               | list[string]     | yes               | Beads ids that must complete first. Empty list = parallel-ready.                                   |
| `estimated_touched_paths`  | list[string]     | yes               | Best-effort repo-relative globs. Drives cohort grouping in `:fanout`.                              |
| `spec_path`                | string \| null   | yes               | `.specs/<slug>/` pointer; **`null` for tiny flow**.                                                |
| `inline_spec`              | string           | tiny only         | Markdown body of the spec (intent + AC + notes). Required iff `spec_path is null`; forbidden otherwise. |

### Example — feature slice

```json
{
  "id": "checkout-3.2",
  "title": "Apply discount code on checkout",
  "acceptance_criteria": "WHEN the user submits a valid discount code on /checkout THE SYSTEM SHALL recompute the order total and reflect the new line in the summary.",
  "depends_on": ["checkout-3.1"],
  "estimated_touched_paths": [
    "src/checkout/DiscountField.tsx",
    "src/checkout/discount_service.ts"
  ],
  "spec_path": ".specs/checkout-redesign/"
}
```

### Example — tiny slice

```json
{
  "id": "docs-typo-19",
  "title": "Fix typo in README install snippet",
  "acceptance_criteria": "WHEN a user copies the install command from README.md THE SYSTEM SHALL paste a syntactically correct command.",
  "depends_on": [],
  "estimated_touched_paths": ["README.md"],
  "spec_path": null,
  "inline_spec": "## Intent\nFix README typo blocking new-user onboarding.\n\n## AC\nWHEN a user copies the install command from README.md THE SYSTEM SHALL paste a syntactically correct command.\n\n## Notes\nNo .specs/ dir; this slice is the whole spec."
}
```

## 2. Flow variants

The schema itself only distinguishes **tiny** (no `.specs/` dir) from
**non-tiny** (PRD on disk). The other three entry flows — `feature`, `bugfix`,
`quick` — share an identical slice shape: they differ only in how the upstream
PRD is authored and reviewed, not in the slice contract.

| Flow      | `spec_path`            | `inline_spec`   | Notes                                                                                       |
| --------- | ---------------------- | --------------- | ------------------------------------------------------------------------------------------- |
| `feature` | `.specs/<slug>/`       | forbidden       | Full PRD on disk; slices are AC fan-out children.                                            |
| `bugfix`  | `.specs/<slug>/`       | forbidden       | Same disk shape. Mandatory 2-slice split: regression-test slice → fix slice (`depends_on`).  |
| `quick`   | `.specs/<slug>/`       | forbidden       | One-pass auto-gen; `requirements.md` carries an `## Assumptions` section. Same slice shape. |
| `tiny`    | `null`                 | **required**    | No `.specs/<slug>/` dir. Whole spec lives in `inline_spec`. Single beads issue per slice.   |

The validator enforces the discriminator as a hard rule:
**`spec_path is null` ↔ `inline_spec` is a non-empty string**. Every non-tiny
flow MUST have `spec_path` matching the regex `^\.specs/[^/]+/$`.

## 3. Glob rules (`estimated_touched_paths`)

Globs are best-effort; `:fanout` uses them only to deduplicate cohort members
by path overlap, not to enforce diff scope at execute time. Required form:

- Non-empty string.
- **Repo-relative.** No leading `/`.
- No `..` path segments (prevents escapes during glob expansion).
- Characters limited to `[A-Za-z0-9_./*?\[\]\-{},!]` — i.e. printable
  POSIX-friendly path characters plus shell glob metacharacters.
- Parseable by Python's stdlib `fnmatch.translate` (the validator calls it).

Cohort grouping in `:fanout` calls `fnmatch.fnmatch` between every pair of
ready slices' globs; any overlap pushes the second slice to the next cohort.

## 4. `depends_on` semantics

- A slice may be claimed by `:fanout` only when **all** ids in its `depends_on`
  list are in beads status `done`.
- Self-references are forbidden (`id` must not appear in its own `depends_on`).
- Cycles across the slice set are forbidden. The validator runs a 3-colour DFS
  and reports the first cycle it finds.
- Unknown ids (referencing a slice not in the current corpus) are reported as
  errors during corpus-level validation. At runtime, `:fanout` treats an
  unknown parent as a hard block and surfaces it to the user.
- `:execute` reads `depends_on` to set the PR base branch when stacking: the
  PR is opened with `--base <parent-slice-branch>` when the slice has exactly
  one parent; multi-parent slices are rare and reviewed by the user.

## 5. Beads metadata mapping

The schema is persisted in beads as follows. `bd create` carries the freeform
fields inside the issue description; cross-slice edges are wired with `bd dep
add` immediately after the slice's id is returned.

```bash
# 1. Create the slice. The new id (e.g. ${SLICE_ID}=checkout-3.2) is returned.
bd create \
  --title "Apply discount code on checkout" \
  --type task \
  --priority 2 \
  --description "$(cat <<'EOF'
## Acceptance criterion

WHEN the user submits a valid discount code on /checkout THE SYSTEM SHALL recompute the order total and reflect the new line in the summary.

## Estimated touched paths

- src/checkout/DiscountField.tsx
- src/checkout/discount_service.ts

## Spec

.specs/checkout-redesign/
EOF
)"

# 2. Wire every parent in `depends_on` as a beads dependency edge.
#    `--blocked-by` is the edge type read by `bd ready` to compute the ready set.
bd dep add ${SLICE_ID} --blocked-by checkout-3.1
```

Translation rules:

| Schema field              | Beads expression                                               |
| ------------------------- | -------------------------------------------------------------- |
| `id`                      | The issue id returned by `bd create` (not set by `:slice`).    |
| `title`                   | `bd create --title <...>`                                      |
| `acceptance_criteria`     | `## Acceptance criterion` subsection of the description body.   |
| `depends_on` (each entry) | One `bd dep add <new-id> --blocked-by <parent-id>` call.       |
| `estimated_touched_paths` | `## Estimated touched paths` markdown list in the description. |
| `spec_path`               | `## Spec` subsection of the description body.                  |
| `inline_spec` (tiny only) | The full description body; the standard subsections above are replaced by the inline-spec format in §5.1. |

### 5.1 Tiny-flow inline-spec format

For `spec_path == null` (tiny flow), **no** `.specs/<slug>/` directory is
created. The full spec body lives inline in the beads issue description using
this fixed markdown layout:

```markdown
## Intent
<one-paragraph why; what user pain this resolves>

## AC
WHEN <trigger> THE SYSTEM SHALL <observable response>

## Notes
<optional design constraints, links to prior art, expected touched files>
```

The validator's tiny rule mirrors this:

- `spec_path` MUST be JSON `null`.
- `inline_spec` MUST be a non-empty string that the human reviewer can read
  end-to-end inside the beads issue body.
- `inline_spec` is forbidden when `spec_path` is set (it would create two
  competing sources of truth).

`:execute` loads tiny slices purely from beads — no disk read for the spec.
`:review` runs the lightweight single-reviewer path for tiny slices (see
`review-format.md`).

## 6. Validator

The fixture validator at `tests/slice_schema_validator.py` enforces every rule
above. It is stdlib-only (re, json, sys, argparse, fnmatch, pathlib) and runs
two ways:

```bash
python tests/slice_schema_validator.py        # CLI: walks fixtures, exits 1 on mismatch
python -m pytest tests/slice_schema_validator.py -v   # pytest discovery
```

Fixtures live under `tests/fixtures/slice-schema/`:

- `positive/` — at minimum one per flow variant (feature, bugfix, quick,
  tiny). Each MUST validate clean.
- `negative/` — at minimum one each for: missing required field, bad glob,
  self-referential `depends_on`, multi-slice cycle. Each MUST raise at least
  one error.

The CLI fails if either directory contains fewer than four fixtures, so the
floor is mechanically enforced.

## 7. Change-management rule

Adding or removing a required field MUST be accompanied by:

1. An update to the table in §1.
2. New positive fixtures exercising the field where relevant.
3. New negative fixtures asserting the rejection rule.
4. A green validator run under both invocation modes.

If the new field changes the beads-metadata mapping (§5), update that section
in the same PR so writers and readers cannot drift.
