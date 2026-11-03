"""Miolo de consulta de trabalhos relacionados (referências e citações), deduplicação e gravação."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from rslapp.core.dedup import deduplicate_works_with_merge, normalize_doi
from rslapp.core.errors import RSLError
from rslapp.core.models import SourceResult, Work
from rslapp.sources.base import Source
from rslapp.store import Store

PAGE_SIZE = 25
DEFAULT_MAX_RESULTS = 1_000
MIN_MAX_RESULTS = 1
MAX_MAX_RESULTS = 10_000

__all__ = [
    "DEFAULT_MAX_RESULTS",
    "MAX_MAX_RESULTS",
    "MIN_MAX_RESULTS",
    "PAGE_SIZE",
    "run_related",
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


def _short_openalex_id(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    val = raw.strip().rstrip("/")
    lower = val.lower()
    for prefix in ("https://openalex.org/", "http://openalex.org/"):
        if lower.startswith(prefix):
            val = val[len(prefix) :].strip().rstrip("/")
            lower = val.lower()
    return val.upper() if val else None


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


# FR-15, FR-08, FR-14, UC-04, D-005, D-010: Orquestração de referências e citações de um artigo
async def run_related(
    store: Store,
    sources: Sequence[Source],
    *,
    direction: str,
    doi: str | None = None,
    work_id: str | None = None,
    request_summary: str = "",
    max_results: int = DEFAULT_MAX_RESULTS,
    source_names: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Busca referências ou citações nas fontes configuradas, deduplica e grava lista própria."""
    if not isinstance(direction, str) or direction not in ("references", "citations"):
        raise RSLError("invalid_input", "direction deve ser 'references' ou 'citations'")

    if (doi is None and work_id is None) or (doi is not None and work_id is not None):
        raise RSLError("invalid_input", "informe exatamente um entre doi ou work_id")

    clean_doi: str | None = None
    clean_work_id: str | None = None

    if doi is not None:
        if not isinstance(doi, str) or not doi.strip():
            raise RSLError("invalid_input", "doi não pode ser vazio")
        clean_doi = normalize_doi(doi) or doi.strip()
        origin_work = clean_doi
    else:
        assert work_id is not None
        if not isinstance(work_id, str) or not work_id.strip():
            raise RSLError("invalid_input", "work_id não pode ser vazio")
        clean_work_id = work_id.strip()
        origin_work = clean_work_id

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

    openalex_src: Any = next((s for s in selected_sources if s.name == "openalex"), None)
    s2_src: Any = next((s for s in selected_sources if s.name == "semantic_scholar"), None)

    source_results_map: dict[str, SourceResult] = {}

    # FR-15, FR-08: Crossref não suporta referências completas nem citações abertas
    for src in selected_sources:
        if src.name == "crossref" or not hasattr(src, "related"):
            source_results_map[src.name] = SourceResult(
                name=src.name,
                status="not_supported",
                reason="não suportado pela Crossref" if src.name == "crossref" else f"não suportado por {src.name}",
                query=src.name,
                found=None,
                fetched=0,
                works=[],
            )

    # FR-15, D-010: Resolução do artigo de origem e consulta concorrente às fontes
    if clean_work_id is not None:
        # Origem fornecida por work_id (OpenAlex ID)
        if openalex_src is None or not hasattr(openalex_src, "get_origin_work"):
            raise RSLError("work_not_found", f"artigo {clean_work_id} não encontrado")

        origin_data, oa_status, _oa_reason = await openalex_src.get_origin_work(clean_work_id)
        if oa_status == "missing_key":
            raise RSLError("no_source_available", "nenhuma fonte pode responder; configure OPENALEX_API_KEY")
        if oa_status is not None:
            raise RSLError("work_not_found", f"artigo {clean_work_id} não encontrado")

        assert origin_data is not None
        resolved_doi = normalize_doi(origin_data.get("doi"))
        resolved_oa_id = _short_openalex_id(origin_data.get("id")) or clean_work_id

        # Prepara chamadas concorrentes
        async def _call_oa() -> SourceResult:
            return await openalex_src.related(
                resolved_oa_id, direction, max_results, origin_data=origin_data
            )

        async def _call_s2() -> SourceResult:
            if s2_src is None or not hasattr(s2_src, "related"):
                return SourceResult(
                    name="semantic_scholar",
                    status="not_supported",
                    reason="artigo de origem sem DOI",
                    query="",
                    found=None,
                    fetched=0,
                    works=[],
                )
            if not resolved_doi:
                return SourceResult(
                    name=s2_src.name,
                    status="not_supported",
                    reason="artigo de origem sem DOI",
                    query="",
                    found=None,
                    fetched=0,
                    works=[],
                )
            return await s2_src.related(resolved_doi, direction, max_results)

        tasks: list[asyncio.Task[Any]] = []
        task_names: list[str] = []
        if openalex_src is not None and "openalex" not in source_results_map:
            tasks.append(asyncio.create_task(_call_oa()))
            task_names.append("openalex")
        if s2_src is not None and "semantic_scholar" not in source_results_map:
            tasks.append(asyncio.create_task(_call_s2()))
            task_names.append("semantic_scholar")

        if tasks:
            outcomes = await asyncio.gather(*tasks)
            for name, outcome in zip(task_names, outcomes):
                source_results_map[name] = outcome

    else:
        # Origem fornecida por DOI
        assert clean_doi is not None

        oa_origin_data: dict[str, Any] | None = None
        oa_failed_404 = False
        oa_lookup_status: str | None = None
        oa_lookup_reason: str | None = None

        if openalex_src is not None and hasattr(openalex_src, "get_origin_work"):
            data, err_status, err_reason = await openalex_src.get_origin_work(clean_doi)
            if err_status is None:
                oa_origin_data = data
            elif err_reason == "HTTP 404":
                oa_failed_404 = True
            else:
                oa_lookup_status = err_status
                oa_lookup_reason = err_reason

        # Se o OpenAlex não achou (404) e a entrada é um DOI, segue só com a Semantic Scholar
        if oa_failed_404 or openalex_src is None or oa_origin_data is None:
            if oa_failed_404:
                source_results_map["openalex"] = SourceResult(
                    name="openalex",
                    status="failed",
                    reason="HTTP 404",
                    query=f"doi:{clean_doi}",
                    found=None,
                    fetched=0,
                    works=[],
                )
            elif oa_lookup_status is not None:
                source_results_map["openalex"] = SourceResult(
                    name="openalex",
                    status=oa_lookup_status,
                    reason=oa_lookup_reason,
                    query=f"doi:{clean_doi}",
                    found=None,
                    fetched=0,
                    works=[],
                )

            if s2_src is not None and hasattr(s2_src, "related"):
                s2_res = await s2_src.related(clean_doi, direction, max_results)
                if s2_res.status == "failed" and s2_res.reason == "HTTP 404":
                    # Nenhuma fonte achou o artigo: erro work_not_found e nada gravado
                    raise RSLError("work_not_found", f"artigo {clean_doi} não encontrado")
                source_results_map["semantic_scholar"] = s2_res
            else:
                raise RSLError("work_not_found", f"artigo {clean_doi} não encontrado")

        else:
            # OpenAlex achou o artigo de origem
            resolved_oa_id = _short_openalex_id(oa_origin_data.get("id")) or clean_doi

            async def _call_oa_with_origin() -> SourceResult:
                return await openalex_src.related(
                    resolved_oa_id, direction, max_results, origin_data=oa_origin_data
                )

            async def _call_s2_direct() -> SourceResult:
                return await s2_src.related(clean_doi, direction, max_results)

            tasks = []
            task_names = []
            if "openalex" not in source_results_map:
                tasks.append(asyncio.create_task(_call_oa_with_origin()))
                task_names.append("openalex")
            if s2_src is not None and "semantic_scholar" not in source_results_map:
                tasks.append(asyncio.create_task(_call_s2_direct()))
                task_names.append("semantic_scholar")

            if tasks:
                outcomes = await asyncio.gather(*tasks)
                for name, outcome in zip(task_names, outcomes):
                    source_results_map[name] = outcome

    # Monta a lista ordenada segundo selected_sources
    source_entries: list[dict[str, Any]] = []
    raw_works: list[Work] = []

    for src in selected_sources:
        result = source_results_map.get(src.name)
        if result is None:
            continue
        raw_works.extend(result.works)
        source_entries.append(
            {
                "name": result.name,
                "query": result.query,
                "status": result.status,
                "reason": result.reason,
                "found": result.found,
                "fetched": result.fetched,
                "from_cache": False,
                "fetched_at": None,
            }
        )

    # D-002: Erro no_source_available quando todas as fontes estão sem chave
    if all(entry["status"] == "missing_key" for entry in source_entries):
        raise RSLError(
            "no_source_available",
            "nenhuma fonte pode responder; configure OPENALEX_API_KEY",
        )

    # FR-04, FR-14: Deduplicação e junção entre fontes com precedência e divergências
    dedup_result = deduplicate_works_with_merge(raw_works)
    deduped_works = dedup_result.works
    total = len(deduped_works)

    # FR-08, D-010: Lista incompleta quando alguma fonte não terminou em ok ou teve teto/limite
    list_status = (
        "complete"
        if all(entry["status"] == "ok" and not entry.get("reason") for entry in source_entries)
        else "incomplete"
    )

    # FR-05, FR-08, FR-15, UC-04, D-005, D-010: Gravação em searches/, lists/ e log.md
    params_dict: dict[str, Any] = {
        "direction": direction,
        "max_results": max_results,
        "sources": [src.name for src in selected_sources],
    }
    if clean_doi:
        params_dict["doi"] = clean_doi
    if clean_work_id:
        params_dict["work_id"] = clean_work_id

    search_data: dict[str, Any] = {
        "kind": "related",
        "request_summary": request_summary,
        "repeated_from": None,
        "origin": {
            "work": origin_work,
            "direction": direction,
        },
        "params": params_dict,
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
