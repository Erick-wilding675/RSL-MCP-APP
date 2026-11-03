"""Modelos de dados do miolo do RSL.app."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


# FR-03, D-004: Afiliação de autor com nome, identificadores (OpenAlex, ROR) e país
@dataclass
class Affiliation:
    """Instituição de afiliação de um autor."""

    name: str | None = None
    ids: dict[str, str] = field(default_factory=dict)
    country_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ids": dict(self.ids),
            "country_code": self.country_code,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Affiliation:
        return cls(
            name=data.get("name"),
            ids=dict(data.get("ids") or {}),
            country_code=data.get("country_code"),
        )


# FR-03, D-004: Dados completos do autor (nome, ORCID curto, ids nas fontes e afiliações)
@dataclass
class Author:
    """Autor de um trabalho acadêmico."""

    name: str
    orcid: str | None = None
    ids: dict[str, str] = field(default_factory=dict)
    position: str | None = None
    is_corresponding: bool | None = None
    affiliations: list[Affiliation] = field(default_factory=list)
    raw_affiliations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "orcid": self.orcid,
            "ids": dict(self.ids),
            "position": self.position,
            "is_corresponding": self.is_corresponding,
            "affiliations": [aff.to_dict() for aff in self.affiliations],
            "raw_affiliations": list(self.raw_affiliations),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Author:
        return cls(
            name=str(data["name"]),
            orcid=data.get("orcid"),
            ids=dict(data.get("ids") or {}),
            position=data.get("position"),
            is_corresponding=data.get("is_corresponding"),
            affiliations=[
                Affiliation.from_dict(a) for a in (data.get("affiliations") or [])
            ],
            raw_affiliations=list(data.get("raw_affiliations") or []),
        )


# FR-03, FR-14, D-004, D-010: Registro completo do artigo com autores, referências e citações
@dataclass
class Work:
    """Artigo acadêmico normalizado no formato comum do miolo."""

    title: str
    doi: str | None = None
    year: int | None = None
    type: str | None = None
    venue: str | None = None
    abstract: str | None = None
    keywords: list[str] = field(default_factory=list)
    authors: list[Author] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    references_count: int | None = None
    citations: dict[str, int] = field(default_factory=dict)
    source_ids: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "doi": self.doi,
            "year": self.year,
            "type": self.type,
            "venue": self.venue,
            "abstract": self.abstract,
            "keywords": list(self.keywords),
            "authors": [author.to_dict() for author in self.authors],
            "references": list(self.references),
            "references_count": self.references_count,
            "citations": dict(self.citations),
            "source_ids": dict(self.source_ids),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Work:
        return cls(
            title=str(data["title"]),
            doi=data.get("doi"),
            year=data.get("year"),
            type=data.get("type"),
            venue=data.get("venue"),
            abstract=data.get("abstract"),
            keywords=list(data.get("keywords") or []),
            authors=[Author.from_dict(a) for a in (data.get("authors") or [])],
            references=list(data.get("references") or []),
            references_count=data.get("references_count"),
            citations=dict(data.get("citations") or {}),
            source_ids=dict(data.get("source_ids") or {}),
        )


# FR-01, NFR-03: Resultado de uma fonte com estado, contagens e consulta sem chave de API
@dataclass
class SourceResult:
    """Resultado devolvido por um conector de fonte acadêmica."""

    name: str
    status: str
    reason: str | None = None
    query: str = ""
    found: int | None = None
    fetched: int = 0
    works: list[Work] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "reason": self.reason,
            "query": self.query,
            "found": self.found,
            "fetched": self.fetched,
            "works": [work.to_dict() for work in self.works],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SourceResult:
        return cls(
            name=str(data["name"]),
            status=str(data["status"]),
            reason=data.get("reason"),
            query=str(data.get("query", "")),
            found=data.get("found"),
            fetched=int(data.get("fetched", 0)),
            works=[Work.from_dict(w) for w in (data.get("works") or [])],
        )
