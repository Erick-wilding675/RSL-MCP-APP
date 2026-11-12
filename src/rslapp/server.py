"""Servidor MCP do RSL.app (transporte stdio e streamable HTTP)."""

from __future__ import annotations

import contextvars
from pathlib import Path
from typing import Annotated, Any, Literal

import anyio
import uvicorn
from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecurityMiddleware, TransportSecuritySettings
from pydantic import AnyHttpUrl, BeforeValidator, ValidationInfo
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send
from typing_extensions import TypedDict

from rslapp import __version__, config, downloads, people
from rslapp.auth import (
    AuthStore,
    RSLOAuthProvider,
    RSLTokenVerifier,
    build_auth_routes,
    current_person_id,
)
from rslapp.core.errors import RSLError
from rslapp.core.find import run_find
from rslapp.core.merge import run_merge
from rslapp.core.related import run_related
from rslapp.core.repeat import run_repeat
from rslapp.core.search import run_search
from rslapp.core.views import get_list_view, get_search_log_view
from rslapp.exporters import run_export
from rslapp.prompts import INSTRUCTIONS, render_plan_search
from rslapp.sources.base import Source
from rslapp.sources.crossref import CrossrefSource
from rslapp.sources.europe_pmc import EuropePMCSource
from rslapp.sources.openalex import OpenAlexSource
from rslapp.sources.pubmed import PubmedSource
from rslapp.sources.scopus import ScopusSource
from rslapp.sources.semantic_scholar import SemanticScholarSource
from rslapp.sources.web_of_science import WebOfScienceSource
from rslapp.store import Store

# D-020, D-023: Nomes válidos de fontes acadêmicas disponíveis no servidor
SourceName = Literal[
    "openalex",
    "crossref",
    "semantic_scholar",
    "europe_pmc",
    "pubmed",
    "scopus",
    "web_of_science",
]
SourceStatus = Literal["ok", "missing_key"]


# D-002: Entradas numéricas inteiras das ferramentas recusam true/false com invalid_input
def _reject_bool(v: Any, info: ValidationInfo) -> Any:
    if isinstance(v, bool):
        prefix = f"{info.field_name} " if info.field_name else ""
        raise ValueError(f"invalid_input: {prefix}deve ser um número inteiro, não true/false")  # noqa: TRY004
    return v


NonBoolInt = Annotated[int, BeforeValidator(_reject_bool)]


# D-022, D-002: Entrada booleana recusa número no lugar de booleano com invalid_input
def _reject_int(v: Any, info: ValidationInfo) -> Any:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        prefix = f"{info.field_name} " if info.field_name else ""
        raise ValueError(f"invalid_input: {prefix}deve ser um booleano (true/false), não número")  # noqa: TRY004
    return v


NonIntBool = Annotated[bool, BeforeValidator(_reject_int)]


# D-002, FR-07, NFR-03: Estrutura de retorno de list_sources sem expor o valor de chaves
class SourceInfo(TypedDict):
    """Estado de configuração de uma fonte acadêmica."""

    name: SourceName
    configured: bool
    needs_key: bool
    status: SourceStatus


# D-006, NFR-02: Servidor MCP padrão para transporte stdio
mcp = MCPServer("rslapp", instructions=INSTRUCTIONS)

# D-012, D-014, D-015: Contexto de execução do modo HTTP para pessoa e URL pública
_http_mode_var: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "_http_mode_var", default=False
)
_http_public_url_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_http_public_url_var", default=None
)


def _is_http_mode() -> bool:
    """Indica se a ferramenta está rodando no modo HTTP (servidor HTTP ou contexto de autenticação)."""
    return _http_mode_var.get() or get_access_token() is not None


def _resolve_public_url() -> str:
    """Obtém a URL pública base do servidor HTTP para montar links de download (D-014)."""
    raw_env = config.os.environ.get("RSL_PUBLIC_URL")
    if raw_env and raw_env.strip():
        return config.load_http().public_url
    ctx_url = _http_public_url_var.get()
    if ctx_url:
        return ctx_url
    token = get_access_token()
    if token is not None and token.resource and token.resource.endswith("/mcp"):
        return token.resource[:-4]
    return config.load_http().public_url


