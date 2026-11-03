"""Operações atômicas de arquivo, geração de IDs sequenciais e limpeza de credenciais."""

from __future__ import annotations

import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# NFR-03: Nomes de parâmetros de credencial que nunca podem ir para disco ou chave de cache
CREDENTIAL_KEYS: frozenset[str] = frozenset(
    {"api_key", "apikey", "api-key", "key", "token", "authorization"}
)

_INLINE_CREDENTIAL_RE = re.compile(
    r"(?i)(?<![a-z0-9_])(?:"
    r"(?:api_key|apikey|api-key|key|token|authorization)\s*=\s*[^\s&,;'\"]+"
    r"|(?:api_key|apikey|api-key|token|authorization)\s*:\s*(?:bearer\s+)?[^\s&,;'\"]+"
    r")"
)


# NFR-03: Remove parâmetros de credencial de textos ou URLs antes de gravar
def sanitize_string(value: str) -> str:
    """Remove parâmetros de credencial de URLs ou strings de consulta."""
    if not value:
        return value
    result = value
    if "://" in result or "?" in result:
        try:
            parts = urlsplit(result)
            if parts.query:
                filtered = [
                    (k, v)
                    for k, v in parse_qsl(parts.query, keep_blank_values=True)
                    if k.strip().lower() not in CREDENTIAL_KEYS
                ]
                result = urlunsplit(
                    (parts.scheme, parts.netloc, parts.path, urlencode(filtered), parts.fragment)
                )
        except ValueError:
            pass
    return _INLINE_CREDENTIAL_RE.sub("", result).strip()


# NFR-03: Remove chaves de credencial recursivamente e ordena chaves de dicionários
def sanitize_query(data: Any) -> Any:
    """Retira credenciais de dicionários/listas/strings e ordena as chaves."""
    if isinstance(data, dict):
        cleaned: dict[str, Any] = {}
        for k in sorted(data.keys(), key=lambda x: str(x)):
            if str(k).strip().lower() in CREDENTIAL_KEYS:
                continue
            cleaned[str(k)] = sanitize_query(data[k])
        return cleaned
    if isinstance(data, list):
        return [sanitize_query(item) for item in data]
    if isinstance(data, str):
        return sanitize_string(data)
    return data


# D-007: Gravação atômica via arquivo temporário na mesma pasta, flush e os.fsync
def _write_temp_file(dest: Path, content: str) -> Path:
    """Cria e sincroniza um arquivo temporário na mesma pasta do destino."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=dest.parent,
            prefix=f".{dest.name}.",
            suffix=".tmp",
            delete=False,
        ) as f:
            tmp_path = Path(f.name)
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        return tmp_path
    except BaseException:
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


# D-007, FR-05, FR-09, FR-12: Publicação exclusiva via os.link para impedir sobrescrita
def atomic_write_exclusive(dest: Path, content: str) -> None:
    """Grava arquivo de forma atômica e exclusiva (falha se o destino já existir)."""
    tmp_path = _write_temp_file(dest, content)
    try:
        os.link(tmp_path, dest)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


# D-007: Publicação atômica com substituição via os.replace e repetição curta no Windows
def atomic_write_replace(dest: Path, content: str, retries: int = 5, delay: float = 0.02) -> None:
    """Grava arquivo de forma atômica substituindo o destino existente."""
    tmp_path = _write_temp_file(dest, content)
    try:
        for attempt in range(retries):
            try:
                os.replace(tmp_path, dest)
                return
            except PermissionError:
                if attempt == retries - 1:
                    raise
                time.sleep(delay * (attempt + 1))
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


# FR-09, D-007: Extração e formatação de identificadores sequenciais (s-NNNN e l-NNNN)
def parse_seq_id(raw_id: str, prefix: str) -> int:
    """Valida um id sequencial (ex.: s-0001) e devolve seu número inteiro positivo."""
    match = re.fullmatch(rf"{re.escape(prefix)}-(\d{{4,}})", raw_id) if type(raw_id) is str else None
    if not match:
        raise ValueError(
            f"Identificador inválido para prefixo {prefix}: formato esperado {prefix}-NNNN"
        )
    num = int(match.group(1))
    if num <= 0:
        raise ValueError(f"Identificador inválido para prefixo {prefix}")
    return num


def format_seq_id(prefix: str, number: int) -> str:
    """Formata um número sequencial com ao menos quatro dígitos (ex.: s-0001, s-10000)."""
    return f"{prefix}-{number:04d}"


def existing_id_numbers(directory: Path, prefix: str) -> list[int]:
    """Lista os números de IDs já gravados na pasta, ordenados numericamente."""
    if not directory.exists():
        return []
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d{{4,}})\.json$")
    numbers: list[int] = []
    for entry in directory.iterdir():
        if entry.is_file():
            m = pattern.match(entry.name)
            if m:
                numbers.append(int(m.group(1)))
    numbers.sort()
    return numbers


def next_id_number(directory: Path, prefix: str, reserved: set[int] | None = None) -> int:
    """Calcula o próximo número sequencial a partir do maior existente em disco mais um."""
    nums = existing_id_numbers(directory, prefix)
    max_disk = nums[-1] if nums else 0
    max_reserved = max(reserved) if reserved else 0
    return max(max_disk, max_reserved) + 1
