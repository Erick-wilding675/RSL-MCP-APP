"""Testes do fluxo OAuth 2.1 completo sobre o app ASGI (httpx.ASGITransport, sem rede)."""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from rslapp import config, people, server
from rslapp.auth import AuthStore, RSLOAuthProvider

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


def _pkce_pair(verifier: str = "verificador-pkce-completo-para-fluxo-asgi-987654321") -> tuple[str, str]:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def _extract_jsonrpc_body(resp: httpx.Response) -> dict[str, Any]:
    content_type = resp.headers.get("content-type", "")
    if "text/event-stream" in content_type:
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[len("data:") :].strip())
    return resp.json()


# D-015, D-016: Fluxo OAuth 2.1 ponta a ponta via httpx.ASGITransport até listar ferramentas em /mcp
@pytest.mark.anyio
async def test_d015_d016_full_oauth_flow_over_asgi_transport_lists_tools_and_stores_only_hashes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("RSL_DATA_DIR", str(tmp_path))
    ana_code = people.add("ana", data_dir=tmp_path)

    public_url = "http://127.0.0.1:8000"
    http_cfg = config.HttpConfig(host="127.0.0.1", port=8000, public_url=public_url)
    app = server.create_http_app(http_cfg)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=public_url) as client:
        # 1. Chamada a /mcp sem token recebe 401 com WWW-Authenticate apontando os metadados
        unauth_resp = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        assert unauth_resp.status_code == 401
        www_auth = unauth_resp.headers.get("www-authenticate", "")
        assert "/.well-known/oauth-protected-resource/mcp" in www_auth

        # Com token inventado também recebe 401
        invented_resp = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={
                "Authorization": "Bearer token-inventado-invalido-123",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        assert invented_resp.status_code == 401

        # 2. Metadados do recurso protegido (/.well-known/oauth-protected-resource/mcp)
        prm_resp = await client.get("/.well-known/oauth-protected-resource/mcp")
        assert prm_resp.status_code == 200
        prm_data = prm_resp.json()
        assert prm_data["resource"].rstrip("/") == f"{public_url}/mcp"
        assert public_url in [u.rstrip("/") for u in prm_data["authorization_servers"]]
        assert "rsl" in prm_data["scopes_supported"]

        # 3. Metadados do servidor de autorização (/.well-known/oauth-authorization-server)
        as_resp = await client.get("/.well-known/oauth-authorization-server")
        assert as_resp.status_code == 200
        as_data = as_resp.json()
        assert as_data["issuer"].rstrip("/") == public_url
        assert as_data["authorization_endpoint"].rstrip("/") == f"{public_url}/authorize"
        assert as_data["token_endpoint"].rstrip("/") == f"{public_url}/token"
        assert as_data["registration_endpoint"].rstrip("/") == f"{public_url}/register"
        assert as_data["revocation_endpoint"].rstrip("/") == f"{public_url}/revoke"
        assert "S256" in as_data["code_challenge_methods_supported"]

        # 4. Registro automático de cliente (POST /register)
        reg_resp = await client.post(
            "/register",
            json={
                "client_name": "Claude Web",
                "redirect_uris": ["http://localhost:3030/callback"],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
            },
        )
        assert reg_resp.status_code == 201
        client_info = reg_resp.json()
        client_id = client_info["client_id"]
        assert client_info["scope"] == "rsl"

        # 5. GET /authorize redireciona para /login?req=...
        verifier, challenge = _pkce_pair()
        auth_resp = await client.get(
            "/authorize",
            params={
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": "http://localhost:3030/callback",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": "estado-fluxo-completo",
                "scope": "rsl",
                "resource": f"{public_url}/mcp",
            },
        )
        assert auth_resp.status_code == 302
        login_url = auth_resp.headers["location"]
        parsed_login = urlsplit(login_url)
        assert parsed_login.path == "/login"
        req_id = parse_qs(parsed_login.query)["req"][0]

        # 6. GET /login exibe a página em português com o nome do conector
        login_get = await client.get("/login", params={"req": req_id})
        assert login_get.status_code == 200
        assert "Claude Web" in login_get.text

        # 7. POST /login com o código certo redireciona com code e state
        login_post = await client.post(
            "/login",
            data={"req": req_id, "code": ana_code},
        )
        assert login_post.status_code == 302
        callback_parsed = urlsplit(login_post.headers["location"])
        callback_qs = parse_qs(callback_parsed.query)
        assert callback_qs["state"] == ["estado-fluxo-completo"]
        auth_code = callback_qs["code"][0]

        # 8. POST /token com PKCE devolve access_token e refresh_token
        token_resp = await client.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": client_id,
                "redirect_uri": "http://localhost:3030/callback",
                "code_verifier": verifier,
                "resource": f"{public_url}/mcp",
            },
        )
        assert token_resp.status_code == 200
        tokens = token_resp.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        assert tokens["token_type"].lower() == "bearer"
        assert tokens["expires_in"] == 3600

        # 9. Chamada a /mcp com o token de acesso lista as 8 ferramentas
        mcp_resp = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        assert mcp_resp.status_code == 200
        body = _extract_jsonrpc_body(mcp_resp)
        tool_names = {tool["name"] for tool in body["result"]["tools"]}
        assert tool_names == EXPECTED_TOOLS

        # 10. Nenhum arquivo de auth/ contém token, código de autorização ou código pessoal em texto
        auth_dir = tmp_path / "auth"
        assert auth_dir.is_dir()
        for file_path in auth_dir.iterdir():
            if file_path.is_file():
                raw_text = file_path.read_text(encoding="utf-8")
                assert access_token not in raw_text
                assert refresh_token not in raw_text
                assert auth_code not in raw_text
                assert ana_code not in raw_text

        # 11. Revogar a pessoa corta imediatamente tanto /mcp quanto a renovação em /token
        people.revoke("ana", data_dir=tmp_path)
        revoked_mcp = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        assert revoked_mcp.status_code == 401

        revoked_refresh = await client.post(
            "/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
            },
        )
        assert revoked_refresh.status_code == 400


