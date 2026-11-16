"""Tela de verificação de referências contra alucinação de IA no app desktop (FR-21, D-030, D-031)."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from rslapp.core.errors import RSLError
from rslapp.desktop.components import (
    empty_state,
    metric_card,
    section_card,
)
from rslapp.desktop.pages import render_shell
from rslapp.desktop.service import DesktopService
from rslapp.desktop.theme import apply_theme

TABLE_COLUMNS: list[dict[str, Any]] = [
    {
        "name": "status",
        "label": "Status",
        "field": "status",
        "align": "center",
        "sortable": True,
    },
    {
        "name": "input_ref",
        "label": "Referência citada",
        "field": "input_ref",
        "align": "left",
        "sortable": True,
    },
    {
        "name": "match",
        "label": "Correspondência nas bases",
        "field": "matched_title",
        "align": "left",
        "sortable": True,
    },
    {
        "name": "details",
        "label": "Análise / Divergências",
        "field": "details_text",
        "align": "left",
    },
    {
        "name": "doi",
        "label": "DOI",
        "field": "doi",
        "align": "left",
    },
]


def _format_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prepara os dados estruturados de verificação para as linhas do ui.table."""
    rows: list[dict[str, Any]] = []
    for idx, item in enumerate(results, start=1):
        doi_val = item.get("doi")
        doi_url = f"https://doi.org/{doi_val}" if doi_val else None
        authors = item.get("matched_authors") or []
        authors_str = ", ".join(authors) if isinstance(authors, list) else str(authors)
        divergences = item.get("divergence_details") or []
        details_text = "; ".join(divergences) if divergences else ""

        rows.append(
            {
                "id": idx,
                "status": item.get("status", "not_found"),
                "status_label": item.get("status_label", "Não encontrada"),
                "input_ref": item.get("input_ref", ""),
                "matched_title": item.get("matched_title") or "",
                "matched_year": item.get("matched_year"),
                "matched_authors": authors_str,
                "source": item.get("source") or "",
                "divergence_details": divergences,
                "details_text": details_text,
                "doi": doi_val or "",
                "doi_url": doi_url,
            }
        )
    return rows


