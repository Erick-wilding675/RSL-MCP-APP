"""Testes das opções --check e --mcp e interpretação de argumentos do app desktop sem importar nicegui (D-025, D-026, D-028, FR-16, FR-19)."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters

from rslapp import server
from rslapp.desktop import app as desktop_app
from rslapp.desktop.service import DesktopService
from rslapp.desktop.settings import ALLOWED_VARS, DesktopSettings, save_settings


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# D-025, FR-16: parse_args interpreta argumentos vazios, --check e sys.argv sem importar nicegui
def test_d025_fr16_parse_args_decide_modo_check_sem_importar_nicegui(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert desktop_app.parse_args([]).check is False
    assert desktop_app.parse_args(["--check"]).check is True

    monkeypatch.setattr(sys, "argv", ["rslapp-desktop", "--check"])
    assert desktop_app.parse_args().check is True

    monkeypatch.setattr(sys, "argv", ["rslapp-desktop"])
    assert desktop_app.parse_args().check is False

    with pytest.raises(SystemExit) as exc_info:
        desktop_app.parse_args(["--opcao-invalida"])
    assert exc_info.value.code == 2

    monkeypatch.setattr(sys, "argv", ["rslapp-desktop", "--opcao-invalida"])
    with pytest.raises(SystemExit) as exc_info_argv:
        desktop_app.parse_args()
    assert exc_info_argv.value.code == 2
    assert "nicegui" not in sys.modules


# D-025, D-026, FR-16: main(["--check"]) carrega configurações, registra páginas, confere fontes e sai com 0 sem abrir janela
def test_d025_fr16_main_check_registra_paginas_e_sai_zero_sem_ui_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    for var in ALLOWED_VARS:
        monkeypatch.delenv(var, raising=False)

    cfg_file = tmp_path / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))
    save_settings(DesktopSettings(values={"RSL_CONTACT_EMAIL": "check@exemplo.org"}))

    events: list[str] = []

    def fake_register_pages(service: DesktopService | None = None) -> DesktopService:
        events.append("register_pages")
        return service if service is not None else DesktopService()

    def fake_run_ui() -> None:
        events.append("run_ui")

    monkeypatch.setattr(desktop_app, "register_pages", fake_register_pages)
    monkeypatch.setattr(desktop_app, "_run_ui", fake_run_ui)

    exit_code = desktop_app.main(["--check"])
    assert exit_code == 0
    assert events == ["register_pages"]
    assert os.environ.get("RSL_CONTACT_EMAIL") == "check@exemplo.org"
    assert "nicegui" not in sys.modules

    # No modo normal (sem --check), registra as páginas e chama _run_ui
    events.clear()
    exit_code_normal = desktop_app.main([])
    assert exit_code_normal == 0
    assert events == ["register_pages", "run_ui"]
    assert "nicegui" not in sys.modules


# D-025, FR-16: No Windows com --windowed (stdout/stderr None), _ensure_stdio_streams evita falha do uvicorn
def test_d025_fr16_ensure_stdio_streams_substitui_none_por_devnull(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    desktop_app._ensure_stdio_streams()
    try:
        assert sys.stdout is not None
        assert sys.stderr is not None
        assert isinstance(sys.stdout.isatty(), bool)
        assert isinstance(sys.stderr.isatty(), bool)
        sys.stdout.write("ok\n")
        sys.stderr.write("ok\n")
    finally:
        if sys.stdout is not None:
            sys.stdout.close()
        if sys.stderr is not None:
            sys.stderr.close()


# D-028, FR-19: parse_args interpreta --mcp e recusa --mcp junto com --check (código 2) sem importar nicegui
def test_d028_fr19_parse_args_mcp_e_exclusao_mutua_com_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args_default = desktop_app.parse_args([])
    assert args_default.mcp is False
    assert args_default.check is False

    args_mcp = desktop_app.parse_args(["--mcp"])
    assert args_mcp.mcp is True
    assert args_mcp.check is False

    args_check = desktop_app.parse_args(["--check"])
    assert args_check.mcp is False
    assert args_check.check is True

    monkeypatch.setattr(sys, "argv", ["rslapp-desktop", "--mcp"])
    assert desktop_app.parse_args().mcp is True

    for combo in (["--mcp", "--check"], ["--check", "--mcp"]):
        with pytest.raises(SystemExit) as exc_info:
            desktop_app.parse_args(combo)
        assert exc_info.value.code == 2

    assert "nicegui" not in sys.modules


# D-026, D-028, FR-19: main(["--mcp"]) carrega desktop.json sem sobrescrever o sistema, chama server.main e não escreve no stdout
def test_d026_d028_fr19_main_mcp_carrega_configuracoes_chama_servidor_sem_stdout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    for var in ALLOWED_VARS:
        monkeypatch.delenv(var, raising=False)

    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "s2-do-sistema")
    cfg_file = tmp_path / "desktop.json"
    data_dir = tmp_path / "dados_mcp"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))
    save_settings(
        DesktopSettings(
            values={
                "OPENALEX_API_KEY": "oa-do-desktop",
                "SEMANTIC_SCHOLAR_API_KEY": "s2-do-desktop",
                "RSL_CONTACT_EMAIL": "mcp@exemplo.org",
                "RSL_DATA_DIR": str(data_dir),
            }
        )
    )

    server_calls: list[dict[str, str | None]] = []

    def fake_server_main() -> None:
        server_calls.append(
            {
                "OPENALEX_API_KEY": os.environ.get("OPENALEX_API_KEY"),
                "SEMANTIC_SCHOLAR_API_KEY": os.environ.get("SEMANTIC_SCHOLAR_API_KEY"),
                "RSL_CONTACT_EMAIL": os.environ.get("RSL_CONTACT_EMAIL"),
                "RSL_DATA_DIR": os.environ.get("RSL_DATA_DIR"),
            }
        )

    monkeypatch.setattr(desktop_app.server, "main", fake_server_main)
    monkeypatch.setattr(
        desktop_app,
        "register_pages",
        lambda *_a, **_kw: pytest.fail("register_pages não deve rodar em --mcp"),
    )
    monkeypatch.setattr(
        desktop_app,
        "_run_ui",
        lambda: pytest.fail("_run_ui não deve rodar em --mcp"),
    )
    monkeypatch.setattr(
        desktop_app,
        "_run_check",
        lambda: pytest.fail("_run_check não deve rodar em --mcp"),
    )

    exit_code = desktop_app.main(["--mcp"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""
    assert server_calls == [
        {
            "OPENALEX_API_KEY": "oa-do-desktop",
            "SEMANTIC_SCHOLAR_API_KEY": "s2-do-sistema",
            "RSL_CONTACT_EMAIL": "mcp@exemplo.org",
            "RSL_DATA_DIR": str(data_dir),
        }
    ]
    assert "nicegui" not in sys.modules


# D-028, FR-19: No modo --mcp, stdin ou stdout None não são trocados por devnull e retornam código 1
def test_d028_fr19_main_mcp_recusa_stdin_ou_stdout_none_sem_trocar_por_devnull(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))
    monkeypatch.setattr(
        desktop_app.server,
        "main",
        lambda: pytest.fail("server.main não deve rodar sem stdin/stdout"),
    )

    # 1. stdin None com stderr presente: escreve mensagem curta no stderr e sai com 1
    with monkeypatch.context() as mp:
        mp.setattr(sys, "stdin", None)
        code_no_stdin = desktop_app.main(["--mcp"])
        assert code_no_stdin == 1
        assert sys.stdin is None
    captured_stdin = capsys.readouterr()
    assert captured_stdin.out == ""
    assert "--mcp" in captured_stdin.err

    # 2. stdout None com stderr presente: escreve mensagem curta no stderr e sai com 1
    with monkeypatch.context() as mp:
        mp.setattr(sys, "stdout", None)
        code_no_stdout = desktop_app.main(["--mcp"])
        assert code_no_stdout == 1
        assert sys.stdout is None
    captured_stdout = capsys.readouterr()
    assert captured_stdout.out == ""
    assert "--mcp" in captured_stdout.err

    # 3. stdout e stderr None: sai com 1 sem levantar exceção
    with monkeypatch.context() as mp:
        mp.setattr(sys, "stdout", None)
        mp.setattr(sys, "stderr", None)
        code_no_both = desktop_app.main(["--mcp"])
        assert code_no_both == 1
        assert sys.stdout is None
        assert sys.stderr is None


# D-026, D-028, FR-19: Teste de ponta a ponta em subprocesso com python -m rslapp.desktop --mcp
@pytest.mark.anyio
async def test_d026_d028_fr19_ponta_a_ponta_desktop_mcp_stdio_initialize_e_tools_list(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "desktop.json"
    data_dir = tmp_path / "rsl_data"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))
    save_settings(
        DesktopSettings(
            values={
                "OPENALEX_API_KEY": "fake-oa-desktop-key",
                "RSL_CONTACT_EMAIL": "pesquisador@inst.br",
            }
        )
    )

    env: dict[str, str] = {}
    for var in ("SYSTEMROOT", "PATH", "USERPROFILE", "PYTHONPATH"):
        if var in os.environ:
            env[var] = os.environ[var]
    env.setdefault("USERPROFILE", str(tmp_path))
    env["HOME"] = str(tmp_path)
    env["RSL_DATA_DIR"] = str(data_dir)
    env["RSL_DESKTOP_CONFIG"] = str(cfg_file)

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "rslapp.desktop", "--mcp"],
        env=env,
    )

    async with Client(params) as client:
        assert client.instructions == server.INSTRUCTIONS
        tools_result = await client.list_tools()
        tool_names = [tool.name for tool in tools_result.tools]
        assert "search_works" in tool_names

        call_result = await client.call_tool("list_sources", {})
        assert call_result.is_error is False
        sources = {item["name"]: item for item in call_result.structured_content["result"]}
        assert sources["openalex"] == {
            "name": "openalex",
            "configured": True,
            "needs_key": True,
            "status": "ok",
        }
        assert "fake-oa-desktop-key" not in call_result.model_dump_json()


# D-028, FR-19: Script packaging/smoke_mcp.py valida initialize via Popen/pipes e falha quando não há JSON-RPC
def test_d028_fr19_smoke_mcp_script_valida_initialize_e_erros(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    smoke_path = Path(__file__).resolve().parents[2] / "packaging" / "smoke_mcp.py"
    if not smoke_path.exists():
        pytest.skip("packaging/smoke_mcp.py ausente fora do repositório")

    spec = importlib.util.spec_from_file_location("smoke_mcp", smoke_path)
    assert spec is not None and spec.loader is not None
    smoke_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke_mod)

    fake_appimage = tmp_path / "RSL.app-2.0.0-linux-x86_64.AppImage"
    fake_appimage.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    built_cmd = smoke_mod.resolve_command(
        ["./RSL.app-2.0.0-linux-x86_64.AppImage", "--appimage-extract-and-run", "--mcp"]
    )
    assert built_cmd == [
        str(fake_appimage.resolve()),
        "--appimage-extract-and-run",
        "--mcp",
    ]
    assert Path(built_cmd[0]).is_absolute()

    assert smoke_mod.main([]) == 2
    assert smoke_mod.main([sys.executable, "-m", "rslapp.desktop", "--mcp"]) == 0
    assert (
        smoke_mod.run_smoke_test(
            [sys.executable, "-c", "import sys; sys.stdout.write('nao-json\\n')"],
            timeout=5.0,
        )
        == 1
    )
