# gea guide: delegate

Gastá tus tokens en el plan y la revisión, no en escribir código.

1. Precondiciones: la task existe (`gea task show <ID>`), `Status: planned`,
   con `## Files` y `## Acceptance` llenos. Dentro de herdr.
2. `gea agents available` lista los builders usables (`mode ask`: preguntá
   cuál al usuario; `auto`: el primero).
3. `gea delegate <ID> [--agent <id>] [--worktree]`. Toma un checkpoint (o un
   git worktree), bloquea hasta que el builder termina e imprime un resumen
   corto: archivos cambiados, fuera de alcance, resultado del verify. No
   edites el repo mientras tanto ni leas la terminal del builder.
4. `BLOCKED` es un diálogo de confirmación: `herdr agent read <pane>
   --source recent-unwrapped --lines 40` (el nombre del pane está en la línea
   que imprimió `gea delegate`: `<3 letras del proyecto>-builder-<id>`) y decile al usuario qué aprobar.
5. Cupo o rate limit agotado: gea detecta el mensaje, marca el pool del agente
   como no disponible hasta el reinicio, cierra el pane e imprime a qué agente
   probar (`gea delegate <ID> --agent <otro>`). Ante un timeout: `gea agents
   check <id>` y elegí otro agente. Una
   corrida mala: `gea undo <ID>` restaura el checkpoint.
6. Mismos hallazgos tras dos rondas de corrección → cambiá de agente. Tras una
   corrida verificada gea cierra el pane del builder (`builders.close` en
   gea.json: `on-success`, el defecto, o `never`); las corridas fallidas quedan
   abiertas. Una ronda de corrección arranca entonces sesión nueva — el archivo
   de la task lleva el contexto.
7. Sin agentes disponibles → implementalo vos y anotalo en *Deviations*.

Siguiente: `gea guide review`.
