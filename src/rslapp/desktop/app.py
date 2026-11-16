"""Ponto de entrada e roteamento do app desktop em NiceGUI (D-024, D-025, D-026, D-028, FR-16, FR-19)."""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
from collections.abc import Sequence
from multiprocessing import freeze_support

from rslapp import server
from rslapp.desktop.service import DesktopService
from rslapp.desktop.settings import (
    apply_to_environ,
    capture_system_env_vars,
    load_settings,
)

DESKTOP_HOST = "127.0.0.1"
DESKTOP_TITLE = "RSL.app"
DESKTOP_WINDOW_SIZE: tuple[int, int] = (1200, 800)


# D-025, D-028, FR-16, FR-19: Parser de linha de comando do app desktop (--check e --mcp mutuamente exclusivos)
def build_parser() -> argparse.ArgumentParser:
    """Cria o parser de argumentos de linha de comando do app desktop."""
    parser = argparse.ArgumentParser(
        prog="rslapp-desktop",
        description="Inicia o aplicativo desktop do RSL.app ou o servidor MCP por stdio.",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--check",
        action="store_true",
        help="Importa os módulos do app, registra as páginas e sai com código 0 sem abrir janela.",
    )
    mode_group.add_argument(
        "--mcp",
        action="store_true",
        help="Inicia o servidor MCP por stdio usando as configurações salvas do app, sem abrir janela.",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Interpreta os argumentos do app desktop e decide se roda em modo --check, --mcp ou janela."""
    parser = build_parser()
    args_list = list(sys.argv[1:] if argv is None else argv)
    return parser.parse_args(args_list)


def _ensure_stdio_streams() -> None:
    """Garante sys.stdout e sys.stderr válidos no executável Windows empacotado com --windowed."""
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115


def _ensure_native_backend() -> None:
    """Verifica se o pywebview e o backend gráfico do sistema estão disponíveis."""
    import webview  # noqa: F401

    if sys.platform.startswith("linux"):
        for mod_name in ("webview.platforms.gtk", "webview.platforms.qt"):
            with contextlib.suppress(ImportError, ValueError, RuntimeError, OSError):
                __import__(mod_name)
                return
        raise RuntimeError(
            "Nenhum backend gráfico (GTK/WebKit2 ou Qt) disponível para o pywebview"
        )


# D-024, D-025, D-028, FR-16, FR-17, FR-18, FR-19: Registra as rotas do app desktop
def register_pages(service: DesktopService | None = None) -> DesktopService:
    """Registra as páginas /, /lista/{list_id}, /historico, /conectar e /configuracoes no NiceGUI."""
    from nicegui import app, ui

    from rslapp.desktop.pages import (
        connect_page,
        history,
        list_view,
        search,
        settings_page,
    )

    app.native.window_args.setdefault("resizable", True)
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

    @ui.page("/conectar")
    def connect_route_page() -> None:
        connect_page.build(resolved_service)

    @ui.page("/configuracoes")
    def settings_route_page() -> None:
        settings_page.build(resolved_service)

    return resolved_service


# FR-16, D-025: No Windows, valida a carga do pythonnet e das DLLs do WebView2 / WinForms
def _ensure_windows_dotnet() -> None:
    """Carrega o pythonnet e as DLLs do WebView2 que a janela nativa utiliza no Windows."""
    try:
        try:
            import clr
        except (ImportError, RuntimeError, OSError):
            os.environ["PYTHONNET_RUNTIME"] = "coreclr"
            import clr

        clr.AddReference("System.Windows.Forms")
        clr.AddReference("System.Collections")
        clr.AddReference("System.Threading")
        clr.AddReference("System.Reflection")

        from webview.platforms import winforms  # noqa: F401
        from webview.util import interop_dll_path

        clr.AddReference(interop_dll_path("Microsoft.Web.WebView2.Core.dll"))
        clr.AddReference(interop_dll_path("Microsoft.Web.WebView2.WinForms.dll"))
        from Microsoft.Web.WebView2.Core import CoreWebView2Cookie  # noqa: F401
        from Microsoft.Web.WebView2.WinForms import WebView2  # noqa: F401
    except Exception as exc:
        if sys.stderr is not None:
            print(
                f"Erro ao carregar .NET / WebView2 no Windows: {exc}",
                file=sys.stderr,
            )
        raise SystemExit(1) from exc


# D-025, FR-16: Executa a verificação de fumaça (--check) sem iniciar servidor nem abrir janela
def _run_check() -> None:
    """Importa o núcleo, as fontes, o NiceGUI e as páginas e registra as rotas sem chamar ui.run."""
    from rslapp.core.repeat import run_repeat  # noqa: F401
    from rslapp.core.search import run_search  # noqa: F401
    from rslapp.exporters import run_export  # noqa: F401
    from rslapp.sources import build_sources, list_sources_info  # noqa: F401

    # FR-16, D-025: No Windows, garante que pythonnet e WebView2 carregam sem abrir janela
    if sys.platform == "win32":
        _ensure_windows_dotnet()

    service = register_pages()
    build_sources(include_paid=True)
    service.list_sources()


def _run_ui() -> None:
    """Abre a janela nativa em 127.0.0.1 ou recua para o navegador local se não houver backend nativo."""
    from nicegui import app, ui

    app.native.window_args.setdefault("resizable", True)
    try:
        _ensure_native_backend()
        ui.run(
            host=DESKTOP_HOST,
            reload=False,
            title=DESKTOP_TITLE,
            native=True,
            window_size=DESKTOP_WINDOW_SIZE,
        )
    except (ImportError, RuntimeError, OSError, SystemExit):
        ui.run(
            host=DESKTOP_HOST,
            reload=False,
            title=DESKTOP_TITLE,
            native=False,
            show=True,
        )


# D-024, D-025, D-026, D-028, FR-16, FR-19, NFR-02: Inicia o app desktop em 127.0.0.1, verifica (--check) ou serve MCP (--mcp)
def main(argv: Sequence[str] | None = None) -> int:
    """Carrega configurações, registra as páginas e abre a janela nativa (ou roda --check / --mcp)."""
    freeze_support()
    args = parse_args(argv)

    # D-026, D-028, FR-19: No modo --mcp preserva stdin/stdout reais e inicia o servidor MCP por stdio
    if args.mcp:
        if sys.stdin is None or sys.stdout is None:
            if sys.stderr is not None:
                print(
                    "Erro: o modo --mcp exige stdin e stdout disponíveis.",
                    file=sys.stderr,
                )
            return 1
        capture_system_env_vars()
        settings = load_settings()
        apply_to_environ(settings)
        server.main()
        return 0

    _ensure_stdio_streams()
    capture_system_env_vars()
    settings = load_settings()
    apply_to_environ(settings)

    if args.check:
        try:
            _run_check()
        except SystemExit as exc:
            return exc.code if isinstance(exc.code, int) else 1
        return 0

    register_pages()
    _run_ui()
    return 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
