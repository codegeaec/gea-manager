# `gea setup`

Idempotent machine wizard, one step per concern:

1. **Language** — picks `ui_lang` (see `docs/i18n.md`).
2. **System packages** — `git`, `curl`, `sqlite3`, a compiler, via `apt`/`brew`.
3. **mise** — installs [mise](https://mise.jdx.dev) if missing, then uses it
   to install `gh`, `jq`, `yq`, `rg`, `fd`, `ast-grep`, `just`, `duckdb`,
   `shellcheck`, `uv`, `lazygit` — no `sudo`, same versions on Linux/WSL/macOS.
4. **node** — respects an existing `nvm`/`node`; installs `node@lts` via
   mise only if neither is present.
5. **herdr** — the terminal workspace manager gea drives everything else
   through.
6. **Agents** — Claude Code (recommended as primary), OpenCode, Codex CLI,
   agy, Kimi Code CLI. All optional except whichever the project's wizard
   picks as primary.
7. **herdr integrations** — `herdr integration install <target>` for every
   installed agent that has one, so herdr reads each CLI's own
   idle/working/blocked hook instead of guessing from the screen.
8. **rtk** — installs it, then `rtk init -g` plus the right per-agent flag
   for each detected agent, so Bash commands get rewritten to their
   token-saving form automatically.
9. **codegraph** — installs it and wires its MCP server into every detected
   agent.
10. **shadcn** — installs the `shadcn` CLI and scans for a shadcn MCP
    server (see `src/gea/shadcn.py`); offers to remove it so shadcn work
    always goes through the CLI (reviewable diffs, no MCP round-trip).
11. **Global instructions** — writes/refreshes the `<!-- gea:start -->`
    block (available CLI tools, rtk/codegraph usage, the shadcn-CLI rule,
    the 400-line rule) into each agent's global instructions file, without
    touching anything else the user wrote there (`src/gea/setup/
    global_instructions.py`).
12. **Skills** — syncs third-party skills (ponytail, the vercel-labs
    bundle, ui-ux-pro-max) and this repo's own `skills/gea-*` to every
    detected agent via `npx skills add -g`.
13. **Legacy cleanup** — removes the old herdr-setup gist's `herdr()`
    shell function and `~/.local/bin/herdr-repo`, with a timestamped
    backup (`src/gea/setup/shell_rc.py`).

`--yes` accepts the recommended default at every prompt (used by
`install.sh`/`install.ps1`). `--only <step>` runs a single step (`lang`,
`system`, `mise`, `node`, `herdr`, `cleanup`) for local debugging.

`gea update` re-runs the mise-tools, global-instructions and skills steps
only — the ones that make sense to refresh without redoing the full wizard.

## Visibility while it runs

Every step prints a `[n/total]` header before it starts, so it's always
clear which of the 13 steps is currently running — not just a wall of ✓
lines with no sense of progress.

Slow or network-bound commands (curl-piped installers, `npm install -g`,
`mise use -g`, `rtk init`, `codegraph install`, `npx skills add`) run
through `gea.proc.run_visible` instead of the usual captured `proc.run`:
their real stdout/stderr stream straight to the terminal. This matters for
two reasons — a long `npm install` shows its own progress instead of
looking frozen, and if a tool needs to ask something interactively (a
first-run confirmation), the prompt is actually visible and answerable
instead of being silently captured while gea waits on a timeout. `rtk init
-g` additionally passes `--auto-patch` (rtk's own non-interactive flag) so
it doesn't need to prompt in the first place.

A tool freshly installed via `mise use -g` is checked again right after
install (`platform.refresh_mise_shims_on_path()` prepends mise's shims dir
to this process's `PATH` first) — this is what stops `gea setup` from
reporting a tool as both "installed" and "still missing" in the same run
(mise's shims aren't on `PATH` until a shell re-sources its rc file, which
a script invoked mid-run never does on its own).
