"""Conector da fonte acadêmica Semantic Scholar."""

from __future__ import annotations

import asyncio
import importlib.metadata
import os
import time
import urllib.parse
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

import httpx

from rslapp.core.models import Author, SourceResult, Work
from rslapp.sources.base import Source

SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
# FR-03, FR-14, D-004: Campos do artigo requisitados na busca por relevância
SELECT_FIELDS = (
    "title,externalIds,abstract,venue,journal,year,"
    "publicationTypes,referenceCount,citationCount,authors"
)
MAX_PER_PAGE = 100
MAX_RESULTS_LIMIT = 1_000
DEFAULT_TIMEOUT = 30.0
# NFR-04: Espera crescente de 1 s, 2 s e 4 s para até 3 novas tentativas em 429 e 5xx
RETRY_DELAYS: tuple[int, ...] = (1, 2, 4)
# FR-08, NFR-04: Intervalo mínimo de 1 segundo entre inícios de chamadas
RATE_INTERVAL: float = 1.0

# FR-08, NFR-04: Trava e relógio no nível do módulo para garantir 1 chamada por vez com >= 1s de intervalo
RATE_LOCK = asyncio.Lock()
_last_call_start: float | None = None
_module_clock: Callable[[], float] = time.monotonic
_module_sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep


def reset_rate_limiter(
    *,
    clock: Callable[[], float] | None = None,
    sleep: Callable[[float], Awaitable[Any]] | None = None,
) -> None:
    """Zera o estado do limitador de taxa para testes ou reconfiguração."""
    global _last_call_start, _module_clock, _module_sleep, RATE_LOCK
    _last_call_start = None
    RATE_LOCK = asyncio.Lock()
    _module_clock = clock if clock is not None else time.monotonic
    _module_sleep = sleep if sleep is not None else asyncio.sleep


@asynccontextmanager
async def rate_limited_call(
    clock: Callable[[], float] | None = None,
    sleep: Callable[[float], Awaitable[Any]] | None = None,
) -> AsyncIterator[None]:
    """Garante no máximo uma chamada ativa e pelo menos 1s entre os inícios de chamadas."""
    global _last_call_start
    clk = clock or _module_clock
    slp = sleep or _module_sleep
    async with RATE_LOCK:
        now = clk()
        if _last_call_start is not None:
            elapsed = now - _last_call_start
            if elapsed < RATE_INTERVAL:
                await slp(RATE_INTERVAL - elapsed)
        _last_call_start = clk()
        yield


def _user_agent() -> str:
    try:
        version = importlib.metadata.version("rslapp")
    except importlib.metadata.PackageNotFoundError:
        version = "0"
    return f"rslapp/{version}"


def _is_valid_api_key(key: str) -> bool:
    return bool(key) and key.isascii() and key.isprintable() and not any(c.isspace() for c in key)


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


def _clean_query_text(query: str) -> str:
    # Termos com hífen não casam na Semantic Scholar: troca hífen por espaço
    return " ".join(query.replace("-", " ").split())


# FR-03, D-004: Extrai dados dos autores com nome e id na Semantic Scholar (sem ORCID nem afiliação)
def _parse_author(raw_author: Any) -> Author | None:
    if not isinstance(raw_author, dict):
        return None
    raw_name = raw_author.get("name")
    if not isinstance(raw_name, str) or not raw_name.strip():
        return None
    author_ids: dict[str, str] = {}
    raw_aid = raw_author.get("authorId")
    if isinstance(raw_aid, str) and raw_aid.strip():
        author_ids["semantic_scholar"] = raw_aid.strip()
    return Author(name=raw_name.strip(), ids=author_ids)


