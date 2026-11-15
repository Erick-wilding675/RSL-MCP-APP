"""Testes das telas Histórico e Configurações com o fixture user do NiceGUI 4 (FR-17, FR-18, FR-11, FR-13, NFR-03, D-023, D-026)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from nicegui import ui
from nicegui.testing import User

from rslapp.core.errors import RSLError
from rslapp.desktop.app import register_pages
from rslapp.desktop.pages import history


class FakeHistoryService:
    """Serviço falso para testar a tela Histórico via register_pages(service=...)."""

    def __init__(
        self,
        *,
        lists: dict[str, dict[str, Any]] | None = None,
        searches: list[dict[str, Any]] | None = None,
        log_file: Path | None = None,
        repeat_error: RSLError | None = None,
    ) -> None:
        self.lists: dict[str, dict[str, Any]] = lists if lists is not None else {}
        self.searches: list[dict[str, Any]] = searches if searches is not None else []
        self._log_file = log_file or Path("/tmp/nonexistent_rsl_log.md")
        self.repeat_error = repeat_error
        self.repeat_calls: list[str] = []

    def list_sources(self) -> list[dict[str, Any]]:
        return [
            {"name": "openalex", "configured": True, "needs_key": True, "status": "ok"},
            {"name": "crossref", "configured": True, "needs_key": False, "status": "ok"},
            {
                "name": "semantic_scholar",
                "configured": True,
                "needs_key": False,
                "status": "ok",
            },
        ]

    def list_searches(self) -> list[dict[str, Any]]:
        return list(self.searches)

    def get_list(self, list_id: str) -> dict[str, Any]:
        if list_id not in self.lists:
            raise RSLError("list_not_found", f"Lista não encontrada: {list_id}")
        return self.lists[list_id]

    def get_search(self, search_id: str) -> dict[str, Any]:
        for item in self.searches:
            if item.get("id") == search_id:
                return item
        raise RSLError("search_not_found", f"Busca não encontrada: {search_id}")

    async def repeat(self, search_id: str) -> dict[str, Any]:
        self.repeat_calls.append(search_id)
        if self.repeat_error is not None:
            raise self.repeat_error

        new_list_id = "l-0003"
        new_search_id = "s-0003"
        works = [
            {
                "title": "Repeated Systematic Review Article",
                "doi": "10.1000/repeat-2026",
                "year": 2026,
                "venue": "Scientometrics",
                "authors": [{"name": "Eugene Garfield"}],
                "source_ids": {"openalex": "W300"},
            }
        ]
        new_search = {
            "id": new_search_id,
            "list_id": new_list_id,
            "created_at": "2026-11-15T15:00:00Z",
            "kind": "repeat",
            "repeated_from": search_id,
            "request_summary": "app desktop",
            "params": {
                "query": "bibliometric networks AND co-citation",
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
        }
        self.searches.append(new_search)
        self.lists[new_list_id] = {
            "id": new_list_id,
            "search_id": new_search_id,
            "created_at": "2026-11-15T15:00:00Z",
            "status": "complete",
            "total": 1,
            "works": works,
        }
        return {
            "search_id": new_search_id,
            "list_id": new_list_id,
            "repeated_from": search_id,
            "status": "complete",
            "total": 1,
            "sources": new_search["sources"],
            "works": works,
        }

    def log_path(self) -> Path:
        return self._log_file


# FR-17, FR-11: Histórico lista as buscas da mais recente para a mais antiga, corta string em 80 chars, "Ver lista" e "Repetir" navegam
async def test_fr17_fr11_historico_lista_buscas_e_repetir_chama_servico_e_navega(
    user: User,
) -> None:
    long_query = (
        '("systematic literature review" OR "scoping review") '
        'AND ("bibliometric analysis" OR "science mapping" OR "VOSviewer")'
    )
    assert len(long_query) > 80

    fake_service = FakeHistoryService(
        lists={
            "l-0001": {
                "id": "l-0001",
                "search_id": "s-0001",
                "created_at": "2026-11-15T09:00:00Z",
                "status": "complete",
                "total": 14,
                "works": [
                    {
                        "title": "First Saved Paper",
                        "doi": "10.1000/first",
                        "year": 2024,
                        "venue": "JASIST",
                        "authors": [{"name": "Derek J. de Solla Price"}],
                        "source_ids": {"openalex": "W1"},
                    }
                ],
            },
            "l-0002": {
                "id": "l-0002",
                "search_id": "s-0002",
                "created_at": "2026-11-15T12:30:00Z",
                "status": "incomplete",
                "total": 7,
                "works": [],
            },
        },
        searches=[
            {
                "id": "s-0001",
                "list_id": "l-0001",
                "created_at": "2026-11-15T09:00:00Z",
                "kind": "terms",
                "request_summary": "app desktop",
                "params": {
                    "query": long_query,
                    "max_results": 100,
                    "sources": ["openalex", "crossref"],
                    "include_peer_review": False,
                },
                "sources": [
                    {
                        "name": "openalex",
                        "status": "ok",
                        "reason": None,
                        "found": 10,
                        "fetched": 10,
                    },
                    {
                        "name": "crossref",
                        "status": "ok",
                        "reason": None,
                        "found": 8,
                        "fetched": 8,
                    },
                ],
            },
            {
                "id": "s-0002",
                "list_id": "l-0002",
                "created_at": "2026-11-15T12:30:00Z",
                "kind": "terms",
                "request_summary": "app desktop",
                "params": {
                    "query": "bibliometric networks AND co-citation",
                    "max_results": 50,
                    "sources": ["openalex", "semantic_scholar"],
                    "include_peer_review": False,
                },
                "sources": [
                    {
                        "name": "openalex",
                        "status": "ok",
                        "reason": None,
                        "found": 7,
                        "fetched": 7,
                    },
                    {
                        "name": "semantic_scholar",
                        "status": "rate_limited",
                        "reason": "HTTP 429",
                        "found": None,
                        "fetched": 0,
                    },
                ],
            },
        ],
    )
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/historico")
    await user.should_see("Histórico")
    await user.should_see(ui.table)

    table = user.find(marker="history-table").elements.pop()
    assert [row["id"] for row in table.rows] == ["s-0002", "s-0001"]

    # Linha mais recente (s-0002): incompleta, 7 artigos
    row_recent = table.rows[0]
    assert row_recent["created_at"] == "2026-11-15T12:30:00Z"
    assert row_recent["query"] == "bibliometric networks AND co-citation"
    assert row_recent["query_full"] == "bibliometric networks AND co-citation"
    assert row_recent["sources"] == "OpenAlex, Semantic Scholar"
    assert row_recent["total"] == 7
    assert row_recent["incomplete"] == "Sim"
    assert row_recent["is_incomplete"] is True

    # Linha mais antiga (s-0001): completa, 14 artigos (deduplicados da lista), string cortada em 80 chars
    row_older = table.rows[1]
    assert row_older["created_at"] == "2026-11-15T09:00:00Z"
    assert row_older["query"] == f"{long_query[:80]}…"
    assert row_older["query_full"] == long_query
    assert row_older["sources"] == "OpenAlex, Crossref"
    assert row_older["total"] == 14
    assert row_older["incomplete"] == "Não"
    assert row_older["is_incomplete"] is False

    # Ação "Ver lista" navega para /lista/{list_id}
    user.find(marker="view-list-button").trigger("click", "l-0001")
    await user.should_see("Identificador: l-0001")

    # Volta ao histórico e aciona "Repetir"
    await user.open("/historico")
    user.find(marker="repeat-button").trigger("click", "s-0002")

    await user.should_see("Identificador: l-0003")
    await user.should_see("Total de artigos: 1")
    assert fake_service.repeat_calls == ["s-0002"]


# FR-17: Histórico vazio mostra "nenhuma busca ainda" e um link para Buscar
async def test_fr17_historico_vazio_mostra_mensagem_e_link_buscar(
    user: User,
) -> None:
    fake_service = FakeHistoryService(searches=[])
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/historico")
    await user.should_see("nenhuma busca ainda")
    await user.should_see(marker="go-to-search")

    user.find(marker="go-to-search").click()
    await user.should_see("A string vai como está para cada base")


# FR-17, FR-13: Botão "Abrir log" avisa quando log.md não existe e abre sem shell=True quando existe
async def test_fr17_fr13_abrir_log_avisa_ausente_e_abre_sem_shell_true(
    user: User,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    log_file = tmp_path / "log.md"
    fake_service = FakeHistoryService(log_file=log_file)
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/historico")
    user.find(marker="open-log").click()
    await user.should_see("ainda não existe")

    log_file.write_text("## s-0001\n", encoding="utf-8")
    opened_files: list[Path] = []
    monkeypatch.setattr(
        history,
        "open_log_in_default_app",
        lambda path: opened_files.append(path),
    )
    user.find(marker="open-log").click()
    assert opened_files == [log_file]


# FR-17, FR-13: open_log_in_default_app usa os.startfile no Windows e xdg-open sem shell=True no Linux
def test_fr17_fr13_open_log_in_default_app_windows_e_linux(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    log_file = tmp_path / "log.md"
    log_file.write_text("# Log\n", encoding="utf-8")

    startfile_calls: list[str] = []
    monkeypatch.setattr(history.sys, "platform", "win32")
    monkeypatch.setattr(
        history.os,
        "startfile",
        lambda p: startfile_calls.append(p),
        raising=False,
    )
    history.open_log_in_default_app(log_file)
    assert startfile_calls == [str(log_file)]

    subprocess_calls: list[tuple[Any, dict[str, Any]]] = []
    monkeypatch.setattr(history.sys, "platform", "linux")
    monkeypatch.setattr(
        history.subprocess,
        "run",
        lambda args, **kwargs: subprocess_calls.append((args, kwargs)),
    )
    history.open_log_in_default_app(log_file)
    assert subprocess_calls == [
        (["xdg-open", str(log_file)], {"check": False}),
    ]
