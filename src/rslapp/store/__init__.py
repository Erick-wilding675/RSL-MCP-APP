"""Armazenamento local em arquivos: listas, buscas, log legível e cache."""

from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rslapp.core.notes import sanitize_filename_id, validate_note_data
from rslapp.core.protocols import sanitize_protocol_id, validate_protocol_data
from rslapp.core.screening import calculate_screening_summary
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


# D-007, D-012, D-013, FR-05, FR-09, FR-12, FR-13, NFR-03, NFR-06: Armazenamento somente em arquivos
class Store:
    """Gerencia buscas, listas, log legível e cache na pasta de dados."""

    def __init__(
        self,
        data_dir: Path | str,
        cache_days: int = 7,
        cache_dir: Path | str | None = None,
    ) -> None:
        if type(cache_days) is not int or cache_days <= 0:
            raise ValueError("cache_days deve ser um inteiro positivo")
        self.data_dir: Path = Path(data_dir)
        self.cache_days: int = cache_days
        self.lists_dir: Path = self.data_dir / "lists"
        self.searches_dir: Path = self.data_dir / "searches"
        self.screening_dir: Path = self.data_dir / "screening"
        self.notes_dir: Path = self.data_dir / "notes"
        self.protocols_dir: Path = self.data_dir / "protocols"
        self.differential_dir: Path = self.data_dir / "differential"
        self.fulltext_dir: Path = self.data_dir / "fulltext"
        # D-012, D-013: Pasta de cache opcional separada da pasta de dados da pessoa
        self.cache_dir: Path = Path(cache_dir) if cache_dir is not None else self.data_dir / "cache"
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

    # FR-25, D-036: Gravação atômica de decisão de triagem associada à lista
    def save_screening_decision(
        self, list_id: str, decision: dict[str, Any]
    ) -> dict[str, Any]:
        """Salva ou atualiza a decisão de triagem de um trabalho em screening/{list_id}.json."""
        self.get_list(list_id)  # Valida se a lista existe
        work_id = str(decision.get("work_id", "")).strip()
        if not work_id:
            raise ValueError("decision deve conter 'work_id'")

        now_iso = format_utc_iso(parse_utc_timestamp(None))
        screening_path = self.screening_dir / f"{list_id}.json"

        with file_lock(self.lock_path):
            if screening_path.exists():
                data = json.loads(screening_path.read_text(encoding="utf-8"))
            else:
                data = {
                    "list_id": list_id,
                    "updated_at": now_iso,
                    "decisions": {},
                }

            if "decisions" not in data or not isinstance(data["decisions"], dict):
                data["decisions"] = {}

            data["decisions"][work_id] = copy.deepcopy(decision)
            data["updated_at"] = now_iso

            content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
            atomic_write_replace(screening_path, content)

        return copy.deepcopy(data)

    # FR-25, D-036: Leitura das decisões de triagem de uma lista
    def get_screening(self, list_id: str) -> dict[str, Any]:
        """Recupera todas as decisões de triagem registradas para a lista."""
        self.get_list(list_id)  # Valida existência da lista
        screening_path = self.screening_dir / f"{list_id}.json"
        if not screening_path.exists():
            return {
                "list_id": list_id,
                "updated_at": None,
                "decisions": {},
            }
        return json.loads(screening_path.read_text(encoding="utf-8"))

    # FR-25, D-036, D-037: Resumo estatístico das decisões de triagem
    def get_screening_summary(self, list_id: str) -> dict[str, Any]:
        """Calcula totais, percentual e discriminação por motivo da triagem da lista."""
        list_data = self.get_list(list_id)
        screening_data = self.get_screening(list_id)
        total_works = list_data.get("total")
        if total_works is None or not isinstance(total_works, int):
            total_works = len(list_data.get("works", []))
        return calculate_screening_summary(
            total_works=total_works,
            decisions=screening_data.get("decisions", {}),
        )

    # FR-29, D-040: Fichamento científico estruturado no Store
    def save_note(self, list_id: str, note_data: dict[str, Any]) -> dict[str, Any]:
        """Salva ou atualiza a ficha científica de um trabalho em notes/{list_id}/{work_id}.json."""
        self.get_list(list_id)  # Valida se a lista existe
        work_id = note_data.get("work_id")
        if not work_id:
            raise ValueError("note_data deve conter 'work_id'")

        kwargs = {k: v for k, v in note_data.items() if k not in ("list_id", "work_id")}
        valid_note = validate_note_data(list_id=list_id, work_id=work_id, **kwargs)

        list_notes_dir = self.notes_dir / list_id
        list_notes_dir.mkdir(parents=True, exist_ok=True)
        note_filename = f"{sanitize_filename_id(work_id)}.json"
        note_path = list_notes_dir / note_filename

        with file_lock(self.lock_path):
            content = json.dumps(valid_note, ensure_ascii=False, indent=2) + "\n"
            atomic_write_replace(note_path, content)

        return copy.deepcopy(valid_note)

    def get_note(self, list_id: str, work_id: str | int) -> dict[str, Any] | None:
        """Recupera a ficha científica de um trabalho, se existir."""
        self.get_list(list_id)  # Valida se a lista existe
        note_filename = f"{sanitize_filename_id(work_id)}.json"
        note_path = self.notes_dir / list_id / note_filename
        if not note_path.exists():
            return None
        return json.loads(note_path.read_text(encoding="utf-8"))

    def list_notes(self, list_id: str) -> list[dict[str, Any]]:
        """Lista todas as fichas científicas registradas para a lista."""
        self.get_list(list_id)  # Valida existência da lista
        list_notes_dir = self.notes_dir / list_id
        if not list_notes_dir.exists():
            return []

        notes: list[dict[str, Any]] = []
        for file in sorted(list_notes_dir.glob("*.json")):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                notes.append(data)
            except (json.JSONDecodeError, OSError):
                continue
        return notes

    def delete_note(self, list_id: str, work_id: str | int) -> bool:
        """Remove a ficha científica de um trabalho."""
        self.get_list(list_id)
        note_filename = f"{sanitize_filename_id(work_id)}.json"
        note_path = self.notes_dir / list_id / note_filename
        with file_lock(self.lock_path):
            if note_path.exists():
                note_path.unlink()
                return True
        return False

    # FR-30, D-041: Gestão de Protocolos Metodológicos Pré-Busca com Versionamento
    def save_protocol(self, protocol_data: dict[str, Any]) -> dict[str, Any]:
        """Salva ou atualiza um protocolo de pesquisa, arquivando versões anteriores no histórico."""
        if not isinstance(protocol_data, dict):
            raise TypeError("protocol_data deve ser um dict")

        pid = protocol_data.get("id")
        existing: dict[str, Any] | None = None
        if pid:
            clean_pid = sanitize_protocol_id(pid)
            main_path = self.protocols_dir / f"{clean_pid}.json"
            if main_path.exists():
                try:
                    existing = json.loads(main_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    existing = None

        new_data = copy.deepcopy(protocol_data)
        history = list(new_data.get("history") or [])

        if existing:
            old_version = int(existing.get("version", 1))
            new_version = old_version + 1
            new_data["version"] = new_version
            # Arquiva a versão anterior no histórico se ainda não estiver arquivada
            history_dir = self.protocols_dir / "history"
            history_dir.mkdir(parents=True, exist_ok=True)
            hist_file = history_dir / f"{existing['id']}_v{old_version}.json"
            if not hist_file.exists():
                hist_content = json.dumps(existing, ensure_ascii=False, indent=2) + "\n"
                atomic_write_replace(hist_file, hist_content)

            history.append({
                "version": old_version,
                "timestamp": existing.get("updated_at") or existing.get("created_at"),
                "summary": f"Versão v{old_version} arquivada antes da atualização para v{new_version}",
            })
            new_data["history"] = history
            # Mantém data de criação original
            if existing.get("created_at"):
                new_data["created_at"] = existing["created_at"]

        # Chama a validação do modelo
        valid_protocol = validate_protocol_data(**new_data)

        self.protocols_dir.mkdir(parents=True, exist_ok=True)
        protocol_file = self.protocols_dir / f"{valid_protocol['id']}.json"

        with file_lock(self.lock_path):
            content = json.dumps(valid_protocol, ensure_ascii=False, indent=2) + "\n"
            atomic_write_replace(protocol_file, content)

        return copy.deepcopy(valid_protocol)

    def get_protocol(
        self, protocol_id: str, version: int | None = None
    ) -> dict[str, Any] | None:
        """Recupera um protocolo metodológico atual ou uma versão arquivada específica."""
        clean_pid = sanitize_protocol_id(protocol_id)
        main_path = self.protocols_dir / f"{clean_pid}.json"

        if not main_path.exists():
            return None

        try:
            current_data = json.loads(main_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        if version is None or int(current_data.get("version", 1)) == int(version):
            return current_data

        # Busca versão histórica
        hist_path = self.protocols_dir / "history" / f"{clean_pid}_v{int(version)}.json"
        if hist_path.exists():
            try:
                return json.loads(hist_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None

        return None

    def list_protocols(self) -> list[dict[str, Any]]:
        """Lista todos os protocolos metodológicos ativos ordenados por data de atualização."""
        if not self.protocols_dir.exists():
            return []

        protocols: list[dict[str, Any]] = []
        for file in self.protocols_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                protocols.append(data)
            except (json.JSONDecodeError, OSError):
                continue

        protocols.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
        return protocols

    def delete_protocol(self, protocol_id: str) -> bool:
        """Remove o protocolo principal e todas as suas versões arquivadas."""
        clean_pid = sanitize_protocol_id(protocol_id)
        main_path = self.protocols_dir / f"{clean_pid}.json"

        with file_lock(self.lock_path):
            existed = False
            if main_path.exists():
                main_path.unlink()
                existed = True

            history_dir = self.protocols_dir / "history"
            if history_dir.exists():
                for hist_file in history_dir.glob(f"{clean_pid}_v*.json"):
                    hist_file.unlink()

            return existed

    # FR-32, D-043: Armazenamento de comparações diferenciais da Revisão Viva
    def save_differential(self, diff_data: dict[str, Any]) -> dict[str, Any]:
        """Salva a comparação diferencial de busca atomicamente em differential/{base_list_id}_{new_list_id}_{timestamp}.json."""
        self.differential_dir.mkdir(parents=True, exist_ok=True)
        base_id = sanitize_filename_id(str(diff_data.get("base_list_id", "diff")))
        new_id = sanitize_filename_id(str(diff_data.get("new_list_id", "diff")))
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        diff_file = self.differential_dir / f"{base_id}_{new_id}_{ts}.json"
        with file_lock(self.lock_path):
            content = json.dumps(diff_data, ensure_ascii=False, indent=2) + "\n"
            atomic_write_replace(diff_file, content)
        return copy.deepcopy(diff_data)

    def list_differentials(self, list_id: str | None = None) -> list[dict[str, Any]]:
        """Lista as comparações diferenciais salvas, opcionalmente filtradas por list_id (base ou nova)."""
        if not self.differential_dir.exists():
            return []
        results: list[dict[str, Any]] = []
        for file in self.differential_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                if list_id is not None and data.get("base_list_id") != list_id and data.get("new_list_id") != list_id:
                    continue
                results.append(data)
            except (json.JSONDecodeError, OSError):
                continue
        results.sort(key=lambda d: d.get("updated_at", ""), reverse=True)
        return results

    def get_latest_differential(self, list_id: str) -> dict[str, Any] | None:
        """Devolve a comparação diferencial mais recente para a lista especificada."""
        diffs = self.list_differentials(list_id)
        return diffs[0] if diffs else None

    # FR-34, D-045: Armazenamento e manifesto de texto completo (Open Access)
    def save_fulltext_record(self, list_id: str, record_data: dict[str, Any]) -> dict[str, Any]:
        """Salva ou atualiza um registro de texto completo no manifesto da lista."""
        clean_lid = sanitize_filename_id(list_id)
        list_ft_dir = self.fulltext_dir / clean_lid
        list_ft_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = list_ft_dir / "manifest.json"

        with file_lock(self.lock_path):
            manifest: dict[str, Any] = {
                "list_id": clean_lid,
                "records": {},
                "updated_at": format_utc_iso(parse_utc_timestamp(None)),
            }
            if manifest_file.exists():
                try:
                    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass
            records = manifest.setdefault("records", {})
            wid = str(record_data.get("work_id", ""))
            records[wid] = copy.deepcopy(record_data)
            manifest["updated_at"] = format_utc_iso(parse_utc_timestamp(None))
            atomic_write_replace(manifest_file, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        return manifest

    def get_fulltext_manifest(self, list_id: str) -> dict[str, Any]:
        """Devolve o manifesto de texto completo para a lista especificada."""
        clean_lid = sanitize_filename_id(list_id)
        manifest_file = self.fulltext_dir / clean_lid / "manifest.json"
        if not manifest_file.exists():
            return {"list_id": clean_lid, "records": {}, "updated_at": None}
        try:
            return json.loads(manifest_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"list_id": clean_lid, "records": {}, "updated_at": None}

    def get_fulltext_dir(self, list_id: str) -> Path:
        """Devolve o caminho da pasta de textos completos para a lista."""
        clean_lid = sanitize_filename_id(list_id)
        p = self.fulltext_dir / clean_lid
        p.mkdir(parents=True, exist_ok=True)
        return p




