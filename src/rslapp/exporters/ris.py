"""Exportador de listas para o formato RIS padrão."""

from __future__ import annotations

from typing import Any

from rslapp.core.models import Work
from rslapp.exporters.base import Exporter


# FR-06: Mapeamento de tipos acadêmicos para tipos de registro RIS (TY)
def _map_ris_type(work_type: str | None) -> str:
    """Mapeia o tipo da obra para o tipo RIS correspondente (TY)."""
    if not work_type or not isinstance(work_type, str):
        return "GEN"
    norm = work_type.strip().lower()
    if norm in {"article", "journal-article", "journal_article", "journalarticle", "journal article"}:
        return "JOUR"
    if any(k in norm for k in ("conf", "proceeding", "proceedings")):
        return "CONF"
    return "GEN"


# FR-06, D-002, D-004: Exportador de listas no formato RIS para VOSviewer e gestores de referência
class RISExporter(Exporter):
    """Renderizador no formato RIS (UTF-8, fim de linha \\r\\n)."""

    format: str = "ris"
    extension: str = "ris"

    # FR-06, D-004: Renderiza registros RIS; ORCID, afiliações e referências ficam fora do RIS
    def render(self, list_data: dict[str, Any]) -> str:
        """Renderiza a lista no formato RIS com terminadores \\r\\n."""
        if not isinstance(list_data, dict):
            raise TypeError("list_data deve ser um dicionário")

        raw_works = list_data.get("works") or []
        records_lines: list[str] = []

        for item in raw_works:
            if isinstance(item, Work):
                work_dict = item.to_dict()
            elif isinstance(item, dict):
                work_dict = item
            else:
                continue

            # TY: Tipo de registro (obrigatório em cada registro RIS)
            ris_type = _map_ris_type(work_dict.get("type"))
            records_lines.append(f"TY  - {ris_type}")

            # TI: Título
            title = work_dict.get("title")
            if title and isinstance(title, str) and title.strip():
                clean_title = " ".join(title.split())
                records_lines.append(f"TI  - {clean_title}")

            # AU: Autores na ordem original (sem inverter Sobrenome, Nome)
            authors = work_dict.get("authors") or []
            for author in authors:
                name: str | None = None
                if isinstance(author, dict):
                    raw_name = author.get("name")
                    name = str(raw_name) if raw_name is not None else None
                elif hasattr(author, "name"):
                    raw_name = author.name
                    name = str(raw_name) if raw_name is not None else None
                elif isinstance(author, str):
                    name = author
                if name and name.strip():
                    clean_name = " ".join(name.split())
                    records_lines.append(f"AU  - {clean_name}")

            # PY: Ano de publicação
            year = work_dict.get("year")
            if year is not None and not isinstance(year, bool):
                try:
                    year_int = int(year)
                    if year_int > 0:
                        records_lines.append(f"PY  - {year_int}")
                except (ValueError, TypeError):
                    pass

            # JO: Periódico / venue
            venue = work_dict.get("venue")
            if venue and isinstance(venue, str) and venue.strip():
                clean_venue = " ".join(venue.split())
                records_lines.append(f"JO  - {clean_venue}")

            # AB: Resumo
            abstract = work_dict.get("abstract")
            if abstract and isinstance(abstract, str) and abstract.strip():
                clean_abstract = " ".join(abstract.split())
                records_lines.append(f"AB  - {clean_abstract}")

            # KW: Palavras-chave (uma linha por termo)
            keywords = work_dict.get("keywords") or []
            for kw in keywords:
                if kw and isinstance(kw, str) and kw.strip():
                    clean_kw = " ".join(kw.split())
                    records_lines.append(f"KW  - {clean_kw}")

            # DO: DOI
            doi = work_dict.get("doi")
            if doi and isinstance(doi, str) and doi.strip():
                clean_doi = doi.strip()
                records_lines.append(f"DO  - {clean_doi}")

            # ER: Fim de registro
            records_lines.append("ER  - ")

        if not records_lines:
            return ""

        return "\r\n".join(records_lines) + "\r\n"
