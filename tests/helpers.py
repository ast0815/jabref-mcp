"""Shared test helpers."""

from __future__ import annotations

import stat
import textwrap
from pathlib import Path


def write_fake_jabref(tmp_path: Path, exit_code: int = 0) -> Path:
    """Create a fake `jabref` executable that logs its argv and exits."""
    log = tmp_path / "calls.log"
    script = tmp_path / "fake-jabref"
    script.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            printf '%s\\n' "$@" >> "{log}"
            echo "fake jabref: imported"
            exit {exit_code}
            """
        )
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script