# Agent notes

## Project shape

- This is a single Python package under `src/jabref_mcp`. The console entrypoint is
  `jabref_mcp.__main__:main`; it starts a FastMCP server over stdio.
- `server.py` wires the MCP tools, `bibtex_io.py` handles `.bib` parsing/search and
  attachment resolution, and `jabref_client.py` is the only import/write path.
- Do not add a direct `.bib` write path: `add_entry` must use
  `jabref --importBibtex`; JabRef 5.x has no read HTTP API in this project.
- Runtime configuration is read from `JABREF_MCP_*` environment variables. Without
  `JABREF_MCP_BIB_FILES`, reads use sorted `*.bib` files in the process working
  directory; the variable accepts comma-separated paths. `JABREF_MCP_JABREF_BIN`
  may be a command prefix, not only a filename.

## Development

- Set up with `uv sync` (Python 3.10+); run the full suite with `uv run pytest`.
- Start the local server with `uv run jabref-mcp`; `opencode.jsonc` uses this
  checkout-aware command rather than a published package.
- `pyproject.toml` sets `testpaths = ["tests"]`, `pythonpath = ["src"]`, and
  `asyncio_mode = "auto"`. Focus a run with a path plus `-k <expression>` or a
  pytest node ID, e.g. `uv run pytest tests/test_server.py -k add_entry`.
- Import tests use the fake executable from `tests/helpers.py` and do not require a
  live JabRef. A real `add_entry` requires JabRef 5.x running with remote operation
  enabled.
- `uv build` is the package/release check. The release workflow checks out full git
  history because the version is supplied by `hatch-vcs`; do not edit the version
  manually.
- There is no configured lint, formatter, or typecheck command in this repository.

## Read-path gotchas

- `LibrarySet` caches parsed libraries but checks filesystem metadata before every
  read and automatically reparses only changed files. Preserve this behavior when
  changing the read path; external JabRef saves must not require an MCP restart.
- `bibtex_io.load_library` deliberately removes JabRef `@comment` metadata and
  braces bare full-month values before calling `bibtexparser`; preserve the
  regression tests if changing this preprocessing.
- Relative attachment paths are tried beside the `.bib` file first, then against
  `JABREF_MCP_PDF_ROOT`.

## Local-only paths and commit safety

- Never commit machine-specific or out-of-repository file references in code,
  configuration, docs, fixtures, or commit messages.
- The committed `opencode.jsonc` example uses `tests/sample.bib`. Any real
  `JABREF_MCP_BIB_FILES` override belongs only in the working tree and must stay
  unstaged.
- Before committing, inspect the diff for absolute or `~`-style paths, machine-
  specific locations, other checkouts, or credentials. Environment values committed
  inside the repository must not point outside it.
