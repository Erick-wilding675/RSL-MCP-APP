"""Exportador de listas para o formato BibTeX padrão (FR-06, D-014)."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Any

from rslapp.core.models import Author, Work
from rslapp.exporters.base import Exporter

_ARTICLE_TYPES: frozenset[str] = frozenset(
    {"article", "journal-article", "journal article", "journal_article", "review"}
)

_LATEX_ESCAPES: dict[str, str] = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "%": r"\%",
    "&": r"\&",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "^": r"\textasciicircum{}",
    "~": r"\textasciitilde{}",
}

_STOP_WORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "o",
        "os",
        "as",
        "um",
        "uma",
        "uns",
        "umas",
        "de",
        "do",
        "da",
        "dos",
        "das",
        "em",
        "no",
        "na",
        "nos",
        "nas",
        "on",
        "in",
        "of",
        "for",
        "to",
        "at",
        "by",
        "with",
        "from",
    }
)

_ORG_KEYWORDS: frozenset[str] = frozenset(
    {
        "organization",
        "organisation",
        "organização",
        "organizacao",
        "institution",
        "instituto",
        "institute",
        "instituição",
        "instituicao",
        "association",
        "associação",
        "associacao",
        "committee",
        "comitê",
        "comite",
        "commission",
        "comissão",
        "comissao",
        "consortium",
        "consórcio",
        "consorcio",
        "group",
        "grupo",
        "team",
        "equipe",
        "ministry",
        "ministério",
        "ministerio",
        "department",
        "departamento",
        "foundation",
        "fundação",
        "fundacao",
        "corporation",
        "empresa",
        "company",
        "university",
        "universidade",
        "universidad",
        "faculdade",
        "college",
        "center",
        "centre",
        "centro",
        "collaboration",
        "colaboração",
        "colaboracao",
        "taskforce",
        "agency",
        "agência",
        "agencia",
        "council",
        "conselho",
        "society",
        "sociedade",
        "hospital",
        "bank",
        "banco",
        "laboratory",
        "laboratório",
        "laboratorio",
        "network",
        "rede",
        "who",
        "unesco",
        "unicef",
        "cdc",
        "nih",
        "nasa",
        "ieee",
        "acm",
        "w3c",
        "iso",
        "fao",
        "fda",
        "oecd",
    }
)


# FR-06: Escapa caracteres especiais do LaTeX (\ { } % & $ # _ ^ ~), mantém acentos UTF-8 e troca quebras de linha por espaço
def escape_latex(text: str) -> str:
    """Escapa caracteres reservados do LaTeX e converte quebras de linha em espaço."""
    if not text:
        return ""
    clean = " ".join(text.split())
    return "".join(_LATEX_ESCAPES.get(ch, ch) for ch in clean)


# FR-06: Converte texto para caracteres alfanuméricos ASCII minúsculos
def _to_ascii_alphanumeric(text: str) -> str:
    """Remove acentos e pontuação, devolvendo apenas letras e dígitos ASCII minúsculos."""
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", ascii_text.lower())


# FR-06: Limpa prefixos de URL de DOI mantendo apenas o identificador puro
def _clean_doi(raw: Any) -> str | None:
    """Remove prefixos comuns como https://doi.org/ do DOI."""
    if not isinstance(raw, str):
        return None
    val = raw.strip()
    lower = val.lower()
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
    ):
        if lower.startswith(prefix):
            val = val[len(prefix) :].strip()
            break
    return val if val else None


# FR-06: Identifica se um autor é pessoa jurídica / organização
def _is_organization_author(author: Any, name: str) -> bool:
    """Verifica se o autor representa uma instituição ou grupo."""
    if isinstance(author, dict) and bool(
        author.get("is_organization")
        or author.get("type") in ("organization", "corporate", "collective")
        or author.get("corporate")
        or author.get("collective_name")
    ):
        return True
    if hasattr(author, "is_organization") and bool(author.is_organization):
        return True
    if name.startswith("{") and name.endswith("}"):
        return True
    lower_name = name.lower()
    words = re.findall(r"\b\w+\b", lower_name)
    return any(w in _ORG_KEYWORDS for w in words)


