"""Testes do conector Web of Science Starter API com MockTransport (sem rede)."""

from __future__ import annotations

import logging
from typing import Any

import httpx
import pytest

from rslapp.sources.base import Source
from rslapp.sources.web_of_science import REQUEST_INTERVAL, WebOfScienceSource


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clean_wos_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WOS_STARTER_API_KEY", raising=False)


async def _noop_sleep(_seconds: float) -> None:
    pass


# D-023: Protocolo Source, cache_query e repr da fonte Web of Science
def test_d023_cache_query_e_repr_e_protocolo() -> None:
    source = WebOfScienceSource()
    assert isinstance(source, Source)
    assert source.name == "web_of_science"
    assert source.needs_key is True
    assert repr(source) == "WebOfScienceSource(name='web_of_science', needs_key=True)"
    assert source.cache_query("  deep learning  ", 50) == {
        "source": "web_of_science",
        "query": "deep learning",
        "max_results": 50,
    }


# FR-01, FR-03, FR-14, D-004, D-023: Mapeamento a partir do exemplo oficial, campos opcionais e descarte sem título
@pytest.mark.anyio
async def test_d023_fr01_fr03_fr14_d004_mapeamento_completo_e_casos_especiais(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WOS_STARTER_API_KEY", "chave-falsa-wos")
    captured_requests: list[httpx.Request] = []

    payload: dict[str, Any] = {
        "metadata": {
            "total": 5,
            "page": 1,
            "limit": 10,
        },
        "hits": [
            {
                "uid": "WOS:000123456700001",
                "title": "Deep learning in systematic reviews",
                "types": ["Article", "Journal"],
                "source": {
                    "sourceTitle": "Journal of Artificial Intelligence",
                    "publishYear": 2024,
                    "volume": "42",
                    "issue": "3",
                    "pages": "100-115",
                },
                "names": {
                    "authors": [
                        {
                            "displayName": "Silva, João P.",
                            "wosStandard": "Silva, JP",
                            "researcherId": "A-1234-2020",
                        },
                        {
                            "displayName": "Doe, Jane",
                            "wosStandard": "Doe, J",
                        },
                    ],
                },
                "citations": [
                    {
                        "db": "WOS",
                        "count": 15,
                    },
                    {
                        "db": "BCI",
                        "count": 2,
                    },
                ],
                "identifiers": {
                    "doi": "10.1016/j.artint.2024.01.001",
                    "issn": "0004-3702",
                    "eissn": "1872-6291",
                    "pmid": "38123456",
                },
                "keywords": {
                    "authorKeywords": [
                        "Deep Learning",
                        "Systematic Review",
                        "NLP",
                        "deep learning",
                    ],
                },
                "links": {
                    "record": "https://www.webofscience.com/wos/woscc/full-record/WOS:000123456700001",
                },
            },
            {
                "uid": "WOS:000123456700002",
                "title": "Trial Plan Document",
                "types": ["Review"],
                "source": {
                    "sourceTitle": "Review Journal",
                    "publishYear": "2023",
                },
                "names": {
                    "authors": [
                        {
                            "displayName": "Alan Turing",
                        },
                    ],
                },
                "citations": [],
                "identifiers": {
                    "pmid": "39999999",
                },
            },
            {
                "uid": "WOS:000123456700003",
                "title": "",
            },
            {
                "uid": "WOS:000123456700004",
                "title": "   ",
            },
            {
                "uid": "WOS:000123456700005",
                "types": ["Article"],
            },
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = WebOfScienceSource(client=client, sleep=_noop_sleep)
        res = await source.search("deep learning", max_results=10)

    assert len(captured_requests) == 1
    assert res.status == "ok"
    assert res.reason is None
    assert res.found == 5
    assert res.fetched == 2
    assert len(res.works) == 2

    # Artigo 1: mapeamento completo
    w1 = res.works[0]
    assert w1.title == "Deep learning in systematic reviews"
    assert w1.doi == "10.1016/j.artint.2024.01.001"
    assert w1.year == 2024
    assert w1.venue == "Journal of Artificial Intelligence"
    assert w1.type == "article"
    assert w1.abstract is None
    assert w1.keywords == ["Deep Learning", "Systematic Review", "NLP"]
    assert w1.citations == {"web_of_science": 15}
    assert w1.source_ids == {
        "web_of_science": "WOS:000123456700001",
        "pubmed": "38123456",
    }
    assert w1.references == []
    assert w1.references_count is None

    # Autores do artigo 1
    assert len(w1.authors) == 2
    a1 = w1.authors[0]
    assert a1.name == "Silva, João P."
    assert a1.orcid is None
    assert a1.ids == {"web_of_science": "A-1234-2020"}
    assert a1.affiliations == []
    assert a1.raw_affiliations == []

    a2 = w1.authors[1]
    assert a2.name == "Doe, Jane"
    assert a2.orcid is None
    assert a2.ids == {}
    assert a2.affiliations == []
    assert a2.raw_affiliations == []

    # Artigo 2: sem DOI, sem citations (plano de teste), com pmid, sem researcherId
    w2 = res.works[1]
    assert w2.title == "Trial Plan Document"
    assert w2.doi is None
    assert w2.year == 2023
    assert w2.venue == "Review Journal"
    assert w2.type == "review"
    assert w2.abstract is None
    assert w2.keywords == []
    assert w2.citations == {}
    assert w2.source_ids == {
        "web_of_science": "WOS:000123456700002",
        "pubmed": "39999999",
    }
    assert len(w2.authors) == 1
    assert w2.authors[0].name == "Alan Turing"
    assert w2.authors[0].ids == {}


# D-023: Consulta: texto simples vira TS=(...) e sintaxe com etiquetas vai como está
@pytest.mark.anyio
async def test_d023_consulta_sintaxe_wos_e_texto_simples(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WOS_STARTER_API_KEY", "chave-falsa-wos")
    queries_sent: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        queries_sent.append(request.url.params["q"])
        return httpx.Response(
            200,
            json={
                "metadata": {"total": 0, "page": 1, "limit": 10},
                "hits": [],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = WebOfScienceSource(client=client, sleep=_noop_sleep)

        await source.search("diabetes mellitus")
        await source.search("AU=Silva AND PY=2020")
        await source.search("TS=(machine learning)")
        await source.search("TI=deep learning")
        await source.search("PMID=38123456")

    assert queries_sent == [
        "TS=(diabetes mellitus)",
        "AU=Silva AND PY=2020",
        "TS=(machine learning)",
        "TI=deep learning",
        "PMID=38123456",
    ]


# D-023: Paginação pede page 1, 2 e 3 e para em max_results ou em total, com intervalo
@pytest.mark.anyio
async def test_d023_paginacao_page_1_2_3_para_em_max_results_ou_total_com_intervalo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WOS_STARTER_API_KEY", "chave-falsa-wos")

    # Caso A: max_results = 120, total = 150 -> pede page 1, 2 e 3 e para em 120 trabalhos
    pages_a: list[str] = []
    limits_a: list[str] = []
    recorded_sleeps_a: list[float] = []

    async def record_sleep_a(seconds: float) -> None:
        recorded_sleeps_a.append(seconds)

    def handler_a(request: httpx.Request) -> httpx.Response:
        page_str = request.url.params["page"]
        limit_str = request.url.params["limit"]
        pages_a.append(page_str)
        limits_a.append(limit_str)
        page_int = int(page_str)
        limit_int = int(limit_str)
        hits = [
            {
                "uid": f"WOS:0001{(page_int - 1) * limit_int + i:08d}",
                "title": f"Artigo {(page_int - 1) * limit_int + i}",
            }
            for i in range(limit_int)
        ]
        return httpx.Response(
            200,
            json={
                "metadata": {"total": 150, "page": page_int, "limit": limit_int},
                "hits": hits,
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_a)) as client:
        source = WebOfScienceSource(client=client, sleep=record_sleep_a)
        res_a = await source.search("ai", max_results=120)

    assert pages_a == ["1", "2", "3"]
    assert limits_a == ["50", "50", "50"]
    assert recorded_sleeps_a == [REQUEST_INTERVAL, REQUEST_INTERVAL]
    assert res_a.status == "ok"
    assert res_a.found == 150
    assert res_a.fetched == 120
    assert len(res_a.works) == 120
    assert res_a.query == "q=TS=(ai) · limit=50 · páginas 1-3"

    # Caso B: max_results = 150, total = 70 -> pede page 1 e 2 e para no total de 70
    pages_b: list[str] = []
    limits_b: list[str] = []
    recorded_sleeps_b: list[float] = []

    async def record_sleep_b(seconds: float) -> None:
        recorded_sleeps_b.append(seconds)

    def handler_b(request: httpx.Request) -> httpx.Response:
        page_str = request.url.params["page"]
        limit_str = request.url.params["limit"]
        pages_b.append(page_str)
        limits_b.append(limit_str)
        page_int = int(page_str)
        count = 50 if page_int == 1 else 20
        hits = [
            {
                "uid": f"WOS:0002{(page_int - 1) * 50 + i:08d}",
                "title": f"Artigo {(page_int - 1) * 50 + i}",
            }
            for i in range(count)
        ]
        return httpx.Response(
            200,
            json={
                "metadata": {"total": 70, "page": page_int, "limit": 50},
                "hits": hits,
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_b)) as client:
        source = WebOfScienceSource(client=client, sleep=record_sleep_b)
        res_b = await source.search("ai", max_results=150)

    assert pages_b == ["1", "2"]
    assert limits_b == ["50", "50"]
    assert recorded_sleeps_b == [REQUEST_INTERVAL]
    assert res_b.status == "ok"
    assert res_b.found == 70
    assert res_b.fetched == 70
    assert len(res_b.works) == 70
    assert res_b.query == "q=TS=(ai) · limit=50 · páginas 1-2"


# D-023: Tratamento de erros 429 repetido, 401 e 403 imediatos, 5xx, timeout e rede
@pytest.mark.anyio
async def test_d023_estados_429_repetido_401_403_e_outros_erros(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WOS_STARTER_API_KEY", "chave-falsa-wos")

    # 429 repetido até o fim: rate_limited com mensagem de limite diário após 3 retentativas
    calls_429 = 0

    def handler_429(_request: httpx.Request) -> httpx.Response:
        nonlocal calls_429
        calls_429 += 1
        return httpx.Response(429, text="Too Many Requests")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_429)) as client:
        source = WebOfScienceSource(client=client, sleep=_noop_sleep)
        res_429 = await source.search("ai")
    assert calls_429 == 4
    assert res_429.status == "rate_limited"
    assert res_429.reason == (
        "limite diário do Web of Science atingido (50 pedidos por dia no plano de teste)"
    )

    # 401 imediato sem novas tentativas
    calls_401 = 0

    def handler_401(_request: httpx.Request) -> httpx.Response:
        nonlocal calls_401
        calls_401 += 1
        return httpx.Response(401, json={"error": "Unauthorized"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_401)) as client:
        source = WebOfScienceSource(client=client, sleep=_noop_sleep)
        res_401 = await source.search("ai")
    assert calls_401 == 1
    assert res_401.status == "failed"
    assert res_401.reason == "chave do Web of Science recusada ou sem acesso"

    # 403 imediato sem novas tentativas
    calls_403 = 0

    def handler_403(_request: httpx.Request) -> httpx.Response:
        nonlocal calls_403
        calls_403 += 1
        return httpx.Response(403, json={"error": "Forbidden"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_403)) as client:
        source = WebOfScienceSource(client=client, sleep=_noop_sleep)
        res_403 = await source.search("ai")
    assert calls_403 == 1
    assert res_403.status == "failed"
    assert res_403.reason == "chave do Web of Science recusada ou sem acesso"

    # 400: failed imediato sem novas tentativas
    calls_400 = 0

    def handler_400(_request: httpx.Request) -> httpx.Response:
        nonlocal calls_400
        calls_400 += 1
        return httpx.Response(400, text="Bad Request")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_400)) as client:
        source = WebOfScienceSource(client=client, sleep=_noop_sleep)
        res_400 = await source.search("ai")
    assert calls_400 == 1
    assert res_400.status == "failed"
    assert res_400.reason == "HTTP 400"

    # 500: failed após 3 tentativas
    calls_500 = 0

    def handler_500(_request: httpx.Request) -> httpx.Response:
        nonlocal calls_500
        calls_500 += 1
        return httpx.Response(500, text="Server Error")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_500)) as client:
        source = WebOfScienceSource(client=client, sleep=_noop_sleep)
        res_500 = await source.search("ai")
    assert calls_500 == 4
    assert res_500.status == "failed"
    assert res_500.reason == "HTTP 500 depois de 3 tentativas"

    # Timeout: failed após 3 tentativas
    calls_timeout = 0

    def handler_timeout(_request: httpx.Request) -> httpx.Response:
        nonlocal calls_timeout
        calls_timeout += 1
        raise httpx.ReadTimeout("Timeout")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_timeout)) as client:
        source = WebOfScienceSource(client=client, sleep=_noop_sleep)
        res_timeout = await source.search("ai")
    assert calls_timeout == 4
    assert res_timeout.status == "failed"
    assert res_timeout.reason == "tempo limite esgotado depois de 3 tentativas"

    # Erro de rede: failed após 3 tentativas
    calls_net = 0

    def handler_net(_request: httpx.Request) -> httpx.Response:
        nonlocal calls_net
        calls_net += 1
        raise httpx.ConnectError("Connection failed")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_net)) as client:
        source = WebOfScienceSource(client=client, sleep=_noop_sleep)
        res_net = await source.search("ai")
    assert calls_net == 4
    assert res_net.status == "failed"
    assert res_net.reason == "erro de rede depois de 3 tentativas"


