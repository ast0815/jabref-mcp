# jabref-mcp

A [Model Context Protocol](https://modelcontextprotocol.io/) server that lets
OpenCode (and other MCP clients) work with your **JabRef 5.x** bibliography:

- **Search** your library (title / author / year / keywords / DOI / full text)
- **Read** full records (BibTeX + abstract) and resolve **attached PDF paths**, so the assistant can read and **summarize papers** itself
- **Add** new entries — *only* through JabRef's official import API, never by editing your `.bib` files

## Why this shape (JabRef 5.x)

JabRef 5.x has **no HTTP read API** (that arrives in 6.x). So:

| Operation | Mechanism |
|---|---|
| Search / read / list | parse your `.bib` file(s) locally |
| Add an entry | `jabref --importBibtex "<bibtex>"` — the exact channel the official browser extension uses. With *Remote operation* enabled, the running JabRef imports into the **currently open library**, with its own duplicate detection. |

## Requirements

- Python ≥ 3.10 and [uv](https://docs.astral.sh/uv/)
- JabRef installed, with **`jabref` on PATH** (or `JABREF_MCP_JABREF_BIN` set)
- For adding entries: JabRef **running** with *Listen to remote operation on port* enabled
  (**Preferences → Network** — the same requirement as the official browser extension)

## Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `JABREF_MCP_BIB_FILES` | `*.bib` in the working directory | Comma-separated `.bib` paths |
| `JABREF_MCP_PDF_ROOT` | — | Optional base dir for resolving relative attached paths |
| `JABREF_MCP_JABREF_BIN` | `jabref` / `JabRef` on PATH | JabRef executable or command prefix (e.g. `flatpak-spawn --host jabref`) |
| `JABREF_MCP_IMPORT_TIMEOUT` | `90` | Import timeout (seconds) |

## Run / install

From a checkout (development):

```sh
uv sync
uv run jabref-mcp
```

From PyPI (published releases):

```sh
uvx jabref-mcp
```

Before a release is published, uvx can build straight from the GitHub repo:

```sh
uvx --from git+https://github.com/ast0815/jabref-mcp jabref-mcp
```

## Register with OpenCode

A project-level registration is already provided in `opencode.jsonc` (it runs
`uvx jabref-mcp`). To use it, start OpenCode from this directory. Alternatively
register globally:

```sh
opencode mcp add jabref -- uvx jabref-mcp
```

(Add `--global` to make it available in every project; then set
`JABREF_MCP_BIB_FILES` to your real libraries.) Check the connection with
`opencode mcp list` — it should report `connected`. Tools appear under
`tools.jabref.*`.

## Tools

- `list_libraries` — configured libraries and entry counts
- `list_entries` — overview of every entry
- `search` — keyword search with field / author / year / tag filters
- `get_entry` — full BibTeX + resolved attached files for a citation key
- `get_pdf` — absolute paths of the PDFs attached to an entry (feed to the assistant's PDF reader for summarizing)
- `add_entry` — import BibTeX via the official JabRef CLI (the only write path)

## Notes

- The server *reads* the `.bib` files; it never writes to them. Additions go
  through JabRef. Petty duplicate detection, group assignment, etc. are handled
  by JabRef itself.
- If your library changes in JabRef, re-run `search`/`get_entry` — the files
  are re-read per call.
- JabRef 6.x will (eventually) ship its own REST API; this server is a drop-in
  for 5.x and can later be re-pointed at `localhost:23119`.