# FR-21, D-030, D-031: Tela Verificar referências contra alucinação
def build(service: DesktopService) -> None:
    """Monta a interface de verificação de referências com entrada textual e tabela de resultados."""
    apply_theme()
    render_shell(
        "Verificar",
        "Verifique se referências citadas existem nas bases reais contra alucinações de IA.",
    )

    with ui.column().classes("w-full gap-5"):
        # Cartão de entrada das referências
        with section_card(
            "Referências a verificar",
            icon="fact_check",
            description="Cole uma lista de referências, texto com citações ou entradas BibTeX para conferência cruzada.",
        ):
            input_area = (
                ui.textarea(
                    label="Lista de referências ou BibTeX",
                    placeholder=(
                        "Exemplo:\n"
                        "@article{vaswani2017,\n"
                        "  title = {Attention is All you Need},\n"
                        "  author = {Vaswani, Ashish and Shazeer, Noam},\n"
                        "  year = {2017},\n"
                        "  doi = {10.5555/3295222.3295349}\n"
                        "}\n\n"
                        "Ou em texto livre:\n"
                        "[1] LeCun, Y. et al. (2015). Deep learning. Nature. doi: 10.1038/nature14539"
                    ),
                )
                .props("rows=6 autogrow outlined")
                .classes("w-full")
                .mark("verify-input")
            )

            with ui.row().classes("w-full items-center justify-between gap-4 mt-2"):
                verify_btn = (
                    ui.button("Verificar referências", icon="fact_check")
                    .props("unelevated")
                    .classes("px-5 py-2 font-medium")
                    .mark("verify-btn")
                )
                clear_btn = (
                    ui.button("Limpar", on_click=lambda: input_area.set_value(""))
                    .props("flat")
                    .classes("rsl-muted text-xs")
                    .mark("verify-clear-btn")
                )
                _ = clear_btn

            progress_bar = (
                ui.linear_progress(size="4px")
                .props("indeterminate")
                .classes("w-full mt-2")
                .mark("verify-progress")
            )
            progress_bar.set_visibility(False)

        # Contêiner de resultados dinâmicos
        results_container = ui.column().classes("w-full gap-5").mark("verify-results-container")

        def _render_empty() -> None:
            results_container.clear()
            with results_container:
                empty_state(
                    icon="fact_check",
                    title="Nenhuma verificação realizada",
                    text="Cole referências ou entradas BibTeX no campo acima e clique em 'Verificar referências' para checar a autenticidade.",
                ).mark("verify-empty-state")

        _render_empty()

        async def _on_verify() -> None:
            raw_text = (input_area.value or "").strip()
            if not raw_text:
                ui.notify("Por favor, cole pelo menos uma referência para verificar.", type="warning")
                return

            verify_btn.props("loading")
            verify_btn.disable()
            progress_bar.set_visibility(True)

            try:
                result_data = await service.verify_references(raw_text)
                results_container.clear()
                total = result_data.get("total", 0)
                verified = result_data.get("verified", 0)
                divergent = result_data.get("divergent", 0)
                not_found = result_data.get("not_found", 0)
                items = result_data.get("results", [])

                with results_container:
                    if total == 0:
                        empty_state(
                            icon="search_off",
                            title="Nenhuma referência identificada",
                            text="Não foi possível identificar títulos, autores ou entradas BibTeX no texto informado.",
                        ).mark("verify-no-refs-state")
                        return

                    # Resumo métrico
                    with ui.row().classes("w-full gap-3 flex-wrap"):
                        metric_card(total, "Total verificado", mark="metric-total")
                        metric_card(
                            verified,
                            "Confirmadas",
                            color_class="text-positive",
                            mark="metric-verified",
                        )
                        metric_card(
                            divergent,
                            "Divergências",
                            color_class="text-warning",
                            mark="metric-divergent",
                        )
                        metric_card(
                            not_found,
                            "Não encontradas",
                            color_class="text-negative",
                            mark="metric-not-found",
                        )

                    # Tabela de resultados
                    with section_card("Resultados da verificação", icon="rule"):
                        with ui.row().classes("w-full items-center justify-between gap-4 mb-2"):
                            filter_input = (
                                ui.input(placeholder="Filtrar resultados...")
                                .props("dense outlined clearable")
                                .classes("w-full max-w-md")
                                .mark("verify-table-filter")
                            )
                            with filter_input.add_slot("prepend"):
                                ui.icon("search").classes("text-grey-6")

                            ui.label(f"{total} referências").classes("text-xs rsl-muted")

                        rows = _format_rows(items)
                        table = (
                            ui.table(
                                columns=TABLE_COLUMNS,
                                rows=rows,
                                row_key="id",
                                pagination=50,
                            )
                            .classes("w-full rsl-table sticky-header-table")
                            .props("flat")
                            .mark("verify-table")
                        )
                        filter_input.bind_value(table, "filter")

                        # Slot de Status com badge Quasar
                        table.add_slot(
                            "body-cell-status",
                            r"""
                            <q-td :props="props">
                                <q-badge v-if="props.row.status === 'verified'" color="positive" class="text-xs px-2 py-0.5 rounded-full font-medium">
                                    Confirmada
                                </q-badge>
                                <q-badge v-else-if="props.row.status === 'divergent'" color="warning" class="text-xs px-2 py-0.5 rounded-full font-medium">
                                    Divergência
                                </q-badge>
                                <q-badge v-else color="negative" class="text-xs px-2 py-0.5 rounded-full font-medium">
                                    Não encontrada
                                </q-badge>
                            </q-td>
                            """,
                        )

                        # Slot da Referência citada
                        table.add_slot(
                            "body-cell-input_ref",
                            r"""
                            <q-td :props="props">
                                <div class="font-medium rsl-title text-xs leading-snug whitespace-pre-wrap">{{ props.row.input_ref }}</div>
                            </q-td>
                            """,
                        )

                        # Slot da Correspondência nas bases
                        table.add_slot(
                            "body-cell-match",
                            r"""
                            <q-td :props="props">
                                <div v-if="props.row.matched_title" class="text-xs leading-snug">
                                    <span class="font-bold rsl-title">{{ props.row.matched_title }}</span>
                                    <span v-if="props.row.matched_year" class="rsl-muted"> ({{ props.row.matched_year }})</span>
                                    <div v-if="props.row.matched_authors" class="text-[11px] rsl-muted mt-0.5">{{ props.row.matched_authors }}</div>
                                    <div v-if="props.row.source" class="text-[11px] rsl-muted mt-0.5">Base: {{ props.row.source }}</div>
                                </div>
                                <span v-else class="rsl-muted text-xs">—</span>
                            </q-td>
                            """,
                        )

                        # Slot dos Detalhes / Divergências
                        table.add_slot(
                            "body-cell-details",
                            r"""
                            <q-td :props="props">
                                <div v-if="props.row.divergence_details && props.row.divergence_details.length" class="text-xs text-warning">
                                    <div v-for="(det, idx) in props.row.divergence_details" :key="idx">• {{ det }}</div>
                                </div>
                                <div v-else-if="props.row.status === 'verified'" class="text-xs text-positive font-medium">
                                    Dados conferem com a base
                                </div>
                                <div v-else class="text-xs rsl-muted">
                                    Sem correspondência nas bases
                                </div>
                            </q-td>
                            """,
                        )

                        # Slot do DOI
                        table.add_slot(
                            "body-cell-doi",
                            r"""
                            <q-td :props="props">
                                <a v-if="props.row.doi_url" :href="props.row.doi_url" target="_blank" class="text-primary underline font-mono text-xs">
                                    {{ props.row.doi }}
                                </a>
                                <span v-else class="rsl-muted text-xs">—</span>
                            </q-td>
                            """,
                        )

                ui.notify(
                    f"Verificação concluída: {verified} confirmadas, {divergent} divergentes, {not_found} não encontradas.",
                    type="positive",
                )
            except (RSLError, Exception) as err:  # noqa: BLE001
                ui.notify(f"Erro ao verificar referências: {err}", type="negative")
            finally:
                verify_btn.props(remove="loading")
                verify_btn.enable()
                progress_bar.set_visibility(False)

        verify_btn.on("click", _on_verify)
