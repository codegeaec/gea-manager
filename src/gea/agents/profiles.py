"""Builder agent profiles: which CLI, which model, which quota pool.

Detected once by `gea setup`/`gea agents refresh` and stored in
`~/gea/config.json["builders"]["profiles"]` — global, not per-project,
because the same accounts (and their rate limits) are shared across every
repo on this machine. A project's `gea.json["builders"]["allow"]` can
narrow this down to a subset of ids for that project only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from gea import config, platform, proc
from gea.agents import state

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
) -> AgentProfile | None:
    """First available builder: not exhausted, allowed by the project's
    `builders.allow`, and not in `exclude_pools`. With `agent_id`, only that
    profile qualifies."""
    pools = state.load()
    allow = config.load_project(repo_root or Path.cwd()).get("builders", {}).get("allow")
    candidates = [
        p
        for p in load_profiles()
        if (not allow or p.id in allow)
        and p.pool not in exclude_pools
        and state.is_pool_available(p.pool, pools)
    ]
    if agent_id:
        return next((p for p in candidates if p.id == agent_id), None)
    return candidates[0] if candidates else None
