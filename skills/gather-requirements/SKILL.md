---
name: gather-requirements
description: Refinement session for tasks with missing or vague context that needs refining and hardening. Use when user asks to gather requirements. Triggers on "gather requirements", "let's refine the ticket", "build requirements.md", "define the what and the why".
context: fork
allowed-tools: Agent(Explore), Bash, Read, Grep, Write, Edit, Glob, AskUserQuestion, TodoWrite
---

# Gather requirements

Assist the user in gathering all the necessary requirements for a task.

When a named tool is unavailable, use the closest native capability: read/search files directly, ask the user in chat, or use an available exploration subagent.

## Explore the codebase

Start by exploring the codebase. Use an available exploration subagent when the
runtime provides one; otherwise search and read files directly to find related
files, documentation, ADRs, or previous implementations of similar features.
Documentation might be found in `/docs` folder, `README.md` files, `CLAUDE.md` files or `CONTEXT.md`
files. If no `CONTEXT.md` exists, create one when the first term is resolved. If no `docs/adr/` exists,
create it when the first ADR is needed.

## Ask clarifying questions

Ask the user specific questions to clarify any remaining ambiguity and fill in
gaps in the requirements. Interview the user relentlessly about every aspect of
the plan until you reach a shared understanding. Walk down each branch of the
design tree, resolving dependencies between decisions one-by-one. For each
question, provide your recommended answer.

Ask the questions one at a time, waiting for feedback on each question before continuing.

## During the session

Consult the `CONTEXT.md` file when the user mentions a specific term, so you are on the same page with
the user about its meaning.

When the user uses a term that conflicts with the existing language in `CONTEXT.md`, call it out
immediately. Example: "Your glossary defines 'concept' as X, but you seem to mean Y - which is it?"

When the user uses vague or overloaded terms, propose a precise canonical term. Example: "You're saying
'account' - do you mean the Customer or the User? Those are different things."

## Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios
that probe edge cases and force the user to be precise about the boundaries between concepts.

When the user states how something works, check whether the code agrees. If you find a contradiction,
surface it: "Your code cancels entire Orders, but you just said partial cancellation is possible - which
is right?"

## Update CONTEXT.md

When a term is resolved, add it inline to the `CONTEXT.md`. Follow this [format](./CONTEXT_FORMAT.md).
`CONTEXT.md` is not a spec, it's just a glossary to keep the agents and the user always in sync when
defining context.

## ADRs

Offer to write ADRs sparingly, and only when a significant architectural decision is made that needs to
be documented.

Only offer to create an ADR when all three are true:

1. **Hard to reverse** - the cost of changing your mind later is meaningful
2. **Surprising without context** - a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** - there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR.

Use the [ADR format](./ADR_FORMAT.md) to write it.

## requirements.md

When the requirements are sufficiently clear and unambiguous, all necessary context gathered, no more
unresolved questions, write a `requirements.md` file with all the gathered requirements, including the
context, the clarified terms, the resolved ambiguities, the scenarios discussed and the links to ADRs
written, if any. This `requirements.md` file will be used as the source of truth for the next phase of
writing the spec. Place it under `/docs/specs/{spec_name}/requirements.md`.

## Next steps

Suggest to the user to move to the next phase of writing the spec with
`/specwright:write-spec` in Claude Code or `$specwright:write-spec` in Codex,
using `requirements.md` as the source of truth.
