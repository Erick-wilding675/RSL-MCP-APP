"""Conectores de fontes acadêmicas do RSL.app."""

from __future__ import annotations

from rslapp.sources.base import Source
from rslapp.sources.crossref import CrossrefSource
from rslapp.sources.europe_pmc import EuropePMCSource
from rslapp.sources.openalex import OpenAlexSource
from rslapp.sources.pubmed import PubmedSource
from rslapp.sources.semantic_scholar import SemanticScholarSource

__all__ = [
    "CrossrefSource",
    "EuropePMCSource",
    "OpenAlexSource",
    "PubmedSource",
    "SemanticScholarSource",
    "Source",
]

