"""`gea task *` and `gea subtask *` CLI dispatch."""

from __future__ import annotations

from pathlib import Path

from gea.agents import notify
from gea.i18n import t
from gea.tasks import store


def _read_issue(number: str) -> dict | None:
    import json

    from gea import proc, ui

    out, err, code = proc.run(["gh", "issue", "view", str(number), "--json", "title,body"])
    try:
        issue = json.loads(out)
    except json.JSONDecodeError:
        issue = None
    if code != 0 or not isinstance(issue, dict) or "title" not in issue:
        ui.err(t("task.issue_failed", number=number, error=err.strip()))
        return None
    return issue


def _offer_worktree_removal(task_id: str, assume_yes: bool = False) -> None:
    """A task closed with a live gea-created worktree: clean it up once its
    branch is merged. Never blocks: it only asks on a terminal, and never without
    one (a merged branch is safe to remove)."""
    import sys
    from pathlib import Path

    from gea import ui
    from gea.agents import log, worktree
    from gea.i18n import t

    wt = worktree.lookup(task_id)
    if wt is None:
        return
    root = Path.cwd()
    if not worktree.branch_merged(wt, root):
        ui.warn(t("worktree.not_merged", branch=wt.branch, path=wt.path))
        return
    # A merged branch is safe to drop (`branch -d`, and a dirty worktree is not
    # removed), so without a terminal there is nothing to ask: just do it.
    if not assume_yes and sys.stdin.isatty():
        if not ui.ask_yes_no(t("worktree.remove", task_id=task_id, path=wt.path), default=False):
            return
    if not worktree.remove(wt, root):
        ui.warn(t("worktree.remove_failed", path=wt.path))
        return
    log.append({"kind": "worktree-removed", "task_id": task_id})
    ui.ok(t("worktree.removed", task_id=task_id))
    if worktree.delete_branch(wt, root):
        ui.ok(t("worktree.branch_deleted", branch=wt.branch))


def _head() -> str | None:
    from gea import proc

    out, _err, code = proc.run(["git", "rev-parse", "HEAD"])
    return out.strip() if code == 0 else None


def _warn_if_head_moved(before: str | None) -> None:
    """Closing a task must never move HEAD. If it did (or something else did,
    meanwhile), say so loudly: that is how a merged commit gets lost."""
    after = _head()
    if before and after and before != after:
        from gea import ui

        ui.err(t("task.head_moved", before=before[:9], after=after[:9]))


def dispatch_task(args) -> int:
    command = args.task_command
    if command == "import":
        from gea.tasks.importer import run_import

        return run_import(
            args.path, dry_run=args.dry_run, remove_source=args.remove_source, assume_yes=args.yes
        )
    if command == "new":
        title, body = args.title, None
        if args.from_issue:
            issue = _read_issue(args.from_issue)
            if issue is None:
                return 1
            title, body = args.title or issue["title"], issue.get("body") or ""
        if not title:
            print(t("task.title_required"))
            return 1
        try:
            path = store.create_task(title, task_type=args.type)
        except ValueError as exc:
            print(exc)
            return 1
        if body:
            heading = "Symptom" if args.type == "bugfix" else "Context"
            store.append_to_section(path, heading, f"From issue #{args.from_issue}:\n\n{body}")
        print(path)
        return 0
    if command == "list":
        for task_id, status in store.list_tasks(getattr(args, "status", None)):
            print(f"{task_id} {status}")
        return 0
    if command == "show":
        path = store.find_task_path(args.task_id)
        if path is None:
            print(f"task not found: {args.task_id}")
            return 1
        print(path.read_text(encoding="utf-8"))
        return 0
    if command == "status":
        if store.set_status(args.task_id, args.new_status):
            print(f"{args.task_id} -> {args.new_status}")
            return 0
        print(f"task not found: {args.task_id}")
        return 1
    if command == "done":
        head_before = _head()
        if store.close_task(args.task_id):
            print(f"{args.task_id} closed")
            notify.stop(Path.cwd().name, args.task_id)
            _offer_worktree_removal(args.task_id, assume_yes=args.yes)
            _warn_if_head_moved(head_before)
            return 0
        print(f"task not found: {args.task_id}")
        return 1
    print("usage: gea task [new|list|show|status|done]")
    return 1


def dispatch_subtask(args) -> int:
    command = args.subtask_command
    if command == "new":
        path = store.create_subtask(args.parent_id, args.title, depends=args.depends)
        print(path)
        return 0
    print("usage: gea subtask new <parent-id> <title> [--depends <id>]")
    return 1
