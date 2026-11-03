"""Testes da consulta de artigo específico por DOI no OpenAlex."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from rslapp.sources.openalex import OpenAlexSource


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clean_openalex_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)


# FR-02, NFR-03: Sem chave configurada retorna missing_key
@pytest.mark.anyio
async def test_fr02_nfr03_openalex_find_by_doi_missing_key() -> None:
    source = OpenAlexSource()
    res = await source.find_by_doi("10.1234/exemplo")
    assert res.status == "missing_key"
    assert "OPENALEX_API_KEY não configurada" in (res.reason or "")
    assert res.fetched == 0
    assert res.works == []


# FR-02, NFR-03: Chave com caracteres inválidos retorna failed
@pytest.mark.anyio
async def test_fr02_nfr03_openalex_find_by_doi_invalid_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "chave com espaço")
    source = OpenAlexSource()
    res = await source.find_by_doi("10.1234/exemplo")
    assert res.status == "failed"
    assert "caracteres inválidos" in (res.reason or "")


# FR-02, NFR-03: Chave no cabeçalho e caminho da URL exatamente cotado
@pytest.mark.anyio
async def test_fr02_nfr03_openalex_find_by_doi_path_and_header(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_key = "fake-key-123"
    monkeypatch.setenv("OPENALEX_API_KEY", fake_key)
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "https://openalex.org/W999",
                "doi": "https://doi.org/10.1234/foo.bar/1",
                "display_name": "Artigo Teste",
                "publication_year": 2024,
                "authorships": [],
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = OpenAlexSource(client=client)
        res = await source.find_by_doi("10.1234/foo.bar/1")

    assert res.status == "ok"
    assert res.found == 1
    assert res.fetched == 1
    assert len(res.works) == 1
    assert res.works[0].title == "Artigo Teste"
    assert res.works[0].doi == "10.1234/foo.bar/1"

    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.headers["Authorization"] == f"Bearer {fake_key}"
    assert req.url.raw_path.startswith(b"/works/doi:10.1234%2Ffoo.bar%2F1")
    assert "select" in req.url.params


# FR-02, D-002: 404 devolve status ok com zero trabalhos
@pytest.mark.anyio
async def test_fr02_d002_openalex_find_by_doi_404_empty_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "Not found"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = OpenAlexSource(client=client)
        res = await source.find_by_doi("10.1234/nao-existe")

    assert res.status == "ok"
    assert res.found == 0
    assert res.fetched == 0
    assert res.works == []


# FR-02, NFR-04: Retentativas em 429 e 500
@pytest.mark.anyio
async def test_fr02_nfr04_openalex_find_by_doi_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(500, json={"error": "Server error"})

    sleep_calls: list[float] = []

    async def fake_sleep(d: float) -> None:
        sleep_calls.append(d)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = OpenAlexSource(client=client, sleep=fake_sleep)
        res = await source.find_by_doi("10.1234/falha")

    assert attempts == 4  # 1 inicial + 3 retentativas
    assert sleep_calls == [1, 2, 4]
    assert res.status == "failed"
    assert "HTTP 500" in (res.reason or "")


# FR-02, NFR-04: Testes parametrizados de erros: 500 com retentativas resultando em failed, ReadTimeout, ConnectError, JSON inválido e JSON em lista
@pytest.mark.anyio
@pytest.mark.parametrize(
    ("handler_action", "expected_status", "expected_reason_substr", "expect_retries"),
    [
        (lambda req: httpx.Response(500, json={"error": "Server error"}), "failed", "HTTP 500", True),
        (lambda req: (_ for _ in ()).throw(httpx.ReadTimeout("timeout", request=req)), "failed", "tempo limite esgotado", True),
        (lambda req: (_ for _ in ()).throw(httpx.ConnectError("connect error", request=req)), "failed", "erro de rede", True),
        (lambda req: httpx.Response(200, text="not-json{"), "failed", "resposta JSON inválida do OpenAlex", False),
        (lambda req: httpx.Response(200, json=[]), "failed", "resposta JSON inválida do OpenAlex", False),
    ],
)
async def test_fr02_nfr04_openalex_find_by_doi_errors_parameterized(
    monkeypatch: pytest.MonkeyPatch,
    handler_action: Any,
    expected_status: str,
    expected_reason_substr: str,
    expect_retries: bool,
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
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
        source = OpenAlexSource(client=client, sleep=fake_sleep)
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
        ("10.1234/foo/../bar", b"/works/doi:10.1234%2Ffoo%2F..%2Fbar"),
        ("10.1234/foo?bar", b"/works/doi:10.1234%2Ffoo%3Fbar"),
        ("10.1234/foo#bar", b"/works/doi:10.1234%2Ffoo%23bar"),
        ("10.1234/foo%bar", b"/works/doi:10.1234%2Ffoo%25bar"),
        ("10.1234/foo bar", b"/works/doi:10.1234%2Ffoo%20bar"),
    ],
)
async def test_fr02_d002_openalex_find_by_doi_quoted_paths_parameterized(
    monkeypatch: pytest.MonkeyPatch,
    doi_input: str,
    expected_raw_path_prefix: bytes,
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(404, json={"error": "Not found"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        source = OpenAlexSource(client=client)
        await source.find_by_doi(doi_input)

    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.url.raw_path.startswith(expected_raw_path_prefix)
