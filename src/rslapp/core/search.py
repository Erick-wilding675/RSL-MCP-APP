"""Miolo de busca por termos, deduplicação na lista, cache por fonte e gravação."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from rslapp.core.dedup import (
    deduplicate_works,
    deduplicate_works_with_merge,
    normalize_title,
)
from rslapp.core.errors import RSLError
from rslapp.core.models import SourceResult, Work
from rslapp.sources.base import Source
from rslapp.store import Store

PAGE_SIZE = 25
DEFAULT_MAX_RESULTS = 100
MIN_MAX_RESULTS = 1
MAX_MAX_RESULTS = 1_000

__all__ = [
    "DEFAULT_MAX_RESULTS",
    "MAX_MAX_RESULTS",
    "MIN_MAX_RESULTS",
    "PAGE_SIZE",
    "deduplicate_works",
    "normalize_title",
    "run_search",
]


def _summarize_work(work: Work) -> dict[str, Any]:
    return {
        "doi": work.doi,
        "title": work.title,
        "authors": [author.name for author in work.authors],
        "year": work.year,
        "venue": work.venue,
        "references_count": work.references_count,
        "citations": dict(work.citations),
    }


def _select_sources(
    available: Sequence[Source],
    requested_names: Sequence[str] | None,
) -> list[Source]:
    if not available:
        raise RSLError("invalid_input", "nenhuma fonte disponível para consulta")
    if requested_names is None:
        return list(available)
    if (
        isinstance(requested_names, (str, bytes))
        or not isinstance(requested_names, Sequence)
        or len(requested_names) == 0
    ):
        raise RSLError(
            "invalid_input",
            "a lista de fontes (sources) não pode ser vazia",
        )

    by_name = {src.name: src for src in available}
    selected: list[Source] = []
    seen: set[str] = set()

    for raw_name in requested_names:
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise RSLError("invalid_input", "nome de fonte inválido")
        name = raw_name.strip()
        if name not in by_name:
            raise RSLError("invalid_input", f"fonte desconhecida: {name}")
        if name not in seen:
            seen.add(name)
            selected.append(by_name[name])

    return selected


# FR-01, FR-04, FR-05, FR-08, FR-09, FR-12, FR-14, NFR-06, D-002, D-003: Orquestração da busca por termos
async def run_search(
    store: Store,
    sources: Sequence[Source],
    *,
    query: str,
    request_summary: str = "",
    max_results: int = DEFAULT_MAX_RESULTS,
    source_names: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Executa busca nas fontes em paralelo, deduplica, grava lista/busca/log e devolve resumo."""
    if not isinstance(query, str) or not query.strip():
        raise RSLError("invalid_input", "a consulta (query) não pode ser vazia")
    clean_query = query.strip()

    if not isinstance(request_summary, str):
        raise RSLError("invalid_input", "request_summary deve ser texto")

    if (
        not isinstance(max_results, int)
        or isinstance(max_results, bool)
        or max_results < MIN_MAX_RESULTS
        or max_results > MAX_MAX_RESULTS
    ):
        raise RSLError(
            "invalid_input",
            f"max_results deve ser um inteiro entre {MIN_MAX_RESULTS} e {MAX_MAX_RESULTS}",
        )

    selected_sources = _select_sources(sources, source_names)

    # NFR-06: Consulta o cache antes de chamar cada fonte e só grava no cache resultados ok
    async def _fetch_from_source(source: Source) -> tuple[SourceResult, bool, str | None]:
        c_query = source.cache_query(clean_query, max_results)
        cached = store.get_cache(source.name, c_query)
        if cached is not None:
            return SourceResult.from_dict(cached["response"]), True, cached.get("fetched_at")
        result = await source.search(clean_query, max_results)
        if result.status == "ok":
            store.set_cache(source.name, c_query, result.to_dict())
        return result, False, None

    # FR-08: Consulta às fontes executada concorrentemente via asyncio.gather
    fetch_outcomes = await asyncio.gather(
        *[_fetch_from_source(src) for src in selected_sources]
    )

    source_entries: list[dict[str, Any]] = []
    raw_works: list[Work] = []

    for result, from_cache, fetched_at in fetch_outcomes:
        raw_works.extend(result.works)
        source_entries.append(
            {
                "name": result.name,
                "query": result.query,
                "status": result.status,
                "reason": result.reason,
                "found": result.found,
                "fetched": result.fetched,
                "from_cache": from_cache,
                "fetched_at": fetched_at,
            }
        )

    # D-002: Erro no_source_available quando todas as fontes estão sem chave, sem gravar nada
    if all(entry["status"] == "missing_key" for entry in source_entries):
        raise RSLError(
            "no_source_available",
            "nenhuma fonte pode responder; configure OPENALEX_API_KEY",
        )

    # FR-04, FR-14: Deduplicação e junção entre fontes com prevalência e contagem de divergências
    dedup_result = deduplicate_works_with_merge(raw_works)
    deduped_works = dedup_result.works
    total = len(deduped_works)

    # FR-08: Lista incompleta quando alguma fonte consultada não terminou em ok
    list_status = (
        "complete"
        if all(entry["status"] == "ok" for entry in source_entries)
        else "incomplete"
    )

    # FR-05, FR-09, FR-12: Cada busca gera lista própria e entrada em searches/ e log.md
    search_data: dict[str, Any] = {
        "kind": "terms",
        "request_summary": request_summary,
        "repeated_from": None,
        "origin": None,
        "params": {
            "query": clean_query,
            "max_results": max_results,
            "sources": [src.name for src in selected_sources],
        },
        "merge": dedup_result.merge,
        "sources": source_entries,
    }
    list_data: dict[str, Any] = {
        "status": list_status,
        "total": total,
        "works": [work.to_dict() for work in deduped_works],
    }
    saved_search, saved_list = store.record_search(search_data, list_data)

    # D-002, D-003: Resposta em resumo com no máximo 25 artigos na primeira página
    first_page_works = [_summarize_work(w) for w in deduped_works[:PAGE_SIZE]]
    next_page: int | None = 2 if total > PAGE_SIZE else None

    return {
        "search_id": saved_search["id"],
        "list_id": saved_list["id"],
        "status": list_status,
        "total": total,
        "page": 1,
        "next_page": next_page,
        "sources": saved_search["sources"],
        "works": first_page_works,
    }
