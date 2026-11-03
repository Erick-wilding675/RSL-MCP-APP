"""Miolo de consulta de trabalhos relacionados (referências e citações), deduplicação e gravação."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from rslapp.core.dedup import deduplicate_works_with_merge, normalize_doi
from rslapp.core.errors import RSLError
from rslapp.core.models import OriginWorkResult, SourceResult, Work
from rslapp.core.search import _select_sources, _summarize_work
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


def _is_ascii_digits(s: str) -> bool:
    return bool(s) and all("0" <= c <= "9" for c in s)


# FR-15, D-002: Validação estrita de work_id (apenas W[0-9]+ ASCII após remover prefixo)
def _validate_and_normalize_work_id(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise RSLError("invalid_input", "work_id não pode ser vazio")
    val = raw.strip()
    lower = val.lower()
    for prefix in ("https://openalex.org/", "http://openalex.org/"):
        if lower.startswith(prefix):
            val = val[len(prefix) :].strip()
            break
    if val.startswith(("W", "w")):
        val = "W" + val[1:]
    if not val.startswith("W") or len(val) < 2 or not _is_ascii_digits(val[1:]):
        raise RSLError("invalid_input", f"work_id inválido: {raw}")
    return val


# FR-15, D-002: Validação estrita de DOI (começa com 10., sem espaço, ?, #, % nem segmentos . ou ..)
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
        clean_doi = _validate_and_normalize_doi(doi)
        origin_work = clean_doi
    else:
        assert work_id is not None
        clean_work_id = _validate_and_normalize_work_id(work_id)
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

        oa_origin_raw = await openalex_src.get_origin_work(clean_work_id)
        if isinstance(oa_origin_raw, tuple):
            oa_data, oa_status, oa_reason = oa_origin_raw[:3]
            oa_not_found = getattr(oa_origin_raw, "not_found", False) or (
                oa_status == "failed" and oa_reason == "HTTP 404"
            )
        elif isinstance(oa_origin_raw, OriginWorkResult):
            oa_data = oa_origin_raw.data
            oa_status = oa_origin_raw.status
            oa_reason = oa_origin_raw.reason
            oa_not_found = oa_origin_raw.not_found
        else:
            oa_data = getattr(oa_origin_raw, "data", None)
            oa_status = getattr(oa_origin_raw, "status", None)
            oa_reason = getattr(oa_origin_raw, "reason", None)
            oa_not_found = bool(getattr(oa_origin_raw, "not_found", False))

        if oa_status == "missing_key":
            raise RSLError("no_source_available", "nenhuma fonte pode responder; configure OPENALEX_API_KEY")

        if oa_not_found:
            raise RSLError("work_not_found", f"artigo {clean_work_id} não encontrado")

        if oa_status is not None:
            # Outras falhas (500, timeout, rate_limited): grava lista incomplete com motivo da fonte (FR-08)
            source_results_map["openalex"] = SourceResult(
                name="openalex",
                status=oa_status,
                reason=oa_reason,
                query=f"work_id={clean_work_id}",
                found=None,
                fetched=0,
                works=[],
                not_found=False,
            )
            if s2_src is not None:
                source_results_map["semantic_scholar"] = SourceResult(
                    name="semantic_scholar",
                    status="not_supported",
                    reason="artigo de origem sem DOI",
                    query="",
                    found=None,
                    fetched=0,
                    works=[],
                )
        else:
            assert oa_data is not None
            resolved_doi = normalize_doi(oa_data.get("doi"))
            resolved_oa_id = _short_openalex_id(oa_data.get("id")) or clean_work_id

            # Prepara chamadas concorrentes
            async def _call_oa() -> SourceResult:
                return await openalex_src.related(
                    resolved_oa_id, direction, max_results, origin_data=oa_data
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

        oa_origin_raw = None
        if openalex_src is not None and hasattr(openalex_src, "get_origin_work"):
            oa_origin_raw = await openalex_src.get_origin_work(clean_doi)

        if oa_origin_raw is not None:
            if isinstance(oa_origin_raw, tuple):
                oa_data, oa_status, oa_reason = oa_origin_raw[:3]
                oa_is_404 = getattr(oa_origin_raw, "not_found", False) or (
                    oa_status == "failed" and oa_reason == "HTTP 404"
                )
            elif isinstance(oa_origin_raw, OriginWorkResult):
                oa_data = oa_origin_raw.data
                oa_status = oa_origin_raw.status
                oa_reason = oa_origin_raw.reason
                oa_is_404 = oa_origin_raw.not_found
            else:
                oa_data = getattr(oa_origin_raw, "data", None)
                oa_status = getattr(oa_origin_raw, "status", None)
                oa_reason = getattr(oa_origin_raw, "reason", None)
                oa_is_404 = bool(getattr(oa_origin_raw, "not_found", False))
        else:
            oa_data = None
            oa_status = None
            oa_reason = None
            oa_is_404 = False

        if oa_status == "missing_key":
            source_results_map["openalex"] = SourceResult(
                name="openalex",
                status="missing_key",
                reason=oa_reason,
                query=f"doi:{clean_doi}",
                found=None,
                fetched=0,
                works=[],
            )

        oa_has_data = oa_data is not None and oa_status is None
        oa_failed_other = bool(
            oa_status is not None and not oa_is_404 and oa_status != "missing_key"
        )

        if oa_is_404 or openalex_src is None or oa_failed_other or not oa_has_data:
            if oa_is_404:
                source_results_map["openalex"] = SourceResult(
                    name="openalex",
                    status="failed",
                    reason=oa_reason or "HTTP 404",
                    query=f"doi:{clean_doi}",
                    found=None,
                    fetched=0,
                    works=[],
                    not_found=True,
                )
            elif oa_failed_other:
                source_results_map["openalex"] = SourceResult(
                    name="openalex",
                    status=oa_status,
                    reason=oa_reason,
                    query=f"doi:{clean_doi}",
                    found=None,
                    fetched=0,
                    works=[],
                    not_found=False,
                )

            if s2_src is not None and hasattr(s2_src, "related"):
                s2_res = await s2_src.related(clean_doi, direction, max_results)
                source_results_map["semantic_scholar"] = s2_res

                # Se ambas as fontes responderam 404 (ou OpenAlex 404 e S2 não achou com 404):
                # Erro work_not_found e nada é gravado
                s2_is_404 = getattr(s2_res, "not_found", False) or (
                    s2_res.status == "failed" and s2_res.reason == "HTTP 404"
                )
                if s2_is_404 and (oa_is_404 or openalex_src is None):
                    raise RSLError("work_not_found", f"artigo {clean_doi} não encontrado")
            else:
                if oa_is_404:
                    raise RSLError("work_not_found", f"artigo {clean_doi} não encontrado")

        else:
            # OpenAlex achou o artigo de origem
            resolved_oa_id = _short_openalex_id(oa_data.get("id")) or clean_doi

            async def _call_oa_with_origin() -> SourceResult:
                return await openalex_src.related(
                    resolved_oa_id, direction, max_results, origin_data=oa_data
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
