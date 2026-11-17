"""Testes da integração da fonte BDTD com o servidor MCP e deduplicação."""

from __future__ import annotations

from typing import Any

import pytest
from mcp import Client

from rslapp import server
from rslapp.core.models import Author, SourceResult, Work
from rslapp.sources.base import Source


class FakeBDTDSource(Source):
    name: str = "bdtd"
    needs_key: bool = False

    def __init__(self, works: list[Work] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._works = works or []

    def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
        return {"source": self.name, "query": query, "max_results": max_results}

    async def search(self, query: str, max_results: int = 100) -> SourceResult:
        self.calls.append({"query": query, "max_results": max_results})
        return SourceResult(
            name=self.name,
            status="ok",
            reason=None,
            query=query,
            found=len(self._works),
            fetched=len(self._works),
            works=self._works,
        )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_d035_search_works_with_bdtd_source(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RSL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("RSL_EXPORTS_DIR", str(tmp_path / "exports"))

    sample_work = Work(
        title="Tese de teste sobre vacinas no Brasil",
        year=2023,
        venue="USP",
        type="thesis",
        authors=[Author(name="Silva, Pedro")],
        source_ids={"bdtd": "USP_998877"},
    )
    fake_bdtd = FakeBDTDSource(works=[sample_work])

    def fake_build_sources(include_paid: bool = True) -> list[Source]:
        return [fake_bdtd]

    monkeypatch.setattr(server, "_build_sources", fake_build_sources)

    async with Client(server.mcp) as client:
        res = await client.call_tool(
            "search_works",
            {"query": "vacinas Brasil", "sources": ["bdtd"]},
        )
        assert res.is_error is False
        data = res.structured_content
        assert data["total"] == 1
        assert len(data["works"]) == 1
        assert data["works"][0]["title"] == "Tese de teste sobre vacinas no Brasil"
        assert data["works"][0]["venue"] == "USP"
        assert len(fake_bdtd.calls) == 1

        # Confere a lista completa via get_list
        res_list = await client.call_tool(
            "get_list",
            {"list_id": data["list_id"], "detail": "full"},
        )
        assert res_list.is_error is False
        full_work = res_list.structured_content["works"][0]
        assert full_work["source_ids"] == {"bdtd": "USP_998877"}


@pytest.mark.anyio
async def test_d035_find_work_and_get_related_reject_bdtd(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RSL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("RSL_EXPORTS_DIR", str(tmp_path / "exports"))

    async with Client(server.mcp) as client:
        res_find = await client.call_tool(
            "find_work",
            {"doi": "10.1234/test", "sources": ["bdtd"]},
        )
        assert res_find.is_error is True
        assert "fonte não suportada nesta ferramenta: bdtd" in str(res_find.content)

        res_rel = await client.call_tool(
            "get_related_works",
            {"doi": "10.1234/test", "direction": "references", "sources": ["bdtd"]},
        )
        assert res_rel.is_error is True
        assert "fonte não suportada nesta ferramenta: bdtd" in str(res_rel.content)


@pytest.mark.anyio
async def test_d035_list_sources_shows_bdtd_as_open_and_ok(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RSL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("RSL_EXPORTS_DIR", str(tmp_path / "exports"))

    async with Client(server.mcp) as client:
        res = await client.call_tool("list_sources", {})
        assert res.is_error is False
        sources = {item["name"]: item for item in res.structured_content["result"]}
        assert "bdtd" in sources
        assert sources["bdtd"]["configured"] is True
        assert sources["bdtd"]["needs_key"] is False
        assert sources["bdtd"]["status"] == "ok"
