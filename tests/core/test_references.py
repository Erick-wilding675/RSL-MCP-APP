"""Testes do serviço de resolução de referências para DOI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest

from rslapp.core.references import ReferenceResolution, resolve_reference_dois
from rslapp.sources.openalex import OpenAlexSource
from rslapp.store import Store


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clean_openalex_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)


# FR-14, NFR-01: 120 ids viram DOI em 2 chamadas (100 e 20); sem DOI e omitidos viram None
@pytest.mark.anyio
async def test_fr14_nfr01_resolve_120_ids_em_2_chamadas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        filter_param = request.url.params.get("filter", "")
        assert filter_param.startswith("openalex:")
        requested_ids = filter_param.removeprefix("openalex:").split("|")

        results = []
        for rid in requested_ids:
            # W50 sem DOI
            if rid == "W50":
                results.append({"id": f"https://openalex.org/{rid}", "doi": None})
            # W99 omitido (não entra em results)
            elif rid == "W99":
                continue
            else:
                results.append(
                    {
                        "id": f"https://openalex.org/{rid}",
                        "doi": f"https://doi.org/10.1000/{rid.lower()}",
                    }
                )

        return httpx.Response(200, json={"results": results})

    store = Store(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    ids = [f"W{i}" for i in range(120)]
    res = await resolve_reference_dois(ids, store=store, source=source)

    assert res.calls == 2
    assert res.from_cache == 0
    assert res.complete is True
    assert res.reason is None
    assert len(res.mapping) == 120

    # Chamada 1 teve 100 ids, chamada 2 teve 20 ids
    assert len(captured_requests) == 2
    filter1 = captured_requests[0].url.params["filter"].removeprefix("openalex:").split("|")
    filter2 = captured_requests[1].url.params["filter"].removeprefix("openalex:").split("|")
    assert len(filter1) == 100
    assert len(filter2) == 20

    # Id com DOI
    assert res.mapping["W0"] == "10.1000/w0"
    # Id sem DOI
    assert res.mapping["W50"] is None
    # Id omitido
    assert res.mapping["W99"] is None


# FR-14, D-010: Ids repetidos e entradas que não são ids do OpenAlex não geram chamada
@pytest.mark.anyio
async def test_fr14_d010_ids_repetidos_e_nao_openalex_ignorados(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "results": [
                    {"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1000/1"},
                    {"id": "https://openalex.org/W2", "doi": "https://doi.org/10.1000/2"},
                ]
            },
        )

    store = Store(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    mixed_ids = [
        "W1",
        "W1",  # repetido
        "10.1000/ja_e_doi",  # não é id do OpenAlex
        "https://doi.org/10.2000/doi_url",  # DOI com URL
        "invalid_text",
        "",
        "W2",
        "W1",  # repetido novamente
    ]
    res = await resolve_reference_dois(mixed_ids, store=store, source=source)

    assert res.calls == 1
    assert res.complete is True
    assert len(captured_requests) == 1
    filter_val = captured_requests[0].url.params["filter"]
    assert filter_val == "openalex:W1|W2"
    assert res.mapping == {"W1": "10.1000/1", "W2": "10.1000/2"}

    # Somente entradas que não são OpenAlex: zero chamadas
    res_no_oa = await resolve_reference_dois(
        ["10.1000/x", "https://doi.org/10.1000/y"], store=store, source=source
    )
    assert res_no_oa.calls == 0
    assert res_no_oa.complete is True
    assert res_no_oa.mapping == {}


# NFR-06, D-007: A segunda troca dos mesmos ids vem do cache e não gasta chamada (calls == 0)
@pytest.mark.anyio
async def test_nfr06_d007_segunda_troca_vem_do_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
    call_count = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(
            200,
            json={
                "results": [
                    {"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1000/1"},
                    {"id": "https://openalex.org/W2", "doi": None},
                ]
            },
        )

    store = Store(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    ids = ["W1", "W2"]
    # Primeira chamada: vai à API
    res1 = await resolve_reference_dois(ids, store=store, source=source)
    assert res1.calls == 1
    assert res1.from_cache == 0
    assert res1.mapping == {"W1": "10.1000/1", "W2": None}
    assert call_count == 1

    # Segunda chamada com os mesmos ids: deve vir totalmente do cache
    res2 = await resolve_reference_dois(ids, store=store, source=source)
    assert res2.calls == 0
    assert res2.from_cache == 2
    assert res2.complete is True
    assert res2.reason is None
    assert res2.mapping == res1.mapping
    # Nenhuma chamada HTTP adicional foi realizada
    assert call_count == 1


# FR-14, NFR-04: Se a segunda chamada falha, mantém DOIs da primeira e não grava falha no cache
@pytest.mark.anyio
async def test_fr14_nfr04_falha_na_segunda_chamada(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Primeiro lote de 100 ids tem sucesso
            filter_param = request.url.params.get("filter", "")
            requested_ids = filter_param.removeprefix("openalex:").split("|")
            results = [
                {
                    "id": f"https://openalex.org/{rid}",
                    "doi": f"https://doi.org/10.1000/{rid.lower()}",
                }
                for rid in requested_ids
            ]
            return httpx.Response(200, json={"results": results})
        # Segundo lote falha com 429 créditos esgotados
        return httpx.Response(429, json={"error": "not_enough_credits"})

    store = Store(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    ids = [f"W{i}" for i in range(120)]
    res = await resolve_reference_dois(ids, store=store, source=source)

    assert res.calls == 2
    assert res.complete is False
    assert res.reason == "rate_limited: créditos diários do OpenAlex esgotados"

    # Primeiro lote (W0..W99) foi resolvido com sucesso
    for i in range(100):
        oid = f"W{i}"
        assert res.mapping[oid] == f"10.1000/w{i}"
        assert store.get_cache("openalex_doi", {"id": oid}) is not None

    # Segundo lote (W100..W119) ficou como None e NÃO foi para o cache
    for i in range(100, 120):
        oid = f"W{i}"
        assert res.mapping[oid] is None
        assert store.get_cache("openalex_doi", {"id": oid}) is None


# NFR-03: Sem chave, nenhuma chamada e reason missing_key; com chave, vai só no cabeçalho
@pytest.mark.anyio
async def test_nfr03_sem_chave_nenhuma_chamada_e_reason_missing_key(
    tmp_path: Path,
) -> None:
    called = False

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={"results": []})

    store = Store(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    # Sem chave configurada
    res = await resolve_reference_dois(["W1", "W2"], store=store, source=source)
    assert called is False
    assert res.calls == 0
    assert res.from_cache == 0
    assert res.complete is False
    assert res.reason == "missing_key"
    assert res.mapping == {"W1": None, "W2": None}
    assert store.get_cache("openalex_doi", {"id": "W1"}) is None
    assert store.get_cache("openalex_doi", {"id": "W2"}) is None


# NFR-03: Com chave, ela vai somente no cabeçalho Authorization
@pytest.mark.anyio
async def test_nfr03_com_chave_vai_so_no_cabecalho(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_key = "fake-secret-token"
    monkeypatch.setenv("OPENALEX_API_KEY", fake_key)
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "results": [
                    {"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1000/1"}
                ]
            },
        )

    store = Store(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    await resolve_reference_dois(["W1"], store=store, source=source)
    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.headers.get("Authorization") == f"Bearer {fake_key}"
    assert fake_key not in str(req.url)


# FR-14: Lista vazia ou None não faz chamadas e devolve sucesso imediato
@pytest.mark.anyio
@pytest.mark.parametrize("empty_input", [[], None, ()])
async def test_fr14_entrada_vazia(tmp_path: Path, empty_input: Any) -> None:
    store = Store(tmp_path)
    res = await resolve_reference_dois(empty_input, store=store)
    assert res.calls == 0
    assert res.from_cache == 0
    assert res.complete is True
    assert res.reason is None
    assert res.mapping == {}


# FR-14: Dataclass ReferenceResolution serialização e desserialização
def test_fr14_reference_resolution_dataclass() -> None:
    obj = ReferenceResolution(
        mapping={"W1": "10.1000/1", "W2": None},
        calls=1,
        from_cache=2,
        complete=True,
        reason=None,
    )
    d = obj.to_dict()
    assert d == {
        "mapping": {"W1": "10.1000/1", "W2": None},
        "calls": 1,
        "from_cache": 2,
        "complete": True,
        "reason": None,
    }
    reconstructed = ReferenceResolution.from_dict(d)
    assert reconstructed == obj
