"""Testes unitários do motor de comparação diferencial da Revisão Viva (FR-32, D-043)."""

from __future__ import annotations

import json
from pathlib import Path

from rslapp.core.differential import (
    compute_search_difference,
    format_differential_markdown,
)
from rslapp.store import Store


# FR-32, D-043: Identificação de artigos adicionados, mantidos e estatísticas
def test_compute_search_difference_basico() -> None:
    work1 = {
        "id": "w1",
        "title": "Estudo sobre Inteligência Artificial",
        "year": 2024,
        "doi": "10.1000/182",
        "authors": [{"name": "Silva, João"}],
    }
    work2 = {
        "id": "w2",
        "title": "Revisões Sistemáticas Automatizadas",
        "year": 2023,
        "doi": "10.1000/183",
        "authors": [{"name": "Souza, Maria"}],
    }
    work3 = {
        "id": "w3",
        "title": "Novo Artigo Publicado Recentemente",
        "year": 2025,
        "doi": "10.1000/999",
        "authors": [{"name": "Santos, Carlos"}],
    }

    base_works = [work1, work2]
    new_works = [work1, work2, work3]

    diff = compute_search_difference(
        base_works=base_works,
        new_works=new_works,
        base_list_id="l-100",
        new_list_id="l-101",
    )

    assert diff["base_total"] == 2
    assert diff["new_total"] == 3
    assert diff["retained_count"] == 2
    assert diff["added_count"] == 1
    assert diff["missing_count"] == 0
    assert "w3" in diff["added_ids"]
    assert len(diff["added_works"]) == 1
    assert diff["added_works"][0]["title"] == "Novo Artigo Publicado Recentemente"


# FR-32, D-043: Correspondência por título e ano quando DOI estiver ausente
def test_compute_search_difference_sem_doi() -> None:
    work_a = {
        "id": "wa",
        "title": "Machine Learning in Healthcare",
        "year": 2022,
        "authors": [{"name": "Smith, J."}],
    }
    work_b = {
        "id": "wb",
        "title": "Deep Learning Diagnostics",
        "year": 2023,
        "authors": [{"name": "Doe, J."}],
    }

    # Nova busca com variação sutil de pontuação/maiúsculas no título
    work_a_updated = {
        "id": "wa_new",
        "title": "Machine Learning in Healthcare!",
        "year": 2022,
        "authors": [{"name": "Smith, J."}],
    }
    work_c = {
        "id": "wc",
        "title": "Transformer Models in Medical Imaging",
        "year": 2024,
        "authors": [{"name": "Taylor, A."}],
    }

    diff = compute_search_difference([work_a, work_b], [work_a_updated, work_c])

    assert diff["retained_count"] == 1  # work_a identificado pelo título e ano
    assert diff["added_count"] == 1
    assert diff["missing_count"] == 1
    assert diff["added_works"][0]["id"] == "wc"


# FR-32, D-043: Relatório metodológico formatado em Markdown
def test_format_differential_markdown() -> None:
    diff_data = {
        "base_list_id": "l-1",
        "new_list_id": "l-2",
        "updated_at": "2026-11-18T20:00:00Z",
        "base_total": 10,
        "new_total": 12,
        "retained_count": 10,
        "added_count": 2,
        "missing_count": 0,
        "added_works": [
            {
                "id": "w_new_1",
                "title": "Artigo Inédito da Área",
                "year": 2025,
                "venue": "Revista Brasileira de Computação",
                "doi": "10.1234/rbc.2025.1",
                "authors": ["Silva, A.", "Mendes, E."],
            }
        ],
    }

    md = format_differential_markdown(diff_data)
    assert "# Relatório de Atualização Metodológica" in md
    assert "FR-32, D-043" in md
    assert "Artigo Inédito da Área" in md
    assert "https://doi.org/10.1234/rbc.2025.1" in md
    assert "Registros anteriores preservados" in md


# FR-32, D-043: Persistência no Store (save_differential, list_differentials, get_latest_differential)
def test_store_differential_persistence(tmp_path: Path) -> None:
    store = Store(data_dir=tmp_path)
    diff_payload = {
        "base_list_id": "l-10",
        "new_list_id": "l-20",
        "updated_at": "2026-11-18T20:30:00Z",
        "base_total": 5,
        "new_total": 7,
        "retained_count": 5,
        "added_count": 2,
        "missing_count": 0,
        "added_ids": ["w6", "w7"],
    }

    saved = store.save_differential(diff_payload)
    assert saved["base_list_id"] == "l-10"

    diffs = store.list_differentials("l-10")
    assert len(diffs) == 1
    assert diffs[0]["added_count"] == 2

    latest = store.get_latest_differential("l-10")
    assert latest is not None
    assert latest["new_list_id"] == "l-20"

    # Confere se o arquivo foi gravado fisicamente em differential/
    files = list(store.differential_dir.glob("*.json"))
    assert len(files) == 1
    content = json.loads(files[0].read_text(encoding="utf-8"))
    assert content["base_list_id"] == "l-10"
