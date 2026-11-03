"""Formatação e validação de entradas do log legível (log.md)."""

from __future__ import annotations

from typing import Any

from rslapp.store._atomic import strip_url_credentials
from rslapp.store.cache import parse_utc_timestamp

_KIND_LABELS = {"terms": "busca por termos", "work": "busca de artigo", "repeat": "repetição"}
_DIRECTION_LABELS = {"references": "referências", "citations": "citações"}
_LIST_STATUS_LABELS = {"complete": "completa", "incomplete": "incompleta"}


def _one_line(text: str) -> str:
    return text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


def _format_source_line(src: Any) -> str:
    if type(src) is not dict or not src.get("name") or not src.get("status"):
        raise ValueError("Fonte inválida: 'name' e 'status' são obrigatórios")
    name, status = _one_line(str(src["name"])), _one_line(str(src["status"]))
    query = _one_line(strip_url_credentials(str(src.get("query") or "")))
    found, fetched, reason = src.get("found"), src.get("fetched"), src.get("reason")
    from_cache, fetched_at = bool(src.get("from_cache", False)), src.get("fetched_at")

    parts: list[str] = [name, status]
    if status == "ok" or (found is not None and fetched is not None):
        parts.append(f"encontrados {found or 0}, trazidos {fetched or 0}")
    if reason:
        parts.append(_one_line(strip_url_credentials(str(reason))))
    if from_cache:
        date_str = parse_utc_timestamp(str(fetched_at)).strftime("%Y-%m-%d") if fetched_at else ""
        parts.append(f"cache: sim, obtida em {date_str}" if date_str else "cache: sim")
    elif status == "ok":
        parts.append("cache: não")
    parts.append(f"string: `{query}`")
    return "- " + " · ".join(parts)


# FR-05, FR-13, NFR-03, NFR-06: Geração determinística de uma entrada de log.md em português
def format_log_entry(search_data: dict[str, Any], list_data: dict[str, Any] | None = None) -> str:
    kind, origin = search_data.get("kind"), search_data.get("origin")
    if origin is not None and (
        type(origin) is not dict or not origin.get("work") or origin.get("direction") not in _DIRECTION_LABELS
    ):
        raise ValueError("Campo 'origin' inválido")
    if kind == "related":
        if origin is None:
            raise ValueError("Busca do tipo 'related' exige 'origin'")
        kind_label = _DIRECTION_LABELS[origin["direction"]]
    elif type(kind) is str and kind in _KIND_LABELS:
        kind_label = _KIND_LABELS[kind]
    else:
        raise ValueError(f"Tipo de busca inválido: {kind!r}")

    sources = search_data.get("sources")
    if type(sources) is not list:
        raise ValueError("Campo 'sources' deve ser uma lista")

    created_str = parse_utc_timestamp(str(search_data["created_at"])).strftime("%Y-%m-%d %H:%M UTC")
    summary = _one_line(str(search_data.get("request_summary") or ""))
    list_id = str(search_data["list_id"])

    if list_data is None:
        list_line = f"Lista: {list_id} · arquivo ausente"
    else:
        raw_status = list_data.get("status")
        if raw_status not in _LIST_STATUS_LABELS:
            raise ValueError(f"Status de lista inválido: {raw_status!r}")
        total = list_data.get("total", len(list_data.get("works") or []))
        if type(total) is not int or total < 0:
            raise ValueError(f"Total de lista inválido: {total!r}")
        unit = "artigo" if total == 1 else "artigos"
        list_line = f"Lista: {list_id} · {_LIST_STATUS_LABELS[raw_status]} · {total} {unit}"

    lines = [
        f"## {search_data['id']} · {created_str} · {kind_label}",
        f"Pedido: {summary}" if summary else "Pedido:",
    ]
    if search_data.get("repeated_from"):
        lines.append(f"Repetida de: {_one_line(str(search_data['repeated_from']))}")
    if origin is not None:
        lines.append(
            f"Artigo de origem: {_one_line(str(origin['work']))} · direção: {_DIRECTION_LABELS[origin['direction']]}"
        )
    lines.append(list_line)
    lines.extend(_format_source_line(src) for src in sources)
    return "\n".join(lines)
