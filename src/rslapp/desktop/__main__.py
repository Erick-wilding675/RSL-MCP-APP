"""Execução do app desktop por `python -m rslapp.desktop` (D-024, D-025, FR-16)."""

from __future__ import annotations

from multiprocessing import freeze_support

from rslapp.desktop.app import main

if __name__ in {"__main__", "__mp_main__"}:
    freeze_support()
    main()
