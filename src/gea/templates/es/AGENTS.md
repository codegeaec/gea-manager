# AGENTS.md — {project_name}

Reglas compartidas para los agentes de IA que trabajen en este repo,
configuradas por `gea init`. Las lee cualquier agente (Claude Code,
OpenCode, Codex CLI, agy, Kimi Code) antes de tocar código.

## Reglas duras

1. **Máximo 400 líneas por archivo.** Si un cambio genuinamente necesita
   más, se justifica en la task (`## Decisions`) en vez de partir el
   archivo de forma artificial.
2. **Reutilizar antes de crear.** Revisar `src/` (o el equivalente) antes
   de escribir un helper nuevo. Nunca duplicar un bloque de lógica en un
   segundo lugar — extraer una función compartida primero, incluso dentro
   del mismo archivo.
3. **Gestor de paquetes: `{pm}`, siempre.** No generar un lockfile de otro
   gestor.
{shadcn_section}
## Idioma

- Commits: {commit_lang}.
- Docs y nombres de entidades de negocio: {docs_lang}.
- Identificadores de código: inglés.

## Verificación

```
{verify_commands}
```

## Flujo de tasks

Los cambios no triviales pasan por una task en `{tasks_root}` antes de
implementarse. Ver `.agents/builder.md` para el ciclo
implementar→revisar→cerrar, y usar `gea task new` / `gea subtask new` /
`gea delegate` para manejarlo.

## Directorios

| Ruta | Qué contiene |
|---|---|
| `.agents/` | Convenciones operativas (commits, gotchas, instrucciones del builder) |
| `docs/` | Conocimiento durable del proyecto (ver `docs/INDEX.md`) |
| `{tasks_root}` | Tasks/subtasks (ver `.agents/builder.md`) |
