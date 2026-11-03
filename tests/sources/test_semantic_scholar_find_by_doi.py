"""Testes da consulta de artigo específico por DOI na Semantic Scholar."""

from __future__ import annotations

import httpx
import pytest

from rslapp.sources.semantic_scholar import SemanticScholarSource, reset_rate_limiter


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clean_s2_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
    reset_rate_limiter()


# FR-02, NFR-03: Chave com caracteres inválidos retorna failed
@pytest.mark.anyio
async def test_fr02_nfr03_semantic_scholar_find_by_doi_invalid_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "chave com espaço")
    source = SemanticScholarSource()
    res = await source.find_by_doi("10.1234/exemplo")
    assert res.status == "failed"
    assert "caracteres inválidos" in (res.reason or "")


# FR-02, NFR-03: Chave no cabeçalho x-api-key e caminho da URL exatamente cotado
@pytest.mark.anyio
async def test_fr02_nfr03_semantic_scholar_find_by_doi_path_and_header(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_key = "fake-s2-key-123"
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", fake_key)
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "paperId": "s2-paper-100",
                "title": "Artigo Semantic Scholar",
                "externalIds": {"DOI": "10.1234/foo.bar/1"},
                "year": 2024,
                "authors": [{"name": "Carlos", "authorId": "a1"}],
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = SemanticScholarSource(client=client)
        res = await source.find_by_doi("10.1234/foo.bar/1")

    assert res.status == "ok"
    assert res.found == 1
    assert res.fetched == 1
    assert len(res.works) == 1
    assert res.works[0].title == "Artigo Semantic Scholar"
    assert res.works[0].doi == "10.1234/foo.bar/1"

    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.headers["x-api-key"] == fake_key
    assert req.url.raw_path.startswith(b"/graph/v1/paper/DOI:10.1234%2Ffoo.bar%2F1")
    assert "fields" in req.url.params


# FR-02, D-002: 404 devolve status ok com zero trabalhos
@pytest.mark.anyio
async def test_fr02_d002_semantic_scholar_find_by_doi_404_empty_ok() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Paper not found"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = SemanticScholarSource(client=client)
        res = await source.find_by_doi("10.1234/nao-existe")

    assert res.status == "ok"
    assert res.found == 0
    assert res.fetched == 0
    assert res.works == []


# FR-02, NFR-04: Retentativas em 429
@pytest.mark.anyio
async def test_fr02_nfr04_semantic_scholar_find_by_doi_retries() -> None:
    attempts = 0
    current_time = 0.0

    def fake_clock() -> float:
        return current_time

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts, current_time
        attempts += 1
        current_time += 0.01
        return httpx.Response(429, json={"message": "Too Many Requests"})

    sleep_calls: list[float] = []

    async def fake_sleep(d: float) -> None:
        nonlocal current_time
        sleep_calls.append(d)
        current_time += d + 1.0

    reset_rate_limiter(clock=fake_clock, sleep=fake_sleep)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = SemanticScholarSource(client=client, sleep=fake_sleep, clock=fake_clock)
        res = await source.find_by_doi("10.1234/falha")

    assert attempts == 4
    assert sleep_calls == [1, 2, 4]
    assert res.status == "rate_limited"
