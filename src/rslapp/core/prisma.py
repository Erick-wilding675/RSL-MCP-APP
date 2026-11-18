"""Cálculo e geração do fluxograma PRISMA 2020 e checklist PRISMA-S (FR-26, D-037)."""

from __future__ import annotations

import html
from typing import Any


# FR-26, D-037: Consolidação quantitativa das etapas do fluxograma PRISMA 2020
def calculate_prisma_flow(
    list_data: dict[str, Any],
    screening_summary: dict[str, Any],
    search_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Calcula os quantitativos de cada fase do PRISMA 2020 a partir da busca e triagem."""
    works = list_data.get("works", [])
    total_unique = int(list_data.get("total", len(works)))

    database_counts: dict[str, int] = {}
    records_other = 0

    if search_record and isinstance(search_record.get("sources"), list):
        for src in search_record["sources"]:
            if isinstance(src, dict):
                name = str(src.get("name", "desconhecido")).strip()
                fetched = src.get("fetched")
                found = src.get("found")
                # Usa 'fetched' ou 'found' como registros brutos identificados
                count = int(fetched if fetched is not None else (found if found is not None else 0))
                if name.lower() in {"import", "file", "upload", "manual"}:
                    records_other += count
                else:
                    database_counts[name] = database_counts.get(name, 0) + count
    else:
        # Dedução a partir dos trabalhos da lista se search_record não foi informado
        for w in works:
            src_name = str(w.get("source") or "base_dados").strip()
            database_counts[src_name] = database_counts.get(src_name, 0) + 1

    records_databases = sum(database_counts.values())
    if records_databases == 0 and records_other == 0:
        records_databases = total_unique

    records_total = records_databases + records_other
    duplicates_removed = max(0, records_total - total_unique)

    # Dados de triagem
    by_stage = screening_summary.get("by_stage", {})
    stg_title = by_stage.get("title_abstract", {})
    stg_full = by_stage.get("full_text", {})

    has_stage_breakdown = bool(
        stg_title.get("included", 0)
        or stg_title.get("excluded", 0)
        or stg_title.get("maybe", 0)
        or stg_full.get("included", 0)
        or stg_full.get("excluded", 0)
        or stg_full.get("maybe", 0)
    )

    if has_stage_breakdown:
        screened_title = (
            stg_title.get("included", 0)
            + stg_title.get("excluded", 0)
            + stg_title.get("maybe", 0)
        )
        excluded_title = stg_title.get("excluded", 0)
        pending_title = max(0, total_unique - screened_title)

        reports_sought = stg_title.get("included", 0) + stg_title.get("maybe", 0)
        if reports_sought == 0 and pending_title == 0 and excluded_title < total_unique:
            reports_sought = total_unique - excluded_title

        excluded_full = stg_full.get("excluded", 0)
        reports_not_retrieved = 0
        reasons_full: dict[str, int] = {}
        reasons_title: dict[str, int] = {}

        # Separação dos motivos por estágio
        for reason, count in screening_summary.get("reasons", {}).items():
            if "não recuperado" in reason.lower() or "not retrieved" in reason.lower():
                reports_not_retrieved += count
            elif excluded_full > 0:
                reasons_full[reason] = count
            else:
                reasons_title[reason] = count

        reports_assessed = max(0, reports_sought - reports_not_retrieved)
        studies_included = (
            stg_full.get("included", 0)
            if (stg_full.get("included", 0) > 0 or excluded_full > 0)
            else stg_title.get("included", 0)
        )
    else:
        # Modelo unificado ou triagem em andamento
        screened_title = screening_summary.get("screened", 0)
        excluded_title = screening_summary.get("excluded", 0)
        pending_title = max(0, total_unique - screened_title)
        reasons_title = dict(screening_summary.get("reasons", {}))

        reports_not_retrieved = 0
        for r_name, r_cnt in list(reasons_title.items()):
            if "não recuperado" in r_name.lower() or "not retrieved" in r_name.lower():
                reports_not_retrieved += r_cnt

        reports_sought = max(0, screened_title - excluded_title)
        reports_assessed = max(0, reports_sought - reports_not_retrieved)
        excluded_full = 0
        reasons_full = {}
        studies_included = screening_summary.get("included", 0)

    return {
        "identification": {
            "database_counts": database_counts,
            "records_databases": records_databases,
            "records_other": records_other,
            "records_total": records_total,
            "duplicates_removed": duplicates_removed,
            "records_screened_input": total_unique,
        },
        "screening": {
            "records_screened": screened_title,
            "records_excluded": excluded_title,
            "reasons_excluded": reasons_title,
            "records_pending": pending_title,
            "reports_sought": reports_sought,
        },
        "eligibility": {
            "reports_sought": reports_sought,
            "reports_not_retrieved": reports_not_retrieved,
            "reports_assessed": reports_assessed,
            "reports_excluded": excluded_full,
            "reasons_excluded": reasons_full,
        },
        "included": {
            "studies_included": studies_included,
            "reports_included": studies_included,
        },
        "meta": {
            "list_id": list_data.get("id", ""),
            "search_id": list_data.get("search_id", ""),
            "query": (search_record or {}).get("request_summary", ""),
            "created_at": list_data.get("created_at", ""),
        },
    }


# FR-26, D-037: Geração de diagrama vetorial SVG esteticamente agradável do PRISMA 2020
def render_prisma_svg(flow_data: dict[str, Any], title: str = "Fluxograma PRISMA 2020") -> str:
    """Gera um documento SVG vetorial diagramado representando o fluxo PRISMA 2020."""
    ident = flow_data.get("identification", {})
    screen = flow_data.get("screening", {})
    elig = flow_data.get("eligibility", {})
    inc = flow_data.get("included", {})
    meta = flow_data.get("meta", {})

    db_counts = ident.get("database_counts", {})
    db_lines = [
        f"{html.escape(k.capitalize())} (n = {v})"
        for k, v in sorted(db_counts.items())
    ]
    db_text = ", ".join(db_lines) if db_lines else f"Bases de dados (n = {ident.get('records_databases', 0)})"

    # Quebra de motivos para exibição resumida
    reasons_screen = screen.get("reasons_excluded", {})
    reasons_screen_lines = [
        f"• {html.escape(str(k))}: {v}"
        for k, v in sorted(reasons_screen.items(), key=lambda x: x[1], reverse=True)[:3]
    ]

    reasons_elig = elig.get("reasons_excluded", {})
    reasons_elig_lines = [
        f"• {html.escape(str(k))}: {v}"
        for k, v in sorted(reasons_elig.items(), key=lambda x: x[1], reverse=True)[:3]
    ]

    svg_width = 1000
    svg_height = 840

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" width="100%" height="100%" style="background-color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#475569"/>
    </marker>
    <filter id="shadow" x="-5%" y="-5%" width="110%" height="115%" filterUnits="userSpaceOnUse">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.06"/>
    </filter>
  </defs>

  <!-- Cabeçalho -->
  <text x="500" y="38" text-anchor="middle" font-size="20" font-weight="700" fill="#0f172a">{html.escape(title)}</text>
  <text x="500" y="60" text-anchor="middle" font-size="12" fill="#64748b">Lista: {html.escape(str(meta.get('list_id', '')))} | Termos: {html.escape(str(meta.get('query', ''))[:80])}</text>

  <!-- FAIXAS DE FASES À ESQUERDA -->
  <!-- Fase 1: Identificação -->
  <rect x="30" y="90" width="130" height="150" rx="6" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1"/>
  <text x="95" y="170" text-anchor="middle" font-size="13" font-weight="700" fill="#334155" transform="rotate(-90, 95, 170)">IDENTIFICAÇÃO</text>

  <!-- Fase 2: Triagem -->
  <rect x="30" y="260" width="130" height="180" rx="6" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1"/>
  <text x="95" y="355" text-anchor="middle" font-size="13" font-weight="700" fill="#334155" transform="rotate(-90, 95, 355)">TRIAGEM</text>

  <!-- Fase 3: Elegibilidade -->
  <rect x="30" y="460" width="130" height="210" rx="6" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1"/>
  <text x="95" y="568" text-anchor="middle" font-size="13" font-weight="700" fill="#334155" transform="rotate(-90, 95, 568)">ELEGIBILIDADE</text>

  <!-- Fase 4: Inclusão -->
  <rect x="30" y="690" width="130" height="110" rx="6" fill="#eff6ff" stroke="#93c5fd" stroke-width="1"/>
  <text x="95" y="750" text-anchor="middle" font-size="13" font-weight="700" fill="#1e40af" transform="rotate(-90, 95, 750)">INCLUSÃO</text>

  <!-- BLOCOS CENTRAIS E LATERAIS -->

  <!-- 1. IDENTIFICAÇÃO -->
  <!-- Box: Registros identificados nas bases -->
  <g filter="url(#shadow)">
    <rect x="200" y="90" width="360" height="80" rx="6" fill="#ffffff" stroke="#0284c7" stroke-width="1.5"/>
    <text x="215" y="115" font-size="13" font-weight="700" fill="#0369a1">Registros identificados em bases de dados</text>
    <text x="215" y="135" font-size="12" fill="#334155">Total identificado: <tspan font-weight="700">n = {ident.get('records_databases', 0)}</tspan></text>
    <text x="215" y="153" font-size="11" fill="#64748b">{db_text[:65]}</text>
  </g>

  <!-- Box Lateral: Duplicatas removidas -->
  <g filter="url(#shadow)">
    <rect x="630" y="115" width="330" height="65" rx="6" fill="#fff1f2" stroke="#f43f5e" stroke-width="1.5"/>
    <text x="645" y="138" font-size="13" font-weight="700" fill="#be123c">Registros duplicados removidos</text>
    <text x="645" y="160" font-size="12" fill="#475569">Duplicatas excluídas: <tspan font-weight="700">n = {ident.get('duplicates_removed', 0)}</tspan></text>
  </g>

  <!-- Seta Identificação -> Remoção Duplicatas -->
  <line x1="380" y1="170" x2="380" y2="195" stroke="#475569" stroke-width="1.5"/>
  <line x1="380" y1="147" x2="624" y2="147" stroke="#475569" stroke-width="1.5" marker-end="url(#arrow)"/>

  <!-- 2. TRIAGEM -->
  <!-- Box: Registros triados em título e resumo -->
  <g filter="url(#shadow)">
    <rect x="200" y="260" width="360" height="80" rx="6" fill="#ffffff" stroke="#2563eb" stroke-width="1.5"/>
    <text x="215" y="285" font-size="13" font-weight="700" fill="#1d4ed8">Registros triados (título e resumo)</text>
    <text x="215" y="306" font-size="12" fill="#334155">Avaliados: <tspan font-weight="700">n = {screen.get('records_screened', 0)}</tspan> de {ident.get('records_screened_input', 0)}</text>
    <text x="215" y="324" font-size="11" fill="#64748b">Pendentes de triagem: n = {screen.get('records_pending', 0)}</text>
  </g>

  <!-- Seta Identificação -> Triagem -->
  <line x1="380" y1="170" x2="380" y2="254" stroke="#475569" stroke-width="1.5" marker-end="url(#arrow)"/>

  <!-- Box Lateral: Registros excluídos na triagem -->
  <g filter="url(#shadow)">
    <rect x="630" y="260" width="330" height="100" rx="6" fill="#fef2f2" stroke="#ef4444" stroke-width="1.5"/>
    <text x="645" y="283" font-size="13" font-weight="700" fill="#b91c1c">Registros excluídos (título e resumo)</text>
    <text x="645" y="303" font-size="12" fill="#475569">Total excluído: <tspan font-weight="700">n = {screen.get('records_excluded', 0)}</tspan></text>
    <text x="645" y="322" font-size="11" fill="#7f1d1d">{reasons_screen_lines[0] if len(reasons_screen_lines) > 0 else '• Critérios de inclusão não atingidos'}</text>
    <text x="645" y="338" font-size="11" fill="#7f1d1d">{reasons_screen_lines[1] if len(reasons_screen_lines) > 1 else ''}</text>
    <text x="645" y="352" font-size="11" fill="#7f1d1d">{reasons_screen_lines[2] if len(reasons_screen_lines) > 2 else ''}</text>
  </g>

  <!-- Seta Triagem -> Excluídos -->
  <line x1="560" y1="300" x2="624" y2="300" stroke="#475569" stroke-width="1.5" marker-end="url(#arrow)"/>

  <!-- 3. RECUPERAÇÃO E ELEGIBILIDADE -->
  <!-- Box: Relatórios buscados para recuperação -->
  <g filter="url(#shadow)">
    <rect x="200" y="375" width="360" height="65" rx="6" fill="#ffffff" stroke="#475569" stroke-width="1.5"/>
    <text x="215" y="400" font-size="13" font-weight="700" fill="#334155">Relatórios buscados para recuperação</text>
    <text x="215" y="422" font-size="12" fill="#475569">Encaminhados para texto completo: <tspan font-weight="700">n = {elig.get('reports_sought', 0)}</tspan></text>
  </g>

  <!-- Seta Triagem -> Busca Texto Completo -->
  <line x1="380" y1="340" x2="380" y2="369" stroke="#475569" stroke-width="1.5" marker-end="url(#arrow)"/>

  <!-- Box Lateral: Não recuperados -->
  <g filter="url(#shadow)">
    <rect x="630" y="380" width="330" height="60" rx="6" fill="#fffbeb" stroke="#f59e0b" stroke-width="1.5"/>
    <text x="645" y="403" font-size="13" font-weight="700" fill="#b45309">Relatórios não recuperados</text>
    <text x="645" y="423" font-size="12" fill="#475569">Texto completo inacessível: <tspan font-weight="700">n = {elig.get('reports_not_retrieved', 0)}</tspan></text>
  </g>

  <!-- Seta Buscados -> Não Recuperados -->
  <line x1="560" y1="410" x2="624" y2="410" stroke="#475569" stroke-width="1.5" marker-end="url(#arrow)"/>

  <!-- Box: Relatórios avaliados na elegibilidade -->
  <g filter="url(#shadow)">
    <rect x="200" y="480" width="360" height="70" rx="6" fill="#ffffff" stroke="#6366f1" stroke-width="1.5"/>
    <text x="215" y="505" font-size="13" font-weight="700" fill="#4338ca">Relatórios avaliados para elegibilidade</text>
    <text x="215" y="527" font-size="12" fill="#334155">Texto completo analisado: <tspan font-weight="700">n = {elig.get('reports_assessed', 0)}</tspan></text>
  </g>

  <!-- Seta Buscados -> Avaliados Elegibilidade -->
  <line x1="380" y1="440" x2="380" y2="474" stroke="#475569" stroke-width="1.5" marker-end="url(#arrow)"/>

  <!-- Box Lateral: Excluídos na elegibilidade -->
  <g filter="url(#shadow)">
    <rect x="630" y="480" width="330" height="95" rx="6" fill="#fef2f2" stroke="#ef4444" stroke-width="1.5"/>
    <text x="645" y="503" font-size="13" font-weight="700" fill="#b91c1c">Relatórios excluídos (texto completo)</text>
    <text x="645" y="523" font-size="12" fill="#475569">Total excluído: <tspan font-weight="700">n = {elig.get('reports_excluded', 0)}</tspan></text>
    <text x="645" y="542" font-size="11" fill="#7f1d1d">{reasons_elig_lines[0] if len(reasons_elig_lines) > 0 else '• Critérios metodológicos não atendidos'}</text>
    <text x="645" y="558" font-size="11" fill="#7f1d1d">{reasons_elig_lines[1] if len(reasons_elig_lines) > 1 else ''}</text>
  </g>

  <!-- Seta Avaliados -> Excluídos Elegibilidade -->
  <line x1="560" y1="515" x2="624" y2="515" stroke="#475569" stroke-width="1.5" marker-end="url(#arrow)"/>

  <!-- 4. INCLUSÃO -->
  <!-- Box: Estudos incluídos na revisão -->
  <g filter="url(#shadow)">
    <rect x="200" y="690" width="360" height="85" rx="6" fill="#f0fdf4" stroke="#16a34a" stroke-width="2"/>
    <text x="215" y="718" font-size="14" font-weight="700" fill="#15803d">Estudos incluídos na revisão</text>
    <text x="215" y="742" font-size="13" fill="#166534">Novos estudos incluídos: <tspan font-weight="700">n = {inc.get('studies_included', 0)}</tspan></text>
    <text x="215" y="760" font-size="12" fill="#15803d">Relatórios de estudos incluídos: n = {inc.get('reports_included', 0)}</text>
  </g>

  <!-- Seta Elegibilidade -> Inclusão -->
  <line x1="380" y1="550" x2="380" y2="684" stroke="#475569" stroke-width="1.5" marker-end="url(#arrow)"/>

  <!-- Rodapé de rastreabilidade -->
  <text x="500" y="818" text-anchor="middle" font-size="11" fill="#94a3b8">Gerado automaticamente pelo RSL.app segundo a declaração PRISMA 2020 (Page et al., BMJ 2021; 372:n71)</text>
</svg>"""


# FR-26, D-037: Relatório em Markdown com checklist PRISMA-S
def render_prisma_markdown(flow_data: dict[str, Any]) -> str:
    """Gera sumário detalhado do fluxograma e checklist de busca PRISMA-S em Markdown."""
    ident = flow_data.get("identification", {})
    screen = flow_data.get("screening", {})
    elig = flow_data.get("eligibility", {})
    inc = flow_data.get("included", {})
    meta = flow_data.get("meta", {})

    db_counts = ident.get("database_counts", {})
    bases_md = "\n".join(
        f"- **{k.capitalize()}:** {v} registros"
        for k, v in sorted(db_counts.items())
    ) or "- Nenhuma base individual discriminada"

    reasons_screen_md = "\n".join(
        f"  - {k}: {v}"
        for k, v in sorted(screen.get("reasons_excluded", {}).items(), key=lambda x: x[1], reverse=True)
    ) or "  - Nenhum motivo discriminado"

    reasons_elig_md = "\n".join(
        f"  - {k}: {v}"
        for k, v in sorted(elig.get("reasons_excluded", {}).items(), key=lambda x: x[1], reverse=True)
    ) or "  - Nenhum motivo discriminado"

    return f"""# Relatório de Fluxo PRISMA 2020 e Checklist PRISMA-S

**Lista:** `{meta.get('list_id', 'N/A')}` | **Busca:** `{meta.get('search_id', 'N/A')}` | **Data:** {meta.get('created_at', 'N/A')}  
**Estratégia de Busca:** {meta.get('query', 'N/A')}

---

## 1. Quantitativos do Fluxograma PRISMA 2020

### Fase 1: Identificação (Identification)
- **Registros identificados em bases de dados:** {ident.get('records_databases', 0)}
{bases_md}
- **Registros identificados em outras fontes/importações:** {ident.get('records_other', 0)}
- **Total bruto de registros:** {ident.get('records_total', 0)}
- **Registros duplicados removidos:** {ident.get('duplicates_removed', 0)}
- **Registros únicos direcionados para triagem:** {ident.get('records_screened_input', 0)}

### Fase 2: Triagem (Screening)
- **Registros triados (título e resumo):** {screen.get('records_screened', 0)}
- **Registros pendentes de triagem:** {screen.get('records_pending', 0)}
- **Registros excluídos na triagem:** {screen.get('records_excluded', 0)}
{reasons_screen_md}
- **Relatórios buscados para recuperação na íntegra:** {screen.get('reports_sought', 0)}

### Fase 3: Elegibilidade (Eligibility)
- **Relatórios não recuperados (texto completo inacessível):** {elig.get('reports_not_retrieved', 0)}
- **Relatórios avaliados quanto à elegibilidade:** {elig.get('reports_assessed', 0)}
- **Relatórios excluídos na avaliação de texto completo:** {elig.get('reports_excluded', 0)}
{reasons_elig_md}

### Fase 4: Inclusão (Included)
- **Estudos incluídos na revisão:** {inc.get('studies_included', 0)}
- **Relatórios de estudos incluídos:** {inc.get('reports_included', 0)}

---

## 2. Checklist PRISMA-S (Extensão para Relato de Buscas)

| Item | Descrição | Status no RSL.app |
|---|---|---|
| **1. Base de Dados** | Nome oficial de cada base consultada | Identificadas: {', '.join(db_counts.keys()) or 'Bases integradas'} |
| **2. Interface** | Nome do servidor/API de busca utilizado | RSL.app MCP Server (OpenAlex, Crossref, Semantic Scholar, PubMed, Europe PMC, BDTD) |
| **3. Data da Busca** | Data completa em que as consultas foram executadas | {meta.get('created_at', 'Registrada em log')} |
| **4. Estratégia de Busca** | String completa de busca com operadores booleanos | `{meta.get('query', '')}` |
| **5. Limites e Filtros** | Filtros de idioma, ano ou tipologia documental | Registrados nos metadados de cada registro |
| **6. Desduplicação** | Método utilizado para identificação de duplicatas | Normalização de DOI e correspondência de título (D-009) |
| **7. Rastreabilidade** | Registro imutável de todas as etapas e decisões | Histórico persistido em `log.md` e `screening/{meta.get('list_id', 'id')}.json` |
"""
