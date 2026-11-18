"""Testes das ferramentas MCP de descritores DeCS/MeSH trilíngues (FR-33, D-044)."""

from __future__ import annotations

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from rslapp.server import build_multilingual_search_query, lookup_descriptors


def test_server_lookup_descriptors() -> None:
    res = lookup_descriptors(query="telemedicina", lang="pt")
    assert res["query"] == "telemedicina"
    assert res["total_matches"] >= 1
    top = res["descriptors"][0]
    assert top["id"] == "D017216"
    assert top["terms"]["en"] == "Telemedicine"


def test_server_build_multilingual_search_query() -> None:
    res = build_multilingual_search_query(descriptors=["D017216"], operator="OR")
    assert res["operator"] == "OR"
    assert "queries" in res
    assert '"Telemedicina"' in res["queries"]["pt"]
    assert '"Telemedicine"' in res["queries"]["en"]


def test_server_build_multilingual_search_query_empty() -> None:
    with pytest.raises(ToolError, match="invalid_input"):
        build_multilingual_search_query(descriptors=[])
