"""`gea task import` — bring tasks kept in another layout into gea's.

Known layouts (looked for under `tasks/`, `.tasks/`, `docs/tasks/`, `task/`):
- `active-completed`: `<dir>/active/TASK-*.md` and `<dir>/completed/TASK-*.md`
- `flat`: `<dir>/TASK-*.md`, done or not according to their `Status:`

`TASK-N` files go to `tasks/`, `TASK-N.M` to `subtasks/`, finished ones to
`done/`. The body is copied untouched; only the header's `Status:` line is
normalised (a trailing remark becomes a `Note:` line). Originals are never
deleted unless `--remove-source` is given.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from gea import dryrun, proc, ui
from gea.i18n import t
from gea.tasks import store

STATUSES = ("planned", "in-progress", "review", "completed")
CANDIDATE_DIRS = ("tasks", ".tasks", "docs/tasks", "task")
STATUS_RE = re.compile(r"^Status:\s*([\w-]+)\s*(?:[—–-]+\s*(.+))?$")
FILE_RE = re.compile(r"TASK-\d+(?:\.\d+)?-.+\.md$")


@dataclass
class Layout:
    root: Path
    kind: str
    count: int

    def __str__(self) -> str:
        return f"{self.root} ({self.kind}, {self.count} file(s))"


@dataclass
class Item:
    source: Path
    dest: Path
    content: str


@dataclass
class Plan:
    items: list[Item] = field(default_factory=list)
    unchanged: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)


def _task_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.glob("*.md") if FILE_RE.match(p.name))


def detect_layouts(repo_root: Path) -> list[Layout]:
    found = []
    for name in CANDIDATE_DIRS:
        root = repo_root / name
        if not root.is_dir():
            continue
        nested = [_task_files(root / sub) for sub in ("active", "completed")]
        if any(nested):
            found.append(Layout(root, "active-completed", sum(map(len, nested))))
        elif _task_files(root):
            found.append(Layout(root, "flat", len(_task_files(root))))
    return found


def _normalise(text: str, done: bool, name: str, plan: Plan) -> tuple[str, bool]:
    """Fix the header's Status line; returns (new text, is_done)."""
    head, sep, rest = text.partition("\n## ")
    lines, status = head.split("\n"), None
    for i, line in enumerate(lines):
        match = STATUS_RE.match(line)
        if not match:
            continue
        status, note = match.group(1).lower(), match.group(2)
        if status not in STATUSES:
            plan.warnings.append(t("import.unknown_status", name=name, status=status))
            break
        if done and status != "completed":
            plan.warnings.append(t("import.forced_completed", name=name, status=status))
            status = "completed"
        lines[i : i + 1] = [f"Status: {status}"] + ([f"Note: {note.strip()}"] if note else [])
        break
    return "\n".join(lines) + sep + rest, done or status == "completed"


def build_plan(layout: Layout, repo_root: Path) -> Plan:
    plan = Plan()
    sources = (
        [(p, p.parent.name == "completed") for sub in ("active", "completed")
         for p in _task_files(layout.root / sub)]
        if layout.kind == "active-completed"
        else [(p, False) for p in _task_files(layout.root)]
    )
    for source, in_completed in sources:
        text = source.read_text(encoding="utf-8")
        new_text, done = _normalise(text, in_completed, source.name, plan)
        is_sub = "." in source.name.split("-", 2)[1]
        base = store.subtasks_dir(repo_root) if is_sub else store.tasks_dir(repo_root)
        dest = (base / "done" if done else base) / source.name
        # A finished task may already sit in the other folder (imported earlier).
        twin = (base if done else base / "done") / source.name
        if twin.exists():
            plan.conflicts.append(t("import.conflict", name=source.name, path=twin))
        elif dest.exists():
            if dest.read_text(encoding="utf-8") == new_text:
                plan.unchanged.append(source)
            else:
                plan.conflicts.append(t("import.conflict", name=source.name, path=dest))
        else:
            plan.items.append(Item(source, dest, new_text))
    return plan


def _remove_sources(plan: Plan, repo_root: Path, assume_yes: bool) -> bool:
    files = [str(i.source) for i in plan.items] + [str(p) for p in plan.unchanged]
    tracked, _e, code = proc.run(["git", "-C", str(repo_root), "ls-files", "--", *files])
    dirty, _e2, _c2 = proc.run(["git", "-C", str(repo_root), "status", "--porcelain", "--", *files])
    if code != 0 or len(tracked.split()) != len(files) or dirty.strip():
        ui.err(t("import.remove_refused"))
        return False
    if not ui.ask_yes_no(t("import.remove_confirm", count=len(files)), False, assume_yes):
        return False
    _o, err, rc = proc.run(["git", "-C", str(repo_root), "rm", "-q", "--", *files])
    if rc != 0:
        ui.err(err.strip())
    return rc == 0


def import_layout(
    layout: Layout, repo_root: Path, remove_source: bool = False, assume_yes: bool = False
) -> int:
    plan = build_plan(layout, repo_root)
    for warning in plan.warnings:
        ui.warn(warning)
    if plan.conflicts:
        for conflict in plan.conflicts:
            ui.err(conflict)
        return 1
    for item in plan.items:
        if dryrun.active():
            dryrun.report(f"import {item.source} -> {item.dest}")
            continue
        item.dest.parent.mkdir(parents=True, exist_ok=True)
        item.dest.write_text(item.content, encoding="utf-8")
    if not dryrun.active():
        store.write_index(repo_root)
    ui.ok(t("import.done", imported=len(plan.items), unchanged=len(plan.unchanged)))
    if remove_source and not dryrun.active():
        return 0 if _remove_sources(plan, repo_root, assume_yes) else 1
    return 0


def run_import(
    path: str | None = None,
    dry_run: bool = False,
    remove_source: bool = False,
    assume_yes: bool = False,
) -> int:
    dryrun.enable(dry_run)
    repo_root = Path.cwd()
    layouts = detect_layouts(repo_root)
    if path:
        wanted = (repo_root / path).resolve()
        layouts = [lay for lay in layouts if lay.root.resolve() == wanted]
    if not layouts:
        ui.err(t("import.none"))
        return 1
    return max(import_layout(lay, repo_root, remove_source, assume_yes) for lay in layouts)
