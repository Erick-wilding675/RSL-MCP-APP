"""Conector da fonte acadêmica PubMed via E-utilities do NCBI."""

from __future__ import annotations

import asyncio
import importlib.metadata
import os
import re
import time
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

import httpx

from rslapp.core.models import Affiliation, Author, SourceResult, Work
from rslapp.sources.base import Source

# D-020: Endereços oficiais das E-utilities do NCBI para busca e recuperação no PubMed
PUBMED_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

BATCH_SIZE = 200
MAX_ESEARCH_RESULTS = 10_000
DEFAULT_TIMEOUT = 30.0
# NFR-04: Espera crescente de 1 s, 2 s e 4 s para até 3 novas tentativas em 429, 5xx e erro de limite
RETRY_DELAYS: tuple[int, ...] = (1, 2, 4)

# NFR-04: Intervalo mínimo entre inícios: 0,34 s sem chave (<= 3 req/s) e 0,10 s com chave (<= 10 req/s)
RATE_INTERVAL_NO_KEY: float = 0.34
RATE_INTERVAL_WITH_KEY: float = 0.10

# NFR-04: Trava e relógio no nível do módulo para garantir 1 pedido por vez, nunca em paralelo
RATE_LOCK = asyncio.Lock()
_last_call_start: float | None = None
_module_clock: Callable[[], float] = time.monotonic
_module_sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep

_ORCID_RE = re.compile(r"^(\d{4}-\d{4}-\d{4}-[\dX]{4})$", re.IGNORECASE)


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
    *,
    has_key: bool = False,
    clock: Callable[[], float] | None = None,
    sleep: Callable[[float], Awaitable[Any]] | None = None,
) -> AsyncIterator[None]:
    """Garante no máximo um pedido ativo e intervalo mínimo entre inícios (0,34 s ou 0,10 s)."""
    global _last_call_start
    clk = clock or _module_clock
    slp = sleep or _module_sleep
    interval = RATE_INTERVAL_WITH_KEY if has_key else RATE_INTERVAL_NO_KEY
    async with RATE_LOCK:
        now = clk()
        if _last_call_start is not None:
            elapsed = now - _last_call_start
            if elapsed < interval:
                await slp(interval - elapsed)
        _last_call_start = clk()
        yield


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


