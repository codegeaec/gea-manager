"""Task/subtask filesystem store: id allocation, creation, status changes,
lookup, and closing (moving to a `done/` subfolder).

Root resolution respects `gea.json`'s `tasks.location`:
- `home` (default question in the init wizard): `~/gea/projects/<name>/`,
  real files live under the user's home even though the repo has a
  gitignored `.gea` symlink pointing at it (created by `gea init`).
- `repo`: `<repo>/.gea/`, a real versioned directory.
"""

from __future__ import annotations

import re
from datetime import date as date_cls
from pathlib import Path

from gea import config, paths
from gea.tasks import decisions, templates

TASK_ID_RE = re.compile(r"TASK-(\d+)(?:\.(\d+))?")


def task_root(repo_root: Path | None = None) -> Path:
    repo_root = repo_root or Path.cwd()
    cfg = config.load_project(repo_root)
    location = cfg.get("tasks", {}).get("location", "home")
    if location == "repo":
        return repo_root / ".gea"
    name = cfg.get("name") or repo_root.name
    return paths.project_task_root(name)


def tasks_dir(repo_root: Path | None = None) -> Path:
    return task_root(repo_root) / "tasks"


def subtasks_dir(repo_root: Path | None = None) -> Path:
    return task_root(repo_root) / "subtasks"


def _all_task_files(repo_root: Path | None = None) -> list[Path]:
    files: list[Path] = []
    for base in (tasks_dir(repo_root), subtasks_dir(repo_root)):
        if base.exists():
            files.extend(base.glob("*.md"))
            done = base / "done"
            if done.exists():
                files.extend(done.glob("*.md"))
    return files


def next_task_number(repo_root: Path | None = None) -> int:
    numbers = []
    for f in _all_task_files(repo_root):
        match = TASK_ID_RE.match(f.name)
        if match and match.group(2) is None:
            numbers.append(int(match.group(1)))
    return max(numbers, default=0) + 1


def next_subtask_number(parent_id: str, repo_root: Path | None = None) -> int:
    parent_num = TASK_ID_RE.match(parent_id).group(1)
    numbers = []
    for f in _all_task_files(repo_root):
        match = TASK_ID_RE.match(f.name)
        if match and match.group(2) is not None and match.group(1) == parent_num:
            numbers.append(int(match.group(2)))
    return max(numbers, default=0) + 1


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "task"


def _docs_lang(repo_root: Path | None = None) -> str:
    cfg = config.load_project(repo_root or Path.cwd())
    return cfg.get("lang", {}).get("docs", "en")


def create_task(
    title: str, repo_root: Path | None = None, task_type: str | None = None
) -> Path:
    repo_root = repo_root or Path.cwd()
    number = next_task_number(repo_root)
    task_id = f"TASK-{number:03d}"
    slug = slugify(title)
    directory = tasks_dir(repo_root)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{task_id}-{slug}.md"
    content = templates.render_task(
        task_id,
        title,
        date_cls.today().isoformat(),
        lang=_docs_lang(repo_root),
        task_type=task_type,
    )
    path.write_text(content, encoding="utf-8")
    write_index(repo_root)
    return path


def create_subtask(
    parent_id: str, title: str, depends: str | None = None, repo_root: Path | None = None
) -> Path:
    repo_root = repo_root or Path.cwd()
    number = next_subtask_number(parent_id, repo_root)
    parent_num = TASK_ID_RE.match(parent_id).group(1)
    task_id = f"TASK-{parent_num}.{number}"
    slug = slugify(title)
    directory = subtasks_dir(repo_root)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{task_id}-{slug}.md"
    content = templates.render_subtask(
        task_id,
        title,
        parent_id,
        depends or "none",
        date_cls.today().isoformat(),
        lang=_docs_lang(repo_root),
    )
    path.write_text(content, encoding="utf-8")
    write_index(repo_root)
    return path


def find_task_path(task_id: str, repo_root: Path | None = None) -> Path | None:
    for f in _all_task_files(repo_root):
        if f.name.startswith(f"{task_id}-"):
            return f
    return None


def read_status(path: Path) -> str | None:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("Status:"):
            return line.split(":", 1)[1].strip()
    return None


def set_status(task_id: str, new_status: str, repo_root: Path | None = None) -> bool:
    path = find_task_path(task_id, repo_root)
    if path is None:
        return False
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("Status:"):
            lines[i] = f"Status: {new_status}\n"
        if line.startswith("Updated:"):
            lines[i] = f"Updated: {date_cls.today().isoformat()}\n"
    path.write_text("".join(lines), encoding="utf-8")
    write_index(repo_root)
    return True


def list_tasks(status: str | None = None, repo_root: Path | None = None) -> list[tuple[str, str]]:
    """Returns [(task_id, status), ...] for every active (not `done/`) task
    and subtask, optionally filtered by status."""
    results = []
    for base in (tasks_dir(repo_root), subtasks_dir(repo_root)):
        if not base.exists():
            continue
        for f in sorted(base.glob("*.md")):
            id_match = re.match(r"(TASK-\d+(?:\.\d+)?)", f.name)
            if not id_match:
                continue
            task_id = id_match.group(1)
            task_status = read_status(f)
            if status is None or task_status == status:
                results.append((task_id, task_status or "unknown"))
    return results


def close_task(task_id: str, repo_root: Path | None = None) -> bool:
    """Move a task/subtask file into its `done/` subfolder."""
    path = find_task_path(task_id, repo_root)
    if path is None:
        return False
    decisions.archive(path, task_id, repo_root or Path.cwd())
    done_dir = path.parent / "done"
    done_dir.mkdir(parents=True, exist_ok=True)
    path.rename(done_dir / path.name)
    write_index(repo_root)
    return True


def write_index(repo_root: Path | None = None) -> Path:
    """Regenerate `<task_root>/INDEX.md` listing every active task/subtask
    and its status. Called after every mutation (create/status/done)."""
    root = task_root(repo_root)
    lines = ["# Tasks index", "", "| ID | Status |", "|---|---|"]
    for task_id, status in sorted(list_tasks(repo_root=repo_root)):
        lines.append(f"| {task_id} | {status} |")
    index_path = root / "INDEX.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return index_path
