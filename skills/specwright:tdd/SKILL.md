---
name: specwright:tdd
description: Run an intent-based RED-GREEN-REFACTOR loop for one specwright slice, testing user-visible behavior through public interfaces rather than implementation details.
---

# specwright:tdd

Use this inside `/specwright:execute` for one vertical slice. The slice is bounded by one acceptance criterion from [references/slice-schema.md](../../references/slice-schema.md) and, when present, the PRD artifacts from [references/spec-format.md](../../references/spec-format.md).

**Intent-vs-implementation framing: RED tests must verify user-visible behavior, NOT internal calls.**

## Scope Guard

- Work on one slice at a time.
- Start from the slice's `acceptance_criteria` text verbatim.
- Prefer tests through public interfaces, CLI commands, HTTP endpoints, UI behavior, or documented module APIs.
- Mock only external boundaries that the system cannot control in the test environment.
- Do not test private methods, internal call counts, incidental data shapes, or collaborator wiring.
- If passing the AC requires changes outside the slice's estimated scope, pause and report the scope mismatch.

## Loop

1. Load the slice body, acceptance criterion, `estimated_touched_paths`, and `spec_path`.
2. Read the relevant `requirements.md`, `design.md`, or tiny inline spec.
3. Choose the narrowest observable behavior that proves the AC.
4. RED: write one failing test for that behavior and run the smallest relevant test command.
5. GREEN: write the minimum production code that makes the test pass.
6. REFACTOR: improve structure only while tests stay green.
7. Repeat only for additional behavior required by the same AC.

## Bugfix Rule

For bugfix flow, slice 1 is regression-test only: prove the bug with a failing test and stop before production changes. Slice 2 implements the fix and preserves `## Unchanged Behavior` from `bugfix.md`.

## Test Quality Checklist

- The test name describes user-visible behavior.
- The test fails for the right reason before the implementation.
- The assertion observes output, state, response, or visible side effect through a public interface.
- The test would survive an internal refactor that keeps behavior unchanged.
- The implementation is no broader than the AC requires.

Return the RED command/output, GREEN command/output, refactor notes, and any scope risks to the caller.
