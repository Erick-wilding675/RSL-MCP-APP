"""Testes do cálculo de Kappa de Cohen e integração expandida ao pacote de reprodutibilidade (FR-37, D-048)."""

from __future__ import annotations

import zipfile
from pathlib import Path

from rslapp.core.reproducibility import build_reproducibility_package
from rslapp.core.screening import calculate_cohen_kappa
from rslapp.store import Store


# FR-37, D-048: Teste matemático rigoroso de cálculo do Kappa de Cohen
def test_fr37_calculate_cohen_kappa() -> None:
    # Caso 1: Concordância perfeita entre dois avaliadores (Po = 1, Kappa = 1.0)
    rev_a = {"w1": "included", "w2": "excluded", "w3": "maybe", "w4": "excluded"}
    rev_b = {"w1": "included", "w2": "excluded", "w3": "maybe", "w4": "excluded"}

    res = calculate_cohen_kappa(rev_a, rev_b)
    assert res["n_common"] == 4
    assert res["observed_agreement"] == 1.0
    assert res["kappa"] == 1.0
    assert "Quase perfeita" in res["interpretation"]
    assert len(res["divergences"]) == 0

    # Caso 2: Presença de divergências conhecidas
    # w1: inc/inc, w2: inc/exc, w3: exc/exc, w4: exc/inc
    rev_1 = {"w1": "included", "w2": "included", "w3": "excluded", "w4": "excluded"}
    rev_2 = {"w1": "included", "w2": "excluded", "w3": "excluded", "w4": "included"}

    res_div = calculate_cohen_kappa(rev_1, rev_2)
    assert res_div["n_common"] == 4
    assert res_div["agreements"] == 2
    assert res_div["observed_agreement"] == 0.50
    assert len(res_div["divergences"]) == 2
    divergent_ids = {d["work_id"] for d in res_div["divergences"]}
    assert divergent_ids == {"w2", "w4"}

    # Caso 3: Sem artigos comuns
    res_empty = calculate_cohen_kappa({"a": "included"}, {"b": "excluded"})
    assert res_empty["n_common"] == 0
    assert res_empty["kappa"] == 0.0


# FR-37, D-048: Expansão do Pacote de Reprodutibilidade com extração, risco de viés e manifesto OA
def test_fr37_reproducibility_package_expansion(tmp_path: Path) -> None:
    store = Store(data_dir=tmp_path)
    works = [
        {
            "id": "w1",
            "title": "Estudo de Ensaio Clínico",
            "doi": "10.1000/1",
            "year": 2024,
            "authors": [{"name": "Santos, M."}],
            "venue": "Revista Médica",
            "type": "article",
            "abstract": "Resumo do estudo",
            "keywords": ["saude"],
            "references": [],
            "source_ids": {},
        }
    ]
    search_data = {
        "kind": "terms",
        "request_summary": "ensaio clinico",
        "sources": [{"name": "openalex", "status": "ok", "fetched": 1, "found": 1}],
    }
    list_data = {
        "query": "ensaio clinico",
        "status": "complete",
        "total": 1,
        "works": works,
    }
    _s_rec, l_rec = store.record_search(search_data, list_data)
    list_id = l_rec["id"]

    # Salva dados de extração
    store.save_extraction(list_id, {
        "work_id": "w1",
        "study_design": "RCT",
        "outcomes": [{"name": "Desfecho Primário", "outcome_type": "dichotomous", "events_intervention": 10, "n_intervention": 100}],
    })

    # Salva avaliação de risco de viés
    store.save_risk_of_bias(list_id, {
        "work_id": "w1",
        "tool": "rob2",
        "domains": [{"domain_id": "D1", "domain_name": "Randomização", "judgment": "low"}],
        "overall_judgment": "low",
    })

    # Salva manifesto de texto completo
    store.save_fulltext_record(list_id, {
        "work_id": "w1",
        "status": "downloaded",
        "oa_url": "https://exemplo.org/pdf",
        "pdf_path": "/tmp/w1.pdf",
    })

    export_dir = tmp_path / "exports"
    pkg_info = build_reproducibility_package(list_id, store, export_dir=export_dir)
    assert pkg_info["path"] is not None
    zip_path = Path(pkg_info["path"])
    assert zip_path.exists()

    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        assert "extraction.csv" in namelist
        assert "extraction.json" in namelist
        assert "risk_of_bias.json" in namelist
        assert "fulltext_manifest.json" in namelist
        assert "checksums.sha256" in namelist

        checksums_txt = zf.read("checksums.sha256").decode("utf-8")
        assert "extraction.csv" in checksums_txt
        assert "risk_of_bias.json" in checksums_txt
        assert "fulltext_manifest.json" in checksums_txt
