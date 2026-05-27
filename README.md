# specwright

**Spec-driven development as a few sharp skills, not a framework.**

## Why

Spec-driven development is a good idea. The frameworks built around it don't have to be.

Existing toolkits ship dozens of markdown files, opinionated directory layouts, and bespoke runtimes you have to learn before you can write a single line of code. The mental tax outweighs the speedup.

specwright is the opposite:

- **A few sharp skills, not a framework.** Compose what you need, drop the rest.
- **Lean by default.** Thin specs, vertical slices, TDD on execution, multi-agent review on completion. No house style, no scaffolding tax.
- **Agent-agnostic.** Skills are plain markdown, designed against both Claude Code and Codex skill formats. Drop them into any agent that loads skills.
- **Beads first, not locked in.** Default tracker is beads; plan-markdown files, GitHub Issues, and GitLab Issues are first-class fallbacks.

## Status

`v0.1.0` — plugin skeleton plus the first utility skills. Manifests, reference contracts, and the forked specwright grill/TDD/PRD/slicing skills are in place.

## Install

### Claude Code

```text
/plugin marketplace add francesco-albanese/specwright
/plugin install specwright@specwright
```

### Codex

```sh
codex plugin marketplace add francesco-albanese/specwright
```

Then open `/plugins` in the Codex TUI and install **specwright**, or:

```text
/plugin install specwright@specwright
```

### Portable (any other agent)

```sh
git clone https://github.com/francesco-albanese/specwright.git
ln -s "$PWD/specwright/skills" <your-agent-skills-dir>/specwright
```

The `skills/` directory holds plain `<name>/SKILL.md` files — any agent that loads markdown skills with YAML frontmatter can use them.

## Layout

```text
.
├── .claude-plugin/
│   ├── plugin.json        # Claude Code plugin manifest
│   └── marketplace.json   # Claude Code marketplace catalog
├── .codex-plugin/
│   └── plugin.json        # Codex plugin manifest
├── marketplace.json       # Codex marketplace catalog
├── skills/                # SKILL.md files (one per skill)
├── references/            # Shared reference docs (contracts)
├── docs/                  # ADRs + discovery notes
├── CONTEXT.md             # Project glossary
└── PLAN.md                # v1 plan
```

## License

MIT — see [LICENSE](./LICENSE).
