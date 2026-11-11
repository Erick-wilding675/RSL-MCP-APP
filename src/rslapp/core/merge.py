"""Miolo de junção de listas salvas (merge_lists) sem duplicatas."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from rslapp.core.dedup import deduplicate_works_with_merge
from rslapp.core.errors import RSLError
from rslapp.core.models import Work
from rslapp.core.search import PAGE_SIZE, _summarize_work
from rslapp.store import Store
from rslapp.store._atomic import parse_seq_id

MIN_MERGE_LISTS = 2
MAX_MERGE_LISTS = 20

__all__ = ["MAX_MERGE_LISTS", "MIN_MERGE_LISTS", "run_merge"]


def _item_to_work(item: Any) -> Work:
    if isinstance(item, Work):
        return item
    if isinstance(item, dict):
        return Work.from_dict(item)
    raise TypeError(f"Item da lista deve ser dict ou Work, recebido: {type(item).__name__}")


# D-021, FR-04, FR-05, FR-12, FR-13: Une de 2 a 20 listas salvas sem duplicatas
async def run_merge(
    store: Store,
    *,
    list_ids: Sequence[str],
    request_summary: str = "",
) -> dict[str, Any]:
    """Une listas salvas de buscas anteriores numa lista nova, sem duplicatas, gravando lista, registro e log."""
    if isinstance(list_ids, (str, bytes)) or not isinstance(list_ids, Sequence):
        raise RSLError("invalid_input", "list_ids deve ser uma lista de identificadores")

    if len(list_ids) < MIN_MERGE_LISTS or len(list_ids) > MAX_MERGE_LISTS:
        raise RSLError(
            "invalid_input",
            f"list_ids deve conter entre {MIN_MERGE_LISTS} e {MAX_MERGE_LISTS} listas",
        )

    if not isinstance(request_summary, str):
        raise RSLError("invalid_input", "request_summary deve ser texto")

    clean_ids: list[str] = []
    seen_ids: set[str] = set()

    for lid in list_ids:
        if not isinstance(lid, str):
            raise RSLError("invalid_input", f"identificador de lista inválido: {lid!r}")
        cleaned = lid.strip()
        try:
            parse_seq_id(cleaned, "l")
        except ValueError as err:
            raise RSLError("invalid_input", f"identificador de lista inválido: {cleaned}") from err

        if cleaned in seen_ids:
            raise RSLError("invalid_input", f"list_ids contém identificadores repetidos: {cleaned}")
        seen_ids.add(cleaned)
        clean_ids.append(cleaned)

    # D-021, FR-12: Validação de existência de todas as listas antes de qualquer gravação
    source_lists: list[dict[str, Any]] = []
    for lid in clean_ids:
        try:
            list_data = store.get_list(lid)
        except (FileNotFoundError, ValueError) as err:
            raise RSLError("list_not_found", f"lista não encontrada: {lid}") from err
        source_lists.append(list_data)

    incomplete_from: list[str] = []
    raw_works: list[Work] = []
    origin_totals: dict[str, int] = {}

    # D-021, FR-04: Coleta trabalhos preservando a ordem das listas e a ordem interna de cada uma
    for list_data in source_lists:
        lid = list_data.get("id") or "desconhecido"
        if list_data.get("status") != "complete":
            incomplete_from.append(lid)
        works_in_list = list_data.get("works") or []
        origin_totals[lid] = len(works_in_list)
        for item in works_in_list:
            raw_works.append(_item_to_work(item))

    list_status = "incomplete" if incomplete_from else "complete"

    # FR-04: Deduplicação com precedência e união de source_ids e citations
    total_raw = len(raw_works)
    dedup_result = deduplicate_works_with_merge(raw_works)
    deduped_works = dedup_result.works
    total = len(deduped_works)
    duplicates_removed = total_raw - total

    # FR-05, FR-12, FR-13, D-021: Gravação como busca (Store.record_search) com kind: merge
    search_data: dict[str, Any] = {
        "kind": "merge",
        "request_summary": request_summary,
        "repeated_from": None,
        "origin": None,
        "params": {"list_ids": clean_ids},
        "merged_from": clean_ids,
        "origin_totals": origin_totals,
        "duplicates_removed": duplicates_removed,
        "total": total,
        "sources": [],
    }
    if incomplete_from:
        search_data["incomplete_from"] = incomplete_from

    list_data_to_save: dict[str, Any] = {
        "status": list_status,
        "total": total,
        "works": [w.to_dict() for w in deduped_works],
    }
    if incomplete_from:
        list_data_to_save["incomplete_from"] = incomplete_from

    saved_search, saved_list = store.record_search(search_data, list_data_to_save)

    first_page_works = [_summarize_work(w) for w in deduped_works[:PAGE_SIZE]]
    next_page: int | None = 2 if total > PAGE_SIZE else None

    result: dict[str, Any] = {
        "search_id": saved_search["id"],
        "list_id": saved_list["id"],
        "status": list_status,
        "total": total,
        "page": 1,
        "next_page": next_page,
        "works": first_page_works,
        "merged_from": clean_ids,
        "duplicates_removed": duplicates_removed,
    }
    if list_status == "incomplete":
        result["incomplete_from"] = incomplete_from

    return result
