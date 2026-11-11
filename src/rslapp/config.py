"""Configuração local do servidor RSL.app a partir de variáveis de ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_DATA_DIR_NAME = "RSL.app"
DEFAULT_EXPORT_DIR_NAME = "exports"
DEFAULT_CACHE_DAYS = 7
DEFAULT_HTTP_HOST = "127.0.0.1"
DEFAULT_HTTP_PORT = 8000
DEFAULT_FORWARDED_ALLOW_IPS = "127.0.0.1"
DEFAULT_ACCESS_TOKEN_MINUTES = 60
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


# FR-07: Configuração do servidor e das chaves de API na máquina do usuário via variáveis de ambiente
# NFR-02: Execução local (self-hosted), usando diretórios locais da máquina do usuário
# NFR-03: O objeto de configuração guarda apenas se as chaves estão presentes (bool), nunca o valor delas
@dataclass(frozen=True)
class Config:
    """Configuração imutável carregada do ambiente local."""

    data_dir: Path
    export_dir: Path
    cache_days: int = DEFAULT_CACHE_DAYS
    contact_email: str | None = field(default=None, repr=False)
    openalex_key_configured: bool = False
    semantic_scholar_key_configured: bool = False
    ncbi_key_configured: bool = False


def _is_key_configured(env_var: str) -> bool:
    """Verifica se uma chave de API está definida e não vazia sem reter seu valor (NFR-03)."""
    raw = os.environ.get(env_var)
    return bool(raw and raw.strip())


def _parse_cache_days(raw_value: str | None) -> int:
    """Valida e converte RSL_CACHE_DAYS para inteiro positivo."""
    if raw_value is None:
        return DEFAULT_CACHE_DAYS
    try:
        days = int(raw_value.strip())
    except ValueError:
        raise ValueError("RSL_CACHE_DAYS deve ser um inteiro positivo") from None
    if days <= 0:
        raise ValueError("RSL_CACHE_DAYS deve ser um inteiro positivo")
    return days


# FR-07: Leitura dinâmica da configuração a cada chamada, sem criar pastas nem reter chaves
def load() -> Config:
    """Lê as variáveis de ambiente e devolve a configuração atual."""
    # NFR-02: Pastas locais padrão na conta do usuário
    raw_data_dir = os.environ.get("RSL_DATA_DIR")
    if raw_data_dir and raw_data_dir.strip():
        data_dir = Path(raw_data_dir.strip()).expanduser()
    else:
        data_dir = Path.home() / DEFAULT_DATA_DIR_NAME

    raw_export_dir = os.environ.get("RSL_EXPORT_DIR")
    if raw_export_dir and raw_export_dir.strip():
        export_dir = Path(raw_export_dir.strip()).expanduser()
    else:
        export_dir = data_dir / DEFAULT_EXPORT_DIR_NAME

    cache_days = _parse_cache_days(os.environ.get("RSL_CACHE_DAYS"))

    raw_email = os.environ.get("RSL_CONTACT_EMAIL")
    contact_email = raw_email.strip() if raw_email and raw_email.strip() else None

    # NFR-03: Apenas booleanos indicando presença das chaves são armazenados
    return Config(
        data_dir=data_dir,
        export_dir=export_dir,
        cache_days=cache_days,
        contact_email=contact_email,
        openalex_key_configured=_is_key_configured("OPENALEX_API_KEY"),
        semantic_scholar_key_configured=_is_key_configured("SEMANTIC_SCHOLAR_API_KEY"),
        ncbi_key_configured=_is_key_configured("NCBI_API_KEY"),
    )


# D-011, D-015, D-017, NFR-03: Configuração imutável do modo HTTP sem expor valores secretos no repr
@dataclass(frozen=True)
class HttpConfig:
    """Configuração imutável do modo HTTP carregada do ambiente e da linha de comando."""

    host: str = DEFAULT_HTTP_HOST
    port: int = DEFAULT_HTTP_PORT
    public_url: str = f"http://{DEFAULT_HTTP_HOST}:{DEFAULT_HTTP_PORT}"
    forwarded_allow_ips: str = DEFAULT_FORWARDED_ALLOW_IPS
    access_token_minutes: int = DEFAULT_ACCESS_TOKEN_MINUTES


# D-011, D-015: Verifica se o host de escuta pertence ao loopback local
def is_loopback_host(host: str) -> bool:
    """Indica se o endereço de escuta pertence ao loopback local (127.0.0.1, localhost ou ::1)."""
    return host.strip().lower() in LOOPBACK_HOSTS


# D-011, D-015, D-017: Com login OAuth, host fora de loopback é aceito quando RSL_PUBLIC_URL usa https://
def validate_http_host(host: str, public_url: str) -> None:
    """Valida que endereços fora do loopback só sejam usados quando RSL_PUBLIC_URL começa com https://."""
    scheme, _ = parse_public_url_host(public_url)
    if not is_loopback_host(host) and scheme != "https":
        raise ValueError(
            "Para escutar fora de loopback (127.0.0.1, localhost ou ::1), "
            f"RSL_PUBLIC_URL deve começar com https://; recebido {host!r} com {public_url!r}."
        )



