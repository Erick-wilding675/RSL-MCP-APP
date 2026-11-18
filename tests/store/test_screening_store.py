"""Testes de persistência e resumo de triagem no Store (FR-25, D-036)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rslapp.core.screening import validate_decision_data
from rslapp.desktop.service import DesktopService
from rslapp.store import Store


@pytest.fixture
def store_with_list(tmp_path: Path) -> tuple[Store, str]:
    """Cria um Store com uma lista salva em lists/l-0001.json."""
    store = Store(data_dir=tmp_path)
    store.lists_dir.mkdir(parents=True, exist_ok=True)
    list_id = "l-0001"
    list_payload = {
        "id": list_id,
        "search_id": "s-0001",
        "created_at": "2026-11-18T10:00:00Z",
        "total": 3,
        "works": [
            {"title": "Estudo 1", "doi": "10.1000/1", "year": 2024},
            {"title": "Estudo 2", "doi": "10.1000/2", "year": 2025},
            {"title": "Estudo 3", "doi": None, "year": 2026},
        ],
    }
    (store.lists_dir / f"{list_id}.json").write_text(
        json.dumps(list_payload, ensure_ascii=False), encoding="utf-8"
    )
    return store, list_id


def test_fr25_d036_store_salva_e_recupera_decisao(store_with_list: tuple[Store, str]) -> None:
    """Gravação de decisão cria screening/l-0001.json sem alterar o arquivo da lista."""
    store, list_id = store_with_list
    dec1 = validate_decision_data(work_id="1", decision="included", decided_by="human")

    result = store.save_screening_decision(list_id, dec1)
    assert result["list_id"] == list_id
    assert "1" in result["decisions"]
    assert result["decisions"]["1"]["decision"] == "included"

    # Confere arquivo persistido em disco
    saved = store.get_screening(list_id)
    assert saved["decisions"]["1"]["decision"] == "included"

    # Segunda decisão na mesma lista acumula sem apagar a primeira
    dec2 = validate_decision_data(
        work_id="2",
        decision="excluded",
        reason="Fora do escopo",
        decided_by="ai:claude",
    )
    updated = store.save_screening_decision(list_id, dec2)
    assert len(updated["decisions"]) == 2
    assert updated["decisions"]["2"]["reason"] == "Fora do escopo"

    # A lista original em lists/ continua intacta
    list_content = store.get_list(list_id)
    assert list_content["total"] == 3


def test_fr25_d036_store_screening_summary(store_with_list: tuple[Store, str]) -> None:
    """Store calcula resumo combinando total da lista com decisões registradas."""
    store, list_id = store_with_list
    summary_initial = store.get_screening_summary(list_id)
    assert summary_initial["total_works"] == 3
    assert summary_initial["screened"] == 0
    assert summary_initial["pending"] == 3

    dec = validate_decision_data(work_id="1", decision="included")
    store.save_screening_decision(list_id, dec)

    summary_after = store.get_screening_summary(list_id)
    assert summary_after["screened"] == 1
    assert summary_after["pending"] == 2
    assert summary_after["included"] == 1
    assert summary_after["progress_percent"] == 33.3


def test_fr25_d036_desktop_service_screening(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """DesktopService expõe operações de triagem respeitando configuração de dados."""
    data_dir = tmp_path / "data"
    export_dir = tmp_path / "exports"
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("RSL_EXPORT_DIR", str(export_dir))

    store = Store(data_dir)
    store.lists_dir.mkdir(parents=True, exist_ok=True)
    list_id = "l-0002"
    (store.lists_dir / f"{list_id}.json").write_text(
        json.dumps({"id": list_id, "total": 2, "works": []}), encoding="utf-8"
    )

    service = DesktopService()
    dec = validate_decision_data(work_id="1", decision="excluded", reason="Critério 1")
    service.save_screening_decision(list_id, dec)

    screening = service.get_screening(list_id)
    assert "1" in screening["decisions"]

    summary = service.get_screening_summary(list_id)
    assert summary["total_works"] == 2
    assert summary["screened"] == 1
    assert summary["excluded"] == 1
