"""Testes da separação de dados por pessoa no modo HTTP e cache compartilhado (D-012, D-013)."""

from __future__ import annotations

import contextlib
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from mcp import Client
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import AnyHttpUrl

from rslapp import cli, config, people, server
from rslapp.auth import AuthStore, RSLTokenVerifier
from rslapp.core.models import Author, OriginWorkResult, SourceResult, Work
from rslapp.store import Store

PUBLIC_URL = "http://127.0.0.1:8000"
ENV_VARS = (
    "RSL_DATA_DIR",
    "RSL_EXPORT_DIR",
    "RSL_CACHE_DAYS",
    "OPENALEX_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "RSL_CONTACT_EMAIL",
    "RSL_HTTP_HOST",
    "RSL_HTTP_PORT",
    "RSL_PUBLIC_URL",
    "RSL_FORWARDED_ALLOW_IPS",
    "RSL_ACCESS_TOKEN_MINUTES",
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    """Isola variáveis de ambiente e configura RSL_DATA_DIR e RSL_EXPORT_DIR temporários."""
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    fake_home = tmp_path / "fake_home"
    data_dir, export_dir = tmp_path / "rsl_data", tmp_path / "rsl_exports"
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("RSL_EXPORT_DIR", str(export_dir))
    return data_dir, export_dir


class FakeCountingSource:
    """Fonte simulada sem rede que contabiliza chamadas para testar cache e isolamento."""

    def __init__(self, works_by_query: dict[str, list[Work]] | None = None) -> None:
        self.name = "openalex"
        self.needs_key = True
        self._works_by_query = works_by_query or {}
        self.calls: list[tuple[str, int]] = []

    def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
        return {"search": query.strip(), "max_results": max_results}

    async def search(self, query: str, max_results: int) -> SourceResult:
        self.calls.append((query, max_results))
        works = self._works_by_query.get(
            query,
            [
                Work(
                    title=f"Artigo sobre {query}",
                    doi="10.1234/artigo.2026",
                    year=2026,
                    venue="Revista de Teste",
                    authors=[Author(name="Autora Teste")],
                    references=["W10"],
                    references_count=1,
                    citations={"openalex": 5},
                    source_ids={"openalex": "W1"},
                )
            ],
        )
        return SourceResult(
            name="openalex",
            status="ok",
            query=f"search={query} · per_page={max_results}",
            found=len(works),
            fetched=len(works),
            works=works,
        )

    async def get_origin_work(self, _identifier: str) -> OriginWorkResult:
        return OriginWorkResult(
            data={"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1234/artigo.2026"},
            status=None,
            reason=None,
            not_found=False,
        )

    async def related(
        self, identifier: str, direction: str, _max_results: int, **_kw: Any
    ) -> SourceResult:
        return SourceResult(
            name="openalex",
            status="ok",
            query=f"related={identifier}:{direction}",
            found=1,
            fetched=1,
            works=[
                Work(
                    title="Artigo Relacionado",
                    doi="10.1234/rel.2026",
                    year=2026,
                    authors=[Author(name="Coautora Teste")],
                    source_ids={"openalex": "W2"},
                )
            ],
        )


def _extract_jsonrpc_body(resp: httpx.Response) -> dict[str, Any]:
    if "text/event-stream" in resp.headers.get("content-type", ""):
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[len("data:") :].strip())
    return resp.json()


async def _call_http_tool(
    client: httpx.AsyncClient, token: str, tool_name: str, arguments: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Abre sessão MCP em /mcp com Bearer token e executa tools/call devolvendo result do JSON-RPC."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    init_resp = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        },
        headers=headers,
    )
    assert init_resp.status_code == 200
    call_headers = dict(headers)
    if session_id := init_resp.headers.get("mcp-session-id"):
        call_headers["mcp-session-id"] = session_id

    call_resp = await client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": tool_name, "arguments": arguments or {}}},
        headers=call_headers,
    )
    assert call_resp.status_code == 200
    return _extract_jsonrpc_body(call_resp)["result"]


