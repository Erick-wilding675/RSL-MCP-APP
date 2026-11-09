"""Testes de entradas inteiras das ferramentas no servidor MCP (D-002)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp import Client

from rslapp import server
from rslapp.core.models import Affiliation, Author, Work
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
    return data_dir


def _extract_result_dict(call_result: Any) -> dict[str, Any]:
    sc = call_result.structured_content
    if isinstance(sc, dict) and "result" in sc and isinstance(sc["result"], dict):
        return sc["result"]
    assert isinstance(sc, dict)
    return sc


def _create_sample_list(data_dir: Path, count: int = 30) -> str:
    store = Store(data_dir)
    works: list[Work] = []
    for i in range(1, count + 1):
        works.append(
            Work(
                title=f"Estudo Sistemático {i:02d}",
                doi=f"10.1234/estudo.{i:02d}",
                year=2024,
                type="article",
                venue="Revista de Teste",
                abstract=f"Resumo detalhado {i}",
                keywords=["ciência", f"teste-{i}"],
                authors=[
                    Author(
                        name=f"Pesquisador {i}",
                        orcid=f"0000-0001-{i:04d}-0000",
                        affiliations=[Affiliation(name=f"Inst {i}", country_code="BR")],
                    )
                ],
                references=[f"W{r:04d}" for r in range(1, 4)],
                references_count=3,
                citations={"openalex": i * 3},
                source_ids={"openalex": f"W{i:04d}"},
            )
        )
    _search, saved_list = store.record_search(
        {
            "kind": "terms",
            "query": "estudo sistemático",
            "sources": [{"name": "openalex", "status": "ok", "query": "q", "found": count, "fetched": count}],
        },
        {"status": "complete", "works": [w.to_dict() for w in works]},
    )
    return str(saved_list["id"])


# D-002: As seis entradas inteiras recusam true e false com invalid_input sem chamar o miolo
@pytest.mark.anyio
@pytest.mark.parametrize("bool_val", [True, False])
@pytest.mark.parametrize(
    ("tool_name", "param_name", "base_args"),
    [
        ("search_works", "max_results", {"query": "bibliometria"}),
        ("get_related_works", "max_results", {"doi": "10.1234/teste", "direction": "references"}),
        ("find_work", "max_results", {"title": "Artigo Exemplo"}),
        ("get_list", "page", {"list_id": "l-0001"}),
        ("get_list", "page_size", {"list_id": "l-0001"}),
        ("get_search_log", "limit", {}),
    ],
)
async def test_d002_entradas_inteiras_recusam_true_e_false_sem_chamar_miolo(
    isolated_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    tool_name: str,
    param_name: str,
    base_args: dict[str, Any],
    bool_val: bool,
) -> None:
    def _fail_if_called(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("O miolo ou as fontes não deveriam ser chamados quando a entrada é booleana")

    monkeypatch.setattr(server, "_build_sources", _fail_if_called)
    monkeypatch.setattr(server, "run_search", _fail_if_called)
    monkeypatch.setattr(server, "run_related", _fail_if_called)
    monkeypatch.setattr(server, "run_find", _fail_if_called)
    monkeypatch.setattr(server, "get_list_view", _fail_if_called)
    monkeypatch.setattr(server, "get_search_log_view", _fail_if_called)

    args = {**base_args, param_name: bool_val}
    async with Client(server.mcp) as client:
        res = await client.call_tool(tool_name, args)

    assert res.is_error is True
    assert res.content
    text = str(res.content[0].text)
    assert "invalid_input" in text
    assert param_name in text

    # Nenhuma lista nem entrada de log criada
    assert not isolated_env.exists()
    store = Store(isolated_env)
    assert store.list_searches() == []
    lists_dir = isolated_env / "lists"
    assert not lists_dir.exists() or list(lists_dir.glob("*.json")) == []


# D-002: get_list com page="2" e page=2.0 continua devolvendo a página 2
@pytest.mark.anyio
@pytest.mark.parametrize("coerced_page", ["2", 2.0])
async def test_d002_get_list_page_texto_e_float_inteiro_aceitos(
    isolated_env: Path,
    coerced_page: Any,
) -> None:
    list_id = _create_sample_list(isolated_env, count=30)

    async with Client(server.mcp) as client:
        res = await client.call_tool(
            "get_list",
            {"list_id": list_id, "page": coerced_page, "page_size": 10},
        )

    assert res.is_error is False
    data = _extract_result_dict(res)
    assert data["page"] == 2
    assert data["page_size"] == 10
    assert len(data["works"]) == 10
    assert data["works"][0]["doi"] == "10.1234/estudo.11"


# D-002: get_list com page=2.5 continua recusado
@pytest.mark.anyio
async def test_d002_get_list_page_float_fracionario_recusado(isolated_env: Path) -> None:
    list_id = _create_sample_list(isolated_env, count=30)

    async with Client(server.mcp) as client:
        res = await client.call_tool(
            "get_list",
            {"list_id": list_id, "page": 2.5},
        )

    assert res.is_error is True


# D-002: input_schema das seis entradas em list_tools mantém type integer e default atual
@pytest.mark.anyio
async def test_d002_list_tools_input_schema_mantem_integer_e_default() -> None:
    expected = {
        ("search_works", "max_results"): 100,
        ("get_related_works", "max_results"): 1000,
        ("find_work", "max_results"): 10,
        ("get_list", "page"): 1,
        ("get_list", "page_size"): 25,
        ("get_search_log", "limit"): 20,
    }

    async with Client(server.mcp) as client:
        tools_res = await client.list_tools()

    tools_by_name = {t.name: t for t in tools_res.tools}
    for (tool_name, param_name), default_val in expected.items():
        tool = tools_by_name[tool_name]
        prop = tool.input_schema["properties"][param_name]
        assert prop["type"] == "integer"
        assert prop["default"] == default_val
