# gea guide: build (sos el builder)

Implementás una task; planificar y revisar se hace en otro lado.

1. Leé `AGENTS.md` y el archivo de la task que te dieron. Pasala a
   `in-progress`.
2. Implementá el plan tocando solo las rutas de `## Files`, reutilizando
   helpers existentes. Si el plan es ambiguo, anotalo en *Deviations* y
   tomá la lectura más razonable.
3. Verificá: `gea verify --quiet --task <ID>` (checks del proyecto +
   `## Acceptance`). Corregí lo que reporte; no corras nada más.
4. Llená *Implementation Notes* / *Deviations* (breve), actualizá `docs/` si
   cambió el comportamiento o la arquitectura y dejá la task en `review`.
5. No commitees ni marques la task como completada.
6. ¿Atascado? Reproducí, buscá la causa raíz, aplicá el fix más chico y
   anotá causa + fix en *Implementation Notes*. Mirá primero
   `.agents/gotchas.md`.
