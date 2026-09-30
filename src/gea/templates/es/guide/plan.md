# gea guide: plan

Convertí un pedido en una task durable; quien implemente lee el archivo de
la task, no el chat.

1. Aterrizá el pedido: hacé solo las 2–3 preguntas que cambiarían el plan.
2. Buscá código existente primero (`docs/INDEX.md`, codegraph si existe
   `.codegraph/`). "Extender X" gana a "agregar un Y nuevo".
3. Crearla: `gea task new "<título>" [--type bugfix|feature|refactor|spike]`
   (o `--from-issue N`).
4. Completá Objective, Context, Requirements, Plan y — obligatorio antes de
   delegar — `## Files` (cada ruta que el builder puede tocar, entre
   backticks; sirven globs y directorios) y `## Acceptance` (un bullet por
   criterio; un comando entre backticks —mejor con prefijo `run:`— lo
   chequea `gea verify --task <ID>`; nombres y rutas entre backticks se
   ignoran).
5. Poné `Tier: S|M|L` (S mecánica, L delicada o transversal) y, si los 30
   min por defecto no sirven, `Budget: 45m`.
6. ¿Task grande (4+ pasos sobre archivos separables)? `gea subtask new <ID>
   "<título>" [--depends <ID>]`; subtasks sobre el mismo archivo son
   secuenciales.
7. Planificar nunca edita código fuente.

Siguiente: `gea guide delegate`.
