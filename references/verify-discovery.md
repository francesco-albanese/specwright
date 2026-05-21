# Verify Command Discovery

Canonical contract for how `/specwright:execute`'s auto-verify loop (step 4 of the execute pipeline) finds the `test`, `lint`, `format`, `typecheck`, and `build` commands at runtime.

Specwright ships no init skill and no on-disk config. Discovery is convention-driven. This document is the single source of truth — the validator at `tests/verify_discovery_validator.py` asserts every example here against fixtures under `tests/fixtures/verify-discovery/`.

---

## 1. Command map shape

The discovery algorithm returns a map with exactly these five keys:

| key | role |
| --- | --- |
| `test` | run the project's automated tests |
| `lint` | run the linter |
| `format` | run the formatter in **check** mode (no writes) |
| `typecheck` | run the static type checker |
| `build` | run the build / compile step |

A key whose value cannot be resolved by stages 1–2 is `None`. The auto-verify loop skips `None` entries silently — they are not failures, just absent capabilities. Stage 3 (ask the user) only fires when **all five** values are `None` for the resolved ecosystem, or when the user explicitly requests adding one.

---

## 2. Three-stage discovery algorithm

Stages run **in order**. The first stage to produce a non-`None` value for a key wins for that key. Different keys may resolve at different stages — e.g., `test` from a CLAUDE.md override, `lint` from ecosystem defaults.

### Stage 1 — explicit override in CLAUDE.md / AGENTS.md

Read `CLAUDE.md` and `AGENTS.md` from the project root (the directory passed to `discover()`). Either, both, or neither may exist.

Look for a section with the exact heading:

```
## Specwright — Verify Commands
```

The heading uses an **em-dash** (`—`, U+2014), not a hyphen. The heading must start with `## ` at the beginning of a line (level-2 ATX heading). Other heading levels are ignored.

Immediately after the heading (blank lines allowed) the section contains exactly one fenced code block. The fence info string may be empty or `yaml` — both are accepted. Inside the block, each non-empty, non-comment line follows:

```
<key>: <command>
```

- `<key>` is one of `test`, `lint`, `format`, `typecheck`, `build`. Unknown keys are ignored (not an error).
- `<command>` is the full command line, run as-is (no shell expansion beyond what the executing shell provides).
- Lines starting with `#` are comments and ignored.
- Empty lines inside the block are ignored.
- Keys not present in the block fall through to stage 2.

**Example override section:**

```markdown
## Specwright — Verify Commands

```yaml
test: pnpm test
lint: pnpm lint
format: pnpm format:check
typecheck: pnpm typecheck
build: pnpm build
```
```

**Precedence between files.** If both `CLAUDE.md` and `AGENTS.md` contain a section, `CLAUDE.md` wins for every key it sets. `AGENTS.md` fills in any keys `CLAUDE.md` omits. This matches the broader specwright pattern: `CLAUDE.md` is the human-curated source of truth, `AGENTS.md` is the agent-replication target.

**Malformed sections fall through.** A section is malformed (and ignored entirely) if any of:

- The fenced block is unterminated (no closing fence before EOF or next heading).
- No fenced block follows the heading before the next `## ` heading.
- The fence info string is neither empty nor `yaml`.

A malformed section does **not** raise — discovery silently falls through to stage 2 for all keys. Unparseable lines inside an otherwise-valid block are ignored individually (the block is not invalidated).

### Stage 2 — per-ecosystem defaults

Detect the project's ecosystem by file presence at the project root, then apply the canonical command map below. **Multiple ecosystems may apply simultaneously** (e.g., a Terraform project with a Python toolchain) — keys are filled from each detected ecosystem in the order listed. First non-`None` value wins per key, but `Makefile` / `justfile` targets always take precedence for a given key over the raw ecosystem command (see "Overrides via Makefile / justfile" below).

| ecosystem | trigger file(s) | `test` | `lint` | `format` | `typecheck` | `build` |
| --- | --- | --- | --- | --- | --- | --- |
| **JS / TS** | `package.json` | `<pm> run test` (if `scripts.test` present) | `<pm> run lint` | `<pm> run format` | `<pm> run typecheck` | `<pm> run build` |
| **Python** | `pyproject.toml` or `requirements.txt` or `setup.py` | `pytest` | `ruff check .` | `ruff format --check .` | `mypy .` (or `pyright` if listed in deps) | `None` |
| **Rust** | `Cargo.toml` | `cargo test` | `cargo clippy -- -D warnings` | `cargo fmt --check` | `cargo check` | `cargo build` |
| **Go** | `go.mod` | `go test ./...` | `go vet ./...` | `gofmt -l .` | `None` | `go build ./...` |
| **Terraform** | any `*.tf` file at root | `None` | `tflint` | `terraform fmt -check -recursive` | `None` | `None` |

**JS/TS package manager detection.** The placeholder `<pm>` resolves to:

- `pnpm` if `pnpm-lock.yaml` exists
- `yarn` if `yarn.lock` exists
- `bun` if `bun.lockb` exists
- `npm` otherwise

A `<pm> run <script>` command is only emitted if the corresponding `scripts.<name>` entry exists in `package.json`. Missing scripts leave the key `None`.

