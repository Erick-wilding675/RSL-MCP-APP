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


# NFR-03: Chave enviada apenas no cabeçalho x-api-key, nunca na URL
@pytest.mark.anyio
async def test_nfr03_s2_chave_somente_no_cabecalho_nunca_na_url(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_key = "fake-s2-secret-key"
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", fake_key)
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "total": 0,
                "data": [],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = SemanticScholarSource(client=client)

    await source.related("10.1234/exemplo", "references")
    assert len(captured_requests) > 0
    for req in captured_requests:
        assert req.headers.get("x-api-key") == fake_key
        assert fake_key not in str(req.url)


# FR-15: DOI codificado na URL da Semantic Scholar com %2F
@pytest.mark.anyio
async def test_fr15_s2_doi_codificado_na_url() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "total": 0,
                "data": [],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = SemanticScholarSource(client=client)

    await source.related("10.1234/exemplo", "references")
    assert len(captured_requests) == 1
    # Confere que o DOI no caminho está codificado com %2F
    assert b"DOI:10.1234%2Fexemplo/references" in captured_requests[0].url.raw_path


# FR-15: Artigo não encontrado na Semantic Scholar devolve HTTP 404 e not_found=True
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
    assert res.not_found is True


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


# D-010: Semantic Scholar para antes de 10 mil e limite da fonte é o motivo (inclusive com next=9500 exigindo limit=500)
@pytest.mark.anyio
async def test_d010_s2_limite_10k_fonte_next_9500() -> None:
    captured_calls: list[tuple[int, int]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", 0))
        limit = int(request.url.params.get("limit", 1000))
        captured_calls.append((offset, limit))

        # Se for chamada com offset + limit > 10.000 a API daria 400
        if offset + limit > 10_000:
            return httpx.Response(400, json={"error": "offset + limit must be <= 10000"})

        if offset == 0:
            return httpx.Response(
                200,
                json={
                    "total": 15000,
                    "next": 9500,
                    "data": [
                        {
                            "citingPaper": {
                                "paperId": f"p-{i}",
                                "title": f"Paper {i}",
                                "year": 2024,
                            }
                        }
                        for i in range(limit)
                    ],
                },
            )
        elif offset == 9500:
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
        return httpx.Response(400)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = SemanticScholarSource(client=client)

    res = await source.related("10.1234/exemplo", "citations", max_results=10_000)
    assert res.status == "ok"
    assert res.found == 15000
    assert res.reason == "limite de 10.000 da fonte"

    # Confere que a segunda requisição chamou exatamente offset=9500 e limit=500 (sem estourar 10.000)
    assert len(captured_calls) == 2
    assert captured_calls[0] == (0, 1000)
    assert captured_calls[1] == (9500, 500)
    for off, lim in captured_calls:
        assert off + lim <= 10_000


# FR-15, D-010: Citações na Semantic Scholar sem total na resposta: com next no teto devolve motivo; sem next, sem motivo
@pytest.mark.anyio
async def test_fr15_d010_s2_citacoes_sem_total_com_next_no_teto_e_sem_next() -> None:
    def handler_com_next(request: httpx.Request) -> httpx.Response:
        limit = int(request.url.params.get("limit", 100))
        return httpx.Response(
            200,
            json={
                "offset": 0,
                "next": limit,
                "data": [
                    {
                        "citingPaper": {
                            "paperId": f"p-{i}",
                            "title": f"Citing Paper {i}",
                            "year": 2024,
                        }
                    }
                    for i in range(limit)
                ],
            },
        )

    client_com_next = httpx.AsyncClient(transport=httpx.MockTransport(handler_com_next))
    source_com_next = SemanticScholarSource(client=client_com_next)

    res_com_next = await source_com_next.related("10.1234/exemplo", "citations", max_results=100)
    assert res_com_next.status == "ok"
    assert res_com_next.found is None
    assert res_com_next.fetched == 100
    assert res_com_next.reason == "teto de 100 atingido"

    def handler_sem_next(request: httpx.Request) -> httpx.Response:
        limit = int(request.url.params.get("limit", 100))
        return httpx.Response(
            200,
            json={
                "offset": 0,
                "data": [
                    {
                        "citingPaper": {
                            "paperId": f"p-{i}",
                            "title": f"Citing Paper {i}",
                            "year": 2024,
                        }
                    }
                    for i in range(limit)
                ],
            },
        )

    client_sem_next = httpx.AsyncClient(transport=httpx.MockTransport(handler_sem_next))
    source_sem_next = SemanticScholarSource(client=client_sem_next)

    res_sem_next = await source_sem_next.related("10.1234/exemplo", "citations", max_results=100)
    assert res_sem_next.status == "ok"
    assert res_sem_next.found is None
    assert res_sem_next.fetched == 100
    assert res_sem_next.reason is None
