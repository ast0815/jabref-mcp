"""Write-side access to JabRef 5.x.

JabRef 5.x has no HTTP API for importing entries. The official, supported
channel - the same one the official browser extension uses through its
``jabrefHost.py`` backend - is the command line::

    jabref --importBibtex "<bibtex>"

When JabRef is already running with "Listen to remote operation on port"
enabled (Preferences -> Network), the new instance hands the arguments over to
the running one, which imports the entry into the *currently open library*
(including JabRef's own duplicate detection). The .bib file is never touched
by this module.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class ImportError(RuntimeError):
    """Raised when the entry could not be imported via the JabRef CLI."""


@dataclass
class ImportResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int
    command: list[str]


def find_jabref_command(explicit: str | None = None) -> list[str]:
    """Resolve the JabRef executable, like jabrefHost.py does.

    Returns a command prefix (list of argv tokens) so that wrappers such as
    ``flatpak-spawn --host jabref`` are supported.
    """
    if explicit:
        tokens = shlex.split(explicit)
        if not tokens:
            raise ImportError("JABREF_MCP_JABREF_BIN is set but empty")
        return tokens
    for name in ("jabref", "JabRef"):
        found = shutil.which(name)
        if found:
            return [found]
    # Portable install: bin/JabRef next to this package's parent.
    portable = Path(__file__).resolve().parent.parent / "bin" / "JabRef"
    if portable.exists():
        return [str(portable)]
    raise ImportError(
        "Could not find the JabRef executable. Install JabRef so that 'jabref' "
        "is on PATH, or set JABREF_MCP_JABREF_BIN to its path or command "
        "(e.g. 'flatpak-spawn --host jabref')."
    )


def import_bibtex(bibtex: str, timeout: int = 90, jabref_bin: str | None = None) -> ImportResult:
    """Import a single BibTeX entry via ``jabref --importBibtex``.

    Never writes to the .bib file; JabRef performs the import itself.
    """
    cmd = find_jabref_command(jabref_bin) + ["--importBibtex", bibtex]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise ImportError(
            f"Could not run '{cmd[0]}': {exc}. Install JabRef, put 'jabref' on "
            "PATH or set JABREF_MCP_JABREF_BIN."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise ImportError(
            f"JabRef did not finish importing within {timeout}s. "
            f"Command: {' '.join(cmd)}"
        ) from exc
    return ImportResult(
        ok=proc.returncode == 0,
        stdout=(proc.stdout or "").strip(),
        stderr=(proc.stderr or "").strip(),
        returncode=proc.returncode,
        command=cmd,
    )