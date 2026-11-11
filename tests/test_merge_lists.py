"""Testes de integração da ferramenta merge_lists no servidor MCP (D-021)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from mcp import Client

from rslapp import config, people, server
from rslapp.auth import AuthStore
from rslapp.core.models import Author, Work
from rslapp.store import Store

PUBLIC_URL = "http://127.0.0.1:8000"
ENV_VARS = (
    "RSL_DATA_DIR",
    "RSL_EXPORT_DIR",
    "RSL_CACHE_DAYS",
    "OPENALEX_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "NCBI_API_KEY",
    "RSL_CONTACT_EMAIL",
    "RSL_PUBLIC_URL",
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Isola variáveis de ambiente e configura pasta de dados temporária."""
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    fake_home = tmp_path / "fake_home"
    data_dir = tmp_path / "rsl_data"
    export_dir = tmp_path / "rsl_export"
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("RSL_EXPORT_DIR", str(export_dir))
    return data_dir


def _extract_result_dict(call_result: Any) -> dict[str, Any]:
    sc = call_result.structured_content
    if isinstance(sc, dict) and "result" in sc and isinstance(sc["result"], dict):
        return sc["result"]
    assert isinstance(sc, dict)
    return sc


def _save_list_in_store(
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


# D-021, FR-04: duas listas com artigo em comum (mesmo DOI) viram uma só lista sem duplicatas
@pytest.mark.anyio
async def test_d021_tool_merge_lists_sucesso_mesmo_doi(isolated_env: Path) -> None:
    store = Store(isolated_env)
    w_a1 = Work(
        title="Artigo Compartilhado",
        doi="10.1000/1",
        year=2023,
        authors=[Author(name="Silva, J.")],
        source_ids={"openalex": "W1"},
        citations={"openalex": 10},
    )
    w_b = Work(title="Artigo B", doi="10.1000/2", year=2023)
    w_a2 = Work(
        title="Artigo Compartilhado",
        doi="10.1000/1",
        year=2023,
        authors=[Author(name="Silva, João")],
        source_ids={"crossref": "10.1000/1"},
        citations={"crossref": 7},
    )
    w_c = Work(title="Artigo C", doi="10.1000/3", year=2024)

    _save_list_in_store(store, [w_a1, w_b])
    _save_list_in_store(store, [w_a2, w_c])

    async with Client(server.mcp) as client:
        res = await client.call_tool(
            "merge_lists",
            {
                "list_ids": ["l-0001", "l-0002"],
                "request_summary": "Juntar buscas A e B",
            },
        )
        assert res.is_error is False
        data = _extract_result_dict(res)

        assert data["status"] == "complete"
        assert data["total"] == 3
        assert data["duplicates_removed"] == 1
        assert data["merged_from"] == ["l-0001", "l-0002"]
        assert data["page"] == 1
        assert data["next_page"] is None
        assert "sources" not in data
        assert len(data["works"]) == 3

        # Verifica na lista salva
        saved = store.get_list(data["list_id"])
        artigo_a = next(w for w in saved["works"] if w["doi"] == "10.1000/1")
        assert artigo_a["source_ids"] == {"openalex": "W1", "crossref": "10.1000/1"}
        assert artigo_a["citations"] == {"openalex": 10, "crossref": 7}


# D-021, FR-04: artigos sem DOI com mesmo título e ano se juntam
@pytest.mark.anyio
async def test_d021_tool_merge_lists_sem_doi_mesmo_titulo_e_ano(isolated_env: Path) -> None:
    store = Store(isolated_env)
    w1 = Work(title="Aprendizado de Máquina no Brasil", doi=None, year=2023, source_ids={"openalex": "W1"})
    w2 = Work(title="aprendizado de maquina no brasil", doi=None, year=2023, source_ids={"semantic_scholar": "S1"})

    _save_list_in_store(store, [w1])
    _save_list_in_store(store, [w2])

    async with Client(server.mcp) as client:
        res = await client.call_tool(
            "merge_lists",
            {"list_ids": ["l-0001", "l-0002"], "request_summary": "ML Brasil"},
        )
        assert res.is_error is False
        data = _extract_result_dict(res)
        assert data["total"] == 1
        assert data["duplicates_removed"] == 1

        saved = store.get_list(data["list_id"])
        assert "openalex" in saved["works"][0]["source_ids"]
        assert "semantic_scholar" in saved["works"][0]["source_ids"]


# D-021, FR-08: lista de origem incompleta deixa a junção incomplete com incomplete_from
@pytest.mark.anyio
async def test_d021_tool_merge_lists_incompleta(isolated_env: Path) -> None:
    store = Store(isolated_env)
    w1 = Work(title="A", doi="10.1000/1")
    w2 = Work(title="B", doi="10.1000/2")

    _save_list_in_store(store, [w1], status="complete")
    _save_list_in_store(store, [w2], status="incomplete")

    async with Client(server.mcp) as client:
        res = await client.call_tool(
            "merge_lists",
            {"list_ids": ["l-0001", "l-0002"]},
        )
        assert res.is_error is False
        data = _extract_result_dict(res)
        assert data["status"] == "incomplete"
        assert data["incomplete_from"] == ["l-0002"]


# D-021: erros de validação e lista inexistente que não grava nada
@pytest.mark.anyio
async def test_d021_tool_merge_lists_erros_e_nada_gravado(isolated_env: Path) -> None:
    store = Store(isolated_env)
    w1 = Work(title="A", doi="10.1000/1")
    _save_list_in_store(store, [w1])

    async with Client(server.mcp) as client:
        # Menos de 2 listas
        res_less = await client.call_tool("merge_lists", {"list_ids": ["l-0001"]})
        assert res_less.is_error is True
        assert "invalid_input" in str(res_less.content[0].text)

        # IDs repetidos
        res_dup = await client.call_tool("merge_lists", {"list_ids": ["l-0001", "l-0001"]})
        assert res_dup.is_error is True
        assert "invalid_input" in str(res_dup.content[0].text)

        # Formato errado
        res_fmt = await client.call_tool("merge_lists", {"list_ids": ["l-0001", "invalid_id"]})
        assert res_fmt.is_error is True
        assert "invalid_input" in str(res_fmt.content[0].text)

        # Lista inexistente: não grava nada
        res_404 = await client.call_tool("merge_lists", {"list_ids": ["l-0001", "l-9999"]})
        assert res_404.is_error is True
        assert "list_not_found" in str(res_404.content[0].text)

        # Confere que nenhuma nova lista, busca ou entrada de log foi gravada
        assert not (store.lists_dir / "l-0002.json").exists()
        assert not (store.searches_dir / "s-0002.json").exists()
        log_content = store.read_log()
        assert "s-0002" not in log_content
        assert "l-0002" not in log_content


# D-021, FR-05, FR-13: log.md ganha entrada de junção e get_search_log mostra registro com kind: merge
@pytest.mark.anyio
async def test_d021_log_md_e_get_search_log_mostram_merge(isolated_env: Path) -> None:
    store = Store(isolated_env)
    w1 = Work(title="A", doi="10.1000/1")
    w2 = Work(title="B", doi="10.1000/2")
    w3 = Work(title="A", doi="10.1000/1")

    _save_list_in_store(store, [w1, w2])
    _save_list_in_store(store, [w3])

    async with Client(server.mcp) as client:
        res = await client.call_tool(
            "merge_lists",
            {
                "list_ids": ["l-0001", "l-0002"],
                "request_summary": "Unir revisões de 2024",
            },
        )
        assert res.is_error is False
        data = _extract_result_dict(res)
        merge_search_id = data["search_id"]

        # get_search_log mostra o registro com kind: merge
        log_res = await client.call_tool("get_search_log", {"search_id": merge_search_id})
        assert log_res.is_error is False
        log_data = _extract_result_dict(log_res)
        assert len(log_data["entries"]) == 1
        entry = log_data["entries"][0]
        assert entry["id"] == merge_search_id
        assert entry["kind"] == "merge"
        assert entry["merged_from"] == ["l-0001", "l-0002"]
        assert entry["duplicates_removed"] == 1

        # log.md ganha a entrada da junção
        log_text = store.read_log()
        assert f"## {merge_search_id} · " in log_text
        assert " · junção\n" in log_text
        assert "Pedido: Unir revisões de 2024\n" in log_text
        assert f"Lista: {data['list_id']} · completa · 2 artigos\n" in log_text
        assert "Duplicatas removidas: 1 artigo\n" in log_text
        assert "- l-0001 · 2 artigos\n" in log_text
        assert "- l-0002 · 1 artigo" in log_text


# D-021: repeat_search de uma junção responde invalid_input
@pytest.mark.anyio
async def test_d021_tool_repeat_search_de_juncao_responde_invalid_input(isolated_env: Path) -> None:
    store = Store(isolated_env)
    w1 = Work(title="A", doi="10.1000/1")
    w2 = Work(title="B", doi="10.1000/2")
    _save_list_in_store(store, [w1])
    _save_list_in_store(store, [w2])

    async with Client(server.mcp) as client:
        res = await client.call_tool("merge_lists", {"list_ids": ["l-0001", "l-0002"]})
        assert res.is_error is False
        search_id = _extract_result_dict(res)["search_id"]

        rep_res = await client.call_tool("repeat_search", {"search_id": search_id})
        assert rep_res.is_error is True
        error_msg = str(rep_res.content[0].text)
        assert "invalid_input" in error_msg
        assert "uma junção não pode ser repetida; repita as buscas de origem" in error_msg


def _extract_http_jsonrpc_body(resp: httpx.Response) -> dict[str, Any]:
    if "text/event-stream" in resp.headers.get("content-type", ""):
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[len("data:") :].strip())
    return resp.json()


