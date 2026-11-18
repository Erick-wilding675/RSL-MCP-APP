"""Tela de Triagem Rápida do app desktop (FR-25, D-024, D-025, D-036)."""

from __future__ import annotations

from typing import Any

from nicegui import events, ui

from rslapp.core.errors import RSLError
from rslapp.core.screening import DEFAULT_EXCLUSION_REASONS, validate_decision_data
from rslapp.desktop.components import empty_state, section_card
from rslapp.desktop.pages import render_shell
from rslapp.desktop.pages.list_view import _format_authors, _format_doi, _format_work_sources
from rslapp.desktop.service import DesktopService
from rslapp.desktop.theme import apply_theme


# FR-25, D-036: Constrói a tela interativa de triagem de artigos (/triagem/{list_id})
def build(service: DesktopService, list_id: str = "") -> None:
    """Renderiza o modo focado de triagem artigo por artigo com atalhos de teclado e rastro de autoria."""
    apply_theme()
    render_shell(
        "Triagem",
        "Seleção e triagem metodológica artigo a artigo com atalhos de teclado e rastro de auditoria.",
        active="Buscar",
    )

    with ui.column().classes("w-full gap-4 max-w-5xl mx-auto"):
        try:
            list_data = service.get_list(list_id)
        except RSLError:
            with ui.column().classes("w-full items-center justify-center p-8 gap-3 text-center"):
                empty_state(
                    icon="search_off",
                    title="Lista não encontrada",
                    text=f"Lista {list_id}: lista não encontrada.",
                )
                ui.link("Voltar para Buscar", "/").props("outline").classes("mt-2")
            return

        raw_works = list_data.get("works")
        works: list[dict[str, Any]] = (
            [w for w in raw_works if isinstance(w, dict)]
            if isinstance(raw_works, list)
            else []
        )
        total_works = len(works)

        if total_works == 0:
            with ui.column().classes("w-full items-center justify-center p-8 gap-3 text-center"):
                empty_state(
                    icon="inbox",
                    title="Nenhum artigo nesta lista",
                    text="Esta lista não contém artigos para triagem.",
                )
                ui.link("Voltar para a Lista", f"/lista/{list_id}").props("outline")
            return

        # Estado local da tela de triagem
        state: dict[str, Any] = {
            "index": 0,
            "stage": "title_abstract",
            "reason": DEFAULT_EXCLUSION_REASONS[0],
            "notes": "",
            "decisions": {},
        }

        try:
            screening_obj = service.get_screening(list_id)
            state["decisions"] = dict(screening_obj.get("decisions", {}))
        except RSLError:
            state["decisions"] = {}

        # 1. Barra de Ações Superior
        with ui.row().classes("w-full items-center justify-between gap-3 mb-1"):
            with ui.row().classes("items-center gap-2"):
                ui.button(
                    "Voltar para a Lista",
                    icon="arrow_back",
                    on_click=lambda: ui.navigate.to(f"/lista/{list_id}"),
                ).props("flat dense").classes("text-sm rsl-title").mark("back-to-list-btn")
                ui.label("•").classes("rsl-muted")
                ui.label(f"Lista: {list_id}").classes("text-sm font-semibold rsl-muted")

            with ui.row().classes("items-center gap-2"):
                ui.button(
                    "Fluxograma PRISMA 2020",
                    icon="schema",
                    on_click=lambda: ui.navigate.to(f"/prisma/{list_id}"),
                ).props("outline size=sm color=primary").mark("open-prisma-btn")

        # 2. Resumo de Progresso e Métricas
        metrics_container = ui.row().classes("w-full gap-2 items-center flex-wrap")
        progress_bar = ui.linear_progress(value=0.0).classes("w-full rounded h-2.5").props("stripe rounded")

        def _get_work_key(work: dict[str, Any], idx: int) -> str:
            doi = work.get("doi")
            if doi and str(doi).strip():
                return str(doi).strip()
            return str(idx + 1)

        def _update_metrics() -> None:
            metrics_container.clear()
            decisions = state["decisions"]
            screened_cnt = len(decisions)
            inc_cnt = sum(1 for d in decisions.values() if d.get("decision") == "included")
            exc_cnt = sum(1 for d in decisions.values() if d.get("decision") == "excluded")
            may_cnt = sum(1 for d in decisions.values() if d.get("decision") == "maybe")
            pending_cnt = max(0, total_works - screened_cnt)
            pct = round((screened_cnt / total_works) * 100.0, 1) if total_works > 0 else 0.0

            progress_bar.set_value(pct / 100.0)

            with metrics_container:
                with ui.card().classes("p-2 px-3 items-center text-center rsl-surface-2"):
                    ui.label(f"{pct}%").classes("text-lg font-bold text-primary")
                    ui.label("Progresso").classes("text-[11px] rsl-muted")
                with ui.card().classes("p-2 px-3 items-center text-center rsl-surface-2"):
                    ui.label(str(inc_cnt)).classes("text-lg font-bold text-positive")
                    ui.label("Incluídos").classes("text-[11px] rsl-muted")
                with ui.card().classes("p-2 px-3 items-center text-center rsl-surface-2"):
                    ui.label(str(exc_cnt)).classes("text-lg font-bold text-negative")
                    ui.label("Excluídos").classes("text-[11px] rsl-muted")
                with ui.card().classes("p-2 px-3 items-center text-center rsl-surface-2"):
                    ui.label(str(may_cnt)).classes("text-lg font-bold text-warning")
                    ui.label("Dúvidas").classes("text-[11px] rsl-muted")
                with ui.card().classes("p-2 px-3 items-center text-center rsl-surface-2"):
                    ui.label(str(pending_cnt)).classes("text-lg font-bold rsl-title")
                    ui.label("Pendentes").classes("text-[11px] rsl-muted")

        # 3. Contêiner dinâmico do Trabalho Atual
        card_container = ui.column().classes("w-full gap-4")

        def _save_and_next(decision: str) -> None:
            curr_idx = state["index"]
            if curr_idx < 0 or curr_idx >= total_works:
                return
            work = works[curr_idx]
            work_key = _get_work_key(work, curr_idx)
            doi_val, _ = _format_doi(work.get("doi"))

            try:
                validated = validate_decision_data(
                    work_id=work_key,
                    decision=decision,
                    reason=state["reason"] if decision == "excluded" else None,
                    decided_by="human",
                    stage=state["stage"],
                    notes=state["notes"] or None,
                    doi=doi_val or None,
                )
                saved = service.save_screening_decision(list_id, validated)
                state["decisions"] = dict(saved.get("decisions", {}))
                state["notes"] = ""
                ui.notify(
                    f"Trabalho {curr_idx + 1} marcado como {decision.upper()}",
                    type="positive" if decision == "included" else ("negative" if decision == "excluded" else "warning"),
                    position="bottom-right",
                )
            except (RSLError, ValueError, KeyError) as err:
                ui.notify(f"Erro ao salvar: {err}", type="negative")
                return

            _update_metrics()
            # Avança se não for o último
            if state["index"] < total_works - 1:
                state["index"] += 1
            _render_current_work()

        def _on_key(e: events.KeyEventArguments) -> None:
            if not e.action.keydown:
                return
            k = e.key.lower()
            if k == "i":
                _save_and_next("included")
            elif k == "e":
                _save_and_next("excluded")
            elif k == "m":
                _save_and_next("maybe")
            elif k in {"arrowright", "d"} and state["index"] < total_works - 1:
                state["index"] += 1
                _render_current_work()
            elif k in {"arrowleft", "a"} and state["index"] > 0:
                state["index"] -= 1
                _render_current_work()

        # Registra captura de teclado
        ui.keyboard(on_key=_on_key)

        def _render_current_work() -> None:
            card_container.clear()
            idx = state["index"]
            work = works[idx]
            work_key = _get_work_key(work, idx)
            current_dec = state["decisions"].get(work_key, {})
            current_status = current_dec.get("decision")

            doi_text, doi_url = _format_doi(work.get("doi"))
            authors_text = _format_authors(work.get("authors"))
            sources_text = _format_work_sources(work)
            abstract_text = str(work.get("abstract") or "").strip()

            with card_container:
                # Barra de Navegação do Artigo
                with ui.row().classes("w-full items-center justify-between gap-3 p-3 rounded rsl-surface-2 border"):
                    with ui.row().classes("items-center gap-2"):
                        ui.button(
                            icon="arrow_back",
                            on_click=lambda: _prev_work(),
                        ).props("flat dense").mark("prev-work-btn")
                        ui.label(f"Artigo {idx + 1} de {total_works}").classes("font-bold text-sm rsl-title")
                        ui.button(
                            icon="arrow_forward",
                            on_click=lambda: _next_work(),
                        ).props("flat dense").mark("next-work-btn")

                    # Seletor de Estágio
                    with ui.row().classes("items-center gap-2"):
                        ui.label("Estágio:").classes("text-xs font-semibold rsl-muted")
                        stage_select = ui.select(
                            {"title_abstract": "Fase 1: Título e Resumo", "full_text": "Fase 2: Texto Completo"},
                            value=state["stage"],
                        ).props("dense outlined options-dense").classes("text-xs")

                        def _on_stage_change(ev: Any) -> None:
                            state["stage"] = ev.value
                        stage_select.on("update:model-value", _on_stage_change)

                    ui.label("Atalhos: [I] Incluir • [E] Excluir • [M] Dúvida • [←/→] Navegar").classes(
                        "text-xs rsl-muted hidden md:block"
                    )

                # Cartão Principal do Artigo
                with section_card(f"Artigo #{idx + 1}", icon="article"):
                    # Badges de estado
                    with ui.row().classes("items-center gap-2 mb-1 flex-wrap"):
                        if current_status == "included":
                            ui.badge("INCLUÍDO", color="positive").classes("text-xs font-bold px-2 py-0.5 rounded-full")
                        elif current_status == "excluded":
                            r_label = current_dec.get("reason") or "Excluído"
                            ui.badge(f"EXCLUÍDO: {r_label}", color="negative").classes("text-xs font-bold px-2 py-0.5 rounded-full")
                        elif current_status == "maybe":
                            ui.badge("DÚVIDA / PENDENTE", color="warning").classes("text-xs font-bold px-2 py-0.5 rounded-full")
                        else:
                            ui.badge("NÃO TRIADO", color="grey").classes("text-xs font-bold px-2 py-0.5 rounded-full")

                        if work.get("is_retracted"):
                            ui.badge("RETRATADO", color="negative").classes("text-xs font-bold px-2 py-0.5 rounded-full")
                        if work.get("type") in {"thesis", "dissertation"}:
                            ui.badge(str(work.get("type")).upper(), color="teal").classes("text-xs font-bold px-2 py-0.5 rounded-full")

                    # Título
                    ui.label(str(work.get("title") or "Sem título")).classes("text-xl font-bold rsl-title leading-snug")

                    # Metadados
                    with ui.row().classes("items-center gap-4 text-xs rsl-muted my-1 flex-wrap"):
                        if work.get("year"):
                            ui.label(f"Ano: {work.get('year')}").classes("font-semibold")
                        if authors_text:
                            ui.label(f"Autores: {authors_text}")
                        if work.get("venue"):
                            ui.label(f"Periódico: {work.get('venue')}")
                        if doi_text:
                            ui.link(doi_text, doi_url, new_tab=True).classes("text-primary underline font-mono")
                        if sources_text:
                            ui.label(f"Bases: {sources_text}")

                    # Resumo (Abstract)
                    ui.separator().classes("my-2")
                    ui.label("Resumo (Abstract):").classes("text-xs font-bold uppercase tracking-wider rsl-muted")
                    if abstract_text:
                        ui.label(abstract_text).classes(
                            "text-sm leading-relaxed p-4 rounded-lg rsl-surface-2 whitespace-pre-wrap select-text border"
                        )
                    else:
                        ui.label("Resumo não disponível nos metadados obtidos da base de dados.").classes(
                            "text-sm italic rsl-muted p-4 rounded-lg rsl-surface-2 border"
                        )

                    # Bloco de Justificativa e Ações de Decisão
                    ui.separator().classes("my-2")
                    with ui.column().classes("w-full gap-3 pt-1"):
                        with ui.row().classes("w-full items-center gap-3 flex-wrap"):
                            reason_select = ui.select(
                                list(DEFAULT_EXCLUSION_REASONS),
                                value=state["reason"],
                                label="Motivo da Exclusão (caso exclua)",
                            ).props("dense outlined").classes("flex-1 min-w-[280px]")

                            def _on_reason_change(ev: Any) -> None:
                                state["reason"] = ev.value
                            reason_select.on("update:model-value", _on_reason_change)

                            notes_input = ui.input(
                                label="Notas metodológicas (opcional)",
                                value=state["notes"],
                            ).props("dense outlined").classes("flex-1 min-w-[240px]")

                            def _on_notes_change(ev: Any) -> None:
                                state["notes"] = ev.value
                            notes_input.on("update:model-value", _on_notes_change)

                        # Botões de Decisão
                        with ui.row().classes("w-full items-center justify-between gap-3 pt-2"):
                            ui.button(
                                "Incluir Artigo (I)",
                                icon="check_circle",
                                on_click=lambda: _save_and_next("included"),
                            ).props("unelevated color=positive size=md").classes("flex-1 font-bold py-2").mark("btn-screen-include")

                            ui.button(
                                "Dúvida / Talvez (M)",
                                icon="help",
                                on_click=lambda: _save_and_next("maybe"),
                            ).props("outline color=warning size=md").classes("flex-1 font-semibold py-2").mark("btn-screen-maybe")

                            ui.button(
                                "Excluir Artigo (E)",
                                icon="cancel",
                                on_click=lambda: _save_and_next("excluded"),
                            ).props("unelevated color=negative size=md").classes("flex-1 font-bold py-2").mark("btn-screen-exclude")

        def _prev_work() -> None:
            if state["index"] > 0:
                state["index"] -= 1
                _render_current_work()

        def _next_work() -> None:
            if state["index"] < total_works - 1:
                state["index"] += 1
                _render_current_work()

        # Renderização inicial
        _update_metrics()
        _render_current_work()
