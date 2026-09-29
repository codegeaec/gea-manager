"""Record of what `gea setup` touched, so `gea uninstall` can revert it.

Stored in `~/gea/manifest.json` as a list of `{kind, target}` entries
(deduplicated). Only reversible, config-level changes are recorded —
installed binaries (mise, herdr, agent CLIs) are never removed by gea.
"""

from __future__ import annotations

import json
from typing import Any

from gea import dryrun, paths

KIND_INSTRUCTIONS = "instructions"  # target: file holding the managed block
KIND_SKILL = "skill"  # target: skill name as `npx skills remove` expects it


def _path():
    return paths.gea_home() / "manifest.json"


def load() -> list[dict[str, str]]:
    path = _path()
    if not path.exists():
        return []
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return [e for e in data.get("entries", []) if "kind" in e and "target" in e]


def record(kind: str, target: str) -> None:
    if dryrun.active():
        return
    entries = load()
    entry = {"kind": kind, "target": target}
    if entry in entries:
        return
    entries.append(entry)
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "entries": entries}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def of_kind(kind: str) -> list[str]:
    return [e["target"] for e in load() if e["kind"] == kind]
