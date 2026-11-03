"""Exportador de URLs da consulta do OpenAlex para VOSviewer."""

from __future__ import annotations

from typing import Any

from rslapp.core.errors import RSLError
from rslapp.core.models import Work
from rslapp.exporters.base import Exporter

MAX_FILTER_IDS = 100


def _short_id(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    val = raw.strip()
    for prefix in ("https://openalex.org/", "http://openalex.org/"):
        if val.lower().startswith(prefix):
            val = val[len(prefix) :].strip()
    return val if val else None


# FR-06, D-002: Exportador de URLs da consulta do OpenAlex em grupos de até 100 IDs
class OpenAlexURLExporter(Exporter):
    """Gera URLs de consulta do OpenAlex aceitas pelo VOSviewer."""

    format: str = "openalex_url"
    extension: str = "openalex.txt"

    # FR-06, D-002: Extrai IDs do OpenAlex preservando ordem
    def get_openalex_ids(self, list_data: dict[str, Any]) -> list[str]:
        """Extrai os IDs do OpenAlex dos trabalhos da lista na ordem de aparecimento."""
        if not isinstance(list_data, dict):
            raise TypeError("list_data deve ser um dicionário")

        raw_works = list_data.get("works") or []
        ids: list[str] = []

        for item in raw_works:
            if isinstance(item, Work):
                oa_id = item.source_ids.get("openalex")
            elif isinstance(item, dict):
                source_ids = item.get("source_ids") or {}
                oa_id = (
                    source_ids.get("openalex")
                    if isinstance(source_ids, dict)
                    else None
                )
            else:
                continue

            sid = _short_id(oa_id)
            if sid:
                ids.append(sid)

        return ids

    # FR-06, D-002: Gera URLs em lotes de até 100 sem expor chaves de API
    def generate_urls(self, list_data: dict[str, Any]) -> list[str]:
        """Gera as URLs do OpenAlex divididas em lotes de até 100 IDs."""
        ids = self.get_openalex_ids(list_data)
        if not ids:
            raise RSLError(
                "format_not_available",
                "Lista não possui trabalhos do OpenAlex",
            )

        urls: list[str] = []
        for i in range(0, len(ids), MAX_FILTER_IDS):
            batch = ids[i : i + MAX_FILTER_IDS]
            urls.append(f"https://api.openalex.org/works?filter=openalex:{'|'.join(batch)}")

        return urls

    # FR-06, D-002: Renderiza URLs uma por linha em arquivo de texto
    def render(self, list_data: dict[str, Any]) -> str:
        """Renderiza as URLs uma por linha."""
        urls = self.generate_urls(list_data)
        return "\n".join(urls) + "\n"