# D-023: Preservação de páginas já trazidas quando página seguinte falha
@pytest.mark.anyio
async def test_d023_preservacao_de_paginas_anteriores_em_falha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WOS_STARTER_API_KEY", "chave-falsa-wos")

    def handler(request: httpx.Request) -> httpx.Response:
        page = request.url.params.get("page")
        if page == "1":
            hits = [
                {"uid": f"WOS:0001000000000{i:02d}", "title": f"Artigo {i}"}
                for i in range(50)
            ]
            return httpx.Response(
                200,
                json={
                    "metadata": {"total": 100, "page": 1, "limit": 50},
                    "hits": hits,
                },
            )
        return httpx.Response(401, json={"error": "Token expired"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = WebOfScienceSource(client=client, sleep=_noop_sleep)
        res = await source.search("ai", max_results=100)

    assert res.status == "failed"
    assert res.reason == "chave do Web of Science recusada ou sem acesso"
    assert res.fetched == 50
    assert len(res.works) == 50
    assert res.query == "q=TS=(ai) · limit=50 · páginas 1-2"


# D-023: Teste de nova tentativa 429 seguida de 200 com sucesso
@pytest.mark.anyio
async def test_d023_retry_429_seguido_de_200_sucesso(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WOS_STARTER_API_KEY", "chave-falsa-wos")
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, text="Rate limit exceeded")
        return httpx.Response(
            200,
            json={
                "metadata": {"total": 1, "page": 1, "limit": 10},
                "hits": [{"uid": "WOS:0001", "title": "Artigo Recuperado"}],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = WebOfScienceSource(client=client, sleep=_noop_sleep)
        res = await source.search("ai", max_results=10)

    assert attempts == 2
    assert res.status == "ok"
    assert res.fetched == 1
    assert len(res.works) == 1
    assert res.works[0].title == "Artigo Recuperado"


# D-023: Chave vai no cabeçalho X-ApiKey e não vaza em URL, query, reason, cache_query, repr nem caplog
@pytest.mark.anyio
async def test_d023_chave_apenas_em_cabecalho_x_apikey_sem_vazamento(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_key = "chave-falsa-secreta-wos-12345"
    monkeypatch.setenv("WOS_STARTER_API_KEY", secret_key)

    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "metadata": {"total": 1, "page": 1, "limit": 10},
                "hits": [{"uid": "WOS:000100", "title": "Artigo Secreto"}],
            },
        )

    with caplog.at_level(logging.DEBUG):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            source = WebOfScienceSource(client=client, sleep=_noop_sleep)
            res = await source.search("ai", max_results=10)

    assert len(captured_requests) == 1
    req = captured_requests[0]

    # Chave vai apenas no cabeçalho X-ApiKey
    assert req.headers["X-ApiKey"] == secret_key

    # Não aparece na URL, em query, reason, cache_query, repr nem caplog
    assert secret_key not in str(req.url)
    assert secret_key not in res.query
    assert secret_key not in (res.reason or "")

    cache_q = source.cache_query("ai", 10)
    assert secret_key not in str(cache_q)
    assert secret_key not in repr(source)
    assert secret_key not in caplog.text


# D-023: Sem WOS_STARTER_API_KEY, missing_key sem nenhuma chamada de rede
@pytest.mark.anyio
async def test_d023_sem_wos_starter_api_key_responde_missing_key_sem_chamada_de_rede() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        pytest.fail("Nenhuma chamada de rede deveria ser feita sem WOS_STARTER_API_KEY")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = WebOfScienceSource(client=client, sleep=_noop_sleep)
        res = await source.search("cancer")

    assert res.status == "missing_key"
    assert res.reason == "variável WOS_STARTER_API_KEY não configurada"
    assert res.found is None
    assert res.fetched == 0
    assert res.works == []
    assert res.query == "q=TS=(cancer) · limit=50 · páginas 1-1"


# D-023: Resultado vazio no Web of Science responde status ok com 0 trabalhos
@pytest.mark.anyio
async def test_d023_resultado_vazio_wos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WOS_STARTER_API_KEY", "chave-falsa-wos")

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "metadata": {"total": 0, "page": 1, "limit": 10},
                "hits": [],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = WebOfScienceSource(client=client, sleep=_noop_sleep)
        res = await source.search("termo_inexistente_xyz_123")

    assert res.status == "ok"
    assert res.found == 0
    assert res.fetched == 0
    assert res.works == []
    assert res.query == "q=TS=(termo_inexistente_xyz_123) · limit=50 · páginas 1-1"


# FR-13: Busca simulada no Web of Science de duas páginas grava q=… · limit=50 · páginas 1-2
@pytest.mark.anyio
async def test_fr13_wos_busca_duas_paginas_grava_paginas_1_2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WOS_STARTER_API_KEY", "chave-falsa-wos")

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        limit = int(request.url.params["limit"])
        hits = [
            {
                "uid": f"WOS:0001{(page - 1) * limit + i:08d}",
                "title": f"Artigo {(page - 1) * limit + i}",
            }
            for i in range(limit)
        ]
        return httpx.Response(
            200,
            json={
                "metadata": {"total": 100, "page": page, "limit": limit},
                "hits": hits,
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = WebOfScienceSource(client=client, sleep=_noop_sleep)
        res = await source.search("TS=(telemedicine)", max_results=100)

    assert res.status == "ok"
    assert res.fetched == 100
    assert res.query == "q=TS=(telemedicine) · limit=50 · páginas 1-2"


# FR-13: Falha na segunda página grava páginas 1-2 no Web of Science
@pytest.mark.anyio
async def test_fr13_wos_falha_segunda_pagina_grava_paginas_1_2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WOS_STARTER_API_KEY", "chave-falsa-wos")

    def handler(request: httpx.Request) -> httpx.Response:
        page = request.url.params.get("page")
        if page == "1":
            return httpx.Response(
                200,
                json={
                    "metadata": {"total": 100, "page": 1, "limit": 50},
                    "hits": [
                        {"uid": f"WOS:0001000000000{i:02d}", "title": f"Artigo {i}"}
                        for i in range(50)
                    ],
                },
            )
        return httpx.Response(500, text="Internal Server Error")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = WebOfScienceSource(client=client, sleep=_noop_sleep)
        res = await source.search("telemedicine", max_results=100)

    assert res.status == "failed"
    assert res.fetched == 50
    assert res.query == "q=TS=(telemedicine) · limit=50 · páginas 1-2"


# FR-13: Sem chave, o Web of Science grava limit adequado e páginas 1-1
@pytest.mark.anyio
async def test_fr13_wos_sem_chave_grava_query_correta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WOS_STARTER_API_KEY", raising=False)
    source = WebOfScienceSource(sleep=_noop_sleep)
    res_100 = await source.search("telemedicine", max_results=100)
    assert res_100.status == "missing_key"
    assert res_100.query == "q=TS=(telemedicine) · limit=50 · páginas 1-1"

    res_10 = await source.search("telemedicine", max_results=10)
    assert res_10.status == "missing_key"
    assert res_10.query == "q=TS=(telemedicine) · limit=10 · páginas 1-1"

