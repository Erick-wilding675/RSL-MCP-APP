"""Importador de registros no formato BibTeX (FR-23, D-033)."""

from __future__ import annotations

import re
from typing import Any

from rslapp.core.models import Author, Work
from rslapp.importers.base import (
    BaseImporter,
    clean_doi,
    clean_latex,
    extract_year,
    parse_author_name,
)

_BIB_ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,]+),\s*(.*?)\n\s*\}", re.DOTALL | re.IGNORECASE)
_BIB_FIELD_RE = re.compile(
    r'(\w+)\s*=\s*(?:\{((?:[^{}]|\{[^{}]*\})*)\}|"([^"]*)"|(\d+))', re.DOTALL | re.IGNORECASE
)

_BIB_TYPE_MAP: dict[str, str] = {
    "article": "article",
    "inproceedings": "conference-paper",
    "conference": "conference-paper",
    "proceedings": "conference-paper",
    "book": "book",
    "incollection": "book-chapter",
    "phdthesis": "dissertation",
    "mastersthesis": "dissertation",
    "techreport": "report",
    "misc": "article",
}


# FR-23, D-033: Importador de arquivos BibTeX padrão (.bib)
class BibTeXImporter(BaseImporter):
    """Lê e interpreta dados bibliográficos no formato BibTeX."""

    format_id: str = "bibtex"

    def parse(self, content: str) -> list[Work]:
        """Interpreta texto no formato BibTeX e retorna a lista de obras Work."""
        works: list[Work] = []
        if not content or not content.strip():
            return works

        for match in _BIB_ENTRY_RE.finditer(content):
            raw_type = match.group(1).lower()
            work_type = _BIB_TYPE_MAP.get(raw_type, "article")
            body = match.group(3)

            fields: dict[str, str] = {}
            for fmatch in _BIB_FIELD_RE.finditer(body):
                k = fmatch.group(1).lower()
                v = next((g for g in fmatch.groups()[1:] if g is not None), "")
                fields[k] = clean_latex(v)

            title = fields.get("title", "")
            doi = clean_doi(fields.get("doi"))
            if not title and not doi:
                continue

            year = extract_year(fields.get("year"))
            venue = fields.get("journal") or fields.get("booktitle") or fields.get("school")
            abstract = fields.get("abstract")

            # Autores separados por ' and '
            authors: list[Author] = []
            author_str = fields.get("author", "")
            if author_str:
                for a_raw in author_str.split(" and "):
                    cleaned_name = a_raw.strip()
                    if cleaned_name:
                        authors.append(parse_author_name(cleaned_name))

            # Palavras-chave separadas por vírgula ou ponto-e-vírgula
            keywords: list[str] = []
            kw_str = fields.get("keywords") or fields.get("keyword") or ""
            if kw_str:
                delimiter = ";" if ";" in kw_str else ","
                keywords = [k.strip() for k in kw_str.split(delimiter) if k.strip()]

            # Checagem de retratação no campo note ou title
            note = fields.get("note", "")
            is_retracted = False
            retraction_details: dict[str, Any] | None = None
            if any(term in note.lower() for term in ("retrata", "retract", "expression of concern")):
                is_retracted = True
                retraction_details = {"source": "bibtex_note", "note": note}
            elif any(term in title.lower() for term in ("[retracted]", "(retracted)")):
                is_retracted = True
                retraction_details = {"source": "bibtex_title", "note": "Marcado como retratado no título"}

            work = Work(
                title=title or f"Artigo sem título ({doi})",
                doi=doi,
                year=year,
                type=work_type,
                venue=venue,
                abstract=abstract,
                keywords=keywords,
                authors=authors,
                is_retracted=is_retracted,
                retraction_details=retraction_details,
            )
            works.append(work)

        return works
