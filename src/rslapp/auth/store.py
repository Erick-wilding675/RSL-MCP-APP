"""Armazenamento local em disco dos clientes e hashes de tokens OAuth 2.1."""

from __future__ import annotations

import hashlib
import json
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from mcp.server.auth.provider import AccessToken, AuthorizationCode, RefreshToken
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import PrivateAttr

from rslapp import config, people
from rslapp.store._atomic import atomic_write_replace, file_lock

AUTH_SUBDIR = "auth"
CLIENTS_FILENAME = "clients.json"
TOKENS_FILENAME = "tokens.json"
LOCK_FILENAME = ".lock"

# Mapa apenas em memória para reidratar client_secret na sessão atual sem gravá-lo em texto puro no disco (NFR-03)
_RUNTIME_CLIENT_SECRETS: dict[str, str] = {}


def _now_utc() -> datetime:
    """Devolve o instante atual em UTC."""
    return datetime.now(timezone.utc)


def _format_utc(dt: datetime) -> str:
    """Formata um datetime UTC em ISO 8601 com sufixo Z."""
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_utc(iso_str: str) -> datetime:
    """Converte uma string ISO 8601 UTC para datetime com timezone."""
    normalized = iso_str[:-1] + "+00:00" if iso_str.endswith("Z") else iso_str
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# D-016, NFR-03: No disco ficam só hashes SHA-256 dos tokens, nunca o valor em texto puro
def hash_token(raw_token: str) -> str:
    """Calcula o hash SHA-256 hexadecimal de um token ou segredo."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def normalize_resource_url(resource: str | None) -> str | None:
    """Normaliza a URL de recurso removendo barra final supérflua."""
    if resource is None:
        return None
    stripped = resource.strip().rstrip("/")
    return stripped or None


# D-015, D-016, NFR-03: Modelos de código e tokens OAuth com repr seguro (sem expor segredos nem hashes)
class RSLAuthorizationCode(AuthorizationCode):
    """Código de autorização de uso único vinculado a uma pessoa cadastrada."""

    person_id: str

    def __repr__(self) -> str:
        return (
            f"RSLAuthorizationCode(client_id={self.client_id!r}, "
            f"person_id={self.person_id!r}, scopes={self.scopes!r})"
        )

    def __str__(self) -> str:
        return self.__repr__()


class RSLAccessToken(AccessToken):
    """Token de acesso verificado, com identidade da pessoa e sem expor o valor no repr."""

    person_id: str
    _token_hash: str = PrivateAttr(default="")

    def __repr__(self) -> str:
        return (
            f"RSLAccessToken(client_id={self.client_id!r}, "
            f"person_id={self.person_id!r}, scopes={self.scopes!r}, "
            f"expires_at={self.expires_at!r}, resource={self.resource!r})"
        )

    def __str__(self) -> str:
        return self.__repr__()


class RSLRefreshToken(RefreshToken):
    """Token de renovação vinculado a uma pessoa cadastrada e sem expor o valor no repr."""

    person_id: str
    resource: str | None = None
    _token_hash: str = PrivateAttr(default="")

    def __repr__(self) -> str:
        return (
            f"RSLRefreshToken(client_id={self.client_id!r}, "
            f"person_id={self.person_id!r}, scopes={self.scopes!r})"
        )

    def __str__(self) -> str:
        return self.__repr__()


# D-016, D-007: Registro persistido em <RSL_DATA_DIR>/auth/tokens.json (apenas hash SHA-256)
@dataclass(frozen=True)
class StoredToken:
    """Metadados persistidos de um token de acesso ou de renovação."""

    token_hash: str = field(repr=False)
    kind: str
    person_id: str
    client_id: str
    scopes: list[str]
    resource: str | None
    issued_at: str
    expires_at: str | None

    def to_dict(self) -> dict[str, Any]:
        """Converte o registro para dicionário serializável em JSON."""
        return {
            "token_hash": self.token_hash,
            "kind": self.kind,
            "person_id": self.person_id,
            "client_id": self.client_id,
            "scopes": list(self.scopes),
            "resource": self.resource,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoredToken:
        """Reconstrói um StoredToken a partir de dicionário lido do JSON."""
        return cls(
            token_hash=str(data["token_hash"]),
            kind=str(data["kind"]),
            person_id=str(data["person_id"]),
            client_id=str(data["client_id"]),
            scopes=[str(s) for s in data.get("scopes", [])],
            resource=normalize_resource_url(data.get("resource")),
            issued_at=str(data["issued_at"]),
            expires_at=str(data["expires_at"]) if data.get("expires_at") is not None else None,
        )


# D-015, D-016, D-007, NFR-03: Armazenamento atômico em <RSL_DATA_DIR>/auth/ com bloqueio entre processos
class AuthStore:
    """Gerencia o armazenamento local de clientes OAuth e hashes de tokens."""

    def __init__(
        self,
        *,
        data_dir: Path | None = None,
        access_token_minutes: int | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._data_dir = data_dir
        self._access_token_minutes = access_token_minutes
        self._clock = clock

    @property
    def data_dir(self) -> Path:
        """Diretório de dados efetivo."""
        return self._data_dir if self._data_dir is not None else config.load().data_dir

    @property
    def auth_dir(self) -> Path:
        """Diretório <RSL_DATA_DIR>/auth/ onde ficam clientes e hashes de tokens."""
        return self.data_dir / AUTH_SUBDIR

    @property
    def access_token_minutes(self) -> int:
        """Prazo em minutos de cada access token emitido."""
        if self._access_token_minutes is not None:
            return self._access_token_minutes
        return config.load_access_token_minutes()

    def now(self) -> datetime:
        """Devolve o instante atual em UTC usando o relógio configurado."""
        if self._clock is not None:
            dt = self._clock()
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        return _now_utc()

    def _lock_path(self) -> Path:
        return self.auth_dir / LOCK_FILENAME

    def _clients_path(self) -> Path:
        return self.auth_dir / CLIENTS_FILENAME

    def _tokens_path(self) -> Path:
        return self.auth_dir / TOKENS_FILENAME

    def _read_clients_unlocked(self) -> dict[str, dict[str, Any]]:
        path = self._clients_path()
        if not path.exists():
            return {}
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {}
        clients = raw.get("clients", {})
        return clients if isinstance(clients, dict) else {}

    def _write_clients_unlocked(self, clients: dict[str, dict[str, Any]]) -> None:
        payload = (
            json.dumps(
                {"clients": clients},
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
        atomic_write_replace(self._clients_path(), payload)

    def _read_tokens_unlocked(self) -> list[StoredToken]:
        path = self._tokens_path()
        if not path.exists():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return []
        items = raw.get("tokens", [])
        if not isinstance(items, list):
            return []
        return [StoredToken.from_dict(item) for item in items if isinstance(item, dict)]

    def _write_tokens_unlocked(self, tokens: list[StoredToken]) -> None:
        payload = (
            json.dumps(
                {"tokens": [t.to_dict() for t in tokens]},
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
        atomic_write_replace(self._tokens_path(), payload)

    # D-015, NFR-03: Registro dinâmico de cliente sem salvar client_secret em texto puro no disco
    def save_client(self, client_info: OAuthClientInformationFull) -> None:
        """Persiste os metadados de um cliente OAuth guardando apenas o hash do segredo em disco."""
        data = client_info.model_dump(mode="json")
        raw_secret = data.pop("client_secret", None)
        if raw_secret:
            secret_hash = hash_token(str(raw_secret))
            data["client_secret_hash"] = secret_hash
            _RUNTIME_CLIENT_SECRETS[secret_hash] = str(raw_secret)
        else:
            data["client_secret_hash"] = None

        with file_lock(self._lock_path()):
            clients = self._read_clients_unlocked()
            clients[client_info.client_id] = data
            self._write_clients_unlocked(clients)

    def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        """Busca um cliente OAuth pelo client_id."""
        with file_lock(self._lock_path()):
            clients = self._read_clients_unlocked()
            raw = clients.get(client_id)
            if raw is None:
                return None

        data = dict(raw)
        secret_hash = data.pop("client_secret_hash", None)
        if secret_hash and secret_hash in _RUNTIME_CLIENT_SECRETS:
            data["client_secret"] = _RUNTIME_CLIENT_SECRETS[secret_hash]
        else:
            data["client_secret"] = None
        return OAuthClientInformationFull.model_validate(data)

    def _compute_issued_at(self, person_id: str) -> datetime:
        """Calcula o timestamp de emissão garantindo monotonicidade após code_created_at atual."""
        now_dt = self.now()
        person = people.get(person_id, data_dir=self.data_dir)
        if person is not None:
            code_dt = _parse_utc(person.code_created_at)
            if now_dt <= code_dt and self._clock is None:
                return code_dt + timedelta(microseconds=1)
            if now_dt == code_dt:
                return code_dt + timedelta(microseconds=1)
        return now_dt

    # D-015, D-016: Emite access token (com prazo) e refresh token (sem vencimento, rotativo)
    def issue_token_pair(
        self,
        *,
        person_id: str,
        client_id: str,
        scopes: list[str],
        resource: str | None,
    ) -> OAuthToken:
        """Gera um novo par de access_token e refresh_token e persiste apenas seus hashes SHA-256."""
        raw_access = secrets.token_urlsafe(32)
        raw_refresh = secrets.token_urlsafe(32)

        issued_dt = self._compute_issued_at(person_id)
        expires_in_seconds = self.access_token_minutes * 60
        expires_dt = issued_dt + timedelta(seconds=expires_in_seconds)

        normalized_resource = normalize_resource_url(resource)
        effective_scopes = list(scopes) if scopes else ["rsl"]

        access_record = StoredToken(
            token_hash=hash_token(raw_access),
            kind="access",
            person_id=person_id,
            client_id=client_id,
            scopes=effective_scopes,
            resource=normalized_resource,
            issued_at=_format_utc(issued_dt),
            expires_at=_format_utc(expires_dt),
        )
        refresh_record = StoredToken(
            token_hash=hash_token(raw_refresh),
            kind="refresh",
            person_id=person_id,
            client_id=client_id,
            scopes=effective_scopes,
            resource=normalized_resource,
            issued_at=_format_utc(issued_dt),
            expires_at=None,
        )

        with file_lock(self._lock_path()):
            tokens = self._read_tokens_unlocked()
            tokens.append(access_record)
            tokens.append(refresh_record)
            self._write_tokens_unlocked(tokens)

        return OAuthToken(
            access_token=raw_access,
            token_type="Bearer",
            expires_in=expires_in_seconds,
            scope=" ".join(effective_scopes),
            refresh_token=raw_refresh,
        )

    # D-016: O refresh token gira a cada uso (o anterior deixa de valer imediatamente)
    def rotate_refresh_token(
        self,
        *,
        old_refresh_token_hash: str,
        scopes: list[str] | None = None,
    ) -> OAuthToken | None:
        """Invalida o refresh token anterior e emite um novo par se a pessoa continuar ativa."""
        with file_lock(self._lock_path()):
            tokens = self._read_tokens_unlocked()
            target: StoredToken | None = None
            remaining: list[StoredToken] = []
            for item in tokens:
                if item.kind == "refresh" and secrets.compare_digest(item.token_hash, old_refresh_token_hash):
                    target = item
                else:
                    remaining.append(item)

            if target is None:
                return None

            # Mesmo se a pessoa tiver sido revogada, o refresh token antigo não volta
            if not self._is_token_record_valid_for_person(target):
                self._write_tokens_unlocked(remaining)
                return None

            raw_access = secrets.token_urlsafe(32)
            raw_refresh = secrets.token_urlsafe(32)
            issued_dt = self._compute_issued_at(target.person_id)
            expires_in_seconds = self.access_token_minutes * 60
            expires_dt = issued_dt + timedelta(seconds=expires_in_seconds)
            effective_scopes = list(scopes) if scopes else list(target.scopes)

            access_record = StoredToken(
                token_hash=hash_token(raw_access),
                kind="access",
                person_id=target.person_id,
                client_id=target.client_id,
                scopes=effective_scopes,
                resource=target.resource,
                issued_at=_format_utc(issued_dt),
                expires_at=_format_utc(expires_dt),
            )
            refresh_record = StoredToken(
                token_hash=hash_token(raw_refresh),
                kind="refresh",
                person_id=target.person_id,
                client_id=target.client_id,
                scopes=effective_scopes,
                resource=target.resource,
                issued_at=_format_utc(issued_dt),
                expires_at=None,
            )

            remaining.append(access_record)
            remaining.append(refresh_record)
            self._write_tokens_unlocked(remaining)

        return OAuthToken(
            access_token=raw_access,
            token_type="Bearer",
            expires_in=expires_in_seconds,
            scope=" ".join(effective_scopes),
            refresh_token=raw_refresh,
        )

    def revoke_by_hash(self, token_hash: str) -> bool:
        """Remove um token (access ou refresh) pelo seu hash SHA-256."""
        with file_lock(self._lock_path()):
            tokens = self._read_tokens_unlocked()
            remaining = [
                item for item in tokens if not secrets.compare_digest(item.token_hash, token_hash)
            ]
            removed = len(remaining) != len(tokens)
            if removed:
                self._write_tokens_unlocked(remaining)
            return removed

    # D-016: Valida que a pessoa está ativa e que o token foi emitido após code_created_at
    def _is_token_record_valid_for_person(self, record: StoredToken) -> bool:
        person = people.get(record.person_id, data_dir=self.data_dir)
        if person is None or not person.is_active:
            return False
        issued_dt = _parse_utc(record.issued_at)
        code_created_dt = _parse_utc(person.code_created_at)
        return issued_dt > code_created_dt

    def verify_access_token(
        self,
        raw_token: str,
        *,
        expected_resource: str | None = None,
    ) -> RSLAccessToken | None:
        """Valida um access token em texto puro contra os hashes em disco e o cadastro de pessoas."""
        if not raw_token or not raw_token.strip():
            return None

        candidate_hash = hash_token(raw_token)
        with file_lock(self._lock_path()):
            tokens = self._read_tokens_unlocked()

        record: StoredToken | None = None
        for item in tokens:
            if item.kind == "access" and secrets.compare_digest(item.token_hash, candidate_hash):
                record = item
                break

        if record is None or record.expires_at is None:
            return None

        now_dt = self.now()
        expires_dt = _parse_utc(record.expires_at)
        if now_dt >= expires_dt:
            return None

        if expected_resource is not None:
            norm_expected = normalize_resource_url(expected_resource)
            norm_actual = normalize_resource_url(record.resource)
            if norm_actual != norm_expected:
                return None

        if not self._is_token_record_valid_for_person(record):
            return None

        token_obj = RSLAccessToken(
            token="***",
            client_id=record.client_id,
            scopes=list(record.scopes),
            expires_at=int(expires_dt.timestamp()),
            resource=record.resource,
            person_id=record.person_id,
        )
        token_obj._token_hash = record.token_hash
        return token_obj

    def verify_refresh_token(self, raw_token: str) -> RSLRefreshToken | None:
        """Valida um refresh token em texto puro contra os hashes em disco e o cadastro de pessoas."""
        if not raw_token or not raw_token.strip():
            return None

        candidate_hash = hash_token(raw_token)
        with file_lock(self._lock_path()):
            tokens = self._read_tokens_unlocked()

        record: StoredToken | None = None
        for item in tokens:
            if item.kind == "refresh" and secrets.compare_digest(item.token_hash, candidate_hash):
                record = item
                break

        if record is None:
            return None

        if record.expires_at is not None:
            expires_dt = _parse_utc(record.expires_at)
            if self.now() >= expires_dt:
                return None

        if not self._is_token_record_valid_for_person(record):
            return None

        token_obj = RSLRefreshToken(
            token="***",
            client_id=record.client_id,
            scopes=list(record.scopes),
            expires_at=None,
            person_id=record.person_id,
            resource=record.resource,
        )
        token_obj._token_hash = record.token_hash
        return token_obj
