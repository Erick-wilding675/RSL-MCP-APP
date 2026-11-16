"""Testes unitários de connect.py sem importar o NiceGUI (FR-19, D-026, D-028, NFR-03)."""

from __future__ import annotations

import base64
import json
import subprocess
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from rslapp.desktop import connect
from rslapp.desktop.connect import (
    ClaudeConfigError,
    claude_code_command,
    claude_desktop_config_path,
    claude_desktop_snippet_json,
    claude_desktop_status,
    connect_claude_desktop,
    cursor_install_url,
    disconnect_claude_desktop,
    generic_mcp_json,
    inspect_claude_desktop,
    mcp_launch_command,
    open_cursor_link,
    vscode_add_mcp_command,
    vscode_add_mcp_json,
    vscode_mcp_config_json,
)
from rslapp.desktop.settings import KEY_VARS


# FR-19, D-028: Importar connect não pode carregar o NiceGUI
def test_fr19_d028_import_connect_nao_importa_nicegui() -> None:
    assert connect is not None
    assert "nicegui" not in sys.modules


# FR-19, D-028: mcp_launch_command nos casos executável empacotado, AppImage e pip (com e sem binário rslapp)
def test_fr19_d028_mcp_launch_command_executavel_appimage_e_pip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("APPIMAGE", raising=False)

    # 1. Executável empacotado (sys.frozen = True)
    fake_exe = tmp_path / "dist" / "RSL.app" / "RSL.app.exe"
    fake_exe.parent.mkdir(parents=True, exist_ok=True)
    fake_exe.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))

    cmd_frozen, args_frozen = mcp_launch_command(environ={})
    assert cmd_frozen == str(fake_exe.resolve())
    assert args_frozen == ["--mcp"]

    # 2. AppImage: usa o caminho de APPIMAGE, e não o caminho temporário de sys.executable
    fake_appimage = tmp_path / "Apps" / "RSL.app-2.1.0-linux-x86_64.AppImage"
    fake_mount_exe = tmp_path / "tmp_mount" / "usr" / "bin" / "RSL.app"
    monkeypatch.setattr(sys, "executable", str(fake_mount_exe))
    cmd_appimage, args_appimage = mcp_launch_command(
        environ={"APPIMAGE": str(fake_appimage)}
    )
    assert cmd_appimage == str(fake_appimage.resolve())
    assert args_appimage == ["--mcp"]

    # 3. Instalado pelo pip, com comando rslapp ao lado de sys.executable
    monkeypatch.delattr(sys, "frozen", raising=False)
    venv_dir = tmp_path / "venv_bin"
    venv_dir.mkdir(parents=True, exist_ok=True)
    fake_python = venv_dir / ("python.exe" if sys.platform == "win32" else "python")
    fake_python.write_text("", encoding="utf-8")
    fake_rslapp = venv_dir / ("rslapp.exe" if sys.platform == "win32" else "rslapp")
    fake_rslapp.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "executable", str(fake_python))

    cmd_pip, args_pip = mcp_launch_command(environ={})
    assert cmd_pip == str(fake_rslapp)
    assert args_pip == []

    # 4. Instalado pelo pip, sem binário rslapp ao lado de sys.executable: recua para python -m rslapp
    fake_rslapp.unlink()
    cmd_fallback, args_fallback = mcp_launch_command(environ={})
    assert cmd_fallback == str(fake_python)
    assert args_fallback == ["-m", "rslapp"]


