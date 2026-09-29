@AGENTS.md

# CLAUDE.md

Claude-Code-specific instructions. Shared rules live in `AGENTS.md`
(imported above) and `.agents/`.

Claude Code plans: it turns requests into durable tasks (`gea task new`)
and reviews the diff a builder produces. Use `gea delegate <TASK-ID>` to
hand off implementation to another agent, or implement directly for
trivial changes.

## Project

- Name: {project_name}
- Tasks live in `{tasks_root}`.
