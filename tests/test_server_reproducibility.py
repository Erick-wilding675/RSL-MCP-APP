"""Testes da ferramenta export_reproducibility_package no servidor MCP (FR-28, D-039)."""

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
async def test_fr28_d039_export_reproducibility_package_stdio(isolated_env: Path) -> None:
    store = Store(isolated_env / "data")
    search_data = {
        "kind": "terms",
        "request_summary": "reproducibility test query",
        "sources": [{"name": "openalex", "status": "ok", "fetched": 1, "found": 1}],
    }
    list_data = {
        "query": "reproducibility test",
        "status": "complete",
        "total": 1,
        "works": [
            {
                "doi": "10.1000/100",
                "title": "Reproducibility in Science",
                "year": 2025,
                "authors": [{"name": "Popper, Karl"}],
                "venue": "Philosophy of Science",
                "source": "openalex",
            }
        ],
    }
    _, l_rec = store.record_search(search_data, list_data)
    list_id = l_rec["id"]

    async with Client(server.mcp) as client:
        call_res = await client.call_tool(
            "export_reproducibility_package",
            {"list_id": list_id},
        )
        data = _extract_result_dict(call_res)

        assert data["list_id"] == list_id
        assert data["filename"] == f"reproducibility_{list_id}.zip"
        assert data["file_count"] == 12
        assert "sha256" in data
        assert len(data["sha256"]) == 64
        assert data["path"] is not None
        assert Path(data["path"]).is_file()


@pytest.mark.anyio
async def test_fr28_d039_export_reproducibility_package_error_empty(isolated_env: Path) -> None:
    store = Store(isolated_env / "data")
    _, l_rec = store.record_search(
        {"kind": "terms", "request_summary": "empty", "sources": []},
        {"query": "empty", "status": "complete", "total": 0, "works": []},
    )

    async with Client(server.mcp) as client:
        res = await client.call_tool(
            "export_reproducibility_package",
            {"list_id": l_rec["id"]},
        )
        assert res.is_error is True
        assert "empty_list" in res.content[0].text
