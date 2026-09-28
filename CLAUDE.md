@AGENTS.md

# CLAUDE.md — gea-manager

Instrucciones específicas de Claude Code para este repo. Las reglas
compartidas viven en `AGENTS.md` (importado arriba) y `.agents/`.

A diferencia de Cotizaciones, en **este** repo Claude Code sí implementa
directamente — todavía no existe un sistema de delegación para gea-manager
(es el propio producto que lo provee). Cuando `gea init` funcione, este
mismo repo se autoinicializa con `gea init` y desde ahí puede delegar como
cualquier otro proyecto.
