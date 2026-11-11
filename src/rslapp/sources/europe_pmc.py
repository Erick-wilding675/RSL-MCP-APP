"""Conector da fonte acadêmica Europe PMC."""

from __future__ import annotations

import asyncio
import html
import importlib.metadata
import os
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

import httpx

from rslapp.core.models import Affiliation, Author, SourceResult, Work
from rslapp.sources.base import Source

EUROPE_PMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
MAX_PER_PAGE = 100
DEFAULT_TIMEOUT = 30.0
# NFR-04: Espera crescente de 1 s, 2 s e 4 s para até 3 novas tentativas em 429 e 5xx
RETRY_DELAYS: tuple[int, ...] = (1, 2, 4)

_BLOCK_TAG_RE = re.compile(
    r"</?(?:jats:)?(?:p|title|sec|list|list-item|def-list|boxed-text|h[1-6]|div|br)(?:\s[^>]*)?/?>",
    re.IGNORECASE,
)
_TAG_RE = re.compile(r"</?[A-Za-z][\w:.-]*(\s[^>]*)?/?>")


def _user_agent() -> str:
    try:
        version = importlib.metadata.version("rslapp")
    except importlib.metadata.PackageNotFoundError:
        version = "0"
    return f"rslapp/{version}"


def _strip_url_prefixes(raw: Any, prefixes: tuple[str, ...]) -> str | None:
    if not isinstance(raw, str):
        return None
    val = raw.strip().rstrip("/")
    lower = val.lower()
    for prefix in prefixes:
        if lower.startswith(prefix):
            val = val[len(prefix) :].strip().rstrip("/")
            lower = val.lower()
    return val if val else None


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
    val = _strip_url_prefixes(raw, ("https://orcid.org/", "http://orcid.org/"))
    return val.upper() if val else None


# FR-03, D-020: Remove marcas HTML/XML, decodifica entidades e normaliza espaços simples
def _clean_html_text(raw_text: Any) -> str | None:
    if not isinstance(raw_text, str):
        return None
    text = _BLOCK_TAG_RE.sub(" ", raw_text)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    cleaned = " ".join(text.split())
    return cleaned if cleaned else None


# FR-03, D-020: Limpa marcas HTML do título e remove o ponto final solto do Europe PMC
def _clean_title(raw_title: Any) -> str | None:
    cleaned = _clean_html_text(raw_title)
    if cleaned is None:
        return None
    cleaned = cleaned.rstrip(".").strip()
    return cleaned if cleaned else None


def _extract_year(raw_year: Any) -> int | None:
    if isinstance(raw_year, bool):
        return None
    if isinstance(raw_year, int):
        return raw_year
    if isinstance(raw_year, str):
        val = raw_year.strip()
        if val.isdigit():
            return int(val)
    return None


def _extract_venue(raw_work: dict[str, Any]) -> str | None:
    journal_info = raw_work.get("journalInfo")
    if not isinstance(journal_info, dict):
        return None
    journal = journal_info.get("journal")
    if not isinstance(journal, dict):
        return None
    raw_title = journal.get("title")
    if isinstance(raw_title, str) and raw_title.strip():
        return raw_title.strip()
    return None


def _extract_keywords(raw_work: dict[str, Any]) -> list[str]:
    kw_list = raw_work.get("keywordList")
    if not isinstance(kw_list, dict):
        return []
    raw_keywords = kw_list.get("keyword")
    kw_items = (
        [raw_keywords]
        if isinstance(raw_keywords, str)
        else raw_keywords
        if isinstance(raw_keywords, list)
        else []
    )
    keywords: list[str] = []
    seen: set[str] = set()
    for item in kw_items:
        if isinstance(item, str):
            cleaned = item.strip()
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                keywords.append(cleaned)
    return keywords


def _extract_type(raw_work: dict[str, Any]) -> str | None:
    pub_type_list = raw_work.get("pubTypeList")
    if not isinstance(pub_type_list, dict):
        return None
    raw_types = pub_type_list.get("pubType")
    type_items = (
        [raw_types]
        if isinstance(raw_types, str)
        else raw_types
        if isinstance(raw_types, list)
        else []
    )
    for item in type_items:
        if isinstance(item, str) and item.strip():
            return item.strip().lower()
    return None


