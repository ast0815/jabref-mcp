from __future__ import annotations

from pathlib import Path

from jabref_mcp.bibtex_io import (
    LibrarySet,
    entry_bibtex,
    linked_files,
    strip_jabref_comments,
)

SAMPLE = Path(__file__).parent / "sample.bib"


def make_set(**kwargs) -> LibrarySet:
    kwargs.setdefault("bib_files", [str(SAMPLE)])
    return LibrarySet(**kwargs)


def test_strip_jabref_comments_removes_blocks():
    text = SAMPLE.read_text(encoding="utf-8")
    cleaned = strip_jabref_comments(text)
    assert "@comment" not in cleaned.lower()
    assert "@article{knuth1984literate" in cleaned
    assert "@string{jacm" in cleaned


def test_load_and_count_entries():
    ls = make_set()
    libs = ls.libraries()
    assert len(libs) == 1
    keys = {e["ID"] for e in libs[0].entries}
    assert keys == {"knuth1984literate", "vaswani2017attention", "cormode2008sketching", "chocolate2026yummy"}


def test_search_by_title_word():
    ls = make_set()
    hits = ls.search(query="attention")
    assert [e["ID"] for _, e in hits] == ["vaswani2017attention"]


def test_search_all_tokens_must_match():
    ls = make_set()
    assert ls.search(query="attention chocolate") == []
    assert len(ls.search(query="chocolate yummy")) == 1


def test_search_field_scoped():
    ls = make_set()
    assert len(ls.search(query="knuth", field="author")) == 1
    assert ls.search(query="knuth", field="title") == []


def test_search_filters():
    ls = make_set()
    assert len(ls.search(query="", year="2017")) == 1
    assert len(ls.search(query="", year_from="2008", year_to="2017")) == 2
    assert {e["ID"] for _, e in ls.search(tag="transformer")} == {"vaswani2017attention"}
    assert {e["ID"] for _, e in ls.search(author="cormode")} == {"cormode2008sketching"}


def test_find_entry_and_bibtex_roundtrip():
    ls = make_set()
    found = ls.find_entry("knuth1984literate")
    assert found is not None
    lib, entry = found
    bib = entry_bibtex(entry)
    assert bib.startswith("@article{knuth1984literate,")
    assert "title = {Literate Programming}" in bib
    assert "doi" in bib.lower()


def test_linked_files_resolution():
    ls = make_set()
    lib, entry = ls.find_entry("knuth1984literate")  # type: ignore[assignment]
    files = linked_files(entry, lib, None)
    assert len(files) == 1
    assert files[0].file_type == "PDF"
    assert files[0].exists is True  # dummy PDF lives next to the sample
    assert Path(files[0].path).is_absolute()
    assert files[0].path.endswith("knuth_literate.pdf")


def test_linked_files_pdf_root_fallback(tmp_path):
    """Relative paths that are absent next to the .bib are resolved against pdf_root."""
    from jabref_mcp.bibtex_io import Library

    lib = Library(path=str(SAMPLE), entries=[])
    entry = {"file": "Desc:missing_relative.pdf:PDF"}

    without_root = linked_files(entry, lib, None)
    assert without_root and without_root[0].exists is False

    root = tmp_path / "pdfs"
    root.mkdir()
    (root / "missing_relative.pdf").write_text("dummy")
    with_root = linked_files(entry, lib, str(root))
    assert with_root[0].exists is True
    assert Path(with_root[0].path) == (root / "missing_relative.pdf").resolve()


def test_missing_key_not_found():
    ls = make_set()
    assert ls.find_entry("does-not-exist") is None