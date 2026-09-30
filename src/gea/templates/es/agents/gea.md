# Chuleta de gea

Todo lo que un agente necesita para trabajar con gea aquí. ¿Perdido? `gea
guide` imprime la guía paso a paso (`gea guide plan|delegate|review|build`).

| Objetivo | Comando |
|---|---|
| Nueva task | `gea task new "<título>" [--type bugfix\|feature\|refactor\|spike] [--from-issue N]` |
| Subtask | `gea subtask new <ID> "<título>" [--depends <ID>]` |
| Listar / ver | `gea task list [--status planned]` · `gea task show <ID>` · `gea status` |
| Verificar | `gea verify [--quiet] [--task <ID>]` (checks del proyecto + `## Acceptance`) |
| Delegar | `gea delegate <ID> [--agent <id>] [--worktree]` · `gea agents available` |
| Deshacer una corrida mala | `gea undo <ID>` |
| Revisar | `gea review-pack <ID>` · `gea review <ID>` (otro modelo) |
| Cerrar | `gea task done <ID>` (su `## Decisions` pasa a `docs/decisions.md`) |
| Pull request | `gea pr <ID>` |
| Cambiar de orquestador | `gea handoff --to <cli>` |
| Salud | `gea doctor` · `gea lint` |

Reglas de oro: toda task lleva `## Files` y `## Acceptance` llenos antes de
delegar; los builders no commitean; el orquestador lee `gea review-pack`, no
la terminal del builder.