# D-012, D-013, D-007, FR-12, FR-13: Separa buscas, listas, log e exportações por pessoa com cache compartilhado
def _resolve_person_id() -> str | None:
    """Obtém e valida o identificador da pessoa autenticada; falha se faltar pessoa no modo HTTP."""
    person_id = current_person_id()
    if person_id is None:
        if _is_http_mode():
            raise ToolError("pessoa não identificada no modo HTTP")
        return None
    try:
        return people.validate_person_id(person_id)
    except ValueError as exc:
        raise ToolError(f"invalid_input: {exc}") from exc


def _build_tool_store(cfg: config.Config | None = None) -> tuple[Store, Path]:
    """Monta o Store e a pasta de exportação conforme o modo (stdio na raiz; HTTP em people/<id>/)."""
    resolved_cfg = cfg if cfg is not None else config.load()
    person_id = _resolve_person_id()
    if person_id is None:
        return Store(resolved_cfg.data_dir, resolved_cfg.cache_days), resolved_cfg.export_dir

    people_root = (resolved_cfg.data_dir / "people").resolve()
    person_dir_resolved = (people_root / person_id).resolve()
    if person_dir_resolved.parent != people_root:
        raise ToolError("invalid_input: identificador de pessoa inválido")

    person_dir = resolved_cfg.data_dir / "people" / person_id
    shared_cache_dir = resolved_cfg.data_dir / "cache"
    return (
        Store(person_dir, resolved_cfg.cache_days, cache_dir=shared_cache_dir),
        person_dir / "exports",
    )


# D-002, D-012, FR-07, NFR-03, D-020, D-023: Lista as fontes acadêmicas indicando se estão configuradas e prontas
@mcp.tool()
def list_sources() -> list[SourceInfo]:
    """Informa para cada fonte acadêmica se está configurada, se exige chave e seu estado. A chave da Semantic Scholar é opcional e evita recusas por limite; a do PubMed também é opcional. PubMed e Europe PMC são bases de saúde e ciências da vida e entram quando pedidas. Scopus e Web of Science são bases pagas e só funcionam com a chave e a assinatura do próprio usuário ou da instituição dele."""
    _resolve_person_id()
    cfg = config.load()
    openalex_configured = cfg.openalex_key_configured
    sources: list[SourceInfo] = [
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
        {
            "name": "europe_pmc",
            "configured": True,
            "needs_key": False,
            "status": "ok",
        },
        {
            "name": "pubmed",
            "configured": True,
            "needs_key": False,
            "status": "ok",
        },
    ]
    # D-023: No modo stdio lista as 7 fontes; no modo HTTP não lista as bases pagas
    if not _is_http_mode():
        scopus_configured = cfg.scopus_key_configured
        wos_configured = cfg.wos_key_configured
        sources.extend(
            [
                {
                    "name": "scopus",
                    "configured": scopus_configured,
                    "needs_key": True,
                    "status": "ok" if scopus_configured else "missing_key",
                },
                {
                    "name": "web_of_science",
                    "configured": wos_configured,
                    "needs_key": True,
                    "status": "ok" if wos_configured else "missing_key",
                },
            ]
        )
    return sources


# FR-01, FR-04, FR-08, D-002, D-020, D-023: Monta os conectores das fontes acadêmicas disponíveis
def _build_sources() -> list[Source]:
    """Instancia os conectores das fontes disponíveis no servidor (as bases pagas entram apenas no modo stdio)."""
    sources: list[Source] = [
        OpenAlexSource(),
        CrossrefSource(),
        SemanticScholarSource(),
        EuropePMCSource(),
        PubmedSource(),
    ]
    if not _is_http_mode():
        sources.extend([
            ScopusSource(),
            WebOfScienceSource(),
        ])
    return sources


