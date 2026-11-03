"""Testes de integração das ferramentas find_work e repeat_search no MCPServer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp import Client
from mcp.server.mcpserver.exceptions import ToolError

from rslapp import server
from rslapp.core.models import Author, SourceResult, Work

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
    """Isola variáveis de ambiente e define RSL_DATA_DIR e RSL_EXPORT_DIR em pasta temporária."""
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    data_dir = tmp_path / "rsl_data"
    export_dir = tmp_path / "rsl_export"
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("RSL_EXPORT_DIR", str(export_dir))
    return data_dir


class FakeServerSource:
    """Fonte simulada para os testes do servidor MCP."""

    def __init__(self, name: str, works: list[Work] | None = None) -> None:
        self.name = name
        self.needs_key = False
        self.works = works if works is not None else []

    def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
        return {"query": query, "max_results": max_results}

    async def search(self, query: str, max_results: int) -> SourceResult:
        return SourceResult(
            name=self.name,
            status="ok",
            reason=None,
            query=f"query={query}",
            found=len(self.works),
            fetched=len(self.works),
            works=list(self.works),
        )

    async def find_by_doi(self, doi: str) -> SourceResult:
        matching = [w for w in self.works if w.doi == doi]
        return SourceResult(
            name=self.name,
            status="ok",
            reason=None,
            query=f"doi:{doi}",
            found=len(matching),
            fetched=len(matching),
            works=matching,
        )


def _extract_result_dict(call_result: Any) -> dict[str, Any]:
    sc = call_result.structured_content
    if isinstance(sc, dict) and "result" in sc and isinstance(sc["result"], dict):
        return sc["result"]
    assert isinstance(sc, dict)
    return sc


def _extract_error_message(call_result: Any) -> str:
    assert call_result.content
    return str(call_result.content[0].text)


# D-002: Ferramentas find_work e repeat_search expostas no MCPServer
@pytest.mark.anyio
async def test_d002_tools_registered_in_mcp_server() -> None:
    async with Client(server.mcp) as client:
        tools_res = await client.list_tools()
        tool_names = [t.name for t in tools_res.tools]
        assert "find_work" in tool_names
        assert "repeat_search" in tool_names


# FR-02, UC-02, D-002: find_work por DOI via cliente MCP
@pytest.mark.anyio
async def test_fr02_uc02_find_work_by_doi_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    w = Work(
        title="Attention Is All You Need",
        doi="10.1234/transformer",
        year=2017,
        venue="NeurIPS",
        authors=[Author(name="Vaswani")],
    )
    fake_src = FakeServerSource("openalex", works=[w])
    monkeypatch.setattr(server, "_build_sources", lambda: [fake_src])

    async with Client(server.mcp) as client:
        call_res = await client.call_tool(
            "find_work",
            {"doi": "10.1234/transformer", "request_summary": "Artigo do transformer"},
        )
        assert call_res.is_error is False
        data = _extract_result_dict(call_res)

        assert data["status"] == "complete"
        assert data["total"] == 1
        assert len(data["works"]) == 1
        assert data["works"][0]["doi"] == "10.1234/transformer"
        assert data["works"][0]["title"] == "Attention Is All You Need"


# FR-02, UC-02, D-002: find_work por título via cliente MCP
@pytest.mark.anyio
async def test_fr02_uc02_find_work_by_title_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    w = Work(
        title="BERT: Pre-training of Deep Bidirectional Transformers",
        doi="10.1234/bert",
        year=2018,
        authors=[Author(name="Devlin")],
    )
    fake_src = FakeServerSource("crossref", works=[w])
    monkeypatch.setattr(server, "_build_sources", lambda: [fake_src])

    async with Client(server.mcp) as client:
        call_res = await client.call_tool(
            "find_work",
            {"title": "BERT", "max_results": 5},
        )
        assert call_res.is_error is False
        data = _extract_result_dict(call_res)

        assert data["status"] == "complete"
        assert data["total"] == 1
        assert data["works"][0]["doi"] == "10.1234/bert"


# FR-02, D-002: find_work com entrada inválida levanta ToolError e devolve is_error no cliente
@pytest.mark.anyio
async def test_fr02_d002_find_work_invalid_input_tool_error() -> None:
    with pytest.raises(ToolError) as exc:
        await server.find_work()
    assert str(exc.value).startswith("invalid_input:")

    async with Client(server.mcp) as client:
        res = await client.call_tool("find_work", {})
        assert res.is_error is True
        assert "invalid_input" in _extract_error_message(res)


# FR-11, UC-03, D-002: repeat_search via cliente MCP repete busca por termos
@pytest.mark.anyio
async def test_fr11_uc03_repeat_search_terms_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    w = Work(title="Quantum Computing", doi="10.1234/qc", year=2024, authors=[Author(name="Feynman")])
    fake_src = FakeServerSource("openalex", works=[w])
    monkeypatch.setattr(server, "_build_sources", lambda: [fake_src])

    async with Client(server.mcp) as client:
        # 1. Faz busca original
        search_res = await client.call_tool("search_works", {"query": "quantum computing"})
        assert search_res.is_error is False
        search_data = _extract_result_dict(search_res)
        orig_search_id = search_data["search_id"]

        # 2. Repete busca
        repeat_res = await client.call_tool("repeat_search", {"search_id": orig_search_id})
        assert repeat_res.is_error is False
        repeat_data = _extract_result_dict(repeat_res)

        assert repeat_data["search_id"] != orig_search_id
        assert repeat_data["repeated_from"] == orig_search_id
        assert repeat_data["status"] == "complete"
        assert repeat_data["total"] == 1


# FR-11, UC-03, D-002: repeat_search via cliente MCP repete find_work
@pytest.mark.anyio
async def test_fr11_uc03_repeat_search_find_work_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    w = Work(title="Target Work", doi="10.1234/target", year=2024, authors=[Author(name="Target")])
    fake_src = FakeServerSource("openalex", works=[w])
    monkeypatch.setattr(server, "_build_sources", lambda: [fake_src])

    async with Client(server.mcp) as client:
        find_res = await client.call_tool("find_work", {"doi": "10.1234/target"})
        assert find_res.is_error is False
        find_data = _extract_result_dict(find_res)
        orig_id = find_data["search_id"]

        repeat_res = await client.call_tool("repeat_search", {"search_id": orig_id})
        assert repeat_res.is_error is False
        repeat_data = _extract_result_dict(repeat_res)

        assert repeat_data["search_id"] != orig_id
        assert repeat_data["repeated_from"] == orig_id
        assert repeat_data["total"] == 1


# FR-11, D-002: repeat_search com id inexistente levanta ToolError search_not_found
@pytest.mark.anyio
async def test_fr11_d002_repeat_search_not_found_tool_error() -> None:
    with pytest.raises(ToolError) as exc:
        await server.repeat_search(search_id="s-9999")
    assert str(exc.value).startswith("search_not_found:")

    async with Client(server.mcp) as client:
        res = await client.call_tool("repeat_search", {"search_id": "s-9999"})
        assert res.is_error is True
        assert "search_not_found" in _extract_error_message(res)
