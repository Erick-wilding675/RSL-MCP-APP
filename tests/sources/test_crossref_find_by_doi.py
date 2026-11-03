"""Testes da consulta de artigo específico por DOI na Crossref."""

from __future__ import annotations

import httpx
import pytest

from rslapp.sources.crossref import CrossrefSource


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# FR-02, D-002: Caminho da URL cotado e mailto opcional quando configurado
@pytest.mark.anyio
async def test_fr02_crossref_find_by_doi_path_and_mailto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RSL_CONTACT_EMAIL", "pesquisador@example.org")
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "message": {
                    "DOI": "10.1234/foo.bar/1",
                    "title": ["Artigo Crossref"],
                    "issued": {"date-parts": [[2023]]},
                    "author": [{"given": "Ana", "family": "Silva"}],
                },
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = CrossrefSource(client=client)
        res = await source.find_by_doi("10.1234/foo.bar/1")

    assert res.status == "ok"
    assert res.found == 1
    assert res.fetched == 1
    assert len(res.works) == 1
    assert res.works[0].title == "Artigo Crossref"
    assert res.works[0].doi == "10.1234/foo.bar/1"

    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.url.raw_path.startswith(b"/works/10.1234%2Ffoo.bar%2F1")
    assert req.url.params.get("mailto") == "pesquisador@example.org"
    assert "select" in req.url.params


# FR-02, D-002: 404 devolve status ok com zero trabalhos
@pytest.mark.anyio
async def test_fr02_d002_crossref_find_by_doi_404_empty_ok() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"status": "not-found"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = CrossrefSource(client=client)
        res = await source.find_by_doi("10.1234/nao-existe")

    assert res.status == "ok"
    assert res.found == 0
    assert res.fetched == 0
    assert res.works == []


# FR-02, NFR-04: Retentativas em 429 e 500
@pytest.mark.anyio
async def test_fr02_nfr04_crossref_find_by_doi_retries() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(429, text="Rate limit exceeded")

    sleep_calls: list[float] = []

    async def fake_sleep(d: float) -> None:
        sleep_calls.append(d)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = CrossrefSource(client=client, sleep=fake_sleep)
        res = await source.find_by_doi("10.1234/falha")

    assert attempts == 4
    assert sleep_calls == [1, 2, 4]
    assert res.status == "rate_limited"
    assert "HTTP 429" in (res.reason or "")
