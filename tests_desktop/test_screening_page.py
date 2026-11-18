"""Testes das telas de Triagem e PRISMA 2020 do app desktop (FR-25, FR-26, FR-27, D-036, D-037, D-038)."""

from __future__ import annotations

from typing import Any

from nicegui import ui
from nicegui.testing import User

from rslapp.desktop.pages import list_view, prisma_view, screening_view
from rslapp.desktop.service import DesktopService


class FakeScreeningDesktopService(DesktopService):
    """Serviço falso para testar as telas de triagem e fluxograma PRISMA."""

    def __init__(self) -> None:
        self.lists: dict[str, dict[str, Any]] = {
            "l-0001": {
                "id": "l-0001",
                "search_id": "s-0001",
                "total": 2,
                "created_at": "2026-11-18T10:00:00Z",
                "works": [
                    {
                        "doi": "10.1016/j.cardio.2024.01",
                        "title": "Machine Learning in Cardiology Screening",
                        "year": 2024,
                        "authors": [{"name": "Silva, Carlos"}, {"name": "Santos, Ana"}],
                        "venue": "Journal of Cardiology",
                        "abstract": "We evaluate deep learning models for ECG screening in primary care clinics.",
                        "source": "openalex",
                    },
                    {
                        "doi": "10.1016/j.cardio.2024.02",
                        "title": "Arrhythmia Detection using Neural Networks",
                        "year": 2023,
                        "authors": [{"name": "Oliveira, Marcos"}],
                        "venue": "Heart Review",
                        "abstract": "Clinical trial on automated arrhythmia classification.",
                        "source": "crossref",
                    },
                ],
            }
        }
        self.searches: dict[str, dict[str, Any]] = {
            "s-0001": {
                "id": "s-0001",
                "request_summary": "machine learning cardiology",
                "created_at": "2026-11-18T10:00:00Z",
                "sources": [
                    {"name": "openalex", "status": "ok", "fetched": 1, "found": 1},
                    {"name": "crossref", "status": "ok", "fetched": 1, "found": 1},
                ],
            }
        }
        self.screening_decisions: dict[str, dict[str, Any]] = {}
        self.saved_calls: list[dict[str, Any]] = []

    def get_list(self, list_id: str) -> dict[str, Any]:
        return self.lists[list_id]

    def get_search(self, search_id: str) -> dict[str, Any]:
        return self.searches[search_id]

    def get_screening(self, list_id: str) -> dict[str, Any]:
        return {
            "list_id": list_id,
            "decisions": self.screening_decisions,
        }

    def save_screening_decision(
        self, list_id: str, decision_data: dict[str, Any]
    ) -> dict[str, Any]:
        self.saved_calls.append(decision_data)
        work_id = decision_data["work_id"]
        self.screening_decisions[work_id] = decision_data
        return {
            "list_id": list_id,
            "decisions": self.screening_decisions,
        }

    def get_screening_summary(self, list_id: str) -> dict[str, Any]:
        screened = len(self.screening_decisions)
        inc = sum(1 for d in self.screening_decisions.values() if d.get("decision") == "included")
        exc = sum(1 for d in self.screening_decisions.values() if d.get("decision") == "excluded")
        return {
            "total_works": 2,
            "screened": screened,
            "pending": 2 - screened,
            "included": inc,
            "excluded": exc,
            "maybe": 0,
            "progress_percent": (screened / 2.0) * 100.0,
            "reasons": {},
            "by_author": {"human": screened, "ai": 0},
            "by_stage": {},
        }

    def get_prisma_flow(self, list_id: str) -> dict[str, Any]:
        from rslapp.core.prisma import (
            calculate_prisma_flow,
            render_prisma_markdown,
            render_prisma_svg,
        )

        list_data = self.get_list(list_id)
        summary = self.get_screening_summary(list_id)
        search_rec = self.get_search("s-0001")
        flow = calculate_prisma_flow(list_data, summary, search_record=search_rec)
        return {
            "list_id": list_id,
            "flow": flow,
            "svg": render_prisma_svg(flow),
            "report_markdown": render_prisma_markdown(flow),
        }

    def get_ai_disclosure(self, list_id: str, lang: str = "pt") -> str:
        from rslapp.core.ai_disclosure import render_ai_disclosure

        self.get_list(list_id)
        summary = self.get_screening_summary(list_id)
        return render_ai_disclosure(
            list_id=list_id,
            search_query="machine learning cardiology",
            total_works=2,
            screening_summary=summary,
            lang=lang,
        )


