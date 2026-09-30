## Trabajo con gea

Los cambios no triviales pasan por una task antes de implementarse
(`gea task new`). El orquestador planifica, delega y revisa
(`.agents/orchestrator.md`); el builder solo implementa (`.agents/builder.md`).
Cada task lleva `## Files` y `## Acceptance` llenos.

- Tasks/subtasks: `{tasks_root}`
- Autonomía: {autonomy_line}
- Verificación: `gea verify --task <TASK-ID>`{verify_note}
- Chuleta de comandos: `.agents/gea.md` · guías paso a paso: `gea guide`
