# Instrucciones del orquestador

Las mismas instrucciones sin importar qué CLI orquesta (Claude Code, Codex,
OpenCode, agy, Kimi Code — se cambia con `gea handoff --to <cli>`).

El orquestador planifica y revisa; los builders implementan.

- **Planificar**: convertí pedidos en tasks durables (`gea task new`, ver la
  skill `gea-plan`). Llená `## Files` y `## Acceptance` para que el builder
  no tenga que explorar.
- **Delegar**: `gea delegate <TASK-ID>`. Imprime un resumen compacto; no
  leas la terminal del builder.
- **Revisar**: `gea review-pack <TASK-ID>` y leé solo ese archivo, o pedí una
  segunda opinión con `gea review <TASK-ID>` (otro modelo).
- **Cerrar**: `gea task done <TASK-ID>` y commit. Deshacé una corrida mala
  con `gea undo <TASK-ID>`.
- Implementá directo solo cambios triviales.
