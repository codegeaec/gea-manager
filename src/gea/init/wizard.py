"""`gea init` — interactive wizard that leaves a repo ready to work with
gea: gea.json, AGENTS.md/CLAUDE.md, .agents/, docs/, .claude/settings.json,
.gitignore, and (if available) codegraph.
"""

from __future__ import annotations

from pathlib import Path

from gea import config, doctor, dryrun, platform, proc, secrets, ui
from gea.agents import manage, spec
from gea.agents.profiles import load_profiles, refresh_and_save
from gea.i18n import t
from gea.init import detect, report, scaffold
from gea.init import inspect as inspect_mod
from gea.tasks import importer, store


def _tasks_root_display(cfg: dict) -> str:
    return str(store.task_root(Path.cwd())) if cfg else ""


def _pick_tasks_location(assume_yes: bool = False) -> str:
    choice = ui.ask_choice(
        "Where should tasks/subtasks live?",
        ["~/gea/projects/<name> (home)", ".gea/ versioned in the repo (repo)"],
        default_index=0,
        assume_yes=assume_yes,
    )
    return "home" if choice == 0 else "repo"


LANGS = ("es", "en")


def _pick_lang(
    question: str, default: str, forced: str | None = None, assume_yes: bool = False
) -> str:
    if forced:
        return forced
    choice = ui.ask_choice(
        question, ["Spanish", "English"], default_index=LANGS.index(default), assume_yes=assume_yes
    )
    return LANGS[choice]


def _pick_langs(
    forced: tuple[str | None, str | None, str | None] = (None, None, None),
    assume_yes: bool = False,
) -> tuple[str, str, str]:
    """(agents, docs, commits): one question each, each defaulting to the
    previous answer so accepting every default gives a single language."""
    agents = _pick_lang(
        "Language of the agent instructions (AGENTS.md, CLAUDE.md, .agents/)",
        "es", forced[0], assume_yes,
    )
    docs = _pick_lang(
        "Language of the documents (docs/, task templates)", agents, forced[1], assume_yes
    )
    commits = _pick_lang("Language of commit messages", docs, forced[2], assume_yes)
    return agents, docs, commits


def _pick_autonomy(assume_yes: bool = False) -> str:
    levels = list(config.AUTONOMY_LEVELS)
    choice = ui.ask_choice(
        "Builder autonomy (supervised = asks first, autonomous = never asks)",
        levels,
        default_index=levels.index(config.DEFAULT_AUTONOMY),
        assume_yes=assume_yes,
    )
    return levels[choice]


def _pick_agents(detected, assume_yes: bool = False) -> spec.AgentsSpec:
    """Planner (+ its model) and subagents, with the same prompts `gea agents
    manage` uses: models come from the CLIs' own lists."""
    value = manage.prompt_planner(spec.AgentsSpec(), assume_yes)
    if not detected:
        return value
    labels = [f"{p.id} ({p.cli}{' ' + p.model if p.model else ''})" for p in detected]
    picked = ui.ask_multi(
        "Subagents this project may delegate to (comma-separated, empty = all detected)",
        labels,
        assume_yes=assume_yes,
    )
    chosen = [detected[i].id for i in picked] or [p.id for p in detected]
    if len(chosen) < len(detected):
        value = spec.AgentsSpec(value.planner, value.planner_model, chosen)
    while not assume_yes and ui.ask_yes_no(
        "Add a custom subagent (another model of an installed CLI)?", default=False
    ):
        value = manage.prompt_custom(value, detected) or value
    return value


def _warn_missing_tools() -> None:
    result = doctor.run_doctor()
    if result.missing_required:
        ui.warn(t("init.warn_missing_tools", tools=", ".join(result.missing_required)))


