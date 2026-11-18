"""Modelo e lógica de triagem com rastro de autoria para revisões sistemáticas (FR-25, D-036)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from rslapp.core.errors import RSLError

VALID_DECISIONS: frozenset[str] = frozenset({"included", "excluded", "maybe"})
VALID_STAGES: frozenset[str] = frozenset({"title_abstract", "full_text"})

DEFAULT_EXCLUSION_REASONS: tuple[str, ...] = (
    "Fora do tema / escopo",
    "População não elegível",
    "Intervenção ou conceito divergente",
    "Desenho de estudo inadequado",
    "Sem dados empíricos primários",
    "Idioma inacessível",
    "Texto completo não recuperado",
    "Artigo duplicado não identificado",
    "Outro motivo",
)


def _format_utc_now() -> str:
    """Gera carimbo ISO 8601 UTC corrente."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# FR-25, D-036: Validação rigorosa dos campos de decisão de triagem
def validate_decision_data(
    work_id: str | int,
    decision: str,
    *,
    reason: str | None = None,
    decided_by: str = "human",
    stage: str = "title_abstract",
    notes: str | None = None,
    doi: str | None = None,
    decided_at: str | None = None,
) -> dict[str, Any]:
    """Valida e normaliza o registro de decisão de triagem de um trabalho.

    Levanta RSLError('invalid_input') se algum campo obrigatório for inválido.
    """
    clean_id = str(work_id).strip()
    if not clean_id:
        raise RSLError("invalid_input", "Identificador do trabalho (work_id) é obrigatório.")

    clean_decision = str(decision).strip().lower()
    if clean_decision not in VALID_DECISIONS:
        raise RSLError(
            "invalid_input",
            f"Decisão inválida: {decision!r}. Valores permitidos: 'included', 'excluded', 'maybe'.",
        )

    clean_stage = str(stage).strip().lower()
    if clean_stage not in VALID_STAGES:
        raise RSLError(
            "invalid_input",
            f"Estágio inválido: {stage!r}. Valores permitidos: 'title_abstract', 'full_text'.",
        )

    clean_author = str(decided_by).strip()
    if not clean_author:
        clean_author = "human"

    clean_reason = str(reason).strip() if reason and str(reason).strip() else None
    if clean_decision == "excluded" and not clean_reason:
        # Motivo padrão se não especificado explicitamente para exclusões
        clean_reason = "Fora do tema / escopo"

    clean_notes = str(notes).strip() if notes and str(notes).strip() else None
    clean_doi = str(doi).strip() if doi and str(doi).strip() else None
    clean_timestamp = str(decided_at).strip() if decided_at else _format_utc_now()

    return {
        "work_id": clean_id,
        "decision": clean_decision,
        "reason": clean_reason,
        "decided_by": clean_author,
        "stage": clean_stage,
        "notes": clean_notes,
        "doi": clean_doi,
        "decided_at": clean_timestamp,
    }


# FR-25, D-036, D-037: Consolidação quantitativa das decisões de triagem
def calculate_screening_summary(
    total_works: int,
    decisions: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Calcula estatísticas agregadas da triagem a partir das decisões registradas."""
    valid_total = max(0, int(total_works))
    screened_count = len(decisions)
    pending_count = max(0, valid_total - screened_count)

    included_count = 0
    excluded_count = 0
    maybe_count = 0

    reasons_count: dict[str, int] = {}
    authors_count: dict[str, int] = {"human": 0, "ai": 0}
    stages_count: dict[str, dict[str, int]] = {
        "title_abstract": {"included": 0, "excluded": 0, "maybe": 0},
        "full_text": {"included": 0, "excluded": 0, "maybe": 0},
    }

    for dec in decisions.values():
        val = dec.get("decision")
        stg = dec.get("stage", "title_abstract")
        auth = str(dec.get("decided_by", "human")).strip().lower()

        if val == "included":
            included_count += 1
        elif val == "excluded":
            excluded_count += 1
            reason_text = dec.get("reason") or "Sem motivo registrado"
            reasons_count[reason_text] = reasons_count.get(reason_text, 0) + 1
        elif val == "maybe":
            maybe_count += 1

        if stg in stages_count and val in stages_count[stg]:
            stages_count[stg][val] += 1

        if auth.startswith("ai") or "ai" in auth:
            authors_count["ai"] = authors_count.get("ai", 0) + 1
        else:
            authors_count["human"] = authors_count.get("human", 0) + 1

    progress_percent = (
        round((screened_count / valid_total) * 100.0, 1) if valid_total > 0 else 0.0
    )

    return {
        "total_works": valid_total,
        "screened": screened_count,
        "pending": pending_count,
        "included": included_count,
        "excluded": excluded_count,
        "maybe": maybe_count,
        "progress_percent": progress_percent,
        "reasons": reasons_count,
        "by_author": authors_count,
        "by_stage": stages_count,
    }
