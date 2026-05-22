---
name: specwright-to-issues
description: Break a specwright PRD or bugfix.md into beads slices conforming to slice-schema.md — one AC per slice, with depends_on, estimated_touched_paths, and spec_path. Applies ready-for-agent label. Use when converting a specwright .specs/<slug>/ directory or a tiny-flow beads body into independently-executable beads slices.
---

<!-- Adapted from ~/.claude/skills/to-issues -->

# Specwright To Issues

Break a specwright PRD into beads slices using vertical tracer bullets — one user-visible acceptance criterion per slice.

All slices must conform to `references/slice-schema.md`. Read it before writing anything. EARS casing must match `requirements.md` exactly: `WHEN ... THE SYSTEM SHALL ...` with **UPPERCASE** keywords.

## Process

### 1. Gather context

Work from whatever is in the conversation. If the user passes a `.specs/<slug>/` path or a beads epic ID, read the relevant files:

- `.specs/<slug>/requirements.md` — user stories and EARS acceptance criteria.
- `.specs/<slug>/design.md` — component map and data flow. Use the component map to estimate touched paths.
- `.specs/<slug>/bugfix.md` — if this is a bugfix flow.

For tiny flow: the spec lives in the beads issue body using the compact inline format from `references/spec-format.md`.

### 2. Explore the codebase

If you haven't already, grep the codebase to estimate which files each AC is likely to touch. Use repo-relative globs. This feeds `estimated_touched_paths` — best-effort estimates used by `/specwright:fanout` for cohort grouping, not enforced at execute time.

Use domain vocabulary from `CONTEXT.md` in all issue titles and descriptions.

### 3. Draft vertical slices

Apply the **cut rule** from `references/slice-schema.md`: one user-visible acceptance criterion per slice (or a tight cluster that cannot be delivered separately).

For each slice, draft:

| Field | Value |
| --- | --- |
| `title` | Short descriptive name; single line; used in PR title. |
| `acceptance_criteria` | Verbatim EARS text from `requirements.md`. UPPERCASE keywords. One AC per slice. |
| `depends_on` | Slice IDs that must reach `done` first. Empty = parallel-ready. |
| `estimated_touched_paths` | Repo-relative globs. Best effort from design.md component map + codebase grep. |
| `spec_path` | `.specs/<slug>/` for feature/quick/bugfix flows. `null` for tiny flow. |

**Sizing check:** if a slice estimates above ~10 files or ~300 LOC, halt and ask:

> "AC X looks too big. Split into [proposed sub-slices A, B] or proceed anyway?"

The user can always override.

**Cycle detection:** before writing, verify no slice `depends_on` itself or creates a cycle. If a cycle is detected, halt and surface it to the user.

**Bugfix mandatory split:** bugfix flow always produces exactly 2 slices:
- Slice 1: failing regression test only (RED). `depends_on: []`.
- Slice 2: fix + green + Unchanged still green. `depends_on: [slice-1-id]`.

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**
- **AC** (verbatim EARS)
- **Blocked by** (which other slices, if any)
- **Estimated paths** (top-level globs)

Ask:
- Does the granularity feel right? (too coarse / too fine)
- Are dependency relationships correct?
- Should any slices be merged or split further?

Iterate until the user approves.

### 5. Publish slices to beads

Publish in dependency order (blockers first) so you can reference real IDs in `depends_on`.

For each slice:

```bash
bd create --title "<title>" --body "$(cat <<'EOF'
## Acceptance criterion

<verbatim EARS text from requirements.md>

## Estimated touched paths

- src/foo/**
- src/bar/baz.ts

## Spec

.specs/<slug>/
EOF
)"
```

Then wire dependencies with a separate call per parent:

```bash
bd dep add <new-id> --blocked-by <parent-id>
```

Apply the `ready-for-agent` label to every slice:

```bash
bd label <id> ready-for-agent
```

For **tiny flow** slices, `spec_path` is `null` — omit the `## Spec` subsection in the issue body. The spec lives inline in the epic body per `references/spec-format.md`.

Do NOT close or modify the parent epic.

### 6. Report

After publishing, print a summary table:

| Slice ID | Title | Depends on | Parallel-ready? |
| --- | --- | --- | --- |
| ... | ... | ... | yes / no |

Tell the user to run `/specwright:fanout` to launch parallel runners once the ready set is confirmed.
