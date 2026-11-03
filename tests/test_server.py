"""Testes do servidor MCP mínimo do RSL.app."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters

from rslapp import server

ENV_VARS = (
    "RSL_DATA_DIR",
    "RSL_EXPORT_DIR",
    "RSL_CACHE_DAYS",
    "OPENALEX_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "RSL_CONTACT_EMAIL",
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Limpa variáveis do RSL.app e isola a pasta home do usuário."""
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    fake_home = tmp_path / "fake_home"
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    return fake_home


def _build_stdio_env(tmp_path: Path, **overrides: str) -> dict[str, str]:
    """Monta ambiente limpo para subprocesso no Windows e POSIX."""
    env: dict[str, str] = {}
    for var in ("SYSTEMROOT", "PATH", "USERPROFILE"):
        if var in os.environ:
            env[var] = os.environ[var]
    env.setdefault("USERPROFILE", str(tmp_path))
    env["HOME"] = str(tmp_path)
    env.update(overrides)
    return env


# D-002, D-006, NFR-02: Handshake real por stdio usando o comando instalado rslapp
@pytest.mark.anyio
async def test_d002_d006_nfr02_handshake_stdio_comando_rslapp(tmp_path: Path) -> None:
    rslapp_cmd = shutil.which("rslapp")
    assert rslapp_cmd is not None, (
        "Comando 'rslapp' não encontrado no PATH; instale o pacote antes de rodar os testes"
    )

    params = StdioServerParameters(
        command=rslapp_cmd,
        env=_build_stdio_env(tmp_path),
    )
    async with Client(params) as client:
        assert client.instructions is not None
        assert client.instructions == server.INSTRUCTIONS
        assert "planeje" in client.instructions.lower()
        assert "dados" in client.instructions.lower()
