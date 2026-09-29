"""gea's entry point: parses the subcommand and dispatches.

Kept intentionally thin — each subcommand's real logic lives in its own
module (doctor.py, setup/, agents/, tasks/, init/, workspace.py) so this
file stays well under the 400-line rule.
"""

from __future__ import annotations

import argparse
import sys

from gea import __version__, config
from gea.i18n import t


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gea", description=t("cli.description"))
    parser.add_argument("--version", action="store_true", help="print gea's version")

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("doctor", help="check installed tools (installs nothing)")

    setup_parser = subparsers.add_parser("setup", help="install and configure this machine")
    setup_parser.add_argument("--yes", action="store_true", help="non-interactive, accept defaults")
    setup_parser.add_argument("--only", help="run a single setup step by id")
    setup_parser.add_argument("--dry-run", action="store_true", help="report, change nothing")

    init_parser = subparsers.add_parser("init", help="set up the current repo to work with gea")
    init_parser.add_argument("--dry-run", action="store_true", help="report, change nothing")

    uninstall_parser = subparsers.add_parser("uninstall", help="revert what gea setup changed")
    uninstall_parser.add_argument("--yes", action="store_true", help="skip the confirmation")
    uninstall_parser.add_argument("--purge", action="store_true", help="also delete ~/gea")
    uninstall_parser.add_argument("--dry-run", action="store_true", help="report, change nothing")

    task_parser = subparsers.add_parser("task", help="manage tasks")
    task_sub = task_parser.add_subparsers(dest="task_command")
    task_new = task_sub.add_parser("new", help="create a new task")
    task_new.add_argument("title")
    task_new.add_argument(
        "--type", choices=["bugfix", "feature", "refactor", "spike"], default=None,
        help="use a type-specific task template",
    )
    task_sub.add_parser("list", help="list tasks").add_argument(
        "--status", default=None, required=False
    )
    task_show = task_sub.add_parser("show", help="show a task")
    task_show.add_argument("task_id")
    task_status = task_sub.add_parser("status", help="change a task's status")
    task_status.add_argument("task_id")
    task_status.add_argument("new_status")
    task_done = task_sub.add_parser("done", help="close a task (move to done/)")
    task_done.add_argument("task_id")

    subtask_parser = subparsers.add_parser("subtask", help="manage subtasks")
    subtask_sub = subtask_parser.add_subparsers(dest="subtask_command")
    subtask_new = subtask_sub.add_parser("new", help="create a new subtask")
    subtask_new.add_argument("parent_id")
    subtask_new.add_argument("title")
    subtask_new.add_argument("--depends", default=None)

    verify_parser = subparsers.add_parser("verify", help="run this project's verify commands")
    verify_parser.add_argument("--task", default=None, help="also run this task's acceptance")

    subparsers.add_parser("scan-secrets", help="scan staged changes for secrets (pre-commit)")
    subparsers.add_parser("lint", help="check the size of AGENTS.md/CLAUDE.md/skills context")

    undo_parser = subparsers.add_parser("undo", help="restore the checkpoint taken before delegate")
    undo_parser.add_argument("task_id")
    undo_parser.add_argument("--yes", action="store_true", help="skip the confirmation")

    agents_parser = subparsers.add_parser("agents", help="manage builder agents")
    agents_sub = agents_parser.add_subparsers(dest="agents_command")
    agents_sub.add_parser("list", help="list all known agent profiles")
    agents_sub.add_parser("available", help="list available (not exhausted) agents")
    agents_start = agents_sub.add_parser("start", help="start a builder pane")
    agents_start.add_argument("agent_id")
    agents_check = agents_sub.add_parser("check", help="check a pane for exhaustion")
    agents_check.add_argument("agent_id")
    agents_reset = agents_sub.add_parser("reset", help="clear exhaustion for an agent's pool")
    agents_reset.add_argument("agent_id")
    agents_mode = agents_sub.add_parser("mode", help="set ask|auto")
    agents_mode.add_argument("value", choices=["ask", "auto"])

    delegate_parser = subparsers.add_parser("delegate", help="delegate a task to a builder")
    delegate_parser.add_argument("task_id")
    delegate_parser.add_argument("--agent", default=None)

    skills_parser = subparsers.add_parser("skills", help="manage global gea skills")
    skills_sub = skills_parser.add_subparsers(dest="skills_command")
    skills_sync = skills_sub.add_parser(
        "sync", help="install/update gea skills for detected agents"
    )
    skills_sync.add_argument("--dry-run", action="store_true", help="report, change nothing")
    skills_sub.add_parser("list", help="list installed gea skills")

    subparsers.add_parser("update", help="update gea, skills and mise-managed tools")

    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except config.ConfigError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1


def _main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = _build_parser()

    if not argv:
        from gea import workspace

        return workspace.open_or_focus()

    args = parser.parse_args(argv)

    if args.version:
        print(t("version.label", version=__version__))
        return 0

    if args.command == "doctor":
        from gea.agents import auth
        from gea.doctor import print_report, run_doctor
        from gea.lint_context import run_lint

        print_report(run_doctor())
        auth.print_report()
        run_lint()
        return 0

    if args.command == "setup":
        from gea.setup.steps import run_setup

        return run_setup(assume_yes=args.yes, only=args.only, dry_run=args.dry_run)

    if args.command == "init":
        from gea.init.wizard import run_init

        return run_init(dry_run=args.dry_run)

    if args.command == "uninstall":
        from gea.uninstall import run_uninstall

        return run_uninstall(assume_yes=args.yes, purge=args.purge, dry_run=args.dry_run)

    if args.command == "task":
        from gea.tasks.commands import dispatch_task

        return dispatch_task(args)

    if args.command == "subtask":
        from gea.tasks.commands import dispatch_subtask

        return dispatch_subtask(args)

    if args.command == "verify":
        from gea.verify import run_verify

        return run_verify(task_id=args.task)

    if args.command == "scan-secrets":
        from gea.secrets import run_scan

        return run_scan()

    if args.command == "lint":
        from gea.lint_context import run_lint

        return run_lint()

    if args.command == "undo":
        from gea.checkpoint import run_undo

        return run_undo(args.task_id, assume_yes=args.yes)

    if args.command == "agents":
        from gea.agents.cli import dispatch_agents

        return dispatch_agents(args)

    if args.command == "delegate":
        from gea.agents.delegate import delegate_task

        return delegate_task(args.task_id, agent_id=args.agent)

    if args.command == "skills":
        from gea.setup.skills import dispatch_skills

        return dispatch_skills(args)

    if args.command == "update":
        from gea.setup.steps import run_update

        return run_update()

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
