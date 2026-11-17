"""Testes da tela de Roteiros Metodológicos e integração com a busca (FR-10, FR-16, D-031, D-035)."""

from __future__ import annotations

from nicegui import ui
from nicegui.testing import User

from rslapp.desktop.app import register_pages
from rslapp.desktop.pages import guidelines_view
from rslapp.desktop.service import DesktopService


# FR-10, D-035: Abertura da tela /roteiros com abas e cabeçalho metodológico
async def test_fr10_d035_tela_roteiros_abertura_e_abas(user: User) -> None:
    service = DesktopService()

    @ui.page("/test-roteiros-view")
    def page() -> None:
        guidelines_view.build(service)

    await user.open("/test-roteiros-view")
    await user.should_see("Roteiros")
    await user.should_see("Metodologia Científica e Rigor Acadêmico")
    await user.should_see("Revisão de Escopo (PCC)")
    await user.should_see("Revisão Integrativa (6 Fases)")
    await user.should_see("Revisão Sistemática (PICO)")
    await user.should_see("Estudo Bibliométrico (VOSviewer)")


# FR-10, D-035: Roteiro de escopo gera conteúdo estruturado JBI e PCC
async def test_fr10_d035_roteiro_escopo_gera_conteudo(user: User) -> None:
    service = DesktopService()

    @ui.page("/test-scoping-generation")
    def page() -> None:
        guidelines_view.build(service)

    await user.open("/test-scoping-generation")
    topic_input = user.find(marker="scoping-topic")
    topic_input.type("Inteligência Artificial na Educação")

    output_area = user.find(marker="scoping-output").elements.pop()
    text = output_area.value
    assert "JBI" in text
    assert "PRISMA-ScR" in text
    assert "Inteligência Artificial na Educação" in text
    assert "bdtd" in text.lower()


# FR-10, D-035: Botões de copiar e navegar para a busca
async def test_fr10_d035_botoes_acao_roteiro(user: User) -> None:
    service = DesktopService()

    @ui.page("/test-roteiros-buttons")
    def page() -> None:
        guidelines_view.build(service)

    await user.open("/test-roteiros-buttons")
    copy_btn = user.find(marker="scoping-copy-btn")
    assert copy_btn is not None
    search_btn = user.find(marker="scoping-search-btn")
    assert search_btn is not None


# FR-16, D-035: Tela de busca aceita query inicial e mostra fonte BDTD
async def test_fr16_d035_busca_com_initial_query_e_bdtd(user: User) -> None:
    register_pages()
    await user.open("/?q=revisao+sistematica")
    await user.should_see("Buscar")
    await user.should_see("BDTD (Teses e Dissertações)")

    query_input = user.find(marker="query-input").elements.pop()
    assert query_input.value == "revisao sistematica"

    bdtd_cb = user.find(marker="source-bdtd")
    assert bdtd_cb is not None
