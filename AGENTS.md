# AGENTS.md — gea-manager

Reglas compartidas del proyecto que construye `gea`: el instalador y
orquestador de agentes de IA (Claude Code, OpenCode, Codex CLI, agy, Kimi
Code) sobre `herdr`. Las lee **Claude Code** (vía `CLAUDE.md`, que lo
importa) y cualquier otro agente que trabaje en este repo.

## Idioma

- **Commits: en inglés** (`lang.commits: en` en el propio `gea.json` de este
  repo — es el ejemplo real de esa opción del wizard).
- **Docs internos (`.agents/`, comentarios de dominio): español.**
- **UI del CLI (`src/gea/i18n/`): bilingüe** (es por defecto, en disponible)
  — ver `docs/` para el mecanismo de catálogos.
- Identificadores de código (variables, funciones, módulos): inglés.

## Reglas duras

1. **Máximo 400 líneas por archivo.** Si un cambio genuinamente necesita
   más, se justifica en la task (`## Decisions`) en vez de partir el archivo
   de forma artificial. Preferir dividir en módulos antes de llegar al
   límite.
2. **Sin dependencias de runtime.** `gea` corre con la librería estándar de
   Python (argparse, json, subprocess, pathlib). Dependencias de desarrollo
   (`pytest`, `ruff`) sí van en `[dependency-groups] dev`.
3. **Reutilizar antes de crear.** Antes de escribir un helper nuevo, revisar
   si ya existe algo equivalente en `src/gea/`. No duplicar lógica entre
   módulos — extraer a un helper compartido.
4. **`herdr` es la única forma de hablar con paneles de otros agentes.**
   Nunca asumir el shape exacto de su JSON sin haberlo comprobado (`herdr
   --skill` es la fuente de verdad, igual que en el proyecto Cotizaciones).
5. **Nunca hardcodear rutas de la máquina del autor.** Todo camino
   específico de usuario pasa por `src/gea/paths.py`.
6. **Nomenclatura:** archivos y módulos en `snake_case` (convención Python),
   clases en `PascalCase`, funciones/variables en `snake_case`, constantes en
   `SCREAMING_SNAKE_CASE`.
7. **Commits atómicos, sin coautor ni firma de herramienta**, formato
   [Conventional Commits](https://www.conventionalcommits.org/) en inglés
   (`feat(tasks): add subtask command`).
8. **Nunca ejecutar acciones destructivas en la máquina del usuario sin
   confirmar** (borrar configs, modificar `.bashrc`/`.zshrc`, borrar MCPs) —
   siempre con backup y una confirmación explícita salvo `--yes`.

## Estructura

| Ruta | Qué contiene |
|---|---|
| `src/gea/cli.py` | Punto de entrada, parseo de subcomandos |
| `src/gea/i18n/` | Catálogos `es.json` / `en.json` + helper `t()` |
| `src/gea/setup/` | `gea setup`: tools, shell rc, instrucciones globales, skills |
| `src/gea/agents/` | Perfiles de builder, estado de agotamiento, delegación vía herdr |
| `src/gea/tasks/` | Tasks/subtasks: store y comandos |
| `src/gea/init/` | Wizard de `gea init`, detección de stack, scaffold |
| `src/gea/templates/{es,en}/` | Plantillas de AGENTS.md, `.agents/`, docs, tasks |
| `skills/gea-*` | Skills instalables globalmente (init, plan, delegate, review) |
| `tests/` | pytest — subprocess/herdr mockeados, sin tocar la red ni la máquina real |

## Verificación

```bash
uv run ruff check .
uv run pytest
shellcheck install.sh
```

No hay `pnpm dev`/build que evitar acá (no es un proyecto Next.js) — pero sí
evitar instalar cosas de verdad en la máquina del autor al testear: los
tests mockean `subprocess.run`/`shutil.which` en vez de instalar tools reales.
