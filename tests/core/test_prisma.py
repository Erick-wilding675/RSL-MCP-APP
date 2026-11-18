"""Testes unitários do cálculo e geração do PRISMA 2020 e PRISMA-S (FR-26, D-037)."""

from __future__ import annotations

from typing import Any

from rslapp.core.prisma import (
    calculate_prisma_flow,
    render_prisma_markdown,
    render_prisma_svg,
)


def _sample_list_and_search() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    search_record = {
        "id": "s-0001",
        "request_summary": "inteligência artificial em revisões sistemáticas",
        "created_at": "2026-11-18T10:00:00Z",
        "sources": [
            {"name": "openalex", "fetched": 150, "found": 150},
            {"name": "crossref", "fetched": 100, "found": 100},
            {"name": "bdtd", "fetched": 50, "found": 50},
        ],
    }
    # 300 brutos, 250 únicos -> 50 duplicatas
    works = [{"doi": f"10.1234/{i}", "title": f"Artigo {i}", "source": "openalex"} for i in range(250)]
    list_data = {
        "id": "l-0001",
        "search_id": "s-0001",
        "total": 250,
        "works": works,
        "created_at": "2026-11-18T10:05:00Z",
    }
    screening_summary = {
        "total_works": 250,
        "screened": 250,
        "pending": 0,
        "included": 40,
        "excluded": 210,
        "maybe": 0,
        "progress_percent": 100.0,
        "reasons": {
            "Fora do tema / escopo": 180,
            "População não elegível": 25,
            "Texto completo não recuperado": 5,
        },
        "by_author": {"human": 200, "ai": 50},
        "by_stage": {
            "title_abstract": {"included": 45, "excluded": 205, "maybe": 0},
            "full_text": {"included": 40, "excluded": 5, "maybe": 0},
        },
    }
    return list_data, screening_summary, search_record


# FR-26, D-037: Validação do cálculo quantitativo dos estágios do PRISMA 2020
def test_prisma_flow_calculation_fr26_d037() -> None:
    list_data, screening_summary, search_record = _sample_list_and_search()
    flow = calculate_prisma_flow(list_data, screening_summary, search_record)

    ident = flow["identification"]
    assert ident["records_databases"] == 300
    assert ident["records_total"] == 300
    assert ident["duplicates_removed"] == 50
    assert ident["records_screened_input"] == 250
    assert ident["database_counts"]["openalex"] == 150
    assert ident["database_counts"]["crossref"] == 100
    assert ident["database_counts"]["bdtd"] == 50

    screen = flow["screening"]
    assert screen["records_screened"] == 250
    assert screen["records_excluded"] == 205
    assert screen["reports_sought"] == 45

    elig = flow["eligibility"]
    assert elig["reports_sought"] == 45
    assert elig["reports_not_retrieved"] == 5
    assert elig["reports_assessed"] == 40
    assert elig["reports_excluded"] == 5

    inc = flow["included"]
    assert inc["studies_included"] == 40
    assert inc["reports_included"] == 40


# FR-26, D-037: Dedução correta quando search_record não é fornecido
def test_prisma_flow_without_search_record_fr26_d037() -> None:
    list_data, screening_summary, _ = _sample_list_and_search()
    flow = calculate_prisma_flow(list_data, screening_summary, search_record=None)

    ident = flow["identification"]
    assert ident["records_databases"] == 250
    assert ident["duplicates_removed"] == 0
    assert ident["records_screened_input"] == 250
    assert flow["included"]["studies_included"] == 40


# FR-26, D-037: Renderização de SVG vetorial válido e bem formatado
def test_prisma_svg_rendering_fr26_d037() -> None:
    list_data, screening_summary, search_record = _sample_list_and_search()
    flow = calculate_prisma_flow(list_data, screening_summary, search_record)
    svg = render_prisma_svg(flow)

    assert "<svg" in svg
    assert "</svg>" in svg
    assert "IDENTIFICAÇÃO" in svg
    assert "TRIAGEM" in svg
    assert "ELEGIBILIDADE" in svg
    assert "INCLUSÃO" in svg
    assert "n = 300" in svg
    assert "n = 50" in svg  # duplicatas
    assert "n = 40" in svg  # incluídos
    assert "marker id=\"arrow\"" in svg


# FR-26, D-037: Renderização do relatório Markdown com checklist PRISMA-S
def test_prisma_markdown_rendering_fr26_d037() -> None:
    list_data, screening_summary, search_record = _sample_list_and_search()
    flow = calculate_prisma_flow(list_data, screening_summary, search_record)
    md = render_prisma_markdown(flow)

    assert "# Relatório de Fluxo PRISMA 2020 e Checklist PRISMA-S" in md
    assert "Checklist PRISMA-S" in md
    assert "Total bruto de registros:** 300" in md
    assert "Registros duplicados removidos:** 50" in md
    assert "Estudos incluídos na revisão:** 40" in md
    assert "Openalex" in md
