"""Página de fichamento científico estruturado com rastro de autoria (FR-29, D-040)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from nicegui import ui

from rslapp.core.abnt import format_abnt_reference
from rslapp.core.errors import RSLError
from rslapp.core.notes import format_note_markdown
from rslapp.desktop.components import section_card
from rslapp.desktop.pages import render_shell
from rslapp.desktop.service import DesktopService
from rslapp.desktop.theme import apply_theme


def _find_work(works: list[dict[str, Any]], work_id: str) -> dict[str, Any] | None:
    clean = str(work_id).strip()
    for w in works:
        if str(w.get("id")) == clean:
            return w
    return None


# FR-29, D-040: Tela de visão geral de todas as fichas de uma lista
def build_list(service: DesktopService, list_id: str) -> None:
    """Monta a página de índice e gerenciamento de fichas científicas da lista."""
    apply_theme()
    render_shell(
        "Fichamento",
        "Fichamento científico estruturado com rastro de autoria e exportação para Obsidian.",
        active="Buscar",
    )
    with ui.column().classes("w-full gap-4 max-w-5xl mx-auto"):
        try:
            list_data = service.get_list(list_id)
        except RSLError as err:
            ui.label(f"Erro ao carregar lista: {err.message}").classes("text-negative font-bold")
            return

        works = list_data.get("works", [])
        notes = service.list_work_notes(list_id)
        notes_by_work_id = {str(n.get("work_id")): n for n in notes}

        with ui.row().classes("w-full items-center justify-between mb-4"):
            with ui.row().classes("items-center gap-2"):
                ui.button(
                    "Voltar à Lista",
                    icon="arrow_back",
                    on_click=lambda: ui.navigate.to(f"/lista/{list_id}"),
                ).props("flat color=primary")
                ui.label(f"Fichamento Científico · Lista {list_id}").classes("text-xl font-bold rsl-title")

            ui.button(
                "Exportar Todas (.md)",
                icon="download",
                on_click=lambda: _handle_export_all(service, list_id),
            ).props("unelevated color=primary").mark("btn-export-all-notes")

        # Cartões de Resumo
        ai_count = sum(1 for n in notes if n.get("source") == "ai_suggested")
        human_count = sum(1 for n in notes if n.get("source") in ("human_reviewed", "human_created"))
        unnoted_count = len(works) - len(notes)

        with ui.row().classes("w-full gap-4 mb-4"):
            with ui.card().classes("p-4 flex-1 items-center text-center rsl-surface-2"):
                ui.label(str(len(works))).classes("text-2xl font-bold rsl-title")
                ui.label("Total de Artigos").classes("text-xs rsl-muted")
            with ui.card().classes("p-4 flex-1 items-center text-center rsl-surface-2"):
                ui.label(str(len(notes))).classes("text-2xl font-bold text-primary")
                ui.label("Artigos Fichados").classes("text-xs rsl-muted")
            with ui.card().classes("p-4 flex-1 items-center text-center rsl-surface-2"):
                ui.label(str(human_count)).classes("text-2xl font-bold text-positive")
                ui.label("Revisados por Humano").classes("text-xs rsl-muted")
            with ui.card().classes("p-4 flex-1 items-center text-center rsl-surface-2"):
                ui.label(str(ai_count)).classes("text-2xl font-bold text-warning")
                ui.label("Sugestões de IA").classes("text-xs rsl-muted")
            with ui.card().classes("p-4 flex-1 items-center text-center rsl-surface-2"):
                ui.label(str(unnoted_count)).classes("text-2xl font-bold text-slate-400")
                ui.label("Fichas Pendentes").classes("text-xs rsl-muted")

        # Tabela com busca
        filter_input = ui.input(placeholder="Filtrar artigos por título ou autor...").props("dense outlined clearable").classes("w-full max-w-md mb-2")

        table_rows = []
        for w in works:
            w_id = str(w.get("id"))
            note = notes_by_work_id.get(w_id)
            source_label = "Sem ficha"
            if note:
                src = note.get("source")
                source_label = "Revisado por humano" if src == "human_reviewed" else "Sugerido por IA" if src == "ai_suggested" else "Elaborado por humano"

            authors_raw = w.get("authors", [])
            authors_str = ", ".join(a.get("name") for a in authors_raw if isinstance(a, dict) and a.get("name")) if isinstance(authors_raw, list) else ""

            table_rows.append({
                "id": w_id,
                "title": w.get("title", ""),
                "authors": authors_str,
                "year": w.get("year", ""),
                "status": source_label,
                "has_note": note is not None,
                "source": note.get("source") if note else None,
            })

        cols = [
            {"name": "id", "label": "ID", "field": "id", "sortable": True},
            {"name": "title", "label": "Título", "field": "title", "align": "left", "sortable": True},
            {"name": "authors", "label": "Autores", "field": "authors", "align": "left"},
            {"name": "year", "label": "Ano", "field": "year", "sortable": True},
            {"name": "status", "label": "Situação da Ficha", "field": "status", "align": "center", "sortable": True},
            {"name": "action", "label": "Ação", "field": "id", "align": "center"},
        ]

        table = ui.table(columns=cols, rows=table_rows, row_key="id").classes("w-full rsl-table").props("flat")
        filter_input.bind_value(table, "filter")

        table.add_slot(
            "body-cell-status",
            r"""
            <q-td :props="props">
                <q-badge v-if="props.row.source === 'human_reviewed'" color="positive" class="text-xs px-2 py-0.5 rounded font-bold">
                    REVISADO
                </q-badge>
                <q-badge v-else-if="props.row.source === 'ai_suggested'" color="warning" class="text-xs px-2 py-0.5 rounded font-bold">
                    SUGESTÃO IA
                </q-badge>
                <q-badge v-else-if="props.row.has_note" color="primary" class="text-xs px-2 py-0.5 rounded font-bold">
                    FICHADO
                </q-badge>
                <span v-else class="text-xs text-slate-400">Pendente</span>
            </q-td>
            """,
        )

        table.add_slot(
            "body-cell-action",
            r"""
            <q-td :props="props">
                <q-btn dense flat round color="primary" icon="edit_note" @click="() => $parent.$emit('open_note', props.row.id)">
                    <q-tooltip>Abrir ficha científica</q-tooltip>
                </q-btn>
            </q-td>
            """,
        )

        table.on("open_note", lambda e: ui.navigate.to(f"/ficha/{list_id}/{quote(str(e.args), safe='')}"))


def _handle_export_all(service: DesktopService, list_id: str) -> None:
    try:
        path = service.export_notes_markdown(list_id)
        ui.notify(f"Fichas exportadas com sucesso: {path.name}", type="positive")
    except (RSLError, OSError, ValueError) as err:
        ui.notify(f"Erro ao exportar fichas: {err}", type="negative")


# FR-29, D-040: Tela de preenchimento e revisão de uma ficha científica individual
def build(service: DesktopService, list_id: str, work_id: str) -> None:
    """Monta o formulário de visualização, edição e validação de uma ficha científica."""
    apply_theme()
    render_shell(
        f"Ficha {work_id}",
        "Preenchimento e validação da ficha científica analítica com rastro de auditoria.",
        active="Buscar",
    )
    with ui.column().classes("w-full gap-4 max-w-5xl mx-auto"):
        try:
            list_data = service.get_list(list_id)
        except RSLError as err:
            ui.label(f"Erro ao carregar lista: {err.message}").classes("text-negative font-bold")
            return

        works = list_data.get("works", [])
        work = _find_work(works, work_id)
        if not work:
            ui.label(f"Artigo '{work_id}' não encontrado nesta lista.").classes("text-negative font-bold")
            ui.button("Voltar", on_click=lambda: ui.navigate.to(f"/lista/{list_id}")).props("flat")
            return

        existing_note = service.get_work_note(list_id, work_id) or {}

        # Determina próximo e anterior para fluxo contínuo de leitura
        work_ids = [str(w.get("id")) for w in works]
        curr_idx = work_ids.index(str(work_id)) if str(work_id) in work_ids else 0
        prev_id = work_ids[curr_idx - 1] if curr_idx > 0 else None
        next_id = work_ids[curr_idx + 1] if curr_idx < len(work_ids) - 1 else None

        # Navegação de topo
        with ui.row().classes("w-full items-center justify-between mb-4"):
            with ui.row().classes("items-center gap-2"):
                ui.button(
                    "Voltar",
                    icon="arrow_back",
                    on_click=lambda: ui.navigate.to(f"/lista/{list_id}"),
                ).props("flat color=primary")
                ui.button(
                    "Todas as Fichas",
                    icon="format_list_bulleted",
                    on_click=lambda: ui.navigate.to(f"/ficha/{list_id}"),
                ).props("flat color=primary")

            with ui.row().classes("items-center gap-2"):
                if prev_id:
                    ui.button("Anterior", icon="chevron_left", on_click=lambda: ui.navigate.to(f"/ficha/{list_id}/{quote(str(prev_id), safe='')}")).props("outline size=sm")
                ui.label(f"{curr_idx + 1} de {len(works)}").classes("text-xs font-mono rsl-muted")
                if next_id:
                    ui.button("Próximo", icon="chevron_right", on_click=lambda: ui.navigate.to(f"/ficha/{list_id}/{quote(str(next_id), safe='')}")).props("outline size=sm")

        # Cabeçalho do Artigo
        title_text = work.get("title") or f"Artigo {work_id}"
        authors_raw = work.get("authors", [])
        authors_text = ", ".join(a.get("name") for a in authors_raw if isinstance(a, dict) and a.get("name")) if isinstance(authors_raw, list) else ""
        year_text = str(work.get("year") or "")
        doi_text = str(work.get("doi") or "")
        abnt_ref = format_abnt_reference(work)

        with section_card("Metadados da Obra", icon="menu_book"):
            ui.label(title_text).classes("text-lg font-bold rsl-title leading-snug")
            if authors_text:
                ui.label(f"{authors_text} ({year_text})").classes("text-xs rsl-muted font-medium")
            if doi_text:
                ui.link(f"DOI: {doi_text}", f"https://doi.org/{doi_text.replace('https://doi.org/', '')}", new_tab=True).classes("text-xs text-primary underline font-mono")
            with ui.row().classes("w-full p-2 rounded rsl-surface-2 border border-slate-200 mt-2 items-center justify-between"):
                ui.label(abnt_ref).classes("text-xs font-mono rsl-title flex-1")
                ui.button(icon="content_copy", on_click=lambda: _copy_text(abnt_ref)).props("flat dense round size=sm").tooltip("Copiar ABNT")

        # Rastro de Autoria e Situação
        curr_source = existing_note.get("source", "human_created")
        curr_ai_model = existing_note.get("ai_model", "")
        curr_reviewed_by = existing_note.get("reviewed_by", "")

        status_card = ui.card().classes("w-full p-4 mb-4 rsl-surface-2 border border-slate-200 rounded-lg")
        with status_card:
            with ui.row().classes("w-full items-center justify-between"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("verified_user").classes("text-xl text-primary")
                    ui.label("Rastro Metodológico de Autoria (D-040)").classes("font-bold text-sm rsl-title")

                with ui.row().classes("items-center gap-2"):
                    source_select = ui.select(
                        options={
                            "human_created": "👤 Elaborado por Humano",
                            "ai_suggested": "🤖 Sugerido por IA",
                            "human_reviewed": "✅ Revisado e Validado por Humano",
                        },
                        value=curr_source,
                    ).props("dense outlined").classes("w-64")

            with ui.row().classes("w-full gap-4 mt-2"):
                ai_model_input = ui.input(label="Modelo de IA (se aplicável)", value=curr_ai_model).props("dense outlined").classes("flex-1")
                reviewer_input = ui.input(label="Pesquisador / Revisor", value=curr_reviewed_by).props("dense outlined").classes("flex-1")

        # Campos Analíticos da Ficha
        with section_card("Campos Analíticos do Fichamento", icon="edit_note"):
            obj_input = ui.textarea(
                label="1. Objetivo da Pesquisa",
                value=existing_note.get("objective", ""),
            ).props("outlined autogrow").classes("w-full mb-3")

            method_input = ui.textarea(
                label="2. Metodologia e Desenho do Estudo",
                value=existing_note.get("methodology", ""),
            ).props("outlined autogrow").classes("w-full mb-3")

            sample_input = ui.textarea(
                label="3. Amostra, Participantes e Contexto Empírico",
                value=existing_note.get("sample", ""),
            ).props("outlined autogrow").classes("w-full mb-3")

            results_input = ui.textarea(
                label="4. Principais Resultados e Achados",
                value=existing_note.get("results", ""),
            ).props("outlined autogrow").classes("w-full mb-3")

            limitations_input = ui.textarea(
                label="5. Limitações Declaradas pelos Autores",
                value=existing_note.get("limitations", ""),
            ).props("outlined autogrow").classes("w-full mb-3")

            # Citações diretas com página
            existing_quotes = existing_note.get("direct_quotes", [])
            quotes_text = ""
            if existing_quotes:
                lines = []
                for q in existing_quotes:
                    page = f" [p. {q['page']}]" if q.get("page") else ""
                    lines.append(f"{q.get('quote', '')}{page}")
                quotes_text = "\n".join(lines)

            quotes_input = ui.textarea(
                label="6. Citações Diretas (uma por linha, com indicação de [p. X] se houver)",
                value=quotes_text,
            ).props("outlined autogrow").classes("w-full mb-3")

            synthesis_input = ui.textarea(
                label="7. Síntese Crítica e Reflexões do Pesquisador",
                value=existing_note.get("synthesis", ""),
            ).props("outlined autogrow").classes("w-full mb-3")

            kw_list = existing_note.get("personal_keywords", [])
            kw_input = ui.input(
                label="8. Palavras-Chave do Pesquisador (separadas por vírgula)",
                value=", ".join(kw_list),
            ).props("outlined dense").classes("w-full mb-3")

        # Botões de Ação
        def _save_current(as_reviewed: bool = False) -> None:
            source_val = "human_reviewed" if as_reviewed else source_select.value
            reviewer_val = reviewer_input.value.strip() if reviewer_input.value else "Pesquisador"

            # Parse de citações diretas
            raw_q = quotes_input.value.strip().split("\n") if quotes_input.value else []
            parsed_quotes = []
            for line in raw_q:
                line = line.strip()
                if not line:
                    continue
                page_val = None
                if "[p." in line and line.endswith("]"):
                    parts = line.rsplit("[p.", 1)
                    line_text = parts[0].strip()
                    page_val = parts[1].rstrip("]").strip()
                else:
                    line_text = line
                parsed_quotes.append({"quote": line_text, "page": page_val})

            kw_parsed = [k.strip() for k in kw_input.value.split(",") if k.strip()] if kw_input.value else []

            note_payload = {
                "work_id": str(work_id),
                "title": title_text,
                "authors": [a.get("name") for a in authors_raw if isinstance(a, dict) and a.get("name")],
                "year": work.get("year"),
                "doi": doi_text or None,
                "abnt_reference": abnt_ref,
                "objective": obj_input.value.strip() or None,
                "methodology": method_input.value.strip() or None,
                "sample": sample_input.value.strip() or None,
                "results": results_input.value.strip() or None,
                "limitations": limitations_input.value.strip() or None,
                "synthesis": synthesis_input.value.strip() or None,
                "personal_keywords": kw_parsed,
                "direct_quotes": parsed_quotes,
                "source": source_val,
                "ai_model": ai_model_input.value.strip() or None,
                "reviewed_by": reviewer_val if source_val == "human_reviewed" else None,
            }

            try:
                service.save_work_note(list_id, note_payload)
                if as_reviewed:
                    source_select.set_value("human_reviewed")
                    reviewer_input.set_value(reviewer_val)
                    ui.notify("Ficha validada como revisada por humano!", type="positive")
                else:
                    ui.notify("Ficha científica salva com sucesso!", type="positive")
            except (RSLError, OSError, ValueError) as err:
                ui.notify(f"Erro ao salvar ficha: {err}", type="negative")

        def _copy_obsidian() -> None:
            note_dict = {
                "list_id": list_id,
                "work_id": str(work_id),
                "title": title_text,
                "authors": [a.get("name") for a in authors_raw if isinstance(a, dict) and a.get("name")],
                "year": work.get("year"),
                "doi": doi_text or None,
                "abnt_reference": abnt_ref,
                "objective": obj_input.value.strip() or None,
                "methodology": method_input.value.strip() or None,
                "sample": sample_input.value.strip() or None,
                "results": results_input.value.strip() or None,
                "limitations": limitations_input.value.strip() or None,
                "synthesis": synthesis_input.value.strip() or None,
                "personal_keywords": [k.strip() for k in kw_input.value.split(",") if k.strip()] if kw_input.value else [],
                "direct_quotes": [{"quote": q.strip()} for q in quotes_input.value.split("\n") if q.strip()] if quotes_input.value else [],
                "source": source_select.value,
                "ai_model": ai_model_input.value.strip() or None,
                "reviewed_by": reviewer_input.value.strip() or None,
            }
            md_text = format_note_markdown(note_dict)
            _copy_text(md_text)

        with ui.row().classes("w-full items-center justify-between p-4 rounded-lg rsl-surface-2 border border-slate-200 mt-4"):
            with ui.row().classes("items-center gap-2"):
                ui.button(
                    "Salvar Ficha",
                    icon="save",
                    on_click=lambda: _save_current(False),
                ).props("unelevated color=primary").mark("btn-save-note")

                ui.button(
                    "Validar como Revisado",
                    icon="check_circle",
                    on_click=lambda: _save_current(True),
                ).props("outline color=positive").mark("btn-validate-reviewed")

            ui.button(
                "Copiar Markdown (Obsidian)",
                icon="content_copy",
                on_click=_copy_obsidian,
            ).props("outline color=primary").mark("btn-copy-markdown")


def _copy_text(text: str) -> None:
    ui.run_javascript(f"navigator.clipboard.writeText({text!r})")
    ui.notify("Texto copiado para a área de transferência!", type="positive")
