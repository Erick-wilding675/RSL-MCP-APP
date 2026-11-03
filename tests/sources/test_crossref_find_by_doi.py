"""Testes da consulta de artigo específico por DOI na Crossref."""

from __future__ import annotations

from typing import Any

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
    assert "select" not in req.url.params


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


# FR-02, NFR-04: Testes parametrizados de erros: 500 com retentativas resultando em failed, ReadTimeout, ConnectError, JSON inválido e JSON em lista
@pytest.mark.anyio
@pytest.mark.parametrize(
    ("handler_action", "expected_status", "expected_reason_substr", "expect_retries"),
    [
        (lambda req: httpx.Response(500, text="Internal Server Error"), "failed", "HTTP 500", True),
        (lambda req: (_ for _ in ()).throw(httpx.ReadTimeout("timeout", request=req)), "failed", "tempo limite esgotado", True),
        (lambda req: (_ for _ in ()).throw(httpx.ConnectError("connect error", request=req)), "failed", "erro de rede", True),
        (lambda req: httpx.Response(200, text="not-json{"), "failed", "resposta JSON inválida da Crossref", False),
        (lambda req: httpx.Response(200, json=[]), "failed", "resposta JSON inválida da Crossref", False),
    ],
)
async def test_fr02_nfr04_crossref_find_by_doi_errors_parameterized(
    handler_action: Any,
    expected_status: str,
    expected_reason_substr: str,
    expect_retries: bool,
) -> None:
    calls = 0
    sleep_calls: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return handler_action(request)

    async def fake_sleep(d: float) -> None:
        sleep_calls.append(d)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = CrossrefSource(client=client, sleep=fake_sleep)
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
    ("doi_input", "expected_raw_path"),
    [
        ("10.1234/foo/../bar", b"/works/10.1234%2Ffoo%2F..%2Fbar"),
        ("10.1234/foo?bar", b"/works/10.1234%2Ffoo%3Fbar"),
        ("10.1234/foo#bar", b"/works/10.1234%2Ffoo%23bar"),
        ("10.1234/foo%bar", b"/works/10.1234%2Ffoo%25bar"),
        ("10.1234/foo bar", b"/works/10.1234%2Ffoo%20bar"),
    ],
)
async def test_fr02_d002_crossref_find_by_doi_quoted_paths_parameterized(
    doi_input: str,
    expected_raw_path: bytes,
) -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(404, json={"status": "not-found"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = CrossrefSource(client=client)
        await source.find_by_doi(doi_input)

    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.url.raw_path == expected_raw_path
    assert "select" not in req.url.params
