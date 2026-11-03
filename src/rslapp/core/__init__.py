"""Miolo (core) do RSL.app: modelos e erros independentes do protocolo MCP."""

from __future__ import annotations

from rslapp.core.errors import ERROR_CODES, ErrorCode, RSLError
from rslapp.core.models import Affiliation, Author, SourceResult, Work

__all__ = [
    "ERROR_CODES",
    "Affiliation",
    "Author",
    "ErrorCode",
    "RSLError",
    "SourceResult",
    "Work",
]