def _issue_person_token(data_dir: Path, person_id: str) -> str:
    """Cadastra a pessoa (se ainda não existir) e emite um token de acesso OAuth para /mcp."""
    if people.get(person_id, data_dir=data_dir) is None:
        people.add(person_id, data_dir=data_dir)
    return AuthStore(data_dir=data_dir).issue_token_pair(
        person_id=person_id, client_id=f"c-{person_id}", scopes=["rsl"], resource=f"{PUBLIC_URL}/mcp"
    ).access_token


@contextlib.asynccontextmanager
async def _http_app_client() -> AsyncIterator[httpx.AsyncClient]:
    http_cfg = config.HttpConfig(host="127.0.0.1", port=8000, public_url=PUBLIC_URL)
    app = server.create_http_app(http_cfg)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=PUBLIC_URL) as client,
    ):
        yield client


# D-012, FR-12, FR-13: Maria faz uma busca e João não vê a lista nem o log dela; ids contam por pessoa
@pytest.mark.anyio
async def test_d012_fr12_fr13_maria_busca_e_joao_nao_ve_lista_nem_log_dela_e_ids_contam_por_pessoa(
    monkeypatch: pytest.MonkeyPatch, isolated_env: tuple[Path, Path]
) -> None:
    data_dir, _ = isolated_env
    fake_source = FakeCountingSource(
        {
            "busca da maria": [Work(title="Estudo da Maria", doi="10.1234/m.1", year=2025, authors=[Author(name="A1")], source_ids={"openalex": "W101"})],
            "busca do joao": [Work(title="Estudo do João", doi="10.1234/j.1", year=2026, authors=[Author(name="A2")], source_ids={"openalex": "W202"})],
        }
    )
    monkeypatch.setattr(server, "_build_sources", lambda: [fake_source])
    maria_token, joao_token = _issue_person_token(data_dir, "maria"), _issue_person_token(data_dir, "joao")

    async with _http_app_client() as client:
        maria_res = await _call_http_tool(
            client, maria_token, "search_works",
            {"query": "busca da maria", "request_summary": "Pedido da Maria", "sources": ["openalex"]},
        )
        assert maria_res.get("isError") is not True
        maria_payload = maria_res["structuredContent"]
        assert (maria_payload["search_id"], maria_payload["list_id"]) == ("s-0001", "l-0001")

        joao_get = await _call_http_tool(client, joao_token, "get_list", {"list_id": maria_payload["list_id"]})
        assert joao_get.get("isError") is True
        assert "list_not_found:" in joao_get["content"][0]["text"]

        joao_log = (await _call_http_tool(client, joao_token, "get_search_log"))["structuredContent"]
        assert joao_log["entries"] == []
        assert Path(joao_log["log_file"]) == (data_dir / "people" / "joao" / "log.md").resolve()

        joao_res = await _call_http_tool(
            client, joao_token, "search_works",
            {"query": "busca do joao", "request_summary": "Pedido do João", "sources": ["openalex"]},
        )
        joao_payload = joao_res["structuredContent"]
        assert (joao_payload["search_id"], joao_payload["list_id"]) == ("s-0001", "l-0001")

        m_list = (await _call_http_tool(client, maria_token, "get_list", {"list_id": "l-0001"}))["structuredContent"]
        j_list = (await _call_http_tool(client, joao_token, "get_list", {"list_id": "l-0001"}))["structuredContent"]
        assert m_list["works"][0]["title"] == "Estudo da Maria"
        assert j_list["works"][0]["title"] == "Estudo do João"

        assert "Pedido da Maria" in (data_dir / "people" / "maria" / "log.md").read_text(encoding="utf-8")
        assert "Pedido da Maria" not in (data_dir / "people" / "joao" / "log.md").read_text(encoding="utf-8")


