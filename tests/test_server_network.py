"""Testes da ferramenta export_network no servidor MCP (FR-31, D-042)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp import Client

from rslapp import server
from rslapp.store import Store


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    export_dir = tmp_path / "exports"
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("RSL_EXPORT_DIR", str(export_dir))
    return tmp_path


def _extract_result_dict(call_result: Any) -> dict[str, Any]:
    sc = call_result.structured_content
    if isinstance(sc, dict) and "result" in sc and isinstance(sc["result"], dict):
        return sc["result"]
    assert isinstance(sc, dict)
    return sc


@pytest.mark.anyio
async def test_fr31_d042_server_export_network(isolated_env: Path) -> None:
    store = Store(isolated_env / "data")
    search_data = {
        "kind": "terms",
        "request_summary": "busca bibliométrica",
        "sources": [{"name": "openalex", "status": "ok", "fetched": 2, "found": 2}],
    }
    list_data = {
        "query": "redes bibliométricas",
        "status": "complete",
        "total": 2,
        "works": [
            {
                "id": "W1",
                "doi": "10.1000/1",
                "title": "Machine Learning in Healthcare",
                "year": 2024,
                "authors": [{"name": "Mendes, Erick"}, {"name": "Silva, Ana"}],
                "venue": "Health Informatics",
                "source": "openalex",
            },
            {
                "id": "W2",
                "doi": "10.1000/2",
                "title": "Systematic Review Automation",
                "year": 2024,
                "authors": [{"name": "Mendes, Erick"}, {"name": "Silva, Ana"}, {"name": "Costa, Carlos"}],
                "venue": "Health Informatics",
                "source": "openalex",
            },
        ],
    }
    _, l_rec = store.record_search(search_data, list_data)
    list_id = l_rec["id"]

    async with Client(server.mcp) as client:
        # 1. Exportação no formato VOSviewer (.map e .network)
        vos_res = await client.call_tool(
            "export_network",
            {"list_id": list_id, "network_type": "coauthorship", "format": "vosviewer"},
        )
        assert vos_res.is_error is False
        vos_data = _extract_result_dict(vos_res)
        assert vos_data["total_nodes"] == 3
        assert vos_data["total_edges"] == 3
        assert Path(vos_data["map_path"]).exists()
        assert Path(vos_data["network_path"]).exists()

        map_content = Path(vos_data["map_path"]).read_text(encoding="utf-8")
        assert "id\tlabel\tweight<Occurrences>" in map_content
        assert "Mendes, Erick" in map_content

        # 2. Exportação no formato Gephi (.gexf)
        gephi_res = await client.call_tool(
            "export_network",
            {"list_id": list_id, "network_type": "coauthorship", "format": "gephi"},
        )
        assert gephi_res.is_error is False
        gephi_data = _extract_result_dict(gephi_res)
        assert Path(gephi_data["path"]).exists()
        gexf_content = Path(gephi_data["path"]).read_text(encoding="utf-8")
        assert "<gexf" in gexf_content
        assert "Mendes, Erick" in gexf_content

        # 3. Exportação no formato JSON
        json_res = await client.call_tool(
            "export_network",
            {"list_id": list_id, "network_type": "coauthorship", "format": "json"},
        )
        assert json_res.is_error is False
        json_data = _extract_result_dict(json_res)
        assert "network" in json_data
        assert json_data["network"]["total_nodes"] == 3
