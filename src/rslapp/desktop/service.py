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

    # FR-16, FR-05: Carrega uma busca salva na pasta de dados
    def get_search(self, search_id: str) -> dict[str, Any]:
        """Lê e devolve os dados completos de uma busca salva, ou levanta RSLError('search_not_found')."""
        if not isinstance(search_id, str) or not search_id.strip():
            raise RSLError("search_not_found", f"Busca não encontrada: {search_id!r}")
        store, _ = self._build_store()
        try:
            return store.get_search(search_id.strip())
        except (FileNotFoundError, ValueError) as err:
            raise RSLError("search_not_found", f"Busca não encontrada: {search_id}") from err

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

    # FR-21, D-030: Verifica referências contra alucinação usando as fontes configuradas
    async def verify_references(
        self,
        references: str | list[Any],
    ) -> dict[str, Any]:
        """Verifica uma lista de referências contra as fontes configuradas."""
        from rslapp.core.verify import run_verify_references

        return await run_verify_references(
            build_sources(include_paid=True),
            references=references,
            request_summary="app desktop",
        )

    # FR-23, D-033: Importa registros bibliográficos externos e salva como nova lista no Store
    def import_works(
        self,
        content: str,
        format: str = "auto",
        list_name: str = "",
    ) -> dict[str, Any]:
        """Importa registros externos (RIS, BibTeX, Scopus CSV, WoS) e grava nova lista no Store."""
        from rslapp.importers import import_to_store

        store, _ = self._build_store()
        return import_to_store(
            store,
            content=content,
            format=format,
            request_summary="app desktop",
            list_name=list_name,
        )

    # FR-25, D-036: Grava ou atualiza a decisão de triagem de um trabalho
    def save_screening_decision(
        self,
        list_id: str,
        decision_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Salva a decisão de triagem no Store para a lista informada."""
        store, _ = self._build_store()
        try:
            return store.save_screening_decision(list_id.strip(), decision_data)
        except FileNotFoundError as err:
            raise RSLError("list_not_found", f"Lista não encontrada: {list_id}") from err
        except ValueError as err:
            raise RSLError("invalid_input", str(err)) from err

    # FR-25, D-036: Recupera todas as decisões de triagem de uma lista
    def get_screening(self, list_id: str) -> dict[str, Any]:
        """Recupera as decisões de triagem salvas para a lista informada."""
        store, _ = self._build_store()
        try:
            return store.get_screening(list_id.strip())
        except FileNotFoundError as err:
            raise RSLError("list_not_found", f"Lista não encontrada: {list_id}") from err

    # FR-25, D-036, D-037: Recupera o resumo quantitativo da triagem de uma lista
    def get_screening_summary(self, list_id: str) -> dict[str, Any]:
        """Recupera totais, percentual e motivos da triagem da lista informada."""
        store, _ = self._build_store()
        try:
            return store.get_screening_summary(list_id.strip())
        except FileNotFoundError as err:
            raise RSLError("list_not_found", f"Lista não encontrada: {list_id}") from err

    # FR-26, D-037: Calcula o fluxo PRISMA 2020 e gera SVG e relatório
    def get_prisma_flow(self, list_id: str) -> dict[str, Any]:
        """Calcula dados quantitativos do PRISMA 2020, diagrama SVG e checklist PRISMA-S."""
        from rslapp.core.prisma import (
            calculate_prisma_flow,
            render_prisma_markdown,
            render_prisma_svg,
        )

        store, _ = self._build_store()
        list_data = self.get_list(list_id)
        search_id = list_data.get("search_id")
        search_record = None
        if search_id:
            try:
                search_record = store.get_search(search_id)
            except (RSLError, FileNotFoundError, ValueError):
                search_record = None
        summary = store.get_screening_summary(list_id)
        flow_data = calculate_prisma_flow(list_data, summary, search_record=search_record)
        return {
            "list_id": list_id,
            "flow": flow_data,
            "svg": render_prisma_svg(flow_data),
            "report_markdown": render_prisma_markdown(flow_data),
        }

    # FR-27, D-038: Gera declaração metodológica formal de uso de IA
    def get_ai_disclosure(self, list_id: str, lang: str = "pt") -> str:
        """Gera a declaração metodológica de uso de IA (padrão COPE/ICMJE/SciELO)."""
        from rslapp.core.ai_disclosure import render_ai_disclosure

        store, _ = self._build_store()
        list_data = self.get_list(list_id)
        search_id = list_data.get("search_id")
        query = ""
        if search_id:
            try:
                s = store.get_search(search_id)
                query = str(s.get("request_summary", ""))
            except (RSLError, FileNotFoundError, ValueError):
                query = ""
        summary = store.get_screening_summary(list_id)
        total_works = int(list_data.get("total", len(list_data.get("works", []))))
        return render_ai_disclosure(
            list_id=list_id,
            search_query=query,
            total_works=total_works,
            screening_summary=summary,
            lang=lang,
        )
