"""Miolo de repetição de busca salva do log (repeat_search)."""

from __future__ import annotations

import copy
from collections.abc import Sequence
from typing import Any

from rslapp.core.errors import RSLError
from rslapp.core.find import run_find
from rslapp.core.related import run_related
from rslapp.core.search import run_search
from rslapp.sources.base import Source
from rslapp.store import Store

__all__ = ["run_repeat"]


class _RepeatStoreProxy:
    """Intermediário para capturar search_data e list_data gerados pelo executor antes da gravação."""

    def __init__(self, real_store: Store) -> None:
        self.real_store = real_store
        self.search_data: dict[str, Any] | None = None
        self.list_data: dict[str, Any] | None = None

    def get_cache(self, *args: Any, **kwargs: Any) -> Any:
        return self.real_store.get_cache(*args, **kwargs)

    def set_cache(self, *args: Any, **kwargs: Any) -> Any:
        return self.real_store.set_cache(*args, **kwargs)

    def record_search(
        self, search_data: dict[str, Any], list_data: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        self.search_data = copy.deepcopy(search_data)
        self.list_data = copy.deepcopy(list_data)
        return (
            {"id": "pending", "sources": search_data.get("sources", [])},
            {"id": "pending"},
        )


# FR-11, UC-03, D-002: Orquestração da repetição de busca salva a partir do log
async def run_repeat(
    store: Store,
    sources: Sequence[Source],
    *,
    search_id: str,
) -> dict[str, Any]:
    """Repete uma busca a partir do seu id com os mesmos parâmetros e fontes, gravando busca e lista novas."""
    if not isinstance(search_id, str) or not search_id.strip():
        raise RSLError("invalid_input", "search_id não pode ser vazio")
    clean_search_id = search_id.strip()

    try:
        orig_search = store.get_search(clean_search_id)
    except (FileNotFoundError, ValueError):
        raise RSLError("search_not_found", f"busca {clean_search_id} não encontrada") from None

    orig_kind = orig_search.get("kind")
    if orig_kind == "merge":
        # D-021: Uma junção não pode ser repetida; repita as buscas de origem
        raise RSLError("invalid_input", "uma junção não pode ser repetida; repita as buscas de origem")

    orig_params = orig_search.get("params")
    if not isinstance(orig_params, dict) or not orig_params:
        raise RSLError("invalid_input", "busca sem parâmetros gravados")
    proxy = _RepeatStoreProxy(store)
    source_names = orig_params.get("sources")
    summary = orig_search.get("request_summary", "")

    # FR-11, D-022: Determina o caminho original (terms, work ou related) a partir do kind e dos parâmetros
    if orig_kind == "terms" or ("query" in orig_params and orig_kind != "related"):
        query = orig_params.get("query", "")
        max_results = orig_params.get("max_results", 100)
        # D-022: Repete com o mesmo valor de include_peer_review; buscas antigas sem o campo usam False
        raw_include = orig_params.get("include_peer_review", False)
        include_peer_review = bool(raw_include) if isinstance(raw_include, bool) else False
        res = await run_search(
            proxy,  # type: ignore[arg-type]
            sources,
            query=query,
            request_summary=summary,
            max_results=max_results,
            source_names=source_names,
            include_peer_review=include_peer_review,
        )
    elif orig_kind == "work" or ("title" in orig_params or ("doi" in orig_params and "direction" not in orig_params)):
        title = orig_params.get("title")
        doi = orig_params.get("doi")
        max_results = orig_params.get("max_results", 10)
        res = await run_find(
            proxy,  # type: ignore[arg-type]
            sources,
            title=title,
            doi=doi,
            request_summary=summary,
            max_results=max_results,
            source_names=source_names,
        )
    elif orig_kind == "related" or "direction" in orig_params:
        direction = orig_params.get("direction", "")
        doi = orig_params.get("doi")
        work_id = orig_params.get("work_id")
        max_results = orig_params.get("max_results", 1000)
        res = await run_related(
            proxy,  # type: ignore[arg-type]
            sources,
            direction=direction,
            doi=doi,
            work_id=work_id,
            request_summary=summary,
            max_results=max_results,
            source_names=source_names,
        )
    else:
        raise RSLError("invalid_input", f"tipo de busca desconhecido para repetição: {orig_kind}")

    new_search_data = proxy.search_data
    new_list_data = proxy.list_data
    assert new_search_data is not None and new_list_data is not None

    # FR-11, UC-03: Grava busca e lista novas com kind: repeat e repeated_from apontando para a original
    new_search_data["kind"] = "repeat"
    new_search_data["repeated_from"] = orig_search["id"]
    new_search_data["params"] = copy.deepcopy(orig_params)
    # D-022: Busca antiga sem include_peer_review repete gravando include_peer_review=False
    if (
        (orig_kind == "terms" or ("query" in orig_params and orig_kind != "related"))
        and "include_peer_review" not in new_search_data["params"]
    ):
        new_search_data["params"]["include_peer_review"] = include_peer_review
    new_search_data["origin"] = copy.deepcopy(orig_search.get("origin"))
    if "request_summary" in orig_search:
        new_search_data["request_summary"] = orig_search["request_summary"]

    saved_search, saved_list = store.record_search(new_search_data, new_list_data)

    res["search_id"] = saved_search["id"]
    res["list_id"] = saved_list["id"]
    res["repeated_from"] = orig_search["id"]
    res["sources"] = saved_search["sources"]

    return res
