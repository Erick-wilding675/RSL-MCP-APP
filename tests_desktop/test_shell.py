"""Testes da casca comum: navegação lateral (drawer), alternador de tema e barra de topo (D-031, FR-16)."""

from __future__ import annotations

from pathlib import Path

import pytest
from nicegui import ui
from nicegui.testing import User

from rslapp import __version__
from rslapp.desktop.app import register_pages
from rslapp.desktop.pages import NAV_ITEMS, render_shell
from rslapp.desktop.settings import get_theme, set_theme


# D-031, FR-16: A casca monta o drawer com os quatro itens na ordem da spec, logo e versão
async def test_d031_fr16_casca_itens_drawer_e_versao(user: User) -> None:
    @ui.page("/test-shell-drawer")
    def page() -> None:
        render_shell("Buscar", "Subtítulo de teste")

    await user.open("/test-shell-drawer")
    await user.should_see("RSL.app")
    await user.should_see("Revisão sistemática com IA rastreável")

    # Os 8 itens na ordem: Buscar, Protocolos, Verificar, Importar, Roteiros, Histórico, Conectar IA, Configurações
    labels = [item[0] for item in NAV_ITEMS]
    assert labels == [
        "Buscar",
        "Protocolos",
        "Verificar",
        "Importar",
        "Roteiros",
        "Histórico",
        "Conectar IA",
        "Configurações",
    ]
    for label in labels:
        await user.should_see(label)

    # Versão do app
    await user.should_see(f"v{__version__}")
    # Título e subtítulo na barra de topo
    await user.should_see("Buscar")
    await user.should_see("Subtítulo de teste")


# D-031, FR-16: O item ativo recebe a classe de destaque nav-item-active
async def test_d031_fr16_item_ativo_destacado(user: User) -> None:
    @ui.page("/test-active-history")
    def page_hist() -> None:
        render_shell("Histórico", "Subtítulo")

    await user.open("/test-active-history")
    hist_item = user.find(marker="nav-history").elements.pop()
    assert "nav-item-active" in hist_item._classes

    search_item = user.find(marker="nav-search").elements.pop()
    assert "nav-item-inactive" in search_item._classes

    # Na tela Lista, o item ativo padrão é Buscar
    @ui.page("/test-active-lista")
    def page_lista() -> None:
        render_shell("Lista", "")

    await user.open("/test-active-lista")
    search_item_lista = user.find(marker="nav-search").elements.pop()
    assert "nav-item-active" in search_item_lista._classes


# D-031: O botão de tema alterna auto -> light -> dark -> auto e grava no desktop.json
async def test_d031_botao_tema_alterna_e_persiste(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    user: User,
) -> None:
    cfg_file = tmp_path / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))
    set_theme("auto")

    @ui.page("/test-toggle-theme")
    def page_toggle() -> None:
        render_shell("Buscar", "Sub")

    await user.open("/test-toggle-theme")
    assert get_theme() == "auto"

    btn = user.find(marker="theme-toggle-btn")
    # 1. Clique de auto -> light
    btn.click()
    assert get_theme() == "light"

    # 2. Clique de light -> dark
    btn.click()
    assert get_theme() == "dark"

    # 3. Clique de dark -> auto
    btn.click()
    assert get_theme() == "auto"


# D-024, D-025, D-031, FR-16: Todas as cinco telas abrem com apply_theme e render_shell
async def test_d031_fr16_todas_as_telas_abrem_com_casca(user: User) -> None:
    register_pages()

    # 1. Buscar (/)
    await user.open("/")
    await user.should_see("RSL.app")
    await user.should_see("Buscar")
    await user.should_see("Busque artigos nas bases acadêmicas configuradas.")

    # 2. Lista (/lista/l-0001)
    await user.open("/lista/l-0001")
    await user.should_see("RSL.app")
    await user.should_see("Lista")

    # 3. Verificar (/verificar)
    await user.open("/verificar")
    await user.should_see("RSL.app")
    await user.should_see("Verificar")
    await user.should_see("Verifique se referências citadas existem nas bases reais contra alucinações de IA.")

    # 4. Roteiros (/roteiros)
    await user.open("/roteiros")
    await user.should_see("RSL.app")
    await user.should_see("Roteiros")
    await user.should_see("Roteiros e protocolos metodológicos para planejamento de revisões e estudos bibliométricos.")

    # 4. Histórico (/historico)
    await user.open("/historico")
    await user.should_see("RSL.app")
    await user.should_see("Histórico")
    await user.should_see(
        "Consulte as buscas já feitas, repita uma busca ou abra o log."
    )

    # 4. Conectar IA (/conectar)
    await user.open("/conectar")
    await user.should_see("RSL.app")
    await user.should_see("Conectar IA")
    await user.should_see(
        "Ligue a sua IA ao RSL.app deste computador. As buscas que ela fizer "
        "ficam na sua pasta de dados e aparecem no Histórico."
    )

    # 5. Configurações (/configuracoes)
    await user.open("/configuracoes")
    await user.should_see("RSL.app")
    await user.should_see("Configurações")
    await user.should_see(
        "Configure as chaves de API, o e-mail de contato e as pastas locais."
    )