# FR-19, D-028: Confere que `python -m rslapp --help` funciona no ambiente atual
def test_fr19_d028_python_m_rslapp_funciona() -> None:
    res = subprocess.run(
        [sys.executable, "-m", "rslapp", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert res.returncode == 0
    assert "rslapp" in res.stdout


# FR-19, D-028: Caminho do claude_desktop_config.json no Windows, macOS e Linux
def test_fr19_d028_claude_desktop_config_path_por_sistema(tmp_path: Path) -> None:
    roaming = tmp_path / "Roaming"
    win_path = claude_desktop_config_path(
        platform="win32",
        environ={"APPDATA": str(roaming)},
        home=tmp_path,
    )
    assert win_path == roaming / "Claude" / "claude_desktop_config.json"

    win_fallback = claude_desktop_config_path(
        platform="win32",
        environ={},
        home=tmp_path,
    )
    assert (
        win_fallback
        == tmp_path / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    )

    mac_path = claude_desktop_config_path(
        platform="darwin",
        environ={},
        home=tmp_path,
    )
    assert (
        mac_path
        == tmp_path
        / "Library"
        / "Application Support"
        / "Claude"
        / "claude_desktop_config.json"
    )

    linux_path = claude_desktop_config_path(
        platform="linux",
        environ={},
        home=tmp_path,
    )
    assert linux_path == tmp_path / ".config" / "Claude" / "claude_desktop_config.json"


# FR-19, D-007, D-028: Conectar, estado e desconectar no Claude Desktop preservam outros servidores e chaves e criam .bak
def test_fr19_d007_d028_claude_desktop_conectar_estado_e_desconectar_preserva_arquivo_e_cria_bak(
    tmp_path: Path,
) -> None:
    cfg_path = tmp_path / "Claude" / "claude_desktop_config.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    # Sem arquivo: estado é "não conectado"
    assert (
        claude_desktop_status(
            cfg_path,
            command="/opt/rslapp/RSL.app",
            args=["--mcp"],
            environ={},
        )
        == "não conectado"
    )

    # Arquivo existente com outra chave de topo e outro servidor MCP e rslapp apontando para outra instalação
    initial_data = {
        "globalShortcut": "Ctrl+Space",
        "preferences": {"theme": "dark"},
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            },
            "rslapp": {
                "command": "uvx",
                "args": ["rslapp"],
            },
        },
    }
    initial_text = json.dumps(initial_data, ensure_ascii=False, indent=2) + "\n"
    cfg_path.write_text(initial_text, encoding="utf-8")

    state_other, current_entry = inspect_claude_desktop(
        cfg_path,
        command="/opt/rslapp/RSL.app",
        args=["--mcp"],
        environ={},
    )
    assert state_other == "conectado a outra instalação"
    assert current_entry == {"command": "uvx", "args": ["rslapp"]}

    # Conecta ao comando deste app
    t1 = datetime(2026, 11, 15, 22, 30, 45)
    written_path, bak_path = connect_claude_desktop(
        cfg_path,
        command="/opt/rslapp/RSL.app",
        args=["--mcp"],
        environ={},
        now=t1,
    )
    assert written_path == cfg_path
    assert bak_path == cfg_path.with_name("claude_desktop_config.json.bak-20261115-223045")
    assert bak_path.read_text(encoding="utf-8") == initial_text

    saved = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert saved["globalShortcut"] == "Ctrl+Space"
    assert saved["preferences"] == {"theme": "dark"}
    assert saved["mcpServers"]["filesystem"] == initial_data["mcpServers"]["filesystem"]
    assert saved["mcpServers"]["rslapp"] == {
        "command": "/opt/rslapp/RSL.app",
        "args": ["--mcp"],
    }

    assert (
        claude_desktop_status(
            cfg_path,
            command="/opt/rslapp/RSL.app",
            args=["--mcp"],
            environ={},
        )
        == "conectado"
    )

    # Desconecta: remove só rslapp, preserva filesystem e globalShortcut, e grava novo .bak
    t2 = datetime(2026, 11, 15, 22, 31, 10)
    _, bak_disconnect = disconnect_claude_desktop(cfg_path, now=t2)
    assert bak_disconnect == cfg_path.with_name(
        "claude_desktop_config.json.bak-20261115-223110"
    )
    assert json.loads(bak_disconnect.read_text(encoding="utf-8")) == saved

    after_disconnect = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert after_disconnect["globalShortcut"] == "Ctrl+Space"
    assert after_disconnect["preferences"] == {"theme": "dark"}
    assert (
        after_disconnect["mcpServers"]["filesystem"]
        == initial_data["mcpServers"]["filesystem"]
    )
    assert "rslapp" not in after_disconnect["mcpServers"]
    assert (
        claude_desktop_status(
            cfg_path,
            command="/opt/rslapp/RSL.app",
            args=["--mcp"],
            environ={},
        )
        == "não conectado"
    )


