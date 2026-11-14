"""Tela Buscar do app desktop (FR-16, D-025)."""

from __future__ import annotations

from nicegui import ui

from rslapp.desktop.pages import render_header
from rslapp.desktop.service import DesktopService


# FR-16, D-024, D-025: Esqueleto da tela Buscar (/)
def build(service: DesktopService) -> None:
    """Monta a tela de busca de artigos acadêmicos."""
    _ = service
    render_header()
    with ui.column().classes("w-full max-w-4xl mx-auto p-4"):
        ui.label("Buscar").classes("text-h5 font-bold")
        ui.label("Busque artigos nas bases acadêmicas configuradas.")
