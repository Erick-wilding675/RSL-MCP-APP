"""Páginas da interface desktop do RSL.app (D-024, D-025, FR-16, FR-17, FR-18)."""

from __future__ import annotations

from nicegui import ui


# D-024, D-025, FR-16: Cabeçalho comum com o nome do app e links para as telas principais
def render_header() -> None:
    """Renderiza o cabeçalho comum com 'RSL.app' e os links Buscar, Histórico e Configurações."""
    with ui.header().classes("items-center justify-between"):
        ui.label("RSL.app").classes("text-h6 font-bold")
        with ui.row().classes("gap-4"):
            ui.link("Buscar", "/").classes("text-white")
            ui.link("Histórico", "/historico").classes("text-white")
            ui.link("Configurações", "/configuracoes").classes("text-white")
