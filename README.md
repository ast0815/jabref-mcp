# jabref-mcp

A [Model Context Protocol](https://modelcontextprotocol.io/) server that lets
OpenCode (and other MCP clients) work with your **JabRef 5.x** bibliography:

- **Search** your library (title / author / year / keywords / DOI and other BibTeX fields)
- **Read** full records (BibTeX + abstract) and resolve **attached PDF paths**, so the assistant can read and **summarize papers** itself
- **Add** new entries through JabRef's command-line import, never by editing your `.bib` files

## Why this shape (JabRef 5.x)

JabRef 5.x does not expose a supported HTTP read API for this project, so:

| Operation | Mechanism |
|---|---|
| Search / read / list | parse your `.bib` file(s) locally |
| Add an entry | `jabref --importBibtex "<bibtex>"` through JabRef's command-line interface. When JabRef's single-instance/remote-operation feature is enabled, the command can be forwarded to the running instance and its currently open library. |

The MCP transport is **stdio**: the server is launched as a local process and
does not listen on a network port. JabRef's remote-operation setting is a
separate JabRef feature.

## Requirements

- Python ≥ 3.10 and [uv](https://docs.astral.sh/uv/)
- JabRef 5.x installed, with **`jabref` on PATH** (or `JABREF_MCP_JABREF_BIN` set)
- To add entries to an already-running JabRef instance, enable **Enforce single
  JabRef instance (and allow remote operations)** under **Preferences → General**.
  In older JabRef 5.x releases this option may be under **Network**.

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
`uv run jabref-mcp`, i.e. the code in this checkout). To use it, start OpenCode
from this directory. Alternatively register globally:

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
  through JabRef, which handles duplicate detection and library updates.
  `add_entry` returns after dispatching the import; JabRef may still require you
  to accept it and save the library. After saving, verify with `search` using stable
  metadata such as title, DOI, or author because JabRef may replace the submitted
  citation key.
- Configured `.bib` files are cached, but checked for changes before every read.
  After JabRef saves a library, the next MCP read automatically reparses only the
  changed file; restarting the MCP is not required.
- This project targets JabRef 5.x. JabRef 6.x has a different CLI/API surface
  and is not claimed to be supported.