# D-004: Normaliza ORCID para o formato canônico 0000-0000-0000-0000; inválido vira None
def _normalize_orcid(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    val = raw.strip()
    for prefix in ("https://orcid.org/", "http://orcid.org/", "orcid.org/"):
        if val.lower().startswith(prefix):
            val = val[len(prefix) :].strip()
    val = val.upper()
    if _ORCID_RE.match(val):
        return val
    return None


def _extract_year_from_text(raw: str | None) -> int | None:
    if not raw:
        return None
    match = re.search(r"\d{4}", raw)
    if match:
        try:
            return int(match.group(0))
        except ValueError:
            return None
    return None


# FR-03, D-020: Extrai o ano por prioridade: PubDate/Year, 4 dígitos de MedlineDate, ArticleDate/Year
def _extract_year(medline_citation: ET.Element | None) -> int | None:
    if medline_citation is None:
        return None
    for year_elem in medline_citation.findall(".//Journal//PubDate/Year"):
        y = _extract_year_from_text("".join(year_elem.itertext()))
        if y is not None:
            return y
    for medline_date_elem in medline_citation.findall(".//Journal//PubDate/MedlineDate"):
        y = _extract_year_from_text("".join(medline_date_elem.itertext()))
        if y is not None:
            return y
    for art_year_elem in medline_citation.findall(".//ArticleDate/Year"):
        y = _extract_year_from_text("".join(art_year_elem.itertext()))
        if y is not None:
            return y
    return None


# FR-03, D-020: Partes de AbstractText unidas por espaço; quando tem Label, prefixa "LABEL: texto"
def _extract_abstract(article_elem: ET.Element) -> str | None:
    abstract_elem = article_elem.find("Abstract")
    if abstract_elem is None:
        return None
    parts: list[str] = []
    for text_elem in abstract_elem.findall("AbstractText"):
        text = " ".join("".join(text_elem.itertext()).split())
        if not text:
            continue
        label = text_elem.attrib.get("Label") or text_elem.attrib.get("label")
        if label and label.strip():
            parts.append(f"{label.strip()}: {text}")
        else:
            parts.append(text)
    return " ".join(parts) if parts else None


# FR-03, D-020: Palavras-chave de KeywordList primeiro, depois MeSH DescriptorName, sem repetir
def _extract_keywords(medline_citation: ET.Element) -> list[str]:
    raw_keywords: list[str] = []
    for kw_elem in medline_citation.findall(".//KeywordList/Keyword"):
        kw_text = " ".join("".join(kw_elem.itertext()).split())
        if kw_text:
            raw_keywords.append(kw_text)
    for mesh_elem in medline_citation.findall(".//MeshHeadingList/MeshHeading/DescriptorName"):
        mesh_text = " ".join("".join(mesh_elem.itertext()).split())
        if mesh_text:
            raw_keywords.append(mesh_text)

    keywords: list[str] = []
    seen: set[str] = set()
    for kw in raw_keywords:
        lower = kw.lower()
        if lower not in seen:
            seen.add(lower)
            keywords.append(kw)
    return keywords


# FR-03, D-020: Primeiro PublicationType em minúsculas
def _extract_type(article_elem: ET.Element) -> str | None:
    pt_elem = article_elem.find(".//PublicationTypeList/PublicationType")
    if pt_elem is not None:
        pt_text = " ".join("".join(pt_elem.itertext()).split()).lower()
        if pt_text:
            return pt_text
    return None


# FR-03, D-004, D-020: Nome (ForeName LastName, LastName ou CollectiveName), ORCID e afiliações
def _parse_author(author_elem: ET.Element) -> Author | None:
    fore_elem = author_elem.find("ForeName")
    fore_name = " ".join("".join(fore_elem.itertext()).split()) if fore_elem is not None else ""
    last_elem = author_elem.find("LastName")
    last_name = " ".join("".join(last_elem.itertext()).split()) if last_elem is not None else ""
    col_elem = author_elem.find("CollectiveName")
    collective = " ".join("".join(col_elem.itertext()).split()) if col_elem is not None else ""

    if fore_name and last_name:
        name = f"{fore_name} {last_name}"
    elif last_name:
        name = last_name
    elif collective:
        name = collective
    elif fore_name:
        name = fore_name
    else:
        return None

    orcid: str | None = None
    for id_elem in author_elem.findall("Identifier"):
        source = (id_elem.attrib.get("Source") or id_elem.attrib.get("source") or "").upper()
        if source == "ORCID" or not source:
            raw_orcid = "".join(id_elem.itertext()).strip()
            cand_orcid = _normalize_orcid(raw_orcid)
            if cand_orcid:
                orcid = cand_orcid
                break

    raw_affiliations: list[str] = []
    affiliations: list[Affiliation] = []
    for aff_elem in author_elem.findall(".//AffiliationInfo/Affiliation"):
        aff_text = " ".join("".join(aff_elem.itertext()).split())
        if aff_text:
            raw_affiliations.append(aff_text)
            affiliations.append(Affiliation(name=aff_text))

    return Author(
        name=name,
        orcid=orcid,
        ids={},
        position=None,
        is_corresponding=None,
        affiliations=affiliations,
        raw_affiliations=raw_affiliations,
    )


# FR-03, D-020: DOI de ArticleId IdType="doi", senão de ELocationID EIdType="doi"
def _extract_doi(article_elem: ET.Element, pubmed_data: ET.Element | None) -> str | None:
    if pubmed_data is not None:
        for aid in pubmed_data.findall(".//ArticleIdList/ArticleId"):
            if aid.attrib.get("IdType", "").lower() == "doi":
                doi = _normalize_doi("".join(aid.itertext()))
                if doi:
                    return doi
    for eloc in article_elem.findall(".//ELocationID"):
        if eloc.attrib.get("EIdType", "").lower() == "doi":
            doi = _normalize_doi("".join(eloc.itertext()))
            if doi:
                return doi
    return None


# FR-14, D-020: DOIs minúsculos das referências; references_count é o total quando ReferenceList existe
def _extract_references(pubmed_data: ET.Element | None) -> tuple[list[str], int | None]:
    if pubmed_data is None:
        return [], None
    ref_list = pubmed_data.find("ReferenceList")
    if ref_list is None:
        return [], None

    references: list[str] = []
    ref_elements = ref_list.findall(".//Reference")
    references_count = len(ref_elements)
    for ref in ref_elements:
        for aid in ref.findall(".//ArticleId"):
            if aid.attrib.get("IdType", "").lower() == "doi":
                doi = _normalize_doi("".join(aid.itertext()))
                if doi:
                    references.append(doi)
                    break
    return references, references_count


# FR-03, FR-14, D-004, D-020: Traduz PubmedArticle XML para Work; descarta registro sem título
def _parse_pubmed_article(article_container: ET.Element) -> Work | None:
    medline_citation = article_container.find("MedlineCitation")
    if medline_citation is None:
        return None
    article_elem = medline_citation.find("Article")
    if article_elem is None:
        return None

    title_elem = article_elem.find("ArticleTitle")
    if title_elem is None:
        return None
    title = " ".join("".join(title_elem.itertext()).split())
    if not title:
        return None

    pubmed_data = article_container.find("PubmedData")

    doi = _extract_doi(article_elem, pubmed_data)
    year = _extract_year(medline_citation)

    venue_elem = article_elem.find("Journal/Title")
    venue = " ".join("".join(venue_elem.itertext()).split()) if venue_elem is not None else None
    if venue == "":
        venue = None

    abstract = _extract_abstract(article_elem)
    keywords = _extract_keywords(medline_citation)
    work_type = _extract_type(article_elem)

    authors: list[Author] = []
    author_list = article_elem.find("AuthorList")
    if author_list is not None:
        for a_elem in author_list.findall("Author"):
            parsed_a = _parse_author(a_elem)
            if parsed_a is not None:
                authors.append(parsed_a)

    references, references_count = _extract_references(pubmed_data)

    pmid_elem = medline_citation.find("PMID")
    pmid = "".join(pmid_elem.itertext()).strip() if pmid_elem is not None else None
    source_ids = {"pubmed": pmid} if pmid else {}

    return Work(
        title=title,
        doi=doi,
        year=year,
        type=work_type,
        venue=venue,
        abstract=abstract,
        keywords=keywords,
        authors=authors,
        references=references,
        references_count=references_count,
        citations={},
        source_ids=source_ids,
    )


def _retry_failure(status: str, prefix: str) -> tuple[str, str]:
    return status, f"{prefix} depois de {len(RETRY_DELAYS)} tentativas"


def _format_query_text(query: str, last_retstart: int = 0) -> str:
    if last_retstart > 0:
        return f"term={query} · retmax={BATCH_SIZE} · retstart 0-{last_retstart}"
    return f"term={query} · retmax={BATCH_SIZE}"


# FR-01, FR-03, FR-14, NFR-03, NFR-04, D-004, D-020: Conector de busca no PubMed via E-utilities
class PubmedSource(Source):
    """Conector de busca acadêmica na API E-utilities do PubMed/NCBI."""

    name: str = "pubmed"
    needs_key: bool = False

    def __init__(
        self,
        api_key: str | None = None,
        email: str | None = None,
        client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._api_key = api_key
        self._email = email
        self._client = client
        self._sleep = sleep
        self._clock = clock

    # NFR-03: repr nunca expõe valores de chaves de API nem email de contato
    def __repr__(self) -> str:
        return f"PubmedSource(name={self.name!r}, needs_key={self.needs_key!r})"

    # NFR-03: Parâmetros de identificação da consulta no cache sem chave e sem email
    def cache_query(self, query: str, max_results: int = 100) -> dict[str, Any]:
        return {
            "source": "pubmed",
            "query": query.strip(),
            "max_results": max_results,
        }

    def _resolve_api_key(self) -> str | None:
        if self._api_key is not None:
            key = self._api_key.strip()
            return key if key else None
        raw = os.environ.get("NCBI_API_KEY")
        if raw and raw.strip():
            return raw.strip()
        return None

    def _resolve_contact_email(self) -> str | None:
        if self._email is not None:
            email = self._email.strip()
            return email if email else None
        raw = os.environ.get("RSL_CONTACT_EMAIL")
        if raw and raw.strip():
            return raw.strip()
        return None

    @asynccontextmanager
    async def _get_client(self) -> AsyncIterator[httpx.AsyncClient]:
        if self._client is not None:
            yield self._client
        else:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                yield client

    # NFR-04: Consulta ESearch com até 3 novas tentativas (1, 2, 4 s) em 429, 5xx e limite
    async def _request_esearch(
        self,
        client: httpx.AsyncClient,
        params: dict[str, str],
        headers: dict[str, str],
        has_key: bool,
    ) -> tuple[dict[str, Any] | None, str | None, str | None]:
        max_retries = len(RETRY_DELAYS)
        err_status, err_reason = "failed", "falha inesperada ao consultar o PubMed"
        for attempt in range(max_retries + 1):
            async with rate_limited_call(
                has_key=has_key, clock=self._clock, sleep=self._sleep
            ):
                try:
                    response = await client.get(
                        PUBMED_ESEARCH_URL,
                        params=params,
                        headers=headers,
                        timeout=DEFAULT_TIMEOUT,
                    )
                except httpx.TimeoutException:
                    err_status, err_reason = _retry_failure("failed", "tempo limite esgotado")
                except httpx.HTTPError:
                    err_status, err_reason = _retry_failure("failed", "erro de rede")
                except Exception:  # noqa: BLE001
                    return None, "failed", "falha inesperada ao consultar o PubMed"
                else:
                    status_code = response.status_code
                    text = response.text
                    if "API rate limit exceeded" in text:
                        err_status, err_reason = _retry_failure(
                            "rate_limited", "limite de taxa da API excedido"
                        )
                    elif status_code == 200:
                        try:
                            data = response.json()
                        except ValueError:
                            return None, "failed", "resposta JSON inválida do ESearch"
                        if not isinstance(data, dict) or not isinstance(data.get("esearchresult"), dict):
                            return None, "failed", "resposta JSON inválida do ESearch"
                        return data, None, None
                    elif status_code == 429:
                        err_status, err_reason = _retry_failure("rate_limited", "HTTP 429")
                    elif 500 <= status_code < 600:
                        err_status, err_reason = _retry_failure("failed", f"HTTP {status_code}")
                    else:
                        return None, "failed", f"HTTP {status_code}"

            if attempt < max_retries:
                await self._sleep(RETRY_DELAYS[attempt])

        return None, err_status, err_reason

    # NFR-04: Consulta EFetch com até 3 novas tentativas (1, 2, 4 s) em 429, 5xx e limite
    async def _request_efetch(
        self,
        client: httpx.AsyncClient,
        params: dict[str, str],
        headers: dict[str, str],
        has_key: bool,
    ) -> tuple[ET.Element | None, str | None, str | None]:
        max_retries = len(RETRY_DELAYS)
        err_status, err_reason = "failed", "falha inesperada ao consultar o PubMed"
        for attempt in range(max_retries + 1):
            async with rate_limited_call(
                has_key=has_key, clock=self._clock, sleep=self._sleep
            ):
                try:
                    response = await client.get(
                        PUBMED_EFETCH_URL,
                        params=params,
                        headers=headers,
                        timeout=DEFAULT_TIMEOUT,
                    )
                except httpx.TimeoutException:
                    err_status, err_reason = _retry_failure("failed", "tempo limite esgotado")
                except httpx.HTTPError:
                    err_status, err_reason = _retry_failure("failed", "erro de rede")
                except Exception:  # noqa: BLE001
                    return None, "failed", "falha inesperada ao consultar o PubMed"
                else:
                    status_code = response.status_code
                    text = response.text
                    if "API rate limit exceeded" in text:
                        err_status, err_reason = _retry_failure(
                            "rate_limited", "limite de taxa da API excedido"
                        )
                    elif status_code == 200:
                        try:
                            root = ET.fromstring(response.content)
                        except ET.ParseError:
                            return None, "failed", "resposta XML inválida do EFetch"
                        return root, None, None
                    elif status_code == 429:
                        err_status, err_reason = _retry_failure("rate_limited", "HTTP 429")
                    elif 500 <= status_code < 600:
                        err_status, err_reason = _retry_failure("failed", f"HTTP {status_code}")
                    else:
                        return None, "failed", f"HTTP {status_code}"

            if attempt < max_retries:
                await self._sleep(RETRY_DELAYS[attempt])

        return None, err_status, err_reason

    # FR-01, FR-03, FR-14, NFR-03, NFR-04, D-004, D-020: Busca sequencial ESearch -> EFetch
    async def search(self, query: str, max_results: int = 100) -> SourceResult:
        clean_query = query.strip()
        effective_max = max(max_results, 1)

        api_key = self._resolve_api_key()
        contact_email = self._resolve_contact_email()
        has_key = bool(api_key)

        headers = {
            "User-Agent": _user_agent(),
        }

        retmax_esearch = min(effective_max, MAX_ESEARCH_RESULTS)
        esearch_params: dict[str, str] = {
            "db": "pubmed",
            "term": clean_query,
            "retmode": "json",
            "retmax": str(retmax_esearch),
            "usehistory": "y",
            "tool": "rslapp",
        }
        if contact_email:
            esearch_params["email"] = contact_email
        if api_key:
            esearch_params["api_key"] = api_key

        works: list[Work] = []
        found: int | None = None
        last_retstart = 0

        try:
            async with self._get_client() as client:
                data, err_status, err_reason = await self._request_esearch(
                    client, esearch_params, headers, has_key
                )
                if err_status is not None:
                    return SourceResult(
                        name=self.name,
                        status=err_status,
                        reason=err_reason,
                        query=_format_query_text(clean_query, last_retstart),
                        found=None,
                        fetched=0,
                        works=[],
                    )

                assert data is not None
                esearchresult = data["esearchresult"]
                raw_count = esearchresult.get("count")
                try:
                    count = int(raw_count) if raw_count is not None else 0
                except (ValueError, TypeError):
                    count = 0
                found = count

                if count == 0:
                    return SourceResult(
                        name=self.name,
                        status="ok",
                        reason=None,
                        query=_format_query_text(clean_query, last_retstart),
                        found=0,
                        fetched=0,
                        works=[],
                    )

                webenv = esearchresult.get("webenv") or esearchresult.get("WebEnv")
                query_key = (
                    esearchresult.get("querykey")
                    or esearchresult.get("QueryKey")
                    or esearchresult.get("query_key")
                )
                if not webenv or not query_key:
                    return SourceResult(
                        name=self.name,
                        status="failed",
                        reason="ESearch não retornou WebEnv ou query_key",
                        query=_format_query_text(clean_query, last_retstart),
                        found=found,
                        fetched=0,
                        works=[],
                    )

                retstart = 0
                total_to_fetch = min(found, effective_max, MAX_ESEARCH_RESULTS)

                while retstart < total_to_fetch and len(works) < effective_max:
                    last_retstart = retstart
                    efetch_params: dict[str, str] = {
                        "db": "pubmed",
                        "retmode": "xml",
                        "WebEnv": str(webenv),
                        "query_key": str(query_key),
                        "retstart": str(retstart),
                        "retmax": str(BATCH_SIZE),
                        "tool": "rslapp",
                    }
                    if contact_email:
                        efetch_params["email"] = contact_email
                    if api_key:
                        efetch_params["api_key"] = api_key

                    xml_root, fetch_err_status, fetch_err_reason = await self._request_efetch(
                        client, efetch_params, headers, has_key
                    )
                    if fetch_err_status is not None:
                        # NFR-04: As páginas já trazidas ficam salvas no resultado parcial
                        return SourceResult(
                            name=self.name,
                            status=fetch_err_status,
                            reason=fetch_err_reason,
                            query=_format_query_text(clean_query, last_retstart),
                            found=found,
                            fetched=len(works),
                            works=works,
                        )

                    assert xml_root is not None
                    articles = xml_root.findall(".//PubmedArticle")
                    if not articles:
                        break

                    for art in articles:
                        parsed_work = _parse_pubmed_article(art)
                        if parsed_work is not None:
                            works.append(parsed_work)
                            if len(works) >= effective_max:
                                break

                    if len(works) >= effective_max:
                        break

                    retstart += BATCH_SIZE

        except Exception:  # noqa: BLE001
            return SourceResult(
                name=self.name,
                status="failed",
                reason="falha inesperada ao consultar o PubMed",
                query=_format_query_text(clean_query, last_retstart),
                found=found,
                fetched=len(works),
                works=works,
            )

        return SourceResult(
            name=self.name,
            status="ok",
            reason=None,
            query=_format_query_text(clean_query, last_retstart),
            found=found,
            fetched=len(works),
            works=works,
        )
