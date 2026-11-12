"""Testes das bases pagas Scopus e Web of Science no servidor MCP (D-023)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp import Client
from mcp.server.mcpserver.exceptions import ToolError

from rslapp import server
from rslapp.core.models import SourceResult, Work
from rslapp.store import Store

ENV_VARS = (
    "RSL_DATA_DIR",
    "RSL_EXPORT_DIR",
    "RSL_CACHE_DAYS",
    "OPENALEX_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "NCBI_API_KEY",
    "SCOPUS_API_KEY",
    "SCOPUS_INSTTOKEN",
    "WOS_STARTER_API_KEY",
    "RSL_CONTACT_EMAIL",
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    data_dir = tmp_path / "rsl_data"
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))
    return data_dir


class TrackingFakeSource:
    """Fonte simulada para registrar chamadas."""

    def __init__(self, name: str, works: list[Work] | None = None) -> None:
        self.name = name
        self.needs_key = False
        self.works = works if works is not None else []
        self.calls: list[tuple[str, int]] = []

    def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
        return {"source": self.name, "query": query, "max": max_results}

    async def search(self, query: str, max_results: int) -> SourceResult:
        self.calls.append((query, max_results))
        return SourceResult(
            name=self.name,
            status="ok",
            query=f"query={query}",
            found=len(self.works),
            fetched=len(self.works),
            works=self.works,
        )

    async def find_by_doi(self, doi: str) -> SourceResult:
        self.calls.append((doi, 1))
        return SourceResult(
            name=self.name,
            status="ok",
            query=f"doi={doi}",
            found=len(self.works),
            fetched=len(self.works),
            works=self.works,
        )


class CrashingTypeErrorSource:
    """Fonte simulada que levanta TypeError dentro de search (D-023)."""

    def __init__(self, name: str = "fonte_quebra") -> None:
        self.name = name
        self.needs_key = False
        self.call_count = 0

    def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
        return {"source": self.name, "query": query}

    async def search(self, query: str, max_results: int) -> SourceResult:
        self.call_count += 1
        raise TypeError("erro interno de tipo dentro da fonte simulada")


def _extract_result_dict(call_result: Any) -> dict[str, Any]:
    sc = call_result.structured_content
    if isinstance(sc, dict) and "result" in sc and isinstance(sc["result"], dict):
        return sc["result"]
    assert isinstance(sc, dict)
    return sc


# D-023: search_works com sources=["scopus", "web_of_science"] consulta as duas, e sem sources consulta só as três de sempre
@pytest.mark.anyio
async def test_d023_search_works_com_bases_pagas_e_sem_sources(
    monkeypatch: pytest.MonkeyPatch,
    isolated_env: Path,
) -> None:
    src_oa = TrackingFakeSource("openalex")
    src_cr = TrackingFakeSource("crossref")
    src_s2 = TrackingFakeSource("semantic_scholar")
    src_epmc = TrackingFakeSource("europe_pmc")
    src_pm = TrackingFakeSource("pubmed")
    src_scopus = TrackingFakeSource("scopus")
    src_wos = TrackingFakeSource("web_of_science")

    all_sources = [src_oa, src_cr, src_s2, src_epmc, src_pm, src_scopus, src_wos]
    monkeypatch.setattr(server, "_build_sources", lambda: all_sources)

    async with Client(server.mcp) as client:
        # 1. Sem sources: consulta apenas as três originais (openalex, crossref, semantic_scholar)
        res_default = await client.call_tool(
            "search_works",
            {"query": "quantum computing"},
        )
        assert res_default.is_error is False
        payload_default = _extract_result_dict(res_default)
        sources_default = [s["name"] for s in payload_default["sources"]]
        assert sources_default == ["openalex", "crossref", "semantic_scholar"]
        assert len(src_oa.calls) == 1
        assert len(src_cr.calls) == 1
        assert len(src_s2.calls) == 1
        assert len(src_scopus.calls) == 0
        assert len(src_wos.calls) == 0

        # 2. Com sources=["scopus", "web_of_science"]: consulta apenas as duas bases pagas
        res_paid = await client.call_tool(
            "search_works",
            {
                "query": "quantum computing",
                "sources": ["scopus", "web_of_science"],
            },
        )
        assert res_paid.is_error is False
        payload_paid = _extract_result_dict(res_paid)
        sources_paid = [s["name"] for s in payload_paid["sources"]]
        assert sources_paid == ["scopus", "web_of_science"]
        assert len(src_scopus.calls) == 1
        assert len(src_wos.calls) == 1
        assert len(src_oa.calls) == 1  # não chamou novamente


# D-023: list_sources no stdio lista as sete, com missing_key sem as chaves e ok com elas, sem mostrar valor de chave
@pytest.mark.anyio
async def test_d023_list_sources_stdio_lista_sete_sem_e_com_chaves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with Client(server.mcp) as client:
        # 1. Sem chaves: scopus e web_of_science aparecem com missing_key
        res_sem = await client.call_tool("list_sources", {})
        assert res_sem.is_error is False
        payload_sem = res_sem.structured_content["result"]
        assert isinstance(payload_sem, list)
        names = [item["name"] for item in payload_sem]
        assert names == [
            "openalex",
            "crossref",
            "semantic_scholar",
            "europe_pmc",
            "pubmed",
            "scopus",
            "web_of_science",
        ]

        scopus_sem = next(item for item in payload_sem if item["name"] == "scopus")
        assert scopus_sem["configured"] is False
        assert scopus_sem["needs_key"] is True
        assert scopus_sem["status"] == "missing_key"

        wos_sem = next(item for item in payload_sem if item["name"] == "web_of_science")
        assert wos_sem["configured"] is False
        assert wos_sem["needs_key"] is True
        assert wos_sem["status"] == "missing_key"

        # 2. Com chaves configuradas: aparecem com ok e configured=True
        chave_scopus = "chave-falsa-scopus-12345"
        chave_wos = "chave-falsa-wos-67890"
        monkeypatch.setenv("SCOPUS_API_KEY", chave_scopus)
        monkeypatch.setenv("WOS_STARTER_API_KEY", chave_wos)

        res_com = await client.call_tool("list_sources", {})
        assert res_com.is_error is False
        payload_com = res_com.structured_content["result"]

        scopus_com = next(item for item in payload_com if item["name"] == "scopus")
        assert scopus_com["configured"] is True
        assert scopus_com["needs_key"] is True
        assert scopus_com["status"] == "ok"

        wos_com = next(item for item in payload_com if item["name"] == "web_of_science")
        assert wos_com["configured"] is True
        assert wos_com["needs_key"] is True
        assert wos_com["status"] == "ok"

        # Nenhum valor de chave aparece na resposta
        dump_json = res_com.model_dump_json()
        assert chave_scopus not in dump_json
        assert chave_wos not in dump_json

        # A descrição da ferramenta diz que as duas são bases pagas e só funcionam com a chave e assinatura do usuário
        tools = await client.list_tools()
        tool_sources = next(t for t in tools.tools if t.name == "list_sources")
        desc = tool_sources.description
        assert "bases pagas" in desc
        assert "chave e a assinatura do próprio usuário ou da instituição" in desc


# D-023: no modo HTTP, list_sources não lista as duas, e search_works/repeat_search respondem invalid_input
@pytest.mark.anyio
async def test_d023_modo_http_recusa_bases_pagas_e_nao_lista_em_list_sources(
    monkeypatch: pytest.MonkeyPatch,
    isolated_env: Path,
) -> None:
    token_mode = server._http_mode_var.set(True)
    monkeypatch.setattr(server, "current_person_id", lambda: "erick")
    try:
        # 1. _build_sources no modo HTTP não cria os conectores scopus nem web_of_science
        http_sources = server._build_sources()
        http_source_names = [s.name for s in http_sources]
        assert "scopus" not in http_source_names
        assert "web_of_science" not in http_source_names
        assert len(http_sources) == 5

        # 2. list_sources no modo HTTP não lista scopus nem web_of_science
        res_list = server.list_sources()
        names_listed = [s["name"] for s in res_list]
        assert "scopus" not in names_listed
        assert "web_of_science" not in names_listed
        assert len(names_listed) == 5

        # 3. search_works com scopus ou web_of_science responde invalid_input com a mensagem exata da D-023
        msg_esperada = "invalid_input: scopus e web_of_science só funcionam no RSL.app instalado no seu computador, com a sua chave e o acesso da sua instituição (D-023)"
        with pytest.raises(ToolError) as exc_info:
            await server.search_works(query="teste", sources=["scopus"])
        assert str(exc_info.value) == msg_esperada

        with pytest.raises(ToolError) as exc_info_wos:
            await server.search_works(query="teste", sources=["web_of_science"])
        assert str(exc_info_wos.value) == msg_esperada

        # 4. repeat_search no modo HTTP de busca gravada com scopus responde invalid_input com a mesma mensagem
        store = Store(isolated_env / "people" / "erick")
        search_data = {
            "kind": "terms",
            "request_summary": "Busca gravada com scopus",
            "params": {"query": "teste", "sources": ["scopus"]},
            "sources": [{"name": "scopus", "status": "ok", "fetched": 1}],
        }
        list_data = {"status": "complete", "total": 1, "works": []}
        saved_s, _ = store.record_search(search_data, list_data)

        with pytest.raises(ToolError) as exc_repeat:
            await server.repeat_search(search_id=saved_s["id"])
        assert str(exc_repeat.value) == msg_esperada

    finally:
        server._http_mode_var.reset(token_mode)


# D-023: find_work e get_related_works com sources=["scopus"] e ["web_of_science"] respondem invalid_input
@pytest.mark.anyio
async def test_d023_find_work_e_get_related_works_recusam_bases_pagas() -> None:
    async with Client(server.mcp) as client:
        # find_work com scopus
        res_find_scopus = await client.call_tool(
            "find_work",
            {"doi": "10.1000/182", "sources": ["scopus"]},
        )
        assert res_find_scopus.is_error is True
        assert "fonte não suportada nesta ferramenta: scopus" in res_find_scopus.content[0].text

        # find_work com web_of_science
        res_find_wos = await client.call_tool(
            "find_work",
            {"doi": "10.1000/182", "sources": ["web_of_science"]},
        )
        assert res_find_wos.is_error is True
        assert "fonte não suportada nesta ferramenta: web_of_science" in res_find_wos.content[0].text

        # get_related_works com scopus
        res_rel_scopus = await client.call_tool(
            "get_related_works",
            {"doi": "10.1000/182", "direction": "references", "sources": ["scopus"]},
        )
        assert res_rel_scopus.is_error is True
        assert "fonte não suportada nesta ferramenta: scopus" in res_rel_scopus.content[0].text

        # get_related_works com web_of_science
        res_rel_wos = await client.call_tool(
            "get_related_works",
            {"doi": "10.1000/182", "direction": "citations", "sources": ["web_of_science"]},
        )
        assert res_rel_wos.is_error is True
        assert "fonte não suportada nesta ferramenta: web_of_science" in res_rel_wos.content[0].text


# D-023: repeat_search de uma busca com scopus repete com scopus
@pytest.mark.anyio
async def test_d023_repeat_search_de_busca_com_scopus_repete_com_scopus(
    monkeypatch: pytest.MonkeyPatch,
    isolated_env: Path,
) -> None:
    src_scopus = TrackingFakeSource("scopus")
    src_oa = TrackingFakeSource("openalex")
    monkeypatch.setattr(server, "_build_sources", lambda: [src_oa, src_scopus])

    async with Client(server.mcp) as client:
        # 1. Executa busca original com scopus
        res_orig = await client.call_tool(
            "search_works",
            {"query": "deep learning", "sources": ["scopus"]},
        )
        assert res_orig.is_error is False
        orig_payload = _extract_result_dict(res_orig)
        orig_search_id = orig_payload["search_id"]
        assert len(src_scopus.calls) == 1

        # 2. Executa repeat_search com o search_id da busca anterior
        res_repeat = await client.call_tool(
            "repeat_search",
            {"search_id": orig_search_id},
        )
        assert res_repeat.is_error is False
        repeat_payload = _extract_result_dict(res_repeat)
        assert repeat_payload["search_id"] != orig_search_id
        assert repeat_payload["repeated_from"] == orig_search_id
        sources_repeated = [s["name"] for s in repeat_payload["sources"]]
        assert sources_repeated == ["scopus"]
        assert repeat_payload["sources"][0]["from_cache"] is True


# D-023, D-022: uma fonte falsa que levanta TypeError dentro de search dá failed para aquela fonte, com um pedido só (sem repetir)
@pytest.mark.anyio
async def test_d023_fonte_falsa_que_levanta_typeerror_da_failed_com_um_pedido_so(
    monkeypatch: pytest.MonkeyPatch,
    isolated_env: Path,
) -> None:
    crashing_src = CrashingTypeErrorSource(name="fonte_quebra")
    ok_src = TrackingFakeSource("openalex")
    monkeypatch.setattr(server, "_build_sources", lambda: [ok_src, crashing_src])

    async with Client(server.mcp) as client:
        res = await client.call_tool(
            "search_works",
            {"query": "test error", "sources": ["openalex", "fonte_quebra"]},
        )
        assert res.is_error is False
        payload = _extract_result_dict(res)
        assert payload["status"] == "incomplete"

        sources = payload["sources"]
        src_entry = next(s for s in sources if s["name"] == "fonte_quebra")
        assert src_entry["status"] == "failed"
        assert "erro interno de tipo dentro da fonte simulada" in src_entry["reason"]
        # Chamou apenas uma vez (sem tentar de novo após o TypeError)
        assert crashing_src.call_count == 1


# D-023: a descrição de search_works orienta sobre scopus e web_of_science
@pytest.mark.anyio
async def test_d023_search_works_descricao_orienta_bases_pagas() -> None:
    async with Client(server.mcp) as client:
        tools = await client.list_tools()
        tool = next(t for t in tools.tools if t.name == "search_works")
        desc = tool.description
        assert "scopus" in desc
        assert "web_of_science" in desc
        assert "bases pagas" in desc
        assert "list_sources mostra" in desc
        assert "Web of Science não traz resumo nem afiliações" in desc
