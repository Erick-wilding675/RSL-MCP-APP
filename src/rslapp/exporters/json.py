"""Exportador de listas para o formato JSON completo."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from rslapp.core.models import Work
from rslapp.exporters.base import Exporter


# FR-06, FR-12, D-002: Exportador de lista completa em formato JSON estruturado
class JSONExporter(Exporter):
    """Renderizador no formato JSON completo com metadados de exportação."""

    format: str = "json"
    extension: str = "json"

    # FR-06, FR-12, D-002: Renderiza registro completo com autores, afiliações, referências e citações
    def render(self, list_data: dict[str, Any]) -> str:
        """Renderiza a lista completa em JSON indentado com exported_at e format_version."""
        if not isinstance(list_data, dict):
            raise TypeError("list_data deve ser um dicionário")

        payload = dict(list_data)
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        payload["exported_at"] = now_iso
        payload["format_version"] = 1

        raw_works = payload.get("works") or []
        serialized_works: list[dict[str, Any]] = []
        for item in raw_works:
            if isinstance(item, Work):
                serialized_works.append(item.to_dict())
            elif isinstance(item, dict):
                serialized_works.append(item)

        payload["works"] = serialized_works
        if "total" not in payload:
            payload["total"] = len(serialized_works)

        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
