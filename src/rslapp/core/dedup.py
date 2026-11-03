"""Deduplicação e junção de artigos acadêmicos entre múltiplas fontes."""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from rslapp.core.models import Author, Work

# FR-04: Ordem canônica de prevalência de fontes acadêmicas
SOURCE_PRECEDENCE: tuple[str, ...] = ("openalex", "crossref", "semantic_scholar")

_DOI_PREFIXES: tuple[str, ...] = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi:",
)


# FR-04: Normalização de DOI (minúsculo, sem prefixos URL ou 'doi:', sem barras finais)
def normalize_doi(raw: str | None) -> str | None:
    """Normaliza um DOI removendo prefixos conhecidos e espaços, em minúsculas."""
    if not isinstance(raw, str):
        return None
    val = raw.strip().lower()
    for prefix in _DOI_PREFIXES:
        if val.startswith(prefix):
            val = val[len(prefix) :].strip()
    val = val.rstrip("/")
    return val if val else None


# FR-04: Normalização de título (minúsculas, sem acento, só letras e números, espaços simples)
def normalize_title(title: str) -> str:
    """Normaliza um título para chave de deduplicação quando não há DOI."""
    if not isinstance(title, str):
        return ""
    decomposed = unicodedata.normalize("NFKD", title.lower())
    without_accents = "".join(
        ch for ch in decomposed if not unicodedata.combining(ch)
    )
    alnum_and_spaces = "".join(
        ch for ch in without_accents if ch.isalnum() or ch.isspace()
    )
    return " ".join(alnum_and_spaces.split())


def get_work_source(work: Work) -> str | None:
    """Identifica o nome da fonte principal de um trabalho acadêmico."""
    for src in SOURCE_PRECEDENCE:
        if src in work.source_ids or src in work.citations:
            return src
    if work.source_ids:
        return next(iter(work.source_ids.keys()))
    if work.citations:
        return next(iter(work.citations.keys()))
    return None


def _source_priority(work: Work) -> int:
    src = get_work_source(work)
    if src in SOURCE_PRECEDENCE:
        return SOURCE_PRECEDENCE.index(src)
    return len(SOURCE_PRECEDENCE)


@dataclass
class _WorkCluster:
    works: list[Work] = field(default_factory=list)
    doi: str | None = None
    norm_title: str = ""
    year: int | None = None


@dataclass
class DedupResult:
    """Resultado da deduplicação contendo trabalhos únicos e metadados de junção."""

    works: list[Work]
    merge: dict[str, Any]


# FR-04, FR-14: Prevalência de campos na junção (OpenAlex > Crossref > Semantic Scholar)
def _merge_cluster_works(cluster: _WorkCluster) -> Work:
    ordered = sorted(cluster.works, key=_source_priority)

    # Campos simples: primeiro valor não vazio na ordem de precedência
    title = next((w.title for w in ordered if w.title and w.title.strip()), "")
    doi = next((normalize_doi(w.doi) for w in ordered if normalize_doi(w.doi)), None)
    year = next((w.year for w in ordered if isinstance(w.year, int)), None)
    type_ = next((w.type for w in ordered if w.type and w.type.strip()), None)
    venue = next((w.venue for w in ordered if w.venue and w.venue.strip()), None)
    abstract = next((w.abstract for w in ordered if w.abstract and w.abstract.strip()), None)
    references_count = next(
        (w.references_count for w in ordered if isinstance(w.references_count, int)), None
    )

    # authors e keywords: primeira fonte que os tiver não vazios
    authors_work = next((w for w in ordered if w.authors), None)
    authors = [Author.from_dict(a.to_dict()) for a in authors_work.authors] if authors_work else []

    keywords_work = next((w for w in ordered if w.keywords), None)
    keywords = list(keywords_work.keywords) if keywords_work else []

    # source_ids e citations: unem todas as fontes sem perda e sem somar citações (FR-14)
    source_ids: dict[str, str] = {}
    for w in ordered:
        for src_name, src_id in w.source_ids.items():
            if src_name not in source_ids:
                source_ids[src_name] = src_id

    citations: dict[str, int] = {}
    for w in ordered:
        for src_name, count in w.citations.items():
            if src_name not in citations:
                citations[src_name] = count

    # references: união na ordem sem repetição, com ids da primeira fonte primeiro
    references: list[str] = []
    seen_refs: set[str] = set()
    for w in ordered:
        for ref in w.references:
            if ref not in seen_refs:
                seen_refs.add(ref)
                references.append(ref)

    return Work(
        title=title,
        doi=doi,
        year=year,
        type=type_,
        venue=venue,
        abstract=abstract,
        keywords=keywords,
        authors=authors,
        references=references,
        references_count=references_count,
        citations=citations,
        source_ids=source_ids,
    )


