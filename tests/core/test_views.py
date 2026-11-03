"""Testes unitários das visualizações de dados em rslapp.core.views."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from rslapp.core.errors import RSLError
from rslapp.core.models import Affiliation, Author, Work
from rslapp.core.views import get_list_view
from rslapp.store import Store


def _build_work(index: int) -> Work:
    return Work(
        title=f"Artigo de Teste {index:03d}",
        doi=f"10.1234/test.{index:03d}",
        year=2020 + (index % 5),
        type="article",
        venue=f"Revista Científica {index % 3}",
        abstract=f"Resumo detalhado do artigo {index:03d} para testes.",
        keywords=[f"keyword-{index}", "ciência", "revisão"],
        authors=[
            Author(
                name=f"Autor {index} A",
                orcid=f"0000-0001-{index:04d}-0001",
                affiliations=[Affiliation(name=f"Universidade {index}", country_code="BR")],
            ),
            Author(name=f"Autor {index} B"),
        ],
        references=[f"W{r:04d}" for r in range(1, 6)],
        references_count=5,
        citations={"openalex": index * 2, "crossref": index},
        source_ids={"openalex": f"W{index:05d}"},
    )


def _seed_list(store: Store, total_works: int = 60, status: str = "complete") -> str:
    works = [_build_work(i) for i in range(1, total_works + 1)]
    _search, saved_list = store.record_search(
        {
            "kind": "terms",
            "query": "inteligência artificial",
            "sources": [{"name": "openalex", "status": "ok", "query": "q", "found": total_works, "fetched": total_works}],
        },
        {"status": status, "works": [w.to_dict() for w in works]},
    )
    return str(saved_list["id"])


# FR-12, D-002: get_list pagina com page e page_size, devolve next_page e respeita total
def test_fr12_d002_get_list_view_paginacao_e_proxima_pagina(tmp_path: Path) -> None:
    store = Store(tmp_path)
    list_id = _seed_list(store, total_works=60)

    # Página 1 (25 itens)
    p1 = get_list_view(store, list_id, page=1, page_size=25, detail="summary")
    assert p1["list_id"] == list_id
    assert p1["search_id"] == "s-0001"
    assert p1["status"] == "complete"
    assert p1["total"] == 60
    assert p1["page"] == 1
    assert p1["page_size"] == 25
    assert p1["next_page"] == 2
    assert len(p1["works"]) == 25
    assert p1["works"][0]["title"] == "Artigo de Teste 001"
    assert p1["works"][24]["title"] == "Artigo de Teste 025"

    # Página 2 (25 itens)
    p2 = get_list_view(store, list_id, page=2, page_size=25, detail="summary")
    assert p2["page"] == 2
    assert p2["next_page"] == 3
    assert len(p2["works"]) == 25
    assert p2["works"][0]["title"] == "Artigo de Teste 026"
    assert p2["works"][24]["title"] == "Artigo de Teste 050"

    # Página 3 (10 itens restantes)
    p3 = get_list_view(store, list_id, page=3, page_size=25, detail="summary")
    assert p3["page"] == 3
    assert p3["next_page"] is None
    assert len(p3["works"]) == 10
    assert p3["works"][0]["title"] == "Artigo de Teste 051"
    assert p3["works"][9]["title"] == "Artigo de Teste 060"

    # Página 4 (além do fim -> vazia e next_page nulo)
    p4 = get_list_view(store, list_id, page=4, page_size=25, detail="summary")
    assert p4["page"] == 4
    assert p4["next_page"] is None
    assert p4["works"] == []
    assert p4["total"] == 60


# FR-12, D-002: get_list respeita detail summary (mesmos campos de search_works) e full (Work.to_dict())
def test_fr12_d002_get_list_view_respeita_detail_summary_e_full(tmp_path: Path) -> None:
    store = Store(tmp_path)
    list_id = _seed_list(store, total_works=5)

    summary_view = get_list_view(store, list_id, page=1, page_size=5, detail="summary")
    item_sum = summary_view["works"][0]
    expected_summary_keys = {"doi", "title", "authors", "year", "venue", "references_count", "citations"}
    assert set(item_sum.keys()) == expected_summary_keys
    assert item_sum["title"] == "Artigo de Teste 001"
    assert item_sum["authors"] == ["Autor 1 A", "Autor 1 B"]
    assert item_sum["references_count"] == 5
    assert item_sum["citations"] == {"openalex": 2, "crossref": 1}
    assert "abstract" not in item_sum
    assert "keywords" not in item_sum
    assert "references" not in item_sum

    full_view = get_list_view(store, list_id, page=1, page_size=5, detail="full")
    item_full = full_view["works"][0]
    expected_full_keys = {
        "title",
        "doi",
        "year",
        "type",
        "venue",
        "abstract",
        "keywords",
        "authors",
        "references",
        "references_count",
        "citations",
        "source_ids",
    }
    assert set(item_full.keys()) == expected_full_keys
    assert item_full["abstract"] == "Resumo detalhado do artigo 001 para testes."
    assert item_full["keywords"] == ["keyword-1", "ciência", "revisão"]
    assert item_full["references"] == ["W0001", "W0002", "W0003", "W0004", "W0005"]
    assert item_full["source_ids"] == {"openalex": "W00001"}
    assert isinstance(item_full["authors"], list)
    assert item_full["authors"][0]["orcid"] == "0000-0001-0001-0001"
    assert item_full["authors"][0]["affiliations"][0]["name"] == "Universidade 1"


# FR-12, D-002: get_list com id inexistente ou malformado devolve list_not_found
@pytest.mark.parametrize(
    "bad_id",
    [
        "l-9999",
        "l-invalido",
        "s-0001",
        "invalido",
        "",
        "   ",
        None,
        123,
    ],
)
def test_fr12_d002_get_list_view_id_inexistente_ou_malformado_lanca_list_not_found(
    tmp_path: Path,
    bad_id: Any,
) -> None:
    store = Store(tmp_path)
    with pytest.raises(RSLError) as exc_info:
        get_list_view(store, list_id=bad_id)
    assert exc_info.value.code == "list_not_found"


# FR-12, D-002: get_list com parâmetros fora do permitido devolve invalid_input
@pytest.mark.parametrize(
    ("page", "page_size", "detail"),
    [
        (0, 25, "summary"),
        (-1, 25, "summary"),
        ("1", 25, "summary"),
        (True, 25, "summary"),
        (1, 0, "summary"),
        (1, -5, "summary"),
        (1, 101, "summary"),
        (1, "25", "summary"),
        (1, True, "summary"),
        (1, 25, "all"),
        (1, 25, ""),
        (1, 25, None),
        (1, 25, 123),
    ],
)
def test_fr12_d002_get_list_view_parametros_invalidos_lanca_invalid_input(
    tmp_path: Path,
    page: Any,
    page_size: Any,
    detail: Any,
) -> None:
    store = Store(tmp_path)
    list_id = _seed_list(store, total_works=5)
    with pytest.raises(RSLError) as exc_info:
        get_list_view(store, list_id, page=page, page_size=page_size, detail=detail)
    assert exc_info.value.code == "invalid_input"
