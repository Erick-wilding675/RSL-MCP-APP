"""Interface de linha de comando do RSL.app (modo stdio padrão e subcomando serve)."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from rslapp import config, server


# D-011: Monta o parser de linha de comando em português com o subcomando serve
def build_parser() -> argparse.ArgumentParser:
    """Cria o parser de argumentos do comando rslapp em português."""
    parser = argparse.ArgumentParser(
        prog="rslapp",
        description=(
            "Servidor MCP do RSL.app para busca acadêmica e revisão sistemática. "
            "Sem subcomando, inicia o servidor por stdio."
        ),
    )
    subparsers = parser.add_subparsers(
        dest="command",
        title="comandos disponíveis",
        metavar="<comando>",
        help="Subcomando a executar (sem argumento, inicia o servidor MCP por stdio)",
    )

    serve_parser = subparsers.add_parser(
        "serve",
        help="Inicia o servidor MCP em modo HTTP (streamable HTTP)",
        description="Inicia o servidor MCP do RSL.app em modo HTTP (/mcp e /health).",
    )
    serve_parser.add_argument(
        "--host",
        type=str,
        default=None,
        metavar="HOST",
        help="Endereço em que o servidor HTTP escuta (sobrepõe RSL_HTTP_HOST; padrão: 127.0.0.1)",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=None,
        metavar="PORTA",
        help="Porta em que o servidor HTTP escuta (sobrepõe RSL_HTTP_PORT; padrão: 8000)",
    )
    return parser


# D-008, D-011: Ponto de entrada principal do comando rslapp (stdio sem argumentos; HTTP em serve)
def main(argv: Sequence[str] | None = None) -> None:
    """Executa o comando rslapp conforme os argumentos recebidos."""
    args_list = list(sys.argv[1:] if argv is None else argv)
    if not args_list:
        server.main()
        return

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure) and not stream.isatty():
            reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(args_list)

    if args.command == "serve":
        try:
            http_cfg = config.load_http(host=args.host, port=args.port)
            if not config.is_loopback_host(http_cfg.host):
                raise ValueError(
                    "O modo HTTP sem login só pode escutar em endereço de loopback "
                    f"(127.0.0.1, localhost ou ::1); recebido {http_cfg.host!r}."
                )
        except ValueError as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            raise SystemExit(1) from None

        server.run_http(host=http_cfg.host, port=http_cfg.port)
        return

    server.main()


if __name__ == "__main__":
    main()
