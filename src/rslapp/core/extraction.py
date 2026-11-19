"""Extração analítica e quantitativa de dados para metanálise, R metafor e RevMan."""

from __future__ import annotations

import csv
import io
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from rslapp.core.errors import RSLError


# FR-35, D-046: Desfecho quantitativo ou qualitativo do estudo
@dataclass
class StudyOutcome:
    name: str
    outcome_type: str = "dichotomous"  # "dichotomous" ou "continuous"
    unit: str | None = None
    # Intervenção / Grupo 1
    n_intervention: int | None = None
    events_intervention: int | None = None
    mean_intervention: float | None = None
    sd_intervention: float | None = None
    # Controle / Grupo 2
    n_control: int | None = None
    events_control: int | None = None
    mean_control: float | None = None
    sd_control: float | None = None
    # Estimativa de efeito relatada ou calculada
    effect_measure: str | None = None  # "OR", "RR", "MD", "SMD", "HR"
    effect_estimate: float | None = None
    ci_lower: float | None = None
    ci_upper: float | None = None
    p_value: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StudyOutcome:
        return cls(
            name=data.get("name", "Desfecho principal"),
            outcome_type=data.get("outcome_type", "dichotomous"),
            unit=data.get("unit"),
            n_intervention=data.get("n_intervention"),
            events_intervention=data.get("events_intervention"),
            mean_intervention=data.get("mean_intervention"),
            sd_intervention=data.get("sd_intervention"),
            n_control=data.get("n_control"),
            events_control=data.get("events_control"),
            mean_control=data.get("mean_control"),
            sd_control=data.get("sd_control"),
            effect_measure=data.get("effect_measure"),
            effect_estimate=data.get("effect_estimate"),
            ci_lower=data.get("ci_lower"),
            ci_upper=data.get("ci_upper"),
            p_value=data.get("p_value"),
        )


# FR-35, D-046: Conjunto completo de dados extraídos de um estudo
@dataclass
class ExtractionData:
    work_id: str
    study_design: str = "RCT"  # "RCT", "Cohort", "Case-Control", "Cross-Sectional", "Other"
    sample_size_total: int | None = None
    country: str | None = None
    intervention_description: str | None = None
    control_description: str | None = None
    outcomes: list[StudyOutcome] = field(default_factory=list)
    evidence_quote: str | None = None
    page_number: str | None = None
    author_type: str = "human"  # "human" ou "ai"
    verified_by_human: bool = True
    notes: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        res["outcomes"] = [o.to_dict() for o in self.outcomes]
        return res

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExtractionData:
        raw_outcomes = data.get("outcomes", [])
        outcomes = [
            StudyOutcome.from_dict(o) if isinstance(o, dict) else o
            for o in raw_outcomes
        ]
        return cls(
            work_id=str(data.get("work_id", "")),
            study_design=data.get("study_design", "RCT"),
            sample_size_total=data.get("sample_size_total"),
            country=data.get("country"),
            intervention_description=data.get("intervention_description"),
            control_description=data.get("control_description"),
            outcomes=outcomes,
            evidence_quote=data.get("evidence_quote"),
            page_number=data.get("page_number"),
            author_type=data.get("author_type", "human"),
            verified_by_human=bool(data.get("verified_by_human", True)),
            notes=data.get("notes"),
            updated_at=data.get("updated_at") or datetime.now(timezone.utc).isoformat(),
        )


# FR-35, D-046: Cálculo paramétrico de Odds Ratio (OR) com IC 95%
def calculate_odds_ratio(
    events_i: int, n_i: int, events_c: int, n_c: int
) -> tuple[float, float, float]:
    """Calcula Odds Ratio e intervalo de confiança 95% com correção de Haldane em células zero."""
    if n_i <= 0 or n_c <= 0 or events_i < 0 or events_c < 0 or events_i > n_i or events_c > n_c:
        raise RSLError("invalid_input", "Valores amostrais inválidos para cálculo de Odds Ratio.")

    a, b = float(events_i), float(n_i - events_i)
    c, d = float(events_c), float(n_c - events_c)

    # Correção de continuidade de Haldane se alguma célula for zero
    if a == 0 or b == 0 or c == 0 or d == 0:
        a += 0.5
        b += 0.5
        c += 0.5
        d += 0.5

    odds_ratio = (a * d) / (b * c)
    se_ln_or = math.sqrt((1.0 / a) + (1.0 / b) + (1.0 / c) + (1.0 / d))
    ci_lower = math.exp(math.log(odds_ratio) - 1.96 * se_ln_or)
    ci_upper = math.exp(math.log(odds_ratio) + 1.96 * se_ln_or)
    return round(odds_ratio, 4), round(ci_lower, 4), round(ci_upper, 4)