# FR-06: Formata um autor individual como 'Sobrenome, Nome' ou organização como '{Nome}'
def _format_author_for_bibtex(author: Any) -> str | None:
    """Renderiza um autor com Sobrenome, Nome ou {Organização} protegida por chaves."""
    raw_name: str | None = None
    if isinstance(author, Author):
        raw_name = author.name
    elif isinstance(author, dict):
        raw_name = author.get("name")
    elif isinstance(author, str):
        raw_name = author

    if not raw_name or not isinstance(raw_name, str):
        return None
    clean_raw = " ".join(raw_name.split())
    if not clean_raw:
        return None

    if _is_organization_author(author, clean_raw):
        if clean_raw.startswith("{") and clean_raw.endswith("}"):
            clean_raw = clean_raw[1:-1].strip()
        escaped_org = escape_latex(clean_raw)
        return f"{{{escaped_org}}}"

    # Pessoa física
    if "," in clean_raw:
        parts = clean_raw.split(",", 1)
        surname = parts[0].strip()
        given = parts[1].strip()
        clean_surname = escape_latex(surname)
        clean_given = escape_latex(given)
        return f"{clean_surname}, {clean_given}" if clean_given else clean_surname

    words = clean_raw.split()
    if len(words) == 1:
        return escape_latex(words[0])

    surname = words[-1]
    given = " ".join(words[:-1])
    clean_surname = escape_latex(surname)
    clean_given = escape_latex(given)
    return f"{clean_surname}, {clean_given}"


# FR-06: Extrai a primeira palavra significativa do título
def _extract_title_key_word(title: str | None) -> str:
    """Obtém a primeira palavra não-trivial do título em ASCII alfanumérico minúsculo."""
    if not title or not isinstance(title, str) or not title.strip():
        return "untitled"
    words = title.strip().split()
    for w in words:
        clean = _to_ascii_alphanumeric(w)
        if clean and clean not in _STOP_WORDS:
            return clean
    for w in words:
        clean = _to_ascii_alphanumeric(w)
        if clean:
            return clean
    return "untitled"


# FR-06: Extrai o sobrenome do primeiro autor para a chave de citação
def _extract_author_key(authors: list[Any] | None) -> str:
    """Extrai o identificador de autor para a chave de citação (sobrenome ou anon)."""
    if not authors:
        return "anon"
    first = authors[0]
    raw_name: str | None = None
    if isinstance(first, Author):
        raw_name = first.name
    elif isinstance(first, dict):
        raw_name = first.get("name")
    elif isinstance(first, str):
        raw_name = first

    if not raw_name or not isinstance(raw_name, str) or not raw_name.strip():
        return "anon"

    clean_raw = " ".join(raw_name.split())
    if _is_organization_author(first, clean_raw):
        if clean_raw.startswith("{") and clean_raw.endswith("}"):
            clean_raw = clean_raw[1:-1].strip()
        words = clean_raw.split()
        for w in words:
            clean = _to_ascii_alphanumeric(w)
            if clean and clean not in _STOP_WORDS:
                return clean
        for w in words:
            clean = _to_ascii_alphanumeric(w)
            if clean:
                return clean
        return "anon"

    if "," in clean_raw:
        surname = clean_raw.split(",", 1)[0].strip()
    else:
        words = clean_raw.split()
        surname = words[-1] if words else ""

    clean = _to_ascii_alphanumeric(surname)
    return clean or "anon"


# FR-06: Extrai o ano em 4 dígitos ou 'nd' para a chave de citação
def _extract_year_key(year: Any) -> str:
    """Obtém o ano em formato de texto para a chave ou 'nd' se ausente."""
    if year is not None and not isinstance(year, bool):
        try:
            y = int(year)
            if y > 0:
                return str(y)
        except (ValueError, TypeError):
            pass
    return "nd"


# FR-06: Sufixo alfabético de desambiguação (0 -> a, 1 -> b, ..., 25 -> z, 26 -> aa)
def _disambiguation_suffix(index: int) -> str:
    """Gera sequência alfabética a, b, c... para chaves repetidas."""
    result = ""
    curr = index
    while True:
        result = chr(ord("a") + (curr % 26)) + result
        curr = curr // 26 - 1
        if curr < 0:
            break
    return result


# FR-06: Gera chaves de citação para todos os trabalhos da lista com resolução de duplicatas
def _generate_citation_keys(works: list[dict[str, Any]]) -> list[str]:
    """Cria chaves de citação únicas com sufixos a, b, c... em caso de colisão."""
    base_keys: list[str] = []
    for w in works:
        author_key = _extract_author_key(w.get("authors"))
        year_key = _extract_year_key(w.get("year"))
        title_key = _extract_title_key_word(w.get("title"))
        base_keys.append(f"{author_key}{year_key}{title_key}")

    counts = Counter(base_keys)
    seen: dict[str, int] = {}
    final_keys: list[str] = []

    for bk in base_keys:
        if counts[bk] > 1:
            idx = seen.get(bk, 0)
            seen[bk] = idx + 1
            suffix = _disambiguation_suffix(idx)
            final_keys.append(f"{bk}{suffix}")
        else:
            final_keys.append(bk)

    return final_keys


