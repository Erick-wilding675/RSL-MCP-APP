"""Testes da ferramenta export_list no servidor MCP (Client(mcp) em memória)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp import Client
from mcp.server.mcpserver.exceptions import ToolError

from rslapp import server
from rslapp.core.models import Author, Work
from rslapp.store import Store

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
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    """Isola variáveis de ambiente e configura diretórios de dados e exportação temporários."""
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    data_dir = tmp_path / "rsl_data"
    export_dir = tmp_path / "rsl_exports"
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("RSL_EXPORT_DIR", str(export_dir))
    return data_dir, export_dir


def _extract_result_dict(call_result: Any) -> dict[str, Any]:
    sc = call_result.structured_content
    if isinstance(sc, dict) and "result" in sc and isinstance(sc["result"], dict):
        return sc["result"]
    assert isinstance(sc, dict)
    return sc


def _extract_tool_error_payload(call_result: Any) -> str:
    assert call_result.content
    raw = str(call_result.content[0].text)
    return raw.removeprefix("Error executing tool export_list: ")


def _create_sample_list(data_dir: Path) -> str:
    store = Store(data_dir)
    work = Work(
        title="Revisão Sistemática com Aprendizado Profundo",
        doi="10.1234/rsp.2024.1",
        year=2024,
        type="article",
        venue="Revista de Informática Aplicada",
        abstract="Síntese metodológica de modelos interpretáveis aplicados à saúde.",
        keywords=["revisão sistemática", "aprendizado profundo"],
        authors=[
            Author(name="José da Silva", orcid="0000-0001-2345-6789"),
            Author(name="Ada Lovelace"),
        ],
    )
    _search, saved_list = store.record_search(
        {
            "kind": "terms",
            "query": "aprendizado profundo",
            "sources": [{"name": "openalex", "status": "ok", "query": "q", "found": 1, "fetched": 1}],
        },
        {"status": "complete", "works": [work.to_dict()]},
    )
    return str(saved_list["id"])


# FR-06, FR-12, UC-01, D-002: export_list via Client(mcp) exporta lista para RIS válido e UTF-8
@pytest.mark.anyio
async def test_fr06_fr12_uc01_d002_export_list_ris_sucesso(
    isolated_env: tuple[Path, Path],
) -> None:
    data_dir, export_dir = isolated_env
    list_id = _create_sample_list(data_dir)

    async with Client(server.mcp) as client:
        tools = await client.list_tools()
        tool_names = [t.name for t in tools.tools]
        assert "export_list" in tool_names

        res = await client.call_tool("export_list", {"list_id": list_id, "format": "ris"})
        assert res.is_error is False

        data = _extract_result_dict(res)
        expected_path = str(export_dir / f"{list_id}.ris")
        assert data["path"] == expected_path
        assert data["format"] == "ris"
        assert data["count"] == 1

        exported_file = Path(data["path"])
        assert exported_file.exists()

        raw_bytes = exported_file.read_bytes()
        assert raw_bytes.startswith(b"TY  - JOUR\r\n")
        assert b"TI  - Revis" in raw_bytes
        assert b"AU  - Jos" in raw_bytes
        assert b"AU  - Ada Lovelace\r\n" in raw_bytes
        assert b"PY  - 2024\r\n" in raw_bytes
        assert b"JO  - Revista de Inform" in raw_bytes
        assert b"AB  - S" in raw_bytes
        assert b"KW  - revis" in raw_bytes
        assert b"DO  - 10.1234/rsp.2024.1\r\n" in raw_bytes
        assert raw_bytes.endswith(b"ER  - \r\n")

        content = raw_bytes.decode("utf-8")
        lines = content.split("\r\n")
        assert "TY  - JOUR" == lines[0]
        assert "TI  - Revisão Sistemática com Aprendizado Profundo" == lines[1]
        assert "AU  - José da Silva" == lines[2]
        assert "AU  - Ada Lovelace" == lines[3]
        assert "PY  - 2024" == lines[4]
        assert "JO  - Revista de Informática Aplicada" == lines[5]
        assert "AB  - Síntese metodológica de modelos interpretáveis aplicados à saúde." == lines[6]
        assert "KW  - revisão sistemática" == lines[7]
        assert "KW  - aprendizado profundo" == lines[8]
        assert "DO  - 10.1234/rsp.2024.1" == lines[9]
        assert "ER  - " == lines[10]


# FR-06: Exportar novamente a mesma lista substitui o arquivo no disco
@pytest.mark.anyio
async def test_fr06_exportar_novamente_substitui_arquivo(
    isolated_env: tuple[Path, Path],
) -> None:
    data_dir, export_dir = isolated_env
    list_id = _create_sample_list(data_dir)

    async with Client(server.mcp) as client:
        res1 = await client.call_tool("export_list", {"list_id": list_id, "format": "ris"})
        assert res1.is_error is False

        dest_file = export_dir / f"{list_id}.ris"
        assert dest_file.exists()

        res2 = await client.call_tool("export_list", {"list_id": list_id, "format": "ris"})
        assert res2.is_error is False
        assert dest_file.exists()


# D-002, FR-12: Lista inexistente ou malformada devolve erro list_not_found
@pytest.mark.anyio
@pytest.mark.parametrize("bad_list_id", ["l-9999", "l-invalido", "invalido", ""])
async def test_d002_fr12_export_list_lista_inexistente_volta_list_not_found(
    isolated_env: tuple[Path, Path],
    bad_list_id: str,
) -> None:
    with pytest.raises(ToolError) as exc_info:
        server.export_list(list_id=bad_list_id, format="ris")
    assert str(exc_info.value).startswith("list_not_found:")

    async with Client(server.mcp) as client:
        res = await client.call_tool("export_list", {"list_id": bad_list_id, "format": "ris"})
        assert res.is_error is True
        err_msg = _extract_tool_error_payload(res)
        assert err_msg.startswith("list_not_found:")


# D-002, FR-06: Formato desconhecido ou não suportado devolve erro invalid_input
@pytest.mark.anyio
@pytest.mark.parametrize("bad_format", ["csv", "json", "dois", "unknown", ""])
async def test_d002_fr06_export_list_formato_invalido_volta_invalid_input(
    isolated_env: tuple[Path, Path],
    bad_format: str,
) -> None:
    data_dir, _ = isolated_env
    list_id = _create_sample_list(data_dir)

    with pytest.raises(ToolError) as exc_info:
        server.export_list(list_id=list_id, format=bad_format)
    assert str(exc_info.value).startswith("invalid_input:")

    async with Client(server.mcp) as client:
        res = await client.call_tool("export_list", {"list_id": list_id, "format": bad_format})
        assert res.is_error is True
        err_msg = _extract_tool_error_payload(res)
        assert err_msg.startswith("invalid_input:")


# D-002, FR-06: Pasta sem permissão devolve erro export_folder_not_writable
@pytest.mark.anyio
async def test_d002_fr06_export_list_pasta_sem_permissao_volta_export_folder_not_writable(
    isolated_env: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir, _ = isolated_env
    list_id = _create_sample_list(data_dir)

    def _fail_write(*_args: Any, **_kwargs: Any) -> None:
        raise PermissionError("Permissão negada simulada")

    monkeypatch.setattr("rslapp.exporters.base.atomic_write_replace", _fail_write)

    with pytest.raises(ToolError) as exc_info:
        server.export_list(list_id=list_id, format="ris")
    assert str(exc_info.value).startswith("export_folder_not_writable:")

    async with Client(server.mcp) as client:
        res = await client.call_tool("export_list", {"list_id": list_id, "format": "ris"})
        assert res.is_error is True
        err_msg = _extract_tool_error_payload(res)
        assert err_msg.startswith("export_folder_not_writable:")
