# specwright — Plan

A platform-agnostic plugin of markdown skills for spec-driven development. Takes the strongest ideas from Kiro (3-phase artifacts), serversia (opinionated scaffolding), and the user's existing workflow (`/grill-me` → PRD → vertical slices → ralph loops), then closes the gaps: parallel execution via worktrees, TDD that tests intent not implementation, auto-verification at task end, severity-graded code review, distinct flows for features / bugfixes / tiny tickets, beads as the default tracker.

See `docs/` for the source notes that informed this plan and `CONTEXT.md` for the shared glossary.

---

## 1. Deliverable & distribution

- **Pure skills bundle.** No CLI, no daemon. Source of truth: `skills/<name>/SKILL.md` files (Markdown + YAML frontmatter `name`, `description`).
- **Two thin manifests on top, same skill files underneath:**
  - Claude Code plugin manifest → published to a Claude Code marketplace (`/plugin install specwright`).
  - Codex `.codex-plugin/plugin.json` + self-hosted `marketplace.json` at the repo root (so users add the repo as a marketplace via `codex /plugins`). Official Codex Directory publishing once it opens.
- **Portable fallback:** the repo is `git clone`-able; users on any other agent copy/symlink `skills/` into wherever their agent loads custom skills.
- **No init skill. No `.specwright/config.json`.** Convention-over-config throughout.

## 2. Skill graph

**Forked + adapted (5)** — copies of the user's existing skills, modified to Kiro style:

| skill | source | adaptation |
| --- | --- | --- |
| `/specwright:grill-me` | `grill-me` | feeds requirements.md |
| `/specwright:grill-with-docs` | `grill-with-docs` | feeds requirements.md, updates `CONTEXT.md` inline |
| `/specwright:tdd` | `tdd` | enforces intent-based tests, vertical-slice scope |
| `/specwright:to-prd` | `to-prd` | produces requirements.md (EARS) + design.md (mermaid) |
| `/specwright:to-issues` | `to-issues` | produces beads slices with `depends_on` + estimated touched paths |

Note: `triage` and `handoff` are explicitly NOT forked.

**New orchestrator skills (10):**

| skill | role |
| --- | --- |
| `/specwright` | umbrella router; 1–2 sizing questions → dispatch |
| `/specwright:feature` | full feature flow (grill → PRD → slice → fanout) |
| `/specwright:bugfix` | bugfix flow (diagnose → bugfix.md → 2-slice split → execute) |
| `/specwright:quick` | one-pass auto-gen with `## Assumptions` + single OK before fanout |
| `/specwright:tiny` | brief grill → 1–2 beads slices → no `.specs/` dir → lightweight review |
| `/specwright:slice` | AC-driven slicer; writes beads with `depends_on` + path metadata |
| `/specwright:fanout` | gtr worktrees + parallel subagent spawn (native primitive, no shell fallback) |
| `/specwright:execute` | per-slice 6-step pipeline |
| `/specwright:review` | 4-subagent fan-out + tabular report + numbered auto-fix prompt |
| `/specwright:resolve-conflict` | single auto-attempt on PR rebase failure, then hand back to user |

## 3. Spec storage & artifacts

Hybrid: PRD on disk, tasks in beads.

```text
.specs/<slug>/
├── requirements.md   # EARS-notation acceptance criteria + user stories
├── design.md         # mermaid diagrams, data flow, error handling, testing strategy
├── bugfix.md         # bugfix flow only: Current / Expected / Unchanged Behavior
└── TASKS.md          # auto-generated mirror of beads slices + depends_on graph
```

- Tasks live canonically in **beads**, queried at runtime.
- `TASKS.md` is regenerated on slice changes — never edited by hand — so the spec PR is fully self-documenting.
- Tiny flow writes **no `.specs/` directory**: spec lives in the beads issue body in a fixed compact format.
- Quick flow: a `## Assumptions` section at the top of `requirements.md` lists every guess the agent made.

## 4. Flows

### Feature (`/specwright:feature`)

