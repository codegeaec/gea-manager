# gea

`gea` es un instalador y orquestador de agentes de IA para desarrollo de
software: deja tu máquina lista (herdr, Claude Code, OpenCode, Codex CLI,
agy, Kimi Code, rtk, codegraph, shadcn CLI y herramientas de línea de
comandos) y da a cada proyecto una forma consistente de planificar,
delegar y revisar cambios con esos agentes vía `herdr`.

## Instalación

```bash
curl -fsSL https://raw.githubusercontent.com/codegeaec/gea-manager/main/install.sh | bash
```

En Windows, desde PowerShell (instala WSL2 + Ubuntu si hace falta y corre
`install.sh` adentro):

```powershell
irm https://raw.githubusercontent.com/codegeaec/gea-manager/main/install.ps1 | iex
```

## Uso

```bash
gea setup      # wizard: instala y configura todo lo necesario en esta máquina
gea doctor     # herramientas, sesión de cada agente y tamaño del contexto (no instala)
gea init       # deja un proyecto listo para trabajar con gea
gea            # abre el workspace de herdr preconfigurado
gea --help
```

`setup`, `init`, `skills sync` y `uninstall` aceptan `--dry-run`: informan qué
harían sin escribir ni instalar nada.

### Tasks y delegación

```bash
gea task new "Título" --type bugfix   # bugfix | feature | refactor | spike
gea verify --task TASK-001            # verify del proyecto + criterios de aceptación
gea delegate TASK-001                 # toma un checkpoint de git y delega al builder
gea undo TASK-001                     # vuelve al checkpoint previo a delegar
gea task done TASK-001                # cierra; su ## Decisions pasa a docs/decisions.md
gea delegate TASK-001 --worktree      # el builder trabaja en su propio git worktree
gea review-pack TASK-001              # task + diff + verify en un solo archivo
gea review TASK-001                   # revisa un modelo distinto al que implementó
gea task new --from-issue 42          # arranca la task desde un issue de GitHub
gea pr TASK-001                       # abre el PR desde la task (pide confirmación)
gea status                            # tasks activas, panes y pools agotados
gea agents stats                      # éxito y duración por agente y tier
gea handoff --to codex                # cambia de orquestador con un prompt de retoma
```

### Seguridad y mantenimiento

```bash
gea scan-secrets   # escanea el diff staged; `gea init` lo instala como hook pre-commit
gea lint           # avisa si AGENTS.md, CLAUDE.md o una skill pesan demasiado
gea uninstall      # revierte lo que setup registró (con backup y confirmación)
gea skills prune   # ofrece quitar skills que gea no instaló (cada una cuesta tokens)
```

Cada proyecto puede fijar el nivel de autonomía del builder en `gea.json`
(`"autonomy": "supervised" | "balanced" | "autonomous"`).

Ver `docs/` para el diseño completo (tasks/subtasks, delegación, i18n,
plantillas de proyecto) y `docs/commands.md` para el detalle de cada comando.

## Licencia

[MIT](LICENSE).

## Desarrollo

```bash
uv sync --group dev
uv run pytest
uv run ruff check .
```

Ver `AGENTS.md` para las reglas del repo.
