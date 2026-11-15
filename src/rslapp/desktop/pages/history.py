"""Tela Histórico do app desktop (FR-17, FR-11, FR-13, D-024, D-025)."""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from nicegui import events, ui

from rslapp.core.errors import RSLError
from rslapp.desktop.pages import render_header
from rslapp.desktop.pages.search import SOURCE_LABELS
from rslapp.desktop.service import DesktopService

MAX_QUERY_CHARS = 80


def _extract_search_query(search: dict[str, Any]) -> str:
    """Extrai a string de busca real a partir de params ou origin no formato do Store."""
    if search.get("kind") == "merge":
        merged = search.get("merged_from")
        if isinstance(merged, list) and merged:
            return ", ".join(str(x) for x in merged)
        return "—"
    params = search.get("params")
    if isinstance(params, dict):
        for key in ("query", "title", "doi", "work_id"):
            val = params.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    origin = search.get("origin")
    if isinstance(origin, dict):
        work = origin.get("work")
        if isinstance(work, str) and work.strip():
            return work.strip()
    return "—"


def _truncate_query(full_query: str) -> str:
    """Corta a string de busca em 80 caracteres para exibição na tabela."""
    if len(full_query) <= MAX_QUERY_CHARS:
        return full_query
    return f"{full_query[:MAX_QUERY_CHARS]}…"


def _format_search_sources(search: dict[str, Any]) -> str:
    """Formata os nomes legíveis das fontes consultadas na busca."""
    raw_sources = search.get("sources")
    names: list[str] = []
    if isinstance(raw_sources, list):
        for item in raw_sources:
            if isinstance(item, dict) and item.get("name"):
                src_name = str(item["name"])
                names.append(SOURCE_LABELS.get(src_name, src_name))
            elif isinstance(item, str) and item.strip():
                src_name = item.strip()
                names.append(SOURCE_LABELS.get(src_name, src_name))
    if not names:
        params = search.get("params")
        if isinstance(params, dict) and isinstance(params.get("sources"), list):
            for item in params["sources"]:
                if isinstance(item, str) and item.strip():
                    src_name = item.strip()
                    names.append(SOURCE_LABELS.get(src_name, src_name))
    return ", ".join(names) if names else "—"


def _resolve_list_summary(
    service: DesktopService,
    search: dict[str, Any],
) -> tuple[int, bool]:
    """Obtém o número de artigos e se a lista ficou incompleta a partir da lista salva e da busca."""
    list_id = search.get("list_id")
    list_data: dict[str, Any] | None = None
    if isinstance(list_id, str) and list_id.strip():
        with contextlib.suppress(RSLError):
            list_data = service.get_list(list_id.strip())

    raw_sources = search.get("sources")
    sources_failed = (
        any(
            isinstance(src, dict) and str(src.get("status", "ok")) != "ok"
            for src in raw_sources
        )
        if isinstance(raw_sources, list)
        else False
    )

    if list_data is not None:
        raw_works = list_data.get("works")
        fallback_total = len(raw_works) if isinstance(raw_works, list) else 0
        raw_total = list_data.get("total", fallback_total)
        total = (
            raw_total
            if isinstance(raw_total, int) and not isinstance(raw_total, bool)
            else fallback_total
        )
        is_incomplete = (
            list_data.get("status") == "incomplete"
            or bool(list_data.get("incomplete_from"))
            or sources_failed
        )
        return total, is_incomplete

    raw_search_total = search.get("total")
    if isinstance(raw_search_total, int) and not isinstance(raw_search_total, bool):
        total = raw_search_total
    elif isinstance(raw_sources, list):
        total = sum(
            int(src["fetched"])
            for src in raw_sources
            if isinstance(src, dict)
            and isinstance(src.get("fetched"), int)
            and not isinstance(src.get("fetched"), bool)
        )
    else:
        total = 0

    is_incomplete = (
        search.get("status") == "incomplete"
        or bool(search.get("incomplete_from"))
        or sources_failed
    )
    return total, is_incomplete


# FR-17, FR-13: Abre o arquivo log.md no programa padrão do sistema sem usar shell=True
def open_log_in_default_app(log_file: Path) -> None:
    """Abre o log.md no programa padrão (os.startfile no Windows, xdg-open no Linux) sem shell=True."""
    if sys.platform == "win32":
        os.startfile(str(log_file))  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", str(log_file)], check=False)


