"""Testes da interface desktop para visualização de artigos retratados (FR-22, D-031, D-032)."""

from __future__ import annotations

from typing import Any

from nicegui.testing import User

from rslapp.core.errors import RSLError
from rslapp.desktop.app import register_pages


class FakeRetractionService:
    """Serviço simulado contendo listas com e sem artigos retratados."""

    def __init__(self) -> None:
        self.lists: dict[str, dict[str, Any]] = {
            # Lista 1: Com artigos retratados
            "l-0081": {
                "id": "l-0081",
                "search_id": "s-0081",
                "created_at": "2026-11-16T12:00:00Z",
                "total": 2,
                "status": "complete",
                "works": [
                    {
                        "title": "Hydroxychloroquine in COVID-19 Patients",
                        "authors": [{"name": "Mehra, Mandeep R."}],
                        "year": 2020,
                        "venue": "The Lancet",
                        "doi": "10.1016/s0140-6736(20)31180-6",
                        "is_retracted": True,
                        "retraction_details": {"source": "retraction-watch", "type": "retraction"},
                        "source_ids": {"crossref": "10.1016/s0140-6736(20)31180-6"},
                    },
                    {
                        "title": "A Normal Valid Observational Study",
                        "authors": [{"name": "Smith, Jane"}],
                        "year": 2021,
                        "venue": "BMJ",
                        "doi": "10.1136/bmj.valid",
                        "is_retracted": False,
                        "source_ids": {"openalex": "W12345"},
                    },
                ],
            },
            # Lista 2: Sem artigos retratados
            "l-0082": {
                "id": "l-0082",
                "search_id": "s-0082",
                "created_at": "2026-11-16T13:00:00Z",
                "total": 1,
                "status": "complete",
                "works": [
                    {
                        "title": "Only Valid Works Here",
                        "authors": [{"name": "Turing, Alan"}],
                        "year": 2022,
                        "venue": "Nature",
                        "doi": "10.1038/valid",
                        "is_retracted": False,
                    }
                ],
            },
        }

    def list_sources(self) -> list[dict[str, Any]]:
        return []

    def get_list(self, list_id: str) -> dict[str, Any]:
        if list_id not in self.lists:
            raise RSLError("list_not_found", f"Lista não encontrada: {list_id}")
        return self.lists[list_id]

    def get_search(self, search_id: str) -> dict[str, Any]:
        return {
            "id": search_id,
            "list_id": "l-0081",
            "created_at": "2026-11-16T12:00:00Z",
            "params": {"query": "covid-19"},
            "sources": [{"name": "crossref", "found": 1}],
        }


# FR-22, D-031, D-032: Visualização de listas com e sem retratações no app desktop
async def test_fr22_desktop_list_view_com_e_sem_retratacoes(user: User) -> None:
    fake_service = FakeRetractionService()
    register_pages(service=fake_service)  # type: ignore[arg-type]

    # 1. Lista com retratação (l-0081)
    await user.open("/lista/l-0081")
    await user.should_see("Lista")

    # Cartão de alerta de retratação no topo
    assert user.find(marker="card-retracted")
    await user.should_see("Artigo retratado")

    # Tabela com as linhas e a propriedade is_retracted
    await user.should_see(marker="works-table")
    table1 = user.find(marker="works-table").elements.pop()
    assert len(table1.rows) == 2
    assert table1.rows[0]["title"] == "Hydroxychloroquine in COVID-19 Patients"
    assert table1.rows[0]["is_retracted"] is True
    assert table1.rows[1]["title"] == "A Normal Valid Observational Study"
    assert table1.rows[1]["is_retracted"] is False

    # 2. Lista sem retratação (l-0082)
    await user.open("/lista/l-0082")
    await user.should_see("Lista")

    # Não deve existir cartão de retratação
    await user.should_not_see(marker="card-retracted")

    # Linha da tabela sem is_retracted
    table2 = user.find(marker="works-table").elements.pop()
    assert len(table2.rows) == 1
    assert table2.rows[0]["title"] == "Only Valid Works Here"
    assert table2.rows[0]["is_retracted"] is False