1. `/specwright:grill-with-docs` interview → resolves vocabulary, updates `CONTEXT.md`.
2. `/specwright:to-prd` writes `requirements.md` + `design.md`.
3. `/specwright:slice` writes beads slices + `TASKS.md` mirror.
4. `/specwright:fanout` spawns parallel runners in worktrees.
5. Each runner is `/specwright:execute <task-id>` → opens PR (stacked if chained).
6. `/specwright:review` on each PR.

### Bugfix (`/specwright:bugfix`)

1. **Diagnose** — agent reproduces locally before writing anything; bails if it can't.
2. `bugfix.md` with **Current / Expected / Unchanged Behavior** sections (Expected in EARS).
3. **Mandatory 2-slice split:** [1] failing regression test (RED only, no fix); [2] fix + green + Unchanged still green. Slice 2 `depends_on` slice 1 → auto-stacked PRs.
4. Review's test-quality reviewer adds an extra check: did the regression test actually fail before the fix? (Verified by running tests on slice-1's commit.)

### Quick (`/specwright:quick "<prompt>"`)

1. **Single auto-gen pass** — `requirements.md` + `design.md` + beads slices + `TASKS.md` in one shot. No per-phase gates.
2. Every guess goes into `## Assumptions` (dated, phrased "Assumed X because Y").
3. **One human gate** immediately before `/specwright:fanout`. After Y, fans out.
4. If the prompt is too ambiguous (plausible major interpretations conflict), bails to feature flow with reason.

### Tiny (`/specwright:tiny "<short ask>"`)

1. 2–3 question grill (capped variant of `/specwright:grill-me`).
2. Spec body in **one beads issue** — no `.specs/` dir, no on-disk artifacts.
3. Usually 1 slice; 2 if a clear test-first split applies.
4. Same execute pipeline.
5. **Lightweight review** — single reviewer subagent (spec + tests + code combined) instead of 4-way fan-out. Auto-fix prompt still applies.

## 5. Parallelism & fan-out

