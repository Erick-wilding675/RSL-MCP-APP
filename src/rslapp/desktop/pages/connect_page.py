"""Tela 'Conectar IA' do app desktop (FR-19, D-026, D-028, D-029)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from nicegui import ui

from rslapp.desktop.connect import (
    CHATGPT_HOSTING_DOCS_URL,
    VSCODE_MCP_DOCS_URL,
    ClaudeConfigError,
    claude_code_command,
    claude_desktop_config_path,
    claude_desktop_snippet_json,
    connect_claude_desktop,
    cursor_install_url,
    disconnect_claude_desktop,
    generic_mcp_json,
    inspect_claude_desktop,
    open_cursor_link,
    vscode_add_mcp_command,
    vscode_mcp_config_json,
)
from rslapp.desktop.pages import render_shell
from rslapp.desktop.service import DesktopService
from rslapp.desktop.theme import apply_theme

TOP_SUBTITLE = (
    "Ligue a sua IA ao RSL.app deste computador. As buscas que ela fizer "
    "ficam na sua pasta de dados e aparecem no Histórico."
)
CLAUDE_RESTART_NOTICE = "Feche e abra o Claude Desktop para ele ver o RSL.app."
WINDOWS_CMD_NOTE = "Cole no Prompt de Comando (cmd), não no PowerShell."
CHATGPT_NOTE = (
    "O ChatGPT só se liga a servidores na internet, não ao computador da pessoa. "
    "A forma de usá-lo é pela instituição, pelo guia de hospedagem (seção ChatGPT)."
)


def _safe_initial_claude_state(config_path: Path) -> tuple[str, str | None]:
    """Obtém o estado inicial do Claude Desktop sem falhar se o JSON estiver corrompido."""
    try:
        state, _ = inspect_claude_desktop(config_path)
        return state, None
    except ClaudeConfigError as err:
        return "não conectado", str(err)


# FR-19, D-026, D-028, D-029, D-031: Monta a tela /conectar com os seis cartões de IA
def build(service: DesktopService | None = None) -> None:
    """Renderiza a tela 'Conectar IA' com os seis cartões e ações de conexão."""
    _ = service
    apply_theme()
    render_shell("Conectar IA", TOP_SUBTITLE)

    claude_cfg_path = claude_desktop_config_path()
    initial_state, initial_err = _safe_initial_claude_state(claude_cfg_path)
    snippet_text = claude_desktop_snippet_json()
    vscode_cmd_text = vscode_add_mcp_command()
    vscode_json_text = vscode_mcp_config_json()
    claude_code_cmd_text = claude_code_command()
    generic_json_text = generic_mcp_json()

    def _copy_text(text: str) -> None:
        ui.clipboard.write(text)
        ui.notify("Copiado para a área de transferência.", type="positive")

    with ui.column().classes("w-full gap-4"):

        # 1. Claude Desktop (FR-19, D-028)
        with ui.card().classes("w-full p-4 gap-2").mark("card-claude-desktop"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("Claude Desktop").classes("text-subtitle1 font-bold")
                claude_status_lbl = (
                    ui.label(initial_state)
                    .classes("text-caption font-medium")
                    .mark("claude-desktop-status")
                )

            ui.label(f"Arquivo: {claude_cfg_path}").classes(
                "text-caption text-grey-7"
            ).mark("claude-config-path")

            claude_error_lbl = (
                ui.label(initial_err or "")
                .classes("text-caption text-negative")
                .mark("claude-error")
            )
            claude_error_lbl.set_visibility(bool(initial_err))

            claude_feedback_lbl = (
                ui.label("")
                .classes("text-caption text-positive")
                .mark("claude-feedback")
            )
            claude_feedback_lbl.set_visibility(False)

            # Caixa de confirmação para conectar ao Claude Desktop
            confirm_box = (
                ui.column()
                .classes("w-full bg-grey-1 border rounded p-3 gap-2")
                .mark("claude-confirm-box")
            )
            confirm_box.set_visibility(False)
            with confirm_box:
                ui.label(
                    "Trecho que será gravado em claude_desktop_config.json:"
                ).classes("text-caption font-medium")
                confirm_snippet_lbl = (
                    ui.label(snippet_text)
                    .classes(
                        "font-mono text-caption bg-grey-2 p-2 rounded w-full "
                        "whitespace-pre-wrap break-all"
                    )
                    .mark("claude-confirm-snippet")
                )
                replace_warning_lbl = (
                    ui.label("")
                    .classes("text-caption text-amber-9 font-medium")
                    .mark("claude-replace-warning")
                )
                replace_warning_lbl.set_visibility(False)
                current_entry_lbl = (
                    ui.label("")
                    .classes(
                        "font-mono text-caption bg-amber-1 p-2 rounded w-full "
                        "whitespace-pre-wrap break-all"
                    )
                    .mark("claude-current-entry")
                )
                current_entry_lbl.set_visibility(False)

                def on_confirm_connect() -> None:
                    cfg_path = claude_desktop_config_path()
                    try:
                        connect_claude_desktop(cfg_path)
                    except (ClaudeConfigError, OSError) as err:
                        err_msg = str(err)
                        claude_error_lbl.text = err_msg
                        claude_error_lbl.set_visibility(True)
                        confirm_box.set_visibility(False)
                        ui.notify(err_msg, type="negative")
                        return

                    confirm_box.set_visibility(False)
                    claude_error_lbl.text = ""
                    claude_error_lbl.set_visibility(False)
                    new_state, _ = _safe_initial_claude_state(cfg_path)
                    claude_status_lbl.text = new_state
                    claude_feedback_lbl.text = CLAUDE_RESTART_NOTICE
                    claude_feedback_lbl.set_visibility(True)
                    ui.notify(CLAUDE_RESTART_NOTICE, type="positive")

                def on_cancel_connect() -> None:
                    confirm_box.set_visibility(False)

                with ui.row().classes("gap-2"):
                    ui.button("Confirmar", on_click=on_confirm_connect).mark(
                        "claude-confirm-btn"
                    )
                    ui.button("Cancelar", on_click=on_cancel_connect).props(
                        "outline"
                    ).mark("claude-cancel-btn")

            def on_open_connect() -> None:
                cfg_path = claude_desktop_config_path()
                try:
                    state, current_entry = inspect_claude_desktop(cfg_path)
                except ClaudeConfigError as err:
                    err_msg = str(err)
                    claude_error_lbl.text = err_msg
                    claude_error_lbl.set_visibility(True)
                    confirm_box.set_visibility(False)
                    ui.notify(err_msg, type="negative")
                    return

                claude_error_lbl.text = ""
                claude_error_lbl.set_visibility(False)
                confirm_snippet_lbl.text = claude_desktop_snippet_json()
                if state == "conectado a outra instalação" and current_entry is not None:
                    replace_warning_lbl.text = (
                        "Já existe uma entrada rslapp diferente. "
                        "Deseja trocar pela configuração abaixo?"
                    )
                    replace_warning_lbl.set_visibility(True)
                    current_entry_lbl.text = json.dumps(
                        current_entry, ensure_ascii=False, indent=2
                    )
                    current_entry_lbl.set_visibility(True)
                else:
                    replace_warning_lbl.text = ""
                    replace_warning_lbl.set_visibility(False)
                    current_entry_lbl.text = ""
                    current_entry_lbl.set_visibility(False)

                confirm_box.set_visibility(True)

            def on_disconnect() -> None:
                cfg_path = claude_desktop_config_path()
                try:
                    disconnect_claude_desktop(cfg_path)
                except (ClaudeConfigError, OSError) as err:
                    err_msg = str(err)
                    claude_error_lbl.text = err_msg
                    claude_error_lbl.set_visibility(True)
                    ui.notify(err_msg, type="negative")
                    return

                confirm_box.set_visibility(False)
                claude_error_lbl.text = ""
                claude_error_lbl.set_visibility(False)
                new_state, _ = _safe_initial_claude_state(cfg_path)
                claude_status_lbl.text = new_state
                claude_feedback_lbl.text = "Entrada rslapp removida do Claude Desktop."
                claude_feedback_lbl.set_visibility(True)
                ui.notify("Entrada rslapp removida do Claude Desktop.", type="info")

            with ui.row().classes("gap-2"):
                ui.button("Conectar", on_click=on_open_connect).mark(
                    "claude-connect-btn"
                )
                ui.button("Desconectar", on_click=on_disconnect).props(
                    "outline"
                ).mark("claude-disconnect-btn")

        # 2. Cursor (FR-19, D-028)
        with ui.card().classes("w-full p-4 gap-2").mark("card-cursor"):
            ui.label("Cursor").classes("text-subtitle1 font-bold")
            ui.label(
                "Abre o link de instalação no Cursor para confirmar a adição do servidor."
            ).classes("text-caption")

            def on_install_cursor() -> None:
                url = cursor_install_url()
                try:
                    open_cursor_link(url)
                except OSError as err:
                    ui.notify(
                        f"Não foi possível abrir o link do Cursor: {err}",
                        type="negative",
                    )

            ui.button("Instalar no Cursor", on_click=on_install_cursor).mark(
                "cursor-install-btn"
            )

        # 3. VS Code (Copilot) (FR-19, D-028)
        with ui.card().classes("w-full p-4 gap-2").mark("card-vscode"):
            ui.label("VS Code (Copilot)").classes("text-subtitle1 font-bold")
            ui.label(
                "Rode o comando abaixo para registrar no seu perfil do VS Code:"
            ).classes("text-caption")

            with ui.row().classes("w-full items-center gap-2"):
                ui.label(vscode_cmd_text).classes(
                    "font-mono text-caption bg-grey-2 p-2 rounded flex-grow "
                    "whitespace-pre-wrap break-all"
                ).mark("vscode-command")
                ui.button(
                    "Copiar",
                    on_click=lambda: _copy_text(vscode_add_mcp_command()),
                ).props("outline").mark("vscode-copy-cmd-btn")

            if sys.platform == "win32":
                ui.label(WINDOWS_CMD_NOTE).classes(
                    "text-caption text-grey-7"
                ).mark("vscode-cmd-note")

            ui.label("Ou copie para o .vscode/mcp.json:").classes(
                "text-caption font-medium mt-2"
            )
            with ui.row().classes("w-full items-start gap-2"):
                ui.label(vscode_json_text).classes(
                    "font-mono text-caption bg-grey-2 p-2 rounded flex-grow "
                    "whitespace-pre-wrap break-all"
                ).mark("vscode-mcp-json")
                ui.button(
                    "Copiar",
                    on_click=lambda: _copy_text(vscode_mcp_config_json()),
                ).props("outline").mark("vscode-copy-json-btn")

            ui.link(
                "Referência de configuração MCP do VS Code",
                VSCODE_MCP_DOCS_URL,
                new_tab=True,
            ).classes("text-caption").mark("vscode-docs-link")

        # 4. Claude Code (FR-19, D-028)
        with ui.card().classes("w-full p-4 gap-2").mark("card-claude-code"):
            ui.label("Claude Code").classes("text-subtitle1 font-bold")
            ui.label("Rode no terminal para cadastrar no escopo do usuário:").classes(
                "text-caption"
            )
            with ui.row().classes("w-full items-center gap-2"):
                ui.label(claude_code_cmd_text).classes(
                    "font-mono text-caption bg-grey-2 p-2 rounded flex-grow "
                    "whitespace-pre-wrap break-all"
                ).mark("claude-code-command")
                ui.button(
                    "Copiar",
                    on_click=lambda: _copy_text(claude_code_command()),
                ).props("outline").mark("claude-code-copy-btn")

        # 5. Outras IAs (FR-19, D-028)
        with ui.card().classes("w-full p-4 gap-2").mark("card-other-ais"):
            ui.label("Outras IAs").classes("text-subtitle1 font-bold")
            ui.label(
                "Trecho JSON para qualquer cliente que aceite servidor MCP local:"
            ).classes("text-caption")
            with ui.row().classes("w-full items-start gap-2"):
                ui.label(generic_json_text).classes(
                    "font-mono text-caption bg-grey-2 p-2 rounded flex-grow "
                    "whitespace-pre-wrap break-all"
                ).mark("generic-mcp-json")
                ui.button(
                    "Copiar",
                    on_click=lambda: _copy_text(generic_mcp_json()),
                ).props("outline").mark("generic-copy-btn")

        # 6. ChatGPT (FR-19, FR-20, D-028, D-029)
        with ui.card().classes("w-full p-4 gap-2").mark("card-chatgpt"):
            ui.label("ChatGPT").classes("text-subtitle1 font-bold")
            ui.label(CHATGPT_NOTE).classes("text-caption").mark("chatgpt-note")
            ui.link(
                "Guia de hospedagem — seção ChatGPT",
                CHATGPT_HOSTING_DOCS_URL,
                new_tab=True,
            ).classes("text-caption").mark("chatgpt-docs-link")
