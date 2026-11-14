"""Testes das rotas e inicialização do app desktop com o fixture user do NiceGUI 4 (D-024, D-025)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from nicegui import ui
from nicegui.testing import User

from rslapp.desktop import app as desktop_app
from rslapp.desktop.app import register_pages
from rslapp.desktop.settings import DesktopSettings, save_settings


# D-024, D-025, FR-16, FR-17, FR-18: As quatro rotas abrem com o cabeçalho comum e o título da tela
async def test_d024_d025_fr16_rotas_e_cabecalho_no_user_fixture(user: User) -> None:
    register_pages()

    await user.open("/")
    await user.should_see("RSL.app")
    await user.should_see("Buscar")
    await user.should_see("Histórico")
    await user.should_see("Configurações")
    await user.should_see("Busque artigos nas bases acadêmicas configuradas.")

    await user.open("/lista/l-0001")
    await user.should_see("RSL.app")
    await user.should_see("Lista")
    await user.should_see("l-0001")

    await user.open("/historico")
    await user.should_see("RSL.app")
    await user.should_see("Histórico")
    await user.should_see("Consulte as buscas já feitas, repita uma busca ou abra o log.")

    await user.open("/configuracoes")
    await user.should_see("RSL.app")
    await user.should_see("Configurações")
    await user.should_see("Configure as chaves de API, o e-mail de contato e as pastas locais.")


# D-024, D-025, D-026: main() aplica desktop.json, escuta em 127.0.0.1 e faz fallback para navegador
def test_d024_d025_d026_main_escuta_em_loopback_e_fallback_navegador(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))
    monkeypatch.delenv("RSL_CONTACT_EMAIL", raising=False)
    save_settings(DesktopSettings(values={"RSL_CONTACT_EMAIL": "app@exemplo.org"}))

    run_calls: list[dict[str, Any]] = []

    def fake_run_ok(**kwargs: Any) -> None:
        run_calls.append(kwargs)

    monkeypatch.setattr(desktop_app, "_ensure_native_backend", lambda: None)
    monkeypatch.setattr(ui, "run", fake_run_ok)

    desktop_app.main()
    assert len(run_calls) == 1
    assert run_calls[0] == {
        "host": "127.0.0.1",
        "reload": False,
        "title": "RSL.app",
        "native": True,
        "window_size": (1200, 800),
    }

    # Simula ausência de backend nativo: deve recuar para native=False e show=True em 127.0.0.1
    run_calls.clear()

    def fake_run_fallback(**kwargs: Any) -> None:
        run_calls.append(kwargs)
        if kwargs.get("native") is True:
            raise RuntimeError("pywebview indisponível")

    monkeypatch.setattr(ui, "run", fake_run_fallback)
    desktop_app.main()
    assert len(run_calls) == 2
    assert run_calls[0]["native"] is True
    assert run_calls[0]["host"] == "127.0.0.1"
    assert run_calls[1] == {
        "host": "127.0.0.1",
        "reload": False,
        "title": "RSL.app",
        "native": False,
        "show": True,
    }
