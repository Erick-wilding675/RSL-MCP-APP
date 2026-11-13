"""Conector da fonte acadêmica Scopus Search API."""

from __future__ import annotations

import asyncio
import importlib.metadata
import os
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

import httpx

from rslapp.core.models import Affiliation, Author, SourceResult, Work
from rslapp.sources.base import Source

SCOPUS_SEARCH_URL = "https://api.elsevier.com/content/search/scopus"
PAGE_SIZE = 25
MAX_RESULTS_LIMIT = 5000
DEFAULT_TIMEOUT = 30.0
# NFR-04: Espera crescente de 1 s, 2 s e 4 s para até 3 novas tentativas em 429 e 5xx
RETRY_DELAYS: tuple[int, ...] = (1, 2, 4)
REQUEST_INTERVAL = 0.2

# D-023: Expressão regular para detectar códigos de campo do Scopus como TITLE-ABS-KEY( ou AUTH(
_SCOPUS_FIELD_CODE_RE = re.compile(r"\b[A-Z][A-Z-]+\(")


def _user_agent() -> str:
    try:
        version = importlib.metadata.version("rslapp")
    except importlib.metadata.PackageNotFoundError:
        version = "0"
    return f"rslapp/{version}"


def _normalize_doi(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    val = raw.strip()
    lower = val.lower()
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    ):
        if lower.startswith(prefix):
            val = val[len(prefix) :].strip()
            lower = val.lower()
    return lower if lower else None


