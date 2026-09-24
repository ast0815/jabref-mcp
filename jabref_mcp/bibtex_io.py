"""Read-side access to JabRef 5.x libraries.

JabRef 5.x exposes no read API, so the library is parsed from its ``.bib``
files. This module loads the files, strips JabRef metadata comments (which are
not entries), parses the remaining BibTeX with ``bibtexparser``, and offers
search / lookup / attached-file resolution on top.

Intentional limitation: entry *additions* never go through this module. The
only write path is the official JabRef import API (see ``jabref_client.py``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import bibtexparser
from bibtexparser.bibdatabase import BibDatabase

# Fields that are "structural" in bibtexparser's dict representation.
_STRUCTURAL_FIELDS = frozenset({"ENTRYTYPE", "ID"})


def strip_jabref_comments(text: str) -> str:
    """Remove ``@comment{...}`` blocks (e.g. ``jabref-meta``) from BibTeX text.

    JabRef stores non-entry metadata in ``@comment`` blocks; bibtexparser
    chokes on some of them (notably ``grouping:``), so they are removed here.
    Block scanning is brace-aware to survive nested braces.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    lower = text.lower()
    while i < n:
        at = lower.find("@comment", i)
        if at == -1:
            out.append(text[i:])
            break
        out.append(text[i:at])
        j = at + len("@comment")
        # Make sure we matched the keyword, not "comment" inside an identifier.
        if j < n and (text[j].isalnum() or text[j] == "_"):
            out.append(text[at:j])
            i = j
            continue
        k = j
        while k < n and text[k] in " \t\r\n":
            k += 1
        if k < n and text[k] == "{":
            depth = 1
            k += 1
            while k < n and depth > 0:
                if text[k] == "{":
                    depth += 1
                elif text[k] == "}":
                    depth -= 1
                k += 1
            i = k  # skip the whole block
        else:
            # Bare "@comment" without braces -> drop to end of line.
            eol = text.find("\n", k)
            i = n if eol == -1 else eol + 1
    return "".join(out)


@dataclass
class Library:
    """A parsed ``.bib`` library file."""

    path: str
    entries: list[dict] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return Path(self.path).name

    def resolve_relative(self, rel: str) -> Path:
        return Path(self.path).resolve().parent / rel


@dataclass
class LinkedFile:
    description: str
    path: str  # absolute (or best-effort resolved) path
    file_type: str
    exists: bool


def load_library(path: str) -> Library:
    """Parse one .bib file (metadata comments stripped)."""
    lib = Library(path=path)
    try:
        raw = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        lib.parse_errors.append(f"cannot read {path}: {exc}")
        return lib
    cleaned = strip_jabref_comments(raw)
    db: BibDatabase = bibtexparser.loads(cleaned)
    for entry in db.entries:
        if entry.get("ENTRYTYPE", "").lower() in {"comment", "string", "preamble"}:
            continue
        lib.entries.append(entry)
    return lib


def load_libraries(paths: list[str]) -> list[Library]:
    return [load_library(p) for p in paths]


def entry_bibtex(entry: dict) -> str:
    """Re-serialize one parsed entry as BibTeX."""
    etype = entry.get("ENTRYTYPE", "misc")
    key = entry.get("ID", "")
    lines = [f"@{etype}{{{key},"]
    for field_name in sorted(entry):
        if field_name in _STRUCTURAL_FIELDS:
            continue
        value = str(entry[field_name])
        lines.append(f"  {field_name.lower()} = {{{value}}},")
    lines.append("}")
    return "\n".join(lines)


def entry_compact(entry: dict) -> str:
    """One-line summary used in search/list output."""
    def f(name: str) -> str:
        return (entry.get(name) or "").strip()

    authors = _shorten_authors(f("author"))
    title = f("title")
    year = f("year")
    venue = f("journal") or f("booktitle") or f("publisher")
    parts = [entry.get("ID", "?")]
    if authors:
        parts.append(authors)
    if year:
        parts.append(year)
    if title:
        parts.append(title)
    if venue:
        parts.append(venue)
    if entry.get("doi"):
        parts.append(f"doi:{entry['doi']}")
    return " | ".join(parts)


