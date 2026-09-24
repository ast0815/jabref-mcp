from __future__ import annotations

import os
import textwrap
from pathlib import Path

from helpers import write_fake_jabref


def test_import_bibtex_success(tmp_path: Path):
    from jabref_mcp.jabref_client import import_bibtex

    fake = write_fake_jabref(tmp_path)
    result = import_bibtex("@article{x, title={Test}}", jabref_bin=str(fake), timeout=10)

    assert result.ok is True
    assert result.returncode == 0
    assert "--importBibtex" in result.command
    assert "@article{x, title={Test}}" in result.command

    calls = (tmp_path / "calls.log").read_text().splitlines()
    assert calls[0] == "--importBibtex"
    assert "@article{x, title={Test}}" in calls


def test_import_bibtex_failure(tmp_path: Path):
    from jabref_mcp.jabref_client import import_bibtex

    fake = write_fake_jabref(tmp_path, exit_code=1)
    result = import_bibtex("@article{x, title={Test}}", jabref_bin=str(fake), timeout=10)

    assert result.ok is False
    assert result.returncode == 1


def test_import_bibtex_no_binary_found():
    from jabref_mcp.jabref_client import ImportError, import_bibtex

    try:
        import_bibtex("@article{x}", jabref_bin="definitely-not-a-real-jabref-binary-xyz", timeout=5)
    except ImportError as exc:
        assert "Could not run" in str(exc) or "Find the JabRef executable" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ImportError")


def test_find_jabref_command_explicit(tmp_path: Path):
    from jabref_mcp.jabref_client import find_jabref_command

    fake = write_fake_jabref(tmp_path)
    assert find_jabref_command(str(fake)) == [str(fake)]


def test_find_jabref_command_multiword():
    from jabref_mcp.jabref_client import find_jabref_command

    # Allow wrappers such as flatpak-spawn --host jabref
    assert find_jabref_command("flatpak-spawn --host jabref") == ["flatpak-spawn", "--host", "jabref"]