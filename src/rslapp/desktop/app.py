"""Ponto de entrada e roteamento do app desktop em NiceGUI (D-024, D-025, D-026, FR-16)."""

from __future__ import annotations

import contextlib
import sys
from multiprocessing import freeze_support

from nicegui import app, ui

from rslapp.desktop.pages import history, list_view, search, settings_page
from rslapp.desktop.service import DesktopService
from rslapp.desktop.settings import apply_to_environ, load_settings

DESKTOP_HOST = "127.0.0.1"
DESKTOP_TITLE = "RSL.app"
DESKTOP_WINDOW_SIZE: tuple[int, int] = (1200, 800)

# D-024, D-025: Opções de app.native fora do bloco if __name__ conforme a documentação do NiceGUI
app.native.window_args.setdefault("resizable", True)

_ORIG_UI_RUN = ui.run


def _ensure_native_backend() -> None:
    """Verifica se o pywebview e o backend gráfico do sistema estão disponíveis."""
    import webview  # noqa: F401

    if sys.platform.startswith("linux") and ui.run is _ORIG_UI_RUN:
        for mod_name in ("webview.platforms.gtk", "webview.platforms.qt"):
            with contextlib.suppress(ImportError, ValueError, RuntimeError, OSError):
                __import__(mod_name)
                return
        raise RuntimeError(
            "Nenhum backend gráfico (GTK/WebKit2 ou Qt) disponível para o pywebview"
        )


# D-024, D-025, FR-16, FR-17, FR-18: Registra as quatro rotas do app desktop
def register_pages(service: DesktopService | None = None) -> DesktopService:
    """Registra as páginas /, /lista/{list_id}, /historico e /configuracoes no NiceGUI."""
    resolved_service = service if service is not None else DesktopService()

    @ui.page("/")
    def index_page() -> None:
        search.build(resolved_service)

    @ui.page("/lista/{list_id}")
    def list_detail_page(list_id: str) -> None:
        list_view.build(resolved_service, list_id)

    @ui.page("/historico")
    def history_page() -> None:
        history.build(resolved_service)

    @ui.page("/configuracoes")
    def settings_route_page() -> None:
        settings_page.build(resolved_service)

    return resolved_service


# D-024, D-025, D-026, FR-16, NFR-02: Inicia o app desktop escutando exclusivamente em 127.0.0.1
def main() -> None:
    """Carrega configurações, registra as páginas e abre a janela nativa (ou navegador local)."""
    freeze_support()
    settings = load_settings()
    apply_to_environ(settings)
    register_pages()

    try:
        _ensure_native_backend()
        ui.run(
            host="127.0.0.1",
            reload=False,
            title=DESKTOP_TITLE,
            native=True,
            window_size=DESKTOP_WINDOW_SIZE,
        )
    except (ImportError, RuntimeError, OSError, SystemExit):
        ui.run(
            host="127.0.0.1",
            reload=False,
            title=DESKTOP_TITLE,
            native=False,
            show=True,
        )


if __name__ in {"__main__", "__mp_main__"}:
    freeze_support()
    main()