# FR-04: Contagem de divergências por campo em artigos presentes em mais de uma fonte
def _compute_cluster_divergences(cluster: _WorkCluster) -> dict[str, bool]:
    diverged = {"year": False, "title": False, "doi": False, "venue": False}
    ordered = sorted(cluster.works, key=_source_priority)

    # Agrupa o primeiro valor de cada fonte distinta
    seen_sources: set[str] = set()
    titles: list[str] = []
    years: list[int] = []
    dois: list[str] = []
    venues: list[str] = []

    for w in ordered:
        src = get_work_source(w) or id(w)
        if src in seen_sources:
            continue
        seen_sources.add(str(src))

        t_norm = normalize_title(w.title)
        if t_norm:
            titles.append(t_norm)

        if isinstance(w.year, int):
            years.append(w.year)

        d_norm = normalize_doi(w.doi)
        if d_norm:
            dois.append(d_norm)

        if w.venue and w.venue.strip():
            venues.append(w.venue.strip())

    if len(set(titles)) > 1:
        diverged["title"] = True
    if len(set(years)) > 1:
        diverged["year"] = True
    if len(set(dois)) > 1:
        diverged["doi"] = True
    if len(set(venues)) > 1:
        diverged["venue"] = True

    return diverged


# FR-04, FR-14: Deduplicação com contagem de artigos juntados e divergências
def deduplicate_works_with_merge(works: Sequence[Work]) -> DedupResult:
    """Agrupa artigos duplicados por DOI ou (título normalizado + ano), gerando merge info."""
    clusters: list[_WorkCluster] = []
    by_doi: dict[str, _WorkCluster] = {}
    by_title_year: dict[tuple[str, int], list[_WorkCluster]] = {}

    for work in works:
        norm_doi = normalize_doi(work.doi)
        norm_title = normalize_title(work.title)
        year = work.year if isinstance(work.year, int) else None

        matched_cluster: _WorkCluster | None = None

        if norm_doi is not None:
            if norm_doi in by_doi:
                matched_cluster = by_doi[norm_doi]
            elif norm_title and year is not None:
                candidates = by_title_year.get((norm_title, year), [])
                for candidate in candidates:
                    if candidate.doi is None:
                        matched_cluster = candidate
                        break
        else:
            # Sem DOI: só junta se houver título normalizado não vazio E ano definido
            if norm_title and year is not None:
                candidates = by_title_year.get((norm_title, year), [])
                if candidates:
                    matched_cluster = candidates[0]

        if matched_cluster is not None:
            matched_cluster.works.append(work)
            if matched_cluster.doi is None and norm_doi is not None:
                matched_cluster.doi = norm_doi
                by_doi[norm_doi] = matched_cluster
            if matched_cluster.year is None and year is not None:
                matched_cluster.year = year
            if not matched_cluster.norm_title and norm_title:
                matched_cluster.norm_title = norm_title
                if matched_cluster.year is not None:
                    by_title_year.setdefault(
                        (norm_title, matched_cluster.year), []
                    ).append(matched_cluster)
        else:
            new_cluster = _WorkCluster(
                works=[work],
                doi=norm_doi,
                norm_title=norm_title,
                year=year,
            )
            clusters.append(new_cluster)
            if norm_doi is not None:
                by_doi[norm_doi] = new_cluster
            if norm_title and year is not None:
                by_title_year.setdefault((norm_title, year), []).append(new_cluster)

    merged_count = 0
    divergence_counts: dict[str, int] = {"year": 0, "title": 0, "doi": 0, "venue": 0}
    deduped_works: list[Work] = []

    for cluster in clusters:
        distinct_sources: set[str] = set()
        for w in cluster.works:
            src = get_work_source(w)
            if src:
                distinct_sources.add(src)

        is_multi_source = len(distinct_sources) > 1 or (
            not distinct_sources and len(cluster.works) > 1
        )

        if is_multi_source:
            merged_count += 1
            divs = _compute_cluster_divergences(cluster)
            for field_name, had_div in divs.items():
                if had_div:
                    divergence_counts[field_name] += 1

        deduped_works.append(_merge_cluster_works(cluster))

    divergences_result = {k: v for k, v in divergence_counts.items() if v > 0}
    merge_info: dict[str, Any] = {
        "merged": merged_count,
        "divergences": divergences_result,
    }

    return DedupResult(works=deduped_works, merge=merge_info)


# FR-04: Interface simplificada de deduplicação preservando compatibilidade
def deduplicate_works(works: Sequence[Work]) -> list[Work]:
    """Remove duplicatas mantendo o primeiro registro pela ordem de precedência e agregando dados."""
    return deduplicate_works_with_merge(works).works
