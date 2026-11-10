"""Provedor OAuth 2.1, rotas de autorização e tela de login do RSL.app."""

from __future__ import annotations

import html
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from mcp.server.auth.provider import (
    AuthorizationParams,
    AuthorizeError,
    OAuthAuthorizationServerProvider,
    TokenError,
    construct_redirect_uri,
)
from mcp.server.auth.routes import create_auth_routes
from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyHttpUrl
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.routing import Route

from rslapp import people
from rslapp.auth.store import (
    AuthStore,
    RSLAccessToken,
    RSLAuthorizationCode,
    RSLRefreshToken,
    normalize_resource_url,
)

PENDING_AUTH_TTL_SECONDS = 600
MAX_PENDING_AUTH_REQUESTS = 1000
AUTH_CODE_TTL_SECONDS = 300
MAX_WRONG_CODES_PER_REQUEST = 5
MAX_WRONG_CODES_PER_IP = 20
IP_RATE_LIMIT_WINDOW_SECONDS = 900

_NO_STORE_HEADERS = {
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "frame-ancestors 'none'",
}


# D-015: Pedido de autorização mantido apenas em memória por até 10 minutos
@dataclass
class PendingAuthRequest:
    """Estado em memória de um pedido /authorize aguardando o código pessoal em /login."""

    req_id: str
    client_id: str
    client_name: str
    params: AuthorizationParams
    scopes: list[str]
    resource: str
    expires_at: float
    failed_attempts: int = 0

    def __repr__(self) -> str:
        return (
            f"PendingAuthRequest(client_id={self.client_id!r}, "
            f"client_name={self.client_name!r}, scopes={self.scopes!r}, "
            f"failed_attempts={self.failed_attempts!r})"
        )


def _extract_client_ip(request: Request) -> str:
    """Extrai o IP do cliente apenas em memória para limitação de tentativas."""
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


