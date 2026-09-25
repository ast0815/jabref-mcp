from __future__ import annotations

from pathlib import Path

from jabref_mcp.bibtex_io import (
    LibrarySet,
    entry_bibtex,
    linked_files,
    load_library,
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


def test_bare_month_names_are_braced_before_parsing(tmp_path):
    bib = tmp_path / "months.bib"
    bib.write_text(
        "@article{a2024, title={T}, month = July},\n"
        "@article{b2024, title={T2}, month = july,\n"
        "  year = 2024}\n",
        encoding="utf-8",
    )
    ls = LibrarySet(bib_files=[str(bib)])
    months = {e["ID"]: e["month"] for _, e in ls.all_entries()}
    # Braced literals keep their original spelling (july!="July").
    assert months == {"a2024": "July", "b2024": "july"}


def test_full_month_names_inside_braces_or_quotes_untouched(tmp_path):
    bib = tmp_path / "months2.bib"
    bib.write_text(
        '@article{c2024, title={Written in July 2020}, month = "July"},\n',
        encoding="utf-8",
    )
    ls = LibrarySet(bib_files=[str(bib)])
    _, entry = ls.find_entry("c2024")  # type: ignore[assignment]
    assert entry["title"] == "Written in July 2020"
    assert entry["month"] == "July"


def test_literal_quotes_in_braced_values_do_not_break_scanning(tmp_path):
    # Regression: titles/abstracts commonly contain literal " quotes; the
    # scanner must treat them as text, not string delimiters, or it drifts
    # and misses later bare months.
    bib = tmp_path / "quotes.bib"
    bib.write_text(
        '@article{q2020, title={Corrigendum to "The Aachen gas-database v2021.2"},\n'
        "  month = July,\n"
        "  year = 2022}\n",
        encoding="utf-8",
    )
    ls = LibrarySet(bib_files=[str(bib)])
    _, entry = ls.find_entry("q2020")  # type: ignore[assignment]
    assert entry["month"] == "July"
    assert "The Aachen gas-database v2021.2" in entry["title"]


def test_nonstandard_entry_type_kept(tmp_path):
    bib = tmp_path / "electronic.bib"
    bib.write_text(
        "@Electronic{NuDat, title={T}, howpublished={Web}}\n", encoding="utf-8"
    )
    ls = LibrarySet(bib_files=[str(bib)])
    hits = ls.all_entries()
    assert [(e["ENTRYTYPE"], e["ID"]) for _, e in hits] == [("electronic", "NuDat")]


def test_undefined_string_raises_helpful_error(tmp_path):
    import pytest

    bib = tmp_path / "bad.bib"
    bib.write_text(
        "@article{d2024, title={T}, publisher = UnpublishedPress}\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="UnpublishedPress".lower()):
        load_library(str(bib))