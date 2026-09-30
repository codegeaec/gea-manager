# AGENTS.md

Shared rules for AI agents working in this repo, set up by `gea init`. Read
by any agent (Claude Code, OpenCode, Codex CLI, agy, Kimi Code) before
touching code. Everything project-specific is at the end, under `## Project`.

## Hard rules

1. **400 lines per file, max.** If a change genuinely needs more, justify
   it in the task (`## Decisions`) instead of splitting the file
   artificially.
2. **Reuse before creating.** Check `src/`/the equivalent for an existing
   helper before writing a new one. Never duplicate a block of logic in a
   second place — extract a shared function first, including within the
   same file.
3. **Use the project's package manager** (see `## Project`). Don't generate
   a lockfile for any other manager.

## Task workflow

Non-trivial changes go through a task before being implemented. See
`.agents/builder.md` for the implement→review→close cycle, and use `gea task
new` / `gea subtask new` / `gea delegate` to drive it. Command cheat sheet:
`.agents/gea.md`; step-by-step guides: `gea guide`.

## Directories

| Path | Contents |
|---|---|
| `.agents/` | Operational conventions (commits, gotchas, builder instructions) |
| `docs/` | Durable project knowledge (see `docs/INDEX.md`) |

## Project

- Name: {project_name}
- Package manager: `{pm}`
- Commits: {commit_lang}. Docs and business-entity names: {docs_lang}.
  Code identifiers: English.
- Tasks/subtasks: `{tasks_root}`
- Autonomy: {autonomy_line}
{shadcn_section}
### Verification

```
{verify_commands}
```
