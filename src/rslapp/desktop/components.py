"""Peças comuns de interface do app desktop (D-031, FR-16)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar

from nicegui import ui


# D-031, FR-16: Cartão com cabeçalho (título, ícone e descrição opcionais), usado com with
class section_card(ui.card):
    """Cartão de seção com cabeçalho padronizado. Usado com o bloco 'with'."""

    def __init__(
        self,
        title: str,
        icon: str | None = None,
        description: str | None = None,
    ) -> None:
        super().__init__()
        self.classes("w-full p-5 gap-3")
        with self:
            with ui.row().classes("items-center gap-2 w-full"):
                if icon:
                    ui.icon(icon).classes("text-primary text-xl")
                ui.label(title).classes(
                    "text-base font-semibold text-grey-9 dark:text-grey-1"
                )
            if description:
                ui.label(description).classes(
                    "text-xs text-grey-6 dark:text-grey-4 -mt-1"
                )


# D-031, FR-16: Estado vazio com ícone suave, título, frase de orientação e botão de ação
class empty_state(ui.column):
    """Componente para estados vazios com ícone, orientações e próximo passo."""

    def __init__(
        self,
        icon: str,
        title: str,
        text: str,
        action_label: str | None = None,
        action_target: str | Callable[[], Any] | None = None,
    ) -> None:
        super().__init__()
        self.classes("w-full items-center justify-center p-8 gap-3 text-center")
        with self:
            ui.icon(icon).classes("text-5xl text-grey-4 dark:text-grey-6")
            ui.label(title).classes(
                "text-lg font-semibold text-grey-8 dark:text-grey-2"
            )
            ui.label(text).classes(
                "text-sm text-grey-6 dark:text-grey-4 max-w-md"
            )
            if action_label and action_target:
                on_click = (
                    action_target
                    if callable(action_target)
                    else (lambda target=action_target: ui.navigate.to(target))
                )
                ui.button(action_label, on_click=on_click).props("outline").classes(
                    "mt-2"
                )


# D-031, FR-16: Selo pequeno com cores semânticas (ok, warning, error, info, neutral)
class status_badge(ui.badge):
    """Selo de status compacto com cor baseada no tipo informado."""

    KIND_COLORS: ClassVar[dict[str, str]] = {
        "ok": "positive",
        "warning": "warning",
        "error": "negative",
        "info": "info",
        "neutral": "grey-6",
    }

    def __init__(self, text: str, kind: str = "neutral") -> None:
        color = self.KIND_COLORS.get(kind, "grey-6")
        super().__init__(text, color=color)
        self.classes("text-xs px-2 py-0.5 rounded-full font-medium")


# D-031, FR-16: Bloco de código monoespaçado com botão Copiar
class copy_block(ui.row):
    """Bloco monoespaçado para comandos ou trechos de código com botão de cópia."""

    def __init__(self, text: str, mark: str | None = None) -> None:
        super().__init__()
        self.classes("w-full items-center gap-2")
        if mark:
            self.mark(mark)

        def _copy() -> None:
            ui.clipboard.write(text)
            ui.notify("Copiado para a área de transferência.", type="positive")

        with self:
            lbl = ui.label(text).classes(
                "font-mono text-xs bg-grey-2 dark:bg-grey-9 p-2 rounded flex-grow "
                "whitespace-pre-wrap break-all text-grey-9 dark:text-grey-2"
            )
            if mark:
                lbl.mark(f"{mark}-text")
            btn = (
                ui.button("Copiar", on_click=_copy)
                .props("outline size=sm")
                .classes("shrink-0")
            )
            if mark:
                btn.mark(f"{mark}-btn")
