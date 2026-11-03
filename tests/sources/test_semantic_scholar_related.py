"""Testes da consulta de trabalhos relacionados na Semantic Scholar."""

from __future__ import annotations

import httpx
import pytest

from rslapp.sources.semantic_scholar import SemanticScholarSource, reset_rate_limiter


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clean_s2_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
    # Zera limitador de taxa para testes rápidos sem espera real
    mock_time = 1000.0

    def fake_clock() -> float:
        nonlocal mock_time
        mock_time += 1.5
        return mock_time

    async def fake_sleep(_: float) -> None:
        pass

    reset_rate_limiter(clock=fake_clock, sleep=fake_sleep)


# FR-15: Semantic Scholar sem DOI do artigo de origem devolve not_supported
@pytest.mark.anyio
@pytest.mark.parametrize("empty_doi", [None, "", "   "])
async def test_fr15_s2_sem_doi_not_supported(empty_doi: str | None) -> None:
    source = SemanticScholarSource()
    res = await source.related(empty_doi, "references")
    assert res.status == "not_supported"
    assert res.reason == "artigo de origem sem DOI"
    assert res.fetched == 0
    assert res.works == []


# FR-15, NFR-03: Chave com caracteres inválidos devolve failed
@pytest.mark.anyio
async def test_fr15_nfr03_s2_chave_invalida(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "chave com espaço")
    source = SemanticScholarSource()
    res = await source.related("10.1234/exemplo", "citations")
    assert res.status == "failed"
    assert "caracteres inválidos" in (res.reason or "")


# FR-15: Artigo não encontrado na Semantic Scholar devolve HTTP 404
@pytest.mark.anyio
async def test_fr15_s2_paper_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "Paper not found"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = SemanticScholarSource(client=client)

    res = await source.related("10.9999/naoexiste", "references")
    assert res.status == "failed"
    assert res.reason == "HTTP 404"
    assert res.fetched == 0


# FR-15, FR-08, FR-14: Consulta de referências e citações com citedPaper e citingPaper
@pytest.mark.anyio
async def test_fr15_fr08_s2_references_and_citations() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "references" in path:
            return httpx.Response(
                200,
                json={
                    "total": 1,
                    "data": [
                        {
                            "citedPaper": {
                                "paperId": "p-ref-1",
                                "title": "Reference Paper 1",
                                "externalIds": {"DOI": "10.1234/ref1"},
                                "year": 2021,
                                "authors": [{"authorId": "a1", "name": "Author One"}],
                            }
                        }
                    ],
                },
            )
        elif "citations" in path:
            return httpx.Response(
                200,
                json={
                    "total": 1,
                    "data": [
                        {
                            "citingPaper": {
                                "paperId": "p-cite-1",
                                "title": "Citing Paper 1",
                                "externalIds": {"DOI": "10.1234/cite1"},
                                "year": 2023,
                                "authors": [{"authorId": "a2", "name": "Author Two"}],
                            }
                        }
                    ],
                },
            )
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = SemanticScholarSource(client=client)

    res_ref = await source.related("10.1234/exemplo", "references")
    assert res_ref.status == "ok"
    assert res_ref.found == 1
    assert res_ref.fetched == 1
    assert len(res_ref.works) == 1
    assert res_ref.works[0].title == "Reference Paper 1"
    assert res_ref.works[0].doi == "10.1234/ref1"

    res_cite = await source.related("10.1234/exemplo", "citations")
    assert res_cite.status == "ok"
    assert res_cite.found == 1
    assert res_cite.fetched == 1
    assert len(res_cite.works) == 1
    assert res_cite.works[0].title == "Citing Paper 1"
    assert res_cite.works[0].doi == "10.1234/cite1"


# D-010: Teto de max_results atingido na Semantic Scholar
@pytest.mark.anyio
async def test_d010_s2_teto_max_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        limit = int(request.url.params.get("limit", 100))
        return httpx.Response(
            200,
            json={
                "total": 1500,
                "data": [
                    {
                        "citedPaper": {
                            "paperId": f"p-{i}",
                            "title": f"Paper {i}",
                            "year": 2022,
                        }
                    }
                    for i in range(limit)
                ],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = SemanticScholarSource(client=client)

    res = await source.related("10.1234/exemplo", "references", max_results=1000)
    assert res.status == "ok"
    assert res.found == 1500
    assert res.fetched == 1000
    assert res.reason == "teto de 1.000 atingido"


# D-010: Semantic Scholar para antes de 10 mil e limite da fonte é o motivo
@pytest.mark.anyio
async def test_d010_s2_limite_10k_fonte() -> None:
    # Simula requisição próxima de 10.000 (offset=9000, limit=1000) onde a próxima daria >= 10.000
    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", 0))
        limit = int(request.url.params.get("limit", 1000))
        # Se for chamada com offset + limit > 10.000 a API daria 400
        if offset + limit > 10_000:
            return httpx.Response(400, json={"error": "offset + limit must be < 10000"})
        return httpx.Response(
            200,
            json={
                "total": 15000,
                "next": 10000,
                "data": [
                    {
                        "citingPaper": {
                            "paperId": f"p-{offset + i}",
                            "title": f"Paper {offset + i}",
                            "year": 2024,
                        }
                    }
                    for i in range(limit)
                ],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = SemanticScholarSource(client=client)

    # Pede 10.000 resultados; na chamada com limit=1000, após offset 0 com next 10000 ele para antes
    res = await source.related("10.1234/exemplo", "citations", max_results=10_000)
    assert res.status == "ok"
    assert res.found == 15000
    assert res.reason == "limite de 10.000 da fonte"
