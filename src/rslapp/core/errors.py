"""Erros do miolo do RSL.app segundo o contrato de interface."""

from __future__ import annotations

from typing import Literal, get_args

# FR-06, D-002: Códigos de erro do contrato de interface (incluindo empty_list para lista sem artigos)
ErrorCode = Literal[
    "no_source_available",
    "invalid_input",
    "list_not_found",
    "search_not_found",
    "work_not_found",
    "format_not_available",
    "export_folder_not_writable",
    "empty_list",
]

ERROR_CODES: frozenset[str] = frozenset(get_args(ErrorCode))


# D-002: Códigos de erro estáveis do contrato, sem dependência do protocolo MCP no miolo
class RSLError(Exception):
    """Exceção de domínio do miolo que o servidor MCP converte na borda."""

    def __init__(self, code: ErrorCode | str, message: str) -> None:
        if code not in ERROR_CODES:
            raise ValueError(f"Código de erro fora do contrato: {code!r}")
        self.code: str = code
        self.message: str = message
        super().__init__(f"{code}: {message}")
