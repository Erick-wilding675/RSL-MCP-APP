"""Testes das rotas e inicialização do app desktop com o fixture user do NiceGUI 4 (D-024, D-025)."""

from __future__ import annotations

import sys
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
    await user.should_see("Conectar IA")
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

    await user.open("/conectar")
    await user.should_see("RSL.app")
    await user.should_see("Conectar IA")
    await user.should_see(
        "Ligue a sua IA ao RSL.app deste computador. As buscas que ela fizer ficam na sua pasta de dados e aparecem no Histórico."
    )

    await user.open("/configuracoes")
    await user.should_see("RSL.app")
    await user.should_see("Configurações")
    await user.should_see("Configure as chaves de API, o e-mail de contato e as pastas locais.")

    await user.open("/ficha/l-0001")
    await user.should_see("RSL.app")
    await user.should_see("Fichamento")

    await user.open("/protocolos")
    await user.should_see("RSL.app")
    await user.should_see("Protocolos")


# D-024, D-025, D-026: main() aplica desktop.json, escuta em 127.0.0.1 e faz fallback para navegador
def test_d024_d025_d026_main_escuta_em_loopback_e_fallback_navegador(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))
    monkeypatch.delenv("RSL_CONTACT_EMAIL", raising=False)
    monkeypatch.setattr(sys, "argv", ["rslapp-desktop"])
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


# D-025, FR-16: main(["--check"]) importa o NiceGUI e as páginas de verdade, registra as rotas e sai com 0 sem chamar ui.run
def test_d025_fr16_main_check_com_nicegui_nao_chama_ui_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))

    run_calls: list[dict[str, Any]] = []
    monkeypatch.setattr(ui, "run", lambda **kwargs: run_calls.append(kwargs))

    code = desktop_app.main(["--check"])
    assert code == 0
    assert run_calls == []


# FR-16, D-025: No Windows, _ensure_windows_dotnet carrega pythonnet e DLLs do WebView2 com sucesso
def test_fr16_d025_ensure_windows_dotnet_sucesso_no_windows() -> None:
    if sys.platform != "win32":
        pytest.skip("Teste exclusivo do ambiente Windows nativo")
    desktop_app._ensure_windows_dotnet()


# FR-16, D-025: Fora do Windows, o --check não tenta carregar o pythonnet/.NET
def test_fr16_d025_check_nao_carrega_dotnet_fora_do_windows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))
    monkeypatch.setattr(sys, "platform", "linux")

    chamou_dotnet = False

    def fake_ensure() -> None:
        nonlocal chamou_dotnet
        chamou_dotnet = True

    monkeypatch.setattr(desktop_app, "_ensure_windows_dotnet", fake_ensure)
    code = desktop_app.main(["--check"])
    assert code == 0
    assert not chamou_dotnet


# FR-16, D-025: No Windows, se o .NET falhar ao carregar, o --check sai com código diferente de zero
def test_fr16_d025_check_falha_com_codigo_diferente_de_zero_quando_dotnet_falha(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))
    monkeypatch.setattr(sys, "platform", "win32")

    def fake_falha() -> None:
        raise SystemExit(1)

    monkeypatch.setattr(desktop_app, "_ensure_windows_dotnet", fake_falha)
    code = desktop_app.main(["--check"])
    assert code != 0


# FR-16, D-025: _ensure_windows_dotnet imprime mensagem no stderr e sai com código 1 em caso de exceção
def test_fr16_d025_ensure_windows_dotnet_imprime_stderr_e_sai_em_excecao(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class FakeClr:
        @staticmethod
        def AddReference(*_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("DLL bloqueada por Zone.Identifier")

    monkeypatch.setitem(sys.modules, "clr", FakeClr)

    with pytest.raises(SystemExit) as exc_info:
        desktop_app._ensure_windows_dotnet()

    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "Erro ao carregar .NET / WebView2 no Windows" in err
    assert "DLL bloqueada por Zone.Identifier" in err