# FR-06: Extrai os nomes das fontes onde o trabalho foi encontrado
def _extract_source_names(work_dict: dict[str, Any]) -> list[str]:
    """Reúne as fontes do artigo a partir de source_ids, sources e citations."""
    names: list[str] = []
    raw_source_ids = work_dict.get("source_ids")
    if isinstance(raw_source_ids, dict):
        for k in raw_source_ids:
            if isinstance(k, str) and k.strip() and k.strip() not in names:
                names.append(k.strip())
    raw_sources = work_dict.get("sources")
    if isinstance(raw_sources, list):
        for s in raw_sources:
            if isinstance(s, str) and s.strip() and s.strip() not in names:
                names.append(s.strip())
    raw_citations = work_dict.get("citations")
    if isinstance(raw_citations, dict):
        for c in raw_citations:
            if isinstance(c, str) and c.strip() and c.strip() not in names:
                names.append(c.strip())
    return names


# FR-06: Define se o tipo é @article ou @misc
def _get_bibtex_entry_type(work_dict: dict[str, Any]) -> str:
    """Determina se a entrada BibTeX é article ou misc."""
    venue = work_dict.get("venue")
    has_venue = isinstance(venue, str) and bool(venue.strip())
    raw_type = work_dict.get("type")
    is_article_type = (
        isinstance(raw_type, str) and raw_type.strip().lower() in _ARTICLE_TYPES
    )
    if has_venue and is_article_type:
        return "article"
    return "misc"


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
        normalized_works: list[dict[str, Any]] = []
        for item in raw_works:
            if isinstance(item, Work):
                normalized_works.append(item.to_dict())
            elif isinstance(item, dict):
                normalized_works.append(item)

        if not normalized_works:
            return ""

        citation_keys = _generate_citation_keys(normalized_works)
        entries: list[str] = []

        for w, cite_key in zip(normalized_works, citation_keys):
            entry_type = _get_bibtex_entry_type(w)
            fields: list[tuple[str, str]] = []

            # title entre chaves duplas
            title = w.get("title")
            if title and isinstance(title, str) and title.strip():
                clean_title = escape_latex(title)
                fields.append(("title", f"{{{clean_title}}}"))

            # author como Sobrenome, Nome unidos por ' and '
            authors = w.get("authors") or []
            author_strings: list[str] = []
            for author in authors:
                formatted = _format_author_for_bibtex(author)
                if formatted:
                    author_strings.append(formatted)
            if author_strings:
                fields.append(("author", " and ".join(author_strings)))

            # year
            raw_year = w.get("year")
            if raw_year is not None and not isinstance(raw_year, bool):
                try:
                    y = int(raw_year)
                    if y > 0:
                        fields.append(("year", str(y)))
                except (ValueError, TypeError):
                    pass

            # journal no @article, howpublished no @misc
            venue = w.get("venue")
            if venue and isinstance(venue, str) and venue.strip():
                clean_venue = escape_latex(venue)
                if entry_type == "article":
                    fields.append(("journal", clean_venue))
                else:
                    fields.append(("howpublished", clean_venue))

            # doi e url
            doi = w.get("doi")
            clean_doi = _clean_doi(doi)
            if clean_doi:
                fields.append(("doi", escape_latex(clean_doi)))
                fields.append(("url", escape_latex(f"https://doi.org/{clean_doi}")))

            # abstract
            abstract = w.get("abstract")
            if abstract and isinstance(abstract, str) and abstract.strip():
                fields.append(("abstract", escape_latex(abstract)))

            # keywords
            raw_kws = w.get("keywords") or []
            clean_kws: list[str] = []
            for kw in raw_kws:
                if kw and isinstance(kw, str) and kw.strip():
                    clean_kws.append(escape_latex(kw))
            if clean_kws:
                fields.append(("keywords", ", ".join(clean_kws)))

            # note com fontes
            source_names = _extract_source_names(w)
            if source_names:
                note_text = f"Fontes: {', '.join(source_names)}"
                fields.append(("note", escape_latex(note_text)))

            lines = [f"@{entry_type}{{{cite_key},"]
            for field_name, field_val in fields:
                lines.append(f"  {field_name} = {{{field_val}}},")
            lines.append("}")
            entries.append("\n".join(lines))

        return "\n\n".join(entries) + "\n"