# FR-35, D-046: Cálculo de Risco Relativo (RR) com IC 95%
def calculate_risk_ratio(
    events_i: int, n_i: int, events_c: int, n_c: int
) -> tuple[float, float, float]:
    """Calcula Risco Relativo e intervalo de confiança 95%."""
    if n_i <= 0 or n_c <= 0 or events_i < 0 or events_c < 0 or events_i > n_i or events_c > n_c:
        raise RSLError("invalid_input", "Valores amostrais inválidos para cálculo de Risco Relativo.")

    a, n1 = float(events_i), float(n_i)
    c, n2 = float(events_c), float(n_c)

    if a == 0:
        a += 0.5
        n1 += 1.0
    if c == 0:
        c += 0.5
        n2 += 1.0

    p_i = a / n1
    p_c = c / n2
    risk_ratio = p_i / p_c
    se_ln_rr = math.sqrt((1.0 / a) - (1.0 / n1) + (1.0 / c) - (1.0 / n2))
    ci_lower = math.exp(math.log(risk_ratio) - 1.96 * se_ln_rr)
    ci_upper = math.exp(math.log(risk_ratio) + 1.96 * se_ln_rr)
    return round(risk_ratio, 4), round(ci_lower, 4), round(ci_upper, 4)


# FR-35, D-046: Cálculo de Diferença de Médias (MD) com IC 95%
def calculate_mean_difference(
    mean_i: float, sd_i: float, n_i: int, mean_c: float, sd_c: float, n_c: int
) -> tuple[float, float, float]:
    """Calcula a Diferença de Médias (MD) e IC 95%."""
    if n_i <= 1 or n_c <= 1 or sd_i < 0 or sd_c < 0:
        raise RSLError("invalid_input", "Parâmetros amostrais inválidos para cálculo de Diferença de Médias.")

    md = mean_i - mean_c
    se_md = math.sqrt(((sd_i**2) / n_i) + ((sd_c**2) / n_c))
    ci_lower = md - 1.96 * se_md
    ci_upper = md + 1.96 * se_md
    return round(md, 4), round(ci_lower, 4), round(ci_upper, 4)


# FR-35, D-046: Cálculo de Diferença Padronizada de Médias (SMD / Hedges' g)
def calculate_smd(
    mean_i: float, sd_i: float, n_i: int, mean_c: float, sd_c: float, n_c: int
) -> tuple[float, float, float]:
    """Calcula SMD padronizado com correção de amostra pequena de Hedges (g)."""
    if n_i <= 1 or n_c <= 1 or sd_i <= 0 or sd_c <= 0:
        raise RSLError("invalid_input", "Desvios e amostras devem ser positivos para SMD.")

    df = n_i + n_c - 2
    s_pooled = math.sqrt((((n_i - 1) * (sd_i**2)) + ((n_c - 1) * (sd_c**2))) / df)
    d = (mean_i - mean_c) / s_pooled
    # Correção de Hedges
    j = 1.0 - (3.0 / (4.0 * df - 1.0))
    g = d * j
    se_g = math.sqrt(((n_i + n_c) / (n_i * n_c)) + ((g**2) / (2.0 * df)))
    ci_lower = g - 1.96 * se_g
    ci_upper = g + 1.96 * se_g
    return round(g, 4), round(ci_lower, 4), round(ci_upper, 4)


# FR-35, D-046: Exportação para R metafor (formato de entrada de rma/rma.uni)
def export_metafor_csv(
    extractions: list[ExtractionData],
    works_info: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Gera CSV pronto para meta-análise com pacote metafor do R."""
    info_map = works_info or {}
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    # Cabeçalho padrão metafor
    writer.writerow([
        "study_id",
        "author_year",
        "design",
        "outcome",
        "outcome_type",
        "n1i",
        "ai",
        "m1i",
        "sd1i",
        "n2i",
        "ci",
        "m2i",
        "sd2i",
        "yi",
        "ci_lower",
        "ci_upper",
    ])

    for ext in extractions:
        w_info = info_map.get(ext.work_id, {})
        first_author = w_info.get("first_author") or ext.work_id
        year = w_info.get("year") or ""
        author_year = f"{first_author} ({year})" if year else first_author

        for out in ext.outcomes:
            yi = out.effect_estimate if out.effect_estimate is not None else ""
            ci_l = out.ci_lower if out.ci_lower is not None else ""
            ci_u = out.ci_upper if out.ci_upper is not None else ""

            writer.writerow([
                ext.work_id,
                author_year,
                ext.study_design,
                out.name,
                out.outcome_type,
                out.n_intervention or "",
                out.events_intervention or "",
                out.mean_intervention or "",
                out.sd_intervention or "",
                out.n_control or "",
                out.events_control or "",
                out.mean_control or "",
                out.sd_control or "",
                yi,
                ci_l,
                ci_u,
            ])

    return output.getvalue()


# FR-35, D-046: Exportação para RevMan 5 / RevMan Web
def export_revman_csv(
    extractions: list[ExtractionData],
    works_info: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Gera CSV estruturado para importação no RevMan."""
    info_map = works_info or {}
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    writer.writerow([
        "Study ID",
        "Intervention Events",
        "Intervention Total",
        "Control Events",
        "Control Total",
        "Intervention Mean",
        "Intervention SD",
        "Control Mean",
        "Control SD",
        "Outcome Name",
        "Study Design",
    ])

    for ext in extractions:
        w_info = info_map.get(ext.work_id, {})
        first_author = w_info.get("first_author") or ext.work_id
        year = w_info.get("year") or ""
        study_id = f"{first_author} {year}".strip()

        for out in ext.outcomes:
            writer.writerow([
                study_id,
                out.events_intervention or "",
                out.n_intervention or "",
                out.events_control or "",
                out.n_control or "",
                out.mean_intervention or "",
                out.sd_intervention or "",
                out.mean_control or "",
                out.sd_control or "",
                out.name,
                ext.study_design,
            ])

    return output.getvalue()
