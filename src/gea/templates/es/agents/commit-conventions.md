# Convenciones de commits

## Formato

[Conventional Commits](https://www.conventionalcommits.org/), en {commit_lang}:

```
<tipo>(<scope>): <descripción en imperativo, minúscula, sin punto final>

<cuerpo opcional: el porqué, no el qué — el diff ya muestra el qué>
```

### Tipos

`feat` `fix` `refactor` `docs` `chore` `test` `perf`

## Atomicidad

Un commit = un cambio lógico.

## Terminantemente prohibido

- `Co-authored-by` en el cuerpo o trailer.
- Firma de la herramienta ("Generated with", emojis de robot, menciones del
  agente/IA que escribió el código).
- Emojis en el asunto.
