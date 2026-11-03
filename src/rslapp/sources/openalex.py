"""Conector da fonte acadêmica OpenAlex."""

from __future__ import annotations

import asyncio
import importlib.metadata
import os
import urllib.parse
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import httpx

from rslapp.core.models import Affiliation, Author, OriginWorkResult, SourceResult, Work
from rslapp.sources.base import Source

OPENALEX_WORKS_URL = "https://api.openalex.org/works"
# NFR-05, D-010: Seleção apenas dos campos de primeiro nível necessários, incluindo referências e citações
SELECT_FIELDS = (
    "id,doi,display_name,publication_year,type,primary_location,"
    "authorships,abstract_inverted_index,keywords,referenced_works,"
    "referenced_works_count,cited_by_count"
)
MAX_PER_PAGE = 100
MAX_RESULTS_LIMIT = 10_000
DEFAULT_TIMEOUT = 30.0
# NFR-04: Espera crescente de 1 s, 2 s e 4 s para até 3 novas tentativas em 429 e 5xx
RETRY_DELAYS: tuple[int, ...] = (1, 2, 4)


def _user_agent() -> str:
    try:
        version = importlib.metadata.version("rslapp")
    except importlib.metadata.PackageNotFoundError:
        version = "0"
    return f"rslapp/{version}"


def _is_valid_api_key(key: str) -> bool:
    return bool(key) and key.isascii() and key.isprintable() and not any(c.isspace() for c in key)


def _is_ascii_digits(s: str) -> bool:
    return bool(s) and all("0" <= c <= "9" for c in s)


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


def _short_openalex_id(raw: Any) -> str | None:
    return _strip_url_prefixes(raw, ("https://openalex.org/", "http://openalex.org/"))


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


# FR-03: Remonta o texto do resumo a partir do abstract_inverted_index do OpenAlex
def _reconstruct_abstract(inverted_index: Any) -> str | None:
    if not isinstance(inverted_index, dict) or not inverted_index:
        return None
    positions: list[tuple[int, str]] = []
    for word, indices in inverted_index.items():
        if not isinstance(word, str) or not isinstance(indices, list):
            continue
        for idx in indices:
            if isinstance(idx, int) and not isinstance(idx, bool) and idx >= 0:
                positions.append((idx, word))
    if not positions:
        return None
    positions.sort(key=lambda item: item[0])
    text = " ".join(word for _, word in positions).strip()
    return text if text else None


# FR-03, D-004: Extrai dados completos de cada autor na ordem, incluindo ORCID e afiliações com ROR
def _parse_author(raw_authorship: Any) -> Author | None:
    if not isinstance(raw_authorship, dict):
        return None
    raw_author = raw_authorship.get("author")
    if not isinstance(raw_author, dict):
        return None
    raw_name = raw_author.get("display_name")
    if not isinstance(raw_name, str) or not raw_name.strip():
        return None

    author_ids: dict[str, str] = {}
    oa_author_id = _short_openalex_id(raw_author.get("id"))
    if oa_author_id:
        author_ids["openalex"] = oa_author_id

    raw_pos = raw_authorship.get("author_position")
    position = raw_pos.strip() if isinstance(raw_pos, str) and raw_pos.strip() else None
    raw_corr = raw_authorship.get("is_corresponding")
    is_corresponding = raw_corr if isinstance(raw_corr, bool) else None

    affiliations: list[Affiliation] = []
    raw_institutions = raw_authorship.get("institutions")
    if isinstance(raw_institutions, list):
        for inst in raw_institutions:
            if not isinstance(inst, dict):
                continue
            raw_inst_name = inst.get("display_name")
            inst_name = (
                raw_inst_name.strip()
                if isinstance(raw_inst_name, str) and raw_inst_name.strip()
                else None
            )
            inst_ids: dict[str, str] = {}
            oa_inst_id = _short_openalex_id(inst.get("id"))
            if oa_inst_id:
                inst_ids["openalex"] = oa_inst_id
            ror = _normalize_ror(inst.get("ror"))
            if ror:
                inst_ids["ror"] = ror
            raw_cc = inst.get("country_code")
            country_code = raw_cc.strip() if isinstance(raw_cc, str) and raw_cc.strip() else None
            affiliations.append(
                Affiliation(name=inst_name, ids=inst_ids, country_code=country_code)
            )

    raw_affs: list[str] = []
    raw_aff_list = raw_authorship.get("raw_affiliation_strings")
    if isinstance(raw_aff_list, list):
        for item in raw_aff_list:
            if isinstance(item, str) and item.strip():
                raw_affs.append(item.strip())

    return Author(
        name=raw_name.strip(),
        orcid=_normalize_orcid(raw_author.get("orcid")),
        ids=author_ids,
        position=position,
        is_corresponding=is_corresponding,
        affiliations=affiliations,
        raw_affiliations=raw_affs,
    )


