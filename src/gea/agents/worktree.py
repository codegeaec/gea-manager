"""Isolated git worktrees for builders (`gea delegate --worktree`).

herdr owns the mechanics (`herdr worktree create|remove`); gea only picks a
deterministic path/branch per task, records the mapping in the delegation
log, and makes sure it only ever removes worktrees it created itself.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from gea import paths, proc, ui, verify
from gea.agents import herdr, log

CONFIG_FILES = ("gea.json", "gea.local.json")  # may be untracked: copy them in


@dataclass
class Worktree:
    task_id: str
    path: Path
    branch: str
    base: str
    workspace_id: str | None = None
    copied: list[str] = field(default_factory=list)  # untracked files put in by gea

    @property
    def slug(self) -> str:
        """`001` for TASK-001, `004-1` for TASK-004.1 (used in the pane name)."""
        return self.task_id.lower().removeprefix("task-").replace(".", "-")


def _git(root: Path, *args: str) -> tuple[str, int]:
    out, _err, code = proc.run(["git", "-C", str(root), *args], timeout=60)
    return out.strip(), code


SETUP_TIMEOUT = 900  # e.g. `pnpm install` in a fresh checkout


def create(
    task_id: str, repo_root: Path, setup: dict | None = None
) -> Worktree | None:
    """Create the task's worktree. None (with nothing left behind) on failure.

    `setup` is `builders.worktree`: `copy` = untracked files a fresh checkout
    lacks (e.g. `.env`), `setup` = a command to run there (e.g. `pnpm install`).
    A failing setup command removes the worktree again."""
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
    setup = setup or {}
    for name in [*CONFIG_FILES, *setup.get("copy", [])]:
        source = repo_root / name
        if source.is_file() and not (wt.path / name).exists():
            (wt.path / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, wt.path / name)
            if name not in CONFIG_FILES:
                wt.copied.append(name)
    command = setup.get("setup")
    if command:
        passed, tail = verify.execute(command, wt.path, timeout=SETUP_TIMEOUT)
        if not passed:
            ui.err(f"worktree setup `{command}` failed:\n{tail}")
            remove(wt, repo_root, force=True)
            return None
    return wt


def remove(wt: Worktree, repo_root: Path, force: bool = False) -> bool:
    """Remove a worktree gea created. Never deletes the branch (see `delete_branch`)."""
    if wt.workspace_id:
        cmd = ["worktree", "remove", "--workspace", wt.workspace_id]
        _result, err = herdr.herdr_json(cmd + (["--force"] if force else []), timeout=60)
        if err is None:
            # herdr keeps the emptied workspace as a "(deleted)" tab: close it too.
            herdr.herdr_json(["workspace", "close", wt.workspace_id])
        return err is None
    args = ["worktree", "remove", str(wt.path)] + (["--force"] if force else [])
    _out, code = _git(repo_root, *args)
    return code == 0


def confine_opencode(wt: Worktree, allow: list[Path]) -> bool:
    """Deny opencode's writes outside its worktree (`permission.external_directory`),
    except `allow` (the task files). Skipped when the checkout already has its own
    opencode.jsonc. The file is gea's: it is never committed (tracked in `wt.copied`)."""
    config = wt.path / "opencode.jsonc"
    if config.exists():
        return False
    rules = {"*": "deny", **{f"{d}/**": "allow" for d in allow}}
    config.write_text(
        json.dumps({"permission": {"external_directory": rules}}, indent=2) + "\n",
        encoding="utf-8",
    )
    wt.copied.append(config.name)
    return True


def branch_merged(wt: Worktree, repo_root: Path) -> bool:
    """True when the task branch is already contained in the current HEAD."""
    if not wt.branch:
        return False
    _out, code = _git(repo_root, "merge-base", "--is-ancestor", wt.branch, "HEAD")
    return code == 0


def delete_branch(wt: Worktree, repo_root: Path, force: bool = False) -> bool:
    """Delete the task branch; without `force`, `-d` refuses unless it is merged."""
    _out, code = _git(repo_root, "branch", "-D" if force else "-d", wt.branch)
    return code == 0


def changed_files(wt: Worktree) -> list[str]:
    """Everything the builder changed relative to the base commit."""
    diff, _ = _git(wt.path, "diff", "--name-only", wt.base)
    new, _ = _git(wt.path, "ls-files", "--others", "--exclude-standard")
    ignore = set(CONFIG_FILES) | set(wt.copied)
    return sorted((set(diff.splitlines()) | set(new.splitlines())) - ignore)


def commit_all(wt: Worktree, message: str) -> bool:
    """Commit the builder's output on the task branch so it can be merged."""
    _git(wt.path, "add", "-A", "--", ".", *(f":!{n}" for n in [*CONFIG_FILES, *wt.copied]))
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
