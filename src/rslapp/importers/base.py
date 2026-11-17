"""Base e utilitários para importadores de arquivos bibliográficos (FR-23, D-033)."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from rslapp.core.models import Author, Work

# Expressão regular para limpeza de prefixos comuns de DOI
_DOI_PREFIX_RE = re.compile(
    r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)",
    re.IGNORECASE,
)

# Expressão regular para captura de anos (1800 a 2099)
_YEAR_RE = re.compile(r"\b(1[89]\d\d|20\d\d)\b")


# FR-23, D-033: Limpa e normaliza strings de DOI
def clean_doi(raw: Any) -> str | None:
    """Extrai e normaliza um identificador DOI limpo, sem prefixo URL."""
    if not isinstance(raw, str):
        return None
    val = raw.strip()
    if not val:
        return None
    val = _DOI_PREFIX_RE.sub("", val).strip()
    return val if val else None


# FR-23, D-033: Extrai ano de publicação inteiro
def extract_year(raw: Any) -> int | None:
    """Extrai um ano de publicação inteiro a partir de texto ou número."""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        y = int(raw)
        return y if 1800 <= y <= 2099 else None
    if isinstance(raw, str):
        match = _YEAR_RE.search(raw)
        if match:
            return int(match.group(1))
    return None


# FR-23, D-033: Normaliza nomes de autores individuais
def parse_author_name(raw_name: str) -> Author:
    """Normaliza o nome do autor, convertendo 'Sobrenome, Nome' quando apropriado."""
    text = " ".join(raw_name.strip().split())
    if not text:
        return Author(name="")

    # Se estiver no formato 'Sobrenome, Nome', converte para 'Nome Sobrenome'
    if "," in text:
        parts = [p.strip() for p in text.split(",", 1)]
        if len(parts) == 2 and parts[0] and parts[1]:
            formatted_name = f"{parts[1]} {parts[0]}"
            return Author(name=formatted_name)

    return Author(name=text)


# FR-23, D-033: Limpa markup LaTeX comum de títulos e resumos BibTeX
def clean_latex(text: str) -> str:
    """Remove chaves e caracteres de escape comuns do formato LaTeX/BibTeX."""
    if not text:
        return ""
    # Remove chaves internas simples: {Exemplo} -> Exemplo
    cleaned = re.sub(r"\{([^{}]*)\}", r"\1", text)
    # Remove barras invertidas de escapes comuns: \_ -> _, \% -> %
    cleaned = re.sub(r"\\([_%&#$])", r"\1", cleaned)
    return " ".join(cleaned.split())


# FR-23, D-033: Classe base abstrata para importadores de formatos
class BaseImporter(ABC):
    """Contrato abstrato de importação de listas bibliográficas."""

    format_id: str

    @abstractmethod
    def parse(self, content: str) -> list[Work]:
        """Processa o conteúdo textual e retorna uma lista de instâncias Work."""
        raise NotImplementedError
