"""Testes das fontes PubMed e Europe PMC no servidor MCP (D-020)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp import Client

from rslapp import server
from rslapp.auth import AuthStore, RSLTokenVerifier
from rslapp.core.models import SourceResult, Work

ENV_VARS = (
    "RSL_DATA_DIR",
    "RSL_EXPORT_DIR",
    "RSL_CACHE_DAYS",
    "OPENALEX_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "NCBI_API_KEY",
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


def _extract_result_dict(call_result: Any) -> dict[str, Any]:
    sc = call_result.structured_content
    if isinstance(sc, dict) and "result" in sc and isinstance(sc["result"], dict):
        return sc["result"]
    assert isinstance(sc, dict)
    return sc


# D-020: search_works com sources=["pubmed", "europe_pmc"] consulta as duas, e sem sources consulta só as três de antes
@pytest.mark.anyio
async def test_d020_search_works_com_fontes_novas_e_sem_sources(
    monkeypatch: pytest.MonkeyPatch,
    isolated_env: Path,
) -> None:
    src_oa = TrackingFakeSource("openalex")
    src_cr = TrackingFakeSource("crossref")
    src_s2 = TrackingFakeSource("semantic_scholar")
    src_epmc = TrackingFakeSource("europe_pmc")
    src_pm = TrackingFakeSource("pubmed")

    all_sources = [src_oa, src_cr, src_s2, src_epmc, src_pm]
    monkeypatch.setattr(server, "_build_sources", lambda: all_sources)

    async with Client(server.mcp) as client:
        # 1. Sem sources: consulta apenas as três originais (openalex, crossref, semantic_scholar)
        res_default = await client.call_tool(
            "search_works",
            {"query": "machine learning"},
        )
        assert res_default.is_error is False
        payload_default = _extract_result_dict(res_default)
        sources_default = [s["name"] for s in payload_default["sources"]]
        assert sources_default == ["openalex", "crossref", "semantic_scholar"]
        assert len(src_oa.calls) == 1
        assert len(src_cr.calls) == 1
        assert len(src_s2.calls) == 1
        assert len(src_epmc.calls) == 0
        assert len(src_pm.calls) == 0

        # 2. Com sources=["pubmed", "europe_pmc"]: consulta apenas as duas fontes novas
        res_new = await client.call_tool(
            "search_works",
            {
                "query": "oncology clinical trials",
                "sources": ["pubmed", "europe_pmc"],
            },
        )
        assert res_new.is_error is False
        payload_new = _extract_result_dict(res_new)
        sources_new = [s["name"] for s in payload_new["sources"]]
        assert sources_new == ["pubmed", "europe_pmc"]
        assert len(src_pm.calls) == 1
        assert len(src_epmc.calls) == 1
        assert len(src_oa.calls) == 1  # não foi chamado novamente
        assert len(src_cr.calls) == 1
        assert len(src_s2.calls) == 1


# D-020: repeat_search de uma busca feita com pubmed repete com pubmed
@pytest.mark.anyio
async def test_d020_repeat_search_com_pubmed_repete_com_pubmed(
    monkeypatch: pytest.MonkeyPatch,
    isolated_env: Path,
) -> None:
    w = Work(
        title="Genomics Study",
        doi="10.1234/genomics",
        year=2024,
        source_ids={"pubmed": "12345"},
    )
    src_pm = TrackingFakeSource("pubmed", works=[w])
    src_oa = TrackingFakeSource("openalex")
    monkeypatch.setattr(server, "_build_sources", lambda: [src_oa, src_pm])

    async with Client(server.mcp) as client:
        # Busca inicial com pubmed
        res_orig = await client.call_tool(
            "search_works",
            {"query": "genomics", "sources": ["pubmed"]},
        )
        assert res_orig.is_error is False
        orig_data = _extract_result_dict(res_orig)
        orig_search_id = orig_data["search_id"]
        assert [s["name"] for s in orig_data["sources"]] == ["pubmed"]

        # Repete a busca a partir do id gravado
        res_repeat = await client.call_tool(
            "repeat_search",
            {"search_id": orig_search_id},
        )
        assert res_repeat.is_error is False
        repeat_data = _extract_result_dict(res_repeat)
        assert repeat_data["search_id"] != orig_search_id
        assert repeat_data["repeated_from"] == orig_search_id
        assert [s["name"] for s in repeat_data["sources"]] == ["pubmed"]
        assert repeat_data["sources"][0]["from_cache"] is True


# D-020: find_work e get_related_works com sources=["pubmed"] respondem invalid_input, sem chamar fonte nenhuma
@pytest.mark.anyio
async def test_d020_find_work_e_get_related_works_recusam_fontes_novas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src_oa = TrackingFakeSource("openalex")
    src_pm = TrackingFakeSource("pubmed")
    src_epmc = TrackingFakeSource("europe_pmc")
    monkeypatch.setattr(server, "_build_sources", lambda: [src_oa, src_pm, src_epmc])

    async with Client(server.mcp) as client:
        # find_work com pubmed
        res_find_pm = await client.call_tool(
            "find_work",
            {"doi": "10.1234/target", "sources": ["pubmed"]},
        )
        assert res_find_pm.is_error is True
        error_msg = str(res_find_pm.content[0].text)
        assert "invalid_input" in error_msg
        assert "fonte não suportada nesta ferramenta: pubmed" in error_msg
        assert len(src_oa.calls) == 0
        assert len(src_pm.calls) == 0

        # find_work com europe_pmc
        res_find_epmc = await client.call_tool(
            "find_work",
            {"title": "Target Title", "sources": ["europe_pmc"]},
        )
        assert res_find_epmc.is_error is True
        error_msg_epmc = str(res_find_epmc.content[0].text)
        assert "invalid_input" in error_msg_epmc
        assert "fonte não suportada nesta ferramenta: europe_pmc" in error_msg_epmc
        assert len(src_epmc.calls) == 0

        # get_related_works com pubmed
        res_rel_pm = await client.call_tool(
            "get_related_works",
            {"doi": "10.1234/target", "direction": "references", "sources": ["pubmed"]},
        )
        assert res_rel_pm.is_error is True
        error_msg_rel = str(res_rel_pm.content[0].text)
        assert "invalid_input" in error_msg_rel
        assert "fonte não suportada nesta ferramenta: pubmed" in error_msg_rel
        assert len(src_pm.calls) == 0

        # get_related_works com europe_pmc
        res_rel_epmc = await client.call_tool(
            "get_related_works",
            {"doi": "10.1234/target", "direction": "citations", "sources": ["europe_pmc"]},
        )
        assert res_rel_epmc.is_error is True
        error_msg_rel_epmc = str(res_rel_epmc.content[0].text)
        assert "invalid_input" in error_msg_rel_epmc
        assert "fonte não suportada nesta ferramenta: europe_pmc" in error_msg_rel_epmc
        assert len(src_epmc.calls) == 0


# D-020: list_sources lista as cinco, e com NCBI_API_KEY definida o valor não aparece em lugar nenhum da resposta
@pytest.mark.anyio
async def test_d020_list_sources_lista_cinco_e_nao_vaza_ncbi_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret_ncbi_key = "segredo-ncbi-super-confidencial-xyz"
    monkeypatch.setenv("NCBI_API_KEY", secret_ncbi_key)

    async with Client(server.mcp) as client:
        res = await client.call_tool("list_sources", {})
        assert res.is_error is False
        payload = res.structured_content["result"]
        assert isinstance(payload, list)
        names = [item["name"] for item in payload]
        assert names == ["openalex", "crossref", "semantic_scholar", "europe_pmc", "pubmed"]

        pm_info = next(item for item in payload if item["name"] == "pubmed")
        assert pm_info["configured"] is True
        assert pm_info["needs_key"] is False
        assert pm_info["status"] == "ok"

        epmc_info = next(item for item in payload if item["name"] == "europe_pmc")
        assert epmc_info["configured"] is True
        assert epmc_info["needs_key"] is False
        assert epmc_info["status"] == "ok"

        # Garante que o valor da chave não vaza em lugar nenhum
        full_dump = res.model_dump_json()
        assert secret_ncbi_key not in full_dump


# D-020: no modo HTTP, as ferramentas continuam as mesmas (a lista do _build_http_mcp_server não muda)
def test_d020_modo_http_mantem_mesmas_ferramentas(tmp_path: Path) -> None:
    from mcp.server.auth.settings import AuthSettings
    from pydantic import AnyHttpUrl

    store = AuthStore(data_dir=tmp_path / "auth", access_token_minutes=60)
    verifier = RSLTokenVerifier(store, resource_server_url="http://127.0.0.1:8000/mcp")
    auth_settings = AuthSettings(
        issuer_url=AnyHttpUrl("http://127.0.0.1:8000"),
        resource_server_url=AnyHttpUrl("http://127.0.0.1:8000/mcp"),
        validate_token_resource=True,
    )
    http_server = server._build_http_mcp_server(
        token_verifier=verifier,
        auth=auth_settings,
    )

    # As 9 ferramentas registradas continuam idênticas (D-021 adiciona merge_lists)
    expected_tools = {
        "list_sources",
        "search_works",
        "get_related_works",
        "find_work",
        "repeat_search",
        "merge_lists",
        "export_list",
        "get_list",
        "get_search_log",
    }
    registered_tools = set(http_server._tool_manager._tools.keys())
    assert registered_tools == expected_tools


# D-020: a descrição de search_works orienta sobre pubmed e europe_pmc em temas de saúde
@pytest.mark.anyio
async def test_d020_search_works_descricao_orienta_fontes_saude() -> None:
    async with Client(server.mcp) as client:
        tools = await client.list_tools()
        tool = next(t for t in tools.tools if t.name == "search_works")
        desc_lower = tool.description.lower()
        assert "pubmed" in desc_lower
        assert "europe_pmc" in desc_lower
        assert "saúde" in desc_lower or "saude" in desc_lower
        assert "medicina" in desc_lower
        assert "biologia" in desc_lower

