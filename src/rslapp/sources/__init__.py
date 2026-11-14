"""Conectores de fontes acadêmicas do RSL.app."""

from __future__ import annotations

from typing import Literal

from typing_extensions import TypedDict

from rslapp import config
from rslapp.sources.base import Source
from rslapp.sources.crossref import CrossrefSource
from rslapp.sources.europe_pmc import EuropePMCSource
from rslapp.sources.openalex import OpenAlexSource
from rslapp.sources.pubmed import PubmedSource
from rslapp.sources.scopus import ScopusSource
from rslapp.sources.semantic_scholar import SemanticScholarSource
from rslapp.sources.web_of_science import WebOfScienceSource

__all__ = [
    "CrossrefSource",
    "EuropePMCSource",
    "OpenAlexSource",
    "PubmedSource",
    "ScopusSource",
    "SemanticScholarSource",
    "Source",
    "SourceInfo",
    "SourceName",
    "SourceStatus",
    "WebOfScienceSource",
    "build_sources",
    "list_sources_info",
]

# D-020, D-023: Nomes válidos de fontes acadêmicas disponíveis
SourceName = Literal[
    "openalex",
    "crossref",
    "semantic_scholar",
    "europe_pmc",
    "pubmed",
    "scopus",
    "web_of_science",
]
SourceStatus = Literal["ok", "missing_key"]


# D-002, FR-07, NFR-03: Estrutura de retorno de list_sources sem expor o valor de chaves
class SourceInfo(TypedDict):
    """Estado de configuração de uma fonte acadêmica."""

    name: SourceName
    configured: bool
    needs_key: bool
    status: SourceStatus


# FR-01, FR-04, FR-08, FR-16, D-002, D-020, D-023: Monta os conectores das fontes acadêmicas
def build_sources(include_paid: bool = True) -> list[Source]:
    """Instancia os conectores das fontes abertas e, quando solicitado, das bases pagas."""
    sources: list[Source] = [
        OpenAlexSource(),
        CrossrefSource(),
        SemanticScholarSource(),
        EuropePMCSource(),
        PubmedSource(),
    ]
    if include_paid:
        sources.extend(
            [
                ScopusSource(),
                WebOfScienceSource(),
            ]
        )
    return sources


# D-002, FR-07, FR-16, NFR-03, D-020, D-023: Monta a lista de estado das fontes acadêmicas
def list_sources_info(
    include_paid: bool = True,
    cfg: config.Config | None = None,
) -> list[SourceInfo]:
    """Informa para cada fonte acadêmica se está configurada, se exige chave e seu estado."""
    resolved_cfg = cfg if cfg is not None else config.load()
    openalex_configured = resolved_cfg.openalex_key_configured
    sources: list[SourceInfo] = [
        {
            "name": "openalex",
            "configured": openalex_configured,
            "needs_key": True,
            "status": "ok" if openalex_configured else "missing_key",
        },
        {
            "name": "crossref",
            "configured": True,
            "needs_key": False,
            "status": "ok",
        },
        {
            "name": "semantic_scholar",
            "configured": True,
            "needs_key": False,
            "status": "ok",
        },
        {
            "name": "europe_pmc",
            "configured": True,
            "needs_key": False,
            "status": "ok",
        },
        {
            "name": "pubmed",
            "configured": True,
            "needs_key": False,
            "status": "ok",
        },
    ]
    if include_paid:
        scopus_configured = resolved_cfg.scopus_key_configured
        wos_configured = resolved_cfg.wos_key_configured
        sources.extend(
            [
                {
                    "name": "scopus",
                    "configured": scopus_configured,
                    "needs_key": True,
                    "status": "ok" if scopus_configured else "missing_key",
                },
                {
                    "name": "web_of_science",
                    "configured": wos_configured,
                    "needs_key": True,
                    "status": "ok" if wos_configured else "missing_key",
                },
            ]
        )
    return sources


