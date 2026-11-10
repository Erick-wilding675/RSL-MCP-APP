"""Testes do link temporário assinado com HMAC-SHA256 e da rota GET /downloads/{token} (D-014, FR-06, D-012)."""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from rslapp import cli, config, downloads, people, server

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

    # Reinicia o servidor HTTP (nova instância de app lendo a mesma pasta de dados)
    async with _http_app_client() as client_2:
        assert secret_file.read_bytes() == key_before
        resp_2 = await client_2.get(f"/downloads/{token}")
        assert resp_2.status_code == 200
        assert resp_2.content == expected_bytes

    # RSL_SECRET_KEY curta (< 32 bytes) é recusada sem expor o valor
    monkeypatch.setenv("RSL_SECRET_KEY", "curta-123")
    with pytest.raises(ValueError, match="32 bytes") as exc_info:
        downloads.load_secret_key(data_dir)
    assert "curta-123" not in str(exc_info.value)