**Python typecheck detection.** Read `pyproject.toml` (text scan, no TOML parser required — match `pyright` as a substring inside a `[project]` or `[tool.poetry.dependencies]` or `[dependency-groups]` block). If `pyright` is mentioned anywhere in `pyproject.toml`, use `pyright`. Otherwise default to `mypy .`. If neither is installable, the auto-verify loop will report the command's exit and the agent escalates per the normal retry-cap path.

### Overrides via `Makefile` / `justfile`

If a `Makefile` or `justfile` exists at the project root, scan it for target names matching any of the five keys (`test`, `lint`, `format`, `typecheck`, `build`). A matching target overrides the stage-2 command for that key:

- `Makefile` → emitted command is `make <key>`.
- `justfile` → emitted command is `just <key>`.

**Target detection** uses a simple regex per line: `^<key>\s*:` for Makefile (must be at column 0, followed by a colon), and `^<key>\s*(:|$)` for justfile (the colon is optional in justfile syntax). Phony targets and target dependencies after the colon are fine — only the target name matters.

**Precedence between `Makefile` and `justfile`.** If both exist and both define a target for the same key, `justfile` wins. Rationale: justfile is typically the newer, more deliberate choice when both are present.

**Makefile / justfile do not override stage 1.** A CLAUDE.md / AGENTS.md override always beats a Makefile/justfile target.

### Stage 3 — ask the user, propose persistence

If after stages 1 and 2 a key the agent considers required is still `None`, or if no ecosystem at all was detected (all five keys `None`), the agent asks the user **once** during execute:

```
I couldn't determine the <key> command for this project automatically.
What should I run for <key>? (Leave blank to skip.)
```

The user types a command (or blank). If the user provides a command, the agent **proposes** an edit to persist the answer. The proposed edit is shown in full diff form before applying. Default target: `CLAUDE.md` if it exists, else `AGENTS.md`, else create `CLAUDE.md`.

**Proposed edit shape (insertion only, never modification of unrelated content):**

```diff
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -<line>,0 +<line>,N @@
+
+## Specwright — Verify Commands
+
+```yaml
+test: <user-supplied command>
+```
+
```

If the section already exists, the proposed edit adds only the new key line inside the existing fenced block:

```diff
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -<line>,N +<line>,N+1 @@
 ## Specwright — Verify Commands

 ```yaml
 test: pnpm test
+lint: pnpm lint
 ```
```

The user confirms (`y` / `n`). On `y`, the file is written and the run continues. On `n`, the answer is used for this run only — no persistence.

This flow is **single-shot per missing key per execute run** — the agent does not repeatedly prompt within a session.

---

## 3. Worked examples (validator fixtures)

Each example below maps 1:1 to a fixture directory under `tests/fixtures/verify-discovery/`. The validator asserts the expected map.

### `js-ts` — JS/TS with yarn

Fixture contains `package.json` (with `test`, `lint`, `format`, `typecheck`, `build` scripts) and `yarn.lock`.

```python
{
    "test": "yarn run test",
    "lint": "yarn run lint",
    "format": "yarn run format",
    "typecheck": "yarn run typecheck",
    "build": "yarn run build",
}
```

### `python` — Python with pyright in pyproject

Fixture contains `pyproject.toml` mentioning `pyright`.

```python
{
    "test": "pytest",
    "lint": "ruff check .",
    "format": "ruff format --check .",
    "typecheck": "pyright",
    "build": None,
}
```

### `rust` — Rust

Fixture contains `Cargo.toml`.

```python
{
    "test": "cargo test",
    "lint": "cargo clippy -- -D warnings",
    "format": "cargo fmt --check",
    "typecheck": "cargo check",
    "build": "cargo build",
}
```

### `go` — Go

Fixture contains `go.mod`.

```python
{
    "test": "go test ./...",
    "lint": "go vet ./...",
    "format": "gofmt -l .",
    "typecheck": None,
    "build": "go build ./...",
}
```

### `terraform` — Terraform

Fixture contains `main.tf`.

```python
{
    "test": None,
    "lint": "tflint",
    "format": "terraform fmt -check -recursive",
    "typecheck": None,
    "build": None,
}
```

### `override-claude` — explicit CLAUDE.md override

Fixture contains `CLAUDE.md` with the `## Specwright — Verify Commands` section setting all five keys, plus a `package.json` (which is ignored because override wins).

```python
{
    "test": "make test-ci",
    "lint": "make lint-ci",
    "format": "make fmt-check",
    "typecheck": "make types",
    "build": "make release",
}
```

### `override-makefile` — Makefile target overrides ecosystem default

Fixture contains `package.json` (with all scripts) and a `Makefile` with `test:` and `lint:` targets. Only those two keys are overridden; the rest fall through to ecosystem defaults.

```python
{
    "test": "make test",
    "lint": "make lint",
    "format": "npm run format",
    "typecheck": "npm run typecheck",
    "build": "npm run build",
}
```

### `override-malformed` — malformed override falls through

Fixture contains `CLAUDE.md` with a `## Specwright — Verify Commands` section whose fenced block is unterminated. The malformed section is ignored entirely; discovery falls through to the `package.json` (npm) defaults.

```python
{
    "test": "npm run test",
    "lint": "npm run lint",
    "format": None,
    "typecheck": None,
    "build": None,
}
```

### `miss` — no ecosystem detected

Fixture contains only a `README.md`. All five keys are `None` — this is the trigger for stage 3 (ask the user).

```python
{
    "test": None,
    "lint": None,
    "format": None,
    "typecheck": None,
    "build": None,
}
```
