"""Testes da opção --check e interpretação de argumentos do app desktop sem importar nicegui (D-025, FR-16)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from rslapp.desktop import app as desktop_app
from rslapp.desktop.service import DesktopService
from rslapp.desktop.settings import ALLOWED_VARS, DesktopSettings, save_settings


# D-025, FR-16: parse_args interpreta argumentos vazios, --check e sys.argv sem importar nicegui
def test_d025_fr16_parse_args_decide_modo_check_sem_importar_nicegui(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert desktop_app.parse_args([]).check is False
    assert desktop_app.parse_args(["--check"]).check is True

    monkeypatch.setattr(sys, "argv", ["rslapp-desktop", "--check"])
    assert desktop_app.parse_args().check is True

    monkeypatch.setattr(sys, "argv", ["rslapp-desktop"])
    assert desktop_app.parse_args().check is False

    with pytest.raises(SystemExit) as exc_info:
        desktop_app.parse_args(["--opcao-invalida"])
    assert exc_info.value.code == 2

    monkeypatch.setattr(sys, "argv", ["rslapp-desktop", "--opcao-invalida"])
    with pytest.raises(SystemExit) as exc_info_argv:
        desktop_app.parse_args()
    assert exc_info_argv.value.code == 2
    assert "nicegui" not in sys.modules


# D-025, D-026, FR-16: main(["--check"]) carrega configurações, registra páginas, confere fontes e sai com 0 sem abrir janela
def test_d025_fr16_main_check_registra_paginas_e_sai_zero_sem_ui_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    for var in ALLOWED_VARS:
        monkeypatch.delenv(var, raising=False)

    cfg_file = tmp_path / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))
    save_settings(DesktopSettings(values={"RSL_CONTACT_EMAIL": "check@exemplo.org"}))

    events: list[str] = []

    def fake_register_pages(service: DesktopService | None = None) -> DesktopService:
        events.append("register_pages")
        return service if service is not None else DesktopService()

    def fake_run_ui() -> None:
        events.append("run_ui")

    monkeypatch.setattr(desktop_app, "register_pages", fake_register_pages)
    monkeypatch.setattr(desktop_app, "_run_ui", fake_run_ui)

    exit_code = desktop_app.main(["--check"])
    assert exit_code == 0
    assert events == ["register_pages"]
    assert os.environ.get("RSL_CONTACT_EMAIL") == "check@exemplo.org"
    assert "nicegui" not in sys.modules

    # No modo normal (sem --check), registra as páginas e chama _run_ui
    events.clear()
    exit_code_normal = desktop_app.main([])
    assert exit_code_normal == 0
    assert events == ["register_pages", "run_ui"]
    assert "nicegui" not in sys.modules


# D-025, FR-16: No Windows com --windowed (stdout/stderr None), _ensure_stdio_streams evita falha do uvicorn
def test_d025_fr16_ensure_stdio_streams_substitui_none_por_devnull(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    desktop_app._ensure_stdio_streams()
    try:
        assert sys.stdout is not None
        assert sys.stderr is not None
        assert isinstance(sys.stdout.isatty(), bool)
        assert isinstance(sys.stderr.isatty(), bool)
        sys.stdout.write("ok\n")
        sys.stderr.write("ok\n")
    finally:
        if sys.stdout is not None:
            sys.stdout.close()
        if sys.stderr is not None:
            sys.stderr.close()
