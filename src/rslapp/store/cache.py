"""Cache em arquivos por fonte e consulta normalizada, com expiração e sem credenciais."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from rslapp.store._atomic import (
    atomic_write_replace,
    strip_dict_credentials,
    strip_response_credentials,
)

_SOURCE_NAME_RE = re.compile(r"^[a-z0-9_]+$")


# D-007: Validação estrita do nome da fonte para nunca sair da pasta de dados
def validate_source_name(source: str) -> str:
    if type(source) is not str or not _SOURCE_NAME_RE.fullmatch(source):
        raise ValueError("Nome de fonte inválido: use apenas [a-z0-9_]+")
    return source


def parse_utc_timestamp(value: datetime | str | None = None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    text = value.strip()
    dt = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text)
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def format_utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# NFR-03, NFR-06: Cálculo da chave SHA-256 sobre a consulta sem parâmetros de credencial
def compute_cache_key(query: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if type(query) is not dict:
        raise ValueError("A consulta do cache deve ser um dict")
    cleaned: dict[str, Any] = strip_dict_credentials(query)
    canonical = json.dumps(cleaned, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest(), cleaned


def _cache_target(cache_dir: Path, source: str, query: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    validate_source_name(source)
    digest, cleaned = compute_cache_key(query)
    return cache_dir / source / f"{digest}.json", cleaned


# NFR-03, NFR-06, D-007: Gravação atômica do cache com prazo de expiração e sem chaves de API
def write_cache_entry(
    cache_dir: Path, source: str, query: dict[str, Any], response: Any, cache_days: int,
    *, fetched_at: datetime | str | None = None,
) -> Path:
    dest, cleaned_query = _cache_target(cache_dir, source, query)
    fetched_dt = parse_utc_timestamp(fetched_at)
    payload = {
        "source": source,
        "query": cleaned_query,
        "response": strip_response_credentials(response),
        "fetched_at": format_utc_iso(fetched_dt),
        "expires_at": format_utc_iso(fetched_dt + timedelta(days=cache_days)),
    }
    atomic_write_replace(dest, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return dest


# NFR-06: Leitura do cache verificando prazo de validade
def read_cache_entry(
    cache_dir: Path, source: str, query: dict[str, Any], *, now: datetime | str | None = None,
) -> dict[str, Any] | None:
    dest, _ = _cache_target(cache_dir, source, query)
    if not dest.exists():
        return None
    raw = json.loads(dest.read_text(encoding="utf-8"))
    if parse_utc_timestamp(now) >= parse_utc_timestamp(raw["expires_at"]):
        return None
    return {"response": copy.deepcopy(raw["response"]), "from_cache": True, "fetched_at": raw["fetched_at"]}
