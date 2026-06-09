# specwright

A plugin for structured spec driven development, helping produce well-crafted software requirement specifications that AI coding agents can turn into executable code.

## Motivation

- Coding tasks require a large amount of contextual information, we need to curate that information carefully
- Provide a structured way to give AI coding agents the context they need for application development.
- Make sure requirements, data model, architecture, and intent are all captured and constitute part of the definition of done
- Clearly define the behaviour of the target software to help with code reviews

## Phases

1. Refinement: a task with missing or vague context that needs refining and hardening. Defines the _what_ and the _why_
2. Planning: defines the _how_, generates a comprehensive plan/spec with clear acceptance criteria and user stories
3. Spec verification: attempts to catch obvious drift and edge cases between the original task requirements and the spec produced
4. Implementation: code generation enforcing test driven development and automatic feedback loops
5. Verification: verification steps to make sure the generated code and tests satisfy the spec, meet requirements etc.
   Checks against spec fidelity, test quality, code quality, security flaws and spec gaps.

## Task tracker

Task tracker of choice is [beads](https://github.com/gastownhall/beads). Beads provides a persistent structured memory for coding agents, allowing them to have constant access to relevant context.
Beads is also a distributed graph issue tracker, like a Jira but for coding agents.

## Why beads?

- allows for rapid context injection
- easy to track dependencies between epics, tasks and subtasks
- helps with parallelization of agents, with abilities for them to claim a task and update its progress in real time

## Expected workflow

Claude Code invokes these skills with `/specwright:<skill>`. Codex invokes the same skills with `$specwright:<skill>`.

| Claude Code | Codex | When to use |
| --- | --- | --- |
| `/specwright:gather-requirements` | `$specwright:gather-requirements` | Refine vague context, clarify terms, and produce `requirements.md`. |
| `/specwright:write-spec` | `$specwright:write-spec` | Write a domain-oriented spec with scenarios, acceptance criteria, contracts, data model, edge cases, and testing strategy. |
| `/specwright:review-spec` | `$specwright:review-spec` | Review the spec with fresh context to find requirement drift, ambiguity, and test gaps. |
| `/specwright:write-tasks` | `$specwright:write-tasks` | Split a reviewed spec into beads epics and vertical-slice tasks with dependencies. |
| `/specwright:execute` | `$specwright:execute` | Implement beads tasks with test driven development and feedback loops. |
| `/specwright:review` | `$specwright:review` | Review implementation against spec fidelity, code quality, test quality, security, and gaps. |

## Agent compatibility

Each skill keeps Claude Code frontmatter such as `allowed-tools`, `argument-hint`,
`context`, `model`, and `disable-model-invocation`. Codex requires only `name`
and `description` in `SKILL.md`; unsupported frontmatter is kept for Claude Code
and ignored by Codex.

Codex plugin metadata lives in `.codex-plugin/plugin.json`, with skills loaded
from `./skills/`. The repo marketplace entry is in `.agents/plugins/marketplace.json`.

## License

MIT — see [LICENSE](./LICENSE).
