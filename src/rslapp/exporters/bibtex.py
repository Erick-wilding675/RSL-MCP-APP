"""Exportador de listas para o formato BibTeX padrão (FR-06, D-014)."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Any

from rslapp.core.models import Work
from rslapp.exporters.base import Exporter

_ARTICLE_TYPES: frozenset[str] = frozenset(
    {"article", "journal-article", "journal article", "journal_article", "review"}
)

_LATEX_ESCAPES: dict[str, str] = {
    "\\": r"\textbackslash{}",
    "{": r"\textbraceleft{}",
    "}": r"\textbraceright{}",
    "%": r"\%",
    "&": r"\&",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "^": r"\textasciicircum{}",
    "~": r"\textasciitilde{}",
}

_STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "o", "os", "as", "um", "uma", "uns", "umas",
    "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
    "on", "in", "of", "for", "to", "at", "by", "with", "from",
})

_NAME_SUFFIXES: frozenset[str] = frozenset({
    "jr", "junior", "júnior", "filho", "neto", "sobrinho", "ii", "iii",
})

_ORG_TERMS: frozenset[str] = frozenset({
    "university", "universidade", "institute", "instituto", "consortium",
    "consórcio", "consorcio", "collaboration", "colaboração", "colaboracao",
    "organization", "organisation", "organização", "organizacao",
    "ministry", "ministério", "ministerio",
})


# FR-06: Escapa caracteres reservados do LaTeX com chaves balanceadas
def escape_latex(text: str) -> str:
    """Escapa caracteres reservados do LaTeX e converte quebras de linha em espaço."""
    if not text:
        return ""
    clean = " ".join(text.split())
    return "".join(_LATEX_ESCAPES.get(ch, ch) for ch in clean)


# FR-06: Converte texto para caracteres alfanuméricos ASCII minúsculos
def _to_ascii_alphanumeric(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", ascii_text.lower())


# FR-06: Extrai a primeira palavra significativa de um texto para chave
def _first_significant_word(text: str | None, default: str) -> str:
    if not text or not isinstance(text, str):
        return default
    words = text.strip().split()
    for w in words:
        clean = _to_ascii_alphanumeric(w)
        if clean and clean not in _STOP_WORDS:
            return clean
    for w in words:
        clean = _to_ascii_alphanumeric(w)
        if clean:
            return clean
    return default


def _extract_title_key_word(title: str | None) -> str:
    return _first_significant_word(title, "untitled")


# FR-06: Formata o ano ou None se inválido
def _format_year(year: Any) -> str | None:
    if year is not None and not isinstance(year, bool):
        try:
            y = int(year)
            if y > 0:
                return str(y)
        except (ValueError, TypeError):
            pass
    return None


def _extract_year_key(year: Any) -> str:
    return _format_year(year) or "nd"


def _is_suffix(word: str) -> bool:
    return word.rstrip(".").lower() in _NAME_SUFFIXES


# FR-06: Identifica se um nome representa uma organização/instituição
def _is_organization_name(name: str) -> bool:
    if name.startswith("{") and name.endswith("}"):
        return True
    words = re.findall(r"\b\w+\b", name.lower())
    if len(words) < 2:
        return False
    if any(w in _ORG_TERMS for w in words):
        return True
    return words[-1] in ("group", "grupo")


# FR-06: Extrai a palavra principal do sobrenome desconsiderando sufixos (Jr., Filho, etc.)
def _extract_surname_key_word(clean_name: str) -> str:
    if "," in clean_name:
        words = clean_name.split(",", 1)[0].strip().split()
    else:
        words = clean_name.split()
    if len(words) >= 2 and _is_suffix(words[-1]):
        return words[-2]
    return words[-1] if words else ""


# FR-06: Extrai chave de citação do primeiro autor (sobrenome, org ou anon)
def _extract_author_key(first_author: dict[str, Any] | None) -> str:
    if not isinstance(first_author, dict):
        return "anon"
    raw_name = first_author.get("name")
    if not raw_name or not isinstance(raw_name, str):
        return "anon"
    clean = " ".join(raw_name.split())
    if not clean:
        return "anon"
    if _is_organization_name(clean):
        if clean.startswith("{") and clean.endswith("}"):
            clean = clean[1:-1].strip()
        return _first_significant_word(clean, "anon")
    key_word = _extract_surname_key_word(clean)
    return _to_ascii_alphanumeric(key_word) or "anon"


# FR-06: Formata um autor individual como 'Sobrenome, Nome' ou organização como '{Nome}'
def _format_author_for_bibtex(author: dict[str, Any]) -> str | None:
    if not isinstance(author, dict):
        return None
    raw_name = author.get("name")
    if not raw_name or not isinstance(raw_name, str):
        return None
    clean = " ".join(raw_name.split())
    if not clean:
        return None
    if _is_organization_name(clean):
        if clean.startswith("{") and clean.endswith("}"):
            clean = clean[1:-1].strip()
        return f"{{{escape_latex(clean)}}}"
    if "," in clean:
        parts = clean.split(",", 1)
        surname, given = parts[0].strip(), parts[1].strip()
        return f"{escape_latex(surname)}, {escape_latex(given)}" if given else escape_latex(surname)
    words = clean.split()
    if len(words) == 1:
        return escape_latex(words[0])
    if len(words) >= 3 and _is_suffix(words[-1]):
        surname, given = f"{words[-2]} {words[-1]}", " ".join(words[:-2])
    else:
        surname, given = words[-1], " ".join(words[:-1])
    return f"{escape_latex(surname)}, {escape_latex(given)}"


# FR-06: Limpa prefixos de URL de DOI mantendo apenas o identificador puro
def _clean_doi(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    val = raw.strip()
    lower = val.lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/"):
        if lower.startswith(prefix):
            val = val[len(prefix) :].strip()
            break
    return val if val else None


# FR-06: Sufixo alfabético de desambiguação (0 -> a, 1 -> b, ..., 25 -> z, 26 -> aa)
def _disambiguation_suffix(index: int) -> str:
    result = ""
    curr = index
    while True:
        result = chr(ord("a") + (curr % 26)) + result
        curr = curr // 26 - 1
        if curr < 0:
            break
    return result


# FR-06: Gera chaves de citação únicas com sufixos a, b, c... evitando colisões com outras chaves base
def _generate_citation_keys(works: list[dict[str, Any]]) -> list[str]:
    base_keys = [
        f"{_extract_author_key((w.get('authors') or [None])[0])}{_extract_year_key(w.get('year'))}{_extract_title_key_word(w.get('title'))}"
        for w in works
    ]
    counts = Counter(base_keys)
    base_key_set = set(base_keys)
    used_keys: set[str] = set()
    suffix_indices: dict[str, int] = {}
    final_keys: list[str] = []

    for bk in base_keys:
        if counts[bk] == 1 and bk not in used_keys:
            candidate = bk
        else:
            idx = suffix_indices.get(bk, 0)
            while True:
                candidate = f"{bk}{_disambiguation_suffix(idx)}"
                idx += 1
                if candidate not in used_keys and candidate not in base_key_set:
                    break
            suffix_indices[bk] = idx
        final_keys.append(candidate)
        used_keys.add(candidate)

    return final_keys


# FR-06: Extrai os nomes das fontes onde o trabalho foi encontrado
def _extract_source_names(work_dict: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for key in ("source_ids", "citations"):
        raw = work_dict.get(key)
        if isinstance(raw, dict):
            names.extend(k.strip() for k in raw if isinstance(k, str) and k.strip() and k.strip() not in names)
    raw_sources = work_dict.get("sources")
    if isinstance(raw_sources, list):
        names.extend(s.strip() for s in raw_sources if isinstance(s, str) and s.strip() and s.strip() not in names)
    return names


# FR-06: Define se o tipo é @article ou @misc
def _get_bibtex_entry_type(work_dict: dict[str, Any]) -> str:
    venue = work_dict.get("venue")
    has_venue = isinstance(venue, str) and bool(venue.strip())
    raw_type = work_dict.get("type")
    is_article = isinstance(raw_type, str) and raw_type.strip().lower() in _ARTICLE_TYPES
    return "article" if (has_venue and is_article) else "misc"


# FR-06, D-014: Exportador de listas no formato BibTeX (.bib)
class BibTeXExporter(Exporter):
    """Renderizador no formato BibTeX padrão (UTF-8, fim de linha \\n)."""

    format: str = "bibtex"
    extension: str = "bib"

    # FR-06, D-014: Renderiza a lista no formato BibTeX (.bib)
    def render(self, list_data: dict[str, Any]) -> str:
        """Renderiza a lista no formato BibTeX com entradas @article ou @misc."""
        if not isinstance(list_data, dict):
            raise TypeError("list_data deve ser um dicionário")

        raw_works = list_data.get("works") or []
        works: list[dict[str, Any]] = [
            item.to_dict() if isinstance(item, Work) else item
            for item in raw_works
            if isinstance(item, (Work, dict))
        ]

        if not works:
            return ""

        citation_keys = _generate_citation_keys(works)
        entries: list[str] = []

        for w, cite_key in zip(works, citation_keys):
            entry_type = _get_bibtex_entry_type(w)
            fields: list[tuple[str, str]] = []

            title = w.get("title")
            if title and isinstance(title, str) and title.strip():
                fields.append(("title", f"{{{escape_latex(title)}}}"))

            authors = [_format_author_for_bibtex(a) for a in (w.get("authors") or [])]
            author_str = " and ".join(a for a in authors if a)
            if author_str:
                fields.append(("author", author_str))

            year = _format_year(w.get("year"))
            if year:
                fields.append(("year", year))

            venue = w.get("venue")
            if venue and isinstance(venue, str) and venue.strip():
                field_name = "journal" if entry_type == "article" else "howpublished"
                fields.append((field_name, escape_latex(venue)))

            clean_doi = _clean_doi(w.get("doi"))
            if clean_doi:
                fields.append(("doi", escape_latex(clean_doi)))
                fields.append(("url", escape_latex(f"https://doi.org/{clean_doi}")))

            abstract = w.get("abstract")
            if abstract and isinstance(abstract, str) and abstract.strip():
                fields.append(("abstract", escape_latex(abstract)))

            raw_kws = w.get("keywords") or []
            clean_kws = [escape_latex(k) for k in raw_kws if k and isinstance(k, str) and k.strip()]
            if clean_kws:
                fields.append(("keywords", ", ".join(clean_kws)))

            source_names = _extract_source_names(w)
            if source_names:
                fields.append(("note", escape_latex(f"Fontes: {', '.join(source_names)}")))

            body = "\n".join(f"  {k} = {{{v}}}," for k, v in fields)
            entries.append(f"@{entry_type}{{{cite_key},\n{body}\n}}")

        return "\n\n".join(entries) + "\n"
