"""Tela de Avaliação de Risco de Viés e Qualidade Metodológica (RoB 2, ROBINS-I, JBI) (FR-36, D-047, FR-38)."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from rslapp.core.errors import RSLError
from rslapp.core.risk_of_bias import (
    JBI_QUESTIONS,
    ROB2_DOMAINS,
    ROBINS_I_DOMAINS,
    DomainAssessment,
    RiskOfBiasAssessment,
    compute_overall_rob2,
    compute_overall_robins_i,
)
from rslapp.desktop.pages import render_shell
from rslapp.desktop.service import DesktopService


def build(service: DesktopService, list_id: str) -> None:
    """Constrói a tela de avaliação de risco de viés e matriz de semáforo."""
    render_shell(f"Risco de Viés · {list_id}", "Avaliação sistemática com RoB 2, ROBINS-I e JBI", active="Buscar")
    with ui.column().classes("w-full gap-4"):
        try:
            list_data = service.get_list(list_id)
        except (RSLError, ValueError, KeyError, OSError) as e:
            ui.label(f"Erro ao carregar lista: {e}").classes("text-negative font-bold")
            return

        works = list_data.get("works", [])
        rob_list = service.list_risk_of_bias(list_id)
        rob_map = {str(r.get("work_id")): r for r in rob_list}

        # Cabeçalho
        with ui.row().classes("w-full items-center justify-between q-mb-md"), ui.row().classes("items-center gap-2"):
            ui.button(
                icon="arrow_back",
                on_click=lambda: ui.navigate.to(f"/lista/{list_id}"),
            ).props("flat round dense")
            ui.label(f"Risco de Viés / Qualidade ({len(rob_list)}/{len(works)} avaliados)").classes("text-h6 font-bold")

        if not works:
            ui.label("Esta lista não possui artigos.").classes("text-grey")
            return

        with ui.splitter(value=30).classes("w-full h-full border rounded") as splitter:
            # Esquerda: Lista de Estudos
            with splitter.before, ui.column().classes("w-full p-2 gap-2"):
                ui.label("Selecione um artigo:").classes("text-subtitle2 font-bold q-mb-xs")
                active_work_id = {"val": str(works[0].get("id") or 0)}

                def on_select_work(wid: str) -> None:
                    active_work_id["val"] = wid
                    render_bias_form()

                for idx, w in enumerate(works):
                    wid = str(w.get("id") or idx)
                    title = w.get("title") or f"Artigo {idx + 1}"
                    existing_rob = rob_map.get(wid)
                    is_active = active_work_id["val"] == wid

                    with ui.card().classes(
                        f"w-full cursor-pointer p-2 {'bg-blue-50 border-primary' if is_active else 'bg-white'}"
                    ).on("click", lambda _, target_id=wid: on_select_work(target_id)), ui.row().classes("items-center justify-between no-wrap"):
                        ui.label(f"#{idx + 1} {title[:50]}...").classes("text-caption font-bold ellipsis")
                        if existing_rob:
                            ov = existing_rob.get("overall_judgment", "low")
                            color = "positive" if ov == "low" else ("warning" if ov in ("some_concerns", "moderate") else "negative")
                            ui.badge(ov.upper(), color=color).props("dense")
                        else:
                            ui.badge("Pendente", color="grey").props("dense")

            # Direita: Formulário do Instrumento
            with splitter.after:
                form_box = ui.column().classes("w-full p-4 gap-3")

                def render_bias_form() -> None:
                    form_box.clear()
                    wid = active_work_id["val"]
                    existing = service.get_risk_of_bias(list_id, wid) or {}

                    w_obj = next((w for w in works if str(w.get("id") or "") == wid), None)
                    w_title = w_obj.get("title") if w_obj else f"Artigo {wid}"

                    with form_box:
                        ui.label(w_title).classes("text-subtitle1 font-bold text-primary")

                        tool_select = ui.select(
                            label="Instrumento de Avaliação",
                            options={"rob2": "Cochrane RoB 2 (Ensaios Clínicos)", "robins_i": "Cochrane ROBINS-I (Não-randomizados)", "jbi": "JBI Critical Appraisal"},
                            value=existing.get("tool", "rob2"),
                        ).classes("w-72")

                        domains_container = ui.column().classes("w-full gap-3 q-mt-sm")

                        def render_domains() -> None:
                            domains_container.clear()
                            tool_name = tool_select.value
                            domains_def = ROB2_DOMAINS if tool_name == "rob2" else (ROBINS_I_DOMAINS if tool_name == "robins_i" else JBI_QUESTIONS)

                            existing_domains = {d.get("domain_id"): d for d in existing.get("domains", [])}
                            domain_inputs: list[tuple[str, str, Any, Any]] = []

                            with domains_container:
                                for d in domains_def:
                                    d_id = d["id"]
                                    d_name = d["name"]
                                    d_val = existing_domains.get(d_id, {}).get("judgment")
                                    if not d_val:
                                        d_val = "low" if tool_name in ("rob2", "robins_i") else "yes"

                                    with ui.card().classes("w-full p-3 bg-grey-1 border"):
                                        ui.label(f"{d_id}: {d_name}").classes("font-bold text-subtitle2")
                                        with ui.row().classes("w-full gap-4 items-center q-my-xs"):
                                            if tool_name == "rob2":
                                                j_select = ui.select(
                                                    options={"low": "Baixo Risco (Low)", "some_concerns": "Alguma Preocupação (Some concerns)", "high": "Alto Risco (High)"},
                                                    value=d_val,
                                                ).classes("w-64")
                                            elif tool_name == "robins_i":
                                                j_select = ui.select(
                                                    options={"low": "Baixo", "moderate": "Moderado", "serious": "Sério", "critical": "Crítico"},
                                                    value=d_val,
                                                ).classes("w-64")
                                            else:
                                                j_select = ui.select(
                                                    options={"yes": "Sim (Adequado)", "no": "Não (Inadequado)", "unclear": "Não Claro", "not_applicable": "N/A"},
                                                    value=d_val,
                                                ).classes("w-64")

                                            q_input = ui.input(
                                                label="Trecho / Evidência no texto",
                                                value=existing_domains.get(d_id, {}).get("quote", ""),
                                            ).classes("flex-1")

                                        r_input = ui.input(
                                            label="Justificativa analítica",
                                            value=existing_domains.get(d_id, {}).get("rationale", ""),
                                        ).classes("w-full")

                                        domain_inputs.append((d_id, d_name, j_select, r_input, q_input))

                                # Botão de salvar
                                with ui.row().classes("w-full justify-between items-center q-mt-md"):
                                    verified_chk = ui.checkbox("Verificado por humano", value=existing.get("verified_by_human", True))

                                    def save_assessment() -> None:
                                        domain_objs: list[DomainAssessment] = []
                                        for d_id, d_name, j_sel, r_in, q_in in domain_inputs:
                                            domain_objs.append(DomainAssessment(
                                                domain_id=d_id,
                                                domain_name=d_name,
                                                judgment=j_sel.value,
                                                rationale=r_in.value,
                                                quote=q_in.value,
                                            ))

                                        if tool_select.value == "rob2":
                                            ov = compute_overall_rob2(domain_objs)
                                        elif tool_select.value == "robins_i":
                                            ov = compute_overall_robins_i(domain_objs)
                                        else:
                                            ov = "low"

                                        ass = RiskOfBiasAssessment(
                                            work_id=wid,
                                            tool=tool_select.value,
                                            domains=domain_objs,
                                            overall_judgment=ov,
                                            verified_by_human=verified_chk.value,
                                        )
                                        service.save_risk_of_bias(list_id, ass.to_dict())
                                        rob_map[wid] = ass.to_dict()
                                        ui.notify(f"Avaliação salva! Julgamento Geral: {ov.upper()}", type="positive")

                                    ui.button("Salvar Avaliação", icon="save", on_click=save_assessment).props("color=primary")

                        tool_select.on_value_change(render_domains)
                        render_domains()

                render_bias_form()

        # Matriz de Semáforo no rodapé
        ui.separator().classes("q-my-lg")
        ui.label("Matriz de Semáforo (Traffic-Light Plot)").classes("text-h6 font-bold q-mb-sm")
        matrix_data = service.get_risk_of_bias_matrix(list_id)
        if matrix_data.get("rows"):
            with ui.row().classes("w-full gap-2 overflow-x-auto"):
                for row in matrix_data["rows"]:
                    with ui.card().classes("p-3 border items-center"):
                        ui.label(row.get("study_label", "")).classes("font-bold text-caption")
                        with ui.row().classes("gap-1 q-my-xs"):
                            for d_id, d_val in row.get("domains", {}).items():
                                col = "positive" if d_val in ("low", "yes") else ("warning" if d_val in ("some_concerns", "moderate", "unclear") else "negative")
                                ui.badge(d_id, color=col).props("dense")
                        ov = row.get("overall", "low")
                        ov_col = "positive" if ov == "low" else ("warning" if ov in ("some_concerns", "moderate") else "negative")
                        ui.badge(f"Geral: {ov.upper()}", color=ov_col)
        else:
            ui.label("Nenhum estudo avaliado para exibição do semáforo.").classes("text-caption text-grey")
