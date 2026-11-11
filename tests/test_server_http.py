"""Testes do modo HTTP (streamable HTTP) do servidor MCP do RSL.app."""

from __future__ import annotations

import contextlib
import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import httpx2
import pytest
import uvicorn
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

import rslapp
from rslapp import config, people, server
from rslapp.auth import AuthStore

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

EXPECTED_TOOLS = {
    "search_works",
    "find_work",
    "get_related_works",
    "repeat_search",
    "get_list",
    "get_search_log",
    "export_list",
    "list_sources",
}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Limpa variáveis de ambiente do RSL.app e isola a pasta home do usuário."""
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    fake_home = tmp_path / "fake_home"
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    return fake_home


def _issue_test_bearer_token(resource_url: str) -> str:
    """Cadastra uma pessoa ativa e emite um access token válido para o resource_url informado."""
    people.add("ana")
    store = AuthStore()
    tokens = store.issue_token_pair(
        person_id="ana",
        client_id="test-client",
        scopes=["rsl"],
        resource=resource_url,
    )
    return tokens.access_token


@contextlib.contextmanager
def _running_http_server(
    *,
    public_url: str | None = None,
    forwarded_allow_ips: str = "127.0.0.1",
) -> Iterator[int]:
    """Sobe um servidor uvicorn real em 127.0.0.1 numa porta livre e encerra no fim."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])

    http_cfg = config.HttpConfig(
        host="127.0.0.1",
        port=port,
        public_url=public_url if public_url is not None else f"http://127.0.0.1:{port}",
        forwarded_allow_ips=forwarded_allow_ips,
    )
    uvicorn_cfg = server.build_uvicorn_config(http_cfg)
    uv_server = uvicorn.Server(uvicorn_cfg)

    thread = threading.Thread(
        target=uv_server.run,
        kwargs={"sockets": [sock]},
        daemon=True,
    )
    thread.start()

    try:
        deadline = time.monotonic() + 5.0
        while not uv_server.started:
            if not thread.is_alive():
                raise RuntimeError("O servidor uvicorn encerrou antes de iniciar")
            if time.monotonic() > deadline:
                raise TimeoutError("Tempo esgotado aguardando o servidor uvicorn iniciar")
            time.sleep(0.01)
        yield port
    finally:
        uv_server.should_exit = True
        thread.join(timeout=5.0)
        sock.close()


# D-011, D-015, D-006, D-002: Servidor HTTP em porta livre lista as 8 ferramentas, o prompt e responde list_sources igual ao stdio
@pytest.mark.anyio
async def test_d011_serve_lista_ferramentas_por_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _running_http_server() as port:
        url = f"http://127.0.0.1:{port}/mcp"
        token = _issue_test_bearer_token(url)
        async with (
            httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"}) as auth_http,
            Client(streamable_http_client(url, http_client=auth_http)) as http_client,
            Client(server.mcp) as stdio_client,
        ):
            assert http_client.instructions == server.INSTRUCTIONS
            assert http_client.instructions == stdio_client.instructions

            http_tools = await http_client.list_tools()
            stdio_tools = await stdio_client.list_tools()
            http_tool_names = [t.name for t in http_tools.tools]
            stdio_tool_names = [t.name for t in stdio_tools.tools]
            assert set(http_tool_names) == EXPECTED_TOOLS
            assert http_tool_names == stdio_tool_names

            http_prompts = await http_client.list_prompts()
            stdio_prompts = await stdio_client.list_prompts()
            assert [p.name for p in http_prompts.prompts] == ["plan_search"]
            assert [p.name for p in http_prompts.prompts] == [
                p.name for p in stdio_prompts.prompts
            ]

            res_http_sem_chave = await http_client.call_tool("list_sources", {})
            res_stdio_sem_chave = await stdio_client.call_tool("list_sources", {})
            assert res_http_sem_chave.is_error is False
            assert res_http_sem_chave.structured_content == res_stdio_sem_chave.structured_content

            monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
            res_http_com_chave = await http_client.call_tool("list_sources", {})
            res_stdio_com_chave = await stdio_client.call_tool("list_sources", {})
            assert res_http_com_chave.is_error is False
            assert res_http_com_chave.structured_content == res_stdio_com_chave.structured_content
            assert "fake-key-123" not in res_http_com_chave.model_dump_json()


