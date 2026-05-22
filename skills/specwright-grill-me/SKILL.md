---
name: specwright-grill-me
description: Interview the user relentlessly about a feature or bugfix until requirements are sharp enough to write EARS acceptance criteria. Feeds .specs/<slug>/requirements.md (feature flow) or the beads issue body (tiny flow). Use when user wants to grill me on a spec, stress-test requirements, or is starting the specwright feature flow.
---

<!-- Adapted from ~/.claude/skills/grill-me -->

Interview me relentlessly about every aspect of this feature or bugfix until we reach shared understanding and requirements are concrete enough to express as EARS acceptance criteria. Walk down each branch of the decision tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask questions one at a time, waiting for feedback on each before continuing.

## Scope

Determine which flow applies before starting:

- **Feature flow** — full PRD on disk. Output feeds `requirements.md` + `design.md` in `.specs/<slug>/`. See `references/spec-format.md`.
- **Tiny flow** — no `.specs/` directory. Output feeds the beads issue body using the compact inline spec format. See `references/spec-format.md` (Tiny-flow inline variant).

If the scope is unclear, ask the first question: "Is this a full feature (needing a spec document) or a quick, self-contained change?"

## During the interview

Focus every question on driving toward concrete, testable acceptance criteria. Each criterion must eventually be expressible in EARS notation (from `references/spec-format.md`):

- `WHEN <trigger> THE SYSTEM SHALL <observable response>` — event-driven
- `WHILE <state> THE SYSTEM SHALL <response>` — state-driven
- `WHERE <feature> THE SYSTEM SHALL <response>` — optional feature
- `THE SYSTEM SHALL <response>` — ubiquitous

Keywords (`WHEN`, `WHILE`, `WHERE`, `THE`, `SHALL`) are **UPPERCASE**. The subject and response are written naturally.

**Push for specificity:** vague requirements produce flawed slices. If the user says "it should be fast," ask: "What response time is acceptable? Under what load?"

**Surface edge cases:** ask what happens when the happy path fails. "What should the system do if the user has no permissions?" These often surface new ACs or Unchanged Behavior items.

**Use project vocabulary:** refer to terms from `CONTEXT.md` throughout. If the user introduces a term not in the glossary, flag it.

## Output (end of session)

Do not write files during the interview. At the end, summarize:

1. The agreed acceptance criteria in EARS form, ready to paste into `requirements.md` (or the tiny-flow beads body).
2. A list of any unresolved questions.
3. A recommendation: feature flow or tiny flow?

Then tell the user to run `/specwright:to-prd` to write the on-disk artifacts (feature flow) or `/specwright:tiny` to write the beads issue inline (tiny flow).
