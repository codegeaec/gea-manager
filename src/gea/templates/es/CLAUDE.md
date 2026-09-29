@AGENTS.md

# CLAUDE.md

Instrucciones específicas de Claude Code. Las reglas compartidas viven en
`AGENTS.md` (importado arriba) y `.agents/`.

Claude Code planifica: convierte pedidos en tasks durables (`gea task
new`) y revisa el diff que produce un builder. Usar `gea delegate
<TASK-ID>` para delegar la implementación a otro agente, o implementar
directo para cambios triviales.

## Project

- Nombre: {project_name}
- Las tasks viven en `{tasks_root}`.
