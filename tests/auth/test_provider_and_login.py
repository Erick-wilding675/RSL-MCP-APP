"""Testes do provedor OAuth 2.1, das rotas de autorização e da tela de login."""

from __future__ import annotations

import base64
import hashlib
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from starlette.applications import Starlette

from rslapp import people
from rslapp.auth import AuthStore, RSLOAuthProvider, build_auth_routes


def _pkce_pair(verifier: str = "verificador-pkce-de-teste-com-tamanho-suficiente-12345") -> tuple[str, str]:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def _create_auth_test_app(
    tmp_path: Path,
    *,
    time_box: list[float],
    public_url: str = "http://127.0.0.1:8000",
) -> tuple[Starlette, RSLOAuthProvider]:
    store = AuthStore(data_dir=tmp_path)
    provider = RSLOAuthProvider(
        store,
        public_url=public_url,
        time_fn=lambda: time_box[0],
    )
    routes = build_auth_routes(provider, issuer_url=public_url)
    return Starlette(routes=routes), provider


async def _register_and_start_authorize(
    client: httpx.AsyncClient,
    *,
    client_name: str = "Claude Conector",
    state: str = "estado-123",
) -> tuple[dict[str, object], str, str]:
    reg_resp = await client.post(
        "/register",
        json={
            "client_name": client_name,
            "redirect_uris": ["http://localhost:3030/callback"],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        },
    )
    assert reg_resp.status_code == 201
    client_info = reg_resp.json()

    verifier, challenge = _pkce_pair()
    auth_resp = await client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": client_info["client_id"],
            "redirect_uri": "http://localhost:3030/callback",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
            "scope": "rsl",
        },
    )
    assert auth_resp.status_code == 302
    login_loc = auth_resp.headers["location"]
    parsed_login = urlsplit(login_loc)
    assert parsed_login.path == "/login"
    req_id = parse_qs(parsed_login.query)["req"][0]
    return client_info, req_id, verifier


# D-015: Página de login em português, autocontida (sem CDN/fontes externas) e com o nome do conector
@pytest.mark.anyio
async def test_d015_login_page_is_self_contained_portuguese_and_shows_connector(
    tmp_path: Path,
) -> None:
    time_box = [time.time()]
    app, _ = _create_auth_test_app(tmp_path, time_box=time_box)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
        _, req_id, _ = await _register_and_start_authorize(
            client,
            client_name="Claude Pesquisador",
        )
        page_resp = await client.get("/login", params={"req": req_id})
        assert page_resp.status_code == 200
        html_body = page_resp.text

        assert 'lang="pt-BR"' in html_body
        assert "Claude Pesquisador" in html_body
        assert "Código pessoal" in html_body
        # Sem nenhum ativo externo (CDN, fonte ou script externo)
        assert "http://" not in html_body
        assert "https://" not in html_body
        assert "<script" not in html_body.lower()
        assert "@import" not in html_body.lower()


# D-015, D-016: Código de autorização vale uma vez só e vence em 5 minutos
@pytest.mark.anyio
async def test_d015_d016_authorization_code_is_single_use_and_expires_in_5_minutes(
    tmp_path: Path,
) -> None:
    ana_code = people.add("ana", data_dir=tmp_path)
    time_box = [time.time()]
    app, _ = _create_auth_test_app(tmp_path, time_box=time_box)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
        # 1. Uso único: segunda troca do mesmo code é recusada
        client_info, req_id, verifier = await _register_and_start_authorize(client)
        login_resp = await client.post(
            "/login",
            data={"req": req_id, "code": ana_code},
        )
        assert login_resp.status_code == 302
        cb_parsed = urlsplit(login_resp.headers["location"])
        cb_params = parse_qs(cb_parsed.query)
        assert cb_params["state"] == ["estado-123"]
        auth_code = cb_params["code"][0]

        first_token_resp = await client.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": client_info["client_id"],
                "redirect_uri": "http://localhost:3030/callback",
                "code_verifier": verifier,
            },
        )
        assert first_token_resp.status_code == 200

        second_token_resp = await client.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": client_info["client_id"],
                "redirect_uri": "http://localhost:3030/callback",
                "code_verifier": verifier,
            },
        )
        assert second_token_resp.status_code == 400
        assert second_token_resp.json()["error"] == "invalid_grant"

        # 2. Vencimento em 5 minutos (300s)
        client_info_2, req_id_2, verifier_2 = await _register_and_start_authorize(client)
        login_resp_2 = await client.post(
            "/login",
            data={"req": req_id_2, "code": ana_code},
        )
        assert login_resp_2.status_code == 302
        auth_code_2 = parse_qs(urlsplit(login_resp_2.headers["location"]).query)["code"][0]

        # Avança 301 segundos (além dos 5 minutos)
        time_box[0] += 301.0
        expired_resp = await client.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code_2,
                "client_id": client_info_2["client_id"],
                "redirect_uri": "http://localhost:3030/callback",
                "code_verifier": verifier_2,
            },
        )
        assert expired_resp.status_code == 400
        assert expired_resp.json()["error"] == "invalid_grant"


