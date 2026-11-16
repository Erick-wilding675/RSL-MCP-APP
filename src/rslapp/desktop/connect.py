"""Funções puras para ligar IAs locais ao RSL.app sem depender do NiceGUI (FR-19, D-026, D-028, D-029)."""

from __future__ import annotations

import base64
import copy
import json
import os
import subprocess
import sys
import urllib.parse
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from rslapp.store._atomic import atomic_write_replace

ClaudeConnectionState = Literal[
    "conectado",
    "conectado a outra instalação",
    "não conectado",
]

VSCODE_MCP_DOCS_URL = "https://code.visualstudio.com/docs/agents/reference/mcp-configuration"
CHATGPT_HOSTING_DOCS_URL = (
    "https://github.com/Erick-wilding675/RSL-MCP-APP/blob/main/docs/hospedagem.md#no-chatgpt"
)


class ClaudeConfigError(ValueError):
    """Erro ao ler ou validar o arquivo claude_desktop_config.json, preservando o caminho."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(
            f"Não foi possível ler a configuração do Claude Desktop em {path}: {reason}"
        )


# FR-19, D-028: Decide o comando e os argumentos que as IAs locais vão executar para subir o servidor MCP
def mcp_launch_command(
    *,
    environ: Mapping[str, str] = os.environ,
) -> tuple[str, list[str]]:
    """Devolve (command, args) para iniciar o RSL.app em modo MCP conforme o empacotamento atual."""
    appimage = environ.get("APPIMAGE")
    if isinstance(appimage, str) and appimage.strip():
        resolved_appimage = os.path.abspath(os.path.expanduser(appimage.strip()))
        return resolved_appimage, ["--mcp"]

    if getattr(sys, "frozen", False):
        return os.path.abspath(sys.executable), ["--mcp"]

    exe_path = Path(os.path.abspath(sys.executable))
    exe_dir = exe_path.parent
    candidate_names = (
        ("rslapp.exe", "rslapp") if sys.platform == "win32" else ("rslapp", "rslapp.exe")
    )
    for name in candidate_names:
        candidate = exe_dir / name
        if candidate.is_file():
            return str(candidate), []

    return str(exe_path), ["-m", "rslapp"]


# FR-19, D-026, NFR-03: Nenhuma chave entra na configuração das IAs; só RSL_DESKTOP_CONFIG quando definido
def mcp_env(environ: Mapping[str, str] = os.environ) -> dict[str, str]:
    """Devolve o dicionário env do servidor MCP contendo apenas RSL_DESKTOP_CONFIG quando definido."""
    raw = environ.get("RSL_DESKTOP_CONFIG")
    if isinstance(raw, str) and raw.strip():
        return {"RSL_DESKTOP_CONFIG": raw.strip()}
    return {}


# FR-19, D-026, D-028: Monta o objeto de configuração do servidor rslapp (command, args e env opcional)
def mcp_server_entry(
    *,
    command: str | None = None,
    args: Sequence[str] | None = None,
    environ: Mapping[str, str] = os.environ,
) -> dict[str, Any]:
    """Monta a entrada do servidor MCP sem nenhuma chave de API."""
    if command is None or args is None:
        default_cmd, default_args = mcp_launch_command(environ=environ)
        resolved_cmd = default_cmd if command is None else command
        resolved_args = default_args if args is None else list(args)
    else:
        resolved_cmd = command
        resolved_args = list(args)

    entry: dict[str, Any] = {
        "command": resolved_cmd,
        "args": resolved_args,
    }
    env = mcp_env(environ)
    if env:
        entry["env"] = env
    return entry


# FR-19, D-028: Caminho oficial do claude_desktop_config.json no Windows, macOS e Linux
def claude_desktop_config_path(
    *,
    platform: str | None = None,
    environ: Mapping[str, str] = os.environ,
    home: Path | None = None,
) -> Path:
    """Resolve o caminho do arquivo claude_desktop_config.json conforme o sistema operacional."""
    plat = sys.platform if platform is None else platform
    base_home = Path.home() if home is None else home

    if plat == "win32":
        appdata = environ.get("APPDATA")
        if isinstance(appdata, str) and appdata.strip():
            roaming = Path(appdata.strip()).expanduser()
        else:
            roaming = base_home / "AppData" / "Roaming"
        return roaming / "Claude" / "claude_desktop_config.json"

    if plat == "darwin":
        return (
            base_home
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )

    return base_home / ".config" / "Claude" / "claude_desktop_config.json"


# FR-19, D-028: Lê e valida claude_desktop_config.json (ou devolve {} se não existir) sem alterá-lo
def read_claude_desktop_config(config_path: Path | None = None) -> dict[str, Any]:
    """Lê claude_desktop_config.json ou devolve {} se ausente; levanta ClaudeConfigError se ilegível."""
    path = config_path if config_path is not None else claude_desktop_config_path()
    if not path.exists():
        return {}
    try:
        raw_text = path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ClaudeConfigError(path, str(exc)) from exc

    if not isinstance(data, dict):
        raise ClaudeConfigError(path, "o conteúdo JSON precisa ser um objeto")

    if "mcpServers" in data and not isinstance(data["mcpServers"], dict):
        raise ClaudeConfigError(path, "o campo 'mcpServers' precisa ser um objeto")

    return data


# FR-19, D-028: Determina o estado da conexão no Claude Desktop e devolve a entrada atual se existir
def inspect_claude_desktop(
    config_path: Path | None = None,
    *,
    command: str | None = None,
    args: Sequence[str] | None = None,
    environ: Mapping[str, str] = os.environ,
) -> tuple[ClaudeConnectionState, dict[str, Any] | None]:
    """Devolve (estado, entrada_atual_ou_none) comparando mcpServers.rslapp com a instalação atual."""
    data = read_claude_desktop_config(config_path)
    servers = data.get("mcpServers")
    if not isinstance(servers, dict) or "rslapp" not in servers:
        return "não conectado", None

    current = servers.get("rslapp")
    expected = mcp_server_entry(command=command, args=args, environ=environ)
    if isinstance(current, dict):
        same_cmd = current.get("command") == expected["command"]
        same_args = current.get("args", []) == expected["args"]
        cur_env = current.get("env") or {}
        exp_env = expected.get("env") or {}
        if same_cmd and same_args and cur_env == exp_env:
            return "conectado", copy.deepcopy(current)
        return "conectado a outra instalação", copy.deepcopy(current)

    return "conectado a outra instalação", {"valor_atual": copy.deepcopy(current)}


def claude_desktop_status(
    config_path: Path | None = None,
    *,
    command: str | None = None,
    args: Sequence[str] | None = None,
    environ: Mapping[str, str] = os.environ,
) -> ClaudeConnectionState:
    """Devolve 'conectado', 'conectado a outra instalação' ou 'não conectado'."""
    state, _ = inspect_claude_desktop(
        config_path,
        command=command,
        args=args,
        environ=environ,
    )
    return state


# FR-19, D-028: Junta a entrada rslapp preservando todas as outras chaves e servidores do arquivo
def merge_claude_desktop_entry(
    data: Mapping[str, Any],
    *,
    command: str | None = None,
    args: Sequence[str] | None = None,
    environ: Mapping[str, str] = os.environ,
) -> dict[str, Any]:
    """Devolve novo dicionário com mcpServers.rslapp atualizado, preservando o restante."""
    result: dict[str, Any] = copy.deepcopy(dict(data))
    existing_servers = result.get("mcpServers")
    servers: dict[str, Any] = (
        copy.deepcopy(existing_servers) if isinstance(existing_servers, dict) else {}
    )
    servers["rslapp"] = mcp_server_entry(command=command, args=args, environ=environ)
    result["mcpServers"] = servers
    return result


# FR-19, D-028: Remove apenas a entrada rslapp preservando todas as outras chaves e servidores
def remove_claude_desktop_entry(data: Mapping[str, Any]) -> dict[str, Any]:
    """Devolve novo dicionário sem mcpServers.rslapp, mantendo as demais chaves e servidores."""
    result: dict[str, Any] = copy.deepcopy(dict(data))
    existing_servers = result.get("mcpServers")
    if isinstance(existing_servers, dict):
        servers = copy.deepcopy(existing_servers)
        servers.pop("rslapp", None)
        result["mcpServers"] = servers
    return result


def _write_claude_backup(path: Path, *, now: datetime | None = None) -> Path:
    """Grava uma cópia claude_desktop_config.json.bak-<data e hora> na mesma pasta."""
    timestamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    backup_path = path.with_name(f"{path.name}.bak-{timestamp}")
    if path.is_file():
        original_content = path.read_text(encoding="utf-8")
    else:
        original_content = "{}\n"
    atomic_write_replace(backup_path, original_content)
    return backup_path


# FR-19, D-007, D-028: Conecta o RSL.app no Claude Desktop com cópia .bak e atomic_write_replace
def connect_claude_desktop(
    config_path: Path | None = None,
    *,
    command: str | None = None,
    args: Sequence[str] | None = None,
    environ: Mapping[str, str] = os.environ,
    now: datetime | None = None,
) -> tuple[Path, Path]:
    """Grava mcpServers.rslapp em claude_desktop_config.json após salvar cópia .bak-<data e hora>."""
    path = config_path if config_path is not None else claude_desktop_config_path()
    current_data = read_claude_desktop_config(path)
    updated_data = merge_claude_desktop_entry(
        current_data,
        command=command,
        args=args,
        environ=environ,
    )
    backup_path = _write_claude_backup(path, now=now)
    content = json.dumps(updated_data, ensure_ascii=False, indent=2) + "\n"
    atomic_write_replace(path, content)
    return path, backup_path


# FR-19, D-007, D-028: Desconecta o RSL.app do Claude Desktop removendo só rslapp com cópia .bak antes
def disconnect_claude_desktop(
    config_path: Path | None = None,
    *,
    now: datetime | None = None,
) -> tuple[Path, Path]:
    """Remove mcpServers.rslapp de claude_desktop_config.json após salvar cópia .bak-<data e hora>."""
    path = config_path if config_path is not None else claude_desktop_config_path()
    current_data = read_claude_desktop_config(path)
    updated_data = remove_claude_desktop_entry(current_data)
    backup_path = _write_claude_backup(path, now=now)
    content = json.dumps(updated_data, ensure_ascii=False, indent=2) + "\n"
    atomic_write_replace(path, content)
    return path, backup_path


# FR-19, D-028: Trecho JSON de mcpServers.rslapp para confirmação no Claude Desktop e para Outras IAs
def claude_desktop_snippet_json(
    *,
    command: str | None = None,
    args: Sequence[str] | None = None,
    environ: Mapping[str, str] = os.environ,
) -> str:
    """Devolve o trecho JSON de mcpServers.rslapp formatado."""
    entry = mcp_server_entry(command=command, args=args, environ=environ)
    return json.dumps({"mcpServers": {"rslapp": entry}}, ensure_ascii=False, indent=2)


# FR-19, D-028: Link cursor://anysphere.cursor-deeplink/mcp/install?name=rslapp&config=<base64>
def cursor_install_url(
    *,
    command: str | None = None,
    args: Sequence[str] | None = None,
    environ: Mapping[str, str] = os.environ,
) -> str:
    """Gera o deeplink de instalação do Cursor com config em JSON + base64 codificado para URL."""
    entry = mcp_server_entry(command=command, args=args, environ=environ)
    raw_json = json.dumps(entry, ensure_ascii=False)
    b64_str = base64.b64encode(raw_json.encode("utf-8")).decode("ascii")
    quoted_b64 = urllib.parse.quote(b64_str, safe="")
    return f"cursor://anysphere.cursor-deeplink/mcp/install?name=rslapp&config={quoted_b64}"


# FR-19, D-028: Abre o link do Cursor no sistema operacional sem usar shell=True
def open_cursor_link(url: str) -> None:
    """Abre o deeplink do Cursor usando os.startfile no Windows ou xdg-open no Linux, sem shell."""
    if sys.platform == "win32":
        os.startfile(url)  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", url], check=False)


# FR-19, D-028: JSON e comando oficial `code --add-mcp '<JSON>'` e trecho para `.vscode/mcp.json`
def vscode_add_mcp_json(
    *,
    command: str | None = None,
    args: Sequence[str] | None = None,
    environ: Mapping[str, str] = os.environ,
) -> str:
    """Devolve o JSON compacto para o comando `code --add-mcp`."""
    entry = mcp_server_entry(command=command, args=args, environ=environ)
    payload: dict[str, Any] = {
        "name": "rslapp",
        "type": "stdio",
        "command": entry["command"],
        "args": entry["args"],
    }
    if "env" in entry:
        payload["env"] = entry["env"]
    return json.dumps(payload, ensure_ascii=False)


def vscode_add_mcp_command(
    *,
    command: str | None = None,
    args: Sequence[str] | None = None,
    environ: Mapping[str, str] = os.environ,
) -> str:
    """Monta o comando `code --add-mcp '<JSON>'` para registrar o RSL.app no perfil do VS Code."""
    return f"code --add-mcp '{vscode_add_mcp_json(command=command, args=args, environ=environ)}'"


def vscode_mcp_config_json(
    *,
    command: str | None = None,
    args: Sequence[str] | None = None,
    environ: Mapping[str, str] = os.environ,
) -> str:
    """Monta o trecho JSON com `servers.rslapp` para o arquivo `.vscode/mcp.json`."""
    entry = mcp_server_entry(command=command, args=args, environ=environ)
    server_cfg: dict[str, Any] = {
        "type": "stdio",
        "command": entry["command"],
        "args": entry["args"],
    }
    if "env" in entry:
        server_cfg["env"] = entry["env"]
    return json.dumps({"servers": {"rslapp": server_cfg}}, ensure_ascii=False, indent=2)


# FR-19, D-028: Comando `claude mcp add` com `--env` antes de `--transport stdio` quando RSL_DESKTOP_CONFIG existir
def claude_code_command(
    *,
    command: str | None = None,
    args: Sequence[str] | None = None,
    environ: Mapping[str, str] = os.environ,
) -> str:
    """Monta o comando `claude mcp add` para registrar o RSL.app no escopo do usuário."""
    entry = mcp_server_entry(command=command, args=args, environ=environ)
    cmd_str = str(entry["command"])
    arg_list = [str(a) for a in entry["args"]]
    env = entry.get("env") or {}

    parts: list[str] = ["claude", "mcp", "add"]
    if "RSL_DESKTOP_CONFIG" in env:
        cfg_val = str(env["RSL_DESKTOP_CONFIG"])
        env_token = (
            f'"RSL_DESKTOP_CONFIG={cfg_val}"'
            if " " in cfg_val
            else f"RSL_DESKTOP_CONFIG={cfg_val}"
        )
        parts.extend(["--env", env_token])

    parts.extend(
        [
            "--transport",
            "stdio",
            "--scope",
            "user",
            "rslapp",
            "--",
            f'"{cmd_str}"',
        ]
    )
    for item in arg_list:
        parts.append(f'"{item}"' if " " in item else item)
    return " ".join(parts)


# FR-19, D-028: Trecho JSON genérico para outras IAs que aceitem servidor MCP local
def generic_mcp_json(
    *,
    command: str | None = None,
    args: Sequence[str] | None = None,
    environ: Mapping[str, str] = os.environ,
) -> str:
    """Devolve o trecho JSON genérico (`mcpServers.rslapp` com `command` e `args`)."""
    return claude_desktop_snippet_json(command=command, args=args, environ=environ)
