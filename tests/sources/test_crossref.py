"""Testes do conector da Crossref com MockTransport (sem rede)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from rslapp.sources.base import Source
from rslapp.sources.crossref import CrossrefSource


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clean_crossref_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RSL_CONTACT_EMAIL", raising=False)


def _make_raw_work(idx: int, title: str | None = None) -> dict[str, Any]:
    work_title = f"Crossref Work {idx}" if title is None else title
    return {
        "DOI": f"10.1000/CROSSREF.{idx}",
        "title": [work_title] if work_title else [],
        "issued": {"date-parts": [[2024, 3, 15]]},
        "container-title": ["Journal of Systematic Reviews"],
        "type": "journal-article",
        "abstract": f"<jats:p>Abstract of work {idx}.</jats:p>",
        "author": [
            {
                "given": "Autor",
                "family": f"Sobrenome {idx}",
                "ORCID": "https://orcid.org/0000-0002-1825-0097",
                "sequence": "first",
                "affiliation": [
                    {
                        "name": "Universidade Teste",
                        "id": [{"id": "https://ror.org/036rp1748", "id-type": "ROR"}],
                    }
                ],
            }
        ],
        "reference": [{"key": "r1", "DOI": "10.1000/REF.1"}],
        "references-count": 1,
        "is-referenced-by-count": 7,
    }


# FR-01, FR-03, FR-14, D-004: Mapeia campos completos, organização, ORCID, ROR, JATS e nulos
@pytest.mark.anyio
async def test_fr01_fr03_fr14_d004_mapeamento_completo_autores_ror_jats_e_nulos() -> None:
    captured_requests: list[httpx.Request] = []

    payload = {
        "status": "ok",
        "message-type": "work-list",
        "message": {
            "total-results": 6,
            "items-per-page": 100,
            "next-cursor": "cur-next",
            "items": [
                {
                    "DOI": "https://doi.org/10.1038/S41586-024-00001-X",
                    "title": ["Systematic Reviews with Graph Networks", "Ignored Subtitle"],
                    "issued": {"date-parts": [[2024, 5, 10]]},
                    "container-title": ["Nature", "Nature Weekly"],
                    "type": "journal-article",
                    "subject": ["Computer Science", "Information Systems"],
                    "abstract": (
                        "<jats:title>Abstract</jats:title>"
                        "<jats:p>We analyze <jats:italic>citation</jats:italic> networks,\n"
                        "   and   <jats:bold>bibliometrics</jats:bold>.</jats:p>"
                    ),
                    "author": [
                        {
                            "given": "Ana",
                            "family": "Beatriz",
                            "ORCID": "https://orcid.org/0000-0002-1825-0097",
                            "sequence": "first",
                            "affiliation": [
                                {
                                    "name": "Universidade de São Paulo",
                                    "id": [
                                        {
                                            "id": "https://ror.org/036rp1748",
                                            "id-type": "ROR",
                                            "asserted-by": "publisher",
                                        }
                                    ],
                                },
                                {"name": "Instituto de Matemática e Estatística"},
                            ],
                        },
                        {
                            "family": "Aristotle",
                            "ORCID": "http://orcid.org/0000-0001-5555-000x",
                            "sequence": "additional",
                            "affiliation": [
                                {
                                    "name": "MIT",
                                    "id": {"id": "042nb2s44", "id-type": "ROR"},
                                },
                                {
                                    "name": "Outro Instituto",
                                    "id": [{"id": "grid.1234.5", "id-type": "GRID"}],
                                },
                            ],
                        },
                        {
                            "name": "World Health Organization",
                            "sequence": "additional",
                        },
                    ],
                    "reference": [
                        {"key": "ref1", "DOI": "10.1000/REF.ONE"},
                        {"key": "ref2", "unstructured": "Reference without DOI"},
                        {"key": "ref3", "DOI": "https://doi.org/10.1000/REF.THREE"},
                    ],
                    "references-count": 25,
                    "is-referenced-by-count": 12,
                },
                {
                    "DOI": "10.1000/SEM-TITULO-1",
                    "title": [],
                },
                {
                    "DOI": "10.1000/SEM-TITULO-2",
                    "title": ["   "],
                },
                {
                    "title": ["Artigo com Issued Null e Campos Vazios"],
                    "issued": {"date-parts": [[None]]},
                },
                {
                    "DOI": "10.1000/ENTITIES-AND-JATS",
                    "title": ["Artigo com Entidades HTML e JATS"],
                    "abstract": "<jats:p>p &lt; 0.05 &amp; x</jats:p>",
                },
                {
                    "DOI": "10.1000/PLAIN-TEXT-INEQUALITIES",
                    "title": ["Artigo com Texto Puro e Desigualdades"],
                    "abstract": "effect p<0.05 when n>30 observed",
                },
            ],
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = CrossrefSource(client=client)
        assert isinstance(source, Source)
        assert source.name == "crossref"
        assert source.needs_key is False
        result = await source.search("graph networks", max_results=100)

    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.url.params["query"] == "graph networks"
    assert req.url.params["rows"] == "100"
    assert (
        req.url.params["select"]
        == "DOI,title,author,issued,container-title,abstract,reference,references-count,is-referenced-by-count,type"
    )
    assert req.url.params["cursor"] == "*"
    assert "mailto" not in req.url.params
    assert req.headers["User-Agent"].startswith("rslapp/")

    assert result.name == "crossref"
    assert result.status == "ok"
    assert result.reason is None
    assert result.found == 6
    assert result.fetched == 4
    assert len(result.works) == 4

    w1 = result.works[0]
    assert w1.title == "Systematic Reviews with Graph Networks"
    assert w1.doi == "10.1038/s41586-024-00001-x"
    assert w1.year == 2024
    assert w1.type == "journal-article"
    assert w1.venue == "Nature"
    assert w1.abstract == "Abstract We analyze citation networks, and bibliometrics."
    assert w1.keywords == []
    assert w1.references == ["10.1000/ref.one", "10.1000/ref.three"]
    assert w1.references_count == 25
    assert w1.citations == {"crossref": 12}
    assert w1.source_ids == {"crossref": "10.1038/s41586-024-00001-x"}

    assert len(w1.authors) == 3
    a1, a2, a3 = w1.authors
    assert a1.name == "Ana Beatriz"
    assert a1.orcid == "0000-0002-1825-0097"
    assert a1.ids == {}
    assert a1.position == "first"
    assert a1.is_corresponding is None
    assert a1.raw_affiliations == []
    assert len(a1.affiliations) == 2
    assert a1.affiliations[0].name == "Universidade de São Paulo"
    assert a1.affiliations[0].ids == {"ror": "https://ror.org/036rp1748"}
    assert a1.affiliations[0].country_code is None
    assert a1.affiliations[1].name == "Instituto de Matemática e Estatística"
    assert a1.affiliations[1].ids == {}

    assert a2.name == "Aristotle"
    assert a2.orcid == "0000-0001-5555-000X"
    assert a2.position == "additional"
    assert len(a2.affiliations) == 2
    assert a2.affiliations[0].name == "MIT"
    assert a2.affiliations[0].ids == {"ror": "https://ror.org/042nb2s44"}
    assert a2.affiliations[1].name == "Outro Instituto"
    assert a2.affiliations[1].ids == {}

    assert a3.name == "World Health Organization"
    assert a3.orcid is None
    assert a3.position == "additional"
    assert a3.affiliations == []

    w2 = result.works[1]
    assert w2.title == "Artigo com Issued Null e Campos Vazios"
    assert w2.doi is None
    assert w2.year is None
    assert w2.type is None
    assert w2.venue is None
    assert w2.abstract is None
    assert w2.keywords == []
    assert w2.authors == []
    assert w2.references == []
    assert w2.references_count is None
    assert w2.citations == {}
    assert w2.source_ids == {}

    w3 = result.works[2]
    assert w3.title == "Artigo com Entidades HTML e JATS"
    assert w3.abstract == "p < 0.05 & x"

    w4 = result.works[3]
    assert w4.title == "Artigo com Texto Puro e Desigualdades"
    assert w4.abstract == "effect p<0.05 when n>30 observed"


# FR-01, NFR-04: Paginação por cursor (next-cursor, max_results, descartes e página menor que rows)
@pytest.mark.anyio
async def test_fr01_nfr04_paginacao_cursor_max_results_descartes_e_pagina_menor() -> None:
    # 1. max_results=10 envia rows=10 e cursor=*
    seen_rows: list[str] = []

    def handler_small(request: httpx.Request) -> httpx.Response:
        seen_rows.append(request.url.params["rows"])
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "message": {
                    "total-results": 50,
                    "next-cursor": "cur-2",
                    "items": [_make_raw_work(i) for i in range(10)],
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_small)) as client:
        res_small = await CrossrefSource(client=client).search("small", max_results=10)

    assert seen_rows == ["10"]
    assert res_small.fetched == 10
    assert res_small.query == "query=small · rows=10 · páginas 1-1"

    # 2. Paginação com next-cursor até max_results=150 e preserva found da primeira página
    cursors_seen: list[str] = []

    def handler_max(request: httpx.Request) -> httpx.Response:
        cur = request.url.params["cursor"]
        cursors_seen.append(cur)
        page_idx = len(cursors_seen)
        start = (page_idx - 1) * 100
        total = 500 if page_idx == 1 else 999
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "message": {
                    "total-results": total,
                    "next-cursor": f"cur-{page_idx + 1}",
                    "items": [_make_raw_work(start + i) for i in range(100)],
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_max)) as client:
        res_max = await CrossrefSource(client=client).search("paging", max_results=150)

    assert cursors_seen == ["*", "cur-2"]
    assert res_max.found == 500
    assert res_max.fetched == 150
    assert len(res_max.works) == 150
    assert res_max.query == "query=paging · rows=100 · páginas 1-2"

    # 3. max_results=100 com 5 itens sem título na página 1 pede a página 2 com next-cursor
    cursors_discard: list[str] = []

    def handler_discard(request: httpx.Request) -> httpx.Response:
        cur = request.url.params["cursor"]
        cursors_discard.append(cur)
        page_idx = len(cursors_discard)
        start = (page_idx - 1) * 100
        items = [
            _make_raw_work(start + i, title="" if (page_idx == 1 and i < 5) else None)
            for i in range(100)
        ]
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "message": {
                    "total-results": 200,
                    "next-cursor": f"cur-d-{page_idx + 1}",
                    "items": items,
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_discard)) as client:
        res_discard = await CrossrefSource(client=client).search("discard", max_results=100)

    assert cursors_discard == ["*", "cur-d-2"]
    assert res_discard.fetched == 100
    assert len(res_discard.works) == 100

    # 4. Para quando a página vem com menos itens que rows, mesmo com next-cursor presente
    cursors_short: list[str] = []

    def handler_short(request: httpx.Request) -> httpx.Response:
        cur = request.url.params["cursor"]
        cursors_short.append(cur)
        count = 100 if cur == "*" else 35
        start = 0 if cur == "*" else 100
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "message": {
                    "total-results": 135,
                    "next-cursor": "cur-next-unused" if cur != "*" else "cur-2",
                    "items": [_make_raw_work(start + i) for i in range(count)],
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_short)) as client:
        res_short = await CrossrefSource(client=client).search("short", max_results=300)

    assert cursors_short == ["*", "cur-2"]
    assert res_short.fetched == 135
    assert len(res_short.works) == 135

    # 5. Se a segunda página falha, preserva as páginas já trazidas
    def handler_partial(request: httpx.Request) -> httpx.Response:
        if request.url.params["cursor"] == "*":
            return httpx.Response(
                200,
                json={
                    "status": "ok",
                    "message": {
                        "total-results": 250,
                        "next-cursor": "cur-2",
                        "items": [_make_raw_work(i) for i in range(100)],
                    },
                },
            )
        return httpx.Response(400, json={"status": "error"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_partial)) as client:
        res_partial = await CrossrefSource(client=client).search("partial", max_results=200)

    assert res_partial.status == "failed"
    assert res_partial.reason == "HTTP 400"
    assert res_partial.found == 250
    assert res_partial.fetched == 100
    assert len(res_partial.works) == 100


# NFR-04: Novas tentativas [1, 2, 4] em 429, 5xx, timeout e erro de rede
@pytest.mark.anyio
@pytest.mark.parametrize(
    ("action", "expected_status", "expected_reason"),
    [
        (
            lambda req: httpx.Response(429, text="Too Many Requests"),
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
                httpx.ReadTimeout("detalhe timeout mailto=segredo@usp.br", request=req)
            ),
            "failed",
            "tempo limite esgotado depois de 3 tentativas",
        ),
        (
            lambda req: (_ for _ in ()).throw(
                httpx.ConnectError("detalhe rede mailto=segredo@usp.br", request=req)
            ),
            "failed",
            "erro de rede depois de 3 tentativas",
        ),
    ],
)
async def test_nfr04_retries_429_5xx_timeout_e_rede(
    action: Callable[[httpx.Request], httpx.Response],
    expected_status: str,
    expected_reason: str,
) -> None:
    sleeps: list[float] = []
    calls = 0

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return action(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        res = await CrossrefSource(client=client, sleep=fake_sleep).search("q")

    assert calls == 4
    assert sleeps == [1, 2, 4]
    assert res.status == expected_status
    assert res.reason == expected_reason
    assert "segredo@usp.br" not in (res.reason or "")
    assert "detalhe" not in (res.reason or "")


# NFR-04: Erros sem repetição (4xx diferente de 429 e JSON inválido)
@pytest.mark.anyio
@pytest.mark.parametrize(
    ("response", "expected_status", "expected_reason"),
    [
        (
            httpx.Response(403, text="Forbidden"),
            "failed",
            "HTTP 403",
        ),
        (
            httpx.Response(400, text="Bad Request"),
            "failed",
            "HTTP 400",
        ),
        (
            httpx.Response(200, text="<html>not json</html>"),
            "failed",
            "resposta JSON inválida da Crossref",
        ),
        (
            httpx.Response(200, json=[{"DOI": "10.1000/1"}]),
            "failed",
            "resposta JSON inválida da Crossref",
        ),
        (
            httpx.Response(200, json={"status": "ok", "message": "invalido"}),
            "failed",
            "resposta JSON inválida da Crossref",
        ),
    ],
)
async def test_nfr04_erros_sem_repeticao_4xx_e_json_invalido(
    response: httpx.Response,
    expected_status: str,
    expected_reason: str,
) -> None:
    sleeps: list[float] = []
    calls = 0

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return response

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        res = await CrossrefSource(client=client, sleep=fake_sleep).search("q")

    assert calls == 1
    assert sleeps == []
    assert res.status == expected_status
    assert res.reason == expected_reason


# NFR-04: Com RSL_CONTACT_EMAIL, mailto vai na URL e não aparece em query, reason, cache nem User-Agent
@pytest.mark.anyio
async def test_nfr04_rsl_contact_email_vai_em_mailto_e_nao_vaza_em_query_reason_ou_cache(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    email = "pesquisador@universidade.br"
    monkeypatch.setenv("RSL_CONTACT_EMAIL", f"  {email}  ")
    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        q = request.url.params.get("query")
        if q == "erro":
            return httpx.Response(403, text=f"Forbidden for {email}")
        if q == "excecao":
            raise RuntimeError(f"boom mailto={email}")
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "message": {
                    "total-results": 1,
                    "next-cursor": "cur-2",
                    "items": [_make_raw_work(1)],
                },
            },
        )

    with caplog.at_level(logging.DEBUG):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            source = CrossrefSource(client=client)
            res_ok = await source.search("bibliometria", max_results=10)
            res_err = await source.search("erro", max_results=10)
            res_exc = await source.search("excecao", max_results=10)
            cache_q = source.cache_query("bibliometria", max_results=10)
            source_repr = repr(source)

    assert len(seen_requests) == 3
    for req in seen_requests:
        assert req.url.params["mailto"] == email
        assert req.headers["User-Agent"].startswith("rslapp/")
        assert email not in req.headers["User-Agent"]

    assert res_ok.status == "ok"
    assert res_err.status == "failed"
    assert res_err.reason == "HTTP 403"
    assert res_exc.status == "failed"
    assert res_exc.reason == "falha inesperada ao consultar a Crossref"

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
    ):
        assert email not in surface
        assert "mailto" not in surface.lower()

    rslapp_logs = [rec.getMessage() for rec in caplog.records if rec.name.startswith("rslapp")]
    for log_msg in rslapp_logs:
        assert email not in log_msg
        assert "mailto" not in log_msg.lower()


# FR-03: Limpeza de resumo JATS/XML, entidades HTML e preservação de texto puro com < e >
@pytest.mark.parametrize(
    ("raw_abstract", "expected"),
    [
        ("<jats:p>p &lt; 0.05 &amp; x</jats:p>", "p < 0.05 & x"),
        ("effect p<0.05 when n>30 observed", "effect p<0.05 when n>30 observed"),
        (
            "<jats:title>Abstract</jats:title><jats:p>p &lt; 0.01 &amp; q &gt; 2</jats:p>",
            "Abstract p < 0.01 & q > 2",
        ),
        (None, None),
        ("", None),
        ("   ", None),
    ],
)
def test_fr03_clean_abstract_entidades_e_comparacoes(
    raw_abstract: Any, expected: str | None
) -> None:
    from rslapp.sources.crossref import _clean_abstract

    assert _clean_abstract(raw_abstract) == expected
