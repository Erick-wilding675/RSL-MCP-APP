"""Testes de configuração do app desktop (D-026, FR-18, NFR-03) sem importar nicegui."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from rslapp.desktop import service, settings
from rslapp.desktop.settings import (
    KEY_VARS,
    OTHER_VARS,
    DesktopSettings,
    apply_to_environ,
    load_settings,
    save_settings,
    settings_path,
)


# FR-16, D-024, D-025: Importar settings e service não pode importar o nicegui
def test_fr16_d024_import_settings_e_service_nao_importa_nicegui() -> None:
    assert service is not None
    assert settings is not None
    assert "nicegui" not in sys.modules


# D-026, FR-18: Caminho do arquivo de configuração por RSL_DESKTOP_CONFIG e por plataforma
def test_d026_fr18_settings_path_por_plataforma_e_rsl_desktop_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    custom_file = tmp_path / "custom" / "meu_desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(custom_file))
    assert settings_path() == custom_file

    # Valor em branco ignora RSL_DESKTOP_CONFIG e segue a plataforma
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", "   ")

    # Windows: %APPDATA%\RSL.app\desktop.json
    appdata_dir = tmp_path / "Roaming"
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(appdata_dir))
    assert settings_path() == appdata_dir / "RSL.app" / "desktop.json"

    # Linux com XDG_CONFIG_HOME: $XDG_CONFIG_HOME/rslapp/desktop.json
    xdg_dir = tmp_path / "xdg_config"
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_dir))
    assert settings_path() == xdg_dir / "rslapp" / "desktop.json"

    # Linux sem XDG_CONFIG_HOME: ~/.config/rslapp/desktop.json
    fake_home = tmp_path / "home_user"
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    assert settings_path() == fake_home / ".config" / "rslapp" / "desktop.json"


# D-026, FR-18: Arquivo ausente, JSON ilegível ou não-objeto devolvem DesktopSettings vazio
def test_d026_fr18_load_settings_ausente_ilegivel_ou_nao_objeto(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))

    # 1. Arquivo não existe
    assert load_settings() == DesktopSettings(values={})

    # 2. JSON corrompido
    cfg_file.write_text("{json invalido", encoding="utf-8")
    assert load_settings() == DesktopSettings(values={})

    # 3. JSON válido mas não é objeto (lista)
    cfg_file.write_text('["item1", "item2"]', encoding="utf-8")
    assert load_settings() == DesktopSettings(values={})


# D-026, FR-18: Ignora nomes desconhecidos e tipos não-texto; valor vazio equivale a apagar
def test_d026_fr18_nomes_desconhecidos_e_valor_vazio_apaga(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "sub" / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))

    cfg_file.parent.mkdir(parents=True, exist_ok=True)
    cfg_file.write_text(
        '{"OPENALEX_API_KEY": "oa-val", "VAR_DESCONHECIDA": "x", "RSL_DATA_DIR": 123}',
        encoding="utf-8",
    )
    loaded = load_settings()
    assert loaded.values == {"OPENALEX_API_KEY": "oa-val"}

    # Salvar com nome desconhecido e valor vazio apaga a chave vazia e ignora a desconhecida
    to_save = DesktopSettings(
        values={
            "OPENALEX_API_KEY": "",
            "RSL_CONTACT_EMAIL": "pesquisador@inst.br",
        }
    )
    to_save.values["OUTRA_DESCONHECIDA"] = "ignorar"
    save_settings(to_save)

    reloaded = load_settings()
    assert reloaded.values == {"RSL_CONTACT_EMAIL": "pesquisador@inst.br"}
    raw_saved = cfg_file.read_text(encoding="utf-8")
    assert "OPENALEX_API_KEY" not in raw_saved
    assert "OUTRA_DESCONHECIDA" not in raw_saved


# D-026, NFR-03: Fora do Windows, save_settings aplica permissão 0o600
@pytest.mark.skipif(sys.platform == "win32", reason="Permissão POSIX 0o600 não se aplica ao Windows")
def test_d026_nfr03_save_settings_permissao_0o600_posix(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))
    save_settings(DesktopSettings(values={"OPENALEX_API_KEY": "fake-oa"}))
    assert (cfg_file.stat().st_mode & 0o777) == 0o600


# D-026, NFR-03: Confere chamada a os.chmod(path, 0o600) quando sys.platform != "win32"
def test_d026_nfr03_save_settings_chama_chmod_0o600_fora_do_windows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))
    chmod_calls: list[tuple[Path, int]] = []

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(os, "chmod", lambda p, mode: chmod_calls.append((Path(p), mode)))

    save_settings(DesktopSettings(values={"RSL_CONTACT_EMAIL": "a@b.org"}))
    assert chmod_calls == [(cfg_file, 0o600)]


# D-026, FR-18, NFR-03: apply_to_environ não sobrescreve variáveis já definidas e não imprime valores
def test_d026_fr18_nfr03_apply_to_environ_nao_sobrescreve_nem_imprime(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_env: dict[str, str] = {
        "OPENALEX_API_KEY": "chave-do-sistema",
        "SEMANTIC_SCHOLAR_API_KEY": "   ",
    }
    cfg = DesktopSettings(
        values={
            "OPENALEX_API_KEY": "chave-do-arquivo",
            "SEMANTIC_SCHOLAR_API_KEY": "s2-do-arquivo",
            "RSL_CONTACT_EMAIL": "contato@exemplo.org",
        }
    )

    applied = apply_to_environ(cfg, environ=fake_env)
    assert applied == ["SEMANTIC_SCHOLAR_API_KEY", "RSL_CONTACT_EMAIL"]
    assert fake_env["OPENALEX_API_KEY"] == "chave-do-sistema"
    assert fake_env["SEMANTIC_SCHOLAR_API_KEY"] == "s2-do-arquivo"
    assert fake_env["RSL_CONTACT_EMAIL"] == "contato@exemplo.org"

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


# D-026, NFR-03: __repr__ de DesktopSettings mascara todas as KEY_VARS com '***'
def test_d026_nfr03_desktop_settings_repr_mascarado() -> None:
    vals = {var: f"segredo-{var.lower()}" for var in KEY_VARS}
    for var in OTHER_VARS:
        vals[var] = f"publico-{var.lower()}"

    cfg = DesktopSettings(values=vals)
    texto_repr = repr(cfg)

    for var in KEY_VARS:
        assert f"segredo-{var.lower()}" not in texto_repr
    for var in OTHER_VARS:
        assert f"publico-{var.lower()}" in texto_repr
    assert "***" in texto_repr
