# `gea` with no arguments

Opens (or focuses) this project's herdr workspace, ported from the old
herdr-setup gist's `herdr-repo` script — minus the llama.cpp/WSL-specific
opencode-roles logic, which doesn't belong in a general-purpose tool.

- Workspace label = the repo's basename, slugified.
- Tabs, created idempotently (skipped if a tab with that label already
  exists), in this order:
  1. `<primary>` (gea.json's `primary`, "claude" by default) running that
     agent's CLI. On a workspace gea has just created, it **reuses the tab and
     pane herdr creates with the workspace** (`tab rename` + `agent start
     --pane <root pane>`), so no stray "1" tab is left; if the rename fails it
     falls back to a separate tab. Existing workspaces are never touched.
  2. `terminal`, a plain shell.
  3. One tab per entry of `gea.json["tabs"]` (`label`, `cwd` relative to the
     repo, optional `command`): `tab create --cwd <repo>/<cwd>`, then
     `pane run <pane> <command>` only when the tab was created by this call.
     A missing `cwd` skips that tab with a warning.
- **Pane/agent names** (`herdr.pane_name_for`): herdr agent names are unique
  among *all* live agents, so a bare `claude` in a second project collides
  with the first one (`agent_name_taken`). gea names every agent
  `<prefix>-<role>`, where `<prefix>` is the first 3 letters/digits of the
  project folder (`cotizaciones` → `cot`): `cot-claude`, `cot-builder-oc-kimi`,
  `cot-wt-001`, `cot-orchestrator-codex`. If another workspace already holds
  the name (two projects sharing a prefix, e.g. `cotizaciones`/`cotizador`),
  `-2`, `-3`... is appended; an agent in *our own* workspace keeps its name so
  the pane is reused. Tab labels stay short (`claude`). Panes created by older
  gea versions (`claude`, `builder-<id>`) are not renamed.
- `tabs` is validated when the config loads (`config._validate_tabs`):
  unique non-reserved labels, `cwd` relative and inside the repo, `command` a
  string. A `tabs` list in `gea.local.json` replaces the shared one.
- Outside herdr: `os.execvp("herdr", ["herdr"])` replaces the current
  process to attach to the session, after the tabs are set up.
- Already inside herdr (`HERDR_ENV=1`): just focuses the workspace instead
  of re-executing — a pane can't exec its way out from under itself.

## First-time model selection (claude only)

`_ensure_agent_tab` reports whether it actually created and started the
tab, as opposed to finding one already running. Only on that first
creation, if the primary agent is `claude` and `gea.json`'s `primaryModel`
is set (asked by `gea init`, see `docs/init.md`), `gea` sends `/model
<value>` to that pane (`herdr agent prompt <agent name> "/model <value>"`, not
waited on). Reopening the workspace later never resends it.
