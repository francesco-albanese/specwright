---
name: specwright:grill-with-docs
description: Interview the user against the repository's glossary and ADRs, then update CONTEXT.md and rare ADRs as specwright decisions crystallize.
---

# specwright:grill-with-docs

Use this when a feature or bugfix needs a deeper interview grounded in the repository's language and documented decisions. Preserve the `grill-me` interview style, but verify claims against docs and code where possible.

## Required References

- Follow [references/spec-format.md](../../references/spec-format.md) for requirements and bugfix artifact shape.
- Use `CONTEXT.md` as the glossary. Create it only when a term is resolved and no glossary exists.
- Use ADRs only for durable architectural decisions.

## Workflow

1. Read `CONTEXT.md`, `CONTEXT-MAP.md` if present, and relevant ADRs before asking domain questions.
2. If a question can be answered by reading code or docs, inspect the repo instead of asking.
3. Ask one question at a time, with a recommended answer.
4. When a term is resolved, update `CONTEXT.md` immediately. Keep it a glossary only: no implementation details, no plans, no task notes.
5. Offer an ADR only when the decision is hard to reverse, surprising without context, and the result of a real trade-off.
6. Continue until the downstream `requirements.md` or `bugfix.md` can be written without guessing.

## Challenges To Make Explicit

- "Your glossary defines X as A, but you seem to mean B. Which is canonical?"
- "The code currently does X, while the proposed behavior says Y. Is the code wrong or is the request different?"
- "This scenario crosses two contexts. Which context owns the rule?"

## Final Response

End with a concise handoff:

- `Resolved terms`: terms changed or added in `CONTEXT.md`.
- `Artifact-ready intent`: one statement suitable for `requirements.md`.
- `Acceptance criteria`: EARS candidates from [references/spec-format.md](../../references/spec-format.md).
- `ADR candidates`: created ADR paths, offered-but-skipped decisions, or `None`.
- `Open questions`: bullets, or `None`.
