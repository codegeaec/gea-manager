# gea guide: review

1. `gea review-pack <ID>` and read only that file: the task, a capped diff
   since the checkpoint, verify results run by gea, scope warnings.
   Never trust the builder's self-report; don't `git diff`/`cat` file by file.
2. Optional second opinion from another model: `gea review <ID>` (the
   reviewer is never the builder's pool).
3. Check against the plan and `AGENTS.md`: only what was planned, reuse before
   creating, file-size limit, naming, docs updated. Repeated blocks are findings.
4. Write findings in the task's `## Review`, one per line: severity
   (`critical`/`important`/`minor`), `file:line`, the concrete failure.
5. Critical/important → fix small ones yourself or send back to the same
   builder (`gea delegate <ID> --agent <id>`).
6. Clean → tick `## Verification`, update `docs/`, `gea task done <ID>`
   (its `## Decisions` go to `docs/decisions.md`), commit atomically
   (`.agents/commit-conventions.md`), optionally `gea pr <ID>`.

Switching orchestrator mid-way: `gea handoff --to <cli>`.
