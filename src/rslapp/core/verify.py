"""Verificador de referências acadêmicas contra alucinações (D-030, FR-21)."""

from __future__ import annotations

import asyncio
import contextlib
import difflib
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from rslapp.core.dedup import normalize_doi, normalize_title
from rslapp.core.models import Work
from rslapp.sources.base import Source

__all__ = [
    "ReferenceInput",
    "VerificationResult",
    "parse_references",
    "run_verify_references",
]

# FR-21: Expressão regular para captura de DOIs em strings de citação
_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b", re.IGNORECASE)

# FR-21: Expressão regular para captura de anos de publicação (1800 a 2099)
_YEAR_RE = re.compile(r"\b(1[89]\d\d|20\d\d)\b")

# FR-21: Expressão regular para blocos BibTeX
_BIBTEX_ENTRY_RE = re.compile(r"@\w+\s*\{[^,]+,(.*?)\n\s*\}", re.DOTALL | re.IGNORECASE)
_BIBTEX_FIELD_RE = re.compile(
    r'(\w+)\s*=\s*(?:\{([^{}]*)\}|"([^"]*)"|(\d+))', re.DOTALL | re.IGNORECASE
)


@dataclass
class ReferenceInput:
    """Dados extraídos de uma referência citada a ser verificada."""

    raw_text: str
    doi: str | None = None
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    year: int | None = None


