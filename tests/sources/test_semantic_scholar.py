"""Testes do conector da Semantic Scholar com MockTransport (sem rede)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from rslapp.sources.base import Source
from rslapp.sources.semantic_scholar import (
    SELECT_FIELDS,
    SemanticScholarSource,
    reset_rate_limiter,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clean_semantic_scholar_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
    simulated_time = 0.0

    def fast_clock() -> float:
        return simulated_time

    async def fast_sleep(seconds: float) -> None:
        nonlocal simulated_time
        simulated_time += seconds

    reset_rate_limiter(clock=fast_clock, sleep=fast_sleep)


def _make_raw_work(idx: int, title: str | None = None) -> dict[str, Any]:
    return {
        "paperId": f"S2_{1000 + idx}",
        "externalIds": {"DOI": f"10.1000/182/{idx}", "ArXiv": f"2101.{idx:04d}"},
        "title": f"Paper Title {idx}" if title is None else title,
        "abstract": f"Abstract of paper {idx}",
        "venue": "Test Venue",
        "journal": {"name": "Journal of Testing"},
        "year": 2024,
        "publicationTypes": ["JournalArticle", "Review"],
        "referenceCount": 20 + idx,
        "citationCount": 5 + idx,
        "authors": [
            {"authorId": f"A{idx}_1", "name": f"Author {idx} One"},
            {"authorId": f"A{idx}_2", "name": f"Author {idx} Two"},
        ],
    }


# FR-01, FR-03, FR-14, D-004: Mapeia campos completos, subcampos e substitui hífen por espaço
@pytest.mark.anyio
async def test_fr01_fr03_fr14_d004_mapeamento_completo_e_subcampos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "fake-s2-key-123")
    captured_requests: list[httpx.Request] = []

    payload = {
        "total": 2,
        "offset": 0,
        "data": [
            {
                "paperId": "s2_abc123",
                "externalIds": {"DOI": "https://doi.org/10.1038/NATURE9999", "CorpusId": "123"},
                "title": "Deep Graph Attention Networks",
                "abstract": "We study graph attention in neural architectures.",
                "journal": {"name": "Nature Machine Intelligence"},
                "venue": "Nature MI Conference",
                "year": 2023,
                "publicationTypes": ["JournalArticle"],
                "referenceCount": 35,
                "citationCount": 110,
                "authors": [
                    {"authorId": "auth_1", "name": "Ana Beatriz"},
                    {"authorId": "auth_2", "name": "Carlos Lima"},
                ],
            },
            {
                "paperId": "s2_xyz789",
                "externalIds": {"DOI": "10.1145/333444.555666"},
                "title": "Survey on Transformers",
                "abstract": None,
                "journal": None,
                "venue": "ACM Computing Surveys",
                "year": 2024,
                "publicationTypes": ["Review"],
                "referenceCount": 80,
                "citationCount": 42,
                "authors": [
                    {"authorId": "auth_3", "name": "Diana Prince"},
                ],
            },
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = SemanticScholarSource(client=client)
        assert isinstance(source, Source)
        assert source.name == "semantic_scholar"
        assert source.needs_key is False
        result = await source.search("deep-learning  interpretability", max_results=100)

    assert len(captured_requests) == 1
    req = captured_requests[0]
    # Termos com hífen são substituídos por espaços
    assert req.url.params["query"] == "deep learning interpretability"
    assert req.url.params["offset"] == "0"
    assert req.url.params["limit"] == "100"
    assert req.url.params["fields"] == SELECT_FIELDS
    assert req.headers["x-api-key"] == "fake-s2-key-123"
    assert req.headers["User-Agent"].startswith("rslapp/")

    assert result.name == "semantic_scholar"
    assert result.status == "ok"
    assert result.reason is None
    assert result.found == 2
    assert result.fetched == 2
    assert len(result.works) == 2

    w1 = result.works[0]
    assert w1.title == "Deep Graph Attention Networks"
    assert w1.doi == "10.1038/nature9999"
    assert w1.year == 2023
    assert w1.type == "JournalArticle"
    assert w1.venue == "Nature Machine Intelligence"
    assert w1.abstract == "We study graph attention in neural architectures."
    assert w1.keywords == []
    assert w1.references == []
    assert w1.references_count == 35
    assert w1.citations == {"semantic_scholar": 110}
    assert w1.source_ids == {"semantic_scholar": "s2_abc123"}
    assert len(w1.authors) == 2
    assert w1.authors[0].name == "Ana Beatriz"
    assert w1.authors[0].ids == {"semantic_scholar": "auth_1"}
    assert w1.authors[0].orcid is None
    assert w1.authors[0].affiliations == []
    assert w1.authors[1].name == "Carlos Lima"
    assert w1.authors[1].ids == {"semantic_scholar": "auth_2"}

    w2 = result.works[1]
    assert w2.doi == "10.1145/333444.555666"
    assert w2.venue == "ACM Computing Surveys"
    assert w2.type == "Review"
    assert w2.abstract is None
    assert w2.source_ids == {"semantic_scholar": "s2_xyz789"}


# FR-03, FR-14: Descarte de trabalhos sem título e aceitação de campos nulos em qualquer nível
@pytest.mark.anyio
async def test_fr03_fr14_campos_nulos_e_descarte_sem_titulo() -> None:
    payload = {
        "total": 5,
        "offset": 0,
        "data": [
            {"paperId": "s1", "title": None},
            {"paperId": "s2", "title": "   "},
            {
                "paperId": None,
                "externalIds": None,
                "title": "Trabalho com Todos os Opcionais Nulos",
                "abstract": None,
                "journal": None,
                "venue": None,
                "year": None,
                "publicationTypes": None,
                "referenceCount": None,
                "citationCount": None,
                "authors": [
                    {"authorId": None, "name": "Autor Sem ID"},
                    {"authorId": "a2", "name": "   "},  # descarta sem nome
                    None,
                ],
            },
            {
                "paperId": "s4",
                "externalIds": {"ArXiv": "2101.1234"},  # sem DOI
                "title": "Trabalho Apenas com Venue",
                "journal": {"name": None},
                "venue": "Workshop on Testing",
                "publicationTypes": ["", "Review"],
                "authors": None,
            },
        ],
    }

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload))
    ) as client:
        result = await SemanticScholarSource(client=client).search("null fields", max_results=50)

    assert result.status == "ok"
    assert result.found == 5
    assert result.fetched == 2
    assert len(result.works) == 2

    w1 = result.works[0]
    assert w1.title == "Trabalho com Todos os Opcionais Nulos"
    assert w1.doi is None
    assert w1.year is None
    assert w1.type is None
    assert w1.venue is None
    assert w1.abstract is None
    assert w1.keywords == []
    assert w1.references == []
    assert w1.references_count is None
    assert w1.citations == {}
    assert w1.source_ids == {}
    assert len(w1.authors) == 1
    assert w1.authors[0].name == "Autor Sem ID"
    assert w1.authors[0].ids == {}

    w2 = result.works[1]
    assert w2.doi is None
    assert w2.venue == "Workshop on Testing"
    assert w2.type == "Review"
    assert w2.authors == []


# FR-01, NFR-04: Paginação por offset para em max_results, next ausente, 1000 itens ou descartes
@pytest.mark.anyio
async def test_fr01_nfr04_paginacao_offset_max_results_next_e_limite_1000() -> None:
    # 1. max_results=10 pede limit=10 na requisição
    seen_limits: list[str] = []

    def handler_small(request: httpx.Request) -> httpx.Response:
        seen_limits.append(request.url.params["limit"])
        return httpx.Response(
            200,
            json={"total": 20, "offset": 0, "data": [_make_raw_work(i) for i in range(10)]},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_small)) as client:
        res_small = await SemanticScholarSource(client=client).search("small", max_results=10)

    assert seen_limits == ["10"]
    assert res_small.fetched == 10
    assert res_small.query == "query=small · limit=10 · offset=0"

    # 2. max_results=150: busca página 1 (offset=0, limit=100) e página 2 (offset=100, limit=100)
    seen_offsets: list[str] = []

    def handler_max(request: httpx.Request) -> httpx.Response:
        off = int(request.url.params["offset"])
        seen_offsets.append(str(off))
        items = [_make_raw_work(off + i) for i in range(100)]
        resp_data: dict[str, Any] = {
            "total": 500 if off == 0 else 999,
            "offset": off,
            "data": items,
        }
        if off == 0:
            resp_data["next"] = 100
        return httpx.Response(200, json=resp_data)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_max)) as client:
        res_max = await SemanticScholarSource(client=client).search("paging", max_results=150)

    assert seen_offsets == ["0", "100"]
    assert res_max.found == 500  # found vem da primeira página
    assert res_max.fetched == 150
    assert len(res_max.works) == 150
    assert res_max.query == "query=paging · limit=100 · offset=100"

    # 3. Descartes na página 1: pede página 2 para completar max_results
    seen_discard_offsets: list[str] = []

    def handler_discard(request: httpx.Request) -> httpx.Response:
        off = int(request.url.params["offset"])
        seen_discard_offsets.append(str(off))
        items = [
            _make_raw_work(off + i, title="" if (off == 0 and i < 5) else None) for i in range(100)
        ]
        return httpx.Response(
            200,
            json={"total": 200, "offset": off, "next": off + 100, "data": items},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_discard)) as client:
        res_discard = await SemanticScholarSource(client=client).search("discard", max_results=100)

    assert seen_discard_offsets == ["0", "100"]
    assert res_discard.fetched == 100
    assert len(res_discard.works) == 100

    # 4. next ausente para a paginação
    seen_next_offsets: list[str] = []

    def handler_no_next(request: httpx.Request) -> httpx.Response:
        off = int(request.url.params["offset"])
        seen_next_offsets.append(str(off))
        return httpx.Response(
            200,
            json={"total": 25, "offset": 0, "data": [_make_raw_work(i) for i in range(25)]},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_no_next)) as client:
        res_no_next = await SemanticScholarSource(client=client).search("no_next", max_results=100)

    assert seen_next_offsets == ["0"]
    assert res_no_next.fetched == 25

    # 5. Teto de 1.000 resultados mesmo se max_results for maior
    offsets_1000: list[int] = []

    def handler_1000(request: httpx.Request) -> httpx.Response:
        off = int(request.url.params["offset"])
        offsets_1000.append(off)
        resp: dict[str, Any] = {
            "total": 5000,
            "offset": off,
            "data": [_make_raw_work(off + i) for i in range(100)],
        }
        if off < 900:
            resp["next"] = off + 100
        else:
            resp["next"] = 1000
        return httpx.Response(200, json=resp)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_1000)) as client:
        res_1000 = await SemanticScholarSource(client=client).search("limit_1000", max_results=1500)

    assert len(offsets_1000) == 10
    assert offsets_1000[0] == 0 and offsets_1000[-1] == 900
    assert res_1000.fetched == 1000

    # 6. Preservação parcial: falha na página 2 preserva itens da página 1
    def handler_partial(request: httpx.Request) -> httpx.Response:
        off = int(request.url.params["offset"])
        if off == 0:
            return httpx.Response(
                200,
                json={
                    "total": 300,
                    "offset": 0,
                    "next": 100,
                    "data": [_make_raw_work(i) for i in range(100)],
                },
            )
        return httpx.Response(400, json={"error": "Offset exceeds limit"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_partial)) as client:
        res_partial = await SemanticScholarSource(client=client).search("partial", max_results=200)

    assert res_partial.status == "failed"
    assert res_partial.reason == "Offset exceeds limit"
    assert res_partial.found == 300
    assert res_partial.fetched == 100
    assert len(res_partial.works) == 100


# FR-08, NFR-04: Ritmo com trava no módulo, >= 1s entre inícios (com e sem chave, com fake clock)
@pytest.mark.anyio
async def test_fr08_nfr04_ritmo_trava_modulo_e_intervalo_1s_com_e_sem_chave(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_time = 100.0
    sleeps: list[float] = []

    def fake_clock() -> float:
        return current_time

    async def fake_sleep(seconds: float) -> None:
        nonlocal current_time
        sleeps.append(seconds)
        current_time += seconds

    reset_rate_limiter(clock=fake_clock, sleep=fake_sleep)

    call_start_times: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal current_time
        call_start_times.append(current_time)
        # Simula duração da requisição de 0.2s
        current_time += 0.2
        return httpx.Response(
            200,
            json={"total": 1, "offset": 0, "data": [_make_raw_work(1)]},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = SemanticScholarSource(client=client, sleep=fake_sleep, clock=fake_clock)

        # Chamada 1 sem chave
        await source.search("call1", max_results=10)
        # Chamada 2 sem chave
        await source.search("call2", max_results=10)

        # Chamada 3 com chave
        monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "fake-key")
        await source.search("call3", max_results=10)

    assert len(call_start_times) == 3
    # Pelo menos 1 segundo entre o início de cada chamada
    assert call_start_times[1] - call_start_times[0] >= 1.0
    assert call_start_times[2] - call_start_times[1] >= 1.0


# NFR-01, NFR-04: Retentativas [1, 2, 4] em 429, 5xx, timeout e rede; 429 sem chave vira rate_limited
@pytest.mark.anyio
@pytest.mark.parametrize(
    ("action", "expected_status", "expected_reason"),
    [
        (
            lambda req: httpx.Response(429, json={"error": "Rate limit exceeded"}),
            "rate_limited",
            "HTTP 429 depois de 3 tentativas",
        ),
        (
            lambda req: httpx.Response(503, text="Service Unavailable"),
            "failed",
            "HTTP 503 depois de 3 tentativas",
        ),
        (
            lambda req: (_ for _ in ()).throw(
                httpx.ReadTimeout("detalhe timeout x-api-key fake-key", request=req)
            ),
            "failed",
            "tempo limite esgotado depois de 3 tentativas",
        ),
        (
            lambda req: (_ for _ in ()).throw(
                httpx.ConnectError("detalhe conexao x-api-key fake-key", request=req)
            ),
            "failed",
            "erro de rede depois de 3 tentativas",
        ),
    ],
)
async def test_nfr01_nfr04_retries_429_5xx_timeout_e_rede(
    action: Callable[[httpx.Request], httpx.Response],
    expected_status: str,
    expected_reason: str,
) -> None:
    current_time = 50.0
    sleeps: list[float] = []
    calls = 0

    def fake_clock() -> float:
        return current_time

    async def fake_sleep(seconds: float) -> None:
        nonlocal current_time
        sleeps.append(seconds)
        current_time += seconds

    reset_rate_limiter(clock=fake_clock, sleep=fake_sleep)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls, current_time
        calls += 1
        current_time += 0.1
        return action(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = SemanticScholarSource(client=client, sleep=fake_sleep, clock=fake_clock)
        # Teste sem chave para provar que 429 persistente devolve rate_limited e não quebra a busca
        res = await source.search("query")

    assert calls == 4
    # Inclui as esperas de retentativas [1, 2, 4]
    assert 1 in sleeps
    assert 2 in sleeps
    assert 4 in sleeps
    assert res.status == expected_status
    assert res.reason == expected_reason
    assert "fake-key" not in (res.reason or "")
    assert "detalhe" not in (res.reason or "")


# NFR-04: Erros 400 falham na hora com o motivo da API e respostas JSON inválidas
@pytest.mark.anyio
@pytest.mark.parametrize(
    ("response", "expected_status", "expected_reason"),
    [
        (
            httpx.Response(400, json={"error": "Unrecognized or unsupported fields: [foo]"}),
            "failed",
            "Unrecognized or unsupported fields: [foo]",
        ),
        (
            httpx.Response(404, text="Not Found"),
            "failed",
            "HTTP 404",
        ),
        (
            httpx.Response(200, text="<html>not json</html>"),
            "failed",
            "resposta JSON inválida da Semantic Scholar",
        ),
        (
            httpx.Response(200, json=[{"paperId": "s1"}]),
            "failed",
            "resposta JSON inválida da Semantic Scholar",
        ),
    ],
)
async def test_nfr04_erros_sem_repeticao_400_e_json_invalido(
    response: httpx.Response,
    expected_status: str,
    expected_reason: str,
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return response

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        res = await SemanticScholarSource(client=client).search("query")

    assert calls == 1
    assert res.status == expected_status
    assert res.reason == expected_reason


# NFR-03: Chave opcional no cabeçalho x-api-key, validação de caracteres e isolamento de segredo
@pytest.mark.anyio
async def test_nfr03_chave_no_cabecalho_e_isolamento_seguro(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_key = "fake-s2-secret-999"
    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        q = request.url.params.get("query")
        if q == "erro":
            return httpx.Response(400, json={"error": f"invalid param for {secret_key}"})
        if q == "excecao":
            raise RuntimeError(f"boom crash {secret_key}")
        return httpx.Response(
            200,
            json={"total": 1, "offset": 0, "data": [_make_raw_work(1)]},
        )

    with caplog.at_level(logging.DEBUG):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            source = SemanticScholarSource(client=client)

            # 1. Sem chave: cabeçalho x-api-key não é enviado e busca funciona
            res_no_key = await source.search("sem-chave", max_results=10)
            assert res_no_key.status == "ok"
            assert "x-api-key" not in seen_requests[0].headers

            # 2. Com chave: cabeçalho x-api-key é enviado
            monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", secret_key)
            res_with_key = await source.search("com-chave", max_results=10)
            assert res_with_key.status == "ok"
            assert seen_requests[1].headers["x-api-key"] == secret_key

            # 3. Erro 400 e exceção não vazam a chave no reason
            res_err = await source.search("erro", max_results=10)
            res_exc = await source.search("excecao", max_results=10)
            cache_q = source.cache_query("com-chave", max_results=10)
            repr_str = repr(source)

            # 4. Chave com caracteres inválidos falha com mensagem fixa sem vazar
            for bad_key in ("chave-ç-inv", "chave com espaco", "chave-\n-inv"):
                monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", bad_key)
                res_bad = await source.search("bad_key", max_results=10)
                assert res_bad.status == "failed"
                assert res_bad.reason == "SEMANTIC_SCHOLAR_API_KEY tem caracteres inválidos"
                assert bad_key not in (res_bad.reason or "")
                assert bad_key not in res_bad.query
                assert bad_key not in caplog.text

    # Verifica todas as superfícies para garantir que a chave nunca vaza
    assert secret_key not in str(seen_requests[1].url)
    assert secret_key not in (res_err.reason or "")
    assert secret_key not in (res_exc.reason or "")
    assert secret_key not in res_with_key.query
    assert secret_key not in str(res_with_key.to_dict())
    assert secret_key not in str(cache_q)
    assert secret_key not in repr_str
    assert secret_key not in caplog.text
