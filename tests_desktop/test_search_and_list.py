"""Testes das telas Buscar e Lista com o fixture user do NiceGUI 4 e DesktopService falso (FR-16, FR-06, FR-08, FR-12, D-022, D-025)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from nicegui import ui
from nicegui.testing import User

from rslapp.core.errors import RSLError
from rslapp.desktop.app import register_pages
from rslapp.desktop.pages import list_view


class FakeDesktopService:
    """Serviço falso para injetar em register_pages(service=...) nos testes das telas."""

    def __init__(
        self,
        *,
        paid_configured: bool = False,
        search_error: RSLError | None = None,
        lists: dict[str, dict[str, Any]] | None = None,
        searches: list[dict[str, Any]] | None = None,
        export_dir: Path | None = None,
    ) -> None:
        self.paid_configured = paid_configured
        self.search_error = search_error
        self.lists: dict[str, dict[str, Any]] = lists if lists is not None else {}
        self.searches: list[dict[str, Any]] = searches if searches is not None else []
        self.export_dir = export_dir or Path("/tmp/rsl_exports")
        self.search_calls: list[dict[str, Any]] = []
        self.export_calls: list[tuple[str, str]] = []

    def list_sources(self) -> list[dict[str, Any]]:
        paid_status = "ok" if self.paid_configured else "missing_key"
        return [
            {"name": "openalex", "configured": True, "needs_key": True, "status": "ok"},
            {"name": "crossref", "configured": True, "needs_key": False, "status": "ok"},
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
            {"name": "pubmed", "configured": True, "needs_key": False, "status": "ok"},
            {
                "name": "scopus",
                "configured": self.paid_configured,
                "needs_key": True,
                "status": paid_status,
            },
            {
                "name": "web_of_science",
                "configured": self.paid_configured,
                "needs_key": True,
                "status": paid_status,
            },
        ]

    async def search(
        self,
        query: str,
        sources: list[str] | None = None,
        max_results: int = 100,
        include_peer_review: bool = False,
    ) -> dict[str, Any]:
        self.search_calls.append(
            {
                "query": query,
                "sources": sources,
                "max_results": max_results,
                "include_peer_review": include_peer_review,
            }
        )
        if self.search_error is not None:
            raise self.search_error

        list_id = "l-0001"
        search_id = "s-0001"
        works = [
            {
                "title": "Deep Learning in Systematic Reviews",
                "doi": "10.1000/dl-rsl-2025",
                "year": 2025,
                "venue": "Journal of Informetrics",
                "authors": [
                    {"name": "Ada Lovelace"},
                    {"name": "Alan Turing"},
                    {"name": "Grace Hopper"},
                    {"name": "Margaret Hamilton"},
                ],
                "source_ids": {"openalex": "W1", "crossref": "10.1000/dl-rsl-2025"},
            },
            {
                "title": "Bibliometric Mapping with VOSviewer",
                "doi": None,
                "year": 2024,
                "venue": "Scientometrics",
                "authors": [{"name": "Nees Jan van Eck"}],
                "source_ids": {"semantic_scholar": "S2"},
            },
        ]
        search_entry = {
            "id": search_id,
            "list_id": list_id,
            "created_at": "2026-11-15T10:00:00Z",
            "kind": "terms",
            "request_summary": "app desktop",
            "params": {
                "query": query,
                "max_results": max_results,
                "sources": sources or [],
                "include_peer_review": include_peer_review,
            },
            "sources": [
                {
                    "name": "openalex",
                    "status": "ok",
                    "reason": None,
                    "found": 10,
                    "fetched": 1,
                },
                {
                    "name": "crossref",
                    "status": "ok",
                    "reason": None,
                    "found": 5,
                    "fetched": 1,
                },
                {
                    "name": "semantic_scholar",
                    "status": "ok",
                    "reason": None,
                    "found": 3,
                    "fetched": 1,
                },
            ],
        }
        self.searches.append(search_entry)
        self.lists[list_id] = {
            "id": list_id,
            "search_id": search_id,
            "created_at": "2026-11-15T10:00:00Z",
            "status": "complete",
            "total": 2,
            "works": works,
        }
        return {
            "search_id": search_id,
            "list_id": list_id,
            "status": "complete",
            "total": 2,
            "sources": search_entry["sources"],
            "works": works,
        }

    def get_list(self, list_id: str) -> dict[str, Any]:
        if list_id not in self.lists:
            raise RSLError("list_not_found", f"Lista não encontrada: {list_id}")
        return self.lists[list_id]

    def get_search(self, search_id: str) -> dict[str, Any]:
        for item in self.searches:
            if item.get("id") == search_id:
                return item
        raise RSLError("search_not_found", f"Busca não encontrada: {search_id}")

    def list_searches(self) -> list[dict[str, Any]]:
        return list(self.searches)

    def export(self, list_id: str, export_format: str) -> dict[str, Any]:
        if list_id not in self.lists:
            raise RSLError("list_not_found", f"Lista não encontrada: {list_id}")
        self.export_calls.append((list_id, export_format))
        ext = "bib" if export_format == "bibtex" else ("txt" if export_format == "dois" else export_format)
        out_path = self.export_dir / f"{list_id}.{ext}"
        return {"path": str(out_path), "format": export_format, "count": 2}


# FR-16, D-022, D-025: Busca preenchida chama o serviço, navega para /lista/{list_id} e mostra os títulos na tabela
async def test_fr16_d022_d025_busca_preenchida_navega_e_mostra_titulos(
    user: User,
) -> None:
    fake_service = FakeDesktopService()
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/")
    await user.should_see("A string vai como está para cada base")
    await user.should_see("saúde e ciências da vida")

    user.find(marker="query-input").type("systematic review AND bibliometrics")
    user.find(marker="include-peer-review").click()
    user.find(marker="search-button").click()

    await user.should_see("Lista")
    await user.should_see("String de busca: systematic review AND bibliometrics")
    await user.should_see("Total de artigos: 2")
    await user.should_see("OpenAlex (openalex): 1 resultados")

    assert len(fake_service.search_calls) == 1
    assert fake_service.search_calls[0] == {
        "query": "systematic review AND bibliometrics",
        "sources": ["openalex", "crossref", "semantic_scholar"],
        "max_results": 100,
        "include_peer_review": True,
    }

    await user.should_see(ui.table)
    table = user.find(ui.table).elements.pop()
    assert table.pagination == {"rowsPerPage": 25}
    titles = [row["title"] for row in table.rows]
    assert titles == [
        "Deep Learning in Systematic Reviews",
        "Bibliometric Mapping with VOSviewer",
    ]
    # Três primeiros autores + et al.
    assert (
        table.rows[0]["authors"]
        == "Ada Lovelace, Alan Turing, Grace Hopper et al."
    )
    assert table.rows[0]["doi"] == "10.1000/dl-rsl-2025"
    assert table.rows[0]["doi_url"] == "https://doi.org/10.1000/dl-rsl-2025"
    assert table.rows[0]["sources"] == "OpenAlex, Crossref"
    assert table.rows[1]["authors"] == "Nees Jan van Eck"
    assert table.rows[1]["doi_url"] == ""


# FR-16: String vazia avisa com ui.notify e não chama service.search
async def test_fr16_string_vazia_avisa_sem_chamar_servico(user: User) -> None:
    fake_service = FakeDesktopService()
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/")
    user.find(marker="search-button").click()

    await user.should_see("Informe a string de busca.")
    assert fake_service.search_calls == []


# FR-16, NFR-03: RSLError durante a busca mostra a mensagem em notificação e reabilita o formulário
async def test_fr16_nfr03_rsl_error_mostra_mensagem_e_reabilita_formulario(
    user: User,
) -> None:
    fake_service = FakeDesktopService(
        search_error=RSLError(
            "no_source_available",
            "nenhuma fonte pode responder; configure OPENALEX_API_KEY",
        )
    )
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/")
    user.find(marker="query-input").type("machine learning")
    user.find(marker="search-button").click()

    await user.should_see("nenhuma fonte pode responder; configure OPENALEX_API_KEY")
    assert len(fake_service.search_calls) == 1
    search_btn = user.find(marker="search-button").elements.pop()
    assert search_btn.enabled is True


# FR-16, D-023, D-025: Fontes pagas sem chave aparecem desabilitadas e com link para Configurações
async def test_fr16_d023_fontes_pagas_sem_chave_aparecem_desabilitadas(
    user: User,
) -> None:
    fake_service = FakeDesktopService(paid_configured=False)
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/")
    await user.should_see("configure a chave em Configurações")

    scopus_cb = user.find(marker="source-scopus").elements.pop()
    wos_cb = user.find(marker="source-web_of_science").elements.pop()
    oa_cb = user.find(marker="source-openalex").elements.pop()
    pubmed_cb = user.find(marker="source-pubmed").elements.pop()

    assert scopus_cb.enabled is False
    assert scopus_cb.value is False
    assert wos_cb.enabled is False
    assert wos_cb.value is False
    assert oa_cb.enabled is True
    assert oa_cb.value is True
    assert pubmed_cb.enabled is True
    assert pubmed_cb.value is False


# FR-08, FR-16: Lista incompleta mostra aviso visível com cada fonte que falhou e o motivo
async def test_fr08_fr16_lista_incompleta_mostra_aviso_com_fonte_e_motivo(
    user: User,
) -> None:
    fake_service = FakeDesktopService(
        lists={
            "l-0002": {
                "id": "l-0002",
                "search_id": "s-0002",
                "created_at": "2026-11-15T11:00:00Z",
                "status": "incomplete",
                "total": 1,
                "works": [
                    {
                        "title": "Partial Results Study",
                        "doi": "10.1000/partial",
                        "year": 2023,
                        "venue": "PLOS ONE",
                        "authors": [{"name": "Marie Curie"}],
                        "source_ids": {"openalex": "W2"},
                    }
                ],
            }
        },
        searches=[
            {
                "id": "s-0002",
                "list_id": "l-0002",
                "created_at": "2026-11-15T11:00:00Z",
                "kind": "terms",
                "request_summary": "app desktop",
                "params": {
                    "query": "radium isotopes",
                    "max_results": 100,
                    "sources": ["openalex", "semantic_scholar"],
                    "include_peer_review": False,
                },
                "sources": [
                    {
                        "name": "openalex",
                        "status": "ok",
                        "reason": None,
                        "found": 1,
                        "fetched": 1,
                    },
                    {
                        "name": "semantic_scholar",
                        "status": "rate_limited",
                        "reason": "HTTP 429 rate limit exceeded",
                        "found": None,
                        "fetched": 0,
                    },
                ],
            }
        ],
    )
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/lista/l-0002")
    await user.should_see("Aviso: lista incompleta")
    await user.should_see(
        "Semantic Scholar (semantic_scholar): HTTP 429 rate limit exceeded"
    )


# FR-06, FR-12, FR-16: Botão de exportar chama o serviço com o formato certo e mostra o caminho; Abrir pasta não usa shell=True
async def test_fr06_fr12_fr16_exportar_mostra_caminho_e_abrir_pasta(
    user: User,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_service = FakeDesktopService(
        export_dir=tmp_path,
        lists={
            "l-0003": {
                "id": "l-0003",
                "search_id": "s-0003",
                "created_at": "2026-11-15T12:00:00Z",
                "status": "complete",
                "total": 1,
                "works": [
                    {
                        "title": "Exportable Paper",
                        "doi": "10.1000/exp-1",
                        "year": 2025,
                        "venue": "Scientometrics",
                        "authors": [{"name": "Paul Otlet"}],
                        "source_ids": {"openalex": "W3"},
                    }
                ],
            }
        },
        searches=[
            {
                "id": "s-0003",
                "list_id": "l-0003",
                "created_at": "2026-11-15T12:00:00Z",
                "kind": "terms",
                "request_summary": "app desktop",
                "params": {
                    "query": "bibliometrics",
                    "max_results": 100,
                    "sources": ["openalex"],
                    "include_peer_review": False,
                },
                "sources": [
                    {
                        "name": "openalex",
                        "status": "ok",
                        "reason": None,
                        "found": 1,
                        "fetched": 1,
                    }
                ],
            }
        ],
    )
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/lista/l-0003")
    user.find(marker="export-ris").click()

    expected_ris = str(tmp_path / "l-0003.ris")
    await user.should_see(expected_ris)
    assert fake_service.export_calls == [("l-0003", "ris")]

    user.find(marker="export-bibtex").click()
    expected_bib = str(tmp_path / "l-0003.bib")
    await user.should_see(expected_bib)
    assert fake_service.export_calls == [("l-0003", "ris"), ("l-0003", "bibtex")]

    opened_folders: list[Path] = []
    monkeypatch.setattr(
        list_view,
        "open_folder_in_file_manager",
        lambda folder: opened_folders.append(folder),
    )
    user.find(marker="open-export-folder").click()
    assert opened_folders == [tmp_path]


# FR-16, FR-05: Lista cuja busca tem request_summary="app desktop" mostra params.query e nunca o texto "app desktop"
async def test_fr16_fr05_lista_mostra_params_query_e_nunca_request_summary(
    user: User,
) -> None:
    fake_service = FakeDesktopService(
        lists={
            "l-0004": {
                "id": "l-0004",
                "search_id": "s-0004",
                "created_at": "2026-11-15T13:00:00Z",
                "status": "complete",
                "total": 1,
                "works": [
                    {
                        "title": "Reproducible Science Study",
                        "doi": "10.1000/repro-1",
                        "year": 2025,
                        "venue": "Nature",
                        "authors": [{"name": "Rosalind Franklin"}],
                        "source_ids": {"openalex": "W4"},
                    }
                ],
            },
            "l-0005": {
                "id": "l-0005",
                "search_id": "s-0005",
                "created_at": "2026-11-15T14:00:00Z",
                "status": "complete",
                "total": 1,
                "works": [
                    {
                        "title": "Merged Work",
                        "doi": "10.1000/merge-1",
                        "year": 2024,
                        "venue": "Science",
                        "authors": [{"name": "Barbara McClintock"}],
                        "source_ids": {"openalex": "W5"},
                    }
                ],
            },
        },
        searches=[
            {
                "id": "s-0004",
                "list_id": "l-0004",
                "created_at": "2026-11-15T13:00:00Z",
                "kind": "terms",
                "request_summary": "app desktop",
                "params": {
                    "query": "open science AND reproducibility",
                    "max_results": 50,
                    "sources": ["openalex"],
                    "include_peer_review": False,
                },
                "sources": [
                    {
                        "name": "openalex",
                        "status": "ok",
                        "reason": None,
                        "found": 1,
                        "fetched": 1,
                    }
                ],
            },
            {
                "id": "s-0005",
                "list_id": "l-0005",
                "created_at": "2026-11-15T14:00:00Z",
                "kind": "merge",
                "request_summary": "app desktop",
                "params": {"list_ids": ["l-0001", "l-0002"]},
                "sources": [],
            },
        ],
    )
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/lista/l-0004")
    await user.should_see("String de busca: open science AND reproducibility")
    await user.should_see("Data: 2026-11-15T13:00:00Z")
    await user.should_see("OpenAlex (openalex): 1 resultados")
    await user.should_not_see("app desktop")

    await user.open("/lista/l-0005")
    await user.should_see("String de busca: —")
    await user.should_not_see("app desktop")


# FR-16: list_id inexistente mostra "lista não encontrada" e link para Buscar
async def test_fr16_list_id_inexistente_mostra_lista_nao_encontrada(
    user: User,
) -> None:
    fake_service = FakeDesktopService()
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/lista/l-9999")
    await user.should_see("lista não encontrada")
    await user.should_see(marker="back-to-search")


# FR-06, FR-16: open_folder_in_file_manager usa os.startfile no Windows e xdg-open sem shell=True no Linux
def test_fr06_fr16_open_folder_in_file_manager_windows_e_linux(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "exports"

    startfile_calls: list[str] = []
    monkeypatch.setattr(list_view.sys, "platform", "win32")
    monkeypatch.setattr(
        list_view.os,
        "startfile",
        lambda p: startfile_calls.append(p),
        raising=False,
    )
    list_view.open_folder_in_file_manager(target)
    assert target.is_dir()
    assert startfile_calls == [str(target)]

    subprocess_calls: list[tuple[Any, dict[str, Any]]] = []
    monkeypatch.setattr(list_view.sys, "platform", "linux")
    monkeypatch.setattr(
        list_view.subprocess,
        "run",
        lambda args, **kwargs: subprocess_calls.append((args, kwargs)),
    )
    list_view.open_folder_in_file_manager(target)
    assert subprocess_calls == [
        (["xdg-open", str(target)], {"check": False}),
    ]

