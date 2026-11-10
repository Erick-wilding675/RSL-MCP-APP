"""Testes da interface de linha de comando (cli.py) e da configuração HTTP (config.py)."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

import pytest

from rslapp import cli, config, server

ENV_VARS = (
    "RSL_DATA_DIR",
    "RSL_EXPORT_DIR",
    "RSL_CACHE_DAYS",
    "OPENALEX_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "RSL_CONTACT_EMAIL",
    "RSL_HTTP_HOST",
    "RSL_HTTP_PORT",
    "RSL_PUBLIC_URL",
    "RSL_FORWARDED_ALLOW_IPS",
)


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Limpa variáveis de ambiente do RSL.app e isola a pasta home do usuário."""
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    fake_home = tmp_path / "fake_home"
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    return fake_home


def _build_clean_env(tmp_path: Path, **overrides: str) -> dict[str, str]:
    """Monta ambiente limpo para subprocesso no Windows e POSIX."""
    env: dict[str, str] = {}
    for var in ("SYSTEMROOT", "PATH", "USERPROFILE"):
        if var in os.environ:
            env[var] = os.environ[var]
    env.setdefault("USERPROFILE", str(tmp_path))
    env["HOME"] = str(tmp_path)
    env.update(overrides)
    return env


def _require_rslapp_command() -> str:
    """Obtém o caminho do comando instalado rslapp."""
    rslapp_cmd = shutil.which("rslapp")
    assert rslapp_cmd is not None, "Comando 'rslapp' não encontrado no PATH"
    return rslapp_cmd


# D-011, D-008: rslapp sem argumento continua iniciando o stdio sem escrever em stdout
def test_d011_rslapp_sem_argumento_inicia_stdio_sem_escrever_em_stdout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    chamadas: list[str] = []
    monkeypatch.setattr(server, "main", lambda: chamadas.append("stdio"))

    cli.main([])

    capturado = capsys.readouterr()
    assert chamadas == ["stdio"]
    assert capturado.out == ""
    assert capturado.err == ""


# D-011, D-006: rslapp.server:main continua existindo e chamando mcp.run() no modo stdio
def test_d011_server_main_continua_iniciando_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(
        server.mcp,
        "run",
        lambda *args, **kwargs: chamadas.append((args, kwargs)),
    )

    server.main()

    assert chamadas == [((), {})]


