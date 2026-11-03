"""Testes da ferramenta get_list no servidor MCP (Client(mcp) em memória)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp import Client
from mcp.server.mcpserver.exceptions import ToolError

from rslapp import server
from rslapp.core.models import Affiliation, Author, Work
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
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Isola variáveis de ambiente e configura RSL_DATA_DIR em pasta temporária."""
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    data_dir = tmp_path / "rsl_data"
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))
    return data_dir


def _extract_result_dict(call_result: Any) -> dict[str, Any]:
    sc = call_result.structured_content
    if isinstance(sc, dict) and "result" in sc and isinstance(sc["result"], dict):
        return sc["result"]
    assert isinstance(sc, dict)
    return sc


def _extract_tool_error_payload(call_result: Any) -> str:
    assert call_result.content
    raw = str(call_result.content[0].text)
    return raw.removeprefix("Error executing tool get_list: ")


def _create_sample_list(data_dir: Path, count: int = 30) -> str:
    store = Store(data_dir)
    works: list[Work] = []
    for i in range(1, count + 1):
        works.append(
            Work(
                title=f"Estudo Sistemático {i:02d}",
                doi=f"10.1234/estudo.{i:02d}",
                year=2024,
                type="article",
                venue="Revista de Teste",
                abstract=f"Resumo detalhado {i}",
                keywords=["ciência", f"teste-{i}"],
                authors=[
                    Author(
                        name=f"Pesquisador {i}",
                        orcid=f"0000-0001-{i:04d}-0000",
                        affiliations=[Affiliation(name=f"Inst {i}", country_code="BR")],
                    )
                ],
                references=[f"W{r:04d}" for r in range(1, 4)],
                references_count=3,
                citations={"openalex": i * 3},
                source_ids={"openalex": f"W{i:04d}"},
            )
        )
    _search, saved_list = store.record_search(
        {
            "kind": "terms",
            "query": "estudo sistemático",
            "sources": [{"name": "openalex", "status": "ok", "query": "q", "found": count, "fetched": count}],
        },
        {"status": "complete", "works": [w.to_dict() for w in works]},
    )
    return str(saved_list["id"])


# FR-12, D-002: get_list via Client(mcp) em memória pagina e respeita detail summary e full
@pytest.mark.anyio
async def test_fr12_d002_get_list_server_paginacao_e_detail(isolated_env: Path) -> None:
    list_id = _create_sample_list(isolated_env, count=30)

    async with Client(server.mcp) as client:
        tools = await client.list_tools()
        tool_names = [t.name for t in tools.tools]
        assert "get_list" in tool_names

        # Página 1 com summary (10 itens)
        res1 = await client.call_tool(
            "get_list",
            {"list_id": list_id, "page": 1, "page_size": 10, "detail": "summary"},
        )
        assert res1.is_error is False
        data1 = _extract_result_dict(res1)
        assert data1["list_id"] == list_id
        assert data1["total"] == 30
        assert data1["page"] == 1
        assert data1["page_size"] == 10
        assert data1["next_page"] == 2
        assert len(data1["works"]) == 10
        # Em summary, campos simplificados
        first = data1["works"][0]
        assert "abstract" not in first
        assert "authors" in first
        assert isinstance(first["authors"], list)
        assert isinstance(first["authors"][0], str)

        # Página 3 com full (últimos 10 itens)
        res3 = await client.call_tool(
            "get_list",
            {"list_id": list_id, "page": 3, "page_size": 10, "detail": "full"},
        )
        assert res3.is_error is False
        data3 = _extract_result_dict(res3)
        assert data3["page"] == 3
        assert data3["next_page"] is None
        assert len(data3["works"]) == 10
        # Em full, registro completo
        item_full = data3["works"][0]
        assert "abstract" in item_full
        assert "keywords" in item_full
        assert isinstance(item_full["authors"][0], dict)
        assert "affiliations" in item_full["authors"][0]


# FR-12, D-002: get_list com id inexistente ou malformado devolve erro list_not_found
@pytest.mark.anyio
@pytest.mark.parametrize("bad_id", ["l-9999", "l-invalido", "s-0001", "invalido", ""])
async def test_fr12_d002_get_list_server_inexistente_volta_list_not_found(
    isolated_env: Path,
    bad_id: str,
) -> None:
    with pytest.raises(ToolError) as exc_info:
        server.get_list(list_id=bad_id)
    assert str(exc_info.value).startswith("list_not_found:")

    async with Client(server.mcp) as client:
        res = await client.call_tool("get_list", {"list_id": bad_id})
        assert res.is_error is True
        err_msg = _extract_tool_error_payload(res)
        assert err_msg.startswith("list_not_found:")


# FR-12, D-002: get_list com parâmetros inválidos devolve erro invalid_input
@pytest.mark.anyio
@pytest.mark.parametrize(
    ("page", "page_size", "detail"),
    [
        (0, 25, "summary"),
        (1, 0, "summary"),
        (1, 101, "summary"),
        (1, 25, "invalid_detail"),
    ],
)
async def test_fr12_d002_get_list_server_parametros_invalidos_volta_invalid_input(
    isolated_env: Path,
    page: int,
    page_size: int,
    detail: str,
) -> None:
    list_id = _create_sample_list(isolated_env, count=5)

    with pytest.raises(ToolError) as exc_info:
        server.get_list(list_id=list_id, page=page, page_size=page_size, detail=detail)
    assert str(exc_info.value).startswith("invalid_input:")

    async with Client(server.mcp) as client:
        res = await client.call_tool(
            "get_list",
            {"list_id": list_id, "page": page, "page_size": page_size, "detail": detail},
        )
        assert res.is_error is True
        err_msg = _extract_tool_error_payload(res)
        assert err_msg.startswith("invalid_input:")
