# Stacking Rules — specwright canonical contract

How chained slices become stacked PRs, and how `/specwright:resolve-conflict`
handles rebase failures. This document is the authoritative reference; the
implementation skills (`/specwright:execute`, `/specwright:resolve-conflict`)
MUST behave per the rules here. Drift is a bug.

The companion validator (`tests/stacking_rules_validator.py`) encodes the
PR base-branch resolution rules as a pure function and asserts them against
the fixtures in `tests/fixtures/stacking-rules/`.

---

## 1. Branch naming convention

Every slice branch is named:

```
slice/<beads-id>-<kebab-slug>
```

Validating regex (also enforced by the validator on every fixture):

```
^slice/[a-z0-9][a-z0-9.\-]*-[a-z0-9][a-z0-9\-]*$
```

- `<beads-id>` is the slice's beads issue ID verbatim (e.g. `specwright-bi2.6`).
  Dots are allowed because beads IDs include them (e.g. `bi2.6`).
- `<kebab-slug>` is a lowercase ASCII hyphenated short title.
- The beads ID is a prefix of the slug portion so a branch is identifiable
  from the beads ID alone with `git branch --list 'slice/<id>-*'`.

Examples:

| beads id           | branch                                          |
| ------------------ | ----------------------------------------------- |
| `specwright-bi2.1` | `slice/specwright-bi2.1-plugin-skeleton`        |
| `specwright-bi2.6` | `slice/specwright-bi2.6-stacking-rules`         |
| `specwright-bi2.12`| `slice/specwright-bi2.12-resolve-conflict-skill`|

## 2. PR base-branch resolution

The contract is a pure function:

```python
def expected_base(
    slice_id: str,
    slices: list[dict],         # the beads dep graph
    pr_state: dict[str, str],   # slice_id -> "open" | "merged"
) -> str:                       # branch name
```

The rules are **total** — every input combination has exactly one answer:

| input condition                                           | base branch                  |
| --------------------------------------------------------- | ---------------------------- |
| `depends_on == []`                                        | `main` (repo default)        |
| first parent's PR state is `open`                         | parent's branch              |
| first parent's PR state is `merged`                       | `main`                       |
| first parent has no PR / unknown state                    | `main` (defensive)           |
| `len(depends_on) > 1` (multi-parent fork)                 | apply rules to `depends_on[0]` only |

### Why "first parent only" for multi-parent slices

In practice almost every chain is linear. When a slice genuinely has more
than one parent, stacking against more than one branch is impossible —
`gh pr create --base` takes one branch. specwright stacks on
`depends_on[0]` and treats the remaining parents as "merge later, not
stack." This is the simplest deterministic rule and lets users reorder
`depends_on` if they want a different stack root.

### Why "merged parent → main"

Once a parent merges, GitHub auto-retargets the open child PR to the
repo default. specwright must agree with GitHub's view, so the rule
returns `main` (not the now-merged-away parent branch). See §4.

### Worked examples (rendered from the fixtures)

**No deps** (`tests/fixtures/stacking-rules/no-deps.json`):

```
specwright-bi2.1 (no parent)        → main
```

**Linear chain** (`tests/fixtures/stacking-rules/linear-chain.json`):

```
specwright-bi2.1 (no parent)        → main
specwright-bi2.2 depends_on bi2.1   → slice/specwright-bi2.1-plugin-skeleton
specwright-bi2.3 depends_on bi2.2   → slice/specwright-bi2.2-grill-skill

(bi2.1 PR open, bi2.2 PR open)
```

**Fork / multi-parent** (`tests/fixtures/stacking-rules/fork-multi-parent.json`):

```
specwright-bi2.1 (no parent)                       → main
specwright-bi2.2 (no parent)                       → main
specwright-bi2.7 depends_on [bi2.1, bi2.2]         → slice/specwright-bi2.1-plugin-skeleton

(bi2.1 PR open, bi2.2 PR merged — first-parent-only rule applies regardless of which parent's state is more recent)
```

**Post-merge retarget** (`tests/fixtures/stacking-rules/post-merge-retarget.json`):

```
specwright-bi2.1 (no parent)        → main      (merged)
specwright-bi2.2 depends_on bi2.1   → main      (parent merged; GitHub retargeted)
specwright-bi2.3 depends_on bi2.2   → slice/specwright-bi2.2-grill-skill   (direct parent still open)
```

## 3. Stacking on PR open

When `/specwright:execute` opens a PR for a slice:

```bash
gh pr create --base "$(specwright_expected_base "$SLICE_ID")" \
             --head "slice/<beads-id>-<slug>" \
             --title "..." --body "..."
```

