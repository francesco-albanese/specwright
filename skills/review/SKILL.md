---
name: review
description: Run a thorough code review of the beads tasks that have been implemented in a previous phase
using a new agent with a fresh context window. Use it when the user asks to review the code, or when the
execute phase has concluded.
context: fork
allowed-tools: Agent(Explore), Bash, Read, Grep, Write, Edit, AskUserQuestion, Glob, TodoWrite
argument-hint: "[beads-id]"
---

# Review

Review the code produced in the previous phase against spec fidelity, code quality and test quality,
security flaws and spec gaps/context drifts.

Invocation:

- Claude Code: `/specwright:review`
- Codex: `$specwright:review`

Compatibility: this skill is shared by Claude Code and Codex. Keep the
frontmatter for Claude Code; Codex uses `name` and `description` and may ignore
unsupported metadata. When a named tool is unavailable, use the closest native
capability: read/search files directly, ask the user in chat, or edit files with
the runtime's normal file-editing tools.

If the relevant spec and context is not already in your context window ask the user to provide a merge
request link or a beads id.

If the user provides a beads id as an argument, fetch the task from beads and read its full body to
gather context.

## Process

1. Use `gh` cli to pull the pull request relevant to the spec
2. Grab the beads id of the tasks executed and link it back to the original spec/epic
3. Read the `/docs/specs/{spec-name}/requirements.md` and `/docs/specs/{spec-name}/spec.md` to understand the full requirements and implementation details
4. Run a thorough review checking for:

- [ ] spec fidelity
- [ ] code quality
- [ ] test quality
- [ ] security concerns
- [ ] spec implementation gaps
- [ ] context drifts
- [ ] all edge cases covered
- [ ] functional and non functional requirements satisfied
- [ ] all contracts implemented

## Verdict

After completing all review checks produce a final verdict using exactly one of the following
classifications:

| Classification     | Criteria                                                                                                                                                                  |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ✅ PASS            | All checklist items satisfied. No spec gaps, no security concerns, safe to merge                                                                                          |
| ⚠️ NEEDS ATTENTION | One or more checklist items partially satisfied. Non-blocking issues that should be addressed before or shortly after merge. List each item with a recommended fix.       |
| ❌ FAIL            | One or more blocking issues found. Spec gaps, security flaws, missing contracts, or functional regressions. Must not merge. List each blocking issue with a required fix. |

Conclude the review giving your verdict using a structured block based on the above classification and provide a list of your recommended fixes, if any.