# FR-03, FR-14, D-004: Traduz registro da Semantic Scholar para Work; descarta trabalho sem título
def _parse_work(raw_work: Any) -> Work | None:
    if not isinstance(raw_work, dict):
        return None
    raw_title = raw_work.get("title")
    if not isinstance(raw_title, str) or not raw_title.strip():
        return None

    # DOI de externalIds (chave DOI) minúsculo
    raw_external = raw_work.get("externalIds")
    raw_doi: str | None = None
    if isinstance(raw_external, dict):
        val = raw_external.get("DOI") or raw_external.get("doi")
        if isinstance(val, str):
            raw_doi = val
    doi = _normalize_doi(raw_doi)

    # Periódico: journal.name ou, sem ele, venue
    venue: str | None = None
    raw_journal = raw_work.get("journal")
    if isinstance(raw_journal, dict):
        raw_jname = raw_journal.get("name")
        if isinstance(raw_jname, str) and raw_jname.strip():
            venue = raw_jname.strip()
    if venue is None:
        raw_venue = raw_work.get("venue")
        if isinstance(raw_venue, str) and raw_venue.strip():
            venue = raw_venue.strip()

    raw_abs = raw_work.get("abstract")
    abstract = raw_abs.strip() if isinstance(raw_abs, str) and raw_abs.strip() else None

    # Tipo: o primeiro de publicationTypes
    work_type: str | None = None
    raw_types = raw_work.get("publicationTypes")
    if isinstance(raw_types, list):
        for item in raw_types:
            if isinstance(item, str) and item.strip():
                work_type = item.strip()
                break

    authors: list[Author] = []
    raw_authors = raw_work.get("authors")
    if isinstance(raw_authors, list):
        for raw_author in raw_authors:
            parsed_author = _parse_author(raw_author)
            if parsed_author is not None:
                authors.append(parsed_author)

    raw_year = raw_work.get("year")
    year = raw_year if isinstance(raw_year, int) and not isinstance(raw_year, bool) else None

    raw_ref_count = raw_work.get("referenceCount")
    references_count = (
        raw_ref_count
        if isinstance(raw_ref_count, int) and not isinstance(raw_ref_count, bool)
        else None
    )

    citations: dict[str, int] = {}
    raw_cite_count = raw_work.get("citationCount")
    if isinstance(raw_cite_count, int) and not isinstance(raw_cite_count, bool):
        citations["semantic_scholar"] = raw_cite_count

    source_ids: dict[str, str] = {}
    raw_paper_id = raw_work.get("paperId")
    if isinstance(raw_paper_id, str) and raw_paper_id.strip():
        source_ids["semantic_scholar"] = raw_paper_id.strip()

    return Work(
        title=raw_title.strip(),
        doi=doi,
        year=year,
        type=work_type,
        venue=venue,
        abstract=abstract,
        keywords=[],
        authors=authors,
        references=[],
        references_count=references_count,
        citations=citations,
        source_ids=source_ids,
    )


def _extract_error_message(response: httpx.Response, api_key: str = "") -> str:
    msg = ""
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        val = payload.get("error") or payload.get("message")
        if isinstance(val, str):
            msg = val.strip()
    if not msg:
        msg = f"HTTP {response.status_code}"
    if api_key and api_key in msg:
        msg = msg.replace(api_key, "[REDACTED]")
    return msg


def _format_query_text(query: str, limit: int, offset: int) -> str:
    return f"query={query} · limit={limit} · offset={offset}"


