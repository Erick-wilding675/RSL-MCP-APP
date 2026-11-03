"""Testes do exportador DOIs (um DOI por linha)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from rslapp.core.models import Work
from rslapp.exporters import get_exporter, run_export
from rslapp.exporters.dois import DOIsExporter
from rslapp.store import Store


# FR-06, D-002: Exportador DOIs renderiza um DOI por linha apenas para trabalhos com DOI
def test_fr06_d002_dois_renderiza_apenas_trabalhos_com_doi() -> None:
    exporter = get_exporter("dois")
    assert isinstance(exporter, DOIsExporter)
    assert exporter.format == "dois"
    assert exporter.extension == "dois.txt"

    list_data: dict[str, Any] = {
        "works": [
            Work(title="Artigo 1", doi="10.1000/artigo.1"),
            Work(title="Artigo 2 sem DOI", doi=None),
            Work(title="Artigo 3", doi="https://doi.org/10.1000/artigo.3"),
            Work(title="Artigo 4 vazio", doi="   "),
            Work(title="Artigo 5 dx", doi="http://dx.doi.org/10.1000/artigo.5"),
        ]
    }

    content = exporter.render(list_data)
    assert content == "10.1000/artigo.1\n10.1000/artigo.3\n10.1000/artigo.5\n"
    assert exporter.get_count(list_data) == 3


# FR-06, D-002: Lista sem nenhum DOI renderiza string vazia e count zero
def test_fr06_d002_dois_lista_sem_doi_renderiza_vazio() -> None:
    exporter = DOIsExporter()
    list_data: dict[str, Any] = {
        "works": [
            Work(title="Artigo 1", doi=None),
            Work(title="Artigo 2", doi=""),
        ]
    }
    assert exporter.render(list_data) == ""
    assert exporter.get_count(list_data) == 0


# FR-06, FR-12, D-002: run_export com dois grava <list_id>.dois.txt e count é o número de linhas
def test_fr06_fr12_d002_run_export_dois_grava_arquivo(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    works = [
        Work(title="Artigo 1", doi="10.1111/1"),
        Work(title="Artigo 2", doi=None),
        Work(title="Artigo 3", doi="10.2222/2"),
    ]
    _search, saved_list = store.record_search(
        {"kind": "terms", "query": "q", "sources": []},
        {"status": "complete", "works": [w.to_dict() for w in works]},
    )
    list_id = str(saved_list["id"])
    export_dir = tmp_path / "exports"

    res = run_export(store, list_id=list_id, export_format="dois", export_dir=export_dir)
    assert res["format"] == "dois"
    assert res["count"] == 2
    expected_path = export_dir / f"{list_id}.dois.txt"
    assert res["path"] == str(expected_path)
    assert expected_path.exists()
    assert expected_path.read_text(encoding="utf-8") == "10.1111/1\n10.2222/2\n"


# FR-06: Tipo inválido em list_data levanta TypeError
def test_fr06_dois_list_data_invalido_levanta_type_error() -> None:
    exporter = DOIsExporter()
    with pytest.raises(TypeError):
        exporter.render(["nao-dict"])  # type: ignore[arg-type]
