# gea guide: review

1. `gea review-pack <ID>` y leé solo ese archivo: la task, un diff acotado
   desde el checkpoint, resultados de verify corridos por gea, avisos de
   alcance. Nunca confíes en el autorreporte del builder; no hagas
   `git diff`/`cat` archivo por archivo.
2. Segunda opinión opcional de otro modelo: `gea review <ID>` (el revisor
   nunca es del pool del builder).
3. Verificá contra el plan y `AGENTS.md`: solo lo planeado, reutilizar antes
   de crear, límite de tamaño, nomenclatura, docs al día. Un bloque repetido
   es un hallazgo.
4. Anotá hallazgos en `## Review` de la task, uno por línea: severidad
   (`critical`/`important`/`minor`), `archivo:línea`, el fallo concreto.
5. Critical/important → arreglá los chicos vos o devolvelos al mismo builder
   (`gea delegate <ID> --agent <id>`).
6. Limpio → tildá `## Verification`, actualizá `docs/`, `gea task done <ID>`
   (su `## Decisions` pasa a `docs/decisions.md`), commit atómico
   (`.agents/commit-conventions.md`), opcional `gea pr <ID>`.

Cambiar de orquestador a mitad de camino: `gea handoff --to <cli>`.
