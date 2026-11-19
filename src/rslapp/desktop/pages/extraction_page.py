"""Tela de Extração de Dados para Metanálise, R metafor e RevMan (FR-35, D-046, FR-38)."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from rslapp.core.errors import RSLError
from rslapp.core.extraction import (
    calculate_mean_difference,
    calculate_odds_ratio,
)
from rslapp.desktop.pages import render_shell
from rslapp.desktop.service import DesktopService


def build(service: DesktopService, list_id: str) -> None:
    """Constrói a tela de extração estruturada de dados para metanálise."""
    render_shell(f"Extração Metanálise · {list_id}", "Extração estruturada de variáveis e desfechos para metanálise", active="Buscar")
    with ui.column().classes("w-full gap-4"):
        try:
            list_data = service.get_list(list_id)
        except (RSLError, ValueError, KeyError, OSError) as e:
            ui.label(f"Erro ao carregar lista: {e}").classes("text-negative font-bold")
            return

        works = list_data.get("works", [])
        extractions_list = service.list_extractions(list_id)
        ext_map = {str(e.get("work_id")): e for e in extractions_list}

        # Cabeçalho com ações
        with ui.row().classes("w-full items-center justify-between q-mb-md"):
            with ui.row().classes("items-center gap-2"):
                ui.button(
                    icon="arrow_back",
                    on_click=lambda: ui.navigate.to(f"/lista/{list_id}"),
                ).props("flat round dense")
                ui.label(f"Extração de Dados para Metanálise ({len(extractions_list)}/{len(works)} preenchidos)").classes("text-h6 font-bold")

            with ui.row().classes("items-center gap-2"):
                def export_metafor() -> None:
                    try:
                        res = service.export_extractions(list_id, format="metafor")
                        ui.notify(f"Arquivo salvo: {res['filename']}", type="positive")
                    except (RSLError, ValueError, KeyError, OSError) as err:
                        ui.notify(f"Erro ao exportar: {err}", type="negative")

                def export_revman() -> None:
                    try:
                        res = service.export_extractions(list_id, format="revman")
                        ui.notify(f"Arquivo salvo: {res['filename']}", type="positive")
                    except (RSLError, ValueError, KeyError, OSError) as err:
                        ui.notify(f"Erro ao exportar: {err}", type="negative")

                ui.button("Exportar R metafor (CSV)", icon="analytics", on_click=export_metafor).props("outline color=primary dense")
                ui.button("Exportar RevMan (CSV)", icon="table_chart", on_click=export_revman).props("outline color=secondary dense")

        if not works:
            ui.label("Esta lista não possui artigos.").classes("text-grey")
            return

        with ui.splitter(value=35).classes("w-full h-full border rounded") as splitter:
            # Lado Esquerdo: Lista de Artigos
            with splitter.before, ui.column().classes("w-full p-2 gap-2"):
                ui.label("Selecione um artigo:").classes("text-subtitle2 font-bold q-mb-xs")
                active_work_id = {"val": str(works[0].get("id") or 0)}

                def on_select_work(wid: str) -> None:
                    active_work_id["val"] = wid
                    render_form()

                for idx, w in enumerate(works):
                    wid = str(w.get("id") or idx)
                    title = w.get("title") or f"Artigo {idx + 1}"
                    has_ext = wid in ext_map
                    is_active = active_work_id["val"] == wid

                    with ui.card().classes(
                        f"w-full cursor-pointer p-2 {'bg-blue-50 border-primary' if is_active else 'bg-white'}"
                    ).on("click", lambda _, target_id=wid: on_select_work(target_id)), ui.row().classes("items-center justify-between no-wrap"):
                        ui.label(f"#{idx + 1} {title[:60]}...").classes("text-caption font-bold ellipsis")
                        if has_ext:
                            ui.badge("Extraído", color="positive").props("dense")
                        else:
                            ui.badge("Pendente", color="grey").props("dense")

            # Lado Direito: Formulário de Extração
            with splitter.after:
                form_container = ui.column().classes("w-full p-4 gap-3")

                def render_form() -> None:
                    form_container.clear()
                    wid = active_work_id["val"]
                    existing = service.get_extraction(list_id, wid) or {}

                    # Busca artigo
                    w_obj = next((w for w in works if str(w.get("id") or "") == wid), None)
                    w_title = w_obj.get("title") if w_obj else f"Artigo {wid}"

                    with form_container:
                        ui.label(w_title).classes("text-subtitle1 font-bold text-primary")

                        with ui.row().classes("w-full gap-4"):
                            design_select = ui.select(
                                label="Desenho do Estudo",
                                options=["RCT", "Cohort", "Case-Control", "Cross-Sectional", "Other"],
                                value=existing.get("study_design", "RCT"),
                            ).classes("w-48")
                            sample_input = ui.number(
                                label="Tamanho Total Amostra (N)",
                                value=existing.get("sample_size_total"),
                                min=1,
                            ).classes("w-48")
                            country_input = ui.input(
                                label="País do Estudo",
                                value=existing.get("country", ""),
                            ).classes("w-48")

                        with ui.row().classes("w-full gap-4"):
                            interv_input = ui.input(
                                label="Descrição da Intervenção / Exposição",
                                value=existing.get("intervention_description", ""),
                            ).classes("flex-1")
                            ctrl_input = ui.input(
                                label="Descrição do Controle / Comparador",
                                value=existing.get("control_description", ""),
                            ).classes("flex-1")

                        ui.separator().classes("q-my-sm")
                        ui.label("Desfechos Extraídos (Outcomes)").classes("text-subtitle2 font-bold")

                        outcomes_state: list[dict[str, Any]] = existing.get("outcomes", [])
                        outcomes_box = ui.column().classes("w-full gap-2")

                        def render_outcomes() -> None:
                            outcomes_box.clear()
                            with outcomes_box:
                                if not outcomes_state:
                                    ui.label("Nenhum desfecho adicionado ainda.").classes("text-caption text-grey")

                                for o_idx, out in enumerate(outcomes_state):
                                    with ui.card().classes("w-full p-3 bg-grey-1 border"):
                                        with ui.row().classes("w-full items-center justify-between"):
                                            ui.label(f"Desfecho {o_idx + 1}: {out.get('name', 'Sem nome')}").classes("font-bold text-subtitle2")
                                            def remove_outcome(target_idx: int = o_idx) -> None:
                                                outcomes_state.pop(target_idx)
                                                render_outcomes()
                                            ui.button(icon="delete", on_click=remove_outcome).props("flat round dense color=negative")

                                        with ui.row().classes("w-full gap-3 q-mt-xs"):
                                            ui.label(f"Tipo: {out.get('outcome_type')}").classes("text-caption")
                                            if out.get("effect_measure") and out.get("effect_estimate") is not None:
                                                ui.badge(
                                                    f"{out.get('effect_measure')} = {out.get('effect_estimate')} (IC 95%: {out.get('ci_lower')} - {out.get('ci_upper')})",
                                                    color="teal",
                                                )

                        render_outcomes()

                        # Modal / Adição de novo desfecho
                        with ui.row().classes("items-center gap-2 q-mt-sm"):
                            def open_add_outcome_dialog() -> None:
                                with ui.dialog() as dlg, ui.card().classes("w-96 p-4"):
                                    ui.label("Adicionar Desfecho").classes("text-h6 font-bold q-mb-sm")
                                    o_name = ui.input(label="Nome do Desfecho (ex: Mortalidade)", value="Desfecho Primário").classes("w-full")
                                    o_type = ui.select(
                                        label="Tipo de Variável",
                                        options=["dichotomous", "continuous"],
                                        value="dichotomous",
                                    ).classes("w-full")

                                    # Dicotômico
                                    dichot_box = ui.column().classes("w-full gap-2")
                                    with dichot_box:
                                        with ui.row().classes("w-full gap-2"):
                                            n1_in = ui.number(label="N Intervenção", value=100, min=1).classes("w-36")
                                            e1_in = ui.number(label="Eventos Interv.", value=10, min=0).classes("w-36")
                                        with ui.row().classes("w-full gap-2"):
                                            n2_in = ui.number(label="N Controle", value=100, min=1).classes("w-36")
                                            e2_in = ui.number(label="Eventos Controle", value=20, min=0).classes("w-36")

                                    # Contínuo
                                    contin_box = ui.column().classes("w-full gap-2")
                                    contin_box.set_visibility(False)
                                    with contin_box:
                                        with ui.row().classes("w-full gap-2"):
                                            m1_in = ui.number(label="Média Interv.", value=110.0).classes("w-36")
                                            sd1_in = ui.number(label="DP Interv.", value=15.0, min=0.01).classes("w-36")
                                        with ui.row().classes("w-full gap-2"):
                                            m2_in = ui.number(label="Média Controle", value=120.0).classes("w-36")
                                            sd2_in = ui.number(label="DP Controle", value=15.0, min=0.01).classes("w-36")

                                    def on_type_change() -> None:
                                        is_d = o_type.value == "dichotomous"
                                        dichot_box.set_visibility(is_d)
                                        contin_box.set_visibility(not is_d)

                                    o_type.on_value_change(on_type_change)

                                    with ui.row().classes("w-full justify-end gap-2 q-mt-md"):
                                        ui.button("Cancelar", on_click=dlg.close).props("flat")
                                        def confirm_add() -> None:
                                            new_out: dict[str, Any] = {
                                                "name": o_name.value,
                                                "outcome_type": o_type.value,
                                            }
                                            if o_type.value == "dichotomous":
                                                n1 = int(n1_in.value or 0)
                                                e1 = int(e1_in.value or 0)
                                                n2 = int(n2_in.value or 0)
                                                e2 = int(e2_in.value or 0)
                                                new_out.update({
                                                    "n_intervention": n1,
                                                    "events_intervention": e1,
                                                    "n_control": n2,
                                                    "events_control": e2,
                                                })
                                                try:
                                                    or_val, ci_l, ci_u = calculate_odds_ratio(e1, n1, e2, n2)
                                                    new_out.update({
                                                        "effect_measure": "OR",
                                                        "effect_estimate": or_val,
                                                        "ci_lower": ci_l,
                                                        "ci_upper": ci_u,
                                                    })
                                                except (ValueError, TypeError, ZeroDivisionError):
                                                    pass
                                            else:
                                                m1 = float(m1_in.value or 0)
                                                sd1 = float(sd1_in.value or 1)
                                                m2 = float(m2_in.value or 0)
                                                sd2 = float(sd2_in.value or 1)
                                                new_out.update({
                                                    "mean_intervention": m1,
                                                    "sd_intervention": sd1,
                                                    "mean_control": m2,
                                                    "sd_control": sd2,
                                                })
                                                try:
                                                    md, ci_l, ci_u = calculate_mean_difference(m1, sd1, 50, m2, sd2, 50)
                                                    new_out.update({
                                                        "effect_measure": "MD",
                                                        "effect_estimate": md,
                                                        "ci_lower": ci_l,
                                                        "ci_upper": ci_u,
                                                    })
                                                except (ValueError, TypeError, ZeroDivisionError):
                                                    pass

                                            outcomes_state.append(new_out)
                                            dlg.close()
                                            render_outcomes()

                                        ui.button("Adicionar", on_click=confirm_add).props("color=primary")
                                dlg.open()

                            ui.button("+ Adicionar Desfecho", icon="add", on_click=open_add_outcome_dialog).props("outline color=primary dense")

                        ui.separator().classes("q-my-sm")
                        quote_input = ui.textarea(
                            label="Citação / Trecho Textual de Evidência",
                            value=existing.get("evidence_quote", ""),
                        ).classes("w-full").props("rows=2")

                        with ui.row().classes("w-full items-center justify-between q-mt-md"):
                            verified_chk = ui.checkbox("Verificado por humano", value=existing.get("verified_by_human", True))

                            def save_form() -> None:
                                payload = {
                                    "work_id": wid,
                                    "study_design": design_select.value,
                                    "sample_size_total": int(sample_input.value) if sample_input.value else None,
                                    "country": country_input.value,
                                    "intervention_description": interv_input.value,
                                    "control_description": ctrl_input.value,
                                    "outcomes": outcomes_state,
                                    "evidence_quote": quote_input.value,
                                    "verified_by_human": verified_chk.value,
                                }
                                try:
                                    service.save_extraction(list_id, payload)
                                    ext_map[wid] = payload
                                    ui.notify("Extração salva com sucesso!", type="positive")
                                except (RSLError, ValueError, KeyError, OSError) as err:
                                    ui.notify(f"Erro ao salvar: {err}", type="negative")

                            ui.button("Salvar Extração", icon="save", on_click=save_form).props("color=primary")

                render_form()
