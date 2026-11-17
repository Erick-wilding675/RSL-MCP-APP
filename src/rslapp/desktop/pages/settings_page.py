"""Tela Configurações do app desktop (FR-18, D-023, D-024, D-025, D-026, D-031, NFR-03)."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from nicegui import ui

import rslapp.config
from rslapp.desktop.components import (
    section_card,
    status_badge,
)
from rslapp.desktop.pages import render_shell
from rslapp.desktop.service import DesktopService
from rslapp.desktop.settings import (
    KEY_VARS,
    OTHER_VARS,
    DesktopSettings,
    get_system_env_vars,
    load_settings,
    remove_app_env_var,
    save_settings,
    set_app_env_var,
)
from rslapp.desktop.theme import apply_theme


@dataclass(frozen=True)
class KeyFieldSpec:
    """Metadados de exibição para cada variável de chave de API em KEY_VARS."""

    var_name: str
    label: str
    link_text: str
    link_url: str
    paid_note: str | None = None


PAID_SOURCE_NOTE = (
    "Nota (D-023): Scopus e Web of Science só funcionam com a assinatura de quem usa ou da instituição."
)

# FR-18, D-023, D-026: Metadados e links para criar cada chave de KEY_VARS
KEY_FIELD_SPECS: dict[str, KeyFieldSpec] = {
    "OPENALEX_API_KEY": KeyFieldSpec(
        var_name="OPENALEX_API_KEY",
        label="OpenAlex (OPENALEX_API_KEY)",
        link_text="https://openalex.org/settings/api",
        link_url="https://openalex.org/settings/api",
    ),
    "SEMANTIC_SCHOLAR_API_KEY": KeyFieldSpec(
        var_name="SEMANTIC_SCHOLAR_API_KEY",
        label="Semantic Scholar (SEMANTIC_SCHOLAR_API_KEY)",
        link_text="https://www.semanticscholar.org/product/api#api-key-form",
        link_url="https://www.semanticscholar.org/product/api#api-key-form",
    ),
    "NCBI_API_KEY": KeyFieldSpec(
        var_name="NCBI_API_KEY",
        label="NCBI / PubMed (NCBI_API_KEY)",
        link_text="página de configurações da conta do NCBI",
        link_url="https://www.ncbi.nlm.nih.gov/account/settings/",
    ),
    "SCOPUS_API_KEY": KeyFieldSpec(
        var_name="SCOPUS_API_KEY",
        label="Scopus — Chave de API (SCOPUS_API_KEY)",
        link_text="https://dev.elsevier.com/apikey/manage",
        link_url="https://dev.elsevier.com/apikey/manage",
        paid_note=PAID_SOURCE_NOTE,
    ),
    "SCOPUS_INSTTOKEN": KeyFieldSpec(
        var_name="SCOPUS_INSTTOKEN",
        label="Scopus — Token institucional (SCOPUS_INSTTOKEN)",
        link_text="https://dev.elsevier.com/apikey/manage",
        link_url="https://dev.elsevier.com/apikey/manage",
        paid_note=PAID_SOURCE_NOTE,
    ),
    "WOS_STARTER_API_KEY": KeyFieldSpec(
        var_name="WOS_STARTER_API_KEY",
        label="Web of Science Starter (WOS_STARTER_API_KEY)",
        link_text="https://developer.clarivate.com/apis/wos-starter",
        link_url="https://developer.clarivate.com/apis/wos-starter",
        paid_note=PAID_SOURCE_NOTE,
    ),
}

DATA_DIR_WARNING = (
    "Aviso: trocá-la faz o app e o Claude Desktop olharem pastas diferentes, "
    "a menos que o Claude Desktop use a mesma."
)


# FR-18, D-026, NFR-03: Determina o texto de situação de uma chave sem nunca expor o valor
def _key_status_text(
    var_name: str,
    file_values: Mapping[str, str],
    sys_vars: frozenset[str],
) -> str:
    """Devolve o texto de situação da chave ('definida no sistema...', 'configurada' ou 'não configurada')."""
    if var_name in sys_vars:
        return "definida no sistema; o valor do sistema vale"
    in_file = bool(file_values.get(var_name, "").strip())
    in_env = bool(os.environ.get(var_name, "").strip())
    if in_file or in_env:
        return "configurada"
    return "não configurada"


def _key_status_kind(
    var_name: str,
    file_values: Mapping[str, str],
    sys_vars: frozenset[str],
) -> str:
    """Devolve a categoria semântica do badge (ok, warning, info ou neutral)."""
    if var_name in sys_vars:
        return "info"
    in_file = bool(file_values.get(var_name, "").strip())
    in_env = bool(os.environ.get(var_name, "").strip())
    if in_file or in_env:
        return "ok"
    if var_name in ("SCOPUS_API_KEY", "SCOPUS_INSTTOKEN", "WOS_STARTER_API_KEY"):
        return "warning"
    return "neutral"


def open_folder(folder_path: str) -> None:
    """Abre uma pasta local no gerenciador de arquivos do sistema operacional."""
    folder = Path(folder_path.strip())
    if not folder.is_dir():
        ui.notify(f"Pasta não existe: {folder}", type="warning")
        return
    try:
        if sys.platform == "win32":
            os.startfile(folder)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", str(folder)], check=False)
    except OSError as err:
        ui.notify(f"Não foi possível abrir a pasta: {err}", type="negative")


# FR-18, D-023, D-024, D-025, D-026, D-031, NFR-03: Tela Configurações (/configuracoes)
def build(service: DesktopService) -> None:
    """Monta a tela de configuração de chaves de API, e-mail de contato e pastas locais."""
    _ = service
    apply_theme()
    render_shell(
        "Configurações",
        "Configure as chaves de API, o e-mail de contato e as pastas locais.",
    )

    file_settings = load_settings()
    sys_vars = get_system_env_vars()
    current_cfg = rslapp.config.load()

    key_inputs: dict[str, ui.input] = {}
    status_badges: dict[str, status_badge] = {}
    other_inputs: dict[str, ui.input] = {}
    other_status_badges: dict[str, status_badge] = {}

    initial_other_values: dict[str, str] = {
        "RSL_CONTACT_EMAIL": current_cfg.contact_email
        or file_settings.values.get("RSL_CONTACT_EMAIL", ""),
        "RSL_DATA_DIR": str(current_cfg.data_dir),
        "RSL_EXPORT_DIR": str(current_cfg.export_dir),
    }

    is_dirty = False

    def mark_dirty() -> None:
        nonlocal is_dirty
        if not is_dirty:
            is_dirty = True
            save_bar.classes(remove="save-bar-clean", add="save-bar-dirty")
            dirty_label.set_visibility(True)

    def clear_dirty() -> None:
        nonlocal is_dirty
        is_dirty = False
        save_bar.classes(remove="save-bar-dirty", add="save-bar-clean")
        dirty_label.set_visibility(False)

    with ui.column().classes("w-full gap-5 pb-20"):

        # 1. Cartão "Chaves de API" (ícone key) (D-031, FR-18)
        with section_card(
            "Chaves de API",
            icon="key",
            description="Chaves para consulta de bases acadêmicas (armazenadas apenas na sua máquina).",
        ):
            def _make_remove_handler(target_var: str):
                def _on_remove() -> None:
                    key_inputs[target_var].value = ""
                    active_sys = get_system_env_vars()
                    loaded = load_settings()
                    if target_var in loaded.values:
                        loaded.values.pop(target_var, None)
                        try:
                            save_settings(loaded)
                        except OSError:
                            ui.notify(
                                "Não foi possível atualizar o arquivo de configuração.",
                                type="negative",
                            )
                            return
                    if target_var not in active_sys:
                        remove_app_env_var(target_var)

                    active_sys_refreshed = get_system_env_vars()
                    status_badges[target_var].set_status(
                        _key_status_text(target_var, loaded.values, active_sys_refreshed),
                        kind=_key_status_kind(target_var, loaded.values, active_sys_refreshed),
                    )
                    ui.notify(f"Chave {target_var} removida.", type="info")

                return _on_remove

            for var_name in KEY_VARS:
                spec = KEY_FIELD_SPECS.get(
                    var_name,
                    KeyFieldSpec(
                        var_name=var_name,
                        label=var_name,
                        link_text="Documentação",
                        link_url="https://openalex.org/settings/api",
                    ),
                )
                with ui.card().classes("w-full p-4 gap-2.5 rsl-surface-2"):
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label(spec.label).classes("font-semibold text-sm rsl-title")
                        badge = (
                            status_badge(
                                _key_status_text(var_name, file_settings.values, sys_vars),
                                kind=_key_status_kind(var_name, file_settings.values, sys_vars),
                            )
                            .mark(f"status-{var_name}")
                        )
                        status_badges[var_name] = badge

                    with ui.row().classes("w-full items-center gap-2"):
                        # NFR-03, D-026: O campo nunca é preenchido com o valor salvo
                        inp = (
                            ui.input(
                                label=spec.label,
                                value="",
                                password=True,
                                password_toggle_button=True,
                                on_change=mark_dirty,
                            )
                            .classes("flex-grow")
                            .mark(f"input-{var_name}")
                        )
                        key_inputs[var_name] = inp

                        ui.button(
                            "Remover",
                            icon="delete_outline",
                            on_click=_make_remove_handler(var_name),
                        ).props("outline size=sm").classes("rsl-surface-2").mark(f"remove-{var_name}")

                    with ui.row().classes("items-center gap-1.5"):
                        ui.label("Onde criar:").classes("text-xs rsl-muted")
                        ui.link(
                            spec.link_text,
                            spec.link_url,
                            new_tab=True,
                        ).classes("text-xs text-primary underline").mark(f"link-{var_name}")
                        ui.icon("open_in_new").classes("text-xs text-primary")

                    if spec.paid_note:
                        ui.label(spec.paid_note).classes(
                            "text-xs text-amber-8 font-medium mt-0.5"
                        ).mark(f"paid-note-{var_name}")

        # 2. Cartão "E-mail de contato" (ícone mail) (D-031, FR-18)
        with section_card(
            "E-mail de contato",
            icon="mail",
            description="Identifica suas requisições nas APIs públicas (OpenAlex e Crossref).",
        ):
            email_inp = (
                ui.input(
                    label="E-mail de contato (RSL_CONTACT_EMAIL)",
                    value=initial_other_values["RSL_CONTACT_EMAIL"],
                    on_change=mark_dirty,
                )
                .classes("w-full")
                .mark("input-RSL_CONTACT_EMAIL")
            )
            other_inputs["RSL_CONTACT_EMAIL"] = email_inp

            email_status = (
                status_badge(
                    "definida no sistema; o valor do sistema vale"
                    if "RSL_CONTACT_EMAIL" in sys_vars
                    else "",
                    kind="info",
                )
                .mark("status-RSL_CONTACT_EMAIL")
            )
            email_status.set_visibility("RSL_CONTACT_EMAIL" in sys_vars)
            other_status_badges["RSL_CONTACT_EMAIL"] = email_status

        # 3. Cartão "Pastas" (ícone folder) (D-031, FR-18)
        with section_card(
            "Pastas",
            icon="folder",
            description="Pastas locais de dados e exportações.",
        ):
            # RSL_DATA_DIR
            with ui.column().classes("w-full gap-1.5"):
                with ui.row().classes("w-full items-center gap-2"):
                    data_inp = (
                        ui.input(
                            label="Pasta de dados (RSL_DATA_DIR)",
                            value=initial_other_values["RSL_DATA_DIR"],
                            on_change=mark_dirty,
                        )
                        .classes("flex-grow")
                        .mark("input-RSL_DATA_DIR")
                    )
                    other_inputs["RSL_DATA_DIR"] = data_inp
                    ui.button(
                        icon="folder_open",
                        on_click=lambda: open_folder(data_inp.value),
                    ).props("flat dense size=sm").classes("rsl-surface-2").tooltip("Abrir pasta no gerenciador de arquivos")

                with ui.row().classes("w-full items-center gap-2 p-2.5 rounded-lg rsl-warning-box"):
                    ui.icon("warning").classes("text-sm shrink-0")
                    ui.label(DATA_DIR_WARNING).classes("text-xs leading-relaxed").mark("data-dir-warning")

                data_status = (
                    status_badge(
                        "definida no sistema; o valor do sistema vale"
                        if "RSL_DATA_DIR" in sys_vars
                        else "",
                        kind="info",
                    )
                    .mark("status-RSL_DATA_DIR")
                )
                data_status.set_visibility("RSL_DATA_DIR" in sys_vars)
                other_status_badges["RSL_DATA_DIR"] = data_status

            # RSL_EXPORT_DIR
            with ui.column().classes("w-full gap-1.5"):
                with ui.row().classes("w-full items-center gap-2"):
                    export_inp = (
                        ui.input(
                            label="Pasta das exportações (RSL_EXPORT_DIR)",
                            value=initial_other_values["RSL_EXPORT_DIR"],
                            on_change=mark_dirty,
                        )
                        .classes("flex-grow")
                        .mark("input-RSL_EXPORT_DIR")
                    )
                    other_inputs["RSL_EXPORT_DIR"] = export_inp
                    ui.button(
                        icon="folder_open",
                        on_click=lambda: open_folder(export_inp.value),
                    ).props("flat dense size=sm").classes("rsl-surface-2").tooltip("Abrir pasta no gerenciador de arquivos")

                export_status = (
                    status_badge(
                        "definida no sistema; o valor do sistema vale"
                        if "RSL_EXPORT_DIR" in sys_vars
                        else "",
                        kind="info",
                    )
                    .mark("status-RSL_EXPORT_DIR")
                )
                export_status.set_visibility("RSL_EXPORT_DIR" in sys_vars)
                other_status_badges["RSL_EXPORT_DIR"] = export_status

        # Barra fixa no pé da tela com Salvar e feedback (D-031, FR-18)
        save_bar = ui.row().classes("save-bar save-bar-clean w-full items-center justify-between p-3 px-4")
        with save_bar:
            with ui.row().classes("items-center gap-2"):
                dirty_label = ui.label("Alterações não salvas").classes("text-xs font-semibold text-emerald-700")
                dirty_label.set_visibility(False)
                save_feedback = ui.label("").classes("text-caption text-positive font-medium").mark(
                    "save-feedback"
                )
                save_feedback.set_visibility(False)

            def on_save() -> None:
                active_sys = get_system_env_vars()
                loaded = load_settings()
                updated_values: dict[str, str] = dict(loaded.values)

                # 1. Processa KEY_VARS e limpa os campos imediatamente para nenhuma chave ficar no HTML
                for var_name in KEY_VARS:
                    raw_val = key_inputs[var_name].value
                    typed = raw_val.strip() if isinstance(raw_val, str) else ""
                    key_inputs[var_name].value = ""
                    if var_name in active_sys:
                        continue
                    if typed:
                        updated_values[var_name] = typed

                # 2. Processa OTHER_VARS respeitando variáveis vindas do sistema
                for var_name in OTHER_VARS:
                    if var_name in active_sys:
                        continue
                    raw_val = other_inputs[var_name].value
                    typed = raw_val.strip() if isinstance(raw_val, str) else ""
                    if var_name == "RSL_CONTACT_EMAIL":
                        if typed:
                            updated_values[var_name] = typed
                        else:
                            updated_values.pop(var_name, None)
                    else:
                        if not typed:
                            updated_values.pop(var_name, None)
                        elif (
                            var_name in loaded.values
                            or typed != initial_other_values[var_name]
                        ):
                            updated_values[var_name] = typed

                try:
                    # D-031: Preserva o tema escolhido ao gravar chaves e pastas
                    saved_path = save_settings(
                        DesktopSettings(values=updated_values, theme=loaded.theme)
                    )
                except OSError:
                    ui.notify(
                        "Não foi possível salvar o arquivo de configuração.",
                        type="negative",
                    )
                    return

                # 3. Aplica no ambiente do processo sem tocar nas variáveis do sistema
                for var_name in KEY_VARS:
                    if var_name in active_sys:
                        continue
                    if var_name in updated_values:
                        set_app_env_var(var_name, updated_values[var_name])
                    else:
                        remove_app_env_var(var_name)

                for var_name in OTHER_VARS:
                    if var_name in active_sys:
                        continue
                    if var_name in updated_values:
                        set_app_env_var(var_name, updated_values[var_name])
                    else:
                        remove_app_env_var(var_name)

                # 4. Atualiza os badges de status e os valores atuais de pasta na tela
                refreshed_sys = get_system_env_vars()
                for var_name in KEY_VARS:
                    status_badges[var_name].set_status(
                        _key_status_text(var_name, updated_values, refreshed_sys),
                        kind=_key_status_kind(var_name, updated_values, refreshed_sys),
                    )

                refreshed_cfg = rslapp.config.load()
                initial_other_values["RSL_CONTACT_EMAIL"] = (
                    refreshed_cfg.contact_email
                    or updated_values.get("RSL_CONTACT_EMAIL", "")
                )
                initial_other_values["RSL_DATA_DIR"] = str(refreshed_cfg.data_dir)
                initial_other_values["RSL_EXPORT_DIR"] = str(
                    refreshed_cfg.export_dir
                )
                for var_name in OTHER_VARS:
                    other_inputs[var_name].value = initial_other_values[var_name]
                    is_sys = var_name in refreshed_sys
                    other_status_badges[var_name].set_status(
                        "definida no sistema; o valor do sistema vale"
                        if is_sys
                        else "",
                        kind="info",
                    )
                    other_status_badges[var_name].set_visibility(is_sys)

                clear_dirty()
                msg = f"Arquivo salvo em: {saved_path}"
                save_feedback.text = msg
                save_feedback.set_visibility(True)
                ui.notify(msg, type="positive")

            ui.button("Salvar", icon="save", on_click=on_save).props("unelevated").classes(
                "bg-primary text-white font-medium px-5"
            ).mark("save-settings")
