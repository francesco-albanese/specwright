---
name: specwright:to-issues
description: Break a specwright PRD into beads vertical slices that conform to slice-schema.md, including dependencies, estimated touched paths, and spec_path metadata.
---

# specwright:to-issues

Break a specwright PRD, bugfix spec, quick spec, or tiny inline spec into independently executable vertical slices. Use beads as the issue tracker.

The output contract is [references/slice-schema.md](../../references/slice-schema.md). When reading PRD artifacts, follow [references/spec-format.md](../../references/spec-format.md).

## Slice Rule

One slice should prove one user-visible acceptance criterion end to end. Cluster ACs only when they cannot be delivered independently.

Each slice must carry:

- `title`
- `acceptance_criteria`
- `depends_on`
- `estimated_touched_paths`
- `spec_path`

## Workflow

1. Read `.specs/<slug>/requirements.md` and `design.md`, or the tiny-flow beads body.
2. Extract EARS acceptance criteria verbatim. Preserve uppercase keywords exactly.
3. Estimate touched paths from the design component map, repo search, and existing file layout.
4. Draft slices with dependencies. Empty `depends_on` means parallel-ready.
5. Run the sizing check: if a slice estimates more than about 10 touched files or 300 LOC, stop and propose sub-slices before creating beads issues.
6. Present the draft breakdown for approval unless the calling flow explicitly runs in approved one-shot mode.
7. Create beads issues in dependency order with `ready-for-agent`.
8. Add dependency edges with `bd dep add` after child issues exist.
9. Regenerate `.specs/<slug>/TASKS.md` as a mirror for non-tiny flows. Do not treat `TASKS.md` as source of truth.

## Beads Body Shape

Use this body shape for each slice:

```markdown
## Parent

<parent epic id>

## What to build

<concise end-to-end behavior>

## Acceptance criterion

- WHEN <trigger> THE SYSTEM SHALL <response>.

## Estimated touched paths

- <repo-relative glob>

## Spec

.specs/<slug>/
```

For tiny flow, omit `## Spec` and put the compact inline spec from `spec-format.md` in the issue body.

## Bugfix Flow

Create exactly two default slices:

1. Regression test only. It must fail before the fix and must not include production changes.
2. Fix plus unchanged-behavior verification. It depends on slice 1.

## Dependency And Base Semantics

Use `depends_on` exactly as described in [references/slice-schema.md](../../references/slice-schema.md):

- No parents: PR base is `main`.
- One parent: PR base is the parent slice branch.
- Multiple parents: PR base is `depends_on[0]`.

Reject self-references and cycles before writing issues.

## Return

Return the created beads IDs, dependency edges, touched-path estimates, and the `TASKS.md` path when written.
