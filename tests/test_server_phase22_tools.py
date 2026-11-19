"""Testes das ferramentas MCP da Fase 22: fulltext, extracao, risco de vies e concordancia (FR-38, D-049)."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from rslapp.server import (
    export_extraction_csv,
    fetch_fulltext,
    get_extraction_table,
    get_fulltext_status,
    get_risk_of_bias_summary,
    get_screening_concordance,
    save_extraction_data,
    save_risk_of_bias,
)
from rslapp.store import Store


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def setup_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Store, str]:
    data_dir = tmp_path / "data"
    export_dir = tmp_path / "exports"
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("RSL_EXPORT_DIR", str(export_dir))

    store = Store(data_dir=data_dir)
    search_data = {
        "kind": "terms",
        "request_summary": "revisao teste",
        "sources": [{"name": "openalex", "status": "ok", "fetched": 1, "found": 1}],
    }
    list_data = {
        "query": "revisao teste",
        "status": "complete",
        "total": 1,
        "works": [
            {
                "id": "w1",
                "doi": "10.1234/ensaio",
                "title": "Ensaio Clinico de Exemplo",
                "year": 2024,
                "authors": [{"name": "Silva, J."}],
                "venue": "Revista Teste",
                "type": "article",
                "source_ids": {"pmc": "PMC1234567"},
            }
        ],
    }
    _s_rec, l_rec = store.record_search(search_data, list_data)
    list_id = l_rec["id"]
    return store, list_id


# FR-34, D-045: Teste das ferramentas fetch_fulltext e get_fulltext_status
@pytest.mark.anyio
async def test_mcp_fulltext_tools(setup_store: tuple[Store, str]) -> None:
    _store, list_id = setup_store

    valid_pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

    def mock_pdf(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=valid_pdf_content, headers={"Content-Type": "application/pdf"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_pdf)) as client:
        # Chama fetch_fulltext
        res = await fetch_fulltext(list_id=list_id, work_id="w1", client=client)
        assert res["list_id"] == list_id
        assert res["work_id"] == "w1"
        rec = res["record"]
        assert rec["status"] in ("available", "downloaded")

        # Chama get_fulltext_status
        status = get_fulltext_status(list_id=list_id)
        assert status["list_id"] == list_id
        assert status["total_checked"] >= 1
        assert "records" in status


# FR-35, D-046: Teste das ferramentas de extração para metanálise
def test_mcp_extraction_tools(setup_store: tuple[Store, str]) -> None:
    _store, list_id = setup_store

    # Salva extração
    save_res = save_extraction_data(
        list_id=list_id,
        work_id="w1",
        study_design="RCT",
        outcomes=[{"name": "Mortalidade", "outcome_type": "dichotomous", "events_intervention": 5, "n_intervention": 50}],
        sample_size_total=100,
        country="Brasil",
    )
    assert save_res["work_id"] == "w1"
    assert save_res["extraction"]["country"] == "Brasil"

    # Obtém tabela consolidada
    table = get_extraction_table(list_id=list_id)
    assert table["count"] == 1
    assert table["extractions"][0]["work_id"] == "w1"

    # Exporta para CSV (metafor)
    exp = export_extraction_csv(list_id=list_id, format="metafor")
    assert exp["format"] == "metafor"
    assert "study_id,author_year" in exp["content"]
    assert Path(exp["path"]).exists()


# FR-36, D-047: Teste das ferramentas de risco de viés
def test_mcp_risk_of_bias_tools(setup_store: tuple[Store, str]) -> None:
    _store, list_id = setup_store

    # Salva RoB 2
    rob_res = save_risk_of_bias(
        list_id=list_id,
        work_id="w1",
        tool="rob2",
        domains=[{"domain_id": "D1", "domain_name": "Randomização", "judgment": "low"}],
    )
    assert rob_res["work_id"] == "w1"
    assert rob_res["risk_of_bias"]["overall_judgment"] == "low"

    # Obtém matriz de semáforo
    summary = get_risk_of_bias_summary(list_id=list_id)
    assert summary["count"] == 1
    assert "matrix" in summary
    assert len(summary["matrix"]["rows"]) == 1


# FR-37, D-048: Teste de get_screening_concordance
def test_mcp_screening_concordance(setup_store: tuple[Store, str]) -> None:
    store, list_id = setup_store
    store.save_screening_decision(list_id, {"work_id": "w1", "decision": "included", "decided_by": "human"})

    res = get_screening_concordance(list_id=list_id)
    assert res["list_id"] == list_id
    concordance = res["concordance"]
    assert "kappa" in concordance
    assert concordance["n_common"] == 1
    assert concordance["observed_agreement"] == 1.0
