# Verify Command Discovery

How `/specwright:execute`'s auto-verify loop (step 4 of the execute pipeline) finds the
`test`, `lint`, `format`, `typecheck`, and `build` commands at runtime.

Specwright ships no init skill and no config file — discovery is convention-driven.
Stages run in order; the first stage to resolve a key wins for that key.
Unresolved keys are skipped; the loop runs what it found.

---

## Stage 1 — explicit override

Read `CLAUDE.md` and `AGENTS.md` from the project root. Look for a section with the
exact heading `## Specwright — Verify Commands` (level-2 ATX, em-dash U+2014).
If the section exists, parse the fenced block tagged `commands` immediately following it:

```markdown
## Specwright — Verify Commands

```commands
test: pnpm test
lint: pnpm lint
format: pnpm format:check
typecheck: pnpm typecheck
build: pnpm build
```
```

Each non-blank, non-comment line is `key: command`. Unknown keys are ignored.
Keys absent from the block fall through to Stage 2.

If both `CLAUDE.md` and `AGENTS.md` contain the section, `CLAUDE.md` wins for any key
it sets; `AGENTS.md` fills remaining gaps.

---

## Stage 2 — per-ecosystem defaults

Detect the ecosystem from files present at the project root and apply the defaults below.
Multiple ecosystems may apply; first non-resolved value per key wins.

| ecosystem | trigger file | `test` | `lint` | `format` | `typecheck` | `build` |
| --- | --- | --- | --- | --- | --- | --- |
| **JS / TS** | `package.json` | `<pm> run test` | `<pm> run lint` | `<pm> run format` | `<pm> run typecheck` | — |
| **Python** | `pyproject.toml`, `requirements.txt`, or `setup.py` | `pytest` | `ruff check` | `ruff format --check` | `mypy` (or `pyright` if in pyproject deps) | — |
| **Rust** | `Cargo.toml` | `cargo test` | `cargo clippy` | `cargo fmt --check` | `cargo check` | `cargo build` |
| **Go** | `go.mod` | `go test ./...` | `go vet ./...` | `gofmt -l .` | — | `go build ./...` |
| **Terraform** | any `*.tf` at root | — | `tflint` | `terraform fmt -check -recursive` | — | — |

`<pm>` resolves to `pnpm` (pnpm-lock.yaml), `yarn` (yarn.lock), `bun` (bun.lockb), or
`npm` (fallback). A `<pm> run <script>` entry is only emitted when the corresponding
`scripts.<name>` key exists in `package.json`. For Python, `pyright` is used when
`pyright` appears anywhere in `pyproject.toml`; otherwise `mypy`.

A target named `test`, `lint`, `format`, `typecheck`, or `build` in a `Makefile` or
`justfile` at the project root overrides the ecosystem default for that key, emitted as
`make <key>` or `just <key>` respectively. Stage-1 overrides always beat Makefile/justfile
targets.

---

## Stage 3 — unresolved miss

If a key the agent needs is still unresolved after Stage 2, the agent asks the user once:

```
I couldn't determine the <key> command automatically.
What should I run for <key>? (Leave blank to skip.)
```

If the user provides a command, the agent proposes a one-shot edit to `CLAUDE.md`
(or `AGENTS.md` if `CLAUDE.md` does not exist) inserting the `## Specwright — Verify Commands`
section so future runs resolve at Stage 1. The user confirms before the file is written.
