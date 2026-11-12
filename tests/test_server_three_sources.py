"""Testes do servidor MCP com as três fontes acadêmicas e Client(mcp) em memória."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp import Client

from rslapp import server
from rslapp.core.models import Author, SourceResult, Work
from rslapp.sources.crossref import CrossrefSource
from rslapp.sources.europe_pmc import EuropePMCSource
from rslapp.sources.openalex import OpenAlexSource
from rslapp.sources.pubmed import PubmedSource
from rslapp.sources.scopus import ScopusSource
from rslapp.sources.semantic_scholar import SemanticScholarSource
from rslapp.sources.web_of_science import WebOfScienceSource


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    data_dir = tmp_path / "rsl_data"
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))
    return data_dir


class FakeServerSource:
    """Fonte simulada para testes do servidor MCP com Client em memória."""

    def __init__(self, name: str, result: SourceResult) -> None:
        self.name = name
        self.needs_key = False
        self._result = result
        self.calls: list[tuple[str, int]] = []

    def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
        return {"source": self.name, "query": query, "max": max_results}

    async def search(self, query: str, max_results: int) -> SourceResult:
        self.calls.append((query, max_results))
        return self._result


def _extract_result_dict(call_result: Any) -> dict[str, Any]:
    sc = call_result.structured_content
    if isinstance(sc, dict) and "result" in sc and isinstance(sc["result"], dict):
        return sc["result"]
    assert isinstance(sc, dict)
    return sc


# FR-01, FR-07, D-002, D-020, D-023: _build_sources instancia as sete fontes na ordem canônica no stdio
def test_fr01_fr07_d002_build_sources_instancia_tres_fontes() -> None:
    sources = server._build_sources()
    assert len(sources) == 7
    assert isinstance(sources[0], OpenAlexSource)
    assert isinstance(sources[1], CrossrefSource)
    assert isinstance(sources[2], SemanticScholarSource)
    assert isinstance(sources[3], EuropePMCSource)
    assert isinstance(sources[4], PubmedSource)
    assert isinstance(sources[5], ScopusSource)
    assert isinstance(sources[6], WebOfScienceSource)


# FR-07, D-002, D-020, D-023: list_sources mostra as sete fontes no stdio e a docstring tem a nota das bases
@pytest.mark.anyio
async def test_fr07_d002_list_sources_docstring_e_tres_fontes() -> None:
    async with Client(server.mcp) as client:
        tools = await client.list_tools()
        tool = next(t for t in tools.tools if t.name == "list_sources")
        assert "Semantic Scholar" in tool.description
        assert "opcional" in tool.description

        res = await client.call_tool("list_sources", {})
        assert res.is_error is False
        assert isinstance(res.structured_content, dict)
        payload = res.structured_content["result"]
        assert isinstance(payload, list)
        names = [item["name"] for item in payload]
        assert names == [
            "openalex",
            "crossref",
            "semantic_scholar",
            "europe_pmc",
            "pubmed",
            "scopus",
            "web_of_science",
        ]

        s2_info = next(item for item in payload if item["name"] == "semantic_scholar")
        assert s2_info["configured"] is True
        assert s2_info["needs_key"] is False
        assert s2_info["status"] == "ok"


# FR-01, FR-04, FR-08, D-002: search_works consulta as três fontes e junta o resultado
@pytest.mark.anyio
async def test_fr01_fr04_fr08_d002_search_works_consulta_tres_fontes_e_junta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    w_shared_oa = Work(
        title="Estudo Concorrente",
        doi="10.1234/shared",
        year=2024,
        authors=[Author(name="Autor OpenAlex")],
        source_ids={"openalex": "W1"},
        citations={"openalex": 10},
    )
    w_shared_cr = Work(
        title="Estudo Concorrente",
        doi="10.1234/shared",
        year=2024,
        authors=[Author(name="Autor Crossref")],
        source_ids={"crossref": "CR1"},
        citations={"crossref": 5},
    )
    w_s2_only = Work(
        title="Trabalho Somente S2",
        doi="10.1234/s2only",
        year=2023,
        authors=[Author(name="Autor S2")],
        source_ids={"semantic_scholar": "S200"},
        citations={"semantic_scholar": 2},
    )

    src_oa = FakeServerSource(
        "openalex",
        SourceResult(name="openalex", status="ok", query="q=x", found=1, fetched=1, works=[w_shared_oa]),
    )
    src_cr = FakeServerSource(
        "crossref",
        SourceResult(name="crossref", status="ok", query="q=x", found=1, fetched=1, works=[w_shared_cr]),
    )
    src_s2 = FakeServerSource(
        "semantic_scholar",
        SourceResult(name="semantic_scholar", status="ok", query="q=x", found=1, fetched=1, works=[w_s2_only]),
    )

    monkeypatch.setattr(server, "_build_sources", lambda: [src_oa, src_cr, src_s2])

    async with Client(server.mcp) as client:
        res = await client.call_tool(
            "search_works",
            {
                "query": "inteligencia artificial",
                "request_summary": "Revisão nas 3 fontes",
                "max_results": 100,
            },
        )
        assert res.is_error is False
        payload = _extract_result_dict(res)

        assert payload["status"] == "complete"
        assert payload["total"] == 2
        assert len(payload["works"]) == 2
        assert len(payload["sources"]) == 3

        shared = next(w for w in payload["works"] if w["doi"] == "10.1234/shared")
        assert shared["citations"] == {"openalex": 10, "crossref": 5}


# D-002: Exceção inesperada no miolo não vaza detalhes sensíveis na resposta do servidor
@pytest.mark.anyio
async def test_d002_excecao_inesperada_nao_vaza_detalhes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CrashingSource:
        name = "openalex"
        needs_key = True

        def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
            return {"q": query}

        async def search(self, query: str, max_results: int) -> SourceResult:
            raise RuntimeError("segredo_interno_que_nao_pode_vazar")

    monkeypatch.setattr(server, "_build_sources", lambda: [CrashingSource()])

    async with Client(server.mcp) as client:
        res = await client.call_tool("search_works", {"query": "crash"})
        assert res.is_error is True
        error_text = str(res.content[0].text)
        # O MCPServer encobre a exceção como erro de execução sem propagar texto interno
        assert "segredo_interno_que_nao_pode_vazar" not in error_text
        assert "Error executing tool" in error_text
