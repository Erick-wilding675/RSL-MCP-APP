"""Testes das telas de Extração para Metanálise e Risco de Viés (FR-35, FR-36, D-046, D-047, FR-38)."""

from __future__ import annotations

from typing import Any

from nicegui import ui
from nicegui.testing import User

from rslapp.desktop.pages import extraction_page, quality_page
from rslapp.desktop.service import DesktopService


class FakePhase22Service(DesktopService):
    def __init__(self) -> None:
        self.lists: dict[str, dict[str, Any]] = {
            "l-0001": {
                "id": "l-0001",
                "search_id": "s-0001",
                "total": 1,
                "created_at": "2026-11-19T10:00:00Z",
                "works": [
                    {
                        "id": "W1",
                        "title": "Ensaio Clinico de Exemplo",
                        "year": 2024,
                        "authors": [{"name": "Mendes, Erick"}],
                        "venue": "Revista Cientifica",
                    }
                ],
            }
        }
        self.extractions: dict[str, dict[str, Any]] = {}
        self.risk_of_bias: dict[str, dict[str, Any]] = {}

    def get_list(self, list_id: str) -> dict[str, Any]:
        return self.lists[list_id]

    def list_extractions(self, list_id: str) -> list[dict[str, Any]]:
        return list(self.extractions.values())

    def get_extraction(self, list_id: str, work_id: str | int) -> dict[str, Any] | None:
        return self.extractions.get(str(work_id))

    def save_extraction(self, list_id: str, extraction_data: dict[str, Any]) -> dict[str, Any]:
        self.extractions[str(extraction_data["work_id"])] = extraction_data
        return extraction_data

    def list_risk_of_bias(self, list_id: str) -> list[dict[str, Any]]:
        return list(self.risk_of_bias.values())

    def get_risk_of_bias(self, list_id: str, work_id: str | int) -> dict[str, Any] | None:
        return self.risk_of_bias.get(str(work_id))

    def save_risk_of_bias(self, list_id: str, assessment_data: dict[str, Any]) -> dict[str, Any]:
        self.risk_of_bias[str(assessment_data["work_id"])] = assessment_data
        return assessment_data

    def get_risk_of_bias_matrix(self, list_id: str) -> dict[str, Any]:
        return {"tool": "rob2", "headers": [], "rows": []}


# FR-35, FR-38: Renderização e interação na tela de Extração
async def test_fr35_tela_extracao(user: User) -> None:
    svc = FakePhase22Service()

    @ui.page("/extracao/l-0001")
    def page() -> None:
        extraction_page.build(svc, "l-0001")

    await user.open("/extracao/l-0001")
    await user.should_see("Extração de Dados para Metanálise")
    await user.should_see("Ensaio Clinico de Exemplo")
    await user.should_see("Desenho do Estudo")
    await user.should_see("Desfechos Extraídos")


# FR-36, FR-38: Renderização e interação na tela de Risco de Viés
async def test_fr36_tela_qualidade(user: User) -> None:
    svc = FakePhase22Service()

    @ui.page("/qualidade/l-0001")
    def page() -> None:
        quality_page.build(svc, "l-0001")

    await user.open("/qualidade/l-0001")
    await user.should_see("Risco de Viés / Qualidade")
    await user.should_see("Cochrane RoB 2 (Ensaios Clínicos)")
    await user.should_see("Matriz de Semáforo")
