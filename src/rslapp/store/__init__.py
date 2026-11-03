"""Armazenamento local em arquivos: listas, buscas, log legível e cache."""

from __future__ import annotations

import copy
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from rslapp.store._atomic import (
    atomic_write_exclusive,
    atomic_write_replace,
    existing_id_numbers,
    format_seq_id,
    next_id_number,
    parse_seq_id,
    sanitize_query,
    sanitize_string,
)
from rslapp.store.cache import (
    cache_file_path,
    compute_cache_key,
    format_utc_iso,
    parse_utc_timestamp,
    read_cache_entry,
    validate_source_name,
    write_cache_entry,
)
from rslapp.store.log import format_log_entry

__all__ = [
    "Store",
    "compute_cache_key",
    "format_log_entry",
    "validate_source_name",
]

_LOCKS_GUARD = threading.Lock()
_DIR_LOCKS: dict[Path, threading.Lock] = {}
_RESERVED_LISTS: dict[Path, set[int]] = {}
_RESERVED_SEARCHES: dict[Path, set[int]] = {}


def _get_dir_state(data_dir: Path) -> tuple[threading.Lock, set[int], set[int]]:
    key = data_dir.resolve()
    with _LOCKS_GUARD:
        if key not in _DIR_LOCKS:
            _DIR_LOCKS[key] = threading.Lock()
            _RESERVED_LISTS[key] = set()
            _RESERVED_SEARCHES[key] = set()
        return _DIR_LOCKS[key], _RESERVED_LISTS[key], _RESERVED_SEARCHES[key]


def _normalize_source_entry(src: dict[str, Any]) -> dict[str, Any]:
    """Normaliza uma linha de fonte da busca e limpa credenciais (FR-05, NFR-03)."""
    fetched_at = src.get("fetched_at")
    return {
        "name": sanitize_string(str(src["name"])),
        "query": sanitize_string(str(src.get("query") or "")),
        "status": sanitize_string(str(src["status"])),
        "reason": sanitize_string(str(src["reason"])) if src.get("reason") is not None else None,
        "found": int(src["found"]) if src.get("found") is not None else None,
        "fetched": int(src["fetched"]) if src.get("fetched") is not None else None,
        "from_cache": bool(src.get("from_cache", False)),
        "fetched_at": sanitize_string(str(fetched_at)) if fetched_at is not None else None,
    }


def _normalize_list_payload(
    list_data: dict[str, Any],
    *,
    list_id: str,
    search_id: str,
    default_created_at: str,
) -> dict[str, Any]:
    """Monta o dicionário padronizado de uma lista (FR-09, FR-12, NFR-03)."""
    status = str(list_data.get("status", "complete"))
    if status not in ("complete", "incomplete"):
        raise ValueError(f"Status de lista inválido: {status}")
    works = sanitize_query(copy.deepcopy(list_data.get("works") or []))
    total = int(list_data["total"]) if "total" in list_data else len(works)
    created_raw = list_data.get("created_at")
    created_at = (
        format_utc_iso(parse_utc_timestamp(created_raw))
        if created_raw is not None
        else default_created_at
    )
    return {
        "id": list_id,
        "search_id": search_id,
        "created_at": created_at,
        "status": status,
        "total": total,
        "works": works,
    }


def _normalize_search_payload(
    search_data: dict[str, Any],
    *,
    search_id: str,
    list_id: str,
    default_created_at: str,
) -> dict[str, Any]:
    """Monta o dicionário padronizado de uma busca (FR-05, NFR-03)."""
    kind = str(search_data.get("kind", "terms"))
    if kind not in ("terms", "work", "related", "repeat"):
        raise ValueError(f"Tipo de busca inválido: {kind}")
    origin_raw = search_data.get("origin")
    origin: dict[str, Any] | None = None
    if origin_raw is not None:
        if not isinstance(origin_raw, dict) or not origin_raw.get("work"):
            raise ValueError("Campo 'origin' inválido")
        direction = str(origin_raw.get("direction", ""))
        if direction not in ("references", "citations"):
            raise ValueError("Campo 'origin.direction' inválido")
        origin = {
            "work": sanitize_string(str(origin_raw["work"])),
            "direction": direction,
        }
    elif kind == "related":
        raise ValueError("Busca 'related' exige 'origin'")

    repeated_raw = search_data.get("repeated_from")
    repeated_from = sanitize_string(str(repeated_raw)) if repeated_raw is not None else None
    created_raw = search_data.get("created_at")
    created_at = (
        format_utc_iso(parse_utc_timestamp(created_raw))
        if created_raw is not None
        else default_created_at
    )
    sources = [_normalize_source_entry(s) for s in (search_data.get("sources") or [])]

    return {
        "id": search_id,
        "created_at": created_at,
        "kind": kind,
        "request_summary": sanitize_string(str(search_data.get("request_summary") or "")),
        "list_id": list_id,
        "repeated_from": repeated_from,
        "origin": origin,
        "sources": sources,
    }


