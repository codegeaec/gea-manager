@AGENTS.md

# CLAUDE.md — {project_name}

Claude-Code-specific instructions. Shared rules live in `AGENTS.md`
(imported above) and `.agents/`.

Claude Code plans: it turns requests into durable tasks under
`{tasks_root}` and reviews the diff a builder produces. Use `gea delegate
<TASK-ID>` to hand off implementation to another agent, or implement
directly for trivial changes.
