"""Servidor MCP do RSL.app (transporte stdio)."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from typing_extensions import TypedDict

from rslapp import config
from rslapp.core.errors import RSLError
from rslapp.core.related import run_related
from rslapp.core.search import run_search
from rslapp.core.views import get_list_view, get_search_log_view
from rslapp.exporters import run_export
from rslapp.prompts import INSTRUCTIONS, render_plan_search
from rslapp.sources.base import Source
from rslapp.sources.crossref import CrossrefSource
from rslapp.sources.openalex import OpenAlexSource
from rslapp.sources.semantic_scholar import SemanticScholarSource
from rslapp.store import Store

SourceName = Literal["openalex", "crossref", "semantic_scholar"]
SourceStatus = Literal["ok", "missing_key"]


# D-002, FR-07, NFR-03: Estrutura de retorno de list_sources sem expor o valor de chaves
class SourceInfo(TypedDict):
    """Estado de configuração de uma fonte acadêmica."""

    name: SourceName
    configured: bool
    needs_key: bool
    status: SourceStatus


# D-006, NFR-02: Servidor MCP usando MCPServer do SDK oficial mcp 2.x para execução local
mcp = MCPServer("rslapp", instructions=INSTRUCTIONS)


# D-002, FR-07, NFR-03: Lista as fontes acadêmicas indicando se estão configuradas e prontas
@mcp.tool()
def list_sources() -> list[SourceInfo]:
    """Informa para cada fonte acadêmica se está configurada, se exige chave e seu estado. A chave da Semantic Scholar é opcional e evita recusas por limite."""
    cfg = config.load()
    openalex_configured = cfg.openalex_key_configured
    return [
        {
            "name": "openalex",
            "configured": openalex_configured,
            "needs_key": True,
            "status": "ok" if openalex_configured else "missing_key",
        },
        {
            "name": "crossref",
            "configured": True,
            "needs_key": False,
            "status": "ok",
        },
        {
            "name": "semantic_scholar",
            "configured": True,
            "needs_key": False,
            "status": "ok",
        },
    ]


# FR-01, FR-04, FR-08, D-002: Monta os três conectores das fontes acadêmicas disponíveis
def _build_sources() -> list[Source]:
    """Instancia os conectores das fontes disponíveis no servidor."""
    return [OpenAlexSource(), CrossrefSource(), SemanticScholarSource()]


# FR-01, FR-04, FR-05, FR-08, FR-09, FR-12, FR-14, NFR-06, D-002, D-003: Busca artigos nas fontes acadêmicas
@mcp.tool()
async def search_works(
    query: str,
    request_summary: str = "",
    sources: list[str] | None = None,
    max_results: int = 100,
) -> dict[str, Any]:
    """Busca artigos nas fontes acadêmicas, deduplica, grava lista e log e devolve a primeira página."""
    cfg = config.load()
    store = Store(cfg.data_dir, cfg.cache_days)
    try:
        return await run_search(
            store,
            _build_sources(),
            query=query,
            request_summary=request_summary,
            max_results=max_results,
            source_names=sources,
        )
    except RSLError as e:
        raise ToolError(f"{e.code}: {e.message}") from e


# FR-15, FR-08, FR-14, UC-04, D-002, D-005, D-010: Consulta referências ou citações de um artigo
@mcp.tool()
async def get_related_works(
    doi: str | None = None,
    work_id: str | None = None,
    direction: str = "",
    request_summary: str = "",
    sources: list[str] | None = None,
    max_results: int = 1000,
) -> dict[str, Any]:
    """Busca referências ou citações de um artigo acadêmico nas fontes, deduplica e grava lista própria."""
    cfg = config.load()
    store = Store(cfg.data_dir, cfg.cache_days)
    try:
        return await run_related(
            store,
            _build_sources(),
            direction=direction,
            doi=doi,
            work_id=work_id,
            request_summary=request_summary,
            max_results=max_results,
            source_names=sources,
        )
    except RSLError as e:
        raise ToolError(f"{e.code}: {e.message}") from e


# FR-06, FR-12, UC-01, D-002: Exporta uma lista salva para arquivo no formato solicitado
@mcp.tool()
def export_list(list_id: str, format: str) -> dict[str, Any]:
    """Exporta uma lista salva para arquivo no formato solicitado ('ris', 'csv', 'json', 'dois', 'openalex_url')."""
    cfg = config.load()
    store = Store(cfg.data_dir, cfg.cache_days)
    try:
        return run_export(
            store,
            list_id=list_id,
            export_format=format,
            export_dir=cfg.export_dir,
        )
    except RSLError as e:
        raise ToolError(f"{e.code}: {e.message}") from e


# FR-12, D-002: Mostra uma lista salva por páginas com resumo ou detalhes completos
@mcp.tool()
def get_list(
    list_id: str,
    page: int = 1,
    page_size: int = 25,
    detail: str = "summary",
) -> dict[str, Any]:
    """Mostra uma lista salva por páginas, com nível de detalhe summary ou full."""
    cfg = config.load()
    store = Store(cfg.data_dir, cfg.cache_days)
    try:
        return get_list_view(
            store,
            list_id=list_id,
            page=page,
            page_size=page_size,
            detail=detail,
        )
    except RSLError as e:
        raise ToolError(f"{e.code}: {e.message}") from e


# FR-05, FR-13, D-002: Mostra entradas do log de buscas e o caminho do log.md legível
@mcp.tool()
def get_search_log(
    search_id: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Mostra entradas do log de buscas em ordem cronológica e o caminho do arquivo legível."""
    cfg = config.load()
    store = Store(cfg.data_dir, cfg.cache_days)
    try:
        return get_search_log_view(
            store,
            search_id=search_id,
            limit=limit,
        )
    except RSLError as e:
        raise ToolError(f"{e.code}: {e.message}") from e


# FR-10, UC-01, D-002, D-003: Prompt de planejamento que orienta a IA antes de buscar
@mcp.prompt()
def plan_search(request: str) -> str:
    """Orienta a IA a planejar antes de buscar, dividir assuntos e tratar dados de fontes com segurança."""
    return render_plan_search(request)


# D-006, NFR-02: Ponto de entrada do comando rslapp via transporte stdio
def main() -> None:
    """Inicia o servidor MCP por stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
