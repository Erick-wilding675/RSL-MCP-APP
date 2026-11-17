"""Testes dos importadores bibliográficos RIS, BibTeX, Scopus CSV e WoS (FR-23, D-033)."""

from __future__ import annotations

from pathlib import Path

import pytest

from rslapp.core.errors import RSLError
from rslapp.importers import (
    BibTeXImporter,
    RISImporter,
    ScopusCSVImporter,
    WebOfScienceImporter,
    auto_detect_format,
    import_to_store,
)
from rslapp.store import Store


# FR-23, D-033: Teste do importador de RIS com metadados e retratação
def test_fr23_d033_ris_importer() -> None:
    sample_ris = """
TY  - JOUR
TI  - Deep learning in medical imaging: A systematic review
AU  - Silva, Carlos
AU  - Santos, Maria
PY  - 2023
DO  - 10.1016/j.media.2023.102800
JF  - Medical Image Analysis
AB  - This systematic review evaluates deep learning algorithms.
KW  - Deep Learning
KW  - Medical Imaging
N1  - [AVISO] Artigo retratado pela editora em 2024
ER  - 

TY  - CONF
T1  - Graph Neural Networks for Citation Analysis
AU  - Alan Turing
PY  - 2021
DO  - https://doi.org/10.1145/3442381.3450000
JO  - Proceedings of the Web Conference
ER  - 
"""
    importer = RISImporter()
    works = importer.parse(sample_ris)
    assert len(works) == 2

    w1 = works[0]
    assert w1.title == "Deep learning in medical imaging: A systematic review"
    assert len(w1.authors) == 2
    assert w1.authors[0].name == "Carlos Silva"
    assert w1.authors[1].name == "Maria Santos"
    assert w1.year == 2023
    assert w1.doi == "10.1016/j.media.2023.102800"
    assert w1.venue == "Medical Image Analysis"
    assert "Deep Learning" in w1.keywords
    assert w1.is_retracted is True
    assert w1.retraction_details is not None

    w2 = works[1]
    assert w2.title == "Graph Neural Networks for Citation Analysis"
    assert w2.type == "conference-paper"
    assert w2.authors[0].name == "Alan Turing"
    assert w2.doi == "10.1145/3442381.3450000"
    assert w2.is_retracted is False


# FR-23, D-033: Teste do importador de BibTeX com LaTeX cleanup e autores
def test_fr23_d033_bibtex_importer() -> None:
    sample_bib = """
@article{vaswani2017attention,
  title = {Attention Is All You {Need}},
  author = {Vaswani, Ashish and Shazeer, Noam and Parmar, Niki},
  journal = {Advances in Neural Information Processing Systems},
  year = {2017},
  doi = {10.5555/3295222.3295349},
  keywords = {transformer, attention, deep learning},
  abstract = {The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.}
}

@inproceedings{smith2022retracted,
  title = {A Study on Fake Data in Science},
  author = {Smith, John},
  booktitle = {IEEE Symposium on Security},
  year = {2022},
  note = {Retracted publication due to author misconduct}
}
"""
    importer = BibTeXImporter()
    works = importer.parse(sample_bib)
    assert len(works) == 2

    w1 = works[0]
    assert w1.title == "Attention Is All You Need"
    assert len(w1.authors) == 3
    assert w1.authors[0].name == "Ashish Vaswani"
    assert w1.authors[1].name == "Noam Shazeer"
    assert w1.year == 2017
    assert w1.doi == "10.5555/3295222.3295349"
    assert "transformer" in w1.keywords
    assert w1.is_retracted is False

    w2 = works[1]
    assert w2.title == "A Study on Fake Data in Science"
    assert w2.type == "conference-paper"
    assert w2.is_retracted is True


# FR-23, D-033: Teste do importador de CSV do Scopus
def test_fr23_d033_scopus_csv_importer() -> None:
    sample_csv = (
        "Authors,Title,Year,Source title,DOI,Abstract,Author Keywords,Document Type,Cited by,EID\n"
        '"Oliveira, J.; Costa, F.","AI in Systematic Literature Reviews",2024,"Scientometrics","10.1007/s11192-024-0001-x","Abstract content here","AI; bibliometrics; RSL","Article",15,"2-s2.0-85199999999"\n'
        '"Menezes, R.","Retracted Analysis of Drug",2020,"Journal of Clinical Trials","10.1000/jct.2020.12","Trial abstract","Clinical","Retracted",0,"2-s2.0-85188888888"\n'
    )
    importer = ScopusCSVImporter()
    works = importer.parse(sample_csv)
    assert len(works) == 2

    w1 = works[0]
    assert w1.title == "AI in Systematic Literature Reviews"
    assert len(w1.authors) == 2
    assert w1.authors[0].name == "J. Oliveira"
    assert w1.authors[1].name == "F. Costa"
    assert w1.year == 2024
    assert w1.venue == "Scientometrics"
    assert w1.doi == "10.1007/s11192-024-0001-x"
    assert w1.citations == {"scopus": 15}
    assert w1.source_ids == {"scopus": "2-s2.0-85199999999"}
    assert w1.is_retracted is False

    w2 = works[1]
    assert w2.is_retracted is True
    assert w2.retraction_details["source"] == "scopus_document_type"


