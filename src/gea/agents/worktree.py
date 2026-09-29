"""Isolated git worktrees for builders (`gea delegate --worktree`).

herdr owns the mechanics (`herdr worktree create|remove`); gea only picks a
deterministic path/branch per task, records the mapping in the delegation
log, and makes sure it only ever removes worktrees it created itself.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from gea import paths, proc
from gea.agents import herdr, log

CONFIG_FILES = ("gea.json", "gea.local.json")  # may be untracked: copy them in


@dataclass
class Worktree:
    task_id: str
    path: Path
    branch: str
    base: str
    workspace_id: str | None = None

    @property
    def pane_name(self) -> str:
        slug = self.task_id.lower().removeprefix("task-").replace(".", "-")
        return f"wt-{slug}"[:20]


def _git(root: Path, *args: str) -> tuple[str, int]:
    out, _err, code = proc.run(["git", "-C", str(root), *args], timeout=60)
    return out.strip(), code


def create(task_id: str, repo_root: Path) -> Worktree | None:
    """Create the task's worktree. None (with nothing left behind) on failure."""
    base, code = _git(repo_root, "rev-parse", "HEAD")
    if code != 0:
        return None
    wt = Worktree(
        task_id=task_id,
        path=paths.gea_home() / "worktrees" / repo_root.name / task_id.lower(),
        branch=f"gea/{task_id.lower()}",
        base=base,
    )
    result, err = herdr.herdr_json(
        [
            "worktree", "create", "--cwd", str(repo_root), "--branch", wt.branch,
            "--base", base, "--path", str(wt.path), "--no-focus",
        ],
        timeout=60,
    )
    wt.workspace_id = (result.get("workspace") or {}).get("workspace_id")
    if err or not wt.path.is_dir():
        remove(wt, repo_root)
        return None
    for name in CONFIG_FILES:
        if (repo_root / name).exists() and not (wt.path / name).exists():
            shutil.copy2(repo_root / name, wt.path / name)
    return wt


def remove(wt: Worktree, repo_root: Path, force: bool = False) -> bool:
    """Remove a worktree gea created. Never deletes the branch."""
    if wt.workspace_id:
        cmd = ["worktree", "remove", "--workspace", wt.workspace_id]
        _result, err = herdr.herdr_json(cmd + (["--force"] if force else []), timeout=60)
        return err is None
    args = ["worktree", "remove", str(wt.path)] + (["--force"] if force else [])
    _out, code = _git(repo_root, *args)
    return code == 0


def changed_files(wt: Worktree) -> list[str]:
    """Everything the builder changed relative to the base commit."""
    diff, _ = _git(wt.path, "diff", "--name-only", wt.base)
    new, _ = _git(wt.path, "ls-files", "--others", "--exclude-standard")
    ignore = set(CONFIG_FILES)
    return sorted((set(diff.splitlines()) | set(new.splitlines())) - ignore)


def commit_all(wt: Worktree, message: str) -> bool:
    """Commit the builder's output on the task branch so it can be merged."""
    _git(wt.path, "add", "-A", "--", ".", *(f":!{n}" for n in CONFIG_FILES))
    _out, code = _git(wt.path, "commit", "-q", "-m", message)
    return code == 0


def lookup(task_id: str) -> Worktree | None:
    """The task's live worktree according to the delegation log."""
    entries = log.read(task_id=task_id)
    live = None
    for e in entries:
        if e.get("kind") == "worktree-removed":
            live = None
        elif e.get("worktree"):
            live = Worktree(
                task_id, Path(e["worktree"]), e.get("branch", ""), e.get("base", ""),
                e.get("workspace_id"),
            )
    return live
