"""Tela Lista do app desktop (FR-16, FR-06, FR-08, FR-12, D-024, D-025)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from nicegui import ui

from rslapp import config
from rslapp.core.errors import RSLError
from rslapp.core.search import PAGE_SIZE
from rslapp.desktop.pages import render_header
from rslapp.desktop.pages.search import SOURCE_LABELS
from rslapp.desktop.service import DesktopService

EXPORT_FORMATS: tuple[tuple[str, str], ...] = (
    ("RIS", "ris"),
    ("CSV", "csv"),
    ("BibTeX", "bibtex"),
    ("JSON", "json"),
    ("DOIs", "dois"),
)


def _format_authors(raw_authors: Any) -> str:
    """Formata até os três primeiros autores e acrescenta 'et al.' quando houver mais."""
    if not isinstance(raw_authors, list):
        return ""
    names: list[str] = []
    for item in raw_authors:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
        elif isinstance(item, str):
            name = item.strip()
        else:
            name = ""
        if name:
            names.append(name)
    if not names:
        return ""
    if len(names) <= 3:
        return ", ".join(names)
    return f"{', '.join(names[:3])} et al."


def _format_doi(raw_doi: Any) -> tuple[str, str]:
    """Extrai o texto do DOI e a URL https://doi.org/... correspondente."""
    if not isinstance(raw_doi, str) or not raw_doi.strip():
        return "", ""
    clean = raw_doi.strip()
    lower = clean.lower()
    if lower.startswith("https://doi.org/"):
        short = clean[len("https://doi.org/") :]
        return short, f"https://doi.org/{short}"
    if lower.startswith("http://doi.org/"):
        short = clean[len("http://doi.org/") :]
        return short, f"https://doi.org/{short}"
    return clean, f"https://doi.org/{clean}"


def _format_work_sources(work: dict[str, Any]) -> str:
    """Formata as fontes em que o artigo apareceu como texto separado por vírgula."""
    source_ids = work.get("source_ids")
    if isinstance(source_ids, dict) and source_ids:
        return ", ".join(
            SOURCE_LABELS.get(str(k), str(k)) for k in source_ids
        )
    raw_sources = work.get("sources")
    if isinstance(raw_sources, list) and raw_sources:
        return ", ".join(
            SOURCE_LABELS.get(str(s), str(s)) for s in raw_sources
        )
    if isinstance(raw_sources, str) and raw_sources.strip():
        return raw_sources.strip()
    return ""


def _resolve_search_metadata(
    service: DesktopService,
    list_id: str,
    list_data: dict[str, Any],
) -> tuple[str, str, list[dict[str, Any]]]:
    """Obtém string de busca, data e resultados por fonte a partir da lista e do registro da busca."""
    search_record: dict[str, Any] = {}
    search_id = list_data.get("search_id")
    list_searches_fn = getattr(service, "list_searches", None)
    if callable(list_searches_fn):
        try:
            for item in list_searches_fn():
                if not isinstance(item, dict):
                    continue
                if (search_id and item.get("id") == search_id) or item.get(
                    "list_id"
                ) == list_id:
                    search_record = item
                    break
        except Exception:  # noqa: BLE001
            search_record = {}

    query_str = ""
    if isinstance(list_data.get("query"), str) and list_data["query"].strip():
        query_str = list_data["query"].strip()
    elif isinstance(list_data.get("params"), dict) and isinstance(
        list_data["params"].get("query"), str
    ):
        query_str = list_data["params"]["query"].strip()
    elif isinstance(search_record.get("query"), str) and search_record["query"].strip():
        query_str = search_record["query"].strip()
    elif isinstance(search_record.get("params"), dict) and isinstance(
        search_record["params"].get("query"), str
    ):
        query_str = search_record["params"]["query"].strip()
    elif (
        isinstance(search_record.get("request_summary"), str)
        and search_record["request_summary"].strip()
    ):
        query_str = search_record["request_summary"].strip()

    created_at = str(
        list_data.get("created_at") or search_record.get("created_at") or "—"
    )

    raw_sources = list_data.get("sources")
    if not isinstance(raw_sources, list):
        raw_sources = search_record.get("sources")

    sources_list: list[dict[str, Any]] = []
    if isinstance(raw_sources, list):
        for src in raw_sources:
            if isinstance(src, dict) and src.get("name"):
                sources_list.append(src)
    else:
        counts: dict[str, int] = {}
        for work in list_data.get("works") or []:
            if not isinstance(work, dict):
                continue
            sids = work.get("source_ids")
            if isinstance(sids, dict):
                for sname in sids:
                    counts[str(sname)] = counts.get(str(sname), 0) + 1
        for sname, cnt in counts.items():
            sources_list.append(
                {"name": sname, "status": "ok", "fetched": cnt, "found": cnt}
            )

    return query_str or "—", created_at, sources_list


# FR-16, FR-06: Abre pasta no gerenciador de arquivos do sistema sem usar shell=True
def open_folder_in_file_manager(folder: Path) -> None:
    """Abre a pasta no Explorer (Windows) ou via xdg-open (Linux) sem shell=True."""
    folder.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        os.startfile(str(folder))  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", str(folder)], check=False)


