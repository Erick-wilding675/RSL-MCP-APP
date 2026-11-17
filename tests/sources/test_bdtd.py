"""Testes do conector BDTD (Biblioteca Digital Brasileira de Teses e Dissertações)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from rslapp.sources.base import Source
from rslapp.sources.bdtd import BDTDSource


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_d035_bdtd_implements_source_protocol() -> None:
    source = BDTDSource()
    assert isinstance(source, Source)
    assert source.name == "bdtd"
    assert source.needs_key is False


def test_d035_bdtd_cache_query() -> None:
    source = BDTDSource()
    cached = source.cache_query("  inteligência artificial na saúde  ", 50)
    assert cached == {
        "source": "bdtd",
        "query": "inteligência artificial na saúde",
        "max_results": 50,
    }


SAMPLE_BDTD_RECORD_DOCTORAL: dict[str, Any] = {
    "id": "PUC_RIO-1_69e0bed4d4ce05f2e6664e5d6c5677e8",
    "title": "[pt] A RESPONSABILIDADE CIVIL NA INTELIGÊNCIA ARTIFICIAL",
    "authors": {
        "primary": {"FARIA, Pedro Alberto Schiller de": []},
        "secondary": {"MULHOLLAND, Caitlin Sampaio": []},
    },
    "formats": ["doctoralThesis"],
    "languages": ["por"],
    "institutions": ["PUC_RIO"],
    "publicationDates": ["2023"],
    "summary": [
        "[pt] A presente tese tem como objeto o estudo da responsabilidade civil decorrente de danos causados por IA."
    ],
    "subjects": [
        ["[pt] INTELIGENCIA ARTIFICIAL"],
        ["[pt] RESPONSABILIDADE CIVIL"],
        ["[en] ARTIFICIAL INTELLIGENCE"],
    ],
    "urls": [
        {
            "desc": "Repositório Institucional",
            "url": "https://www.maxwell.vrac.puc-rio.br/colecao.php?nrSeq=61871",
        },
        {
            "desc": "DOI",
            "url": "http://doi.org/10.17771/PUCRio.acad.61871",
        },
    ],
}

SAMPLE_BDTD_RECORD_MASTER: dict[str, Any] = {
    "id": "USP_12345",
    "title": "[en] Machine Learning Applications in Epidemiology",
    "authors": {
        "primary": {"SILVA, João": []},
        "secondary": {"SANTOS, Maria": []},
    },
    "formats": ["masterThesis"],
    "institutions": ["USP"],
    "publicationDates": ["2022"],
    "summary": ["[en] This dissertation explores machine learning methods."],
    "subjects": ["Machine Learning", "Epidemiology"],
    "urls": [
        {"url": "https://teses.usp.br/teses/disponiveis/12345.pdf"},
    ],
}


@pytest.mark.anyio
async def test_d035_search_successful_mapping() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/vufind/api/v1/search"
        assert "lookfor=inteligencia+artificial" in str(request.url)
        payload = {
            "status": "OK",
            "resultCount": 2,
            "records": [SAMPLE_BDTD_RECORD_DOCTORAL, SAMPLE_BDTD_RECORD_MASTER],
        }
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = BDTDSource(client=client)
        result = await source.search("inteligencia artificial", max_results=10)

    assert result.status == "ok"
    assert result.found == 2
    assert result.fetched == 2
    assert len(result.works) == 2

    # Verifica primeiro registro (Tese de Doutorado)
    w1 = result.works[0]
    assert w1.title == "A RESPONSABILIDADE CIVIL NA INTELIGÊNCIA ARTIFICIAL"
    assert w1.doi == "10.17771/pucrio.acad.61871"
    assert w1.year == 2023
    assert w1.venue == "PUC_RIO"
    assert w1.type == "thesis"
    assert w1.abstract == "A presente tese tem como objeto o estudo da responsabilidade civil decorrente de danos causados por IA."
    assert "INTELIGENCIA ARTIFICIAL" in w1.keywords
    assert "RESPONSABILIDADE CIVIL" in w1.keywords
    assert "ARTIFICIAL INTELLIGENCE" in w1.keywords
    assert w1.source_ids == {"bdtd": "PUC_RIO-1_69e0bed4d4ce05f2e6664e5d6c5677e8"}

    # Autores e filiações
    assert len(w1.authors) == 2
    assert w1.authors[0].name == "FARIA, Pedro Alberto Schiller de"
    assert w1.authors[0].position == 1
    assert w1.authors[0].raw_affiliations == ["PUC_RIO"]
    assert w1.authors[1].name == "MULHOLLAND, Caitlin Sampaio"
    assert w1.authors[1].position is None

    # Verifica segundo registro (Dissertação de Mestrado)
    w2 = result.works[1]
    assert w2.title == "Machine Learning Applications in Epidemiology"
    assert w2.doi is None
    assert w2.year == 2022
    assert w2.type == "dissertation"
    assert w2.venue == "USP"


@pytest.mark.anyio
async def test_d035_search_skips_record_without_title() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = {
            "status": "OK",
            "resultCount": 2,
            "records": [
                {"id": "inv_1", "title": ""},
                {"id": "inv_2", "title": None},
                SAMPLE_BDTD_RECORD_DOCTORAL,
            ],
        }
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = BDTDSource(client=client)
        result = await source.search("teste", max_results=5)

    assert result.status == "ok"
    assert len(result.works) == 1
    assert result.works[0].title == "A RESPONSABILIDADE CIVIL NA INTELIGÊNCIA ARTIFICIAL"


@pytest.mark.anyio
async def test_d035_search_pagination() -> None:
    requested_pages: list[int] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", 1))
        requested_pages.append(page)
        rec = dict(SAMPLE_BDTD_RECORD_DOCTORAL)
        rec["id"] = f"id_page_{page}"
        rec["title"] = f"Título da página {page}"
        payload = {
            "status": "OK",
            "resultCount": 250,
            "records": [rec] * 100 if page <= 2 else [rec] * 50,
        }
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = BDTDSource(client=client)
        result = await source.search("paginacao", max_results=150)

    assert result.status == "ok"
    assert len(result.works) == 150
    assert requested_pages == [1, 2]


@pytest.mark.anyio
async def test_d035_search_empty_results() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "OK", "resultCount": 0, "records": []})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = BDTDSource(client=client)
        result = await source.search("termo_inexistente", max_results=10)

    assert result.status == "ok"
    assert result.found == 0
    assert result.fetched == 0
    assert result.works == []


@pytest.mark.anyio
async def test_d035_search_retries_on_rate_limit_and_error() -> None:
    calls = 0
    sleeps: list[float] = []

    async def fake_sleep(duration: float) -> None:
        sleeps.append(duration)

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, text="Rate Limited")
        if calls == 2:
            return httpx.Response(503, text="Service Unavailable")
        return httpx.Response(200, json={"status": "OK", "resultCount": 1, "records": [SAMPLE_BDTD_RECORD_DOCTORAL]})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = BDTDSource(client=client, sleep_fn=fake_sleep)
        result = await source.search("retry", max_results=10)

    assert result.status == "ok"
    assert len(result.works) == 1
    assert calls == 3
    assert sleeps == [1, 2]
