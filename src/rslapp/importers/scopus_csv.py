"""Importador de arquivos CSV exportados do Scopus (FR-23, D-033)."""

from __future__ import annotations

import csv
import io
import re
from typing import Any

from rslapp.core.models import Affiliation, Author, Work
from rslapp.importers.base import BaseImporter, clean_doi, extract_year, parse_author_name


# FR-23, D-033: Importador de CSV Scopus
class ScopusCSVImporter(BaseImporter):
    """Lê e interpreta exportações CSV do Scopus."""

    format_id: str = "scopus_csv"

    def parse(self, content: str) -> list[Work]:
        """Interpreta CSV do Scopus e retorna a lista de obras Work."""
        works: list[Work] = []
        if not content or not content.strip():
            return works

        # Remove BOM se presente
        clean_content = content.lstrip("\ufeff")
        reader = csv.DictReader(io.StringIO(clean_content))
        if not reader.fieldnames:
            return works

        # Normaliza nomes de colunas em minúsculas sem pontuação
        field_map = {name: name.strip().lower() for name in reader.fieldnames if name}

        for row in reader:
            normalized_row = {field_map[k]: (v or "").strip() for k, v in row.items() if k in field_map}

            title = (
                normalized_row.get("title")
                or normalized_row.get("document title")
                or ""
            )
            doi = clean_doi(normalized_row.get("doi"))
            if not title and not doi:
                continue

            year = extract_year(normalized_row.get("year"))
            venue = normalized_row.get("source title") or normalized_row.get("journal")
            abstract = normalized_row.get("abstract") or None
            if abstract and abstract.lower() == "[no abstract available]":
                abstract = None

            # Autores
            authors: list[Author] = []
            author_names_str = (
                normalized_row.get("author full names")
                or normalized_row.get("authors")
                or ""
            )
            if author_names_str and author_names_str.lower() != "[no author name available]":
                # Scopus separa autores por ponto-e-vírgula ';' ou vírgula
                delim = ";" if ";" in author_names_str else ","
                for a_piece in author_names_str.split(delim):
                    cleaned_a = re.sub(r"\(\d+\)", "", a_piece).strip()
                    if cleaned_a:
                        authors.append(parse_author_name(cleaned_a))

            # Afiliações
            affil_str = normalized_row.get("affiliations") or ""
            if affil_str and authors:
                # Se houver afiliações, adiciona à lista do primeiro autor como contexto
                first_affil = affil_str.split(";")[0].strip()
                if first_affil:
                    authors[0].affiliations.append(Affiliation(name=first_affil))

            # Palavras-chave
            keywords: list[str] = []
            kw_raw = (
                normalized_row.get("author keywords")
                or normalized_row.get("index keywords")
                or ""
            )
            if kw_raw:
                for k in kw_raw.split(";"):
                    k_clean = k.strip()
                    if k_clean and k_clean not in keywords:
                        keywords.append(k_clean)

            # Citações
            citations: dict[str, int] = {}
            cited_by_raw = normalized_row.get("cited by")
            if cited_by_raw:
                with_digits = re.search(r"\d+", cited_by_raw)
                if with_digits:
                    citations["scopus"] = int(with_digits.group(0))

            # Identificador de fonte Scopus EID
            source_ids: dict[str, str] = {}
            eid = normalized_row.get("eid")
            if eid:
                source_ids["scopus"] = eid

            # Referências
            references: list[str] = []
            refs_raw = normalized_row.get("references")
            if refs_raw:
                for r in refs_raw.split(";"):
                    r_clean = r.strip()
                    if r_clean:
                        references.append(r_clean)

            # Tipo e Retratação (D-032)
            doc_type = (normalized_row.get("document type") or "article").lower()
            is_retracted = False
            retraction_details: dict[str, Any] | None = None
            if "retract" in doc_type or "retrata" in doc_type:
                is_retracted = True
                retraction_details = {
                    "source": "scopus_document_type",
                    "document_type": normalized_row.get("document type"),
                }
                work_type = "article"
            elif any(k in doc_type for k in ("review", "survey")):
                work_type = "review"
            elif any(k in doc_type for k in ("conference", "proceeding")):
                work_type = "conference-paper"
            elif "book" in doc_type:
                work_type = "book"
            else:
                work_type = "article"

            work = Work(
                title=title or f"Artigo sem título ({doi})",
                doi=doi,
                year=year,
                type=work_type,
                venue=venue,
                abstract=abstract,
                keywords=keywords,
                authors=authors,
                references=references,
                references_count=len(references),
                citations=citations,
                source_ids=source_ids,
                is_retracted=is_retracted,
                retraction_details=retraction_details,
            )
            works.append(work)

        return works
