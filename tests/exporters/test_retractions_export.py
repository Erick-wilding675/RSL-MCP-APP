"""Testes de exportação para artigos retratados (FR-22, D-032)."""

from __future__ import annotations

import csv
import io

from rslapp.core.models import Author, Work
from rslapp.exporters.bibtex import BibTeXExporter
from rslapp.exporters.csv import CSVExporter
from rslapp.exporters.ris import RISExporter


# FR-22, D-032: Exportador RIS inclui tag N1 de aviso em artigos retratados
def test_fr22_ris_export_retraction_notice() -> None:
    work_retracted = Work(
        title="Hydroxychloroquine in COVID-19",
        doi="10.1016/s0140-6736(20)31180-6",
        year=2020,
        venue="The Lancet",
        authors=[Author(name="Mehra, Mandeep R.")],
        is_retracted=True,
        retraction_details={"source": "retraction-watch", "type": "retraction"},
    )
    work_normal = Work(
        title="Normal Valid Study",
        doi="10.1000/valid.study",
        year=2021,
        authors=[Author(name="Smith, John")],
        is_retracted=False,
    )

    exporter = RISExporter()
    content = exporter.render({"works": [work_retracted, work_normal]})

    assert "N1  - [AVISO] Artigo retratado ou com expressao de preocupacao oficial (Fonte: retraction-watch)" in content
    # O segundo artigo não deve conter aviso de retratação
    records = content.split("ER  - \r\n")
    assert "[AVISO]" in records[0]
    assert "[AVISO]" not in records[1]


# FR-22, D-032: Exportador BibTeX inclui aviso em note
def test_fr22_bibtex_export_retraction_notice() -> None:
    work_retracted = Work(
        title="Fabricated Superconductivity at Room Temperature",
        doi="10.1038/s41586-020-2801-z",
        year=2020,
        venue="Nature",
        authors=[Author(name="Dias, Ranga P.")],
        source_ids={"crossref": "10.1038/s41586-020-2801-z"},
        is_retracted=True,
        retraction_details={"source": "retraction-watch", "type": "retraction"},
    )

    exporter = BibTeXExporter()
    content = exporter.render({"works": [work_retracted]})

    assert "AVISO: Artigo retratado ou com expressao de preocupacao oficial (Fonte: retraction-watch)" in content
    assert "note = {" in content


# FR-22, D-032: Exportador CSV Scopus marca Document Type como Retracted
def test_fr22_csv_export_retraction_doc_type() -> None:
    work_retracted = Work(
        title="Retracted Chemistry Paper",
        doi="10.1000/retracted.chem",
        year=2022,
        type="article",
        venue="Journal of Chemistry",
        authors=[Author(name="Doe, Jane")],
        is_retracted=True,
    )

    exporter = CSVExporter()
    content = exporter.render({"works": [work_retracted]})

    reader = csv.reader(io.StringIO(content.lstrip("\ufeff")), delimiter=",")
    rows = list(reader)
    header = rows[0]
    data = rows[1]

    doc_type_idx = header.index("Document Type")
    assert data[doc_type_idx] == "Retracted (article)"
