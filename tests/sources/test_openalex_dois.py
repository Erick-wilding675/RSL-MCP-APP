"""Testes da consulta em lote de DOIs na API do OpenAlex."""

from __future__ import annotations

import httpx
import pytest

from rslapp.sources.openalex import DoiLookup, OpenAlexSource


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clean_openalex_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)


# FR-14, NFR-01: Consulta de DOIs com parâmetros e normalização de DOI
@pytest.mark.anyio
async def test_fr14_nfr01_lookup_dois_sucesso(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "meta": {"count": 2},
                "results": [
                    {
                        "id": "https://openalex.org/W2741809807",
                        "doi": "https://doi.org/10.7717/peerj.4375",
                    },
                    {
                        "id": "https://openalex.org/W2755950973",
                        "doi": "https://dx.doi.org/10.1038/s41586-020-2649-2",
                    },
                ],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    result = await source.lookup_dois(["W2741809807", "W2755950973"])
    assert result.status == "ok"
    assert result.reason is None
    assert result.mapping == {
        "W2741809807": "10.7717/peerj.4375",
        "W2755950973": "10.1038/s41586-020-2649-2",
    }

    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.url.params.get("filter") == "openalex:W2741809807|W2755950973"
    assert req.url.params.get("select") == "id,doi"
    assert req.url.params.get("per_page") == "100"


# FR-14: Ids com DOI nulo e ids omitidos pela API mapeiam para None
@pytest.mark.anyio
async def test_fr14_lookup_dois_nulos_e_omitidos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "meta": {"count": 1},
                "results": [
                    {
                        "id": "https://openalex.org/W1",
                        "doi": None,
                    }
                    # W2 é omitido pela API
                ],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    result = await source.lookup_dois(["W1", "W2"])
    assert result.status == "ok"
    assert result.mapping == {"W1": None, "W2": None}


# NFR-03: Chave de API vai apenas no cabeçalho Authorization e nunca na URL
@pytest.mark.anyio
async def test_nfr03_lookup_dois_chave_apenas_no_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "secret-key-xyz")
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json={"results": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    await source.lookup_dois(["W100"])
    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.headers.get("Authorization") == "Bearer secret-key-xyz"
    assert "secret-key-xyz" not in str(req.url)
    for v in req.url.params.values():
        assert "secret-key-xyz" not in v


# NFR-03: Sem variável de ambiente nenhuma chamada de rede é feita
@pytest.mark.anyio
async def test_nfr03_lookup_dois_sem_chave() -> None:
    called = False

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    result = await source.lookup_dois(["W100"])
    assert called is False
    assert result.status == "missing_key"
    assert result.reason == "variável OPENALEX_API_KEY não configurada"
    assert result.mapping == {}


# NFR-03: Chave com caracteres inválidos não faz chamada
@pytest.mark.anyio
@pytest.mark.parametrize("bad_key", ["chave com espaço", "chave\nquebrada", "chavé_não_ascii"])
async def test_nfr03_lookup_dois_chave_invalida(
    monkeypatch: pytest.MonkeyPatch, bad_key: str
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", bad_key)
    called = False

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    result = await source.lookup_dois(["W100"])
    assert called is False
    assert result.status == "failed"
    assert result.reason == "OPENALEX_API_KEY tem caracteres inválidos"


# NFR-01, NFR-04: HTTP 429 esgota tentativas e devolve rate_limited
@pytest.mark.anyio
async def test_nfr01_nfr04_lookup_dois_rate_limited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key")
    call_count = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(429, json={"error": "rate limit"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def no_sleep(_: float) -> None:
        pass

    source = OpenAlexSource(client=client, sleep=no_sleep)
    result = await source.lookup_dois(["W100"])
    assert call_count == 4  # 1 inicial + 3 retentativas
    assert result.status == "rate_limited"
    assert "depois de 3 tentativas" in (result.reason or "")


# NFR-01: Créditos esgotados devolve rate_limited imediatamente sem retentativa
@pytest.mark.anyio
async def test_nfr01_lookup_dois_creditos_esgotados(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key")
    call_count = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(
            429, json={"error": "not_enough_credits: daily limit reached"}
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)
    result = await source.lookup_dois(["W100"])
    assert call_count == 1
    assert result.status == "rate_limited"
    assert result.reason == "créditos diários do OpenAlex esgotados"


# FR-14: Exceção inesperada nunca é propagada pelo método
@pytest.mark.anyio
async def test_fr14_lookup_dois_excecao_inesperada_nunca_lanca(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key")

    def handler(_: httpx.Request) -> httpx.Response:
        raise RuntimeError("boom!")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)
    result = await source.lookup_dois(["W100"])
    assert result.status == "failed"
    assert result.reason == "falha inesperada ao consultar o OpenAlex"


# FR-14: Resposta JSON inválida devolve failed
@pytest.mark.anyio
async def test_fr14_lookup_dois_resposta_json_invalida(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key")

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json at all")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)
    result = await source.lookup_dois(["W100"])
    assert result.status == "failed"
    assert result.reason == "resposta JSON inválida do OpenAlex"


# NFR-01: Limita chamada a no máximo 100 ids
@pytest.mark.anyio
async def test_nfr01_lookup_dois_limita_a_100_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key")
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json={"results": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)
    ids_120 = [f"W{i}" for i in range(120)]
    await source.lookup_dois(ids_120)

    assert len(captured_requests) == 1
    req = captured_requests[0]
    filter_val = req.url.params.get("filter")
    assert filter_val is not None and filter_val.startswith("openalex:")
    filter_ids = filter_val.removeprefix("openalex:").split("|")
    assert len(filter_ids) == 100


# FR-14: Lista vazia devolve resultado vazio sem chamada
@pytest.mark.anyio
async def test_fr14_lookup_dois_lista_vazia() -> None:
    source = OpenAlexSource()
    res = await source.lookup_dois([])
    assert res.status == "ok"
    assert res.reason is None
    assert res.mapping == {}


# FR-14: Dataclass DoiLookup serialização e desserialização
def test_fr14_doi_lookup_dataclass() -> None:
    lookup = DoiLookup(status="ok", reason=None, mapping={"W1": "10.123/x"})
    data = lookup.to_dict()
    assert data == {"status": "ok", "reason": None, "mapping": {"W1": "10.123/x"}}
    reconstructed = DoiLookup.from_dict(data)
    assert reconstructed == lookup
