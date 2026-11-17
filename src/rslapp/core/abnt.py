"""Formatador de referências bibliográficas segundo a norma ABNT NBR 6023:2018 (FR-24, D-034)."""

from __future__ import annotations

from typing import Any

from rslapp.core.models import Author, Work

_BRAZILIAN_SUFFIXES = {"junior", "júnior", "filho", "neto", "sobrinho"}


# FR-24, D-034: Normaliza nome do autor para formato ABNT (SOBRENOME, Nome)
def format_abnt_author_name(author_or_name: Author | str) -> str:
    """Converte o nome de um autor para o padrão ABNT (SOBRENOME, Prenomes)."""
    raw_name = (
        author_or_name.name
        if isinstance(author_or_name, Author)
        else str(author_or_name or "")
    )
    clean = " ".join(raw_name.strip().split())
    if not clean:
        return ""

    if "," in clean:
        parts = [p.strip() for p in clean.split(",", 1)]
        surname = parts[0].upper()
        forenames = parts[1] if len(parts) > 1 else ""
        return f"{surname}, {forenames}".strip(", ")

    words = clean.split()
    if len(words) == 1:
        return words[0].upper()

    last_word_lower = words[-1].lower()
    if last_word_lower in _BRAZILIAN_SUFFIXES and len(words) >= 3:
        # Ex: "João Silva Filho" -> "SILVA FILHO, João"
        surname = f"{words[-2]} {words[-1]}".upper()
        forenames = " ".join(words[:-2])
    else:
        # Ex: "Carlos Alberto da Silva" -> "SILVA, Carlos Alberto da"
        surname = words[-1].upper()
        forenames = " ".join(words[:-1])

    return f"{surname}, {forenames}".strip(", ")


# FR-24, D-034: Formata lista de autores segundo a ABNT NBR 6023:2018
def format_abnt_authors(
    authors: list[Author] | list[str],
    *,
    use_et_al_over_three: bool = False,
) -> str:
    """Gera a string de autoria formatada segundo a ABNT NBR 6023:2018."""
    if not authors:
        return ""

    formatted = [format_abnt_author_name(a) for a in authors if a]
    formatted = [f for f in formatted if f]
    if not formatted:
        return ""

    if use_et_al_over_three and len(formatted) > 3:
        return f"{formatted[0]} et al."

    return "; ".join(formatted)


# FR-24, D-032, D-034: Formatação de referência completa segundo a ABNT NBR 6023:2018
def format_abnt_reference(
    work: Work | dict[str, Any],
    *,
    markdown: bool = False,
    use_et_al: bool = False,
) -> str:
    """Gera a referência bibliográfica individual formatada segundo a ABNT NBR 6023:2018.

    Args:
        work: Instância Work ou dicionário contendo metadados do artigo.
        markdown: Se True, aplica negrito com ** no elemento de destaque.
        use_et_al: Se True, resume mais de 3 autores em 'et al.'.
    """
    if isinstance(work, dict):
        work_obj = Work.from_dict(work)
    elif isinstance(work, Work):
        work_obj = work
    else:
        raise TypeError("work deve ser uma instância de Work ou um dicionário")

    # 1. Autores
    authors_str = format_abnt_authors(work_obj.authors, use_et_al_over_three=use_et_al)

    # 2. Título do trabalho
    title = work_obj.title.strip() if work_obj.title else "Sem título"
    title = title.rstrip(".")

    # 3. Tipo e Veículo (Periódico, Evento, Livro)
    work_type = (work_obj.type or "article").lower()
    venue = work_obj.venue.strip() if work_obj.venue else ""
    year = work_obj.year

    parts: list[str] = []

    if authors_str:
        parts.append(f"{authors_str}.")

    if work_type in ("book", "monograph"):
        # Em livros e monografias, o destaque recai no título
        highlighted_title = f"**{title}**." if markdown else f"{title}."
        parts.append(highlighted_title)
        if venue:
            parts.append(f"{venue},")
        if year:
            parts.append(f"{year}.")
    else:
        # Em artigos e conferências, o título é regular e o periódico/anais ganha o destaque
        parts.append(f"{title}.")
        if venue:
            highlighted_venue = f"**{venue}**," if markdown else f"{venue},"
            parts.append(highlighted_venue)
        if year:
            parts.append(f"{year}.")

    # 4. DOI / Disponibilidade eletrônica
    if work_obj.doi:
        doi_clean = work_obj.doi.strip()
        parts.append(f"Disponível em: https://doi.org/{doi_clean}.")

    # 5. Retratação (D-032)
    if work_obj.is_retracted:
        parts.append("[Artigo retratado ou com expressão de preocupação oficial].")

    return " ".join(parts).strip()