# FR-03, D-004, D-020: Extrai autor na ordem com nome, nome coletivo, ORCID curto e afiliações
def _parse_author(raw_author: Any) -> Author | None:
    if not isinstance(raw_author, dict):
        return None

    raw_full = raw_author.get("fullName")
    full_name = raw_full.strip() if isinstance(raw_full, str) and raw_full.strip() else ""
    raw_first = raw_author.get("firstName")
    first_name = raw_first.strip() if isinstance(raw_first, str) and raw_first.strip() else ""
    raw_last = raw_author.get("lastName")
    last_name = raw_last.strip() if isinstance(raw_last, str) and raw_last.strip() else ""
    raw_collective = raw_author.get("collectiveName")
    collective_name = (
        raw_collective.strip()
        if isinstance(raw_collective, str) and raw_collective.strip()
        else ""
    )

    if full_name:
        name = full_name
    elif first_name and last_name:
        name = f"{first_name} {last_name}"
    elif collective_name:
        name = collective_name
    elif last_name:
        name = last_name
    elif first_name:
        name = first_name
    else:
        return None

    orcid: str | None = None
    raw_author_id = raw_author.get("authorId")
    id_items = (
        [raw_author_id]
        if isinstance(raw_author_id, dict)
        else raw_author_id
        if isinstance(raw_author_id, list)
        else []
    )
    for id_item in id_items:
        if not isinstance(id_item, dict):
            continue
        id_type = id_item.get("type")
        if isinstance(id_type, str) and id_type.strip().upper() == "ORCID":
            orcid = _normalize_orcid(id_item.get("value"))
            if orcid:
                break

    raw_affiliations: list[str] = []
    affiliations: list[Affiliation] = []
    aff_details = raw_author.get("authorAffiliationDetailsList")
    if isinstance(aff_details, dict):
        aff_list = aff_details.get("authorAffiliation")
        aff_items = (
            [aff_list]
            if isinstance(aff_list, dict)
            else aff_list
            if isinstance(aff_list, list)
            else []
        )
        for aff_item in aff_items:
            if isinstance(aff_item, dict):
                raw_aff = aff_item.get("affiliation")
                if isinstance(raw_aff, str) and raw_aff.strip():
                    text = raw_aff.strip()
                    raw_affiliations.append(text)
                    affiliations.append(Affiliation(name=text))

    return Author(
        name=name,
        orcid=orcid,
        ids={},
        position=None,
        is_corresponding=None,
        affiliations=affiliations,
        raw_affiliations=raw_affiliations,
    )


# FR-03, FR-14, D-004, D-020: Traduz registro core do Europe PMC para Work; descarta sem título
def _parse_work(raw_work: Any) -> Work | None:
    if not isinstance(raw_work, dict):
        return None
    title = _clean_title(raw_work.get("title"))
    if title is None:
        return None

    doi = _normalize_doi(raw_work.get("doi") or raw_work.get("DOI"))
    year = _extract_year(raw_work.get("pubYear"))
    venue = _extract_venue(raw_work)
    abstract = _clean_html_text(raw_work.get("abstractText"))
    keywords = _extract_keywords(raw_work)
    work_type = _extract_type(raw_work)

    authors: list[Author] = []
    author_list = raw_work.get("authorList")
    if isinstance(author_list, dict):
        raw_authors = author_list.get("author")
        author_items = (
            [raw_authors]
            if isinstance(raw_authors, dict)
            else raw_authors
            if isinstance(raw_authors, list)
            else []
        )
        for raw_author in author_items:
            parsed_author = _parse_author(raw_author)
            if parsed_author is not None:
                authors.append(parsed_author)

    citations: dict[str, int] = {}
    raw_cited = raw_work.get("citedByCount")
    if isinstance(raw_cited, int) and not isinstance(raw_cited, bool):
        citations["europe_pmc"] = raw_cited

    source_ids: dict[str, str] = {}
    raw_src = raw_work.get("source")
    raw_id = raw_work.get("id")
    src_str = (
        str(raw_src).strip()
        if raw_src is not None and not isinstance(raw_src, bool) and str(raw_src).strip()
        else None
    )
    id_str = (
        str(raw_id).strip()
        if raw_id is not None and not isinstance(raw_id, bool) and str(raw_id).strip()
        else None
    )
    if src_str and id_str:
        source_ids["europe_pmc"] = f"{src_str}:{id_str}"

    raw_pmid = raw_work.get("pmid")
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


def _format_query_text(query: str, page_size: int, last_page: int) -> str:
    return f"query={query} · pageSize={page_size} · páginas 1-{last_page}"


def _retry_failure(status: str, prefix: str) -> tuple[str, str]:
    return status, f"{prefix} depois de {len(RETRY_DELAYS)} tentativas"


