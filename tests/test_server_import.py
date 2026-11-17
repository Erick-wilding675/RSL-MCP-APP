"""Testes de integração da ferramenta MCP import_works (FR-23, D-002, D-006, D-029, D-033)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp import Client

from rslapp import server
from rslapp.store import Store

ENV_VARS = (
    "RSL_DATA_DIR",
    "RSL_EXPORT_DIR",
    "RSL_CACHE_DAYS",
    "RSL_HTTP_HOST",
    "RSL_HTTP_PORT",
    "RSL_PUBLIC_URL",
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    data_dir = tmp_path / "rsl_data"
    export_dir = tmp_path / "rsl_export"
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("RSL_EXPORT_DIR", str(export_dir))
    return data_dir


def _extract_result_dict(call_result: Any) -> dict[str, Any]:
    sc = call_result.structured_content
    if isinstance(sc, dict) and "result" in sc and isinstance(sc["result"], dict):
        return sc["result"]
    assert isinstance(sc, dict)
    return sc


# D-002, D-006, D-029, FR-20, FR-23: Ferramenta import_works exposta no MCPServer com anotações aditivas
@pytest.mark.anyio
async def test_d002_d029_import_works_tool_registration() -> None:
    async with Client(server.mcp) as client:
        tools_res = await client.list_tools()
        tools_by_name = {t.name: t for t in tools_res.tools}
        assert "import_works" in tools_by_name
        tool = tools_by_name["import_works"]
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is False
        assert tool.annotations.destructive_hint is False


# FR-23, D-033: Importação de arquivo RIS via MCP Tool gerando nova lista salva
@pytest.mark.anyio
async def test_fr23_d033_import_works_tool_ris(isolated_env: Path) -> None:
    sample_ris = """
TY  - JOUR
TI  - Quantum Computing for Drug Discovery
AU  - Feynman, Richard
PY  - 2024
DO  - 10.1038/s41586-024-00001-x
JF  - Nature
ER  - 
"""
    async with Client(server.mcp) as client:
        res = await client.call_tool(
            "import_works",
            {
                "content": sample_ris,
                "format": "auto",
                "list_name": "Lista Quântica",
            },
        )
        data = _extract_result_dict(res)
        assert data["status"] == "complete"
        assert data["total"] == 1
        assert data["imported_format"] == "ris"
        assert data["list_id"].startswith("l-")

        # Confere que a lista e o log foram salvos fisicamente no Store
        store = Store(isolated_env)
        saved_list = store.get_list(data["list_id"])
        assert saved_list["total"] == 1
        assert saved_list["works"][0]["title"] == "Quantum Computing for Drug Discovery"
        assert saved_list["works"][0]["authors"][0]["name"] == "Richard Feynman"


# FR-23, D-033: Importação com entrada inválida devolve erro invalid_input
@pytest.mark.anyio
async def test_fr23_d033_import_works_tool_invalid_input() -> None:
    async with Client(server.mcp) as client:
        res = await client.call_tool(
            "import_works",
            {
                "content": "conteúdo aleatório sem estrutura bibliográfica válida",
                "format": "auto",
            },
        )
        assert res.is_error is True