# D-011: rslapp --help e rslapp serve --help mostram os comandos em português sem iniciar servidor
def test_d011_help_e_serve_help_mostram_comandos_em_portugues_sem_iniciar_servidor(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    def _nao_deve_iniciar(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Nenhum servidor deveria ser iniciado ao exibir --help")

    monkeypatch.setattr(server, "main", _nao_deve_iniciar)
    monkeypatch.setattr(server, "run_http", _nao_deve_iniciar, raising=False)

    with pytest.raises(SystemExit) as exc_main:
        cli.main(["--help"])
    assert exc_main.value.code == 0
    out_main = capsys.readouterr().out
    assert "serve" in out_main
    assert "stdio" in out_main.lower()
    assert "busca acadêmica" in out_main.lower()

    with pytest.raises(SystemExit) as exc_serve:
        cli.main(["serve", "--help"])
    assert exc_serve.value.code == 0
    out_serve = capsys.readouterr().out
    assert "--host" in out_serve
    assert "--port" in out_serve
    assert "RSL_HTTP_HOST" in out_serve
    assert "RSL_HTTP_PORT" in out_serve

    # Verifica também pelo comando instalado em subprocesso real
    rslapp_cmd = _require_rslapp_command()
    proc_help = subprocess.run(
        [rslapp_cmd, "--help"],
        env=_build_clean_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert proc_help.returncode == 0
    assert "serve" in proc_help.stdout

    proc_serve_help = subprocess.run(
        [rslapp_cmd, "serve", "--help"],
        env=_build_clean_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert proc_serve_help.returncode == 0
    assert "--host" in proc_serve_help.stdout
    assert "--port" in proc_serve_help.stdout


# D-011: rslapp serve --host 0.0.0.0 sai com erro e mensagem clara no stderr sem abrir a porta
@pytest.mark.parametrize("bad_host", ["0.0.0.0", "192.168.1.10", "exemplo.org"])
def test_d011_serve_recusa_host_fora_de_loopback_sem_abrir_porta(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    bad_host: str,
) -> None:
    iniciou = False

    def _nao_deve_iniciar(*_args: object, **_kwargs: object) -> None:
        nonlocal iniciou
        iniciou = True

    monkeypatch.setattr(server, "run_http", _nao_deve_iniciar, raising=False)

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["serve", "--host", bad_host])

    assert exc_info.value.code != 0
    assert iniciou is False
    capturado = capsys.readouterr()
    assert capturado.out == ""
    assert "loopback" in capturado.err.lower()
    assert "127.0.0.1" in capturado.err
    assert bad_host in capturado.err


# D-011: Subprocesso real de rslapp serve --host 0.0.0.0 termina com código != 0 e mensagem no stderr
def test_d011_serve_host_0000_em_subprocesso_sai_com_erro_e_mensagem_clara(
    tmp_path: Path,
) -> None:
    rslapp_cmd = _require_rslapp_command()
    proc = subprocess.run(
        [rslapp_cmd, "serve", "--host", "0.0.0.0"],
        env=_build_clean_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert "loopback" in proc.stderr.lower()
    assert "127.0.0.1" in proc.stderr


# D-011: RSL_HTTP_HOST fora de loopback também é recusado por rslapp serve
def test_d011_serve_recusa_rsl_http_host_fora_de_loopback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("RSL_HTTP_HOST", "0.0.0.0")
    monkeypatch.setattr(
        server,
        "run_http",
        lambda *_a, **_kw: pytest.fail("Não deveria abrir porta"),
        raising=False,
    )

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["serve"])

    assert exc_info.value.code != 0
    err = capsys.readouterr().err
    assert "loopback" in err.lower()


# D-011, D-017: Padrões e variáveis de ambiente de load_http e sobreposição por --host e --port
def test_d011_d017_load_http_padroes_variaveis_e_sobreposicao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    padrao = config.load_http()
    assert padrao.host == "127.0.0.1"
    assert padrao.port == 8000
    assert padrao.public_url == "http://127.0.0.1:8000"
    assert padrao.forwarded_allow_ips == "127.0.0.1"

    # Quando RSL_HTTP_PORT muda e RSL_PUBLIC_URL não está definida, public_url usa a nova porta
    monkeypatch.setenv("RSL_HTTP_HOST", "localhost")
    monkeypatch.setenv("RSL_HTTP_PORT", "9001")
    monkeypatch.setenv("RSL_FORWARDED_ALLOW_IPS", "172.18.0.1")
    cfg_env = config.load_http()
    assert cfg_env.host == "localhost"
    assert cfg_env.port == 9001
    assert cfg_env.public_url == "http://127.0.0.1:9001"
    assert cfg_env.forwarded_allow_ips == "172.18.0.1"

    # --host e --port sobrepõem RSL_HTTP_HOST e RSL_HTTP_PORT
    cfg_override = config.load_http(host="::1", port=9002)
    assert cfg_override.host == "::1"
    assert cfg_override.port == 9002
    assert cfg_override.public_url == "http://127.0.0.1:9002"

    # Com RSL_PUBLIC_URL definida, ela prevalece e remove barra final
    monkeypatch.setenv("RSL_PUBLIC_URL", "https://rsl.exemplo.org/")
    cfg_pub = config.load_http(port=9003)
    assert cfg_pub.public_url == "https://rsl.exemplo.org"


# D-011, D-015, D-017: rslapp serve --host 0.0.0.0 inicia quando RSL_PUBLIC_URL usa https:// e recusa com http://
def test_d015_serve_host_0000_inicia_com_https_e_recusa_com_http(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    recebido: list[tuple[str | None, int | None]] = []
    monkeypatch.setattr(
        server,
        "run_http",
        lambda *, host=None, port=None: recebido.append((host, port)),
        raising=False,
    )

    monkeypatch.setenv("RSL_PUBLIC_URL", "https://exemplo.org")
    cli.main(["serve", "--host", "0.0.0.0", "--port", "8080"])
    assert recebido == [("0.0.0.0", 8080)]

    recebido.clear()
    monkeypatch.setenv("RSL_PUBLIC_URL", "http://exemplo.org")
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["serve", "--host", "0.0.0.0", "--port", "8080"])
    assert exc_info.value.code != 0
    assert recebido == []
    assert "https://" in capsys.readouterr().err


# D-011: rslapp serve repassa --host e --port que sobrepõem as variáveis para server.run_http
def test_d011_cli_serve_repassa_host_e_port_sobrepondo_variaveis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RSL_HTTP_HOST", "0.0.0.0")
    monkeypatch.setenv("RSL_HTTP_PORT", "8000")
    recebido: list[tuple[str | None, int | None]] = []
    monkeypatch.setattr(
        server,
        "run_http",
        lambda *, host=None, port=None: recebido.append((host, port)),
        raising=False,
    )

    cli.main(["serve", "--host", "localhost", "--port", "8765"])

    assert recebido == [("localhost", 8765)]


# D-011, NFR-03: HttpConfig não expõe valores secretos no repr, str, vars ou asdict nem em erros
def test_d011_nfr03_http_config_nao_expoe_segredos_no_repr_nem_em_erros(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_oa_key = "fake-key-123"
    fake_s2_key = "fake-key-456"
    fake_email = "pesquisador@exemplo.org"
    monkeypatch.setenv("OPENALEX_API_KEY", fake_oa_key)
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", fake_s2_key)
    monkeypatch.setenv("RSL_CONTACT_EMAIL", fake_email)

    http_cfg = config.load_http()
    textos = [repr(http_cfg), str(http_cfg), str(vars(http_cfg)), str(asdict(http_cfg))]
    for segredo in (fake_oa_key, fake_s2_key, fake_email):
        for texto in textos:
            assert segredo not in texto

    monkeypatch.setenv("RSL_HTTP_PORT", "invalido-fake-key-123")
    with pytest.raises(ValueError, match="RSL_HTTP_PORT") as exc_port:
        config.load_http()
    assert "fake-key-123" not in str(exc_port.value)

    monkeypatch.setenv("RSL_HTTP_PORT", "8000")
    monkeypatch.setenv("RSL_PUBLIC_URL", "ftp://invalido-fake-key-123")
    with pytest.raises(ValueError, match="RSL_PUBLIC_URL") as exc_url:
        config.load_http()
    assert "fake-key-123" not in str(exc_url.value)
