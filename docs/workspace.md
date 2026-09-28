# `gea` with no arguments

Opens (or focuses) this project's herdr workspace, ported from the old
herdr-setup gist's `herdr-repo` script — minus the llama.cpp/WSL-specific
opencode-roles logic, which doesn't belong in a general-purpose tool.

- Workspace label = the repo's basename, slugified.
- Two tabs, created idempotently (skipped if a tab with that label already
  exists): `<primary>` (gea.json's `primary`, "claude" by default) running
  that agent's CLI, and a plain `terminal` tab for anything else (`pnpm
  dev`, etc.).
- Outside herdr: `os.execvp("herdr", ["herdr"])` replaces the current
  process to attach to the session, after the tabs are set up.
- Already inside herdr (`HERDR_ENV=1`): just focuses the workspace instead
  of re-executing — a pane can't exec its way out from under itself.

## First-time model selection (claude only)

`_ensure_agent_tab` reports whether it actually created and started the
tab, as opposed to finding one already running. Only on that first
creation, if the primary agent is `claude` and `gea.json`'s `primaryModel`
is set (asked by `gea init`, see `docs/init.md`), `gea` sends `/model
<value>` to that pane (`herdr agent prompt <label> "/model <value>"`, not
waited on). Reopening the workspace later never resends it.
