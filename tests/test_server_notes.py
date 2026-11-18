"""Testes das ferramentas de fichamento científico no servidor MCP (FR-29, D-040)."""

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
async def test_fr29_d040_server_notes_lifecycle(isolated_env: Path) -> None:
    store = Store(isolated_env / "data")
    search_data = {
        "kind": "terms",
        "request_summary": "busca de teste de notas",
        "sources": [{"name": "openalex", "status": "ok", "fetched": 1, "found": 1}],
    }
    list_data = {
        "query": "busca notas",
        "status": "complete",
        "total": 1,
        "works": [
            {
                "id": "W123",
                "doi": "10.1000/123",
                "title": "Machine Learning in Healthcare",
                "year": 2024,
                "authors": [{"name": "Turing, Alan"}],
                "venue": "Nature Health",
                "source": "openalex",
            }
        ],
    }
    _, l_rec = store.record_search(search_data, list_data)
    list_id = l_rec["id"]

    async with Client(server.mcp) as client:
        # 1. Salvar nota sugerida por IA
        save_res = await client.call_tool(
            "save_work_note",
            {
                "list_id": list_id,
                "work_id": "W123",
                "objective": "Avaliar modelos preditivos em diagnóstico hospitalar.",
                "methodology": "Coorte retrospectiva com 10.000 pacientes.",
                "results": "AUC de 0.94 na detecção precoce.",
                "limitations": "Dados de centro único.",
                "personal_keywords": ["diagnóstico", "aprendizado de máquina"],
                "source": "ai_suggested",
                "ai_model": "Claude 3.5 Sonnet",
            },
        )
        assert save_res.is_error is False
        save_data = _extract_result_dict(save_res)
        assert save_data["status"] == "saved"
        assert save_data["source"] == "ai_suggested"
        assert save_data["note"]["title"] == "Machine Learning in Healthcare"
        assert save_data["note"]["abnt_reference"] is not None

        # 2. Obter nota
        get_res = await client.call_tool(
            "get_work_note",
            {"list_id": list_id, "work_id": "W123"},
        )
        assert get_res.is_error is False
        get_data = _extract_result_dict(get_res)
        assert get_data["note"]["objective"] == "Avaliar modelos preditivos em diagnóstico hospitalar."

        # 3. Listar notas
        list_res = await client.call_tool(
            "list_work_notes",
            {"list_id": list_id},
        )
        assert list_res.is_error is False
        list_notes_data = _extract_result_dict(list_res)
        assert list_notes_data["total_notes"] == 1
        assert list_notes_data["notes"][0]["work_id"] == "W123"

        # 4. Exportar em Markdown
        export_res = await client.call_tool(
            "export_notes_markdown",
            {"list_id": list_id},
        )
        assert export_res.is_error is False
        export_data = _extract_result_dict(export_res)
        assert export_data["filename"] == f"notes_{list_id}.md"
        assert Path(export_data["path"]).exists()
        md_text = Path(export_data["path"]).read_text(encoding="utf-8")
        assert "Machine Learning in Healthcare" in md_text
        assert "Claude 3.5 Sonnet" in md_text


@pytest.mark.anyio
async def test_fr29_server_notes_not_found(isolated_env: Path) -> None:
    store = Store(isolated_env / "data")
    store.record_search(
        {"kind": "terms", "sources": []},
        {"query": "vazia", "status": "complete", "total": 0, "works": []},
    )

    async with Client(server.mcp) as client:
        # Nota inexistente
        res = await client.call_tool(
            "get_work_note",
            {"list_id": "l-0001", "work_id": "inexistente"},
        )
        assert res.is_error is True

        # Exportação de lista sem notas
        exp_res = await client.call_tool(
            "export_notes_markdown",
            {"list_id": "l-0001"},
        )
        assert exp_res.is_error is True