def run_init(
    dry_run: bool = False,
    assume_yes: bool = False,
    langs: tuple[str | None, str | None, str | None] = (None, None, None),
) -> int:
    dryrun.enable(dry_run)
    repo_root = Path.cwd()

    if not (repo_root / ".git").exists():
        if ui.ask_yes_no("No git repo here — run `git init`?", default=True, assume_yes=assume_yes):
            if dry_run:
                dryrun.report("run: git init")
            else:
                proc.run(["git", "init"], timeout=15)
        else:
            ui.err("gea init needs a git repository")
            return 1

    _warn_missing_tools()
    state = inspect_mod.inspect(repo_root)
    report.print_report(state)

    project_name = repo_root.name
    tasks_location = _pick_tasks_location(assume_yes)
    agents_lang, docs_lang, commit_lang = _pick_langs(langs, assume_yes)
    autonomy = _pick_autonomy(assume_yes)
    ponytail = bool(config.load_global().get("optional", {}).get("ponytail", True))

    pm = detect.detect_pm(repo_root)
    if pm:
        ui.ok(f"package manager detected: {pm}")
    else:
        pm = "npm"

    has_shadcn = detect.has_shadcn(repo_root)
    verify_commands = detect.detect_verify_commands(repo_root, pm)
    if verify_commands:
        ui.info("Detected verify commands:")
        for cmd in verify_commands:
            print(f"  {cmd}")
        if not ui.ask_yes_no("Use these?", default=True, assume_yes=assume_yes):
            verify_commands = []

    agents_spec = _pick_agents(load_profiles() or refresh_and_save(), assume_yes)

    cfg = config.DEFAULT_PROJECT_CONFIG.copy()
    cfg.update(
        {
            "name": project_name,
            "tasks": {"location": tasks_location},
            "verify": verify_commands,
            "builders": {"mode": "ask", "ponytail": ponytail},
            "autonomy": autonomy,
            "lang": {"agents": agents_lang, "commits": commit_lang, "docs": docs_lang},
            "pm": pm,
        }
    )
    config.store_agents(cfg, agents_spec)
    config.save_project(repo_root, cfg)
    ui.ok("gea.json written")

    tasks_root_display = _tasks_root_display(cfg)

    action = scaffold.ensure_agents_md(
        repo_root,
        lang=agents_lang,
        project_name=project_name,
        pm=pm,
        commit_lang=commit_lang,
        docs_lang=docs_lang,
        verify_commands=verify_commands,
        tasks_root_display=tasks_root_display,
        has_shadcn=has_shadcn,
        autonomy=autonomy,
    )
    if action != "unchanged":
        ui.ok(f"AGENTS.md {action}")

    if platform.which("claude"):
        action = scaffold.ensure_claude_md(repo_root, agents_lang, project_name, tasks_root_display)
        if action != "unchanged":
            ui.ok(f"CLAUDE.md {action}")
        if scaffold.merge_claude_settings(repo_root):
            ui.ok(".claude/settings.json written")

    written = scaffold.write_agents_dir(
        repo_root,
        agents_lang,
        project_name,
        commit_lang,
        cfg["builders"]["ponytail"],
        tasks_root_display,
        autonomy,
    )
    for path in written:
        ui.ok(f"{path} written")

    clis = [c for c in scaffold.COMMAND_DIRS if platform.which(c)]
    if clis and ui.ask_yes_no(
        f"Add /gea-plan, /gea-delegate, /gea-review slash commands for {', '.join(clis)}?",
        default=True,
        assume_yes=assume_yes,
    ):
        for path in scaffold.write_slash_commands(repo_root, agents_lang, clis):
            ui.ok(f"{path} written")
    readme = scaffold.ensure_readme(repo_root, agents_lang, project_name, tasks_root_display)
    if readme != "unchanged":
        ui.ok(f"README.md {readme}")

    if not state.has_docs and ui.ask_yes_no(
        "Set up a docs/ system (INDEX.md, vision, ADR template)?",
        default=True,
        assume_yes=assume_yes,
    ):
        written_docs = scaffold.write_docs(repo_root, docs_lang, project_name)
        for path in written_docs:
            ui.ok(f"{path} written")

    if scaffold.update_gitignore(repo_root, tasks_location):
        ui.ok(".gitignore updated")
    if scaffold.gitignore_has_gea_json(repo_root) and ui.ask_yes_no(
        "gea.json is gitignored. Commit it as the team's shared policy "
        "(personal choices live in gea.local.json)?",
        default=True,
        assume_yes=assume_yes,
    ):
        scaffold.stop_ignoring_gea_json(repo_root)
        ui.ok("gea.json is no longer ignored — commit it")

    if tasks_location == "home":
        _ensure_gea_symlink(repo_root, project_name)

    hook = secrets.install_hook(repo_root)
    if hook == "installed":
        ui.ok("pre-commit secret scan installed")
    elif hook == "skipped":
        ui.warn("a pre-commit hook already exists — add `gea scan-secrets` to it yourself")

    should_run_codegraph = platform.which("codegraph") and ui.ask_yes_no(
        "Run `codegraph init` for this project?", default=True, assume_yes=assume_yes
    )
    if should_run_codegraph:
        if dry_run:
            dryrun.report("run: codegraph init")
        else:
            proc.run(["codegraph", "init"], timeout=60)
            ui.ok("codegraph initialized")

    for layout in state.task_layouts:
        if ui.ask_yes_no(t("init.offer_import"), default=True, assume_yes=assume_yes):
            importer.import_layout(layout, repo_root)

    ui.info(t("init.builders_hint"))
    ui.info(t("init.agents_hint"))
    ui.ok("gea init complete")
    return 0


def _ensure_gea_symlink(repo_root: Path, project_name: str) -> None:
    from gea import paths

    target = paths.project_task_root(project_name)
    link = repo_root / ".gea"
    if link.exists() or link.is_symlink():
        return
    if dryrun.active():
        dryrun.report(f"link {link} -> {target}")
        return
    target.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target, target_is_directory=True)
    ui.ok(f".gea -> {target}")
