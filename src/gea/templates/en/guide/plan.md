# gea guide: plan

Turn a request into a durable task; the task file, not the chat, is what
whoever implements it reads.

1. Ground the request: ask only the 2–3 questions that would change the plan.
2. Look for existing code first (`docs/INDEX.md`, codegraph if `.codegraph/`
   exists). "Extend X" beats "add a new Y".
3. Create it: `gea task new "<title>" [--type bugfix|feature|refactor|spike]`
   (or `--from-issue N`).
4. Fill in Objective, Context, Requirements, Plan and — mandatory before
   delegating — `## Files` (every path the builder may touch, each in
   backticks; globs and directories are fine) and `## Acceptance` (one bullet
   per criterion; put a runnable command in backticks so
   `gea verify --task <ID>` checks it).
5. Set `Tier: S|M|L` (S mechanical, L delicate or cross-cutting) and, if the
   default 30 min is wrong, `Budget: 45m`.
6. Big task (4+ steps over separable files)? `gea subtask new <ID> "<title>"
   [--depends <ID>]`; subtasks touching the same file are sequential.
7. Planning never edits source code.

Next: `gea guide delegate`.
