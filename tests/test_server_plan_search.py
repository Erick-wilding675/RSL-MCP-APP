"""Testes do prompt plan_search no servidor MCP do RSL.app."""

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
    """Limpa variáveis de ambiente e define RSL_DATA_DIR em pasta temporária."""
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    data_dir = tmp_path / "rsl_data"
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))
    return data_dir


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


# FR-10, D-002: O prompt plan_search aparece na listagem do servidor com argumento obrigatório
@pytest.mark.anyio
async def test_fr10_d002_list_prompts_traz_plan_search_com_argumento_obrigatorio() -> None:
    async with Client(server.mcp) as client:
        prompts_res = await client.list_prompts()
        prompt_names = [p.name for p in prompts_res.prompts]
        assert "plan_search" in prompt_names

        plan_prompt = next(p for p in prompts_res.prompts if p.name == "plan_search")
        assert plan_prompt.description is not None
        assert len(plan_prompt.description) > 0

        assert plan_prompt.arguments is not None
        arg_names = {a.name: a for a in plan_prompt.arguments}
        assert "request" in arg_names
        assert arg_names["request"].required is True


# FR-10, UC-01, D-002, D-003: get_prompt devolve mensagem de orientação com o pedido delimitado
@pytest.mark.anyio
async def test_fr10_uc01_d002_d003_get_prompt_plan_search_com_pedido_exemplo() -> None:
    async with Client(server.mcp) as client:
        exemplo = "Impacto de modelos de linguagem em tarefas clínicas e biomédicas"
        result = await client.get_prompt("plan_search", {"request": exemplo})

        assert len(result.messages) == 1
        msg = result.messages[0]
        assert msg.role == "user"

        texto = msg.content.text if hasattr(msg.content, "text") else str(msg.content)
        assert "<pedido_pesquisador>" in texto
        assert exemplo in texto
        assert "</pedido_pesquisador>" in texto
        assert "search_works" in texto
        assert "request_summary" in texto
        assert "incomplete" in texto
        assert "dados" in texto.lower()


# FR-10, D-003: get_prompt com pedido vazio ou espaços devolve orientação informando pedido vazio
@pytest.mark.anyio
async def test_fr10_d003_get_prompt_plan_search_pedido_vazio() -> None:
    async with Client(server.mcp) as client:
        result = await client.get_prompt("plan_search", {"request": "   "})

        assert len(result.messages) == 1
        msg = result.messages[0]
        assert msg.role == "user"

        texto = msg.content.text if hasattr(msg.content, "text") else str(msg.content)
        assert "veio vazio" in texto.lower()
        assert "search_works" in texto
        assert "request_summary" in texto


# FR-10, NFR-03, D-002: get_prompt e instruções não expõem chaves configuradas no ambiente
@pytest.mark.anyio
async def test_fr10_nfr03_d002_prompt_e_instrucoes_nao_expoem_chaves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_oa_key = "fake-key-oa-789"
    fake_s2_key = "fake-key-s2-321"
    fake_email = "pesquisador@exemplo.org"

    monkeypatch.setenv("OPENALEX_API_KEY", fake_oa_key)
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", fake_s2_key)
    monkeypatch.setenv("RSL_CONTACT_EMAIL", fake_email)

    async with Client(server.mcp) as client:
        instrucoes = client.instructions or ""
        assert fake_oa_key not in instrucoes
        assert fake_s2_key not in instrucoes
        assert fake_email not in instrucoes

        result = await client.get_prompt("plan_search", {"request": "pesquisa qualquer"})
        msg = result.messages[0]
        texto = msg.content.text if hasattr(msg.content, "text") else str(msg.content)

        assert fake_oa_key not in texto
        assert fake_s2_key not in texto
        assert fake_email not in texto


# FR-10, D-002, D-006: Execução do prompt plan_search via stdio real em subprocesso
@pytest.mark.anyio
async def test_fr10_d002_d006_stdio_list_prompts_e_get_prompt(tmp_path: Path) -> None:
    rslapp_cmd = _require_rslapp_command()
    params = StdioServerParameters(
        command=rslapp_cmd,
        env=_build_stdio_env(tmp_path),
    )

    async with Client(params) as client:
        prompts_res = await client.list_prompts()
        assert "plan_search" in [p.name for p in prompts_res.prompts]

        result = await client.get_prompt("plan_search", {"request": "grafos de conhecimento"})
        assert len(result.messages) == 1
        msg = result.messages[0]
        texto = msg.content.text if hasattr(msg.content, "text") else str(msg.content)
        assert "<pedido_pesquisador>" in texto
        assert "grafos de conhecimento" in texto
        assert "search_works" in texto