# D-012, D-013: A mesma busca feita pela Maria e depois pelo João usa o cache compartilhado na segunda vez
@pytest.mark.anyio
async def test_d012_d013_mesma_busca_maria_e_depois_joao_usa_cache_sem_nova_chamada_as_fontes(
    monkeypatch: pytest.MonkeyPatch, isolated_env: tuple[Path, Path]
) -> None:
    data_dir, _ = isolated_env
    fake_source = FakeCountingSource()
    monkeypatch.setattr(server, "_build_sources", lambda: [fake_source])
    maria_token, joao_token = _issue_person_token(data_dir, "maria"), _issue_person_token(data_dir, "joao")

    async with _http_app_client() as client:
        res_m = await _call_http_tool(client, maria_token, "search_works", {"query": "ml interpretability", "sources": ["openalex"]})
        assert res_m["structuredContent"]["sources"][0]["from_cache"] is False
        assert len(fake_source.calls) == 1

        res_j = await _call_http_tool(client, joao_token, "search_works", {"query": "ml interpretability", "sources": ["openalex"]})
        assert res_j["structuredContent"]["sources"][0]["from_cache"] is True
        assert len(fake_source.calls) == 1


# D-012, D-013, D-007: Pastas de cada pessoa em people/<id>/, exportação em people/<id>/exports/ e cache em cache/ na raiz
@pytest.mark.anyio
async def test_d012_d013_d007_pastas_em_people_id_e_cache_na_raiz_ignorando_rsl_export_dir(
    monkeypatch: pytest.MonkeyPatch, isolated_env: tuple[Path, Path]
) -> None:
    data_dir, export_dir = isolated_env
    assert Store(data_dir / "p", 7, cache_dir=data_dir / "c").cache_dir == data_dir / "c"
    assert Store(data_dir / "p", 7).cache_dir == data_dir / "p" / "cache"

    monkeypatch.setattr(server, "_build_sources", lambda: [FakeCountingSource()])
    maria_token = _issue_person_token(data_dir, "maria")

    async with _http_app_client() as client:
        await _call_http_tool(client, maria_token, "search_works", {"query": "systematic review", "sources": ["openalex"]})
        await _call_http_tool(client, maria_token, "find_work", {"title": "Artigo", "sources": ["openalex"]})
        await _call_http_tool(client, maria_token, "get_related_works", {"work_id": "W1", "direction": "references", "sources": ["openalex"]})
        await _call_http_tool(client, maria_token, "repeat_search", {"search_id": "s-0001"})
        exp_res = await _call_http_tool(client, maria_token, "export_list", {"list_id": "l-0001", "format": "ris"})

    maria_dir = data_dir / "people" / "maria"
    assert (maria_dir / "lists" / "l-0004.json").is_file()
    assert (maria_dir / "searches" / "s-0004.json").is_file()
    assert (maria_dir / "log.md").is_file()
    assert (maria_dir / "exports" / "l-0001.ris").is_file()
    assert "path" not in exp_res["structuredContent"]
    assert exp_res["structuredContent"]["download_url"].startswith(f"{PUBLIC_URL}/downloads/")
    assert list((data_dir / "cache" / "openalex").glob("*.json")) != []
    assert not (maria_dir / "cache").exists()
    assert not (data_dir / "lists").exists()
    assert not (data_dir / "searches").exists()
    assert not (data_dir / "log.md").exists()
    assert not export_dir.exists()


# D-012, D-007: No stdio, tudo continua na raiz de RSL_DATA_DIR e usa RSL_EXPORT_DIR
@pytest.mark.anyio
async def test_d012_stdio_mantem_dados_na_raiz_de_rsl_data_dir_como_na_1_0_1(
    monkeypatch: pytest.MonkeyPatch, isolated_env: tuple[Path, Path]
) -> None:
    data_dir, export_dir = isolated_env
    monkeypatch.setattr(server, "_build_sources", lambda: [FakeCountingSource()])

    async with Client(server.mcp) as stdio_client:
        assert (await stdio_client.call_tool("search_works", {"query": "stdio query", "sources": ["openalex"]})).is_error is False
        assert (await stdio_client.call_tool("export_list", {"list_id": "l-0001", "format": "ris"})).is_error is False

    assert (data_dir / "lists" / "l-0001.json").is_file()
    assert (data_dir / "searches" / "s-0001.json").is_file()
    assert (data_dir / "log.md").is_file()
    assert (data_dir / "cache" / "openalex").is_dir()
    assert (export_dir / "l-0001.ris").is_file()
    assert not (data_dir / "people").exists()


