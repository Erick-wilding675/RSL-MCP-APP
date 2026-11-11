"""Miolo de busca de artigo específico por título ou DOI, deduplicação e gravação."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from rslapp.core.dedup import deduplicate_works_with_merge, normalize_doi
from rslapp.core.errors import RSLError
from rslapp.core.models import SourceResult, Work
from rslapp.core.search import _select_sources, _summarize_work
from rslapp.sources.base import Source
from rslapp.store import Store

PAGE_SIZE = 25
DEFAULT_MAX_RESULTS = 10
MIN_MAX_RESULTS = 1
MAX_MAX_RESULTS = 100

__all__ = [
    "DEFAULT_MAX_RESULTS",
    "MAX_MAX_RESULTS",
    "MIN_MAX_RESULTS",
    "PAGE_SIZE",
    "run_find",
]


# FR-02, D-002: Validação estrita de DOI (começa com 10., sem espaço, ?, #, % nem segmentos . ou ..)
def _validate_and_normalize_doi(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise RSLError("invalid_input", "doi não pode ser vazio")
    val = raw.strip()
    norm = normalize_doi(val)
    if not norm or not norm.startswith("10."):
        raise RSLError("invalid_input", f"doi deve começar com '10.': {raw}")
    if any(ch.isspace() for ch in norm):
        raise RSLError("invalid_input", f"doi não pode conter espaços: {raw}")
    if any(ch in "?#%" for ch in norm):
        raise RSLError("invalid_input", f"doi contém caracteres inválidos: {raw}")
    segments = norm.split("/")
    if any(seg in (".", "..") for seg in segments):
        raise RSLError("invalid_input", f"doi contém segmentos inválidos: {raw}")
    return norm


# FR-02, UC-02, D-002: Orquestração da busca de artigo específico por DOI ou título
async def run_find(
    store: Store,
    sources: Sequence[Source],
    *,
    title: str | None = None,
    doi: str | None = None,
    request_summary: str = "",
    max_results: int = DEFAULT_MAX_RESULTS,
    source_names: Sequence[str] | None = None,
    repeated_from: str | None = None,
    kind: str = "work",
) -> dict[str, Any]:
    """Busca um artigo específico por título ou DOI nas fontes, deduplica e grava lista própria."""
    if (title is None and doi is None) or (title is not None and doi is not None):
        raise RSLError("invalid_input", "informe exatamente um entre title ou doi")

    # D-020: pubmed e europe_pmc não são suportadas em find_work
    if source_names is not None:
        for raw_src in source_names:
            if isinstance(raw_src, str) and raw_src.strip() in ("pubmed", "europe_pmc"):
                raise RSLError(
                    "invalid_input",
                    f"fonte não suportada nesta ferramenta: {raw_src.strip()}",
                )

    clean_doi: str | None = None
    clean_title: str | None = None

    if doi is not None:
        clean_doi = _validate_and_normalize_doi(doi)
    else:
        assert title is not None
        if not isinstance(title, str) or not title.strip():
            raise RSLError("invalid_input", "title não pode ser vazio")
        clean_title = title.strip()

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

    # FR-02: Execução por DOI via find_by_doi ou por título via search
    if clean_doi is not None:
        async def _fetch_by_doi(source: Source) -> tuple[SourceResult, bool, str | None]:
            if not hasattr(source, "find_by_doi"):
                return (
                    SourceResult(
                        name=source.name,
                        status="not_supported",
                        reason=f"não suportado por {source.name}",
                        query=f"doi:{clean_doi}",
                        found=None,
                        fetched=0,
                        works=[],
                    ),
                    False,
                    None,
                )
            result = await source.find_by_doi(clean_doi)
            return result, False, None

        fetch_outcomes = await asyncio.gather(
            *[_fetch_by_doi(src) for src in selected_sources]
        )
    else:
        assert clean_title is not None

        # NFR-06: Consulta o cache antes de chamar cada fonte e só grava no cache resultados ok
        async def _fetch_by_title(source: Source) -> tuple[SourceResult, bool, str | None]:
            c_query = source.cache_query(clean_title, max_results)
            cached = store.get_cache(source.name, c_query)
            if cached is not None:
                return SourceResult.from_dict(cached["response"]), True, cached.get("fetched_at")
            result = await source.search(clean_title, max_results)
            if result.status == "ok":
                store.set_cache(source.name, c_query, result.to_dict())
            return result, False, None

        fetch_outcomes = await asyncio.gather(
            *[_fetch_by_title(src) for src in selected_sources]
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

    # D-002: Erro no_source_available quando todas as fontes estão sem chave
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

    params: dict[str, Any] = {
        "max_results": max_results,
        "sources": [src.name for src in selected_sources],
    }
    if clean_doi is not None:
        params["doi"] = clean_doi
    else:
        assert clean_title is not None
        params["title"] = clean_title

    # FR-02, FR-05, FR-09, FR-12: Gravação da busca e lista (vazia ou preenchida)
    search_data: dict[str, Any] = {
        "kind": kind,
        "request_summary": request_summary,
        "repeated_from": repeated_from,
        "origin": None,
        "params": params,
        "merge": dedup_result.merge,
        "sources": source_entries,
    }
    list_data: dict[str, Any] = {
        "status": list_status,
        "total": total,
        "works": [work.to_dict() for work in deduped_works],
    }
    saved_search, saved_list = store.record_search(search_data, list_data)

    first_page_works = [_summarize_work(w) for w in deduped_works[:PAGE_SIZE]]
    next_page: int | None = 2 if total > PAGE_SIZE else None

    result_dict: dict[str, Any] = {
        "search_id": saved_search["id"],
        "list_id": saved_list["id"],
        "status": list_status,
        "total": total,
        "page": 1,
        "next_page": next_page,
        "sources": saved_search["sources"],
        "works": first_page_works,
    }
    if repeated_from is not None:
        result_dict["repeated_from"] = repeated_from

    return result_dict
