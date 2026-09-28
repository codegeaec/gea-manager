# Commit conventions — gea-manager

## Format

[Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <imperative, lowercase, no trailing period>

<optional body: why, not what — the diff already shows the what>
```

- Subject in imperative mood: "add", "fix", "remove" — not "added"/"adding".
- Subject ≤ 72 characters.

### Types

`feat` `fix` `refactor` `docs` `chore` `test` `perf`

### Scopes

`cli` `setup` `agents` `tasks` `init` `workspace` `skills` `i18n` `docs`

## Atomicity

One commit = one logical change. Never mix a refactor with a new feature in
the same commit.

## Strictly forbidden

- `Co-authored-by` in the body or trailer.
- Any tool signature ("Generated with", robot emojis, mentions of
  Claude/AI in the message).
- Emojis in the subject.
