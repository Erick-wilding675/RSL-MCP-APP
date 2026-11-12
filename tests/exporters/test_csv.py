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
from rslapp.exporters.csv import CSV_COLUMNS, CSVExporter, _protect_formula
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
        "PubMed ID",
        "Europe PMC ID",
        "Citations Europe PMC",
        "Scopus EID",
        "Web of Science UID",
        "Citations Scopus",
        "Citations Web of Science",
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
    assert data[19] == ""
    assert data[20] == ""
    assert data[21] == ""


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


# FR-06: Proteção contra fórmula nos seis caracteres iniciais, sem alterar o meio nem Year e Cited by
@pytest.mark.parametrize("prefix", ["=", "+", "-", "@", "\t", "\r"])
def test_fr06_csv_protecao_contra_formula_seis_caracteres(prefix: str) -> None:
    assert _protect_formula(f"{prefix}valor") == f"'{prefix}valor"

    exporter = CSVExporter()
    work_inicio = Work(
        title=f"{prefix}Título com Fórmula",
        doi="10.1000/182",
        year=2024,
        type=f"{prefix}article",
        venue=f"{prefix}Journal of Formulas",
        abstract=f"{prefix}Resumo que começa com caractere de fórmula.",
        keywords=[f"{prefix}palavra-chave", "segunda"],
        authors=[
            Author(
                name=f"{prefix}Turing, Alan",
                affiliations=[Affiliation(name=f"{prefix}University of Manchester")],
            ),
            Author(name="Lovelace, Ada"),
        ],
        references=[f"{prefix}10.2000/ref.1"],
        citations={"openalex": 42, "crossref": 10, "semantic_scholar": 15},
        source_ids={
            "openalex": "=W999",
            "crossref": "+10.1000/182",
            "semantic_scholar": "-S123",
        },
    )
    work_meio = Work(
        title=f"Título com {prefix} no meio",
        doi="10.1000/183",
        year=2023,
        type=f"journal {prefix} article",
        venue=f"Journal {prefix} Venue",
        abstract=f"Resumo com {prefix} no meio da frase.",
        keywords=["primeira", f"{prefix}segunda-palavra"],
        authors=[
            Author(
                name="Lovelace, Ada",
                affiliations=[Affiliation(name="Oxford")],
            ),
            Author(
                name=f"{prefix}Turing, Alan",
                affiliations=[Affiliation(name=f"{prefix}Cambridge")],
            ),
        ],
        references=["10.2000/normal", f"{prefix}10.2000/ref.2"],
        citations={"openalex": 7},
        source_ids={"openalex": "W888"},
    )

    content = exporter.render({"works": [work_inicio, work_meio]})
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")), delimiter=",")
    rows = list(reader)
    assert len(rows) == 2

    row_inicio = rows[0]
    assert row_inicio["Abstract"] == f"'{prefix}Resumo que começa com caractere de fórmula."
    if prefix in ("\t", "\r"):
        # Com a normalização, colunas limpas por _clean_text/_clean_doi não começam com tab ou CR
        assert row_inicio["Title"] == "Título com Fórmula"
        assert row_inicio["Authors"] == "Turing, Alan; Lovelace, Ada"
        assert row_inicio["Author full names"] == "Turing, Alan; Lovelace, Ada"
        assert row_inicio["Author Keywords"] == "palavra-chave; segunda"
        assert row_inicio["Source title"] == "Journal of Formulas"
        assert row_inicio["Affiliations"] == "University of Manchester"
        assert row_inicio["Document Type"] == "article"
        assert row_inicio["References"] == "10.2000/ref.1"
    else:
        assert row_inicio["Title"] == f"'{prefix}Título com Fórmula"
        assert row_inicio["Authors"] == f"'{prefix}Turing, Alan; Lovelace, Ada"
        assert row_inicio["Author full names"] == f"'{prefix}Turing, Alan; Lovelace, Ada"
        assert row_inicio["Author Keywords"] == f"'{prefix}palavra-chave; segunda"
        assert row_inicio["Source title"] == f"'{prefix}Journal of Formulas"
        assert row_inicio["Affiliations"] == f"'{prefix}University of Manchester"
        assert row_inicio["Document Type"] == f"'{prefix}article"
        assert row_inicio["References"] == f"'{prefix}10.2000/ref.1"

    # Colunas de número e de id não mudam
    assert row_inicio["Year"] == "2024"
    assert row_inicio["Cited by"] == "42"
    assert row_inicio["Citations OpenAlex"] == "42"
    assert row_inicio["Citations Crossref"] == "10"
    assert row_inicio["Citations Semantic Scholar"] == "15"
    assert row_inicio["DOI"] == "10.1000/182"
    assert row_inicio["OpenAlex ID"] == "=W999"
    assert row_inicio["Crossref DOI"] == "+10.1000/182"
    assert row_inicio["Semantic Scholar ID"] == "-S123"

    row_meio = rows[1]
    assert row_meio["Abstract"] == f"Resumo com {prefix} no meio da frase."
    if prefix in ("\t", "\r"):
        assert row_meio["Title"] == "Título com no meio"
        assert row_meio["Authors"] == "Lovelace, Ada; Turing, Alan"
        assert row_meio["Author full names"] == "Lovelace, Ada; Turing, Alan"
        assert row_meio["Author Keywords"] == "primeira; segunda-palavra"
        assert row_meio["Source title"] == "Journal Venue"
        assert row_meio["Affiliations"] == "Oxford; Cambridge"
        assert row_meio["Document Type"] == "journal article"
        assert row_meio["References"] == "10.2000/normal; 10.2000/ref.2"
    else:
        assert row_meio["Title"] == f"Título com {prefix} no meio"
        assert row_meio["Authors"] == f"Lovelace, Ada; {prefix}Turing, Alan"
        assert row_meio["Author full names"] == f"Lovelace, Ada; {prefix}Turing, Alan"
        assert row_meio["Author Keywords"] == f"primeira; {prefix}segunda-palavra"
        assert row_meio["Source title"] == f"Journal {prefix} Venue"
        assert row_meio["Affiliations"] == f"Oxford; {prefix}Cambridge"
        assert row_meio["Document Type"] == f"journal {prefix} article"
        assert row_meio["References"] == f"10.2000/normal; {prefix}10.2000/ref.2"
    assert row_meio["Year"] == "2023"
    assert row_meio["Cited by"] == "7"