# FR-03, FR-14, D-004, D-010: Traduz registro do OpenAlex para Work; descarta trabalho sem título
def _parse_work(raw_work: Any) -> Work | None:
    if not isinstance(raw_work, dict):
        return None
    raw_title = raw_work.get("display_name")
    if not isinstance(raw_title, str) or not raw_title.strip():
        return None

    venue: str | None = None
    primary_loc = raw_work.get("primary_location")
    if isinstance(primary_loc, dict):
        source = primary_loc.get("source")
        if isinstance(source, dict):
            raw_venue = source.get("display_name")
            if isinstance(raw_venue, str) and raw_venue.strip():
                venue = raw_venue.strip()

    keywords: list[str] = []
    raw_keywords = raw_work.get("keywords")
    if isinstance(raw_keywords, list):
        for kw in raw_keywords:
            if isinstance(kw, dict):
                kw_name = kw.get("display_name")
                if isinstance(kw_name, str) and kw_name.strip():
                    keywords.append(kw_name.strip())

    authors: list[Author] = []
    raw_authorships = raw_work.get("authorships")
    if isinstance(raw_authorships, list):
        for authorship in raw_authorships:
            parsed_author = _parse_author(authorship)
            if parsed_author is not None:
                authors.append(parsed_author)

    # FR-14, D-010: Referências guardadas como ids curtos do OpenAlex (W...)
    references: list[str] = []
    raw_refs = raw_work.get("referenced_works")
    if isinstance(raw_refs, list):
        for ref in raw_refs:
            short_ref = _short_openalex_id(ref)
            if short_ref:
                references.append(short_ref)

    raw_ref_count = raw_work.get("referenced_works_count")
    references_count = (
        raw_ref_count
        if isinstance(raw_ref_count, int) and not isinstance(raw_ref_count, bool)
        else None
    )

    citations: dict[str, int] = {}
    raw_cited = raw_work.get("cited_by_count")
    if isinstance(raw_cited, int) and not isinstance(raw_cited, bool):
        citations["openalex"] = raw_cited

    source_ids: dict[str, str] = {}
    oa_work_id = _short_openalex_id(raw_work.get("id"))
    if oa_work_id:
        source_ids["openalex"] = oa_work_id

    raw_year = raw_work.get("publication_year")
    year = raw_year if isinstance(raw_year, int) and not isinstance(raw_year, bool) else None
    raw_type = raw_work.get("type")
    work_type = raw_type.strip() if isinstance(raw_type, str) and raw_type.strip() else None

    return Work(
        title=raw_title.strip(),
        doi=_normalize_doi(raw_work.get("doi")),
        year=year,
        type=work_type,
        venue=venue,
        abstract=_reconstruct_abstract(raw_work.get("abstract_inverted_index")),
        keywords=keywords,
        authors=authors,
        references=references,
        references_count=references_count,
        citations=citations,
        source_ids=source_ids,
    )