# D-015: Página HTML simples em português, sem nenhum ativo externo (sem CDN, fontes ou scripts)
def _render_login_html(
    *,
    req_id: str,
    client_name: str,
    error_message: str | None = None,
) -> str:
    """Gera o HTML autocontido da tela de login em português."""
    safe_req = html.escape(req_id, quote=True)
    safe_client = html.escape(client_name or "Conector MCP", quote=True)
    error_block = ""
    if error_message:
        safe_error = html.escape(error_message, quote=True)
        error_block = f'<p class="error" role="alert">{safe_error}</p>'

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Entrar no RSL.app</title>
  <style>
    body {{
      font-family: system-ui, -apple-system, sans-serif;
      background-color: #f6f7f9;
      color: #1a1d21;
      margin: 0;
      padding: 2rem 1rem;
      display: flex;
      justify-content: center;
      align-items: flex-start;
      min-height: 100vh;
    }}
    main {{
      background: #ffffff;
      border: 1px solid #d8dee4;
      border-radius: 8px;
      max-width: 420px;
      width: 100%;
      padding: 1.75rem;
      box-sizing: border-box;
    }}
    h1 {{
      font-size: 1.25rem;
      margin: 0 0 0.75rem 0;
    }}
    p {{
      font-size: 0.95rem;
      line-height: 1.45;
      margin: 0 0 1rem 0;
    }}
    .connector {{
      font-weight: 600;
    }}
    .error {{
      background: #fff1f0;
      border: 1px solid #ffa39e;
      color: #a8071a;
      padding: 0.65rem 0.75rem;
      border-radius: 6px;
    }}
    label {{
      display: block;
      font-size: 0.9rem;
      font-weight: 600;
      margin-bottom: 0.4rem;
    }}
    input[type="password"] {{
      width: 100%;
      padding: 0.6rem 0.7rem;
      font-size: 1rem;
      border: 1px solid #8c959f;
      border-radius: 6px;
      box-sizing: border-box;
      margin-bottom: 1rem;
    }}
    button {{
      width: 100%;
      padding: 0.65rem 1rem;
      font-size: 1rem;
      font-weight: 600;
      color: #ffffff;
      background-color: #0969da;
      border: none;
      border-radius: 6px;
      cursor: pointer;
    }}
    button:hover {{
      background-color: #0550ae;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Conectar ao RSL.app</h1>
    <p>O conector <span class="connector">{safe_client}</span> está pedindo acesso ao RSL.app.</p>
    {error_block}
    <form method="post" action="/login?req={safe_req}">
      <input type="hidden" name="req" value="{safe_req}">
      <label for="code">Código pessoal</label>
      <input id="code" name="code" type="password" autocomplete="off" required autofocus>
      <button type="submit">Autorizar acesso</button>
    </form>
  </main>
</body>
</html>
"""


def _render_message_html(*, title: str, message: str) -> str:
    """Gera uma página HTML simples de erro ou aviso em português."""
    safe_title = html.escape(title, quote=True)
    safe_message = html.escape(message, quote=True)
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title} - RSL.app</title>
  <style>
    body {{
      font-family: system-ui, -apple-system, sans-serif;
      background-color: #f6f7f9;
      color: #1a1d21;
      margin: 0;
      padding: 2rem 1rem;
      display: flex;
      justify-content: center;
      align-items: flex-start;
      min-height: 100vh;
    }}
    main {{
      background: #ffffff;
      border: 1px solid #d8dee4;
      border-radius: 8px;
      max-width: 420px;
      width: 100%;
      padding: 1.75rem;
      box-sizing: border-box;
    }}
    h1 {{
      font-size: 1.25rem;
      margin: 0 0 0.75rem 0;
    }}
    p {{
      font-size: 0.95rem;
      line-height: 1.45;
      margin: 0;
    }}
  </style>
</head>
<body>
  <main>
    <h1>{safe_title}</h1>
    <p role="alert">{safe_message}</p>
  </main>
</body>
</html>
"""


# D-015, D-016, D-012: Provedor OAuth 2.1 que valida o código pessoal e emite tokens rotativos
class RSLOAuthProvider(
    OAuthAuthorizationServerProvider[RSLAuthorizationCode, RSLRefreshToken, RSLAccessToken]
):
    """Provedor do Authorization Server OAuth 2.1 integrado ao cadastro de pessoas."""

    def __init__(
        self,
        store: AuthStore,
        *,
        public_url: str,
        time_fn: Callable[[], float] | None = None,
    ) -> None:
        self._store = store
        self._public_url = public_url.strip().rstrip("/")
        self._resource_server_url = f"{self._public_url}/mcp"
        self._time_fn = time_fn or time.time
        # Estruturas mantidas exclusivamente em memória (D-015, D-016)
        self._pending_requests: dict[str, PendingAuthRequest] = {}
        self._auth_codes: dict[str, RSLAuthorizationCode] = {}
        self._ip_failures: dict[str, list[float]] = {}

    @property
    def store(self) -> AuthStore:
        """Armazenamento subjacente de clientes e tokens."""
        return self._store

    @property
    def public_url(self) -> str:
        """URL pública base do servidor."""
        return self._public_url

    @property
    def resource_server_url(self) -> str:
        """URL canônica do endpoint MCP protegido."""
        return self._resource_server_url

    def _now_ts(self) -> float:
        return float(self._time_fn())

    def _prune_expired_memory_state(self, now_ts: float) -> None:
        """Remove pedidos de autorização, códigos e contadores de IP já expirados da memória."""
        expired_reqs = [
            req_id
            for req_id, req in self._pending_requests.items()
            if now_ts >= req.expires_at
        ]
        for req_id in expired_reqs:
            self._pending_requests.pop(req_id, None)

        expired_codes = [
            code
            for code, auth_code in self._auth_codes.items()
            if now_ts >= auth_code.expires_at
        ]
        for code in expired_codes:
            self._auth_codes.pop(code, None)

        cutoff = now_ts - IP_RATE_LIMIT_WINDOW_SECONDS
        for ip in list(self._ip_failures.keys()):
            recent = [ts for ts in self._ip_failures[ip] if ts > cutoff]
            if recent:
                self._ip_failures[ip] = recent
            else:
                self._ip_failures.pop(ip, None)

    def _is_ip_rate_limited(self, ip: str, now_ts: float) -> bool:
        cutoff = now_ts - IP_RATE_LIMIT_WINDOW_SECONDS
        recent = [ts for ts in self._ip_failures.get(ip, []) if ts > cutoff]
        if recent:
            self._ip_failures[ip] = recent
        else:
            self._ip_failures.pop(ip, None)
        return len(recent) >= MAX_WRONG_CODES_PER_IP

    def _record_ip_failure(self, ip: str, now_ts: float) -> int:
        cutoff = now_ts - IP_RATE_LIMIT_WINDOW_SECONDS
        recent = [ts for ts in self._ip_failures.get(ip, []) if ts > cutoff]
        recent.append(now_ts)
        self._ip_failures[ip] = recent
        return len(recent)

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        """Busca um cliente OAuth registrado."""
        return self._store.get_client(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        """Registra dinamicamente um cliente OAuth."""
        self._store.save_client(client_info)

    # D-015: Guarda o pedido em memória por até 10 minutos e redireciona para /login?req=<id>
    async def authorize(
        self,
        client: OAuthClientInformationFull,
        params: AuthorizationParams,
    ) -> str:
        """Registra o pedido de autorização em memória e devolve a URL da tela de login."""
        now_ts = self._now_ts()
        self._prune_expired_memory_state(now_ts)

        if params.resource is not None:
            normalized_resource = normalize_resource_url(params.resource)
            if normalized_resource != self._resource_server_url:
                raise AuthorizeError(
                    error="invalid_target",
                    error_description="O recurso solicitado não corresponde ao endpoint /mcp deste servidor",
                )
        resource = self._resource_server_url

        if len(self._pending_requests) >= MAX_PENDING_AUTH_REQUESTS:
            raise AuthorizeError(
                error="temporarily_unavailable",
                error_description="Muitos pedidos de autorização pendentes; tente novamente em instantes",
            )

        req_id = secrets.token_urlsafe(24)
        scopes = list(params.scopes) if params.scopes else ["rsl"]

        self._pending_requests[req_id] = PendingAuthRequest(
            req_id=req_id,
            client_id=client.client_id,
            client_name=client.client_name or client.client_id,
            params=params,
            scopes=scopes,
            resource=resource,
            expires_at=now_ts + PENDING_AUTH_TTL_SECONDS,
        )
        return f"{self._public_url}/login?{urlencode({'req': req_id})}"

    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str,
    ) -> RSLAuthorizationCode | None:
        """Carrega um código de autorização em memória se existir, não tiver vencido e for do cliente."""
        now_ts = self._now_ts()
        auth_code = self._auth_codes.get(authorization_code)
        if auth_code is None:
            return None
        if now_ts >= auth_code.expires_at:
            self._auth_codes.pop(authorization_code, None)
            return None
        if auth_code.client_id != client.client_id:
            return None
        return auth_code

    # D-015, D-016: Código de autorização vale uma única vez e gera access + refresh token
    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: RSLAuthorizationCode,
    ) -> OAuthToken:
        """Consome o código de autorização (uso único) e emite os tokens da sessão."""
        now_ts = self._now_ts()
        stored_code = self._auth_codes.pop(authorization_code.code, None)
        if stored_code is None or now_ts >= stored_code.expires_at:
            raise TokenError(
                error="invalid_grant",
                error_description="Código de autorização inválido ou expirado",
            )
        if stored_code.client_id != client.client_id:
            raise TokenError(
                error="invalid_grant",
                error_description="Código de autorização não pertence a este cliente",
            )

        person = people.get(stored_code.person_id, data_dir=self._store.data_dir)
        if person is None or not person.is_active:
            raise TokenError(
                error="invalid_grant",
                error_description="Acesso não autorizado",
            )

        return self._store.issue_token_pair(
            person_id=stored_code.person_id,
            client_id=client.client_id,
            scopes=stored_code.scopes,
            resource=stored_code.resource,
        )

    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
    ) -> RSLRefreshToken | None:
        """Carrega e valida um refresh token pertencente ao cliente."""
        token_obj = self._store.verify_refresh_token(refresh_token)
        if token_obj is None or token_obj.client_id != client.client_id:
            return None
        return token_obj

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RSLRefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        """Gira o refresh token, invalidando o anterior e emitindo um novo par."""
        if refresh_token.client_id != client.client_id:
            raise TokenError(
                error="invalid_grant",
                error_description="Token de renovação inválido",
            )
        rotated = self._store.rotate_refresh_token(
            old_refresh_token_hash=refresh_token._token_hash,
            scopes=scopes,
        )
        if rotated is None:
            raise TokenError(
                error="invalid_grant",
                error_description="Token de renovação inválido ou revogado",
            )
        return rotated

    async def load_access_token(self, token: str) -> RSLAccessToken | None:
        """Carrega um access token para revogação ou inspeção."""
        return self._store.verify_access_token(
            token,
            expected_resource=self._resource_server_url,
        )

    async def revoke_token(self, token: RSLAccessToken | RSLRefreshToken) -> None:
        """Revoga um access token ou refresh token removendo seu hash do disco."""
        self._store.revoke_by_hash(token._token_hash)

    # D-015: Tela de login GET /login
    async def handle_login_get(self, request: Request) -> Response:
        """Exibe a página HTML de login para um pedido de autorização pendente."""
        now_ts = self._now_ts()
        self._prune_expired_memory_state(now_ts)

        client_ip = _extract_client_ip(request)
        if self._is_ip_rate_limited(client_ip, now_ts):
            return HTMLResponse(
                _render_message_html(
                    title="Muitas tentativas",
                    message=(
                        "Muitas tentativas com código inválido a partir deste endereço. "
                        "Aguarde 15 minutos antes de tentar novamente."
                    ),
                ),
                status_code=429,
                headers=_NO_STORE_HEADERS,
            )

        req_id = request.query_params.get("req", "").strip()
        pending = self._pending_requests.get(req_id)
        if pending is None or now_ts >= pending.expires_at:
            self._pending_requests.pop(req_id, None)
            return HTMLResponse(
                _render_message_html(
                    title="Pedido inválido ou expirado",
                    message=(
                        "Este pedido de autorização não existe ou já expirou. "
                        "Volte ao conector e inicie a conexão novamente."
                    ),
                ),
                status_code=400,
                headers=_NO_STORE_HEADERS,
            )

        if pending.failed_attempts >= MAX_WRONG_CODES_PER_REQUEST:
            return HTMLResponse(
                _render_message_html(
                    title="Limite de tentativas excedido",
                    message=(
                        "O limite de tentativas para este pedido de autorização foi atingido. "
                        "Inicie um novo pedido no conector."
                    ),
                ),
                status_code=429,
                headers=_NO_STORE_HEADERS,
            )

        return HTMLResponse(
            _render_login_html(req_id=req_id, client_name=pending.client_name),
            status_code=200,
            headers=_NO_STORE_HEADERS,
        )

    # D-015, D-012: Validação do código pessoal em POST /login com limite de tentativas em memória
    async def handle_login_post(self, request: Request) -> Response:
        """Valida o código pessoal informado e redireciona com o código de autorização OAuth."""
        form_data: dict[str, Any] = dict(await request.form())
        req_id = str(form_data.get("req") or request.query_params.get("req") or "").strip()
        submitted_code = str(form_data.get("code") or "")

        now_ts = self._now_ts()
        self._prune_expired_memory_state(now_ts)

        client_ip = _extract_client_ip(request)
        if self._is_ip_rate_limited(client_ip, now_ts):
            return HTMLResponse(
                _render_message_html(
                    title="Muitas tentativas",
                    message=(
                        "Muitas tentativas com código inválido a partir deste endereço. "
                        "Aguarde 15 minutos antes de tentar novamente."
                    ),
                ),
                status_code=429,
                headers=_NO_STORE_HEADERS,
            )

        pending = self._pending_requests.get(req_id)
        if pending is None or now_ts >= pending.expires_at:
            self._pending_requests.pop(req_id, None)
            return HTMLResponse(
                _render_message_html(
                    title="Pedido inválido ou expirado",
                    message=(
                        "Este pedido de autorização não existe ou já expirou. "
                        "Volte ao conector e inicie a conexão novamente."
                    ),
                ),
                status_code=400,
                headers=_NO_STORE_HEADERS,
            )

        if pending.failed_attempts >= MAX_WRONG_CODES_PER_REQUEST:
            return HTMLResponse(
                _render_message_html(
                    title="Limite de tentativas excedido",
                    message=(
                        "O limite de tentativas para este pedido de autorização foi atingido. "
                        "Inicie um novo pedido no conector."
                    ),
                ),
                status_code=429,
                headers=_NO_STORE_HEADERS,
            )

        person = people.find_by_code(submitted_code, data_dir=self._store.data_dir)
        if person is None:
            pending.failed_attempts += 1
            ip_count = self._record_ip_failure(client_ip, now_ts)
            if (
                pending.failed_attempts >= MAX_WRONG_CODES_PER_REQUEST
                or ip_count >= MAX_WRONG_CODES_PER_IP
            ):
                return HTMLResponse(
                    _render_message_html(
                        title="Limite de tentativas excedido",
                        message=(
                            "Muitas tentativas com código inválido. "
                            "Aguarde ou inicie um novo pedido de autorização no conector."
                        ),
                    ),
                    status_code=429,
                    headers=_NO_STORE_HEADERS,
                )

            return HTMLResponse(
                _render_login_html(
                    req_id=req_id,
                    client_name=pending.client_name,
                    error_message="Código inválido. Verifique seu código pessoal e tente novamente.",
                ),
                status_code=200,
                headers=_NO_STORE_HEADERS,
            )

        # Código válido de pessoa ativa: consome o pedido pendente e emite código de uso único (5 min)
        self._pending_requests.pop(req_id, None)
        raw_auth_code = secrets.token_urlsafe(32)
        self._auth_codes[raw_auth_code] = RSLAuthorizationCode(
            code=raw_auth_code,
            scopes=list(pending.scopes),
            expires_at=now_ts + AUTH_CODE_TTL_SECONDS,
            client_id=pending.client_id,
            code_challenge=pending.params.code_challenge,
            redirect_uri=pending.params.redirect_uri,
            redirect_uri_provided_explicitly=pending.params.redirect_uri_provided_explicitly,
            resource=pending.resource,
            person_id=person.id,
        )

        redirect_url = construct_redirect_uri(
            str(pending.params.redirect_uri),
            code=raw_auth_code,
            state=pending.params.state,
        )
        return RedirectResponse(
            url=redirect_url,
            status_code=302,
            headers=_NO_STORE_HEADERS,
        )


# D-015: Monta as rotas de create_auth_routes do SDK v2 mais /login (GET e POST)
def build_auth_routes(
    provider: RSLOAuthProvider,
    *,
    issuer_url: str | None = None,
) -> list[Route]:
    """Cria as rotas OAuth 2.1 do SDK (DCR e revogação ligados) somadas às rotas /login."""
    effective_issuer = (issuer_url or provider.public_url).strip().rstrip("/")
    sdk_routes = create_auth_routes(
        provider=provider,
        issuer_url=AnyHttpUrl(effective_issuer),
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=["rsl"],
            default_scopes=["rsl"],
        ),
        revocation_options=RevocationOptions(enabled=True),
    )
    login_routes = [
        Route("/login", endpoint=provider.handle_login_get, methods=["GET"]),
        Route("/login", endpoint=provider.handle_login_post, methods=["POST"]),
    ]
    return [*sdk_routes, *login_routes]