# FR-01, FR-04, FR-05, FR-08, FR-09, FR-12, FR-14, NFR-06, D-002, D-003, D-012, D-013, D-020, D-022, D-023: Busca artigos nas fontes acadêmicas
@mcp.tool()
async def search_works(
    query: str,
    request_summary: str = "",
    sources: list[str] | None = None,
    max_results: NonBoolInt = 100,
    include_peer_review: NonIntBool = False,
) -> dict[str, Any]:
    """Busca artigos nas fontes acadêmicas, deduplica, grava lista e log e devolve a primeira página. Pareceres de revisão por pares ficam de fora por padrão; use include_peer_review=True apenas para quem estuda o processo de revisão por pares. Quando o tema for de saúde, medicina ou biologia, vale pedir também pubmed e europe_pmc em sources. As bases pagas scopus e web_of_science entram quando a pessoa pedir e tiver configurado as chaves (list_sources mostra); o Web of Science não traz resumo nem afiliações."""
    # D-023: No modo HTTP, recusa scopus e web_of_science antes de chamar qualquer fonte
    if _is_http_mode() and sources is not None:
        for s in sources:
            if isinstance(s, str) and s.strip() in ("scopus", "web_of_science"):
                raise ToolError(
                    "invalid_input: scopus e web_of_science só funcionam no RSL.app instalado no seu computador, com a sua chave e o acesso da sua instituição (D-023)"
                )
    store, _ = _build_tool_store()
    try:
        return await run_search(
            store,
            _build_sources(),
            query=query,
            request_summary=request_summary,
            max_results=max_results,
            source_names=sources,
            include_peer_review=include_peer_review,
        )
    except RSLError as e:
        raise ToolError(f"{e.code}: {e.message}") from e


# FR-15, FR-08, FR-14, UC-04, D-002, D-005, D-010, D-012, D-013, D-020: Consulta referências ou citações de um artigo
@mcp.tool()
async def get_related_works(
    doi: str | None = None,
    work_id: str | None = None,
    direction: str = "",
    request_summary: str = "",
    sources: list[str] | None = None,
    max_results: NonBoolInt = 1000,
) -> dict[str, Any]:
    """Busca referências ou citações de um artigo acadêmico nas fontes, deduplica e grava lista própria."""
    # D-020, D-023: pubmed, europe_pmc, scopus e web_of_science não são suportadas em get_related_works
    if sources is not None:
        for s in sources:
            if isinstance(s, str) and s.strip() in (
                "pubmed",
                "europe_pmc",
                "scopus",
                "web_of_science",
            ):
                raise ToolError(f"invalid_input: fonte não suportada nesta ferramenta: {s.strip()}")
    store, _ = _build_tool_store()
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

# FR-02, UC-02, D-002, D-012, D-013, D-020: Encontra um artigo específico por título ou DOI
@mcp.tool()
async def find_work(
    title: str | None = None,
    doi: str | None = None,
    request_summary: str = "",
    sources: list[str] | None = None,
    max_results: NonBoolInt = 10,
) -> dict[str, Any]:
    """Busca um artigo específico por título ou DOI nas fontes, deduplica candidatos e grava lista própria."""
    # D-020, D-023: pubmed, europe_pmc, scopus e web_of_science não são suportadas em find_work
    if sources is not None:
        for s in sources:
            if isinstance(s, str) and s.strip() in (
                "pubmed",
                "europe_pmc",
                "scopus",
                "web_of_science",
            ):
                raise ToolError(f"invalid_input: fonte não suportada nesta ferramenta: {s.strip()}")
    store, _ = _build_tool_store()
    try:
        return await run_find(
            store,
            _build_sources(),
            title=title,
            doi=doi,
            request_summary=request_summary,
            max_results=max_results,
            source_names=sources,
        )
    except RSLError as e:
        raise ToolError(f"{e.code}: {e.message}") from e


# FR-11, UC-03, D-002, D-012, D-013, D-023: Repete uma busca salva do log com os mesmos parâmetros
@mcp.tool()
async def repeat_search(
    search_id: str,
) -> dict[str, Any]:
    """Repete uma busca salva do log com as mesmas strings e fontes, gravando busca e lista novas."""
    store, _ = _build_tool_store()
    # D-023: No modo HTTP, recusa scopus e web_of_science antes de chamar qualquer fonte
    if _is_http_mode():
        clean_id = search_id.strip() if isinstance(search_id, str) else ""
        if clean_id:
            try:
                orig = store.get_search(clean_id)
                orig_params = orig.get("params") or {}
                orig_sources = orig_params.get("sources") or []
            except (FileNotFoundError, ValueError, OSError):
                orig_sources = []
            for s in orig_sources:
                if isinstance(s, str) and s.strip() in ("scopus", "web_of_science"):
                    raise ToolError(
                        "invalid_input: scopus e web_of_science só funcionam no RSL.app instalado no seu computador, com a sua chave e o acesso da sua instituição (D-023)"
                    )
    try:
        return await run_repeat(
            store,
            _build_sources(),
            search_id=search_id,
        )
    except RSLError as e:
        raise ToolError(f"{e.code}: {e.message}") from e


