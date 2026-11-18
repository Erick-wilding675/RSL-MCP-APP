"""Modelo e gerador de Protocolo Metodológico Pré-Busca Versionado (FR-30, D-041).

Suporta os frameworks PICO, PCC (JBI), PICo, SPIDER e Narrativo, com critérios de
elegibilidade, estratégia de busca planejada, versionamento histórico e conformidade
com as diretrizes do PROSPERO, OSF e PRISMA-P.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from rslapp.core.errors import RSLError

VALID_FRAMEWORKS: frozenset[str] = frozenset(
    {"pico", "pcc", "pico_qualitative", "spider", "narrative"}
)

VALID_STATUSES: frozenset[str] = frozenset({"draft", "registered", "completed"})

FRAMEWORK_LABELS: dict[str, str] = {
    "pico": "PICO (População, Intervenção, Comparação, Desfecho)",
    "pcc": "PCC (População, Conceito, Contexto - Padrão JBI)",
    "pico_qualitative": "PICo (População, Interesse, Contexto - Revisão Qualitativa)",
    "spider": "SPIDER (Amostra, Fenômeno, Desenho, Avaliação, Tipo de Pesquisa)",
    "narrative": "Narrativo / Tradicional (Questão, Escopo e Objetivos)",
}

FRAMEWORK_COMPONENTS: dict[str, list[str]] = {
    "pico": ["population", "intervention", "comparison", "outcome", "study_design"],
    "pcc": ["population", "concept", "context"],
    "pico_qualitative": ["population", "interest", "context"],
    "spider": ["sample", "phenomenon_of_interest", "design", "evaluation", "research_type"],
    "narrative": ["central_question", "thematic_scope", "theoretical_context", "objectives"],
}

COMPONENT_LABELS: dict[str, str] = {
    "population": "População / Participantes (P)",
    "intervention": "Intervenção / Exposição (I)",
    "comparison": "Comparação / Controle (C)",
    "outcome": "Desfecho / Resultados (O)",
    "study_design": "Desenho de Estudo (S)",
    "concept": "Conceito Central (C)",
    "context": "Contexto (C)",
    "interest": "Fenômeno de Interesse (I)",
    "sample": "Amostra / Participantes (S)",
    "phenomenon_of_interest": "Fenômeno de Interesse (PI)",
    "design": "Desenho Metodológico (D)",
    "evaluation": "Avaliação / Medida de Efeito (E)",
    "research_type": "Tipo de Pesquisa (R)",
    "central_question": "Questão Central",
    "thematic_scope": "Escopo Temático",
    "theoretical_context": "Contexto Teórico",
    "objectives": "Objetivos da Revisão",
}


def _format_utc_now() -> str:
    """Gera carimbo ISO 8601 UTC corrente."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def generate_protocol_id() -> str:
    """Gera um identificador legível e seguro para novos protocolos."""
    short_hash = uuid.uuid4().hex[:8]
    return f"prot_{short_hash}"


def sanitize_protocol_id(protocol_id: str) -> str:
    """Higieniza o ID do protocolo para nomes de arquivo seguros."""
    clean = str(protocol_id).strip().lower()
    clean = re.sub(r'[/\\:*?"<>|\s]', "_", clean)
    return clean or generate_protocol_id()


