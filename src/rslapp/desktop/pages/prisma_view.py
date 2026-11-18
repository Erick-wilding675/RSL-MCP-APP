"""Tela do Fluxograma PRISMA 2020 e Declaração de IA do app desktop (FR-26, FR-27, D-037, D-038)."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from rslapp.core.errors import RSLError
from rslapp.desktop.components import empty_state
from rslapp.desktop.pages import render_shell
from rslapp.desktop.service import DesktopService
from rslapp.desktop.theme import apply_theme


# FR-26, FR-27, D-037, D-038: Constrói a tela visual do PRISMA 2020 (/prisma/{list_id})
def build(service: DesktopService, list_id: str = "") -> None:
    """Renderiza visualizador do fluxograma vetorial PRISMA 2020, checklist PRISMA-S e declaração de IA."""
    apply_theme()
    render_shell(
        "PRISMA 2020",
        "Diagrama oficial PRISMA 2020 com números calculados, checklist PRISMA-S e declaração ética de IA.",
        active="Buscar",
    )

    with ui.column().classes("w-full gap-4 max-w-6xl mx-auto"):
        try:
            prisma_result = service.get_prisma_flow(list_id)
        except RSLError:
            with ui.column().classes("w-full items-center justify-center p-8 gap-3 text-center"):
                empty_state(
                    icon="search_off",
                    title="Lista não encontrada",
                    text=f"Lista {list_id}: lista não encontrada para gerar o fluxograma.",
                )
                ui.link("Voltar para Buscar", "/").props("outline").classes("mt-2")
            return

        svg_content = prisma_result.get("svg", "")
        markdown_report = prisma_result.get("report_markdown", "")

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
                def _handle_download_pkg() -> None:
                    try:
                        res = service.export_reproducibility_package(list_id)
                        zip_bytes = res.get("zip_bytes")
                        if zip_bytes:
                            ui.download(zip_bytes, res.get("filename", f"reproducibility_{list_id}.zip"))
                        ui.notify("Pacote de Reprodutibilidade gerado com sucesso!", type="positive")
                    except (RSLError, OSError, ValueError) as err:
                        ui.notify(f"Erro ao gerar pacote: {err}", type="negative")

                ui.button(
                    "Pacote Completo (.zip)",
                    icon="archive",
                    on_click=_handle_download_pkg,
                ).props("outline size=sm").mark("btn-reproducibility-zip")

                ui.button(
                    "Ir para Triagem",
                    icon="filter_alt",
                    on_click=lambda: ui.navigate.to(f"/triagem/{list_id}"),
                ).props("unelevated size=sm color=primary").mark("go-to-screening-btn")

        # 2. Abas de Visualização
        with ui.tabs().classes("w-full rsl-surface-2 rounded-t-lg") as tabs:
            tab_diagram = ui.tab("Diagrama PRISMA 2020", icon="schema")
            tab_checklist = ui.tab("Checklist PRISMA-S", icon="fact_check")
            tab_disclosure = ui.tab("Declaração de Uso de IA", icon="psychology")

        with ui.tab_panels(tabs, value=tab_diagram).classes("w-full p-4 rsl-surface-2 rounded-b-lg border"):
            # ABA 1: Diagrama SVG do PRISMA 2020
            with ui.tab_panel(tab_diagram), ui.column().classes("w-full gap-4 items-center"):
                with ui.row().classes("w-full items-center justify-between gap-3"):
                    with ui.column().classes("gap-0.5"):
                        ui.label("Fluxograma PRISMA 2020").classes("text-lg font-bold rsl-title")
                        ui.label("Diagrama vetorial em alta resolução com os números reais de cada fase").classes("text-xs rsl-muted")

                    ui.button(
                        "Baixar Diagrama SVG",
                        icon="download",
                        on_click=lambda: ui.download(
                            svg_content.encode("utf-8"),
                            f"prisma_2020_{list_id}.svg",
                        ),
                    ).props("unelevated color=primary size=sm").mark("download-svg-btn")

                # Injeção segura do SVG
                with ui.card().classes("w-full p-2 bg-white rounded-lg shadow-sm overflow-x-auto border border-slate-200"):
                    ui.html(svg_content).classes("w-full min-w-[700px]")

            # ABA 2: Checklist PRISMA-S
            with ui.tab_panel(tab_checklist), ui.column().classes("w-full gap-4"):
                with ui.row().classes("w-full items-center justify-between gap-3"):
                    with ui.column().classes("gap-0.5"):
                        ui.label("Checklist PRISMA-S (Relato de Buscas)").classes("text-lg font-bold rsl-title")
                        ui.label("Extensão metodológica oficial para relatar buscas sistemáticas").classes("text-xs rsl-muted")

                    ui.button(
                        "Copiar Relatório",
                        icon="content_copy",
                        on_click=lambda: _copy_text(markdown_report, "Relatório copiado!"),
                    ).props("outline size=sm").mark("copy-report-btn")

                with ui.card().classes("w-full p-5 rsl-surface-2 rounded-lg border"):
                    ui.markdown(markdown_report).classes("w-full select-text text-sm leading-relaxed")

            # ABA 3: Declaração de Uso de IA
            with ui.tab_panel(tab_disclosure), ui.column().classes("w-full gap-4"):
                current_text = {"text": service.get_ai_disclosure(list_id, lang="pt")}

                with ui.row().classes("w-full items-center justify-between gap-3"):
                    with ui.column().classes("gap-0.5"):
                        ui.label("Transparência Metodológica e Ética de IA").classes("text-lg font-bold rsl-title")
                        ui.label("Texto pronto para a seção de Metodologia segundo as diretrizes COPE, ICMJE e SciELO").classes("text-xs rsl-muted")

                    with ui.row().classes("items-center gap-2"):
                        lang_select = ui.select(
                            {"pt": "Português (SciELO / ABNT)", "en": "Inglês (COPE / ICMJE)"},
                            value="pt",
                        ).props("dense outlined options-dense").classes("text-xs w-60").mark("lang-select")

                        def _copy_action() -> None:
                            _copy_text(current_text["text"], "Declaração copiada com sucesso!")

                        ui.button(
                            "Copiar Declaração",
                            icon="content_copy",
                            on_click=_copy_action,
                        ).props("unelevated color=primary size=sm").mark("copy-disclosure-btn")

                with ui.card().classes("w-full p-5 rsl-surface-2 rounded border"):
                    disclosure_md = ui.markdown(current_text["text"]).classes("w-full select-text text-sm leading-relaxed").mark("disclosure-markdown")

                def _on_lang_change(ev: Any) -> None:
                    selected_val = ev.value if hasattr(ev, "value") else str(ev)
                    new_text = service.get_ai_disclosure(list_id, lang=selected_val)
                    current_text["text"] = new_text
                    disclosure_md.set_content(new_text)

                lang_select.on_value_change(_on_lang_change)

    def _copy_text(content: str, message: str) -> None:
        ui.run_javascript(f"navigator.clipboard.writeText({content!r});")
        ui.notify(message, type="positive", position="bottom-right")
