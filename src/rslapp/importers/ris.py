"""Importador de registros no formato RIS (FR-23, D-033)."""

from __future__ import annotations

import re
from typing import Any

from rslapp.core.models import Work
from rslapp.importers.base import BaseImporter, clean_doi, extract_year, parse_author_name

_RIS_LINE_RE = re.compile(r"^([A-Z0-9]{2})\s*-\s*(.*)$")

_TYPE_MAP: dict[str, str] = {
    "JOUR": "article",
    "CONF": "conference-paper",
    "CPAPER": "conference-paper",
    "BOOK": "book",
    "CHAP": "book-chapter",
    "THES": "dissertation",
    "RPRT": "report",
    "ELEC": "dataset",
    "GEN": "article",
}


# FR-23, D-033: Importador de arquivos RIS padrão e variantes (Scopus, WoS, Zotero, Mendeley)
class RISImporter(BaseImporter):
    """Lê e interpreta dados bibliográficos no formato RIS."""

    format_id: str = "ris"

    def parse(self, content: str) -> list[Work]:
        """Interpreta texto no formato RIS e retorna a lista de obras Work."""
        works: list[Work] = []
        if not content or not content.strip():
            return works

        lines = content.splitlines()
        current_record: dict[str, Any] = self._new_record_accumulator()

        for line in lines:
            trimmed = line.rstrip()
            if not trimmed:
                continue

            match = _RIS_LINE_RE.match(trimmed)
            if match:
                tag = match.group(1).upper()
                value = match.group(2).strip()

                if tag == "TY":
                    current_record["type"] = _TYPE_MAP.get(value.upper(), "article")
                elif tag in {"TI", "T1", "CT", "BT"}:
                    if not current_record["title"]:
                        current_record["title"] = value
                    else:
                        current_record["title"] += " " + value
                elif tag in {"AU", "A1", "A2"}:
                    if value:
                        current_record["authors"].append(parse_author_name(value))
                elif tag in {"PY", "Y1", "DA"}:
                    y = extract_year(value)
                    if y and not current_record["year"]:
                        current_record["year"] = y
                elif tag in {"DO", "DI"}:
                    d = clean_doi(value)
                    if d:
                        current_record["doi"] = d
                elif tag in {"AB", "N2"}:
                    if not current_record["abstract"]:
                        current_record["abstract"] = value
                    else:
                        current_record["abstract"] += " " + value
                elif tag == "KW":
                    if value and value not in current_record["keywords"]:
                        current_record["keywords"].append(value)
                elif tag in {"JF", "JO", "T2", "JA"}:
                    if not current_record["venue"]:
                        current_record["venue"] = value
                elif tag in {"N1", "RN"}:
                    current_record["notes"].append(value)
                elif tag == "ER":
                    # Fim do registro atual
                    work = self._build_work(current_record)
                    if work:
                        works.append(work)
                    current_record = self._new_record_accumulator()

            elif trimmed.startswith("   ") and current_record["title"]:
                # Linha de continuação
                extra = trimmed.strip()
                if extra:
                    current_record["title"] += " " + extra

        # Se o arquivo não encerrou com ER mas acumulou dados
        if current_record["title"] or current_record["doi"]:
            work = self._build_work(current_record)
            if work:
                works.append(work)

        return works

    @staticmethod
    def _new_record_accumulator() -> dict[str, Any]:
        return {
            "type": "article",
            "title": "",
            "authors": [],
            "year": None,
            "doi": None,
            "venue": None,
            "abstract": None,
            "keywords": [],
            "notes": [],
        }

    # FR-23, D-032, D-033: Constrói Work com checagem de retratação anotada em notas
    def _build_work(self, rec: dict[str, Any]) -> Work | None:
        title = " ".join(rec["title"].split()) if rec["title"] else ""
        doi = rec["doi"]
        if not title and not doi:
            return None

        is_retracted = False
        retraction_details: dict[str, Any] | None = None

        # Verifica se alguma nota sinaliza retratação (D-032)
        for note in rec["notes"]:
            lower_note = note.lower()
            if "retrata" in lower_note or "retract" in lower_note or "expression of concern" in lower_note:
                is_retracted = True
                retraction_details = {"source": "ris_note", "note": note}
                break

        return Work(
            title=title or f"Artigo sem título ({doi})",
            doi=doi,
            year=rec["year"],
            type=rec["type"],
            venue=rec["venue"],
            abstract=rec["abstract"],
            keywords=rec["keywords"],
            authors=rec["authors"],
            is_retracted=is_retracted,
            retraction_details=retraction_details,
        )
