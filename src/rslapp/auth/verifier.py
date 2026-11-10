"""Verificador de tokens OAuth 2.1 por requisição e leitura da pessoa autenticada."""

from __future__ import annotations

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import TokenVerifier

from rslapp.auth.store import AuthStore, RSLAccessToken, normalize_resource_url


# D-015, D-016: Verificação por requisição contra <RSL_DATA_DIR>/auth/ e people.json
class RSLTokenVerifier(TokenVerifier):
    """Verifica tokens de acesso em cada chamada a /mcp sem depender de cache em memória."""

    def __init__(self, store: AuthStore, *, resource_server_url: str) -> None:
        self._store = store
        self._resource_server_url = normalize_resource_url(resource_server_url) or ""

    @property
    def resource_server_url(self) -> str:
        """URL canônica do Resource Server (/mcp) exigida no campo resource do token."""
        return self._resource_server_url

    async def verify_token(self, token: str) -> RSLAccessToken | None:
        """Devolve o RSLAccessToken se válido, para este /mcp e de pessoa ativa; caso contrário, None."""
        return self._store.verify_access_token(
            token,
            expected_resource=self._resource_server_url,
        )


# D-015, D-016: Identidade de quem chamou a ferramenta no contexto da requisição MCP
def current_person_id() -> str | None:
    """Devolve o person_id autenticado no modo HTTP ou None no modo stdio."""
    access_token = get_access_token()
    if access_token is None:
        return None
    if isinstance(access_token, RSLAccessToken):
        return access_token.person_id
    person_id = getattr(access_token, "person_id", None)
    if isinstance(person_id, str) and person_id:
        return person_id
    return None
