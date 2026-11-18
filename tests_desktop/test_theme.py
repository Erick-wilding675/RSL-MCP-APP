"""Testes do tema visual do app desktop: cores, tipografia, modo escuro e persistência (D-031)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from nicegui import ui
from nicegui.testing import User

from rslapp.desktop.settings import (
    DesktopSettings,
    get_theme,
    load_settings,
    save_settings,
    set_theme,
)
from rslapp.desktop.theme import COMMON_CSS, apply_theme


# D-031: O valor padrão do tema é 'auto' em arquivo ausente, corrompido ou com valor inválido
def test_d031_theme_default_auto(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))

    # 1. Arquivo ausente
    assert get_theme() == "auto"
    assert load_settings().theme == "auto"

    # 2. Arquivo com tema inválido
    cfg_file.write_text('{"theme": "desconhecido"}', encoding="utf-8")
    assert get_theme() == "auto"
    assert load_settings().theme == "auto"

    # 3. Arquivo com JSON corrompido
    cfg_file.write_text("{corrompido", encoding="utf-8")
    assert get_theme() == "auto"
    assert load_settings().theme == "auto"


# D-031: Leitura e persistência de 'light', 'dark' e 'auto' via set_theme e save_settings
def test_d031_theme_settings_persistencia(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))

    # Grava 'dark'
    set_theme("dark")
    assert get_theme() == "dark"
    data = json.loads(cfg_file.read_text(encoding="utf-8"))
    assert data["theme"] == "dark"

    # Grava 'light'
    set_theme("light")
    assert get_theme() == "light"
    data = json.loads(cfg_file.read_text(encoding="utf-8"))
    assert data["theme"] == "light"

    # Retorna para 'auto'
    set_theme("auto")
    assert get_theme() == "auto"
    data = json.loads(cfg_file.read_text(encoding="utf-8"))
    assert data["theme"] == "auto"


# D-031: A alteração de tema não apaga nem mistura as chaves de API já salvas no desktop.json
def test_d031_theme_nao_apaga_chaves(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))

    # Salva chave inicial
    initial = DesktopSettings(
        values={"OPENALEX_API_KEY": "oa-segredo", "RSL_CONTACT_EMAIL": "test@org.br"}
    )
    save_settings(initial)

    # Altera o tema
    set_theme("dark")

    # Confere que as chaves anteriores foram preservadas
    reloaded = load_settings()
    assert reloaded.theme == "dark"
    assert reloaded.values["OPENALEX_API_KEY"] == "oa-segredo"
    assert reloaded.values["RSL_CONTACT_EMAIL"] == "test@org.br"

    # Salva nova configuração com theme preservado
    reloaded.values["RSL_CONTACT_EMAIL"] = "novo@org.br"
    save_settings(reloaded)

    after = load_settings()
    assert after.theme == "dark"
    assert after.values["RSL_CONTACT_EMAIL"] == "novo@org.br"
    assert after.values["OPENALEX_API_KEY"] == "oa-segredo"


# D-031: CSS comum contém fontes do sistema, cantos de 6px sóbrios, transição de 150ms e foco visível
def test_d031_common_css_regras_visuais() -> None:
    assert '"Segoe UI Variable"' in COMMON_CSS
    assert "border-radius: 6px" in COMMON_CSS
    assert "150ms" in COMMON_CSS
    assert ":focus-visible" in COMMON_CSS
    assert "--q-primary" in COMMON_CSS
    assert "#F8FAFC" in COMMON_CSS
    assert "#1E293B" in COMMON_CSS


# D-031: apply_theme() inicializa ui.dark_mode de acordo com o tema configurado
async def test_d031_apply_theme_inicializa_dark_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    user: User,
) -> None:
    cfg_file = tmp_path / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))

    # Testa com dark
    set_theme("dark")

    @ui.page("/test-theme-dark")
    def page_dark() -> None:
        dm = apply_theme()
        ui.label(f"dm-value: {dm.value}").mark("dm-label")

    await user.open("/test-theme-dark")
    await user.should_see("dm-value: True")

    # Testa com light
    set_theme("light")

    @ui.page("/test-theme-light")
    def page_light() -> None:
        dm = apply_theme()
        ui.label(f"dm-value: {dm.value}").mark("dm-label")

    await user.open("/test-theme-light")
    await user.should_see("dm-value: False")

    # Testa com auto
    set_theme("auto")

    @ui.page("/test-theme-auto")
    def page_auto() -> None:
        dm = apply_theme()
        ui.label(f"dm-value: {dm.value}").mark("dm-label")

    await user.open("/test-theme-auto")
    await user.should_see("dm-value: None")


# D-031: Nenhum arquivo em src/rslapp/desktop contém 'dark:' fora de comentários
def test_d031_sem_variantes_dark_do_tailwind() -> None:
    desktop_dir = Path(__file__).resolve().parent.parent / "src" / "rslapp" / "desktop"
    assert desktop_dir.is_dir()

    violating_lines: list[str] = []
    for py_file in desktop_dir.rglob("*.py"):
        lines = py_file.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            code_part = line.split("#", 1)[0]
            if "dark:" in code_part:
                violating_lines.append(f"{py_file.name}:{idx}: {line.strip()}")

    assert not violating_lines, f"Classes 'dark:' do Tailwind encontradas: {violating_lines}"


# D-031: O CSS comum define body.body--dark para cada uma das cinco classes semânticas
def test_d031_classes_semanticas_modo_escuro() -> None:
    classes_esperadas = (
        "body.body--dark .rsl-title",
        "body.body--dark .rsl-muted",
        "body.body--dark .rsl-surface-2",
        "body.body--dark .rsl-surface-disabled",
        "body.body--dark .rsl-code",
    )
    for selector in classes_esperadas:
        assert selector in COMMON_CSS, f"Seletor {selector} ausente em COMMON_CSS"
