"""Exportador de referências bibliográficas no padrão ABNT NBR 6023:2018 (FR-24, D-034)."""

from __future__ import annotations

from typing import Any

from rslapp.core.abnt import format_abnt_reference
from rslapp.core.models import Work
from rslapp.exporters.base import Exporter


# FR-24, D-034: Exportador de listas no formato ABNT NBR 6023:2018 (.txt)
class ABNTExporter(Exporter):
    """Renderiza a lista no formato de referências da ABNT NBR 6023:2018 em ordem alfabética."""

    format: str = "abnt"
    extension: str = "txt"

    def render(self, list_data: dict[str, Any]) -> str:
        """Renderiza a lista de trabalhos como referências ABNT separadas por linha em branco."""
        if not isinstance(list_data, dict):
            raise TypeError("list_data deve ser um dicionário")

        raw_works = list_data.get("works") or []
        works: list[Work] = []

        for item in raw_works:
            if isinstance(item, Work):
                works.append(item)
            elif isinstance(item, dict):
                works.append(Work.from_dict(item))

        # Gera as referências individuais
        rendered_refs: list[str] = [format_abnt_reference(w) for w in works]

        # ABNT NBR 6023: Ordenação alfabética pelo cabeçalho da referência
        rendered_refs.sort(key=lambda ref: ref.lower())

        if not rendered_refs:
            return ""

        return "\n\n".join(rendered_refs) + "\n"
