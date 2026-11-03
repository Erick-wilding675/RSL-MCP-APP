"""Testes da linha de junção (merge) no log legível (store/log.py e Store.rebuild_log)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from rslapp.store import Store, format_log_entry


def _base_search(**extra: Any) -> dict[str, Any]:
    return {
        "id": "s-0001",
        "list_id": "l-0001",
        "created_at": "2026-11-03T14:00:00Z",
        "kind": "terms",
        "request_summary": "Busca sobre aprendizado de máquina",
        "repeated_from": None,
        "origin": None,
        "sources": [
            {
                "name": "openalex",
                "status": "ok",
                "query": "search=ml",
                "found": 50,
                "fetched": 20,
                "from_cache": False,
                "fetched_at": None,
            },
            {
                "name": "crossref",
                "status": "ok",
                "query": "query=ml",
                "found": 40,
                "fetched": 20,
                "from_cache": False,
                "fetched_at": None,
            },
        ],
        **extra,
    }


def _base_list(**extra: Any) -> dict[str, Any]:
    return {
        "id": "l-0001",
        "search_id": "s-0001",
        "created_at": "2026-11-03T14:00:00Z",
        "status": "complete",
        "total": 30,
        "works": [],
        **extra,
    }


# FR-04, FR-13: Formatação da linha de junção com divergências
def test_fr04_fr13_linha_de_juncao_com_divergencias() -> None:
    search_data = _base_search(
        merge={
            "merged": 12,
            "divergences": {"year": 3, "title": 1},
        }
    )
    entry = format_log_entry(search_data, _base_list())
    assert (
        "Lista: l-0001 · completa · 30 artigos\n"
        "Junção: 12 artigos em mais de uma fonte · divergências: ano 3, título 1\n"
        "- openalex · ok"
    ) in entry


# FR-04, FR-13: Formatação da linha de junção sem divergências
def test_fr04_fr13_linha_de_juncao_sem_divergencias() -> None:
    search_data = _base_search(
        merge={
            "merged": 12,
            "divergences": {},
        }
    )
    entry = format_log_entry(search_data, _base_list())
    assert (
        "Lista: l-0001 · completa · 30 artigos\n"
        "Junção: 12 artigos em mais de uma fonte · sem divergências\n"
        "- openalex · ok"
    ) in entry


# FR-04, FR-13: Singular e zero artigos na linha de junção
def test_fr04_fr13_linha_de_juncao_singular_e_zero() -> None:
    entry_1 = format_log_entry(
        _base_search(merge={"merged": 1, "divergences": {}}), _base_list()
    )
    assert "Junção: 1 artigo em mais de uma fonte · sem divergências" in entry_1

    entry_0 = format_log_entry(
        _base_search(merge={"merged": 0, "divergences": {}}), _base_list()
    )
    assert "Junção: 0 artigos em mais de uma fonte · sem divergências" in entry_0


# FR-04, FR-13: Todos os quatro campos de divergência são suportados (ano, título, doi, veículo)
def test_fr04_fr13_todos_os_campos_de_divergencia_formatados() -> None:
    search_data = _base_search(
        merge={
            "merged": 5,
            "divergences": {"year": 2, "title": 1, "doi": 1, "venue": 3},
        }
    )
    entry = format_log_entry(search_data, _base_list())
    assert (
        "Junção: 5 artigos em mais de uma fonte · divergências: ano 2, título 1, doi 1, veículo 3"
    ) in entry


# FR-13: Busca sem merge preserva formato sem linha de junção (retrocompatibilidade)
def test_fr13_busca_sem_merge_nao_tem_linha_de_juncao() -> None:
    search_data = _base_search()  # sem campo merge
    entry = format_log_entry(search_data, _base_list())
    assert "Junção:" not in entry


# FR-13: Validações de erro no campo merge
def test_fr13_merge_invalido_levanta_value_error() -> None:
    with pytest.raises(ValueError, match="Campo 'merge' deve ser um dicionário"):
        format_log_entry(_base_search(merge="invalido"), _base_list())

    with pytest.raises(ValueError, match="Total de 'merged' inválido"):
        format_log_entry(_base_search(merge={"merged": -1}), _base_list())

    with pytest.raises(ValueError, match="Campo 'divergences' deve ser um dicionário"):
        format_log_entry(_base_search(merge={"merged": 2, "divergences": "invalido"}), _base_list())


# D-007, FR-13: rebuild_log reproduz exatamente a mesma linha de junção a partir de searches/
def test_d007_fr13_rebuild_log_reproduz_mesma_linha_de_juncao(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    search_data = {
        "kind": "terms",
        "request_summary": "Deduplicação de busca com divergências",
        "repeated_from": None,
        "origin": None,
        "merge": {
            "merged": 7,
            "divergences": {"year": 2, "title": 1},
        },
        "sources": [
            {
                "name": "openalex",
                "status": "ok",
                "query": "search=test",
                "found": 10,
                "fetched": 5,
                "from_cache": False,
                "fetched_at": None,
            }
        ],
    }
    list_data = {
        "status": "complete",
        "total": 5,
        "works": [],
    }

    store.record_search(search_data, list_data)
    original_log = store.read_log()
    assert "Junção: 7 artigos em mais de uma fonte · divergências: ano 2, título 1" in original_log

    # Apaga o log.md do disco e reconstrói
    store.log_path.unlink()
    rebuilt = store.rebuild_log()
    assert rebuilt == original_log
    assert store.read_log() == original_log
