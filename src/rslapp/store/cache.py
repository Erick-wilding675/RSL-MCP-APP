"""Cache em arquivos por fonte e consulta normalizada, com expiração e sem credenciais."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from rslapp.store._atomic import atomic_write_replace, sanitize_query

_SOURCE_NAME_RE = re.compile(r"^[a-z0-9_]+$")


# D-007: Validação estrita do nome da fonte para nunca sair da pasta de dados
def validate_source_name(source: str) -> str:
    """Garante que o nome da fonte contém apenas [a-z0-9_]+."""
    matched = _SOURCE_NAME_RE.fullmatch(source) if type(source) is str else None
    if not matched:
        raise ValueError("Nome de fonte inválido: use apenas [a-z0-9_]+")
    return source


def parse_utc_timestamp(value: datetime | str | None = None) -> datetime:
    """Converte datetime ou texto ISO 8601 para datetime em UTC (compatível com Python 3.10)."""
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    text = value.strip()
    if text.endswith(" UTC"):
        dt = datetime.strptime(text[:-4].strip(), "%Y-%m-%d %H:%M")
        return dt.replace(tzinfo=timezone.utc)
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_utc_iso(dt: datetime) -> str:
    """Formata um datetime em UTC no padrão ISO 8601 com sufixo Z."""
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# NFR-03, NFR-06: Cálculo da chave SHA-256 sobre a consulta sem parâmetros de credencial
def compute_cache_key(query: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Normaliza a consulta (sem credenciais e com chaves ordenadas) e devolve (sha256, query_limpa)."""
    if type(query) is not dict:
        raise ValueError("A consulta do cache deve ser um dict")
    cleaned_query: dict[str, Any] = sanitize_query(query)
    canonical = json.dumps(cleaned_query, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return digest, cleaned_query


def cache_file_path(cache_dir: Path, source: str, query: dict[str, Any]) -> Path:
    """Devolve o caminho cache/<fonte>/<sha256>.json para a fonte e consulta."""
    validate_source_name(source)
    digest, _ = compute_cache_key(query)
    return cache_dir / source / f"{digest}.json"


# NFR-03, NFR-06, D-007: Gravação atômica do cache com prazo de expiração e sem chaves de API
def write_cache_entry(
    cache_dir: Path,
    source: str,
    query: dict[str, Any],
    response: Any,
    cache_days: int,
    *,
    fetched_at: datetime | str | None = None,
) -> Path:
    """Grava ou substitui uma entrada de cache em cache/<fonte>/<sha256>.json."""
    validate_source_name(source)
    digest, cleaned_query = compute_cache_key(query)
    fetched_dt = parse_utc_timestamp(fetched_at)
    expires_dt = fetched_dt + timedelta(days=cache_days)
    payload = {
        "source": source,
        "query": cleaned_query,
        "response": copy.deepcopy(response),
        "fetched_at": format_utc_iso(fetched_dt),
        "expires_at": format_utc_iso(expires_dt),
    }
    dest = cache_dir / source / f"{digest}.json"
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    atomic_write_replace(dest, content)
    return dest


# NFR-06: Leitura do cache verificando prazo de validade
def read_cache_entry(
    cache_dir: Path,
    source: str,
    query: dict[str, Any],
    *,
    now: datetime | str | None = None,
) -> dict[str, Any] | None:
    """Lê resposta do cache se existir e estiver no prazo; devolve None se ausente ou vencida."""
    validate_source_name(source)
    digest, _ = compute_cache_key(query)
    dest = cache_dir / source / f"{digest}.json"
    if not dest.exists():
        return None
    raw = json.loads(dest.read_text(encoding="utf-8"))
    expires_dt = parse_utc_timestamp(raw["expires_at"])
    now_dt = parse_utc_timestamp(now)
    if now_dt >= expires_dt:
        return None
    return {
        "response": copy.deepcopy(raw["response"]),
        "from_cache": True,
        "fetched_at": raw["fetched_at"],
    }
