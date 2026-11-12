"""Conector da fonte acadêmica Web of Science Starter API."""

from __future__ import annotations

import asyncio
import importlib.metadata
import os
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

import httpx

from rslapp.core.models import Author, SourceResult, Work
from rslapp.sources.base import Source

# D-023: Endereço oficial da Web of Science Starter API
WOS_STARTER_URL = "https://api.clarivate.com/apis/wos-starter/v1/documents"
MAX_PAGE_SIZE = 50
DEFAULT_TIMEOUT = 30.0
# NFR-04: Espera crescente de 1 s, 2 s e 4 s para até 3 novas tentativas em 429 e 5xx
RETRY_DELAYS: tuple[int, ...] = (1, 2, 4)
# D-023, NFR-04: Intervalo mínimo entre pedidos para caber no plano de teste (1 por segundo)
REQUEST_INTERVAL = 1.1

# D-023: Expressão regular para detectar etiquetas de campo do Web of Science como TS=, AU=, TI=, etc.
_WOS_FIELD_TAG_RE = re.compile(r"\b[A-Z]{2,4}=")


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


# FR-03, D-023: Extrai os 4 primeiros dígitos de publishYear quando válidos
def _extract_year(raw: Any) -> int | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        val = raw.strip()
        if len(val) >= 4 and val[:4].isascii() and val[:4].isdigit():
            return int(val[:4])
    return None


# FR-03, D-023: Primeiro tipo de types em minúsculas
def _extract_type(raw_types: Any) -> str | None:
    if isinstance(raw_types, list) and raw_types:
        first = raw_types[0]
        if isinstance(first, str) and first.strip():
            return first.strip().lower()
    elif isinstance(raw_types, str) and raw_types.strip():
        return raw_types.strip().lower()
    return None


# FR-03, D-023: keywords.authorKeywords sem espaços nas pontas e sem repetir
def _extract_keywords(raw_kw: Any) -> list[str]:
    if not isinstance(raw_kw, dict):
        return []
    raw_author_kw = raw_kw.get("authorKeywords")
    items = (
        [raw_author_kw]
        if isinstance(raw_author_kw, str)
        else raw_author_kw
        if isinstance(raw_author_kw, list)
        else []
    )
    keywords: list[str] = []
    seen: set[str] = set()
    for item in items:
        if isinstance(item, str):
            cleaned = item.strip()
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                keywords.append(cleaned)
    return keywords


# FR-03, D-023: Extrai contagem de citações com db igual a WOS quando houver
def _extract_citations(raw_citations: Any) -> dict[str, int]:
    items = (
        [raw_citations]
        if isinstance(raw_citations, dict)
        else raw_citations
        if isinstance(raw_citations, list)
        else []
    )
    for item in items:
        if isinstance(item, dict):
            raw_db = item.get("db")
            if isinstance(raw_db, str) and raw_db.strip().upper() == "WOS":
                raw_count = item.get("count")
                if isinstance(raw_count, int) and not isinstance(raw_count, bool):
                    return {"web_of_science": raw_count}
                if isinstance(raw_count, str):
                    val = raw_count.strip()
                    if val.isascii() and val.isdigit():
                        return {"web_of_science": int(val)}
    return {}


# D-023: Mantém consultas com etiquetas de campo do Web of Science ou envolve em TS=(...)
def _build_query_param(query: str) -> str:
    clean = query.strip()
    if _WOS_FIELD_TAG_RE.search(clean):
        return clean
    return f"TS=({clean})"


# FR-03, D-004, D-023: Mapeia autores do Web of Science na ordem, sem ORCID e sem afiliações
def _parse_authors(raw_names: Any) -> list[Author]:
    if not isinstance(raw_names, dict):
        return []
    raw_authors = raw_names.get("authors")
    author_items = (
        [raw_authors]
        if isinstance(raw_authors, dict)
        else raw_authors
        if isinstance(raw_authors, list)
        else []
    )
    authors: list[Author] = []
    for raw_author in author_items:
        if not isinstance(raw_author, dict):
            continue
        raw_display = raw_author.get("displayName")
        name = (
            raw_display.strip()
            if isinstance(raw_display, str) and raw_display.strip()
            else ""
        )
        if not name:
            raw_std = raw_author.get("wosStandard")
            name = raw_std.strip() if isinstance(raw_std, str) and raw_std.strip() else ""
        if not name:
            continue

        ids: dict[str, str] = {}
        raw_rid = raw_author.get("researcherId")
        if isinstance(raw_rid, str) and raw_rid.strip():
            ids["web_of_science"] = raw_rid.strip()
        elif raw_rid is not None and not isinstance(raw_rid, bool) and str(raw_rid).strip():
            ids["web_of_science"] = str(raw_rid).strip()

        authors.append(
            Author(
                name=name,
                orcid=None,
                ids=ids,
                position=None,
                is_corresponding=None,
                affiliations=[],
                raw_affiliations=[],
            )
        )
    return authors