`specwright_expected_base` is the pure function in §2, called with the
beads dep graph and the current PR state queried from `gh pr list`.

The function NEVER returns an empty string — every call yields a real
branch (`main` or a slice branch).

## 4. Rebase semantics on parent merge

specwright does not interfere with GitHub's auto-retarget. When a parent
PR merges, GitHub automatically retargets every open child PR whose
base was the now-merged parent branch onto the repo default. The child
PR's state in `pr_state` after this is still `open`; only the parent's
state flips to `merged`. The validator reflects this in the post-merge
fixture.

specwright's only job after a parent merge is to update the local
worktree if work continues on the child (a normal `git fetch && git
rebase origin/main`). If that rebase fails, §5 kicks in.

## 5. Conflict resolution algorithm — `/specwright:resolve-conflict`

When `git rebase` fails on a child slice (typically because a sibling
that touched overlapping paths merged first), `/specwright:resolve-conflict`
runs a **single auto-attempt** to recover. Pseudocode:

```
1. abort the failed rebase (`git rebase --abort`)
2. capture two diffs:
     - original_diff = git diff <slice-branch-base>..<slice-branch>
     - merged_base_diff = git diff origin/main..<merged-parent-branch>
   ...as recorded immediately before the conflict surfaced.
3. start a fresh rebase onto the current merged base.
4. for each conflicting hunk:
     re-apply the intent of `original_diff` semantically on top of the
     merged base — preferring the slice's intent where the surrounding
     code has merely moved, escalating to "unresolved" where both sides
     changed the same lines for different reasons.
5. run the project's verify commands (test / lint / typecheck per
    `/specwright:execute`'s discovery rules).
6. if all verify commands return 0:
     git push --force-with-lease origin <slice-branch>
     post a PR comment "rebase auto-resolved by /specwright:resolve-conflict"
     stop.
7. otherwise (any verify command fails OR step 4 marked any hunk
    unresolved):
     git rebase --abort   (discard the attempted resolution)
     post the failure comment per §6
     stop.
```

**Single-attempt cap.** `/specwright:resolve-conflict` runs the
algorithm above **once** per parent-merge event. If it fails, the
human must take over — specwright does not retry, does not "try a
different strategy," does not loop. The skill exits and surfaces to
the user.

## 6. Failure comment format

When auto-resolution fails (step 7 above), `/specwright:resolve-conflict`
posts the following comment to the slice's PR. The format is a literal
template; `/specwright:resolve-conflict` (issue specwright-bi2.12) MUST
emit exactly this shape so downstream tooling (humans, dashboards,
future skills) can rely on it.

````markdown
## specwright: rebase auto-resolution failed

`/specwright:resolve-conflict` attempted a single auto-rebase after
`<parent-slice-id>` merged. The attempt did not converge. Human action
required.

### Original slice diff (before conflict)

```diff
<diff -- slice branch vs its original base, truncated to first 200 lines>
```

### Merged-base diff (what changed on `main`)

```diff
<diff -- merged parent vs origin/main at the time, truncated to first 200 lines>
```

### Verify command output (excerpt)

```
<stderr/stdout of the first failing verify command, last 80 lines>
```

### Unresolved hunks

- `<path/to/file>:<line>` — `<one-line reason>`
- ... (one bullet per hunk marked unresolved at step 4)

### Human action required

1. Pull the slice branch locally.
2. Rebase manually against `origin/main`.
3. Re-run the project's verify commands.
4. Push and remove the `auto-resolve-failed` label to re-enable
   future automation on this PR.

— specwright (single-attempt cap reached; no further auto-retries)
````

The comment uses these stable section headings (case- and
order-sensitive) so future tooling can parse them:

- `## specwright: rebase auto-resolution failed`
- `### Original slice diff (before conflict)`
- `### Merged-base diff (what changed on \`main\`)`
- `### Verify command output (excerpt)`
- `### Unresolved hunks`
- `### Human action required`

The PR is also labelled `auto-resolve-failed` so it can be filtered
out of any future auto-resolution sweeps until a human clears the
label.

## 7. Validator

`tests/stacking_rules_validator.py` is the executable contract for §2.
It exposes:

```python
expected_base(slice_id, slices, pr_state) -> str
```

…and asserts the rule against every JSON fixture in
`tests/fixtures/stacking-rules/`. New rule changes MUST be accompanied
by a fixture change in the same PR.

Run it two ways:

```bash
python tests/stacking_rules_validator.py        # standalone runner
python -m pytest tests/stacking_rules_validator.py -v
```

Both invocations exercise the same assertions against the same fixtures,
so the validator stays runnable whether or not pytest is installed.
