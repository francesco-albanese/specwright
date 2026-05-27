---
name: specwright:grill-me
description: Interview the user relentlessly about a specwright plan until intent, acceptance criteria, and unresolved decisions are precise enough to feed requirements.md or a tiny-flow beads issue.
---

# specwright:grill-me

Interview the user about a plan or design until there is shared understanding. Walk the design tree one decision at a time, resolving dependencies before moving on. Ask one question at a time and provide your recommended answer with each question.

Use this skill when a specwright flow needs human clarification before writing artifacts.

## Output Targets

Use [references/spec-format.md](../../references/spec-format.md) as the contract for downstream output.

- Feature, quick, and bugfix flows feed `requirements.md` acceptance criteria.
- Tiny flow feeds the compact beads issue body described by the tiny-flow inline variant.
- Acceptance criteria must be user-visible behavior in EARS notation.
- Keep unresolved questions explicit so the calling flow can decide whether to continue, ask, or bail.

## Interview Rules

- Start from the user's concrete goal, not an implementation idea.
- Challenge vague terms and overloaded nouns immediately.
- Prefer concrete scenarios over abstract preferences.
- Ask about boundaries: in scope, out of scope, unchanged behavior, failure modes.
- Ask about observable behavior before architecture.
- Stop when each major branch has either a decision or a named unresolved question.

## Final Response

End with:

- `Intent`: one concise statement.
- `Acceptance criteria`: EARS candidates, each as one sentence.
- `Unchanged behavior`: bullets, if any.
- `Open questions`: bullets, or `None`.

Do not write files. The calling flow writes artifacts.
