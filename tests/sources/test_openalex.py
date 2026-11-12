"""Testes do conector do OpenAlex com MockTransport (sem rede)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from rslapp.sources.base import Source
from rslapp.sources.openalex import SELECT_FIELDS, OpenAlexSource


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clean_openalex_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)


def _make_raw_work(idx: int, title: str | None = None) -> dict[str, Any]:
    return {
        "id": f"https://openalex.org/W{1000 + idx}",
        "doi": f"https://doi.org/10.1000/WORK.{idx}",
        "display_name": f"Work Title {idx}" if title is None else title,
        "publication_year": 2024,
        "type": "article",
        "primary_location": {"source": {"display_name": "Test Journal"}},
        "authorships": [
            {
                "author_position": "first",
                "is_corresponding": True,
                "author": {
                    "id": f"https://openalex.org/A{2000 + idx}",
                    "display_name": f"Author {idx}",
                    "orcid": "https://orcid.org/0000-0002-1825-0097",
                },
                "institutions": [
                    {
                        "id": "https://openalex.org/I300",
                        "display_name": "Inst",
                        "ror": "https://ror.org/042nb2s44",
                        "country_code": "BR",
                    }
                ],
                "raw_affiliation_strings": ["Inst, Brasil"],
            }
        ],
        "abstract_inverted_index": {"Study": [0], "of": [1], "AI": [2]},
        "keywords": [{"display_name": "ai", "score": 0.9}],
        "referenced_works": ["https://openalex.org/W9001"],
        "referenced_works_count": 1,
        "cited_by_count": 5,
    }


# FR-01, FR-03, FR-14, D-004, D-010: Mapeia campos completos e aceita URL e forma curta
@pytest.mark.anyio
async def test_fr01_fr03_fr14_d004_d010_mapeamento_completo_url_e_forma_curta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
    captured_requests: list[httpx.Request] = []

    payload = {
        "meta": {"count": 2, "per_page": 100, "page": 1},
        "results": [
            {
                "id": "https://openalex.org/W2741809807",
                "doi": "https://doi.org/10.1038/NATURE12373",
                "display_name": "Deep Interpretability",
                "publication_year": 2023,
                "type": "article",
                "primary_location": {
                    "source": {"display_name": "Nature Machine Intelligence"}
                },
                "abstract_inverted_index": {
                    "Interpretability": [0],
                    "in": [1],
                    "deep": [2],
                    "models": [3, 5],
                    "helps": [4],
                },
                "keywords": [
                    {"display_name": "interpretability", "score": 0.98},
                    {"display_name": "explainable ai", "score": 0.85},
                ],
                "authorships": [
                    {
                        "author_position": "first",
                        "is_corresponding": True,
                        "author": {
                            "id": "https://openalex.org/A5023888391",
                            "display_name": "Ana Beatriz",
                            "orcid": "https://orcid.org/0000-0002-1825-0097",
                        },
                        "institutions": [
                            {
                                "id": "https://openalex.org/I17974374",
                                "display_name": "Universidade de São Paulo",
                                "ror": "https://ror.org/036rp1748",
                                "country_code": "BR",
                            }
                        ],
                        "raw_affiliation_strings": ["USP, São Paulo, Brasil"],
                    },
                    {
                        "author_position": "last",
                        "is_corresponding": False,
                        "author": {
                            "id": "A5099999999",
                            "display_name": "Carlos Lima",
                            "orcid": "0000-0001-5555-000X",
                        },
                        "institutions": [
                            {
                                "id": "I136199984",
                                "display_name": "MIT",
                                "ror": "042nb2s44",
                                "country_code": "US",
                            }
                        ],
                        "raw_affiliation_strings": ["MIT, Cambridge, USA"],
                    },
                ],
                "referenced_works": [
                    "https://openalex.org/W2100837269",
                    "W2155555555",
                ],
                "referenced_works_count": 2,
                "cited_by_count": 42,
            },
            {
                "id": "W3000000002",
                "doi": "10.1145/333444.555666",
                "display_name": "Short Identifiers Paper",
                "publication_year": 2024,
                "type": "review",
                "primary_location": {"source": {"display_name": "ACM Computing Surveys"}},
                "abstract_inverted_index": {"Short": [0], "test": [1]},
                "keywords": [],
                "authorships": [],
                "referenced_works": [],
                "referenced_works_count": 0,
                "cited_by_count": 0,
            },
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = OpenAlexSource(client=client)
        assert isinstance(source, Source)
        result = await source.search("machine learning interpretability", max_results=100)

    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.url.params["search"] == "machine learning interpretability"
    assert req.url.params["per_page"] == "100"
    assert req.url.params["page"] == "1"
    assert req.url.params["select"] == SELECT_FIELDS
    assert req.headers["User-Agent"].startswith("rslapp/")

    assert result.name == "openalex"
    assert result.status == "ok"
    assert result.reason is None
    assert result.found == 2
    assert result.fetched == 2
    assert len(result.works) == 2

    w1 = result.works[0]
    assert w1.title == "Deep Interpretability"
    assert w1.doi == "10.1038/nature12373"
    assert w1.year == 2023
    assert w1.type == "article"
    assert w1.venue == "Nature Machine Intelligence"
    assert w1.abstract == "Interpretability in deep models helps models"
    assert w1.keywords == ["interpretability", "explainable ai"]
    assert w1.references == ["W2100837269", "W2155555555"]
    assert w1.references_count == 2
    assert w1.citations == {"openalex": 42}
    assert w1.source_ids == {"openalex": "W2741809807"}

    assert len(w1.authors) == 2
    a1, a2 = w1.authors
    assert a1.name == "Ana Beatriz"
    assert a1.orcid == "0000-0002-1825-0097"
    assert a1.ids == {"openalex": "A5023888391"}
    assert a1.position == "first"
    assert a1.is_corresponding is True
    assert a1.raw_affiliations == ["USP, São Paulo, Brasil"]
    assert len(a1.affiliations) == 1
    assert a1.affiliations[0].name == "Universidade de São Paulo"
    assert a1.affiliations[0].ids == {
        "openalex": "I17974374",
        "ror": "https://ror.org/036rp1748",
    }
    assert a1.affiliations[0].country_code == "BR"

    assert a2.name == "Carlos Lima"
    assert a2.orcid == "0000-0001-5555-000X"
    assert a2.ids == {"openalex": "A5099999999"}
    assert a2.position == "last"
    assert a2.is_corresponding is False
    assert a2.affiliations[0].ids == {
        "openalex": "I136199984",
        "ror": "https://ror.org/042nb2s44",
    }

    w2 = result.works[1]
    assert w2.doi == "10.1145/333444.555666"
    assert w2.source_ids == {"openalex": "W3000000002"}
    assert w2.citations == {"openalex": 0}


# FR-03, FR-14: Trabalho sem título é descartado e campos nulos ficam vazios sem exceção
@pytest.mark.anyio
async def test_fr03_fr14_descarta_sem_titulo_e_aceita_nulos_em_qualquer_nivel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
    payload = {
        "meta": {"count": 4, "per_page": 100, "page": 1},
        "results": [
            {"id": "https://openalex.org/W1", "display_name": None},
            {"id": "https://openalex.org/W2", "display_name": "   "},
            {
                "id": None,
                "doi": None,
                "display_name": "Artigo com Campos Nulos",
                "publication_year": None,
                "type": None,
                "primary_location": None,
                "abstract_inverted_index": None,
                "keywords": [{"score": 0.5}, {"display_name": None}, {"display_name": ""}],
                "authorships": [
                    {
                        "author_position": None,
                        "is_corresponding": None,
                        "author": {
                            "id": None,
                            "display_name": "Autor Sem ORCID",
                            "orcid": None,
                        },
                        "institutions": [],
                        "raw_affiliation_strings": [],
                    }
                ],
                "referenced_works": None,
                "referenced_works_count": None,
                "cited_by_count": None,
            },
            {
                "id": "W4",
                "display_name": "Artigo com Source Nulo",
                "primary_location": {"source": None},
            },
        ],
    }

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload))
    ) as client:
        result = await OpenAlexSource(client=client).search("null fields", max_results=100)

    assert result.status == "ok"
    assert result.found == 4
    assert result.fetched == 2
    assert len(result.works) == 2

    w = result.works[0]
    assert w.title == "Artigo com Campos Nulos"
    assert w.doi is None
    assert w.year is None
    assert w.type is None
    assert w.venue is None
    assert w.abstract is None
    assert w.keywords == []
    assert w.references == []
    assert w.references_count is None
    assert w.citations == {}
    assert w.source_ids == {}
    assert len(w.authors) == 1
    assert w.authors[0].name == "Autor Sem ORCID"
    assert w.authors[0].orcid is None
    assert w.authors[0].ids == {}
    assert w.authors[0].affiliations == []
    assert w.authors[0].raw_affiliations == []
    assert result.works[1].venue is None


# FR-01, NFR-05: Paginação, per_page menor, descartes sem título, meta.count fixo e teto 10.000
@pytest.mark.anyio
async def test_fr01_nfr05_paginacao_max_results_fim_descartes_e_limite_10000(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")

    # 1. max_results=10 pede per_page=10 na URL
    seen_per_page: list[str] = []

    def handler_small(request: httpx.Request) -> httpx.Response:
        seen_per_page.append(request.url.params["per_page"])
        items = [_make_raw_work(i) for i in range(10)]
        return httpx.Response(200, json={"meta": {"count": 50}, "results": items})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_small)) as client:
        res_small = await OpenAlexSource(client=client).search("small", max_results=10)

    assert seen_per_page == ["10"]
    assert res_small.fetched == 10
    assert res_small.query == "search=small · filter=type:!peer-review · per_page=10 · páginas 1-1"

    # 2. Para em max_results (150 -> páginas 1 e 2) e preserva found da primeira página
    pages_called: list[int] = []

    def handler_max(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        pages_called.append(page)
        start = (page - 1) * 100
        items = [_make_raw_work(start + i) for i in range(100)]
        meta_count = 500 if page == 1 else 999
        return httpx.Response(200, json={"meta": {"count": meta_count}, "results": items})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_max)) as client:
        res_max = await OpenAlexSource(client=client).search("paging", max_results=150)

    assert pages_called == [1, 2]
    assert res_max.found == 500
    assert res_max.fetched == 150
    assert len(res_max.works) == 150
    assert res_max.query == "search=paging · filter=type:!peer-review · per_page=100 · páginas 1-2"

    # 3. max_results=100 com 5 sem título na página 1 pede a página 2 para completar 100
    pages_discard: list[int] = []

    def handler_discard(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        pages_discard.append(page)
        start = (page - 1) * 100
        items = [
            _make_raw_work(start + i, title="" if (page == 1 and i < 5) else None)
            for i in range(100)
        ]
        return httpx.Response(200, json={"meta": {"count": 200}, "results": items})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_discard)) as client:
        res_discard = await OpenAlexSource(client=client).search("discard", max_results=100)

    assert pages_discard == [1, 2]
    assert res_discard.fetched == 100
    assert len(res_discard.works) == 100

    # 4. Para no fim do resultado antes de max_results
    pages_end: list[int] = []

    def handler_end(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        pages_end.append(page)
        count = 100 if page == 1 else 20
        start = (page - 1) * 100
        items = [_make_raw_work(start + i) for i in range(count)]
        return httpx.Response(200, json={"meta": {"count": 120}, "results": items})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_end)) as client:
        res_end = await OpenAlexSource(client=client).search("end", max_results=300)

    assert pages_end == [1, 2]
    assert res_end.fetched == 120

    # 5. Para nos 10.000 resultados mesmo se max_results for maior
    pages_10k: list[int] = []

    def handler_10k(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        pages_10k.append(page)
        start = (page - 1) * 100
        items = [_make_raw_work(start + i) for i in range(100)]
        return httpx.Response(200, json={"meta": {"count": 50000}, "results": items})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_10k)) as client:
        res_10k = await OpenAlexSource(client=client).search("ten_k", max_results=10500)

    assert len(pages_10k) == 100
    assert pages_10k[0] == 1 and pages_10k[-1] == 100
    assert res_10k.fetched == 10000
    assert res_10k.query == "search=ten_k · filter=type:!peer-review · per_page=100 · páginas 1-100"

    # 6. Se a segunda página falha, preserva os trabalhos já trazidos na primeira
    def handler_partial(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        if page == 1:
            return httpx.Response(
                200,
                json={
                    "meta": {"count": 300},
                    "results": [_make_raw_work(i) for i in range(100)],
                },
            )
        return httpx.Response(400, json={"error": "bad_request"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_partial)) as client:
        res_partial = await OpenAlexSource(client=client).search("partial", max_results=200)

    assert res_partial.status == "failed"
    assert res_partial.reason == "HTTP 400"
    assert res_partial.found == 300
    assert res_partial.fetched == 100
    assert len(res_partial.works) == 100


# NFR-01, NFR-04, NFR-05: Novas tentativas [1, 2, 4] em 429, 5xx, timeout e erro de rede
@pytest.mark.anyio
@pytest.mark.parametrize(
    ("action", "expected_status", "expected_reason"),
    [
        (
            lambda req: httpx.Response(429, json={"error": "rate_limit_exceeded"}),
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
                httpx.ReadTimeout("detalhe timeout Bearer fake-key-123", request=req)
            ),
            "failed",
            "tempo limite esgotado depois de 3 tentativas",
        ),
        (
            lambda req: (_ for _ in ()).throw(
                httpx.ConnectError("detalhe rede Bearer fake-key-123", request=req)
            ),
            "failed",
            "erro de rede depois de 3 tentativas",
        ),
    ],
)
async def test_nfr01_nfr04_nfr05_retries_429_5xx_timeout_e_rede(
    monkeypatch: pytest.MonkeyPatch,
    action: Callable[[httpx.Request], httpx.Response],
    expected_status: str,
    expected_reason: str,
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
    sleeps: list[float] = []
    calls = 0

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return action(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        res = await OpenAlexSource(client=client, sleep=fake_sleep).search("q")

    assert calls == 4
    assert sleeps == [1, 2, 4]
    assert res.status == expected_status
    assert res.reason == expected_reason
    assert "fake-key-123" not in (res.reason or "")
    assert "detalhe" not in (res.reason or "")


# NFR-01, NFR-04, NFR-05: Erros sem repetição (cota diária, chave não ativada, JSON inválido)
@pytest.mark.anyio
@pytest.mark.parametrize(
    ("response", "expected_status", "expected_reason"),
    [
        (
            httpx.Response(429, json={"error": "not_enough_credits"}),
            "rate_limited",
            "créditos diários do OpenAlex esgotados",
        ),
        (
            httpx.Response(403, json={"error": "key_not_activated"}),
            "failed",
            "a chave do OpenAlex ainda não foi ativada pelo link do e-mail",
        ),
        (
            httpx.Response(200, text="<html>not json</html>"),
            "failed",
            "resposta JSON inválida do OpenAlex",
        ),
        (
            httpx.Response(200, json=[{"id": "W1"}]),
            "failed",
            "resposta JSON inválida do OpenAlex",
        ),
    ],
)
async def test_nfr01_nfr04_nfr05_erros_sem_repeticao_e_json_invalido(
    monkeypatch: pytest.MonkeyPatch,
    response: httpx.Response,
    expected_status: str,
    expected_reason: str,
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
    sleeps: list[float] = []
    calls = 0

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return response

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        res = await OpenAlexSource(client=client, sleep=fake_sleep).search("q")

    assert calls == 1
    assert sleeps == []
    assert res.status == expected_status
    assert res.reason == expected_reason


# FR-07, NFR-03: Sem OPENALEX_API_KEY devolve missing_key sem chamar a API
@pytest.mark.anyio
async def test_fr07_nfr03_sem_chave_devolve_missing_key_sem_chamar_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={"meta": {"count": 0}, "results": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = OpenAlexSource(client=client)
        res_unset = await source.search("machine learning", max_results=50)
        monkeypatch.setenv("OPENALEX_API_KEY", "   ")
        res_blank = await source.search("machine learning", max_results=50)

    assert called is False
    assert res_unset.status == "missing_key"
    assert res_unset.fetched == 0
    assert res_blank.status == "missing_key"


# NFR-03: Chave no cabeçalho, validação contra caracteres inválidos e proteção contra exceções
@pytest.mark.anyio
async def test_nfr03_chave_vai_no_cabecalho_e_nao_vaza_em_url_query_reason_repr_ou_caplog(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_key = "fake-key-123"
    monkeypatch.setenv("OPENALEX_API_KEY", secret_key)
    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        if request.url.params.get("search") == "erro":
            return httpx.Response(401, json={"error": "unauthorized"})
        if request.url.params.get("search") == "excecao":
            raise RuntimeError(f"boom Bearer {secret_key}")
        return httpx.Response(
            200,
            json={"meta": {"count": 1}, "results": [_make_raw_work(1)]},
        )

    with caplog.at_level(logging.DEBUG):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            source = OpenAlexSource(client=client)
            res_ok = await source.search("seguranca", max_results=10)
            res_err = await source.search("erro", max_results=10)
            res_exc = await source.search("excecao", max_results=10)
            cache_q = source.cache_query("seguranca", max_results=10)
            source_repr = repr(source)

            for bad_key in ("chave-çé-123", "chave-\u200b-123", "chave com espaco"):
                monkeypatch.setenv("OPENALEX_API_KEY", bad_key)
                res_bad = await source.search("seguranca", max_results=10)
                assert res_bad.status == "failed"
                assert res_bad.reason == "OPENALEX_API_KEY tem caracteres inválidos"
                assert bad_key not in (res_bad.reason or "")
                assert bad_key not in res_bad.query
                assert bad_key not in caplog.text

    assert len(seen_requests) == 3
    for req in seen_requests:
        assert req.headers["Authorization"] == f"Bearer {secret_key}"
        assert secret_key not in str(req.url)
        assert "api_key" not in str(req.url).lower()

    assert res_exc.status == "failed"
    assert res_exc.reason == "falha inesperada ao consultar o OpenAlex"
    assert "boom" not in (res_exc.reason or "")

    for surface in (
        res_ok.query,
        str(res_ok.reason),
        str(res_ok.to_dict()),
        res_err.query,
        str(res_err.reason),
        str(res_err.to_dict()),
        res_exc.query,
        str(res_exc.reason),
        str(res_exc.to_dict()),
        str(cache_q),
        source_repr,
        caplog.text,
    ):
        assert secret_key not in surface
