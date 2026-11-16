"""Testes de integração da ferramenta MCP verify_references (FR-21, D-002, D-006, D-030)."""

from __future__ import annotations

from typing import Any

import pytest
from mcp import Client

from rslapp import server
from rslapp.core.models import Author, SourceResult, Work


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class FakeServerSource:
    """Fonte simulada para testes da ferramenta verify_references."""

    def __init__(self, name: str, works: list[Work] | None = None) -> None:
        self.name = name
        self.needs_key = False
        self.works = works if works is not None else []

    def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
        return {"query": query, "max_results": max_results}

    async def search(self, query: str, max_results: int = 10) -> SourceResult:
        query_lower = query.lower()
        matched = [
            w for w in self.works if query_lower in w.title.lower() or w.title.lower() in query_lower
        ]
        return SourceResult(
            name=self.name,
            status="ok",
            reason=None,
            query=f"query={query}",
            found=len(matched),
            fetched=len(matched),
            works=matched[:max_results],
        )

    async def find_by_doi(self, doi: str) -> Work | None:
        doi_clean = doi.lower().strip()
        for w in self.works:
            if w.doi and w.doi.lower().strip() == doi_clean:
                return w
        return None


def _extract_result_dict(call_result: Any) -> dict[str, Any]:
    sc = call_result.structured_content
    if isinstance(sc, dict) and "result" in sc and isinstance(sc["result"], dict):
        return sc["result"]
    assert isinstance(sc, dict)
    return sc


# D-002, D-006, D-029, FR-20, FR-21: Ferramenta verify_references exposta no MCPServer com readOnlyHint
@pytest.mark.anyio
async def test_d002_d029_verify_references_tool_registration() -> None:
    async with Client(server.mcp) as client:
        tools_res = await client.list_tools()
        tools_by_name = {t.name: t for t in tools_res.tools}
        assert "verify_references" in tools_by_name
        tool = tools_by_name["verify_references"]
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True


# FR-21, D-002, D-030: Chamada de verify_references via cliente MCP com referências confirmadas e inventadas
@pytest.mark.anyio
async def test_fr21_verify_references_via_mcp_client(monkeypatch: pytest.MonkeyPatch) -> None:
    sample_work = Work(
        title="Attention is All you Need",
        doi="10.5555/3295222.3295349",
        year=2017,
        venue="NeurIPS",
        authors=[Author(name="Ashish Vaswani"), Author(name="Noam Shazeer")],
    )
    fake_source = FakeServerSource("openalex", [sample_work])
    monkeypatch.setattr(server, "_build_sources", lambda: [fake_source])

    bibtex_input = """
    @article{vaswani2017attention,
      title = {Attention is All you Need},
      author = {Vaswani, Ashish},
      year = {2017},
      doi = {10.5555/3295222.3295349}
    }
    @article{fictional2024,
      title = {Completely Nonexistent Hallucinated Paper On Dark Matter},
      author = {Ghost, Writer},
      year = {2024}
    }
    """

    async with Client(server.mcp) as client:
        call_res = await client.call_tool(
            "verify_references",
            {"references": bibtex_input, "request_summary": "Checagem de alucinação"},
        )
        assert call_res.is_error is False
        data = _extract_result_dict(call_res)
        assert data["total"] == 2
        assert data["verified"] == 1
        assert data["not_found"] == 1
        assert len(data["results"]) == 2
        assert data["results"][0]["status"] == "verified"
        assert data["results"][1]["status"] == "not_found"


# FR-21: verify_references com lista de dicionários e lista vazia
@pytest.mark.anyio
async def test_fr21_verify_references_dict_list_and_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    work = Work(
        title="Deep Residual Learning for Image Recognition",
        doi="10.1109/CVPR.2016.90",
        year=2016,
        authors=[Author(name="Kaiming He")],
    )
    fake_source = FakeServerSource("crossref", [work])
    monkeypatch.setattr(server, "_build_sources", lambda: [fake_source])

    async with Client(server.mcp) as client:
        # 1. Lista de dicionários
        call_res = await client.call_tool(
            "verify_references",
            {
                "references": [
                    {
                        "title": "Deep Residual Learning for Image Recognition",
                        "year": 2016,
                        "authors": ["He, Kaiming"],
                    }
                ]
            },
        )
        assert call_res.is_error is False
        data = _extract_result_dict(call_res)
        assert data["total"] == 1
        assert data["verified"] == 1

        # 2. Entrada vazia
        empty_res = await client.call_tool("verify_references", {"references": ""})
        assert empty_res.is_error is False
        empty_data = _extract_result_dict(empty_res)
        assert empty_data["total"] == 0
        assert empty_data["results"] == []
