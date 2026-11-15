"""Execução do app desktop por `python -m rslapp.desktop` e ponto de entrada do PyInstaller (D-024, D-025, FR-16)."""

from __future__ import annotations

from multiprocessing import freeze_support

from nicegui import app

from rslapp.desktop.app import main
from rslapp.desktop.pages import history, list_view, search, settings_page  # noqa: F401

# D-024, D-025: Opções de app.native fora do bloco if __name__ conforme a documentação do NiceGUI
app.native.window_args.setdefault("resizable", True)

if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