# FR-23, D-033: Teste do importador de Web of Science TSV e Tagged
def test_fr23_d033_wos_importer() -> None:
    sample_tsv = (
        "PT\tAU\tTI\tSO\tDT\tDE\tAB\tTC\tPY\tDI\tUT\n"
        "J\tAlmeida, B; Pereira, K\tBibliometric mapping with VOSviewer\tJournal of Informetrics\tArticle\tVOSviewer; Co-authorship\tWe map citation networks\t42\t2022\t10.1016/j.joi.2022.101234\tWOS:000888888800001\n"
    )
    importer = WebOfScienceImporter()
    works_tsv = importer.parse(sample_tsv)
    assert len(works_tsv) == 1
    w_tsv = works_tsv[0]
    assert w_tsv.title == "Bibliometric mapping with VOSviewer"
    assert len(w_tsv.authors) == 2
    assert w_tsv.authors[0].name == "B Almeida"
    assert w_tsv.year == 2022
    assert w_tsv.doi == "10.1016/j.joi.2022.101234"
    assert w_tsv.citations == {"web_of_science": 42}
    assert w_tsv.source_ids == {"web_of_science": "WOS:000888888800001"}

    sample_tagged = """
PT J
AU Ferreira, Lucas
TI Machine Learning for Evidence Synthesis
SO Research Synthesis Methods
DT Article
DE Systematic Reviews; ML
TC 8
PY 2023
DI 10.1002/jrsm.1600
UT WOS:000999999900002
ER
"""
    works_tagged = importer.parse(sample_tagged)
    assert len(works_tagged) == 1
    w_tagged = works_tagged[0]
    assert w_tagged.title == "Machine Learning for Evidence Synthesis"
    assert w_tagged.authors[0].name == "Lucas Ferreira"
    assert w_tagged.year == 2023
    assert w_tagged.doi == "10.1002/jrsm.1600"
    assert w_tagged.citations == {"web_of_science": 8}


# FR-23, D-033: Detecção automática de formatos
def test_fr23_d033_auto_detect_format() -> None:
    assert auto_detect_format("TY  - JOUR\nTI  - Test\nER  - ") == "ris"
    assert auto_detect_format("@article{key,\n  title = {Test}\n}") == "bibtex"
    assert auto_detect_format("Authors,Title,Year,Source title,DOI\nSmith,Test,2022,Nature,10.1000/1") == "scopus_csv"
    assert auto_detect_format("PT\tAU\tTI\tSO\nJ\tSmith\tTest\tNature") == "wos"
    assert auto_detect_format("PT J\nAU Smith\nTI Test\nUT WOS:0001\nER") == "wos"

    with pytest.raises(RSLError):
        auto_detect_format("Texto aleatório sem nenhum formato acadêmico conhecido.")


# FR-23, D-033: Importação com persistência no Store e registro no log.md
def test_fr23_d033_import_to_store_grava_lista_e_log(tmp_path: Path) -> None:
    store = Store(tmp_path)
    sample_ris = """
TY  - JOUR
TI  - Artificial Intelligence in Healthcare
AU  - Zhang, Wei
PY  - 2023
DO  - 10.1038/s41746-023-00001-x
ER  - 

TY  - JOUR
TI  - Artificial Intelligence in Healthcare
AU  - Zhang, Wei
PY  - 2023
DO  - 10.1038/s41746-023-00001-x
ER  - 
"""
    # Note que o sample contém 2 registros idênticos para testar a deduplicação interna
    res = import_to_store(
        store,
        sample_ris,
        format="auto",
        list_name="Revisão IA Saúde",
    )

    assert res["status"] == "complete"
    assert res["total"] == 1
    assert res["duplicates_removed"] == 1
    assert res["imported_format"] == "ris"
    assert res["list_id"].startswith("l-")
    assert res["search_id"].startswith("s-")

    # Verifica persistência no Store
    saved_list = store.get_list(res["list_id"])
    assert saved_list["total"] == 1
    assert saved_list["works"][0]["title"] == "Artificial Intelligence in Healthcare"
    assert saved_list["works"][0]["doi"] == "10.1038/s41746-023-00001-x"

    saved_search = store.get_search(res["search_id"])
    assert saved_search["kind"] == "import"
    assert saved_search["imported_format"] == "ris"

    # Verifica gravação no log.md
    log_content = store.read_log()
    assert res["search_id"] in log_content
    assert "importação" in log_content
    assert "Formato: ris" in log_content