# D-016: Token de acesso vencido é recusado em /mcp, e a renovação por /token continua funcionando
@pytest.mark.anyio
async def test_d016_expired_access_token_is_rejected_and_refresh_rotates_over_http(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("RSL_DATA_DIR", str(tmp_path))
    now_box = [datetime.now(timezone.utc)]
    time_box = [now_box[0].timestamp()]
    monkeypatch.setattr(people, "_now_utc", lambda: now_box[0])

    ana_code = people.add("ana", data_dir=tmp_path)
    now_box[0] = now_box[0] + timedelta(seconds=1)
    time_box[0] = now_box[0].timestamp()

    public_url = "http://127.0.0.1:8000"
    store = AuthStore(
        data_dir=tmp_path,
        access_token_minutes=60,
        clock=lambda: now_box[0],
    )
    provider = RSLOAuthProvider(
        store,
        public_url=public_url,
        time_fn=lambda: time_box[0],
    )
    http_cfg = config.HttpConfig(host="127.0.0.1", port=8000, public_url=public_url)
    app = server.create_http_app(http_cfg, auth_store=store, oauth_provider=provider)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=public_url) as client:
        reg_resp = await client.post(
            "/register",
            json={
                "client_name": "Claude",
                "redirect_uris": ["http://localhost:3030/callback"],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
            },
        )
        client_id = reg_resp.json()["client_id"]
        verifier, challenge = _pkce_pair()
        auth_resp = await client.get(
            "/authorize",
            params={
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": "http://localhost:3030/callback",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": "s1",
            },
        )
        req_id = parse_qs(urlsplit(auth_resp.headers["location"]).query)["req"][0]
        login_resp = await client.post("/login", data={"req": req_id, "code": ana_code})
        auth_code = parse_qs(urlsplit(login_resp.headers["location"]).query)["code"][0]

        token_resp = await client.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": client_id,
                "redirect_uri": "http://localhost:3030/callback",
                "code_verifier": verifier,
            },
        )
        initial_tokens = token_resp.json()
        access_1 = initial_tokens["access_token"]
        refresh_1 = initial_tokens["refresh_token"]

        # Adianta o relógio em 61 minutos: o access token vence
        now_box[0] = now_box[0] + timedelta(minutes=61)
        time_box[0] = now_box[0].timestamp()

        expired_mcp = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={
                "Authorization": f"Bearer {access_1}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        assert expired_mcp.status_code == 401

        # A renovação continua funcionando e devolve um par novo
        refresh_resp = await client.post(
            "/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_1,
                "client_id": client_id,
            },
        )
        assert refresh_resp.status_code == 200
        new_tokens = refresh_resp.json()
        access_2 = new_tokens["access_token"]
        refresh_2 = new_tokens["refresh_token"]
        assert access_2 != access_1
        assert refresh_2 != refresh_1

        # O refresh token antigo é recusado na hora
        old_refresh_resp = await client.post(
            "/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_1,
                "client_id": client_id,
            },
        )
        assert old_refresh_resp.status_code == 400
        assert old_refresh_resp.json()["error"] == "invalid_grant"

        # O novo access token funciona em /mcp
        ok_mcp = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            headers={
                "Authorization": f"Bearer {access_2}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        assert ok_mcp.status_code == 200

        # Depois de replace_code (token add --replace), tanto access_2 quanto refresh_2 deixam de valer na hora
        people.replace_code("ana", data_dir=tmp_path)
        replaced_mcp = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}},
            headers={
                "Authorization": f"Bearer {access_2}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        assert replaced_mcp.status_code == 401

        replaced_refresh = await client.post(
            "/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_2,
                "client_id": client_id,
            },
        )
        assert replaced_refresh.status_code == 400
