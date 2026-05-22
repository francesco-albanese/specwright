---
name: specwright-grill-with-docs
description: Grilling session that challenges a specwright feature plan against the existing domain model in CONTEXT.md, sharpens EARS terminology, and updates CONTEXT.md inline as decisions crystallise. Offers ADRs sparingly. Feeds .specs/<slug>/requirements.md. Use when user wants to stress-test a specwright plan against their project's language and documented decisions before writing the PRD.
---

<!-- Adapted from ~/.claude/skills/grill-with-docs -->

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask questions one at a time, waiting for feedback on each before continuing.

If a question can be answered by exploring the codebase, explore the codebase instead.

## Domain awareness

During codebase exploration, also look for:

- `CONTEXT.md` at the repo root — the project glossary. Read it before starting.
- `docs/adr/` — architectural decision records.
- `references/spec-format.md` — the on-disk artifact contract that `requirements.md` and `design.md` must conform to.

If a `CONTEXT-MAP.md` exists at the root, the repo has multiple bounded contexts; read it to find which one the current topic relates to.

Create files lazily — only when you have something to write. If no `CONTEXT.md` exists, create one when the first term is resolved.

## During the session

### Challenge against the glossary

When the user uses a term that conflicts with `CONTEXT.md`, call it out immediately. "Your glossary defines 'cancellation' as X, but you seem to mean Y — which is it?"

### Sharpen fuzzy language toward EARS

When the user describes behavior vaguely, sharpen it toward EARS notation (per `references/spec-format.md`):

- `WHEN <trigger> THE SYSTEM SHALL <observable response>` — event-driven
- `WHILE <state> THE SYSTEM SHALL <response>` — state-driven
- `WHERE <feature> THE SYSTEM SHALL <response>` — optional feature
- `THE SYSTEM SHALL <response>` — ubiquitous

Keywords (`WHEN`, `WHILE`, `WHERE`, `THE`, `SHALL`) are **UPPERCASE**.

When the user says "it should handle X," push them to an EARS sentence: "Can we say WHEN X occurs THE SYSTEM SHALL Y?"

### Discuss concrete scenarios

Stress-test domain relationships with specific scenarios. Probe edge cases and force precision about concept boundaries. Use the project's vocabulary from `CONTEXT.md` throughout.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: "Your code does X, but you just said Y — which is right?"

### Update CONTEXT.md inline

When a term is resolved, update `CONTEXT.md` right there. Don't batch these up — capture them as they happen.

`CONTEXT.md` is a glossary only — no implementation details, no spec content, no decisions. Each entry: term in bold, one or two sentence definition, _Avoid: synonyms to reject_.

### Offer ADRs sparingly

Only offer to create an ADR in `docs/adr/` when **all three** are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful.
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons.

If any of the three is missing, skip the ADR. ADRs use sequential numbering (`0001-slug.md`). The format: title, date, 1–3 sentences of context + decision + rationale.

## Output (end of session)

Do not write spec files during the interview. At the end, summarize:

1. The agreed acceptance criteria in EARS form, ready to paste into `requirements.md`.
2. Any new or updated `CONTEXT.md` terms resolved during the session.
3. Any ADRs created.
4. Unresolved questions.

Then tell the user to run `/specwright:to-prd` to write `requirements.md` + `design.md` to `.specs/<slug>/`.
