"""End-to-end tests of the MCP server via FastMCP's in-process client."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from jabref_mcp.config import Config
from jabref_mcp.server import create_app

SAMPLE = Path(__file__).parent / "sample.bib"


def make_app(**overrides) -> Client:
    kwargs = {"bib_files": [str(SAMPLE)], "import_timeout": 10, **overrides}
    return Client(create_app(Config(**kwargs)))


@pytest.fixture()
async def client():
    async with make_app() as c:
        yield c


def text_of(result) -> str:
    """Join text blocks of a CallToolResult."""
    parts = []
    for block in result.content:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
    return "".join(parts)


async def call(client: Client, tool: str, **args) -> str:
    return text_of(await client.call_tool(tool, args))


async def test_tools_registered(client: Client):
    tools = await client.list_tools()
    names = {t.name for t in tools}
    assert {
        "list_libraries",
        "list_entries",
        "search",
        "get_entry",
        "get_pdf",
        "add_entry",
    } <= names


async def test_list_libraries(client: Client):
    out = await call(client, "list_libraries")
    assert "sample.bib (4 entries)" in out


async def test_list_entries(client: Client):
    out = await call(client, "list_entries")
    assert "vaswani2017attention" in out
    assert "knuth1984literate" in out


async def test_search_tool(client: Client):
    out = await call(client, "search", query="attention")
    assert "vaswani2017attention" in out


async def test_search_matches_citation_key(client: Client):
    out = await call(client, "search", query="chocolate yummy")  # 'yummy' appears only in the citation key
    assert "chocolate2026yummy" in out


async def test_search_tool_no_match(client: Client):
    out = await call(client, "search", query="nonexistent-term-xyz")
    assert "No matches" in out


async def test_get_entry_returns_bibtex(client: Client):
    out = await call(client, "get_entry", citation_key="knuth1984literate")
    assert "@article{knuth1984literate," in out
    assert "Literate Programming" in out
    assert "knuth_literate.pdf" in out


async def test_get_entry_unknown_key_raises(client: Client):
    with pytest.raises(ToolError, match="No entry with citation key"):
        await client.call_tool("get_entry", {"citation_key": "nope"})


async def test_get_pdf_returns_path(client: Client):
    out = await call(client, "get_pdf", citation_key="knuth1984literate")
    assert out.endswith("knuth_literate.pdf") or "knuth_literate.pdf" in out


async def test_get_pdf_entry_without_pdf_raises(client: Client):
    # vaswani2017attention has no file field
    with pytest.raises(ToolError, match="No PDF attached"):
        await client.call_tool("get_pdf", {"citation_key": "vaswani2017attention"})


async def test_add_entry_validation_error(client: Client):
    with pytest.raises(ToolError, match="Could not parse"):
        await client.call_tool("add_entry", {"bibtex": "this is not bibtex"})


async def test_add_entry_empty_error(client: Client):
    with pytest.raises(ToolError, match="Empty BibTeX"):
        await client.call_tool("add_entry", {"bibtex": "   "})


async def test_add_entry_success_via_fake_jabref(tmp_path: Path):
    """Happy path: valid BibTeX is handed to `jabref --importBibtex` and reported as imported."""
    from helpers import write_fake_jabref

    fake = write_fake_jabref(tmp_path)
    bibtex = "@article{demo2024, title={Demo Paper}, author={Doe, Jane}, year={2024}}"

    app = make_app(jabref_bin=str(fake))
    async with app as client:
        out = text_of(await client.call_tool("add_entry", {"bibtex": bibtex}))

    assert "Entry imported" in out
    assert "@article{demo2024," in out

    calls = (tmp_path / "calls.log").read_text().splitlines()
    assert calls[0] == "--importBibtex"
    assert any("@article{demo2024," in c for c in calls)


async def test_add_entry_failure_via_fake_jabref(tmp_path: Path):
    """JabRef exits non-zero -> the tool reports the failure instead of pretending success."""
    from helpers import write_fake_jabref

    fake = write_fake_jabref(tmp_path, exit_code=1)

    app = make_app(jabref_bin=str(fake))
    async with app as client:
        with pytest.raises(ToolError, match="JabRef rejected the import"):
            await client.call_tool("add_entry", {"bibtex": "@article{k, title={T}}"})