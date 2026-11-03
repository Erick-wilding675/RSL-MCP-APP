"""Testes do exportador CSV compatível com Scopus / VOSviewer."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

import httpx
import pytest

from rslapp.core.models import Affiliation, Author, Work
from rslapp.exporters import get_exporter, run_export
from rslapp.exporters.csv import CSV_COLUMNS, CSVExporter
from rslapp.sources.openalex import OpenAlexSource
from rslapp.store import Store


# FR-06, FR-12, D-002, D-004: Exportador CSV gera cabeçalho Scopus, UTF-8 BOM e dados formatados
def test_fr06_fr12_d002_csv_cabecalho_scopus_e_bom() -> None:
    exporter = get_exporter("csv")
    assert isinstance(exporter, CSVExporter)
    assert exporter.format == "csv"
    assert exporter.extension == "csv"

    work = Work(
        title='Machine Learning: "A Review, and Perspectives"',
        doi="10.1000/182",
        year=2023,
        type="journal-article",
        venue="AI Journal",
        abstract="Resumo com vírgula, aspas \"duplas\" e\nquebra de linha interna.",
        keywords=["machine learning", "deep learning"],
        authors=[
            Author(
                name="Turing, Alan",
                affiliations=[Affiliation(name="University of Manchester")],
                raw_affiliations=["Manchester, UK"],
            ),
            Author(
                name="Lovelace, Ada",
                affiliations=[Affiliation(name="London")],
            ),
        ],
        references=["W123", "10.2000/ref.already.doi"],
        citations={"openalex": 45, "crossref": 30, "semantic_scholar": 50},
        source_ids={"openalex": "W999", "crossref": "10.1000/182", "semantic_scholar": "S123"},
    )

    list_data: dict[str, Any] = {"works": [work]}
    doi_mapping = {"W123": "10.3000/resolved.w123"}

    content = exporter.render(list_data, doi_mapping=doi_mapping)

    # UTF-8 BOM
    assert content.startswith("\ufeff")
    raw_bytes = content.encode("utf-8")
    assert raw_bytes.startswith(b"\xef\xbb\xbf")

    # Lê de volta com o módulo csv padrão do Python
    reader = csv.reader(io.StringIO(content.lstrip("\ufeff")), delimiter=",")
    rows = list(reader)
    assert len(rows) == 2

    header = rows[0]
    assert tuple(header) == CSV_COLUMNS
    assert header == [
        "Authors",
        "Author full names",
        "Title",
        "Year",
        "Source title",
        "DOI",
        "Abstract",
        "Author Keywords",
        "References",
        "Cited by",
        "Affiliations",
        "Document Type",
        "Source",
        "OpenAlex ID",
        "Crossref DOI",
        "Semantic Scholar ID",
        "Citations OpenAlex",
        "Citations Crossref",
        "Citations Semantic Scholar",
    ]

    data = rows[1]
    assert data[0] == "Turing, Alan; Lovelace, Ada"
    assert data[1] == "Turing, Alan; Lovelace, Ada"
    assert data[2] == 'Machine Learning: "A Review, and Perspectives"'
    assert data[3] == "2023"
    assert data[4] == "AI Journal"
    assert data[5] == "10.1000/182"
    # Quebra de linha, vírgulas e aspas preservadas no resumo
    assert data[6] == "Resumo com vírgula, aspas \"duplas\" e\nquebra de linha interna."
    assert data[7] == "machine learning; deep learning"
    assert data[8] == "10.3000/resolved.w123; 10.2000/ref.already.doi"
    assert data[9] == "50"  # maior número entre 45, 30 e 50
    assert data[10] == "University of Manchester; Manchester, UK; London"
    assert data[11] == "journal-article"
    assert data[12] == "RSL.app"
    assert data[13] == "W999"
    assert data[14] == "10.1000/182"
    assert data[15] == "S123"
    assert data[16] == "45"
    assert data[17] == "30"
    assert data[18] == "50"


# FR-06, FR-14, D-010: Referências sem DOI não entram na coluna de referências do CSV
def test_fr06_fr14_d010_csv_referencias_sem_doi_sao_omitidas() -> None:
    exporter = CSVExporter()
    work = Work(
        title="Estudo com Referências Mistas",
        references=["W10", "W20", "W30", "10.4000/direto"],
    )
    list_data: dict[str, Any] = {"works": [work]}
    # W10 virou DOI, W20 não tem DOI (None), W30 omitido (sem mapping)
    doi_mapping = {"W10": "10.1000/w10", "W20": None}

    content = exporter.render(list_data, doi_mapping=doi_mapping)
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")), delimiter=",")
    row = next(reader)
    assert row["References"] == "10.1000/w10; 10.4000/direto"


# FR-06, FR-12, FR-14, D-002: run_export com csv resolve referências via OpenAlex
def test_fr06_fr12_fr14_d002_run_export_csv_com_resolucao_referencias(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    work = Work(
        title="Trabalho com Referência OpenAlex",
        doi="10.1000/t1",
        references=["W100"],
    )
    _search, saved_list = store.record_search(
        {"kind": "terms", "query": "q", "sources": []},
        {"status": "complete", "works": [work.to_dict()]},
    )
    list_id = str(saved_list["id"])
    export_dir = tmp_path / "exports"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {"id": "https://openalex.org/W100", "doi": "https://doi.org/10.1000/ref.w100"}
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    source = OpenAlexSource(client=client)

    import os

    os.environ["OPENALEX_API_KEY"] = "fake-key-123"
    try:
        res = run_export(
            store,
            list_id=list_id,
            export_format="csv",
            export_dir=export_dir,
            source=source,
        )
    finally:
        os.environ.pop("OPENALEX_API_KEY", None)

    assert res["format"] == "csv"
    assert res["count"] == 1
    assert "warnings" not in res

    dest_file = Path(res["path"])
    assert dest_file.exists()
    content = dest_file.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    row = next(reader)
    assert row["References"] == "10.1000/ref.w100"


# FR-06, FR-14, NFR-03: Sem chave, resolução fica incompleta e adiciona warning
def test_fr06_fr14_nfr03_run_export_csv_sem_chave_adiciona_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    store = Store(tmp_path / "data")
    work = Work(
        title="Trabalho sem Chave",
        doi="10.1000/t2",
        references=["W200"],
    )
    _search, saved_list = store.record_search(
        {"kind": "terms", "query": "q", "sources": []},
        {"status": "complete", "works": [work.to_dict()]},
    )
    list_id = str(saved_list["id"])
    export_dir = tmp_path / "exports"

    res = run_export(
        store,
        list_id=list_id,
        export_format="csv",
        export_dir=export_dir,
    )
    assert res["format"] == "csv"
    assert res["count"] == 1
    assert "warnings" in res
    assert res["warnings"] == ["referências: missing_key"]

    dest_file = Path(res["path"])
    assert dest_file.exists()
    content = dest_file.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    row = next(reader)
    assert row["References"] == ""


# FR-06: Tipo inválido em list_data levanta TypeError
def test_fr06_csv_list_data_invalido_levanta_type_error() -> None:
    exporter = CSVExporter()
    with pytest.raises(TypeError):
        exporter.render(None)  # type: ignore[arg-type]