# D-015, D-012: 5 códigos errados no mesmo pedido levam a 429; erro não diz se a pessoa existe
@pytest.mark.anyio
async def test_d015_five_wrong_codes_return_429_and_error_does_not_leak_person_existence(
    tmp_path: Path,
) -> None:
    active_code = people.add("ana", data_dir=tmp_path)
    revoked_code = people.add("beto", data_dir=tmp_path)
    people.revoke("beto", data_dir=tmp_path)

    time_box = [time.time()]
    app, _ = _create_auth_test_app(tmp_path, time_box=time_box)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
        _, req_id, _ = await _register_and_start_authorize(client)

        # Tentativa 1: código totalmente inexistente
        wrong_unknown = "rsl_inexistente_999999999999"
        resp_1 = await client.post("/login", data={"req": req_id, "code": wrong_unknown})
        assert resp_1.status_code == 200

        # Tentativa 2: código de pessoa revogada (beto)
        resp_2 = await client.post("/login", data={"req": req_id, "code": revoked_code})
        assert resp_2.status_code == 200

        # A página de erro é idêntica nos dois casos e não revela se a pessoa existe nem ecoa o código
        assert resp_1.text == resp_2.text
        assert "Código inválido" in resp_1.text
        assert wrong_unknown not in resp_1.text
        assert revoked_code not in resp_1.text
        assert "Beto" not in resp_1.text
        assert "beto" not in resp_1.text
        assert "Ana" not in resp_1.text
        assert "ana" not in resp_1.text

        # Tentativas 3 e 4 erradas continuam mostrando a página de erro
        resp_3 = await client.post("/login", data={"req": req_id, "code": "errado-3"})
        assert resp_3.status_code == 200
        resp_4 = await client.post("/login", data={"req": req_id, "code": "errado-4"})
        assert resp_4.status_code == 200

        # 5ª tentativa errada no mesmo pedido devolve HTTP 429 em português
        resp_5 = await client.post("/login", data={"req": req_id, "code": "errado-5"})
        assert resp_5.status_code == 429
        assert "tentativas" in resp_5.text.lower()

        # Mesmo com o código certo depois disso, o pedido bloqueado continua em 429
        resp_6 = await client.post("/login", data={"req": req_id, "code": active_code})
        assert resp_6.status_code == 429


# D-015: Limite de 20 códigos errados por IP a cada 15 minutos mantido apenas em memória
@pytest.mark.anyio
async def test_d015_twenty_wrong_codes_per_ip_in_15_minutes_returns_429_in_memory_only(
    tmp_path: Path,
) -> None:
    people.add("ana", data_dir=tmp_path)
    time_box = [time.time()]
    app, _ = _create_auth_test_app(tmp_path, time_box=time_box)

    transport = httpx.ASGITransport(app=app, client=("198.51.100.42", 54321))
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
        statuses: list[int] = []
        # 5 pedidos diferentes x 4 tentativas erradas cada = 20 tentativas erradas no mesmo IP
        for _ in range(5):
            _, req_id, _ = await _register_and_start_authorize(client)
            for attempt in range(4):
                resp = await client.post(
                    "/login",
                    data={"req": req_id, "code": f"errado-{attempt}"},
                )
                statuses.append(resp.status_code)

        assert statuses[:-1] == [200] * 19
        assert statuses[-1] == 429

        # Novo pedido do mesmo IP dentro dos 15 minutos recebe 429 imediatamente
        _, blocked_req, _ = await _register_and_start_authorize(client)
        get_blocked = await client.get("/login", params={"req": blocked_req})
        assert get_blocked.status_code == 429

        # O IP nunca é gravado em nenhum arquivo de <RSL_DATA_DIR>/auth/
        auth_dir = tmp_path / "auth"
        for file_path in auth_dir.iterdir():
            if file_path.is_file():
                assert "198.51.100.42" not in file_path.read_text(encoding="utf-8")

        # Após 15 minutos (901s), o bloqueio em memória expira
        time_box[0] += 901.0
        _, fresh_req, _ = await _register_and_start_authorize(client)
        get_fresh = await client.get("/login", params={"req": fresh_req})
        assert get_fresh.status_code == 200
