# Stacking Rules — specwright canonical contract

How chained slices become stacked PRs and how `/specwright:resolve-conflict`
handles rebase failures. This document is the authoritative reference;
`/specwright:execute` (sets PR base on creation) and
`/specwright:resolve-conflict` (rebase-fail handler) MUST behave per the
rules here. Drift is a bug.

---

## 1. Branch naming convention

Every slice branch is named:

```
slice/<beads-id>-<kebab-slug>
```

- `<beads-id>` is the slice's beads issue ID verbatim (e.g. `specwright-bi2.6`).
  Dots are allowed because beads IDs contain them.
- `<kebab-slug>` is a lowercase ASCII hyphenated short title.
- Because the beads ID is a prefix of the slug, a branch is identifiable
  from the ID alone: `git branch --list 'slice/<id>-*'`.

Examples:

| beads id            | branch                                   |
| ------------------- | ---------------------------------------- |
| `specwright-bi2.1`  | `slice/specwright-bi2.1-plugin-skeleton` |
| `specwright-bi2.6`  | `slice/specwright-bi2.6-stacking-rules`  |

## 2. PR base-branch resolution

The rules are total — every input combination has exactly one answer:

| condition                                         | base branch                              |
| ------------------------------------------------- | ---------------------------------------- |
| `depends_on == []`                                | `main` (repo default)                    |
| single parent, parent PR open                     | parent's branch                          |
| single parent, parent PR merged                   | `main` (GitHub already retargeted)       |
| single parent, no PR / unknown state              | `main` (defensive)                       |
| `len(depends_on) > 1` (multi-parent)              | apply rules to `depends_on[0]` only      |

### Why `depends_on[0]` for multi-parent slices

`gh pr create --base` takes one branch. When a slice genuinely has more than
one parent, specwright auto-stacks on `depends_on[0]` and treats the remaining
parents as "merge later, not stack." This is the simplest deterministic rule
and matches `slice-schema.md`. If the first-parent default is wrong, the user
can override: `gh pr edit --base <other-branch>`.

### Why merged parent → `main`

Once a parent merges, GitHub auto-retargets open child PRs to the repo
default. specwright agrees with GitHub's view and returns `main` — not the
now-deleted parent branch. See §4.

## 3. Worked examples

| shape                  | graph                              | base for the dependent slice         |
| ---------------------- | ---------------------------------- | ------------------------------------ |
| No deps                | A (standalone)                     | `main`                               |
| Linear chain           | A → B → C (all open)               | B's branch (for C); `main` (for A)   |
| Fork / parallel        | A → B; A → C (siblings, both open) | A's branch (for both B and C)        |
| Post-merge retarget    | A merged → B (open)                | `main` (GitHub retargeted B already) |

## 4. Stacking on PR open

When `/specwright:execute` opens a PR for a slice, it resolves the base
branch per §2, then runs:

```bash
gh pr create --base <parent-slice-branch-or-main> \
             --head slice/<beads-id>-<slug> \
             --title "..." --body "..."
```

The resolved base is always a real branch — never empty.

## 5. Rebase on parent merge

When a parent PR merges, GitHub automatically retargets every open child PR
whose base was the now-merged branch onto the repo default. specwright does
not interfere on the happy path.

If work continues on the child afterward, a normal
`git fetch && git rebase origin/main` brings the local worktree up to date.
If that rebase fails, §6 kicks in.

## 6. Conflict resolution algorithm — `/specwright:resolve-conflict`

When `git rebase` fails on a child slice after the parent merges,
`/specwright:resolve-conflict` makes a **single auto-attempt**:

1. Abort the failed rebase: `git rebase --abort`.
2. Capture two diffs from the pre-conflict state:
   - the child's diff (child branch vs its original base);
   - the merged-parent's diff (merged parent vs `origin/main`).
3. Start a fresh rebase onto the current merged base.
4. For each conflicting hunk, semantically re-apply the child's intent on
   top of the merged base — preferring the child's changes where the
   surrounding code has only moved, escalating to "unresolved" where both
   sides changed the same lines for different reasons.
5. Run the verify command set (cross-ref `verify-discovery.md`).
6. If all verify commands exit 0: `git push --force-with-lease origin <slice-branch>`,
   post a brief PR comment that the rebase was auto-resolved, stop.
7. If any verify command fails OR any hunk remains unresolved:
   `git rebase --abort`, post a failure comment (see §7), stop.

**Single-attempt cap.** `/specwright:resolve-conflict` runs the algorithm
above once per parent-merge event. If it fails, the human takes over.
specwright does not retry, does not loop, does not try a different strategy.

## 7. Failure comment

When auto-resolution fails (step 7 above), `/specwright:resolve-conflict`
posts a comment to the slice's PR containing: the child's pre-conflict diff
and the merged-parent's diff, both annotated with the conflicting hunks;
a one-line note that auto-resolution stopped; and a request for user input
to resolve manually, rebase against `origin/main`, and force-push.
