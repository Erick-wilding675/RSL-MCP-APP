"""Geração de declaração ética de uso de inteligência artificial em metodologia (FR-27, D-038)."""

from __future__ import annotations

from typing import Any

from rslapp import __version__


# FR-27, D-038: Geração de declaração metodológica formal de uso de IA (padrão COPE/ICMJE/SciELO)
def render_ai_disclosure(
    list_id: str,
    search_query: str,
    total_works: int,
    screening_summary: dict[str, Any],
    lang: str = "pt",
) -> str:
    """Gera texto de transparência metodológica sobre uso de ferramentas de IA na pesquisa.

    Suporta idiomas 'pt' (Português - SciELO/ABNT) e 'en' (Inglês - COPE/ICMJE).
    """
    clean_lang = str(lang).strip().lower()
    by_author = screening_summary.get("by_author", {})
    human_count = by_author.get("human", 0)
    ai_count = by_author.get("ai", 0)
    screened_count = screening_summary.get("screened", 0)
    included_count = screening_summary.get("included", 0)
    excluded_count = screening_summary.get("excluded", 0)

    if clean_lang == "en":
        return _render_disclosure_en(
            list_id=list_id,
            search_query=search_query,
            total_works=total_works,
            screened_count=screened_count,
            human_count=human_count,
            ai_count=ai_count,
            included_count=included_count,
            excluded_count=excluded_count,
        )

    return _render_disclosure_pt(
        list_id=list_id,
        search_query=search_query,
        total_works=total_works,
        screened_count=screened_count,
        human_count=human_count,
        ai_count=ai_count,
        included_count=included_count,
        excluded_count=excluded_count,
    )


def _render_disclosure_pt(
    list_id: str,
    search_query: str,
    total_works: int,
    screened_count: int,
    human_count: int,
    ai_count: int,
    included_count: int,
    excluded_count: int,
) -> str:
    ai_screening_part = (
        f"Na fase de seleção e triagem, {ai_count} trabalhos contaram com pré-classificação assistida por inteligência artificial "
        f"e {human_count} decisões foram registradas diretamente por pesquisadores humanos."
        if ai_count > 0
        else "Todas as decisões de triagem foram executadas e verificadas integralmente por pesquisadores humanos."
    )

    return f"""### Declaração de Uso de Inteligência Artificial e Transparência Metodológica

Em conformidade com as diretrizes do **Committee on Publication Ethics (COPE)**, do **International Committee of Medical Journal Editors (ICMJE)** e do **Guia de Boas Práticas do SciELO Brasil** sobre integridade científica e uso de ferramentas de inteligência artificial generativa na pesquisa:

1. **Ferramental e Protocolo Automatizado:**
   O levantamento bibliográfico e o gerenciamento de metadados foram conduzidos com o auxílio do **RSL.app** (versão {__version__}), software de código aberto e servidor de protocolo de contexto para modelos de linguagem (Model Context Protocol - MCP). A ferramenta conectou consultas parametrizadas a bases acadêmicas de dados abertos (OpenAlex, Crossref, Semantic Scholar, PubMed, Europe PMC e BDTD) sob a estratégia de busca:
   > *"{search_query}"* (Identificador de lista de busca: `{list_id}`, totalizando {total_works} registros deduplicados).

2. **Rastreabilidade e Assistência na Triagem:**
   Das referências triadas ({screened_count} avaliadas, resultando em {included_count} incluídas e {excluded_count} excluídas):
   - {ai_screening_part}
   - Todas as sugestões ou classificações fornecidas por modelos de linguagem foram acompanhadas de justificativas explícitas registradas em trilha de auditoria (`screening/{list_id}.json`).

3. **Supervisão e Responsabilidade Humana:**
   Os autores declaram explicitamente que mantiveram supervisão contínua, validação manual e responsabilidade científica irrestrita sobre a elegibilidade dos artigos selecionados, interpretação das evidências, síntese dos resultados e conclusões apresentadas neste manuscrito. Nenhuma tecnologia de inteligência artificial figura como autora ou coautora deste estudo.
"""


def _render_disclosure_en(
    list_id: str,
    search_query: str,
    total_works: int,
    screened_count: int,
    human_count: int,
    ai_count: int,
    included_count: int,
    excluded_count: int,
) -> str:
    ai_screening_part = (
        f"During the screening phase, {ai_count} records received assistive pre-classification from AI models, "
        f"and {human_count} decisions were registered directly by human researchers."
        if ai_count > 0
        else "All screening decisions were independently conducted and verified entirely by human investigators."
    )

    return f"""### Statement on Artificial Intelligence and Methodological Transparency

In accordance with the recommendations of the **Committee on Publication Ethics (COPE)**, the **International Committee of Medical Journal Editors (ICMJE)**, and the **SciELO Guidelines on Artificial Intelligence**:

1. **Tools and Automated Workflow:**
   Literature retrieval and metadata orchestration were assisted by **RSL.app** (version {__version__}), an open-source research infrastructure providing Model Context Protocol (MCP) interfaces to academic databases (OpenAlex, Crossref, Semantic Scholar, PubMed, Europe PMC, and BDTD). Search queries were executed using the strategy:
   > *"{search_query}"* (Search List ID: `{list_id}`, yielding {total_works} deduplicated records).

2. **Screening Traceability and AI Assistance:**
   Of the screened citations ({screened_count} assessed, resulting in {included_count} inclusions and {excluded_count} exclusions):
   - {ai_screening_part}
   - All AI-assisted suggestions were recorded with explicit inclusion/exclusion justifications in a dedicated audit trail (`screening/{list_id}.json`).

3. **Human Authorship and Scientific Accountability:**
   The human authors affirm that they exercised complete oversight, manual verification, and full intellectual responsibility for all study selections, data extractions, evidence synthesis, and conclusions drawn in this paper. Artificial intelligence tools do not meet authorship criteria and are not listed as authors.
"""
