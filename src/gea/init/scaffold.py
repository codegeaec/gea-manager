"""Write the project scaffold (AGENTS.md, .agents/, docs/, gea.json,
.claude/settings.json, .gitignore) from `src/gea/templates/{lang}/`.

Never overwrites a file that already exists — `gea init` is meant to be
re-run safely (e.g. after upgrading gea) without clobbering edits the user
made to their own AGENTS.md.
"""

from __future__ import annotations

import json
from pathlib import Path

TEMPLATES_ROOT = Path(__file__).resolve().parent.parent / "templates"

LANG_NAMES = {"es": "Spanish", "en": "English"}


def _read_template(lang: str, relative_path: str) -> str:
    path = TEMPLATES_ROOT / lang / relative_path
    if not path.exists():
        path = TEMPLATES_ROOT / "en" / relative_path
    return path.read_text(encoding="utf-8")


def _write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _shadcn_section(lang: str, pm: str, has_shadcn: bool) -> str:
    if not has_shadcn:
        return ""
    runner = {"pnpm": "pnpm dlx", "npm": "npx", "yarn": "yarn dlx", "bun": "bunx"}.get(
        pm, "npx"
    )
    if lang == "es":
        return (
            "\n## shadcn/ui\n\n"
            f"Siempre por el CLI (`{runner} shadcn@latest add ...`), nunca por MCP.\n"
        )
    return (
        "\n## shadcn/ui\n\n"
        f"Always through the CLI (`{runner} shadcn@latest add ...`), never via MCP.\n"
    )


def render_agents_md(
    *,
    lang: str,
    project_name: str,
    pm: str,
    commit_lang: str,
    docs_lang: str,
    verify_commands: list[str],
    tasks_root_display: str,
    has_shadcn: bool,
) -> str:
    template = _read_template(lang, "AGENTS.md")
    return template.format(
        project_name=project_name,
        pm=pm,
        commit_lang=LANG_NAMES.get(commit_lang, commit_lang),
        docs_lang=LANG_NAMES.get(docs_lang, docs_lang),
        verify_commands="\n".join(verify_commands) or "(none configured yet)",
        tasks_root=tasks_root_display,
        shadcn_section=_shadcn_section(lang, pm, has_shadcn),
    )


def write_agents_md(repo_root: Path, **kwargs) -> bool:
    content = render_agents_md(**kwargs)
    return _write_if_missing(repo_root / "AGENTS.md", content)


def write_claude_md(repo_root: Path, lang: str, project_name: str, tasks_root_display: str) -> bool:
    template = _read_template(lang, "CLAUDE.md")
    content = template.format(project_name=project_name, tasks_root=tasks_root_display)
    return _write_if_missing(repo_root / "CLAUDE.md", content)


def write_agents_dir(
    repo_root: Path,
    lang: str,
    project_name: str,
    commit_lang: str,
    ponytail: bool,
    tasks_root_display: str,
) -> list[str]:
    written = []
    agents_dir = repo_root / ".agents"

    readme = _read_template(lang, "agents/README.md").format(project_name=project_name)
    if _write_if_missing(agents_dir / "README.md", readme):
        written.append(".agents/README.md")

    commits = _read_template(lang, "agents/commit-conventions.md").format(
        commit_lang=LANG_NAMES.get(commit_lang, commit_lang)
    )
    if _write_if_missing(agents_dir / "commit-conventions.md", commits):
        written.append(".agents/commit-conventions.md")

    gotchas = _read_template(lang, "agents/gotchas.md").format(project_name=project_name)
    if _write_if_missing(agents_dir / "gotchas.md", gotchas):
        written.append(".agents/gotchas.md")

    ponytail_section = _ponytail_section(lang) if ponytail else ""
    builder = _read_template(lang, "agents/builder.md").format(
        project_name=project_name,
        tasks_root=tasks_root_display,
        ponytail_section=ponytail_section,
    )
    if _write_if_missing(agents_dir / "builder.md", builder):
        written.append(".agents/builder.md")

    return written


def _ponytail_section(lang: str) -> str:
    if lang == "es":
        return (
            "\n## Minimalismo (ponytail)\n\n"
            "Aplicá la skill `ponytail`: el mejor código es el que no escribiste. "
            "El plan de la task tiene prioridad — si pide explícitamente una "
            "abstracción o un archivo, se hace igual.\n"
        )
    return (
        "\n## Minimalism (ponytail)\n\n"
        "Apply the `ponytail` skill: the best code is the code you never wrote. "
        "The task's plan wins — if it explicitly asks for an abstraction or a "
        "file, do it anyway.\n"
    )


def write_docs(repo_root: Path, lang: str, project_name: str) -> list[str]:
    written = []
    docs_dir = repo_root / "docs"

    index = _read_template(lang, "docs/INDEX.md").format(project_name=project_name)
    if _write_if_missing(docs_dir / "INDEX.md", index):
        written.append("docs/INDEX.md")

    vision_name = "00-vision-producto.md" if lang == "es" else "00-vision-product.md"
    vision = _read_template(lang, f"docs/{vision_name}").format(project_name=project_name)
    if _write_if_missing(docs_dir / vision_name, vision):
        written.append(f"docs/{vision_name}")

    adr_template = _read_template(lang, "docs/adr-template.md")
    if _write_if_missing(docs_dir / "adr" / "0000-template.md", adr_template):
        written.append("docs/adr/0000-template.md")

    return written


def merge_claude_settings(repo_root: Path) -> bool:
    path = repo_root / ".claude" / "settings.json"
    default = {"attribution": {"commit": "", "pr": "", "sessionUrl": False}}
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(default, indent=2) + "\n", encoding="utf-8")
        return True
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    if "attribution" in data:
        return False
    data["attribution"] = default["attribution"]
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return True


def update_gitignore(repo_root: Path, tasks_location: str) -> bool:
    path = repo_root / ".gitignore"
    entries = ["gea.json", ".codegraph/"]
    if tasks_location == "home":
        entries.append(".gea")
    existing = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    to_add = [e for e in entries if e not in existing]
    if not to_add:
        return False
    with path.open("a", encoding="utf-8") as f:
        if existing and existing[-1] != "":
            f.write("\n")
        f.write("\n".join(to_add) + "\n")
    return True
