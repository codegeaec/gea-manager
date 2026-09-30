"""`gea agents manage` — add, remove, re-model and re-order the project's agents
without touching JSON, plus the pure edit functions the non-interactive
`gea agents add|remove|planner` commands share.

Everything is stored in the `agents` key (agents/spec.py) of `gea.local.json`
through `config.save_project`, so the key and its place are always right.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from gea import config, platform, ui
from gea.agents import models, profiles, spec
from gea.agents.profiles import AgentProfile
from gea.agents.spec import AgentsSpec
from gea.i18n import t

DEFAULT_LABEL = "(default model of the CLI)"


# --- pure edits: each returns a new AgentsSpec, or raises ValueError -----------------


def _entries(value: AgentsSpec, detected: list[AgentProfile]) -> list:
    """Subagent entries, materialising 'every detected profile' before the first edit."""
    return list(value.subagents) if value.subagents is not None else [p.id for p in detected]


def _index(entries: list, ident: str) -> int:
    for i, entry in enumerate(entries):
        if spec.entry_id(entry) == ident:
            return i
    raise ValueError(t("agents.unknown_subagent", id=ident))


def _checked(value: AgentsSpec) -> AgentsSpec:
    found = spec.problems(value.to_dict())
    if found:
        raise ValueError("; ".join(found))
    return value


def set_planner(value: AgentsSpec, cli: str, model: str | None) -> AgentsSpec:
    return _checked(replace(value, planner=cli, planner_model=model))


def add_detected(value: AgentsSpec, ident: str, detected: list[AgentProfile]) -> AgentsSpec:
    entries = _entries(value, detected)
    if ident in {spec.entry_id(e) for e in entries}:
        raise ValueError(t("agents.already_there", id=ident))
    if ident not in {p.id for p in detected}:
        raise ValueError(t("agents.not_detected", id=ident))
    return _checked(replace(value, subagents=[*entries, ident]))


def add_custom(
    value: AgentsSpec,
    ident: str,
    cli: str,
    model: str | None,
    pool: str | None,
    detected: list[AgentProfile],
) -> AgentsSpec:
    entries = _entries(value, detected)
    if ident in {spec.entry_id(e) for e in entries}:
        raise ValueError(t("agents.already_there", id=ident))
    entry = {"id": ident, "cli": cli}
    entry |= {k: v for k, v in (("model", model), ("pool", pool)) if v}
    return _checked(replace(value, subagents=[*entries, entry]))


def set_subagent_model(
    value: AgentsSpec, ident: str, model: str | None, detected: list[AgentProfile]
) -> AgentsSpec:
    """Change a subagent's model. A detected profile becomes an override (and back
    to the plain id when `model` is None); a custom entry is edited in place
    (None = the CLI's default). An override's pool is recomputed from the model."""
    entries = _entries(value, detected)
    i = _index(entries, ident)
    entry = {"id": entries[i]} if isinstance(entries[i], str) else dict(entries[i])
    if entry.get("cli"):
        entry.pop("model", None)
        entries[i] = entry | ({"model": model} if model else {})
    else:
        entries[i] = {"id": ident, "model": model} if model else ident
    return _checked(replace(value, subagents=entries))


def remove(value: AgentsSpec, ident: str, detected: list[AgentProfile]) -> AgentsSpec:
    entries = _entries(value, detected)
    del entries[_index(entries, ident)]
    return replace(value, subagents=entries or None)


def move(value: AgentsSpec, ident: str, delta: int, detected: list[AgentProfile]) -> AgentsSpec:
    entries = _entries(value, detected)
    i = _index(entries, ident)
    j = max(0, min(len(entries) - 1, i + delta))
    entries.insert(j, entries.pop(i))
    return replace(value, subagents=entries)


# --- reading -------------------------------------------------------------------------


def origin(entry: str | dict) -> str:
    if isinstance(entry, str):
        return "detected"
    return "custom" if entry.get("cli") else "override"


def describe(value: AgentsSpec, detected: list[AgentProfile]) -> list[str]:
    """One line per resolved subagent, with its origin and a warning for a model
    the CLI no longer lists."""
    cfg: dict = {}
    config.store_agents(cfg, value)
    origins = {spec.entry_id(e): origin(e) for e in (value.subagents or [])}
    lines = []
    for p in profiles.resolve_subagents(cfg, detected):
        warn = " ⚠" if p.model and models.is_known(p.cli, p.model) is False else ""
        tag = origins.get(p.id, "detected")
        lines.append(
            f"{p.id:<16} {p.cli:<9} {(p.model or DEFAULT_LABEL):<40} pool={p.pool} [{tag}]{warn}"
        )
    return lines


# --- interactive pieces (also used by the init wizard) --------------------------------


def pick_model(cli: str, default: str | None = None, assume_yes: bool = False) -> str | None:
    """A model of `cli`, chosen from the list the CLI reports (free text when it
    cannot list). None = the CLI's own default."""
    available = models.list_models(cli)
    if assume_yes:
        return default
    if available is None:
        return ui.ask_text(t("agents.model_prompt", cli=cli), default)
    labels = {str(m): m.id for m in available}
    options = [DEFAULT_LABEL, *labels]
    chosen = ui.ask_pick(
        t("agents.pick_model", cli=cli),
        options,
        default=next((str(m) for m in available if m.id == default), DEFAULT_LABEL),
        free_text=True,
    )
    if chosen in (None, DEFAULT_LABEL):
        return None
    model = labels.get(chosen, chosen)
    if models.is_known(cli, model) is False:
        ui.warn(t("agents.model_unknown", model=model, cli=cli))
    return model


def installed_clis() -> list[str]:
    return [c for c in spec.KNOWN_CLIS if platform.which(c)]


def suggest_id(cli: str, model: str | None) -> str:
    slug = (model or "default").split("/")[-1].lower()
    slug = "".join(ch if ch.isalnum() else "-" for ch in slug).strip("-")
    return f"{cli}-{slug}"[:32].rstrip("-_")


def prompt_custom(value: AgentsSpec, detected: list[AgentProfile]) -> AgentsSpec | None:
    """Ask for one custom subagent (a CLI + model of the user's choice)."""
    clis = installed_clis()
    if not clis:
        ui.warn(t("agents.no_clis"))
        return None
    cli = clis[ui.ask_choice(t("agents.pick_cli"), clis)]
    model = pick_model(cli)
    ident = ui.ask_text(t("agents.id_prompt"), suggest_id(cli, model))
    pool = profiles.default_pool(cli, model)
    ui.info(t("agents.pool_note", pool=pool))
    pool = ui.ask_text(t("agents.pool_prompt"), pool)
    try:
        return add_custom(value, ident or suggest_id(cli, model), cli, model, pool, detected)
    except ValueError as exc:
        ui.err(str(exc))
        return None


def prompt_planner(value: AgentsSpec, assume_yes: bool = False) -> AgentsSpec:
    clis = installed_clis() or [value.planner]
    default = clis.index(value.planner) if value.planner in clis else 0
    cli = clis[ui.ask_choice(t("agents.pick_planner"), clis, default, assume_yes)]
    suggestion = "opusplan" if cli == "claude" else None
    keep = value.planner_model if cli == value.planner and value.planner_model else suggestion
    return set_planner(value, cli, pick_model(cli, keep, assume_yes))


# --- the menu ------------------------------------------------------------------------


def _choose(question: str, ids: list[str]) -> str | None:
    if not ids:
        ui.warn(t("agents.nothing_to_pick"))
        return None
    index = ui.ask_choice(question, ids)
    return ids[index]


def run_manage() -> int:
    root = Path.cwd()
    cfg = config.load_project(root)
    value = config.agents(cfg)
    detected = profiles.load_profiles() or profiles.refresh_and_save()
    while True:
        ui.info(t("agents.header", project=root.name, planner=value.planner,
                  model=value.planner_model or DEFAULT_LABEL))
        for line in describe(value, detected) or [t("agents.none")]:
            print(f"  {line}")
        print(t("agents.menu"))
        key = input("> ").strip().lower()
        try:
            if key == "p":
                value = prompt_planner(value)
            elif key == "a":
                value = _add(value, detected)
            elif key == "m":
                ident = _choose(t("agents.which"), [p.id for p in _resolved(value, detected)])
                if ident:
                    cli = next(p.cli for p in _resolved(value, detected) if p.id == ident)
                    value = set_subagent_model(value, ident, pick_model(cli), detected)
            elif key in ("r", "o"):
                ident = _choose(t("agents.which"), [p.id for p in _resolved(value, detected)])
                if ident and key == "r":
                    value = remove(value, ident, detected)
                elif ident:
                    step = -1 if input(t("agents.up_or_down")).strip().lower() == "u" else 1
                    value = move(value, ident, step, detected)
            elif key == "q":
                config.store_agents(cfg, value)
                config.save_project(root, cfg)
                ui.ok(t("agents.saved"))
                return 0
            elif key == "x":
                ui.warn(t("common.aborted"))
                return 1
        except ValueError as exc:
            ui.err(str(exc))


def _resolved(value: AgentsSpec, detected: list[AgentProfile]) -> list[AgentProfile]:
    cfg: dict = {}
    config.store_agents(cfg, value)
    return profiles.resolve_subagents(cfg, detected)


def _add(value: AgentsSpec, detected: list[AgentProfile]) -> AgentsSpec:
    have = {p.id for p in _resolved(value, detected)}
    missing = [p.id for p in detected if p.id not in have]
    custom = t("agents.custom_option")
    choice = ui.ask_pick(t("agents.add_which"), [*missing, custom], default=custom)
    if choice == custom:
        return prompt_custom(value, detected) or value
    return add_detected(value, choice, detected) if choice else value
