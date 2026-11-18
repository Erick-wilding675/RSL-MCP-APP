"""Testes das ferramentas de protocolo metodológico no servidor MCP (FR-30, D-041)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp import Client

from rslapp import server


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
async def test_fr30_d041_server_protocols_lifecycle(isolated_env: Path) -> None:
    async with Client(server.mcp) as client:
        # 1. Salvar novo protocolo
        save_res = await client.call_tool(
            "save_protocol",
            {
                "title": "Protocolo sobre Agentes de IA em Revisões Sistemáticas",
                "framework": "pico",
                "question": "Como agentes de IA afetam a precisão de revisões sistemáticas?",
                "subquestions": ["Qual o impacto no tempo de triagem?"],
                "components": {
                    "population": "Pesquisadores acadêmicos",
                    "intervention": "Uso de sistemas multiagente autônomos",
                    "comparison": "Processo manual tradicional",
                    "outcome": "Acurácia de seleção e redução de tempo",
                },
                "inclusion_criteria": ["Estudos revisados por pares", "Medição empírica"],
                "exclusion_criteria": ["Comentários e editoriais"],
                "planned_sources": ["openalex", "pubmed"],
                "search_strategy": "('AI agents' OR 'LLM') AND 'systematic review'",
                "authors": ["Erick Mendes"],
                "status": "registered",
                "registration_platform": "PROSPERO",
                "registration_number": "CRD42026111111",
                "ai_assisted": True,
                "ai_model": "Claude 3.5 Sonnet",
            },
        )
        assert save_res.is_error is False
        save_data = _extract_result_dict(save_res)
        assert save_data["status"] == "saved"
        assert save_data["version"] == 1
        protocol_id = save_data["protocol_id"]
        assert protocol_id.startswith("prot_")

        # 2. Consultar protocolo
        get_res = await client.call_tool(
            "get_protocol",
            {"protocol_id": protocol_id},
        )
        assert get_res.is_error is False
        get_data = _extract_result_dict(get_res)
        assert get_data["protocol"]["title"] == "Protocolo sobre Agentes de IA em Revisões Sistemáticas"
        assert get_data["protocol"]["framework"] == "pico"
        assert get_data["protocol"]["registration_number"] == "CRD42026111111"

        # 3. Listar protocolos
        list_res = await client.call_tool("list_protocols", {})
        assert list_res.is_error is False
        list_data = _extract_result_dict(list_res)
        assert list_data["count"] == 1
        assert list_data["protocols"][0]["id"] == protocol_id

        # 4. Atualizar protocolo gerando versão 2
        update_res = await client.call_tool(
            "save_protocol",
            {
                "protocol_id": protocol_id,
                "title": "Protocolo sobre Agentes de IA (v2 Refinado)",
                "framework": "pico",
                "question": "Pergunta refinada?",
                "inclusion_criteria": ["Critério novo adicionado"],
            },
        )
        assert update_res.is_error is False
        update_data = _extract_result_dict(update_res)
        assert update_data["version"] == 2

        # 5. Exportar protocolo em Markdown
        export_res = await client.call_tool(
            "export_protocol_markdown",
            {"protocol_id": protocol_id},
        )
        assert export_res.is_error is False
        export_data = _extract_result_dict(export_res)
        assert export_data["version"] == 2
        assert "content" in export_data
        assert "# Protocolo sobre Agentes de IA (v2 Refinado)" in export_data["content"]
        assert Path(export_data["path"]).exists()
