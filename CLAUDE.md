@AGENTS.md

# CLAUDE.md — gea-manager

Claude-Code-specific instructions for this repo. Shared rules live in
`AGENTS.md` (imported above) and `.agents/`.

Claude Code implements directly in this repo — there's no delegation
system for gea-manager yet (this repo is the product that provides one).
Once `gea init` works, this repo can self-initialize with `gea init` and
delegate like any other project from there.
