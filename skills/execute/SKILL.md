---
name: execute
description: Instructs an agent to execute the tasks defined in beads, enforcing test driven development and tight feedback loops. Use this skill when the user asks to execute the tasks defined in beads, or when the tasks have been recently written.
context: fork
model: sonnet
allowed-tools: Agent(Explore), Bash, Read, Grep, Write, Edit, Glob, TodoWrite
argument-hint: "[beads-id]"
---

# Execute

Implement the code required to satisfy the tasks defined in beads ticket.

When a named tool is unavailable, use the closest native capability: read/search files directly, ask the user in chat, or edit files with the runtime's normal file-editing tools.

If the user provides a beads id as an argument, fetch the task from beads and read its full body to
gather context, the task should contain a link to the relevant spec that contains the full requirements
for implementation.

## Process

### Find ready tasks and epic

1. Find a task if not provided by the user. `bd ready --type task --limit 20`. If the list is empty check for an active epic and confirm completion. If this is also empty close the epic and stop.
2. Find the beads epic by looking into `/docs/specs/{spec-name}/spec.md` for the beads id.
3. Read the full body and the comments of the epic to gather all the necessary context.

4. Find ready tasks using `bd ready --parent {epic-id} --json` to list all unblocked tasks ready for execution.

If no ready tasks are found:

- Check if all tasks are already completed: `bd show <epic-id> --json`
- If all done, report that the spec is fully implemented
- If tasks exist but are blocked, report the blockers and stop

### Claim task and update status

5. Claim the task setting the status to `in_progress` `bd update <id> --claim`
6. Read the description of the task `bd show <id>` and acceptance criteria. Understand what needs to be built before writing any code.
7. Read the progress log that lives on the epic. Iteration history and codebase patterns will be recorded there.

### Implement the task using TDD

8. Implement the one task described in the issue. Keep changes small and focused:

- one logical change per commit
- if a task feels to large, break it down into subtasks and use subagents for each
- prefer multiple small commits over one large commit

9. Follow [test driven development practices](./TEST_DRIVEN_DEVELOPMENT.md)

### Run feedback loops

10. Feedback loops: before committing all available checks must pass. Do not commit if any check fails, fix issues first.

Discover available commands from `CLAUDE.md`, the project's `Makefile`, `package.json` scripts, any custom scripts defined in the project, pre-commit hooks, CI checks etc.

### Final phase

11. Make a git commit and push to the remote. Only commit work for a single task.
12. mark the beads task as done `bd close <id>`
13. update the progress log, append an iteration summary as a comment on the epic:

```bash
bd comment <epic-id> "# $(date -u +%Y-%m-%d)

- **Task completed**: <brief description> (<task-id>)
- **Files changed**: <list of files>
- **Decisions made**: <and why>
- **Blockers encountered**: <if any>
- **Architectural decisions**: <if any>
- **Notes for next iteration**: <context for the next agent>
```

If you discovered new codebase patterns append them to the epic's notes field:

```bash

bd note <epic-id> "## Codebase Patterns (added $(date -u +%Y-%m-%d))
- <pattern 1>
- <pattern 2>
```

Do not close or modify the parent epic unless the task list is fully complete.
