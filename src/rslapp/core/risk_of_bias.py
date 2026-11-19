"""Avaliação metodológica de risco de viés e qualidade: RoB 2, ROBINS-I e JBI."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from rslapp.core.errors import RSLError

ROB2_DOMAINS = [
    {"id": "D1", "name": "Processo de randomização"},
    {"id": "D2", "name": "Desvios das intervenções pretendidas"},
    {"id": "D3", "name": "Dados faltantes de desfechos"},
    {"id": "D4", "name": "Mensuração do desfecho"},
    {"id": "D5", "name": "Seleção do relato de resultados"},
]

ROBINS_I_DOMAINS = [
    {"id": "D1", "name": "Viés por fatores de confusão"},
    {"id": "D2", "name": "Seleção dos participantes no estudo"},
    {"id": "D3", "name": "Classificação das intervenções"},
    {"id": "D4", "name": "Desvios das intervenções pretendidas"},
    {"id": "D5", "name": "Dados faltantes"},
    {"id": "D6", "name": "Mensuração dos desfechos"},
    {"id": "D7", "name": "Seleção do relato dos resultados"},
]

JBI_QUESTIONS = [
    {"id": "Q1", "name": "Critérios de inclusão claramente definidos"},
    {"id": "Q2", "name": "Descrição detalhada dos sujeitos e do cenário"},
    {"id": "Q3", "name": "Exposição medida de forma válida e confiável"},
    {"id": "Q4", "name": "Critérios padrão objetivos para a condição"},
    {"id": "Q5", "name": "Fatores de confusão identificados"},
    {"id": "Q6", "name": "Estratégias para lidar com fatores de confusão"},
    {"id": "Q7", "name": "Desfechos medidos de forma válida e confiável"},
    {"id": "Q8", "name": "Análise estatística apropriada utilizada"},
]


# FR-36, D-047: Avaliação de um domínio individual de viés
@dataclass
class DomainAssessment:
    domain_id: str
    domain_name: str
    judgment: str  # "low", "some_concerns", "high", "moderate", "serious", "critical", "yes", "no", "unclear", "not_applicable"
    rationale: str = ""
    quote: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DomainAssessment:
        return cls(
            domain_id=str(data.get("domain_id", "")),
            domain_name=str(data.get("domain_name", "")),
            judgment=str(data.get("judgment", "low")).lower().strip(),
            rationale=str(data.get("rationale", "")),
            quote=data.get("quote"),
        )


# FR-36, D-047: Avaliação completa de risco de viés de um artigo
@dataclass
class RiskOfBiasAssessment:
    work_id: str
    tool: str = "rob2"  # "rob2", "robins_i", "jbi"
    domains: list[DomainAssessment] = field(default_factory=list)
    overall_judgment: str = "low"
    overall_rationale: str | None = None
    author_type: str = "human"  # "human" ou "ai"
    verified_by_human: bool = True
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        res["domains"] = [d.to_dict() for d in self.domains]
        return res

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RiskOfBiasAssessment:
        raw_domains = data.get("domains", [])
        domains = [
            DomainAssessment.from_dict(d) if isinstance(d, dict) else d
            for d in raw_domains
        ]
        tool = str(data.get("tool", "rob2")).lower().strip()
        overall = str(data.get("overall_judgment", "")).lower().strip()
        if not overall:
            if tool == "rob2":
                overall = compute_overall_rob2(domains)
            elif tool == "robins_i":
                overall = compute_overall_robins_i(domains)
            else:
                overall = "low"

        return cls(
            work_id=str(data.get("work_id", "")),
            tool=tool,
            domains=domains,
            overall_judgment=overall,
            overall_rationale=data.get("overall_rationale"),
            author_type=data.get("author_type", "human"),
            verified_by_human=bool(data.get("verified_by_human", True)),
            updated_at=data.get("updated_at") or datetime.now(timezone.utc).isoformat(),
        )


# FR-36, D-047: Algoritmo oficial Cochrane RoB 2 para risco geral
def compute_overall_rob2(domains: list[DomainAssessment]) -> str:
    """Calcula o julgamento geral de risco de viés conforme manual Cochrane RoB 2."""
    if not domains:
        return "low"
    judgments = {d.judgment.lower().strip() for d in domains}
    if "high" in judgments:
        return "high"
    if "some_concerns" in judgments:
        return "some_concerns"
    return "low"


# FR-36, D-047: Algoritmo oficial Cochrane ROBINS-I para risco geral
def compute_overall_robins_i(domains: list[DomainAssessment]) -> str:
    """Calcula o julgamento geral de risco de viés conforme Cochrane ROBINS-I."""
    if not domains:
        return "low"
    judgments = {d.judgment.lower().strip() for d in domains}
    if "critical" in judgments:
        return "critical"
    if "serious" in judgments:
        return "serious"
    if "moderate" in judgments:
        return "moderate"
    return "low"


# FR-36, D-047: Gera estrutura de matriz de semáforo (Traffic-light plot data)
def generate_traffic_light_matrix(
    assessments: list[RiskOfBiasAssessment],
    works_info: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Gera matriz padronizada de semáforo para visualização no app ou exportação."""
    info_map = works_info or {}
    rows: list[dict[str, Any]] = []

    for item in assessments:
        w_info = info_map.get(item.work_id, {})
        first_author = w_info.get("first_author") or item.work_id
        year = w_info.get("year") or ""
        label = f"{first_author} ({year})" if year else first_author

        domain_judgments = {d.domain_id: d.judgment for d in item.domains}
        rows.append({
            "work_id": item.work_id,
            "study_label": label,
            "tool": item.tool,
            "domains": domain_judgments,
            "overall": item.overall_judgment,
            "verified_by_human": item.verified_by_human,
        })

    tool_type = assessments[0].tool if assessments else "rob2"
    headers = ROB2_DOMAINS if tool_type == "rob2" else (ROBINS_I_DOMAINS if tool_type == "robins_i" else JBI_QUESTIONS)

    return {
        "tool": tool_type,
        "headers": headers,
        "rows": rows,
    }


def create_empty_assessment(work_id: str, tool: str = "rob2") -> RiskOfBiasAssessment:
    """Cria uma avaliação com domínios padrão pré-preenchidos."""
    tool_clean = tool.lower().strip()
    if tool_clean == "rob2":
        domains = [DomainAssessment(domain_id=d["id"], domain_name=d["name"], judgment="low") for d in ROB2_DOMAINS]
        overall = "low"
    elif tool_clean == "robins_i":
        domains = [DomainAssessment(domain_id=d["id"], domain_name=d["name"], judgment="low") for d in ROBINS_I_DOMAINS]
        overall = "low"
    elif tool_clean == "jbi":
        domains = [DomainAssessment(domain_id=d["id"], domain_name=d["name"], judgment="yes") for d in JBI_QUESTIONS]
        overall = "low"
    else:
        raise RSLError("invalid_input", f"Ferramenta de viés '{tool}' não suportada.")

    return RiskOfBiasAssessment(
        work_id=work_id,
        tool=tool_clean,
        domains=domains,
        overall_judgment=overall,
        author_type="human",
        verified_by_human=True,
    )
