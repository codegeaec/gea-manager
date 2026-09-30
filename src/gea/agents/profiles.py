"""Builder agent profiles: which CLI, which model, which quota pool.

Detected once by `gea setup`/`gea agents refresh` and stored in
`~/gea/config.json["builders"]["profiles"]` — global, not per-project,
because the same accounts (and their rate limits) are shared across every
repo on this machine. A project's `gea.json["builders"]["allow"]` can
narrow this down to a subset of ids for that project only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path

from gea import config, platform, proc
from gea.agents import log, state

# Profiles are listed cheapest-first: with no history, delegation follows
# `priority` (see pick_agent / rank_for_tier).
# Known cloud profiles behind a single CLI — mirrors what a real install
# would report via `opencode models`, kept as a static fallback so
# detection still works offline/in tests.
OPENCODE_PROFILES = [
    {"id": "oc-kimi", "model": "opencode-go/kimi-k2.7-code", "pool": "opencode-go", "priority": 1},
    {"id": "oc-grok", "model": "opencode-go/grok-4.7", "pool": "opencode-go", "priority": 2},
    {
        "id": "oc-deepseek",
        "model": "opencode-go/deepseek-v4-pro",
        "pool": "opencode-go",
        "priority": 3,
    },
]
AGY_PROFILES = [
    {"id": "agy", "cli": "agy", "model": None, "pool": "agy-gemini", "priority": 10},
    {
        "id": "agy-claude",
        "cli": "agy",
        "model": "claude-sonnet-4-6",
        "pool": "agy-claude",
        "priority": 10.5,
    },
    {
        "id": "agy-gpt-oss",
        "cli": "agy",
        "model": "gpt-oss-120b-medium",
        "pool": "agy-gpt-oss",
        "priority": 10.7,
    },
]
# agy exposes no quota command (`agy models` only lists models), so each
# model family gets its own pool and exhaustion is detected from the pane
# output like every other CLI (agents/state.py). The Gemini profile has no
# pinned model: it runs agy's default.


@dataclass
class AgentProfile:
    id: str
    cli: str
    model: str | None
    pool: str
    priority: float

    def to_dict(self) -> dict:
        return asdict(self)


def detect_profiles() -> list[AgentProfile]:
    detected: list[AgentProfile] = []

    if platform.which("opencode"):
        models_out, _err, _code = proc.run(["opencode", "models"])
        for profile in OPENCODE_PROFILES:
            if not models_out or profile["model"] in models_out:
                detected.append(
                    AgentProfile(
                        id=profile["id"],
                        cli="opencode",
                        model=profile["model"],
                        pool=profile["pool"],
                        priority=profile["priority"],
                    )
                )

    if platform.which("agy"):
        models_out, _err, _code = proc.run(["agy", "models"])
        for profile in AGY_PROFILES:
            if profile["model"] and models_out and profile["model"] not in models_out:
                continue
            detected.append(
                AgentProfile(
                    id=profile["id"],
                    cli="agy",
                    model=profile["model"],
                    pool=profile["pool"],
                    priority=profile["priority"],
                )
            )

    if platform.which("codex"):
        detected.append(
            AgentProfile(id="codex", cli="codex", model=None, pool="codex", priority=11)
        )

    if platform.which("kimi"):
        detected.append(
            AgentProfile(id="kimi", cli="kimi", model=None, pool="kimi", priority=12)
        )

    return sorted(detected, key=lambda p: p.priority)


def refresh_and_save() -> list[AgentProfile]:
    profiles = detect_profiles()
    cfg = config.load_global()
    cfg.setdefault("builders", {})["profiles"] = [p.to_dict() for p in profiles]
    config.save_global(cfg)
    return profiles


def load_profiles() -> list[AgentProfile]:
    cfg = config.load_global()
    raw = cfg.get("builders", {}).get("profiles", [])
    return [AgentProfile(**p) for p in raw]


def pick_agent(
    agent_id: str | None = None,
    exclude_pools: tuple[str, ...] | list[str] = (),
    repo_root: Path | None = None,
    tier: str | None = None,
) -> AgentProfile | None:
    """First available builder: one of the project's subagents (`agents.subagents`,
    in priority order), not exhausted, and not in `exclude_pools`. With `agent_id`,
    only that profile qualifies."""
    pools = state.load()
    cfg = config.load_project(repo_root or Path.cwd())
    builders = cfg.get("builders", {})
    candidates = [
        p
        for p in resolve_subagents(cfg)
        if p.pool not in exclude_pools and state.is_pool_available(p.pool, pools)
    ]
    if agent_id:
        return next((p for p in candidates if p.id == agent_id), None)
    if tier:
        candidates = rank_for_tier(candidates, tier, builders.get("tiers", {}).get(tier))
    return candidates[0] if candidates else None


MIN_ATTEMPTS_TO_RANK = 5


def rank_for_tier(
    candidates: list[AgentProfile], tier: str, forced: list[str] | None = None
) -> list[AgentProfile]:
    """Order candidates for a task tier.

    `builders.tiers[tier]` in gea.json (a list of ids) restricts and orders
    them outright. Otherwise the priority order stands, except that agents
    with at least MIN_ATTEMPTS_TO_RANK logged builds in this tier are ranked
    by their verified success rate; agents with less history count as 0.5,
    so a proven-bad agent sinks and a proven-good one rises.
    """
    if forced:
        by_id = {p.id: p for p in candidates}
        return [by_id[i] for i in forced if i in by_id]
    builds = [
        e for e in log.read(tier=tier) if e.get("kind", "build") == "build"
    ]

    def score(p: AgentProfile) -> float:
        mine = [e for e in builds if e.get("agent_id") == p.id]
        if len(mine) < MIN_ATTEMPTS_TO_RANK:
            return 0.5
        return sum(1 for e in mine if e.get("result") == "done" and e.get("verify_ok")) / len(mine)

    return sorted(candidates, key=lambda p: -score(p))


# agy serves several model families with separate quotas (see AGY_PROFILES).
AGY_FAMILY_POOLS = (("gemini", "agy-gemini"), ("claude", "agy-claude"), ("gpt-oss", "agy-gpt-oss"))


def default_pool(cli: str, model: str | None) -> str:
    """The quota pool a custom subagent falls into when none is given: models
    behind one provider/account share a quota, so `opencode-go/x` -> `opencode-go`."""
    if cli == "agy":
        for prefix, pool in AGY_FAMILY_POOLS:
            if model and model.startswith(prefix):
                return pool
        return "agy-gemini"  # agy's own default model
    if model and "/" in model:
        return model.split("/", 1)[0]
    return cli


def resolve_subagents(
    cfg: dict, detected: list[AgentProfile] | None = None
) -> list[AgentProfile]:
    """The project's subagents as profiles, in priority order (list position).

    Entries of `agents.subagents`: an id of a detected profile; a dict with such an
    id and no `cli` (overrides its model/pool); or a dict with `cli` (custom).
    No list at all means every detected profile. Unknown ids are skipped (see
    `unknown_subagent_ids`)."""
    detected = load_profiles() if detected is None else detected
    entries = config.agents(cfg).subagents
    if not entries:
        return list(detected)
    by_id = {p.id: p for p in detected}
    resolved = []
    for position, entry in enumerate(entries, start=1):
        item = {"id": entry} if isinstance(entry, str) else entry
        base = by_id.get(item["id"])
        if item.get("cli"):  # custom (it may reuse a detected id: then it replaces it)
            model = item.get("model")
            pool = item.get("pool") or default_pool(item["cli"], model)
            resolved.append(AgentProfile(item["id"], item["cli"], model, pool, position))
        elif base:
            model = item.get("model", base.model)
            pool = item.get("pool") or (
                default_pool(base.cli, model) if model != base.model else base.pool
            )
            resolved.append(replace(base, model=model, pool=pool, priority=position))
    return resolved


def unknown_subagent_ids(cfg: dict, detected: list[AgentProfile] | None = None) -> list[str]:
    """Ids in `agents.subagents` that match no detected profile and define no `cli`."""
    detected = load_profiles() if detected is None else detected
    known = {p.id for p in detected}
    return [
        item["id"]
        for entry in (config.agents(cfg).subagents or [])
        if not (item := {"id": entry} if isinstance(entry, str) else entry).get("cli")
        and item["id"] not in known
    ]
