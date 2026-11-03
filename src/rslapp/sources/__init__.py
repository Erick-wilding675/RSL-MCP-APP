"""Conectores de fontes acadêmicas do RSL.app."""

from __future__ import annotations

from rslapp.sources.base import Source
from rslapp.sources.openalex import OpenAlexSource

__all__ = ["OpenAlexSource", "Source"]