def _format_number(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _retry_failure(status: str, prefix: str) -> tuple[str, str]:
    return status, f"{prefix} depois de {len(RETRY_DELAYS)} tentativas"


# FR-01, FR-03, FR-08, FR-14, NFR-03, NFR-04, D-004: Conector Semantic Scholar
class SemanticScholarSource(Source):
    """Conector de busca acadêmica na API da Semantic Scholar."""

    name: str = "semantic_scholar"
    needs_key: bool = False

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[Any]] | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._client = client
        self._sleep = sleep
        self._clock = clock

    # NFR-03: Representação textual sem chave de API
    def __repr__(self) -> str:
        return f"SemanticScholarSource(name={self.name!r}, needs_key={self.needs_key!r})"

    # NFR-03: Parâmetros que identificam a consulta no cache, sem incluir a chave
    def cache_query(self, query: str, max_results: int = 100) -> dict[str, Any]:
        effective_max = min(max(max_results, 1), MAX_RESULTS_LIMIT)
        limit = min(effective_max, MAX_PER_PAGE)
        clean_query = _clean_query_text(query)
        return {
            "query": clean_query,
            "max_results": max_results,
            "limit": limit,
            "fields": SELECT_FIELDS,
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
        api_key: str = "",
    ) -> tuple[dict[str, Any] | None, str | None, str | None]:
        max_retries = len(RETRY_DELAYS)
        err_status, err_reason = "failed", "falha inesperada ao consultar a Semantic Scholar"
        sleep_fn = self._sleep or _module_sleep
        clock_fn = self._clock or _module_clock

        for attempt in range(max_retries + 1):
            try:
                async with rate_limited_call(clock=clock_fn, sleep=sleep_fn):
                    response = await client.get(
                        SEMANTIC_SCHOLAR_SEARCH_URL,
                        params=params,
                        headers=headers,
                        timeout=DEFAULT_TIMEOUT,
                    )
            except httpx.TimeoutException:
                err_status, err_reason = _retry_failure("failed", "tempo limite esgotado")
            except httpx.HTTPError:
                err_status, err_reason = _retry_failure("failed", "erro de rede")
            except Exception:  # noqa: BLE001
                return None, "failed", "falha inesperada ao consultar a Semantic Scholar"
            else:
                status_code = response.status_code
                if status_code == 200:
                    try:
                        data = response.json()
                    except ValueError:
                        return None, "failed", "resposta JSON inválida da Semantic Scholar"
                    if not isinstance(data, dict):
                        return None, "failed", "resposta JSON inválida da Semantic Scholar"
                    return data, None, None

                # 429 e 5xx entram na política de novas tentativas
                if status_code == 429:
                    err_status, err_reason = _retry_failure("rate_limited", "HTTP 429")
                elif 500 <= status_code < 600:
                    err_status, err_reason = _retry_failure("failed", f"HTTP {status_code}")
                else:
                    # 400 e outras 4xx falham na hora com o texto do error da API
                    error_msg = _extract_error_message(response, api_key=api_key)
                    return None, "failed", error_msg

            if attempt < max_retries:
                await sleep_fn(RETRY_DELAYS[attempt])

        return None, err_status, err_reason

    # FR-15, FR-08, NFR-03, NFR-04: Chamada de página para trabalhos relacionados com tratamento específico de 404
    async def _request_related_page(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
        api_key: str = "",
    ) -> tuple[dict[str, Any] | None, str | None, str | None, bool]:
        max_retries = len(RETRY_DELAYS)
        err_status, err_reason = "failed", "falha inesperada ao consultar a Semantic Scholar"
        sleep_fn = self._sleep or _module_sleep
        clock_fn = self._clock or _module_clock

        for attempt in range(max_retries + 1):
            try:
                async with rate_limited_call(clock=clock_fn, sleep=sleep_fn):
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
                return None, "failed", "falha inesperada ao consultar a Semantic Scholar", False
            else:
                status_code = response.status_code
                if status_code == 200:
                    try:
                        data = response.json()
                    except ValueError:
                        return None, "failed", "resposta JSON inválida da Semantic Scholar", False
                    if not isinstance(data, dict):
                        return None, "failed", "resposta JSON inválida da Semantic Scholar", False
                    return data, None, None, False

                if status_code == 404:
                    return None, "failed", "HTTP 404", True

                # 429 e 5xx entram na política de novas tentativas
                if status_code == 429:
                    err_status, err_reason = _retry_failure("rate_limited", "HTTP 429")
                elif 500 <= status_code < 600:
                    err_status, err_reason = _retry_failure("failed", f"HTTP {status_code}")
                else:
                    # 400 e outras 4xx falham na hora com o texto do error da API
                    error_msg = _extract_error_message(response, api_key=api_key)
                    return None, "failed", error_msg, False

            if attempt < max_retries:
                await sleep_fn(RETRY_DELAYS[attempt])

        return None, err_status, err_reason, False

    # FR-01, FR-08, NFR-03, NFR-04: Busca paginada por offset com chave opcional no cabeçalho x-api-key
    async def search(self, query: str, max_results: int = 100) -> SourceResult:
        clean_query = _clean_query_text(query)
        effective_max = min(max(max_results, 1), MAX_RESULTS_LIMIT)
        limit = min(effective_max, MAX_PER_PAGE)

        # NFR-03: Lê a chave diretamente do ambiente a cada chamada, sem guardá-la em atributo
        raw_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        api_key = raw_key.strip(" \t\r\n") if raw_key else ""
        if api_key and not _is_valid_api_key(api_key):
            return SourceResult(
                name=self.name,
                status="failed",
                reason="SEMANTIC_SCHOLAR_API_KEY tem caracteres inválidos",
                query=_format_query_text(clean_query, limit, 0),
                found=None,
                fetched=0,
                works=[],
            )

        headers = {"User-Agent": _user_agent()}
        if api_key:
            headers["x-api-key"] = api_key

        works: list[Work] = []
        found: int | None = None
        offset = 0

        try:
            async with self._get_client() as client:
                while True:
                    params = {
                        "query": clean_query,
                        "offset": str(offset),
                        "limit": str(limit),
                        "fields": SELECT_FIELDS,
                    }
                    data, err_status, err_reason = await self._request_page(
                        client, params, headers, api_key=api_key
                    )
                    if err_status is not None:
                        return SourceResult(
                            name=self.name,
                            status=err_status,
                            reason=err_reason,
                            query=_format_query_text(clean_query, limit, offset),
                            found=found,
                            fetched=len(works),
                            works=works,
                        )

                    assert data is not None
                    if offset == 0:
                        raw_total = data.get("total")
                        if isinstance(raw_total, int) and not isinstance(raw_total, bool):
                            found = raw_total
                        elif isinstance(raw_total, str) and raw_total.strip().isdigit():
                            found = int(raw_total.strip())

                    raw_data = data.get("data")
                    if not isinstance(raw_data, list) or not raw_data:
                        break

                    for raw_item in raw_data:
                        parsed = _parse_work(raw_item)
                        if parsed is not None:
                            works.append(parsed)
                            if len(works) >= effective_max:
                                break

                    # Para quando atinge max_results, quando next some ou nos 1.000 resultados
                    if len(works) >= effective_max:
                        break

                    next_offset = data.get("next")
                    if (
                        next_offset is None
                        or not isinstance(next_offset, int)
                        or isinstance(next_offset, bool)
                    ):
                        break
                    if next_offset >= MAX_RESULTS_LIMIT or next_offset <= offset:
                        break

                    offset = next_offset
        except Exception:  # noqa: BLE001
            return SourceResult(
                name=self.name,
                status="failed",
                reason="falha inesperada ao consultar a Semantic Scholar",
                query=_format_query_text(clean_query, limit, offset),
                found=found,
                fetched=len(works),
                works=works,
            )

        return SourceResult(
            name=self.name,
            status="ok",
            reason=None,
            query=_format_query_text(clean_query, limit, offset),
            found=found,
            fetched=len(works),
            works=works,
        )

    # FR-15, FR-08, FR-14, D-005, D-010: Consulta referências ou citações na Semantic Scholar
    async def related(
        self,
        doi: str | None,
        direction: str,
        max_results: int = 1000,
    ) -> SourceResult:
        if not doi or not isinstance(doi, str) or not doi.strip():
            return SourceResult(
                name=self.name,
                status="not_supported",
                reason="artigo de origem sem DOI",
                query="",
                found=None,
                fetched=0,
                works=[],
            )

        clean_doi = _normalize_doi(doi) or doi.strip()
        quoted_doi = urllib.parse.quote(clean_doi, safe="")
        query_text = f"paper=DOI:{clean_doi}/{direction}"

        raw_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        api_key = raw_key.strip(" \t\r\n") if raw_key else ""
        if api_key and not _is_valid_api_key(api_key):
            return SourceResult(
                name=self.name,
                status="failed",
                reason="SEMANTIC_SCHOLAR_API_KEY tem caracteres inválidos",
                query=query_text,
                found=None,
                fetched=0,
                works=[],
            )

        headers = {"User-Agent": _user_agent()}
        if api_key:
            headers["x-api-key"] = api_key

        if direction not in ("references", "citations"):
            return SourceResult(
                name=self.name,
                status="failed",
                reason=f"direção inválida: {direction}",
                query=query_text,
                found=None,
                fetched=0,
                works=[],
            )

        effective_max = min(max(max_results, 1), 10_000)
        paper_url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{quoted_doi}/{direction}"

        works: list[Work] = []
        found: int | None = None
        offset = 0
        batch_limit = min(effective_max, 1000)
        stopped_by_source_limit = False
        stopped_by_ceiling = False

        try:
            async with self._get_client() as client:
                while True:
                    if offset >= 10_000:
                        stopped_by_source_limit = True
                        break

                    current_limit = min(batch_limit, 10_000 - offset, effective_max - len(works))
                    if current_limit <= 0:
                        break

                    params = {
                        "offset": str(offset),
                        "limit": str(current_limit),
                        "fields": SELECT_FIELDS,
                    }

                    data, err_status, err_reason, is_not_found = await self._request_related_page(
                        client, paper_url, params, headers, api_key=api_key
                    )
                    if err_status is not None:
                        return SourceResult(
                            name=self.name,
                            status=err_status,
                            reason=err_reason,
                            query=f"{query_text} · limit={current_limit} · offset={offset}",
                            found=found,
                            fetched=len(works),
                            works=works,
                            not_found=is_not_found,
                        )

                    assert data is not None
                    if offset == 0:
                        raw_total = data.get("total")
                        if isinstance(raw_total, int) and not isinstance(raw_total, bool):
                            found = raw_total
                        elif isinstance(raw_total, str) and raw_total.strip().isdigit():
                            found = int(raw_total.strip())

                    raw_data = data.get("data")
                    if not isinstance(raw_data, list) or not raw_data:
                        break

                    for raw_item in raw_data:
                        if isinstance(raw_item, dict):
                            paper_info = (
                                raw_item.get("citedPaper")
                                if direction == "references"
                                else raw_item.get("citingPaper")
                            )
                            if paper_info is None:
                                paper_info = raw_item
                            parsed = _parse_work(paper_info)
                            if parsed is not None:
                                works.append(parsed)
                                if len(works) >= effective_max:
                                    break

                    if len(works) >= effective_max:
                        next_offset = data.get("next")
                        if (
                            isinstance(next_offset, int)
                            and not isinstance(next_offset, bool)
                            and next_offset > offset
                        ):
                            stopped_by_ceiling = True
                        break

                    next_offset = data.get("next")
                    if (
                        next_offset is None
                        or not isinstance(next_offset, int)
                        or isinstance(next_offset, bool)
                    ):
                        if len(raw_data) < current_limit:
                            break
                        next_offset = offset + len(raw_data)

                    if next_offset >= 10_000:
                        stopped_by_source_limit = True
                        break
                    if next_offset <= offset:
                        break

                    offset = next_offset

        except Exception:  # noqa: BLE001
            return SourceResult(
                name=self.name,
                status="failed",
                reason="falha inesperada ao consultar a Semantic Scholar",
                query=query_text,
                found=found,
                fetched=len(works),
                works=works,
            )

        # FR-15, D-010: Marca teto atingido mesmo sem total informado quando parou no teto com next presente
        reason: str | None = None
        if (
            (found is not None and found > len(works))
            or stopped_by_source_limit
            or stopped_by_ceiling
        ):
            if stopped_by_source_limit or len(works) >= 10_000:
                reason = "limite de 10.000 da fonte"
            elif (
                stopped_by_ceiling
                or (found is not None and found > max_results)
                or len(works) >= max_results
                or offset >= max_results
            ):
                reason = f"teto de {_format_number(max_results)} atingido"

        return SourceResult(
            name=self.name,
            status="ok",
            reason=reason,
            query=f"{query_text} · limit={batch_limit} · offset={offset}",
            found=found,
            fetched=len(works),
            works=works,
        )

    # FR-02, D-002, NFR-03, NFR-04: Consulta trabalho direto por DOI na Semantic Scholar
    async def find_by_doi(self, doi: str) -> SourceResult:
        """Consulta um artigo pelo DOI na Semantic Scholar."""
        clean_doi = _normalize_doi(doi) or doi.strip()
        quoted_doi = urllib.parse.quote(clean_doi, safe="")
        query_text = f"paper=DOI:{clean_doi}"

        def _fail(status: str, reason: str | None) -> SourceResult:
            return SourceResult(
                name=self.name,
                status=status,
                reason=reason,
                query=query_text,
                found=None,
                fetched=0,
                works=[],
            )

        raw_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        api_key = raw_key.strip(" \t\r\n") if raw_key else ""
        if api_key and not _is_valid_api_key(api_key):
            return _fail("failed", "SEMANTIC_SCHOLAR_API_KEY tem caracteres inválidos")

        headers = {"User-Agent": _user_agent()}
        if api_key:
            headers["x-api-key"] = api_key

        paper_url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{quoted_doi}"
        params = {"fields": SELECT_FIELDS}

        try:
            async with self._get_client() as client:
                max_retries = len(RETRY_DELAYS)
                err_status, err_reason = "failed", "falha inesperada ao consultar a Semantic Scholar"
                for attempt in range(max_retries + 1):
                    async with rate_limited_call(self._clock, self._sleep):
                        try:
                            response = await client.get(
                                paper_url,
                                params=params,
                                headers=headers,
                                timeout=DEFAULT_TIMEOUT,
                            )
                        except httpx.TimeoutException:
                            err_status, err_reason = _retry_failure("failed", "tempo limite esgotado")
                        except httpx.HTTPError:
                            err_status, err_reason = _retry_failure("failed", "erro de rede")
                        except Exception:  # noqa: BLE001
                            return _fail("failed", "falha inesperada ao consultar a Semantic Scholar")
                        else:
                            status_code = response.status_code
                            if status_code == 200:
                                try:
                                    data = response.json()
                                except ValueError:
                                    return _fail("failed", "resposta JSON inválida da Semantic Scholar")
                                if not isinstance(data, dict):
                                    return _fail("failed", "resposta JSON inválida da Semantic Scholar")
                                work = _parse_work(data)
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
                            msg = _extract_error_message(response, api_key=api_key)
                            if status_code == 429:
                                err_status, err_reason = _retry_failure("rate_limited", msg)
                            elif 500 <= status_code < 600:
                                err_status, err_reason = _retry_failure("failed", msg)
                            else:
                                return _fail("failed", msg)

                    if attempt < max_retries:
                        slp = self._sleep or _module_sleep
                        await slp(RETRY_DELAYS[attempt])

                return _fail(err_status, err_reason)
        except Exception:  # noqa: BLE001
            return _fail("failed", "falha inesperada ao consultar a Semantic Scholar")
