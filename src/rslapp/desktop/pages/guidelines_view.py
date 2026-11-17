"""Tela de Roteiros Metodológicos para Revisões Acadêmicas no app desktop (FR-10, D-031, D-035)."""

from __future__ import annotations

import urllib.parse

from nicegui import ui

from rslapp.desktop.components import section_card
from rslapp.desktop.pages import render_shell
from rslapp.desktop.service import DesktopService
from rslapp.desktop.theme import apply_theme
from rslapp.prompts import (
    render_plan_bibliometric_study,
    render_plan_integrative_review,
    render_plan_scoping_review,
    render_plan_systematic_review,
)


def _copy_to_clipboard(text: str) -> None:
    """Copia texto para a área de transferência do usuário com notificação."""
    ui.clipboard.write(text)
    ui.notify("Roteiro copiado para a área de transferência!", type="positive")


def _navigate_to_search(query: str) -> None:
    """Navega para a página de busca com a string sugerida preenchida."""
    encoded = urllib.parse.quote_plus(query.strip())
    ui.navigate.to(f"/?q={encoded}")


# FR-10, D-031, D-035: Construtor da tela de roteiros metodológicos
def build(service: DesktopService, initial_type: str = "escopo") -> None:
    """Monta a tela de Roteiros Metodológicos do RSL.app."""
    apply_theme()
    render_shell(
        "Roteiros",
        "Roteiros e protocolos metodológicos para planejamento de revisões e estudos bibliométricos.",
    )

    with ui.column().classes("w-full gap-5"):
        # Cartão introdutório
        with section_card("Metodologia Científica e Rigor Acadêmico", icon="school"):
            ui.label(
                "Planeje sua revisão seguindo os métodos consolidados na academia brasileira e internacional. "
                "Preencha os parâmetros abaixo para gerar o roteiro metodológico detalhado, copiar o prompt para sua "
                "IA ou iniciar a coleta diretamente no RSL.app."
            ).classes("text-sm rsl-muted leading-relaxed")

        # Seleção de Abas por Tipo de Revisão
        with ui.tabs().classes("w-full border-b border-grey-4") as tabs:
            tab_scoping = ui.tab("Revisão de Escopo (PCC)", icon="explore").mark("tab-scoping")
            tab_integrative = ui.tab("Revisão Integrativa (6 Fases)", icon="layers").mark(
                "tab-integrative"
            )
            tab_systematic = ui.tab("Revisão Sistemática (PICO)", icon="verified").mark(
                "tab-systematic"
            )
            tab_bibliometric = ui.tab(
                "Estudo Bibliométrico (VOSviewer)", icon="bubble_chart"
            ).mark("tab-bibliometric")

        with ui.tab_panels(tabs, value=tab_scoping).classes("w-full bg-transparent p-0"):
            # -------------------------------------------------------------
            # 1. REVISÃO DE ESCOPO (JBI / PRISMA-ScR / PCC)
            # -------------------------------------------------------------
            with ui.tab_panel(tab_scoping).classes("p-0 pt-4 flex flex-col gap-4"):
                with section_card("Fundamento: JBI e PRISMA-ScR", icon="info"):
                    ui.label(
                        "A Revisão de Escopo (Scoping Review) mapeia a literatura existente, identifica lacunas "
                        "de pesquisa e clarifica conceitos-chave. Utiliza o mnemônico PCC (População, Conceito e Contexto) "
                        "e recomenda enfaticamente a inclusão de literatura cinzenta (como teses e dissertações na BDTD)."
                    ).classes("text-sm rsl-muted")

                with (
                    section_card("Parâmetros do Estudo de Escopo", icon="tune"),
                    ui.column().classes("w-full gap-3"),
                ):
                    sc_topic = (
                        ui.input("Tema / Pergunta de pesquisa")
                        .classes("w-full")
                        .mark("scoping-topic")
                    )
                    with ui.row().classes("w-full gap-3"):
                        sc_pop = (
                            ui.input("População (P)", placeholder="Ex.: pesquisadores, docentes")
                            .classes("flex-1")
                            .mark("scoping-population")
                        )
                        sc_con = (
                            ui.input(
                                "Conceito (C)",
                                placeholder="Ex.: inteligência artificial, revisão de literatura",
                            )
                            .classes("flex-1")
                            .mark("scoping-concept")
                        )
                        sc_ctx = (
                            ui.input(
                                "Contexto (C)",
                                placeholder="Ex.: ensino superior, pós-graduação no Brasil",
                            )
                            .classes("flex-1")
                            .mark("scoping-context")
                        )

                with section_card("Roteiro Metodológico Gerado", icon="description"):
                    sc_output = (
                        ui.textarea()
                        .props("rows=12 readonly")
                        .classes("w-full font-mono text-xs")
                        .mark("scoping-output")
                    )

                    def update_scoping() -> None:
                        topic = sc_topic.value.strip() if isinstance(sc_topic.value, str) else ""
                        pop = sc_pop.value.strip() if isinstance(sc_pop.value, str) else ""
                        con = sc_con.value.strip() if isinstance(sc_con.value, str) else ""
                        ctx = sc_ctx.value.strip() if isinstance(sc_ctx.value, str) else ""
                        sc_output.value = render_plan_scoping_review(
                            topic=topic,
                            population=pop,
                            concept=con,
                            context=ctx,
                        )

                    update_scoping()
                    sc_topic.on_value_change(update_scoping)
                    sc_pop.on_value_change(update_scoping)
                    sc_con.on_value_change(update_scoping)
                    sc_ctx.on_value_change(update_scoping)

                    with ui.row().classes("w-full justify-end gap-3 mt-2"):
                        ui.button(
                            "Copiar Roteiro",
                            icon="content_copy",
                            on_click=lambda: _copy_to_clipboard(sc_output.value),
                        ).props("outline").mark("scoping-copy-btn")
                        ui.button(
                            "Buscar no RSL.app",
                            icon="search",
                            on_click=lambda: _navigate_to_search(sc_topic.value or sc_con.value),
                        ).props("color=primary").mark("scoping-search-btn")

            # -------------------------------------------------------------
            # 2. REVISÃO INTEGRATIVA (Whittemore & Knafl / Mendes, Silveira e Galvão)
            # -------------------------------------------------------------
            with ui.tab_panel(tab_integrative).classes("p-0 pt-4 flex flex-col gap-4"):
                with section_card(
                    "Fundamento: 6 Fases Metodológicas (Whittemore & Knafl / Mendes et al.)",
                    icon="info",
                ):
                    ui.label(
                        "Método amplamente exigido na pós-graduação e na área de saúde no Brasil. "
                        "Permite integrar estudos com diferentes abordagens metodológicas (quantitativas, qualitativas "
                        "e teóricas) em 6 etapas: 1. Identificação do tema; 2. Amostragem e busca; 3. Categorização; "
                        "4. Avaliação crítica; 5. Discussão dos resultados; 6. Apresentação da síntese."
                    ).classes("text-sm rsl-muted")

                with (
                    section_card("Parâmetros da Revisão Integrativa", icon="tune"),
                    ui.column().classes("w-full gap-3"),
                ):
                    it_topic = (
                        ui.input("Tema de pesquisa")
                        .classes("w-full")
                        .mark("integrative-topic")
                    )
                    it_question = (
                        ui.input(
                            "Questão Norteadora",
                            placeholder="Qual a pergunta central que norteia a síntese do conhecimento?",
                        )
                        .classes("w-full")
                        .mark("integrative-question")
                    )
                    it_framework = (
                        ui.input(
                            "Referencial Teórico ou Hipótese",
                            placeholder="Objetivo geral, hipótese ou modelo teórico orientador",
                        )
                        .classes("w-full")
                        .mark("integrative-framework")
                    )

                with section_card("Roteiro Metodológico Gerado", icon="description"):
                    it_output = (
                        ui.textarea()
                        .props("rows=12 readonly")
                        .classes("w-full font-mono text-xs")
                        .mark("integrative-output")
                    )

                    def update_integrative() -> None:
                        topic = it_topic.value.strip() if isinstance(it_topic.value, str) else ""
                        q = it_question.value.strip() if isinstance(it_question.value, str) else ""
                        fw = (
                            it_framework.value.strip()
                            if isinstance(it_framework.value, str)
                            else ""
                        )
                        it_output.value = render_plan_integrative_review(
                            topic=topic,
                            guiding_question=q,
                            theoretical_framework=fw,
                        )

                    update_integrative()
                    it_topic.on_value_change(update_integrative)
                    it_question.on_value_change(update_integrative)
                    it_framework.on_value_change(update_integrative)

                    with ui.row().classes("w-full justify-end gap-3 mt-2"):
                        ui.button(
                            "Copiar Roteiro",
                            icon="content_copy",
                            on_click=lambda: _copy_to_clipboard(it_output.value),
                        ).props("outline").mark("integrative-copy-btn")
                        ui.button(
                            "Buscar no RSL.app",
                            icon="search",
                            on_click=lambda: _navigate_to_search(
                                it_topic.value or it_question.value
                            ),
                        ).props("color=primary").mark("integrative-search-btn")

            # -------------------------------------------------------------
            # 3. REVISÃO SISTEMÁTICA (Cochrane / PRISMA 2020 / PICO)
            # -------------------------------------------------------------
            with ui.tab_panel(tab_systematic).classes("p-0 pt-4 flex flex-col gap-4"):
                with section_card("Fundamento: Cochrane e PRISMA 2020", icon="info"):
                    ui.label(
                        "Padrão ouro para sintetizar evidências empíricas sobre intervenções ou fenômenos com rigor máximo. "
                        "Usa a estratégia PICO (População, Intervenção, Comparação e Desfecho), com dupla triagem independente, "
                        "avaliação rigorosa do risco de viés e transparência pelo fluxograma PRISMA."
                    ).classes("text-sm rsl-muted")

                with (
                    section_card("Parâmetros PICO da Revisão Sistemática", icon="tune"),
                    ui.column().classes("w-full gap-3"),
                ):
                    sy_topic = (
                        ui.input("Tema / Pergunta Geral")
                        .classes("w-full")
                        .mark("systematic-topic")
                    )
                    with ui.row().classes("w-full gap-3"):
                        sy_p = (
                            ui.input("População / Pacientes (P)", placeholder="População-alvo")
                            .classes("flex-1")
                            .mark("systematic-p")
                        )
                        sy_i = (
                            ui.input(
                                "Intervenção (I)",
                                placeholder="Intervenção ou exposição principal",
                            )
                            .classes("flex-1")
                            .mark("systematic-i")
                        )
                    with ui.row().classes("w-full gap-3"):
                        sy_c = (
                            ui.input("Comparação (C)", placeholder="Controle, placebo ou padrão")
                            .classes("flex-1")
                            .mark("systematic-c")
                        )
                        sy_o = (
                            ui.input(
                                "Desfecho / Outcome (O)",
                                placeholder="Resultados clínicos ou acadêmicos",
                            )
                            .classes("flex-1")
                            .mark("systematic-o")
                        )

                with section_card("Roteiro Metodológico Gerado", icon="description"):
                    sy_output = (
                        ui.textarea()
                        .props("rows=12 readonly")
                        .classes("w-full font-mono text-xs")
                        .mark("systematic-output")
                    )

                    def update_systematic() -> None:
                        topic = sy_topic.value.strip() if isinstance(sy_topic.value, str) else ""
                        p = sy_p.value.strip() if isinstance(sy_p.value, str) else ""
                        i = sy_i.value.strip() if isinstance(sy_i.value, str) else ""
                        c = sy_c.value.strip() if isinstance(sy_c.value, str) else ""
                        o = sy_o.value.strip() if isinstance(sy_o.value, str) else ""
                        sy_output.value = render_plan_systematic_review(
                            topic=topic,
                            population=p,
                            intervention=i,
                            comparison=c,
                            outcome=o,
                        )

                    update_systematic()
                    sy_topic.on_value_change(update_systematic)
                    sy_p.on_value_change(update_systematic)
                    sy_i.on_value_change(update_systematic)
                    sy_c.on_value_change(update_systematic)
                    sy_o.on_value_change(update_systematic)

                    with ui.row().classes("w-full justify-end gap-3 mt-2"):
                        ui.button(
                            "Copiar Roteiro",
                            icon="content_copy",
                            on_click=lambda: _copy_to_clipboard(sy_output.value),
                        ).props("outline").mark("systematic-copy-btn")
                        ui.button(
                            "Buscar no RSL.app",
                            icon="search",
                            on_click=lambda: _navigate_to_search(
                                sy_topic.value or f"{sy_p.value} {sy_i.value}"
                            ),
                        ).props("color=primary").mark("systematic-search-btn")

            # -------------------------------------------------------------
            # 4. ESTUDO BIBLIOMÉTRICO (VOSviewer / Leis de Bradford, Lotka, Zipf)
            # -------------------------------------------------------------
            with ui.tab_panel(tab_bibliometric).classes("p-0 pt-4 flex flex-col gap-4"):
                with section_card("Fundamento: VOSviewer e Leis Bibliométricas", icon="info"):
                    ui.label(
                        "Mapeamento científico estruturado para exportação direta ao VOSviewer. "
                        "Abrange as três leis clássicas da bibliometria: Lei de Bradford (zonas de dispersão e periódicos "
                        "do núcleo), Lei de Lotka (produtividade científica dos autores) e Lei de Zipf (frequência de termos e vocabulário)."
                    ).classes("text-sm rsl-muted")

                with (
                    section_card("Parâmetros do Estudo Bibliométrico", icon="tune"),
                    ui.column().classes("w-full gap-3"),
                ):
                    bb_topic = (
                        ui.input("Tema do Mapeamento Bibliométrico")
                        .classes("w-full")
                        .mark("bibliometric-topic")
                    )
                    bb_analysis = (
                        ui.select(
                            label="Tipo de Análise",
                            options=["all", "co-authorship", "co-occurrence", "citation", "bibliographic-coupling", "co-citation"],
                            value="all",
                        )
                        .classes("w-full")
                        .mark("bibliometric-analysis")
                    )

                with section_card("Roteiro Metodológico Gerado", icon="description"):
                    bb_output = (
                        ui.textarea()
                        .props("rows=12 readonly")
                        .classes("w-full font-mono text-xs")
                        .mark("bibliometric-output")
                    )

                    def update_bibliometric() -> None:
                        topic = bb_topic.value.strip() if isinstance(bb_topic.value, str) else ""
                        an = (
                            bb_analysis.value.strip()
                            if isinstance(bb_analysis.value, str)
                            else "all"
                        )
                        bb_output.value = render_plan_bibliometric_study(
                            topic=topic,
                            analysis_type=an,
                        )

                    update_bibliometric()
                    bb_topic.on_value_change(update_bibliometric)
                    bb_analysis.on_value_change(update_bibliometric)

                    with ui.row().classes("w-full justify-end gap-3 mt-2"):
                        ui.button(
                            "Copiar Roteiro",
                            icon="content_copy",
                            on_click=lambda: _copy_to_clipboard(bb_output.value),
                        ).props("outline").mark("bibliometric-copy-btn")
                        ui.button(
                            "Buscar no RSL.app",
                            icon="search",
                            on_click=lambda: _navigate_to_search(bb_topic.value),
                        ).props("color=primary").mark("bibliometric-search-btn")
