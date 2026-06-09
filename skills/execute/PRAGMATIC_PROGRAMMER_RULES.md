# Pragmatic programmer

Universal engineering principles that apply to every project, stack, and language.

## Decoupling

- **Orthogonality** — reduce interdependency among components. Keep code decoupled, avoid global data,
  avoid similar functions.
- **Minimise coupling between modules** — a change in one place should not ripple through unrelated code.
- **Design components that are self-contained, independent, and with a single well-defined purpose.**

## Change & Reuse

- **Plan for change**
- **Make it easy to reuse**
- **Invest in the abstraction, not the implementation** — abstractions outlive any single implementation.

## Correctness

- **Don't assume it, prove it** — verify assumptions in the actual environment
- **Crash early** — fail fast and loudly when an invariant breaks

## Testing

- **Test state coverage, not code coverage**
- **Design to test**