def _shorten_authors(authors: str, max_authors: int = 3) -> str:
    if not authors:
        return ""
    parts = [a.strip() for a in authors.split(" and ") if a.strip()]
    if len(parts) > max_authors:
        return ", ".join(parts[:max_authors]) + " et al."
    return ", ".join(parts)


def linked_files(entry: dict, library: Library, pdf_root: str | None) -> list[LinkedFile]:
    """Resolve the entry's attached files to absolute paths.

    Relative paths are resolved against the library directory and,
    as a fallback, against ``pdf_root``.
    """
    results: list[LinkedFile] = []
    raw = (entry.get("file") or "").strip()
    if not raw:
        return results
    base = Path(library.path).resolve().parent
    roots = [base]
    if pdf_root:
        roots.append(Path(pdf_root).expanduser().resolve())

    for segment in raw.split(";"):
        segment = segment.strip()
        if not segment:
            continue
        file_type = ""
        if segment.count(":") >= 2:
            description, rel, file_type = segment.split(":", 2)
        else:
            description, rel = "", segment
        candidate: Path | None = None
        for root in roots:
            candidate = root / rel
            if candidate.exists():
                break
        if candidate is None:
            candidate = Path(rel)
        results.append(
            LinkedFile(
                description=description.strip(),
                path=str(candidate),
                file_type=file_type.strip(),
                exists=candidate.exists(),
            )
        )
    return results


class LibrarySet:
    """All configured libraries with search/lookup operations."""

    def __init__(self, bib_files: list[str], pdf_root: str | None = None):
        self.bib_files = list(bib_files)
        self.pdf_root = pdf_root
        self._libraries: list[Library] | None = None

    def reload(self) -> None:
        self._libraries = load_libraries(self.bib_files)

    def libraries(self) -> list[Library]:
        if self._libraries is None:
            self.reload()
        return self._libraries

    def all_entries(self) -> list[tuple[Library, dict]]:
        return [(lib, entry) for lib in self.libraries() for entry in lib.entries]

    def find_entry(self, citation_key: str) -> tuple[Library, dict] | None:
        key = citation_key.strip()
        for lib, entry in self.all_entries():
            if entry.get("ID") == key:
                return lib, entry
        return None

    def search(
        self,
        query: str | None = None,
        field: str | None = None,
        author: str | None = None,
        year: str | None = None,
        year_from: str | None = None,
        year_to: str | None = None,
        tag: str | None = None,
        limit: int = 10,
    ) -> list[tuple[Library, dict]]:
        """Case-insensitive search over the parsed libraries."""
        tokens = [t.lower() for t in (query or "").split() if t]
        hits: list[tuple[Library, dict]] = []

        def matches(e: dict) -> bool:
            if field:
                candidates = {field.lower(): e.get(field, "")}
            else:
                candidates = {k.lower(): v for k, v in e.items() if k != "ENTRYTYPE"}
            text = " ".join(str(v).lower() for v in candidates.values())
            if tokens and not all(t in text for t in tokens):
                return False
            if author and author.lower() not in (e.get("author") or "").lower():
                return False
            if tag and tag.lower() not in ((e.get("keywords") or "") + " " + (e.get("tags") or "")).lower():
                return False
            e_year = (e.get("year") or "").strip()
            if year and e_year != year.strip():
                return False
            if year_from and e_year and int(year_from) > _year_int(e_year):
                return False
            if year_to and e_year and int(year_to) < _year_int(e_year):
                return False
            return True

        for lib, entry in self.all_entries():
            if matches(entry):
                hits.append((lib, entry))
        if limit > 0:
            hits = hits[:limit]
        return hits


def _year_int(value: str) -> int:
    match = re.search(r"\d{4}", value)
    return int(match.group(0)) if match else 0