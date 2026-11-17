"""Testes do modelo e conectores para detecção e unificação de retratações (FR-22, D-032)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from rslapp.core.dedup import deduplicate_works_with_merge
from rslapp.core.models import Author, Work
from rslapp.sources import crossref, europe_pmc, openalex, pubmed


# FR-22, D-032: Serialização, desserialização e retrocompatibilidade de Work com retratações
def test_fr22_work_model_retraction_fields_and_backwards_compat() -> None:
    # 1. Artigo com retratação explícita
    w = Work(
        title="Estudo Retratado",
        doi="10.1000/retracted.2020",
        year=2020,
        is_retracted=True,
        retraction_details={"source": "openalex", "label": "Retracted"},
    )
    data = w.to_dict()
    assert data["is_retracted"] is True
    assert data["retraction_details"] == {"source": "openalex", "label": "Retracted"}

    w_restored = Work.from_dict(data)
    assert w_restored.is_retracted is True
    assert w_restored.retraction_details == {"source": "openalex", "label": "Retracted"}

    # 2. Retrocompatibilidade: dicionário antigo sem os campos de retratação
    old_data = {
        "title": "Artigo Antigo",
        "doi": "10.1000/antigo.2015",
        "year": 2015,
    }
    w_old = Work.from_dict(old_data)
    assert w_old.is_retracted is False
    assert w_old.retraction_details is None


# FR-22, D-032: Parser do OpenAlex extrai is_retracted nativo
def test_fr22_openalex_parse_retraction() -> None:
    raw_retracted = {
        "id": "https://openalex.org/W99999999",
        "display_name": "Hydrogel Synthesis and Characterization",
        "doi": "https://doi.org/10.1000/hydrogel.retracted",
        "publication_year": 2021,
        "is_retracted": True,
    }
    work = openalex._parse_work(raw_retracted)
    assert work is not None
    assert work.is_retracted is True
    assert work.retraction_details is not None
    assert work.retraction_details["source"] == "openalex"

    # Artigo não retratado
    raw_normal = {
        "id": "https://openalex.org/W11111111",
        "display_name": "Normal Paper",
        "doi": "https://doi.org/10.1000/normal",
        "publication_year": 2021,
        "is_retracted": False,
    }
    work_normal = openalex._parse_work(raw_normal)
    assert work_normal is not None
    assert work_normal.is_retracted is False
    assert work_normal.retraction_details is None


# FR-22, D-032: Parser da Crossref extrai updated-by com tipo retraction do Retraction Watch
def test_fr22_crossref_parse_retraction() -> None:
    raw_retracted = {
        "title": ["Fabricated Nanoparticle Drug Delivery"],
        "DOI": "10.1021/am300292v",
        "issued": {"date-parts": [[2019, 5, 10]]},
        "updated-by": [
            {
                "DOI": "10.1021/acsami.9b11759",
                "type": "retraction",
                "label": "Retraction",
                "source": "retraction-watch",
                "record-id": "20946",
            }
        ],
    }
    work = crossref._parse_work(raw_retracted)
    assert work is not None
    assert work.is_retracted is True
    assert work.retraction_details == {
        "type": "retraction",
        "label": "Retraction",
        "source": "retraction-watch",
        "doi": "10.1021/acsami.9b11759",
    }

    # Artigo com errata/correção normal (não retratação)
    raw_correction = {
        "title": ["Paper with simple erratum"],
        "DOI": "10.1000/erratum.paper",
        "issued": {"date-parts": [[2020, 1, 1]]},
        "updated-by": [
            {
                "type": "correction",
                "label": "Correction",
                "source": "publisher",
            }
        ],
    }
    work_corr = crossref._parse_work(raw_correction)
    assert work_corr is not None
    assert work_corr.is_retracted is False
    assert work_corr.retraction_details is None


# FR-22, D-032: Parser do Europe PMC extrai isRetracted
def test_fr22_europe_pmc_parse_retraction() -> None:
    raw = {
        "title": "Clinical Study on Hydroxychloroquine",
        "doi": "10.1016/s0140-6736(20)31180-6",
        "pubYear": "2020",
        "isRetracted": "Y",
    }
    work = europe_pmc._parse_work(raw)
    assert work is not None
    assert work.is_retracted is True
    assert work.retraction_details == {"source": "europe_pmc", "label": "Retracted"}


# FR-22, D-032: Parser do PubMed identifica PublicationType de retratação
def test_fr22_pubmed_parse_retraction() -> None:
    xml_str = """
    <PubmedArticle>
      <MedlineCitation>
        <PMID>12345678</PMID>
        <Article>
          <ArticleTitle>Retracted Clinical Trial Results</ArticleTitle>
          <PublicationTypeList>
            <PublicationType>Journal Article</PublicationType>
            <PublicationType>Retracted Publication</PublicationType>
          </PublicationTypeList>
        </Article>
      </MedlineCitation>
    </PubmedArticle>
    """
    elem = ET.fromstring(xml_str)
    work = pubmed._parse_pubmed_article(elem)
    assert work is not None
    assert work.is_retracted is True
    assert work.retraction_details is not None
    assert work.retraction_details["source"] == "pubmed"


# FR-22, D-032: Deduplicação preserva is_retracted=True mesmo que uma das fontes não o sinalize
def test_fr22_dedup_preserves_retraction_flag() -> None:
    # Obra vinda do Crossref (com retratação detectada)
    work_crossref = Work(
        title="Attention is All You Need and Transformers",
        doi="10.1000/transformer-fake-retraction",
        year=2017,
        source_ids={"crossref": "10.1000/transformer-fake-retraction"},
        is_retracted=True,
        retraction_details={"source": "retraction-watch", "type": "retraction"},
    )

    # Mesma obra vinda de outra base sem flag de retratação
    work_other = Work(
        title="Attention is All You Need and Transformers",
        doi="10.1000/transformer-fake-retraction",
        year=2017,
        source_ids={"semantic_scholar": "S123"},
        authors=[Author(name="Ashish Vaswani")],
        is_retracted=False,
    )

    dedup_res = deduplicate_works_with_merge([work_other, work_crossref])
    assert len(dedup_res.works) == 1
    merged = dedup_res.works[0]
    assert merged.is_retracted is True
    assert merged.retraction_details is not None
    assert merged.retraction_details["source"] == "retraction-watch"
    assert "crossref" in merged.source_ids
    assert "semantic_scholar" in merged.source_ids