# FR-19, D-028: Arquivo claude_desktop_config.json ilegível não é modificado e devolve erro com o caminho
def test_fr19_d028_claude_desktop_arquivo_ilegivel_nao_mexe_e_inclui_caminho(
    tmp_path: Path,
) -> None:
    cfg_path = tmp_path / "Claude" / "claude_desktop_config.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    corrupted = "{json corrompido sem fechar"
    cfg_path.write_text(corrupted, encoding="utf-8")

    with pytest.raises(ClaudeConfigError) as exc_info:
        connect_claude_desktop(
            cfg_path,
            command="/opt/rslapp/RSL.app",
            args=["--mcp"],
            environ={},
        )
    assert str(cfg_path) in str(exc_info.value)
    assert cfg_path.read_text(encoding="utf-8") == corrupted
    assert list(cfg_path.parent.glob("*.bak-*")) == []

    with pytest.raises(ClaudeConfigError) as exc_disconnect:
        disconnect_claude_desktop(cfg_path)
    assert str(cfg_path) in str(exc_disconnect.value)
    assert cfg_path.read_text(encoding="utf-8") == corrupted
    assert list(cfg_path.parent.glob("*.bak-*")) == []


# FR-19, D-028: Link do Cursor decodificado de volta ao mesmo JSON e abertura sem shell=True
def test_fr19_d028_cursor_install_url_decodifica_mesmo_json_e_abre_sem_shell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cmd = r"C:\Program Files\RSL.app\RSL.app.exe"
    args = ["--mcp"]
    env = {"RSL_DESKTOP_CONFIG": r"C:\Users\Maria Silva\desktop.json"}

    url = cursor_install_url(command=cmd, args=args, environ=env)
    assert url.startswith(
        "cursor://anysphere.cursor-deeplink/mcp/install?name=rslapp&config="
    )

    parsed = urllib.parse.urlsplit(url)
    assert parsed.scheme == "cursor"
    assert parsed.netloc == "anysphere.cursor-deeplink"
    assert parsed.path == "/mcp/install"

    # A parte config na query está codificada para URL (sem '+', '/' ou '=' crus)
    raw_config_param = parsed.query.split("&config=", 1)[1]
    assert "+" not in raw_config_param
    assert "/" not in raw_config_param
    assert "=" not in raw_config_param

    unquoted_b64 = urllib.parse.unquote(raw_config_param)
    decoded_json = base64.b64decode(unquoted_b64.encode("ascii")).decode("utf-8")
    decoded_obj = json.loads(decoded_json)
    assert decoded_obj == {
        "command": cmd,
        "args": ["--mcp"],
        "env": {"RSL_DESKTOP_CONFIG": r"C:\Users\Maria Silva\desktop.json"},
    }

    # Confere abertura sem shell=True no Windows e no Linux
    startfile_calls: list[str] = []
    monkeypatch.setattr(connect.sys, "platform", "win32")
    monkeypatch.setattr(
        connect.os,
        "startfile",
        lambda u: startfile_calls.append(u),
        raising=False,
    )
    open_cursor_link(url)
    assert startfile_calls == [url]

    subprocess_calls: list[tuple[Any, dict[str, Any]]] = []
    monkeypatch.setattr(connect.sys, "platform", "linux")
    monkeypatch.setattr(
        connect.subprocess,
        "run",
        lambda a, **kw: subprocess_calls.append((a, kw)),
    )
    open_cursor_link(url)
    assert subprocess_calls == [(["xdg-open", url], {"check": False})]


# FR-19, D-028: JSON do code --add-mcp, .vscode/mcp.json e comando do Claude Code com e sem RSL_DESKTOP_CONFIG e com espaço
def test_fr19_d028_vscode_e_claude_code_com_e_sem_rsl_desktop_config_e_com_espaco() -> None:
    cmd_space = r"C:\Program Files\RSL.app\RSL.app.exe"
    args = ["--mcp"]

    # 1. Sem RSL_DESKTOP_CONFIG
    vs_json_no_env = vscode_add_mcp_json(command=cmd_space, args=args, environ={})
    assert json.loads(vs_json_no_env) == {
        "name": "rslapp",
        "type": "stdio",
        "command": cmd_space,
        "args": ["--mcp"],
    }
    vs_cmd_no_env = vscode_add_mcp_command(command=cmd_space, args=args, environ={})
    assert vs_cmd_no_env == f"code --add-mcp '{vs_json_no_env}'"

    vs_file_no_env = json.loads(
        vscode_mcp_config_json(command=cmd_space, args=args, environ={})
    )
    assert vs_file_no_env == {
        "servers": {
            "rslapp": {
                "type": "stdio",
                "command": cmd_space,
                "args": ["--mcp"],
            }
        }
    }

    cc_no_env = claude_code_command(command=cmd_space, args=args, environ={})
    assert (
        cc_no_env
        == f'claude mcp add --transport stdio --scope user rslapp -- "{cmd_space}" --mcp'
    )

    # 2. Com RSL_DESKTOP_CONFIG sem espaço
    env_simple = {"RSL_DESKTOP_CONFIG": "/tmp/rsl/desktop.json"}
    cc_simple_env = claude_code_command(
        command="/opt/RSL.app",
        args=["--mcp"],
        environ=env_simple,
    )
    assert cc_simple_env == (
        "claude mcp add --env RSL_DESKTOP_CONFIG=/tmp/rsl/desktop.json "
        '--transport stdio --scope user rslapp -- "/opt/RSL.app" --mcp'
    )
    # --env vem antes de --transport stdio para não ficar logo antes do nome rslapp
    assert cc_simple_env.index("--env") < cc_simple_env.index("--transport")
    assert cc_simple_env.index("--transport") < cc_simple_env.index("rslapp")

    # 3. Com RSL_DESKTOP_CONFIG contendo espaço no caminho
    cfg_with_space = r"C:\Users\Maria Silva\Config RSL\desktop.json"
    env_space = {"RSL_DESKTOP_CONFIG": cfg_with_space}

    vs_json_env = vscode_add_mcp_json(command=cmd_space, args=args, environ=env_space)
    assert json.loads(vs_json_env) == {
        "name": "rslapp",
        "type": "stdio",
        "command": cmd_space,
        "args": ["--mcp"],
        "env": {"RSL_DESKTOP_CONFIG": cfg_with_space},
    }

    cc_space_env = claude_code_command(
        command=cmd_space,
        args=args,
        environ=env_space,
    )
    assert f'"RSL_DESKTOP_CONFIG={cfg_with_space}"' in cc_space_env
    assert f'-- "{cmd_space}" --mcp' in cc_space_env
    assert cc_space_env.index("--env") < cc_space_env.index("--transport")


# FR-19, D-026, NFR-03: Nenhuma chave entra em nenhuma saída de connect.py, mesmo com todas as chaves no ambiente
def test_fr19_d026_nfr03_nenhuma_chave_entra_nas_saidas_mesmo_com_chaves_no_ambiente(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    secrets = {var: f"segredo-proibido-{var.lower()}-98765" for var in KEY_VARS}
    for var_name, secret_val in secrets.items():
        monkeypatch.setenv(var_name, secret_val)
    monkeypatch.setenv("RSL_CONTACT_EMAIL", "pesquisador@inst.br")
    monkeypatch.setenv("RSL_DATA_DIR", str(tmp_path / "dados"))
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(tmp_path / "desktop.json"))

    cmd = "/opt/rslapp/RSL.app"
    args = ["--mcp"]

    cfg_path = tmp_path / "claude_desktop_config.json"
    connect_claude_desktop(cfg_path, command=cmd, args=args)

    cursor_url = cursor_install_url(command=cmd, args=args)
    raw_b64 = urllib.parse.unquote(cursor_url.split("&config=", 1)[1])
    cursor_decoded = base64.b64decode(raw_b64.encode("ascii")).decode("utf-8")

    text_outputs = [
        cfg_path.read_text(encoding="utf-8"),
        claude_desktop_snippet_json(command=cmd, args=args),
        vscode_add_mcp_json(command=cmd, args=args),
        vscode_add_mcp_command(command=cmd, args=args),
        vscode_mcp_config_json(command=cmd, args=args),
        claude_code_command(command=cmd, args=args),
        generic_mcp_json(command=cmd, args=args),
        cursor_decoded,
    ]

    for out in [*text_outputs, cursor_url]:
        for var_name, secret_val in secrets.items():
            assert var_name not in out
            assert secret_val not in out

    for out in text_outputs:
        assert "RSL_DESKTOP_CONFIG" in out
