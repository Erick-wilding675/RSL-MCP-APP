"""Testes unitários das visualizações de dados em rslapp.core.views."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from rslapp.core.errors import RSLError
from rslapp.core.models import Affiliation, Author, Work
from rslapp.core.views import get_list_view, get_search_log_view
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


def _seed_searches(store: Store, count: int = 25) -> list[str]:
    search_ids: list[str] = []
    for i in range(1, count + 1):
        saved_search, _list = store.record_search(
            {
                "kind": "terms",
                "query": f"busca-{i}",
                "request_summary": f"Resumo da busca {i}",
                "sources": [{"name": "openalex", "status": "ok", "query": f"q{i}", "found": i, "fetched": i}],
            },
            {"status": "complete", "works": []},
        )
        search_ids.append(str(saved_search["id"]))
    return search_ids


# FR-05, FR-13, D-002: get_search_log devolve entradas mais recentes em ordem cronológica e respeita limit
def test_fr05_fr13_d002_get_search_log_ordem_cronologica_e_limite(tmp_path: Path) -> None:
    store = Store(tmp_path)
    search_ids = _seed_searches(store, count=25)

    # limit=10: as 10 mais recentes (s-0016 até s-0025) em ordem cronológica (antiga primeiro)
    res = get_search_log_view(store, limit=10)
    entries = res["entries"]
    assert len(entries) == 10
    entry_ids = [e["id"] for e in entries]
    assert entry_ids == search_ids[-10:]
    assert entry_ids[0] == "s-0016"
    assert entry_ids[-1] == "s-0025"
    assert res["log_file"] == str((tmp_path / "log.md").resolve())

    # limit padrão de 20
    res_default = get_search_log_view(store)
    assert len(res_default["entries"]) == 20
    assert [e["id"] for e in res_default["entries"]] == search_ids[-20:]


# FR-05, FR-13, D-002: get_search_log com search_id devolve apenas a entrada solicitada
def test_fr05_fr13_d002_get_search_log_filtra_por_search_id(tmp_path: Path) -> None:
    store = Store(tmp_path)
    _seed_searches(store, count=5)

    res = get_search_log_view(store, search_id="s-0003")
    assert len(res["entries"]) == 1
    assert res["entries"][0]["id"] == "s-0003"
    assert res["entries"][0]["query"] == "busca-3"
    assert res["log_file"] == str((tmp_path / "log.md").resolve())


# FR-05, FR-13, D-002: get_search_log com search_id inexistente ou malformado devolve search_not_found
@pytest.mark.parametrize(
    "bad_id",
    [
        "s-9999",
        "s-invalido",
        "l-0001",
        "invalido",
        "",
        "   ",
        None,
        123,
    ],
)
def test_fr05_fr13_d002_get_search_log_busca_inexistente_ou_malformada_lanca_search_not_found(
    tmp_path: Path,
    bad_id: Any,
) -> None:
    store = Store(tmp_path)
    _seed_searches(store, count=3)
    if bad_id is None:
        # None significa busca geral, não search_id inválido
        return
    with pytest.raises(RSLError) as exc_info:
        get_search_log_view(store, search_id=bad_id)
    assert exc_info.value.code == "search_not_found"


# FR-05, FR-13, D-002: get_search_log com limit inválido devolve invalid_input
@pytest.mark.parametrize(
    "bad_limit",
    [
        0,
        -1,
        201,
        "20",
        True,
        False,
        None,
    ],
)
def test_fr05_fr13_d002_get_search_log_limite_invalido_lanca_invalid_input(
    tmp_path: Path,
    bad_limit: Any,
) -> None:
    store = Store(tmp_path)
    with pytest.raises(RSLError) as exc_info:
        get_search_log_view(store, limit=bad_limit)
    assert exc_info.value.code == "invalid_input"


# FR-13, D-002: get_search_log devolve caminho absoluto do log.md mesmo sem o arquivo existir ainda
def test_fr13_d002_get_search_log_caminho_absoluto_mesmo_sem_log_md(tmp_path: Path) -> None:
    store = Store(tmp_path)
    assert not store.log_path.exists()

    res = get_search_log_view(store)
    assert res["entries"] == []
    log_path = Path(res["log_file"])
    assert log_path.is_absolute()
    assert log_path.name == "log.md"
    assert log_path == store.log_path.resolve()


def _create_synthetic_work(idx: int) -> Work:
    """Cria um trabalho sintético com exatamente 10 autores e 40 referências para medição T-006."""
    authors = [
        Author(
            name=f"Synthetic Author {a:02d}",
            orcid=f"0000-0002-{a:04d}-{idx:04d}",
            affiliations=[
                Affiliation(
                    name=f"Laboratory of Systematic Reviews {a}, University of Benchmark",
                    country_code="BR",
                )
            ],
        )
        for a in range(1, 11)
    ]
    references = [f"W{r:09d}" for r in range(1, 41)]
    return Work(
        title=f"Synthetic Benchmark Work {idx:04d} on Systematic Literature Review and Artificial Intelligence",
        doi=f"10.1234/synth.benchmark.{idx:04d}",
        year=2024,
        type="article",
        venue="Journal of Synthetic Reviews and Empirical Methods",
        abstract=(
            "This is a realistic synthetic abstract for benchmarking payload sizes of get_list responses. "
            "It contains typical academic terminology regarding methodology, deduplication, and citation networks."
        ),
        keywords=["systematic review", "benchmark", "mcp server", "bibliometrics", "vosviewer"],
        authors=authors,
        references=references,
        references_count=40,
        citations={"openalex": 15, "crossref": 12, "semantic_scholar": 8},
        source_ids={"openalex": f"W{idx:09d}", "crossref": f"10.1234/synth.benchmark.{idx:04d}"},
    )


# D-002, T-006: Medição do tamanho em bytes do JSON de get_list com 100 e 500 trabalhos (10 autores, 40 referências)
def test_t006_d002_medicao_tamanho_payload_100_e_500_trabalhos(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path)

    # Criação da lista de 100 trabalhos sintéticos
    works_100 = [_create_synthetic_work(i) for i in range(1, 101)]
    _search_100, saved_list_100 = store.record_search(
        {
            "kind": "terms",
            "query": "benchmark-100",
            "sources": [{"name": "openalex", "status": "ok", "query": "q", "found": 100, "fetched": 100}],
        },
        {"status": "complete", "works": [w.to_dict() for w in works_100]},
    )
    list_id_100 = str(saved_list_100["id"])

    # 100 artigos em summary
    res_100_summary = get_list_view(store, list_id_100, page=1, page_size=100, detail="summary")
    bytes_100_summary = len(json.dumps(res_100_summary, ensure_ascii=False).encode("utf-8"))

    # 100 artigos em full
    res_100_full = get_list_view(store, list_id_100, page=1, page_size=100, detail="full")
    bytes_100_full = len(json.dumps(res_100_full, ensure_ascii=False).encode("utf-8"))

    # Criação da lista de 500 trabalhos sintéticos
    works_500 = [_create_synthetic_work(i) for i in range(1, 501)]
    _search_500, saved_list_500 = store.record_search(
        {
            "kind": "terms",
            "query": "benchmark-500",
            "sources": [{"name": "openalex", "status": "ok", "query": "q", "found": 500, "fetched": 500}],
        },
        {"status": "complete", "works": [w.to_dict() for w in works_500]},
    )
    list_id_500 = str(saved_list_500["id"])

    # 500 artigos em summary (usando max_page_size=500 para permitir medir resposta com 500 itens)
    res_500_summary = get_list_view(
        store, list_id_500, page=1, page_size=500, detail="summary", max_page_size=500
    )
    bytes_500_summary = len(json.dumps(res_500_summary, ensure_ascii=False).encode("utf-8"))

    # 500 artigos em full (usando max_page_size=500)
    res_500_full = get_list_view(
        store, list_id_500, page=1, page_size=500, detail="full", max_page_size=500
    )
    bytes_500_full = len(json.dumps(res_500_full, ensure_ascii=False).encode("utf-8"))

    # Asserções de sanidade das respostas e medições
    assert len(res_100_summary["works"]) == 100
    assert len(res_100_full["works"]) == 100
    assert len(res_500_summary["works"]) == 500
    assert len(res_500_full["works"]) == 500

    assert bytes_100_summary > 0
    assert bytes_100_full > bytes_100_summary
    assert bytes_500_summary > bytes_100_summary
    assert bytes_500_full > bytes_500_summary

    # Exibe os valores para captura no log do teste
    print("\n--- MEDIÇÃO T-006 (Bytes UTF-8 compactos) ---")
    print(f"100 artigos summary: {bytes_100_summary} bytes ({bytes_100_summary / 1024:.2f} KB)")
    print(f"100 artigos full:    {bytes_100_full} bytes ({bytes_100_full / 1024:.2f} KB)")
    print(f"500 artigos summary: {bytes_500_summary} bytes ({bytes_500_summary / 1024:.2f} KB)")
    print(f"500 artigos full:    {bytes_500_full} bytes ({bytes_500_full / 1024:.2f} KB)")


