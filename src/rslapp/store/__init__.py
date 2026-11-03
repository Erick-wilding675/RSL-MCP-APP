"""Armazenamento local em arquivos: listas, buscas, log legível e cache."""

from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rslapp.store._atomic import (
    atomic_write_exclusive,
    atomic_write_replace,
    existing_id_numbers,
    file_lock,
    format_seq_id,
    parse_seq_id,
    strip_url_credentials,
)
from rslapp.store.cache import (
    compute_cache_key,
    format_utc_iso,
    parse_utc_timestamp,
    read_cache_entry,
    validate_source_name,
    write_cache_entry,
)
from rslapp.store.log import format_log_entry

__all__ = ["Store", "compute_cache_key", "format_log_entry", "validate_source_name"]


def _clean_sources(sources: Any) -> Any:
    if not isinstance(sources, list):
        return sources
    cleaned: list[Any] = []
    for item in sources:
        src = copy.deepcopy(item)
        if isinstance(src, dict):
            if isinstance(src.get("query"), str):
                src["query"] = strip_url_credentials(src["query"])
            if isinstance(src.get("reason"), str):
                src["reason"] = strip_url_credentials(src["reason"])
        cleaned.append(src)
    return cleaned


# D-007, FR-05, FR-09, FR-12, FR-13, NFR-03, NFR-06: Armazenamento somente em arquivos
class Store:
    """Gerencia buscas, listas, log legível e cache na pasta de dados."""

    def __init__(self, data_dir: Path | str, cache_days: int = 7) -> None:
        if type(cache_days) is not int or cache_days <= 0:
            raise ValueError("cache_days deve ser um inteiro positivo")
        self.data_dir: Path = Path(data_dir)
        self.cache_days: int = cache_days
        self.lists_dir: Path = self.data_dir / "lists"
        self.searches_dir: Path = self.data_dir / "searches"
        self.cache_dir: Path = self.data_dir / "cache"
        self.log_path: Path = self.data_dir / "log.md"
        self.lock_path: Path = self.data_dir / ".lock"

    # D-007, FR-05, FR-09, FR-12, FR-13: Ordem obrigatória de gravação: lista -> busca -> log
    def record_search(
        self, search_data: dict[str, Any], list_data: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if type(search_data) is not dict or type(list_data) is not dict:
            raise ValueError("search_data e list_data devem ser dicts")
        now_iso = format_utc_iso(parse_utc_timestamp(None))
        list_created = (
            format_utc_iso(parse_utc_timestamp(list_data["created_at"]))
            if list_data.get("created_at") is not None else now_iso
        )
        search_created = (
            format_utc_iso(parse_utc_timestamp(search_data["created_at"]))
            if search_data.get("created_at") is not None else now_iso
        )
        base_list, base_search = copy.deepcopy(list_data), copy.deepcopy(search_data)
        if "sources" in base_search:
            base_search["sources"] = _clean_sources(base_search["sources"])

        with file_lock(self.lock_path):
            nums = existing_id_numbers(self.lists_dir, "l") + existing_id_numbers(self.searches_dir, "s")
            num = (max(nums) if nums else 0) + 1
            while True:
                list_id, search_id = format_seq_id("l", num), format_seq_id("s", num)
                list_payload = {**base_list, "id": list_id, "search_id": search_id, "created_at": list_created}
                search_payload = {**base_search, "id": search_id, "list_id": list_id, "created_at": search_created}
                entry = format_log_entry(search_payload, list_payload)
                list_dest = self.lists_dir / f"{list_id}.json"
                try:
                    atomic_write_exclusive(list_dest, json.dumps(list_payload, ensure_ascii=False, indent=2) + "\n")
                    break
                except FileExistsError:
                    num += 1

            search_dest = self.searches_dir / f"{search_id}.json"
            atomic_write_exclusive(search_dest, json.dumps(search_payload, ensure_ascii=False, indent=2) + "\n")
            existing = self.log_path.read_text(encoding="utf-8").rstrip("\n") if self.log_path.exists() else ""
            atomic_write_replace(self.log_path, f"{existing}\n\n{entry}\n" if existing else f"{entry}\n")

        return copy.deepcopy(search_payload), copy.deepcopy(list_payload)

    # FR-12: Leitura de lista salva em lists/l-NNNN.json
    def get_list(self, list_id: str) -> dict[str, Any]:
        parse_seq_id(list_id, "l")
        path = self.lists_dir / f"{list_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Lista não encontrada: {list_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    # FR-05: Leitura de busca salva em searches/s-NNNN.json
    def get_search(self, search_id: str) -> dict[str, Any]:
        parse_seq_id(search_id, "s")
        path = self.searches_dir / f"{search_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Busca não encontrada: {search_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def list_searches(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for num in existing_id_numbers(self.searches_dir, "s"):
            path = self.searches_dir / f"{format_seq_id('s', num)}.json"
            if path.exists():
                results.append(json.loads(path.read_text(encoding="utf-8")))
        return results

    def read_log(self) -> str:
        return self.log_path.read_text(encoding="utf-8") if self.log_path.exists() else ""

    # FR-13, D-007: Reconstrução byte a byte do log.md a partir de searches/
    def rebuild_log(self) -> str:
        with file_lock(self.lock_path):
            entries: list[str] = []
            for search in self.list_searches():
                list_id = search.get("list_id")
                list_path = self.lists_dir / f"{list_id}.json" if isinstance(list_id, str) else None
                list_data = (
                    json.loads(list_path.read_text(encoding="utf-8"))
                    if list_path and list_path.exists() else None
                )
                entries.append(format_log_entry(search, list_data))
            content = "\n\n".join(entries) + "\n" if entries else ""
            atomic_write_replace(self.log_path, content)
            return content

    # NFR-03, NFR-06, D-007: Operações de cache por fonte e consulta
    def set_cache(
        self, source: str, query: dict[str, Any], response: Any, *, fetched_at: datetime | str | None = None
    ) -> Path:
        return write_cache_entry(self.cache_dir, source, query, response, self.cache_days, fetched_at=fetched_at)

    def get_cache(
        self, source: str, query: dict[str, Any], *, now: datetime | str | None = None
    ) -> dict[str, Any] | None:
        return read_cache_entry(self.cache_dir, source, query, now=now)
