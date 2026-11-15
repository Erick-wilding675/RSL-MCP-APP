"""Teste de fumaça do modo --mcp para os executáveis gerados no workflow (D-028, FR-19)."""

from __future__ import annotations

import contextlib
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
from collections.abc import Sequence
from pathlib import Path

SMOKE_TIMEOUT_SECONDS = 30.0


# D-028, FR-19: Inicia o executável com --mcp via Popen e pipes e valida o handshake JSON-RPC initialize em até 30 s
def run_smoke_test(
    command: Sequence[str],
    *,
    timeout: float = SMOKE_TIMEOUT_SECONDS,
) -> int:
    """Executa o comando MCP via stdio, envia initialize e confere result.serverInfo."""
    if not command:
        print("Uso: python packaging/smoke_mcp.py <executavel> [args...]", file=sys.stderr)
        return 2

    exe_candidate = Path(command[0])
    resolved_exe = (
        str(exe_candidate)
        if exe_candidate.exists()
        else (shutil.which(command[0]) or command[0])
    )
    full_command = [resolved_exe, *command[1:]]

    with tempfile.TemporaryDirectory(prefix="rslapp-smoke-") as tmp_dir:
        env = os.environ.copy()
        env["RSL_DATA_DIR"] = os.path.join(tmp_dir, "data")
        env["RSL_DESKTOP_CONFIG"] = os.path.join(tmp_dir, "desktop.json")

        try:
            proc = subprocess.Popen(
                full_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,
                env=env,
            )
        except OSError as exc:
            print(f"Erro ao iniciar {full_command!r}: {exc}", file=sys.stderr)
            return 1

        line_queue: queue.Queue[str | Exception] = queue.Queue()

        def _stdout_reader() -> None:
            assert proc.stdout is not None
            try:
                for raw_line in proc.stdout:
                    line_queue.put(raw_line)
                line_queue.put("")
            except (OSError, ValueError) as exc:  # pragma: no cover
                line_queue.put(exc)

        reader_thread = threading.Thread(target=_stdout_reader, daemon=True)
        reader_thread.start()

        try:
            assert proc.stdin is not None
            init_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "rslapp-smoke", "version": "1.0.0"},
                },
            }
            proc.stdin.write(json.dumps(init_msg) + "\n")
            proc.stdin.flush()

            try:
                first_item = line_queue.get(timeout=timeout)
            except queue.Empty:
                print(
                    f"Erro: sem resposta JSON-RPC ao initialize em {timeout:.0f} s para {list(command)!r}.",
                    file=sys.stderr,
                )
                return 1

            if isinstance(first_item, Exception):
                print(f"Erro ao ler stdout do processo MCP: {first_item}", file=sys.stderr)
                return 1

            if not first_item:
                rc = proc.poll()
                err_out = proc.stderr.read() if proc.stderr is not None else ""
                print(
                    f"Erro: processo MCP encerrou sem responder no stdout (returncode={rc}).\n{err_out}",
                    file=sys.stderr,
                )
                return 1

            try:
                payload = json.loads(first_item)
            except json.JSONDecodeError as exc:
                print(
                    f"Erro: saída no stdout não é JSON-RPC válido: {first_item!r} ({exc})",
                    file=sys.stderr,
                )
                return 1

            if not isinstance(payload, dict):
                print(f"Erro: resposta JSON-RPC não é objeto: {payload!r}", file=sys.stderr)
                return 1

            result = payload.get("result")
            server_info = result.get("serverInfo") if isinstance(result, dict) else None
            if (
                payload.get("jsonrpc") != "2.0"
                or payload.get("id") != 1
                or not isinstance(server_info, dict)
                or not server_info.get("name")
            ):
                print(
                    f"Erro: resposta sem result.serverInfo válido: {payload!r}",
                    file=sys.stderr,
                )
                return 1

            return 0
        finally:
            if proc.stdin is not None:
                with contextlib.suppress(OSError, ValueError):
                    proc.stdin.close()
            try:
                proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                with contextlib.suppress(subprocess.TimeoutExpired):
                    proc.wait(timeout=5.0)
            if proc.stdout is not None:
                with contextlib.suppress(OSError, ValueError):
                    proc.stdout.close()
            if proc.stderr is not None:
                with contextlib.suppress(OSError, ValueError):
                    proc.stderr.close()


def main(argv: Sequence[str] | None = None) -> int:
    """Interpreta o caminho do executável e argumentos opcionais (padrão: --mcp)."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("Uso: python packaging/smoke_mcp.py <executavel> [args...]", file=sys.stderr)
        return 2
    executable = args[0]
    extra_args = args[1:] if len(args) > 1 else ["--mcp"]
    return run_smoke_test([executable, *extra_args])


if __name__ == "__main__":
    raise SystemExit(main())