# D-011, D-017: Chamada com Host estranho a RSL_PUBLIC_URL recebe 421; com Host igual a RSL_PUBLIC_URL passa
@pytest.mark.anyio
async def test_d011_d017_protecao_host_recusa_dominio_estranho_com_421_e_aceita_rsl_public_url() -> None:
    public_url = "https://rsl.exemplo.org"
    token = _issue_test_bearer_token(f"{public_url}/mcp")
    with _running_http_server(public_url=public_url) as port:
        url = f"http://127.0.0.1:{port}/mcp"
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }

        async with httpx.AsyncClient() as raw_client:
            # Host fora de RSL_PUBLIC_URL e de loopback -> 421 Misdirected Request
            resp_estranho = await raw_client.post(
                url,
                json=init_payload,
                headers={
                    "Host": "intruso.exemplo.com",
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
            )
            assert resp_estranho.status_code == 421

            resp_estranho_porta = await raw_client.post(
                url,
                json=init_payload,
                headers={
                    "Host": "intruso.exemplo.com:8000",
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
            )
            assert resp_estranho_porta.status_code == 421

            # Host igual ao domínio de RSL_PUBLIC_URL (forma pura e com porta :*) -> aceito
            resp_publico_puro = await raw_client.post(
                url,
                json=init_payload,
                headers={
                    "Host": "rsl.exemplo.org",
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
            )
            assert resp_publico_puro.status_code == 200

            resp_publico_porta = await raw_client.post(
                url,
                json=init_payload,
                headers={
                    "Host": "rsl.exemplo.org:8443",
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
            )
            assert resp_publico_porta.status_code == 200

        # Cliente MCP completo enviando Host igual ao domínio de RSL_PUBLIC_URL conecta e lista ferramentas
        async with (
            httpx2.AsyncClient(
                headers={
                    "Host": "rsl.exemplo.org",
                    "Authorization": f"Bearer {token}",
                }
            ) as custom_http,
            Client(streamable_http_client(url, http_client=custom_http)) as mcp_client,
        ):
            tools = await mcp_client.list_tools()
            assert {t.name for t in tools.tools} == EXPECTED_TOOLS


# D-011, D-017: uvicorn.Config habilita proxy_headers e forwarded_allow_ips num processo único
def test_d011_d017_build_uvicorn_config_habilita_proxy_headers_e_forwarded_allow_ips() -> None:
    http_cfg = config.HttpConfig(
        host="127.0.0.1",
        port=8000,
        public_url="https://rsl.exemplo.org",
        forwarded_allow_ips="172.18.0.1",
    )
    uv_cfg = server.build_uvicorn_config(http_cfg)

    assert uv_cfg.host == "127.0.0.1"
    assert uv_cfg.port == 8000
    assert uv_cfg.proxy_headers is True
    assert uv_cfg.forwarded_allow_ips == "172.18.0.1"
    assert uv_cfg.workers == 1

    uv_cfg.load()
    assert isinstance(uv_cfg.loaded_app, ProxyHeadersMiddleware)


# D-011, D-015: server.run_http recusa hosts fora de loopback quando RSL_PUBLIC_URL usa http://
def test_d011_run_http_recusa_host_fora_de_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        uvicorn,
        "Server",
        lambda *_a, **_kw: pytest.fail("uvicorn.Server não deveria ser instanciado"),
    )
    with pytest.raises(ValueError, match="loopback"):
        server.run_http(host="0.0.0.0", port=8000)


# D-015, D-017: server.run_http aceita host 0.0.0.0 quando RSL_PUBLIC_URL começa com https://
def test_d015_run_http_aceita_host_0000_quando_rsl_public_url_usa_https(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RSL_PUBLIC_URL", "https://exemplo.org")
    started_hosts: list[tuple[str, int]] = []

    class _FakeUvicornServer:
        def __init__(self, cfg: uvicorn.Config) -> None:
            started_hosts.append((cfg.host, cfg.port))

        async def serve(self) -> None:
            return None

    monkeypatch.setattr(uvicorn, "Server", _FakeUvicornServer)
    server.run_http(host="0.0.0.0", port=8000)
    assert started_hosts == [("0.0.0.0", 8000)]


# D-011, D-017: GET /health devolve 200 com status e version e nenhum outro dado
@pytest.mark.anyio
async def test_d011_d017_health_devolve_200_com_status_e_version_e_nada_mais(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
    with _running_http_server() as port:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://127.0.0.1:{port}/health")
            assert resp.status_code == 200
            dados = resp.json()
            assert set(dados.keys()) == {"status", "version"}
            assert dados == {"status": "ok", "version": rslapp.__version__}
            assert "fake-key-123" not in resp.text


# D-011, D-017: Todas as rotas HTTP (/login, /authorize, metadados OAuth, /downloads/{token}, /health) recusam Host estranho com 421
@pytest.mark.anyio
async def test_d011_d017_protecao_host_todas_as_rotas_recusam_dominio_estranho_com_421() -> None:
    public_url = "https://rsl.exemplo.org"
    http_cfg = config.HttpConfig(host="127.0.0.1", port=8000, public_url=public_url)
    app = server.create_http_app(http_cfg)

    routes_to_test = [
        "/health",
        "/login",
        "/authorize",
        "/downloads/fake-token-123",
        "/.well-known/oauth-authorization-server",
        "/.well-known/oauth-protected-resource",
    ]

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url=public_url
    ) as client:
        for path in routes_to_test:
            # Host estranho -> 421
            resp_estranho = await client.get(
                path,
                headers={"Host": "intruso.exemplo.com"},
            )
            assert resp_estranho.status_code == 421, f"Falha na rota {path} com host estranho"

            # Domínio público de RSL_PUBLIC_URL -> responde normalmente (não 421)
            resp_publico = await client.get(
                path,
                headers={"Host": "rsl.exemplo.org"},
            )
            assert resp_publico.status_code != 421, f"Falha na rota {path} com host público"

            # Loopback 127.0.0.1:8000 -> responde normalmente (não 421)
            resp_loopback = await client.get(
                path,
                headers={"Host": "127.0.0.1:8000"},
            )
            assert resp_loopback.status_code != 421, f"Falha na rota {path} com host loopback"

