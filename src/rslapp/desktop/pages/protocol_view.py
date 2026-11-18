"""Interface gráfica de Protocolos Metodológicos Pré-Busca Versionados (FR-30, D-041).

Padrão estritamente acadêmico: tema light com detalhes verdes discretos (#1B4D3E),
bordas nítidas de 1px solid #E5E7EB e cantos de 6px, alinhado aos padrões PROSPERO, OSF e PRISMA-P.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from nicegui import ui

from rslapp.core.errors import RSLError
from rslapp.core.protocols import (
    COMPONENT_LABELS,
    FRAMEWORK_COMPONENTS,
    FRAMEWORK_LABELS,
    format_protocol_markdown,
)
from rslapp.desktop.components import section_card
from rslapp.desktop.pages import render_shell
from rslapp.desktop.service import DesktopService
from rslapp.desktop.theme import apply_theme

AVAILABLE_SOURCES: tuple[str, ...] = (
    "openalex",
    "crossref",
    "semanticscholar",
    "pubmed",
    "europepmc",
    "bdtd",
    "scopus",
    "wos",
)


# FR-30, D-041: Lista e índice geral de protocolos metodológicos
def build_list(service: DesktopService) -> None:
    """Monta a tela de visualização e gestão de todos os protocolos cadastrados."""
    apply_theme()
    render_shell(
        "Protocolos",
        "Protocolos metodológicos pré-busca versionados compatíveis com PROSPERO e OSF.",
        active="Protocolos",
    )

    with ui.column().classes("w-full gap-4 max-w-5xl mx-auto"):
        protocols = service.list_protocols()

        with ui.row().classes("w-full items-center justify-between mb-2"):
            with ui.row().classes("items-center gap-2"):
                ui.label("Protocolos Metodológicos Pré-Busca").classes(
                    "text-xl font-bold rsl-title"
                )
            ui.button(
                "Novo Protocolo",
                icon="add",
                on_click=lambda: ui.navigate.to("/protocolo/novo"),
            ).props("unelevated color=primary").mark("btn-new-protocol")

        # Cartões de Resumo Métrico
        total_count = len(protocols)
        draft_count = sum(1 for p in protocols if p.get("status") == "draft")
        registered_count = sum(1 for p in protocols if p.get("status") == "registered")
        completed_count = sum(1 for p in protocols if p.get("status") == "completed")

        with ui.row().classes("w-full gap-4 mb-4"):
            with ui.card().classes("p-4 flex-1 items-center text-center rsl-surface-2"):
                ui.label(str(total_count)).classes("text-2xl font-bold rsl-title")
                ui.label("Total de Protocolos").classes("text-xs rsl-muted")
            with ui.card().classes("p-4 flex-1 items-center text-center rsl-surface-2"):
                ui.label(str(registered_count)).classes("text-2xl font-bold text-positive")
                ui.label("Registrados (PROSPERO/OSF)").classes("text-xs rsl-muted")
            with ui.card().classes("p-4 flex-1 items-center text-center rsl-surface-2"):
                ui.label(str(draft_count)).classes("text-2xl font-bold text-warning")
                ui.label("Em Elaboração (Draft)").classes("text-xs rsl-muted")
            with ui.card().classes("p-4 flex-1 items-center text-center rsl-surface-2"):
                ui.label(str(completed_count)).classes("text-2xl font-bold text-primary")
                ui.label("Concluídos").classes("text-xs rsl-muted")

        if not protocols:
            with ui.card().classes("w-full p-8 text-center items-center justify-center rsl-surface-2"):
                ui.icon("assignment", size="48px").classes("text-slate-400 mb-2")
                ui.label("Nenhum protocolo cadastrado ainda").classes("text-base font-bold rsl-title")
                ui.label(
                    "O protocolo metodológico pré-busca define formalmente os critérios de elegibilidade, "
                    "estratégias de busca e enquadramento teórico (PICO, PCC, etc.) antes da execução da revisão."
                ).classes("text-sm rsl-muted max-w-lg mb-4 text-center")
                ui.button(
                    "Criar Primeiro Protocolo",
                    icon="add",
                    on_click=lambda: ui.navigate.to("/protocolo/novo"),
                ).props("unelevated color=primary")
            return

        # Tabela de Protocolos
        table_rows = []
        for p in protocols:
            fw = p.get("framework", "pico")
            fw_label = FRAMEWORK_LABELS.get(fw, fw.upper()).split("(")[0].strip()
            table_rows.append({
                "id": p.get("id"),
                "title": p.get("title", "Sem título"),
                "framework": fw_label,
                "version": f"v{p.get('version', 1)}",
                "status": (
                    "Registrado"
                    if p.get("status") == "registered"
                    else "Concluído"
                    if p.get("status") == "completed"
                    else "Rascunho"
                ),
                "updated_at": (p.get("updated_at") or "")[:10],
            })

        columns = [
            {"name": "title", "label": "Título do Protocolo", "field": "title", "align": "left"},
            {"name": "framework", "label": "Framework", "field": "framework", "align": "center"},
            {"name": "version", "label": "Versão", "field": "version", "align": "center"},
            {"name": "status", "label": "Status", "field": "status", "align": "center"},
            {"name": "updated_at", "label": "Atualização", "field": "updated_at", "align": "center"},
            {"name": "actions", "label": "Ações", "field": "actions", "align": "right"},
        ]

        table = ui.table(columns=columns, rows=table_rows, row_key="id").classes("w-full rsl-surface-2")

        table.add_slot(
            "body-cell-framework",
            """
            <q-td :props="props">
                <q-badge color="teal-9" text-color="white" :label="props.value" />
            </q-td>
            """,
        )

        table.add_slot(
            "body-cell-status",
            """
            <q-td :props="props">
                <q-badge :color="props.value === 'Registrado' ? 'positive' : (props.value === 'Concluído' ? 'primary' : 'warning')" text-color="white" :label="props.value" />
            </q-td>
            """,
        )

        table.add_slot(
            "body-cell-actions",
            """
            <q-td :props="props">
                <q-btn flat dense round icon="edit" color="primary" @click="() => $parent.$emit('edit', props.row.id)">
                    <q-tooltip>Editar Protocolo</q-tooltip>
                </q-btn>
                <q-btn flat dense round icon="download" color="primary" @click="() => $parent.$emit('export', props.row.id)">
                    <q-tooltip>Exportar Markdown</q-tooltip>
                </q-btn>
                <q-btn flat dense round icon="delete" color="negative" @click="() => $parent.$emit('delete', props.row.id)">
                    <q-tooltip>Excluir Protocolo</q-tooltip>
                </q-btn>
            </q-td>
            """,
        )

        table.on("edit", lambda e: ui.navigate.to(f"/protocolo/{e.args}"))
        table.on("export", lambda e: _handle_export_protocol(service, e.args))
        table.on("delete", lambda e: _confirm_delete_protocol(service, e.args))


def _handle_export_protocol(service: DesktopService, protocol_id: str) -> None:
    try:
        path = service.export_protocol_markdown(protocol_id)
        ui.notify(f"Protocolo exportado: {path.name}", type="positive")
        # Dispara download no navegador
        safe_name = quote(path.name)
        ui.run_javascript(
            f'const a = document.createElement("a"); a.href = "/exports/{safe_name}"; a.download = "{safe_name}"; document.body.appendChild(a); a.click(); a.remove();'
        )
    except RSLError as err:
        ui.notify(f"Erro ao exportar: {err.message}", type="negative")


def _confirm_delete_protocol(service: DesktopService, protocol_id: str) -> None:
    with ui.dialog() as dialog, ui.card().classes("p-6 max-w-md"):
        ui.label("Excluir Protocolo").classes("text-lg font-bold rsl-title mb-2")
        ui.label(
            f"Tem certeza que deseja excluir o protocolo '{protocol_id}' e todo seu histórico de versões?"
        ).classes("text-sm rsl-muted mb-4")
        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancelar", on_click=dialog.close).props("flat")
            ui.button(
                "Excluir",
                color="negative",
                on_click=lambda: (_execute_delete(service, protocol_id), dialog.close()),
            ).props("unelevated")
    dialog.open()


def _execute_delete(service: DesktopService, protocol_id: str) -> None:
    if service.delete_protocol(protocol_id):
        ui.notify("Protocolo excluído com sucesso.", type="positive")
        ui.navigate.to("/protocolos")
    else:
        ui.notify("Erro ao excluir protocolo.", type="negative")


# FR-30, D-041: Editor e visualizador de protocolo metodológico
def build_editor(service: DesktopService, protocol_id: str | None = None) -> None:
    """Monta a página de criação ou edição detalhada do protocolo de pesquisa."""
    apply_theme()
    is_edit = protocol_id is not None
    current: dict[str, Any] = {}
    if is_edit:
        loaded = service.get_protocol(protocol_id)  # type: ignore[arg-type]
        if not loaded:
            ui.label("Protocolo não encontrado.").classes("text-negative font-bold p-8")
            return
        current = loaded

    page_title = "Editar Protocolo" if is_edit else "Novo Protocolo"
    render_shell(
        page_title,
        "Formulação rigorosa pré-busca nos frameworks PICO, PCC, PICo, SPIDER ou Narrativo.",
        active="Protocolos",
    )

    with ui.column().classes("w-full gap-6 max-w-4xl mx-auto pb-12"):
        # Barra superior com navegação
        with ui.row().classes("w-full items-center justify-between"):
            ui.button(
                "Voltar aos Protocolos",
                icon="arrow_back",
                on_click=lambda: ui.navigate.to("/protocolos"),
            ).props("flat color=primary")

            if is_edit:
                with ui.row().classes("gap-2 items-center"):
                    ui.label(f"Versão Atual: v{current.get('version', 1)}").classes(
                        "text-xs px-2 py-1 rounded bg-teal-100 text-teal-900 font-bold"
                    )

        # 1. Identificação Geral do Estudo
        with section_card("1. Identificação Geral e Registro"):
            title_input = ui.input(
                "Título da Revisão / Protocolo",
                value=current.get("title", ""),
                placeholder="Ex.: Efetividade de Agentes de IA em Revisões Sistemáticas de Saúde",
            ).props("outlined dense").classes("w-full").mark("input-protocol-title")

            with ui.row().classes("w-full gap-4"):
                authors_str = ", ".join(current.get("authors", []))
                authors_input = ui.input(
                    "Autores e Pesquisadores (separados por vírgula)",
                    value=authors_str,
                    placeholder="Ex.: Erick Mendes, Profa. Dra. Orientadora",
                ).props("outlined dense").classes("flex-1")

                status_options = {
                    "draft": "Em Elaboração (Draft)",
                    "registered": "Registrado Formalmente",
                    "completed": "Concluído",
                }
                status_select = ui.select(
                    status_options,
                    value=current.get("status", "draft"),
                    label="Status do Protocolo",
                ).props("outlined dense").classes("w-56")

            with ui.row().classes("w-full gap-4"):
                platform_input = ui.input(
                    "Plataforma de Registro",
                    value=current.get("registration_platform", ""),
                    placeholder="Ex.: PROSPERO, OSF, JBI, Inquérito Institucional",
                ).props("outlined dense").classes("flex-1")

                number_input = ui.input(
                    "Número / Identificador / DOI do Registro",
                    value=current.get("registration_number", ""),
                    placeholder="Ex.: CRD42026123456 ou 10.17605/OSF.IO/XXXXX",
                ).props("outlined dense").classes("flex-1")

        # 2. Enquadramento Teórico e Pergunta de Pesquisa
        with section_card("2. Pergunta de Pesquisa e Framework Metodológico"):
            framework_select = ui.select(
                FRAMEWORK_LABELS,
                value=current.get("framework", "pico"),
                label="Framework Metodológico",
            ).props("outlined dense").classes("w-full mb-2").mark("select-protocol-framework")

            question_input = ui.textarea(
                "Pergunta Principal de Pesquisa",
                value=current.get("question", ""),
                placeholder="Formule a pergunta norteadora baseada no framework selecionado...",
            ).props("outlined").classes("w-full").mark("input-protocol-question")

            subq_str = "\n".join(current.get("subquestions", []))
            subq_input = ui.textarea(
                "Perguntas Secundárias / Específicas (uma por linha)",
                value=subq_str,
                placeholder="1. Qual a acurácia diagnóstica observada?\n2. Há redução no tempo de triagem?",
            ).props("outlined").classes("w-full")

            # Componentes dinâmicos do framework selecionado
            ui.label("Componentes Específicos do Framework").classes("text-sm font-bold rsl-title mt-2")
            comp_container = ui.column().classes("w-full gap-3")
            comp_inputs: dict[str, Any] = {}

            def _render_components(fw_key: str) -> None:
                comp_container.clear()
                comp_inputs.clear()
                comps = FRAMEWORK_COMPONENTS.get(fw_key, [])
                saved_comps = current.get("components", {})
                with comp_container:
                    for c_key in comps:
                        c_label = COMPONENT_LABELS.get(c_key, c_key.capitalize())
                        val = saved_comps.get(c_key, "")
                        inp = ui.input(c_label, value=val).props("outlined dense").classes("w-full")
                        comp_inputs[c_key] = inp

            _render_components(framework_select.value)
            framework_select.on_value_change(lambda e: _render_components(e.value))

        # 3. Critérios Formais de Elegibilidade
        with section_card("3. Critérios Formais de Elegibilidade (Inclusão e Exclusão)"):
            inc_str = "\n".join(current.get("inclusion_criteria", []))
            inc_input = ui.textarea(
                "Critérios de Inclusão (um por linha)",
                value=inc_str,
                placeholder="Ensaios clínicos randomizados\nArtigos publicados entre 2018 e 2026\nAmostra composta por estudantes universitários",
            ).props("outlined").classes("w-full mb-2").mark("input-protocol-inclusion")

            exc_str = "\n".join(current.get("exclusion_criteria", []))
            exc_input = ui.textarea(
                "Critérios de Exclusão (um por linha)",
                value=exc_str,
                placeholder="Editoriais, pareceres e cartas ao editor\nEstudos sem grupo controle\nTextos não disponíveis na íntegra",
            ).props("outlined").classes("w-full").mark("input-protocol-exclusion")

        # 4. Estratégia de Busca e Fontes Planejadas
        with section_card("4. Estratégia de Busca e Fontes Planejadas"):
            ui.label("Bases de Dados Acadêmicas Previstas").classes("text-xs font-bold rsl-muted")
            saved_sources = set(current.get("planned_sources", ["openalex", "crossref", "semanticscholar"]))
            source_checkboxes: dict[str, Any] = {}
            with ui.row().classes("w-full gap-4 flex-wrap mb-2"):
                for src in AVAILABLE_SOURCES:
                    cb = ui.checkbox(src.upper(), value=(src in saved_sources))
                    source_checkboxes[src] = cb

            strategy_input = ui.textarea(
                "Sintaxe Booleana Planejada / Termos de Busca",
                value=current.get("search_strategy", ""),
                placeholder="Ex.: ('artificial intelligence' OR 'machine learning' OR 'LLM') AND ('systematic review' OR 'literature review')",
            ).props("outlined").classes("w-full")

            with ui.row().classes("w-full gap-4"):
                langs_str = ", ".join(current.get("languages", ["pt", "en"]))
                langs_input = ui.input(
                    "Idiomas Abrangidos (separados por vírgula)",
                    value=langs_str,
                    placeholder="pt, en, es",
                ).props("outlined dense").classes("flex-1")

                dr = current.get("date_range", {})
                start_year = ui.number(
                    "Ano Inicial",
                    value=dr.get("start_year"),
                    format="%d",
                ).props("outlined dense").classes("w-32")
                end_year = ui.number(
                    "Ano Final",
                    value=dr.get("end_year"),
                    format="%d",
                ).props("outlined dense").classes("w-32")

        # 5. Rastreabilidade Ética de IA
        with section_card("5. Rastreabilidade Ética e Apoio de IA (COPE/ICMJE)"):
            ai_assisted_cb = ui.checkbox(
                "Este protocolo metodológico foi formulado com auxílio de Inteligência Artificial",
                value=current.get("ai_assisted", False),
            ).mark("cb-protocol-ai")

            ai_model_input = ui.input(
                "Modelo de Inteligência Artificial Utilizado",
                value=current.get("ai_model", "Claude 3.5 Sonnet"),
                placeholder="Ex.: Claude 3.5 Sonnet, Gemini 1.5 Pro, GPT-4o",
            ).props("outlined dense").classes("w-full")

        # Barra Fixa / Inferior de Gravação e Exportação
        with ui.row().classes("w-full justify-between items-center pt-4"):
            with ui.row().classes("gap-2"):
                ui.button(
                    "Copiar Markdown (PROSPERO/OSF)",
                    icon="content_copy",
                    on_click=lambda: _copy_protocol_markdown(
                        _build_protocol_dict(
                            current,
                            title_input,
                            authors_input,
                            framework_select,
                            status_select,
                            platform_input,
                            number_input,
                            question_input,
                            subq_input,
                            comp_inputs,
                            inc_input,
                            exc_input,
                            source_checkboxes,
                            strategy_input,
                            langs_input,
                            start_year,
                            end_year,
                            ai_assisted_cb,
                            ai_model_input,
                        )
                    ),
                ).props("outline color=primary").mark("btn-copy-protocol-md")

            ui.button(
                "Salvar Protocolo",
                icon="save",
                on_click=lambda: _handle_save(
                    service,
                    current,
                    title_input,
                    authors_input,
                    framework_select,
                    status_select,
                    platform_input,
                    number_input,
                    question_input,
                    subq_input,
                    comp_inputs,
                    inc_input,
                    exc_input,
                    source_checkboxes,
                    strategy_input,
                    langs_input,
                    start_year,
                    end_year,
                    ai_assisted_cb,
                    ai_model_input,
                ),
            ).props("unelevated color=primary").classes("px-6").mark("btn-save-protocol")


def _build_protocol_dict(
    current: dict[str, Any],
    title_inp: Any,
    authors_inp: Any,
    fw_sel: Any,
    status_sel: Any,
    plat_inp: Any,
    num_inp: Any,
    quest_inp: Any,
    subq_inp: Any,
    comp_inps: dict[str, Any],
    inc_inp: Any,
    exc_inp: Any,
    sources_cbs: dict[str, Any],
    strat_inp: Any,
    langs_inp: Any,
    start_y: Any,
    end_y: Any,
    ai_cb: Any,
    ai_model_inp: Any,
) -> dict[str, Any]:
    authors = [a.strip() for a in str(authors_inp.value).split(",") if a.strip()]
    subqs = [s.strip() for s in str(subq_inp.value).splitlines() if s.strip()]
    incs = [i.strip() for i in str(inc_inp.value).splitlines() if i.strip()]
    excs = [e.strip() for e in str(exc_inp.value).splitlines() if e.strip()]
    sources = [s for s, cb in sources_cbs.items() if cb.value]
    langs = [l.strip() for l in str(langs_inp.value).split(",") if l.strip()]
    components = {k: str(inp.value).strip() for k, inp in comp_inps.items() if inp.value}

    date_range = {
        "start_year": int(start_y.value) if start_y.value else None,
        "end_year": int(end_y.value) if end_y.value else None,
    }

    data: dict[str, Any] = {
        "title": str(title_inp.value).strip(),
        "authors": authors,
        "framework": str(fw_sel.value).strip(),
        "status": str(status_sel.value).strip(),
        "registration_platform": str(plat_inp.value).strip() or None,
        "registration_number": str(num_inp.value).strip() or None,
        "question": str(quest_inp.value).strip(),
        "subquestions": subqs,
        "components": components,
        "inclusion_criteria": incs,
        "exclusion_criteria": excs,
        "planned_sources": sources,
        "search_strategy": str(strat_inp.value).strip(),
        "languages": langs,
        "date_range": date_range,
        "ai_assisted": bool(ai_cb.value),
        "ai_model": str(ai_model_inp.value).strip() if ai_cb.value else None,
    }
    if current.get("id"):
        data["id"] = current["id"]
        data["version"] = current.get("version", 1)

    return data


def _copy_protocol_markdown(proto_data: dict[str, Any]) -> None:
    try:
        md = format_protocol_markdown(proto_data)
        safe_js = md.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        ui.run_javascript(f'navigator.clipboard.writeText(`{safe_js}`);')
        ui.notify("Markdown copiado para a área de transferência!", type="positive")
    except Exception as err:  # noqa: BLE001
        ui.notify(f"Erro ao formatar markdown: {err}", type="negative")


def _handle_save(
    service: DesktopService,
    current: dict[str, Any],
    title_inp: Any,
    authors_inp: Any,
    fw_sel: Any,
    status_sel: Any,
    plat_inp: Any,
    num_inp: Any,
    quest_inp: Any,
    subq_inp: Any,
    comp_inps: dict[str, Any],
    inc_inp: Any,
    exc_inp: Any,
    sources_cbs: dict[str, Any],
    strat_inp: Any,
    langs_inp: Any,
    start_y: Any,
    end_y: Any,
    ai_cb: Any,
    ai_model_inp: Any,
) -> None:
    proto_data = _build_protocol_dict(
        current,
        title_inp,
        authors_inp,
        fw_sel,
        status_sel,
        plat_inp,
        num_inp,
        quest_inp,
        subq_inp,
        comp_inps,
        inc_inp,
        exc_inp,
        sources_cbs,
        strat_inp,
        langs_inp,
        start_y,
        end_y,
        ai_cb,
        ai_model_inp,
    )

    if not proto_data["title"]:
        ui.notify("O título do protocolo é obrigatório.", type="warning")
        return

    if not proto_data["question"]:
        ui.notify("A pergunta de pesquisa é obrigatória.", type="warning")
        return

    try:
        saved = service.save_protocol(proto_data)
        v = saved.get("version", 1)
        ui.notify(f"Protocolo salvo com sucesso! Versão v{v}.", type="positive")
        ui.navigate.to(f"/protocolo/{saved['id']}")
    except RSLError as err:
        ui.notify(f"Erro ao salvar: {err.message}", type="negative")
