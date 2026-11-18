"""Testes das páginas de Fichamento Científico do app desktop (FR-29, D-040)."""

from __future__ import annotations

from typing import Any

from nicegui import ui
from nicegui.testing import User

from rslapp.desktop.pages import note_view
from rslapp.desktop.service import DesktopService


class FakeNotesDesktopService(DesktopService):
    """Serviço simulado para testar as telas de fichamento científico."""

    def __init__(self) -> None:
        self.lists: dict[str, dict[str, Any]] = {
            "l-0001": {
                "id": "l-0001",
                "search_id": "s-0001",
                "total": 2,
                "created_at": "2026-11-18T10:00:00Z",
                "works": [
                    {
                        "id": "W1",
                        "doi": "10.1016/j.edu.2024.01",
                        "title": "Inteligência Artificial no Ensino Superior",
                        "year": 2024,
                        "authors": [{"name": "Mendes, Erick"}],
                        "venue": "Revista Brasileira de Educação",
                        "source": "openalex",
                    },
                    {
                        "id": "W2",
                        "doi": "10.1016/j.edu.2024.02",
                        "title": "Metodologia de Revisão Sistemática",
                        "year": 2023,
                        "authors": [{"name": "Silva, Ana"}],
                        "venue": "Educação em Foco",
                        "source": "bdtd",
                    },
                ],
            }
        }
        self.notes: dict[str, dict[str, Any]] = {
            "W1": {
                "list_id": "l-0001",
                "work_id": "W1",
                "title": "Inteligência Artificial no Ensino Superior",
                "authors": ["Mendes, Erick"],
                "year": 2024,
                "doi": "10.1016/j.edu.2024.01",
                "abnt_reference": "MENDES, Erick. Inteligência Artificial no Ensino Superior. 2024.",
                "objective": "Analisar o impacto pedagógico de ferramentas generativas.",
                "source": "ai_suggested",
                "ai_model": "Claude 3.5 Sonnet",
            }
        }
        self.saved_notes: list[dict[str, Any]] = []

    def get_list(self, list_id: str) -> dict[str, Any]:
        if list_id in self.lists:
            return self.lists[list_id]
        from rslapp.core.errors import RSLError
        raise RSLError("list_not_found", f"Lista não encontrada: {list_id}")

    def get_work_note(self, list_id: str, work_id: str | int) -> dict[str, Any] | None:
        return self.notes.get(str(work_id))

    def list_work_notes(self, list_id: str) -> list[dict[str, Any]]:
        return list(self.notes.values())

    def save_work_note(self, list_id: str, note_data: dict[str, Any]) -> dict[str, Any]:
        self.saved_notes.append(note_data)
        work_id = str(note_data["work_id"])
        self.notes[work_id] = note_data
        return note_data


async def test_fr29_notes_list_view(user: User) -> None:
    service = FakeNotesDesktopService()

    @ui.page("/test_notes_list")
    def page() -> None:
        note_view.build_list(service, "l-0001")

    await user.open("/test_notes_list")
    await user.should_see("Fichamento Científico · Lista l-0001")
    await user.should_see("Total de Artigos")
    await user.should_see("Artigos Fichados")
    await user.should_see("Sugestões de IA")
    await user.should_see(ui.table)
    table = user.find(ui.table).elements.pop()
    assert table.rows[0]["title"] == "Inteligência Artificial no Ensino Superior"
    assert table.rows[0]["status"] == "Sugerido por IA"
    assert table.rows[1]["status"] == "Sem ficha"


async def test_fr29_note_detail_view_and_save(user: User) -> None:
    service = FakeNotesDesktopService()

    @ui.page("/test_note_detail")
    def page() -> None:
        note_view.build(service, "l-0001", "W1")

    await user.open("/test_note_detail")
    await user.should_see("Inteligência Artificial no Ensino Superior")
    await user.should_see("MENDES, Erick")
    await user.should_see("Rastro Metodológico de Autoria")
    await user.should_see("1. Objetivo da Pesquisa")
    await user.should_see("Analisar o impacto pedagógico de ferramentas generativas.")

    # Clica no botão Salvar Ficha
    user.find(marker="btn-save-note").click()
    assert len(service.saved_notes) >= 1
    last_saved = service.saved_notes[-1]
    assert last_saved["work_id"] == "W1"


async def test_fr29_note_validate_as_reviewed(user: User) -> None:
    service = FakeNotesDesktopService()

    @ui.page("/test_note_validate")
    def page() -> None:
        note_view.build(service, "l-0001", "W1")

    await user.open("/test_note_validate")
    # Clica em Validar como Revisado
    user.find(marker="btn-validate-reviewed").click()
    assert len(service.saved_notes) >= 1
    last_saved = service.saved_notes[-1]
    assert last_saved["source"] == "human_reviewed"
