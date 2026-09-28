# Commit conventions

## Format

[Conventional Commits](https://www.conventionalcommits.org/), in {commit_lang}:

```
<type>(<scope>): <imperative, lowercase, no trailing period>

<optional body: why, not what — the diff already shows the what>
```

### Types

`feat` `fix` `refactor` `docs` `chore` `test` `perf`

## Atomicity

One commit = one logical change.

## Strictly forbidden

- `Co-authored-by` in the body or trailer.
- Any tool signature ("Generated with", robot emojis, mentions of the
  agent/AI that wrote the code).
- Emojis in the subject.