# D-021, FR-04, FR-05, FR-12, FR-13, D-012: Junta listas salvas numa lista nova sem duplicatas
@mcp.tool()
async def merge_lists(
    list_ids: list[str],
    request_summary: str = "",
) -> dict[str, Any]:
    """Une listas salvas de buscas diferentes numa lista nova e sem duplicatas (D-021). Aceita de 2 a 20 listas sem repetir."""
    store, _ = _build_tool_store()
    try:
        return await run_merge(
            store,
            list_ids=list_ids,
            request_summary=request_summary,
        )
    except RSLError as e:
        raise ToolError(f"{e.code}: {e.message}") from e


# FR-06, FR-12, UC-01, D-002, D-012, D-013, D-014: Exporta uma lista salva (caminho no stdio; link assinado no HTTP)
@mcp.tool()
def export_list(list_id: str, format: str) -> dict[str, Any]:
    """Exporta uma lista salva para arquivo no formato solicitado ('ris', 'csv', 'json', 'dois', 'openalex_url', 'bibtex')."""
    cfg = config.load()
    person_id = _resolve_person_id()
    store, export_dir = _build_tool_store(cfg)

    # D-012, D-014, FR-06: No modo HTTP, apaga exportações antigas da própria pessoa antes de gravar
    if person_id is not None:
        downloads.clean_expired_exports(export_dir)

    try:
        result = run_export(
            store,
            list_id=list_id,
            export_format=format,
            export_dir=export_dir,
        )
    except RSLError as e:
        raise ToolError(f"{e.code}: {e.message}") from e

    # D-014, D-012, FR-06: No modo HTTP, devolve download_url e expires_at no lugar de path
    if person_id is not None:
        exported_path = Path(str(result.pop("path")))
        download_url, expires_at = downloads.create_download_link(
            person_id,
            exported_path.name,
            public_url=_resolve_public_url(),
            data_dir=cfg.data_dir,
        )
        result["download_url"] = download_url
        result["expires_at"] = expires_at
    return result


# FR-12, D-002, D-012: Mostra uma lista salva por páginas com resumo ou detalhes completos
@mcp.tool()
def get_list(
    list_id: str,
    page: NonBoolInt = 1,
    page_size: NonBoolInt = 25,
    detail: str = "summary",
) -> dict[str, Any]:
    """Mostra uma lista salva por páginas, com nível de detalhe summary ou full."""
    store, _ = _build_tool_store()
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


# FR-05, FR-13, D-002, D-012, D-014: Mostra entradas do log de buscas (caminho no stdio; link assinado no HTTP)
@mcp.tool()
def get_search_log(
    search_id: str | None = None,
    limit: NonBoolInt = 20,
) -> dict[str, Any]:
    """Mostra entradas do log de buscas em ordem cronológica e o caminho do arquivo legível."""
    cfg = config.load()
    person_id = _resolve_person_id()
    store, _ = _build_tool_store(cfg)
    try:
        result = get_search_log_view(
            store,
            search_id=search_id,
            limit=limit,
        )
    except RSLError as e:
        raise ToolError(f"{e.code}: {e.message}") from e

    # D-014, D-012, FR-05, FR-13: No modo HTTP, devolve log_download_url e expires_at no lugar de log_file
    if person_id is not None:
        result.pop("log_file", None)
        log_download_url, expires_at = downloads.create_log_download_link(
            person_id,
            public_url=_resolve_public_url(),
            data_dir=cfg.data_dir,
        )
        result["log_download_url"] = log_download_url
        result["expires_at"] = expires_at
    return result


