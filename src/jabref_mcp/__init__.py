"""jabref-mcp: MCP server bridging OpenCode and a JabRef 5.x bibliography."""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__ = _pkg_version("jabref-mcp")
except PackageNotFoundError:  # pragma: no cover - source checkout without install
    __version__ = "0.0.0"