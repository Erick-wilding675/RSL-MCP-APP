"""Testes dos geradores de prompts para tipos de revisão acadêmica (D-035)."""

from __future__ import annotations

from rslapp.prompts import (
    render_plan_bibliometric_study,
    render_plan_integrative_review,
    render_plan_scoping_review,
    render_plan_systematic_review,
)


def test_d035_render_plan_scoping_review_vazio_e_com_pedido() -> None:
    # Caso vazio: orientações JBI e PCC
    res_vazio = render_plan_scoping_review("")
    assert "JBI" in res_vazio
    assert "PCC" in res_vazio
    assert "População" in res_vazio
    assert "Conceito" in res_vazio
    assert "Contexto" in res_vazio
    assert "PRISMA-ScR" in res_vazio
    assert "BDTD" in res_vazio

    # Caso com parâmetros
    res = render_plan_scoping_review(
        topic="Telemedicina na atenção primária",
        population="Idosos com doenças crônicas",
        concept="Adesão ao tratamento digital",
        context="Unidades Básicas de Saúde no Brasil",
    )
    assert "<pedido_pesquisador>" in res
    assert "Telemedicina na atenção primária" in res
    assert "Idosos com doenças crônicas" in res
    assert "Adesão ao tratamento digital" in res
    assert "Unidades Básicas de Saúde no Brasil" in res
    assert "PRISMA-ScR" in res
    assert "bdtd" in res.lower()


def test_d035_render_plan_integrative_review_vazio_e_com_pedido() -> None:
    # Caso vazio: diretrizes Whittemore & Knafl e 6 fases
    res_vazio = render_plan_integrative_review("")
    assert "Whittemore & Knafl" in res_vazio
    assert "Mendes, Silveira" in res_vazio
    assert "6 Fases" in res_vazio or "6 fases" in res_vazio

    # Caso com parâmetros
    res = render_plan_integrative_review(
        topic="Intervenções de enfermagem em saúde mental",
        guiding_question="Quais as estratégias de acolhimento em CAPS?",
        theoretical_framework="Teoria das Relações Interpessoais de Peplau",
    )
    assert "<pedido_pesquisador>" in res
    assert "Intervenções de enfermagem em saúde mental" in res
    assert "Quais as estratégias de acolhimento em CAPS?" in res
    assert "Teoria das Relações Interpessoais de Peplau" in res
    assert "1ª Fase" in res
    assert "6ª Fase" in res
    assert "bdtd" in res.lower()


def test_d035_render_plan_systematic_review_vazio_e_com_pedido() -> None:
    # Caso vazio: padrão Cochrane e PRISMA 2020
    res_vazio = render_plan_systematic_review("")
    assert "Cochrane" in res_vazio
    assert "PRISMA 2020" in res_vazio
    assert "PICO" in res_vazio
    assert "PROSPERO" in res_vazio

    # Caso com parâmetros PICO completos
    res = render_plan_systematic_review(
        topic="Eficácia de vacinas contra dengue",
        population="Crianças de 4 a 14 anos",
        intervention="Vacina TAK-003",
        comparison="Placebo ou controle",
        outcome="Taxa de hospitalização por dengue grave",
    )
    assert "<pedido_pesquisador>" in res
    assert "Eficácia de vacinas contra dengue" in res
    assert "Crianças de 4 a 14 anos" in res
    assert "Vacina TAK-003" in res
    assert "Placebo ou controle" in res
    assert "Taxa de hospitalização por dengue grave" in res
    assert "PROSPERO" in res
    assert "RoB" in res or "risco de viés" in res.lower()
    assert "bdtd" in res.lower()


def test_d035_render_plan_bibliometric_study_vazio_e_com_pedido() -> None:
    # Caso vazio: VOSviewer e leis bibliométricas
    res_vazio = render_plan_bibliometric_study("")
    assert "VOSviewer" in res_vazio
    assert "Bradford" in res_vazio
    assert "Lotka" in res_vazio
    assert "Zipf" in res_vazio

    # Caso com parâmetros
    res = render_plan_bibliometric_study(
        topic="Inteligência Artificial na Educação Superior",
        analysis_type="Coautoria e acoplamento bibliográfico",
    )
    assert "<pedido_pesquisador>" in res
    assert "Inteligência Artificial na Educação Superior" in res
    assert "Coautoria e acoplamento bibliográfico" in res
    assert "VOSviewer" in res
    assert "Bradford" in res
    assert "export_list" in res