# FR-06: Normalização de título e DOI e proteção de resumo iniciando com espaço ou quebra antes de '='
@pytest.mark.parametrize("leading_ws", [" ", "  ", "\n", "  \n", "\t", "\r\n"])
def test_fr06_csv_normalizacao_titulo_doi_e_resumo_com_espaco_ou_quebra_antes_de_formula(
    leading_ws: str,
) -> None:
    exporter = CSVExporter()
    work_normalizado = Work(
        title="Machine\n  learning   for\tschools",
        doi="https://doi.org/10.1/X\n",
        abstract=f"{leading_ws}=1+1",
    )
    work_titulo_formula = Work(
        title="  \n=1+1",
        doi="10.1000/clean\n",
        abstract="Resumo normal\ncom duas linhas",
    )

    content = exporter.render({"works": [work_normalizado, work_titulo_formula]})
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")), delimiter=",")
    rows = list(reader)
    assert len(rows) == 2

    assert rows[0]["Title"] == "Machine learning for schools"
    assert rows[0]["DOI"] == "10.1/X"
    assert rows[0]["Abstract"] == "'=1+1"

    assert rows[1]["Title"] == "'=1+1"
    assert rows[1]["DOI"] == "10.1000/clean"
    assert rows[1]["Abstract"] == "Resumo normal\ncom duas linhas"


