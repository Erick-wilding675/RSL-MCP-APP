"""Detector automático de formatos de arquivos bibliográficos (FR-23, D-033)."""

from __future__ import annotations

import re

from rslapp.core.errors import RSLError

_BIBTEX_DETECT_RE = re.compile(r"@\w+\s*\{", re.IGNORECASE)
_RIS_DETECT_RE = re.compile(r"^TY\s+-\s+", re.MULTILINE | re.IGNORECASE)
_WOS_TAGGED_RE = re.compile(r"^PT\s+[A-Z]", re.MULTILINE)


# FR-23, D-033: Detecta automaticamente o formato bibliográfico do conteúdo
def auto_detect_format(content: str) -> str:
    """Analisa o conteúdo textual e identifica o formato bibliográfico correspondente.

    Returns:
        Um dos formatos: 'ris', 'bibtex', 'scopus_csv', 'wos'.

    Raises:
        RSLError('invalid_input'): Quando o formato não puder ser identificado.
    """
    if not isinstance(content, str) or not content.strip():
        raise RSLError("invalid_input", "Conteúdo vazio ou inválido para importação")

    clean = content.lstrip("\ufeff").strip()
    first_lines = "\n".join(clean.splitlines()[:50])

    # 1. RIS: Presença de TY  -
    if _RIS_DETECT_RE.search(first_lines):
        return "ris"

    # 2. BibTeX: Presença de @article{, @book{, etc.
    if _BIBTEX_DETECT_RE.search(first_lines):
        return "bibtex"

    # 3. Web of Science Plain Text Tagged: Inicia com PT seguido de tags WoS
    if _WOS_TAGGED_RE.search(first_lines) or ("\nER\n" in clean and "UT WOS:" in clean):
        return "wos"

    # 4. Web of Science TSV: Cabeçalho com tabulações contendo PT, AU, TI, SO
    first_line = clean.splitlines()[0] if clean.splitlines() else ""
    if "\t" in first_line:
        upper_header = first_line.upper()
        if "PT\t" in upper_header or "\tUT" in upper_header or "\tTI\t" in upper_header:
            return "wos"

    # 5. Scopus CSV: Cabeçalho com colunas típicas do Scopus
    lower_header = first_line.lower()
    if ("," in first_line or ";" in first_line) and "authors" in lower_header and (
        "source title" in lower_header or "doi" in lower_header or "eid" in lower_header or "title" in lower_header
    ):
        return "scopus_csv"

    # Fallback: Se tiver cabeçalho CSV padrão com Title e DOI
    if ("title" in lower_header and "doi" in lower_header) and ("," in first_line or ";" in first_line):
        return "scopus_csv"

    raise RSLError(
        "invalid_input",
        "Formato de arquivo bibliográfico não reconhecido. Formatos suportados: RIS, BibTeX, Scopus CSV e Web of Science.",
    )