# FR-30, D-041: Validação e normalização de protocolo metodológico
def validate_protocol_data(
    protocol_id: str | None = None,
    *,
    id: str | None = None,
    title: str,
    framework: str = "pico",
    question: str,
    subquestions: list[str] | None = None,
    components: dict[str, str] | None = None,
    inclusion_criteria: list[str] | None = None,
    exclusion_criteria: list[str] | None = None,
    planned_sources: list[str] | None = None,
    search_strategy: str | None = None,
    languages: list[str] | None = None,
    date_range: dict[str, Any] | None = None,
    authors: list[str] | None = None,
    status: str = "draft",
    registration_platform: str | None = None,
    registration_number: str | None = None,
    version: int | str = 1,
    created_at: str | None = None,
    updated_at: str | None = None,
    history: list[dict[str, Any]] | None = None,
    ai_assisted: bool = False,
    ai_model: str | None = None,
) -> dict[str, Any]:
    """Valida e normaliza a estrutura de um protocolo metodológico pré-busca.

    Levanta RSLError('invalid_input') se campos essenciais forem violados.
    """
    clean_title = str(title).strip()
    if not clean_title:
        raise RSLError("invalid_input", "O título do protocolo é obrigatório.")

    clean_question = str(question).strip()
    if not clean_question:
        raise RSLError("invalid_input", "A pergunta de pesquisa do protocolo é obrigatória.")

    clean_framework = str(framework).strip().lower()
    if clean_framework not in VALID_FRAMEWORKS:
        raise RSLError(
            "invalid_input",
            f"Framework inválido: '{framework}'. Esperado um de: {sorted(VALID_FRAMEWORKS)}",
        )

    clean_status = str(status).strip().lower()
    if clean_status not in VALID_STATUSES:
        raise RSLError(
            "invalid_input",
            f"Status inválido: '{status}'. Esperado um de: {sorted(VALID_STATUSES)}",
        )

    try:
        clean_version = max(int(version), 1)
    except (ValueError, TypeError):
        raise RSLError("invalid_input", f"Versão inválida: {version!r}") from None

    target_id = protocol_id or id
    pid = sanitize_protocol_id(target_id) if target_id else generate_protocol_id()

    # Normalização de subquestões
    clean_subquestions: list[str] = []
    if subquestions:
        for sq in subquestions:
            if isinstance(sq, str) and sq.strip():
                clean_subquestions.append(sq.strip())

    # Normalização dos componentes do framework
    expected_components = FRAMEWORK_COMPONENTS.get(clean_framework, [])
    clean_components: dict[str, str] = {}
    if components and isinstance(components, dict):
        for k, v in components.items():
            if isinstance(k, str) and v and isinstance(v, str) and v.strip():
                clean_components[k.strip().lower()] = v.strip()
    # Assegura que chaves esperadas existam mesmo que vazias
    for key in expected_components:
        if key not in clean_components:
            clean_components[key] = ""

    # Normalização de critérios de inclusão e exclusão
    clean_inclusion: list[str] = []
    if inclusion_criteria:
        for inc in inclusion_criteria:
            if isinstance(inc, str) and inc.strip():
                clean_inclusion.append(inc.strip())

    clean_exclusion: list[str] = []
    if exclusion_criteria:
        for exc in exclusion_criteria:
            if isinstance(exc, str) and exc.strip():
                clean_exclusion.append(exc.strip())

    # Normalização de fontes planejadas
    clean_sources: list[str] = []
    if planned_sources:
        for s in planned_sources:
            if isinstance(s, str) and s.strip():
                clean_sources.append(s.strip().lower())

    # Normalização de idiomas
    clean_languages: list[str] = []
    if languages:
        for lang in languages:
            if isinstance(lang, str) and lang.strip():
                clean_languages.append(lang.strip().lower())

    # Normalização de autores
    clean_authors: list[str] = []
    if authors:
        for a in authors:
            if isinstance(a, str) and a.strip():
                clean_authors.append(a.strip())

    # Normalização de datas de recorte
    clean_date_range: dict[str, int | None] = {"start_year": None, "end_year": None}
    if date_range and isinstance(date_range, dict):
        for y_key in ("start_year", "end_year"):
            val = date_range.get(y_key)
            if val is not None:
                try:
                    clean_date_range[y_key] = int(val)
                except (ValueError, TypeError):
                    clean_date_range[y_key] = None

    now = _format_utc_now()
    clean_created_at = str(created_at).strip() if created_at else now
    clean_updated_at = str(updated_at).strip() if updated_at else now

    clean_history: list[dict[str, Any]] = []
    if history and isinstance(history, list):
        for item in history:
            if isinstance(item, dict):
                clean_history.append(item)

    return {
        "id": pid,
        "title": clean_title,
        "framework": clean_framework,
        "question": clean_question,
        "subquestions": clean_subquestions,
        "components": clean_components,
        "inclusion_criteria": clean_inclusion,
        "exclusion_criteria": clean_exclusion,
        "planned_sources": clean_sources,
        "search_strategy": str(search_strategy).strip() if search_strategy else "",
        "languages": clean_languages,
        "date_range": clean_date_range,
        "authors": clean_authors,
        "status": clean_status,
        "registration_platform": (
            str(registration_platform).strip() if registration_platform else None
        ),
        "registration_number": (
            str(registration_number).strip() if registration_number else None
        ),
        "version": clean_version,
        "created_at": clean_created_at,
        "updated_at": clean_updated_at,
        "history": clean_history,
        "ai_assisted": bool(ai_assisted),
        "ai_model": str(ai_model).strip() if ai_model else None,
    }