# D-020: o CSV tem as três colunas novas no fim, e as colunas antigas continuam iguais
def test_d020_csv_tres_colunas_novas_no_fim_e_colunas_antigas_iguais() -> None:
    original_19_columns = (
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
    )
    new_3_columns = ("PubMed ID", "Europe PMC ID", "Citations Europe PMC")

    # Verifica que as colunas no CSV_COLUMNS mantêm as 19 originais idênticas e acrescentam 3 no fim
    assert CSV_COLUMNS[:19] == original_19_columns
    assert CSV_COLUMNS[19:22] == new_3_columns
    assert len(CSV_COLUMNS) == 26

    # Renderiza artigo com metadados de PubMed e Europe PMC
    work = Work(
        title="Genomic analysis of oncology markers",
        doi="10.1000/markers.2024",
        year=2024,
        venue="Biomedical Journal",
        authors=[Author(name="Watson, James")],
        source_ids={"pubmed": "38999999", "europe_pmc": "MED:38999999"},
        citations={"europe_pmc": 42},
    )

    exporter = CSVExporter()
    content = exporter.render({"works": [work]})
    reader = csv.reader(io.StringIO(content.lstrip("\ufeff")), delimiter=",")
    rows = list(reader)

    header = rows[0]
    assert tuple(header) == CSV_COLUMNS

    data = rows[1]
    # Colunas originais mantêm os valores correspondentes
    assert data[0] == "Watson, James"
    assert data[2] == "Genomic analysis of oncology markers"
    assert data[3] == "2024"
    assert data[5] == "10.1000/markers.2024"
    assert data[9] == "42"  # Cited by (máximo entre as fontes)
    assert data[13] == ""   # OpenAlex ID
    assert data[14] == ""   # Crossref DOI
    assert data[15] == ""   # Semantic Scholar ID

    # Três colunas do PubMed e Europe PMC (índices 19, 20, 21)
    assert data[19] == "38999999"      # PubMed ID
    assert data[20] == "MED:38999999"  # Europe PMC ID
    assert data[21] == "42"            # Citations Europe PMC


# D-023, FR-06: O CSV tem as quatro colunas novas no fim, e as 22 anteriores continuam iguais
def test_d023_csv_quatro_colunas_novas_no_fim_e_colunas_antigas_iguais() -> None:
    previous_22_columns = (
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
        "PubMed ID",
        "Europe PMC ID",
        "Citations Europe PMC",
    )
    paid_4_columns = (
        "Scopus EID",
        "Web of Science UID",
        "Citations Scopus",
        "Citations Web of Science",
    )

    # Verifica que as colunas anteriores permanecem idênticas e as 4 novas estão no fim
    assert CSV_COLUMNS[:22] == previous_22_columns
    assert CSV_COLUMNS[22:] == paid_4_columns
    assert len(CSV_COLUMNS) == 26

    # Renderiza artigo com metadados de Scopus e Web of Science
    work = Work(
        title="Quantum Error Correction",
        doi="10.1000/qec.2024",
        year=2024,
        venue="Quantum Science Review",
        authors=[Author(name="Shor, Peter")],
        source_ids={
            "scopus": "2-s2.0-85000000000",
            "web_of_science": "WOS:000123456700001",
        },
        citations={
            "scopus": 35,
            "web_of_science": 28,
        },
    )

    exporter = CSVExporter()
    content = exporter.render({"works": [work]})
    reader = csv.reader(io.StringIO(content.lstrip("\ufeff")), delimiter=",")
    rows = list(reader)

    header = rows[0]
    assert tuple(header) == CSV_COLUMNS

    data = rows[1]
    # Colunas anteriores preservam integridade
    assert data[0] == "Shor, Peter"
    assert data[2] == "Quantum Error Correction"
    assert data[3] == "2024"
    assert data[5] == "10.1000/qec.2024"
    assert data[9] == "35"  # Cited by (máximo entre as fontes)
    assert data[13] == ""   # OpenAlex ID
    assert data[19] == ""   # PubMed ID

    # Quatro colunas novas no fim (índices 22, 23, 24, 25)
    assert data[22] == "2-s2.0-85000000000"      # Scopus EID
    assert data[23] == "WOS:000123456700001"     # Web of Science UID
    assert data[24] == "35"                      # Citations Scopus
    assert data[25] == "28"                      # Citations Web of Science

