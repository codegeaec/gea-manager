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
gea doctor     # verifica sin instalar
gea init       # deja un proyecto listo para trabajar con gea
gea            # abre el workspace de herdr preconfigurado
gea --help
```

Ver `docs/` para el diseño completo (tasks/subtasks, delegación, i18n,
plantillas de proyecto).

## Desarrollo

```bash
uv sync --group dev
uv run pytest
uv run ruff check .
```

Ver `AGENTS.md` para las reglas del repo.
