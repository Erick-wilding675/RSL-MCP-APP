"""Testes do modelo e lógica de triagem com rastro de autoria (FR-25, D-036)."""

from __future__ import annotations

import pytest

from rslapp.core.errors import RSLError
from rslapp.core.screening import (
    calculate_screening_summary,
    validate_decision_data,
)


def test_fr25_d036_validacao_decisao_sucesso() -> None:
    """Valida registro correto com campos completos e carimbo de data."""
    res = validate_decision_data(
        work_id="1",
        decision="included",
        stage="title_abstract",
        decided_by="human",
        notes="Artigo aderente ao objetivo",
        doi="10.1000/182",
    )
    assert res["work_id"] == "1"
    assert res["decision"] == "included"
    assert res["stage"] == "title_abstract"
    assert res["decided_by"] == "human"
    assert res["notes"] == "Artigo aderente ao objetivo"
    assert res["doi"] == "10.1000/182"
    assert "decided_at" in res


def test_fr25_d036_validacao_exclusao_com_motivo_padrao() -> None:
    """Se excluir sem motivo, preenche motivo padrão."""
    res = validate_decision_data(
        work_id=2,
        decision="excluded",
        decided_by="ai:claude-3-5-sonnet",
    )
    assert res["work_id"] == "2"
    assert res["decision"] == "excluded"
    assert res["reason"] == "Fora do tema / escopo"
    assert res["decided_by"] == "ai:claude-3-5-sonnet"


def test_fr25_d036_validacao_recusa_entradas_invalidas() -> None:
    """Valida recusa de work_id vazio, decisão desconhecida e estágio inválido."""
    with pytest.raises(RSLError) as exc_id:
        validate_decision_data(work_id="", decision="included")
    assert exc_id.value.code == "invalid_input"

    with pytest.raises(RSLError) as exc_dec:
        validate_decision_data(work_id="1", decision="maybe_later")
    assert exc_dec.value.code == "invalid_input"

    with pytest.raises(RSLError) as exc_stg:
        validate_decision_data(work_id="1", decision="maybe", stage="invalid_stage")
    assert exc_stg.value.code == "invalid_input"


def test_fr25_d036_calculo_resumo_triagem() -> None:
    """Valida cálculo de totais, percentuais, motivos e distribuição de autoria."""
    decisions = {
        "1": {
            "work_id": "1",
            "decision": "included",
            "stage": "title_abstract",
            "decided_by": "human",
            "reason": None,
        },
        "2": {
            "work_id": "2",
            "decision": "excluded",
            "stage": "title_abstract",
            "decided_by": "ai:gpt-4o",
            "reason": "População não elegível",
        },
        "3": {
            "work_id": "3",
            "decision": "excluded",
            "stage": "title_abstract",
            "decided_by": "human",
            "reason": "População não elegível",
        },
        "4": {
            "work_id": "4",
            "decision": "maybe",
            "stage": "full_text",
            "decided_by": "human",
            "reason": None,
        },
    }

    summary = calculate_screening_summary(total_works=10, decisions=decisions)

    assert summary["total_works"] == 10
    assert summary["screened"] == 4
    assert summary["pending"] == 6
    assert summary["included"] == 1
    assert summary["excluded"] == 2
    assert summary["maybe"] == 1
    assert summary["progress_percent"] == 40.0

    # Motivos
    assert summary["reasons"] == {"População não elegível": 2}

    # Autores
    assert summary["by_author"]["human"] == 3
    assert summary["by_author"]["ai"] == 1

    # Estágios
    assert summary["by_stage"]["title_abstract"]["included"] == 1
    assert summary["by_stage"]["title_abstract"]["excluded"] == 2
    assert summary["by_stage"]["full_text"]["maybe"] == 1


def test_fr25_d036_resumo_lista_vazia() -> None:
    """Lista sem trabalhos ou sem decisões não quebra nem divide por zero."""
    summary = calculate_screening_summary(total_works=0, decisions={})
    assert summary["total_works"] == 0
    assert summary["screened"] == 0
    assert summary["pending"] == 0
    assert summary["progress_percent"] == 0.0
