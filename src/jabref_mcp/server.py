"""FastMCP server exposing a JabRef 5.x bibliography to OpenCode.

Read paths parse the configured ``.bib`` files directly; the only write path is
the official JabRef CLI import (``jabref --importBibtex``), so entries are
added through JabRef itself - the .bib files are never edited here.
"""

from __future__ import annotations

from fastmcp import FastMCP

from .bibtex_io import LibrarySet, entry_bibtex, entry_compact, linked_files
from .config import Config
from .jabref_client import ImportError, import_bibtex

SERVER_NAME = "jabref"


def create_app(config: Config | None = None) -> FastMCP:
    """Build the MCP application for the given configuration."""
    cfg = config or Config.from_env()
    library_set = LibrarySet(bib_files=cfg.bib_files, pdf_root=cfg.pdf_root)

    mcp = FastMCP(SERVER_NAME)

    @mcp.tool()
    def list_libraries() -> str:
        """List the configured JabRef libraries (the .bib files the server reads)
        with the number of parsed entries in each."""
        lines = []
        for lib in library_set.libraries():
            lines.append(f"{lib.name} ({len(lib.entries)} entries) - {lib.path}")
            for err in lib.parse_errors:
                lines.append(f"  warning: {err}")
        if not lines:
            return "No libraries configured. Set JABREF_MCP_BIB_FILES (comma-separated .bib paths) or place .bib files in the working directory."
        return "\n".join(lines)

    @mcp.tool()
    def list_entries(limit: int = 100) -> str:
        """List entries in the JabRef library (citation key, authors, year, title, venue, DOI), most useful for getting an overview or picking citation keys."""
        hits = library_set.all_entries()
        if limit > 0:
            hits = hits[:limit]
        if not hits:
            return "No entries found."
        return "\n".join(entry_compact(entry) for _, entry in hits)

    @mcp.tool()
    def search(
        query: str = "",
        field: str | None = None,
        author: str | None = None,
        year: str | None = None,
        year_from: str | None = None,
        year_to: str | None = None,
        tag: str | None = None,
        limit: int = 10,
    ) -> str:
        """Search the JabRef library. Returns matching entries as 'key | authors | year | title | venue | doi'.

        Args:
            query: space-separated terms; every term must match (AND). Matches case-insensitively across all fields
                (title, author, keywords, abstract, ...) unless `field` is given.
            field: restrict the search to a single BibTeX field, e.g. "title", "author", "year", "doi", "abstract".
            author: only entries whose author field contains this substring.
            year: exact year match (single entry year).
            year_from / year_to: inclusive year range.
            tag: only entries whose keywords/tags contain this substring.
            limit: maximum number of results (0 = no limit).
        """
        try:
            hits = library_set.search(
                query=query or None,
                field=field,
                author=author,
                year=year,
                year_from=year_from,
                year_to=year_to,
                tag=tag,
                limit=limit,
            )
        except ValueError as exc:
            return f"Invalid search parameters: {exc}"
        if not hits:
            return "No matches found."
        return "\n".join(
            f"[{lib.name}] {entry_compact(entry)}" for lib, entry in hits
        )

    @mcp.tool()
    def get_entry(citation_key: str) -> str:
        """Get the full record for one citation key: complete BibTeX plus the resolved attached files
        (needed for summarization). Raises an error if the key does not exist."""
        found = library_set.find_entry(citation_key)
        if found is None:
            raise ValueError(
                f"No entry with citation key '{citation_key}'. Use search() or list_entries() to find valid keys."
            )
        lib, entry = found
        files = linked_files(entry, lib, library_set.pdf_root)
        parts = [
            f"Library: {lib.name}",
            f"Citation key: {entry.get('ID')}",
            "Attached files:",
        ]
        if files:
            for f in files:
                status = "exists" if f.exists else "MISSING"
                parts.append(f"  - [{status}] {f.file_type or 'file'}: {f.path}")
                if f.description:
                    parts[-1] += f"  ({f.description})"
        else:
            parts.append("  (none)")
        parts.append("")
        parts.append("BibTeX:")
        parts.append(entry_bibtex(entry))
        return "\n".join(parts)

    @mcp.tool()
    def get_pdf(citation_key: str) -> str:
        """Return the absolute file paths of the PDFs attached to an entry, so the assistant can read and
        summarize them. Only existing files are returned; a key with no PDF raises an error."""
        found = library_set.find_entry(citation_key)
        if found is None:
            raise ValueError(
                f"No entry with citation key '{citation_key}'. Use search() or list_entries() to find valid keys."
            )
        lib, entry = found
        files = linked_files(entry, lib, library_set.pdf_root)
        pdfs = [f for f in files if f.exists and (f.file_type.lower() == "pdf" or f.path.lower().endswith(".pdf"))]
        if not pdfs:
            existing = [f for f in files if f.exists]
            hint = ", ".join(f.path for f in existing) if existing else "none"
            raise ValueError(
                f"No PDF attached to '{citation_key}' (attached files: {hint}). "
                "Use get_entry() to inspect the record, or attach a file in JabRef first."
            )
        return "\n".join(f.path for f in pdfs)

    @mcp.tool()
    def add_entry(bibtex: str, timeout: int | None = None) -> str:
        """Add a new entry to the JabRef library - the ONLY supported way of adding entries.

        This requests an import through JabRef's official CLI API (`jabref --importBibtex`), which means:
        - the entry is sent to the library that is OPEN in JabRef, with JabRef's own duplicate detection;
        - JabRef may ask you to accept the import before you save the library;
        - the .bib file is never modified by this server.
        Requires JabRef to be running with 'Listen to remote operation on port' enabled
        (Preferences -> Network), same as for the official browser extension.

        Args:
            bibtex: a complete BibTeX entry, e.g. '@article{key, title={...}, author={...}, year={2024}}'.
            timeout: optional override of the import timeout in seconds.

        Returns the canonical BibTeX that was sent to JabRef. A successful return confirms
        dispatch to JabRef, not that the entry has already been accepted and saved.

        Workflow after successful dispatch:
        - Ask the user to accept and save the import in JabRef if prompted, and to confirm
          when the library has been saved before attempting verification.
        - Do not claim that the entry is persisted yet.
        - After the user confirms saving, verify with search using stable metadata such as
          title, DOI, or author, rather than relying only on the submitted citation key.
        - JabRef may replace the submitted citation key; use the key returned by search when
          calling get_entry or get_pdf.
        - Read tools automatically detect the saved file. Do not ask for an MCP restart.
        """
        bibtex = bibtex.strip()
        if not bibtex:
            raise ValueError("Empty BibTeX. Provide one complete entry, e.g. '@article{key, title={...}}'.")
        # Validate before handing over to JabRef - reject input that is not (parseable as) BibTeX.
        try:
            import bibtexparser

            db = bibtexparser.loads(bibtex)
            if not db.entries:
                raise ValueError
            canonical = entry_bibtex(db.entries[0])
        except Exception as exc:
            raise ValueError(
                "Could not parse the argument as BibTeX. Provide one complete entry, e.g. "
                "'@article{key, title={The Title}, author={Doe, Jane and Roe, Richard}, year={2024}}'."
            ) from exc
        try:
            result = import_bibtex(canonical, timeout=timeout or cfg.import_timeout, jabref_bin=cfg.jabref_bin)
        except ImportError as exc:
            raise RuntimeError(str(exc)) from exc
        if not result.ok:
            detail = result.stderr or result.stdout or f"exit code {result.returncode}"
            raise RuntimeError(
                f"JabRef import command failed (exit code {result.returncode}): {detail}\n"
                "Make sure JabRef is running and 'Listen to remote operation on port' is "
                "enabled under Preferences -> Network."
            )
        return (
            "Entry sent to JabRef (the library currently open in JabRef; JabRef applies "
            "its own duplicate detection). JabRef may ask you to accept the import; save "
            "the library and confirm when done. Then verify with search using stable "
            "metadata because JabRef may have changed the citation key. MCP reads refresh "
            "automatically; no restart is needed. No .bib file was modified by this server.\n"
            f"Sent BibTeX:\n{canonical}"
        )

    return mcp


def main(config: Config | None = None) -> None:
    app = create_app(config)
    app.run(transport="stdio")


if __name__ == "__main__":
    main()