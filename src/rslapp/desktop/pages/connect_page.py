"""Tela 'Conectar IA' do app desktop (FR-19, D-026, D-028, D-029, D-031)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from nicegui import ui

from rslapp.desktop.components import (
    copy_block,
    status_badge,
)
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


def _claude_status_kind(state: str) -> str:
    """Devolve a cor semântica para o estado do Claude Desktop."""
    if state == "conectado":
        return "ok"
    if state == "conectado a outra instalação":
        return "warning"
    return "neutral"


# FR-19, D-026, D-028, D-029, D-031: Monta a tela /conectar com grade de seis cartões
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

    with ui.column().classes("w-full gap-4 pb-12"):

        # Subtítulo explícito com marker e faixa info de apoio (D-031, FR-19)
        ui.label(TOP_SUBTITLE).classes("rsl-muted text-sm -mt-2 mb-1").mark("connect-subtitle")
        with ui.row().classes("w-full items-center gap-2 p-3 rounded-lg rsl-info-box mb-1"):
            ui.icon("info").classes("text-sm shrink-0")
            ui.label("As buscas que a IA fizer aparecem no Histórico deste app.").classes(
                "text-xs font-medium"
            )

        # Diálogo de confirmação para conectar ao Claude Desktop (D-031, FR-19)
        confirm_dialog = ui.dialog().mark("claude-confirm-box")
        with confirm_dialog, ui.card().classes("w-full max-w-lg p-5 gap-3 rsl-surface-2"):
            with ui.row().classes("items-center justify-between w-full"):
                ui.label("Confirmar conexão ao Claude Desktop").classes(
                    "font-semibold text-base rsl-title"
                )
                ui.button(icon="close", on_click=confirm_dialog.close).props("flat round dense")

            ui.label(
                "Trecho que será gravado em claude_desktop_config.json:"
            ).classes("text-xs font-medium rsl-muted")
            confirm_snippet_lbl = (
                ui.label(snippet_text)
                .classes(
                    "rsl-code text-xs p-2.5 rounded w-full whitespace-pre-wrap break-all"
                )
                .mark("claude-confirm-snippet")
            )
            replace_warning_lbl = (
                ui.label("")
                .classes("text-xs text-amber-8 font-medium")
                .mark("claude-replace-warning")
            )
            replace_warning_lbl.set_visibility(False)
            current_entry_lbl = (
                ui.label("")
                .classes(
                    "rsl-code text-xs p-2.5 rounded w-full whitespace-pre-wrap break-all"
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
                    confirm_dialog.close()
                    ui.notify(err_msg, type="negative")
                    return

                confirm_dialog.close()
                claude_error_lbl.text = ""
                claude_error_lbl.set_visibility(False)
                new_state, _ = _safe_initial_claude_state(cfg_path)
                claude_status_badge.set_status(new_state, kind=_claude_status_kind(new_state))
                claude_feedback_lbl.text = CLAUDE_RESTART_NOTICE
                claude_feedback_lbl.set_visibility(True)
                ui.notify(CLAUDE_RESTART_NOTICE, type="positive")

            def on_cancel_connect() -> None:
                confirm_dialog.close()

            with ui.row().classes("w-full justify-end gap-2 mt-2"):
                ui.button("Cancelar", on_click=on_cancel_connect).props(
                    "outline size=sm"
                ).classes("rsl-surface-2").mark("claude-cancel-btn")
                ui.button("Confirmar", on_click=on_confirm_connect).props(
                    "unelevated size=sm"
                ).classes("bg-primary text-white").mark("claude-confirm-btn")

        # Grade responsiva de 6 cartões: 2 por linha em tela larga, 1 em tela estreita (D-031)
        with ui.element("div").classes("grid grid-cols-1 md:grid-cols-2 gap-4 w-full"):

            # 1. Claude Desktop (FR-19, D-028, D-031)
            with ui.card().classes("w-full p-4 gap-3 flex flex-col justify-between rsl-surface-2").mark(
                "card-claude-desktop"
            ):
                with ui.column().classes("w-full gap-2"):
                    with ui.row().classes("w-full items-center justify-between"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("desktop_windows").classes("text-primary text-lg")
                            ui.label("Claude Desktop").classes("font-semibold text-sm rsl-title")
                        claude_status_badge = (
                            status_badge(
                                initial_state,
                                kind=_claude_status_kind(initial_state),
                            )
                            .mark("claude-desktop-status")
                        )

                    ui.label("Conecta o app Claude Desktop ao servidor MCP local.").classes(
                        "text-xs rsl-muted -mt-1"
                    )

                    ui.label(f"Arquivo: {claude_cfg_path}").classes(
                        "text-xs rsl-muted break-all"
                    ).mark("claude-config-path")

                    claude_error_lbl = (
                        ui.label(initial_err or "")
                        .classes("text-xs text-negative")
                        .mark("claude-error")
                    )
                    claude_error_lbl.set_visibility(bool(initial_err))

                    claude_feedback_lbl = (
                        ui.label("")
                        .classes("text-xs text-positive font-medium")
                        .mark("claude-feedback")
                    )
                    claude_feedback_lbl.set_visibility(False)

                def on_open_connect() -> None:
                    cfg_path = claude_desktop_config_path()
                    try:
                        state, current_entry = inspect_claude_desktop(cfg_path)
                    except ClaudeConfigError as err:
                        err_msg = str(err)
                        claude_error_lbl.text = err_msg
                        claude_error_lbl.set_visibility(True)
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

                    confirm_dialog.open()

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

                    confirm_dialog.close()
                    claude_error_lbl.text = ""
                    claude_error_lbl.set_visibility(False)
                    new_state, _ = _safe_initial_claude_state(cfg_path)
                    claude_status_badge.set_status(new_state, kind=_claude_status_kind(new_state))
                    claude_feedback_lbl.text = "Entrada rslapp removida do Claude Desktop."
                    claude_feedback_lbl.set_visibility(True)
                    ui.notify("Entrada rslapp removida do Claude Desktop.", type="info")

                with ui.row().classes("gap-2 mt-2"):
                    ui.button("Conectar", icon="link", on_click=on_open_connect).props(
                        "unelevated size=sm"
                    ).classes("bg-primary text-white font-medium").mark("claude-connect-btn")
                    ui.button("Desconectar", icon="link_off", on_click=on_disconnect).props(
                        "outline size=sm"
                    ).classes("rsl-surface-2").mark("claude-disconnect-btn")

            # 2. Cursor (FR-19, D-028, D-031)
            with ui.card().classes("w-full p-4 gap-3 flex flex-col justify-between rsl-surface-2").mark(
                "card-cursor"
            ):
                with ui.column().classes("w-full gap-2"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("code").classes("text-primary text-lg")
                        ui.label("Cursor").classes("font-semibold text-sm rsl-title")
                    ui.label(
                        "Abre o link de instalação no Cursor para confirmar a adição do servidor."
                    ).classes("text-xs rsl-muted")

                def on_install_cursor() -> None:
                    url = cursor_install_url()
                    try:
                        open_cursor_link(url)
                    except OSError as err:
                        ui.notify(
                            f"Não foi possível abrir o link do Cursor: {err}",
                            type="negative",
                        )

                ui.button(
                    "Instalar no Cursor",
                    icon="open_in_browser",
                    on_click=on_install_cursor,
                ).props("outline size=sm").classes("rsl-surface-2 mt-2 self-start").mark("cursor-install-btn")

            # 3. VS Code (Copilot) (FR-19, D-028, D-031)
            with ui.card().classes("w-full p-4 gap-3 flex flex-col justify-between rsl-surface-2").mark(
                "card-vscode"
            ):
                with ui.column().classes("w-full gap-2.5"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("terminal").classes("text-primary text-lg")
                        ui.label("VS Code (Copilot)").classes("font-semibold text-sm rsl-title")

                    ui.label(
                        "Rode o comando abaixo para registrar no seu perfil do VS Code:"
                    ).classes("text-xs rsl-muted")

                    copy_block(
                        vscode_cmd_text,
                        mark="vscode-command",
                        button_mark="vscode-copy-cmd-btn",
                    )

                    if sys.platform == "win32":
                        ui.label(WINDOWS_CMD_NOTE).classes("text-xs text-amber-8 font-medium").mark(
                            "vscode-cmd-note"
                        )

                    ui.label("Ou copie para o .vscode/mcp.json:").classes(
                        "text-xs font-semibold rsl-title mt-1"
                    )

                    copy_block(
                        vscode_json_text,
                        mark="vscode-mcp-json",
                        button_mark="vscode-copy-json-btn",
                    )

                ui.link(
                    "Referência de configuração MCP do VS Code",
                    VSCODE_MCP_DOCS_URL,
                    new_tab=True,
                ).classes("text-xs text-primary underline mt-2").mark("vscode-docs-link")

            # 4. Claude Code (FR-19, D-028, D-031)
            with (
                ui.card()
                .classes("w-full p-4 gap-3 flex flex-col justify-between rsl-surface-2")
                .mark("card-claude-code"),
                ui.column().classes("w-full gap-2.5"),
            ):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("integration_instructions").classes("text-primary text-lg")
                    ui.label("Claude Code").classes("font-semibold text-sm rsl-title")

                ui.label(
                    "Rode no terminal para cadastrar no escopo do usuário:"
                ).classes("text-xs rsl-muted")

                copy_block(
                    claude_code_cmd_text,
                    mark="claude-code-command",
                    button_mark="claude-code-copy-btn",
                )

            # 5. Outras IAs (FR-19, D-028, D-031)
            with (
                ui.card()
                .classes("w-full p-4 gap-3 flex flex-col justify-between rsl-surface-2")
                .mark("card-other-ais"),
                ui.column().classes("w-full gap-2.5"),
            ):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("smart_toy").classes("text-primary text-lg")
                    ui.label("Outras IAs").classes("font-semibold text-sm rsl-title")

                ui.label(
                    "Trecho JSON para qualquer cliente que aceite servidor MCP local:"
                ).classes("text-xs rsl-muted")

                copy_block(
                    generic_json_text,
                    mark="generic-mcp-json",
                    button_mark="generic-copy-btn",
                )

            # 6. ChatGPT (FR-19, FR-20, D-028, D-029, D-031)
            with ui.card().classes("w-full p-4 gap-3 flex flex-col justify-between rsl-surface-2").mark(
                "card-chatgpt"
            ):
                with ui.column().classes("w-full gap-2"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("cloud_queue").classes("text-primary text-lg")
                        ui.label("ChatGPT").classes("font-semibold text-sm rsl-title")

                    ui.label(CHATGPT_NOTE).classes("text-xs rsl-muted leading-relaxed").mark(
                        "chatgpt-note"
                    )

                ui.link(
                    "Guia de hospedagem — seção ChatGPT",
                    CHATGPT_HOSTING_DOCS_URL,
                    new_tab=True,
                ).classes("text-xs text-primary underline mt-2").mark("chatgpt-docs-link")
