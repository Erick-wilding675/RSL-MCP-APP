"""Testes unitários da declaração ética de uso de inteligência artificial (FR-27, D-038)."""

from __future__ import annotations

from rslapp.core.ai_disclosure import render_ai_disclosure


# FR-27, D-038: Geração da declaração em Português (SciELO / ABNT) com assistência de IA
def test_ai_disclosure_pt_with_ai_screening_fr27_d038() -> None:
    screening_summary = {
        "screened": 100,
        "included": 15,
        "excluded": 85,
        "by_author": {"human": 70, "ai": 30},
    }
    text = render_ai_disclosure(
        list_id="l-0042",
        search_query="revisões sistemáticas com IA",
        total_works=120,
        screening_summary=screening_summary,
        lang="pt",
    )

    assert "Declaração de Uso de Inteligência Artificial" in text
    assert "Committee on Publication Ethics (COPE)" in text
    assert "SciELO Brasil" in text
    assert "l-0042" in text
    assert "120 registros deduplicados" in text
    assert "30 trabalhos contaram com pré-classificação assistida por inteligência artificial" in text
    assert "70 decisões foram registradas diretamente por pesquisadores humanos" in text
    assert "Supervisão e Responsabilidade Humana" in text
    assert "Nenhuma tecnologia de inteligência artificial figura como autora ou coautora" in text


# FR-27, D-038: Geração da declaração em Português quando a triagem foi 100% humana
def test_ai_disclosure_pt_all_human_screening_fr27_d038() -> None:
    screening_summary = {
        "screened": 50,
        "included": 10,
        "excluded": 40,
        "by_author": {"human": 50, "ai": 0},
    }
    text = render_ai_disclosure(
        list_id="l-0010",
        search_query="saúde pública e epidemiologia",
        total_works=50,
        screening_summary=screening_summary,
        lang="pt",
    )

    assert "Todas as decisões de triagem foram executadas e verificadas integralmente por pesquisadores humanos" in text


# FR-27, D-038: Geração da declaração em Inglês (COPE / ICMJE)
def test_ai_disclosure_en_fr27_d038() -> None:
    screening_summary = {
        "screened": 200,
        "included": 25,
        "excluded": 175,
        "by_author": {"human": 150, "ai": 50},
    }
    text = render_ai_disclosure(
        list_id="l-0099",
        search_query="deep learning in bioinformatics",
        total_works=250,
        screening_summary=screening_summary,
        lang="en",
    )

    assert "Statement on Artificial Intelligence and Methodological Transparency" in text
    assert "Committee on Publication Ethics (COPE)" in text
    assert "International Committee of Medical Journal Editors (ICMJE)" in text
    assert "Search List ID: `l-0099`" in text
    assert "50 records received assistive pre-classification from AI models" in text
    assert "150 decisions were registered directly by human researchers" in text
    assert "Human Authorship and Scientific Accountability" in text
