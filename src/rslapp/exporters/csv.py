"""Exportador de listas para o formato CSV compatível com Scopus / VOSviewer."""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping
from typing import Any

from rslapp.core.models import Affiliation, Author, Work
from rslapp.exporters.base import Exporter

# FR-06, D-020, D-023: Colunas do CSV compatível com Scopus com Scopus e Web of Science no fim
CSV_COLUMNS: tuple[str, ...] = (
    "Authors",
    "Author full names",
    "Title",
    "Year",
    "Source title",
    "DOI",
    "Abstract",
    "Author Keywords",
    "References",
    "Cited by",
    "Affiliations",
    "Document Type",
    "Source",
    "OpenAlex ID",
    "Crossref DOI",
    "Semantic Scholar ID",
    "Citations OpenAlex",
    "Citations Crossref",
    "Citations Semantic Scholar",
    "PubMed ID",
    "Europe PMC ID",
    "Citations Europe PMC",
    "Scopus EID",
    "Web of Science UID",
    "Citations Scopus",
    "Citations Web of Science",
)


def _clean_doi(raw: Any) -> str | None:
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


_FORMULA_PREFIXES: tuple[str, ...] = ("=", "+", "-", "@", "\t", "\r")


def _clean_text(raw: Any) -> str:
    if not isinstance(raw, str):
        return ""
    return " ".join(raw.split())


# FR-06: Protege célula de texto contra injeção de fórmula em planilhas (Excel)
def _protect_formula(value: str) -> str:
    if value.startswith(_FORMULA_PREFIXES):
        return f"'{value}"
    return value


