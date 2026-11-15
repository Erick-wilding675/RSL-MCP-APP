"""Tela Buscar do app desktop (FR-16, D-022, D-023, D-024, D-025)."""

from __future__ import annotations

from nicegui import ui

from rslapp.core.errors import RSLError
from rslapp.core.search import (
    DEFAULT_MAX_RESULTS,
    DEFAULT_SEARCH_SOURCES,
    MAX_MAX_RESULTS,
    MIN_MAX_RESULTS,
)
from rslapp.desktop.pages import render_header
from rslapp.desktop.service import DesktopService

SOURCE_LABELS: dict[str, str] = {
    "openalex": "OpenAlex",
    "crossref": "Crossref",
    "semantic_scholar": "Semantic Scholar",
    "europe_pmc": "Europe PMC",
    "pubmed": "PubMed",
    "scopus": "Scopus",
    "web_of_science": "Web of Science",
}

LIFE_SCIENCES_SOURCES: frozenset[str] = frozenset({"pubmed", "europe_pmc"})
PAID_SOURCES: frozenset[str] = frozenset({"scopus", "web_of_science"})


# FR-16, D-022, D-023, D-024, D-025: Formulário da tela Buscar (/)
def build(service: DesktopService) -> None:
    """Monta a tela de busca de artigos acadêmicos."""
    render_header()
    sources_info = service.list_sources()

    with ui.column().classes("w-full max-w-4xl mx-auto p-4 gap-4"):
        ui.label("Buscar").classes("text-h5 font-bold")
        ui.label("Busque artigos nas bases acadêmicas configuradas.")

        # FR-16: String de busca enviada diretamente a cada base, sem IA no meio
        query_input = (
            ui.textarea(
                label="String de busca",
                placeholder='Ex.: ("systematic review" OR "literature review") AND bibliometrics',
            )
            .classes("w-full")
            .mark("query-input")
        )
        ui.label(
            "A string vai como está para cada base selecionada; o app não usa IA."
        ).classes("text-caption text-grey-7")

        # FR-16, D-020, D-023: Seleção de fontes acadêmicas com notas e bloqueio de pagas sem chave
        ui.label("Fontes").classes("text-subtitle1 font-bold")
        source_checkboxes: dict[str, ui.checkbox] = {}
        permanently_disabled: set[str] = set()

        with ui.column().classes("gap-1"):
            for src in sources_info:
                name = str(src["name"])
                status = str(src.get("status", "ok"))
                label = SOURCE_LABELS.get(name, name)
                default_checked = name in DEFAULT_SEARCH_SOURCES
                is_paid_missing_key = name in PAID_SOURCES and status == "missing_key"

                with ui.row().classes("items-center gap-2"):
                    cb = ui.checkbox(
                        label,
                        value=False if is_paid_missing_key else default_checked,
                    ).mark(f"source-{name}")
                    if is_paid_missing_key:
                        cb.disable()
                        permanently_disabled.add(name)
                    source_checkboxes[name] = cb

                    if name in LIFE_SCIENCES_SOURCES:
                        ui.label("saúde e ciências da vida").classes(
                            "text-caption text-grey-7"
                        )
                    if is_paid_missing_key:
                        ui.label("configure a chave em Configurações").classes(
                            "text-caption text-amber-9"
                        )
                        ui.link("Configurações", "/configuracoes").classes(
                            "text-caption"
                        )

        # FR-16: Quantidade máxima por fonte usando os limites do núcleo
        max_results_input = (
            ui.number(
                label="Quantidade",
                value=DEFAULT_MAX_RESULTS,
                min=MIN_MAX_RESULTS,
                max=MAX_MAX_RESULTS,
                precision=0,
                step=1,
            )
            .classes("w-48")
            .mark("max-results")
        )

        # D-022, FR-16: Opção para incluir pareceres de revisão por pares, desmarcada por padrão
        peer_review_cb = ui.checkbox(
            "Incluir pareceres de revisão por pares",
            value=False,
        ).mark("include-peer-review")

        progress_row = ui.row().classes("items-center gap-2")
        with progress_row:
            ui.spinner(size="sm")
            ui.label("Buscando artigos nas fontes selecionadas...")
        progress_row.set_visibility(False)

        def _set_form_enabled(enabled: bool) -> None:
            if enabled:
                query_input.enable()
                max_results_input.enable()
                peer_review_cb.enable()
                search_button.enable()
                for name, cb in source_checkboxes.items():
                    if name not in permanently_disabled:
                        cb.enable()
            else:
                query_input.disable()
                max_results_input.disable()
                peer_review_cb.disable()
                search_button.disable()
                for cb in source_checkboxes.values():
                    cb.disable()

        # FR-16, FR-08, NFR-03: Execução assíncrona da busca com tratamento de erro e navegação
        async def on_search() -> None:
            raw_query = query_input.value if isinstance(query_input.value, str) else ""
            if not raw_query.strip():
                ui.notify("Informe a string de busca.", type="negative")
                return

            selected_sources = [
                name for name, cb in source_checkboxes.items() if cb.value
            ]
            raw_max = max_results_input.value
            if (
                raw_max is None
                or isinstance(raw_max, bool)
                or int(raw_max) != raw_max
            ):
                max_results = 0
            else:
                max_results = int(raw_max)

            _set_form_enabled(False)
            progress_row.set_visibility(True)
            try:
                result = await service.search(
                    query=raw_query.strip(),
                    sources=selected_sources,
                    max_results=max_results,
                    include_peer_review=bool(peer_review_cb.value),
                )
            except RSLError as err:
                ui.notify(err.message, type="negative")
                return
            finally:
                progress_row.set_visibility(False)
                _set_form_enabled(True)

            list_id = result.get("list_id", "")
            ui.navigate.to(f"/lista/{list_id}")

        search_button = ui.button("Buscar", on_click=on_search).mark("search-button")
