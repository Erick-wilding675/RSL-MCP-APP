"""Testes da exportação por link temporário assinado e da rota GET /downloads/{token} (D-014, FR-06, D-012)."""

from __future__ import annotations

import contextlib
import json
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
import pytest
from mcp import Client

from rslapp import cli, config, downloads, people, server
from rslapp.auth import AuthStore
from rslapp.core.models import Author, SourceResult, Work

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
    "RSL_SECRET_KEY",
    "RSL_DOWNLOAD_TTL_MINUTES",
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


class FakeOpenAlexSource:
    """Fonte OpenAlex simulada sem rede para criar listas nos testes de exportação."""

    name = "openalex"
    needs_key = True

    def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
        return {"search": query.strip(), "max_results": max_results}

    async def search(self, query: str, max_results: int) -> SourceResult:
        works = [
            Work(
                title=f"Artigo sobre {query}",
                doi="10.1234/artigo.2026",
                year=2026,
                venue="Revista de Teste",
                authors=[Author(name="Autora Teste")],
                references=[],
                references_count=0,
                citations={"openalex": 5},
                source_ids={"openalex": "W100"},
            )
        ]
        return SourceResult(
            name="openalex",
            status="ok",
            query=f"search={query} · per_page={max_results}",
            found=1,
            fetched=1,
            works=works,
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
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments or {}},
        },
        headers=call_headers,
    )
    assert call_resp.status_code == 200
    return _extract_jsonrpc_body(call_resp)["result"]


