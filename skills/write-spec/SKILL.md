---
name: write-spec
description: Turns the current conversation context, such as requirements.md files, adrs, and other relevant documentation into a comprehensive software requirement specification. Use when the user wants to create a spec for a task or project, or asks to cristallise requirements into a spec.
disable-model-invocation: true
context: fork
allowed-tools: Agent(Explore), Bash, Read, Grep, Write, Edit, Glob, TodoWrite
---

# Write spec

Invocation:

- Claude Code: `/specwright:write-spec`
- Codex: `$specwright:write-spec`

Compatibility: this skill is shared by Claude Code and Codex. Keep the
frontmatter for Claude Code; Codex uses `name` and `description` and may ignore
unsupported metadata. When a named tool is unavailable, use the closest native
capability: read/search files directly, ask the user in chat, or edit files with
the runtime's normal file-editing tools.

## Hard stop

When the user asks to write a spec, check first if the required information is contained in your context
window. Check the previous conversation history, also check for `/docs/**/requirements.md`, or `/docs/adr`.
If the context is not sufficient, ask the user to provide more information and suggest
`/specwright:gather-requirements` in Claude Code or `$specwright:gather-requirements` in Codex to refine
the requirements first.

## Issue tracker

The issue tracker is beads. Create beads epic and return bead id in `spec.md` so that the spec can be
easily linked to this epic.

## How to write the spec

The spec should explicitly define the external behaviour of the target software, things like input/output
mappings, preconditions/postconditions, invariants, constraints, interface types, integration contracts
and sequential logic/state machines.

The spec should be written using domain-oriented ubiquitous language to describe business intent rather
than specific tech-bound implementations. It should also have a clear structure, include scenarios and
user stories using Given/When/Then with acceptance criteria, system behaviour, functional/non functional
requirements, edge cases and error handling and testing strategy.

The spec should aim to be **extremely** readable, a good spec is a spec that humans find easy to read,
split in sections, information is clearly organised and well presented, with a clear narrative and flow.
The spec should be structured in a way that makes it easy to review and understand for both humans and AI
agents, with clear sections, headings, bullet points, tables, diagrams etc.

Use the project's domain glossary vocabulary and ubiquitous language contained in `CONTEXT.md` throughout
the spec, and respect any ADRs in the area you are touching.

## Organization of spec files

Spec files live in `/docs/specs/{spec-name}` folder

Each spec should have the following file structure:

- **contracts.md** - [contract.md format](./CONTRACTS_FORMAT.md)
- **data-model.md** - [data-model.md format](./DATA_MODEL_FORMAT.md)
- **user-stories.md** - [user-stories.md format](./USER_STORIES_FORMAT.md)
- **acceptance-criteria.md** - [acceptance-criteria.md format](./ACCEPTANCE_CRITERIA_FORMAT.md)
- **spec.md** - [spec.md format](./SPEC_FORMAT.md)

## Next steps

Suggest to the user to move to the next phase of reviewing the spec using a new agent with a fresh
context window, with `/specwright:review-spec` in Claude Code or `$specwright:review-spec` in Codex,
populating the `beads-id` as argument hint.