async def _call_http_tool(
    client: httpx.AsyncClient, token: str, tool_name: str, arguments: dict[str, Any] | None = None
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    init_resp = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        },
        headers=headers,
    )
    assert init_resp.status_code == 200
    call_headers = dict(headers)
    if session_id := init_resp.headers.get("mcp-session-id"):
        call_headers["mcp-session-id"] = session_id

    call_resp = await client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": tool_name, "arguments": arguments or {}}},
        headers=call_headers,
    )
    assert call_resp.status_code == 200
    return _extract_http_jsonrpc_body(call_resp)["result"]


def _issue_person_token(data_dir: Path, person_id: str) -> str:
    if people.get(person_id, data_dir=data_dir) is None:
        people.add(person_id, data_dir=data_dir)
    return AuthStore(data_dir=data_dir).issue_token_pair(
        person_id=person_id, client_id=f"c-{person_id}", scopes=["rsl"], resource=f"{PUBLIC_URL}/mcp"
    ).access_token


# D-012, D-021: no modo HTTP, Maria não consegue juntar lista do João (list_not_found) e o servidor lista 9 ferramentas
@pytest.mark.anyio
async def test_d021_http_maria_nao_consegue_juntar_lista_do_joao(
    isolated_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_dir = isolated_env
    monkeypatch.setenv("RSL_PUBLIC_URL", PUBLIC_URL)

    maria_token = _issue_person_token(data_dir, "maria")
    joao_token = _issue_person_token(data_dir, "joao")

    maria_store = Store(data_dir / "people" / "maria")
    joao_store = Store(data_dir / "people" / "joao")

    w1 = Work(title="Trabalho Maria 1", doi="10.1000/m1")
    w2 = Work(title="Trabalho Maria 2", doi="10.1000/m2")
    _save_list_in_store(maria_store, [w1, w2])  # l-0001 da Maria

    wj = Work(title="Trabalho Joao 1", doi="10.1000/j1")
    _save_list_in_store(joao_store, [wj])  # l-0001 do João

    http_cfg = config.HttpConfig(
        host="127.0.0.1",
        port=8000,
        public_url=PUBLIC_URL,
    )
    app = server.create_http_app(http_cfg)

    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=PUBLIC_URL) as client,
    ):
        # 1. Verifica que o servidor lista 9 ferramentas em /mcp
        headers = {
            "Authorization": f"Bearer {maria_token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        init_r = await client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "c", "version": "1"}},
            },
            headers=headers,
        )
        assert init_r.status_code == 200
        call_headers = dict(headers)
        if session_id := init_r.headers.get("mcp-session-id"):
            call_headers["mcp-session-id"] = session_id

        tools_r = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            headers=call_headers,
        )
        assert tools_r.status_code == 200
        tools_body = _extract_http_jsonrpc_body(tools_r)
        tool_names = {t["name"] for t in tools_body["result"]["tools"]}
        assert len(tool_names) == 9
        assert "merge_lists" in tool_names

        # 2. Maria tenta juntar sua lista l-0001 com l-0002 (inexistente nela): list_not_found
        call_err = await _call_http_tool(
            client,
            maria_token,
            "merge_lists",
            {"list_ids": ["l-0001", "l-0002"]},
        )
        assert call_err.get("isError") is True
        error_text = call_err["content"][0]["text"]
        assert "list_not_found" in error_text

        # 3. Maria adiciona l-0002 no seu espaço e junta com sucesso
        w3 = Work(title="Trabalho Maria 3", doi="10.1000/m3")
        _save_list_in_store(maria_store, [w3])  # l-0002 da Maria

        ok_call = await _call_http_tool(
            client,
            maria_token,
            "merge_lists",
            {"list_ids": ["l-0001", "l-0002"]},
        )
        assert ok_call.get("isError") is not True
        maria_merge_data = ok_call["structuredContent"]
        assert maria_merge_data["status"] == "complete"
        assert maria_merge_data["total"] == 3

        # 4. João tenta juntar l-0001 e l-0002 (l-0002 existe na Maria, mas não no João): list_not_found
        joao_call = await _call_http_tool(
            client,
            joao_token,
            "merge_lists",
            {"list_ids": ["l-0001", "l-0002"]},
        )
        assert joao_call.get("isError") is True
        assert "list_not_found" in joao_call["content"][0]["text"]