def _issue_person_token(data_dir: Path, person_id: str) -> str:
    if people.get(person_id, data_dir=data_dir) is None:
        people.add(person_id, data_dir=data_dir)
    return AuthStore(data_dir=data_dir).issue_token_pair(
        person_id=person_id,
        client_id=f"c-{person_id}",
        scopes=["rsl"],
        resource=f"{PUBLIC_URL}/mcp",
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


def _flip_char(text: str, idx: int) -> str:
    ch = text[idx]
    replacement = "a" if ch != "a" else "b"
    return f"{text[:idx]}{replacement}{text[idx + 1 :]}"


# D-014, FR-06, D-012: No modo HTTP, export_list em RIS devolve download_url e expires_at sem path e baixa o arquivo
@pytest.mark.anyio
async def test_d014_fr06_http_export_list_ris_devolve_download_url_e_expires_at_sem_path_e_baixa_arquivo(
    monkeypatch: pytest.MonkeyPatch, isolated_env: tuple[Path, Path]
) -> None:
    data_dir, _ = isolated_env
    monkeypatch.setattr(server, "_build_sources", lambda: [FakeOpenAlexSource()])
    maria_token = _issue_person_token(data_dir, "maria")

    now_fixed = datetime(2026, 11, 10, 15, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(downloads, "_now_utc", lambda: now_fixed)

    async with _http_app_client() as client:
        await _call_http_tool(
            client, maria_token, "search_works", {"query": "vosviewer", "sources": ["openalex"]}
        )
        exp_res = await _call_http_tool(
            client, maria_token, "export_list", {"list_id": "l-0001", "format": "ris"}
        )
        assert exp_res.get("isError") is not True
        payload = exp_res["structuredContent"]

        assert "path" not in payload
        assert payload["format"] == "ris"
        assert payload["count"] == 1
        assert payload["download_url"].startswith(f"{PUBLIC_URL}/downloads/")
        assert payload["expires_at"] == "2026-11-10T16:00:00Z"

        saved_file = data_dir / "people" / "maria" / "exports" / "l-0001.ris"
        assert saved_file.is_file()

        dl_path = urlsplit(payload["download_url"]).path
        dl_resp = await client.get(dl_path)
        assert dl_resp.status_code == 200
        assert dl_resp.content == saved_file.read_bytes()
        assert "attachment" in dl_resp.headers.get("content-disposition", "")
        assert 'filename="l-0001.ris"' in dl_resp.headers.get("content-disposition", "")
        assert dl_resp.headers.get("cache-control") == "no-store"


# D-014, FR-06: O link baixa nos cinco formatos com o Content-Type certo e preserva url em openalex_url
@pytest.mark.anyio
async def test_d014_fr06_link_baixa_nos_cinco_formatos_com_tipo_de_conteudo_certo(
    monkeypatch: pytest.MonkeyPatch, isolated_env: tuple[Path, Path]
) -> None:
    data_dir, _ = isolated_env
    monkeypatch.setattr(server, "_build_sources", lambda: [FakeOpenAlexSource()])
    maria_token = _issue_person_token(data_dir, "maria")

    expected_types = {
        "ris": ("l-0001.ris", "application/x-research-info-systems; charset=utf-8"),
        "csv": ("l-0001.csv", "text/csv; charset=utf-8"),
        "json": ("l-0001.json", "application/json; charset=utf-8"),
        "dois": ("l-0001.dois.txt", "text/plain; charset=utf-8"),
        "openalex_url": ("l-0001.openalex.txt", "text/plain; charset=utf-8"),
    }

    async with _http_app_client() as client:
        await _call_http_tool(
            client, maria_token, "search_works", {"query": "bibliometrics", "sources": ["openalex"]}
        )
        for fmt, (expected_filename, expected_mime) in expected_types.items():
            exp_res = await _call_http_tool(
                client, maria_token, "export_list", {"list_id": "l-0001", "format": fmt}
            )
            assert exp_res.get("isError") is not True
            payload = exp_res["structuredContent"]
            assert "path" not in payload
            assert payload["format"] == fmt
            assert payload["download_url"].startswith(f"{PUBLIC_URL}/downloads/")
            assert "expires_at" in payload
            if fmt == "openalex_url":
                assert payload["url"].startswith("https://api.openalex.org/works?filter=openalex:")

            saved_path = data_dir / "people" / "maria" / "exports" / expected_filename
            assert saved_path.is_file()

            dl_resp = await client.get(urlsplit(payload["download_url"]).path)
            assert dl_resp.status_code == 200
            assert dl_resp.headers.get("content-type") == expected_mime
            assert f'attachment; filename="{expected_filename}"' == dl_resp.headers.get(
                "content-disposition"
            )
            assert dl_resp.headers.get("cache-control") == "no-store"
            assert dl_resp.content == saved_path.read_bytes()


# D-014: Link vencido (relógio adiantado no teste) recebe 410 em português; link com 1 caractere trocado recebe 404
@pytest.mark.anyio
async def test_d014_link_vencido_recebe_410_e_link_com_caractere_trocado_recebe_404(
    monkeypatch: pytest.MonkeyPatch, isolated_env: tuple[Path, Path]
) -> None:
    data_dir, _ = isolated_env
    people.add("maria", data_dir=data_dir)
    exports_dir = data_dir / "people" / "maria" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    (exports_dir / "l-0001.ris").write_bytes(b"TY  - JOUR\r\nER  - \r\n")

    now_box = [datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)]
    monkeypatch.setattr(downloads, "_now_utc", lambda: now_box[0])

    token, _ = downloads.sign_download_token("maria", "l-0001.ris", data_dir=data_dir)

    async with _http_app_client() as client:
        for pos in (0, len(token) // 2, len(token) - 1):
            tampered = _flip_char(token, pos)
            resp_bad = await client.get(f"/downloads/{tampered}")
            assert resp_bad.status_code == 404

        now_box[0] = now_box[0] + timedelta(minutes=61)
        resp_expired = await client.get(f"/downloads/{token}")
        assert resp_expired.status_code == 410
        assert "exportação" in resp_expired.text.lower()
        assert resp_expired.headers.get("cache-control") == "no-store"


# D-014, D-012: Token assinado direito apontando para ../, caminho absoluto ou pasta de outra pessoa recebe 404
@pytest.mark.anyio
async def test_d014_d012_token_assinado_apontando_para_fora_ou_outra_pessoa_recebe_404(
    isolated_env: tuple[Path, Path]
) -> None:
    data_dir, _ = isolated_env
    people.add("maria", data_dir=data_dir)
    people.add("joao", data_dir=data_dir)

    maria_exports = data_dir / "people" / "maria" / "exports"
    joao_exports = data_dir / "people" / "joao" / "exports"
    maria_exports.mkdir(parents=True, exist_ok=True)
    joao_exports.mkdir(parents=True, exist_ok=True)

    (data_dir / "people" / "maria" / "log.md").write_text("segredo maria", encoding="utf-8")
    joao_file = joao_exports / "l-0001.ris"
    joao_file.write_bytes(b"TY  - JOUR\r\nTI  - Do Joao\r\nER  - \r\n")

    outside_file = data_dir / "fora.ris"
    outside_file.write_text("fora", encoding="utf-8")

    candidates = [
        downloads.sign_download_token("maria", "../log.md", data_dir=data_dir)[0],
        downloads.sign_download_token("maria", "..\\log.md", data_dir=data_dir)[0],
        downloads.sign_download_token("maria", "../../fora.ris", data_dir=data_dir)[0],
        downloads.sign_download_token("maria", str(outside_file.resolve()), data_dir=data_dir)[0],
        downloads.sign_download_token("maria", "/etc/passwd", data_dir=data_dir)[0],
        downloads.sign_download_token("maria", "../../joao/exports/l-0001.ris", data_dir=data_dir)[0],
        downloads.sign_download_token("maria", str(joao_file.resolve()), data_dir=data_dir)[0],
        downloads.sign_download_token("maria", "l-0001.ris", data_dir=data_dir)[0],
        downloads.sign_download_token("../joao", "l-0001.ris", data_dir=data_dir)[0],
    ]

    async with _http_app_client() as client:
        for tok in candidates:
            resp = await client.get(f"/downloads/{tok}")
            assert resp.status_code == 404


# D-014, D-012, D-016: Depois de token revoke da pessoa, os links dela deixam de baixar
@pytest.mark.anyio
async def test_d014_d012_d016_depois_de_token_revoke_links_da_pessoa_deixam_de_baixar(
    isolated_env: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    data_dir, _ = isolated_env
    people.add("maria", data_dir=data_dir)
    exports_dir = data_dir / "people" / "maria" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    (exports_dir / "l-0001.ris").write_bytes(b"TY  - JOUR\r\nER  - \r\n")

    token, _ = downloads.sign_download_token("maria", "l-0001.ris", data_dir=data_dir)

    async with _http_app_client() as client:
        ok_resp = await client.get(f"/downloads/{token}")
        assert ok_resp.status_code == 200

        cli.main(["token", "revoke", "maria"])
        capsys.readouterr()

        revoked_resp = await client.get(f"/downloads/{token}")
        assert revoked_resp.status_code == 404


# D-014, D-007: Sem RSL_SECRET_KEY, a chave é criada uma vez em auth/secret.key e reaproveitada após reiniciar
@pytest.mark.anyio
async def test_d014_sem_rsl_secret_key_cria_uma_vez_e_reaproveita_apos_reiniciar(
    monkeypatch: pytest.MonkeyPatch, isolated_env: tuple[Path, Path]
) -> None:
    data_dir, _ = isolated_env
    people.add("maria", data_dir=data_dir)
    exports_dir = data_dir / "people" / "maria" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    expected_bytes = b"TY  - JOUR\r\nTI  - Persistencia\r\nER  - \r\n"
    (exports_dir / "l-0001.ris").write_bytes(expected_bytes)

    secret_file = data_dir / "auth" / "secret.key"
    assert not secret_file.exists()

    async with _http_app_client() as client_1:
        assert secret_file.is_file()
        key_before = secret_file.read_bytes()
        assert len(key_before.strip()) >= 32
        token, _ = downloads.sign_download_token("maria", "l-0001.ris", data_dir=data_dir)
        resp_1 = await client_1.get(f"/downloads/{token}")
        assert resp_1.status_code == 200
        assert resp_1.content == expected_bytes

    async with _http_app_client() as client_2:
        assert secret_file.read_bytes() == key_before
        resp_2 = await client_2.get(f"/downloads/{token}")
        assert resp_2.status_code == 200
        assert resp_2.content == expected_bytes

    monkeypatch.setenv("RSL_SECRET_KEY", "curta-123")
    with pytest.raises(ValueError, match="32 bytes") as exc_info:
        downloads.load_secret_key(data_dir)
    assert "curta-123" not in str(exc_info.value)


# D-014, FR-06: No stdio, export_list continua devolvendo path e sem download_url
@pytest.mark.anyio
async def test_d014_fr06_stdio_export_list_continua_com_path_e_sem_download_url(
    monkeypatch: pytest.MonkeyPatch, isolated_env: tuple[Path, Path]
) -> None:
    _, export_dir = isolated_env
    monkeypatch.setattr(server, "_build_sources", lambda: [FakeOpenAlexSource()])

    async with Client(server.mcp) as stdio_client:
        s_res = await stdio_client.call_tool(
            "search_works", {"query": "stdio export", "sources": ["openalex"]}
        )
        assert s_res.is_error is False
        e_res = await stdio_client.call_tool(
            "export_list", {"list_id": "l-0001", "format": "ris"}
        )
        assert e_res.is_error is False
        data = e_res.structured_content
        assert Path(data["path"]) == export_dir / "l-0001.ris"
        assert "download_url" not in data
        assert "expires_at" not in data
