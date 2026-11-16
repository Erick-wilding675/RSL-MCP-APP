"""Testes das peças comuns de interface do app desktop (D-031, FR-16)."""

from __future__ import annotations

from nicegui import ui
from nicegui.testing import User

from rslapp.desktop.components import (
    copy_block,
    empty_state,
    section_card,
    status_badge,
)


# D-031, FR-16: section_card monta cabeçalho com título, ícone, descrição e aceita filhos com with
async def test_d031_fr16_section_card_monta_com_filhos(user: User) -> None:
    @ui.page("/test-section-card")
    def page() -> None:
        with section_card("Seção Teste", icon="settings", description="Descrição auxiliar"):
            ui.label("Conteúdo interno da seção").mark("inner-label")

    await user.open("/test-section-card")
    await user.should_see("Seção Teste")
    await user.should_see("Descrição auxiliar")
    await user.should_see("Conteúdo interno da seção")


# D-031, FR-16: empty_state monta ícone, título, texto orientador e botão de ação
async def test_d031_fr16_empty_state_monta_com_acao(user: User) -> None:
    @ui.page("/test-empty-state")
    def page() -> None:
        empty_state(
            icon="search_off",
            title="Nenhum artigo encontrado",
            text="Tente reformular a string de busca.",
            action_label="Voltar",
            action_target="/",
        )

    await user.open("/test-empty-state")
    await user.should_see("Nenhum artigo encontrado")
    await user.should_see("Tente reformular a string de busca.")
    await user.should_see("Voltar")


# D-031, FR-16: status_badge monta os selos para cada tipo com as cores corretas
async def test_d031_fr16_status_badge_monta_tipos(user: User) -> None:
    @ui.page("/test-status-badge")
    def page() -> None:
        status_badge("Ativo", kind="ok").mark("badge-ok")
        status_badge("Atenção", kind="warning").mark("badge-warn")
        status_badge("Erro", kind="error").mark("badge-err")
        status_badge("Info", kind="info").mark("badge-info")
        status_badge("Neutro", kind="neutral").mark("badge-neutral")

    await user.open("/test-status-badge")
    await user.should_see("Ativo")
    await user.should_see("Atenção")
    await user.should_see("Erro")
    await user.should_see("Info")
    await user.should_see("Neutro")

    b_ok = user.find(marker="badge-ok").elements.pop()
    assert b_ok._props.get("color") == "positive"

    b_err = user.find(marker="badge-err").elements.pop()
    assert b_err._props.get("color") == "negative"


# D-031, FR-16: copy_block monta bloco de código monoespaçado e botão Copiar
async def test_d031_fr16_copy_block_monta_com_botao_copiar(user: User) -> None:
    @ui.page("/test-copy-block")
    def page() -> None:
        copy_block("pip install rslapp", mark="cmd-block")

    await user.open("/test-copy-block")
    await user.should_see("pip install rslapp")
    await user.should_see("Copiar")

    # Confere marcas dos subelementos
    user.find(marker="cmd-block-text")
    btn = user.find(marker="cmd-block-btn").elements.pop()
    assert btn.text == "Copiar"
