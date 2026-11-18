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

    # FR-28, D-039: Gera o pacote de reprodutibilidade científica em .zip
    def export_reproducibility_package(self, list_id: str) -> dict[str, Any]:
        """Gera o arquivo zip com todos os artefatos da revisão e o manifesto SHA-256."""
        from rslapp.core.reproducibility import build_reproducibility_package

        store, export_dir = self._build_store()
        return build_reproducibility_package(list_id=list_id, store=store, export_dir=export_dir)

    # FR-29, D-040: Salva ou atualiza a ficha analítica de um artigo
    def save_work_note(self, list_id: str, note_data: dict[str, Any]) -> dict[str, Any]:
        """Salva ou atualiza a ficha científica de um trabalho em notes/{list_id}/{work_id}.json."""
        store, _ = self._build_store()
        try:
            return store.save_note(list_id.strip(), note_data)
        except FileNotFoundError as err:
            raise RSLError("list_not_found", f"Lista não encontrada: {list_id}") from err
        except ValueError as err:
            raise RSLError("invalid_input", str(err)) from err

    # FR-29, D-040: Recupera a ficha analítica de um artigo
    def get_work_note(self, list_id: str, work_id: str | int) -> dict[str, Any] | None:
        """Recupera a ficha analítica de um artigo, se existir."""
        store, _ = self._build_store()
        try:
            return store.get_note(list_id.strip(), work_id)
        except FileNotFoundError as err:
            raise RSLError("list_not_found", f"Lista não encontrada: {list_id}") from err

    # FR-29, D-040: Lista todas as fichas científicas registradas para a lista
    def list_work_notes(self, list_id: str) -> list[dict[str, Any]]:
        """Lista todas as fichas analíticas da lista informada."""
        store, _ = self._build_store()
        try:
            return store.list_notes(list_id.strip())
        except FileNotFoundError as err:
            raise RSLError("list_not_found", f"Lista não encontrada: {list_id}") from err

    # FR-29, D-040: Exporta todas as fichas em Markdown para Obsidian
    def export_notes_markdown(self, list_id: str) -> Path:
        """Exporta todas as fichas em arquivo Markdown consolidado na pasta de exportações."""
        from rslapp.core.notes import format_notes_compilation
        from rslapp.store._atomic import atomic_write_replace

        store, export_dir = self._build_store()
        notes = self.list_work_notes(list_id)
        if not notes:
            raise RSLError("empty_list", f"Não há fichas científicas salvas para a lista {list_id}.")

        list_data = self.get_list(list_id)
        search_id = list_data.get("search_id")
        query_str = ""
        if search_id:
            try:
                s = store.get_search(search_id)
                query_str = str(s.get("request_summary", ""))
            except (RSLError, FileNotFoundError, ValueError):
                query_str = ""
        if not query_str:
            query_str = list_data.get("query", f"Lista {list_id}")

        md_content = format_notes_compilation(notes, list_id=list_id, list_title=query_str)
        filename = f"notes_{list_id}.md"
        dest_path = export_dir / filename
        atomic_write_replace(dest_path, md_content)
        return dest_path

    # FR-30, D-041: Gestão de Protocolos Metodológicos Pré-Busca
    def save_protocol(self, protocol_data: dict[str, Any]) -> dict[str, Any]:
        """Salva ou atualiza um protocolo de pesquisa estruturado com versionamento automático."""
        store, _ = self._build_store()
        try:
            return store.save_protocol(protocol_data)
        except (ValueError, TypeError) as err:
            raise RSLError("invalid_input", str(err)) from err

    def get_protocol(self, protocol_id: str, version: int | None = None) -> dict[str, Any] | None:
        """Recupera um protocolo metodológico atual ou versão específica."""
        store, _ = self._build_store()
        return store.get_protocol(protocol_id, version=version)

    def list_protocols(self) -> list[dict[str, Any]]:
        """Lista todos os protocolos cadastrados ordenados por atualização."""
        store, _ = self._build_store()
        return store.list_protocols()

    def delete_protocol(self, protocol_id: str) -> bool:
        """Remove um protocolo e seu histórico de versões."""
        store, _ = self._build_store()
        return store.delete_protocol(protocol_id)

    def export_protocol_markdown(self, protocol_id: str, version: int | None = None) -> Path:
        """Exporta o protocolo metodológico completo em Markdown para a pasta de exportações."""
        from rslapp.core.protocols import format_protocol_markdown
        from rslapp.store._atomic import atomic_write_replace

        store, export_dir = self._build_store()
        protocol = store.get_protocol(protocol_id, version=version)
        if not protocol:
            raise RSLError("invalid_input", f"Protocolo {protocol_id} não encontrado.")

        md_content = format_protocol_markdown(protocol)
        v = protocol.get("version", 1)
        filename = f"protocol_{protocol_id}_v{v}.md"
        dest_path = export_dir / filename
        atomic_write_replace(dest_path, md_content)
        return dest_path

    # FR-31, D-042: Exporta redes bibliométricas nativas (VOSviewer e Gephi)
    def export_network(
        self,
        list_id: str,
        network_type: str = "coauthorship",
        fmt: str = "vosviewer",
        *,
        min_node_weight: int = 1,
        min_edge_weight: int = 1,
        max_nodes: int = 500,
    ) -> dict[str, Any]:
        """Extrai e exporta a rede bibliométrica da lista para a pasta de exportações."""
        from rslapp.core.network import (
            extract_bibliometric_network,
            format_gephi_gexf,
            format_vosviewer_map,
            format_vosviewer_network,
        )
        from rslapp.store._atomic import atomic_write_replace

        _store, export_dir = self._build_store()
        list_data = self.get_list(list_id)
        works = list_data.get("works", [])
        if not works:
            raise RSLError("empty_list", f"A lista {list_id} está vazia.")

        net = extract_bibliometric_network(
            works,
            network_type,
            min_node_weight=min_node_weight,
            min_edge_weight=min_edge_weight,
            max_nodes=max_nodes,
        )

        res: dict[str, Any] = {
            "network_type": network_type,
            "format": fmt,
            "total_nodes": net["total_nodes"],
            "total_edges": net["total_edges"],
        }

        if fmt == "vosviewer":
            map_name = f"network_{list_id}_{network_type}.map"
            net_name = f"network_{list_id}_{network_type}.network"
            map_path = export_dir / map_name
            net_path = export_dir / net_name
            atomic_write_replace(map_path, format_vosviewer_map(net["nodes"]))
            atomic_write_replace(net_path, format_vosviewer_network(net["edges"]))
            res["map_file"] = map_name
            res["network_file"] = net_name
            res["map_path"] = map_path
            res["network_path"] = net_path
        elif fmt == "gephi":
            gexf_name = f"network_{list_id}_{network_type}.gexf"
            gexf_path = export_dir / gexf_name
            atomic_write_replace(
                gexf_path,
                format_gephi_gexf(
                    net["nodes"],
                    net["edges"],
                    title=f"RSL.app {network_type} - {list_id}",
                ),
            )
            res["gexf_file"] = gexf_name
            res["gexf_path"] = gexf_path

        return res

