"""Conector da fonte acadêmica BDTD (Biblioteca Digital Brasileira de Teses e Dissertações - IBICT)."""

from __future__ import annotations

import asyncio
import html
import importlib.metadata
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

import httpx

from rslapp.core.models import Affiliation, Author, SourceResult, Work
from rslapp.sources.base import Source

BDTD_SEARCH_URL = "https://bdtd.ibict.br/vufind/api/v1/search"
MAX_PER_PAGE = 100
DEFAULT_TIMEOUT = 30.0
# NFR-04, D-035: Espera crescente de 1 s, 2 s e 4 s para até 3 novas tentativas em 429 e 5xx
RETRY_DELAYS: tuple[int, ...] = (1, 2, 4)

_LANG_PREFIX_RE = re.compile(r"^\[(?:pt|en|es|fr|de|it)\]\s*", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(19\d\d|20\d\d)\b")
_DOI_RE = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", re.IGNORECASE)

BDTD_FIELDS = [
    "id",
    "title",
    "authors",
    "publicationDates",
    "summary",
    "urls",
    "institutions",
    "formats",
    "subjects",
    "languages",
]


def _user_agent() -> str:
    try:
        version = importlib.metadata.version("rslapp")
    except importlib.metadata.PackageNotFoundError:
        version = "0"
    return f"rslapp/{version}"


def _clean_text(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    text = html.unescape(raw)
    text = _LANG_PREFIX_RE.sub("", text.strip())
    cleaned = " ".join(text.split())
    return cleaned if cleaned else None


def _extract_doi(urls_data: Any) -> str | None:
    if not isinstance(urls_data, list):
        return None
    for entry in urls_data:
        target = ""
        if isinstance(entry, dict):
            target = f"{entry.get('url', '')} {entry.get('desc', '')}"
        elif isinstance(entry, str):
            target = entry
        match = _DOI_RE.search(target)
        if match:
            doi = match.group(1).rstrip(".").strip().lower()
            return doi
    return None


def _extract_year(pub_dates: Any) -> int | None:
    if isinstance(pub_dates, list):
        for item in pub_dates:
            match = _YEAR_RE.search(str(item))
            if match:
                return int(match.group(1))
    elif isinstance(pub_dates, str):
        match = _YEAR_RE.search(pub_dates)
        if match:
            return int(match.group(1))
    return None


def _extract_institution(inst_data: Any) -> str | None:
    if isinstance(inst_data, list) and inst_data:
        first = inst_data[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
    elif isinstance(inst_data, str) and inst_data.strip():
        return inst_data.strip()
    return None


def _determine_document_type(formats_data: Any) -> str:
    if isinstance(formats_data, list):
        lower_formats = [str(f).lower() for f in formats_data]
        if any("master" in f for f in lower_formats):
            return "dissertation"
        if any("doctor" in f or "thesis" in f for f in lower_formats):
            return "thesis"
    return "thesis"


def _extract_keywords(subjects_data: Any) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()

    def _add_kw(raw_kw: str) -> None:
        cleaned = _clean_text(raw_kw)
        if cleaned:
            low = cleaned.lower()
            if low not in seen:
                seen.add(low)
                keywords.append(cleaned)

    if isinstance(subjects_data, list):
        for item in subjects_data:
            if isinstance(item, list):
                for sub in item:
                    if isinstance(sub, str):
                        _add_kw(sub)
            elif isinstance(item, str):
                _add_kw(item)

    return keywords


def _extract_authors(authors_data: Any, institution: str | None) -> list[Author]:
    authors: list[Author] = []
    if not isinstance(authors_data, dict):
        return authors

    affils = [Affiliation(name=institution)] if institution else []
    raw_affils = [institution] if institution else []

    primary_dict = authors_data.get("primary")
    if isinstance(primary_dict, dict):
        for name in primary_dict:
            cleaned_name = " ".join(str(name).split())
            if cleaned_name:
                authors.append(
                    Author(
                        name=cleaned_name,
                        position=1 if len(authors) == 0 else None,
                        affiliations=affils,
                        raw_affiliations=raw_affils,
                    )
                )

    secondary_dict = authors_data.get("secondary")
    if isinstance(secondary_dict, dict):
        for name in secondary_dict:
            cleaned_name = " ".join(str(name).split())
            if cleaned_name:
                authors.append(
                    Author(
                        name=cleaned_name,
                        position=None,
                        affiliations=affils,
                        raw_affiliations=raw_affils,
                    )
                )

    return authors


# FR-01, FR-03, D-035: Traduz um registro JSON retornado pela API VuFind da BDTD para Work
def _record_to_work(record: dict[str, Any]) -> Work | None:
    if not isinstance(record, dict):
        return None

    raw_title = record.get("title")
    title = _clean_text(raw_title)
    if not title:
        return None

    record_id = record.get("id")
    source_id = str(record_id) if record_id else None

    year = _extract_year(record.get("publicationDates"))
    institution = _extract_institution(record.get("institutions"))

    summary_list = record.get("summary")
    abstract = None
    if isinstance(summary_list, list) and summary_list:
        abstract = _clean_text(summary_list[0])
    elif isinstance(summary_list, str):
        abstract = _clean_text(summary_list)

    doi = _extract_doi(record.get("urls"))

    venue = institution or "BDTD / IBICT"
    doc_type = _determine_document_type(record.get("formats"))
    keywords = _extract_keywords(record.get("subjects"))
    authors = _extract_authors(record.get("authors"), institution)

    source_ids = {"bdtd": source_id} if source_id else {}

    return Work(
        title=title,
        doi=doi,
        year=year,
        venue=venue,
        abstract=abstract,
        authors=authors,
        keywords=keywords,
        type=doc_type,
        source_ids=source_ids,
    )


# FR-01, NFR-04, D-035: Conector BDTD implementando a interface Source
class BDTDSource(Source):
    """Conector da BDTD (Biblioteca Digital Brasileira de Teses e Dissertações)."""

    name: str = "bdtd"
    needs_key: bool = False

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        sleep_fn: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._client = client
        self._sleep = sleep_fn

    def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
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

    async def _request_page(
        self,
        client: httpx.AsyncClient,
        query: str,
        page: int,
        limit: int,
        headers: dict[str, str],
    ) -> tuple[dict[str, Any] | None, str | None, str | None]:
        max_retries = len(RETRY_DELAYS)
        err_status, err_reason = "failed", "falha inesperada ao consultar a BDTD"

        params: list[tuple[str, str]] = [
            ("lookfor", query),
            ("page", str(page)),
            ("limit", str(limit)),
        ]
        for field in BDTD_FIELDS:
            params.append(("field[]", field))

        for attempt in range(max_retries + 1):
            try:
                response = await client.get(
                    BDTD_SEARCH_URL,
                    params=params,
                    headers=headers,
                    timeout=DEFAULT_TIMEOUT,
                )
            except httpx.TimeoutException:
                err_status, err_reason = "failed", "tempo limite esgotado"
            except httpx.HTTPError:
                err_status, err_reason = "failed", "erro de rede"
            except Exception:  # noqa: BLE001
                return None, "failed", "falha inesperada ao consultar a BDTD"
            else:
                status_code = response.status_code
                if status_code == 200:
                    try:
                        data = response.json()
                    except ValueError:
                        return None, "failed", "resposta JSON inválida da BDTD"
                    if not isinstance(data, dict):
                        return None, "failed", "resposta JSON inválida da BDTD"
                    if data.get("status") != "OK":
                        reason = str(data.get("status", "erro desconhecido"))
                        return None, "failed", f"status BDTD: {reason}"
                    return data, None, None

                if status_code == 429:
                    err_status, err_reason = "rate_limited", "HTTP 429"
                elif 500 <= status_code < 600:
                    err_status, err_reason = "failed", f"HTTP {status_code}"
                else:
                    return None, "failed", f"HTTP {status_code}"

            if attempt < max_retries:
                await self._sleep(RETRY_DELAYS[attempt])

        return None, err_status, err_reason

    # FR-01, NFR-04, D-035: Busca sequencial paginada na API REST VuFind da BDTD
    async def search(self, query: str, max_results: int = 100) -> SourceResult:
        clean_query = query.strip()
        effective_max = max(max_results, 1)

        headers = {
            "User-Agent": _user_agent(),
            "Accept": "application/json",
        }

        works: list[Work] = []
        found: int | None = None
        page = 1

        try:
            async with self._get_client() as client:
                while len(works) < effective_max:
                    page_limit = min(effective_max - len(works), MAX_PER_PAGE)
                    data, err_status, err_reason = await self._request_page(
                        client, clean_query, page, page_limit, headers
                    )

                    if data is None:
                        if not works:
                            return SourceResult(
                                name=self.name,
                                status=err_status or "failed",
                                reason=err_reason,
                                query=clean_query,
                                works=[],
                                found=found,
                                fetched=0,
                            )
                        break

                    if found is None:
                        count_val = data.get("resultCount")
                        if isinstance(count_val, int):
                            found = count_val

                    raw_records = data.get("records")
                    if not isinstance(raw_records, list) or not raw_records:
                        break

                    for rec in raw_records:
                        work = _record_to_work(rec)
                        if work is not None:
                            works.append(work)
                            if len(works) >= effective_max:
                                break

                    # Se a página retornou menos registros que o requisitado, chegamos ao fim
                    if len(raw_records) < page_limit:
                        break

                    page += 1

        except Exception as exc:  # noqa: BLE001
            return SourceResult(
                name=self.name,
                status="failed",
                reason=f"erro inesperado no conector BDTD: {exc}",
                query=clean_query,
                works=works,
                found=found,
                fetched=len(works),
            )

        return SourceResult(
            name=self.name,
            status="ok",
            reason=None,
            query=clean_query,
            works=works,
            found=found,
            fetched=len(works),
        )
