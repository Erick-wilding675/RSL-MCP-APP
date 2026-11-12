"""Testes de exclusão de pareceres de revisão por pares e parâmetro include_peer_review (D-022)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from mcp import Client

from rslapp import server
from rslapp.core.errors import RSLError
from rslapp.core.models import Affiliation, Author, SourceResult, Work
from rslapp.core.repeat import run_repeat
from rslapp.core.search import run_search
from rslapp.prompts import render_plan_search
from rslapp.sources.openalex import OpenAlexSource
from rslapp.store import Store

ENV_VARS = (
    "RSL_DATA_DIR",
    "RSL_EXPORT_DIR",
    "RSL_CACHE_DAYS",
    "OPENALEX_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "RSL_CONTACT_EMAIL",
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Isola variáveis de ambiente e configura RSL_DATA_DIR em pasta temporária."""
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    data_dir = tmp_path / "rsl_data"
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("OPENALEX_API_KEY", "fake-key-123")
    return data_dir


def _make_work(title: str, doi: str, work_type: str = "article") -> Work:
    return Work(
        title=title,
        doi=doi,
        year=2024,
        type=work_type,
        venue="Revista de Teste",
        abstract="Resumo de teste",
        keywords=["teste"],
        authors=[Author(name="Autor Teste", affiliations=[Affiliation(name="Inst", country_code="BR")])],
        references=[],
        references_count=0,
        citations={},
        source_ids={"mock": doi},
    )


class FakeMockSource:
    """Fonte simulada para testar exclusão de pareceres pós-busca."""

    def __init__(self, name: str = "crossref", works: list[Work] | None = None) -> None:
        self.name = name
        self.needs_key = False
        self.works = list(works or [])
        self.last_query: str | None = None
        self.last_max: int | None = None

    def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
        return {"query": query, "max": max_results}

    async def search(self, query: str, max_results: int) -> SourceResult:
        self.last_query = query
        self.last_max = max_results
        return SourceResult(
            name=self.name,
            status="ok",
            query=f"query={query} · rows={max_results}",
            found=len(self.works),
            fetched=len(self.works),
            works=list(self.works),
        )


