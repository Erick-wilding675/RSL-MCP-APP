"""Testes do exportador OpenAlex URL (consulta para VOSviewer)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from rslapp.core.errors import RSLError
from rslapp.core.models import Work
from rslapp.exporters import get_exporter, run_export
from rslapp.exporters.openalex_url import OpenAlexURLExporter
from rslapp.store import Store


# FR-06, D-002: Exportador OpenAlex URL gera URLs em grupos de até 100 IDs
def test_fr06_d002_openalex_url_grupos_de_100_ids() -> None:
    exporter = get_exporter("openalex_url")
    assert isinstance(exporter, OpenAlexURLExporter)
    assert exporter.format == "openalex_url"
    assert exporter.extension == "openalex.txt"

    # Cria 150 trabalhos com IDs do OpenAlex
    works = [
        Work(
            title=f"Trabalho {i}",
            source_ids={"openalex": f"W{i}"},
        )
        for i in range(150)
    ]
    list_data: dict[str, Any] = {"works": works}

    urls = exporter.generate_urls(list_data)
    assert len(urls) == 2

    # Lote 1 tem 100 ids
    assert urls[0].startswith("https://api.openalex.org/works?filter=openalex:")
    filter_1 = urls[0].removeprefix("https://api.openalex.org/works?filter=openalex:")
    ids_1 = filter_1.split("|")
    assert len(ids_1) == 100
    assert ids_1[0] == "W0"
    assert ids_1[-1] == "W99"

    # Lote 2 tem 50 ids
    assert urls[1].startswith("https://api.openalex.org/works?filter=openalex:")
    filter_2 = urls[1].removeprefix("https://api.openalex.org/works?filter=openalex:")
    ids_2 = filter_2.split("|")
    assert len(ids_2) == 50
    assert ids_2[0] == "W100"
    assert ids_2[-1] == "W149"

    # Nenhuma chave de API nas URLs
    for u in urls:
        assert "api_key" not in u
        assert "Bearer" not in u


# FR-06, D-002: URL com prefixo https://openalex.org/ é normalizada para ID curto W...
def test_fr06_d002_openalex_url_normaliza_prefixo() -> None:
    exporter = OpenAlexURLExporter()
    list_data: dict[str, Any] = {
        "works": [
            Work(title="Artigo 1", source_ids={"openalex": "https://openalex.org/W4567"}),
            Work(title="Artigo 2", source_ids={"openalex": "http://openalex.org/W8910"}),
        ]
    }
    urls = exporter.generate_urls(list_data)
    assert len(urls) == 1
    assert urls[0] == "https://api.openalex.org/works?filter=openalex:W4567|W8910"


# FR-06, D-002: Lista sem trabalhos do OpenAlex devolve erro format_not_available
def test_fr06_d002_openalex_url_sem_openalex_retorna_format_not_available() -> None:
    exporter = OpenAlexURLExporter()
    list_data: dict[str, Any] = {
        "works": [
            Work(title="Crossref Only", source_ids={"crossref": "10.1000/cr"}),
            Work(title="S2 Only", source_ids={"semantic_scholar": "s2_id"}),
        ]
    }
    with pytest.raises(RSLError) as exc_info:
        exporter.generate_urls(list_data)
    assert exc_info.value.code == "format_not_available"


# FR-06, FR-12, D-002: run_export com openalex_url devolve url, count e grava <list_id>.openalex.txt
def test_fr06_fr12_d002_run_export_openalex_url_sucesso(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    works = [
        Work(title="W1", source_ids={"openalex": "W1"}),
        Work(title="W2", source_ids={"openalex": "W2"}),
    ]
    _search, saved_list = store.record_search(
        {"kind": "terms", "query": "q", "sources": []},
        {"status": "complete", "works": [w.to_dict() for w in works]},
    )
    list_id = str(saved_list["id"])
    export_dir = tmp_path / "exports"

    res = run_export(store, list_id=list_id, export_format="openalex_url", export_dir=export_dir)
    assert res["format"] == "openalex_url"
    assert res["count"] == 1
    assert res["url"] == "https://api.openalex.org/works?filter=openalex:W1|W2"

    dest_path = Path(res["path"])
    assert dest_path == export_dir / f"{list_id}.openalex.txt"
    assert dest_path.exists()
    assert dest_path.read_text(encoding="utf-8") == "https://api.openalex.org/works?filter=openalex:W1|W2\n"


# FR-06, D-002: run_export com openalex_url em lista sem OpenAlex levanta format_not_available
def test_fr06_d002_run_export_openalex_url_sem_openalex_levanta_format_not_available(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "data")
    works = [Work(title="Crossref Only", source_ids={"crossref": "10.1000/1"})]
    _search, saved_list = store.record_search(
        {"kind": "terms", "query": "q", "sources": []},
        {"status": "complete", "works": [w.to_dict() for w in works]},
    )
    list_id = str(saved_list["id"])
    export_dir = tmp_path / "exports"

    with pytest.raises(RSLError) as exc_info:
        run_export(store, list_id=list_id, export_format="openalex_url", export_dir=export_dir)
    assert exc_info.value.code == "format_not_available"
