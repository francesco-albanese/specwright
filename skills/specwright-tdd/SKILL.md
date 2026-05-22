---
name: specwright-tdd
description: Test-driven development with red-green-refactor loop scoped to a single specwright vertical slice. RED tests MUST verify user-visible behavior, NOT internal calls. Use when implementing a specwright slice via /specwright:execute or when doing TDD on a specwright-tracked feature.
---

<!-- Adapted from ~/.claude/skills/tdd -->

# Specwright TDD

**Vertical-slice scope reminder:** this TDD session is scoped to one slice. If you are about to write code or tests outside the slice's `estimated_touched_paths`, pause and report to the user before proceeding.

## Core principle (non-negotiable)

**RED tests MUST verify user-visible behavior, NOT internal calls.**

This is the single rule that determines whether a test is useful or harmful. Write a test that would still pass after a complete internal refactor — if renaming an internal function breaks the test, the test is wrong. Tests describe *what* the system does for users, not *how* it does it internally.

## Philosophy

Tests should verify behavior through public interfaces. Code can change entirely; tests should not break when behavior hasn't changed.

**Good tests** exercise real code paths through public APIs. They read like specifications: "user can submit a valid discount code and see the updated total." These tests survive refactors.

**Bad tests** are coupled to implementation: they mock internal collaborators, test private methods, or verify through implementation-level means. Warning sign: your test breaks on a refactor, but behavior hasn't changed.

## Anti-pattern: horizontal slices

**DO NOT write all tests first, then all implementation.** This produces tests that verify imagined structure, not actual behavior.

```
WRONG (horizontal):
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical):
  RED→GREEN: test1→impl1
  RED→GREEN: test2→impl2
  RED→GREEN: test3→impl3
  ...
```

## Workflow

### 1. Load slice context

Before writing any code, read:

- The beads slice (acceptance criteria, `estimated_touched_paths`, `depends_on`).
- `.specs/<slug>/requirements.md` and `design.md` if `spec_path` is non-null.
- `CONTEXT.md` for domain vocabulary.

Test names and interface vocabulary must match the project's domain language.

### 2. Planning

- Confirm with user which behaviors to test (prioritize by AC from `requirements.md`).
- List the behaviors to test — framed as user-visible outcomes, not implementation steps.
- Design interfaces for testability before writing tests.
- Get user approval on the plan.

Ask: "Which acceptance criteria from the slice are most critical to cover first?"

### 3. Tracer bullet

Write ONE test that confirms ONE thing about the system:

```
RED:   Write test for first AC behavior → test fails
GREEN: Write minimal code to pass → test passes
```

This proves the path works end-to-end.

### 4. Incremental loop

For each remaining AC behavior:

```
RED:   Write next test → fails
GREEN: Minimal code to pass → passes
```

Rules:
- One test at a time.
- Only enough code to pass the current test.
- Don't anticipate future tests.
- Keep tests focused on observable, user-visible behavior.

### 5. Refactor

After all tests pass:

- Extract duplication.
- Deepen modules (move complexity behind simple interfaces).
- Run tests after each refactor step.
- **Never refactor while RED.** Get to GREEN first.

## Checklist per cycle

```
[ ] Test describes user-visible behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive internal refactor
[ ] Test name uses domain vocabulary from CONTEXT.md
[ ] Code is minimal for this test
[ ] No speculative features added
[ ] Changes stay within slice's estimated_touched_paths
```

## Scope check

After each GREEN, verify the changes are within the slice boundary. If a new file or path outside `estimated_touched_paths` is needed, pause and confirm with the user before continuing.
