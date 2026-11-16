"""Testes da tela 'Conectar IA' (/conectar) com o fixture user do NiceGUI 4 (FR-19, D-026, D-028, D-029)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from nicegui.testing import User

from rslapp.desktop import connect
from rslapp.desktop.app import register_pages
from rslapp.desktop.pages import connect_page
from rslapp.desktop.settings import KEY_VARS


# FR-19, D-028, D-029: A tela /conectar mostra os seis cartões, o comando do VS Code para cmd no Windows, o estado do Claude Desktop e abre o link do Cursor
async def test_fr19_d028_d029_conectar_mostra_seis_cartoes_conecta_desconecta_e_abre_cursor(
    user: User,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    claude_cfg = tmp_path / "Claude" / "claude_desktop_config.json"
    monkeypatch.setattr(
        connect_page,
        "claude_desktop_config_path",
        lambda: claude_cfg,
    )
    monkeypatch.setattr(connect_page.sys, "platform", "win32")
    monkeypatch.setattr(connect.sys, "platform", "win32")

    register_pages()

    # 1. Sem arquivo de configuração: mostra os seis cartões e estado "não conectado"
    await user.open("/conectar")
    await user.should_see("Conectar IA")
    await user.should_see(
        "Ligue a sua IA ao RSL.app deste computador. As buscas que ela fizer ficam na sua pasta de dados e aparecem no Histórico."
    )
    await user.should_see("Claude Desktop")
    await user.should_see("Cursor")
    await user.should_see("VS Code (Copilot)")
    await user.should_see("Claude Code")
    await user.should_see("Outras IAs")
    await user.should_see("ChatGPT")
    await user.should_see('code --add-mcp "{\\"name\\":')
    await user.should_see("Cole no Prompt de Comando (cmd), não no PowerShell.")
    await user.should_see(".vscode/mcp.json")
    await user.should_see("claude mcp add")
    await user.should_see(
        "O ChatGPT só se liga a servidores na internet, não ao computador da pessoa."
    )

    status_lbl = user.find(marker="claude-desktop-status").elements.pop()
    assert status_lbl.text == "não conectado"

    # 2. Cria arquivo existente com outro servidor e entrada rslapp diferente ("conectado a outra instalação")
    claude_cfg.parent.mkdir(parents=True, exist_ok=True)
    initial_data = {
        "globalShortcut": "Alt+Space",
        "mcpServers": {
            "zotero": {"command": "npx", "args": ["zotero-mcp"]},
            "rslapp": {"command": "uvx", "args": ["rslapp"]},
        },
    }
    claude_cfg.write_text(
        json.dumps(initial_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    await user.open("/conectar")
    status_lbl = user.find(marker="claude-desktop-status").elements.pop()
    assert status_lbl.text == "conectado a outra instalação"

    # Clica em "Conectar": abre a caixa de confirmação com o trecho novo e a entrada atual
    user.find(marker="claude-connect-btn").click()
    await user.should_see("Já existe uma entrada rslapp diferente.")
    current_lbl = user.find(marker="claude-current-entry").elements.pop()
    assert "uvx" in current_lbl.text

    # Confirma a gravação
    user.find(marker="claude-confirm-btn").click()
    await user.should_see("Feche e abra o Claude Desktop para ele ver o RSL.app.")
    assert status_lbl.text == "conectado"

    saved = json.loads(claude_cfg.read_text(encoding="utf-8"))
    assert saved["globalShortcut"] == "Alt+Space"
    assert saved["mcpServers"]["zotero"] == {"command": "npx", "args": ["zotero-mcp"]}
    assert "command" in saved["mcpServers"]["rslapp"]
    assert list(claude_cfg.parent.glob("claude_desktop_config.json.bak-*"))

    # Clica em "Desconectar": remove rslapp, preserva o resto e volta para "não conectado"
    user.find(marker="claude-disconnect-btn").click()
    assert status_lbl.text == "não conectado"
    after_disc = json.loads(claude_cfg.read_text(encoding="utf-8"))
    assert after_disc["globalShortcut"] == "Alt+Space"
    assert after_disc["mcpServers"]["zotero"] == {"command": "npx", "args": ["zotero-mcp"]}
    assert "rslapp" not in after_disc["mcpServers"]

    # 3. Botão "Instalar no Cursor" chama open_cursor_link com o deeplink cursor://
    opened_urls: list[str] = []
    monkeypatch.setattr(
        connect_page,
        "open_cursor_link",
        lambda url: opened_urls.append(url),
    )
    user.find(marker="cursor-install-btn").click()
    assert len(opened_urls) == 1
    assert opened_urls[0].startswith(
        "cursor://anysphere.cursor-deeplink/mcp/install?name=rslapp&config="
    )


# FR-19, D-026, D-028, NFR-03: Arquivo ilegível do Claude Desktop mostra erro com o caminho e nenhuma chave aparece na tela
async def test_fr19_d026_d028_conectar_arquivo_ilegivel_e_nenhuma_chave_na_tela(
    user: User,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    secrets = {var: f"chave-secreta-tela-{var.lower()}-1234" for var in KEY_VARS}
    for var_name, secret_val in secrets.items():
        monkeypatch.setenv(var_name, secret_val)

    claude_cfg = tmp_path / "Claude" / "claude_desktop_config.json"
    claude_cfg.parent.mkdir(parents=True, exist_ok=True)
    corrupted = "{json invalido"
    claude_cfg.write_text(corrupted, encoding="utf-8")

    monkeypatch.setattr(
        connect_page,
        "claude_desktop_config_path",
        lambda: claude_cfg,
    )

    register_pages()
    await user.open("/conectar")

    user.find(marker="claude-connect-btn").click()
    err_lbl = user.find(marker="claude-error").elements.pop()
    assert str(claude_cfg) in err_lbl.text
    assert claude_cfg.read_text(encoding="utf-8") == corrupted

    for var_name, secret_val in secrets.items():
        await user.should_not_see(var_name)
        await user.should_not_see(secret_val)


# D-031, FR-19: Tela /conectar com subtítulo, faixa informativa e cancelamento do diálogo sem alterações
async def test_d031_fr19_conectar_grade_e_cancelar_dialogo(
    user: User,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    claude_cfg = tmp_path / "Claude" / "claude_desktop_config.json"
    claude_cfg.parent.mkdir(parents=True, exist_ok=True)
    initial_content = '{\n  "mcpServers": {}\n}\n'
    claude_cfg.write_text(initial_content, encoding="utf-8")

    monkeypatch.setattr(
        connect_page,
        "claude_desktop_config_path",
        lambda: claude_cfg,
    )

    register_pages()
    await user.open("/conectar")

    await user.should_see(marker="connect-subtitle")
    await user.should_see("As buscas que a IA fizer aparecem no Histórico deste app.")

    # Abre o diálogo de confirmação e clica em Cancelar
    user.find(marker="claude-connect-btn").click()
    await user.should_see("Confirmar conexão ao Claude Desktop")

    user.find(marker="claude-cancel-btn").click()
    # Arquivo permanece intocado após Cancelar
    assert claude_cfg.read_text(encoding="utf-8") == initial_content

