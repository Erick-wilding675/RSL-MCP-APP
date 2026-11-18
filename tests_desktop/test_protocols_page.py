"""Testes das páginas de Protocolo Metodológico Pré-Busca do app desktop (FR-30, D-041)."""

from __future__ import annotations

from typing import Any

from nicegui import ui
from nicegui.testing import User

from rslapp.desktop.pages import protocol_view
from rslapp.desktop.service import DesktopService


class FakeProtocolsDesktopService(DesktopService):
    """Serviço simulado para testar as telas de protocolo metodológico."""

    def __init__(self) -> None:
        self.protocols: dict[str, dict[str, Any]] = {
            "prot_0001": {
                "id": "prot_0001",
                "title": "Protocolo sobre IA na Educação Médica",
                "framework": "pico",
                "question": "Como tutores de IA melhoram o aprendizado clínico?",
                "subquestions": ["Qual o impacto na retenção de conteúdo?"],
                "components": {
                    "population": "Estudantes de medicina",
                    "intervention": "Tutores baseados em LLM",
                    "comparison": "Ensino tradicional",
                    "outcome": "Acurácia no diagnóstico",
                },
                "inclusion_criteria": ["Ensaios randomizados"],
                "exclusion_criteria": ["Opiniões de especialistas"],
                "planned_sources": ["openalex", "pubmed"],
                "search_strategy": "AI AND 'medical education'",
                "languages": ["pt", "en"],
                "date_range": {"start_year": 2020, "end_year": 2026},
                "authors": ["Erick Mendes"],
                "status": "registered",
                "registration_platform": "PROSPERO",
                "registration_number": "CRD42026111111",
                "version": 1,
                "created_at": "2026-11-18T10:00:00Z",
                "updated_at": "2026-11-18T10:00:00Z",
                "ai_assisted": True,
                "ai_model": "Claude 3.5 Sonnet",
            }
        }
        self.saved_protocols: list[dict[str, Any]] = []

    def list_protocols(self) -> list[dict[str, Any]]:
        return list(self.protocols.values())

    def get_protocol(self, protocol_id: str, version: int | None = None) -> dict[str, Any] | None:
        return self.protocols.get(protocol_id)

    def save_protocol(self, protocol_data: dict[str, Any]) -> dict[str, Any]:
        data = dict(protocol_data)
        pid = data.get("id") or "prot_new_123"
        data["id"] = pid
        data["version"] = data.get("version", 1)
        self.protocols[pid] = data
        self.saved_protocols.append(data)
        return data

    def delete_protocol(self, protocol_id: str) -> bool:
        if protocol_id in self.protocols:
            del self.protocols[protocol_id]
            return True
        return False


async def test_fr30_protocols_list_view(user: User) -> None:
    service = FakeProtocolsDesktopService()

    @ui.page("/test_protocols_list")
    def page() -> None:
        protocol_view.build_list(service)

    await user.open("/test_protocols_list")
    await user.should_see("Protocolos Metodológicos Pré-Busca")
    await user.should_see("Total de Protocolos")
    await user.should_see("Registrados (PROSPERO/OSF)")
    await user.should_see("Novo Protocolo")
    await user.should_see(ui.table)
    table = user.find(ui.table).elements.pop()
    assert table.rows[0]["title"] == "Protocolo sobre IA na Educação Médica"
    assert table.rows[0]["framework"] == "PICO"
    assert table.rows[0]["version"] == "v1"
    assert table.rows[0]["status"] == "Registrado"


async def test_fr30_protocol_editor_load_existing(user: User) -> None:
    service = FakeProtocolsDesktopService()

    @ui.page("/test_protocol_edit")
    def page() -> None:
        protocol_view.build_editor(service, protocol_id="prot_0001")

    await user.open("/test_protocol_edit")
    await user.should_see("Editar Protocolo")
    await user.should_see("Versão Atual: v1")
    await user.should_see("Identificação Geral e Registro")
    await user.should_see("Pergunta de Pesquisa e Framework Metodológico")
    await user.should_see("Critérios Formais de Elegibilidade (Inclusão e Exclusão)")
    await user.should_see("Salvar Protocolo")
    await user.should_see("Copiar Markdown (PROSPERO/OSF)")


async def test_fr30_protocol_editor_create_and_save(user: User) -> None:
    service = FakeProtocolsDesktopService()

    @ui.page("/test_protocol_new")
    def page() -> None:
        protocol_view.build_editor(service, protocol_id=None)

    await user.open("/test_protocol_new")
    await user.should_see("Novo Protocolo")

    # Preenche título e pergunta de pesquisa
    user.find(marker="input-protocol-title").type("Novo Protocolo de Escopo PCC")
    user.find(marker="input-protocol-question").type("Como o RSL.app opera com IA?")
    user.find(marker="input-protocol-inclusion").type("Artigos empíricos")
    user.find(marker="input-protocol-exclusion").type("Editoriais")

    # Salva
    user.find(marker="btn-save-protocol").click()
    assert len(service.saved_protocols) == 1
    saved = service.saved_protocols[0]
    assert saved["title"] == "Novo Protocolo de Escopo PCC"
    assert saved["question"] == "Como o RSL.app opera com IA?"
    assert "Artigos empíricos" in saved["inclusion_criteria"]
    assert "Editoriais" in saved["exclusion_criteria"]
