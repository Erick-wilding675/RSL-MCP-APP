"""Testes unitários do miolo de repetição de busca salva (repeat_search)."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from rslapp.core.errors import RSLError
from rslapp.core.find import run_find
from rslapp.core.models import Author, OriginWorkResult, SourceResult, Work
from rslapp.core.related import run_related
from rslapp.core.repeat import run_repeat
from rslapp.core.search import run_search
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
        status: str = "ok",
        reason: str | None = None,
        works: list[Work] | None = None,
    ) -> None:
        self.name = name
        self.status = status
        self.reason = reason
        self.works = works if works is not None else []
        self.search_calls: list[tuple[str, int]] = []
        self.doi_calls: list[str] = []

    def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
        return {"query": query, "max_results": max_results}

    async def search(self, query: str, max_results: int) -> SourceResult:
        self.search_calls.append((query, max_results))
        return SourceResult(
            name=self.name,
            status=self.status,
            reason=self.reason,
            query=f"query={query}",
            found=len(self.works),
            fetched=len(self.works),
            works=list(self.works),
        )

    async def find_by_doi(self, doi: str) -> SourceResult:
        self.doi_calls.append(doi)
        return SourceResult(
            name=self.name,
            status=self.status,
            reason=self.reason,
            query=f"doi:{doi}",
            found=len(self.works),
            fetched=len(self.works),
            works=list(self.works),
        )


# FR-11, D-002: Busca inexistente levanta search_not_found
@pytest.mark.anyio
async def test_fr11_d002_repeat_search_not_found(store: Store) -> None:
    src = FakeSource()
    with pytest.raises(RSLError) as exc:
        await run_repeat(store, [src], search_id="s-9999")
    assert exc.value.code == "search_not_found"
    assert "s-9999 não encontrada" in exc.value.message


# FR-11, D-002: search_id malformado ('s-1', '../x', etc.) levanta search_not_found
@pytest.mark.anyio
@pytest.mark.parametrize("malformed_id", ["s-1", "../x", "s-01", "s-99999", "invalid", "s-", "l-0001"])
async def test_fr11_d002_repeat_search_malformed_id_gives_search_not_found(store: Store, malformed_id: str) -> None:
    src = FakeSource()
    with pytest.raises(RSLError) as exc:
        await run_repeat(store, [src], search_id=malformed_id)
    assert exc.value.code == "search_not_found"
    assert f"busca {malformed_id} não encontrada" in exc.value.message


# FR-11, D-002: search_id vazio levanta invalid_input
@pytest.mark.anyio
@pytest.mark.parametrize("invalid_id", ["", "   "])
async def test_fr11_d002_repeat_search_empty_id(store: Store, invalid_id: str) -> None:
    src = FakeSource()
    with pytest.raises(RSLError) as exc:
        await run_repeat(store, [src], search_id=invalid_id)
    assert exc.value.code == "invalid_input"
    assert "search_id não pode ser vazio" in exc.value.message


# FR-11: Busca legada sem params levanta invalid_input com mensagem especificada
@pytest.mark.anyio
async def test_fr11_repeat_search_missing_params(store: Store) -> None:
    search_data: dict[str, Any] = {
        "kind": "terms",
        "request_summary": "busca antiga",
        "sources": [{"name": "fake", "status": "ok", "query": "antiga"}],
    }
    list_data: dict[str, Any] = {
        "status": "complete",
        "total": 0,
        "works": [],
    }
    saved_search, _ = store.record_search(search_data, list_data)

    src = FakeSource()
    with pytest.raises(RSLError) as exc:
        await run_repeat(store, [src], search_id=saved_search["id"])
    assert exc.value.code == "invalid_input"
    assert "busca sem parâmetros gravados" in exc.value.message


# FR-11, UC-03: repeat_search gera s- e l- novos, com repeated_from apontando para a original
@pytest.mark.anyio
async def test_fr11_uc03_repeat_search_creates_new_records(store: Store) -> None:
    w1 = Work(title="Machine Learning 1", doi="10.1234/ml1", year=2023, authors=[Author(name="Autor A")])
    src1 = FakeSource("source_a", works=[w1])
    src2 = FakeSource("source_b", works=[])

    # 1. Executa busca original
    orig_res = await run_search(
        store,
        [src1, src2],
        query="machine learning",
        request_summary="Pesquisa sobre ML",
        max_results=50,
        source_names=["source_a", "source_b"],
    )
    orig_search_id = orig_res["search_id"]
    orig_list_id = orig_res["list_id"]

    orig_search_content = store.get_search(orig_search_id)
    orig_list_content = store.get_list(orig_list_id)
    assert orig_list_content["status"] == "complete"

    # Limpa cache para garantir que a repetição chame as fontes de fato
    import shutil
    if store.cache_dir.exists():
        shutil.rmtree(store.cache_dir)

    # 2. Executa repeat_search
    repeat_res = await run_repeat(store, [src1, src2], search_id=orig_search_id)

    # Confere retorno da repetição
    assert repeat_res["search_id"] != orig_search_id
    assert repeat_res["list_id"] != orig_list_id
    assert repeat_res["repeated_from"] == orig_search_id
    assert repeat_res["status"] == "complete"
    assert repeat_res["total"] == 1

    # Confere gravação da busca repetida
    new_search = store.get_search(repeat_res["search_id"])
    assert new_search["kind"] == "repeat"
    assert new_search["repeated_from"] == orig_search_id
    assert new_search["params"] == orig_search_content["params"]
    assert new_search["request_summary"] == "Pesquisa sobre ML"

    new_list = store.get_list(repeat_res["list_id"])
    assert new_list["status"] == "complete"
    assert new_list["total"] == 1

    # Confere que cada fonte foi chamada com a mesma query e mesmo max_results da original
    assert src1.search_calls == [("machine learning", 50), ("machine learning", 50)]
    assert src2.search_calls == [("machine learning", 50), ("machine learning", 50)]

    # Confere que sources[].query e sources[].name da busca original e repetida são idênticos
    assert len(new_search["sources"]) == len(orig_search_content["sources"])
    for s_orig, s_new in zip(orig_search_content["sources"], new_search["sources"]):
        assert s_orig["name"] == s_new["name"]
        assert s_orig["query"] == s_new["query"]
        assert s_orig["status"] == s_new["status"]

    # Confere log legível
    log_content = store.read_log()
    assert f"Repetida de: {orig_search_id}" in log_content


# FR-11: A busca original e a lista original continuam idênticas depois da repetição
@pytest.mark.anyio
async def test_fr11_original_search_and_list_remain_identical(store: Store) -> None:
    w1 = Work(title="Data Science", doi="10.1234/ds", year=2024, authors=[Author(name="Autor B")])
    src = FakeSource("source_a", works=[w1])

    orig_res = await run_search(store, [src], query="data science", request_summary="Resumo original")
    orig_s_before = copy.deepcopy(store.get_search(orig_res["search_id"]))
    orig_l_before = copy.deepcopy(store.get_list(orig_res["list_id"]))

    # Roda repetição
    await run_repeat(store, [src], search_id=orig_res["search_id"])

    orig_s_after = store.get_search(orig_res["search_id"])
    orig_l_after = store.get_list(orig_res["list_id"])

    assert orig_s_before == orig_s_after
    assert orig_l_before == orig_l_after


# FR-08, FR-11: Se uma fonte usada antes está sem chave, a repetição segue com as outras e marca a falha
@pytest.mark.anyio
async def test_fr08_fr11_repeat_search_missing_key_source_proceeds(store: Store) -> None:
    w1 = Work(title="Paper Alpha", doi="10.1234/alpha", year=2024, authors=[Author(name="Alpha")])
    w2 = Work(title="Paper Beta", doi="10.1234/beta", year=2024, authors=[Author(name="Beta")])

    src_oa = FakeSource("openalex", status="ok", works=[w1])
    src_cr = FakeSource("crossref", status="ok", works=[w2])

    orig_res = await run_search(
        store,
        [src_oa, src_cr],
        query="alpha beta",
        source_names=["openalex", "crossref"],
    )
    assert orig_res["status"] == "complete"

    # Agora a OpenAlex fica sem chave (missing_key) e o cache expirou
    import shutil
    if store.cache_dir.exists():
        shutil.rmtree(store.cache_dir)

    src_oa_no_key = FakeSource("openalex", status="missing_key", reason="OPENALEX_API_KEY não configurada", works=[])

    repeat_res = await run_repeat(store, [src_oa_no_key, src_cr], search_id=orig_res["search_id"])

    # Repetição segue com a Crossref e marca status incomplete
    assert repeat_res["status"] == "incomplete"
    assert repeat_res["total"] == 1
    assert repeat_res["works"][0]["doi"] == "10.1234/beta"

    source_statuses = {s["name"]: s["status"] for s in repeat_res["sources"]}
    assert source_statuses["openalex"] == "missing_key"
    assert source_statuses["crossref"] == "ok"


# FR-11, UC-03: Repetição de busca de artigo (kind: "work") por DOI
@pytest.mark.anyio
async def test_fr11_repeat_find_work_by_doi(store: Store) -> None:
    w = Work(title="Artigo Alvo", doi="10.1234/alvo.1", year=2023, authors=[Author(name="Alvo")])
    src = FakeSource("openalex", works=[w])

    orig_find = await run_find(store, [src], doi="10.1234/alvo.1", request_summary="Encontrar alvo")
    assert orig_find["status"] == "complete"

    repeat_res = await run_repeat(store, [src], search_id=orig_find["search_id"])
    assert repeat_res["repeated_from"] == orig_find["search_id"]
    assert repeat_res["status"] == "complete"
    assert repeat_res["total"] == 1
    assert repeat_res["works"][0]["title"] == "Artigo Alvo"

    new_search = store.get_search(repeat_res["search_id"])
    assert new_search["kind"] == "repeat"
    assert new_search["params"]["doi"] == "10.1234/alvo.1"


# FR-11, UC-03: Repetição de busca de artigo (kind: "work") por título
@pytest.mark.anyio
async def test_fr11_repeat_find_work_by_title(store: Store) -> None:
    w = Work(title="Deep Learning Survey", doi="10.1234/dl", year=2023, authors=[Author(name="DL")])
    src = FakeSource("openalex", works=[w])

    orig_find = await run_find(store, [src], title="Deep Learning Survey", max_results=5)
    repeat_res = await run_repeat(store, [src], search_id=orig_find["search_id"])

    assert repeat_res["repeated_from"] == orig_find["search_id"]
    assert repeat_res["total"] == 1

    new_search = store.get_search(repeat_res["search_id"])
    assert new_search["kind"] == "repeat"
    assert new_search["params"]["title"] == "Deep Learning Survey"


class FakeRelatedSource:
    """Fonte simulada para buscas de relacionados."""

    def __init__(
        self,
        name: str,
        result: SourceResult,
    ) -> None:
        self.name = name
        self.needs_key = True
        self._result = result
        self.related_calls: list[tuple[str, str, int]] = []
        self.origin_calls: list[str] = []

    def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
        return {"query": query, "max_results": max_results}

    async def get_origin_work(
        self, doi_or_id: str
    ) -> OriginWorkResult:
        self.origin_calls.append(doi_or_id)
        return OriginWorkResult(
            data={"id": "W1", "doi": "10.1234/test", "referenced_works": []},
            status=None,
            reason=None,
            not_found=False,
        )

    async def related(
        self,
        doi_or_id: str,
        direction: str,
        max_results: int = 1000,
        origin_data: dict[str, Any] | None = None,
    ) -> SourceResult:
        self.related_calls.append((doi_or_id, direction, max_results))
        return self._result


# FR-11, UC-03: Repetição de busca 'related' copia origin da original e repete chamadas às fontes
@pytest.mark.anyio
async def test_fr11_repeat_related_search_copies_origin(store: Store, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
    w1 = Work(title="Ref 1", doi="10.1234/ref1", year=2021, authors=[Author(name="Autor R")])
    src_res = SourceResult(
        name="openalex",
        status="ok",
        reason=None,
        query="related=10.1234/test · direction=references",
        found=1,
        fetched=1,
        works=[w1],
    )
    src = FakeRelatedSource("openalex", src_res)

    orig_res = await run_related(
        store,
        [src],
        direction="references",
        doi="10.1234/test",
        request_summary="Referências do artigo teste",
        max_results=50,
        source_names=["openalex"],
    )
    orig_search_id = orig_res["search_id"]
    orig_search = store.get_search(orig_search_id)
    assert orig_search["kind"] == "related"
    assert orig_search["origin"] is not None
    assert orig_search["origin"]["direction"] == "references"

    # Limpa cache para garantir chamada real à fonte na repetição
    import shutil
    if store.cache_dir.exists():
        shutil.rmtree(store.cache_dir)

    # Executa repetição
    repeat_res = await run_repeat(store, [src], search_id=orig_search_id)
    assert repeat_res["search_id"] != orig_search_id
    assert repeat_res["repeated_from"] == orig_search_id
    assert repeat_res["status"] == "complete"
    assert repeat_res["total"] == 1

    new_search = store.get_search(repeat_res["search_id"])
    assert new_search["kind"] == "repeat"
    assert new_search["repeated_from"] == orig_search_id
    # origin deve ser copiado identicamente da busca original
    assert new_search["origin"] == orig_search["origin"]
    assert new_search["params"] == orig_search["params"]
    assert new_search["request_summary"] == orig_search["request_summary"]

    # Prova que chamou a fonte com os mesmos argumentos da original
    assert src.origin_calls == ["10.1234/test", "10.1234/test"]
    assert src.related_calls == [
        ("W1", "references", 50),
        ("W1", "references", 50),
    ]

    # Compara sources[].query entre a original e a repetida
    assert len(new_search["sources"]) == len(orig_search["sources"])
    for s_orig, s_new in zip(orig_search["sources"], new_search["sources"]):
        assert s_orig["name"] == s_new["name"]
        assert s_orig["query"] == s_new["query"]