# D-007, FR-05, FR-09, FR-12, FR-13, NFR-03, NFR-06: Armazenamento somente em arquivos
class Store:
    """Gerencia buscas, listas, log legível e cache na pasta de dados."""

    def __init__(self, data_dir: Path | str, cache_days: int = 7) -> None:
        if type(cache_days) is not int or cache_days <= 0:
            raise ValueError("cache_days deve ser um inteiro positivo")
        self.data_dir: Path = Path(data_dir)
        self.cache_days: int = cache_days

    @property
    def lists_dir(self) -> Path:
        return self.data_dir / "lists"

    @property
    def searches_dir(self) -> Path:
        return self.data_dir / "searches"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def log_path(self) -> Path:
        return self.data_dir / "log.md"

    def next_list_id(self) -> str:
        """Devolve o próximo identificador sequencial de lista (l-NNNN)."""
        _, reserved_lists, _ = _get_dir_state(self.data_dir)
        return format_seq_id("l", next_id_number(self.lists_dir, "l", reserved_lists))

    def next_search_id(self) -> str:
        """Devolve o próximo identificador sequencial de busca (s-NNNN)."""
        _, _, reserved_searches = _get_dir_state(self.data_dir)
        return format_seq_id("s", next_id_number(self.searches_dir, "s", reserved_searches))

    # FR-09, FR-12, D-007: Gravação exclusiva e imutável de lista em lists/l-NNNN.json
    def save_list(self, list_data: dict[str, Any]) -> dict[str, Any]:
        """Grava uma lista em lists/l-NNNN.json sem permitir sobrescrita."""
        lock, reserved_lists, _ = _get_dir_state(self.data_dir)
        explicit_id = list_data.get("id")
        now_iso = format_utc_iso(parse_utc_timestamp(None))
        search_id = str(list_data.get("search_id") or "s-0001")
        parse_seq_id(search_id, "s")

        if explicit_id is not None:
            parse_seq_id(str(explicit_id), "l")
            payload = _normalize_list_payload(
                list_data,
                list_id=str(explicit_id),
                search_id=search_id,
                default_created_at=now_iso,
            )
            dest = self.lists_dir / f"{payload['id']}.json"
            content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
            atomic_write_exclusive(dest, content)
            return copy.deepcopy(payload)

        with lock:
            num = next_id_number(self.lists_dir, "l", reserved_lists)
            reserved_lists.add(num)
        try:
            while True:
                list_id = format_seq_id("l", num)
                payload = _normalize_list_payload(
                    list_data,
                    list_id=list_id,
                    search_id=search_id,
                    default_created_at=now_iso,
                )
                dest = self.lists_dir / f"{list_id}.json"
                content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
                try:
                    atomic_write_exclusive(dest, content)
                    return copy.deepcopy(payload)
                except FileExistsError:
                    if not dest.exists():
                        raise
                    with lock:
                        reserved_lists.discard(num)
                        num = max(num + 1, next_id_number(self.lists_dir, "l", reserved_lists))
                        reserved_lists.add(num)
        finally:
            with lock:
                reserved_lists.discard(num)

    # FR-12: Leitura de lista salva em lists/l-NNNN.json
    def get_list(self, list_id: str) -> dict[str, Any]:
        """Lê e devolve uma lista salva pelo seu identificador."""
        parse_seq_id(list_id, "l")
        path = self.lists_dir / f"{list_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Lista não encontrada: {list_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    # FR-05, D-007: Gravação exclusiva e imutável de busca em searches/s-NNNN.json
    def save_search(self, search_data: dict[str, Any]) -> dict[str, Any]:
        """Grava uma busca em searches/s-NNNN.json sem permitir sobrescrita."""
        lock, _, reserved_searches = _get_dir_state(self.data_dir)
        explicit_id = search_data.get("id")
        now_iso = format_utc_iso(parse_utc_timestamp(None))
        list_id = str(search_data.get("list_id") or "l-0001")
        parse_seq_id(list_id, "l")

        if explicit_id is not None:
            parse_seq_id(str(explicit_id), "s")
            payload = _normalize_search_payload(
                search_data,
                search_id=str(explicit_id),
                list_id=list_id,
                default_created_at=now_iso,
            )
            dest = self.searches_dir / f"{payload['id']}.json"
            content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
            atomic_write_exclusive(dest, content)
            return copy.deepcopy(payload)

        with lock:
            num = next_id_number(self.searches_dir, "s", reserved_searches)
            reserved_searches.add(num)
        try:
            while True:
                search_id = format_seq_id("s", num)
                payload = _normalize_search_payload(
                    search_data,
                    search_id=search_id,
                    list_id=list_id,
                    default_created_at=now_iso,
                )
                dest = self.searches_dir / f"{search_id}.json"
                content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
                try:
                    atomic_write_exclusive(dest, content)
                    return copy.deepcopy(payload)
                except FileExistsError:
                    if not dest.exists():
                        raise
                    with lock:
                        reserved_searches.discard(num)
                        num = max(num + 1, next_id_number(self.searches_dir, "s", reserved_searches))
                        reserved_searches.add(num)
        finally:
            with lock:
                reserved_searches.discard(num)

    # FR-05: Leitura de busca salva em searches/s-NNNN.json
    def get_search(self, search_id: str) -> dict[str, Any]:
        """Lê e devolve uma busca salva pelo seu identificador."""
        parse_seq_id(search_id, "s")
        path = self.searches_dir / f"{search_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Busca não encontrada: {search_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def list_searches(self) -> list[dict[str, Any]]:
        """Devolve todas as buscas gravadas em searches/, ordenadas numericamente pelo id."""
        numbers = existing_id_numbers(self.searches_dir, "s")
        results: list[dict[str, Any]] = []
        for num in numbers:
            sid = format_seq_id("s", num)
            path = self.searches_dir / f"{sid}.json"
            if path.exists():
                results.append(json.loads(path.read_text(encoding="utf-8")))
        return results

    # FR-05, FR-13, D-007: Acréscimo atômico de uma entrada ao log.md
    def append_log(
        self,
        search_data: dict[str, Any],
        list_data: dict[str, Any] | None = None,
    ) -> str:
        """Acrescenta uma entrada de busca ao log.md usando arquivo temporário e os.replace."""
        if list_data is None:
            list_id = search_data.get("list_id")
            if list_id:
                list_path = self.lists_dir / f"{list_id}.json"
                if list_path.exists():
                    list_data = json.loads(list_path.read_text(encoding="utf-8"))

        entry = format_log_entry(search_data, list_data)
        lock, _, _ = _get_dir_state(self.data_dir)
        with lock:
            existing = (
                self.log_path.read_text(encoding="utf-8").rstrip("\n")
                if self.log_path.exists()
                else ""
            )
            new_content = f"{existing}\n\n{entry}\n" if existing else f"{entry}\n"
            atomic_write_replace(self.log_path, new_content)
        return entry

    def read_log(self) -> str:
        """Lê o conteúdo atual de log.md (ou string vazia se ainda não existir)."""
        if not self.log_path.exists():
            return ""
        return self.log_path.read_text(encoding="utf-8")

    # FR-13, D-007: Reconstrução byte a byte do log.md a partir de searches/
    def rebuild_log(self) -> str:
        """Reconstrói log.md inteiramente a partir dos arquivos em searches/ em ordem numérica."""
        lock, _, _ = _get_dir_state(self.data_dir)
        with lock:
            searches = self.list_searches()
            entries: list[str] = []
            for search in searches:
                list_id = search.get("list_id")
                list_data: dict[str, Any] | None = None
                if list_id:
                    list_path = self.lists_dir / f"{list_id}.json"
                    if list_path.exists():
                        list_data = json.loads(list_path.read_text(encoding="utf-8"))
                entries.append(format_log_entry(search, list_data))
            content = "\n\n".join(entries) + "\n" if entries else ""
            atomic_write_replace(self.log_path, content)
            return content

    # D-007, FR-05, FR-09, FR-12, FR-13: Ordem obrigatória de gravação: lista -> busca -> log
    def record_search(
        self,
        search_data: dict[str, Any],
        list_data: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Reserva os IDs e grava na ordem: 1) lists/, 2) searches/, 3) log.md."""
        lock, reserved_lists, reserved_searches = _get_dir_state(self.data_dir)
        explicit_list_id = list_data.get("id")
        explicit_search_id = search_data.get("id")
        now_iso = format_utc_iso(parse_utc_timestamp(None))

        list_num: int | None = None
        search_num: int | None = None

        with lock:
            if explicit_list_id is not None:
                list_num = parse_seq_id(str(explicit_list_id), "l")
                list_id = str(explicit_list_id)
            else:
                list_num = next_id_number(self.lists_dir, "l", reserved_lists)
                reserved_lists.add(list_num)
                list_id = format_seq_id("l", list_num)

            if explicit_search_id is not None:
                search_num = parse_seq_id(str(explicit_search_id), "s")
                search_id = str(explicit_search_id)
                if (self.searches_dir / f"{search_id}.json").exists():
                    raise FileExistsError(f"Busca já existe: {search_id}")
            else:
                search_num = next_id_number(self.searches_dir, "s", reserved_searches)
                reserved_searches.add(search_num)
                search_id = format_seq_id("s", search_num)

        try:
            # 1. Grava a lista primeiro (lists/l-NNNN.json)
            while True:
                list_payload = _normalize_list_payload(
                    list_data,
                    list_id=list_id,
                    search_id=search_id,
                    default_created_at=now_iso,
                )
                list_dest = self.lists_dir / f"{list_id}.json"
                list_json = json.dumps(list_payload, ensure_ascii=False, indent=2) + "\n"
                try:
                    atomic_write_exclusive(list_dest, list_json)
                    break
                except FileExistsError:
                    if explicit_list_id is not None or not list_dest.exists():
                        raise
                    with lock:
                        if list_num is not None:
                            reserved_lists.discard(list_num)
                        list_num = next_id_number(self.lists_dir, "l", reserved_lists)
                        reserved_lists.add(list_num)
                        list_id = format_seq_id("l", list_num)
                        if explicit_search_id is None and search_num is not None:
                            reserved_searches.discard(search_num)
                            search_num = next_id_number(self.searches_dir, "s", reserved_searches)
                            reserved_searches.add(search_num)
                            search_id = format_seq_id("s", search_num)

            # 2. Grava a busca em segundo lugar (searches/s-NNNN.json)
            while True:
                search_payload = _normalize_search_payload(
                    search_data,
                    search_id=search_id,
                    list_id=list_id,
                    default_created_at=now_iso,
                )
                search_dest = self.searches_dir / f"{search_id}.json"
                search_json = json.dumps(search_payload, ensure_ascii=False, indent=2) + "\n"
                try:
                    atomic_write_exclusive(search_dest, search_json)
                    break
                except FileExistsError:
                    if explicit_search_id is not None or not search_dest.exists():
                        raise
                    with lock:
                        if search_num is not None:
                            reserved_searches.discard(search_num)
                        search_num = next_id_number(self.searches_dir, "s", reserved_searches)
                        reserved_searches.add(search_num)
                        search_id = format_seq_id("s", search_num)

            # 3. Grava a entrada no log legível por último (log.md)
            self.append_log(search_payload, list_payload)

            return copy.deepcopy(search_payload), copy.deepcopy(list_payload)
        finally:
            with lock:
                if explicit_list_id is None and list_num is not None:
                    reserved_lists.discard(list_num)
                if explicit_search_id is None and search_num is not None:
                    reserved_searches.discard(search_num)

    # NFR-03, NFR-06, D-007: Operações de cache por fonte e consulta
    def cache_path(self, source: str, query: dict[str, Any]) -> Path:
        """Devolve o caminho do arquivo de cache para a fonte e consulta informadas."""
        return cache_file_path(self.cache_dir, source, query)

    def set_cache(
        self,
        source: str,
        query: dict[str, Any],
        response: Any,
        *,
        fetched_at: datetime | str | None = None,
    ) -> Path:
        """Grava resposta no cache com prazo de validade, sem chaves de API."""
        return write_cache_entry(
            self.cache_dir,
            source,
            query,
            response,
            self.cache_days,
            fetched_at=fetched_at,
        )

    def get_cache(
        self,
        source: str,
        query: dict[str, Any],
        *,
        now: datetime | str | None = None,
    ) -> dict[str, Any] | None:
        """Lê resposta do cache se estiver dentro do prazo; devolve None se vencida ou ausente."""
        return read_cache_entry(self.cache_dir, source, query, now=now)
