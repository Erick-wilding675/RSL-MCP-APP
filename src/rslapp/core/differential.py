"""Módulo de Revisão Sistemática Viva e Comparação Diferencial de Buscas (FR-32, D-043)."""

from __future__ import annotations

import datetime
import re
from typing import Any

from rslapp.core.models import Work


# FR-32, D-043: Normalização canônica para identificação unívoca de artigos entre versões de busca
def _work_canonical_key(work: Work | dict[str, Any]) -> str:
    """Devolve a chave unívoca do artigo (DOI normalizado ou combinação título+ano)."""
    if isinstance(work, Work):
        doi = work.doi
        title = work.title
        year = work.year
    else:
        doi = work.get("doi")
        title = work.get("title", "")
        year = work.get("year")

    if doi and isinstance(doi, str) and doi.strip():
        clean_doi = doi.strip().lower()
        clean_doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", clean_doi)
        return f"doi:{clean_doi}"

    clean_title = re.sub(r"[^\w\s]", "", (title or "").lower())
    clean_title = re.sub(r"\s+", " ", clean_title).strip()
    return f"title:{clean_title}|year:{year or ''}"


# FR-32, D-043: Calcula a diferença rigorosa entre duas listas de busca (artigos adicionados, mantidos e removidos)
def compute_search_difference(
    base_works: list[Work] | list[dict[str, Any]],
    new_works: list[Work] | list[dict[str, Any]],
    base_list_id: str = "",
    new_list_id: str = "",
) -> dict[str, Any]:
    """Compara duas listas de artigos retornando os trabalhos retidos, adicionados e removidos com estatísticas."""
    base_map: dict[str, Any] = {}
    for w in base_works:
        key = _work_canonical_key(w)
        base_map[key] = w

    new_map: dict[str, Any] = {}
    for w in new_works:
        key = _work_canonical_key(w)
        new_map[key] = w

    base_keys = set(base_map.keys())
    new_keys = set(new_map.keys())

    retained_keys = base_keys & new_keys
    added_keys = new_keys - base_keys
    missing_keys = base_keys - new_keys

    def _get_id(w: Any) -> str:
        if isinstance(w, Work):
            return w.id
        return str(w.get("id", ""))

    retained_ids = [_get_id(base_map[k]) for k in retained_keys]
    added_ids = [_get_id(new_map[k]) for k in added_keys]
    missing_ids = [_get_id(base_map[k]) for k in missing_keys]

    added_works_summary: list[dict[str, Any]] = []
    for k in added_keys:
        item = new_map[k]
        if isinstance(item, Work):
            d = item.to_dict()
        else:
            d = dict(item)
        added_works_summary.append(
            {
                "id": d.get("id"),
                "title": d.get("title"),
                "year": d.get("year"),
                "venue": d.get("venue"),
                "doi": d.get("doi"),
                "authors": [
                    a.get("name") if isinstance(a, dict) else str(a)
                    for a in d.get("authors", [])
                ],
            }
        )

    # Ordena os adicionados por ano decrescente e título
    added_works_summary.sort(
        key=lambda x: (-(x.get("year") or 0), str(x.get("title") or ""))
    )

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    return {
        "base_list_id": base_list_id,
        "new_list_id": new_list_id,
        "updated_at": now_iso,
        "base_total": len(base_works),
        "new_total": len(new_works),
        "retained_count": len(retained_keys),
        "added_count": len(added_keys),
        "missing_count": len(missing_keys),
        "retained_ids": retained_ids,
        "added_ids": added_ids,
        "missing_ids": missing_ids,
        "added_works": added_works_summary,
    }


# FR-32, D-043: Formata relatório metodológico em Markdown para anexos de defesa e submissões
def format_differential_markdown(
    diff_data: dict[str, Any],
    base_title: str = "Busca Anterior",
    new_title: str = "Busca Atualizada",
) -> str:
    """Gera relatório metodológico acadêmico detalhado das alterações da Revisão Viva."""
    base_total = diff_data.get("base_total", 0)
    new_total = diff_data.get("new_total", 0)
    retained_count = diff_data.get("retained_count", 0)
    added_count = diff_data.get("added_count", 0)
    missing_count = diff_data.get("missing_count", 0)
    updated_at = diff_data.get("updated_at", "")
    added_works = diff_data.get("added_works", [])

    lines: list[str] = [
        "# Relatório de Atualização Metodológica — Revisão Sistemática Viva",
        "",
        "> **Documento de Auditoria Científica (FR-32, D-043)**  ",
        f"> **Data da Atualização:** {updated_at}  ",
        f"> **Lista Base:** `{diff_data.get('base_list_id', 'N/A')}` ({base_title})  ",
        f"> **Lista Atualizada:** `{diff_data.get('new_list_id', 'N/A')}` ({new_title})",
        "",
        "## Resumo Quantitativo da Atualização",
        "",
        "| Métrica | Quantidade | Percentual em relação ao total atual |",
        "|---|---|---|",
        f"| Registros catalogados na busca base | {base_total} | - |",
        f"| Registros anteriores preservados | {retained_count} | {(retained_count / max(1, new_total) * 100):.1f}% |",
        f"| Novos artigos identificados | **{added_count}** | **{(added_count / max(1, new_total) * 100):.1f}%** |",
        f"| Registros ausentes na nova execução | {missing_count} | - |",
        f"| **Total no Corpus Atualizado** | **{new_total}** | **100%** |",
        "",
        "## Preservação de Rastreabilidade e Decisões Prévias",
        "",
        "- Todos os **"
        + str(retained_count)
        + "** artigos catalogados na busca inicial mantêm intactas suas respectivas decisões de triagem (inclusão, exclusão e motivos) e fichamentos analíticos.",
        "- Os **"
        + str(added_count)
        + "** novos artigos adicionados ao corpus são destacados para triagem prioritária pelo pesquisador e sua IA.",
        "",
    ]

    if added_works:
        lines.append("## Artigos Inéditos Identificados na Atualização")
        lines.append("")
        for idx, w in enumerate(added_works, start=1):
            title = w.get("title") or "Sem título"
            year = w.get("year") or "s.d."
            venue = w.get("venue") or "Periódico não informado"
            authors = ", ".join(w.get("authors") or []) or "Autores não informados"
            doi = w.get("doi")
            doi_link = f"https://doi.org/{doi}" if doi else "N/A"

            lines.append(f"### {idx}. {title} ({year})")
            lines.append(f"- **Autores:** {authors}")
            lines.append(f"- **Periódico/Veículo:** {venue}")
            if doi:
                lines.append(f"- **DOI:** [{doi}]({doi_link})")
            lines.append(f"- **Identificador interno:** `{w.get('id')}`")
            lines.append("")
    else:
        lines.append("## Artigos Inéditos Identificados na Atualização")
        lines.append("")
        lines.append(
            "_Nenhum novo artigo indexado foi encontrado nas bases consultadas desde a última execução da busca._"
        )
        lines.append("")

    return "\n".join(lines)
