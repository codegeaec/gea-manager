# AGENTS.md

Reglas compartidas para los agentes de IA que trabajen en este repo,
configuradas por `gea init`. Las lee cualquier agente (Claude Code,
OpenCode, Codex CLI, agy, Kimi Code) antes de tocar código. Todo lo
específico del proyecto está al final, en `## Project`.

## Reglas duras

1. **Máximo 400 líneas por archivo.** Si un cambio genuinamente necesita
   más, se justifica en la task (`## Decisions`) en vez de partir el
   archivo de forma artificial.
2. **Reutilizar antes de crear.** Revisar `src/` (o el equivalente) antes
   de escribir un helper nuevo. Nunca duplicar un bloque de lógica en un
   segundo lugar — extraer una función compartida primero, incluso dentro
   del mismo archivo.
3. **Usar el gestor de paquetes del proyecto** (ver `## Project`). No
   generar un lockfile de otro gestor.

## Flujo de tasks

Los cambios no triviales pasan por una task antes de implementarse. Ver
`.agents/builder.md` para el ciclo implementar→revisar→cerrar, y usar `gea
task new` / `gea subtask new` / `gea delegate` para manejarlo.

## Directorios

| Ruta | Qué contiene |
|---|---|
| `.agents/` | Convenciones operativas (commits, gotchas, instrucciones del builder) |
| `docs/` | Conocimiento durable del proyecto (ver `docs/INDEX.md`) |

## Project

- Nombre: {project_name}
- Gestor de paquetes: `{pm}`
- Commits: {commit_lang}. Docs y nombres de entidades de negocio:
  {docs_lang}. Identificadores de código: inglés.
- Tasks/subtasks: `{tasks_root}`
- Autonomía: {autonomy_line}
{shadcn_section}
### Verificación

```
{verify_commands}
```
