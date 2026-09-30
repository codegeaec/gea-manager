---
name: gea-delegate
description: Delegate an already-planned task (created with gea-plan) to a builder agent via herdr, wait for it, and review the resulting diff. Use when the user says "delegate this", "/gea-delegate TASK-00N", or a planned task is ready to implement and you want to spend your own tokens on the plan and review, not on writing the code.
---

# gea-delegate — hand a task to a builder

The working guide lives in gea itself, so every agent (with or without this
skill) follows the same steps. Run:

```bash
gea guide delegate
```

and follow exactly what it prints. It is written in the project's agents
language and matches the commands your installed gea actually has. For the
whole flow at once: `gea guide all`; the command cheat sheet is
`.agents/gea.md`.
