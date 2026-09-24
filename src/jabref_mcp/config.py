"""Configuration for the JabRef MCP server.

All settings are read from environment variables (JABREF_MCP_*) so the server
can be started from OpenCode without extra files.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    if not raw:
        return default
    return [part.strip() for part in raw.split(",") if part.strip()]


def default_bib_files() -> list[str]:
    """Default: every *.bib in the current working directory."""
    return sorted(str(p) for p in Path.cwd().glob("*.bib"))


@dataclass
class Config:
    """Runtime configuration of the MCP server."""

    #: Paths to the .bib library files that are parsed for reading/searching.
    bib_files: list[str] = field(default_factory=default_bib_files)

    #: Optional root used to resolve relative attached-file paths that do not
    #: exist next to the .bib file.
    pdf_root: str | None = None

    #: Executable (or command prefix) used to run JabRef for imports, e.g.
    #: "jabref" or "flatpak-spawn --host jabref".
    jabref_bin: str | None = None

    #: Timeout in seconds for an import call.
    import_timeout: int = 90

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            bib_files=_env_list("JABREF_MCP_BIB_FILES", default_bib_files()),
            pdf_root=os.environ.get("JABREF_MCP_PDF_ROOT") or None,
            jabref_bin=os.environ.get("JABREF_MCP_JABREF_BIN") or None,
            import_timeout=int(os.environ.get("JABREF_MCP_IMPORT_TIMEOUT", "90")),
        )