# FR-16, FR-06, FR-08, FR-12, D-024, D-025: Tela Lista (/lista/{list_id})
def build(service: DesktopService, list_id: str = "") -> None:
    """Monta a tela de visualização e exportação de uma lista salva."""
    render_header()

    with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-4"):
        ui.label("Lista").classes("text-h5 font-bold")

        try:
            list_data = service.get_list(list_id)
        except RSLError:
            ui.label(f"Lista {list_id}: lista não encontrada.").mark("list-not-found")
            ui.link("Voltar para Buscar", "/").mark("back-to-search")
            return

        raw_works = list_data.get("works")
        works: list[dict[str, Any]] = (
            [w for w in raw_works if isinstance(w, dict)]
            if isinstance(raw_works, list)
            else []
        )
        total = list_data.get("total", len(works))
        query_str, created_at, sources_list = _resolve_search_metadata(
            service, list_id, list_data
        )

        # FR-16, FR-05: Cabeçalho da lista com string, data, total e resultados por fonte
        with ui.card().classes("w-full p-4 gap-2"):
            ui.label(f"Identificador: {list_data.get('id', list_id)}").classes(
                "text-subtitle2 text-grey-7"
            )
            ui.label(f"String de busca: {query_str}").classes("font-medium")
            ui.label(f"Data: {created_at}")
            ui.label(f"Total de artigos: {total}").classes("font-bold")

            if sources_list:
                with ui.row().classes("gap-4 flex-wrap"):
                    for src in sources_list:
                        src_name = str(src.get("name", ""))
                        src_label = SOURCE_LABELS.get(src_name, src_name)
                        fetched = src.get("fetched")
                        if fetched is None:
                            fetched = src.get("count", src.get("found", 0))
                        ui.label(f"{src_label} ({src_name}): {fetched} resultados")

        # FR-08, FR-16: Aviso visível quando a lista for incompleta, indicando fonte e motivo
        failed_sources = [
            src
            for src in sources_list
            if str(src.get("status", "ok")) != "ok"
        ]
        if list_data.get("status") == "incomplete" or failed_sources:
            with ui.card().classes(
                "w-full bg-amber-50 border border-amber-400 p-3 gap-1"
            ).mark("incomplete-warning"):
                ui.label(
                    "Aviso: lista incompleta — uma ou mais fontes falharam."
                ).classes("font-bold text-amber-900")
                for src in failed_sources:
                    src_name = str(src.get("name", ""))
                    src_label = SOURCE_LABELS.get(src_name, src_name)
                    reason = (
                        src.get("reason")
                        or src.get("status")
                        or "falha na consulta"
                    )
                    ui.label(f"{src_label} ({src_name}): {reason}").classes(
                        "text-amber-900"
                    )

        # FR-06, FR-12, FR-16: Botões de exportação por formato e abertura da pasta
        last_export_dir: list[Path] = [config.load().export_dir]

        def _make_export_handler(fmt: str) -> Any:
            def _handle_export() -> None:
                try:
                    res = service.export(list_id, fmt)
                except RSLError as err:
                    ui.notify(err.message, type="negative")
                    return
                exported_path = str(res.get("path", ""))
                if exported_path:
                    last_export_dir[0] = Path(exported_path).parent
                ui.notify(exported_path, type="positive")

            return _handle_export

        def _handle_open_folder() -> None:
            try:
                open_folder_in_file_manager(last_export_dir[0])
            except OSError as err:
                ui.notify(f"Não foi possível abrir a pasta: {err}", type="negative")

        with ui.row().classes("items-center gap-2 flex-wrap"):
            for label, fmt in EXPORT_FORMATS:
                ui.button(label, on_click=_make_export_handler(fmt)).mark(
                    f"export-{fmt}"
                )
            ui.button("Abrir pasta", on_click=_handle_open_folder).props(
                "outline"
            ).mark("open-export-folder")

        # FR-16, FR-03: Tabela paginada (25 por página), com filtro por texto e ordenação por ano e título
        rows: list[dict[str, Any]] = []
        for idx, work in enumerate(works, start=1):
            doi_text, doi_url = _format_doi(work.get("doi"))
            rows.append(
                {
                    "id": idx,
                    "title": str(work.get("title") or ""),
                    "authors": _format_authors(work.get("authors")),
                    "year": work.get("year") if work.get("year") is not None else "",
                    "venue": str(work.get("venue") or ""),
                    "doi": doi_text,
                    "doi_url": doi_url,
                    "sources": _format_work_sources(work),
                }
            )

        columns: list[dict[str, Any]] = [
            {
                "name": "title",
                "label": "Título",
                "field": "title",
                "sortable": True,
                "align": "left",
            },
            {
                "name": "authors",
                "label": "Autores",
                "field": "authors",
                "sortable": False,
                "align": "left",
            },
            {
                "name": "year",
                "label": "Ano",
                "field": "year",
                "sortable": True,
                "align": "left",
            },
            {
                "name": "venue",
                "label": "Periódico",
                "field": "venue",
                "sortable": False,
                "align": "left",
            },
            {
                "name": "doi",
                "label": "DOI",
                "field": "doi",
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
        ]

        filter_input = (
            ui.input(
                label="Filtrar na tabela",
                placeholder="Buscar por título, autor, periódico ou DOI...",
            )
            .classes("w-full max-w-md")
            .mark("table-filter")
        )
        table = (
            ui.table(
                columns=columns,
                rows=rows,
                row_key="id",
                pagination=PAGE_SIZE,
            )
            .classes("w-full")
            .mark("works-table")
        )
        table.add_slot(
            "body-cell-doi",
            r"""
            <q-td :props="props">
                <a v-if="props.row.doi_url" :href="props.row.doi_url" target="_blank" class="text-primary underline">
                    {{ props.value }}
                </a>
                <span v-else>—</span>
            </q-td>
            """,
        )
        filter_input.bind_value(table, "filter")
