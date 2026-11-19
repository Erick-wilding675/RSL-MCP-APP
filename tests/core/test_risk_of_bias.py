"""Testes do módulo de avaliação sistemática de risco de viés: RoB 2, ROBINS-I e JBI (FR-36, D-047)."""

from __future__ import annotations

from pathlib import Path

from rslapp.core.risk_of_bias import (
    DomainAssessment,
    RiskOfBiasAssessment,
    compute_overall_rob2,
    compute_overall_robins_i,
    create_empty_assessment,
    generate_traffic_light_matrix,
)
from rslapp.store import Store


# FR-36, D-047: Algoritmo de risco geral RoB 2 (Cochrane)
def test_fr36_rob2_overall_algorithm() -> None:
    # 1. Todos low -> Geral low
    domains_all_low = [
        DomainAssessment("D1", "Randomização", "low"),
        DomainAssessment("D2", "Desvios", "low"),
        DomainAssessment("D3", "Dados faltantes", "low"),
        DomainAssessment("D4", "Mensuração", "low"),
        DomainAssessment("D5", "Relato", "low"),
    ]
    assert compute_overall_rob2(domains_all_low) == "low"

    # 2. Um some_concerns, nenhum high -> Geral some_concerns
    domains_some = [
        DomainAssessment("D1", "Randomização", "low"),
        DomainAssessment("D2", "Desvios", "some_concerns"),
        DomainAssessment("D3", "Dados faltantes", "low"),
        DomainAssessment("D4", "Mensuração", "low"),
        DomainAssessment("D5", "Relato", "low"),
    ]
    assert compute_overall_rob2(domains_some) == "some_concerns"

    # 3. Pelo menos um high -> Geral high
    domains_high = [
        DomainAssessment("D1", "Randomização", "some_concerns"),
        DomainAssessment("D2", "Desvios", "low"),
        DomainAssessment("D3", "Dados faltantes", "high"),
        DomainAssessment("D4", "Mensuração", "low"),
        DomainAssessment("D5", "Relato", "low"),
    ]
    assert compute_overall_rob2(domains_high) == "high"


# FR-36, D-047: Algoritmo de risco geral ROBINS-I (Cochrane)
def test_fr36_robins_i_overall_algorithm() -> None:
    domains_mod = [
        DomainAssessment("D1", "Confusão", "low"),
        DomainAssessment("D2", "Seleção", "moderate"),
    ]
    assert compute_overall_robins_i(domains_mod) == "moderate"

    domains_ser = [
        DomainAssessment("D1", "Confusão", "serious"),
        DomainAssessment("D2", "Seleção", "moderate"),
    ]
    assert compute_overall_robins_i(domains_ser) == "serious"

    domains_crit = [
        DomainAssessment("D1", "Confusão", "serious"),
        DomainAssessment("D2", "Seleção", "critical"),
    ]
    assert compute_overall_robins_i(domains_crit) == "critical"


# FR-36, D-047: Criação com domínios padrão e matriz de semáforo
def test_fr36_empty_assessment_and_matrix() -> None:
    ass1 = create_empty_assessment("w1", "rob2")
    assert ass1.tool == "rob2"
    assert len(ass1.domains) == 5
    assert ass1.overall_judgment == "low"

    ass2 = create_empty_assessment("w2", "rob2")
    ass2.domains[0].judgment = "high"
    ass2.overall_judgment = compute_overall_rob2(ass2.domains)

    matrix = generate_traffic_light_matrix([ass1, ass2], {"w1": {"first_author": "Almeida", "year": 2021}})
    assert matrix["tool"] == "rob2"
    assert len(matrix["headers"]) == 5
    assert len(matrix["rows"]) == 2
    assert matrix["rows"][0]["study_label"] == "Almeida (2021)"
    assert matrix["rows"][0]["overall"] == "low"
    assert matrix["rows"][1]["overall"] == "high"


# FR-36, D-047: Persistência no Store
def test_fr36_store_risk_of_bias(tmp_path: Path) -> None:
    store = Store(data_dir=tmp_path)
    ass = RiskOfBiasAssessment(
        work_id="work-200",
        tool="rob2",
        domains=[DomainAssessment("D1", "Randomização", "some_concerns", rationale="Falta cegamento")],
        overall_judgment="some_concerns",
    )

    saved = store.save_risk_of_bias("l-test", ass.to_dict())
    assert saved["work_id"] == "work-200"
    assert saved["overall_judgment"] == "some_concerns"

    loaded = store.get_risk_of_bias("l-test", "work-200")
    assert loaded is not None
    assert loaded["tool"] == "rob2"
    assert len(loaded["domains"]) == 1
    assert loaded["domains"][0]["rationale"] == "Falta cegamento"

    all_ass = store.list_risk_of_bias("l-test")
    assert len(all_ass) == 1

    assert store.delete_risk_of_bias("l-test", "work-200") is True
    assert store.get_risk_of_bias("l-test", "work-200") is None
