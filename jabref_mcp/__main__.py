"""Entry point so `python -m jabref_mcp` and the `jabref-mcp` script work."""

from __future__ import annotations

from .server import main

if __name__ == "__main__":
    main()