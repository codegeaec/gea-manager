# gea cheat sheet

Everything an agent needs to work with gea here. Lost? `gea guide` prints the
step-by-step guide (`gea guide plan|delegate|review|build`).

| Goal | Command |
|---|---|
| New task | `gea task new "<title>" [--type bugfix\|feature\|refactor\|spike] [--from-issue N]` |
| Subtask | `gea subtask new <ID> "<title>" [--depends <ID>]` |
| List / show | `gea task list [--status planned]` · `gea task show <ID>` · `gea status` |
| Check | `gea verify [--quiet] [--task <ID>]` (project checks + task `## Acceptance`) |
| Delegate | `gea delegate <ID> [--agent <id>] [--worktree]` · `gea agents available` |
| Undo a bad run | `gea undo <ID>` |
| Review | `gea review-pack <ID>` · `gea review <ID>` (different model) |
| Close | `gea task done <ID>` (its `## Decisions` go to `docs/decisions.md`) |
| Pull request | `gea pr <ID>` |
| Switch orchestrator | `gea handoff --to <cli>` |
| Health | `gea doctor` · `gea lint` |
| One agent only, no tasks or builders | `gea --only` (remembered; `gea --team` goes back to the normal flow) |

Rules of thumb: every task has `## Files` and `## Acceptance` filled in before
delegating; builders never commit; the orchestrator reads `gea review-pack`,
not the builder's terminal.
