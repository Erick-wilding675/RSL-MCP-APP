"""Formatação e reconstrução do log legível (log.md) a partir das buscas."""

from __future__ import annotations

from typing import Any

from rslapp.store._atomic import sanitize_string
from rslapp.store.cache import parse_utc_timestamp

_KIND_LABELS: dict[str, str] = {
    "terms": "busca por termos",
    "work": "busca de artigo",
    "repeat": "repetição",
}

_DIRECTION_LABELS: dict[str, str] = {
    "references": "referências",
    "citations": "citações",
}

_LIST_STATUS_LABELS: dict[str, str] = {
    "complete": "completa",
    "incomplete": "incompleta",
}


def resolve_kind_label(kind: str, origin: dict[str, Any] | None) -> str:
    """Traduz kind e origin.direction para o rótulo em português do cabeçalho do log."""
    if kind in _KIND_LABELS:
        return _KIND_LABELS[kind]
    if kind == "related":
        if not isinstance(origin, dict):
            raise ValueError("Busca do tipo 'related' exige o campo 'origin'")
        direction = origin.get("direction")
        if direction not in _DIRECTION_LABELS:
            raise ValueError("Campo 'origin.direction' deve ser 'references' ou 'citations'")
        return _DIRECTION_LABELS[direction]
    raise ValueError(f"Tipo de busca inválido: {kind}")


def _format_header_timestamp(created_at: str) -> str:
    """Formata created_at em 'YYYY-MM-DD HH:MM UTC'."""
    dt = parse_utc_timestamp(created_at)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def _format_fetched_date(fetched_at: str | None) -> str:
    """Extrai a data YYYY-MM-DD de fetched_at para exibição no log."""
    if not fetched_at:
        return ""
    text = str(fetched_at).strip()
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    dt = parse_utc_timestamp(text)
    return dt.strftime("%Y-%m-%d")


def _format_source_line(src: dict[str, Any]) -> str:
    """Formata uma linha de fonte no log.md sem expor chaves de API (FR-05, NFR-03, NFR-06)."""
    name = sanitize_string(str(src["name"]))
    status = sanitize_string(str(src["status"]))
    query = sanitize_string(str(src.get("query") or ""))
    found = src.get("found")
    fetched = src.get("fetched")
    reason = src.get("reason")
    from_cache = bool(src.get("from_cache", False))
    fetched_at = src.get("fetched_at")

    parts: list[str] = [name, status]
    if status == "ok":
        parts.append(f"encontrados {found or 0}, trazidos {fetched or 0}")
        if from_cache:
            date_str = _format_fetched_date(fetched_at)
            parts.append(f"cache: sim, obtida em {date_str}" if date_str else "cache: sim")
        else:
            parts.append("cache: não")
    else:
        if found is not None and fetched is not None:
            parts.append(f"encontrados {found}, trazidos {fetched}")
        if reason:
            parts.append(sanitize_string(str(reason)))
        if from_cache:
            date_str = _format_fetched_date(fetched_at)
            parts.append(f"cache: sim, obtida em {date_str}" if date_str else "cache: sim")

    parts.append(f"string: `{query}`")
    return "- " + " · ".join(parts)


# FR-05, FR-13, NFR-03, NFR-06: Geração determinística de uma entrada de log.md em português
def format_log_entry(
    search_data: dict[str, Any],
    list_data: dict[str, Any] | None = None,
) -> str:
    """Formata uma busca (e os metadados da lista correspondente) no formato legível de log.md."""
    search_id = str(search_data["id"])
    created_at_str = _format_header_timestamp(str(search_data["created_at"]))
    kind = str(search_data["kind"])
    origin = search_data.get("origin")
    kind_label = resolve_kind_label(kind, origin)

    request_summary = sanitize_string(str(search_data.get("request_summary") or ""))
    list_id = str(search_data["list_id"])
    repeated_from = search_data.get("repeated_from")

    if list_data is not None:
        raw_status = str(list_data.get("status", "complete"))
        total = int(list_data.get("total", len(list_data.get("works", []))))
    else:
        sources_list = search_data.get("sources") or []
        default_status = (
            "complete"
            if sources_list and all(s.get("status") == "ok" for s in sources_list)
            else "incomplete"
        )
        raw_status = str(search_data.get("status", default_status))
        total = int(
            search_data.get(
                "total",
                sum(int(s.get("fetched") or 0) for s in sources_list),
            )
        )

    if raw_status not in _LIST_STATUS_LABELS:
        raise ValueError(f"Status de lista inválido: {raw_status}")
    status_label = _LIST_STATUS_LABELS[raw_status]

    lines: list[str] = [
        f"## {search_id} · {created_at_str} · {kind_label}",
        f"Pedido: {request_summary}" if request_summary else "Pedido:",
    ]

    if repeated_from:
        lines.append(f"Repetida de: {sanitize_string(str(repeated_from))}")

    if isinstance(origin, dict) and origin.get("work"):
        direction = str(origin.get("direction", ""))
        if direction not in _DIRECTION_LABELS:
            raise ValueError("Campo 'origin.direction' deve ser 'references' ou 'citations'")
        work_ref = sanitize_string(str(origin["work"]))
        lines.append(f"Artigo de origem: {work_ref} · direção: {_DIRECTION_LABELS[direction]}")

    lines.append(f"Lista: {list_id} · {status_label} · {total} artigos")

    for src in search_data.get("sources") or []:
        lines.append(_format_source_line(src))

    return "\n".join(lines)
