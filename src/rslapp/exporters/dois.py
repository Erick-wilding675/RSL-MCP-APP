"""Exportador de listas para o formato de lista de DOIs (um por linha)."""

from __future__ import annotations

from typing import Any

from rslapp.core.models import Work
from rslapp.exporters.base import Exporter


def _clean_doi(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    val = raw.strip()
    lower = val.lower()
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
    ):
        if lower.startswith(prefix):
            val = val[len(prefix) :].strip()
            break
    return val if val else None


# FR-06, D-002: Exportador de lista de DOIs (um por linha, apenas trabalhos com DOI)
class DOIsExporter(Exporter):
    """Renderizador no formato de lista de DOIs (um por linha, apenas os trabalhos com DOI)."""

    format: str = "dois"
    extension: str = "dois.txt"

    # FR-06, D-002: Renderiza um DOI por linha na ordem da lista para os trabalhos que possuem DOI
    def render(self, list_data: dict[str, Any]) -> str:
        """Renderiza a lista como DOIs separados por quebra de linha."""
        if not isinstance(list_data, dict):
            raise TypeError("list_data deve ser um dicionário")

        raw_works = list_data.get("works") or []
        doi_lines: list[str] = []

        for item in raw_works:
            if isinstance(item, Work):
                raw_doi = item.doi
            elif isinstance(item, dict):
                raw_doi = item.get("doi")
            else:
                continue

            clean = _clean_doi(raw_doi)
            if clean:
                doi_lines.append(clean)

        if not doi_lines:
            return ""

        return "\n".join(doi_lines) + "\n"

    # FR-06, D-002: Contagem de linhas com DOI para o retorno de export_list
    def get_count(self, list_data: dict[str, Any]) -> int:
        """Retorna a contagem de DOIs na lista."""
        if not isinstance(list_data, dict):
            return 0
        raw_works = list_data.get("works") or []
        count = 0
        for item in raw_works:
            raw_doi = (
                item.doi
                if isinstance(item, Work)
                else (item.get("doi") if isinstance(item, dict) else None)
            )
            if _clean_doi(raw_doi):
                count += 1
        return count
