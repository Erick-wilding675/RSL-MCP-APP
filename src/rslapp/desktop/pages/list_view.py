"""Tela Lista do app desktop (FR-16, FR-06, FR-08, FR-12, D-024, D-025, D-031)."""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from nicegui import ui

from rslapp import config
from rslapp.core.errors import RSLError
from rslapp.core.search import PAGE_SIZE
from rslapp.desktop.components import (
    copy_block,
    empty_state,
    section_card,
    status_badge,
)
from rslapp.desktop.pages import render_shell
from rslapp.desktop.pages.search import SOURCE_LABELS
from rslapp.desktop.service import DesktopService
from rslapp.desktop.theme import apply_theme

EXPORT_FORMATS: tuple[tuple[str, str], ...] = (
    ("RIS", "ris"),
    ("CSV", "csv"),
    ("BibTeX", "bibtex"),
    ("ABNT", "abnt"),
    ("JSON", "json"),
    ("DOIs", "dois"),
)

EXPORT_ICONS: dict[str, str] = {
    "ris": "description",
    "csv": "table_view",
    "bibtex": "menu_book",
    "abnt": "format_quote",
    "json": "data_object",
    "dois": "link",
}


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
    list_data: dict[str, Any],
) -> tuple[str, str, list[dict[str, Any]]]:
    """Obtém string de busca, data e resultados por fonte a partir da lista e da busca gravadas pelo Store."""
    created_at = str(list_data.get("created_at") or "—")
    search_id = list_data.get("search_id")
    if not isinstance(search_id, str) or not search_id.strip():
        return "—", created_at, []

    try:
        search_record = service.get_search(search_id)
    except RSLError:
        return "—", created_at, []

    query_str = "—"
    if search_record.get("kind") != "merge":
        params = search_record.get("params")
        if isinstance(params, dict):
            raw_query = params.get("query")
            if isinstance(raw_query, str) and raw_query.strip():
                query_str = raw_query.strip()

    raw_sources = search_record.get("sources")
    sources_list: list[dict[str, Any]] = (
        [src for src in raw_sources if isinstance(src, dict) and src.get("name")]
        if isinstance(raw_sources, list)
        else []
    )
    return query_str, created_at, sources_list


# FR-16, FR-06: Abre pasta no gerenciador de arquivos do sistema sem usar shell=True
def open_folder_in_file_manager(folder: Path) -> None:
    """Abre a pasta no Explorer (Windows) ou via xdg-open (Linux) sem shell=True."""
    folder.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        os.startfile(str(folder))  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", str(folder)], check=False)