# D-011, D-017: Extrai esquema e host (com colchetes em IPv6) de RSL_PUBLIC_URL para proteção de host
def parse_public_url_host(public_url: str) -> tuple[str, str]:
    """Valida RSL_PUBLIC_URL e devolve (scheme, host_para_cabecalho_http)."""
    parsed = urlsplit(public_url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("RSL_PUBLIC_URL deve ser uma URL http:// ou https:// com host válido")
    hostname = parsed.hostname
    if ":" in hostname:
        return parsed.scheme, f"[{hostname}]"
    return parsed.scheme, hostname


def _parse_http_port(raw_value: str | None) -> int:
    """Valida e converte RSL_HTTP_PORT para inteiro entre 1 e 65535."""
    if raw_value is None or not raw_value.strip():
        return DEFAULT_HTTP_PORT
    try:
        port = int(raw_value.strip())
    except ValueError:
        raise ValueError("RSL_HTTP_PORT deve ser um inteiro entre 1 e 65535") from None
    if port < 1 or port > 65535:
        raise ValueError("RSL_HTTP_PORT deve ser um inteiro entre 1 e 65535")
    return port


# D-015, D-016: Prazo em minutos do token de acesso OAuth (RSL_ACCESS_TOKEN_MINUTES, padrão 60)
def _parse_access_token_minutes(raw_value: str | None) -> int:
    """Valida e converte RSL_ACCESS_TOKEN_MINUTES para inteiro positivo."""
    if raw_value is None or not raw_value.strip():
        return DEFAULT_ACCESS_TOKEN_MINUTES
    try:
        minutes = int(raw_value.strip())
    except ValueError:
        raise ValueError("RSL_ACCESS_TOKEN_MINUTES deve ser um inteiro positivo") from None
    if minutes <= 0:
        raise ValueError("RSL_ACCESS_TOKEN_MINUTES deve ser um inteiro positivo")
    return minutes


def load_access_token_minutes() -> int:
    """Lê RSL_ACCESS_TOKEN_MINUTES do ambiente (padrão 60)."""
    return _parse_access_token_minutes(os.environ.get("RSL_ACCESS_TOKEN_MINUTES"))


# D-011, D-015, D-017: Lê a configuração do modo HTTP com sobreposição por --host e --port
def load_http(*, host: str | None = None, port: int | None = None) -> HttpConfig:
    """Lê as variáveis de ambiente do modo HTTP, aplicando --host e --port quando informados."""
    if host is not None:
        resolved_host = host.strip()
        if not resolved_host:
            raise ValueError("O endereço de escuta HTTP (--host) não pode ser vazio")
    else:
        raw_host = os.environ.get("RSL_HTTP_HOST")
        resolved_host = raw_host.strip() if raw_host and raw_host.strip() else DEFAULT_HTTP_HOST

    if port is not None:
        if isinstance(port, bool) or not isinstance(port, int) or port < 1 or port > 65535:
            raise ValueError("A porta HTTP (--port) deve ser um inteiro entre 1 e 65535")
        resolved_port = port
    else:
        resolved_port = _parse_http_port(os.environ.get("RSL_HTTP_PORT"))

    raw_public_url = os.environ.get("RSL_PUBLIC_URL")
    if raw_public_url and raw_public_url.strip():
        resolved_public_url = raw_public_url.strip().rstrip("/")
    else:
        resolved_public_url = f"http://127.0.0.1:{resolved_port}"
    parse_public_url_host(resolved_public_url)

    raw_forwarded = os.environ.get("RSL_FORWARDED_ALLOW_IPS")
    if raw_forwarded and raw_forwarded.strip():
        resolved_forwarded = raw_forwarded.strip()
    else:
        resolved_forwarded = DEFAULT_FORWARDED_ALLOW_IPS

    access_token_minutes = load_access_token_minutes()

    return HttpConfig(
        host=resolved_host,
        port=resolved_port,
        public_url=resolved_public_url,
        forwarded_allow_ips=resolved_forwarded,
        access_token_minutes=access_token_minutes,
    )
