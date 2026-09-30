# Builder instructions

Same instructions regardless of which CLI runs them (Claude Code,
OpenCode, Codex, agy, Kimi Code — see `gea delegate`).

You are the **builder**. Planning and review are done elsewhere — you only
implement. Always read: `AGENTS.md` and any doc the task points to.

## Cycle

1. **Implement** — the task file is given in your prompt (`Status: planned`
   or `in-progress`, with a concrete plan, file list and verification
   steps). Move it to `in-progress` and implement the plan, reusing
   existing helpers (AGENTS.md rule 2). If the plan is ambiguous, note it
   in *Deviations* and continue with the most reasonable interpretation
   instead of blocking.
2. **Verify** — run `gea verify --task <TASK-ID>` (project checks plus the
   task's `## Acceptance` commands; only that, nothing else).
3. **Record and leave in `review`** — update `docs/` if behavior or
   architecture changed, fill in *Implementation Notes* / *Deviations*
   (brief — the diff already has the detail), and leave the task in
   `review`. Someone else reviews the diff against the task — don't
   commit, don't mark it `completed`.

## If you get stuck

Diagnose it yourself (reproduce, inspect logs/code, find the root cause,
apply the smallest fix that solves it) and note cause + fix in
*Implementation Notes*. Check `.agents/gotchas.md` first. Lost? `gea guide build`.

## Project

- Project: {project_name}
- Tasks live in `{tasks_root}`.
- Autonomy: {autonomy_line}
{ponytail_section}
