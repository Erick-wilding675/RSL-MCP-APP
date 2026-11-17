"""Tela de importação de arquivos bibliográficos externos no app desktop (FR-23, D-031, D-033)."""

from __future__ import annotations

from typing import Any

from nicegui import events, ui

from rslapp.core.errors import RSLError
from rslapp.desktop.components import (
    empty_state,
    metric_card,
    section_card,
)
from rslapp.desktop.pages import render_shell
from rslapp.desktop.service import DesktopService
from rslapp.desktop.theme import apply_theme

FORMAT_OPTIONS: dict[str, str] = {
    "auto": "Detecção automática",
    "ris": "RIS (.ris)",
    "bibtex": "BibTeX (.bib)",
    "scopus_csv": "Scopus CSV (.csv)",
    "wos": "Web of Science (TSV / Tagged)",
}


# FR-23, D-031, D-033: Constrói a tela de importação de arquivos bibliográficos externos
def build(service: DesktopService) -> None:
    """Monta a interface de importação com upload de arquivo, colagem de texto e feedback métrico."""
    apply_theme()
    render_shell(
        "Importar",
        "Importe buscas e referências exportadas do Scopus, Web of Science, Portal CAPES, Zotero e Mendeley.",
    )

    uploaded_data: dict[str, str] = {"content": "", "filename": ""}

    with ui.column().classes("w-full gap-5"):
        # Cartão de configuração e envio de arquivo
        with section_card(
            "Origem dos dados bibliográficos",
            icon="file_upload",
            description="Carregue um arquivo (.ris, .bib, .csv, .tsv, .txt) ou cole o conteúdo exportado diretamente.",
        ):
            with ui.row().classes("w-full gap-4 items-center flex-wrap"):
                format_select = (
                    ui.select(
                        options=FORMAT_OPTIONS,
                        value="auto",
                        label="Formato de arquivo",
                    )
                    .classes("w-64")
                    .mark("import-format-select")
                )
                list_name_input = (
                    ui.input(
                        label="Nome da lista (opcional)",
                        placeholder="Ex: Busca Scopus Inteligência Artificial 2024",
                    )
                    .classes("flex-1 min-w-[240px]")
                    .mark("import-name-input")
                )

            # Upload de arquivo
            file_badge = ui.label("").classes("text-xs text-primary font-medium").mark("import-file-badge")
            file_badge.set_visibility(False)

            def _handle_upload(e: events.UploadEventArguments) -> None:
                try:
                    content_str = e.content.read().decode("utf-8", errors="replace")
                    uploaded_data["content"] = content_str
                    uploaded_data["filename"] = e.name
                    file_badge.set_text(f"Arquivo carregado: {e.name}")
                    file_badge.set_visibility(True)
                    ui.notify(f"Arquivo '{e.name}' pronto para processamento.", type="info")
                except (OSError, UnicodeDecodeError, ValueError) as exc:
                    ui.notify(f"Erro ao ler arquivo: {exc}", type="negative")

            ui.upload(
                label="Selecionar ou arrastar arquivo",
                on_upload=_handle_upload,
                auto_upload=True,
                max_files=1,
            ).props("outlined accept='.ris,.bib,.csv,.tsv,.txt'").classes("w-full").mark("import-upload")

            # Entrada alternativa por texto
            input_area = (
                ui.textarea(
                    label="Ou cole o conteúdo textual aqui",
                    placeholder="Cole aqui o conteúdo de um arquivo RIS, BibTeX, Scopus CSV ou Web of Science...",
                )
                .props("rows=5 autogrow outlined")
                .classes("w-full mt-2")
                .mark("import-textarea")
            )

            with ui.row().classes("w-full items-center justify-between gap-4 mt-2"):
                import_btn = (
                    ui.button("Processar importação", icon="file_upload")
                    .props("unelevated")
                    .classes("px-5 py-2 font-medium")
                    .mark("import-btn")
                )
                clear_btn = (
                    ui.button(
                        "Limpar",
                        on_click=lambda: (
                            input_area.set_value(""),
                            uploaded_data.update({"content": "", "filename": ""}),
                            file_badge.set_text(""),
                            file_badge.set_visibility(False),
                        ),
                    )
                    .props("flat")
                    .classes("rsl-muted text-xs")
                    .mark("import-clear-btn")
                )
                _ = clear_btn

            progress_bar = (
                ui.linear_progress(size="4px")
                .props("indeterminate")
                .classes("w-full mt-2")
                .mark("import-progress")
            )
            progress_bar.set_visibility(False)

        # Contêiner de resultados dinâmicos
        results_container = ui.column().classes("w-full gap-5").mark("import-results-container")

        def _render_empty() -> None:
            results_container.clear()
            with results_container:
                empty_state(
                    icon="file_upload",
                    title="Nenhuma importação realizada",
                    text="Selecione um arquivo exportado de uma base acadêmica ou cole o texto no campo acima para gerar uma lista nova.",
                ).mark("import-empty-state")

        _render_empty()

        async def _on_process_import() -> None:
            content_to_parse = uploaded_data["content"] or (input_area.value or "").strip()
            if not content_to_parse:
                ui.notify(
                    "Por favor, selecione um arquivo ou cole o conteúdo antes de importar.",
                    type="warning",
                )
                return

            import_btn.props("loading")
            import_btn.disable()
            progress_bar.set_visibility(True)

            try:
                selected_format = format_select.value or "auto"
                list_name = (list_name_input.value or "").strip()
                if not list_name and uploaded_data["filename"]:
                    list_name = uploaded_data["filename"]

                res: dict[str, Any] = service.import_works(
                    content=content_to_parse,
                    format=selected_format,
                    list_name=list_name,
                )

                results_container.clear()
                total = res.get("total", 0)
                dups = res.get("duplicates_removed", 0)
                fmt = res.get("imported_format", "desconhecido")
                list_id = res.get("list_id", "")

                with (
                    results_container,
                    section_card(
                        "Importação concluída com sucesso",
                        icon="check_circle",
                        description=f"Lista {list_id} gerada e pronta para triagem, verificação e mapas no VOSviewer.",
                    ),
                ):
                    with ui.row().classes("w-full gap-3 flex-wrap"):
                        metric_card(total, "Artigos importados", mark="metric-imported-total")
                        metric_card(
                            dups,
                            "Duplicatas unificadas",
                            color_class="rsl-muted",
                            mark="metric-duplicates",
                        )
                        metric_card(
                            fmt.upper(),
                            "Formato identificado",
                            color_class="text-primary",
                            mark="metric-format",
                        )

                    with ui.row().classes("w-full items-center justify-end gap-3 mt-3"):
                        ui.button(
                            "Abrir lista importada",
                            icon="arrow_forward",
                            on_click=lambda lid=list_id: ui.navigate.to(f"/lista/{lid}"),
                        ).props("unelevated").classes("px-5 py-2 font-medium").mark("open-list-btn")

                ui.notify(f"Lista {list_id} importada com {total} artigos!", type="positive")

            except RSLError as rsl_err:
                ui.notify(f"Erro na importação: {rsl_err.message}", type="negative")
            except (OSError, RuntimeError, ValueError) as exc:
                ui.notify(f"Falha inesperada ao importar: {exc}", type="negative")
            finally:
                import_btn.props(remove="loading")
                import_btn.enable()
                progress_bar.set_visibility(False)

        import_btn.on_click(_on_process_import)