# FR-03, FR-14, D-004, D-023: Traduz registro Web of Science Starter para Work; descarta sem título
def _parse_work(hit: Any) -> Work | None:
    if not isinstance(hit, dict):
        return None

    raw_title = hit.get("title")
    if not isinstance(raw_title, str):
        return None
    title = " ".join(raw_title.split())
    if not title:
        return None

    raw_identifiers = hit.get("identifiers")
    identifiers = raw_identifiers if isinstance(raw_identifiers, dict) else {}
    doi = _normalize_doi(identifiers.get("doi"))

    raw_source = hit.get("source")
    source_dict = raw_source if isinstance(raw_source, dict) else {}
    year = _extract_year(source_dict.get("publishYear"))

    raw_venue = source_dict.get("sourceTitle")
    venue = (
        raw_venue.strip()
        if isinstance(raw_venue, str) and raw_venue.strip()
        else None
    )

    work_type = _extract_type(hit.get("types"))
    keywords = _extract_keywords(hit.get("keywords"))
    authors = _parse_authors(hit.get("names"))
    citations = _extract_citations(hit.get("citations"))

    source_ids: dict[str, str] = {}
    raw_uid = hit.get("uid")
    if isinstance(raw_uid, str) and raw_uid.strip():
        source_ids["web_of_science"] = raw_uid.strip()
    elif raw_uid is not None and not isinstance(raw_uid, bool) and str(raw_uid).strip():
        source_ids["web_of_science"] = str(raw_uid).strip()

    raw_pmid = identifiers.get("pmid")
    if isinstance(raw_pmid, str) and raw_pmid.strip():
        source_ids["pubmed"] = raw_pmid.strip()
    elif raw_pmid is not None and not isinstance(raw_pmid, bool) and str(raw_pmid).strip():
        source_ids["pubmed"] = str(raw_pmid).strip()

    return Work(
        title=title,
        doi=doi,
        year=year,
        type=work_type,
        venue=venue,
        abstract=None,
        keywords=keywords,
        authors=authors,
        references=[],
        references_count=None,
        citations=citations,
        source_ids=source_ids,
    )


def _format_query_text(query: str, limit: int, page: int) -> str:
    return f"q={query} · limit={limit} · page={page}"


def _retry_failure(status: str, prefix: str) -> tuple[str, str]:
    return status, f"{prefix} depois de {len(RETRY_DELAYS)} tentativas"


