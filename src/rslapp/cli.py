"""Interface de linha de comando do RSL.app (modo stdio padrão e subcomando serve)."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from rslapp import config, people, server


# D-011, D-016: Monta o parser de linha de comando em português com serve e token
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

    # D-016: Subcomando token (add, list, revoke)
    token_parser = subparsers.add_parser(
        "token",
        help="Gerencia pessoas e códigos pessoais de acesso (add, list, revoke)",
        description="Gerencia o cadastro de pessoas e seus códigos pessoais de acesso.",
    )
    token_sub = token_parser.add_subparsers(
        dest="token_command",
        title="ações de token",
        metavar="<ação>",
        required=True,
    )

    token_add = token_sub.add_parser(
        "add",
        help="Cadastra uma pessoa e exibe o código pessoal uma única vez",
    )
    token_add.add_argument("id", type=str, help="Identificador da pessoa (1..40 caracteres)")
    token_add.add_argument(
        "--replace",
        action="store_true",
        help="Gera um código novo para pessoa existente ou revogada e a reativa",
    )

    token_sub.add_parser(
        "list",
        help="Lista as pessoas cadastradas sem exibir código nem hash",
    )

    token_revoke = token_sub.add_parser(
        "revoke",
        help="Marca uma pessoa como revogada sem apagar seus dados",
    )
    token_revoke.add_argument("id", type=str, help="Identificador da pessoa a revogar")

    # D-016: Subcomando user (purge)
    user_parser = subparsers.add_parser(
        "user",
        help="Gerencia os dados das pessoas cadastradas (purge)",
        description="Gerencia os dados salvos das pessoas no servidor.",
    )
    user_sub = user_parser.add_subparsers(
        dest="user_command",
        title="ações de usuário",
        metavar="<ação>",
        required=True,
    )
    user_purge = user_sub.add_parser(
        "purge",
        help="Apaga a pessoa do cadastro e a pasta de dados dela",
    )
    user_purge.add_argument("id", type=str, help="Identificador da pessoa a apagar")
    user_purge.add_argument(
        "--yes",
        action="store_true",
        help="Pula a confirmação interativa e apaga imediatamente",
    )

    return parser


def _run_token_command(args: argparse.Namespace) -> None:
    try:
        if args.token_command == "add":
            code = people.replace_code(args.id) if args.replace else people.add(args.id)
            print(f"Pessoa: {args.id}")
            print(f"Código pessoal: {code}")
            print("Guarde este código agora: ele é mostrado uma vez só e não aparece de novo.")
            return
        if args.token_command == "list":
            for person in people.list_people():
                print(
                    f"{person.id}\t{person.created_at}\t"
                    f"{person.code_created_at}\t{person.status}"
                )
            return
        if args.token_command == "revoke":
            person = people.revoke(args.id)
            print(f"Pessoa '{person.id}' marcada como {person.status}.")
            return
    except ValueError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        raise SystemExit(1) from None


def _run_user_command(args: argparse.Namespace) -> None:
    try:
        people.validate_person_id(args.id)
        if not args.yes:
            try:
                confirmed = input(f"Digite '{args.id}' para confirmar a exclusão: ")
            except EOFError:
                confirmed = ""
            if confirmed.strip() != args.id:
                print(
                    "Operação cancelada: confirmação não confere. Nada foi apagado.",
                    file=sys.stderr,
                )
                raise SystemExit(1)
        people.purge(args.id)
        print(f"Pessoa '{args.id}' e sua pasta de dados foram apagadas.")
    except ValueError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        raise SystemExit(1) from None


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

    if args.command == "token":
        _run_token_command(args)
        return

    if args.command == "user":
        _run_user_command(args)
        return

    server.main()


if __name__ == "__main__":
    main()