# FR-06, FR-12, D-002, D-004: Exportador de listas no formato CSV Scopus para o VOSviewer
class CSVExporter(Exporter):
    """Renderizador no formato CSV compatível com Scopus (UTF-8 com BOM, delimitador vírgula)."""

    format: str = "csv"
    extension: str = "csv"

    # FR-06, FR-12, D-002, D-004, D-005, D-010: Renderiza CSV com colunas do Scopus e referências resolvidas para DOI
    def render(
        self,
        list_data: dict[str, Any],
        doi_mapping: Mapping[str, str | None] | None = None,
    ) -> str:
        """Renderiza a lista no formato CSV com BOM e terminadores \\r\\n."""
        if not isinstance(list_data, dict):
            raise TypeError("list_data deve ser um dicionário")

        raw_works = list_data.get("works") or []
        mapping = dict(doi_mapping or {})

        output = io.StringIO()
        # D-007, FR-06: UTF-8 com BOM (\ufeff)
        output.write("\ufeff")
        writer = csv.writer(
            output,
            delimiter=",",
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\r\n",
        )
        writer.writerow(CSV_COLUMNS)

        for item in raw_works:
            if isinstance(item, Work):
                w = item.to_dict()
            elif isinstance(item, dict):
                w = item
            else:
                continue

            # Authors, Author full names e Affiliations
            author_names: list[str] = []
            affiliations_list: list[str] = []
            authors = w.get("authors") or []
            for author in authors:
                name: str | None = None
                affs: list[Any] = []
                raw_affs: list[str] = []

                if isinstance(author, Author):
                    name = author.name
                    affs = author.affiliations
                    raw_affs = author.raw_affiliations
                elif isinstance(author, dict):
                    name = author.get("name")
                    affs = author.get("affiliations") or []
                    raw_affs = author.get("raw_affiliations") or []
                elif isinstance(author, str):
                    name = author

                clean_name = _clean_text(name)
                if clean_name:
                    author_names.append(clean_name)

                for aff in affs:
                    aff_name = (
                        aff.name
                        if isinstance(aff, Affiliation)
                        else (aff.get("name") if isinstance(aff, dict) else None)
                    )
                    clean_aff = _clean_text(aff_name)
                    if clean_aff and clean_aff not in affiliations_list:
                        affiliations_list.append(clean_aff)

                for raw_aff in raw_affs:
                    clean_raw = _clean_text(raw_aff)
                    if clean_raw and clean_raw not in affiliations_list:
                        affiliations_list.append(clean_raw)

            # FR-06: Proteção contra fórmula apenas no começo da célula das colunas de texto
            authors_str = _protect_formula("; ".join(author_names))
            authors_full_str = authors_str

            # Title
            title_str = _protect_formula(_clean_text(w.get("title")))

            # Year
            raw_year = w.get("year")
            year_str = ""
            if raw_year is not None and not isinstance(raw_year, bool):
                try:
                    y = int(raw_year)
                    if y > 0:
                        year_str = str(y)
                except (ValueError, TypeError):
                    pass

            # Source title (venue)
            source_title_str = _protect_formula(_clean_text(w.get("venue")))

            # DOI
            clean_work_doi = _clean_doi(w.get("doi"))
            doi_str = clean_work_doi or ""

            # Abstract (preserva pontuação, aspas e quebras de linha internas)
            abstract = w.get("abstract")
            if abstract and isinstance(abstract, str):
                abstract_clean = (
                    abstract
                    if abstract.startswith(("\t", "\r"))
                    and not abstract.lstrip().startswith(_FORMULA_PREFIXES)
                    else abstract.lstrip()
                )
                abstract_str = _protect_formula(abstract_clean)
            else:
                abstract_str = ""

            # Author Keywords
            raw_keywords = w.get("keywords") or []
            clean_keywords: list[str] = []
            for kw in raw_keywords:
                clean_kw = _clean_text(kw)
                if clean_kw:
                    clean_keywords.append(clean_kw)
            keywords_str = _protect_formula("; ".join(clean_keywords))

            # References (trocadas por DOI quando OpenAlex, omitindo sem DOI)
            raw_refs = w.get("references") or []
            ref_dois: list[str] = []
            for r in raw_refs:
                if not isinstance(r, str):
                    continue
                r_clean = r.strip()
                for prefix in ("https://openalex.org/", "http://openalex.org/"):
                    if r_clean.lower().startswith(prefix):
                        r_clean = r_clean[len(prefix) :].strip()
                r_clean_upper = r_clean.upper()

                if r_clean_upper in mapping:
                    mapped_doi = mapping[r_clean_upper]
                    cleaned_mapped = _clean_doi(mapped_doi)
                    if cleaned_mapped and cleaned_mapped not in ref_dois:
                        ref_dois.append(cleaned_mapped)
                elif r in mapping:
                    mapped_doi = mapping[r]
                    cleaned_mapped = _clean_doi(mapped_doi)
                    if cleaned_mapped and cleaned_mapped not in ref_dois:
                        ref_dois.append(cleaned_mapped)
                else:
                    cleaned_direct = _clean_doi(r)
                    if (
                        cleaned_direct
                        and (cleaned_direct.startswith("10.") or "/" in cleaned_direct)
                        and cleaned_direct not in ref_dois
                    ):
                        ref_dois.append(cleaned_direct)

            references_str = _protect_formula("; ".join(ref_dois))

            # Cited by (o maior número entre as fontes)
            raw_citations = w.get("citations") or {}
            cited_by_str = ""
            if isinstance(raw_citations, dict):
                valid_counts = [
                    v
                    for v in raw_citations.values()
                    if isinstance(v, int) and not isinstance(v, bool) and v >= 0
                ]
                if valid_counts:
                    cited_by_str = str(max(valid_counts))

            # Affiliations
            affiliations_str = _protect_formula("; ".join(affiliations_list))

            # Document Type
            doc_type_str = _protect_formula(_clean_text(w.get("type")))

            # Source (RSL.app)
            source_str = "RSL.app"

            # Identificadores nas fontes
            source_ids = w.get("source_ids") or {}
            openalex_id_str = ""
            crossref_doi_str = ""
            semantic_scholar_id_str = ""
            pubmed_id_str = ""
            europe_pmc_id_str = ""
            scopus_eid_str = ""
            wos_uid_str = ""
            if isinstance(source_ids, dict):
                openalex_id_str = str(source_ids.get("openalex") or "")
                crossref_doi_str = str(source_ids.get("crossref") or "")
                semantic_scholar_id_str = str(source_ids.get("semantic_scholar") or "")
                pubmed_id_str = str(source_ids.get("pubmed") or "")
                europe_pmc_id_str = str(source_ids.get("europe_pmc") or "")
                scopus_eid_str = str(source_ids.get("scopus") or "")
                wos_uid_str = str(source_ids.get("web_of_science") or "")

            # Citações por fonte
            cit_openalex_str = ""
            cit_crossref_str = ""
            cit_s2_str = ""
            cit_europe_pmc_str = ""
            cit_scopus_str = ""
            cit_wos_str = ""
            if isinstance(raw_citations, dict):
                oa_cit = raw_citations.get("openalex")
                if isinstance(oa_cit, int) and not isinstance(oa_cit, bool) and oa_cit >= 0:
                    cit_openalex_str = str(oa_cit)
                cr_cit = raw_citations.get("crossref")
                if isinstance(cr_cit, int) and not isinstance(cr_cit, bool) and cr_cit >= 0:
                    cit_crossref_str = str(cr_cit)
                s2_cit = raw_citations.get("semantic_scholar")
                if isinstance(s2_cit, int) and not isinstance(s2_cit, bool) and s2_cit >= 0:
                    cit_s2_str = str(s2_cit)
                epmc_cit = raw_citations.get("europe_pmc")
                if isinstance(epmc_cit, int) and not isinstance(epmc_cit, bool) and epmc_cit >= 0:
                    cit_europe_pmc_str = str(epmc_cit)
                scopus_cit = raw_citations.get("scopus")
                if isinstance(scopus_cit, int) and not isinstance(scopus_cit, bool) and scopus_cit >= 0:
                    cit_scopus_str = str(scopus_cit)
                wos_cit = raw_citations.get("web_of_science")
                if isinstance(wos_cit, int) and not isinstance(wos_cit, bool) and wos_cit >= 0:
                    cit_wos_str = str(wos_cit)

            row = [
                authors_str,
                authors_full_str,
                title_str,
                year_str,
                source_title_str,
                doi_str,
                abstract_str,
                keywords_str,
                references_str,
                cited_by_str,
                affiliations_str,
                doc_type_str,
                source_str,
                openalex_id_str,
                crossref_doi_str,
                semantic_scholar_id_str,
                cit_openalex_str,
                cit_crossref_str,
                cit_s2_str,
                pubmed_id_str,
                europe_pmc_id_str,
                cit_europe_pmc_str,
                scopus_eid_str,
                wos_uid_str,
                cit_scopus_str,
                cit_wos_str,
            ]
            writer.writerow(row)

        return output.getvalue()
