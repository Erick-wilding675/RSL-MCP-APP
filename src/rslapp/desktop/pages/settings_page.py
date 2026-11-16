"""Tela Configurações do app desktop (FR-18, D-023, D-024, D-025, D-026, NFR-03)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from nicegui import ui

import rslapp.config
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
    status_labels: dict[str, ui.label] = {}
    other_inputs: dict[str, ui.input] = {}
    other_status_labels: dict[str, ui.label] = {}

    initial_other_values: dict[str, str] = {
        "RSL_CONTACT_EMAIL": current_cfg.contact_email
        or file_settings.values.get("RSL_CONTACT_EMAIL", ""),
        "RSL_DATA_DIR": str(current_cfg.data_dir),
        "RSL_EXPORT_DIR": str(current_cfg.export_dir),
    }

    with ui.column().classes("w-full gap-4"):

        # FR-18, D-026, NFR-03: Campos de senha para cada chave de KEY_VARS, sempre vazios na tela
        ui.label("Chaves de API").classes("text-subtitle1 font-bold")

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
                status_labels[target_var].text = _key_status_text(
                    target_var, loaded.values, get_system_env_vars()
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
            with ui.card().classes("w-full p-3 gap-2"):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label(spec.label).classes("font-medium")
                    status_lbl = (
                        ui.label(
                            _key_status_text(
                                var_name, file_settings.values, sys_vars
                            )
                        )
                        .classes("text-caption")
                        .mark(f"status-{var_name}")
                    )
                    status_labels[var_name] = status_lbl

                with ui.row().classes("w-full items-center gap-2"):
                    # NFR-03, D-026: O campo nunca é preenchido com o valor salvo
                    inp = (
                        ui.input(
                            label=spec.label,
                            value="",
                            password=True,
                            password_toggle_button=True,
                        )
                        .classes("flex-grow")
                        .mark(f"input-{var_name}")
                    )
                    key_inputs[var_name] = inp

                    ui.button(
                        "Remover",
                        on_click=_make_remove_handler(var_name),
                    ).props("outline").mark(f"remove-{var_name}")

                with ui.row().classes("items-center gap-2"):
                    ui.label("Onde criar:").classes("text-caption text-grey-7")
                    ui.link(
                        spec.link_text,
                        spec.link_url,
                        new_tab=True,
                    ).classes("text-caption").mark(f"link-{var_name}")

                if spec.paid_note:
                    ui.label(spec.paid_note).classes(
                        "text-caption text-amber-9"
                    ).mark(f"paid-note-{var_name}")

        # FR-18, D-026: E-mail de contato e pastas locais
        ui.label("E-mail e pastas").classes("text-subtitle1 font-bold mt-2")

        with ui.card().classes("w-full p-3 gap-3"):
            email_inp = (
                ui.input(
                    label="E-mail de contato (RSL_CONTACT_EMAIL)",
                    value=initial_other_values["RSL_CONTACT_EMAIL"],
                )
                .classes("w-full")
                .mark("input-RSL_CONTACT_EMAIL")
            )
            other_inputs["RSL_CONTACT_EMAIL"] = email_inp
            email_status = (
                ui.label(
                    "definida no sistema; o valor do sistema vale"
                    if "RSL_CONTACT_EMAIL" in sys_vars
                    else ""
                )
                .classes("text-caption")
                .mark("status-RSL_CONTACT_EMAIL")
            )
            email_status.set_visibility("RSL_CONTACT_EMAIL" in sys_vars)
            other_status_labels["RSL_CONTACT_EMAIL"] = email_status

            data_inp = (
                ui.input(
                    label="Pasta de dados (RSL_DATA_DIR)",
                    value=initial_other_values["RSL_DATA_DIR"],
                )
                .classes("w-full")
                .mark("input-RSL_DATA_DIR")
            )
            other_inputs["RSL_DATA_DIR"] = data_inp
            ui.label(DATA_DIR_WARNING).classes("text-caption text-amber-9").mark(
                "data-dir-warning"
            )
            data_status = (
                ui.label(
                    "definida no sistema; o valor do sistema vale"
                    if "RSL_DATA_DIR" in sys_vars
                    else ""
                )
                .classes("text-caption")
                .mark("status-RSL_DATA_DIR")
            )
            data_status.set_visibility("RSL_DATA_DIR" in sys_vars)
            other_status_labels["RSL_DATA_DIR"] = data_status

            export_inp = (
                ui.input(
                    label="Pasta das exportações (RSL_EXPORT_DIR)",
                    value=initial_other_values["RSL_EXPORT_DIR"],
                )
                .classes("w-full")
                .mark("input-RSL_EXPORT_DIR")
            )
            other_inputs["RSL_EXPORT_DIR"] = export_inp
            export_status = (
                ui.label(
                    "definida no sistema; o valor do sistema vale"
                    if "RSL_EXPORT_DIR" in sys_vars
                    else ""
                )
                .classes("text-caption")
                .mark("status-RSL_EXPORT_DIR")
            )
            export_status.set_visibility("RSL_EXPORT_DIR" in sys_vars)
            other_status_labels["RSL_EXPORT_DIR"] = export_status

        save_feedback = ui.label("").classes("text-caption text-positive").mark(
            "save-feedback"
        )
        save_feedback.set_visibility(False)

        # FR-18, D-026, NFR-03: Salva configurações no arquivo e aplica no processo exceto variáveis do sistema
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

            # 4. Atualiza os textos de status e os valores atuais de pasta na tela
            refreshed_sys = get_system_env_vars()
            for var_name in KEY_VARS:
                status_labels[var_name].text = _key_status_text(
                    var_name, updated_values, refreshed_sys
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
                other_status_labels[var_name].text = (
                    "definida no sistema; o valor do sistema vale"
                    if is_sys
                    else ""
                )
                other_status_labels[var_name].set_visibility(is_sys)

            msg = f"Arquivo salvo em: {saved_path}"
            save_feedback.text = msg
            save_feedback.set_visibility(True)
            ui.notify(msg, type="positive")

        ui.button("Salvar", on_click=on_save).mark("save-settings")