# FR-16, FR-06, FR-08, FR-12, D-024, D-025, D-031: Tela Lista (/lista/{list_id})
def build(service: DesktopService, list_id: str = "") -> None:
    """Monta a tela de visualização e exportação de uma lista salva."""
    apply_theme()
    render_shell(
        "Lista",
        "Visualize os artigos recuperados, consulte os metadados e exporte para ferramentas de revisão sistemática.",
    )

    with ui.column().classes("w-full gap-5"):
        try:
            list_data = service.get_list(list_id)
        except RSLError:
            with ui.column().classes("w-full items-center justify-center p-8 gap-3 text-center"):
                empty_state(
                    icon="search_off",
                    title="Lista não encontrada",
                    text=f"Lista {list_id}: lista não encontrada.",
                )
                ui.label(f"Lista {list_id}: lista não encontrada.").classes("hidden").mark("list-not-found")
                ui.link("Voltar para Buscar", "/").props("outline").classes("mt-2").mark("back-to-search")
            return

        raw_works = list_data.get("works")
        works: list[dict[str, Any]] = (
            [w for w in raw_works if isinstance(w, dict)]
            if isinstance(raw_works, list)
            else []
        )
        total = list_data.get("total", len(works))
        query_str, created_at, sources_list = _resolve_search_metadata(
            service, list_data
        )

        screening_summary = {
            "total_works": total,
            "screened": 0,
            "pending": total,
            "included": 0,
            "excluded": 0,
            "maybe": 0,
            "progress_percent": 0.0,
        }
        decisions_map: dict[str, Any] = {}
        if hasattr(service, "get_screening_summary"):
            with contextlib.suppress(RSLError, Exception):
                screening_summary = service.get_screening_summary(list_id)
        if hasattr(service, "get_screening"):
            with contextlib.suppress(RSLError, Exception):
                screening_data = service.get_screening(list_id)
                decisions_map = screening_data.get("decisions", {})

        notes_map: dict[str, Any] = {}
        if hasattr(service, "list_work_notes"):
            with contextlib.suppress(RSLError, Exception):
                notes_list = service.list_work_notes(list_id)
                notes_map = {str(n.get("work_id")): n for n in notes_list}

        # FR-32, D-043: Identifica se esta lista é fruto de uma atualização da Revisão Viva
        diff_added_ids: set[str] = set()
        if hasattr(service, "get_latest_differential"):
            with contextlib.suppress(Exception):
                diff_obj = service.get_latest_differential(list_id)
                if diff_obj and diff_obj.get("new_list_id") == list_id:
                    diff_added_ids = {str(aid) for aid in diff_obj.get("added_ids", [])}

        # 1. Aviso de lista incompleta no topo (FR-08, FR-16, D-031)
        failed_sources = [
            src
            for src in sources_list
            if str(src.get("status", "ok")) != "ok"
        ]
        if list_data.get("status") == "incomplete" or failed_sources:
            with ui.card().classes(
                "w-full p-4 gap-2 border-l-4 border-warning rsl-surface-2"
            ).mark("incomplete-warning"):
                with ui.row().classes("items-center gap-2 text-warning"):
                    ui.icon("warning").classes("text-xl")
                    ui.label(
                        "Aviso: lista incompleta — uma ou mais fontes falharam."
                    ).classes("font-bold")
                for src in failed_sources:
                    src_name = str(src.get("name", ""))
                    src_label = SOURCE_LABELS.get(src_name, src_name)
                    reason = (
                        src.get("reason")
                        or src.get("status")
                        or "falha na consulta"
                    )
                    with ui.row().classes("items-center gap-2 pl-7"):
                        status_badge(src_label, kind="warning")
                        ui.label(f"{src_label} ({src_name}): {reason}").classes(
                            "rsl-muted text-sm"
                        )

        # 2. Faixa de resumo no topo com números grandes em cartões pequenos (D-031, FR-16)
        with ui.row().classes("w-full gap-3 flex-wrap"):
            with ui.card().classes("p-4 flex-1 min-w-[140px] items-center text-center gap-1"):
                ui.label(str(total)).classes("text-2xl font-bold rsl-title")
                ui.label(f"Total de artigos: {total}").classes("text-xs rsl-muted")

            with ui.card().classes("p-4 flex-1 min-w-[140px] items-center text-center gap-1"):
                num_sources = len(sources_list) if sources_list else (
                    len(list_data.get("sources", []))
                    if isinstance(list_data.get("sources"), list)
                    else 1
                )
                ui.label(str(num_sources)).classes("text-2xl font-bold rsl-title")
                ui.label("Fontes consultadas").classes("text-xs rsl-muted")

            duplicates_count = None
            if isinstance(list_data.get("merge"), dict):
                merged_val = list_data["merge"].get("merged")
                if isinstance(merged_val, int) and not isinstance(merged_val, bool):
                    duplicates_count = merged_val
            elif isinstance(list_data.get("duplicates_removed"), int) and not isinstance(
                list_data.get("duplicates_removed"), bool
            ):
                duplicates_count = list_data.get("duplicates_removed")

            if duplicates_count is not None:
                with ui.card().classes("p-4 flex-1 min-w-[140px] items-center text-center gap-1"):
                    ui.label(str(duplicates_count)).classes("text-2xl font-bold rsl-title")
                    ui.label("Repetidos unificados").classes("text-xs rsl-muted")

            with ui.card().classes("p-4 flex-1 min-w-[140px] items-center text-center gap-1"):
                short_date = created_at
                with contextlib.suppress(ValueError, TypeError):
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    short_date = dt.strftime("%d/%m/%Y %H:%M")
                ui.label(short_date).classes("text-lg font-bold rsl-title")
                ui.label(f"Data: {created_at}").classes("text-xs rsl-muted")

            # FR-25, D-036: Cartão de métricas e acesso à triagem
            with (
                ui.card()
                .classes("p-4 flex-1 min-w-[140px] items-center text-center gap-1 cursor-pointer rsl-surface-2")
                .on("click", lambda: ui.navigate.to(f"/triagem/{list_id}"))
                .mark("card-screening")
            ):
                pct = screening_summary.get("progress_percent", 0.0)
                screened_cnt = screening_summary.get("screened", 0)
                ui.label(f"{pct}%").classes("text-2xl font-bold text-primary")
                ui.label(f"Triados ({screened_cnt}/{total})").classes("text-xs rsl-muted")

            # FR-22, D-032: Cartão de alerta de retratação caso a lista contenha artigos retratados
            retracted_count = sum(
                1 for w in works if isinstance(w, dict) and w.get("is_retracted")
            )
            if retracted_count > 0:
                with (
                    ui.card()
                    .classes("p-4 flex-1 min-w-[140px] items-center text-center gap-1")
                    .mark("card-retracted")
                ):
                    ui.label(str(retracted_count)).classes("text-2xl font-bold text-negative")
                    ui.label(
                        f"Artigo{'s' if retracted_count > 1 else ''} retratado{'s' if retracted_count > 1 else ''}"
                    ).classes("text-xs text-negative font-medium")

        # FR-25, FR-26, D-036, D-037: Barra de ações para Triagem Rápida e Fluxograma PRISMA 2020
        with ui.row().classes("w-full items-center justify-between gap-3 p-4 rounded-lg rsl-surface-2 border border-slate-200"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("fact_check").classes("text-2xl text-primary")
                with ui.column().classes("gap-0.5"):
                    ui.label("Seleção Metodológica e PRISMA 2020").classes("font-bold text-sm rsl-title")
                    ui.label("Triagem título/resumo com rastro, fluxograma vetorial e declaração ética de IA").classes("text-xs rsl-muted")
            with ui.row().classes("items-center gap-2"):
                ui.button(
                    "Iniciar Triagem",
                    icon="filter_alt",
                    on_click=lambda: ui.navigate.to(f"/triagem/{list_id}"),
                ).props("unelevated color=primary").mark("btn-open-screening")
                ui.button(
                    "PRISMA 2020",
                    icon="schema",
                    on_click=lambda: ui.navigate.to(f"/prisma/{list_id}"),
                ).props("outline color=primary").mark("btn-open-prisma")
                ui.button(
                    "Fichamento",
                    icon="edit_note",
                    on_click=lambda: ui.navigate.to(f"/ficha/{list_id}"),
                ).props("outline color=primary").mark("btn-open-notes")

                # FR-32, D-043: Botão e diálogo da Revisão Sistemática Viva
                def _handle_living_review() -> None:
                    with ui.dialog() as dialog, ui.card().classes("p-6 gap-4 max-w-lg w-full"):
                        ui.label("Revisão Sistemática Viva (LSR)").classes("text-lg font-bold rsl-title")
                        ui.label(
                            "Reexecuta a busca nas fontes mantendo intactas todas as decisões de triagem e fichamentos dos artigos já catalogados, identificando apenas os novos artigos indexados nas bases."
                        ).classes("text-sm rsl-muted")

                        status_label = ui.label("Pronto para verificar atualizações.").classes("text-xs font-mono rsl-muted")
                        spinner = ui.spinner(size="md").classes("self-center")
                        spinner.set_visibility(False)

                        async def _run_update() -> None:
                            spinner.set_visibility(True)
                            status_label.text = "Consultando fontes configuradas e comparando dados..."
                            try:
                                diff = service.update_search_differential(list_id)
                                added = diff.get("added_count", 0)
                                retained = diff.get("retained_count", 0)
                                new_lid = diff.get("new_list_id", "")
                                status_label.text = f"Sucesso! {retained} artigos preservados e {added} novos artigos identificados."
                                ui.notify(f"Revisão Viva: {added} novos artigos encontrados!", type="positive" if added > 0 else "info")
                                if new_lid:
                                    ui.button("Abrir Lista Atualizada", on_click=lambda: ui.navigate.to(f"/lista/{new_lid}")).props("unelevated color=primary mt-2")
                            except (RSLError, ValueError, OSError, RuntimeError) as e:
                                status_label.text = f"Erro na atualização: {e}"
                                ui.notify(f"Erro: {e}", type="negative")
                            finally:
                                spinner.set_visibility(False)

                        with ui.row().classes("w-full justify-end gap-2 mt-2"):
                            ui.button("Fechar", on_click=dialog.close).props("flat")
                            ui.button("Atualizar Busca Agora", icon="sync", on_click=_run_update).props("unelevated color=primary").mark("btn-confirm-living-review")
                    dialog.open()

                ui.button(
                    "Revisão Viva",
                    icon="sync",
                    on_click=_handle_living_review,
                ).props("outline color=primary").mark("btn-open-living-review")

        # 3. Cartão "Busca": string em monoespaçado com copy_block, ID e fontes (D-031, FR-16)
        with section_card("Busca", icon="search"):
            ui.label(f"Identificador: {list_data.get('id', list_id)}").classes(
                "text-xs rsl-muted"
            )
            ui.label(f"String de busca: {query_str}").classes(
                "text-xs font-semibold rsl-muted"
            )
            copy_block(query_str, mark="query-copy")

            if sources_list:
                ui.label("Resultados por fonte:").classes(
                    "text-xs font-medium rsl-muted mt-2"
                )
                with ui.column().classes("gap-2 w-full"):
                    for src in sources_list:
                        src_name = str(src.get("name", ""))
                        src_label = SOURCE_LABELS.get(src_name, src_name)
                        fetched = src.get("fetched") or 0
                        status = str(src.get("status", "ok"))
                        with ui.row().classes("items-center gap-2"):
                            if status == "ok":
                                status_badge(f"{fetched} resultados", kind="ok")
                                ui.label(
                                    f"{src_label} ({src_name}): {fetched} resultados"
                                ).classes("text-sm rsl-title")
                            else:
                                reason = (
                                    src.get("reason") or status or "falha na consulta"
                                )
                                status_badge("incompleta", kind="warning")
                                ui.label(
                                    f"{src_label} ({src_name}): {reason}"
                                ).classes("text-sm text-warning")

        # 4. Cartão "Exportar": botões com ícones lado a lado e abrir pasta (FR-06, FR-12, FR-16, D-031)
        with section_card(
            "Exportar",
            icon="file_download",
            description="Exporte a lista nos formatos compatíveis com ferramentas de revisão sistemática",
        ):
            last_export_dir: list[Path] = [config.load().export_dir]

            export_feedback_row = ui.row().classes(
                "w-full items-center gap-2 p-3 rounded rsl-surface-2"
            )
            export_feedback_row.set_visibility(False)
            with export_feedback_row:
                ui.icon("check_circle").classes("text-positive text-xl")
                export_feedback_label = ui.label("").classes(
                    "text-xs font-mono break-all flex-1"
                )
                ui.button(
                    "Abrir pasta", on_click=lambda: _handle_open_folder()
                ).props("outline size=sm")

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
                        export_feedback_label.text = exported_path
                        export_feedback_row.set_visibility(True)
                    ui.notify(exported_path, type="positive")

                return _handle_export

            def _handle_open_folder() -> None:
                try:
                    open_folder_in_file_manager(last_export_dir[0])
                except OSError as err:
                    ui.notify(f"Não foi possível abrir a pasta: {err}", type="negative")

            def _handle_reproducibility() -> None:
                try:
                    res = service.export_reproducibility_package(list_id)
                except (RSLError, AttributeError) as err:
                    msg = getattr(err, "message", str(err))
                    ui.notify(msg, type="negative")
                    return
                exported_path = str(res.get("path", ""))
                if exported_path:
                    last_export_dir[0] = Path(exported_path).parent
                    export_feedback_label.text = exported_path
                    export_feedback_row.set_visibility(True)
                ui.notify(f"Pacote de reprodutibilidade gerado: {res.get('filename')}", type="positive")

            def _handle_notes_export() -> None:
                try:
                    res_path = service.export_notes_markdown(list_id)
                except (RSLError, AttributeError) as err:
                    msg = getattr(err, "message", str(err))
                    ui.notify(msg, type="negative")
                    return
                last_export_dir[0] = res_path.parent
                export_feedback_label.text = str(res_path)
                export_feedback_row.set_visibility(True)
                ui.notify(f"Fichamento exportado: {res_path.name}", type="positive")

            def _handle_vosviewer_export() -> None:
                try:
                    res = service.export_network(list_id, fmt="vosviewer")
                except (RSLError, AttributeError) as err:
                    msg = getattr(err, "message", str(err))
                    ui.notify(msg, type="negative")
                    return
                last_export_dir[0] = res["map_path"].parent
                export_feedback_label.text = f"{res['map_file']} / {res['network_file']}"
                export_feedback_row.set_visibility(True)
                ui.notify(
                    f"Rede VOSviewer exportada ({res['total_nodes']} autores, {res['total_edges']} colaborações).",
                    type="positive",
                )

            def _handle_gephi_export() -> None:
                try:
                    res = service.export_network(list_id, fmt="gephi")
                except (RSLError, AttributeError) as err:
                    msg = getattr(err, "message", str(err))
                    ui.notify(msg, type="negative")
                    return
                last_export_dir[0] = res["gexf_path"].parent
                export_feedback_label.text = str(res["gexf_path"])
                export_feedback_row.set_visibility(True)
                ui.notify(
                    f"Rede Gephi exportada: {res['gexf_file']} ({res['total_nodes']} nós, {res['total_edges']} arestas).",
                    type="positive",
                )

            with ui.row().classes("items-center gap-3 flex-wrap"):
                for label, fmt in EXPORT_FORMATS:
                    ui.button(
                        label,
                        icon=EXPORT_ICONS.get(fmt, "download"),
                        on_click=_make_export_handler(fmt),
                    ).props("unelevated").classes("rsl-surface-2 font-medium").mark(
                        f"export-{fmt}"
                    )
                ui.button(
                    "Fichas (.md)",
                    icon="note_alt",
                    on_click=_handle_notes_export,
                ).props("unelevated").classes("rsl-surface-2 font-medium").mark(
                    "export-notes-md"
                )
                ui.button(
                    "VOSviewer (.map/.net)",
                    icon="hub",
                    on_click=_handle_vosviewer_export,
                ).props("unelevated").classes("rsl-surface-2 font-medium").mark(
                    "export-vosviewer-network"
                )
                ui.button(
                    "Gephi (.gexf)",
                    icon="grain",
                    on_click=_handle_gephi_export,
                ).props("unelevated").classes("rsl-surface-2 font-medium").mark(
                    "export-gephi-network"
                )
                ui.button(
                    "Pacote de Reprodutibilidade (.zip)",
                    icon="archive",
                    on_click=_handle_reproducibility,
                ).props("unelevated color=primary").classes("font-medium").mark(
                    "export-reproducibility"
                )
                ui.button(
                    "Abrir pasta",
                    icon="folder_open",
                    on_click=_handle_open_folder,
                ).props("outline").mark("open-export-folder")

        # 5. Cartão Tabela de artigos: cabeçalho fixo, linhas alternadas, título em negrito e autores em cinza, DOI link e filtro com lupa (D-031, FR-16, FR-03)
        rows: list[dict[str, Any]] = []
        for idx, work in enumerate(works, start=1):
            doi_text, doi_url = _format_doi(work.get("doi"))
            work_key = str(work.get("doi") or idx)
            dec_obj = decisions_map.get(work_key) or decisions_map.get(str(idx)) or {}
            raw_work_id = str(work.get("id") or idx)
            note_obj = notes_map.get(raw_work_id) or notes_map.get(str(idx)) or {}
            rows.append(
                {
                    "id": idx,
                    "raw_work_id": raw_work_id,
                    "title": str(work.get("title") or ""),
                    "authors": _format_authors(work.get("authors")),
                    "year": work.get("year") if work.get("year") is not None else "",
                    "venue": str(work.get("venue") or ""),
                    "doi": doi_text,
                    "doi_url": doi_url,
                    "sources": _format_work_sources(work),
                    "is_retracted": bool(work.get("is_retracted", False)),
                    "type": str(work.get("type") or ""),
                    "screening_decision": dec_obj.get("decision", ""),
                    "has_note": bool(note_obj),
                    "note_source": str(note_obj.get("source") or ""),
                    "is_new_in_search": raw_work_id in diff_added_ids or str(work.get("id")) in diff_added_ids,
                }
            )

        columns: list[dict[str, Any]] = [
            {
                "name": "title",
                "label": "Título e autores",
                "field": "title",
                "sortable": True,
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
            {
                "name": "ficha",
                "label": "Ficha",
                "field": "raw_work_id",
                "sortable": False,
                "align": "center",
            },
        ]

        with section_card("Artigos da lista", icon="article"):
            with ui.row().classes("w-full items-center justify-between gap-4 mb-2"):
                filter_input = (
                    ui.input(
                        placeholder="Filtrar por título, autor ou DOI",
                    )
                    .props("dense outlined clearable")
                    .classes("w-full max-w-md")
                    .mark("table-filter")
                )
                with filter_input.add_slot("prepend"):
                    ui.icon("search").classes("text-grey-6")

                ui.label(f"{len(works)} artigos").classes("text-xs rsl-muted")

            table = (
                ui.table(
                    columns=columns,
                    rows=rows,
                    row_key="id",
                    pagination=PAGE_SIZE,
                )
                .classes("w-full rsl-table sticky-header-table")
                .props("flat")
                .mark("works-table")
            )
            filter_input.bind_value(table, "filter")

            table.add_slot(
                "body-cell-title",
                r"""
                <q-td :props="props">
                    <div class="flex items-center gap-2 flex-wrap">
                        <span class="font-bold rsl-title leading-snug">{{ props.row.title }}</span>
                        <q-badge v-if="props.row.is_new_in_search" color="positive" class="text-xs px-2 py-0.5 rounded-full font-bold">
                            NOVO NA BUSCA
                            <q-tooltip>Artigo inédito indexado após a busca original (Revisão Viva)</q-tooltip>
                        </q-badge>
                        <q-badge v-if="props.row.is_retracted" color="negative" class="text-xs px-2 py-0.5 rounded-full font-bold">
                            RETRATADO
                            <q-tooltip>Artigo formalmente retratado ou com expressão de preocupação oficial</q-tooltip>
                        </q-badge>
                        <q-badge v-if="props.row.type === 'thesis'" color="teal-8" class="text-xs px-2 py-0.5 rounded font-bold">
                            TESE
                            <q-tooltip>Tese de Doutorado defendida no Brasil (BDTD)</q-tooltip>
                        </q-badge>
                        <q-badge v-if="props.row.type === 'dissertation'" color="blue-grey-8" class="text-xs px-2 py-0.5 rounded font-bold">
                            DISSERTAÇÃO
                            <q-tooltip>Dissertação de Mestrado defendida no Brasil (BDTD)</q-tooltip>
                        </q-badge>
                        <q-badge v-if="props.row.screening_decision === 'included'" color="positive" class="text-xs px-2 py-0.5 rounded-full font-bold">
                            INCLUÍDO
                            <q-tooltip>Artigo incluído na triagem</q-tooltip>
                        </q-badge>
                        <q-badge v-if="props.row.screening_decision === 'excluded'" color="negative" class="text-xs px-2 py-0.5 rounded-full font-bold">
                            EXCLUÍDO
                            <q-tooltip>Artigo excluído na triagem</q-tooltip>
                        </q-badge>
                        <q-badge v-if="props.row.screening_decision === 'maybe'" color="warning" class="text-xs px-2 py-0.5 rounded-full font-bold">
                            DÚVIDA
                            <q-tooltip>Artigo em dúvida na triagem</q-tooltip>
                        </q-badge>
                        <q-badge v-if="props.row.has_note && props.row.note_source === 'human_reviewed'" color="positive" class="text-xs px-2 py-0.5 rounded-full font-bold">
                            FICHA OK
                            <q-tooltip>Ficha científica revisada por humano</q-tooltip>
                        </q-badge>
                        <q-badge v-else-if="props.row.has_note && props.row.note_source === 'ai_suggested'" color="warning" class="text-xs px-2 py-0.5 rounded-full font-bold">
                            FICHA IA
                            <q-tooltip>Ficha científica sugerida por IA</q-tooltip>
                        </q-badge>
                        <q-badge v-else-if="props.row.has_note" color="primary" class="text-xs px-2 py-0.5 rounded-full font-bold">
                            FICHA
                            <q-tooltip>Ficha científica preenchida</q-tooltip>
                        </q-badge>
                    </div>
                    <div v-if="props.row.authors" class="text-xs rsl-muted mt-0.5">{{ props.row.authors }}</div>
                </q-td>
                """,
            )

            table.add_slot(
                "body-cell-doi",
                r"""
                <q-td :props="props">
                    <a v-if="props.row.doi_url" :href="props.row.doi_url" target="_blank" class="text-primary underline font-mono text-xs">
                        {{ props.value }}
                    </a>
                    <span v-else class="rsl-muted">—</span>
                </q-td>
                """,
            )

            table.add_slot(
                "body-cell-sources",
                r"""
                <q-td :props="props">
                    <span v-if="props.value" class="text-xs px-2 py-0.5 rounded-full font-medium rsl-surface-2 rsl-muted">
                        {{ props.value }}
                    </span>
                    <span v-else class="rsl-muted">—</span>
                </q-td>
                """,
            )

            table.add_slot(
                "body-cell-ficha",
                r"""
                <q-td :props="props">
                    <q-btn dense flat round color="primary" icon="edit_note" @click="() => $parent.$emit('open_work_note', props.row.raw_work_id)">
                        <q-tooltip>Abrir ficha científica</q-tooltip>
                    </q-btn>
                </q-td>
                """,
            )
            table.on(
                "open_work_note",
                lambda e: ui.navigate.to(
                    f"/ficha/{list_id}/{quote(str(e.args), safe='')}"
                ),
            )
