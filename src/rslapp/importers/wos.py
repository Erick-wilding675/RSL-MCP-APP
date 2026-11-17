"""Importador de exportações do Web of Science (TSV delimitado por tabulação e texto marcado) (FR-23, D-033)."""

from __future__ import annotations

import csv
import io
import re
from typing import Any

from rslapp.core.models import Author, Work
from rslapp.importers.base import BaseImporter, clean_doi, extract_year, parse_author_name


# FR-23, D-033: Importador de arquivos exportados do Web of Science
class WebOfScienceImporter(BaseImporter):
    """Lê e interpreta exportações do Web of Science (TSV e Plain Text Tagged)."""

    format_id: str = "wos"

    def parse(self, content: str) -> list[Work]:
        """Interpreta exportação do Web of Science e retorna a lista de obras Work."""
        if not content or not content.strip():
            return []

        clean_content = content.lstrip("\ufeff")

        # Verifica se é formato tab-delimited (TSV) ou formato marcado linha-a-linha (Tagged)
        first_line = clean_content.splitlines()[0] if clean_content.splitlines() else ""
        if "\t" in first_line:
            return self._parse_tsv(clean_content)
        return self._parse_tagged(clean_content)

    def _parse_tsv(self, content: str) -> list[Work]:
        works: list[Work] = []
        reader = csv.DictReader(io.StringIO(content), delimiter="\t")
        if not reader.fieldnames:
            return works

        field_map = {name.strip().upper(): name for name in reader.fieldnames if name}

        for row in reader:
            normalized_row = {k: (row.get(orig) or "").strip() for k, orig in field_map.items()}

            title = normalized_row.get("TI", "")
            doi = clean_doi(normalized_row.get("DI"))
            if not title and not doi:
                continue

            year = extract_year(normalized_row.get("PY"))
            venue = normalized_row.get("SO")
            abstract = normalized_row.get("AB") or None

            # Autores (AU separados por ponto-e-vírgula ';')
            authors: list[Author] = []
            author_names_str = normalized_row.get("AU") or ""
            if author_names_str:
                for a_piece in author_names_str.split(";"):
                    cleaned_a = a_piece.strip()
                    if cleaned_a:
                        authors.append(parse_author_name(cleaned_a))

            # Palavras-chave (DE = Author Keywords, ID = Keywords Plus)
            keywords: list[str] = []
            for kw_field in ("DE", "ID"):
                kw_str = normalized_row.get(kw_field) or ""
                if kw_str:
                    for k in kw_str.split(";"):
                        cleaned_k = k.strip()
                        if cleaned_k and cleaned_k not in keywords:
                            keywords.append(cleaned_k)

            # Citações (TC = Times Cited)
            citations: dict[str, int] = {}
            tc_raw = normalized_row.get("TC")
            if tc_raw:
                match_digits = re.search(r"\d+", tc_raw)
                if match_digits:
                    citations["web_of_science"] = int(match_digits.group(0))

            # Identificador WoS (UT)
            source_ids: dict[str, str] = {}
            ut = normalized_row.get("UT")
            if ut:
                source_ids["web_of_science"] = ut

            # Referências citadas (CR)
            references: list[str] = []
            cr_str = normalized_row.get("CR") or ""
            if cr_str:
                for r in cr_str.split(";"):
                    cleaned_r = r.strip()
                    if cleaned_r:
                        references.append(cleaned_r)

            # Tipo de documento e Retratações (DT)
            dt_raw = (normalized_row.get("DT") or "").lower()
            is_retracted = False
            retraction_details: dict[str, Any] | None = None
            if "retract" in dt_raw or "retrata" in dt_raw:
                is_retracted = True
                retraction_details = {
                    "source": "wos_document_type",
                    "document_type": normalized_row.get("DT"),
                }
                work_type = "article"
            elif "review" in dt_raw:
                work_type = "review"
            elif any(k in dt_raw for k in ("proceeding", "conference")):
                work_type = "conference-paper"
            elif "book" in dt_raw:
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

    def _parse_tagged(self, content: str) -> list[Work]:
        works: list[Work] = []
        lines = content.splitlines()

        current: dict[str, Any] = self._new_tagged_accumulator()
        current_tag: str | None = None

        for line in lines:
            trimmed = line.rstrip()
            if not trimmed:
                continue

            # Tag de duas letras maiúsculas no início da linha
            if len(trimmed) >= 2 and trimmed[:2].isupper() and (len(trimmed) == 2 or trimmed[2] == " "):
                tag = trimmed[:2]
                val = trimmed[2:].strip()
                current_tag = tag

                if tag == "ER":
                    # Fim do registro
                    w = self._build_tagged_work(current)
                    if w:
                        works.append(w)
                    current = self._new_tagged_accumulator()
                    current_tag = None
                    continue

                if tag in current:
                    if isinstance(current[tag], list):
                        if val:
                            current[tag].append(val)
                    else:
                        current[tag] = val

            elif current_tag and line.startswith("   "):
                # Linha de continuação
                val = line.strip()
                if val:
                    if isinstance(current.get(current_tag), list):
                        current[current_tag].append(val)
                    elif current.get(current_tag):
                        current[current_tag] += " " + val

        if current["TI"] or current["DI"]:
            w = self._build_tagged_work(current)
            if w:
                works.append(w)

        return works

    @staticmethod
    def _new_tagged_accumulator() -> dict[str, Any]:
        return {
            "PT": "",
            "AU": [],
            "TI": "",
            "SO": "",
            "DT": "",
            "DE": [],
            "ID": [],
            "AB": "",
            "CR": [],
            "TC": "",
            "PY": "",
            "DI": "",
            "UT": "",
        }

    def _build_tagged_work(self, rec: dict[str, Any]) -> Work | None:
        title = " ".join(rec["TI"].split()) if rec["TI"] else ""
        doi = clean_doi(rec["DI"])
        if not title and not doi:
            return None

        year = extract_year(rec["PY"])
        venue = rec["SO"] or None
        abstract = rec["AB"] or None

        authors: list[Author] = [parse_author_name(a) for a in rec["AU"] if a.strip()]

        keywords: list[str] = []
        for kw_list in (rec["DE"], rec["ID"]):
            for k in kw_list:
                for piece in k.split(";"):
                    piece_c = piece.strip()
                    if piece_c and piece_c not in keywords:
                        keywords.append(piece_c)

        citations: dict[str, int] = {}
        if rec["TC"]:
            digits = re.search(r"\d+", rec["TC"])
            if digits:
                citations["web_of_science"] = int(digits.group(0))

        source_ids: dict[str, str] = {}
        if rec["UT"]:
            source_ids["web_of_science"] = rec["UT"]

        references: list[str] = [r.strip() for r in rec["CR"] if r.strip()]

        dt_raw = rec["DT"].lower()
        is_retracted = False
        retraction_details: dict[str, Any] | None = None
        if "retract" in dt_raw or "retrata" in dt_raw:
            is_retracted = True
            retraction_details = {
                "source": "wos_document_type",
                "document_type": rec["DT"],
            }

        return Work(
            title=title or f"Artigo sem título ({doi})",
            doi=doi,
            year=year,
            type="article",
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
