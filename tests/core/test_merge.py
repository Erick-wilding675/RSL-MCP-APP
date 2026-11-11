"""Testes unitários do miolo de junção de listas salvas (merge_lists) (D-021)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from rslapp.core.errors import RSLError
from rslapp.core.merge import run_merge
from rslapp.core.models import Author, Work
from rslapp.core.repeat import run_repeat
from rslapp.store import Store


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path)


def _save_test_list(
    store: Store,
    works: list[Work],
    *,
    status: str = "complete",
    request_summary: str = "Busca teste",
) -> tuple[dict[str, Any], dict[str, Any]]:
    search_data = {
        "kind": "terms",
        "request_summary": request_summary,
        "repeated_from": None,
        "origin": None,
        "params": {"query": "teste", "max_results": 100, "sources": ["openalex"]},
        "sources": [
            {
                "name": "openalex",
                "status": "ok" if status == "complete" else "failed",
                "query": "query=teste",
                "found": len(works),
                "fetched": len(works),
                "from_cache": False,
                "fetched_at": None,
            }
        ],
    }
    list_data = {
        "status": status,
        "total": len(works),
        "works": [w.to_dict() for w in works],
    }
    return store.record_search(search_data, list_data)


# D-021, FR-04: duas listas com um artigo em comum (mesmo DOI) viram uma lista sem duplicatas com source_ids unidos
@pytest.mark.anyio
async def test_d021_fr04_merge_com_mesmo_doi_deduplica_e_une_source_ids(store: Store) -> None:
    work_a1 = Work(
        title="Estudo sobre Aprendizado de Máquina",
        doi="10.1000/182",
        year=2024,
        authors=[Author(name="Silva, João")],
        source_ids={"openalex": "W1001"},
        citations={"openalex": 15},
    )
    work_b = Work(
        title="Redes Neurais Convolucionais",
        doi="10.1000/183",
        year=2023,
        authors=[Author(name="Souza, Maria")],
        source_ids={"openalex": "W1002"},
        citations={"openalex": 8},
    )
    work_a2 = Work(
        title="Estudo sobre Aprendizado de Máquina",
        doi="10.1000/182",
        year=2024,
        authors=[Author(name="Silva, J.")],
        source_ids={"crossref": "10.1000/182"},
        citations={"crossref": 10},
    )
    work_c = Work(
        title="Processamento de Linguagem Natural",
        doi="10.1000/184",
        year=2024,
        authors=[Author(name="Pereira, Ana")],
        source_ids={"crossref": "10.1000/184"},
        citations={"crossref": 3},
    )

    _save_test_list(store, [work_a1, work_b])
    _save_test_list(store, [work_a2, work_c])

    res = await run_merge(
        store,
        list_ids=["l-0001", "l-0002"],
        request_summary="Juntar buscas em IA",
    )

    assert res["status"] == "complete"
    assert res["total"] == 3
    assert res["duplicates_removed"] == 1
    assert res["merged_from"] == ["l-0001", "l-0002"]
    assert len(res["works"]) == 3
    assert "incomplete_from" not in res

    saved_list = store.get_list(res["list_id"])
    assert saved_list["status"] == "complete"
    assert saved_list["total"] == 3

    # Confere que o artigo com mesmo DOI tem source_ids e citations combinados
    merged_a = next(w for w in saved_list["works"] if w["doi"] == "10.1000/182")
    assert merged_a["source_ids"] == {"openalex": "W1001", "crossref": "10.1000/182"}
    assert merged_a["citations"] == {"openalex": 15, "crossref": 10}


# D-021, FR-04: artigos sem DOI com o mesmo título e ano também se juntam
@pytest.mark.anyio
async def test_d021_fr04_merge_sem_doi_com_mesmo_titulo_e_ano_junta(store: Store) -> None:
    work_sem_doi_1 = Work(
        title="Ensino Híbrido na Educação Básica: Uma Revisão",
        doi=None,
        year=2022,
        authors=[Author(name="Santos, Carlos")],
        source_ids={"openalex": "W2001"},
    )
    work_outro = Work(
        title="Metodologias Ativas no Ensino Superior",
        doi="10.1000/999",
        year=2021,
    )
    work_sem_doi_2 = Work(
        title="ensino hibrido na educacao basica: uma revisao!",
        doi=None,
        year=2022,
        authors=[Author(name="Santos, C.")],
        source_ids={"semantic_scholar": "S2001"},
    )

    _save_test_list(store, [work_sem_doi_1, work_outro])
    _save_test_list(store, [work_sem_doi_2])

    res = await run_merge(
        store,
        list_ids=["l-0001", "l-0002"],
        request_summary="Juntar ensino híbrido",
    )

    assert res["status"] == "complete"
    assert res["total"] == 2
    assert res["duplicates_removed"] == 1

    saved_list = store.get_list(res["list_id"])
    merged_hibrido = next(w for w in saved_list["works"] if w["year"] == 2022)
    assert merged_hibrido["source_ids"] == {"openalex": "W2001", "semantic_scholar": "S2001"}


# D-021, FR-08: uma lista de origem incompleta deixa a junção incompleta com incomplete_from
@pytest.mark.anyio
async def test_d021_fr08_merge_lista_incompleta_gera_status_incomplete(store: Store) -> None:
    w1 = Work(title="Artigo 1", doi="10.1000/1")
    w2 = Work(title="Artigo 2", doi="10.1000/2")
    w3 = Work(title="Artigo 3", doi="10.1000/3")

    _save_test_list(store, [w1], status="complete")
    _save_test_list(store, [w2], status="incomplete")
    _save_test_list(store, [w3], status="complete")

    res = await run_merge(
        store,
        list_ids=["l-0001", "l-0002", "l-0003"],
        request_summary="Junção com lista incompleta",
    )

    assert res["status"] == "incomplete"
    assert res["incomplete_from"] == ["l-0002"]

    saved_list = store.get_list(res["list_id"])
    assert saved_list["status"] == "incomplete"
    assert saved_list["incomplete_from"] == ["l-0002"]

    saved_search = store.get_search(res["search_id"])
    assert saved_search["incomplete_from"] == ["l-0002"]


# D-021: validações de entrada em list_ids e request_summary
@pytest.mark.anyio
async def test_d021_validacao_erros_invalid_input(store: Store) -> None:
    _save_test_list(store, [Work(title="Artigo 1", doi="10.1000/1")])
    _save_test_list(store, [Work(title="Artigo 2", doi="10.1000/2")])

    # Menos de 2 listas
    with pytest.raises(RSLError) as exc_less:
        await run_merge(store, list_ids=["l-0001"])
    assert exc_less.value.code == "invalid_input"

    # Mais de 20 listas
    fake_21_ids = [f"l-{i:04d}" for i in range(1, 22)]
    with pytest.raises(RSLError) as exc_more:
        await run_merge(store, list_ids=fake_21_ids)
    assert exc_more.value.code == "invalid_input"

    # IDs repetidos
    with pytest.raises(RSLError) as exc_dup:
        await run_merge(store, list_ids=["l-0001", "l-0001"])
    assert exc_dup.value.code == "invalid_input"

    # Formato inválido de ID
    with pytest.raises(RSLError) as exc_fmt:
        await run_merge(store, list_ids=["l-0001", "s-0002"])
    assert exc_fmt.value.code == "invalid_input"

    with pytest.raises(RSLError) as exc_fmt2:
        await run_merge(store, list_ids=["l-0001", "invalido"])
    assert exc_fmt2.value.code == "invalid_input"

    # list_ids não sendo lista
    with pytest.raises(RSLError) as exc_notlist:
        await run_merge(store, list_ids="l-0001,l-0002")  # type: ignore[arg-type]
    assert exc_notlist.value.code == "invalid_input"

    # request_summary não sendo string
    with pytest.raises(RSLError) as exc_sum:
        await run_merge(store, list_ids=["l-0001", "l-0002"], request_summary=123)  # type: ignore[arg-type]
    assert exc_sum.value.code == "invalid_input"


# D-021: lista inexistente devolve list_not_found e nada é gravado
@pytest.mark.anyio
async def test_d021_lista_inexistente_volta_list_not_found_e_nada_gravado(store: Store) -> None:
    _save_test_list(store, [Work(title="Artigo 1", doi="10.1000/1")])

    with pytest.raises(RSLError) as exc_info:
        await run_merge(store, list_ids=["l-0001", "l-9999"])

    assert exc_info.value.code == "list_not_found"
    assert not (store.lists_dir / "l-0002.json").exists()
    assert not (store.searches_dir / "s-0002.json").exists()


# D-021, FR-05, FR-13: log.md ganha entrada de junção e rebuild_log preserva conteúdo
@pytest.mark.anyio
async def test_d021_fr05_fr13_log_md_ganha_entrada_de_juncao_e_rebuild_log(store: Store) -> None:
    w1 = Work(title="A", doi="10.1000/1")
    w2 = Work(title="B", doi="10.1000/2")
    w3 = Work(title="A", doi="10.1000/1")

    _save_test_list(store, [w1, w2])
    _save_test_list(store, [w3])

    res = await run_merge(
        store,
        list_ids=["l-0001", "l-0002"],
        request_summary="Juntar A e B",
    )

    log_content = store.read_log()
    assert f"## {res['search_id']} · " in log_content
    assert " · junção\n" in log_content
    assert "Pedido: Juntar A e B\n" in log_content
    assert f"Lista: {res['list_id']} · completa · 2 artigos\n" in log_content
    assert "Duplicatas removidas: 1 artigo\n" in log_content
    assert "- l-0001 · 2 artigos\n" in log_content
    assert "- l-0002 · 1 artigo" in log_content

    # FR-13: rebuild_log deve manter o conteúdo idêntico
    rebuilt = store.rebuild_log()
    assert rebuilt == log_content


# D-021: repeat_search em registro de junção responde invalid_input
@pytest.mark.anyio
async def test_d021_repeat_search_em_juncao_responde_invalid_input(store: Store) -> None:
    w1 = Work(title="A", doi="10.1000/1")
    w2 = Work(title="B", doi="10.1000/2")
    _save_test_list(store, [w1])
    _save_test_list(store, [w2])

    res = await run_merge(store, list_ids=["l-0001", "l-0002"])
    merge_search_id = res["search_id"]

    with pytest.raises(RSLError) as exc_info:
        await run_repeat(store, sources=[], search_id=merge_search_id)

    assert exc_info.value.code == "invalid_input"
    assert "uma junção não pode ser repetida; repita as buscas de origem" in exc_info.value.message
