---
name: review-spec
description: Reviews the spec written in the previous phase using a new agent with a fresh context window, to identify drift from the requirements, ambiguity, test gaps etc. Use it when the user asks to review the spec, or when the spec has been recently written and needs to be reviewed before moving to the next phase of writing tasks and implementation.
disable-model-invocation: true
context: fork
allowed-tools: Agent(Explore), Bash, Read, Grep, Write, Edit, Glob, AskUserQuestion, TodoWrite
argument-hint: "[beads-id]"
---

# Review spec

When a named tool is unavailable, use the closest native capability: read/search files directly, ask the user in chat, or edit files with the runtime's normal file-editing tools.

The goal is to review the spec located at
`/docs/specs/{spec-name}/spec.md`
to identify drift from the original requirements, ambiguity, test gaps etc.

## Phases

1. Review the original requirements located in `/docs/specs/{spec-name}/requirements.md`. This file should have been written in the previous phase of gather requirements, and should contain all the necessary context, clarified terms, resolved ambiguities, scenarios discussed and links to ADRs written, if any.

2. Review the spec located in `/docs/specs/{spec-name}/spec.md`

3. Provide a list of issues found in the spec, with links to the relevant sections of the spec and original requirements. For each issue found, give your recommendation on how to address it.

4. Make sure all ambiguities are resolved, all gaps filled, all edge cases and scenarios covered and drift from original requirements identified and addressed.

5. Offer the user to write back to the spec with the necessary changes, or to write a new version of the spec if the issues found are too many or too significant to be addressed with simple edits. If the user agrees, update the original `spec.md` file with the runtime's normal file-editing tools.

## Next steps

Suggest to the user to move to the next phase of writing tasks for implementation, with
`/specwright:write-tasks` in Claude Code or `$specwright:write-tasks` in Codex.
