"""Módulo de exportadores de listas do RSL.app."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rslapp.core.errors import RSLError
from rslapp.exporters.base import Exporter, save_export_file
from rslapp.exporters.ris import RISExporter
from rslapp.store import Store

__all__ = [
    "Exporter",
    "RISExporter",
    "get_exporter",
    "run_export",
    "save_export_file",
]

_EXPORTERS: dict[str, type[Exporter]] = {
    "ris": RISExporter,
}


# FR-06, D-002: Obtém o exportador correspondente ao formato solicitado
def get_exporter(format_name: str) -> Exporter:
    """Retorna a instância do exportador registrado para o formato.

    Levanta RSLError('invalid_input') se o formato for desconhecido ou não suportado.
    """
    if not isinstance(format_name, str):
        raise RSLError("invalid_input", f"Formato deve ser texto, recebido: {type(format_name).__name__}")
    exporter_cls = _EXPORTERS.get(format_name.strip().lower())
    if exporter_cls is None:
        raise RSLError(
            "invalid_input",
            f"Formato inválido ou não suportado: {format_name!r}. Suportado: 'ris'",
        )
    return exporter_cls()


# FR-06, FR-12, UC-01, D-002: Execução de exportação de lista salva
def run_export(
    store: Store,
    list_id: str,
    export_format: str,
    export_dir: Path | str,
) -> dict[str, Any]:
    """Carrega a lista do armazenamento, renderiza no formato e grava no disco."""
    exporter = get_exporter(export_format)

    try:
        list_data = store.get_list(list_id)
    except (FileNotFoundError, ValueError) as err:
        raise RSLError("list_not_found", f"Lista não encontrada: {list_id}") from err

    content = exporter.render(list_data)
    filename = f"{list_id}.{exporter.extension}"
    dest_path = save_export_file(export_dir, filename, content)
    works = list_data.get("works") or []
    count = len(works) if isinstance(works, list) else 0

    return {
        "path": str(dest_path),
        "format": exporter.format,
        "count": count,
    }