@dataclass
class VerificationResult:
    """Resultado detalhado da verificação de uma referência contra as fontes."""

    input_ref: str
    status: str  # "verified", "divergent", "not_found"
    status_label: str  # "Confirmada", "Divergência", "Não encontrada"
    doi: str | None = None
    matched_title: str | None = None
    matched_authors: list[str] = field(default_factory=list)
    matched_year: int | None = None
    matched_venue: str | None = None
    source: str | None = None
    divergence_details: list[str] = field(default_factory=list)
    similarity: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Converte o resultado em dicionário serializável."""
        return asdict(self)


# FR-21: Extrai referências estruturadas a partir de texto livre, BibTeX ou sequência de entradas
def parse_references(
    input_data: str | Sequence[str | dict[str, Any]],
) -> list[ReferenceInput]:
    """Interpreta as referências de entrada e extrai metadados estruturados."""
    results: list[ReferenceInput] = []

    if isinstance(input_data, str):
        text = input_data.strip()
        if not text:
            return []

        # 1. Verifica se contém blocos BibTeX
        bibtex_matches = list(_BIBTEX_ENTRY_RE.finditer(text))
        if bibtex_matches:
            for match in bibtex_matches:
                entry_body = match.group(1)
                fields: dict[str, str] = {}
                for fmatch in _BIBTEX_FIELD_RE.finditer(entry_body):
                    key = fmatch.group(1).lower()
                    val = next((g for g in fmatch.groups()[1:] if g is not None), "")
                    fields[key] = val.strip()

                raw_doi = fields.get("doi")
                norm_doi = normalize_doi(raw_doi) if raw_doi else None
                raw_year = fields.get("year")
                year_val = int(raw_year) if raw_year and raw_year.isdigit() else None
                raw_author = fields.get("author", "")
                authors_list = [
                    a.strip() for a in re.split(r"\s+and\s+", raw_author, flags=re.IGNORECASE) if a.strip()
                ]
                results.append(
                    ReferenceInput(
                        raw_text=match.group(0).strip(),
                        doi=norm_doi,
                        title=fields.get("title"),
                        authors=authors_list,
                        year=year_val,
                    )
                )
            return results

        # 2. Divide referências em texto livre (por quebra dupla ou linhas numeradas)
        chunks = [c.strip() for c in re.split(r"\n\s*\n+", text) if c.strip()]
        if len(chunks) == 1 and "\n" in chunks[0]:
            # Se for uma linha por referência numerada (ex: [1], 1., etc.)
            lines = [line.strip() for line in chunks[0].splitlines() if line.strip()]
            if all(re.match(r"^(\[\d+\]|\d+[\.\)])\s+", line) for line in lines):
                chunks = lines

        for chunk in chunks:
            # Remove numeração inicial comum: [1], 1., 1)
            clean_chunk = re.sub(r"^(\[\d+\]|\d+[\.\)])\s*", "", chunk).strip()
            doi_match = _DOI_RE.search(clean_chunk)
            norm_doi = normalize_doi(doi_match.group(0)) if doi_match else None

            year_matches = _YEAR_RE.findall(clean_chunk)
            year_val = int(year_matches[0]) if year_matches else None

            # Tenta separar título de autores pelo ano ou pontuação
            title_candidate: str | None = None
            authors_list: list[str] = []

            # Procura autores antes do ano (formato clássico: Autor (Ano). Título.)
            m_author_year = re.match(
                r"^([A-ZÀ-Ú][^.]+?)\s*(?:\((\d{4})\)|\b(\d{4})\b)[\.\:\,\s]+(.+)$",
                clean_chunk,
                re.DOTALL,
            )
            if m_author_year:
                author_str = m_author_year.group(1).strip()
                authors_list = [
                    a.strip()
                    for a in re.split(r";|\s+and\s+|\s+e\s+", author_str, flags=re.IGNORECASE)
                    if a.strip()
                ]
                rest = m_author_year.group(4).strip()
                # O título geralmente termina no primeiro ponto ou ponto e vírgula
                title_parts = re.split(r"[\.\?!]\s+", rest)
                title_candidate = title_parts[0].strip() if title_parts else rest
            else:
                title_candidate = clean_chunk

            results.append(
                ReferenceInput(
                    raw_text=chunk,
                    doi=norm_doi,
                    title=title_candidate,
                    authors=authors_list,
                    year=year_val,
                )
            )
        return results

    # Lista de itens (strings ou dicionários)
    for item in input_data:
        if isinstance(item, dict):
            raw_doi = item.get("doi")
            norm_doi = normalize_doi(str(raw_doi)) if raw_doi else None
            raw_year = item.get("year")
            year_val = int(raw_year) if isinstance(raw_year, int) else None
            authors_raw = item.get("authors") or item.get("author") or []
            if isinstance(authors_raw, str):
                authors_list = [authors_raw]
            elif isinstance(authors_raw, list):
                authors_list = [str(a) for a in authors_raw if str(a).strip()]
            else:
                authors_list = []
            title_val = str(item.get("title") or "").strip() or None
            results.append(
                ReferenceInput(
                    raw_text=str(item.get("raw_text") or title_val or norm_doi or "ref"),
                    doi=norm_doi,
                    title=title_val,
                    authors=authors_list,
                    year=year_val,
                )
            )
        elif isinstance(item, str) and item.strip():
            parsed_single = parse_references(item)
            results.extend(parsed_single)

    return results


# FR-21: Avalia semelhança entre a citação fornecida e o registro oficial encontrado
def _evaluate_match(
    ref: ReferenceInput,
    work: Work,
    source_name: str,
) -> VerificationResult:
    """Compara os campos de uma referência fornecida com o trabalho real e detecta divergências."""
    divergences: list[str] = []

    # 1. Similaridade do título normalizado
    norm_ref_title = normalize_title(ref.title or ref.raw_text)
    norm_work_title = normalize_title(work.title)
    similarity = difflib.SequenceMatcher(None, norm_ref_title, norm_work_title).ratio()

    # 2. Conferência de DOI
    doi_matches = False
    if ref.doi and work.doi:
        norm_ref_doi = normalize_doi(ref.doi)
        norm_work_doi = normalize_doi(work.doi)
        if norm_ref_doi == norm_work_doi:
            doi_matches = True

    # 3. Conferência de Ano
    if ref.year is not None and work.year is not None and abs(ref.year - work.year) > 1:
        divergences.append(
            f"Ano citado ({ref.year}) difere do ano de publicação oficial ({work.year})."
        )

    # 4. Conferência de Autores
    if ref.authors and work.authors:
        first_ref_author = ref.authors[0].lower()
        # Extrai sobrenome (última palavra ou primeira em formato ABNT 'SOBRENOME, Nome')
        author_tokens = re.findall(r"\w+", first_ref_author)
        surname = author_tokens[0] if "," in first_ref_author else (author_tokens[-1] if author_tokens else "")
        if surname and len(surname) >= 3:
            matched_any = any(
                surname in normalize_title(w_author.name) for w_author in work.authors
            )
            if not matched_any:
                divergences.append(
                    f"Autor principal citado ({ref.authors[0]}) não coincide com os autores oficiais ({', '.join(a.name for a in work.authors[:3])})."
                )

    # Decisão de status
    author_names = [a.name for a in work.authors if a.name]
    if doi_matches or similarity >= 0.82:
        if divergences:
            status = "divergent"
            label = "Divergência"
        else:
            status = "verified"
            label = "Confirmada"
    elif similarity >= 0.65:
        divergences.append(
            f"Título citado possui baixa similaridade ({similarity:.0%}) com o título encontrado."
        )
        status = "divergent"
        label = "Divergência"
    else:
        return VerificationResult(
            input_ref=ref.raw_text,
            status="not_found",
            status_label="Não encontrada",
            divergence_details=["Nenhuma correspondência com confiança suficiente encontrada nas bases."],
            similarity=similarity,
        )

    return VerificationResult(
        input_ref=ref.raw_text,
        status=status,
        status_label=label,
        doi=work.doi,
        matched_title=work.title,
        matched_authors=author_names,
        matched_year=work.year,
        matched_venue=work.venue,
        source=source_name,
        divergence_details=divergences,
        similarity=round(similarity, 3),
    )


# FR-21, D-030: Consulta assíncrona com fallback entre Crossref e OpenAlex
async def _verify_single_reference(
    ref: ReferenceInput,
    sources_map: dict[str, Source],
) -> VerificationResult:
    """Verifica uma referência individual consultando Crossref e OpenAlex."""
    best_result: VerificationResult | None = None

    # Ordem canônica de verificação aberta: OpenAlex e Crossref
    active_sources = [
        (name, sources_map[name])
        for name in ("openalex", "crossref")
        if name in sources_map
    ]
    if not active_sources:
        active_sources = list(sources_map.items())

    # Passo 1: Busca direta por DOI se disponível
    if ref.doi:
        norm_doi = normalize_doi(ref.doi)
        if norm_doi:
            for src_name, source in active_sources:
                find_fn = getattr(source, "find_by_doi", None)
                if callable(find_fn):
                    with contextlib.suppress(Exception):
                        work = await find_fn(norm_doi)
                        if work is not None:
                            return _evaluate_match(ref, work, src_name)

    # Passo 2: Busca textual pelo título ou texto da referência
    search_query = (ref.title or ref.raw_text).strip()
    # Limpa caracteres desnecessários para a busca
    search_query = re.sub(r"[^\w\s\-\:]", " ", search_query).strip()
    if not search_query:
        return VerificationResult(
            input_ref=ref.raw_text,
            status="not_found",
            status_label="Não encontrada",
            divergence_details=["Texto de referência insuficiente para consulta."],
        )

    for src_name, source in active_sources:
        with contextlib.suppress(Exception):
            res = await source.search(search_query, max_results=3)
            if res.works:
                for candidate in res.works:
                    eval_res = _evaluate_match(ref, candidate, src_name)
                    if eval_res.status == "verified":
                        return eval_res
                    if best_result is None or eval_res.similarity > best_result.similarity:
                        best_result = eval_res

    if best_result is not None and best_result.status != "not_found":
        return best_result

    return VerificationResult(
        input_ref=ref.raw_text,
        status="not_found",
        status_label="Não encontrada",
        divergence_details=["Referência não encontrada nas bases consultadas. Possível alucinação de IA."],
        similarity=best_result.similarity if best_result else 0.0,
    )


# FR-21, D-002, D-030: Função principal do verificador de referências
async def run_verify_references(
    sources: Sequence[Source],
    references: str | Sequence[str | dict[str, Any]],
    *,
    request_summary: str = "",
) -> dict[str, Any]:
    """Verifica uma coleção de referências contra alucinação usando Crossref e OpenAlex."""
    _ = request_summary
    parsed = parse_references(references)
    if not parsed:
        return {
            "total": 0,
            "verified": 0,
            "divergent": 0,
            "not_found": 0,
            "results": [],
        }

    sources_map = {s.name: s for s in sources}
    semaphore = asyncio.Semaphore(5)

    async def _safe_verify(ref_item: ReferenceInput) -> VerificationResult:
        async with semaphore:
            return await _verify_single_reference(ref_item, sources_map)

    results = await asyncio.gather(*[_safe_verify(item) for item in parsed])

    verified_count = sum(1 for r in results if r.status == "verified")
    divergent_count = sum(1 for r in results if r.status == "divergent")
    not_found_count = sum(1 for r in results if r.status == "not_found")

    return {
        "total": len(results),
        "verified": verified_count,
        "divergent": divergent_count,
        "not_found": not_found_count,
        "results": [r.to_dict() for r in results],
    }
