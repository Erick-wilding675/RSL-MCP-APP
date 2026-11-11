"""Links temporários assinados com HMAC-SHA256 e rota de download de exportações (D-014, FR-06, D-012)."""

from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import json
import os
import re
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

from rslapp import config, people
from rslapp.store._atomic import atomic_write_replace, file_lock

DEFAULT_DOWNLOAD_TTL_MINUTES = 60
MIN_SECRET_KEY_BYTES = 32
SECRET_KEY_FILENAME = "secret.key"

EXPIRED_LINK_MESSAGE = (
    "Este link de download venceu. Peça a exportação novamente para gerar um novo link."
)
NOT_FOUND_MESSAGE = "Não encontrado."

# D-014, FR-06: Tipos de conteúdo (MIME) para cada extensão de arquivo exportado
_MEDIA_TYPES: dict[str, str] = {
    ".ris": "application/x-research-info-systems; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
}

_NO_STORE_HEADERS: dict[str, str] = {
    "Cache-Control": "no-store",
}


def _now_utc() -> datetime:
    """Devolve o instante atual em UTC."""
    return datetime.now(timezone.utc)


def _format_utc(dt: datetime) -> str:
    """Formata um datetime UTC em ISO 8601 com sufixo Z."""
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_utc(iso_str: str) -> datetime:
    """Converte uma string ISO 8601 UTC para datetime com timezone UTC."""
    text = iso_str.strip()
    normalized = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# D-014: Prazo de validade do link em minutos via RSL_DOWNLOAD_TTL_MINUTES (padrão 60)
def load_download_ttl_minutes() -> int:
    """Lê e valida RSL_DOWNLOAD_TTL_MINUTES do ambiente (padrão 60)."""
    raw = os.environ.get("RSL_DOWNLOAD_TTL_MINUTES")
    if raw is None or not raw.strip():
        return DEFAULT_DOWNLOAD_TTL_MINUTES
    try:
        minutes = int(raw.strip())
    except ValueError:
        raise ValueError("RSL_DOWNLOAD_TTL_MINUTES deve ser um inteiro positivo") from None
    if minutes <= 0:
        raise ValueError("RSL_DOWNLOAD_TTL_MINUTES deve ser um inteiro positivo")
    return minutes


# D-014, D-007, NFR-03: Chave HMAC-SHA256 vinda de RSL_SECRET_KEY (>= 32 bytes) ou <RSL_DATA_DIR>/auth/secret.key
def load_secret_key(data_dir: Path | str | None = None) -> bytes:
    """Obtém a chave de assinatura HMAC-SHA256 sem expor seu valor em logs, erros ou repr."""
    raw_env = os.environ.get("RSL_SECRET_KEY")
    if raw_env is not None and raw_env != "":
        key_bytes = raw_env.strip().encode("utf-8")
        if len(key_bytes) < MIN_SECRET_KEY_BYTES:
            raise ValueError(
                f"RSL_SECRET_KEY deve ter pelo menos {MIN_SECRET_KEY_BYTES} bytes"
            )
        return key_bytes

    base_dir = Path(data_dir) if data_dir is not None else config.load().data_dir
    auth_dir = base_dir / "auth"
    key_path = auth_dir / SECRET_KEY_FILENAME
    lock_path = auth_dir / ".lock"

    with file_lock(lock_path):
        if key_path.is_file():
            existing = key_path.read_bytes().strip()
            if len(existing) >= MIN_SECRET_KEY_BYTES:
                return existing
        generated = secrets.token_hex(MIN_SECRET_KEY_BYTES)
        atomic_write_replace(key_path, generated + "\n")
        with contextlib.suppress(OSError):
            os.chmod(key_path, 0o600)
        return generated.encode("ascii")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    if not text or not re.fullmatch(r"[A-Za-z0-9_-]+", text):
        raise ValueError("base64url inválido")
    padding = "=" * ((4 - len(text) % 4) % 4)
    raw = base64.urlsafe_b64decode((text + padding).encode("ascii"))
    if _b64url_encode(raw) != text:
        raise ValueError("base64url não canônico")
    return raw


def _compute_signature(secret_key: bytes, payload_b64: str) -> str:
    return hmac.new(secret_key, payload_b64.encode("ascii"), hashlib.sha256).hexdigest()


