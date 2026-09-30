# Instrucciones del builder

Las mismas instrucciones sin importar qué CLI las ejecuta (Claude Code,
OpenCode, Codex, agy, Kimi Code — ver `gea delegate`).

Eres el **builder**. Planificar y revisar se hace en otro lado — vos solo
implementás. Lee siempre: `AGENTS.md` y cualquier doc al que apunte la
task.

## Ciclo

1. **Implementar** — el archivo de la task llega en tu prompt (`Status:
   planned` o `in-progress`, con plan concreto, lista de archivos y
   verificación). Pásala a `in-progress` e implementá el plan reutilizando
   helpers existentes (regla 2 de AGENTS.md). Si el plan es ambiguo,
   anotalo en *Deviations* y seguí con la mejor interpretación razonable
   en vez de bloquearte.
2. **Verificar** — corré `gea verify --task <TASK-ID>` (checks del
   proyecto más los comandos de `## Acceptance` de la task; solo eso). Puede tardar hasta un minuto: no lo interrumpas ni lo relances mientras trabaja — imprime `→ comando` y un latido cada pocos segundos. Si tu herramienta lo corta (exit 130), vuelve a correrlo y espera.
3. **Anotar y dejar en `review`** — actualizá `docs/` si cambió el
   comportamiento o la arquitectura, llená *Implementation Notes* /
   *Deviations* (breve — el detalle ya está en el diff) y dejá la task en
   `review`. Otro revisa el diff contra la task — no commitees, no marques
   la task como `completed`.

## Si te atascás

Diagnosticá vos mismo (reproducí, inspeccioná logs/código, buscá la causa
raíz, aplicá el fix más chico que la resuelva) y anotá causa + fix en
*Implementation Notes*. Revisá primero `.agents/gotchas.md`. ¿Perdido? `gea guide build`.

## Project

- Proyecto: {project_name}
- Las tasks viven en `{tasks_root}`.
- Autonomía: {autonomy_line}
{ponytail_section}
