"""Módulo de exportadores de listas do RSL.app."""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from typing import Any

from rslapp.core.errors import RSLError
from rslapp.core.models import Work
from rslapp.exporters.base import Exporter, save_export_file
from rslapp.exporters.csv import CSVExporter
from rslapp.exporters.dois import DOIsExporter
from rslapp.exporters.json import JSONExporter
from rslapp.exporters.openalex_url import OpenAlexURLExporter
from rslapp.exporters.ris import RISExporter
from rslapp.store import Store

__all__ = [
    "CSVExporter",
    "DOIsExporter",
    "Exporter",
    "JSONExporter",
    "OpenAlexURLExporter",
    "RISExporter",
    "get_exporter",
    "run_export",
    "save_export_file",
]

# FR-06, D-002: Tabela de exportadores registrados para formatos suportados
_EXPORTERS: dict[str, type[Exporter]] = {
    "ris": RISExporter,
    "csv": CSVExporter,
    "json": JSONExporter,
    "dois": DOIsExporter,
    "openalex_url": OpenAlexURLExporter,
}


def _run_sync(coro_fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Executa uma corotina de forma síncrona com suporte a AnyIO e asyncio."""
    with contextlib.suppress(RuntimeError, ImportError):
        import anyio.from_thread

        return anyio.from_thread.run(lambda: coro_fn(*args, **kwargs))

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro_fn(*args, **kwargs)).result()

    return asyncio.run(coro_fn(*args, **kwargs))


# FR-06, D-002: Obtém o exportador correspondente ao formato solicitado
def get_exporter(format_name: str) -> Exporter:
    """Retorna a instância do exportador registrado para o formato.

    Levanta RSLError('invalid_input') se o formato for desconhecido ou não suportado.
    """
    if not isinstance(format_name, str):
        raise RSLError(
            "invalid_input",
            f"Formato deve ser texto, recebido: {type(format_name).__name__}",
        )
    exporter_cls = _EXPORTERS.get(format_name.strip().lower())
    if exporter_cls is None:
        raise RSLError(
            "invalid_input",
            f"Formato inválido ou não suportado: {format_name!r}. "
            f"Suportados: 'ris', 'csv', 'json', 'dois', 'openalex_url'",
        )
    return exporter_cls()


# FR-06, FR-12, UC-01, D-002: Execução de exportação de lista salva
def run_export(
    store: Store,
    list_id: str,
    export_format: str,
    export_dir: Path | str,
    *,
    source: Any = None,
) -> dict[str, Any]:
    """Carrega a lista do armazenamento, renderiza no formato e grava no disco."""
    exporter = get_exporter(export_format)

    try:
        list_data = store.get_list(list_id)
    except (FileNotFoundError, ValueError) as err:
        raise RSLError("list_not_found", f"Lista não encontrada: {list_id}") from err

    # FR-06: Lista vazia não exporta em nenhum formato e não grava arquivo
    raw_works = list_data.get("works") if isinstance(list_data, dict) else None
    if not isinstance(raw_works, list) or len(raw_works) == 0:
        raise RSLError("empty_list", "a lista está vazia, não há o que exportar")

    warnings: list[str] = []
    extra_fields: dict[str, Any] = {}
    normalized_format = export_format.strip().lower()

    if normalized_format == "openalex_url":
        if not isinstance(exporter, OpenAlexURLExporter):
            raise RSLError("invalid_input", "Exportador inválido para openalex_url")
        urls = exporter.generate_urls(list_data)
        content = "\n".join(urls) + "\n"
        count = len(urls)
        extra_fields["url"] = urls[0]
    elif normalized_format == "dois":
        if not isinstance(exporter, DOIsExporter):
            raise RSLError("invalid_input", "Exportador inválido para dois")
        content = exporter.render(list_data)
        count = exporter.get_count(list_data)
    elif normalized_format == "csv":
        if not isinstance(exporter, CSVExporter):
            raise RSLError("invalid_input", "Exportador inválido para csv")
        # FR-14, D-005, D-010: Troca referências do OpenAlex por DOI
        all_refs: list[str] = []
        raw_works = list_data.get("works") or []
        for w in raw_works:
            refs = (
                w.references
                if isinstance(w, Work)
                else (w.get("references") if isinstance(w, dict) else None)
            )
            if refs:
                all_refs.extend(refs)

        doi_mapping: dict[str, str | None] = {}
        if all_refs:
            from rslapp.core.references import resolve_reference_dois

            res = _run_sync(resolve_reference_dois, all_refs, store=store, source=source)
            doi_mapping = res.mapping
            if not res.complete and res.reason:
                warnings.append(f"referências: {res.reason}")

        content = exporter.render(list_data, doi_mapping=doi_mapping)
        count = len(raw_works)
    else:
        content = exporter.render(list_data)
        raw_works = list_data.get("works") or []
        count = len(raw_works) if isinstance(raw_works, list) else 0

    filename = f"{list_id}.{exporter.extension}"
    dest_path = save_export_file(export_dir, filename, content)

    result: dict[str, Any] = {
        "path": str(dest_path),
        "format": exporter.format,
        "count": count,
    }
    result.update(extra_fields)
    if warnings:
        result["warnings"] = warnings

    return result