def _extract_error_tag(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return ""
    if isinstance(payload, dict):
        for key in ("error", "code", "message"):
            val = payload.get(key)
            if isinstance(val, str):
                if "not_enough_credits" in val:
                    return "not_enough_credits"
                if "key_not_activated" in val:
                    return "key_not_activated"
    return ""


def _format_query_text(query: str, per_page: int, last_page: int) -> str:
    return f"search={query} · per_page={per_page} · páginas 1-{last_page}"


def _format_number(n: int) -> str:
    return f"{n:,}".replace(",", ".")


# FR-14, NFR-01, NFR-03: Resultado da busca em lote de DOIs por ids do OpenAlex
@dataclass
class DoiLookup:
    """Resultado da consulta de DOIs por ids do OpenAlex."""

    status: str
    reason: str | None = None
    mapping: dict[str, str | None] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "mapping": dict(self.mapping),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DoiLookup:
        return cls(
            status=str(data["status"]),
            reason=data.get("reason"),
            mapping=dict(data.get("mapping") or {}),
        )


def _retry_failure(status: str, prefix: str) -> tuple[str, str]:
    return status, f"{prefix} depois de {len(RETRY_DELAYS)} tentativas"


# FR-01, FR-03, FR-14, NFR-01, NFR-03, NFR-04, NFR-05, D-004, D-010: Conector OpenAlex
class OpenAlexSource(Source):
    """Conector de busca acadêmica na API do OpenAlex."""

    name: str = "openalex"
    needs_key: bool = True

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    ) -> None:
        self._client = client
        self._sleep = sleep

    # NFR-03: Representação textual sem chave de API
    def __repr__(self) -> str:
        return f"OpenAlexSource(name={self.name!r}, needs_key={self.needs_key!r})"

    # NFR-03: Parâmetros que identificam a consulta no cache, sem incluir a chave
    def cache_query(self, query: str, max_results: int = 100) -> dict[str, Any]:
        effective_max = min(max(max_results, 1), MAX_RESULTS_LIMIT)
        per_page = min(effective_max, MAX_PER_PAGE)
        return {
            "search": query.strip(),
            "max_results": max_results,
            "per_page": per_page,
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
        url: str = OPENALEX_WORKS_URL,
    ) -> tuple[dict[str, Any] | None, str | None, str | None]:
        max_retries = len(RETRY_DELAYS)
        err_status, err_reason = "failed", "falha inesperada ao consultar o OpenAlex"
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
                return None, "failed", "falha inesperada ao consultar o OpenAlex"
            else:
                status_code = response.status_code
                if status_code == 200:
                    try:
                        data = response.json()
                    except ValueError:
                        return None, "failed", "resposta JSON inválida do OpenAlex"
                    if not isinstance(data, dict):
                        return None, "failed", "resposta JSON inválida do OpenAlex"
                    return data, None, None

                error_tag = _extract_error_tag(response)
                # NFR-01, NFR-05: Cota diária esgotada não faz novas tentativas
                if status_code == 429 and error_tag == "not_enough_credits":
                    return None, "rate_limited", "créditos diários do OpenAlex esgotados"
                if status_code == 403 and error_tag == "key_not_activated":
                    return (
                        None,
                        "failed",
                        "a chave do OpenAlex ainda não foi ativada pelo link do e-mail",
                    )
                if status_code == 429:
                    err_status, err_reason = _retry_failure("rate_limited", "HTTP 429")
                elif 500 <= status_code < 600:
                    err_status, err_reason = _retry_failure("failed", f"HTTP {status_code}")
                else:
                    return None, "failed", f"HTTP {status_code}"

            if attempt < max_retries:
                await self._sleep(RETRY_DELAYS[attempt])

        return None, err_status, err_reason

    # FR-01, NFR-03, NFR-04, NFR-05: Busca paginada com chave via cabeçalho Authorization: Bearer
    async def search(self, query: str, max_results: int = 100) -> SourceResult:
        clean_query = query.strip()
        effective_max = min(max(max_results, 1), MAX_RESULTS_LIMIT)
        per_page = min(effective_max, MAX_PER_PAGE)

        # NFR-03: Lê a chave diretamente do ambiente a cada chamada, sem guardá-la em atributo
        raw_key = os.environ.get("OPENALEX_API_KEY")
        api_key = raw_key.strip(" \t\r\n") if raw_key else ""
        if not api_key:
            return SourceResult(
                name=self.name,
                status="missing_key",
                reason="variável OPENALEX_API_KEY não configurada",
                query=_format_query_text(clean_query, per_page, 1),
                found=None,
                fetched=0,
                works=[],
            )
        if not _is_valid_api_key(api_key):
            return SourceResult(
                name=self.name,
                status="failed",
                reason="OPENALEX_API_KEY tem caracteres inválidos",
                query=_format_query_text(clean_query, per_page, 1),
                found=None,
                fetched=0,
                works=[],
            )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": _user_agent(),
        }

        works: list[Work] = []
        found: int | None = None
        page = 1

        try:
            async with self._get_client() as client:
                while True:
                    params = {
                        "search": clean_query,
                        "per_page": str(per_page),
                        "page": str(page),
                        "select": SELECT_FIELDS,
                    }
                    data, err_status, err_reason = await self._request_page(
                        client, params, headers
                    )
                    if err_status is not None:
                        return SourceResult(
                            name=self.name,
                            status=err_status,
                            reason=err_reason,
                            query=_format_query_text(clean_query, per_page, page),
                            found=found,
                            fetched=len(works),
                            works=works,
                        )

                    assert data is not None
                    if page == 1:
                        meta = data.get("meta")
                        if isinstance(meta, dict):
                            raw_count = meta.get("count")
                            if isinstance(raw_count, int) and not isinstance(raw_count, bool):
                                found = raw_count

                    raw_results = data.get("results")
                    if not isinstance(raw_results, list) or not raw_results:
                        break

                    for raw_item in raw_results:
                        parsed = _parse_work(raw_item)
                        if parsed is not None:
                            works.append(parsed)
                            if len(works) >= effective_max:
                                break

                    # Para quando atinge max_results, o limite de 10.000 ou o fim dos resultados
                    if len(works) >= effective_max:
                        break
                    if len(raw_results) < per_page:
                        break
                    if found is not None and page * per_page >= found:
                        break
                    if (page + 1) * per_page > MAX_RESULTS_LIMIT:
                        break

                    page += 1
        except Exception:  # noqa: BLE001
            return SourceResult(
                name=self.name,
                status="failed",
                reason="falha inesperada ao consultar o OpenAlex",
                query=_format_query_text(clean_query, per_page, page),
                found=found,
                fetched=len(works),
                works=works,
            )

        return SourceResult(
            name=self.name,
            status="ok",
            reason=None,
            query=_format_query_text(clean_query, per_page, page),
            found=found,
            fetched=len(works),
            works=works,
        )

    # FR-14, NFR-01, NFR-03, D-010: Consulta em lote de DOIs para até 100 ids do OpenAlex
    async def lookup_dois(self, ids: list[str]) -> DoiLookup:
        if not ids:
            return DoiLookup(status="ok", reason=None, mapping={})

        clean_ids: list[str] = []
        for raw_id in ids[:MAX_PER_PAGE]:
            sid = _short_openalex_id(raw_id) or (raw_id.strip() if isinstance(raw_id, str) else "")
            if sid and sid not in clean_ids:
                clean_ids.append(sid)

        if not clean_ids:
            return DoiLookup(status="ok", reason=None, mapping={})

        raw_key = os.environ.get("OPENALEX_API_KEY")
        api_key = raw_key.strip(" \t\r\n") if raw_key else ""
        if not api_key:
            return DoiLookup(
                status="missing_key",
                reason="variável OPENALEX_API_KEY não configurada",
                mapping={},
            )
        if not _is_valid_api_key(api_key):
            return DoiLookup(
                status="failed",
                reason="OPENALEX_API_KEY tem caracteres inválidos",
                mapping={},
            )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": _user_agent(),
        }

        filter_val = "|".join(clean_ids)
        params = {
            "filter": f"openalex:{filter_val}",
            "select": "id,doi",
            "per_page": "100",
        }

        try:
            async with self._get_client() as client:
                data, err_status, err_reason = await self._request_page(
                    client, params, headers
                )
                if err_status is not None:
                    return DoiLookup(
                        status=err_status,
                        reason=err_reason,
                        mapping={},
                    )

                assert data is not None
                raw_results = data.get("results")
                if not isinstance(raw_results, list):
                    return DoiLookup(
                        status="failed",
                        reason="resposta JSON inválida do OpenAlex",
                        mapping={},
                    )

                found_map: dict[str, str | None] = {}
                for item in raw_results:
                    if isinstance(item, dict):
                        sid = _short_openalex_id(item.get("id"))
                        if sid:
                            found_map[sid] = _normalize_doi(item.get("doi"))

                mapping: dict[str, str | None] = {}
                for raw_id in ids[:MAX_PER_PAGE]:
                    sid = _short_openalex_id(raw_id) or (raw_id.strip() if isinstance(raw_id, str) else "")
                    if sid:
                        doi = found_map.get(sid)
                        mapping[sid] = doi
                        if raw_id != sid:
                            mapping[raw_id] = doi

                return DoiLookup(status="ok", reason=None, mapping=mapping)
        except Exception:  # noqa: BLE001
            return DoiLookup(
                status="failed",
                reason="falha inesperada ao consultar o OpenAlex",
                mapping={},
            )

    # FR-15, D-005, D-010: Consulta o artigo de origem avulso no OpenAlex para obter id, doi e referenced_works
    async def get_origin_work(
        self, doi_or_id: str
    ) -> OriginWorkResult:
        raw_key = os.environ.get("OPENALEX_API_KEY")
        api_key = raw_key.strip(" \t\r\n") if raw_key else ""
        if not api_key:
            return OriginWorkResult(
                status="missing_key",
                reason="variável OPENALEX_API_KEY não configurada",
            )
        if not _is_valid_api_key(api_key):
            return OriginWorkResult(
                status="failed",
                reason="OPENALEX_API_KEY tem caracteres inválidos",
            )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": _user_agent(),
        }

        short_id = _short_openalex_id(doi_or_id)
        if short_id and short_id.upper().startswith("W") and _is_ascii_digits(short_id[1:]):
            target = short_id.upper()
        else:
            norm_doi = _normalize_doi(doi_or_id) or doi_or_id.strip()
            quoted_doi = urllib.parse.quote(norm_doi, safe="")
            target = f"doi:{quoted_doi}"

        url = f"{OPENALEX_WORKS_URL}/{target}"
        params = {"select": "id,doi,referenced_works,cited_by_count"}

        try:
            async with self._get_client() as client:
                max_retries = len(RETRY_DELAYS)
                err_status, err_reason = "failed", "falha inesperada ao consultar o OpenAlex"
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
                        return OriginWorkResult(
                            status="failed",
                            reason="falha inesperada ao consultar o OpenAlex",
                        )
                    else:
                        status_code = response.status_code
                        if status_code == 200:
                            try:
                                data = response.json()
                            except ValueError:
                                return OriginWorkResult(
                                    status="failed",
                                    reason="resposta JSON inválida do OpenAlex",
                                )
                            if not isinstance(data, dict):
                                return OriginWorkResult(
                                    status="failed",
                                    reason="resposta JSON inválida do OpenAlex",
                                )
                            return OriginWorkResult(data=data, status=None, reason=None, not_found=False)

                        error_tag = _extract_error_tag(response)
                        if status_code == 429 and error_tag == "not_enough_credits":
                            return OriginWorkResult(
                                status="rate_limited",
                                reason="créditos diários do OpenAlex esgotados",
                            )
                        if status_code == 403 and error_tag == "key_not_activated":
                            return OriginWorkResult(
                                status="failed",
                                reason="a chave do OpenAlex ainda não foi ativada pelo link do e-mail",
                            )
                        if status_code == 404:
                            return OriginWorkResult(
                                status="failed",
                                reason="HTTP 404",
                                not_found=True,
                            )
                        if status_code == 429:
                            err_status, err_reason = _retry_failure("rate_limited", "HTTP 429")
                        elif 500 <= status_code < 600:
                            err_status, err_reason = _retry_failure("failed", f"HTTP {status_code}")
                        else:
                            return OriginWorkResult(status="failed", reason=f"HTTP {status_code}")

                    if attempt < max_retries:
                        await self._sleep(RETRY_DELAYS[attempt])

                return OriginWorkResult(status=err_status, reason=err_reason, not_found=False)
        except Exception:  # noqa: BLE001
            return OriginWorkResult(
                status="failed",
                reason="falha inesperada ao consultar o OpenAlex",
            )

    # FR-15, FR-08, FR-14, D-005, D-010: Consulta referências ou citações no OpenAlex
    async def related(
        self,
        doi_or_id: str,
        direction: str,
        max_results: int = 1000,
        origin_data: dict[str, Any] | None = None,
    ) -> SourceResult:
        clean_id_or_doi = doi_or_id.strip() if isinstance(doi_or_id, str) else ""
        query_text = f"related={clean_id_or_doi} · direction={direction}"

        raw_key = os.environ.get("OPENALEX_API_KEY")
        api_key = raw_key.strip(" \t\r\n") if raw_key else ""
        if not api_key:
            return SourceResult(
                name=self.name,
                status="missing_key",
                reason="variável OPENALEX_API_KEY não configurada",
                query=query_text,
                found=None,
                fetched=0,
                works=[],
            )
        if not _is_valid_api_key(api_key):
            return SourceResult(
                name=self.name,
                status="failed",
                reason="OPENALEX_API_KEY tem caracteres inválidos",
                query=query_text,
                found=None,
                fetched=0,
                works=[],
            )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": _user_agent(),
        }

        effective_max = min(max(max_results, 1), MAX_RESULTS_LIMIT)

        try:
            async with self._get_client() as client:
                if origin_data is None:
                    origin_res = await self.get_origin_work(clean_id_or_doi)
                    if origin_res.status is not None:
                        return SourceResult(
                            name=self.name,
                            status=origin_res.status,
                            reason=origin_res.reason,
                            query=query_text,
                            found=None,
                            fetched=0,
                            works=[],
                            not_found=origin_res.not_found,
                        )
                    origin_data = origin_res.data

                assert origin_data is not None
                origin_id = _short_openalex_id(origin_data.get("id"))
                works: list[Work] = []
                found: int | None = None
                reason: str | None = None

                if direction == "citations":
                    if not origin_id:
                        return SourceResult(
                            name=self.name,
                            status="failed",
                            reason="artigo de origem sem id no OpenAlex",
                            query=query_text,
                            found=None,
                            fetched=0,
                            works=[],
                        )
                    raw_count = origin_data.get("cited_by_count")
                    if isinstance(raw_count, int) and not isinstance(raw_count, bool):
                        found = raw_count

                    per_page = min(effective_max, MAX_PER_PAGE)
                    page = 1
                    stopped_by_cap = False
                    stopped_by_source_limit = False

                    while True:
                        params = {
                            "filter": f"cites:{origin_id}",
                            "select": SELECT_FIELDS,
                            "per_page": str(per_page),
                            "page": str(page),
                        }
                        page_data, err_status, err_reason = await self._request_page(
                            client, params, headers
                        )
                        if err_status is not None:
                            return SourceResult(
                                name=self.name,
                                status=err_status,
                                reason=err_reason,
                                query=f"cites={origin_id} · per_page={per_page} · páginas 1-{page}",
                                found=found,
                                fetched=len(works),
                                works=works,
                            )

                        assert page_data is not None
                        if page == 1 and found is None:
                            meta = page_data.get("meta")
                            if isinstance(meta, dict):
                                c = meta.get("count")
                                if isinstance(c, int) and not isinstance(c, bool):
                                    found = c

                        raw_results = page_data.get("results")
                        if not isinstance(raw_results, list) or not raw_results:
                            break

                        for raw_item in raw_results:
                            parsed = _parse_work(raw_item)
                            if parsed is not None:
                                works.append(parsed)
                                if len(works) >= effective_max:
                                    stopped_by_cap = True
                                    break

                        if stopped_by_cap or len(works) >= effective_max:
                            stopped_by_cap = True
                            break
                        if len(raw_results) < per_page:
                            break
                        if found is not None and page * per_page >= found:
                            break
                        if (page + 1) * per_page > MAX_RESULTS_LIMIT:
                            stopped_by_source_limit = True
                            break
                        if page * per_page >= effective_max:
                            stopped_by_cap = True
                            break
                        page += 1

                    if (found is not None and found > len(works)) or stopped_by_cap or stopped_by_source_limit:
                        if stopped_by_source_limit or (effective_max >= MAX_RESULTS_LIMIT and (found is not None and found > MAX_RESULTS_LIMIT)):
                            reason = "limite de 10.000 da fonte"
                        elif stopped_by_cap or (found is not None and found > max_results) or len(works) >= max_results:
                            reason = f"teto de {_format_number(max_results)} atingido"

                    return SourceResult(
                        name=self.name,
                        status="ok",
                        reason=reason,
                        query=f"cites={origin_id} · per_page={per_page} · páginas 1-{page}",
                        found=found,
                        fetched=len(works),
                        works=works,
                    )

                elif direction == "references":
                    raw_refs = origin_data.get("referenced_works") or []
                    clean_ref_ids: list[str] = []
                    for ref in raw_refs:
                        sid = _short_openalex_id(ref)
                        if sid and sid.upper().startswith("W") and _is_ascii_digits(sid[1:]):
                            clean_ref_ids.append(sid.upper())

                    found = len(clean_ref_ids)
                    target_ids = clean_ref_ids[:effective_max]
                    cut_by_cap = len(clean_ref_ids) > effective_max
                    stopped_by_cap = False

                    batch_size = 100
                    last_batch_num = 0
                    for i in range(0, len(target_ids), batch_size):
                        batch = target_ids[i : i + batch_size]
                        last_batch_num = i // batch_size + 1
                        params = {
                            "filter": f"openalex:{'|'.join(batch)}",
                            "select": SELECT_FIELDS,
                            "per_page": "100",
                        }
                        batch_data, err_status, err_reason = await self._request_page(
                            client, params, headers
                        )
                        if err_status is not None:
                            return SourceResult(
                                name=self.name,
                                status=err_status,
                                reason=err_reason,
                                query=f"references={origin_id or clean_id_or_doi} · lotes 1-{last_batch_num}",
                                found=found,
                                fetched=len(works),
                                works=works,
                            )

                        assert batch_data is not None
                        raw_results = batch_data.get("results")
                        if isinstance(raw_results, list):
                            for raw_item in raw_results:
                                parsed = _parse_work(raw_item)
                                if parsed is not None:
                                    works.append(parsed)
                                    if len(works) >= effective_max:
                                        stopped_by_cap = True
                                        break
                        if len(works) >= effective_max:
                            stopped_by_cap = True
                            break

                    if (found > len(works)) or cut_by_cap or stopped_by_cap:
                        if effective_max >= MAX_RESULTS_LIMIT and found > MAX_RESULTS_LIMIT:
                            reason = "limite de 10.000 da fonte"
                        elif cut_by_cap or stopped_by_cap or found > max_results or len(works) >= max_results:
                            reason = f"teto de {_format_number(max_results)} atingido"

                    return SourceResult(
                        name=self.name,
                        status="ok",
                        reason=reason,
                        query=f"references={origin_id or clean_id_or_doi} · {found} referências",
                        found=found,
                        fetched=len(works),
                        works=works,
                    )
                else:
                    return SourceResult(
                        name=self.name,
                        status="failed",
                        reason=f"direção inválida: {direction}",
                        query=query_text,
                        found=None,
                        fetched=0,
                        works=[],
                    )
        except Exception:  # noqa: BLE001
            return SourceResult(
                name=self.name,
                status="failed",
                reason="falha inesperada ao consultar o OpenAlex",
                query=query_text,
                found=None,
                fetched=0,
                works=[],
            )
