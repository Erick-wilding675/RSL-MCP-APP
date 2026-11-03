"""Testes da consulta de trabalhos relacionados (referências e citações) no OpenAlex."""

from __future__ import annotations

import httpx
import pytest

from rslapp.sources.openalex import OpenAlexSource


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clean_openalex_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)


# FR-15, NFR-03: Sem chave configurada retorna missing_key
@pytest.mark.anyio
async def test_fr15_nfr03_openalex_related_missing_key() -> None:
    source = OpenAlexSource()
    res = await source.related("10.1234/exemplo", "citations")
    assert res.status == "missing_key"
    assert "OPENALEX_API_KEY não configurada" in (res.reason or "")
    assert res.fetched == 0
    assert res.works == []


# FR-15, NFR-03: Chave com caracteres inválidos retorna failed
@pytest.mark.anyio
async def test_fr15_nfr03_openalex_related_chave_invalida(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "chave com espaço")
    source = OpenAlexSource()
    res = await source.related("10.1234/exemplo", "citations")
    assert res.status == "failed"
    assert "caracteres inválidos" in (res.reason or "")


# FR-15: Artigo de origem não encontrado retorna 404
@pytest.mark.anyio
async def test_fr15_openalex_related_origem_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "Not Found"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    res = await source.related("10.9999/naoexiste", "citations")
    assert res.status == "failed"
    assert res.reason == "HTTP 404"
    assert res.fetched == 0


# FR-15, FR-08: Citações de um artigo consultadas com filter=cites:W... e paginação
@pytest.mark.anyio
async def test_fr15_fr08_openalex_related_citations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        path = request.url.path
        if "doi:10.1234/exemplo" in path or "W100" in path:
            return httpx.Response(
                200,
                json={
                    "id": "https://openalex.org/W100",
                    "doi": "https://doi.org/10.1234/exemplo",
                    "cited_by_count": 2,
                    "referenced_works": [],
                },
            )
        # Chamada de citações
        return httpx.Response(
            200,
            json={
                "meta": {"count": 2},
                "results": [
                    {
                        "id": "https://openalex.org/W201",
                        "display_name": "Citing Paper 1",
                        "doi": "https://doi.org/10.1234/cite1",
                        "publication_year": 2023,
                        "authorships": [],
                    },
                    {
                        "id": "https://openalex.org/W202",
                        "display_name": "Citing Paper 2",
                        "doi": "https://doi.org/10.1234/cite2",
                        "publication_year": 2024,
                        "authorships": [],
                    },
                ],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    res = await source.related("10.1234/exemplo", "citations", max_results=100)
    assert res.status == "ok"
    assert res.reason is None
    assert res.found == 2
    assert res.fetched == 2
    assert len(res.works) == 2
    assert res.works[0].title == "Citing Paper 1"
    assert res.works[1].title == "Citing Paper 2"

    assert len(captured_requests) == 2
    # Segunda requisição filtra por cites:W100
    assert captured_requests[1].url.params.get("filter") == "cites:W100"


# FR-14, D-010: Referências são pedidas em grupos de no máximo 100 ids
@pytest.mark.anyio
async def test_fr14_openalex_related_references_lotes_100(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
    captured_requests: list[httpx.Request] = []

    # Cria 150 referências
    fake_refs = [f"https://openalex.org/W{i}" for i in range(1, 151)]

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        path = request.url.path
        if "W100" in path:
            return httpx.Response(
                200,
                json={
                    "id": "https://openalex.org/W100",
                    "doi": "https://doi.org/10.1234/exemplo",
                    "cited_by_count": 0,
                    "referenced_works": fake_refs,
                },
            )

        filter_param = request.url.params.get("filter", "")
        assert filter_param.startswith("openalex:")
        ids = filter_param.removeprefix("openalex:").split("|")
        assert len(ids) <= 100

        results = [
            {
                "id": f"https://openalex.org/{wid}",
                "display_name": f"Reference {wid}",
                "doi": f"https://doi.org/10.1234/{wid.lower()}",
                "publication_year": 2020,
                "authorships": [],
            }
            for wid in ids
        ]
        return httpx.Response(200, json={"results": results})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    res = await source.related("W100", "references", max_results=200)
    assert res.status == "ok"
    assert res.found == 150
    assert res.fetched == 150
    assert len(res.works) == 150

    # 1 de origem + 2 lotes (100 e 50)
    assert len(captured_requests) == 3
    lote1_ids = captured_requests[1].url.params["filter"].removeprefix("openalex:").split("|")
    lote2_ids = captured_requests[2].url.params["filter"].removeprefix("openalex:").split("|")
    assert len(lote1_ids) == 100
    assert len(lote2_ids) == 50


# D-010: Teto de max_results atingido retorna reason apropriado
@pytest.mark.anyio
async def test_d010_openalex_related_teto_atingido(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")

    fake_refs = [f"https://openalex.org/W{i}" for i in range(1, 1501)]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "W100" in path:
            return httpx.Response(
                200,
                json={
                    "id": "https://openalex.org/W100",
                    "doi": "https://doi.org/10.1234/exemplo",
                    "referenced_works": fake_refs,
                },
            )
        filter_param = request.url.params.get("filter", "")
        ids = filter_param.removeprefix("openalex:").split("|")
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": f"https://openalex.org/{wid}",
                        "display_name": f"Ref {wid}",
                        "publication_year": 2021,
                        "authorships": [],
                    }
                    for wid in ids
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    res = await source.related("W100", "references", max_results=1000)
    assert res.status == "ok"
    assert res.found == 1500
    assert res.fetched == 1000
    assert res.reason == "teto de 1.000 atingido"
