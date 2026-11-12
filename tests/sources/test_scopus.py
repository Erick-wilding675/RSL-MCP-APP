"""Testes do conector Scopus Search API com MockTransport (sem rede)."""

from __future__ import annotations

import logging

import httpx
import pytest

from rslapp.sources.base import Source
from rslapp.sources.scopus import ScopusSource


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clean_scopus_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SCOPUS_API_KEY", raising=False)
    monkeypatch.delenv("SCOPUS_INSTTOKEN", raising=False)


async def _noop_sleep(_seconds: float) -> None:
    pass


# D-023: Protocolo Source, cache_query e repr da fonte Scopus
def test_d023_cache_query_e_repr_e_protocolo() -> None:
    source = ScopusSource()
    assert isinstance(source, Source)
    assert source.name == "scopus"
    assert source.needs_key is True
    assert repr(source) == "ScopusSource(name='scopus', needs_key=True)"
    assert source.cache_query("  deep learning  ", 50) == {
        "source": "scopus",
        "query": "deep learning",
        "max_results": 50,
    }


# FR-01, FR-03, FR-14, D-004, D-023: Mapeamento completo visão COMPLETE, autores, ORCID, afiliações, nulos e descartes
@pytest.mark.anyio
async def test_d023_fr01_fr03_fr14_d004_mapeamento_completo_visao_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCOPUS_API_KEY", "chave-falsa-scopus")
    captured_requests: list[httpx.Request] = []

    payload = {
        "search-results": {
            "opensearch:totalResults": "5",
            "opensearch:startIndex": "0",
            "opensearch:itemsPerPage": "25",
            "entry": [
                {
                    "dc:identifier": "SCOPUS_ID:85012345678",
                    "eid": "2-s2.0-85012345678",
                    "dc:title": "Deep learning for systematic literature reviews",
                    "prism:doi": "10.1016/j.artint.2024.102345",
                    "prism:publicationName": "Artificial Intelligence",
                    "prism:coverDate": "2024-05-20",
                    "dc:description": "A comprehensive overview of NLP and deep learning in reviews. © 2024 Elsevier B.V. All rights reserved.",
                    "authkeywords": "Deep Learning | Systematic Review | NLP | deep learning | AI",
                    "citedby-count": "42",
                    "subtype": "ar",
                    "subtypeDescription": "Article",
                    "pubmed-id": "38123456",
                    "affiliation": [
                        {
                            "afid": "60021508",
                            "affilname": "Universidade de São Paulo",
                            "affiliation-city": "São Paulo",
                            "affiliation-country": "Brazil",
                        },
                        {
                            "afid": "60012345",
                            "affilname": "Harvard University",
                            "affiliation-city": "Cambridge",
                            "affiliation-country": "United States",
                        },
                    ],
                    "author": [
                        {
                            "authid": "57190001",
                            "authname": "Silva, João P.",
                            "given-name": "João P.",
                            "surname": "Silva",
                            "orcid": "https://orcid.org/0000-0002-1825-0097",
                            "afid": [{"$": "60021508"}, {"$": "60012345"}],
                        },
                        {
                            "authid": "57190002",
                            "authname": "Doe, Jane",
                            "given-name": "Jane",
                            "surname": "Doe",
                            "afid": [{"$": "60012345"}],
                        },
                        {
                            "authid": "57190003",
                            "authname": "Consórcio Latino-Americano",
                        },
                    ],
                },
                {
                    "dc:identifier": "SCOPUS_ID:85099999999",
                    "eid": "2-s2.0-85099999999",
                    "dc:title": "Paper with missing date and empty keywords",
                    "prism:doi": "https://doi.org/10.1016/j.artint.2024.999999",
                    "prism:publicationName": "AI Reports",
                    "subtypeDescription": "Review",
                    "dc:description": "No copyright symbol in this abstract.",
                    "authkeywords": "",
                    "citedby-count": 10,
                    "affiliation": [
                        {
                            "afid": "60099999",
                            "affilname": "Oxford University",
                            "affiliation-city": "Oxford",
                            "affiliation-country": "United Kingdom",
                        }
                    ],
                    "author": [
                        {
                            "authid": "57190004",
                            "given-name": "Alan",
                            "surname": "Turing",
                            "afid": [{"$": "60099999"}],
                        }
                    ],
                },
                {
                    "dc:identifier": "SCOPUS_ID:SEM-TITULO-1",
                    "eid": "2-s2.0-00000000001",
                    "dc:title": "",
                },
                {
                    "dc:identifier": "SCOPUS_ID:SEM-TITULO-2",
                    "eid": "2-s2.0-00000000002",
                    "dc:title": "    ",
                },
                {
                    "error": "Result set was empty",
                },
            ],
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = ScopusSource(client=client, sleep=_noop_sleep)
        res = await source.search("deep learning", max_results=10)

    assert len(captured_requests) == 1
    assert res.status == "ok"
    assert res.reason is None
    assert res.found == 5
    assert res.fetched == 2
    assert len(res.works) == 2

    # Artigo 1: mapeamento completo
    w1 = res.works[0]
    assert w1.title == "Deep learning for systematic literature reviews"
    assert w1.doi == "10.1016/j.artint.2024.102345"
    assert w1.year == 2024
    assert w1.venue == "Artificial Intelligence"
    assert w1.type == "article"
    assert w1.abstract == "A comprehensive overview of NLP and deep learning in reviews."
    assert w1.keywords == ["Deep Learning", "Systematic Review", "NLP", "AI"]
    assert w1.citations == {"scopus": 42}
    assert w1.source_ids == {"scopus": "2-s2.0-85012345678", "pubmed": "38123456"}
    assert w1.references == []
    assert w1.references_count is None

    # Autores do artigo 1: autor com 2 afiliações, autor sem ORCID, autor só com authname
    assert len(w1.authors) == 3

    a1 = w1.authors[0]
    assert a1.name == "João P. Silva"
    assert a1.orcid == "0000-0002-1825-0097"
    assert a1.ids == {"scopus": "57190001"}
    assert len(a1.affiliations) == 2
    assert a1.affiliations[0].name == "Universidade de São Paulo"
    assert a1.affiliations[0].ids == {"scopus": "60021508"}
    assert a1.affiliations[1].name == "Harvard University"
    assert a1.affiliations[1].ids == {"scopus": "60012345"}
    assert a1.raw_affiliations == [
        "Universidade de São Paulo, São Paulo, Brazil",
        "Harvard University, Cambridge, United States",
    ]

    a2 = w1.authors[1]
    assert a2.name == "Jane Doe"
    assert a2.orcid is None
    assert a2.ids == {"scopus": "57190002"}
    assert len(a2.affiliations) == 1
    assert a2.affiliations[0].name == "Harvard University"
    assert a2.raw_affiliations == ["Harvard University, Cambridge, United States"]

    a3 = w1.authors[2]
    assert a3.name == "Consórcio Latino-Americano"
    assert a3.orcid is None
    assert a3.ids == {"scopus": "57190003"}
    assert a3.affiliations == []
    assert a3.raw_affiliations == []

    # Artigo 2: sem data de capa, authkeywords vazio, resumo sem copyright, doi com prefixo https
    w2 = res.works[1]
    assert w2.title == "Paper with missing date and empty keywords"
    assert w2.doi == "10.1016/j.artint.2024.999999"
    assert w2.year is None
    assert w2.venue == "AI Reports"
    assert w2.type == "review"
    assert w2.abstract == "No copyright symbol in this abstract."
    assert w2.keywords == []
    assert w2.citations == {"scopus": 10}
    assert w2.source_ids == {"scopus": "2-s2.0-85099999999"}
    assert len(w2.authors) == 1
    assert w2.authors[0].name == "Alan Turing"


# D-023: Consulta: texto simples vira TITLE-ABS-KEY(...) e sintaxe Scopus vai como está
@pytest.mark.anyio
async def test_d023_consulta_sintaxe_scopus_e_texto_simples(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCOPUS_API_KEY", "chave-falsa-scopus")
    queries_sent: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        queries_sent.append(request.url.params["query"])
        return httpx.Response(
            200,
            json={
                "search-results": {
                    "opensearch:totalResults": "0",
                    "entry": [],
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = ScopusSource(client=client, sleep=_noop_sleep)

        await source.search("diabetes mellitus")
        await source.search("AUTH(silva) AND TITLE(x)")
        await source.search("DOI(10.1016/j.artint.2024.102345)")
        await source.search("TITLE-ABS-KEY(machine learning)")

    assert queries_sent == [
        "TITLE-ABS-KEY(diabetes mellitus)",
        "AUTH(silva) AND TITLE(x)",
        "DOI(10.1016/j.artint.2024.102345)",
        "TITLE-ABS-KEY(machine learning)",
    ]


# D-023: Paginação pede start 0, 25 e 50 e para em max_results ou em totalResults
@pytest.mark.anyio
async def test_d023_paginacao_start_0_25_50_para_em_max_results_ou_total_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCOPUS_API_KEY", "chave-falsa-scopus")

    # Caso A: max_results = 60, totalResults = 100 -> pede 0, 25, 50 e para em 60
    starts_a: list[str] = []
    counts_a: list[str] = []

    def handler_a(request: httpx.Request) -> httpx.Response:
        starts_a.append(request.url.params["start"])
        counts_a.append(request.url.params["count"])
        start_int = int(request.url.params["start"])
        count_int = int(request.url.params["count"])
        entries = [
            {
                "eid": f"2-s2.0-{start_int + i}",
                "dc:title": f"Artigo {start_int + i}",
            }
            for i in range(count_int)
        ]
        return httpx.Response(
            200,
            json={
                "search-results": {
                    "opensearch:totalResults": "100",
                    "entry": entries,
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_a)) as client:
        source = ScopusSource(client=client, sleep=_noop_sleep)
        res_a = await source.search("ai", max_results=60)

    assert starts_a == ["0", "25", "50"]
    assert counts_a == ["25", "25", "10"]
    assert res_a.status == "ok"
    assert res_a.found == 100
    assert res_a.fetched == 60
    assert len(res_a.works) == 60

    # Caso B: max_results = 100, totalResults = 60 -> pede 0, 25, 50 e para em totalResults
    starts_b: list[str] = []
    counts_b: list[str] = []

    def handler_b(request: httpx.Request) -> httpx.Response:
        starts_b.append(request.url.params["start"])
        counts_b.append(request.url.params["count"])
        start_int = int(request.url.params["start"])
        count_int = int(request.url.params["count"])
        entries = [
            {
                "eid": f"2-s2.0-{start_int + i}",
                "dc:title": f"Artigo {start_int + i}",
            }
            for i in range(count_int)
        ]
        return httpx.Response(
            200,
            json={
                "search-results": {
                    "opensearch:totalResults": "60",
                    "entry": entries,
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_b)) as client:
        source = ScopusSource(client=client, sleep=_noop_sleep)
        res_b = await source.search("ai", max_results=100)

    assert starts_b == ["0", "25", "50"]
    assert counts_b == ["25", "25", "10"]
    assert res_b.status == "ok"
    assert res_b.found == 60
    assert res_b.fetched == 60
    assert len(res_b.works) == 60


# D-023: Visão reduzida: 403 na COMPLETE e 200 na STANDARD segue com aviso; 403 nas duas dá failed
@pytest.mark.anyio
async def test_d023_fallback_visao_reduzida_403_complete_200_standard_e_403_nas_duas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCOPUS_API_KEY", "chave-falsa-scopus")

    # Caso 1: 403 na COMPLETE, 200 na STANDARD
    views_called_1: list[str] = []

    def handler_fallback(request: httpx.Request) -> httpx.Response:
        view = request.url.params.get("view")
        views_called_1.append(view or "")
        if view == "COMPLETE":
            return httpx.Response(403, json={"error": "Not Entitled"})
        return httpx.Response(
            200,
            json={
                "search-results": {
                    "opensearch:totalResults": "1",
                    "entry": [
                        {
                            "eid": "2-s2.0-85012345678",
                            "dc:title": "Standard View Paper",
                            "dc:creator": "Silva, João P.",
                            "prism:coverDate": "2024-01-10",
                            "prism:doi": "10.1016/j.standard.2024.1",
                            "prism:publicationName": "Journal of Standard",
                            "citedby-count": "3",
                        }
                    ],
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_fallback)) as client:
        source = ScopusSource(client=client, sleep=_noop_sleep)
        res = await source.search("genomics", max_results=10)

    assert views_called_1 == ["COMPLETE", "STANDARD"]
    assert res.status == "ok"
    assert res.reason == (
        "visão reduzida do Scopus: só o primeiro autor, sem resumo nem palavras-chave"
    )
    assert res.fetched == 1
    assert len(res.works) == 1
    work = res.works[0]
    assert work.title == "Standard View Paper"
    assert work.abstract is None
    assert work.keywords == []
    assert len(work.authors) == 1
    assert work.authors[0].name == "Silva, João P."
    assert work.authors[0].orcid is None
    assert work.authors[0].affiliations == []

    # Caso 2: 403 nas duas visões dá failed com mensagem específica da decisão 4
    views_called_2: list[str] = []

    def handler_denied(request: httpx.Request) -> httpx.Response:
        view = request.url.params.get("view")
        views_called_2.append(view or "")
        return httpx.Response(403, json={"error": "Forbidden"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_denied)) as client:
        source = ScopusSource(client=client, sleep=_noop_sleep)
        res_denied = await source.search("genomics", max_results=10)

    assert views_called_2 == ["COMPLETE", "STANDARD"]
    assert res_denied.status == "failed"
    assert res_denied.reason == (
        "o Scopus recusou o acesso: confira se está na rede da instituição "
        "ou configure SCOPUS_INSTTOKEN"
    )


# D-023: Tratamento de erros 401, 429, 5xx, timeout, rede e preservação de páginas já trazidas
@pytest.mark.anyio
async def test_d023_estados_401_429_5xx_timeout_rede_e_paginas_preservadas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCOPUS_API_KEY", "chave-falsa-scopus")

    # 401: failed na hora, sem tentativas adicionais
    calls_401 = 0

    def handler_401(request: httpx.Request) -> httpx.Response:
        nonlocal calls_401
        calls_401 += 1
        return httpx.Response(401, json={"error": "Invalid API Key"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_401)) as client:
        source = ScopusSource(client=client, sleep=_noop_sleep)
        res_401 = await source.search("ai")
    assert calls_401 == 1
    assert res_401.status == "failed"
    assert res_401.reason == "chave do Scopus recusada"

    # 429: rate_limited após 3 tentativas
    calls_429 = 0

    def handler_429(request: httpx.Request) -> httpx.Response:
        nonlocal calls_429
        calls_429 += 1
        return httpx.Response(429, text="Too Many Requests")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_429)) as client:
        source = ScopusSource(client=client, sleep=_noop_sleep)
        res_429 = await source.search("ai")
    assert calls_429 == 4
    assert res_429.status == "rate_limited"
    assert res_429.reason == "HTTP 429 depois de 3 tentativas"

    # 500: failed após 3 tentativas
    calls_500 = 0

    def handler_500(request: httpx.Request) -> httpx.Response:
        nonlocal calls_500
        calls_500 += 1
        return httpx.Response(500, text="Internal Server Error")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_500)) as client:
        source = ScopusSource(client=client, sleep=_noop_sleep)
        res_500 = await source.search("ai")
    assert calls_500 == 4
    assert res_500.status == "failed"
    assert res_500.reason == "HTTP 500 depois de 3 tentativas"

    # 400: failed imediato sem novas tentativas
    calls_400 = 0

    def handler_400(request: httpx.Request) -> httpx.Response:
        nonlocal calls_400
        calls_400 += 1
        return httpx.Response(400, text="Bad Request")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_400)) as client:
        source = ScopusSource(client=client, sleep=_noop_sleep)
        res_400 = await source.search("ai")
    assert calls_400 == 1
    assert res_400.status == "failed"
    assert res_400.reason == "HTTP 400"

    # Timeout: failed após 3 tentativas
    calls_timeout = 0

    def handler_timeout(request: httpx.Request) -> httpx.Response:
        nonlocal calls_timeout
        calls_timeout += 1
        raise httpx.ReadTimeout("Timeout ao ler dados")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_timeout)) as client:
        source = ScopusSource(client=client, sleep=_noop_sleep)
        res_timeout = await source.search("ai")
    assert calls_timeout == 4
    assert res_timeout.status == "failed"
    assert res_timeout.reason == "tempo limite esgotado depois de 3 tentativas"

    # Preservação de páginas já trazidas quando página 2 falha
    def handler_partial(request: httpx.Request) -> httpx.Response:
        start = request.url.params.get("start")
        if start == "0":
            return httpx.Response(
                200,
                json={
                    "search-results": {
                        "opensearch:totalResults": "50",
                        "entry": [
                            {"eid": f"2-s2.0-{i}", "dc:title": f"Artigo {i}"}
                            for i in range(25)
                        ],
                    }
                },
            )
        return httpx.Response(401, text="Key Expired")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_partial)) as client:
        source = ScopusSource(client=client, sleep=_noop_sleep)
        res_partial = await source.search("ai", max_results=50)

    assert res_partial.status == "failed"
    assert res_partial.reason == "chave do Scopus recusada"
    assert res_partial.fetched == 25
    assert len(res_partial.works) == 25


