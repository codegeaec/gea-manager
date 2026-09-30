"""Models each agent CLI can run, read from the CLI itself (so a retired or new
model shows up without gea changing). Verified against the CLIs' own commands:

- opencode: `opencode models [provider]` -> `provider/model` per line
- agy: `agy models` -> `id<TAB>name` per line (plus a "Fetching..." notice)
- codex: `codex debug models` -> JSON, models with `visibility: list`
- claude: no listing command -> its aliases (any full model name also works)
- kimi: unknown -> None (the caller asks for free text)
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from gea import proc

CLAUDE_ALIASES = (
    ("opusplan", "Opus for planning, Sonnet for execution"),
    ("opus", "latest Opus"),
    ("sonnet", "latest Sonnet"),
    ("haiku", "latest Haiku"),
)


@dataclass(frozen=True)
class Model:
    id: str
    label: str = ""

    def __str__(self) -> str:
        has_label = self.label and self.label != self.id
        return f"{self.id}  {self.label}" if has_label else self.id


_cache: dict[str, list[Model] | None] = {}


def _opencode() -> list[Model] | None:
    out, _err, code = proc.run(["opencode", "models"], timeout=60)
    lines = (line.strip() for line in out.splitlines())
    models = [Model(line) for line in lines if "/" in line and " " not in line]
    return models if code == 0 and models else None


def _agy() -> list[Model] | None:
    out, _err, code = proc.run(["agy", "models"], timeout=60)
    models = []
    for line in out.splitlines():
        ident, sep, label = line.partition("\t")
        if sep and ident.strip():
            models.append(Model(ident.strip(), label.strip()))
    return models if code == 0 and models else None


def _codex() -> list[Model] | None:
    out, _err, code = proc.run(["codex", "debug", "models"], timeout=60)
    try:
        listed = json.loads(out).get("models", [])
    except (json.JSONDecodeError, AttributeError):
        return None
    models = [
        Model(m["slug"], m.get("display_name", ""))
        for m in listed
        if isinstance(m, dict) and m.get("visibility") == "list" and m.get("slug")
    ]
    return models if code == 0 and models else None


def _claude() -> list[Model]:
    return [Model(ident, label) for ident, label in CLAUDE_ALIASES]


LISTERS = {"opencode": _opencode, "agy": _agy, "codex": _codex, "claude": _claude}


def list_models(cli: str, refresh: bool = False) -> list[Model] | None:
    """The models `cli` reports, or None when it cannot list them."""
    if refresh or cli not in _cache:
        lister = LISTERS.get(cli)
        _cache[cli] = lister() if lister else None
    return _cache[cli]


def is_known(cli: str, model: str) -> bool | None:
    """True/False against the CLI's list; None when the CLI cannot list (or for
    claude, where any full model name is valid besides the aliases)."""
    if cli == "claude":
        return None
    models = list_models(cli)
    return None if models is None else any(m.id == model for m in models)
