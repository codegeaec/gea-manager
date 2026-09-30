## Trabajo con gea

Este proyecto está preparado para [gea](https://github.com/codegeaec/gea-manager),
que orquesta agentes de IA para programar.

- Una vez por máquina: instalar gea y correr `gea setup`.
- Una vez por proyecto: `gea init` (ya hecho aquí).
- Flujo: `gea task new` → `gea delegate <ID>` → `gea review-pack <ID>` →
  `gea task done <ID>`.
- Las tasks viven en `{tasks_root}`. Agentes: `AGENTS.md`, `.agents/gea.md`
  (chuleta de comandos) y `gea guide` (guías paso a paso).