# FR-10, UC-01, D-002, D-003: Prompt de planejamento que orienta a IA antes de buscar
@mcp.prompt()
def plan_search(request: str) -> str:
    """Orienta a IA a planejar antes de buscar, dividir assuntos e tratar dados de fontes com segurança."""
    return render_plan_search(request)


# D-011, D-017: Rota /health para verificação do servidor HTTP e healthcheck do Docker
@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request: Request) -> Response:
    """Devolve 200 com status e version, sem nenhum outro dado."""
    return JSONResponse({"status": "ok", "version": __version__})


# D-014, D-012, FR-06: Rota GET /downloads/{token} sem login, protegida pela assinatura HMAC-SHA256
@mcp.custom_route("/downloads/{token}", methods=["GET"])
async def download_export(request: Request) -> Response:
    """Entrega o arquivo exportado se o token HMAC-SHA256 for válido, ativo e dentro do prazo."""
    return await downloads.handle_download(request)


# D-011, D-017: Proteção contra DNS rebinding aceitando o host de RSL_PUBLIC_URL (puro e :*) e loopback
def build_transport_security(public_url: str) -> TransportSecuritySettings:
    """Monta TransportSecuritySettings com os hosts de loopback e o host de RSL_PUBLIC_URL."""
    scheme, public_host = config.parse_public_url_host(public_url)
    allowed_hosts = [
        "127.0.0.1",
        "127.0.0.1:*",
        "localhost",
        "localhost:*",
        "[::1]",
        "[::1]:*",
    ]
    for candidate in (public_host, f"{public_host}:*"):
        if candidate not in allowed_hosts:
            allowed_hosts.append(candidate)

    allowed_origins = [
        "http://127.0.0.1",
        "http://127.0.0.1:*",
        "http://localhost",
        "http://localhost:*",
        "http://[::1]",
        "http://[::1]:*",
    ]
    for origin_candidate in (f"{scheme}://{public_host}", f"{scheme}://{public_host}:*"):
        if origin_candidate not in allowed_origins:
            allowed_origins.append(origin_candidate)

    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )


# D-011, D-017: Protege todas as rotas HTTP contra DNS rebinding conferindo Host em todas e Origin em /mcp e POST /login
class _HostOriginProtectionASGIApp:
    """Valida Host em todas as rotas e Origin em /mcp e POST /login contra DNS rebinding."""

    def __init__(self, app: ASGIApp, security: TransportSecuritySettings) -> None:
        self._app = app
        self._validator = TransportSecurityMiddleware(security)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            request = Request(scope, receive)
            if self._validator.settings.enable_dns_rebinding_protection:
                host = request.headers.get("host")
                if not self._validator._validate_host(host):
                    resp = Response("Invalid Host header", status_code=421)
                    await resp(scope, receive, send)
                    return

                path = scope.get("path", "")
                method = scope.get("method", "GET").upper()
                if (path == "/mcp" or path.startswith("/mcp/")) or (method == "POST" and path == "/login"):
                    origin = request.headers.get("origin")
                    if not self._validator._validate_origin(origin):
                        resp = Response("Invalid Origin header", status_code=403)
                        await resp(scope, receive, send)
                        return
        token = _http_mode_var.set(True)
        try:
            await self._app(scope, receive, send)
        finally:
            _http_mode_var.reset(token)


class _HttpMCPServer(MCPServer):
    """MCPServer do modo HTTP que marca o contexto de execução das ferramentas como HTTP (D-012, D-014)."""

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        context: Any = None,
    ) -> Any:
        mode_token = _http_mode_var.set(True)
        issuer = str(self.settings.auth.issuer_url).rstrip("/") if self.settings.auth else None
        url_token = _http_public_url_var.set(issuer)
        try:
            return await super().call_tool(name, arguments, context)
        finally:
            _http_public_url_var.reset(url_token)
            _http_mode_var.reset(mode_token)


