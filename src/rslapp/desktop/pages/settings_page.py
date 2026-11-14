"""Tela Configurações do app desktop (FR-18, D-025, D-026)."""

from __future__ import annotations

from nicegui import ui

from rslapp.desktop.pages import render_header
from rslapp.desktop.service import DesktopService


# FR-18, D-024, D-025, D-026: Esqueleto da tela Configurações (/configuracoes)
def build(service: DesktopService) -> None:
    """Monta a tela de configuração de chaves de API, e-mail e pastas."""
    _ = service
    render_header()
    with ui.column().classes("w-full max-w-4xl mx-auto p-4"):
        ui.label("Configurações").classes("text-h5 font-bold")
        ui.label("Configure as chaves de API, o e-mail de contato e as pastas locais.")