# FR-25, D-036: Abertura da tela de triagem com artigo e botões de decisão
async def test_fr25_d036_triagem_view_render(user: User) -> None:
    service = FakeScreeningDesktopService()

    @ui.page("/test-screening-page")
    def page() -> None:
        screening_view.build(service, "l-0001")

    await user.open("/test-screening-page")
    await user.should_see("Triagem")
    await user.should_see("Artigo 1 de 2")
    await user.should_see("Machine Learning in Cardiology Screening")
    await user.should_see("We evaluate deep learning models for ECG screening")
    await user.should_see("Incluir Artigo (I)")
    await user.should_see("Excluir Artigo (E)")
    await user.should_see("Dúvida / Talvez (M)")


# FR-25, D-036: Gravação de decisão de inclusão na tela de triagem
async def test_fr25_d036_triagem_acao_incluir(user: User) -> None:
    service = FakeScreeningDesktopService()

    @ui.page("/test-screening-action")
    def page() -> None:
        screening_view.build(service, "l-0001")

    await user.open("/test-screening-action")
    btn_include = user.find(marker="btn-screen-include")
    assert btn_include is not None
    btn_include.click()

    assert len(service.saved_calls) == 1
    call = service.saved_calls[0]
    assert call["work_id"] == "10.1016/j.cardio.2024.01"
    assert call["decision"] == "included"
    assert call["decided_by"] == "human"


# FR-26, D-037: Tela PRISMA 2020 exibe diagrama SVG e checklist PRISMA-S
async def test_fr26_d037_prisma_view_render(user: User) -> None:
    service = FakeScreeningDesktopService()

    @ui.page("/test-prisma-page")
    def page() -> None:
        prisma_view.build(service, "l-0001")

    await user.open("/test-prisma-page")
    await user.should_see("PRISMA 2020")
    await user.should_see("Diagrama PRISMA 2020")
    await user.should_see("Checklist PRISMA-S")
    await user.should_see("Declaração de Uso de IA")
    await user.should_see("Baixar Diagrama SVG")


# FR-27, D-038: Tela PRISMA 2020 exibe declaração ética de IA com conformidade COPE/SciELO e reatividade de idioma
async def test_fr27_d038_prisma_view_disclosure(user: User) -> None:
    service = FakeScreeningDesktopService()

    @ui.page("/test-prisma-disclosure")
    def page() -> None:
        prisma_view.build(service, "l-0001")

    await user.open("/test-prisma-disclosure")
    await user.should_see("Declaração de Uso de IA")
    await user.should_see("Transparência Metodológica e Ética de IA")
    await user.should_see("COPE")
    await user.should_see("Declaração de Uso de Inteligência Artificial")

    # Testa alternância de idioma de pt para en
    sel_element: ui.select = user.find(marker="lang-select").elements.pop()  # type: ignore[assignment]
    sel_element.value = "en"

    # Confere que o texto em inglês agora está visível no componente markdown
    await user.should_see("Statement on Artificial Intelligence")


# FR-25, FR-26, D-036, D-037: Tela Lista exibe botões de atalho para Triagem e PRISMA 2020
async def test_fr25_fr26_lista_view_botoes(user: User) -> None:
    service = FakeScreeningDesktopService()

    @ui.page("/test-list-screening-buttons")
    def page() -> None:
        list_view.build(service, "l-0001")

    await user.open("/test-list-screening-buttons")
    await user.should_see("Lista")
    await user.should_see("Iniciar Triagem")
    await user.should_see("PRISMA 2020")
    assert user.find(marker="btn-open-screening") is not None
    assert user.find(marker="btn-open-prisma") is not None
    assert user.find(marker="card-screening") is not None