# FR-01, FR-03, FR-14, NFR-04, D-004, D-023: Conector Web of Science Starter API com interface Source
class WebOfScienceSource(Source):
    """Conector de busca acadêmica na Web of Science Starter API."""

    name: str = "web_of_science"
    needs_key: bool = True

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    ) -> None:
        self._client = client
        self._sleep = sleep

    def __repr__(self) -> str:
        return f"WebOfScienceSource(name={self.name!r}, needs_key={self.needs_key!r})"

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
    ) -> tuple[dict[str, Any] | None, str | None, str | None]:
        """Devolve (data, err_status, err_reason)."""
        max_retries = len(RETRY_DELAYS)
        err_status, err_reason = "failed", "falha inesperada ao consultar o Web of Science"
        for attempt in range(max_retries + 1):
            try:
                response = await client.get(
                    WOS_STARTER_URL,
                    params=params,
                    headers=headers,
                    timeout=DEFAULT_TIMEOUT,
                )
            except httpx.TimeoutException:
                err_status, err_reason = _retry_failure("failed", "tempo limite esgotado")
            except httpx.HTTPError:
                err_status, err_reason = _retry_failure("failed", "erro de rede")
            except Exception:  # noqa: BLE001
                return None, "failed", "falha inesperada ao consultar o Web of Science"
            else:
                status_code = response.status_code
                if status_code == 200:
                    try:
                        data = response.json()
                    except ValueError:
                        return None, "failed", "resposta JSON inválida do Web of Science"
                    if not isinstance(data, dict):
                        return None, "failed", "resposta JSON inválida do Web of Science"
                    return data, None, None

                if status_code in (401, 403):
                    return None, "failed", "chave do Web of Science recusada ou sem acesso"
                if status_code == 429:
                    err_status = "rate_limited"
                    err_reason = (
                        "limite diário do Web of Science atingido (50 pedidos por dia no plano de teste)"
                    )
                elif 500 <= status_code < 600:
                    err_status, err_reason = _retry_failure("failed", f"HTTP {status_code}")
                else:
                    return None, "failed", f"HTTP {status_code}"

            if attempt < max_retries:
                await self._sleep(RETRY_DELAYS[attempt])

        return None, err_status, err_reason

    # FR-01, FR-03, FR-14, NFR-04, D-004, D-023: Busca na Web of Science Starter API
    async def search(self, query: str, max_results: int = 100) -> SourceResult:
        clean_query = query.strip()
        query_param = _build_query_param(clean_query)
        effective_max = max(max_results, 1)
        limit = min(MAX_PAGE_SIZE, effective_max)

        raw_key = os.environ.get("WOS_STARTER_API_KEY")
        api_key = raw_key.strip(" \t\r\n") if raw_key else ""
        if not api_key:
            return SourceResult(
                name=self.name,
                status="missing_key",
                reason="variável WOS_STARTER_API_KEY não configurada",
                query=_format_query_text(query_param, limit, 1),
                found=None,
                fetched=0,
                works=[],
            )

        headers = {
            "X-ApiKey": api_key,
            "Accept": "application/json",
            "User-Agent": _user_agent(),
        }

        works: list[Work] = []
        found: int | None = None
        page = 1

        try:
            async with self._get_client() as client:
                while len(works) < effective_max:
                    if page > 1:
                        await self._sleep(REQUEST_INTERVAL)

                    params: dict[str, str] = {
                        "db": "WOS",
                        "q": query_param,
                        "limit": str(limit),
                        "page": str(page),
                    }

                    data, err_status, err_reason = await self._request_page(
                        client, params, headers
                    )
                    if err_status is not None:
                        return SourceResult(
                            name=self.name,
                            status=err_status,
                            reason=err_reason,
                            query=_format_query_text(query_param, limit, page),
                            found=found,
                            fetched=len(works),
                            works=works,
                        )

                    assert data is not None
                    if page == 1:
                        raw_metadata = data.get("metadata")
                        if isinstance(raw_metadata, dict):
                            raw_total = raw_metadata.get("total")
                            if isinstance(raw_total, int) and not isinstance(raw_total, bool):
                                found = raw_total
                            elif isinstance(raw_total, str) and raw_total.strip().isdigit():
                                found = int(raw_total.strip())

                    raw_hits = data.get("hits")
                    hits = (
                        [raw_hits]
                        if isinstance(raw_hits, dict)
                        else raw_hits
                        if isinstance(raw_hits, list)
                        else []
                    )

                    if not hits:
                        break

                    for raw_hit in hits:
                        parsed = _parse_work(raw_hit)
                        if parsed is not None:
                            works.append(parsed)
                            if len(works) >= effective_max:
                                break

                    if len(works) >= effective_max:
                        break
                    if len(hits) < limit:
                        break
                    if found is not None and (page * limit) >= found:
                        break

                    page += 1
        except Exception:  # noqa: BLE001
            return SourceResult(
                name=self.name,
                status="failed",
                reason="falha inesperada ao consultar o Web of Science",
                query=_format_query_text(query_param, limit, page),
                found=found,
                fetched=len(works),
                works=works,
            )

        return SourceResult(
            name=self.name,
            status="ok",
            reason=None,
            query=_format_query_text(query_param, limit, page),
            found=found,
            fetched=len(works),
            works=works,
        )
