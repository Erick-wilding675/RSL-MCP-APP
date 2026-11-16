"""Tela Buscar do app desktop (FR-16, D-022, D-023, D-024, D-025, D-031)."""

from __future__ import annotations

from nicegui import ui

from rslapp.core.errors import RSLError
from rslapp.core.search import (
    DEFAULT_MAX_RESULTS,
    DEFAULT_SEARCH_SOURCES,
    MAX_MAX_RESULTS,
    MIN_MAX_RESULTS,
)
from rslapp.desktop.components import section_card
from rslapp.desktop.pages import render_shell
from rslapp.desktop.service import DesktopService
from rslapp.desktop.theme import apply_theme

SOURCE_LABELS: dict[str, str] = {
    "openalex": "OpenAlex",
    "crossref": "Crossref",
    "semantic_scholar": "Semantic Scholar",
    "europe_pmc": "Europe PMC",
    "pubmed": "PubMed",
    "scopus": "Scopus",
    "web_of_science": "Web of Science",
}

# D-031, FR-16: Linhas de descrição de cada fonte acadêmica
SOURCE_DESCRIPTIONS: dict[str, str] = {
    "openalex": "ampla, todas as áreas",
    "crossref": "metadados dos DOIs",
    "semantic_scholar": "citações e áreas de computação e saúde",
    "europe_pmc": "saúde e ciências da vida",
    "pubmed": "saúde e ciências da vida",
    "scopus": "base multidisciplinar (Elsevier)",
    "web_of_science": "base multidisciplinar (Clarivate)",
}

LIFE_SCIENCES_SOURCES: frozenset[str] = frozenset({"pubmed", "europe_pmc"})
PAID_SOURCES: frozenset[str] = frozenset({"scopus", "web_of_science"})


# FR-16, D-022, D-023, D-024, D-025, D-031: Tela Buscar refeita com tema visual novo
def build(service: DesktopService) -> None:
    """Monta a tela de busca de artigos acadêmicos com novo layout de cartões."""
    apply_theme()
    render_shell("Buscar", "Busque artigos nas bases acadêmicas configuradas.")
    sources_info = service.list_sources()

    with ui.column().classes("w-full gap-5"):
        # FR-16, D-031: Cartão 'String de busca' com textarea grande (4 a 10 linhas) e atalho Ctrl+Enter
        with section_card("String de busca", icon="search"):
            query_input = (
                ui.textarea(
                    label="String de busca",
                    placeholder='Ex.: ("systematic review" OR "literature review") AND bibliometrics',
                )
                .props("rows=4 autogrow")
                .classes("w-full")
                .style("max-height: 240px; overflow-y: auto;")
                .mark("query-input")
            )

            with ui.row().classes(
                "w-full justify-between items-center text-caption text-grey-7 dark:text-grey-4"
            ):
                ui.label(
                    "A string vai como está para cada base selecionada; o app não usa IA."
                )
                ui.label("Ctrl+Enter para buscar").classes(
                    "font-mono text-xs bg-grey-2 dark:bg-grey-9 px-2 py-0.5 rounded text-grey-8 dark:text-grey-3"
                )

        # FR-16, D-020, D-023, D-031: Cartão 'Fontes' com chips/cartões em grade de 2 a 3 colunas
        with section_card("Fontes", icon="menu_book"):
            source_checkboxes: dict[str, ui.checkbox] = {}
            permanently_disabled: set[str] = set()

            with ui.element("div").classes(
                "grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 w-full"
            ):
                for src in sources_info:
                    name = str(src["name"])
                    status = str(src.get("status", "ok"))
                    label = SOURCE_LABELS.get(name, name)
                    default_checked = name in DEFAULT_SEARCH_SOURCES
                    is_paid_missing_key = (
                        name in PAID_SOURCES and status == "missing_key"
                    )

                    card_classes = (
                        "p-3 rounded-lg border gap-1 flex flex-col justify-between transition-colors "
                    )
                    if is_paid_missing_key:
                        card_classes += "bg-grey-1 dark:bg-grey-9 border-grey-3 dark:border-grey-8 opacity-75"
                    else:
                        card_classes += "bg-white dark:bg-[#121933] border-grey-3 dark:border-grey-8 hover:border-primary"

                    with ui.card().classes(card_classes).style(
                        "box-shadow: none !important;"
                    ):
                        cb = ui.checkbox(
                            label,
                            value=False if is_paid_missing_key else default_checked,
                        ).mark(f"source-{name}").classes("font-semibold text-sm")
                        if is_paid_missing_key:
                            cb.disable()
                            permanently_disabled.add(name)
                        source_checkboxes[name] = cb

                        if is_paid_missing_key:
                            with ui.column().classes("gap-0.5 mt-1"):
                                ui.label(
                                    "configure a chave em Configurações"
                                ).classes("text-caption text-amber-9 font-medium")
                                ui.link(
                                    "Configurações", "/configuracoes"
                                ).classes("text-caption underline")
                        else:
                            desc = SOURCE_DESCRIPTIONS.get(name, "")
                            if desc:
                                ui.label(desc).classes(
                                    "text-caption text-grey-6 dark:text-grey-4"
                                )

        # FR-16, D-022, D-031: Cartão 'Opções' com Quantidade e Pareceres lado a lado
        with (
            section_card("Opções", icon="tune"),
            ui.row().classes("w-full items-center gap-6 flex-wrap"),
        ):
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

            peer_review_cb = ui.checkbox(
                "Incluir pareceres de revisão por pares",
                value=False,
            ).mark("include-peer-review")

        # D-031, FR-16: Cartão de progresso com texto e barra indeterminada durante a busca
        with (
            ui.card()
            .classes(
                "w-full p-4 gap-3 bg-indigo-50/50 dark:bg-indigo-950/20 "
                "border border-primary/20"
            )
            .mark("progress-card") as progress_card
        ):
            with ui.row().classes("items-center gap-3"):
                ui.spinner("dots", size="sm", color="primary")
                ui.label("Buscando artigos nas fontes selecionadas...").classes(
                    "text-sm font-medium text-primary"
                )
            ui.linear_progress(show_value=False).props(
                "indeterminate rounded color=primary"
            ).classes("w-full")
        progress_card.set_visibility(False)

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

        is_searching = False

        # FR-16, FR-08, D-031, NFR-03: Execução da busca com proteção contra clique duplo e Ctrl+Enter
        async def on_search() -> None:
            nonlocal is_searching
            if is_searching or not query_input.enabled:
                return

            raw_query = (
                query_input.value if isinstance(query_input.value, str) else ""
            )
            if not raw_query.strip():
                ui.notify("Informe a string de busca.", type="negative")
                return

            is_searching = True
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
            progress_card.set_visibility(True)
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
                is_searching = False
                progress_card.set_visibility(False)
                _set_form_enabled(True)

            list_id = result.get("list_id", "")
            ui.navigate.to(f"/lista/{list_id}")

        # D-031: Ctrl+Enter na caixa de busca dispara a busca
        query_input.on("keydown.ctrl.enter", on_search)
        query_input.on("keydown.meta.enter", on_search)

        # D-031, FR-16: Botão Buscar grande, na cor primary, com ícone e alinhado à direita
        with ui.row().classes("w-full justify-end"):
            search_button = (
                ui.button("Buscar", icon="search", on_click=on_search)
                .props("size=lg color=primary")
                .classes("px-6 font-semibold")
                .mark("search-button")
            )
