"""Interface comum para conectores de fontes acadêmicas."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from rslapp.core.models import SourceResult


# FR-01, D-009: Contrato comum para que o miolo consulte qualquer fonte sem acoplamento
@runtime_checkable
class Source(Protocol):
    """Protocolo de uma fonte acadêmica consultada pelo miolo."""

    name: str
    needs_key: bool

    def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
        """Devolve os parâmetros que identificam a consulta no cache, sem chaves de API (NFR-03)."""
        ...

    async def search(self, query: str, max_results: int) -> SourceResult:
        """Executa a busca na fonte e devolve SourceResult sem levantar exceção para o miolo."""
        ...