- **Unit = slice = beads issue.** `depends_on` edges express dependencies; no edges = parallel-ready.
- **Pre-flight conflict avoidance:** `/specwright:slice` records estimated touched paths per slice (best-effort: design.md component map + repo grep). `/specwright:fanout` groups the ready set into non-overlapping cohorts — if two ready slices share any path, they're serialized.
- **Worktrees:** `/specwright:fanout` calls `gtr` to create one worktree per cohort member; trusts the user's `.gtrconfig` for copy rules.
- **Spawn:** native subagent primitive only (Claude Code's `Agent` tool with `isolation: worktree`, Codex equivalent). **No shell-script fallback** — environments without native parallel subagent + worktree get sequential execution.
- **Chains → stacks:** slices with `depends_on` open PRs with `--base <parent-slice-branch>`. GitHub auto-retargets when the parent merges.

## 6. Execute pipeline (per slice)

`/specwright:execute <task-id>` — six steps:

1. **Load context** — beads slice (acceptance criteria, touched paths, dep parent) + `.specs/<slug>/requirements.md` + `design.md`.
2. **Branch** — create feature branch; base = parent slice's branch if stacked, else `main`.
3. **TDD** via forked `/specwright:tdd`: RED (tests written against ACs, framed as user-visible behavior, NOT internal calls) → GREEN → REFACTOR.
4. **Auto-verify loop** — run all detected commands. **N=3 retry cap;** on cap, mark beads slice `blocked` with failure attached, surface to user.
5. **Commit + push** with co-author trailer.
6. **Open PR** — body auto-generated from ACs + link to `.specs/<slug>/`. Mark beads slice `done`.

The skill preamble carries the vertical-slice reminder: if the agent produces changes outside slice scope, it pauses and reports.

### Verify command discovery

At execute time, in order:

1. Read `CLAUDE.md` and `AGENTS.md` for a `## Specwright — Verify Commands` section (if present, use verbatim).
2. Fall back to per-ecosystem defaults:
   - JS/TS: `package.json` scripts named `test` / `lint` / `format` / `typecheck`
   - Python: `pytest`, `ruff check`, `ruff format --check`, `mypy`/`pyright` (from pyproject deps)
   - Rust: `cargo test`, `cargo clippy`, `cargo fmt --check`, `cargo check`
   - Go: `go test ./...`, `go vet ./...`, `gofmt -l .`
   - Terraform: `terraform fmt -check -recursive`, `tflint`
   - `Makefile` / `justfile` targets named the same override.
3. On unresolved miss, ask the user once and **propose a `CLAUDE.md`/`AGENTS.md` edit** to persist the answer.

## 7. Review skill

`/specwright:review <pr|slice>` — 4-subagent fan-out, each isolated context:

| subagent | concern |
| --- | --- |
| Spec alignment | PR diff vs `requirements.md` + `design.md`; drift, missing ACs, scope creep |
| Test quality | intent vs implementation tests, vertical-slice coverage, mocks-at-boundaries-only |
| Code quality + security | codebase patterns, complexity, OWASP top 10, secret leaks |
| Vertical-slice adherence | did the PR stay inside slice scope? PR reviewable in <30 min? |

Each emits `{severity, file:line, concern, why, recommended_fix}`. Main skill merges into a **tabular report** sorted CRITICAL → HIGH → MEDIUM → LOW.

After the table, a numbered prompt:

- [1] auto-fix all CRITICAL
- [2] CRITICAL + HIGH
- [3] pick individually
- [4] file as new beads tasks
- [5] skip

Selected items run inline as `/specwright:execute` mini-runs in the same worktree, OR become follow-up beads slices linked to the original.

## 8. Slicing rules

`/specwright:slice`:

- **Cut rule:** one user-visible acceptance criterion per slice (or a tight cluster that can't be delivered separately).
- **Sizing check:** estimate each slice from design.md component count × rough complexity. If > ~10 files touched or > ~300 LOC est., halt and ask: "AC X looks too big. Split into [proposed sub-slices A, B] or proceed anyway?" — user can always override.
- **Beads metadata per slice:** `{title, acceptance_criteria (verbatim from requirements.md), depends_on, estimated_touched_paths, spec_path}`.

## 9. PR stacking & conflict resolution

- **Stacking:** raw git + `gh pr create --base <parent-slice-branch>`. No dedicated stacking tool dependency.
- **Conflict resolution:** when a sibling PR merges and the next PR in the ready set fails to rebase, `/specwright:resolve-conflict` kicks in automatically: reads both diffs → semantically re-applies the changes → runs tests → on green, commits + force-pushes the PR branch; on red or unresolvable, opens a PR comment with both diffs annotated and notifies the user. **Single auto-attempt cap.**

## 10. Out of scope for v1

- **Alt trackers.** Beads-only. Jira / Linear / GitHub Issues ship later as separate companion plugins that override `/specwright:slice` and `/specwright:fanout`.
- **Shell-script fan-out fallback.** Native subagent + worktree only.
- **Spec-implementation drift validator.** No continuous-validation skill yet; review is the only check.
- **Quick flow no-gate mode.** Single OK before fan-out is mandatory.

## Unresolved questions

1. **Quick flow ambiguity-detection threshold** — what concretely makes a prompt "too ambiguous"? Needs a heuristic the skill can apply.
2. **Tiny flow auto-routing trigger** — how does the umbrella `/specwright` decide a user ask is tiny without asking? Token count? Keywords? Or always ask explicitly?
3. **Conflict-resolution scope** — does the auto-attempt also handle schema migration conflicts, or just code-level? Surface to user on schema by default?
4. **Codex marketplace listing format** — once OpenAI opens the official Plugin Directory, we'll need to register; for now self-hosted `marketplace.json` works. Confirm we ship both the Claude Code manifest and the self-hosted Codex marketplace.json in v1.
5. **Forked skill licensing** — the source skills (grill-me, tdd, to-prd, etc.) live in `~/.claude/skills/` as user-private. When forking into a public marketplace plugin, are they to be re-licensed (MIT?) and attributed back to the user?
6. **Review subagent model selection** — do we hard-code Opus for review and Sonnet for execute, or detect from environment?
7. **Slice-size override prompt** — when the slicer hits the >10 files / >300 LOC heuristic, does it interrupt the AFK flow or proceed with a warning?