# D-023: Teste de nova tentativa 429 seguida de 200 com sucesso
@pytest.mark.anyio
async def test_d023_retry_429_seguido_de_200_sucesso(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCOPUS_API_KEY", "chave-falsa-scopus")
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, text="Rate limit exceeded")
        return httpx.Response(
            200,
            json={
                "search-results": {
                    "opensearch:totalResults": "1",
                    "entry": [{"eid": "2-s2.0-1", "dc:title": "Artigo Recuperado"}],
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = ScopusSource(client=client, sleep=_noop_sleep)
        res = await source.search("ai", max_results=10)

    assert attempts == 2
    assert res.status == "ok"
    assert res.fetched == 1
    assert len(res.works) == 1
    assert res.works[0].title == "Artigo Recuperado"


# D-023: Credenciais SCOPUS_API_KEY e SCOPUS_INSTTOKEN vão só em cabeçalhos e não vazam
@pytest.mark.anyio
async def test_d023_credenciais_apenas_em_cabecalhos_sem_vazamento(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_key = "chave-falsa-secreta-scopus-12345"
    secret_token = "token-falso-institucional-67890"
    monkeypatch.setenv("SCOPUS_API_KEY", secret_key)
    monkeypatch.setenv("SCOPUS_INSTTOKEN", secret_token)

    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "search-results": {
                    "opensearch:totalResults": "1",
                    "entry": [{"eid": "2-s2.0-100", "dc:title": "Artigo Secreto"}],
                }
            },
        )

    with caplog.at_level(logging.DEBUG):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            source = ScopusSource(client=client, sleep=_noop_sleep)
            res = await source.search("ai", max_results=10)

    assert len(captured_requests) == 1
    req = captured_requests[0]

    # As credenciais estão nos cabeçalhos corretos
    assert req.headers["X-ELS-APIKey"] == secret_key
    assert req.headers["X-ELS-Insttoken"] == secret_token

    # Nenhuma credencial aparece na URL, query, reason, cache_query, repr ou caplog
    assert secret_key not in str(req.url)
    assert secret_token not in str(req.url)

    assert secret_key not in res.query
    assert secret_token not in res.query

    assert secret_key not in (res.reason or "")
    assert secret_token not in (res.reason or "")

    cache_q = source.cache_query("ai", 10)
    assert secret_key not in str(cache_q)
    assert secret_token not in str(cache_q)

    assert secret_key not in repr(source)
    assert secret_token not in repr(source)

    assert secret_key not in caplog.text
    assert secret_token not in caplog.text


# D-023: Sem SCOPUS_API_KEY, responde missing_key sem nenhuma chamada de rede
@pytest.mark.anyio
async def test_d023_sem_scopus_api_key_responde_missing_key_sem_chamada_de_rede() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        pytest.fail("Nenhuma chamada de rede deveria ser feita sem SCOPUS_API_KEY")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = ScopusSource(client=client, sleep=_noop_sleep)
        res = await source.search("cancer")

    assert res.status == "missing_key"
    assert res.reason == "variável SCOPUS_API_KEY não configurada"
    assert res.found is None
    assert res.fetched == 0
    assert res.works == []


# D-023: Busca sem resultado com entrada de erro conta como zero resultados
@pytest.mark.anyio
async def test_d023_resultado_vazio_scopus_com_error_na_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCOPUS_API_KEY", "chave-falsa-scopus")

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "search-results": {
                    "opensearch:totalResults": "0",
                    "entry": [{"error": "Result set was empty"}],
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = ScopusSource(client=client, sleep=_noop_sleep)
        res = await source.search("termo_inexistente_xyz_123")

    assert res.status == "ok"
    assert res.found == 0
    assert res.fetched == 0
    assert res.works == []
