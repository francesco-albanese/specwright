# ADR 0001: Hybrid spec storage — PRD on disk, tasks in beads

- **Status:** Accepted
- **Date:** 2026-05-21

## Context

specwright produces two kinds of structured output per piece of work:

1. **The reviewable spec** — `requirements.md` (EARS-notation acceptance criteria), `design.md` (architecture + mermaid diagrams), or `bugfix.md` (Current / Expected / Unchanged Behavior). These are human-reviewed artifacts that should travel with the branch implementing them, and they should be diff-able as part of a code review.
2. **The trackable task list** — one beads issue per vertical slice, with `depends_on` edges expressing dependencies. Slice lifecycle (ready / in-progress / done / blocked) is the primary signal the fan-out skill reads to decide what to launch in parallel. This must be queryable, mutable, and shared across worktrees / parallel runners.

These two outputs pull in different directions:

- A reviewable spec wants to live next to the code in git so reviewers see "the spec changed because the implementation changed" in the same PR.
- A trackable task list wants to live in a structured datastore (beads) with cheap queries ("which slices are ready?"), atomic state updates, and a dependency graph that doesn't have to be reparsed from markdown.

We considered three approaches.

## Decision

**Hybrid:** the PRD lives on disk in `.specs/<slug>/`. Tasks live in beads. A `.specs/<slug>/TASKS.md` mirror is auto-generated as a snapshot view of the beads slices so the PR introducing the spec is fully self-documenting.

```text
.specs/<slug>/
├── requirements.md   # EARS-notation acceptance criteria + user stories
├── design.md         # mermaid diagrams, data flow, error handling, testing strategy
├── bugfix.md         # bugfix flow only
└── TASKS.md          # auto-generated mirror; never edited by hand
```

The tiny flow is an exception: it writes no `.specs/<slug>/` directory and stores the entire spec in a single beads issue body. The PRD overhead isn't worth it for 1-2-slice work.

## Alternatives considered

### Everything in beads

PRD content lives in the epic issue body; design lives in a child issue; slices are grandchildren.

**Rejected because:** the spec stops being PR-reviewable. A reviewer can't see "this PR changed the spec from X to Y" as a diff in the same review — they have to navigate to beads and compare versions there. It also makes the spec invisible to anyone reading the repo without beads installed.

### Everything on disk, beads optional

Full Kiro: `requirements.md` + `design.md` + `tasks.md` all on disk. Beads (or any tracker) becomes a thin pointer at most.

**Rejected because:** beads' ready-set query and `depends_on` graph are first-class to specwright's parallelism model. Pushing tasks onto disk means re-implementing dependency resolution in markdown, which loses the "must use beads as issue tracker" must-have and the cheap atomic state updates the fan-out skill depends on.

## Consequences

**Positive:**

- Spec changes are reviewable in the same PR as the code change that motivates them.
- Beads' dependency graph drives parallelism cleanly; no markdown parsing for ready-set queries.
- `TASKS.md` mirror keeps PRs self-documenting without making the markdown a source of truth.
- The tiny flow stays lightweight (no `.specs/` overhead for 1-2-slice work).

**Negative:**

- Two storage backends to keep in sync. The mirror file is the synchronisation point — it must regenerate atomically when slices change, and edits to it by hand are silently overwritten. Tooling around the mirror generation needs to be robust.
- Alternative trackers (jira, linear, github-issues) are harder to support because the slice metadata schema is beads-shaped. Acknowledged: v1 ships beads-only; alternatives ship later as companion plugins.
- Path discipline: the `.specs/<slug>/` slug must match the beads epic ID; we rely on convention and the orchestrator skills enforcing it. There's no schema-level guarantee.

**Reversibility:** moderate. Switching to "everything in beads" later means moving PRD content into issue bodies (mechanical migration). Switching to "everything on disk" means re-implementing the dependency graph in markdown (harder, but tractable). Either reversal would require a migration step but is not a one-way door.
