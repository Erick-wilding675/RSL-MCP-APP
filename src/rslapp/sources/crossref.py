"""Conector da fonte acadêmica Crossref."""

from __future__ import annotations

import asyncio
import html
import importlib.metadata
import os
import re
import urllib.parse
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

import httpx

from rslapp.core.models import Affiliation, Author, SourceResult, Work
from rslapp.sources.base import Source

CROSSREF_WORKS_URL = "https://api.crossref.org/works"
# FR-03, FR-14: Seleção apenas dos campos necessários da API REST da Crossref
SELECT_FIELDS = (
    "DOI,title,author,issued,container-title,abstract,"
    "reference,references-count,is-referenced-by-count,type"
)
MAX_PER_PAGE = 100
DEFAULT_TIMEOUT = 30.0
# NFR-04: Espera crescente de 1 s, 2 s e 4 s para até 3 novas tentativas em 429 e 5xx
RETRY_DELAYS: tuple[int, ...] = (1, 2, 4)

_BLOCK_TAG_RE = re.compile(
    r"</?(?:jats:)?(?:p|title|sec|list|list-item|def-list|boxed-text)(?:\s[^>]*)?>",
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


def _normalize_ror(raw: Any) -> str | None:
    val = _strip_url_prefixes(raw, ("https://ror.org/", "http://ror.org/"))
    return f"https://ror.org/{val}" if val else None


def _first_str(raw_list: Any) -> str | None:
    if isinstance(raw_list, list) and raw_list:
        first = raw_list[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
    return None


def _extract_year(raw_issued: Any) -> int | None:
    if not isinstance(raw_issued, dict):
        return None
    date_parts = raw_issued.get("date-parts")
    if not isinstance(date_parts, list) or not date_parts:
        return None
    first_date = date_parts[0]
    if not isinstance(first_date, list) or not first_date:
        return None
    raw_year = first_date[0]
    return raw_year if isinstance(raw_year, int) and not isinstance(raw_year, bool) else None


# FR-03: Remove marcas JATS/XML do resumo, decodifica entidades HTML e normaliza espaços simples
def _clean_abstract(raw_abstract: Any) -> str | None:
    if not isinstance(raw_abstract, str):
        return None
    text = _BLOCK_TAG_RE.sub(" ", raw_abstract)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    cleaned = " ".join(text.split())
    return cleaned if cleaned else None


# FR-03, D-004: Extrai dados completos de cada autor na ordem, incluindo organização, ORCID curto e ROR
def _parse_author(raw_author: Any) -> Author | None:
    if not isinstance(raw_author, dict):
        return None
    raw_given = raw_author.get("given")
    given = raw_given.strip() if isinstance(raw_given, str) and raw_given.strip() else ""
    raw_family = raw_author.get("family")
    family = raw_family.strip() if isinstance(raw_family, str) and raw_family.strip() else ""
    raw_org = raw_author.get("name")
    org_name = raw_org.strip() if isinstance(raw_org, str) and raw_org.strip() else ""

    if given and family:
        name = f"{given} {family}"
    elif family:
        name = family
    elif org_name:
        name = org_name
    elif given:
        name = given
    else:
        return None

    raw_seq = raw_author.get("sequence")
    position = raw_seq.strip() if isinstance(raw_seq, str) and raw_seq.strip() else None

    affiliations: list[Affiliation] = []
    raw_affs = raw_author.get("affiliation")
    if isinstance(raw_affs, list):
        for aff in raw_affs:
            if not isinstance(aff, dict):
                continue
            raw_aff_name = aff.get("name")
            aff_name = (
                raw_aff_name.strip()
                if isinstance(raw_aff_name, str) and raw_aff_name.strip()
                else None
            )
            inst_ids: dict[str, str] = {}
            raw_id_field = aff.get("id")
            id_items = (
                raw_id_field
                if isinstance(raw_id_field, list)
                else [raw_id_field]
                if isinstance(raw_id_field, dict)
                else []
            )
            for id_item in id_items:
                if not isinstance(id_item, dict):
                    continue
                id_type = id_item.get("id-type")
                if isinstance(id_type, str) and id_type.strip().upper() == "ROR":
                    ror = _normalize_ror(id_item.get("id"))
                    if ror:
                        inst_ids["ror"] = ror
            if aff_name is not None or inst_ids:
                affiliations.append(Affiliation(name=aff_name, ids=inst_ids))

    return Author(
        name=name,
        orcid=_normalize_orcid(raw_author.get("ORCID") or raw_author.get("orcid")),
        ids={},
        position=position,
        is_corresponding=None,
        affiliations=affiliations,
        raw_affiliations=[],
    )


# FR-03, FR-14, D-004: Traduz registro da Crossref para Work; descarta trabalho sem título
def _parse_work(raw_work: Any) -> Work | None:
    if not isinstance(raw_work, dict):
        return None
    title = _first_str(raw_work.get("title"))
    if title is None:
        return None

    doi = _normalize_doi(raw_work.get("DOI") or raw_work.get("doi"))
    year = _extract_year(raw_work.get("issued"))
    venue = _first_str(raw_work.get("container-title"))
    abstract = _clean_abstract(raw_work.get("abstract"))

    raw_type = raw_work.get("type")
    work_type = raw_type.strip() if isinstance(raw_type, str) and raw_type.strip() else None

    authors: list[Author] = []
    raw_authors = raw_work.get("author")
    if isinstance(raw_authors, list):
        for raw_author in raw_authors:
            parsed_author = _parse_author(raw_author)
            if parsed_author is not None:
                authors.append(parsed_author)

    # FR-14: Referências guardadas como DOIs minúsculos quando a referência traz DOI
    references: list[str] = []
    raw_refs = raw_work.get("reference")
    if isinstance(raw_refs, list):
        for ref in raw_refs:
            if isinstance(ref, dict):
                ref_doi = _normalize_doi(ref.get("DOI") or ref.get("doi"))
                if ref_doi:
                    references.append(ref_doi)

    raw_ref_count = raw_work.get("references-count")
    references_count = (
        raw_ref_count
        if isinstance(raw_ref_count, int) and not isinstance(raw_ref_count, bool)
        else None
    )

    citations: dict[str, int] = {}
    raw_cited = raw_work.get("is-referenced-by-count")
    if isinstance(raw_cited, int) and not isinstance(raw_cited, bool):
        citations["crossref"] = raw_cited

    source_ids: dict[str, str] = {"crossref": doi} if doi else {}

    return Work(
        title=title,
        doi=doi,
        year=year,
        type=work_type,
        venue=venue,
        abstract=abstract,
        keywords=[],
        authors=authors,
        references=references,
        references_count=references_count,
        citations=citations,
        source_ids=source_ids,
    )


def _format_query_text(query: str, rows: int, last_page: int) -> str:
    return f"query={query} · rows={rows} · páginas 1-{last_page}"


def _retry_failure(status: str, prefix: str) -> tuple[str, str]:
    return status, f"{prefix} depois de {len(RETRY_DELAYS)} tentativas"


# FR-01, FR-03, FR-14, NFR-04, D-004: Conector Crossref com paginação por cursor e fila educada
class CrossrefSource(Source):
    """Conector de busca acadêmica na API da Crossref."""

    name: str = "crossref"
    needs_key: bool = False

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    ) -> None:
        self._client = client
        self._sleep = sleep

    def __repr__(self) -> str:
        return f"CrossrefSource(name={self.name!r}, needs_key={self.needs_key!r})"

    def cache_query(self, query: str, max_results: int = 100) -> dict[str, Any]:
        effective_max = max(max_results, 1)
        rows = min(effective_max, MAX_PER_PAGE)
        return {
            "query": query.strip(),
            "max_results": max_results,
            "rows": rows,
            "select": SELECT_FIELDS,
        }

    @asynccontextmanager
    async def _get_client(self) -> AsyncIterator[httpx.AsyncClient]:
        if self._client is not None:
            yield self._client
        else:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                yield client

    # NFR-04: Faz a chamada de uma página com até 3 novas tentativas (1, 2, 4 s) em 429 e 5xx
    async def _request_page(
        self,
        client: httpx.AsyncClient,
        params: dict[str, str],
        headers: dict[str, str],
    ) -> tuple[dict[str, Any] | None, str | None, str | None]:
        max_retries = len(RETRY_DELAYS)
        err_status, err_reason = "failed", "falha inesperada ao consultar a Crossref"
        for attempt in range(max_retries + 1):
            try:
                response = await client.get(
                    CROSSREF_WORKS_URL,
                    params=params,
                    headers=headers,
                    timeout=DEFAULT_TIMEOUT,
                )
            except httpx.TimeoutException:
                err_status, err_reason = _retry_failure("failed", "tempo limite esgotado")
            except httpx.HTTPError:
                err_status, err_reason = _retry_failure("failed", "erro de rede")
            except Exception:  # noqa: BLE001
                return None, "failed", "falha inesperada ao consultar a Crossref"
            else:
                status_code = response.status_code
                if status_code == 200:
                    try:
                        data = response.json()
                    except ValueError:
                        return None, "failed", "resposta JSON inválida da Crossref"
                    if not isinstance(data, dict) or not isinstance(data.get("message"), dict):
                        return None, "failed", "resposta JSON inválida da Crossref"
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

    # FR-01, NFR-04: Busca sequencial por cursor com mailto opcional vindo de RSL_CONTACT_EMAIL
    async def search(self, query: str, max_results: int = 100) -> SourceResult:
        clean_query = query.strip()
        effective_max = max(max_results, 1)
        rows = min(effective_max, MAX_PER_PAGE)

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
                        "rows": str(rows),
                        "select": SELECT_FIELDS,
                        "cursor": cursor,
                    }
                    if contact_email:
                        params["mailto"] = contact_email

                    data, err_status, err_reason = await self._request_page(
                        client, params, headers
                    )
                    if err_status is not None:
                        return SourceResult(
                            name=self.name,
                            status=err_status,
                            reason=err_reason,
                            query=_format_query_text(clean_query, rows, page),
                            found=found,
                            fetched=len(works),
                            works=works,
                        )

                    assert data is not None
                    message = data["message"]
                    if page == 1:
                        raw_total = message.get("total-results")
                        if isinstance(raw_total, int) and not isinstance(raw_total, bool):
                            found = raw_total

                    raw_items = message.get("items")
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
                    if len(raw_items) < rows:
                        break

                    raw_next_cursor = message.get("next-cursor")
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
                reason="falha inesperada ao consultar a Crossref",
                query=_format_query_text(clean_query, rows, page),
                found=found,
                fetched=len(works),
                works=works,
            )

        return SourceResult(
            name=self.name,
            status="ok",
            reason=None,
            query=_format_query_text(clean_query, rows, page),
            found=found,
            fetched=len(works),
            works=works,
        )

    # FR-02, D-002, NFR-04: Consulta trabalho direto por DOI na Crossref
    async def find_by_doi(self, doi: str) -> SourceResult:
        """Consulta um artigo pelo DOI na Crossref."""
        clean_doi = _normalize_doi(doi) or doi.strip()
        quoted_doi = urllib.parse.quote(clean_doi, safe="")
        query_text = f"doi:{clean_doi}"

        raw_email = os.environ.get("RSL_CONTACT_EMAIL")
        contact_email = raw_email.strip() if raw_email and raw_email.strip() else None

        headers = {
            "User-Agent": _user_agent(),
        }

        url = f"{CROSSREF_WORKS_URL}/{quoted_doi}"
        params: dict[str, str] = {"select": SELECT_FIELDS}
        if contact_email:
            params["mailto"] = contact_email

        try:
            async with self._get_client() as client:
                max_retries = len(RETRY_DELAYS)
                err_status, err_reason = "failed", "falha inesperada ao consultar a Crossref"
                for attempt in range(max_retries + 1):
                    try:
                        response = await client.get(
                            url,
                            params=params,
                            headers=headers,
                            timeout=DEFAULT_TIMEOUT,
                        )
                    except httpx.TimeoutException:
                        err_status, err_reason = _retry_failure("failed", "tempo limite esgotado")
                    except httpx.HTTPError:
                        err_status, err_reason = _retry_failure("failed", "erro de rede")
                    except Exception:  # noqa: BLE001
                        return SourceResult(
                            name=self.name,
                            status="failed",
                            reason="falha inesperada ao consultar a Crossref",
                            query=query_text,
                            found=None,
                            fetched=0,
                            works=[],
                        )
                    else:
                        status_code = response.status_code
                        if status_code == 200:
                            try:
                                data = response.json()
                            except ValueError:
                                return SourceResult(
                                    name=self.name,
                                    status="failed",
                                    reason="resposta JSON inválida da Crossref",
                                    query=query_text,
                                    found=None,
                                    fetched=0,
                                    works=[],
                                )
                            if not isinstance(data, dict) or not isinstance(data.get("message"), dict):
                                return SourceResult(
                                    name=self.name,
                                    status="failed",
                                    reason="resposta JSON inválida da Crossref",
                                    query=query_text,
                                    found=None,
                                    fetched=0,
                                    works=[],
                                )
                            work = _parse_work(data["message"])
                            works = [work] if work is not None else []
                            found_cnt = len(works)
                            return SourceResult(
                                name=self.name,
                                status="ok",
                                reason=None,
                                query=query_text,
                                found=found_cnt,
                                fetched=found_cnt,
                                works=works,
                            )

                        if status_code == 404:
                            return SourceResult(
                                name=self.name,
                                status="ok",
                                reason=None,
                                query=query_text,
                                found=0,
                                fetched=0,
                                works=[],
                            )
                        if status_code == 429:
                            err_status, err_reason = _retry_failure("rate_limited", "HTTP 429")
                        elif 500 <= status_code < 600:
                            err_status, err_reason = _retry_failure("failed", f"HTTP {status_code}")
                        else:
                            return SourceResult(
                                name=self.name,
                                status="failed",
                                reason=f"HTTP {status_code}",
                                query=query_text,
                                found=None,
                                fetched=0,
                                works=[],
                            )

                    if attempt < max_retries:
                        await self._sleep(RETRY_DELAYS[attempt])

                return SourceResult(
                    name=self.name,
                    status=err_status,
                    reason=err_reason,
                    query=query_text,
                    found=None,
                    fetched=0,
                    works=[],
                )
        except Exception:  # noqa: BLE001
            return SourceResult(
                name=self.name,
                status="failed",
                reason="falha inesperada ao consultar a Crossref",
                query=query_text,
                found=None,
                fetched=0,
                works=[],
            )