# D-022, FR-01: A busca no OpenAlex manda filter=type:!peer-review por padrão e não manda com include_peer_review=true
@pytest.mark.anyio
async def test_d022_openalex_manda_filtro_peer_review_por_padrao_e_omite_com_true() -> None:
    seen_params: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_params.append(dict(request.url.params))
        item = {
            "id": "https://openalex.org/W100",
            "doi": "https://doi.org/10.1234/teste.1",
            "display_name": "Artigo Normal",
            "publication_year": 2024,
            "type": "article",
            "primary_location": {"source": {"display_name": "Journal"}},
            "authorships": [],
            "abstract_inverted_index": None,
            "keywords": [],
            "referenced_works": [],
            "referenced_works_count": 0,
            "cited_by_count": 0,
        }
        return httpx.Response(200, json={"meta": {"count": 1}, "results": [item]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source = OpenAlexSource(client=client)

        # 1. Padrão (include_peer_review=False): deve conter type:!peer-review
        res_default = await source.search("diabetes", max_results=10)
        assert seen_params[0].get("filter") == "type:!peer-review"
        assert "filter=type:!peer-review" in res_default.query

        # 2. Com include_peer_review=True: não deve conter o filtro
        res_included = await source.search("diabetes", max_results=10, include_peer_review=True)
        assert "filter" not in seen_params[1]
        assert "filter=" not in res_included.query

        # 3. Com filtro preexistente e include_peer_review=False: junta com vírgula
        res_combined = await source.search("diabetes", max_results=10, filter="has_doi:true")
        assert seen_params[2].get("filter") == "has_doi:true,type:!peer-review"
        assert "filter=has_doi:true,type:!peer-review" in res_combined.query


# D-022, FR-01, FR-12: Fonte falsa devolvendo peer-review e article grava só article com excluded_peer_review: 1
@pytest.mark.anyio
async def test_d022_outra_fonte_exclui_peer_review_e_registra_quantidade(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    w_article = _make_work("Estudo Clínico A", "10.1000/art.1", work_type="article")
    w_review = _make_work("Review for Journal X", "10.1000/rev.1", work_type="peer-review")
    fake_source = FakeMockSource("crossref", works=[w_article, w_review])

    res = await run_search(
        store,
        [fake_source],
        query="clínico",
        include_peer_review=False,
    )

    # Apenas o article é mantido
    assert res["total"] == 1
    assert len(res["works"]) == 1
    assert res["works"][0]["doi"] == "10.1000/art.1"

    # Entrada da fonte ganha excluded_peer_review: 1
    src_entry = res["sources"][0]
    assert src_entry["name"] == "crossref"
    assert src_entry["excluded_peer_review"] == 1

    # Confere na lista salva em disco
    saved_list = store.get_list(res["list_id"])
    assert saved_list["total"] == 1
    assert saved_list["works"][0]["doi"] == "10.1000/art.1"

    # Confere nos parâmetros gravados da busca
    saved_search = store.get_search(res["search_id"])
    assert saved_search["params"]["include_peer_review"] is False
    assert saved_search["sources"][0]["excluded_peer_review"] == 1


# D-022, FR-01: include_peer_review=true mantém os dois registros
@pytest.mark.anyio
async def test_d022_include_peer_review_true_mantem_ambos(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    w_article = _make_work("Estudo Clínico A", "10.1000/art.1", work_type="article")
    w_review = _make_work("Review for Journal X", "10.1000/rev.1", work_type="peer-review")
    fake_source = FakeMockSource("crossref", works=[w_article, w_review])

    res = await run_search(
        store,
        [fake_source],
        query="clínico",
        include_peer_review=True,
    )

    assert res["total"] == 2
    assert len(res["works"]) == 2
    dois = {w["doi"] for w in res["works"]}
    assert dois == {"10.1000/art.1", "10.1000/rev.1"}

    # Nenhuma exclusão registrada
    src_entry = res["sources"][0]
    assert "excluded_peer_review" not in src_entry

    saved_search = store.get_search(res["search_id"])
    assert saved_search["params"]["include_peer_review"] is True
    assert "excluded_peer_review" not in saved_search["sources"][0]


# D-022, D-002: include_peer_review=1 responde invalid_input
@pytest.mark.anyio
@pytest.mark.parametrize("invalid_val", [1, 0, 1.0, 2])
async def test_d022_include_peer_review_numero_responde_invalid_input(
    isolated_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_val: Any,
) -> None:
    # 1. No miolo run_search
    store = Store(isolated_env)
    fake_source = FakeMockSource("crossref", works=[])
    with pytest.raises(RSLError) as exc_info:
        await run_search(
            store,
            [fake_source],
            query="termo",
            include_peer_review=invalid_val,
        )
    assert exc_info.value.code == "invalid_input"

    # 2. No servidor MCP
    def _fail_if_called(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("O miolo não deve ser chamado quando include_peer_review não for booleano")

    monkeypatch.setattr(server, "run_search", _fail_if_called)

    async with Client(server.mcp) as client:
        res = await client.call_tool(
            "search_works",
            {"query": "termo", "include_peer_review": invalid_val},
        )

    assert res.is_error is True
    assert res.content
    text = str(res.content[0].text)
    assert "invalid_input" in text
    assert "include_peer_review" in text


# D-022, FR-11: repeat_search de busca antiga sem o campo repete com false; com true repete com true
@pytest.mark.anyio
async def test_d022_repeat_search_busca_antiga_e_busca_com_true(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    w_art = _make_work("Artigo 1", "10.1000/1", work_type="article")
    w_rev = _make_work("Review 1", "10.1000/2", work_type="peer-review")

    # 1. Busca antiga sem o campo include_peer_review gravado em params
    old_search, _ = store.record_search(
        {
            "kind": "terms",
            "request_summary": "Busca legada",
            "params": {"query": "teste antigo", "max_results": 50, "sources": ["crossref"]},
            "sources": [{"name": "crossref", "status": "ok", "query": "q", "found": 2, "fetched": 2}],
        },
        {"status": "complete", "works": [w_art.to_dict(), w_rev.to_dict()]},
    )

    fake_source = FakeMockSource("crossref", works=[w_art, w_rev])
    res_repeat_old = await run_repeat(store, [fake_source], search_id=old_search["id"])

    # Repete com include_peer_review=False -> exclui o peer-review
    assert res_repeat_old["total"] == 1
    assert res_repeat_old["works"][0]["doi"] == "10.1000/1"
    new_search_old = store.get_search(res_repeat_old["search_id"])
    assert new_search_old["params"]["include_peer_review"] is False

    # 2. Busca recente com include_peer_review=True
    search_true, _ = store.record_search(
        {
            "kind": "terms",
            "request_summary": "Busca com true",
            "params": {
                "query": "teste recente",
                "max_results": 50,
                "sources": ["crossref"],
                "include_peer_review": True,
            },
            "sources": [{"name": "crossref", "status": "ok", "query": "q", "found": 2, "fetched": 2}],
        },
        {"status": "complete", "works": [w_art.to_dict(), w_rev.to_dict()]},
    )

    res_repeat_true = await run_repeat(store, [fake_source], search_id=search_true["id"])

    # Repete com include_peer_review=True -> mantém ambos
    assert res_repeat_true["total"] == 2
    new_search_true = store.get_search(res_repeat_true["search_id"])
    assert new_search_true["params"]["include_peer_review"] is True


# D-022, NFR-06: Cache do OpenAlex não confunde as duas buscas (com e sem include_peer_review)
@pytest.mark.anyio
async def test_d022_cache_openalex_nao_confunde_as_duas_buscas(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        filter_param = request.url.params.get("filter", "")
        # Se veio com filtro, devolve só 1 resultado; se sem filtro, devolve 2
        if "type:!peer-review" in filter_param:
            items = [
                {
                    "id": "https://openalex.org/W1",
                    "doi": "https://doi.org/10.1234/1",
                    "display_name": "Artigo Único",
                    "publication_year": 2024,
                    "type": "article",
                    "primary_location": {"source": {"display_name": "J"}},
                    "authorships": [],
                    "abstract_inverted_index": None,
                    "keywords": [],
                    "referenced_works": [],
                    "referenced_works_count": 0,
                    "cited_by_count": 0,
                }
            ]
        else:
            items = [
                {
                    "id": "https://openalex.org/W1",
                    "doi": "https://doi.org/10.1234/1",
                    "display_name": "Artigo Único",
                    "publication_year": 2024,
                    "type": "article",
                    "primary_location": {"source": {"display_name": "J"}},
                    "authorships": [],
                    "abstract_inverted_index": None,
                    "keywords": [],
                    "referenced_works": [],
                    "referenced_works_count": 0,
                    "cited_by_count": 0,
                },
                {
                    "id": "https://openalex.org/W2",
                    "doi": "https://doi.org/10.1234/2",
                    "display_name": "Review for J",
                    "publication_year": 2024,
                    "type": "peer-review",
                    "primary_location": {"source": {"display_name": "J"}},
                    "authorships": [],
                    "abstract_inverted_index": None,
                    "keywords": [],
                    "referenced_works": [],
                    "referenced_works_count": 0,
                    "cited_by_count": 0,
                },
            ]
        return httpx.Response(200, json={"meta": {"count": len(items)}, "results": items})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        oa = OpenAlexSource(client=client)

        # 1. Primeira busca: include_peer_review=False (padrão)
        res1 = await run_search(store, [oa], query="cache_test", include_peer_review=False)
        assert res1["total"] == 1
        assert calls == 1

        # 2. Segunda busca com False de novo: deve vir do cache
        res2 = await run_search(store, [oa], query="cache_test", include_peer_review=False)
        assert res2["total"] == 1
        assert calls == 1  # não chamou API novamente

        # 3. Terceira busca com True: chave do cache deve ser diferente e chamar a API
        res3 = await run_search(store, [oa], query="cache_test", include_peer_review=True)
        assert res3["total"] == 2
        assert calls == 2  # chamou a API porque a chave é diferente

        # 4. Quarta busca com True de novo: deve vir do cache de True
        res4 = await run_search(store, [oa], query="cache_test", include_peer_review=True)
        assert res4["total"] == 2
        assert calls == 2


# D-022, FR-13: log.md diz se os pareceres foram excluídos ou incluídos e mostra quantos saíram por fonte
@pytest.mark.anyio
async def test_d022_log_md_diz_se_pareceres_foram_excluidos_e_mostra_quantidade(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    w_article = _make_work("Artigo Regular", "10.1000/regular", work_type="article")
    w_review = _make_work("Decision Letter", "10.1000/decision", work_type="peer-review")
    fake_source = FakeMockSource("crossref", works=[w_article, w_review])

    # 1. Busca com pareceres excluídos
    await run_search(
        store,
        [fake_source],
        query="metodologia",
        request_summary="Busca sem pareceres",
        include_peer_review=False,
    )

    log_text = store.read_log()
    assert "pareceres de revisão excluídos" in log_text
    assert "1 parecer de revisão excluído" in log_text

    # 2. Busca com pareceres incluídos
    await run_search(
        store,
        [fake_source],
        query="metodologia",
        request_summary="Busca com pareceres",
        include_peer_review=True,
    )

    log_text2 = store.read_log()
    assert "pareceres de revisão incluídos" in log_text2


# D-022, FR-10: Orientação à IA em search_works e plan_search
def test_d022_orientacao_ia_search_works_e_plan_search() -> None:
    # 1. Docstring de search_works
    doc = server.search_works.__doc__ or ""
    assert "pareceres" in doc.lower()
    assert "include_peer_review" in doc

    # 2. Prompt plan_search com pedido
    prompt_pedido = render_plan_search("Pesquisa sobre câncer")
    assert "pareceres" in prompt_pedido.lower()
    assert "include_peer_review=true" in prompt_pedido.lower() or "include_peer_review" in prompt_pedido

    # 3. Prompt plan_search vazio
    prompt_vazio = render_plan_search("")
    assert "pareceres" in prompt_vazio.lower()
    assert "include_peer_review=true" in prompt_vazio.lower() or "include_peer_review" in prompt_vazio