# FR-01, FR-03, FR-14, NFR-04, D-004, D-020: Conector Europe PMC com paginação por cursorMark
class EuropePMCSource(Source):
    """Conector de busca acadêmica na API REST do Europe PMC."""

    name: str = "europe_pmc"
    needs_key: bool = False

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    ) -> None:
        self._client = client
        self._sleep = sleep

    def __repr__(self) -> str:
        return f"EuropePMCSource(name={self.name!r}, needs_key={self.needs_key!r})"

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

    # NFR-04, D-020: Faz a chamada de uma página com até 3 novas tentativas (1, 2, 4 s) em 429 e 5xx
    async def _request_page(
        self,
        client: httpx.AsyncClient,
        params: dict[str, str],
        headers: dict[str, str],
    ) -> tuple[dict[str, Any] | None, str | None, str | None]:
        max_retries = len(RETRY_DELAYS)
        err_status, err_reason = "failed", "falha inesperada ao consultar o Europe PMC"
        for attempt in range(max_retries + 1):
            try:
                response = await client.get(
                    EUROPE_PMC_SEARCH_URL,
                    params=params,
                    headers=headers,
                    timeout=DEFAULT_TIMEOUT,
                )
            except httpx.TimeoutException:
                err_status, err_reason = _retry_failure("failed", "tempo limite esgotado")
            except httpx.HTTPError:
                err_status, err_reason = _retry_failure("failed", "erro de rede")
            except Exception:  # noqa: BLE001
                return None, "failed", "falha inesperada ao consultar o Europe PMC"
            else:
                status_code = response.status_code
                if status_code == 200:
                    try:
                        data = response.json()
                    except ValueError:
                        return None, "failed", "resposta JSON inválida do Europe PMC"
                    if not isinstance(data, dict):
                        return None, "failed", "resposta JSON inválida do Europe PMC"
                    raw_result_list = data.get("resultList")
                    if raw_result_list is not None and not isinstance(raw_result_list, dict):
                        return None, "failed", "resposta JSON inválida do Europe PMC"
                    if isinstance(raw_result_list, dict):
                        raw_results = raw_result_list.get("result")
                        if raw_results is not None and not isinstance(raw_results, list):
                            return None, "failed", "resposta JSON inválida do Europe PMC"
                    return data, None, None

                if status_code == 429:
                    err_status, err_reason = _retry_failure("rate_limited", "HTTP 429")
                elif 500 <= status_code < 600:
                    err_status, err_reason = _retry_failure("failed", f"HTTP {status_code}")
                else:
                    return None, "failed", f"HTTP {status_code}"

            if attempt < max_retries:
                await self._sleep(RETRY_DELAYS[attempt])

        return None, err_status, err_reason

    # FR-01, NFR-04, D-020: Busca sequencial por cursorMark com email opcional de RSL_CONTACT_EMAIL
    async def search(self, query: str, max_results: int = 100) -> SourceResult:
        clean_query = query.strip()
        effective_max = max(max_results, 1)
        page_size = min(effective_max, MAX_PER_PAGE)

        raw_email = os.environ.get("RSL_CONTACT_EMAIL")
        contact_email = raw_email.strip() if raw_email and raw_email.strip() else None

        headers = {
            "User-Agent": _user_agent(),
        }

        works: list[Work] = []
        found: int | None = None
        page = 1
        cursor = "*"

        try:
            async with self._get_client() as client:
                while True:
                    params: dict[str, str] = {
                        "query": clean_query,
                        "resultType": "core",
                        "format": "json",
                        "pageSize": str(page_size),
                        "cursorMark": cursor,
                    }
                    if contact_email:
                        params["email"] = contact_email

                    data, err_status, err_reason = await self._request_page(
                        client, params, headers
                    )
                    if err_status is not None:
                        return SourceResult(
                            name=self.name,
                            status=err_status,
                            reason=err_reason,
                            query=_format_query_text(clean_query, page_size, page),
                            found=found,
                            fetched=len(works),
                            works=works,
                        )

                    assert data is not None
                    if page == 1:
                        raw_total = data.get("hitCount")
                        if isinstance(raw_total, int) and not isinstance(raw_total, bool):
                            found = raw_total

                    result_list = data.get("resultList")
                    raw_items = (
                        result_list.get("result")
                        if isinstance(result_list, dict)
                        else None
                    )
                    if not isinstance(raw_items, list) or not raw_items:
                        break

                    for raw_item in raw_items:
                        parsed = _parse_work(raw_item)
                        if parsed is not None:
                            works.append(parsed)
                            if len(works) >= effective_max:
                                break

                    if len(works) >= effective_max:
                        break
                    if len(raw_items) < page_size:
                        break

                    raw_next_cursor = data.get("nextCursorMark")
                    if not isinstance(raw_next_cursor, str) or not raw_next_cursor.strip():
                        break
                    next_cursor = raw_next_cursor.strip()
                    if next_cursor == cursor:
                        break

                    cursor = next_cursor
                    page += 1
        except Exception:  # noqa: BLE001
            return SourceResult(
                name=self.name,
                status="failed",
                reason="falha inesperada ao consultar o Europe PMC",
                query=_format_query_text(clean_query, page_size, page),
                found=found,
                fetched=len(works),
                works=works,
            )

        return SourceResult(
            name=self.name,
            status="ok",
            reason=None,
            query=_format_query_text(clean_query, page_size, page),
            found=found,
            fetched=len(works),
            works=works,
        )


EuropePmcSource = EuropePMCSource
