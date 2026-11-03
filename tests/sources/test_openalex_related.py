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


# NFR-03: Chave enviada apenas no cabeçalho Authorization, nunca na URL
@pytest.mark.anyio
async def test_nfr03_openalex_chave_somente_no_cabecalho_nunca_na_url(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_key = "fake-secret-key-xyz"
    monkeypatch.setenv("OPENALEX_API_KEY", fake_key)
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "https://openalex.org/W100",
                "doi": "https://doi.org/10.1234/exemplo",
                "cited_by_count": 0,
                "referenced_works": [],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    await source.related("10.1234/exemplo", "citations")
    assert len(captured_requests) > 0
    for req in captured_requests:
        assert req.headers.get("Authorization") == f"Bearer {fake_key}"
        assert fake_key not in str(req.url)


# FR-15: DOI codificado na URL do OpenAlex com %2F
@pytest.mark.anyio
async def test_fr15_openalex_doi_codificado_na_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "https://openalex.org/W100",
                "doi": "https://doi.org/10.1234/exemplo",
                "cited_by_count": 0,
                "referenced_works": [],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    await source.get_origin_work("10.1234/exemplo")
    assert len(captured_requests) == 1
    # Confere que o caminho na rede contém o DOI codificado com %2F
    assert b"doi:10.1234%2Fexemplo" in captured_requests[0].url.raw_path


# FR-15: Artigo de origem não encontrado retorna 404 e not_found=True
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
    assert res.not_found is True


# FR-15, FR-08: Citações de um artigo consultadas com filter=cites:W... e paginação
@pytest.mark.anyio
async def test_fr15_fr08_openalex_related_citations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        path = request.url.path
        if "doi:10.1234" in path or "W100" in path:
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


# D-010: Teto em citações do OpenAlex retorna motivo do teto
@pytest.mark.anyio
async def test_d010_openalex_citations_teto_atingido(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "doi:10.1234" in path or "W100" in path:
            return httpx.Response(
                200,
                json={
                    "id": "https://openalex.org/W100",
                    "doi": "https://doi.org/10.1234/exemplo",
                    "cited_by_count": 250,
                    "referenced_works": [],
                },
            )
        return httpx.Response(
            200,
            json={
                "meta": {"count": 250},
                "results": [
                    {
                        "id": f"https://openalex.org/W{i}",
                        "display_name": f"Citing {i}",
                        "publication_year": 2023,
                        "authorships": [],
                    }
                    for i in range(100)
                ],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    res = await source.related("W100", "citations", max_results=100)
    assert res.status == "ok"
    assert res.found == 250
    assert res.fetched == 100
    assert res.reason == "teto de 100 atingido"


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


# FR-14: IDs sujos são descartados antes de montar o filtro openalex:
@pytest.mark.anyio
async def test_fr14_openalex_ids_sujos_descartados(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
    captured_requests: list[httpx.Request] = []

    dirty_refs = [
        "https://openalex.org/W1",
        "invalid_id",
        "https://openalex.org/W123?bad=1",
        "https://openalex.org/A99",
        "https://openalex.org/W2\u0660",
        "https://openalex.org/W3",
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        path = request.url.path
        if "W100" in path:
            return httpx.Response(
                200,
                json={
                    "id": "https://openalex.org/W100",
                    "doi": "https://doi.org/10.1234/exemplo",
                    "referenced_works": dirty_refs,
                },
            )
        filter_param = request.url.params.get("filter", "")
        assert filter_param == "openalex:W1|W3"
        return httpx.Response(
            200,
            json={
                "results": [
                    {"id": "https://openalex.org/W1", "display_name": "Work 1", "publication_year": 2020, "authorships": []},
                    {"id": "https://openalex.org/W3", "display_name": "Work 3", "publication_year": 2020, "authorships": []},
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    res = await source.related("W100", "references")
    assert res.status == "ok"
    assert res.found == 2
    assert res.fetched == 2
    assert len(res.works) == 2


# D-010: Teto de max_results atingido retorna reason apropriado mesmo se um item do lote não voltar
@pytest.mark.anyio
async def test_d010_openalex_related_teto_atingido_com_item_faltante(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")

    # 1.500 referências, teto de 1.000
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
        # Simula que o id W1000 não volta da API (999 resultados retornados no total)
        results = [
            {
                "id": f"https://openalex.org/{wid}",
                "display_name": f"Ref {wid}",
                "publication_year": 2021,
                "authorships": [],
            }
            for wid in ids
            if wid != "W1000"
        ]
        return httpx.Response(200, json={"results": results})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    res = await source.related("W100", "references", max_results=1000)
    assert res.status == "ok"
    assert res.found == 1500
    assert res.fetched == 999  # 1 faltou, mas o teto foi de 1.000 e a lista original tinha 1.500
    assert res.reason == "teto de 1.000 atingido"
