"""Tela Lista do app desktop (FR-16, D-025)."""

from __future__ import annotations

from nicegui import ui

from rslapp.desktop.pages import render_header
from rslapp.desktop.service import DesktopService


# FR-16, D-024, D-025: Esqueleto da tela Lista (/lista/{list_id})
def build(service: DesktopService, list_id: str = "") -> None:
    """Monta a tela de visualização e exportação de uma lista salva."""
    _ = service
    render_header()
    with ui.column().classes("w-full max-w-4xl mx-auto p-4"):
        ui.label("Lista").classes("text-h5 font-bold")
        texto = (
            f"Visualização e exportação da lista {list_id}."
            if list_id
            else "Visualização e exportação da lista de artigos."
        )
        ui.label(texto)
