# specwright — Glossary

Shared vocabulary for the specwright project. Capture terms here as they're resolved during planning and implementation. No implementation details — this is a glossary, not a spec.

---

**Acceptance criterion (AC)**
A single user-visible behavioral guarantee expressed in EARS notation (`WHEN <trigger> THE SYSTEM SHALL <response>`). The unit of `/specwright:slice`'s cut rule: one AC = one slice (unless tightly clustered).

**Assumption** (quick flow)
A guess the `/specwright:quick` skill made when auto-generating artifacts from a short prompt. Every assumption is recorded in the `## Assumptions` section at the top of `requirements.md`, dated, phrased "Assumed X because Y." The user reviews the assumption list at the single OK gate before fan-out.

**Auto-verify loop**
The post-implementation check phase inside `/specwright:execute` (step 4). Runs detected test / lint / format / typecheck / build commands. On failure, the agent reads the output and fixes; capped at N=3 retries. On cap, the slice is marked `blocked` in beads and surfaced to the user.

**Beads**
The default issue tracker for specwright. Source of truth for tasks. PRD lives on disk in `.specs/<slug>/`; slice lifecycle (ready / in-progress / done / blocked) lives in beads. Alternative trackers are out of scope for v1.

**Chain**
A linear sequence of slices connected by `depends_on` edges. Chains never fan out in parallel — they become stacked PRs (each PR's base branch is the parent slice's branch).

**Cohort**
The subset of the **ready set** that `/specwright:fanout` actually launches together — picked so no two members share any estimated touched path. Overlapping ready slices are deferred to subsequent cohorts.

**`depends_on`**
Beads metadata field on a slice listing slice IDs that must complete first. The fan-out skill reads this graph to compute the ready set; the execute skill reads it to set the PR base branch for stacking.

**EARS**
Easy Approach to Requirements Syntax. Structured AC notation specwright requires in `requirements.md`. Pattern: `WHEN <trigger> THE SYSTEM SHALL <observable response>`. Variants exist for state-driven, optional, and ubiquitous requirements.

**Epic**
A PRD's top-level beads issue. Slices are its children. Equivalent to a Kiro "feature spec." Bugfix flow has an epic too (one per bugfix.md).

**Execute pipeline**
The six-step per-slice flow `/specwright:execute <task-id>` runs inside a worktree: load context → branch → TDD → auto-verify → commit/push → open PR.

**Fan-out**
The act of launching multiple parallel runners — one per cohort member. Done by `/specwright:fanout` using `gtr` for worktrees and the host agent's native subagent primitive.

**Flow**
One of the four entry-point shapes: **feature** (full PRD), **bugfix** (diagnose + bugfix.md + 2-slice split), **quick** (one-pass auto-gen + assumptions + single OK), **tiny** (no PRD, brief grill, beads-only).

**`gtr`**
The git-worktree-runner CLI ([coderabbitai/git-worktree-runner](https://github.com/coderabbitai/git-worktree-runner)). specwright calls it to create worktrees but does not manage its configuration — trust the user's `.gtrconfig`.

**Mirror** (a.k.a. TASKS.md mirror)
The auto-generated `.specs/<slug>/TASKS.md` file. A snapshot view of the beads slices for human PR review. Regenerated on slice changes. Never edited by hand. Not a source of truth — beads is.

**PRD**
Product Requirements Document. In specwright: `requirements.md` + `design.md` (+ `bugfix.md` for bugfix flow) on disk in `.specs/<slug>/`. Reviewable as code, travels with the branch.

**Quick flow**
Kiro-style auto-generation path. `/specwright:quick "<prompt>"` produces all PRD artifacts in one pass, surfaces every assumption, requires a single user OK before fanout.

**Ready set**
The current set of slices in beads with all `depends_on` parents marked done. The fan-out skill picks cohorts from this set.

**Reviewer subagent**
One of four specialized review subagents fanned out by `/specwright:review`: spec-alignment, test-quality, code-quality + security, vertical-slice adherence. Each runs in isolated context and emits findings tagged with a severity bucket.

**Runner**
A subagent spawned by `/specwright:fanout` inside a worktree to execute one slice. Invokes `/specwright:execute <task-id>`. Returns to the parent on PR open or block.

**Severity bucket**
One of CRITICAL / HIGH / MEDIUM / LOW. Assigned per review finding. The auto-fix prompt offers to jump into CRITICAL and HIGH; MEDIUM and LOW are reported only.

**Slice (vertical slice)**
A complete piece of functionality cutting through every layer (UI → service → data). Independently deliverable, user-testable, reviewable in <30 min. The unit of parallelism, the unit of a single PR, the unit of one beads issue. Distinct from a "task" in the Kiro sense — slices always deliver user-visible value.

**Sizing check**
Heuristic in `/specwright:slice` that halts and prompts the user if a slice estimates above ~10 touched files or ~300 LOC. User can override or accept proposed sub-splits.

**Stacked PR**
A PR whose base branch is another open PR's branch (set via `gh pr create --base <parent-slice-branch>`). Used for chains. GitHub auto-retargets dependent PRs when the parent merges.

**Tiny flow**
The smallest path. `/specwright:tiny "<short ask>"` — 2-3 question grill, 1-2 slices in a single beads issue body, no `.specs/` directory, lightweight single-reviewer review. Auto-routed by the umbrella `/specwright` when the ask is obviously small.

**Touched paths**
Best-effort glob list per slice in beads metadata. Estimated by `/specwright:slice` from the design.md component map plus repo grep. Used by `/specwright:fanout` for cohort grouping — not enforced at execute time.

**Umbrella router** (`/specwright`)
The entry skill with no arguments. Asks 1-2 sizing questions and dispatches to one of the four flow skills. Not a state machine; one-shot routing only.

**Worktree**
A git working tree created by `gtr` for isolated parallel execution. One per runner. Cleaned up on PR open or on user-initiated cleanup.
