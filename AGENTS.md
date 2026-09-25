# Repository rules

## Never commit references to files outside this repository

Do **not** commit — in any form (code, config values, comments, docs, sample
data, commit messages) — references to files or paths outside this repository:
machine-specific locations, the author's own directories (e.g.
`/home/<user>/...`), other checkouts, or credentials.

Concretely:

- `opencode.jsonc` and similar configs ship with in-repo examples such as
  `tests/sample.bib`. If you need a real (out-of-repo) value locally, keep it
  as an **uncommitted working-tree change** only.
- Before committing, double-check diffs for absolute paths and `~`-style
  references. If a change must be local-only, leave it unstaged.
- Environment variables in files inside the repo must not point outside the
  repo.