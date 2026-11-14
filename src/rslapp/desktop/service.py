"""Serviço do app desktop sobre o núcleo do RSL.app (FR-16, FR-17)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rslapp import config
from rslapp.core.errors import RSLError
from rslapp.core.repeat import run_repeat
from rslapp.core.search import DEFAULT_MAX_RESULTS, run_search
from rslapp.exporters import run_export
from rslapp.sources import SourceInfo, build_sources, list_sources_info
from rslapp.store import Store


# FR-16, FR-17, D-024, D-025: Serviço sem estado global que chama o núcleo com a mesma pasta e log do stdio
class DesktopService:
    """Fachada sem estado sobre o núcleo, Store e exportadores para as telas do app desktop."""

    def _build_store(self) -> tuple[Store, config.Config]:
        cfg = config.load()
        return Store(cfg.data_dir, cfg.cache_days), cfg

    # FR-16, FR-07, D-023: Lista o estado das 7 fontes no mesmo formato do servidor no modo stdio
    def list_sources(self) -> list[SourceInfo]:
        """Devolve as 7 fontes acadêmicas e seu estado de configuração atual."""
        cfg = config.load()
        return list_sources_info(include_paid=True, cfg=cfg)

    # FR-16, FR-01, FR-04, FR-05, FR-08, FR-09, FR-12: Executa busca nas fontes com request_summary="app desktop"
    async def search(
        self,
        query: str,
        sources: list[str] | None = None,
        max_results: int = DEFAULT_MAX_RESULTS,
        include_peer_review: bool = False,
    ) -> dict[str, Any]:
        """Executa busca por termos no núcleo e grava lista, busca e entrada no log.md."""
        store, _ = self._build_store()
        return await run_search(
            store,
            build_sources(include_paid=True),
            query=query,
            request_summary="app desktop",
            max_results=max_results,
            source_names=sources,
            include_peer_review=include_peer_review,
        )

    # FR-16, FR-12: Carrega uma lista salva na pasta de dados
    def get_list(self, list_id: str) -> dict[str, Any]:
        """Lê e devolve os dados completos de uma lista salva, ou levanta RSLError('list_not_found')."""
        if not isinstance(list_id, str) or not list_id.strip():
            raise RSLError("list_not_found", f"Lista não encontrada: {list_id!r}")
        store, _ = self._build_store()
        try:
            return store.get_list(list_id.strip())
        except (FileNotFoundError, ValueError) as err:
            raise RSLError("list_not_found", f"Lista não encontrada: {list_id}") from err

    # FR-16, FR-06, FR-12: Exporta uma lista salva para cfg.export_dir e devolve o caminho gravado
    def export(self, list_id: str, export_format: str) -> dict[str, Any]:
        """Exporta a lista no formato pedido para a pasta de exportações configurada."""
        store, cfg = self._build_store()
        return run_export(
            store,
            list_id=list_id,
            export_format=export_format,
            export_dir=cfg.export_dir,
        )

    # FR-17, FR-05: Lista as buscas já registradas na pasta de dados
    def list_searches(self) -> list[dict[str, Any]]:
        """Devolve as buscas registradas em searches/."""
        store, _ = self._build_store()
        return store.list_searches()

    # FR-17, FR-11: Repete uma busca salva do histórico
    async def repeat(self, search_id: str) -> dict[str, Any]:
        """Repete uma busca salva a partir do seu identificador."""
        store, _ = self._build_store()
        return await run_repeat(
            store,
            build_sources(include_paid=True),
            search_id=search_id,
        )

    # FR-17, FR-13: Caminho do arquivo log.md legível por pessoas
    def log_path(self) -> Path:
        """Devolve o caminho do arquivo log.md na pasta de dados atual."""
        store, _ = self._build_store()
        return store.log_path
