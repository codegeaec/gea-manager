"""`gea init` — interactive wizard that leaves a repo ready to work with
gea: gea.json, AGENTS.md/CLAUDE.md, .agents/, docs/, .claude/settings.json,
.gitignore, and (if available) codegraph.
"""

from __future__ import annotations

from pathlib import Path

from gea import config, platform, proc, ui
from gea.agents.profiles import load_profiles
from gea.init import detect, scaffold
from gea.tasks import store


def _tasks_root_display(cfg: dict) -> str:
    return str(store.task_root(Path.cwd())) if cfg else ""


def _pick_primary_agent() -> str:
    candidates = [c for c in ("claude", "opencode", "codex", "agy", "kimi") if platform.which(c)]
    if not candidates:
        return "claude"
    if "claude" in candidates:
        default = candidates.index("claude")
    else:
        default = 0
    choice = ui.ask_choice(
        "Primary agent" + (" (claude recommended)" if "claude" in candidates else ""),
        candidates,
        default_index=default,
    )
    return candidates[choice]


def _pick_tasks_location() -> str:
    choice = ui.ask_choice(
        "Where should tasks/subtasks live?",
        ["~/gea/projects/<name> (home)", ".gea/ versioned in the repo (repo)"],
        default_index=0,
    )
    return "home" if choice == 0 else "repo"


def _pick_lang() -> tuple[str, str]:
    commit_choice = ui.ask_choice("Commit language", ["Spanish", "English"], default_index=0)
    commit_lang = "es" if commit_choice == 0 else "en"
    same = ui.ask_yes_no("Use the same language for docs?", default=True)
    docs_lang = commit_lang if same else ("en" if commit_lang == "es" else "es")
    return commit_lang, docs_lang


def run_init() -> int:
    repo_root = Path.cwd()

    if not (repo_root / ".git").exists():
        if ui.ask_yes_no("No git repo here — run `git init`?", default=True):
            proc.run(["git", "init"], timeout=15)
        else:
            ui.err("gea init needs a git repository")
            return 1

    project_name = repo_root.name
    primary = _pick_primary_agent()
    tasks_location = _pick_tasks_location()
    commit_lang, docs_lang = _pick_lang()

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
        if not ui.ask_yes_no("Use these?", default=True):
            verify_commands = []

    all_profiles = load_profiles()
    allow = [p.id for p in all_profiles] if all_profiles else []

    cfg = config.DEFAULT_PROJECT_CONFIG.copy()
    cfg.update(
        {
            "name": project_name,
            "primary": primary,
            "tasks": {"location": tasks_location},
            "verify": verify_commands,
            "builders": {"mode": "ask", "allow": allow, "ponytail": True},
            "lang": {"commits": commit_lang, "docs": docs_lang},
            "pm": pm,
        }
    )
    config.save_project(repo_root, cfg)
    ui.ok("gea.json written")

    tasks_root_display = _tasks_root_display(cfg)

    if scaffold.write_agents_md(
        repo_root,
        lang=docs_lang,
        project_name=project_name,
        pm=pm,
        commit_lang=commit_lang,
        docs_lang=docs_lang,
        verify_commands=verify_commands,
        tasks_root_display=tasks_root_display,
        has_shadcn=has_shadcn,
    ):
        ui.ok("AGENTS.md written")

    if platform.which("claude"):
        if scaffold.write_claude_md(repo_root, docs_lang, project_name, tasks_root_display):
            ui.ok("CLAUDE.md written")
        if scaffold.merge_claude_settings(repo_root):
            ui.ok(".claude/settings.json written")

    written = scaffold.write_agents_dir(
        repo_root,
        docs_lang,
        project_name,
        commit_lang,
        cfg["builders"]["ponytail"],
        tasks_root_display,
    )
    for path in written:
        ui.ok(f"{path} written")

    if ui.ask_yes_no("Set up a docs/ system (INDEX.md, vision, ADR template)?", default=True):
        written_docs = scaffold.write_docs(repo_root, docs_lang, project_name)
        for path in written_docs:
            ui.ok(f"{path} written")

    if scaffold.update_gitignore(repo_root, tasks_location):
        ui.ok(".gitignore updated")

    if tasks_location == "home":
        _ensure_gea_symlink(repo_root, project_name)

    should_run_codegraph = platform.which("codegraph") and ui.ask_yes_no(
        "Run `codegraph init` for this project?", default=True
    )
    if should_run_codegraph:
        proc.run(["codegraph", "init"], timeout=60)
        ui.ok("codegraph initialized")

    ui.ok("gea init complete")
    return 0


def _ensure_gea_symlink(repo_root: Path, project_name: str) -> None:
    from gea import paths

    target = paths.project_task_root(project_name)
    target.mkdir(parents=True, exist_ok=True)
    link = repo_root / ".gea"
    if link.exists() or link.is_symlink():
        return
    link.symlink_to(target, target_is_directory=True)
    ui.ok(f".gea -> {target}")
