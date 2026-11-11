"""Testes do conector do Europe PMC com MockTransport (sem rede)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from rslapp.sources.base import Source
from rslapp.sources.europe_pmc import EuropePMCSource, EuropePmcSource


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clean_europe_pmc_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RSL_CONTACT_EMAIL", raising=False)


def _make_raw_work(idx: int, title: str | None = None) -> dict[str, Any]:
    work_title = f"Europe PMC Work {idx}." if title is None else title
    res: dict[str, Any] = {
        "id": f"33510{idx:03d}",
        "source": "MED",
        "pmid": f"33510{idx:03d}",
        "doi": f"10.1000/EPMC.{idx}",
        "pubYear": "2024",
        "journalInfo": {"journal": {"title": "Journal of Medical Research"}},
        "pubTypeList": {"pubType": ["Journal Article"]},
        "abstractText": f"<p>Abstract of work {idx}.</p>",
        "authorList": {
            "author": [
                {
                    "fullName": f"Author {idx}",
                    "authorId": {"type": "ORCID", "value": "0000-0002-1825-0097"},
                    "authorAffiliationDetailsList": {
                        "authorAffiliation": [{"affiliation": "Medical School"}]
                    },
                }
            ]
        },
        "citedByCount": 5,
    }
    if work_title is not None:
        res["title"] = work_title
    return res


# FR-01, FR-03, FR-14, D-004, D-020: Mapeamento completo, autor sem ORCID, coletivo, afiliações, HTML, nulos e PPR
@pytest.mark.anyio
async def test_fr01_fr03_fr14_d004_d020_mapeamento_completo_autores_html_afiliacoes_e_nulos() -> None:
    captured_requests: list[httpx.Request] = []

    payload = {
        "hitCount": 7,
        "nextCursorMark": "cur-next",
        "resultList": {
            "result": [
                {
                    "id": "33510057",
                    "source": "MED",
                    "pmid": "33510057",
                    "doi": "https://doi.org/10.1038/S41586-024-00001-X",
                    "title": "Systematic Reviews of Genomics in Healthcare.",
                    "pubYear": "2024",
                    "journalInfo": {"journal": {"title": "Nature Medicine"}},
                    "pubTypeList": {"pubType": ["Journal Article", "Research Support"]},
                    "keywordList": {
                        "keyword": ["Genomics", "Healthcare", "genomics", "  AI  "]
                    },
                    "abstractText": (
                        "<jats:title>Abstract</jats:title>"
                        "<p>We analyze <b>genomic</b> networks &amp; healthcare.</p>"
                    ),
                    "authorList": {
                        "author": [
                            {
                                "fullName": "Ana Beatriz",
                                "authorId": [
                                    {"type": "ORCID", "value": "https://orcid.org/0000-0002-1825-0097"}
                                ],
                                "authorAffiliationDetailsList": {
                                    "authorAffiliation": [
                                        {"affiliation": "Universidade de São Paulo"},
                                        {"affiliation": "Hospital das Clínicas"},
                                    ]
                                },
                            },
                            {
                                "firstName": "John",
                                "lastName": "Doe",
                                "authorAffiliationDetailsList": {
                                    "authorAffiliation": {"affiliation": "Harvard Medical School"}
                                },
                            },
                            {
                                "collectiveName": "COVID-19 Genomics UK (COG-UK) Consortium",
                            },
                        ]
                    },
                    "citedByCount": 42,
                },
                {
                    "id": "PPR123456",
                    "source": "PPR",
                    "doi": "10.1101/2024.01.01.123456",
                    "title": "Preprint on Genomic Variants in Viral Lineages.",
                    "pubYear": "2024",
                    "pubTypeList": {"pubType": ["Preprint"]},
                    "abstractText": "Preprint abstract text without HTML.",
                },
                {
                    "id": "SEM-TITULO-1",
                    "source": "MED",
                    "title": "",
                },
                {
                    "id": "SEM-TITULO-2",
                    "source": "MED",
                    "title": "   .   ",
                },
                {
                    "id": "SEM-ANO-E-CAMPOS-VAZIOS",
                    "source": "MED",
                    "title": "Artigo sem Ano e com Campos Vazios",
                    "pubYear": "in press",
                },
                {
                    "id": "HTML-NO-TITULO-E-RESUMO",
                    "source": "MED",
                    "doi": "10.1000/ENTITIES-AND-HTML",
                    "title": "<i>Effects of</i> <b>Drug X</b> on Cells.",
                    "abstractText": "p &lt; 0.05 &amp; n &gt; 30 observed",
                },
            ]
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = EuropePMCSource(client=client)
        assert isinstance(source, Source)
        assert source.name == "europe_pmc"
        assert source.needs_key is False
        assert EuropePmcSource is EuropePMCSource
        result = await source.search("genomics healthcare", max_results=100)

    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.url.params["query"] == "genomics healthcare"
    assert req.url.params["resultType"] == "core"
    assert req.url.params["format"] == "json"
    assert req.url.params["pageSize"] == "100"
    assert req.url.params["cursorMark"] == "*"
    assert "email" not in req.url.params
    assert req.headers["User-Agent"].startswith("rslapp/")

    assert result.name == "europe_pmc"
    assert result.status == "ok"
    assert result.reason is None
    assert result.found == 7
    assert result.fetched == 4
    assert len(result.works) == 4

    # 1. Artigo completo do MED / PubMed
    w1 = result.works[0]
    assert w1.title == "Systematic Reviews of Genomics in Healthcare"
    assert w1.doi == "10.1038/s41586-024-00001-x"
    assert w1.year == 2024
    assert w1.type == "journal article"
    assert w1.venue == "Nature Medicine"
    assert w1.abstract == "Abstract We analyze genomic networks & healthcare."
    assert w1.keywords == ["Genomics", "Healthcare", "AI"]
    assert w1.references == []
    assert w1.references_count is None
    assert w1.citations == {"europe_pmc": 42}
    assert w1.source_ids == {
        "europe_pmc": "MED:33510057",
        "pubmed": "33510057",
    }

    assert len(w1.authors) == 3
    a1, a2, a3 = w1.authors
    assert a1.name == "Ana Beatriz"
    assert a1.orcid == "0000-0002-1825-0097"
    assert a1.position is None
    assert a1.is_corresponding is None
    assert a1.raw_affiliations == [
        "Universidade de São Paulo",
        "Hospital das Clínicas",
    ]
    assert len(a1.affiliations) == 2
    assert a1.affiliations[0].name == "Universidade de São Paulo"
    assert a1.affiliations[1].name == "Hospital das Clínicas"

    assert a2.name == "John Doe"
    assert a2.orcid is None
    assert a2.position is None
    assert a2.raw_affiliations == ["Harvard Medical School"]
    assert len(a2.affiliations) == 1
    assert a2.affiliations[0].name == "Harvard Medical School"

    assert a3.name == "COVID-19 Genomics UK (COG-UK) Consortium"
    assert a3.orcid is None
    assert a3.position is None
    assert a3.affiliations == []
    assert a3.raw_affiliations == []

    # 2. Preprint (source PPR)
    w2 = result.works[1]
    assert w2.title == "Preprint on Genomic Variants in Viral Lineages"
    assert w2.doi == "10.1101/2024.01.01.123456"
    assert w2.year == 2024
    assert w2.type == "preprint"
    assert w2.venue is None
    assert w2.abstract == "Preprint abstract text without HTML."
    assert w2.keywords == []
    assert w2.authors == []
    assert w2.references == []
    assert w2.references_count is None
    assert w2.citations == {}
    assert w2.source_ids == {"europe_pmc": "PPR:PPR123456"}

    # 3. Artigo com ano não numérico e campos nulos
    w3 = result.works[2]
    assert w3.title == "Artigo sem Ano e com Campos Vazios"
    assert w3.doi is None
    assert w3.year is None
    assert w3.type is None
    assert w3.venue is None
    assert w3.abstract is None
    assert w3.source_ids == {"europe_pmc": "MED:SEM-ANO-E-CAMPOS-VAZIOS"}

    # 4. Artigo com HTML no título e entidades no abstract
    w4 = result.works[3]
    assert w4.title == "Effects of Drug X on Cells"
    assert w4.abstract == "p < 0.05 & n > 30 observed"


# FR-01, NFR-04, D-020: Paginação por cursorMark, parada em max_results, página menor e cursor repetido
@pytest.mark.anyio
async def test_fr01_nfr04_d020_paginacao_cursor_max_results_descartes_e_cursor_repetido() -> None:
    # 1. max_results=10 envia pageSize=10 e cursorMark=*
    seen_sizes: list[str] = []

    def handler_small(request: httpx.Request) -> httpx.Response:
        seen_sizes.append(request.url.params["pageSize"])
        return httpx.Response(
            200,
            json={
                "hitCount": 50,
                "nextCursorMark": "cur-2",
                "resultList": {"result": [_make_raw_work(i) for i in range(10)]},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_small)) as client:
        res_small = await EuropePMCSource(client=client).search("small", max_results=10)

    assert seen_sizes == ["10"]
    assert res_small.fetched == 10
    assert res_small.query == "query=small · pageSize=10 · páginas 1-1"

    # 2. Paginação com nextCursorMark até max_results=150 preservando found
    cursors_seen: list[str] = []

    def handler_max(request: httpx.Request) -> httpx.Response:
        cur = request.url.params["cursorMark"]
        cursors_seen.append(cur)
        page_idx = len(cursors_seen)
        start = (page_idx - 1) * 100
        total = 500 if page_idx == 1 else 999
        return httpx.Response(
            200,
            json={
                "hitCount": total,
                "nextCursorMark": f"cur-{page_idx + 1}",
                "resultList": {"result": [_make_raw_work(start + i) for i in range(100)]},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_max)) as client:
        res_max = await EuropePMCSource(client=client).search("paging", max_results=150)

    assert cursors_seen == ["*", "cur-2"]
    assert res_max.found == 500
    assert res_max.fetched == 150
    assert len(res_max.works) == 150
    assert res_max.query == "query=paging · pageSize=100 · páginas 1-2"

    # 3. max_results=100 com 5 itens sem título na página 1 pede a página 2
    cursors_discard: list[str] = []

    def handler_discard(request: httpx.Request) -> httpx.Response:
        cur = request.url.params["cursorMark"]
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
                "hitCount": 200,
                "nextCursorMark": f"cur-d-{page_idx + 1}",
                "resultList": {"result": items},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_discard)) as client:
        res_discard = await EuropePMCSource(client=client).search("discard", max_results=100)

    assert cursors_discard == ["*", "cur-d-2"]
    assert res_discard.fetched == 100
    assert len(res_discard.works) == 100

    # 4. Para quando a página vem com menos itens que pageSize
    cursors_short: list[str] = []

    def handler_short(request: httpx.Request) -> httpx.Response:
        cur = request.url.params["cursorMark"]
        cursors_short.append(cur)
        count = 100 if cur == "*" else 35
        start = 0 if cur == "*" else 100
        return httpx.Response(
            200,
            json={
                "hitCount": 135,
                "nextCursorMark": "cur-next-unused" if cur != "*" else "cur-2",
                "resultList": {"result": [_make_raw_work(start + i) for i in range(count)]},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_short)) as client:
        res_short = await EuropePMCSource(client=client).search("short", max_results=300)

    assert cursors_short == ["*", "cur-2"]
    assert res_short.fetched == 135
    assert len(res_short.works) == 135

    # 5. Para quando nextCursorMark é igual ao cursor anterior (cursor repetido)
    cursors_repeat: list[str] = []

    def handler_repeat(request: httpx.Request) -> httpx.Response:
        cur = request.url.params["cursorMark"]
        cursors_repeat.append(cur)
        return httpx.Response(
            200,
            json={
                "hitCount": 200,
                "nextCursorMark": cur,
                "resultList": {"result": [_make_raw_work(i) for i in range(100)]},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_repeat)) as client:
        res_repeat = await EuropePMCSource(client=client).search("repeat", max_results=300)

    assert cursors_repeat == ["*"]
    assert res_repeat.fetched == 100

    # 6. Para quando nextCursorMark está ausente ou vazio
    cursors_none: list[str] = []

    def handler_none(request: httpx.Request) -> httpx.Response:
        cur = request.url.params["cursorMark"]
        cursors_none.append(cur)
        return httpx.Response(
            200,
            json={
                "hitCount": 200,
                "nextCursorMark": None,
                "resultList": {"result": [_make_raw_work(i) for i in range(100)]},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_none)) as client:
        res_none = await EuropePMCSource(client=client).search("none", max_results=300)

    assert cursors_none == ["*"]
    assert res_none.fetched == 100

    # 7. Se a segunda página falha, preserva os trabalhos já trazidos
    def handler_partial(request: httpx.Request) -> httpx.Response:
        if request.url.params["cursorMark"] == "*":
            return httpx.Response(
                200,
                json={
                    "hitCount": 250,
                    "nextCursorMark": "cur-2",
                    "resultList": {"result": [_make_raw_work(i) for i in range(100)]},
                },
            )
        return httpx.Response(400, json={"status": "error"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_partial)) as client:
        res_partial = await EuropePMCSource(client=client).search("partial", max_results=200)

    assert res_partial.status == "failed"
    assert res_partial.reason == "HTTP 400"
    assert res_partial.found == 250
    assert res_partial.fetched == 100
    assert len(res_partial.works) == 100


# NFR-04, D-020: Novas tentativas [1, 2, 4] em 429, 5xx, timeout e erro de rede
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
                httpx.ReadTimeout("timeout email=segredo@ebi.ac.uk", request=req)
            ),
            "failed",
            "tempo limite esgotado depois de 3 tentativas",
        ),
        (
            lambda req: (_ for _ in ()).throw(
                httpx.ConnectError("rede email=segredo@ebi.ac.uk", request=req)
            ),
            "failed",
            "erro de rede depois de 3 tentativas",
        ),
    ],
)
async def test_nfr04_d020_retries_429_5xx_timeout_e_rede(
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
        res = await EuropePMCSource(client=client, sleep=fake_sleep).search("q")

    assert calls == 4
    assert sleeps == [1, 2, 4]
    assert res.status == expected_status
    assert res.reason == expected_reason
    assert "segredo@ebi.ac.uk" not in (res.reason or "")
    assert "timeout" not in (res.reason or "")


# NFR-04, D-020: Erros sem repetição (4xx diferente de 429 e JSON inválido)
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
            "resposta JSON inválida do Europe PMC",
        ),
        (
            httpx.Response(200, json=[{"id": "1"}]),
            "failed",
            "resposta JSON inválida do Europe PMC",
        ),
        (
            httpx.Response(200, json={"hitCount": 1, "resultList": "not-a-dict"}),
            "failed",
            "resposta JSON inválida do Europe PMC",
        ),
    ],
)
async def test_nfr04_d020_erros_sem_repeticao_4xx_e_json_invalido(
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
        res = await EuropePMCSource(client=client, sleep=fake_sleep).search("q")

    assert calls == 1
    assert sleeps == []
    assert res.status == expected_status
    assert res.reason == expected_reason


# NFR-04, D-020: Com RSL_CONTACT_EMAIL, email vai na URL e não aparece em query, reason nem cache_query
@pytest.mark.anyio
async def test_nfr04_d020_rsl_contact_email_vai_em_email_e_nao_vaza(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    email = "pesquisador@ebi.ac.uk"
    monkeypatch.setenv("RSL_CONTACT_EMAIL", f"  {email}  ")
    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        q = request.url.params.get("query")
        if q == "erro":
            return httpx.Response(403, text=f"Forbidden for {email}")
        if q == "excecao":
            raise RuntimeError(f"boom email={email}")
        return httpx.Response(
            200,
            json={
                "hitCount": 1,
                "nextCursorMark": "cur-2",
                "resultList": {"result": [_make_raw_work(1)]},
            },
        )

    with caplog.at_level(logging.DEBUG):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            source = EuropePMCSource(client=client)
            res_ok = await source.search("genomics", max_results=10)
            res_err = await source.search("erro", max_results=10)
            res_exc = await source.search("excecao", max_results=10)
            cache_q = source.cache_query("genomics", max_results=10)
            source_repr = repr(source)

    assert len(seen_requests) == 3
    for req in seen_requests:
        assert req.url.params["email"] == email
        assert req.headers["User-Agent"].startswith("rslapp/")
        assert email not in req.headers["User-Agent"]

    assert res_ok.status == "ok"
    assert res_err.status == "failed"
    assert res_err.reason == "HTTP 403"
    assert res_exc.status == "failed"
    assert res_exc.reason == "falha inesperada ao consultar o Europe PMC"

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
        assert "email=" not in surface.lower()

    rslapp_logs = [rec.getMessage() for rec in caplog.records if rec.name.startswith("rslapp")]
    for log_msg in rslapp_logs:
        assert email not in log_msg


# FR-03, D-020: Limpeza de HTML/XML, entidades e ponto final solto em títulos e resumos
@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        ("<p>Abstract with &lt;b&gt;bold&lt;/b&gt; &amp; italic.</p>", "Abstract with <b>bold</b> & italic."),
        ("effect p<0.05 when n>30 observed", "effect p<0.05 when n>30 observed"),
        ("<div>Section title<br>second line</div>", "Section title second line"),
        (None, None),
        ("", None),
        ("   ", None),
    ],
)
def test_fr03_d020_clean_html_text(raw_text: Any, expected: str | None) -> None:
    from rslapp.sources.europe_pmc import _clean_html_text

    assert _clean_html_text(raw_text) == expected


# FR-03, D-020: Limpeza de títulos com ponto final solto e tags
@pytest.mark.parametrize(
    ("raw_title", "expected"),
    [
        ("A title with trailing dot.", "A title with trailing dot"),
        ("<i>A title with html.</i>", "A title with html"),
        ("Title without dot", "Title without dot"),
        ("...", None),
        (".", None),
        (None, None),
        ("", None),
    ],
)
def test_fr03_d020_clean_title(raw_title: Any, expected: str | None) -> None:
    from rslapp.sources.europe_pmc import _clean_title

    assert _clean_title(raw_title) == expected


# D-020: cache_query e repr da fonte
def test_d020_cache_query_e_repr() -> None:
    source = EuropePMCSource()
    assert source.cache_query("query test", 50) == {
        "source": "europe_pmc",
        "query": "query test",
        "max_results": 50,
    }
    assert repr(source) == "EuropePMCSource(name='europe_pmc', needs_key=False)"
