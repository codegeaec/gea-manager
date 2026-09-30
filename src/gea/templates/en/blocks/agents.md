## Working with gea

Non-trivial changes go through a task before being implemented
(`gea task new`). The orchestrator plans, delegates and reviews
(`.agents/orchestrator.md`); the builder only implements (`.agents/builder.md`).
Each task carries `## Files` and `## Acceptance` filled in.

- Tasks/subtasks: `{tasks_root}`
- Autonomy: {autonomy_line}
- Verification: `gea verify --task <TASK-ID>`{verify_note}
