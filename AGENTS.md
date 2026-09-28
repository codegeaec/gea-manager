# AGENTS.md — gea-manager

Shared project rules for `gea`: the installer and orchestrator for AI coding
agents (Claude Code, OpenCode, Codex CLI, agy, Kimi Code) on top of `herdr`.
Read by **Claude Code** (via `CLAUDE.md`, which imports it) and any other
agent working in this repo.

## Language

- **Commits, docs (`.agents/`, this file, `CLAUDE.md`), and code
  identifiers: English.**
- **UI strings (`src/gea/i18n/`): bilingual** (Spanish by default,
  English available) — see `docs/` for the catalog mechanism. This is
  the one place Spanish is a first-class option: gea is meant to be used
  by Spanish-speaking teams by default, even though the project that
  builds it is documented in English.

## Hard rules

1. **400 lines per file, max.** If a change genuinely needs more, justify
   it in the task (`## Decisions`) instead of splitting the file
   artificially. Prefer splitting into modules before hitting the limit.
2. **No runtime dependencies.** `gea` runs on the Python standard library
   (argparse, json, subprocess, pathlib). Dev dependencies (`pytest`,
   `ruff`) belong in `[dependency-groups] dev`.
3. **Reuse before creating.** Before writing a new helper, check whether
   something equivalent already exists in `src/gea/`. Don't duplicate logic
   across modules — extract a shared helper instead.
4. **`herdr` is the only way to talk to another agent's pane.** Never
   assume the exact shape of its JSON without checking — `herdr --skill`
   is the source of truth.
5. **Never hardcode a path specific to the author's machine.** Every
   user-machine-specific path goes through `src/gea/paths.py`.
6. **Naming:** files and modules in `snake_case` (Python convention),
   classes in `PascalCase`, functions/variables in `snake_case`, constants
   in `SCREAMING_SNAKE_CASE`.
7. **Atomic commits, no co-author or tool signature**,
   [Conventional Commits](https://www.conventionalcommits.org/) format in
   English (`feat(tasks): add subtask command`).
8. **Never run a destructive action on the user's machine without
   confirming** (deleting configs, editing `.bashrc`/`.zshrc`, removing
   MCP servers) — always with a backup and explicit confirmation unless
   `--yes` was passed.

## Structure

| Path | Contents |
|---|---|
| `src/gea/cli.py` | Entry point, subcommand parsing |
| `src/gea/i18n/` | `es.json` / `en.json` catalogs + `t()` helper |
| `src/gea/setup/` | `gea setup`: tools, shell rc, global instructions, skills |
| `src/gea/agents/` | Builder profiles, exhaustion state, herdr-based delegation |
| `src/gea/tasks/` | Tasks/subtasks: store and commands |
| `src/gea/init/` | `gea init` wizard, stack detection, scaffold |
| `src/gea/templates/{es,en}/` | AGENTS.md, `.agents/`, docs, task templates |
| `src/gea/skills/gea-*` | Globally installable skills (init, plan, delegate, review) — packaged with the wheel so `gea skills sync` can install them from any machine, not just a repo checkout |
| `tests/` | pytest — subprocess/herdr mocked, never touches the network or the real machine |

## Verification

```bash
uv run ruff check .
uv run pytest
shellcheck install.sh
```

There's no `pnpm dev`/build to avoid here (not a Next.js project) — but
tests must never install anything for real on the author's machine: mock
`subprocess.run`/`shutil.which` instead of running actual installers.