# FR-17, FR-11, FR-13, D-024, D-025: Tela Histórico (/historico)
def build(service: DesktopService) -> None:
    """Monta a tela de histórico de buscas e acesso ao log metodológico."""
    render_header()
    raw_searches = service.list_searches()
    ordered_searches = [
        s
        for _, s in sorted(
            enumerate(raw_searches),
            key=lambda pair: (str(pair[1].get("created_at") or ""), pair[0]),
            reverse=True,
        )
        if isinstance(s, dict)
    ]

    with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-4"):
        with ui.row().classes("w-full items-center justify-between"):
            with ui.column().classes("gap-1"):
                ui.label("Histórico").classes("text-h5 font-bold")
                ui.label(
                    "Consulte as buscas já feitas, repita uma busca ou abra o log."
                )

            def on_open_log() -> None:
                log_file = service.log_path()
                if not log_file.is_file():
                    ui.notify("O arquivo log.md ainda não existe.", type="warning")
                    return
                try:
                    open_log_in_default_app(log_file)
                except OSError as err:
                    ui.notify(f"Não foi possível abrir o log: {err}", type="negative")

            ui.button("Abrir log", on_click=on_open_log).props("outline").mark(
                "open-log"
            )

        if not ordered_searches:
            ui.label("Histórico vazio: nenhuma busca ainda.").mark("empty-history")
            ui.link("Ir para Buscar", "/").mark("go-to-search")
            return

        progress_row = ui.row().classes("items-center gap-2")
        with progress_row:
            ui.spinner(size="sm")
            ui.label("Repetindo a busca selecionada...")
        progress_row.set_visibility(False)

        rows: list[dict[str, Any]] = []
        for search in ordered_searches:
            search_id = str(search.get("id") or "")
            list_id = str(search.get("list_id") or "")
            created_at = str(search.get("created_at") or "—")
            full_query = _extract_search_query(search)
            short_query = _truncate_query(full_query)
            sources_str = _format_search_sources(search)
            total, is_incomplete = _resolve_list_summary(service, search)
            rows.append(
                {
                    "id": search_id,
                    "list_id": list_id,
                    "created_at": created_at,
                    "query": short_query,
                    "query_full": full_query,
                    "sources": sources_str,
                    "total": total,
                    "incomplete": "Sim" if is_incomplete else "Não",
                    "is_incomplete": is_incomplete,
                }
            )

        columns: list[dict[str, Any]] = [
            {
                "name": "created_at",
                "label": "Data",
                "field": "created_at",
                "sortable": True,
                "align": "left",
            },
            {
                "name": "query",
                "label": "String",
                "field": "query",
                "sortable": False,
                "align": "left",
            },
            {
                "name": "sources",
                "label": "Fontes",
                "field": "sources",
                "sortable": False,
                "align": "left",
            },
            {
                "name": "total",
                "label": "Artigos",
                "field": "total",
                "sortable": True,
                "align": "left",
            },
            {
                "name": "incomplete",
                "label": "Incompleta",
                "field": "incomplete",
                "sortable": False,
                "align": "left",
            },
            {
                "name": "actions",
                "label": "Ações",
                "field": "actions",
                "sortable": False,
                "align": "left",
            },
        ]

        table = (
            ui.table(
                columns=columns,
                rows=rows,
                row_key="id",
            )
            .classes("w-full")
            .mark("history-table")
        )
        table.add_slot(
            "body-cell-query",
            r"""
            <q-td :props="props">
                <span>
                    {{ props.value }}
                    <q-tooltip v-if="props.row.query_full">{{ props.row.query_full }}</q-tooltip>
                </span>
            </q-td>
            """,
        )

        def on_view_list(e: events.GenericEventArguments) -> None:
            arg = e.args
            target_list_id = (
                str(arg.get("list_id") or "")
                if isinstance(arg, dict)
                else str(arg or "")
            )
            if target_list_id:
                ui.navigate.to(f"/lista/{target_list_id}")

        # FR-17, FR-11: Repete a busca selecionada com indicador de progresso e navega para a lista nova
        async def on_repeat(e: events.GenericEventArguments) -> None:
            arg = e.args
            target_search_id = (
                str(arg.get("id") or "")
                if isinstance(arg, dict)
                else str(arg or "")
            )
            if not target_search_id:
                return
            repeat_btn.disable()
            progress_row.set_visibility(True)
            try:
                result = await service.repeat(target_search_id)
            except RSLError as err:
                ui.notify(err.message, type="negative")
                return
            finally:
                progress_row.set_visibility(False)
                repeat_btn.enable()

            new_list_id = str(result.get("list_id") or "")
            if new_list_id:
                ui.navigate.to(f"/lista/{new_list_id}")

        with table.add_slot("body-cell-actions"), table.cell("actions"):
            ui.button("Ver lista").props("flat dense").mark("view-list-button").on(
                "click",
                js_handler="() => emit(props.row.list_id)",
                handler=on_view_list,
            )
            repeat_btn = (
                ui.button("Repetir")
                .props("flat dense")
                .mark("repeat-button")
                .on(
                    "click",
                    js_handler="() => emit(props.row.id)",
                    handler=on_repeat,
                )
            )
