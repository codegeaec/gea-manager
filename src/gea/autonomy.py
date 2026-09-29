"""Autonomy levels (`gea.json["autonomy"]`): how much freedom a builder
gets. Read by the scaffold templates (AGENTS.md, builder.md) and by the
delegator, which appends the *current* level to every builder prompt so a
later edit of gea.json takes effect without re-running `gea init`.
"""

from __future__ import annotations

from gea import config

DESCRIPTIONS = {
    "en": {
        "supervised": "supervised — stop and ask before anything not spelled out in the task "
        "(new files, dependencies, refactors, deviations).",
        "balanced": "balanced — follow the plan; note small deviations in *Deviations* "
        "and ask only when blocked.",
        "autonomous": "autonomous — never stop to ask; choose the most reasonable "
        "interpretation, fix adjacent breakage, and record decisions in *Decisions*.",
    },
    "es": {
        "supervised": "supervisada — detenete y preguntá antes de cualquier cosa que la task "
        "no diga explícitamente (archivos nuevos, dependencias, refactors, desvíos).",
        "balanced": "equilibrada — seguí el plan; anotá desvíos chicos en *Deviations* "
        "y preguntá solo si te bloqueás.",
        "autonomous": "autónoma — no te detengas a preguntar; elegí la interpretación más "
        "razonable, arreglá lo adyacente que rompas y registrá decisiones en *Decisions*.",
    },
}


def describe(level: str | None, lang: str = "en") -> str:
    level = level if level in config.AUTONOMY_LEVELS else config.DEFAULT_AUTONOMY
    table = DESCRIPTIONS.get(lang, DESCRIPTIONS["en"])
    return table[level]
