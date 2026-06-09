---
name: write-tasks
description: Writes beads tasks splitting into epics, tickets with dependencies between tasks. Use when the user asks to write tasks for implementation, or when the spec has been recently reviewed and is ready for implementation.
context: fork
allowed-tools: Agent(Explore), Bash, Read, Grep, Write, Edit, Glob, AskUserQuestion, TodoWrite
argument-hint: "[beads-id]"
---

# Write tasks

Break a plan into independently-grabbable issues using vertical slices.

When a named tool is unavailable, use the closest native capability: read/search files directly, ask the user in chat, or edit files with the runtime's normal file-editing tools.

## Process

### 1. Gather context

The user should have produced a comprehensive software specification. This might already be in your
context window. If not, look for the most recent spec in
`/docs/specs/{spec-name}/spec.md`.
If the user passes a beads id as an argument, fetch it from beads and read its full body and comments.

### 2. Draft vertical slices

Break the spec down into thin vertical slices, that cuts through all integration layers end-to-end, NOT a
horizontal slice of only one layer.

Each slice is independently testable and deployable and delivers a narrow but COMPLETE path through every
layer (schema, API, UI, tests). A complete slice is demoable or verifiable on its own. ALWAYS prefer many
thin slices over few thick ones.

### 3. Quiz the user

Present the proposed breakdown as a numbered list. For each slice show:

- **Title**: short descriptive name
- **Description**: short description of what the slice covers
- **Dependencies**: which other slices (if any) must be completed first
- **Acceptance criteria**: which user stories this addresses

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?

### 4. Write to beads

For each approved slice, create a beads task using the template below. Publish tasks in dependency order
(blockers first) so you can reference real task identifiers in in the "Dependencies" field.

<issue-template>

# Parent

A reference to the parent issue on the issue tracker (if the source was an existing issue, otherwise omit
this section).

## What to build

A concise description of this vertical slice. Describe the end-to-end behavior, not layer-by-layer
implementation.

Avoid specific file paths or code snippets because they go stale fast. Trim to the decision-rich parts,
not a working demo, just the important bits.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Dependencies

- A reference to the blocking ticket (if any)

Or "None - can start immediately" if no blockers.

</issue-template>

Do NOT close or modify any parent issue.

## Next steps

Suggest to the user to move to the next phase of implementing the tasks, with
`/specwright:execute` in Claude Code or `$specwright:execute` in Codex.
