"""Testes do conector da fonte acadêmica PubMed com MockTransport (sem rede)."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from rslapp.sources.base import Source
from rslapp.sources.pubmed import (
    PubmedSource,
    reset_rate_limiter,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clean_pubmed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    monkeypatch.delenv("RSL_CONTACT_EMAIL", raising=False)
    reset_rate_limiter()


def _make_article_xml(
    pmid: str,
    title: str | None = None,
    doi: str | None = None,
    eloc_doi: str | None = None,
    year: int | None = None,
    medline_date: str | None = None,
    article_date_year: int | None = None,
    venue: str = "Test Medical Journal",
    abstract_parts: list[tuple[str | None, str]] | None = None,
    keywords: list[str] | None = None,
    mesh_descriptors: list[str] | None = None,
    pub_type: str = "Journal Article",
    authors_xml: str | None = None,
    references: list[str | None] | None = None,
) -> str:
    parts = ["<PubmedArticle><MedlineCitation>"]
    parts.append(f"<PMID>{pmid}</PMID>")
    parts.append("<Article>")
    parts.append("<Journal><JournalIssue><PubDate>")
    if year is not None:
        parts.append(f"<Year>{year}</Year>")
    if medline_date is not None:
        parts.append(f"<MedlineDate>{medline_date}</MedlineDate>")
    parts.append("</PubDate></JournalIssue>")
    parts.append(f"<Title>{venue}</Title></Journal>")

    if title is not None:
        parts.append(f"<ArticleTitle>{title}</ArticleTitle>")

    if eloc_doi is not None:
        parts.append(f'<ELocationID EIdType="doi">{eloc_doi}</ELocationID>')

    if article_date_year is not None:
        parts.append(f"<ArticleDate><Year>{article_date_year}</Year></ArticleDate>")

    if abstract_parts is not None:
        parts.append("<Abstract>")
        for label, text in abstract_parts:
            lbl_attr = f' Label="{label}"' if label else ""
            parts.append(f"<AbstractText{lbl_attr}>{text}</AbstractText>")
        parts.append("</Abstract>")

    if authors_xml is not None:
        parts.append(f"<AuthorList>{authors_xml}</AuthorList>")

    parts.append(f"<PublicationTypeList><PublicationType>{pub_type}</PublicationType></PublicationTypeList>")
    parts.append("</Article>")

    if keywords:
        parts.append("<KeywordList>")
        for kw in keywords:
            parts.append(f"<Keyword>{kw}</Keyword>")
        parts.append("</KeywordList>")

    if mesh_descriptors:
        parts.append("<MeshHeadingList>")
        for desc in mesh_descriptors:
            parts.append(f"<MeshHeading><DescriptorName>{desc}</DescriptorName></MeshHeading>")
        parts.append("</MeshHeadingList>")

    parts.append("</MedlineCitation>")

    parts.append("<PubmedData>")
    parts.append("<ArticleIdList>")
    parts.append(f'<ArticleId IdType="pubmed">{pmid}</ArticleId>')
    if doi:
        parts.append(f'<ArticleId IdType="doi">{doi}</ArticleId>')
    parts.append("</ArticleIdList>")

    if references is not None:
        parts.append("<ReferenceList>")
        for ref_doi in references:
            parts.append("<Reference>")
            parts.append("<Citation>Ref citation text</Citation>")
            if ref_doi:
                parts.append(f'<ArticleIdList><ArticleId IdType="doi">{ref_doi}</ArticleId></ArticleIdList>')
            parts.append("</Reference>")
        parts.append("</ReferenceList>")

    parts.append("</PubmedData></PubmedArticle>")
    return "".join(parts)


# D-020: PubmedSource cumpre o protocolo Source do miolo
def test_d020_cumpre_protocolo_source() -> None:
    source = PubmedSource()
    assert isinstance(source, Source)
    assert source.name == "pubmed"
    assert source.needs_key is False
    assert repr(source) == "PubmedSource(name='pubmed', needs_key=False)"


# FR-01, FR-03, FR-14, D-004, D-020: Mapeamento completo dos campos do PubMed
@pytest.mark.anyio
async def test_fr01_fr03_fr14_d004_d020_mapeamento_completo_campos() -> None:
    authors_xml = """
    <Author>
        <ForeName>Carlos</ForeName>
        <LastName>Silva</LastName>
        <Identifier Source="ORCID">https://orcid.org/0000-0002-1825-0097</Identifier>
        <AffiliationInfo><Affiliation>Universidade de São Paulo</Affiliation></AffiliationInfo>
        <AffiliationInfo><Affiliation>Instituto de Biociências</Affiliation></AffiliationInfo>
    </Author>
    <Author>
        <LastName>Santos</LastName>
        <Identifier Source="ORCID">0000-0001-5555-000X</Identifier>
    </Author>
    <Author>
        <CollectiveName>Grupo de Pesquisa Integrado</CollectiveName>
    </Author>
    <Author>
        <ForeName>Mariana</ForeName>
        <LastName>Costa</LastName>
        <Identifier Source="ORCID">orcid-invalido-1234</Identifier>
    </Author>
    """

    art1_xml = _make_article_xml(
        pmid="11111",
        title="Estudo sobre <i>Helicobacter pylori</i> em <b>gastrite</b>",
        doi="https://doi.org/10.1000/PMID.1",
        year=2024,
        venue="Revista Médica Brasileira",
        abstract_parts=[
            ("BACKGROUND", "Introdução ao estudo."),
            ("METHODS", "Métodos aplicados."),
        ],
        keywords=["Genômica", "Bioinformática"],
        mesh_descriptors=["GENÔMICA", "Algoritmos"],
        pub_type="Journal Article",
        authors_xml=authors_xml,
        references=["10.1000/REF.1", None, "10.1000/REF.3"],
    )

    art2_xml = _make_article_xml(
        pmid="22222",
        title="Segundo Artigo com DOI em ELocationID",
        eloc_doi="10.1000/ELOC.2",
        medline_date="2020 Jan-Feb",
        abstract_parts=[(None, "Resumo em texto corrido sem rótulo.")],
        references=None,
    )

    art3_sem_titulo = _make_article_xml(
        pmid="33333",
        title=None,
        doi="10.1000/SEM.TITULO",
    )

    art4_article_date = _make_article_xml(
        pmid="44444",
        title="Quarto Artigo com Ano em ArticleDate",
        article_date_year=2019,
    )

    xml_set = f"<PubmedArticleSet>{art1_xml}{art2_xml}{art3_sem_titulo}{art4_article_date}</PubmedArticleSet>"

    async def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "esearch.fcgi" in url_str:
            return httpx.Response(
                200,
                json={
                    "esearchresult": {
                        "count": "4",
                        "retmax": "10",
                        "retstart": "0",
                        "querykey": "1",
                        "webenv": "NCID_TEST_ENV",
                        "idlist": ["11111", "22222", "33333", "44444"],
                    }
                },
            )
        if "efetch.fcgi" in url_str:
            return httpx.Response(200, content=xml_set.encode())
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = PubmedSource(client=client)
        result = await source.search("gastrite", max_results=10)

    assert result.status == "ok"
    assert result.name == "pubmed"
    assert result.found == 4
    # Registro sem título foi descartado; restam 3
    assert result.fetched == 3
    assert len(result.works) == 3

    # Artigo 1
    w1 = result.works[0]
    assert w1.title == "Estudo sobre Helicobacter pylori em gastrite"
    assert w1.doi == "10.1000/pmid.1"
    assert w1.year == 2024
    assert w1.venue == "Revista Médica Brasileira"
    assert w1.type == "journal article"
    assert w1.abstract == "BACKGROUND: Introdução ao estudo. METHODS: Métodos aplicados."
    # Palavras-chave sem duplicações (GENÔMICA casou insensível com Genômica)
    assert w1.keywords == ["Genômica", "Bioinformática", "Algoritmos"]
    assert w1.source_ids == {"pubmed": "11111"}
    assert w1.citations == {}
    assert w1.references_count == 3
    assert w1.references == ["10.1000/ref.1", "10.1000/ref.3"]

    assert len(w1.authors) == 4
    # Autor 1: ForeName + LastName, ORCID URL normalizado, afiliações múltiplas
    a1 = w1.authors[0]
    assert a1.name == "Carlos Silva"
    assert a1.orcid == "0000-0002-1825-0097"
    assert a1.raw_affiliations == ["Universidade de São Paulo", "Instituto de Biociências"]
    assert len(a1.affiliations) == 2
    assert a1.affiliations[0].name == "Universidade de São Paulo"
    assert a1.affiliations[1].name == "Instituto de Biociências"
    assert a1.position is None

    # Autor 2: apenas LastName, ORCID número
    a2 = w1.authors[1]
    assert a2.name == "Santos"
    assert a2.orcid == "0000-0001-5555-000X"

    # Autor 3: CollectiveName
    a3 = w1.authors[2]
    assert a3.name == "Grupo de Pesquisa Integrado"
    assert a3.orcid is None

    # Autor 4: ORCID inválido vira nulo
    a4 = w1.authors[3]
    assert a4.name == "Mariana Costa"
    assert a4.orcid is None

    # Artigo 2: DOI em ELocationID, MedlineDate para ano, sem ReferenceList
    w2 = result.works[1]
    assert w2.title == "Segundo Artigo com DOI em ELocationID"
    assert w2.doi == "10.1000/eloc.2"
    assert w2.year == 2020
    assert w2.abstract == "Resumo em texto corrido sem rótulo."
    assert w2.references == []
    assert w2.references_count is None

    # Artigo 4 (o terceiro retornado): ano via ArticleDate/Year
    w3 = result.works[2]
    assert w3.title == "Quarto Artigo com Ano em ArticleDate"
    assert w3.year == 2019


# FR-03, FR-14, D-020: DOI próprio não confunde com DOIs em ReferenceList
@pytest.mark.anyio
async def test_fr03_d020_doi_proprio_nao_confunde_com_referencias() -> None:
    # Caso (a): DOI só em ELocationID + ReferenceList com DOIs -> doi do ELocationID
    art_eloc_xml = _make_article_xml(
        pmid="55551",
        title="Artigo com DOI apenas em ELocationID",
        doi=None,
        eloc_doi="10.1000/OWN.ELOC",
        references=["10.9000/REF.DOI.1", "10.9000/REF.DOI.2"],
    )

    # Caso (b): sem DOI nenhum + referências com DOI -> doi None
    art_no_doi_xml = _make_article_xml(
        pmid="55552",
        title="Artigo sem nenhum DOI próprio",
        doi=None,
        eloc_doi=None,
        references=["10.9000/REF.DOI.3"],
    )

    xml_set = f"<PubmedArticleSet>{art_eloc_xml}{art_no_doi_xml}</PubmedArticleSet>"

    async def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "esearch.fcgi" in url_str:
            return httpx.Response(
                200,
                json={
                    "esearchresult": {
                        "count": "2",
                        "retmax": "2",
                        "retstart": "0",
                        "querykey": "1",
                        "webenv": "NCID_DOI_TEST",
                        "idlist": ["55551", "55552"],
                    }
                },
            )
        if "efetch.fcgi" in url_str:
            return httpx.Response(200, content=xml_set.encode())
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = PubmedSource(client=client)
        result = await source.search("teste doi", max_results=2)

    assert result.status == "ok"
    assert len(result.works) == 2

    # Caso (a)
    w_eloc = result.works[0]
    assert w_eloc.doi == "10.1000/own.eloc"
    assert w_eloc.references == ["10.9000/ref.doi.1", "10.9000/ref.doi.2"]

    # Caso (b)
    w_no_doi = result.works[1]
    assert w_no_doi.doi is None
    assert w_no_doi.references == ["10.9000/ref.doi.3"]


# FR-01, D-020: ESearch pede usehistory=y e EFetch pagina em lotes de 200 pelo WebEnv
@pytest.mark.anyio
async def test_fr01_d020_esearch_usehistory_e_efetch_lotes_de_200() -> None:
    captured_requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        url_str = str(request.url)
        if "esearch.fcgi" in url_str:
            assert request.url.params["usehistory"] == "y"
            assert request.url.params["db"] == "pubmed"
            assert request.url.params["retmode"] == "json"
            assert request.url.params["tool"] == "rslapp"
            assert request.url.params["retmax"] == "300"
            return httpx.Response(
                200,
                json={
                    "esearchresult": {
                        "count": "500",
                        "retmax": "300",
                        "retstart": "0",
                        "querykey": "2",
                        "webenv": "NCID_ENV_LOTES",
                        "idlist": [str(i) for i in range(1, 301)],
                    }
                },
            )
        if "efetch.fcgi" in url_str:
            assert request.url.params["WebEnv"] == "NCID_ENV_LOTES"
            assert request.url.params["query_key"] == "2"
            retstart = int(request.url.params["retstart"])
            retmax = int(request.url.params["retmax"])
            # Gera artigos para cada lote
            batch = [
                _make_article_xml(pmid=str(retstart + i), title=f"Artigo {retstart + i}")
                for i in range(1, retmax + 1)
            ]
            content = f"<PubmedArticleSet>{''.join(batch)}</PubmedArticleSet>"
            return httpx.Response(200, content=content.encode())
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = PubmedSource(client=client)
        result = await source.search("oncology", max_results=300)

    assert result.status == "ok"
    assert result.found == 500
    assert result.fetched == 300
    assert len(result.works) == 300

    # 1 chamada ESearch + 2 chamadas EFetch (retstart 0 com retmax 200, retstart 200 com retmax 100)
    assert len(captured_requests) == 3
    assert "esearch.fcgi" in str(captured_requests[0].url)
    assert captured_requests[1].url.params["retstart"] == "0"
    assert captured_requests[1].url.params["retmax"] == "200"
    assert captured_requests[2].url.params["retstart"] == "200"
    assert captured_requests[2].url.params["retmax"] == "100"


# FR-01, D-020: Busca sem resultados no ESearch devolve ok com zero artigos sem chamar EFetch
@pytest.mark.anyio
async def test_fr01_d020_busca_sem_resultados_retorna_ok_zero() -> None:
    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={"esearchresult": {"count": "0", "retmax": "0", "retstart": "0", "idlist": []}},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = PubmedSource(client=client)
        result = await source.search("termo_inexistente_xyz_123")

    assert result.status == "ok"
    assert result.found == 0
    assert result.fetched == 0
    assert result.works == []
    assert len(captured) == 1
    assert "esearch.fcgi" in str(captured[0].url)


# NFR-04, D-020: Retentativas em 429, 5xx, timeout, rede e mensagem de rate limit; outras 4xx falham na hora
@pytest.mark.anyio
@pytest.mark.parametrize(
    ("trigger_mode", "expected_status", "expected_reason_substr"),
    [
        ("http_429", "rate_limited", "HTTP 429 depois de 3 tentativas"),
        ("rate_limit_msg", "rate_limited", "limite de taxa da API excedido depois de 3 tentativas"),
        ("http_503", "failed", "HTTP 503 depois de 3 tentativas"),
        ("timeout", "failed", "tempo limite esgotado depois de 3 tentativas"),
        ("network_error", "failed", "erro de rede depois de 3 tentativas"),
        ("http_400", "failed", "HTTP 400"),
    ],
)
async def test_nfr04_d020_retentativas_e_estados_de_erro(
    trigger_mode: str, expected_status: str, expected_reason_substr: str
) -> None:
    attempts = 0
    sleeps: list[float] = []
    current_time = 100.0

    def fake_clock() -> float:
        return current_time

    async def fake_sleep(sec: float) -> None:
        nonlocal current_time
        sleeps.append(sec)
        current_time += sec
        await asyncio.sleep(0)

    reset_rate_limiter()

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if trigger_mode == "http_429":
            return httpx.Response(429, text="Too Many Requests")
        if trigger_mode == "rate_limit_msg":
            return httpx.Response(200, text="<ERROR>API rate limit exceeded</ERROR>")
        if trigger_mode == "http_503":
            return httpx.Response(503, text="Service Unavailable")
        if trigger_mode == "timeout":
            raise httpx.ReadTimeout("timed out", request=request)
        if trigger_mode == "network_error":
            raise httpx.NetworkError("connection reset", request=request)
        if trigger_mode == "http_400":
            return httpx.Response(400, text="Bad Request")
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = PubmedSource(client=client, sleep=fake_sleep, clock=fake_clock)
        result = await source.search("qualquer", max_results=10)

    assert result.status == expected_status
    assert result.reason is not None
    assert expected_reason_substr in result.reason

    if trigger_mode == "http_400":
        # 4xx (exceto 429) não tenta novamente
        assert attempts == 1
        assert sleeps == []
    else:
        # 1 tentativa inicial + 3 novas tentativas (1, 2, 4 s)
        assert attempts == 4
        assert sleeps == [1, 2, 4]


# NFR-04, D-020: Falha no EFetch mantém as páginas já trazidas no resultado
@pytest.mark.anyio
async def test_nfr04_d020_falha_no_efetch_preserva_paginas_anteriores() -> None:
    efetch_count = 0

    async def fake_sleep(sec: float) -> None:
        pass

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal efetch_count
        url_str = str(request.url)
        if "esearch.fcgi" in url_str:
            return httpx.Response(
                200,
                json={
                    "esearchresult": {
                        "count": "500",
                        "retmax": "400",
                        "retstart": "0",
                        "querykey": "1",
                        "webenv": "NCID_PARTIAL",
                        "idlist": [str(i) for i in range(1, 401)],
                    }
                },
            )
        if "efetch.fcgi" in url_str:
            efetch_count += 1
            if efetch_count == 1:
                batch = [
                    _make_article_xml(pmid=str(i), title=f"Artigo Lote 1 - {i}")
                    for i in range(1, 201)
                ]
                content = f"<PubmedArticleSet>{''.join(batch)}</PubmedArticleSet>"
                return httpx.Response(200, content=content.encode())
            # Segundo lote falha persistentemente com 500
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = PubmedSource(client=client, sleep=fake_sleep)
        result = await source.search("cardiologia", max_results=400)

    assert result.status == "failed"
    assert result.reason == "HTTP 500 depois de 3 tentativas"
    assert result.found == 500
    # Os 200 artigos trazidos na primeira página foram preservados
    assert result.fetched == 200
    assert len(result.works) == 200


# NFR-03, D-020: NCBI_API_KEY e RSL_CONTACT_EMAIL vão na URL mas não vazam em query, reason, cache ou repr
@pytest.mark.anyio
async def test_nfr03_d020_chaves_e_email_nao_vazam_em_nenhum_campo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret_key = "secret-ncbi-token-999"
    secret_email = "pesquisador@laboratorio.org"

    monkeypatch.setenv("NCBI_API_KEY", secret_key)
    monkeypatch.setenv("RSL_CONTACT_EMAIL", secret_email)

    captured_urls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        captured_urls.append(url_str)
        if "esearch.fcgi" in url_str:
            assert request.url.params["api_key"] == secret_key
            assert request.url.params["email"] == secret_email
            return httpx.Response(
                200,
                json={
                    "esearchresult": {
                        "count": "1",
                        "retmax": "10",
                        "retstart": "0",
                        "querykey": "1",
                        "webenv": "NCID_SECRET_TEST",
                        "idlist": ["77777"],
                    }
                },
            )
        if "efetch.fcgi" in url_str:
            assert request.url.params["api_key"] == secret_key
            assert request.url.params["email"] == secret_email
            xml = _make_article_xml(pmid="77777", title="Artigo Seguro")
            return httpx.Response(200, content=f"<PubmedArticleSet>{xml}</PubmedArticleSet>".encode())
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = PubmedSource(client=client)
        result = await source.search("vacina", max_results=10)

    assert len(captured_urls) == 2

    # Verifica cache_query
    cached = source.cache_query("vacina", max_results=10)
    assert cached == {"source": "pubmed", "query": "vacina", "max_results": 10}

    # Verifica repr
    texto_repr = repr(source)
    assert secret_key not in texto_repr
    assert secret_email not in texto_repr

    # Verifica campos de SourceResult
    assert secret_key not in result.query
    assert secret_email not in result.query
    if result.reason:
        assert secret_key not in result.reason
        assert secret_email not in result.reason


# NFR-04, D-020: Ritmo: pedidos saem 1 por vez, nunca em paralelo; intervalo >= 0,34 s sem chave e >= 0,10 s com chave
@pytest.mark.anyio
async def test_nfr04_d020_ritmo_pedidos_sequenciais_e_intervalo_minimo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_time = 10.0
    call_start_times: list[float] = []

    def fake_clock() -> float:
        return current_time

    async def fake_sleep(seconds: float) -> None:
        nonlocal current_time
        current_time += seconds
        await asyncio.sleep(0)

    reset_rate_limiter()

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal current_time
        call_start_times.append(current_time)
        await asyncio.sleep(0)
        url_str = str(request.url)
        if "esearch.fcgi" in url_str:
            return httpx.Response(
                200,
                json={
                    "esearchresult": {
                        "count": "1",
                        "retmax": "10",
                        "retstart": "0",
                        "querykey": "1",
                        "webenv": "NCID_RITMO",
                        "idlist": ["101"],
                    }
                },
            )
        if "efetch.fcgi" in url_str:
            xml = _make_article_xml(pmid="101", title="Artigo Ritmo")
            return httpx.Response(200, content=f"<PubmedArticleSet>{xml}</PubmedArticleSet>".encode())
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        # Sem chave: intervalo >= 0,34 s
        source_no_key = PubmedSource(client=client, sleep=fake_sleep, clock=fake_clock)
        await asyncio.gather(
            source_no_key.search("call1", max_results=1),
            source_no_key.search("call2", max_results=1),
        )

        sem_chave_count = len(call_start_times)
        # Cada busca fez 2 chamadas (1 esearch + 1 efetch) -> 4 chamadas
        assert sem_chave_count == 4
        diffs_no_key = [
            call_start_times[i + 1] - call_start_times[i]
            for i in range(sem_chave_count - 1)
        ]
        assert all(d >= 0.33999 for d in diffs_no_key)

        # Com chave: intervalo >= 0,10 s
        monkeypatch.setenv("NCBI_API_KEY", "minha-chave-ncbi")
        call_start_times.clear()
        source_with_key = PubmedSource(client=client, sleep=fake_sleep, clock=fake_clock)
        await asyncio.gather(
            source_with_key.search("call3", max_results=1),
            source_with_key.search("call4", max_results=1),
        )

        com_chave_count = len(call_start_times)
        assert com_chave_count == 4
        diffs_with_key = [
            call_start_times[i + 1] - call_start_times[i]
            for i in range(com_chave_count - 1)
        ]
        assert all(d >= 0.09999 for d in diffs_with_key)


# FR-01, D-020: Respostas inválidas no ESearch ou ausência de WebEnv/query_key geram falha limpa
@pytest.mark.anyio
async def test_fr01_d020_esearch_resposta_invalida_ou_sem_webenv() -> None:
    # Caso 1: JSON inválido
    async def handler_bad_json(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json content")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_bad_json)) as client:
        source = PubmedSource(client=client)
        result = await source.search("termo")
    assert result.status == "failed"
    assert "resposta JSON inválida do ESearch" in (result.reason or "")

    # Caso 2: Falta WebEnv quando count > 0
    async def handler_missing_webenv(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"esearchresult": {"count": "10", "idlist": ["1"]}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_missing_webenv)) as client:
        source = PubmedSource(client=client)
        result = await source.search("termo")
    assert result.status == "failed"
    assert "ESearch não retornou WebEnv ou query_key" in (result.reason or "")


# FR-01, D-020: Resposta XML inválida do EFetch gera status failed com motivo descritivo
@pytest.mark.anyio
async def test_fr01_d020_efetch_xml_invalido() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "esearch.fcgi" in url_str:
            return httpx.Response(
                200,
                json={
                    "esearchresult": {
                        "count": "1",
                        "retmax": "10",
                        "retstart": "0",
                        "querykey": "1",
                        "webenv": "NCID_BAD_XML",
                        "idlist": ["99"],
                    }
                },
            )
        return httpx.Response(200, content=b"<<<invalid xml<<<")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = PubmedSource(client=client)
        result = await source.search("termo")
    assert result.status == "failed"
    assert "resposta XML inválida do EFetch" in (result.reason or "")