def _normalize_orcid(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    val = raw.strip().rstrip("/")
    lower = val.lower()
    for prefix in ("https://orcid.org/", "http://orcid.org/"):
        if lower.startswith(prefix):
            val = val[len(prefix) :].strip().rstrip("/")
            lower = val.lower()
    return val.upper() if val else None


# FR-03, D-023: Prefixo de direitos autorais logo antes de © como Copyright ou (C)
_COPYRIGHT_PREFIX_RE = re.compile(r"(?i)(?:\bcopyright\s*(?:\([cс]\))?|\([cс]\))\s*$")
_RIGHTS_RESERVED_RE = re.compile(
    r"(?i)\s*(?:all rights reserved|tous droits r[eé]serv[eé]s|todos os direitos reservados)[\.\s]*$"
)
_ABBREVIATION_RE = re.compile(r"\b(?:[A-Z]\.)+\s")
_COMPANY_ABBREV_RE = re.compile(r"\b(?:Inc|Ltd|Corp|Co|Pvt)\.\s", flags=re.IGNORECASE)
_SENTENCE_END_RE = re.compile(r"\.\s+\S")


def _has_sentence_end(text: str) -> bool:
    t = _RIGHTS_RESERVED_RE.sub("", text)
    t = _ABBREVIATION_RE.sub(" ", t)
    t = _COMPANY_ABBREV_RE.sub(" ", t)
    return bool(_SENTENCE_END_RE.search(t))


# FR-03, D-023: Remove trecho de direitos autorais da última frase a partir de © (e Copyright/(C) logo antes)
def _clean_abstract(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    text = raw
    c_idx = text.rfind("©")
    if c_idx != -1:
        after_c = text[c_idx + 1 :]
        if not _has_sentence_end(after_c):
            prefix = text[:c_idx]
            match_prefix = _COPYRIGHT_PREFIX_RE.search(prefix)
            cut_idx = match_prefix.start() if match_prefix else c_idx
            text = text[:cut_idx]
    cleaned = " ".join(text.split())
    return cleaned if cleaned else None


# FR-03, D-023: authkeywords dividido por |, sem espaços nas pontas e sem repetir
def _extract_keywords(raw: Any) -> list[str]:
    if not isinstance(raw, str):
        return []
    keywords: list[str] = []
    seen: set[str] = set()
    for part in raw.split("|"):
        cleaned = part.strip()
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            keywords.append(cleaned)
    return keywords


# FR-03, D-023: Extrai os 4 primeiros dígitos de prism:coverDate quando válidos
def _extract_year(raw: Any) -> int | None:
    if not isinstance(raw, str):
        return None
    val = raw.strip()
    if len(val) >= 4 and val[:4].isascii() and val[:4].isdigit():
        return int(val[:4])
    return None


# FR-03, D-023: citedby-count como número inteiro quando for válido
def _extract_citations(raw: Any) -> dict[str, int]:
    if isinstance(raw, int) and not isinstance(raw, bool):
        return {"scopus": raw}
    if isinstance(raw, str):
        val = raw.strip()
        if val.isascii() and val.isdigit():
            return {"scopus": int(val)}
    return {}


# D-023: Mantém consultas com sintaxe Scopus ou envolve em TITLE-ABS-KEY(...)
def _build_query_param(query: str) -> str:
    clean = query.strip()
    if _SCOPUS_FIELD_CODE_RE.search(clean):
        return clean
    return f"TITLE-ABS-KEY({clean})"


# FR-03, D-004, D-023: Monta mapa de afiliações por afid a partir da lista affiliation
def _extract_affiliations(entry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_affils = entry.get("affiliation")
    affil_items = (
        [raw_affils]
        if isinstance(raw_affils, dict)
        else raw_affils
        if isinstance(raw_affils, list)
        else []
    )
    affil_map: dict[str, dict[str, Any]] = {}
    for aff in affil_items:
        if not isinstance(aff, dict):
            continue
        raw_afid = aff.get("afid")
        if raw_afid is None or isinstance(raw_afid, bool):
            continue
        afid_str = str(raw_afid).strip()
        if not afid_str:
            continue

        raw_name = aff.get("affilname")
        name = raw_name.strip() if isinstance(raw_name, str) and raw_name.strip() else None

        raw_city = aff.get("affiliation-city")
        city = raw_city.strip() if isinstance(raw_city, str) and raw_city.strip() else None

        raw_country = aff.get("affiliation-country")
        country = raw_country.strip() if isinstance(raw_country, str) and raw_country.strip() else None

        parts = [p for p in (name, city, country) if p]
        raw_aff = ", ".join(parts) if parts else ""

        affil_map[afid_str] = {
            "name": name,
            "raw": raw_aff,
            "affiliation": Affiliation(name=name, ids={"scopus": afid_str}),
        }
    return affil_map


# FR-03, D-004, D-023: Mapeia autor na visão COMPLETE com nome, ORCID, authid e afiliações
def _parse_author(raw_author: Any, affil_map: dict[str, dict[str, Any]]) -> Author | None:
    if not isinstance(raw_author, dict):
        return None

    raw_given = raw_author.get("given-name")
    raw_sur = raw_author.get("surname")
    raw_authname = raw_author.get("authname")

    clean_given = raw_given.strip() if isinstance(raw_given, str) and raw_given.strip() else ""
    clean_sur = raw_sur.strip() if isinstance(raw_sur, str) and raw_sur.strip() else ""
    clean_authname = (
        raw_authname.strip() if isinstance(raw_authname, str) and raw_authname.strip() else ""
    )

    if clean_given and clean_sur:
        name = f"{clean_given} {clean_sur}"
    elif clean_authname:
        name = clean_authname
    elif clean_given:
        name = clean_given
    elif clean_sur:
        name = clean_sur
    else:
        return None

    orcid = _normalize_orcid(raw_author.get("orcid"))

    ids: dict[str, str] = {}
    raw_authid = raw_author.get("authid")
    if raw_authid is not None and not isinstance(raw_authid, bool):
        authid_str = str(raw_authid).strip()
        if authid_str:
            ids["scopus"] = authid_str

    affiliations: list[Affiliation] = []
    raw_affiliations: list[str] = []

    raw_afids = raw_author.get("afid")
    afid_items = (
        [raw_afids]
        if isinstance(raw_afids, dict)
        else raw_afids
        if isinstance(raw_afids, list)
        else []
    )
    for item in afid_items:
        afid_val: str | None = None
        if isinstance(item, dict):
            val = item.get("$") or item.get("afid")
            if val is not None and not isinstance(val, bool) and str(val).strip():
                afid_val = str(val).strip()
        elif isinstance(item, str) and item.strip():
            afid_val = item.strip()

        if afid_val:
            aff_info = affil_map.get(afid_val)
            if aff_info is not None:
                affiliations.append(aff_info["affiliation"])
                if aff_info["raw"]:
                    raw_affiliations.append(aff_info["raw"])
            else:
                affiliations.append(Affiliation(name=None, ids={"scopus": afid_val}))

    return Author(
        name=name,
        orcid=orcid,
        ids=ids,
        position=None,
        is_corresponding=None,
        affiliations=affiliations,
        raw_affiliations=raw_affiliations,
    )


# FR-03, FR-14, D-004, D-023: Traduz registro Scopus para Work; descarta sem título
def _parse_work(entry: Any, view: str = "COMPLETE") -> Work | None:
    if not isinstance(entry, dict) or "error" in entry:
        return None

    raw_title = entry.get("dc:title")
    if not isinstance(raw_title, str):
        return None
    title = " ".join(raw_title.split())
    if not title:
        return None

    doi = _normalize_doi(entry.get("prism:doi"))
    year = _extract_year(entry.get("prism:coverDate"))

    raw_venue = entry.get("prism:publicationName")
    venue = raw_venue.strip() if isinstance(raw_venue, str) and raw_venue.strip() else None

    raw_type = entry.get("subtypeDescription")
    work_type = raw_type.strip().lower() if isinstance(raw_type, str) and raw_type.strip() else None

    if view == "STANDARD":
        abstract = None
        keywords: list[str] = []
        authors: list[Author] = []
        raw_creator = entry.get("dc:creator")
        if isinstance(raw_creator, str) and raw_creator.strip():
            authors.append(
                Author(
                    name=raw_creator.strip(),
                    orcid=None,
                    ids={},
                    position=None,
                    is_corresponding=None,
                    affiliations=[],
                    raw_affiliations=[],
                )
            )
    else:
        abstract = _clean_abstract(entry.get("dc:description"))
        keywords = _extract_keywords(entry.get("authkeywords"))
        affil_map = _extract_affiliations(entry)
        authors = []
        raw_authors = entry.get("author")
        author_items = (
            [raw_authors]
            if isinstance(raw_authors, dict)
            else raw_authors
            if isinstance(raw_authors, list)
            else []
        )
        for raw_author in author_items:
            author = _parse_author(raw_author, affil_map)
            if author is not None:
                authors.append(author)

    citations = _extract_citations(entry.get("citedby-count"))

    source_ids: dict[str, str] = {}
    raw_eid = entry.get("eid")
    if isinstance(raw_eid, str) and raw_eid.strip():
        source_ids["scopus"] = raw_eid.strip()
    raw_pmid = entry.get("pubmed-id")
    if raw_pmid is not None and not isinstance(raw_pmid, bool):
        pmid_str = str(raw_pmid).strip()
        if pmid_str:
            source_ids["pubmed"] = pmid_str

    return Work(
        title=title,
        doi=doi,
        year=year,
        type=work_type,
        venue=venue,
        abstract=abstract,
        keywords=keywords,
        authors=authors,
        references=[],
        references_count=None,
        citations=citations,
        source_ids=source_ids,
    )


# FR-13, D-023: Formata a string de consulta gravada no registro da busca (query do SourceResult)
def _format_query_text(query: str, view: str, count: int, last_page: int) -> str:
    return f"query={query} · view={view} · count={count} · páginas 1-{last_page}"


def _retry_failure(status: str, prefix: str) -> tuple[str, str]:
    return status, f"{prefix} depois de {len(RETRY_DELAYS)} tentativas"


# FR-01, FR-03, FR-14, NFR-04, D-004, D-023: Conector Scopus Search API com interface Source
class ScopusSource(Source):
    """Conector de busca acadêmica na Scopus Search API."""

    name: str = "scopus"
    needs_key: bool = True

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    ) -> None:
        self._client = client
        self._sleep = sleep

    def __repr__(self) -> str:
        return f"ScopusSource(name={self.name!r}, needs_key={self.needs_key!r})"

    # NFR-03, D-023: Consulta para cache sem expor credenciais
    def cache_query(self, query: str, max_results: int = 100) -> dict[str, Any]:
        return {
            "source": self.name,
            "query": query.strip(),
            "max_results": max_results,
        }

    @asynccontextmanager
    async def _get_client(self) -> AsyncIterator[httpx.AsyncClient]:
        if self._client is not None:
            yield self._client
        else:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                yield client

    # NFR-04, D-023: Faz chamada de uma página com até 3 novas tentativas (1, 2, 4 s) em 429 e 5xx
    async def _request_page(
        self,
        client: httpx.AsyncClient,
        params: dict[str, str],
        headers: dict[str, str],
    ) -> tuple[dict[str, Any] | None, int | None, str | None, str | None]:
        """Devolve (data, http_status_code, err_status, err_reason)."""
        max_retries = len(RETRY_DELAYS)
        err_status, err_reason = "failed", "falha inesperada ao consultar o Scopus"
        for attempt in range(max_retries + 1):
            try:
                response = await client.get(
                    SCOPUS_SEARCH_URL,
                    params=params,
                    headers=headers,
                    timeout=DEFAULT_TIMEOUT,
                )
            except httpx.TimeoutException:
                err_status, err_reason = _retry_failure("failed", "tempo limite esgotado")
            except httpx.HTTPError:
                err_status, err_reason = _retry_failure("failed", "erro de rede")
            except Exception:  # noqa: BLE001
                return None, None, "failed", "falha inesperada ao consultar o Scopus"
            else:
                status_code = response.status_code
                if status_code == 200:
                    try:
                        data = response.json()
                    except ValueError:
                        return None, 200, "failed", "resposta JSON inválida do Scopus"
                    if not isinstance(data, dict):
                        return None, 200, "failed", "resposta JSON inválida do Scopus"
                    raw_results = data.get("search-results")
                    if raw_results is not None and not isinstance(raw_results, dict):
                        return None, 200, "failed", "resposta JSON inválida do Scopus"
                    return data, 200, None, None

                if status_code == 401:
                    return None, 401, "failed", "chave do Scopus recusada"
                if status_code == 403:
                    return None, 403, None, None
                if status_code == 429:
                    err_status, err_reason = _retry_failure("rate_limited", "HTTP 429")
                elif 500 <= status_code < 600:
                    err_status, err_reason = _retry_failure("failed", f"HTTP {status_code}")
                else:
                    return None, status_code, "failed", f"HTTP {status_code}"

            if attempt < max_retries:
                await self._sleep(RETRY_DELAYS[attempt])

        return None, None, err_status, err_reason

    # FR-01, FR-03, FR-13, FR-14, NFR-04, D-004, D-023: Busca no Scopus na visão COMPLETE com fallback para STANDARD
    async def search(self, query: str, max_results: int = 100) -> SourceResult:
        clean_query = query.strip()
        query_param = _build_query_param(clean_query)
        effective_max = min(max(max_results, 1), MAX_RESULTS_LIMIT)
        # FR-13: count no log é o tamanho de página usado (PAGE_SIZE, ou menos quando max_results for menor)
        page_size = min(effective_max, PAGE_SIZE)

        raw_key = os.environ.get("SCOPUS_API_KEY")
        api_key = raw_key.strip(" \t\r\n") if raw_key else ""
        if not api_key:
            return SourceResult(
                name=self.name,
                status="missing_key",
                reason="variável SCOPUS_API_KEY não configurada",
                query=_format_query_text(query_param, "COMPLETE", page_size, 1),
                found=None,
                fetched=0,
                works=[],
            )

        raw_token = os.environ.get("SCOPUS_INSTTOKEN")
        insttoken = raw_token.strip(" \t\r\n") if raw_token else ""

        headers = {
            "X-ELS-APIKey": api_key,
            "Accept": "application/json",
            "User-Agent": _user_agent(),
        }
        if insttoken:
            headers["X-ELS-Insttoken"] = insttoken

        works: list[Work] = []
        found: int | None = None
        current_view = "COMPLETE"
        active_reason: str | None = None
        start = 0
        page = 1

        try:
            async with self._get_client() as client:
                while start < effective_max and len(works) < effective_max:
                    target = min(effective_max, found) if found is not None else effective_max
                    falta = target - start
                    if falta <= 0:
                        break
                    count = min(PAGE_SIZE, falta)

                    if start > 0:
                        await self._sleep(REQUEST_INTERVAL)

                    params: dict[str, str] = {
                        "query": query_param,
                        "view": current_view,
                        "start": str(start),
                        "count": str(count),
                    }

                    data, code, err_status, err_reason = await self._request_page(
                        client, params, headers
                    )

                    # Trata 403 e fallback da visão COMPLETE para STANDARD (D-023)
                    if code == 403:
                        if current_view == "COMPLETE":
                            await self._sleep(REQUEST_INTERVAL)
                            params["view"] = "STANDARD"
                            data, code, err_status, err_reason = await self._request_page(
                                client, params, headers
                            )
                            if code == 200:
                                current_view = "STANDARD"
                                active_reason = (
                                    "visão reduzida do Scopus: só o primeiro autor, "
                                    "sem resumo nem palavras-chave"
                                )
                        if code == 403:
                            err_status = "failed"
                            err_reason = (
                                "o Scopus recusou o acesso: confira se está na rede da instituição "
                                "ou configure SCOPUS_INSTTOKEN"
                            )

                    if err_status is not None:
                        return SourceResult(
                            name=self.name,
                            status=err_status,
                            reason=err_reason,
                            query=_format_query_text(query_param, current_view, page_size, page),
                            found=found,
                            fetched=len(works),
                            works=works,
                        )

                    assert data is not None
                    search_results = data.get("search-results")
                    if not isinstance(search_results, dict):
                        break

                    if start == 0:
                        raw_total = search_results.get("opensearch:totalResults")
                        if (
                            isinstance(raw_total, str)
                            and raw_total.strip().isascii()
                            and raw_total.strip().isdigit()
                        ):
                            found = int(raw_total.strip())
                        elif isinstance(raw_total, int) and not isinstance(raw_total, bool):
                            found = raw_total

                    raw_entries = search_results.get("entry")
                    entries = (
                        [raw_entries]
                        if isinstance(raw_entries, dict)
                        else raw_entries
                        if isinstance(raw_entries, list)
                        else []
                    )

                    for raw_entry in entries:
                        parsed = _parse_work(raw_entry, view=current_view)
                        if parsed is not None:
                            works.append(parsed)
                            if len(works) >= effective_max:
                                break

                    if len(works) >= effective_max:
                        break
                    if len(entries) < count:
                        break
                    if found is not None and (start + count) >= found:
                        break

                    start += count
                    page += 1
        except Exception:  # noqa: BLE001
            return SourceResult(
                name=self.name,
                status="failed",
                reason="falha inesperada ao consultar o Scopus",
                query=_format_query_text(query_param, current_view, page_size, page),
                found=found,
                fetched=len(works),
                works=works,
            )

        return SourceResult(
            name=self.name,
            status="ok",
            reason=active_reason,
            query=_format_query_text(query_param, current_view, page_size, page),
            found=found,
            fetched=len(works),
            works=works,
        )
