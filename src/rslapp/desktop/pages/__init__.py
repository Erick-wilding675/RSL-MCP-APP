"""Casca comum da interface desktop do RSL.app (D-024, D-025, D-031, FR-16)."""

from __future__ import annotations

from nicegui import ui

from rslapp import __version__
from rslapp.desktop.settings import get_theme, set_theme
from rslapp.desktop.theme import apply_theme

# D-031, FR-16: Itens de navegação lateral na ordem exata da spec: Buscar, Histórico, Conectar IA, Configurações
NAV_ITEMS: tuple[tuple[str, str, str], ...] = (
    ("Buscar", "search", "/"),
    ("Histórico", "history", "/historico"),
    ("Conectar IA", "hub", "/conectar"),
    ("Configurações", "settings", "/configuracoes"),
)

THEME_ICONS: dict[str, str] = {
    "auto": "brightness_auto",
    "light": "light_mode",
    "dark": "dark_mode",
}

THEME_TOOLTIPS: dict[str, str] = {
    "auto": "Tema: automático (sistema)",
    "light": "Tema: claro",
    "dark": "Tema: escuro",
}


# D-031, FR-16: Casca comum com navegação lateral (drawer) e barra superior de conteúdo
def render_shell(
    title: str,
    subtitle: str = "",
    *,
    active: str | None = None,
) -> None:
    """Renderiza a casca da página com navegação lateral e barra superior da área de conteúdo."""
    # Garante que o tema foi inicializado
    dm = getattr(getattr(ui.context, "client", None), "_rsl_dark_mode", None)
    if dm is None:
        dm = apply_theme()

    current_active = active or ("Buscar" if title == "Lista" else title)
    theme_state = get_theme()

    # D-031: Navegação lateral recolhe para só ícones abaixo de 1000px
    with (
        ui.left_drawer(value=True, bordered=True)
        .props(
            'breakpoint=0 :mini="$q.screen.width < 1000" :width="260" :mini-width="72"'
        )
        .classes("p-3 flex flex-col justify-between select-none")
    ):
        with ui.column().classes("w-full gap-3"):
            # Topo com nome e frase orientadora
            with ui.column().classes("px-3 py-2 gap-0.5"):
                ui.label("RSL.app").classes(
                    "text-xl font-bold tracking-tight text-primary cursor-pointer"
                ).on("click", lambda: ui.navigate.to("/"))
                ui.label("Revisão sistemática com IA rastreável").classes(
                    "text-xs text-grey-6 leading-tight drawer-full-only"
                )

            # Itens de navegação
            with ui.column().classes("w-full gap-1"):
                for name, icon, path in NAV_ITEMS:
                    is_active = name == current_active
                    with (
                        ui.item(on_click=lambda p=path: ui.navigate.to(p))
                        .classes(
                            f"nav-item-{'active' if is_active else 'inactive'} "
                            "cursor-pointer w-full my-0.5 px-3 py-2"
                        )
                        .mark(f"nav-{icon}")
                    ):
                        with ui.item_section().props("avatar"):
                            ui.icon(icon).classes(
                                "text-primary text-xl"
                                if is_active
                                else "text-grey-7 dark:text-grey-3 text-xl"
                            )
                        with ui.item_section():
                            ui.label(name).classes(
                                "font-semibold text-sm"
                                if is_active
                                else "font-medium text-sm text-grey-8 dark:text-grey-2"
                            )
                        ui.tooltip(name)

        # Pé do drawer com versão e alternador de tema
        with (
            ui.column().classes(
                "w-full pt-3 border-t border-grey-3 dark:border-grey-8 gap-2"
            ),
            ui.row().classes(
                "w-full items-center justify-between px-2 drawer-footer-row"
            ),
        ):
            ui.label(f"v{__version__}").classes(
                "text-xs text-grey-5 font-mono drawer-full-only"
            ).mark("app-version-label")

            def _cycle_theme() -> None:
                nonlocal theme_state
                if theme_state == "auto":
                    next_theme = "light"
                elif theme_state == "light":
                    next_theme = "dark"
                else:
                    next_theme = "auto"
                theme_state = next_theme
                set_theme(next_theme)
                if dm is not None:
                    if next_theme == "light":
                        dm.disable()
                    elif next_theme == "dark":
                        dm.enable()
                    else:
                        dm.auto()
                theme_btn.props(f"icon={THEME_ICONS.get(next_theme, 'brightness_auto')}")
                theme_tooltip.text = THEME_TOOLTIPS.get(
                    next_theme, "Tema: automático (sistema)"
                )

            theme_btn = (
                ui.button(
                    icon=THEME_ICONS.get(theme_state, "brightness_auto"),
                    on_click=_cycle_theme,
                )
                .props("flat round dense")
                .mark("theme-toggle-btn")
            )
            with theme_btn:
                theme_tooltip = ui.tooltip(
                    THEME_TOOLTIPS.get(theme_state, "Tema: automático (sistema)")
                ).mark("theme-tooltip")

    # D-031, FR-16: Barra de cima da área de conteúdo com título e subtítulo idêntico
    with ui.column().classes("w-full gap-1 mb-4"):
        ui.label(title).classes("page-title text-2xl font-bold")
        if subtitle:
            ui.label(subtitle).classes("text-sm text-grey-7 dark:text-grey-4")


# D-024, D-025: Mantém compatibilidade com chamadas legadas a render_header
def render_header() -> None:
    """Função legada: delega para render_shell mantendo compatibilidade."""
    render_shell("RSL.app", "")
