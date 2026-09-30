"""The `agents` key of gea.json / gea.local.json: which CLI plans and which
subagents (builders) a project may delegate to, and with which models.

```json
"agents": {
  "planner": "claude", "plannerModel": "opusplan",
  "subagents": [
    "codex",                                                         # a detected profile
    {"id": "oc-kimi", "model": "opencode-go/kimi-k2.7-code"},        # override its model/pool
    {"id": "oc-lite", "cli": "opencode", "model": "opencode-go/deepseek-v4-flash"}  # custom
  ]
}
```
The list order is the delegation priority. Projects written before this key
existed (`primary`, `primaryModel`, `builders.allow`) are read as if they had it.
Pure data helpers — no I/O, so config.py can validate with them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

KNOWN_CLIS = ("claude", "codex", "opencode", "agy", "kimi")
ID_RE = re.compile(r"[a-z][a-z0-9_-]{0,31}")
DEFAULT_PLANNER = "claude"


@dataclass
class AgentsSpec:
    planner: str = DEFAULT_PLANNER
    planner_model: str | None = None
    # Entries are ids (str) or dicts; None means "every detected profile".
    subagents: list[str | dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        """The compact form written to disk (defaults omitted)."""
        out: dict[str, Any] = {}
        if self.planner != DEFAULT_PLANNER or self.planner_model or self.subagents:
            out["planner"] = self.planner
        if self.planner_model:
            out["plannerModel"] = self.planner_model
        if self.subagents:
            out["subagents"] = list(self.subagents)
        return out


def from_config(cfg: dict[str, Any]) -> AgentsSpec:
    """Normalize a merged project config, honoring the pre-`agents` keys."""
    raw = cfg.get("agents") or {}
    allow = (cfg.get("builders") or {}).get("allow") or None
    subs = raw.get("subagents") or (list(allow) if allow else None)
    return AgentsSpec(
        planner=raw.get("planner") or cfg.get("primary") or DEFAULT_PLANNER,
        planner_model=raw["plannerModel"] if "plannerModel" in raw else cfg.get("primaryModel"),
        subagents=list(subs) if subs else None,
    )


def entry_id(entry: str | dict[str, Any]) -> str:
    return entry if isinstance(entry, str) else entry.get("id", "")


def problems(value: Any) -> list[str]:
    """Human-readable problems with an `agents` value (empty = valid)."""
    if not isinstance(value, dict):
        return ["agents must be an object"]
    found = []
    planner = value.get("planner")
    if planner is not None and planner not in KNOWN_CLIS:
        found.append(f"agents.planner must be one of {', '.join(KNOWN_CLIS)}")
    model = value.get("plannerModel")
    if model is not None and not isinstance(model, str):
        found.append("agents.plannerModel must be a string")
    subs = value.get("subagents", [])
    if not isinstance(subs, list):
        return [*found, "agents.subagents must be a list"]
    seen: set[str] = set()
    for entry in subs:
        ident = entry_id(entry) if isinstance(entry, (str, dict)) else ""
        if not ID_RE.fullmatch(ident):
            found.append(f"agents.subagents: invalid id {ident!r} (use [a-z][a-z0-9_-]*)")
            continue
        if ident in seen:
            found.append(f"agents.subagents: duplicated id {ident!r}")
        seen.add(ident)
        if isinstance(entry, dict):
            found += _entry_problems(ident, entry)
    return found


def _entry_problems(ident: str, entry: dict[str, Any]) -> list[str]:
    found = []
    if entry.get("cli") is not None and entry["cli"] not in KNOWN_CLIS:
        found.append(f"agents.subagents[{ident}].cli must be one of {', '.join(KNOWN_CLIS)}")
    for key in ("model", "pool"):
        if entry.get(key) is not None and not isinstance(entry[key], str):
            found.append(f"agents.subagents[{ident}].{key} must be a string")
    return found
