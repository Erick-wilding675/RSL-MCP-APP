"""Formatação e validação de entradas do log legível (log.md)."""

from __future__ import annotations

from typing import Any

from rslapp.store._atomic import strip_url_credentials
from rslapp.store.cache import parse_utc_timestamp

_KIND_LABELS = {
    "terms": "busca por termos",
    "work": "busca de artigo",
    "repeat": "repetição",
    "merge": "junção",
}
_DIRECTION_LABELS = {"references": "referências", "citations": "citações"}
_LIST_STATUS_LABELS = {"complete": "completa", "incomplete": "incompleta"}
_DIVERGENCE_LABELS = {
    "year": "ano",
    "title": "título",
    "doi": "doi",
    "venue": "veículo",
}


def _one_line(text: str) -> str:
    return text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


# FR-04, FR-13: Formatação da linha de junção e divergências no log.md
def _format_merge_line(merge: Any) -> str:
    if type(merge) is not dict:
        raise ValueError("Campo 'merge' deve ser um dicionário")
    merged = merge.get("merged", 0)
    if type(merged) is not int or merged < 0:
        raise ValueError(f"Total de 'merged' inválido: {merged!r}")
    unit = "artigo" if merged == 1 else "artigos"

    raw_divs = merge.get("divergences")
    if raw_divs is None:
        raw_divs = {}
    elif type(raw_divs) is not dict:
        raise ValueError("Campo 'divergences' deve ser um dicionário")

    ordered_keys = [k for k in ("year", "title", "doi", "venue") if k in raw_divs]
    extra_keys = [k for k in raw_divs if k not in ordered_keys]

    div_parts: list[str] = []
    for k in ordered_keys + extra_keys:
        cnt = raw_divs[k]
        if type(cnt) is int and cnt > 0:
            label = _DIVERGENCE_LABELS.get(k, str(k))
            div_parts.append(f"{label} {cnt}")

    if div_parts:
        div_str = f"divergências: {', '.join(div_parts)}"
    else:
        div_str = "sem divergências"

    return f"Junção: {merged} {unit} em mais de uma fonte · {div_str}"


def _format_source_line(src: Any) -> str:
    if type(src) is not dict or not src.get("name") or not src.get("status"):
        raise ValueError("Fonte inválida: 'name' e 'status' são obrigatórios")
    name, status = _one_line(str(src["name"])), _one_line(str(src["status"]))
    query = _one_line(strip_url_credentials(str(src.get("query") or "")))
    found, fetched, reason = src.get("found"), src.get("fetched"), src.get("reason")
    from_cache, fetched_at = bool(src.get("from_cache", False)), src.get("fetched_at")
    exc_pr = src.get("excluded_peer_review")

    parts: list[str] = [name, status]
    # FR-13, FR-15: Quando a fonte não informa o total (found is None), exibe "total não informado"
    if status == "ok" or (found is not None and fetched is not None):
        if found is None:
            parts.append(f"total não informado, trazidos {fetched or 0}")
        else:
            parts.append(f"encontrados {found}, trazidos {fetched or 0}")
    # D-022: Mostra quantos pareceres saíram por fonte quando houver
    if type(exc_pr) is int and exc_pr > 0:
        pr_unit = "parecer de revisão excluído" if exc_pr == 1 else "pareceres de revisão excluídos"
        parts.append(f"{exc_pr} {pr_unit}")
    if reason:
        parts.append(_one_line(strip_url_credentials(str(reason))))
    if from_cache:
        date_str = parse_utc_timestamp(str(fetched_at)).strftime("%Y-%m-%d") if fetched_at else ""
        parts.append(f"cache: sim, obtida em {date_str}" if date_str else "cache: sim")
    elif status == "ok":
        parts.append("cache: não")
    parts.append(f"string: `{query}`")
    return "- " + " · ".join(parts)


# FR-04, FR-05, FR-13, NFR-03, NFR-06, D-007, D-022: Geração determinística de uma entrada de log.md em português
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

    if kind != "merge":
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

    # D-022: Indica se pareceres de revisão foram excluídos ou incluídos quando include_peer_review estiver nos parâmetros
    params = search_data.get("params")
    if isinstance(params, dict) and "include_peer_review" in params:
        pr_label = (
            "pareceres de revisão incluídos"
            if params["include_peer_review"]
            else "pareceres de revisão excluídos"
        )
        list_line = f"{list_line} · {pr_label}"

    # D-021, FR-05, FR-13: Formatação específica para entradas de junção de listas no log.md
    if kind == "merge":
        merged_from = search_data.get("merged_from") or []
        origin_totals = search_data.get("origin_totals") or {}
        dups = search_data.get("duplicates_removed", 0)
        if type(dups) is not int or dups < 0:
            raise ValueError(f"Total de duplicates_removed inválido: {dups!r}")
        dup_unit = "artigo" if dups == 1 else "artigos"

        lines = [
            f"## {search_data['id']} · {created_str} · {kind_label}",
            f"Pedido: {summary}" if summary else "Pedido:",
            list_line,
            f"Duplicatas removidas: {dups} {dup_unit}",
        ]
        for lid in merged_from:
            cnt = origin_totals.get(lid)
            if cnt is not None and type(cnt) is int:
                c_unit = "artigo" if cnt == 1 else "artigos"
                lines.append(f"- {lid} · {cnt} {c_unit}")
            else:
                lines.append(f"- {lid}")
        return "\n".join(lines)

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
    if search_data.get("merge") is not None:
        lines.append(_format_merge_line(search_data["merge"]))
    lines.extend(_format_source_line(src) for src in sources)
    return "\n".join(lines)
