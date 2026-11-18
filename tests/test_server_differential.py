"""Testes das ferramentas MCP de comparação diferencial da Revisão Viva (FR-32, D-043)."""

from __future__ import annotations

from pathlib import Path

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from rslapp.core.models import Work
from rslapp.server import compare_search_versions, update_search_differential
from rslapp.store import Store


def test_server_compare_search_versions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))

    store = Store(data_dir=data_dir)

    w1 = Work(title="Artigo 1", doi="10.1000/1", year=2023)
    w2 = Work(title="Artigo 2", doi="10.1000/2", year=2024)
    w3 = Work(title="Artigo Novo 3", doi="10.1000/3", year=2025)

    _s1, l1 = store.record_search(
        {"query": "ia medicina", "kind": "terms", "status": "complete", "sources": [{"name": "openalex", "status": "ok"}]},
        {"query": "ia medicina", "status": "complete", "works": [w1.to_dict(), w2.to_dict()]},
    )
    _s2, l2 = store.record_search(
        {"query": "ia medicina", "kind": "terms", "status": "complete", "sources": [{"name": "openalex", "status": "ok"}]},
        {"query": "ia medicina", "status": "complete", "works": [w1.to_dict(), w2.to_dict(), w3.to_dict()]},
    )

    res = compare_search_versions(l1["id"], l2["id"])

    assert res["base_list_id"] == l1["id"]
    assert res["new_list_id"] == l2["id"]
    assert res["base_total"] == 2
    assert res["new_total"] == 3
    assert res["added_count"] == 1
    assert res["retained_count"] == 2
    assert "report_markdown" in res
    assert "Artigo Novo 3" in res["report_markdown"]


def test_server_compare_search_versions_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))

    with pytest.raises(ToolError, match="list_not_found"):
        compare_search_versions("l-0099", "l-0098")


def test_server_update_search_differential_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))

    with pytest.raises(ToolError, match="list_not_found"):
        update_search_differential("l-0099")
