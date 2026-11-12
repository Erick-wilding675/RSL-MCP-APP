"""Testes da ferramenta search_works no servidor MCP (Client(mcp) em memória)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from mcp import Client
from mcp.server.mcpserver.exceptions import ToolError

from rslapp import server
from rslapp.core.models import Author, SourceResult, Work
from rslapp.sources.crossref import CrossrefSource
from rslapp.sources.europe_pmc import EuropePMCSource
from rslapp.sources.openalex import OpenAlexSource
from rslapp.sources.pubmed import PubmedSource
from rslapp.sources.scopus import ScopusSource
from rslapp.sources.semantic_scholar import SemanticScholarSource
from rslapp.sources.web_of_science import WebOfScienceSource

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
    """Isola variáveis de ambiente e define RSL_DATA_DIR em pasta temporária."""
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    data_dir = tmp_path / "rsl_data"
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))
    return data_dir


class FakeServerSource:
    """Fonte simulada para testes do servidor MCP sem rede."""

    def __init__(self, result: SourceResult) -> None:
        self.name = result.name
        self.needs_key = True
        self._result = result
        self.calls: list[tuple[str, int]] = []

    def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
        return {"search": query.strip(), "max_results": max_results}

    async def search(self, query: str, max_results: int) -> SourceResult:
        self.calls.append((query, max_results))
        return self._result


def _extract_result_dict(call_result: Any) -> dict[str, Any]:
    sc = call_result.structured_content
    if isinstance(sc, dict) and "result" in sc and isinstance(sc["result"], dict):
        return sc["result"]
    assert isinstance(sc, dict)
    return sc


def _extract_tool_error_payload(call_result: Any) -> str:
    assert call_result.content
    raw = str(call_result.content[0].text)
    return raw.removeprefix("Error executing tool search_works: ")


# FR-01, FR-05, FR-12, D-002, D-003: search_works via Client(mcp) responde como no contrato
@pytest.mark.anyio
async def test_fr01_fr05_fr12_d002_d003_search_works_em_memoria_responde_como_no_contrato(
    monkeypatch: pytest.MonkeyPatch,
    isolated_env: Path,
) -> None:
    default_sources = server._build_sources()
    assert len(default_sources) == 7
    assert isinstance(default_sources[0], OpenAlexSource)
    assert isinstance(default_sources[1], CrossrefSource)
    assert isinstance(default_sources[2], SemanticScholarSource)
    assert isinstance(default_sources[3], EuropePMCSource)
    assert isinstance(default_sources[4], PubmedSource)
    assert isinstance(default_sources[5], ScopusSource)
    assert isinstance(default_sources[6], WebOfScienceSource)

    monkeypatch.setenv("RSL_CACHE_DAYS", "14")
    fake_work = Work(
        title="Interpretable Machine Learning",
        doi="10.1234/iml.2024",
        year=2024,
        venue="AI Review",
        abstract="Abstract text that stays in saved list only.",
        authors=[Author(name="Ada Lovelace", orcid="0000-0001-2345-6789")],
        references=["W10"],
        references_count=1,
        citations={"openalex": 42},
        source_ids={"openalex": "W1"},
    )
    fake_oa = FakeServerSource(
        SourceResult(
            name="openalex",
            status="ok",
            query="search=machine learning · per_page=100 · páginas 1-1",
            found=120,
            fetched=1,
            works=[fake_work],
        )
    )
    fake_other = FakeServerSource(
        SourceResult(name="crossref", status="ok", query="q", found=0, fetched=0, works=[])
    )
    monkeypatch.setattr(server, "_build_sources", lambda: [fake_oa, fake_other])

    async with Client(server.mcp) as client:
        tools = await client.list_tools()
        assert "search_works" in [t.name for t in tools.tools]

        res = await client.call_tool(
            "search_works",
            {
                "query": "machine learning",
                "request_summary": "Revisão sobre aprendizado de máquina",
                "sources": ["openalex", "openalex"],
                "max_results": 100,
            },
        )
        assert res.is_error is False
        payload = _extract_result_dict(res)

        assert payload["search_id"] == "s-0001"
        assert payload["list_id"] == "l-0001"
        assert payload["status"] == "complete"
        assert payload["total"] == 1
        assert payload["page"] == 1
        assert payload["next_page"] is None
        assert len(payload["sources"]) == 1
        assert payload["sources"][0]["name"] == "openalex"
        assert payload["sources"][0]["status"] == "ok"
        assert payload["sources"][0]["found"] == 120
        assert payload["sources"][0]["fetched"] == 1
        assert payload["sources"][0]["from_cache"] is False
        assert payload["works"] == [
            {
                "doi": "10.1234/iml.2024",
                "title": "Interpretable Machine Learning",
                "authors": ["Ada Lovelace"],
                "year": 2024,
                "venue": "AI Review",
                "references_count": 1,
                "citations": {"openalex": 42},
            }
        ]
        assert fake_oa.calls == [("machine learning", 100)]
        assert fake_other.calls == []
        assert (isolated_env / "lists" / "l-0001.json").exists()
        assert (isolated_env / "searches" / "s-0001.json").exists()
        assert (isolated_env / "log.md").exists()

        cache_files = list((isolated_env / "cache" / "openalex").glob("*.json"))
        assert len(cache_files) == 1
        cache_payload = json.loads(cache_files[0].read_text(encoding="utf-8"))
        assert cache_payload["fetched_at"] != cache_payload["expires_at"]


# D-002: Entrada inválida em search_works volta como erro com invalid_input: no início do texto
@pytest.mark.anyio
@pytest.mark.parametrize(
    "invalid_args",
    [
        {"query": ""},
        {"query": "   "},
        {"query": "ml", "max_results": 0},
        {"query": "ml", "max_results": -5},
        {"query": "ml", "max_results": 1001},
        {"query": "ml", "sources": ["fonte_desconhecida"]},
        {"query": "ml", "sources": [""]},
        {"query": "ml", "sources": []},
    ],
)
async def test_d002_search_works_entrada_invalida_volta_com_invalid_input_no_inicio(
    monkeypatch: pytest.MonkeyPatch,
    isolated_env: Path,
    invalid_args: dict[str, Any],
) -> None:
    fake_src = FakeServerSource(
        SourceResult(name="openalex", status="ok", query="q", found=0, fetched=0, works=[])
    )
    monkeypatch.setattr(server, "_build_sources", lambda: [fake_src])

    with pytest.raises(ToolError) as exc_info:
        await server.search_works(**invalid_args)
    assert str(exc_info.value).startswith("invalid_input:")

    async with Client(server.mcp) as client:
        res = await client.call_tool("search_works", invalid_args)
        assert res.is_error is True
        err_text = _extract_tool_error_payload(res)
        assert err_text.startswith("invalid_input:")
        assert fake_src.calls == []
        assert not (isolated_env / "lists").exists()


# D-002: Limites válidos de max_results (1 e 1000) funcionam; missing_key devolve no_source_available:
@pytest.mark.anyio
async def test_d002_search_works_limites_max_results_e_erro_no_source_available(
    monkeypatch: pytest.MonkeyPatch,
    isolated_env: Path,
) -> None:
    ok_src = FakeServerSource(
        SourceResult(name="openalex", status="ok", query="q", found=0, fetched=0, works=[])
    )
    monkeypatch.setattr(server, "_build_sources", lambda: [ok_src])

    async with Client(server.mcp) as client:
        r_min = await client.call_tool("search_works", {"query": "ml", "max_results": 1})
        assert r_min.is_error is False
        r_max = await client.call_tool("search_works", {"query": "ml", "max_results": 1000})
        assert r_max.is_error is False
        assert ok_src.calls == [("ml", 1), ("ml", 1000)]

    missing_src = FakeServerSource(
        SourceResult(
            name="openalex",
            status="missing_key",
            reason="variável OPENALEX_API_KEY não configurada",
            query="search=ml",
            found=None,
            fetched=0,
            works=[],
        )
    )
    monkeypatch.setattr(server, "_build_sources", lambda: [missing_src])

    with pytest.raises(ToolError) as exc_info:
        await server.search_works(query="ml")
    assert str(exc_info.value).startswith("no_source_available:")

    async with Client(server.mcp) as client:
        res_err = await client.call_tool("search_works", {"query": "ml"})
        assert res_err.is_error is True
        assert _extract_tool_error_payload(res_err).startswith("no_source_available:")