# D-006, D-012, D-015, D-016: Monta um MCPServer pelo construtor com token_verifier e AuthSettings sem duplicar ferramentas
def _build_http_mcp_server(
    *,
    token_verifier: RSLTokenVerifier,
    auth: AuthSettings,
) -> MCPServer:
    """Instancia um MCPServer com token_verifier e AuthSettings compartilhando as ferramentas registradas."""
    http_mcp = _HttpMCPServer(
        "rslapp",
        instructions=INSTRUCTIONS,
        token_verifier=token_verifier,
        auth=auth,
    )
    for tool_fn in (
        list_sources,
        search_works,
        get_related_works,
        find_work,
        repeat_search,
        merge_lists,
        export_list,
        get_list,
        get_search_log,
    ):
        http_mcp.add_tool(tool_fn)
    http_mcp.prompt()(plan_search)
    http_mcp.custom_route("/health", methods=["GET"])(health_check)
    http_mcp.custom_route("/downloads/{token}", methods=["GET"])(download_export)
    return http_mcp


# D-011, D-015, D-016, D-006: Cria a aplicação ASGI unificando Resource Server MCP e Authorization Server OAuth 2.1
def create_http_app(
    http_cfg: config.HttpConfig | None = None,
    *,
    auth_store: AuthStore | None = None,
    oauth_provider: RSLOAuthProvider | None = None,
) -> Starlette:
    """Cria a aplicação ASGI Streamable HTTP (/mcp) protegida por OAuth 2.1 e com rotas /login."""
    cfg = http_cfg if http_cfg is not None else config.load_http()
    security = build_transport_security(cfg.public_url)

    public_url = cfg.public_url.rstrip("/")
    resource_server_url = f"{public_url}/mcp"
    store = (
        auth_store
        if auth_store is not None
        else AuthStore(access_token_minutes=cfg.access_token_minutes)
    )
    downloads.load_secret_key(store.data_dir)
    verifier = RSLTokenVerifier(store, resource_server_url=resource_server_url)
    auth_settings = AuthSettings(
        issuer_url=AnyHttpUrl(public_url),
        resource_server_url=AnyHttpUrl(resource_server_url),
        required_scopes=["rsl"],
        validate_token_resource=True,
    )
    provider = (
        oauth_provider
        if oauth_provider is not None
        else RSLOAuthProvider(store, public_url=public_url)
    )

    http_mcp = _build_http_mcp_server(
        token_verifier=verifier,
        auth=auth_settings,
    )
    app = http_mcp.streamable_http_app(
        transport_security=security,
        host=cfg.host,
    )

    app.router.routes.extend(build_auth_routes(provider, issuer_url=public_url))
    app.state.auth_store = store
    app.state.oauth_provider = provider
    app.state.token_verifier = verifier

    # D-011, D-017: Protege todas as rotas HTTP contra DNS rebinding antes de middlewares e rotas
    app.user_middleware.insert(
        0,
        Middleware(_HostOriginProtectionASGIApp, security=security),
    )
    return app


# D-011, D-017: Configura o uvicorn em processo único com proxy_headers e forwarded_allow_ips
def build_uvicorn_config(http_cfg: config.HttpConfig) -> uvicorn.Config:
    """Monta o uvicorn.Config com cabeçalhos de proxy ligados para uso atrás do Caddy."""
    app = create_http_app(http_cfg)
    return uvicorn.Config(
        app,
        host=http_cfg.host,
        port=http_cfg.port,
        proxy_headers=True,
        forwarded_allow_ips=http_cfg.forwarded_allow_ips,
        log_level=mcp.settings.log_level.lower(),
    )


# D-011, D-015, D-017: Inicia o servidor MCP em modo HTTP aceitando host não-loopback apenas com https://
def run_http(*, host: str | None = None, port: int | None = None) -> None:
    """Valida o host de escuta conforme RSL_PUBLIC_URL e executa o servidor HTTP num processo único."""
    http_cfg = config.load_http(host=host, port=port)
    config.validate_http_host(http_cfg.host, http_cfg.public_url)
    uvicorn_cfg = build_uvicorn_config(http_cfg)
    uv_server = uvicorn.Server(uvicorn_cfg)
    anyio.run(uv_server.serve)


# D-006, NFR-02: Ponto de entrada do comando rslapp via transporte stdio
def main() -> None:
    """Inicia o servidor MCP por stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