# FR-30, D-041: Exportação formal de protocolo em Markdown para PROSPERO, OSF e tese
def format_protocol_markdown(protocol: dict[str, Any]) -> str:
    """Gera documento Markdown completo do protocolo metodológico para submissão."""
    title = protocol.get("title", "Protocolo Metodológico de Revisão")
    framework_key = protocol.get("framework", "pico")
    framework_label = FRAMEWORK_LABELS.get(framework_key, framework_key.upper())
    question = protocol.get("question", "")
    subquestions = protocol.get("subquestions", [])
    components = protocol.get("components", {})
    inclusion = protocol.get("inclusion_criteria", [])
    exclusion = protocol.get("exclusion_criteria", [])
    sources = protocol.get("planned_sources", [])
    search_strategy = protocol.get("search_strategy", "")
    languages = protocol.get("languages", [])
    date_range = protocol.get("date_range", {})
    authors = protocol.get("authors", [])
    status = protocol.get("status", "draft").upper()
    platform = protocol.get("registration_platform")
    reg_num = protocol.get("registration_number")
    version = protocol.get("version", 1)
    updated_at = protocol.get("updated_at", "")[:10]
    ai_assisted = protocol.get("ai_assisted", False)
    ai_model = protocol.get("ai_model")

    lines: list[str] = [
        f"# {title}",
        "",
        "> **Protocolo Metodológico Pré-Busca de Revisão Sistemática / Escopo**  ",
        f"> **Padrão:** PRISMA-P & PROSPERO / OSF · **Versão:** {version} · **Status:** {status} · **Data:** {updated_at}",
        "",
        "## 1. Identificação e Metadados do Registro",
        "",
        f"- **ID Interno do Protocolo:** `{protocol.get('id', '')}`",
        f"- **Autores / Pesquisadores:** {', '.join(authors) if authors else 'Não especificado'}",
        f"- **Plataforma de Registro:** {platform or 'Não registrada formalmente (Uso interno/laboratório)'}",
        f"- **Número / DOI de Registro:** {reg_num or 'Pendente / Não aplicável'}",
        f"- **Framework Metodológico:** {framework_label}",
        "",
        "## 2. Pergunta de Pesquisa e Enquadramento",
        "",
        f"### Pergunta Principal\n> **{question}**",
        "",
    ]

    if subquestions:
        lines.append("### Perguntas Secundárias")
        for idx, sq in enumerate(subquestions, 1):
            lines.append(f"{idx}. {sq}")
        lines.append("")

    lines.extend([
        f"### Componentes do Framework ({framework_key.upper()})",
        "",
        "| Componente | Descrição Metodológica |",
        "|---|---|",
    ])

    for comp_key, comp_val in components.items():
        comp_label = COMPONENT_LABELS.get(comp_key, comp_key.capitalize())
        safe_val = comp_val.replace("\n", " ").strip() if comp_val else "*Não informado*"
        lines.append(f"| **{comp_label}** | {safe_val} |")

    lines.extend([
        "",
        "## 3. Critérios Formais de Elegibilidade",
        "",
        "### Critérios de Inclusão",
    ])

    if inclusion:
        for inc in inclusion:
            lines.append(f"- [x] {inc}")
    else:
        lines.append("*Nenhum critério de inclusão formalmente delimitado.*")

    lines.extend([
        "",
        "### Critérios de Exclusão",
    ])

    if exclusion:
        for exc in exclusion:
            lines.append(f"- [ ] {exc}")
    else:
        lines.append("*Nenhum critério de exclusão formalmente delimitado.*")

    lines.extend([
        "",
        "## 4. Estratégia de Busca e Fontes Planejadas",
        "",
        f"- **Bases Acadêmicas Planejadas:** {', '.join(s.upper() for s in sources) if sources else 'Não especificadas'}",
        f"- **Idiomas Abrangidos:** {', '.join(languages) if languages else 'Sem restrição explícita de idioma'}",
    ])

    start_y = date_range.get("start_year")
    end_y = date_range.get("end_year")
    if start_y or end_y:
        lines.append(f"- **Recorte Temporal:** {start_y or 'Início'} até {end_y or 'Presente'}")
    else:
        lines.append("- **Recorte Temporal:** Sem restrição temporal planejada")

    lines.extend([
        "",
        "### Sintaxe de Busca Planejada",
        "",
        "```text",
        search_strategy or "Sintaxe booleana a ser definida na fase exploratória.",
        "```",
        "",
        "## 5. Rastreabilidade, Versão e Transparência Ética",
        "",
        f"- **Versão do Protocolo:** {version}",
        f"- **Última Atualização:** {protocol.get('updated_at', '')}",
    ])

    history = protocol.get("history", [])
    if history:
        lines.extend([
            "",
            "### Histórico de Revisões do Protocolo",
            "",
            "| Versão | Data | Alterações Registradas |",
            "|---|---|---|",
        ])
        for h in history:
            v_num = h.get("version", "?")
            d_str = (h.get("timestamp") or "")[:10]
            summary = h.get("summary") or "Atualização metodológica do protocolo"
            lines.append(f"| v{v_num} | {d_str} | {summary} |")

    lines.extend([
        "",
        "### Declaração de Uso de Inteligência Artificial",
        "",
    ])

    if ai_assisted:
        lines.append(
            f"> Este protocolo metodológico contou com auxílio computacional de Inteligência Artificial ({ai_model or 'Modelo LLM'}) "
            "para assistência na estruturação formal, refinamento de termos de busca e enquadramento nos frameworks internacionais. "
            "A formulação final, a decisão de inclusão e exclusão e a responsabilidade científica e ética são exclusivamente dos pesquisadores humanos."
        )
    else:
        lines.append(
            "> Este protocolo metodológico foi formulado inteiramente por pesquisadores humanos, sem assistência de modelos de linguagem para tomada de decisão pré-busca."
        )

    lines.append("")
    return "\n".join(lines)
