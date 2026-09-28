# AGENTS.md — {project_name}

Shared rules for AI agents working in this repo, set up by `gea init`. Read
by any agent (Claude Code, OpenCode, Codex CLI, agy, Kimi Code) before
touching code.

## Hard rules

1. **400 lines per file, max.** If a change genuinely needs more, justify
   it in the task (`## Decisions`) instead of splitting the file
   artificially.
2. **Reuse before creating.** Check `src/`/the equivalent for an existing
   helper before writing a new one. Never duplicate a block of logic in a
   second place — extract a shared function first, including within the
   same file.
3. **Package manager: `{pm}`, always.** Don't generate a lockfile for any
   other manager.
{shadcn_section}
## Language

- Commits: {commit_lang}.
- Docs and business-entity names: {docs_lang}.
- Code identifiers: English.

## Verification

```
{verify_commands}
```

## Task workflow

Non-trivial changes go through a task in `{tasks_root}` before being
implemented. See `.agents/builder.md` for the implement→review→close cycle,
and use `gea task new` / `gea subtask new` / `gea delegate` to drive it.

## Directories

| Path | Contents |
|---|---|
| `.agents/` | Operational conventions (commits, gotchas, builder instructions) |
| `docs/` | Durable project knowledge (see `docs/INDEX.md`) |
| `{tasks_root}` | Tasks/subtasks (see `.agents/builder.md`) |
