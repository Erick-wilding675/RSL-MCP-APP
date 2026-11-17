"""Importadores de listas e arquivos bibliográficos de fontes externas (FR-23, D-033)."""

from __future__ import annotations

from typing import Any

from rslapp.core.dedup import deduplicate_works_with_merge
from rslapp.core.errors import RSLError
from rslapp.core.models import Work
from rslapp.core.search import PAGE_SIZE, _summarize_work
from rslapp.importers.base import BaseImporter
from rslapp.importers.bibtex import BibTeXImporter
from rslapp.importers.detector import auto_detect_format
from rslapp.importers.ris import RISImporter
from rslapp.importers.scopus_csv import ScopusCSVImporter
from rslapp.importers.wos import WebOfScienceImporter
from rslapp.store import Store

__all__ = [
    "BaseImporter",
    "BibTeXImporter",
    "RISImporter",
    "ScopusCSVImporter",
    "WebOfScienceImporter",
    "auto_detect_format",
    "import_records",
    "import_to_store",
]

_IMPORTERS: dict[str, type[BaseImporter]] = {
    "ris": RISImporter,
    "bibtex": BibTeXImporter,
    "scopus_csv": ScopusCSVImporter,
    "wos": WebOfScienceImporter,
}


# FR-23, D-033: Processa o conteúdo e extrai a lista de Work
def import_records(content: str, format: str = "auto") -> tuple[list[Work], str]:
    """Interpreta registros bibliográficos a partir de string de texto ou arquivo.

    Args:
        content: Conteúdo textual do arquivo bibliográfico.
        format: 'auto', 'ris', 'bibtex', 'scopus_csv' ou 'wos'.

    Returns:
        Tupla (lista de obras Work, formato detectado/utilizado).

    Raises:
        RSLError('invalid_input'): Formato desconhecido ou dados inválidos.
    """
    if not isinstance(content, str) or not content.strip():
        raise RSLError("invalid_input", "Conteúdo vazio ou inválido para importação")

    target_format = format.strip().lower() if isinstance(format, str) else "auto"
    if target_format == "auto":
        detected = auto_detect_format(content)
    else:
        detected = target_format

    importer_cls = _IMPORTERS.get(detected)
    if importer_cls is None:
        raise RSLError(
            "invalid_input",
            f"Formato de importação não suportado: {format!r}. Suportados: auto, ris, bibtex, scopus_csv, wos.",
        )

    importer = importer_cls()
    works = importer.parse(content)
    return works, detected


# FR-23, D-033: Importa registros e grava como uma nova lista no Store
def import_to_store(
    store: Store,
    content: str,
    format: str = "auto",
    request_summary: str = "",
    list_name: str = "",
) -> dict[str, Any]:
    """Processa arquivo bibliográfico, deduplica e grava como lista e busca no Store.

    Returns:
        Dicionário com search_id, list_id, status, total, page, next_page, works, etc.
    """
    if not isinstance(store, Store):
        raise TypeError("store deve ser uma instância de Store")

    raw_works, detected_format = import_records(content, format=format)
    if not raw_works:
        raise RSLError("invalid_input", "Nenhum artigo válido foi encontrado no conteúdo fornecido.")

    # Deduplicação interna caso o arquivo exportado contenha obras repetidas
    total_raw = len(raw_works)
    dedup_result = deduplicate_works_with_merge(raw_works)
    deduped_works = dedup_result.works
    total = len(deduped_works)
    duplicates_removed = total_raw - total

    summary_text = request_summary.strip()
    if not summary_text:
        unit = "artigo" if total == 1 else "artigos"
        name_part = f" '{list_name}'" if list_name.strip() else ""
        summary_text = f"Importação de {total} {unit}{name_part} ({detected_format})"

    search_data: dict[str, Any] = {
        "kind": "import",
        "request_summary": summary_text,
        "repeated_from": None,
        "origin": None,
        "params": {
            "format": detected_format,
            "list_name": list_name.strip() or None,
        },
        "imported_format": detected_format,
        "total": total,
        "duplicates_removed": duplicates_removed,
    }

    list_data_to_save: dict[str, Any] = {
        "status": "complete",
        "total": total,
        "title": list_name.strip() or None,
        "works": [w.to_dict() for w in deduped_works],
    }

    saved_search, saved_list = store.record_search(search_data, list_data_to_save)

    first_page_works = [_summarize_work(w) for w in deduped_works[:PAGE_SIZE]]
    next_page: int | None = 2 if total > PAGE_SIZE else None

    return {
        "search_id": saved_search["id"],
        "list_id": saved_list["id"],
        "status": "complete",
        "total": total,
        "page": 1,
        "next_page": next_page,
        "imported_format": detected_format,
        "duplicates_removed": duplicates_removed,
        "works": first_page_works,
    }
