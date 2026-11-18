"""Testes de integração das ferramentas MCP de triagem, PRISMA 2020 e declaração de IA (FR-25, FR-26, FR-27, D-036, D-037, D-038)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp import Client

from rslapp import server
from rslapp.store import Store

ENV_VARS = (
    "RSL_DATA_DIR",
    "RSL_EXPORT_DIR",
    "RSL_CACHE_DAYS",
    "RSL_HTTP_HOST",
    "RSL_HTTP_PORT",
    "RSL_PUBLIC_URL",
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    data_dir = tmp_path / "rsl_data"
    export_dir = tmp_path / "rsl_export"
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("RSL_EXPORT_DIR", str(export_dir))
    return data_dir


def _extract_result_dict(call_result: Any) -> dict[str, Any]:
    sc = call_result.structured_content
    if isinstance(sc, dict) and "result" in sc and isinstance(sc["result"], dict):
        return sc["result"]
    assert isinstance(sc, dict)
    return sc


def _create_sample_list(data_dir: Path) -> str:
    st = Store(data_dir)
    search_data = {
        "kind": "terms",
        "request_summary": "inteligência artificial em cardiologia",
        "sources": [
            {"name": "openalex", "status": "ok", "fetched": 10, "found": 10},
            {"name": "crossref", "status": "ok", "fetched": 5, "found": 5},
        ],
    }
    list_data = {
        "status": "complete",
        "total": 12,
        "works": [
            {"doi": f"10.1000/{i}", "title": f"Cardio AI Estudo {i}", "source": "openalex"}
            for i in range(12)
        ],
    }
    _, recorded_list = st.record_search(search_data, list_data)
    return recorded_list["id"]


# D-002, D-006, D-029, FR-20: Verificação do registro e anotações das ferramentas MCP
@pytest.mark.anyio
async def test_screening_tools_registration_fr25_fr26_fr27() -> None:
    async with Client(server.mcp) as client:
        tools_res = await client.list_tools()
        tools_by_name = {t.name: t for t in tools_res.tools}

        # screen_work (aditiva)
        assert "screen_work" in tools_by_name
        tool_sw = tools_by_name["screen_work"]
        assert tool_sw.annotations is not None
        assert tool_sw.annotations.read_only_hint is False
        assert tool_sw.annotations.destructive_hint is False

        # get_screening_status (read-only)
        assert "get_screening_status" in tools_by_name
        assert tools_by_name["get_screening_status"].annotations.read_only_hint is True

        # get_prisma_flow (read-only)
        assert "get_prisma_flow" in tools_by_name
        assert tools_by_name["get_prisma_flow"].annotations.read_only_hint is True

        # get_ai_disclosure (read-only)
        assert "get_ai_disclosure" in tools_by_name
        assert tools_by_name["get_ai_disclosure"].annotations.read_only_hint is True


# FR-25, D-036: Teste de ponta a ponta de screen_work e get_screening_status via MCP
@pytest.mark.anyio
async def test_screen_work_and_status_tool_fr25_d036(isolated_env: Path) -> None:
    list_id = _create_sample_list(isolated_env)

    async with Client(server.mcp) as client:
        # Decisão 1: inclusão com IA
        res1 = await client.call_tool(
            "screen_work",
            {
                "list_id": list_id,
                "work_id": "10.1000/0",
                "decision": "included",
                "decided_by": "ai:claude-3-5-sonnet",
                "notes": "Artigo central sobre ECG e redes neurais",
            },
        )
        data1 = _extract_result_dict(res1)
        assert data1["status"] == "ok"
        assert data1["decision"]["decision"] == "included"
        assert data1["decision"]["decided_by"] == "ai:claude-3-5-sonnet"
        assert data1["summary"]["included"] == 1
        assert data1["summary"]["screened"] == 1

        # Decisão 2: exclusão com pesquisador humano
        res2 = await client.call_tool(
            "screen_work",
            {
                "list_id": list_id,
                "work_id": "10.1000/1",
                "decision": "excluded",
                "reason": "População não elegível",
                "decided_by": "human:dr_erick",
            },
        )
        data2 = _extract_result_dict(res2)
        assert data2["decision"]["decision"] == "excluded"
        assert data2["summary"]["excluded"] == 1
        assert data2["summary"]["screened"] == 2

        # Consulta de status
        res_status = await client.call_tool("get_screening_status", {"list_id": list_id})
        status_data = _extract_result_dict(res_status)
        assert status_data["total_works"] == 12
        assert status_data["screened"] == 2
        assert status_data["pending"] == 10
        assert status_data["included"] == 1
        assert status_data["excluded"] == 1
        assert status_data["reasons"]["População não elegível"] == 1
        assert status_data["by_author"]["ai"] == 1
        assert status_data["by_author"]["human"] == 1


# FR-26, D-037: Teste da ferramenta get_prisma_flow via MCP
@pytest.mark.anyio
async def test_get_prisma_flow_tool_fr26_d037(isolated_env: Path) -> None:
    list_id = _create_sample_list(isolated_env)

    async with Client(server.mcp) as client:
        # Triar alguns trabalhos
        await client.call_tool(
            "screen_work",
            {"list_id": list_id, "work_id": "10.1000/0", "decision": "included"},
        )
        await client.call_tool(
            "screen_work",
            {
                "list_id": list_id,
                "work_id": "10.1000/1",
                "decision": "excluded",
                "reason": "Fora do tema / escopo",
            },
        )

        res_flow = await client.call_tool(
            "get_prisma_flow",
            {"list_id": list_id, "include_svg": True},
        )
        flow_data = _extract_result_dict(res_flow)
        assert "flow" in flow_data
        assert "report_markdown" in flow_data
        assert "svg" in flow_data

        f = flow_data["flow"]
        assert f["identification"]["records_total"] == 15  # 10 openalex + 5 crossref
        assert f["identification"]["duplicates_removed"] == 3  # 15 - 12
        assert f["screening"]["records_screened"] == 2
        assert f["screening"]["records_excluded"] == 1
        assert f["included"]["studies_included"] == 1
        assert "<svg" in flow_data["svg"]
        assert "Checklist PRISMA-S" in flow_data["report_markdown"]


# FR-27, D-038: Teste da ferramenta get_ai_disclosure via MCP
@pytest.mark.anyio
async def test_get_ai_disclosure_tool_fr27_d038(isolated_env: Path) -> None:
    list_id = _create_sample_list(isolated_env)

    async with Client(server.mcp) as client:
        await client.call_tool(
            "screen_work",
            {
                "list_id": list_id,
                "work_id": "10.1000/0",
                "decision": "included",
                "decided_by": "ai:gpt-4o",
            },
        )

        res_pt = await client.call_tool(
            "get_ai_disclosure",
            {"list_id": list_id, "language": "pt"},
        )
        pt_data = _extract_result_dict(res_pt)
        assert pt_data["language"] == "pt"
        assert "Committee on Publication Ethics (COPE)" in pt_data["disclosure_markdown"]
        assert "SciELO Brasil" in pt_data["disclosure_markdown"]
        assert "Supervisão e Responsabilidade Humana" in pt_data["disclosure_markdown"]

        res_en = await client.call_tool(
            "get_ai_disclosure",
            {"list_id": list_id, "language": "en"},
        )
        en_data = _extract_result_dict(res_en)
        assert en_data["language"] == "en"
        assert "Statement on Artificial Intelligence" in en_data["disclosure_markdown"]
        assert "Human Authorship and Scientific Accountability" in en_data["disclosure_markdown"]
