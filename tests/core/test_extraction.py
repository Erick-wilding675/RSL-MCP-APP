"""Testes da tabela de extração de dados para metanálise, R metafor e RevMan (FR-35, D-046)."""

from __future__ import annotations

from pathlib import Path

import pytest

from rslapp.core.extraction import (
    ExtractionData,
    StudyOutcome,
    calculate_mean_difference,
    calculate_odds_ratio,
    calculate_risk_ratio,
    calculate_smd,
    export_metafor_csv,
    export_revman_csv,
)
from rslapp.store import Store


# FR-35, D-046: Cálculo de Odds Ratio paramétrico com IC 95%
def test_fr35_calculate_odds_ratio() -> None:
    # Caso 1: Ensaio clínico clássico 2x2
    # Intervenção: 15 eventos em 100 pacientes
    # Controle: 30 eventos em 100 pacientes
    or_val, ci_l, ci_u = calculate_odds_ratio(events_i=15, n_i=100, events_c=30, n_c=100)
    assert or_val == pytest.approx(0.4118, rel=1e-2)
    assert ci_l < or_val < ci_u
    assert ci_l == pytest.approx(0.2072, rel=1e-2)
    assert ci_u == pytest.approx(0.8183, rel=1e-2)

    # Caso 2: Célula zero ativa correção de Haldane (0.5) sem divisão por zero
    or_zero, ci_l_z, ci_u_z = calculate_odds_ratio(events_i=0, n_i=50, events_c=10, n_c=50)
    assert or_zero > 0
    assert ci_l_z < or_zero < ci_u_z


# FR-35, D-046: Cálculo de Risco Relativo com IC 95%
def test_fr35_calculate_risk_ratio() -> None:
    # Intervenção: 20 eventos em 100 (p_i = 0.20)
    # Controle: 40 eventos em 100 (p_c = 0.40) -> RR = 0.50
    rr_val, ci_l, ci_u = calculate_risk_ratio(events_i=20, n_i=100, events_c=40, n_c=100)
    assert rr_val == pytest.approx(0.50, rel=1e-2)
    assert ci_l < rr_val < ci_u
    assert ci_l == pytest.approx(0.317, rel=1e-2)
    assert ci_u == pytest.approx(0.788, rel=1e-2)


# FR-35, D-046: Cálculo de Diferença de Médias (MD) e SMD / Hedges' g
def test_fr35_calculate_md_and_smd() -> None:
    # Intervenção: média 110 mmHg, DP 10, N 50
    # Controle: média 120 mmHg, DP 12, N 50
    md, ci_l, ci_u = calculate_mean_difference(mean_i=110.0, sd_i=10.0, n_i=50, mean_c=120.0, sd_c=12.0, n_c=50)
    assert md == pytest.approx(-10.0, rel=1e-2)
    assert ci_l < md < ci_u
    assert ci_l == pytest.approx(-14.33, rel=1e-2)
    assert ci_u == pytest.approx(-5.67, rel=1e-2)

    # SMD (Hedges' g)
    g, g_l, g_u = calculate_smd(mean_i=110.0, sd_i=10.0, n_i=50, mean_c=120.0, sd_c=12.0, n_c=50)
    assert g < 0
    assert g == pytest.approx(-0.90, rel=1e-2)
    assert g_l < g < g_u


# FR-35, D-046: Exportação de CSV para R metafor e RevMan
def test_fr35_export_metafor_and_revman() -> None:
    ext1 = ExtractionData(
        work_id="w-01",
        study_design="RCT",
        sample_size_total=200,
        outcomes=[
            StudyOutcome(
                name="Mortalidade",
                outcome_type="dichotomous",
                n_intervention=100,
                events_intervention=10,
                n_control=100,
                events_control=25,
                effect_measure="OR",
                effect_estimate=0.33,
                ci_lower=0.15,
                ci_upper=0.74,
            ),
            StudyOutcome(
                name="Pressão Arterial",
                outcome_type="continuous",
                n_intervention=100,
                mean_intervention=120.0,
                sd_intervention=15.0,
                n_control=100,
                mean_control=130.0,
                sd_control=14.0,
                effect_measure="MD",
                effect_estimate=-10.0,
                ci_lower=-14.0,
                ci_upper=-6.0,
            ),
        ],
    )

    info_map = {"w-01": {"first_author": "Silva", "year": 2023}}

    metafor_csv = export_metafor_csv([ext1], info_map)
    assert "study_id,author_year,design,outcome,outcome_type" in metafor_csv
    assert "w-01,Silva (2023),RCT,Mortalidade,dichotomous" in metafor_csv
    assert "100,10" in metafor_csv

    revman_csv = export_revman_csv([ext1], info_map)
    assert "Study ID,Intervention Events,Intervention Total" in revman_csv
    assert "Silva 2023,10,100,25,100" in revman_csv


# FR-35, D-046: Persistência no Store
def test_fr35_store_extraction(tmp_path: Path) -> None:
    store = Store(data_dir=tmp_path)
    ext = ExtractionData(
        work_id="work-100",
        study_design="Cohort",
        sample_size_total=500,
        country="Brasil",
        outcomes=[StudyOutcome(name="Incidência de doença", outcome_type="dichotomous", events_intervention=50, n_intervention=250)],
    )

    saved = store.save_extraction("l-test", ext.to_dict())
    assert saved["work_id"] == "work-100"
    assert saved["country"] == "Brasil"

    loaded = store.get_extraction("l-test", "work-100")
    assert loaded is not None
    assert loaded["study_design"] == "Cohort"
    assert len(loaded["outcomes"]) == 1

    all_exts = store.list_extractions("l-test")
    assert len(all_exts) == 1
    assert all_exts[0]["work_id"] == "work-100"

    assert store.delete_extraction("l-test", "work-100") is True
    assert store.get_extraction("l-test", "work-100") is None
