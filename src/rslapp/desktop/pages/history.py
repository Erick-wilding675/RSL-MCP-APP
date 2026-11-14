"""Tela Histórico do app desktop (FR-17, D-025)."""

from __future__ import annotations

from nicegui import ui

from rslapp.desktop.pages import render_header
from rslapp.desktop.service import DesktopService


# FR-17, D-024, D-025: Esqueleto da tela Histórico (/historico)
def build(service: DesktopService) -> None:
    """Monta a tela de histórico de buscas e acesso ao log metodológico."""
    _ = service
    render_header()
    with ui.column().classes("w-full max-w-4xl mx-auto p-4"):
        ui.label("Histórico").classes("text-h5 font-bold")
        ui.label("Consulte as buscas já feitas, repita uma busca ou abra o log.")