# D-012: Uma ferramenta no modo HTTP sem pessoa identificada falha com erro e não grava nada
@pytest.mark.anyio
async def test_d012_ferramenta_no_modo_http_sem_pessoa_identificada_falha_e_nao_grava_nada(
    monkeypatch: pytest.MonkeyPatch, isolated_env: tuple[Path, Path]
) -> None:
    data_dir, export_dir = isolated_env
    fake_source = FakeCountingSource()
    monkeypatch.setattr(server, "_build_sources", lambda: [fake_source])

    verifier = RSLTokenVerifier(AuthStore(data_dir=data_dir), resource_server_url=f"{PUBLIC_URL}/mcp")
    auth_settings = AuthSettings(
        issuer_url=AnyHttpUrl(PUBLIC_URL),
        resource_server_url=AnyHttpUrl(f"{PUBLIC_URL}/mcp"),
        required_scopes=["rsl"],
        validate_token_resource=True,
    )
    http_mcp = server._build_http_mcp_server(token_verifier=verifier, auth=auth_settings)

    async with Client(http_mcp) as http_client:
        for tool_name, args in (
            ("search_works", {"query": "ml", "sources": ["openalex"]}),
            ("find_work", {"title": "ml", "sources": ["openalex"]}),
            ("get_related_works", {"work_id": "W1", "direction": "references", "sources": ["openalex"]}),
            ("repeat_search", {"search_id": "s-0001"}),
            ("get_list", {"list_id": "l-0001"}),
            ("get_search_log", {}),
            ("export_list", {"list_id": "l-0001", "format": "ris"}),
            ("list_sources", {}),
        ):
            assert (await http_client.call_tool(tool_name, args)).is_error is True

    maria_token = _issue_person_token(data_dir, "maria")
    monkeypatch.setattr(server, "current_person_id", lambda: None)
    async with _http_app_client() as client:
        resp = await _call_http_tool(client, maria_token, "search_works", {"query": "ml", "sources": ["openalex"]})
        assert resp.get("isError") is True

    monkeypatch.setattr(server, "current_person_id", lambda: "../fora")
    with pytest.raises(ToolError):
        await server.search_works(query="ml", sources=["openalex"])

    assert fake_source.calls == []
    for sub in ("lists", "searches", "log.md", "cache", "people"):
        assert not (data_dir / sub).exists()
    assert not export_dir.exists()


# D-012, D-016: user purge maria --yes apaga listas, log e exportações dela e mantém o cache
@pytest.mark.anyio
async def test_d012_d016_user_purge_maria_yes_apaga_dados_dela_e_mantem_cache(
    monkeypatch: pytest.MonkeyPatch, isolated_env: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    data_dir, _ = isolated_env
    monkeypatch.setattr(server, "_build_sources", lambda: [FakeCountingSource()])
    maria_token, joao_token = _issue_person_token(data_dir, "maria"), _issue_person_token(data_dir, "joao")

    async with _http_app_client() as client:
        await _call_http_tool(client, maria_token, "search_works", {"query": "tema", "sources": ["openalex"]})
        await _call_http_tool(client, maria_token, "export_list", {"list_id": "l-0001", "format": "ris"})
        await _call_http_tool(client, joao_token, "search_works", {"query": "tema", "sources": ["openalex"]})

    maria_dir, joao_dir = data_dir / "people" / "maria", data_dir / "people" / "joao"
    cache_files = list((data_dir / "cache" / "openalex").glob("*.json"))
    assert (maria_dir / "exports" / "l-0001.ris").is_file()
    assert len(cache_files) == 1

    cli.main(["user", "purge", "maria", "--yes"])
    assert "maria" in capsys.readouterr().out
    assert not maria_dir.exists()
    assert cache_files[0].is_file()
    assert (joao_dir / "lists" / "l-0001.json").is_file()
