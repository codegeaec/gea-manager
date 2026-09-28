# gea skills

Four skills live in `src/gea/skills/gea-{init,plan,delegate,review}/` —
packaged with the wheel (not a top-level repo folder) so `gea skills sync`
can install them on any machine, not just from a gea-manager checkout.

- **gea-init** — runs `gea init`, then does what the wizard can't: turns a
  conversation with the user into `docs/00-vision-product.md` and a
  starter glossary.
- **gea-plan** — grills the request for the couple of questions that would
  actually change the plan, checks for existing code first, writes it with
  `gea task new` / `gea subtask new`.
- **gea-delegate** — the global, gea.json-driven version of Cotizaciones'
  `delegar` skill: `gea agents available` → `gea delegate <ID>` → read the
  diff, not the terminal → review → close.
- **gea-review** — the review/close half on its own, for re-reviewing
  without going through delegation again.

`gea skills sync` installs these plus a short list of third-party skills
(`src/gea/setup/skills.py`'s `THIRD_PARTY_SKILLS` — ponytail, the
vercel-labs bundle, ui-ux-pro-max) into every detected agent via `npx
skills add -g -a <agent-ids>`.
