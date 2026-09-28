@AGENTS.md

# CLAUDE.md — {project_name}

Instrucciones específicas de Claude Code. Las reglas compartidas viven en
`AGENTS.md` (importado arriba) y `.agents/`.

Claude Code planifica: convierte pedidos en tasks durables bajo
`{tasks_root}` y revisa el diff que produce un builder. Usar `gea delegate
<TASK-ID>` para delegar la implementación a otro agente, o implementar
directo para cambios triviales.
