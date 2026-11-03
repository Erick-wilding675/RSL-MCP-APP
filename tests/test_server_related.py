"""Testes da ferramenta get_related_works no servidor MCP (Client(mcp) em memória)."""

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
        monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
        monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
    data_dir = tmp_path / "rsl_data"
    export_dir = tmp_path / "rsl_export"
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("RSL_EXPORT_DIR", str(export_dir))
    return data_dir


class FakeRelatedServerSource:
    """Fonte simulada para testes do servidor MCP com get_related_works."""

    def __init__(self, name: str, result: SourceResult) -> None:
        self.name = name
        self.needs_key = True
        self._result = result

    def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
        return {"query": query, "max_results": max_results}

    async def get_origin_work(
        self, doi_or_id: str
    ) -> tuple[dict[str, Any] | None, str | None, str | None]:
        return {"id": "https://openalex.org/W100", "doi": "https://doi.org/10.1234/test"}, None, None

    async def related(
        self,
        doi_or_id: str,
        direction: str,
        max_results: int = 1000,
        origin_data: dict[str, Any] | None = None,
    ) -> SourceResult:
        return self._result


def _extract_result_dict(call_result: Any) -> dict[str, Any]:
    sc = call_result.structured_content
    if isinstance(sc, dict) and "result" in sc and isinstance(sc["result"], dict):
        return sc["result"]
    assert isinstance(sc, dict)
    return sc


# FR-15, FR-06, FR-12, D-002: get_related_works gera lista no log e exportável em RIS
@pytest.mark.anyio
async def test_fr15_fr06_get_related_works_servidor_e_exporta_ris(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_work = Work(
        title="Impact of Large Language Models on Scientific Research",
        doi="10.1000/182",
        year=2024,
        venue="Communications of the ACM",
        authors=[Author(name="Ada Lovelace")],
        references=[],
        references_count=0,
        citations={"openalex": 12},
        source_ids={"openalex": "W99"},
    )
    fake_oa = FakeRelatedServerSource(
        "openalex",
        SourceResult(
            name="openalex",
            status="ok",
            reason=None,
            query="cites=W100",
            found=1,
            fetched=1,
            works=[fake_work],
        ),
    )
    monkeypatch.setattr(server, "_build_sources", lambda: [fake_oa])

    async with Client(server.mcp) as client:
        # Chama get_related_works pelo protocolo MCP
        res = await client.call_tool(
            "get_related_works",
            {
                "doi": "10.1234/test",
                "direction": "citations",
                "request_summary": "Citações teste",
            },
        )
        data = _extract_result_dict(res)
        assert data["status"] == "complete"
        assert data["total"] == 1
        assert len(data["works"]) == 1
        assert data["works"][0]["doi"] == "10.1000/182"
        list_id = data["list_id"]
        search_id = data["search_id"]

        # Confere que o log tem a entrada
        log_res = await client.call_tool("get_search_log", {"search_id": search_id})
        log_data = _extract_result_dict(log_res)
        assert len(log_data["entries"]) == 1
        assert log_data["entries"][0]["id"] == search_id
        assert log_data["entries"][0]["kind"] == "related"

        # Confere que a lista pode ser exportada para RIS
        export_res = await client.call_tool("export_list", {"list_id": list_id, "format": "ris"})
        exp_data = _extract_result_dict(export_res)
        assert exp_data["format"] == "ris"
        assert exp_data["count"] == 1
        export_file = Path(exp_data["path"])
        assert export_file.exists()
        ris_text = export_file.read_text(encoding="utf-8")
        assert "TI  - Impact of Large Language Models on Scientific Research" in ris_text
        assert "DO  - 10.1000/182" in ris_text


def _extract_tool_error_payload(call_result: Any) -> str:
    assert call_result.content
    raw = str(call_result.content[0].text)
    return raw.removeprefix("Error executing tool get_related_works: ")


# FR-15, D-002: Entradas inválidas no servidor retornam ToolError com invalid_input
@pytest.mark.anyio
@pytest.mark.parametrize(
    "invalid_args",
    [
        {"doi": "10.1234/test", "direction": "unknown"},
        {"direction": "references"},
        {"doi": "10.1234/test", "work_id": "W123", "direction": "references"},
        {"doi": "   ", "direction": "references"},
        {"work_id": "   ", "direction": "references"},
        {"doi": "10.1234/test", "direction": "references", "max_results": 0},
        {"doi": "10.1234/test", "direction": "references", "max_results": 10001},
        {"doi": "10.1234/test", "direction": "references", "sources": ["fonte_desconhecida"]},
    ],
)
async def test_fr15_d002_get_related_works_entradas_invalidas(invalid_args: dict[str, Any]) -> None:
    # Chamada direta levanta ToolError
    with pytest.raises(ToolError) as exc_info:
        await server.get_related_works(**invalid_args)
    assert str(exc_info.value).startswith("invalid_input:")

    # Chamada via Client(mcp) retorna res.is_error is True
    async with Client(server.mcp) as client:
        res = await client.call_tool("get_related_works", invalid_args)
        assert res.is_error is True
        err_text = _extract_tool_error_payload(res)
        assert err_text.startswith("invalid_input:")
