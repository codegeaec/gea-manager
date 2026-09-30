"""`gea task *` and `gea subtask *` CLI dispatch."""

from __future__ import annotations

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


def _offer_worktree_removal(task_id: str) -> None:
    """A task closed with a live gea-created worktree: offer to remove it."""
    from pathlib import Path

    from gea import ui
    from gea.agents import log, worktree
    from gea.i18n import t

    wt = worktree.lookup(task_id)
    if wt is None:
        return
    if not ui.ask_yes_no(t("worktree.remove", task_id=task_id, path=wt.path), default=False):
        return
    if worktree.remove(wt, Path.cwd()):
        log.append({"kind": "worktree-removed", "task_id": task_id})
        ui.ok(t("worktree.removed", task_id=task_id))
    else:
        ui.warn(t("worktree.remove_failed", path=wt.path))


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
        if store.close_task(args.task_id):
            print(f"{args.task_id} closed")
            _offer_worktree_removal(args.task_id)
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
