# Builder agents

Ported from Cotizaciones' `scripts/agents.py`, generalized to be global
instead of per-repo:

- `~/gea/config.json["builders"]["profiles"]` — detected agent profiles
  (id, cli, model, quota pool, priority). Refreshed by `gea setup`/`gea
  agents refresh`.
- `~/gea/state.json` — which pools are exhausted and until when. Global on
  purpose: a rate limit belongs to the account, not to one project, so it
  now carries over between repos instead of resetting per-project.
- `gea.json["builders"]["allow"]` — optional per-project narrowing to a
  subset of profile ids; `["builders"]["mode"]` is `ask`/`auto`.

`gea agents available` prints the mode and every non-exhausted, allowed
profile. `gea agents start <id>` reuses an existing `builder-<id>` herdr
pane or splits a sibling pane in the current tab (same heuristic as the
Cotizaciones skill: wide pane splits right, narrow/tall splits down).
`gea agents check <id>` reads the pane and marks its whole pool exhausted
if it matches a rate-limit pattern.

`gea delegate <task-id> [--agent <id>]` picks the requested (or
highest-priority available) agent, starts its pane, and sends a short
prompt pointing at the task file — the task itself carries the plan, so the
prompt stays short. Unlike Claude Code's own delegar skill, this is a
blocking CLI call (`herdr agent prompt --wait`): there's no harness here to
resume a backgrounded wait.
