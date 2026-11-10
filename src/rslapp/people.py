"""Cadastro de pessoas e códigos pessoais de acesso ao modo HTTP (D-012, D-016)."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from rslapp import config
from rslapp.store._atomic import atomic_write_replace, file_lock

# D-016: Identificador de 1 a 40 caracteres (a-z, 0-9, - e _), começando por letra ou número
PERSON_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$", re.ASCII)
CODE_PREFIX = "rsl_"
# D-016: Entropia mínima de 24 bytes aleatórios para o código pessoal
CODE_RANDOM_BYTES = 24


# D-012, D-016, D-004: Registro de pessoa sem expor código nem hash no repr
@dataclass(frozen=True)
class Person:
    """Representa uma pessoa cadastrada no servidor hospedado."""

    id: str
    created_at: str
    code_hash: str = field(repr=False)
    code_created_at: str
    revoked_at: str | None = None

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    @property
    def status(self) -> str:
        return "ativa" if self.revoked_at is None else "revogada"

    def __getitem__(self, key: str) -> Any:
        if key in ("id", "created_at", "code_hash", "code_created_at", "revoked_at"):
            return getattr(self, key)
        raise KeyError(key)

    def to_dict(self) -> dict[str, str | None]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "code_hash": self.code_hash,
            "code_created_at": self.code_created_at,
            "revoked_at": self.revoked_at,
        }


# D-016: Valida o identificador da pessoa e bloqueia caminhos relativos como ../
def validate_person_id(person_id: str) -> str:
    """Valida o formato do identificador de pessoa (1..40 chars, [a-z0-9][a-z0-9_-]*)."""
    if type(person_id) is not str or not PERSON_ID_RE.fullmatch(person_id):
        raise ValueError(
            "Identificador inválido: deve ter de 1 a 40 caracteres, usando apenas "
            "letras minúsculas sem acento (a-z), números (0-9), '-' e '_', "
            "começando por letra ou número."
        )
    return person_id


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _format_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _parse_utc(value: str) -> datetime:
    text = value.strip()
    dt = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text)
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _generate_code() -> str:
    return f"{CODE_PREFIX}{secrets.token_urlsafe(CODE_RANDOM_BYTES)}"


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _resolve_data_dir(data_dir: Path | str | None) -> Path:
    return Path(data_dir) if data_dir is not None else config.load().data_dir


def _people_file(base_dir: Path) -> Path:
    return base_dir / "auth" / "people.json"


def _lock_file(base_dir: Path) -> Path:
    return base_dir / "auth" / ".lock"


def _read_people(base_dir: Path) -> list[Person]:
    path = _people_file(base_dir)
    if not path.exists():
        return []
    return [
        Person(
            id=str(item["id"]),
            created_at=str(item["created_at"]),
            code_hash=str(item["code_hash"]),
            code_created_at=str(item["code_created_at"]),
            revoked_at=str(item["revoked_at"]) if item.get("revoked_at") is not None else None,
        )
        for item in json.loads(path.read_text(encoding="utf-8"))
    ]


# D-007, D-016: Gravação atômica do cadastro em <RSL_DATA_DIR>/auth/people.json
def _write_people(base_dir: Path, people_list: list[Person]) -> None:
    content = json.dumps([p.to_dict() for p in people_list], ensure_ascii=False, indent=2) + "\n"
    atomic_write_replace(_people_file(base_dir), content)


# D-012, D-016: Cadastra pessoa nova e devolve o código pessoal uma única vez
def add(person_id: str, *, data_dir: Path | str | None = None) -> str:
    """Cadastra uma nova pessoa, grava apenas o SHA-256 do código e devolve o código gerado."""
    validate_person_id(person_id)
    base_dir = _resolve_data_dir(data_dir)
    with file_lock(_lock_file(base_dir)):
        current = _read_people(base_dir)
        if any(p.id == person_id for p in current):
            raise ValueError(
                f"A pessoa '{person_id}' já está cadastrada. Use --replace para gerar um código novo."
            )
        code = _generate_code()
        now_iso = _format_utc(_now_utc())
        current.append(Person(person_id, now_iso, _hash_code(code), now_iso, None))
        _write_people(base_dir, current)
    return code


# D-016: Gera novo código para pessoa existente ou revogada, reativando-a e atualizando code_created_at
def replace_code(person_id: str, *, data_dir: Path | str | None = None) -> str:
    """Troca o código de uma pessoa existente (ou revogada), reativando-a."""
    validate_person_id(person_id)
    base_dir = _resolve_data_dir(data_dir)
    with file_lock(_lock_file(base_dir)):
        current = _read_people(base_dir)
        idx = next((i for i, p in enumerate(current) if p.id == person_id), None)
        if idx is None:
            raise ValueError(f"Pessoa '{person_id}' não encontrada.")
        existing = current[idx]
        code = _generate_code()
        while hmac.compare_digest(_hash_code(code), existing.code_hash):
            code = _generate_code()
        now_dt = max(_now_utc(), _parse_utc(existing.code_created_at) + timedelta(microseconds=1))
        current[idx] = Person(
            existing.id, existing.created_at, _hash_code(code), _format_utc(now_dt), None
        )
        _write_people(base_dir, current)
    return code


# D-016: Revoga o acesso da pessoa sem apagar seus dados
def revoke(person_id: str, *, data_dir: Path | str | None = None) -> Person:
    """Marca uma pessoa como revogada mantendo os dados dela."""
    validate_person_id(person_id)
    base_dir = _resolve_data_dir(data_dir)
    with file_lock(_lock_file(base_dir)):
        current = _read_people(base_dir)
        idx = next((i for i, p in enumerate(current) if p.id == person_id), None)
        if idx is None:
            raise ValueError(f"Pessoa '{person_id}' não encontrada.")
        existing = current[idx]
        updated = Person(
            existing.id,
            existing.created_at,
            existing.code_hash,
            existing.code_created_at,
            existing.revoked_at or _format_utc(_now_utc()),
        )
        current[idx] = updated
        _write_people(base_dir, current)
    return updated


# D-016: Lista todas as pessoas cadastradas sem expor código nem hash
def list_people(*, data_dir: Path | str | None = None) -> list[Person]:
    """Devolve a lista de pessoas cadastradas."""
    return _read_people(_resolve_data_dir(data_dir))


# D-012, D-016: Busca uma pessoa pelo identificador (ativa ou revogada)
def get(person_id: str, *, data_dir: Path | str | None = None) -> Person | None:
    """Devolve a pessoa correspondente ao id, ou None se não existir ou for inválido."""
    if type(person_id) is not str or not PERSON_ID_RE.fullmatch(person_id):
        return None
    return next((p for p in _read_people(_resolve_data_dir(data_dir)) if p.id == person_id), None)


# D-012, D-016: Localiza pessoa ativa pelo código pessoal usando hmac.compare_digest
def find_by_code(code: str, *, data_dir: Path | str | None = None) -> Person | None:
    """Devolve a pessoa ativa dona do código informado, ou None se inválido/revogada."""
    if type(code) is not str or not code.startswith(CODE_PREFIX) or len(code) <= len(CODE_PREFIX):
        return None
    candidate_hash = _hash_code(code)
    matched: Person | None = None
    for person in _read_people(_resolve_data_dir(data_dir)):
        if hmac.compare_digest(person.code_hash, candidate_hash):
            matched = person
    return matched if matched is not None and matched.is_active else None
