"""Configuração local do servidor RSL.app a partir de variáveis de ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_DATA_DIR_NAME = "RSL.app"
DEFAULT_EXPORT_DIR_NAME = "exports"
DEFAULT_CACHE_DAYS = 7


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
    )
