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


def _require_rslapp_command() -> str:
    """Obtém o caminho do comando instalado rslapp ou falha com mensagem clara."""
    rslapp_cmd = shutil.which("rslapp")
    assert rslapp_cmd is not None, (
        "Comando 'rslapp' não encontrado no PATH; instale o pacote antes de rodar os testes"
    )
    return rslapp_cmd


# D-002, D-006, FR-07, NFR-02: Handshake real por stdio em subprocesso com list_tools e list_sources
@pytest.mark.anyio
async def test_d002_d006_fr07_nfr02_handshake_stdio_e_list_sources_sem_chaves(
    tmp_path: Path,
) -> None:
    rslapp_cmd = _require_rslapp_command()
    params = StdioServerParameters(
        command=rslapp_cmd,
        env=_build_stdio_env(tmp_path),
    )

    async with Client(params) as client:
        assert client.instructions is not None
        assert client.instructions == server.INSTRUCTIONS
        assert "planeje" in client.instructions.lower()
        assert "dados" in client.instructions.lower()

        tools_result = await client.list_tools()
        tool_names = [t.name for t in tools_result.tools]
        assert "list_sources" in tool_names

        call_result = await client.call_tool("list_sources", {})
        assert call_result.is_error is False
        assert call_result.structured_content == {
            "result": [
                {
                    "name": "openalex",
                    "configured": False,
                    "needs_key": True,
                    "status": "missing_key",
                },
                {
                    "name": "crossref",
                    "configured": True,
                    "needs_key": False,
                    "status": "ok",
                },
                {
                    "name": "semantic_scholar",
                    "configured": True,
                    "needs_key": False,
                    "status": "ok",
                },
                {
                    "name": "europe_pmc",
                    "configured": True,
                    "needs_key": False,
                    "status": "ok",
                },
                {
                    "name": "pubmed",
                    "configured": True,
                    "needs_key": False,
                    "status": "ok",
                },
            ]
        }


# FR-07, NFR-03, D-002: Com chaves configuradas no subprocesso stdio, nenhuma resposta expõe chaves
@pytest.mark.anyio
async def test_fr07_nfr03_d002_stdio_com_chaves_nao_expoe_valores_e_marca_openalex_configurado(
    tmp_path: Path,
) -> None:
    rslapp_cmd = _require_rslapp_command()
    fake_oa_key = "fake-key-123"
    fake_s2_key = "fake-key-456"
    fake_email = "pesquisador@exemplo.org"

    params = StdioServerParameters(
        command=rslapp_cmd,
        env=_build_stdio_env(
            tmp_path,
            OPENALEX_API_KEY=fake_oa_key,
            SEMANTIC_SCHOLAR_API_KEY=fake_s2_key,
            RSL_CONTACT_EMAIL=fake_email,
        ),
    )

    async with Client(params) as client:
        instructions_text = client.instructions or ""
        tools_result = await client.list_tools()
        call_result = await client.call_tool("list_sources", {})

        assert call_result.is_error is False
        assert call_result.structured_content == {
            "result": [
                {
                    "name": "openalex",
                    "configured": True,
                    "needs_key": True,
                    "status": "ok",
                },
                {
                    "name": "crossref",
                    "configured": True,
                    "needs_key": False,
                    "status": "ok",
                },
                {
                    "name": "semantic_scholar",
                    "configured": True,
                    "needs_key": False,
                    "status": "ok",
                },
                {
                    "name": "europe_pmc",
                    "configured": True,
                    "needs_key": False,
                    "status": "ok",
                },
                {
                    "name": "pubmed",
                    "configured": True,
                    "needs_key": False,
                    "status": "ok",
                },
            ]
        }

        payload_completo = " ".join(
            [
                instructions_text,
                server.INSTRUCTIONS,
                tools_result.model_dump_json(),
                call_result.model_dump_json(),
                str(call_result.structured_content),
                str(call_result.content),
            ]
        )
        for segredo in (fake_oa_key, fake_s2_key, fake_email):
            assert segredo not in payload_completo


# FR-07, D-002: Sem chaves em memória, OpenAlex exige chave e não está configurado; Crossref está ok
@pytest.mark.anyio
async def test_fr07_d002_list_sources_sem_chaves_em_memoria() -> None:
    async with Client(server.mcp) as client:
        result = await client.call_tool("list_sources", {})
        assert result.is_error is False
        sources = {item["name"]: item for item in result.structured_content["result"]}

        assert set(sources.keys()) == {
            "openalex",
            "crossref",
            "semantic_scholar",
            "europe_pmc",
            "pubmed",
        }
        assert sources["openalex"] == {
            "name": "openalex",
            "configured": False,
            "needs_key": True,
            "status": "missing_key",
        }
        assert sources["crossref"] == {
            "name": "crossref",
            "configured": True,
            "needs_key": False,
            "status": "ok",
        }
        assert sources["semantic_scholar"] == {
            "name": "semantic_scholar",
            "configured": True,
            "needs_key": False,
            "status": "ok",
        }
        assert sources["europe_pmc"] == {
            "name": "europe_pmc",
            "configured": True,
            "needs_key": False,
            "status": "ok",
        }
        assert sources["pubmed"] == {
            "name": "pubmed",
            "configured": True,
            "needs_key": False,
            "status": "ok",
        }


# FR-07, NFR-03: list_sources relê config.load() a cada chamada sem reter nem expor chaves
@pytest.mark.anyio
async def test_fr07_nfr03_list_sources_rele_ambiente_em_cada_chamada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with Client(server.mcp) as client:
        res_sem_chave = await client.call_tool("list_sources", {})
        oa_antes = res_sem_chave.structured_content["result"][0]
        assert oa_antes["name"] == "openalex"
        assert oa_antes["configured"] is False
        assert oa_antes["status"] == "missing_key"

        monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
        monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "fake-key-456")

        res_com_chave = await client.call_tool("list_sources", {})
        oa_depois = res_com_chave.structured_content["result"][0]
        assert oa_depois["name"] == "openalex"
        assert oa_depois["configured"] is True
        assert oa_depois["needs_key"] is True
        assert oa_depois["status"] == "ok"

        texto_resposta = res_com_chave.model_dump_json()
        assert "fake-key-123" not in texto_resposta
        assert "fake-key-456" not in texto_resposta


# D-006, NFR-02: Execução de list_sources não escreve nada em stdout (canal do protocolo stdio)
def test_d006_nfr02_list_sources_nao_escreve_em_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    resultado = server.list_sources()
    capturado = capsys.readouterr()
    assert capturado.out == ""
    assert len(resultado) == 3
