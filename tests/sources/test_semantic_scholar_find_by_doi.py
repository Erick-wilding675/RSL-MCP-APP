"""Testes da consulta de artigo específico por DOI na Semantic Scholar."""

from __future__ import annotations

from typing import Any

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


# NFR-01, NFR-04: find_by_doi utiliza rate_limited_call garantindo espera de 1s entre chamadas consecutivas
@pytest.mark.anyio
async def test_nfr01_nfr04_semantic_scholar_find_by_doi_rate_limited() -> None:
    current_time = 100.0
    sleeps: list[float] = []

    def frozen_clock() -> float:
        # Relógio falso que não avança sozinho
        return current_time

    async def fake_sleep(seconds: float) -> None:
        nonlocal current_time
        sleeps.append(seconds)
        current_time += seconds

    reset_rate_limiter(clock=frozen_clock, sleep=fake_sleep)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "paperId": "p1",
                "title": "P1",
                "externalIds": {"DOI": "10.1234/test"},
                "year": 2024,
                "authors": [],
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = SemanticScholarSource(client=client, sleep=fake_sleep, clock=frozen_clock)
        # Primeira chamada executa imediatamente
        res1 = await source.find_by_doi("10.1234/test1")
        assert res1.status == "ok"
        assert sleeps == []

        # Segunda chamada com relógio congelado: rate_limited_call força espera de 1.0s
        res2 = await source.find_by_doi("10.1234/test2")
        assert res2.status == "ok"
        assert sleeps == [1.0]


# FR-02, NFR-04: Testes parametrizados de erros: 500 com retentativas resultando em failed, ReadTimeout, ConnectError, JSON inválido e JSON em lista
@pytest.mark.anyio
@pytest.mark.parametrize(
    ("handler_action", "expected_status", "expected_reason_substr", "expect_retries"),
    [
        (lambda req: httpx.Response(500, json={"message": "Internal Server Error"}), "failed", "Internal Server Error", True),
        (lambda req: (_ for _ in ()).throw(httpx.ReadTimeout("timeout", request=req)), "failed", "tempo limite esgotado", True),
        (lambda req: (_ for _ in ()).throw(httpx.ConnectError("connect error", request=req)), "failed", "erro de rede", True),
        (lambda req: httpx.Response(200, text="not-json{"), "failed", "resposta JSON inválida da Semantic Scholar", False),
        (lambda req: httpx.Response(200, json=[]), "failed", "resposta JSON inválida da Semantic Scholar", False),
    ],
)
async def test_fr02_nfr04_semantic_scholar_find_by_doi_errors_parameterized(
    handler_action: Any,
    expected_status: str,
    expected_reason_substr: str,
    expect_retries: bool,
) -> None:
    current_time = 100.0
    calls = 0
    sleep_calls: list[float] = []

    def fake_clock() -> float:
        return current_time

    async def fake_sleep(d: float) -> None:
        nonlocal current_time
        sleep_calls.append(d)
        current_time += d

    reset_rate_limiter(clock=fake_clock, sleep=fake_sleep)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return handler_action(request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = SemanticScholarSource(client=client, sleep=fake_sleep, clock=fake_clock)
        res = await source.find_by_doi("10.1234/test")

    assert res.status == expected_status
    assert res.status != "ok"
    assert res.found is None
    assert res.fetched == 0
    assert res.works == []
    assert expected_reason_substr in (res.reason or "")
    if expect_retries:
        assert calls == 4
        assert sleep_calls == [1, 2, 4]
    else:
        assert calls == 1


# FR-02, D-002: Caminho exato cotado com MockTransport para DOIs contendo ../, ?, #, % e espaço
@pytest.mark.anyio
@pytest.mark.parametrize(
    ("doi_input", "expected_raw_path_prefix"),
    [
        ("10.1234/foo/../bar", b"/graph/v1/paper/DOI:10.1234%2Ffoo%2F..%2Fbar"),
        ("10.1234/foo?bar", b"/graph/v1/paper/DOI:10.1234%2Ffoo%3Fbar"),
        ("10.1234/foo#bar", b"/graph/v1/paper/DOI:10.1234%2Ffoo%23bar"),
        ("10.1234/foo%bar", b"/graph/v1/paper/DOI:10.1234%2Ffoo%25bar"),
        ("10.1234/foo bar", b"/graph/v1/paper/DOI:10.1234%2Ffoo%20bar"),
    ],
)
async def test_fr02_d002_semantic_scholar_find_by_doi_quoted_paths_parameterized(
    doi_input: str,
    expected_raw_path_prefix: bytes,
) -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(404, json={"message": "Not found"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = SemanticScholarSource(client=client)
        await source.find_by_doi(doi_input)

    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.url.raw_path.startswith(expected_raw_path_prefix)
