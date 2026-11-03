"""Testes unitários do miolo de busca de artigo específico (find_work)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from rslapp.core.errors import RSLError
from rslapp.core.find import run_find
from rslapp.core.models import Author, SourceResult, Work
from rslapp.store import Store


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path)


class FakeSource:
    name: str = "fake_source"
    needs_key: bool = False

    def __init__(
        self,
        name: str = "fake_source",
        *,
        doi_result: SourceResult | None = None,
        search_result: SourceResult | None = None,
        status: str = "ok",
    ) -> None:
        self.name = name
        self._doi_result = doi_result
        self._search_result = search_result
        self._status = status
        self.doi_calls: list[str] = []
        self.search_calls: list[tuple[str, int]] = []

    def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
        return {"query": query, "max_results": max_results}

    async def search(self, query: str, max_results: int) -> SourceResult:
        self.search_calls.append((query, max_results))
        if self._search_result is not None:
            return self._search_result
        return SourceResult(
            name=self.name,
            status=self._status,
            reason=None if self._status == "ok" else "falha",
            query=f"query={query}",
            found=0,
            fetched=0,
            works=[],
        )

    async def find_by_doi(self, doi: str) -> SourceResult:
        self.doi_calls.append(doi)
        if self._doi_result is not None:
            return self._doi_result
        return SourceResult(
            name=self.name,
            status=self._status,
            reason=None if self._status == "ok" else "falha",
            query=f"doi:{doi}",
            found=0,
            fetched=0,
            works=[],
        )


# FR-02, D-002: Exatamente um entre title ou doi, senão invalid_input
@pytest.mark.anyio
@pytest.mark.parametrize(
    ("title", "doi"),
    [
        (None, None),
        ("Titulo", "10.1234/exemplo"),
    ],
)
async def test_fr02_d002_find_work_title_or_doi_exclusive(store: Store, title: str | None, doi: str | None) -> None:
    src = FakeSource()
    with pytest.raises(RSLError) as exc:
        await run_find(store, [src], title=title, doi=doi)
    assert exc.value.code == "invalid_input"
    assert "exatamente um entre title ou doi" in exc.value.message


# FR-02, D-002: Validação estrita de DOI
@pytest.mark.anyio
@pytest.mark.parametrize(
    "invalid_doi",
    [
        "",
        "   ",
        "not-a-doi",
        "11.1234/test",
        "10.1234/test with space",
        "10.1234/test?query=1",
        "10.1234/test#frag",
        "10.1234/test%20frag",
        "10.1234/./test",
        "10.1234/../test",
    ],
)
async def test_fr02_d002_find_work_invalid_doi(store: Store, invalid_doi: str) -> None:
    src = FakeSource()
    with pytest.raises(RSLError) as exc:
        await run_find(store, [src], doi=invalid_doi)
    assert exc.value.code == "invalid_input"


# FR-02: DOIs válidos com parênteses, ponto e vírgula e chevron são aceitos
@pytest.mark.anyio
@pytest.mark.parametrize(
    "valid_doi",
    [
        "10.1000/182<3>;(4)",
        "10.1234/s12345-020-00123-x",
        "https://doi.org/10.5555/clean",
    ],
)
async def test_fr02_find_work_valid_special_chars_doi(store: Store, valid_doi: str) -> None:
    src = FakeSource()
    res = await run_find(store, [src], doi=valid_doi)
    assert res["status"] == "complete"
    assert len(src.doi_calls) == 1


# FR-02, D-002: Validação de título e max_results
@pytest.mark.anyio
@pytest.mark.parametrize(
    ("kwargs", "expected_err"),
    [
        ({"title": ""}, "title não pode ser vazio"),
        ({"title": "   "}, "title não pode ser vazio"),
        ({"title": "ok", "max_results": 0}, "max_results deve ser um inteiro"),
        ({"title": "ok", "max_results": 101}, "max_results deve ser um inteiro"),
        ({"title": "ok", "max_results": True}, "max_results deve ser um inteiro"),
        ({"title": "ok", "request_summary": 123}, "request_summary deve ser texto"),
    ],
)
async def test_fr02_d002_find_work_validation_errors(store: Store, kwargs: dict[str, Any], expected_err: str) -> None:
    src = FakeSource()
    with pytest.raises(RSLError) as exc:
        await run_find(store, [src], **kwargs)
    assert exc.value.code == "invalid_input"
    assert expected_err in exc.value.message


# FR-02, UC-02, D-002: Busca por DOI exato devolve artigo e grava kind: "work" com params
@pytest.mark.anyio
async def test_fr02_uc02_find_work_by_doi_exact(store: Store) -> None:
    w = Work(
        title="Estudo de Caso",
        doi="10.1234/estudo.1",
        year=2023,
        authors=[Author(name="Maria Santos")],
        venue="Revista X",
    )
    src_oa = FakeSource(
        name="openalex",
        doi_result=SourceResult("openalex", "ok", None, "doi:10.1234/estudo.1", 1, 1, [w]),
    )
    src_cr = FakeSource(
        name="crossref",
        doi_result=SourceResult("crossref", "ok", None, "doi:10.1234/estudo.1", 0, 0, []),
    )

    res = await run_find(
        store,
        [src_oa, src_cr],
        doi="10.1234/estudo.1",
        request_summary="Achar artigo Maria",
    )

    assert res["status"] == "complete"
    assert res["total"] == 1
    assert len(res["works"]) == 1
    assert res["works"][0]["title"] == "Estudo de Caso"
    assert res["works"][0]["doi"] == "10.1234/estudo.1"

    # Confere gravação em store
    saved_search = store.get_search(res["search_id"])
    assert saved_search["kind"] == "work"
    assert saved_search["repeated_from"] is None
    assert saved_search["params"]["doi"] == "10.1234/estudo.1"
    assert saved_search["params"]["max_results"] == 10
    assert saved_search["params"]["sources"] == ["openalex", "crossref"]

    saved_list = store.get_list(res["list_id"])
    assert saved_list["status"] == "complete"
    assert saved_list["total"] == 1


# FR-02, D-002: Sem resultado devolve lista vazia registrada (não levanta work_not_found)
@pytest.mark.anyio
async def test_fr02_d002_find_work_by_doi_not_found_records_empty_list(store: Store) -> None:
    src_oa = FakeSource(
        name="openalex",
        doi_result=SourceResult("openalex", "ok", None, "doi:10.1234/inexistente", 0, 0, []),
    )
    src_cr = FakeSource(
        name="crossref",
        doi_result=SourceResult("crossref", "ok", None, "doi:10.1234/inexistente", 0, 0, []),
    )

    res = await run_find(store, [src_oa, src_cr], doi="10.1234/inexistente")

    assert res["status"] == "complete"
    assert res["total"] == 0
    assert res["works"] == []

    # Lista e busca salvas com lista vazia
    saved_list = store.get_list(res["list_id"])
    assert saved_list["status"] == "complete"
    assert saved_list["total"] == 0
    assert saved_list["works"] == []


# FR-02, UC-02: Busca por título parecido devolve candidatos deduplicados
@pytest.mark.anyio
async def test_fr02_uc02_find_work_by_title_candidates(store: Store) -> None:
    w1 = Work(
        title="Machine Learning in Health",
        doi="10.1234/ml.1",
        year=2022,
        authors=[Author(name="Ana")],
    )
    w2 = Work(
        title="Machine Learning in Health Care",
        doi="10.1234/ml.2",
        year=2023,
        authors=[Author(name="Beto")],
    )
    w1_dup = Work(
        title="Machine Learning in Health",
        doi="10.1234/ml.1",
        year=2022,
        authors=[Author(name="Ana")],
    )

    src_oa = FakeSource(
        name="openalex",
        search_result=SourceResult("openalex", "ok", None, "search", 2, 2, [w1, w2]),
    )
    src_cr = FakeSource(
        name="crossref",
        search_result=SourceResult("crossref", "ok", None, "search", 1, 1, [w1_dup]),
    )

    res = await run_find(
        store,
        [src_oa, src_cr],
        title="Machine Learning in Health",
        max_results=5,
    )

    assert res["status"] == "complete"
    assert res["total"] == 2  # deduplicou w1 e w1_dup
    assert len(res["works"]) == 2

    saved_search = store.get_search(res["search_id"])
    assert saved_search["kind"] == "work"
    assert saved_search["params"]["title"] == "Machine Learning in Health"
    assert saved_search["params"]["max_results"] == 5


# FR-08: Falha de uma fonte marca status incomplete
@pytest.mark.anyio
async def test_fr08_find_work_source_failure_incomplete(store: Store) -> None:
    w1 = Work(title="Artigo Único", doi="10.1234/u1", year=2024, authors=[Author(name="Ana")])
    src_ok = FakeSource(
        name="openalex",
        doi_result=SourceResult("openalex", "ok", None, "doi:10.1234/u1", 1, 1, [w1]),
    )
    src_fail = FakeSource(
        name="crossref",
        doi_result=SourceResult("crossref", "failed", "HTTP 500", "doi:10.1234/u1", None, 0, []),
    )

    res = await run_find(store, [src_ok, src_fail], doi="10.1234/u1")
    assert res["status"] == "incomplete"
    assert res["total"] == 1

    saved_list = store.get_list(res["list_id"])
    assert saved_list["status"] == "incomplete"


# D-002: Todas as fontes com missing_key levantam no_source_available sem salvar nada
@pytest.mark.anyio
async def test_d002_find_work_all_missing_key(store: Store) -> None:
    src1 = FakeSource(
        name="openalex",
        status="missing_key",
        doi_result=SourceResult("openalex", "missing_key", "sem chave", "doi:10.1234/x", None, 0, []),
    )
    src2 = FakeSource(
        name="crossref",
        status="missing_key",
        doi_result=SourceResult("crossref", "missing_key", "sem chave", "doi:10.1234/x", None, 0, []),
    )

    with pytest.raises(RSLError) as exc:
        await run_find(store, [src1, src2], doi="10.1234/x")
    assert exc.value.code == "no_source_available"
    assert len(store.list_searches()) == 0


# NFR-06: Busca por título consulta e grava cache
@pytest.mark.anyio
async def test_nfr06_find_work_title_uses_cache(store: Store) -> None:
    w = Work(title="Cache Paper", doi="10.1234/cp.1", year=2024, authors=[Author(name="Caio")])
    src = FakeSource(
        name="openalex",
        search_result=SourceResult("openalex", "ok", None, "query=Cache Paper", 1, 1, [w]),
    )

    res1 = await run_find(store, [src], title="Cache Paper")
    assert res1["sources"][0]["from_cache"] is False
    assert len(src.search_calls) == 1

    # Segunda chamada deve vir do cache
    res2 = await run_find(store, [src], title="Cache Paper")
    assert res2["sources"][0]["from_cache"] is True
    assert len(src.search_calls) == 1
