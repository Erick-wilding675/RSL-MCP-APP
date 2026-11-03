"""Serviço de resolução de referências (ids do OpenAlex para DOI) com cache."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

_OPENALEX_WORK_ID_RE = re.compile(r"^W\d+$", re.IGNORECASE)


# FR-14, D-005, D-010: Resultado da resolução de referências para DOI
@dataclass
class ReferenceResolution:
    """Resultado da resolução de referências de ids do OpenAlex para DOI."""

    mapping: dict[str, str | None]
    calls: int
    from_cache: int
    complete: bool
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mapping": dict(self.mapping),
            "calls": self.calls,
            "from_cache": self.from_cache,
            "complete": self.complete,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ReferenceResolution:
        return cls(
            mapping=dict(data.get("mapping") or {}),
            calls=int(data.get("calls", 0)),
            from_cache=int(data.get("from_cache", 0)),
            complete=bool(data.get("complete", False)),
            reason=data.get("reason"),
        )


def _is_openalex_work_id(raw: Any) -> bool:
    if not isinstance(raw, str):
        return False
    val = raw.strip()
    for prefix in ("https://openalex.org/", "http://openalex.org/"):
        if val.lower().startswith(prefix):
            val = val[len(prefix) :].strip()
    return bool(_OPENALEX_WORK_ID_RE.fullmatch(val))


def _clean_openalex_work_id(raw: str) -> str:
    val = raw.strip()
    for prefix in ("https://openalex.org/", "http://openalex.org/"):
        if val.lower().startswith(prefix):
            val = val[len(prefix) :].strip()
    return val.upper()


# FR-14, NFR-01, NFR-03, D-005, D-010: Resolução de ids do OpenAlex para DOI em lotes de até 100 com cache
async def resolve_reference_dois(
    ids: Iterable[str] | None,
    *,
    store: Any,
    source: Any = None,
) -> ReferenceResolution:
    if source is None:
        from rslapp.sources.openalex import OpenAlexSource

        source = OpenAlexSource()

    if not ids:
        return ReferenceResolution(
            mapping={},
            calls=0,
            from_cache=0,
            complete=True,
            reason=None,
        )

    # FR-14, D-010: Tira repetidos preservando ordem e ignora entradas que não são ids do OpenAlex
    unique_ids: list[str] = []
    seen: set[str] = set()
    for item in ids:
        if _is_openalex_work_id(item):
            cid = _clean_openalex_work_id(item)
            if cid not in seen:
                seen.add(cid)
                unique_ids.append(cid)

    if not unique_ids:
        return ReferenceResolution(
            mapping={},
            calls=0,
            from_cache=0,
            complete=True,
            reason=None,
        )

    mapping: dict[str, str | None] = {}
    missing_ids: list[str] = []
    from_cache = 0

    # NFR-06, D-007, D-010: Consulta o cache local por id ("openalex_doi", {"id": "W123"})
    for oid in unique_ids:
        cached = store.get_cache("openalex_doi", {"id": oid})
        if cached is not None:
            resp = cached.get("response")
            doi = resp.get("doi") if isinstance(resp, dict) else None
            mapping[oid] = doi
            from_cache += 1
        else:
            missing_ids.append(oid)

    if not missing_ids:
        return ReferenceResolution(
            mapping=mapping,
            calls=0,
            from_cache=from_cache,
            complete=True,
            reason=None,
        )

    # NFR-01, D-010: Agrupa os ids faltantes em lotes de até 100
    batch_size = 100
    calls = 0
    complete = True
    reason: str | None = None

    for i in range(0, len(missing_ids), batch_size):
        batch = missing_ids[i : i + batch_size]
        lookup = await source.lookup_dois(batch)

        if lookup.status == "missing_key":
            # NFR-03: Sem chave configurada nenhuma chamada é feita
            complete = False
            reason = "missing_key"
            for remaining_id in missing_ids[i:]:
                mapping[remaining_id] = None
            break

        calls += 1

        if lookup.status != "ok":
            # NFR-04: Falha na fonte: não grava no cache e marca incompleta
            complete = False
            reason = f"{lookup.status}: {lookup.reason}" if lookup.reason else lookup.status
            for remaining_id in missing_ids[i:]:
                mapping[remaining_id] = None
            break

        # Grava no cache cada id respondido (inclusive sem DOI e omitidos)
        for oid in batch:
            doi = lookup.mapping.get(oid)
            mapping[oid] = doi
            store.set_cache("openalex_doi", {"id": oid}, {"doi": doi})

    return ReferenceResolution(
        mapping=mapping,
        calls=calls,
        from_cache=from_cache,
        complete=complete,
        reason=reason,
    )
