"""Testes do exportador JSON completo."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from rslapp.core.models import Affiliation, Author, Work
from rslapp.exporters import get_exporter, run_export
from rslapp.exporters.json import JSONExporter
from rslapp.store import Store


# FR-06, FR-12, D-002: Exportador JSON guarda todos os campos, exported_at e format_version: 1
def test_fr06_fr12_d002_json_guarda_campos_completos() -> None:
    exporter = get_exporter("json")
    assert isinstance(exporter, JSONExporter)
    assert exporter.format == "json"
    assert exporter.extension == "json"

    work = Work(
        title="Estudo de Caso sobre Redes Complexas",
        doi="10.5555/estudo.2024",
        year=2024,
        type="article",
        venue="Journal of Systems",
        abstract="Análise empírica de métricas de centralidade.",
        keywords=["redes", "centralidade"],
        authors=[
            Author(
                name="Maria Silva",
                orcid="0000-0002-1825-0097",
                ids={"openalex": "A123", "crossref": "CR-M"},
                position="first",
                is_corresponding=True,
                affiliations=[
                    Affiliation(name="Universidade Federal", ids={"ror": "01abc"}, country_code="BR")
                ],
                raw_affiliations=["UF, Brasil"],
            )
        ],
        references=["W100", "10.1000/ref1"],
        references_count=2,
        citations={"openalex": 10, "crossref": 8, "semantic_scholar": 12},
        source_ids={"openalex": "W999", "crossref": "10.5555/estudo.2024"},
    )

    list_data: dict[str, Any] = {
        "id": "l-0001",
        "search_id": "s-0001",
        "status": "complete",
        "total": 1,
        "works": [work],
    }

    raw_json = exporter.render(list_data)
    # Verifica indentação
    assert raw_json.startswith("{\n")
    assert raw_json.endswith("\n")

    parsed = json.loads(raw_json)
    assert parsed["id"] == "l-0001"
    assert parsed["search_id"] == "s-0001"
    assert parsed["status"] == "complete"
    assert parsed["total"] == 1
    assert parsed["format_version"] == 1

    # exported_at é timestamp ISO UTC válido
    exported_at_str = parsed["exported_at"]
    parsed_dt = datetime.fromisoformat(exported_at_str.replace("Z", "+00:00"))
    assert parsed_dt.tzinfo == timezone.utc

    # Obras completas serializadas
    assert len(parsed["works"]) == 1
    w_out = parsed["works"][0]
    assert w_out["title"] == "Estudo de Caso sobre Redes Complexas"
    assert w_out["doi"] == "10.5555/estudo.2024"
    assert w_out["year"] == 2024
    assert w_out["type"] == "article"
    assert w_out["venue"] == "Journal of Systems"
    assert w_out["abstract"] == "Análise empírica de métricas de centralidade."
    assert w_out["keywords"] == ["redes", "centralidade"]
    assert w_out["references"] == ["W100", "10.1000/ref1"]
    assert w_out["references_count"] == 2
    assert w_out["citations"] == {"openalex": 10, "crossref": 8, "semantic_scholar": 12}
    assert w_out["source_ids"] == {"openalex": "W999", "crossref": "10.5555/estudo.2024"}

    author_out = w_out["authors"][0]
    assert author_out["name"] == "Maria Silva"
    assert author_out["orcid"] == "0000-0002-1825-0097"
    assert author_out["ids"] == {"openalex": "A123", "crossref": "CR-M"}
    assert author_out["position"] == "first"
    assert author_out["is_corresponding"] is True
    assert author_out["affiliations"] == [
        {"name": "Universidade Federal", "ids": {"ror": "01abc"}, "country_code": "BR"}
    ]
    assert author_out["raw_affiliations"] == ["UF, Brasil"]


# FR-06, FR-12, D-002: run_export com json grava <list_id>.json com gravação atômica
def test_fr06_fr12_d002_run_export_json_grava_arquivo(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    work = Work(title="Artigo Simples", doi="10.1234/s")
    _search, saved_list = store.record_search(
        {"kind": "terms", "query": "q", "sources": []},
        {"status": "complete", "works": [work.to_dict()]},
    )
    list_id = str(saved_list["id"])
    export_dir = tmp_path / "exports"

    res = run_export(store, list_id=list_id, export_format="json", export_dir=export_dir)
    assert res["format"] == "json"
    assert res["count"] == 1
    expected_path = export_dir / f"{list_id}.json"
    assert res["path"] == str(expected_path)
    assert expected_path.exists()

    content = json.loads(expected_path.read_text(encoding="utf-8"))
    assert content["id"] == list_id
    assert content["format_version"] == 1
    assert "exported_at" in content
    assert len(content["works"]) == 1
    assert content["works"][0]["title"] == "Artigo Simples"


# FR-06: Tipo inválido em list_data levanta TypeError
def test_fr06_json_list_data_invalido_levanta_type_error() -> None:
    exporter = JSONExporter()
    with pytest.raises(TypeError):
        exporter.render(123)  # type: ignore[arg-type]
