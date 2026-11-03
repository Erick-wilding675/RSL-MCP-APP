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
    dois: set[str] = field(default_factory=set)
    title_years: set[tuple[str, int]] = field(default_factory=set)


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


# FR-04: Atualização de índices do grupo para junção transitiva
def _reindex_cluster(
    cluster: _WorkCluster,
    by_doi: dict[str, _WorkCluster],
    by_title_year: dict[tuple[str, int], list[_WorkCluster]],
) -> None:
    for w in cluster.works:
        norm_d = normalize_doi(w.doi)
        if norm_d is not None:
            cluster.dois.add(norm_d)
            by_doi[norm_d] = cluster

        # FR-04: só o título com o ano do próprio registro entra no índice; ano ausente
        # nunca é emprestado de outro membro (a regra é por par, e assim não depende da ordem)
        norm_t = normalize_title(w.title)
        if norm_t and isinstance(w.year, int):
            ty = (norm_t, w.year)
            cluster.title_years.add(ty)
            cands = by_title_year.setdefault(ty, [])
            if cluster not in cands:
                cands.append(cluster)


# FR-04: Fusão de grupo de origem no alvo com migração de referências e índices
def _merge_clusters(
    target: _WorkCluster,
    source: _WorkCluster,
    clusters: list[_WorkCluster],
    by_doi: dict[str, _WorkCluster],
    by_title_year: dict[tuple[str, int], list[_WorkCluster]],
) -> None:
    target.works.extend(source.works)
    if source in clusters:
        clusters.remove(source)
    for ty in source.title_years:
        if ty in by_title_year and source in by_title_year[ty]:
            by_title_year[ty].remove(source)
    for d in source.dois:
        if by_doi.get(d) is source:
            by_doi[d] = target
    _reindex_cluster(target, by_doi, by_title_year)


# FR-04, FR-14: Deduplicação transitiva com contagem de artigos juntados e divergências
def deduplicate_works_with_merge(works: Sequence[Work]) -> DedupResult:
    """Agrupa artigos duplicados por DOI ou (título normalizado + ano), gerando merge info."""
    clusters: list[_WorkCluster] = []
    by_doi: dict[str, _WorkCluster] = {}
    by_title_year: dict[tuple[str, int], list[_WorkCluster]] = {}

    for work in works:
        norm_doi = normalize_doi(work.doi)
        norm_title = normalize_title(work.title)
        year = work.year if isinstance(work.year, int) else None

        doi_cluster = by_doi.get(norm_doi) if norm_doi is not None else None

        title_clusters: list[_WorkCluster] = []
        if norm_title and year is not None:
            for cand in by_title_year.get((norm_title, year), []):
                if cand not in title_clusters:
                    title_clusters.append(cand)

        # Escolha do cluster alvo respeitando regras de DOI e junção transitiva:
        # - Dois DOIs diferentes nunca se juntam (FR-04).
        # - Se um registro casa com dois grupos diferentes (um pelo DOI, outro pelo título),
        #   ele fica no grupo do DOI (FR-04).
        target: _WorkCluster
        if doi_cluster is not None:
            target = doi_cluster
        elif norm_doi is not None:
            valid_cands = [c for c in title_clusters if not c.dois]
            if valid_cands:
                target = valid_cands[0]
            else:
                target = _WorkCluster()
                clusters.append(target)
        else:
            if title_clusters:
                doi_cands = [c for c in title_clusters if c.dois]
                target = doi_cands[0] if doi_cands else title_clusters[0]
            else:
                target = _WorkCluster()
                clusters.append(target)

        # Funde transitivamente quaisquer candidatos por título que não tenham DOI conflitante
        for cand in title_clusters:
            if cand is not target and not cand.dois:
                _merge_clusters(target, cand, clusters, by_doi, by_title_year)

        target.works.append(work)
        _reindex_cluster(target, by_doi, by_title_year)

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