# D-014, D-012, FR-06: Gera token assinado com HMAC-SHA256 contendo pessoa, arquivo de exportação e validade UTC
def sign_download_token(
    person_id: str,
    filename: str,
    *,
    data_dir: Path | str | None = None,
    ttl_minutes: int | None = None,
    now: datetime | None = None,
) -> tuple[str, str]:
    """Assina um token de download para (person_id, filename) e devolve (token, expires_at_iso)."""
    secret_key = load_secret_key(data_dir)
    effective_ttl = ttl_minutes if ttl_minutes is not None else load_download_ttl_minutes()
    now_dt = now.astimezone(timezone.utc) if now is not None else _now_utc()
    expires_dt = now_dt + timedelta(minutes=effective_ttl)
    expires_at = _format_utc(expires_dt)

    payload_bytes = json.dumps(
        {
            "expires_at": expires_at,
            "filename": filename,
            "kind": "export",
            "person_id": person_id,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    signature = _compute_signature(secret_key, payload_b64)
    return f"{payload_b64}.{signature}", expires_at


# D-012, D-014, FR-05, FR-13: Gera token assinado para baixar o log.md da pessoa autenticada
def sign_log_download_token(
    person_id: str,
    *,
    data_dir: Path | str | None = None,
    ttl_minutes: int | None = None,
    now: datetime | None = None,
) -> tuple[str, str]:
    """Assina um token de download para o log.md de person_id e devolve (token, expires_at_iso)."""
    secret_key = load_secret_key(data_dir)
    effective_ttl = ttl_minutes if ttl_minutes is not None else load_download_ttl_minutes()
    now_dt = now.astimezone(timezone.utc) if now is not None else _now_utc()
    expires_dt = now_dt + timedelta(minutes=effective_ttl)
    expires_at = _format_utc(expires_dt)

    payload_bytes = json.dumps(
        {
            "expires_at": expires_at,
            "kind": "log",
            "person_id": person_id,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    signature = _compute_signature(secret_key, payload_b64)
    return f"{payload_b64}.{signature}", expires_at


# D-014, D-012, FR-06: Monta o link <RSL_PUBLIC_URL>/downloads/<token> e a data de expiração ISO 8601
def create_download_link(
    person_id: str,
    filename: str,
    *,
    public_url: str,
    data_dir: Path | str | None = None,
    ttl_minutes: int | None = None,
    now: datetime | None = None,
) -> tuple[str, str]:
    """Cria a URL pública temporária de download e devolve (download_url, expires_at)."""
    token, expires_at = sign_download_token(
        person_id,
        filename,
        data_dir=data_dir,
        ttl_minutes=ttl_minutes,
        now=now,
    )
    base_url = public_url.strip().rstrip("/")
    return f"{base_url}/downloads/{token}", expires_at


# D-012, D-014, FR-05, FR-13: Monta o link assinado para download do log.md da pessoa
def create_log_download_link(
    person_id: str,
    *,
    public_url: str,
    data_dir: Path | str | None = None,
    ttl_minutes: int | None = None,
    now: datetime | None = None,
) -> tuple[str, str]:
    """Cria a URL pública temporária para baixar o log.md e devolve (log_download_url, expires_at)."""
    token, expires_at = sign_log_download_token(
        person_id,
        data_dir=data_dir,
        ttl_minutes=ttl_minutes,
        now=now,
    )
    base_url = public_url.strip().rstrip("/")
    return f"{base_url}/downloads/{token}", expires_at


def _is_safe_export_filename(filename: str) -> bool:
    """Garante nome de arquivo simples, sem '..', sem separadores de pasta e sem caminho absoluto."""
    if type(filename) is not str or not filename or filename != filename.strip():
        return False
    if "/" in filename or "\\" in filename or "\x00" in filename:
        return False
    path_obj = Path(filename)
    if path_obj.is_absolute() or path_obj.drive or path_obj.root:
        return False
    return path_obj.name == filename and filename not in (".", "..") and ".." not in path_obj.parts


def _not_found_response() -> Response:
    return PlainTextResponse(NOT_FOUND_MESSAGE, status_code=404, headers=_NO_STORE_HEADERS)


# D-012, D-014, FR-06: Limpeza das exportações antigas da própria pessoa antes de gravar nova exportação
def clean_expired_exports(
    export_dir: Path,
    *,
    retention_hours: int | None = None,
    now: datetime | None = None,
) -> None:
    """Apaga arquivos normais da pasta exports com idade superior a retention_hours sem interromper em caso de erro."""
    try:
        resolved_dir = export_dir.resolve()
        if not resolved_dir.is_dir():
            return
    except OSError:
        return

    effective_hours = (
        retention_hours
        if retention_hours is not None
        else config.load_export_retention_hours()
    )
    now_dt = now.astimezone(timezone.utc) if now is not None else _now_utc()
    cutoff_ts = now_dt.timestamp() - (effective_hours * 3600)

    try:
        entries = list(resolved_dir.iterdir())
    except OSError:
        return

    for entry in entries:
        try:
            if entry.is_symlink() or not entry.is_file():
                continue
            if entry.resolve().parent != resolved_dir:
                continue
            stat_res = entry.stat()
            if stat_res.st_mtime < cutoff_ts:
                entry.unlink()
        except OSError:
            continue


# D-014, D-012, FR-06: Rota GET /downloads/{token} sem login OAuth, validada por assinatura HMAC-SHA256
async def handle_download(
    request: Request,
    *,
    data_dir: Path | str | None = None,
    clock: Callable[[], datetime] | None = None,
) -> Response:
    """Valida assinatura, validade, pessoa ativa e caminho dentro de people/<id>/exports/."""
    token = request.path_params.get("token", "")
    if type(token) is not str or "." not in token or not token.isascii():
        return _not_found_response()

    parts = token.split(".")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return _not_found_response()
    payload_b64, received_sig = parts

    app_state = getattr(getattr(request, "app", None), "state", None)
    auth_store = getattr(app_state, "auth_store", None)
    resolved_data_dir = (
        Path(data_dir)
        if data_dir is not None
        else (auth_store.data_dir if auth_store is not None else config.load().data_dir)
    )

    secret_key = load_secret_key(resolved_data_dir)
    expected_sig = _compute_signature(secret_key, payload_b64)
    if not hmac.compare_digest(expected_sig, received_sig):
        return _not_found_response()

    try:
        raw_payload = _b64url_decode(payload_b64)
        payload = json.loads(raw_payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return _not_found_response()

    if not isinstance(payload, dict):
        return _not_found_response()

    person_id = payload.get("person_id")
    expires_at = payload.get("expires_at")
    kind = payload.get("kind", "export")
    if (
        type(person_id) is not str
        or type(expires_at) is not str
        or kind not in ("export", "log")
    ):
        return _not_found_response()

    try:
        people.validate_person_id(person_id)
        expires_dt = _parse_utc(expires_at)
    except ValueError:
        return _not_found_response()

    people_root = (resolved_data_dir / "people").resolve()
    person_dir = (people_root / person_id).resolve()
    if person_dir.parent != people_root:
        return _not_found_response()

    if kind == "export":
        filename = payload.get("filename")
        if type(filename) is not str or not _is_safe_export_filename(filename):
            return _not_found_response()
        exports_dir = (person_dir / "exports").resolve()
        target_path = (exports_dir / filename).resolve()
        if exports_dir.parent != person_dir or target_path.parent != exports_dir:
            return _not_found_response()
        out_filename = filename
        media_type = _MEDIA_TYPES.get(target_path.suffix.lower(), "application/octet-stream")
    else:
        filename_in_payload = payload.get("filename")
        if filename_in_payload is not None and filename_in_payload != "log.md":
            return _not_found_response()
        target_path = (person_dir / "log.md").resolve()
        if target_path.parent != person_dir:
            return _not_found_response()
        out_filename = "log.md"
        media_type = "text/markdown; charset=utf-8"

    person = people.get(person_id, data_dir=resolved_data_dir)
    if person is None or not person.is_active:
        return _not_found_response()

    now_dt = clock() if clock is not None else _now_utc()
    if now_dt.astimezone(timezone.utc) >= expires_dt:
        return PlainTextResponse(
            EXPIRED_LINK_MESSAGE,
            status_code=410,
            headers=_NO_STORE_HEADERS,
        )

    if not target_path.is_file():
        return _not_found_response()

    try:
        content_bytes = target_path.read_bytes()
    except OSError:
        return _not_found_response()

    headers = {
        **_NO_STORE_HEADERS,
        "Content-Disposition": f'attachment; filename="{out_filename}"',
    }
    return Response(content=content_bytes, media_type=media_type, headers=headers)
