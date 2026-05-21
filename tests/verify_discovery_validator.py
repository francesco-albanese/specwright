"""Validator for the verify-command discovery contract.

Implements the three-stage discovery algorithm documented in
``references/verify-discovery.md`` and asserts the expected command map for
each fixture under ``tests/fixtures/verify-discovery/``.

Runnable two ways:

    python tests/verify_discovery_validator.py        # standalone
    python -m pytest tests/verify_discovery_validator.py -v

Stdlib only: ``re``, ``pathlib``, ``json``, ``sys``, ``argparse``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KEYS: tuple[str, ...] = ("test", "lint", "format", "typecheck", "build")

OVERRIDE_HEADING = "## Specwright — Verify Commands"  # em-dash U+2014

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "verify-discovery"


# ---------------------------------------------------------------------------
# Stage 1 — CLAUDE.md / AGENTS.md override
# ---------------------------------------------------------------------------


def _extract_override_block(text: str) -> str | None:
    """Return the body of the override fenced block, or ``None`` if absent or malformed.

    Malformed cases (return ``None``):
      * heading not found
      * no fenced block before the next ``## `` heading or EOF
      * fence info string is neither empty nor ``yaml``
      * fence is unterminated
    """
    lines = text.splitlines()
    idx = None
    for i, line in enumerate(lines):
        if line.rstrip() == OVERRIDE_HEADING:
            idx = i
            break
    if idx is None:
        return None

    # Walk forward looking for the opening fence. Bail if we hit another ## heading.
    i = idx + 1
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            return None
        stripped = line.strip()
        if stripped.startswith("```"):
            info = stripped[3:].strip()
            if info not in ("", "yaml"):
                return None
            # Capture until closing fence
            body_lines: list[str] = []
            j = i + 1
            while j < len(lines):
                if lines[j].strip().startswith("```"):
                    return "\n".join(body_lines)
                body_lines.append(lines[j])
                j += 1
            # Unterminated fence
            return None
        i += 1
    return None


def _parse_override_block(body: str) -> dict[str, str]:
    """Parse ``key: command`` lines from an override block body."""
    out: dict[str, str] = {}
    line_re = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+?)\s*$")
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = line_re.match(line)
        if not m:
            continue  # unparseable individual line — skip
        key, cmd = m.group(1), m.group(2)
        if key in KEYS:
            out[key] = cmd
    return out


def _stage1(project_root: Path) -> dict[str, str]:
    """Merge CLAUDE.md (winner) over AGENTS.md."""
    merged: dict[str, str] = {}
    agents = project_root / "AGENTS.md"
    if agents.is_file():
        body = _extract_override_block(agents.read_text(encoding="utf-8"))
        if body is not None:
            merged.update(_parse_override_block(body))
    claude = project_root / "CLAUDE.md"
    if claude.is_file():
        body = _extract_override_block(claude.read_text(encoding="utf-8"))
        if body is not None:
            merged.update(_parse_override_block(body))  # CLAUDE.md wins
    return merged


# ---------------------------------------------------------------------------
# Stage 2 — per-ecosystem defaults
# ---------------------------------------------------------------------------


def _detect_js_pm(project_root: Path) -> str:
    if (project_root / "pnpm-lock.yaml").is_file():
        return "pnpm"
    if (project_root / "yarn.lock").is_file():
        return "yarn"
    if (project_root / "bun.lockb").is_file():
        return "bun"
    return "npm"


def _js_ts_defaults(project_root: Path) -> dict[str, str | None]:
    pkg_path = project_root / "package.json"
    if not pkg_path.is_file():
        return {}
    try:
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    scripts = pkg.get("scripts") or {}
    if not isinstance(scripts, dict):
        return {}
    pm = _detect_js_pm(project_root)
    out: dict[str, str | None] = {}
    for key in KEYS:
        if key in scripts:
            out[key] = f"{pm} run {key}"
    return out


def _python_defaults(project_root: Path) -> dict[str, str | None]:
    has_pyproject = (project_root / "pyproject.toml").is_file()
    has_reqs = (project_root / "requirements.txt").is_file()
    has_setup = (project_root / "setup.py").is_file()
    if not (has_pyproject or has_reqs or has_setup):
        return {}
    typecheck = "mypy ."
    if has_pyproject:
        try:
            txt = (project_root / "pyproject.toml").read_text(encoding="utf-8")
        except OSError:
            txt = ""
        if "pyright" in txt:
            typecheck = "pyright"
    return {
        "test": "pytest",
        "lint": "ruff check .",
        "format": "ruff format --check .",
        "typecheck": typecheck,
        "build": None,
    }


def _rust_defaults(project_root: Path) -> dict[str, str | None]:
    if not (project_root / "Cargo.toml").is_file():
        return {}
    return {
        "test": "cargo test",
        "lint": "cargo clippy -- -D warnings",
        "format": "cargo fmt --check",
        "typecheck": "cargo check",
        "build": "cargo build",
    }


def _go_defaults(project_root: Path) -> dict[str, str | None]:
    if not (project_root / "go.mod").is_file():
        return {}
    return {
        "test": "go test ./...",
        "lint": "go vet ./...",
        "format": "gofmt -l .",
        "typecheck": None,
        "build": "go build ./...",
    }


def _terraform_defaults(project_root: Path) -> dict[str, str | None]:
    if not any(project_root.glob("*.tf")):
        return {}
    return {
        "test": None,
        "lint": "tflint",
        "format": "terraform fmt -check -recursive",
        "typecheck": None,
        "build": None,
    }


def _stage2(project_root: Path) -> dict[str, str | None]:
    """Aggregate ecosystem defaults — first non-None per key wins.

    A key explicitly set to ``None`` by one ecosystem (e.g. Terraform's
    ``test: None``) is still overridden by a later ecosystem that supplies a
    concrete command. This matters when ecosystems co-exist in a polyglot
    repo.
    """
    aggregated: dict[str, str | None] = {}
    for fn in (
        _js_ts_defaults,
        _python_defaults,
        _rust_defaults,
        _go_defaults,
        _terraform_defaults,
    ):
        for key, val in fn(project_root).items():
            if key not in aggregated or (aggregated[key] is None and val is not None):
                aggregated[key] = val
    return aggregated


# ---------------------------------------------------------------------------
# Makefile / justfile overrides on top of stage 2
# ---------------------------------------------------------------------------


def _scan_targets(path: Path, target_re: re.Pattern[str]) -> set[str]:
    found: set[str] = set()
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            m = target_re.match(line)
            if m and m.group(1) in KEYS:
                found.add(m.group(1))
    except OSError:
        pass
    return found


def _apply_make_just(
    project_root: Path, base: dict[str, str | None]
) -> dict[str, str | None]:
    out = dict(base)
    makefile = project_root / "Makefile"
    justfile = project_root / "justfile"
    make_re = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:")
    just_re = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*(?::|$)")
    if makefile.is_file():
        for key in _scan_targets(makefile, make_re):
            out[key] = f"make {key}"
    if justfile.is_file():  # justfile wins over Makefile
        for key in _scan_targets(justfile, just_re):
            out[key] = f"just {key}"
    return out


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def discover(project_root: Path) -> dict[str, str | None]:
    """Run the three-stage discovery against ``project_root``.

    Stage 3 (ask the user) is non-interactive in this validator — it is
    documented in ``references/verify-discovery.md`` but not exercised here.
    Unresolved keys remain ``None``.
    """
    project_root = Path(project_root)

    # Stage 2 baseline
    stage2 = _stage2(project_root)

    # Makefile / justfile override stage 2
    after_make = _apply_make_just(project_root, stage2)

    # Stage 1 wins last (highest precedence)
    overrides = _stage1(project_root)

    final: dict[str, str | None] = {key: None for key in KEYS}
    for key in KEYS:
        if key in overrides:
            final[key] = overrides[key]
        elif key in after_make and after_make[key] is not None:
            final[key] = after_make[key]
        else:
            # Preserve explicit None from ecosystem defaults if it was set;
            # otherwise still None.
            final[key] = after_make.get(key)
    return final


# ---------------------------------------------------------------------------
# Expected maps per fixture
# ---------------------------------------------------------------------------

EXPECTED: dict[str, dict[str, str | None]] = {
    "js-ts": {
        "test": "yarn run test",
        "lint": "yarn run lint",
        "format": "yarn run format",
        "typecheck": "yarn run typecheck",
        "build": "yarn run build",
    },
    "python": {
        "test": "pytest",
        "lint": "ruff check .",
        "format": "ruff format --check .",
        "typecheck": "pyright",
        "build": None,
    },
    "rust": {
        "test": "cargo test",
        "lint": "cargo clippy -- -D warnings",
        "format": "cargo fmt --check",
        "typecheck": "cargo check",
        "build": "cargo build",
    },
    "go": {
        "test": "go test ./...",
        "lint": "go vet ./...",
        "format": "gofmt -l .",
        "typecheck": None,
        "build": "go build ./...",
    },
    "terraform": {
        "test": None,
        "lint": "tflint",
        "format": "terraform fmt -check -recursive",
        "typecheck": None,
        "build": None,
    },
    "override-claude": {
        "test": "make test-ci",
        "lint": "make lint-ci",
        "format": "make fmt-check",
        "typecheck": "make types",
        "build": "make release",
    },
    "override-makefile": {
        "test": "make test",
        "lint": "make lint",
        "format": "npm run format",
        "typecheck": "npm run typecheck",
        "build": "npm run build",
    },
    "override-malformed": {
        "test": "npm run test",
        "lint": "npm run lint",
        "format": None,
        "typecheck": None,
        "build": None,
    },
    "miss": {
        "test": None,
        "lint": None,
        "format": None,
        "typecheck": None,
        "build": None,
    },
}


# ---------------------------------------------------------------------------
# pytest-discoverable tests
# ---------------------------------------------------------------------------


def _check(name: str) -> None:
    actual = discover(FIXTURES_DIR / name)
    expected = EXPECTED[name]
    assert actual == expected, (
        f"fixture {name!r}: expected {expected!r}, got {actual!r}"
    )


def test_js_ts() -> None:
    _check("js-ts")


def test_python() -> None:
    _check("python")


def test_rust() -> None:
    _check("rust")


def test_go() -> None:
    _check("go")


def test_terraform() -> None:
    _check("terraform")


def test_override_claude() -> None:
    _check("override-claude")


def test_override_makefile() -> None:
    _check("override-makefile")


def test_override_malformed() -> None:
    _check("override-malformed")


def test_miss() -> None:
    _check("miss")


# ---------------------------------------------------------------------------
# Standalone CLI
# ---------------------------------------------------------------------------


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Validate verify-command discovery against fixtures."
    )
    parser.add_argument(
        "--fixture",
        help="Run a single fixture by name (default: all).",
    )
    args = parser.parse_args(argv)

    names = [args.fixture] if args.fixture else list(EXPECTED.keys())
    failed: list[tuple[str, str]] = []
    for name in names:
        try:
            _check(name)
            print(f"PASS  {name}")
        except AssertionError as e:
            print(f"FAIL  {name}: {e}")
            failed.append((name, str(e)))
    if failed:
        print(f"\n{len(failed)} failure(s).", file=sys.stderr)
        return 1
    print(f"\n{len(names)} fixture(s) passed.")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
