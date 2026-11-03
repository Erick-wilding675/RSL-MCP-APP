"""Operações atômicas de arquivo, trava entre processos, IDs sequenciais e limpeza de credenciais."""

from __future__ import annotations

import contextlib
import copy
import os
import re
import sys
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

# NFR-03: Parâmetros de credencial que nunca podem ir para disco ou chave de cache
CREDENTIAL_KEYS: frozenset[str] = frozenset(
    {"api_key", "apikey", "api-key", "key", "token", "authorization"}
)
_URL_RE = re.compile(r"(?i)https?://[^\s\"'<>`]+")


def _clean_matched_url(match: re.Match[str]) -> str:
    raw_url = match.group(0)
    base_and_query, sep_hash, fragment = raw_url.partition("#")
    base, sep_q, query_str = base_and_query.partition("?")
    if not sep_q:
        return raw_url
    parts = query_str.split("&")
    kept = [
        p for p in parts
        if not (p.partition("=")[1] and p.partition("=")[0].strip().lower() in CREDENTIAL_KEYS)
    ]
    if len(kept) == len(parts):
        return raw_url
    return f"{f'{base}?{chr(38).join(kept)}' if kept else base}{sep_hash}{fragment}"


# NFR-03: Remove apenas parâmetros de credencial de URLs http(s) mantendo o resto byte a byte
def strip_url_credentials(text: str) -> str:
    if "http://" not in text.lower() and "https://" not in text.lower():
        return text
    return _URL_RE.sub(_clean_matched_url, text)


# NFR-03: Remove chaves de credencial de dicionários em qualquer nível sem alterar textos
def strip_dict_credentials(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            str(k): strip_dict_credentials(data[k])
            for k in sorted(data, key=lambda x: str(x))
            if str(k).strip().lower() not in CREDENTIAL_KEYS
        }
    if isinstance(data, list):
        return [strip_dict_credentials(item) for item in data]
    return copy.deepcopy(data)


# NFR-03: Aplica strip_url_credentials às strings da resposta do cache
def strip_response_credentials(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: strip_response_credentials(v) for k, v in data.items()}
    if isinstance(data, list):
        return [strip_response_credentials(item) for item in data]
    return strip_url_credentials(data) if isinstance(data, str) else copy.deepcopy(data)


# D-007: Gravação atômica via arquivo temporário na mesma pasta, flush e os.fsync
def _write_temp_file(dest: Path, content: str) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=dest.parent,
            prefix=f".{dest.name}.", suffix=".tmp", delete=False,
        ) as f:
            tmp_path = Path(f.name)
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        return tmp_path
    except BaseException:
        if tmp_path is not None:
            with contextlib.suppress(OSError):
                tmp_path.unlink()
        raise


# D-007, FR-05, FR-09, FR-12: Publicação exclusiva via os.link para impedir sobrescrita
def atomic_write_exclusive(dest: Path, content: str) -> None:
    tmp_path = _write_temp_file(dest, content)
    try:
        try:
            os.link(tmp_path, dest)
        except FileExistsError:
            raise
        except OSError as exc:
            if sys.platform == "win32" and os.name == "nt":
                os.rename(tmp_path, dest)
            else:
                raise OSError("A pasta de dados precisa aceitar hard links") from exc
    finally:
        with contextlib.suppress(OSError):
            if tmp_path.exists():
                tmp_path.unlink()


# D-007: Publicação atômica com substituição via os.replace e repetição (~1 s) no Windows
def atomic_write_replace(dest: Path, content: str, retries: int = 10, delay: float = 0.022) -> None:
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
        with contextlib.suppress(OSError):
            if tmp_path.exists():
                tmp_path.unlink()


# D-007: Trava em arquivo entre processos e threads via O_CREAT | O_EXCL
@contextlib.contextmanager
def file_lock(
    lock_path: Path, *, timeout: float = 15.0, delay: float = 0.005, stale_after: float = 10.0
) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    while True:
        try:
            os.close(os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except (FileExistsError, PermissionError) as exc:
            with contextlib.suppress(OSError):
                if time.time() - lock_path.stat().st_mtime > stale_after:
                    lock_path.unlink()
                    continue
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Tempo esgotado aguardando trava: {lock_path}") from exc
            time.sleep(delay)
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            lock_path.unlink()


# FR-09, D-007: Extração e formatação de identificadores sequenciais (s-NNNN e l-NNNN)
def format_seq_id(prefix: str, number: int) -> str:
    return f"{prefix}-{number:04d}"


def parse_seq_id(raw_id: str, prefix: str) -> int:
    match = re.fullmatch(rf"{re.escape(prefix)}-(\d{{4,}})", raw_id) if type(raw_id) is str else None
    num = int(match.group(1)) if match else 0
    if num <= 0 or format_seq_id(prefix, num) != raw_id:
        raise ValueError(f"Identificador inválido para prefixo {prefix}: {raw_id!r}")
    return num


def existing_id_numbers(directory: Path, prefix: str) -> list[int]:
    if not directory.exists():
        return []
    nums: list[int] = []
    for entry in directory.iterdir():
        if entry.is_file() and entry.suffix == ".json":
            with contextlib.suppress(ValueError):
                nums.append(parse_seq_id(entry.stem, prefix))
    return sorted(nums)
