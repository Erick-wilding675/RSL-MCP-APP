"""Testes da tela Importar arquivos bibliográficos (FR-23, D-031, D-033)."""

from __future__ import annotations

from typing import Any

from nicegui.testing import User

from rslapp.core.errors import RSLError
from rslapp.desktop.app import register_pages


class FakeImportDesktopService:
    """Serviço desktop simulado para testes da tela /importar."""

    def __init__(
        self,
        result: dict[str, Any] | None = None,
        should_fail: bool = False,
    ) -> None:
        self.result = result if result is not None else {
            "search_id": "s-0001",
            "list_id": "l-0001",
            "status": "complete",
            "total": 42,
            "page": 1,
            "next_page": 2,
            "imported_format": "ris",
            "duplicates_removed": 3,
            "works": [],
        }
        self.should_fail = should_fail
        self.import_calls: list[dict[str, Any]] = []

    def list_sources(self) -> list[dict[str, Any]]:
        return []

    def import_works(
        self,
        content: str,
        format: str = "auto",
        list_name: str = "",
    ) -> dict[str, Any]:
        self.import_calls.append({
            "content": content,
            "format": format,
            "list_name": list_name,
        })
        if self.should_fail:
            raise RSLError("invalid_input", "Formato de arquivo bibliográfico não reconhecido")
        return self.result


# FR-23, D-031, D-033: Abertura da tela /importar e estado inicial
async def test_fr23_tela_importar_abertura_e_estado_inicial(user: User) -> None:
    fake_service = FakeImportDesktopService()
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/importar")
    await user.should_see("Importar")
    await user.should_see("Importe buscas e referências exportadas do Scopus, Web of Science, Portal CAPES, Zotero e Mendeley.")
    await user.should_see("Origem dos dados bibliográficos")
    await user.should_see("Nenhuma importação realizada")

    # Verifica os elementos e controles
    assert user.find(marker="import-format-select")
    assert user.find(marker="import-name-input")
    assert user.find(marker="import-upload")
    assert user.find(marker="import-textarea")
    assert user.find(marker="import-btn")
    assert user.find(marker="import-clear-btn")


# FR-23, D-031: Tentar importar sem arquivo ou texto dispara notificação de aviso
async def test_fr23_tela_importar_clique_vazio_aviso(user: User) -> None:
    fake_service = FakeImportDesktopService()
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/importar")
    user.find(marker="import-btn").click()

    await user.should_see("Por favor, selecione um arquivo ou cole o conteúdo antes de importar.")
    assert len(fake_service.import_calls) == 0


# FR-23, D-031, D-033: Importação com sucesso exibe cartões métricos e botão de navegação
async def test_fr23_tela_importar_execucao_com_sucesso(user: User) -> None:
    fake_service = FakeImportDesktopService()
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/importar")
    sample_text = "TY  - JOUR\nTI  - Quantum Computing\nER  - "
    user.find(marker="import-textarea").type(sample_text)
    user.find(marker="import-name-input").type("Busca Quântica")
    user.find(marker="import-btn").click()

    # Aguarda a conclusão da tarefa assíncrona na interface
    await user.should_see("Importação concluída com sucesso")
    assert len(fake_service.import_calls) == 1
    call = fake_service.import_calls[0]
    assert call["content"] == sample_text.strip()
    assert call["list_name"] == "Busca Quântica"

    # Confere feedback visual
    await user.should_see("Importação concluída com sucesso")
    await user.should_see("Lista l-0001 gerada e pronta para triagem, verificação e mapas no VOSviewer.")
    await user.should_see("Artigos importados")
    await user.should_see("Duplicatas unificadas")
    assert user.find(marker="open-list-btn")


# FR-23, D-031, D-033: Tratamento de erro quando o núcleo recusa o formato
async def test_fr23_tela_importar_tratamento_de_erro(user: User) -> None:
    fake_service = FakeImportDesktopService(should_fail=True)
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/importar")
    user.find(marker="import-textarea").type("texto sem formato válido")
    user.find(marker="import-btn").click()

    await user.should_see("Erro na importação: Formato de arquivo bibliográfico não reconhecido")
