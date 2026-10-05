Modo `gea --only`: trabajas solo, sin builders. Esto reemplaza a `.agents/orchestrator.md` y al "Flujo de tasks" de AGENTS.md.
- Implementa directo. No uses `gea task`, `gea delegate`, `gea review-pack`, `gea review` ni las skills gea-plan, gea-delegate y gea-review, salvo que el usuario lo pida (p. ej. trabajo de varias sesiones).
- Para cambios grandes usa tu propio modo plan / lista de tareas.
- Al terminar verifica con `gea verify --quiet`. Las reglas duras de AGENTS.md siguen vigentes.
