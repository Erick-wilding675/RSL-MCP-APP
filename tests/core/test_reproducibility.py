"""Testes unitários da geração do Pacote de Reprodutibilidade Científica (FR-28, D-039)."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from rslapp.core.errors import RSLError
from rslapp.core.reproducibility import build_reproducibility_package
from rslapp.store import Store


@pytest.fixture
def store_with_data(tmp_path: Path) -> tuple[Store, str]:
    store = Store(tmp_path / "data")
    search_data = {
        "kind": "terms",
        "request_summary": "quantum computing systematic review",
        "sources": [
            {"name": "openalex", "status": "ok", "fetched": 1, "found": 1},
            {"name": "crossref", "status": "ok", "fetched": 1, "found": 1},
        ],
    }
    list_data = {
        "query": "quantum computing",
        "status": "complete",
        "total": 2,
        "works": [
            {
                "doi": "10.1000/182",
                "title": "Quantum Computing Principles",
                "year": 2024,
                "authors": [{"name": "Feynman, Richard"}],
                "venue": "Physics Review",
                "abstract": "Foundations of quantum computational systems.",
                "source": "openalex",
            },
            {
                "doi": "10.1000/183",
                "title": "Algorithms for Quantum Hardware",
                "year": 2023,
                "authors": [{"name": "Shor, Peter"}],
                "venue": "ACM Computing",
                "abstract": "Polynomial-time quantum factoring algorithms.",
                "source": "crossref",
            },
        ],
    }
    _s_rec, l_rec = store.record_search(search_data, list_data)
    list_id = l_rec["id"]

    # Adiciona decisões de triagem
    store.save_screening_decision(
        list_id,
        {
            "work_id": "10.1000/182",
            "decision": "included",
            "reason": None,
            "decided_by": "human",
            "notes": "Trabalho fundamental",
        },
    )
    store.save_screening_decision(
        list_id,
        {
            "work_id": "10.1000/183",
            "decision": "excluded",
            "reason": "Fora do escopo temporal",
            "decided_by": "ai",
            "ai_model": "gemini-1.5-pro",
        },
    )

    return store, list_id


def test_fr28_d039_build_reproducibility_package_success(
    store_with_data: tuple[Store, str],
    tmp_path: Path,
) -> None:
    store, list_id = store_with_data
    export_dir = tmp_path / "exports"

    res = build_reproducibility_package(list_id, store, export_dir=export_dir)

    assert res["list_id"] == list_id
    assert res["filename"] == f"reproducibility_{list_id}.zip"
    assert res["file_count"] == 15
    assert res["size_bytes"] > 0
    assert len(res["sha256"]) == 64
    assert res["path"] is not None

    zip_file = Path(res["path"])
    assert zip_file.is_file()

    # Confere que o hash do arquivo no disco bate com o retornado
    disk_hash = hashlib.sha256(zip_file.read_bytes()).hexdigest()
    assert disk_hash == res["sha256"]

    # Abre o zip e valida os 15 arquivos
    with zipfile.ZipFile(zip_file, "r") as zf:
        namelist = zf.namelist()
        expected_files = [
            "metadata.json",
            "search_log.md",
            "works.csv",
            "works.ris",
            "works.bib",
            "references_abnt.txt",
            "screening.json",
            "prisma_2020.svg",
            "prisma_s_checklist.md",
            "ai_disclosure_pt.md",
            "ai_disclosure_en.md",
            "vosviewer_coauthorship.map",
            "vosviewer_coauthorship.network",
            "gephi_coauthorship.gexf",
            "checksums.sha256",
        ]
        for expected in expected_files:
            assert expected in namelist, f"Arquivo {expected} ausente no zip"

        # Valida metadata.json
        meta = json.loads(zf.read("metadata.json").decode("utf-8"))
        assert meta["list_id"] == list_id
        assert meta["total_works"] == 2
        assert meta["standard_spec"] == "FR-28 / D-039"

        # Valida manifesto checksums.sha256
        checksum_text = zf.read("checksums.sha256").decode("utf-8")
        lines = [line.strip() for line in checksum_text.splitlines() if line.strip()]
        assert len(lines) == 14  # 14 arquivos auditados (exclui checksums.sha256)

        for line in lines:
            fhash, fname = line.split("  ", 1)
            file_bytes = zf.read(fname)
            calc_hash = hashlib.sha256(file_bytes).hexdigest()
            assert fhash == calc_hash, f"Hash inválido para {fname}: {fhash} != {calc_hash}"


def test_fr28_d039_build_reproducibility_package_list_not_found(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    with pytest.raises(RSLError) as exc_info:
        build_reproducibility_package("l-9999", store)
    assert exc_info.value.code == "list_not_found"


def test_fr28_d039_build_reproducibility_package_empty_list(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    _, l_rec = store.record_search(
        {"kind": "terms", "request_summary": "empty test", "sources": []},
        {"query": "empty", "status": "complete", "total": 0, "works": []},
    )
    with pytest.raises(RSLError) as exc_info:
        build_reproducibility_package(l_rec["id"], store)
    assert exc_info.value.code == "empty_list"
