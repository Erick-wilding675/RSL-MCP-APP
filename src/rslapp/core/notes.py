"""Modelo e gerador de fichamento científico estruturado com rastro de autoria (FR-29, D-040)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from rslapp.core.errors import RSLError

VALID_NOTE_SOURCES: frozenset[str] = frozenset(
    {"human_created", "ai_suggested", "human_reviewed"}
)


def _format_utc_now() -> str:
    """Gera carimbo ISO 8601 UTC corrente."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sanitize_filename_id(work_id: str | int) -> str:
    """Higieniza identificador de trabalho para uso seguro em nomes de arquivo."""
    clean = str(work_id).strip()
    return re.sub(r'[/\\:*?"<>|]', "_", clean)


# FR-29, D-040: Validação estruturada de ficha científica com rastro de autoria
def validate_note_data(
    list_id: str,
    work_id: str | int,
    *,
    title: str | None = None,
    authors: list[str] | None = None,
    year: int | str | None = None,
    doi: str | None = None,
    abnt_reference: str | None = None,
    objective: str | None = None,
    methodology: str | None = None,
    sample: str | None = None,
    results: str | None = None,
    limitations: str | None = None,
    personal_keywords: list[str] | None = None,
    synthesis: str | None = None,
    direct_quotes: list[dict[str, Any]] | None = None,
    source: str = "human_created",
    ai_model: str | None = None,
    reviewed_by: str | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    """Valida e normaliza o registro de ficha científica de um artigo.

    Levanta RSLError('invalid_input') se os identificadores ou fontes forem inválidos.
    """
    clean_list_id = str(list_id).strip()
    if not clean_list_id:
        raise RSLError("invalid_input", "list_id é obrigatório para a ficha científica.")

    clean_work_id = str(work_id).strip()
    if not clean_work_id:
        raise RSLError("invalid_input", "work_id é obrigatório para a ficha científica.")

    clean_source = str(source).strip().lower()
    if clean_source not in VALID_NOTE_SOURCES:
        raise RSLError(
            "invalid_input",
            f"Fonte de autoria inválida: '{source}'. Esperado um de: {sorted(VALID_NOTE_SOURCES)}",
        )

    clean_year: int | None = None
    if year is not None:
        try:
            clean_year = int(year)
        except (ValueError, TypeError):
            raise RSLError("invalid_input", f"Ano inválido: {year!r}") from None

    # Normalização de autores
    clean_authors: list[str] = []
    if authors:
        for a in authors:
            if isinstance(a, str) and a.strip():
                clean_authors.append(a.strip())

    # Normalização de palavras-chave próprias
    clean_keywords: list[str] = []
    if personal_keywords:
        for kw in personal_keywords:
            if isinstance(kw, str) and kw.strip():
                clean_keywords.append(kw.strip())

    # Normalização de citações diretas
    clean_quotes: list[dict[str, Any]] = []
    if direct_quotes:
        for q in direct_quotes:
            if isinstance(q, dict) and q.get("quote"):
                clean_quotes.append({
                    "quote": str(q["quote"]).strip(),
                    "page": str(q["page"]).strip() if q.get("page") else None,
                    "comment": str(q["comment"]).strip() if q.get("comment") else None,
                })

    now_iso = _format_utc_now()
    final_created = created_at or now_iso
    final_updated = updated_at or now_iso

    return {
        "list_id": clean_list_id,
        "work_id": clean_work_id,
        "title": title.strip() if title else None,
        "authors": clean_authors,
        "year": clean_year,
        "doi": doi.strip() if doi else None,
        "abnt_reference": abnt_reference.strip() if abnt_reference else None,
        "objective": objective.strip() if objective else None,
        "methodology": methodology.strip() if methodology else None,
        "sample": sample.strip() if sample else None,
        "results": results.strip() if results else None,
        "limitations": limitations.strip() if limitations else None,
        "personal_keywords": clean_keywords,
        "synthesis": synthesis.strip() if synthesis else None,
        "direct_quotes": clean_quotes,
        "source": clean_source,
        "ai_model": ai_model.strip() if ai_model else None,
        "reviewed_by": reviewed_by.strip() if reviewed_by else None,
        "created_at": final_created,
        "updated_at": final_updated,
    }


# FR-29, D-040: Exportação em Markdown estruturado para Obsidian/Logseq
def format_note_markdown(note: dict[str, Any]) -> str:
    """Renderiza a ficha científica em formato Markdown compatível com Obsidian."""
    title = note.get("title") or f"Artigo {note.get('work_id')}"
    authors = note.get("authors") or []
    year = note.get("year") or ""
    doi = note.get("doi") or ""
    source = note.get("source", "human_created")
    ai_model = note.get("ai_model") or ""
    reviewed_by = note.get("reviewed_by") or ""
    created_at = note.get("created_at") or ""

    # Frontmatter YAML
    lines = [
        "---",
        f'title: "{title}"',
        f"work_id: {note.get('work_id')}",
        f"list_id: {note.get('list_id')}",
    ]
    if authors:
        lines.append("authors:")
        for a in authors:
            lines.append(f'  - "{a}"')
    if year:
        lines.append(f"year: {year}")
    if doi:
        lines.append(f'doi: "{doi}"')
    lines.append(f'source: "{source}"')
    if ai_model:
        lines.append(f'ai_model: "{ai_model}"')
    if reviewed_by:
        lines.append(f'reviewed_by: "{reviewed_by}"')
    lines.extend([
        "tags:",
        "  - fichamento",
        "  - revisao-sistematica",
        "  - rslapp",
        "---",
        "",
        f"# {title}",
        "",
    ])

    if note.get("abnt_reference"):
        lines.extend([
            f"> **Referência ABNT:** {note['abnt_reference']}",
            "",
        ])

    # Callout de rastro de autoria
    if source == "ai_suggested":
        lines.extend([
            "> [!WARNING] Rastro de Autoria: Sugestão de IA",
            f"> Esta ficha foi sugerida pelo modelo **{ai_model or 'IA'}** em `{created_at}` e **ainda não foi revisada** integralmente pelo pesquisador.",
            "",
        ])
    elif source == "human_reviewed":
        reviewer_str = f" por **{reviewed_by}**" if reviewed_by else ""
        lines.extend([
            "> [!NOTE] Rastro de Autoria: Revisado por Humano",
            f"> Esta ficha foi conferida e validada{reviewer_str} a partir da leitura direta do artigo.",
            "",
        ])
    else:
        lines.extend([
            "> [!NOTE] Rastro de Autoria: Elaboração Humana",
            "> Esta ficha foi redigida diretamente pelo pesquisador.",
            "",
        ])

    # Seções científicas
    if note.get("objective"):
        lines.extend(["## 1. Objetivo da Pesquisa", note["objective"], ""])

    if note.get("methodology"):
        lines.extend(["## 2. Metodologia e Desenho", note["methodology"], ""])

    if note.get("sample"):
        lines.extend(["## 3. Amostra e Contexto", note["sample"], ""])

    if note.get("results"):
        lines.extend(["## 4. Principais Resultados", note["results"], ""])

    if note.get("limitations"):
        lines.extend(["## 5. Limitações Apontadas", note["limitations"], ""])

    quotes = note.get("direct_quotes") or []
    if quotes:
        lines.extend(["## 6. Citações Diretas"])
        for q in quotes:
            page_str = f" (p. {q['page']})" if q.get("page") else ""
            lines.append(f"> \"{q['quote']}\"{page_str}")
            if q.get("comment"):
                lines.append(f"> \n> *Comentário:* {q['comment']}")
            lines.append("")

    if note.get("synthesis"):
        lines.extend(["## 7. Síntese e Comentários Críticos", note["synthesis"], ""])

    keywords = note.get("personal_keywords") or []
    if keywords:
        kw_tags = " ".join([f"`#{kw.replace(' ', '_')}`" for kw in keywords])
        lines.extend(["## 8. Palavras-Chave do Pesquisador", kw_tags, ""])

    return "\n".join(lines).strip() + "\n"


# FR-29, D-040: Compilação consolidada de todas as fichas de uma lista
def format_notes_compilation(
    notes: list[dict[str, Any]],
    list_id: str,
    list_title: str | None = None,
) -> str:
    """Renderiza todas as fichas de uma revisão em um único documento Markdown."""
    now_iso = _format_utc_now()
    title_display = list_title or f"Lista {list_id}"

    lines = [
        f"# Fichamento Científico Consolidado · {title_display}",
        "",
        f"- **Lista ID:** `{list_id}`",
        f"- **Total de Fichas:** {len(notes)}",
        f"- **Data de Compilação:** {now_iso}",
        "",
        "---",
        "",
        "## Índice das Fichas",
        "",
    ]

    for idx, n in enumerate(notes, 1):
        work_id = n.get("work_id")
        title = n.get("title") or f"Artigo {work_id}"
        source = n.get("source", "human_created")
        badge = "🤖 IA" if source == "ai_suggested" else "👤 Humano"
        lines.append(f"{idx}. [{title}](#artigo-{work_id}) — *{badge}*")

    lines.extend(["", "---", ""])

    for n in notes:
        work_id = n.get("work_id")
        lines.append(f"<a id='artigo-{work_id}'></a>\n")
        lines.append(format_note_markdown(n))
        lines.extend(["", "---", ""])

    return "\n".join(lines).strip() + "\n"
