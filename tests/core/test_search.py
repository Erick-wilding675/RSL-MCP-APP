"""Testes do miolo de busca (core/search.py) com fontes simuladas."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from rslapp.core import search as search_mod
from rslapp.core.errors import RSLError
from rslapp.core.models import Affiliation, Author, SourceResult, Work
from rslapp.core.search import deduplicate_works, normalize_title, run_search
from rslapp.store import Store


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class FakeSource:
    """Fonte acadêmica simulada sem chamadas de rede."""

    def __init__(
        self,
        name: str = "openalex",
        results: list[SourceResult] | SourceResult | None = None,
        needs_key: bool = True,
    ) -> None:
        self.name = name
        self.needs_key = needs_key
        if isinstance(results, list):
            self._results = list(results)
        elif results is not None:
            self._results = [results]
        else:
            self._results = []
        self.calls: list[tuple[str, int]] = []

    def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
        return {"search": query.strip(), "max_results": max_results}

    async def search(self, query: str, max_results: int) -> SourceResult:
        self.calls.append((query, max_results))
        if len(self._results) > 1:
            return self._results.pop(0)
        if self._results:
            return self._results[0]
        return SourceResult(
            name=self.name,
            status="ok",
            query=f"search={query} · max={max_results}",
            found=0,
            fetched=0,
            works=[],
        )


def _sample_work(
    title: str = "Interpretability in Machine Learning",
    doi: str | None = "10.1234/ml.2024.01",
    year: int | None = 2024,
    oa_id: str = "W100",
    cited: int = 17,
) -> Work:
    return Work(
        title=title,
        doi=doi,
        year=year,
        type="article",
        venue="Journal of AI",
        abstract="Resumo completo do trabalho sobre interpretabilidade.",
        keywords=["machine learning", "xai"],
        authors=[
            Author(
                name="Maria Silva",
                orcid="0000-0002-1825-0097",
                ids={"openalex": "A1"},
                position="first",
                is_corresponding=True,
                affiliations=[
                    Affiliation(
                        name="USP",
                        ids={"openalex": "I1", "ror": "https://ror.org/036rp1748"},
                        country_code="BR",
                    )
                ],
                raw_affiliations=["Universidade de São Paulo"],
            ),
            Author(name="João Souza", ids={"openalex": "A2"}, position="last"),
        ],
        references=["W200", "W300"],
        references_count=2,
        citations={"openalex": cited},
        source_ids={"openalex": oa_id},
    )


# FR-01, FR-05, FR-12, D-002, D-003: Busca devolve lista, grava lists/, searches/ e log.md com ids
@pytest.mark.anyio
async def test_fr01_fr05_fr12_d002_d003_busca_grava_lista_busca_e_log_e_devolve_ids(
    tmp_path: Path,
) -> None:
    tree = ast.parse(Path(search_mod.__file__).read_text(encoding="utf-8"))
    imported = [
        node.name
        for stmt in ast.walk(tree)
        if isinstance(stmt, (ast.Import, ast.ImportFrom))
        for node in ([ast.alias(name=stmt.module or "")] if isinstance(stmt, ast.ImportFrom) else stmt.names)
    ]
    assert not any(name == "mcp" or name.startswith("mcp.") for name in imported)

    store = Store(tmp_path / "data")
    w1 = _sample_work(title="Artigo Um", doi="10.1234/um", oa_id="W1", cited=10)
    w2 = _sample_work(title="Artigo Dois", doi="10.1234/dois", oa_id="W2", cited=5)
    src = FakeSource(
        results=SourceResult(
            name="openalex",
            status="ok",
            query="search=machine learning · per_page=100 · páginas 1-1",
            found=412,
            fetched=2,
            works=[w1, w2],
        )
    )

    res = await run_search(
        store,
        [src],
        query="machine learning",
        request_summary="Artigos sobre aprendizado de máquina",
        max_results=100,
    )

    assert res["search_id"] == "s-0001"
    assert res["list_id"] == "l-0001"
    assert res["status"] == "complete"
    assert res["total"] == 2
    assert res["page"] == 1
    assert res["next_page"] is None
    assert len(res["works"]) == 2
    assert res["sources"] == [
        {
            "name": "openalex",
            "query": "search=machine learning · per_page=100 · páginas 1-1",
            "status": "ok",
            "reason": None,
            "found": 412,
            "fetched": 2,
            "from_cache": False,
            "fetched_at": None,
        }
    ]

    assert (store.lists_dir / "l-0001.json").exists()
    assert (store.searches_dir / "s-0001.json").exists()
    assert store.log_path.exists()

    saved_list = store.get_list("l-0001")
    assert saved_list["id"] == "l-0001"
    assert saved_list["search_id"] == "s-0001"
    assert saved_list["status"] == "complete"
    assert saved_list["total"] == 2
    assert saved_list["works"] == [w1.to_dict(), w2.to_dict()]

    saved_search = store.get_search("s-0001")
    assert saved_search["id"] == "s-0001"
    assert saved_search["list_id"] == "l-0001"
    assert saved_search["kind"] == "terms"
    assert saved_search["request_summary"] == "Artigos sobre aprendizado de máquina"

    log_text = store.read_log()
    assert "## s-0001 · " in log_text
    assert "busca por termos" in log_text
    assert "Pedido: Artigos sobre aprendizado de máquina" in log_text
    assert "Lista: l-0001 · completa · 2 artigos" in log_text
    assert "- openalex · ok · encontrados 412, trazidos 2 · cache: não" in log_text


# FR-04: Mesmo DOI vira um; sem DOI, mesmo título normalizado vira um; DOI diferente e título igual fica dois
@pytest.mark.anyio
async def test_fr04_deduplicacao_por_doi_e_titulo_normalizado_e_preserva_dois_diferentes(
    tmp_path: Path,
) -> None:
    assert normalize_title("  Revisão Sistemática: Árvores de Decisão (2024)! ") == (
        "revisao sistematica arvores de decisao 2024"
    )
    assert normalize_title("ab c") != normalize_title("a bc")

    w_doi_1 = Work(
        title="Título Original",
        doi=" 10.1234/ABC-1 ",
        year=2023,
        venue="Venue A",
        source_ids={"openalex": "W1"},
        citations={"openalex": 11},
    )
    w_doi_2 = Work(
        title="Título Diferente do Mesmo DOI",
        doi="10.1234/abc-1",
        year=2024,
        venue="Venue B",
        source_ids={"openalex": "W99", "crossref": "CR1"},
        citations={"openalex": 99, "crossref": 14},
    )
    w_title_1 = Work(
        title="Revisão Sistemática: Árvores de Decisão!",
        doi=None,
        year=2022,
        source_ids={"openalex": "W2"},
        citations={"openalex": 4},
    )
    w_title_2 = Work(
        title="  revisao   sistematica - arvores de decisao  ",
        doi="   ",
        year=2022,
        source_ids={"semantic_scholar": "S2"},
        citations={"semantic_scholar": 8},
    )
    w_diff_doi_1 = Work(
        title="Same Exact Title",
        doi="10.1234/first",
        year=2024,
        source_ids={"openalex": "W3"},
        citations={"openalex": 1},
    )
    w_diff_doi_2 = Work(
        title="Same Exact Title",
        doi="10.1234/second",
        year=2024,
        source_ids={"openalex": "W4"},
        citations={"openalex": 2},
    )

    deduped = deduplicate_works(
        [w_doi_1, w_doi_2, w_title_1, w_title_2, w_diff_doi_1, w_diff_doi_2]
    )
    assert len(deduped) == 4

    assert w_doi_1.source_ids == {"openalex": "W1"}
    assert w_doi_1.citations == {"openalex": 11}
    assert deduped[0].doi == "10.1234/abc-1"
    assert deduped[0].title == "Título Original"
    assert deduped[0].year == 2023
    assert deduped[0].source_ids == {"openalex": "W1", "crossref": "CR1"}
    assert deduped[0].citations == {"openalex": 11, "crossref": 14}

    assert deduped[1].doi is None
    assert deduped[1].title == "Revisão Sistemática: Árvores de Decisão!"
    assert deduped[1].source_ids == {"openalex": "W2", "semantic_scholar": "S2"}
    assert deduped[1].citations == {"openalex": 4, "semantic_scholar": 8}

    assert deduped[2].doi == "10.1234/first"
    assert deduped[3].doi == "10.1234/second"

    store = Store(tmp_path / "data")
    src = FakeSource(
        results=SourceResult(
            name="openalex",
            status="ok",
            query="search=dedup",
            found=6,
            fetched=6,
            works=[w_doi_1, w_doi_2, w_title_1, w_title_2, w_diff_doi_1, w_diff_doi_2],
        )
    )
    res = await run_search(store, [src], query="dedup")
    assert res["total"] == 4
    assert len(res["works"]) == 4


# FR-08: Fonte em failed marca lista como incomplete com motivo; zero resultados gera lista vazia
@pytest.mark.anyio
async def test_fr08_fonte_failed_marca_incompleta_e_zero_resultados_gera_lista_vazia(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "data")
    failed_src = FakeSource(
        results=SourceResult(
            name="openalex",
            status="failed",
            reason="HTTP 503 depois de 3 tentativas",
            query="search=falha · per_page=100 · páginas 1-1",
            found=None,
            fetched=0,
            works=[],
        )
    )

    res_fail = await run_search(
        store,
        [failed_src],
        query="falha",
        request_summary="Busca com falha na fonte",
    )
    assert res_fail["status"] == "incomplete"
    assert res_fail["total"] == 0
    assert res_fail["works"] == []
    assert res_fail["sources"][0]["name"] == "openalex"
    assert res_fail["sources"][0]["status"] == "failed"
    assert res_fail["sources"][0]["reason"] == "HTTP 503 depois de 3 tentativas"
    assert store.get_list("l-0001")["status"] == "incomplete"

    log_text = store.read_log()
    assert "Lista: l-0001 · incompleta · 0 artigos" in log_text
    assert "- openalex · failed · HTTP 503 depois de 3 tentativas" in log_text

    # Zero resultados com status ok gera lista complete e vazia; corte por max_results também é complete
    empty_src = FakeSource(
        results=SourceResult(
            name="openalex",
            status="ok",
            query="search=vazio · per_page=10 · páginas 1-1",
            found=0,
            fetched=0,
            works=[],
        )
    )
    res_empty = await run_search(store, [empty_src], query="vazio", max_results=10)
    assert res_empty["list_id"] == "l-0002"
    assert res_empty["status"] == "complete"
    assert res_empty["total"] == 0
    assert res_empty["works"] == []
    assert "Lista: l-0002 · completa · 0 artigos" in store.read_log()

    cut_src = FakeSource(
        results=SourceResult(
            name="openalex",
            status="ok",
            query="search=corte · per_page=1 · páginas 1-1",
            found=500,
            fetched=1,
            works=[_sample_work()],
        )
    )
    res_cut = await run_search(store, [cut_src], query="corte", max_results=1)
    assert res_cut["status"] == "complete"
    assert res_cut["sources"][0]["found"] == 500
    assert res_cut["sources"][0]["fetched"] == 1


# D-002, FR-08: Todas as fontes em missing_key devolvem no_source_available sem gravar nada
@pytest.mark.anyio
async def test_d002_fr08_todas_fontes_missing_key_levanta_no_source_available_sem_gravar(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "data")
    missing_src = FakeSource(
        results=SourceResult(
            name="openalex",
            status="missing_key",
            reason="variável OPENALEX_API_KEY não configurada",
            query="search=ml · per_page=100 · páginas 1-1",
            found=None,
            fetched=0,
            works=[],
        )
    )

    with pytest.raises(RSLError) as exc_info:
        await run_search(store, [missing_src], query="ml")

    assert exc_info.value.code == "no_source_available"
    assert not store.lists_dir.exists() or list(store.lists_dir.iterdir()) == []
    assert not store.searches_dir.exists() or list(store.searches_dir.iterdir()) == []
    assert not store.log_path.exists()
    assert not store.cache_dir.exists()

    # Se apenas uma fonte está em missing_key e outra responde ok, grava como incomplete
    ok_src = FakeSource(
        name="crossref",
        needs_key=False,
        results=SourceResult(
            name="crossref",
            status="ok",
            query="query=ml",
            found=1,
            fetched=1,
            works=[_sample_work()],
        ),
    )
    res = await run_search(store, [missing_src, ok_src], query="ml")
    assert res["status"] == "incomplete"
    assert res["total"] == 1


# NFR-06: Segunda busca igual vem do cache sem chamar a fonte; resultado failed não vai para o cache
@pytest.mark.anyio
async def test_nfr06_segunda_busca_vem_do_cache_e_failed_nao_entra_no_cache(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "data", cache_days=7)
    src = FakeSource(
        results=SourceResult(
            name="openalex",
            status="ok",
            query="search=cache test · per_page=100 · páginas 1-1",
            found=1,
            fetched=1,
            works=[_sample_work()],
        )
    )

    res1 = await run_search(store, [src], query="cache test", max_results=50)
    assert src.calls == [("cache test", 50)]
    assert res1["sources"][0]["from_cache"] is False
    assert res1["sources"][0]["fetched_at"] is None

    res2 = await run_search(store, [src], query="cache test", max_results=50)
    assert src.calls == [("cache test", 50)]
    assert res2["search_id"] == "s-0002"
    assert res2["list_id"] == "l-0002"
    assert res2["sources"][0]["from_cache"] is True
    assert isinstance(res2["sources"][0]["fetched_at"], str)
    assert res2["sources"][0]["fetched_at"].endswith("Z")

    # Mudar max_results altera cache_query e deve consultar a fonte novamente
    await run_search(store, [src], query="cache test", max_results=20)
    assert src.calls == [("cache test", 50), ("cache test", 20)]

    log_text = store.read_log()
    assert "cache: sim, obtida em " in log_text

    # Resultado failed não deve ser gravado no cache
    flaky_src = FakeSource(
        results=[
            SourceResult(
                name="openalex",
                status="failed",
                reason="erro de rede depois de 3 tentativas",
                query="search=flaky",
                found=None,
                fetched=0,
                works=[],
            ),
            SourceResult(
                name="openalex",
                status="ok",
                query="search=flaky",
                found=1,
                fetched=1,
                works=[_sample_work()],
            ),
        ]
    )
    res_fail = await run_search(store, [flaky_src], query="flaky")
    assert res_fail["status"] == "incomplete"
    assert len(flaky_src.calls) == 1

    res_retry = await run_search(store, [flaky_src], query="flaky")
    assert len(flaky_src.calls) == 2
    assert res_retry["status"] == "complete"
    assert res_retry["sources"][0]["from_cache"] is False


# FR-12, D-002: Resposta traz resumo de no máximo 25 artigos; registro completo fica na lista salva
@pytest.mark.anyio
async def test_fr12_d002_resumo_ate_25_artigos_na_resposta_e_registro_completo_na_lista_salva(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "data")
    works_25 = [
        _sample_work(title=f"Artigo {i}", doi=f"10.1234/w.{i}", oa_id=f"W{i}", cited=i)
        for i in range(1, 26)
    ]
    src_25 = FakeSource(
        results=SourceResult(
            name="openalex", status="ok", query="q=25", found=25, fetched=25, works=works_25
        )
    )
    res_25 = await run_search(store, [src_25], query="vinte e cinco")
    assert res_25["total"] == 25
    assert len(res_25["works"]) == 25
    assert res_25["page"] == 1
    assert res_25["next_page"] is None

    works_30 = [
        _sample_work(title=f"Artigo {i}", doi=f"10.1234/w30.{i}", oa_id=f"W{i}", cited=i)
        for i in range(1, 31)
    ]
    src_30 = FakeSource(
        results=SourceResult(
            name="openalex", status="ok", query="q=30", found=30, fetched=30, works=works_30
        )
    )
    res_30 = await run_search(store, [src_30], query="trinta")
    assert res_30["total"] == 30
    assert len(res_30["works"]) == 25
    assert res_30["page"] == 1
    assert res_30["next_page"] == 2

    summary_item = res_30["works"][0]
    assert set(summary_item.keys()) == {
        "doi",
        "title",
        "authors",
        "year",
        "venue",
        "references_count",
        "citations",
    }
    assert summary_item["authors"] == ["Maria Silva", "João Souza"]
    assert summary_item["references_count"] == 2
    assert summary_item["citations"] == {"openalex": 1}

    saved_list = store.get_list(res_30["list_id"])
    assert len(saved_list["works"]) == 30
    full_item = saved_list["works"][0]
    assert full_item["abstract"] == "Resumo completo do trabalho sobre interpretabilidade."
    assert full_item["keywords"] == ["machine learning", "xai"]
    assert full_item["references"] == ["W200", "W300"]
    assert full_item["source_ids"] == {"openalex": "W1"}
    assert full_item["authors"][0]["orcid"] == "0000-0002-1825-0097"
    assert full_item["authors"][0]["affiliations"][0]["ids"]["ror"] == "https://ror.org/036rp1748"


# FR-09: Cada busca gera uma lista própria; duas buscas seguidas não se juntam
@pytest.mark.anyio
async def test_fr09_duas_buscas_seguidas_geram_listas_separadas(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    src1 = FakeSource(
        results=SourceResult(
            name="openalex",
            status="ok",
            query="search=tema1",
            found=1,
            fetched=1,
            works=[_sample_work(title="Apenas Tema 1", doi="10.1234/t1")],
        )
    )
    src2 = FakeSource(
        results=SourceResult(
            name="openalex",
            status="ok",
            query="search=tema2",
            found=1,
            fetched=1,
            works=[_sample_work(title="Apenas Tema 2", doi="10.1234/t2")],
        )
    )

    r1 = await run_search(store, [src1], query="tema1")
    r2 = await run_search(store, [src2], query="tema2")

    assert r1["list_id"] == "l-0001"
    assert r2["list_id"] == "l-0002"
    assert r1["search_id"] == "s-0001"
    assert r2["search_id"] == "s-0002"
    assert [w["doi"] for w in store.get_list("l-0001")["works"]] == ["10.1234/t1"]
    assert [w["doi"] for w in store.get_list("l-0002")["works"]] == ["10.1234/t2"]
