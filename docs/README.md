# gea-manager docs

Design notes for `gea` itself, one file per area:

| Doc | Covers |
|---|---|
| [`i18n.md`](./i18n.md) | Bilingual UI catalogs (`gea.i18n`), language resolution |
| [`setup.md`](./setup.md) | `gea setup`'s steps: tools, mise, agents, rtk, codegraph, shadcn cleanup, global instructions, skills, legacy cleanup |
| [`agents.md`](./agents.md) | Builder profiles, global exhaustion state, `gea delegate` |
| [`init.md`](./init.md) | `gea init`'s wizard, templates, `gea verify` |
| [`workspace.md`](./workspace.md) | `gea` with no arguments (herdr tab setup) |
| [`skills.md`](./skills.md) | The bundled `gea-*` skills and third-party skill sync |
| [`commands.md`](./commands.md) | Schema versions, `--dry-run`, uninstall, task types, checkpoints, secrets, lint, autonomy |

For usage (not design), see the root `README.md`.
