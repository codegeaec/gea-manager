# gea guide: delegate

Spend your tokens on the plan and the review, not on writing code.

1. Preconditions: the task exists (`gea task show <ID>`), `Status: planned`,
   with `## Files` and `## Acceptance` filled in. Running inside herdr.
2. `gea agents available` lists usable builders (`mode ask`: ask the user
   which; `auto`: take the first).
3. `gea delegate <ID> [--agent <id>] [--worktree]`. It takes a checkpoint
   (or a git worktree), blocks until the builder settles and prints a short
   summary: files changed, files outside scope, verify result. Do not edit the
   repo meanwhile and do not read the builder's terminal.
4. `BLOCKED` means a confirmation dialog: `herdr agent read <pane>
   --source recent-unwrapped --lines 40` (the pane name is in the line
   `gea delegate` printed: `<3 letters of the project>-builder-<id>`), then tell the user what to approve.
5. Timeout or exhausted quota: `gea agents check <id>`, then pick another
   agent. A bad run: `gea undo <ID>` restores the checkpoint.
6. Same findings after two correction rounds → switch agent.
7. No agent available → implement it yourself and note it in *Deviations*.

Next: `gea guide review`.
