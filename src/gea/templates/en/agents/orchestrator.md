# Orchestrator instructions

Same instructions whichever CLI is the orchestrator (Claude Code, Codex,
OpenCode, agy, Kimi Code — switch with `gea handoff --to <cli>`).

The orchestrator plans and reviews; builders implement.

- **Plan**: turn requests into durable tasks (`gea task new`, see the
  `gea-plan` skill). Fill in `## Files` and `## Acceptance` so the builder
  never has to explore.
- **Delegate**: `gea delegate <TASK-ID>`. It prints a compact summary; don't
  read the builder's terminal.
- **Review**: `gea review-pack <TASK-ID>` and read only that file, or get a
  second opinion with `gea review <TASK-ID>` (a different model).
- **Close**: `gea task done <TASK-ID>`, then commit. Undo a bad run with
  `gea undo <TASK-ID>`.
- Implement directly only for trivial changes.
