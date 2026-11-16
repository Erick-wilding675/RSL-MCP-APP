"""Testes das telas Histórico e Configurações com o fixture user do NiceGUI 4 (FR-17, FR-18, FR-11, FR-13, NFR-03, D-023, D-026)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from nicegui import ui
from nicegui.testing import User

from rslapp.core.errors import RSLError
from rslapp.desktop.app import register_pages
from rslapp.desktop.pages import history
from rslapp.desktop.settings import (
    ALLOWED_VARS,
    DesktopSettings,
    apply_to_environ,
    capture_system_env_vars,
    load_settings,
    save_settings,
)


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


# D-031, FR-17: Histórico com data curta, paginação de 25, selos de fontes e novo cabeçalho
async def test_d031_fr17_historico_componentes_e_formato_data(
    user: User,
) -> None:
    fake_service = FakeHistoryService(
        searches=[
            {
                "id": "s-0100",
                "list_id": "l-0100",
                "created_at": "2026-11-16T14:25:00Z",
                "kind": "terms",
                "request_summary": "app desktop",
                "params": {
                    "query": "machine learning AND bibliometrics",
                    "max_results": 20,
                    "sources": ["openalex", "europe_pmc"],
                    "include_peer_review": False,
                },
                "sources": [
                    {
                        "name": "openalex",
                        "status": "ok",
                        "reason": None,
                        "found": 15,
                        "fetched": 15,
                    },
                    {
                        "name": "europe_pmc",
                        "status": "ok",
                        "reason": None,
                        "found": 5,
                        "fetched": 5,
                    },
                ],
            }
        ]
    )
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/historico")
    await user.should_see("1 buscas registradas")
    table = user.find(marker="history-table").elements.pop()
    assert table.props.get("pagination", {}).get("rowsPerPage") == 25
    assert len(table.rows) == 1
    row = table.rows[0]
    assert row["date_short"] == "16/11/2026 14:25"
    assert row["created_at"] == "2026-11-16T14:25:00Z"
    assert row["sources_list"] == ["OpenAlex", "Europe PMC"]


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


def _clear_desktop_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove do os.environ todas as variáveis gerenciadas pelo app desktop antes do teste."""
    for var in ALLOWED_VARS:
        monkeypatch.delenv(var, raising=False)


def _assert_secret_absent_from_page(user: User, secret: str) -> None:
    """Garante que o texto da chave não está em nenhum elemento, propriedade ou notificação da página."""
    assert user.client is not None
    for elem in user.client.elements.values():
        for item in elem._displayed_contents(only_visible=False):
            assert secret not in str(item)
        if hasattr(elem, "value") and elem.value is not None:
            assert secret not in str(elem.value)
        assert secret not in repr(elem._props)


# FR-18, D-023, D-026, NFR-03: Salvar uma chave grava no arquivo, aplica no ambiente e nunca mostra a chave na página
async def test_fr18_d026_nfr03_configuracoes_salvar_chave_grava_aplica_e_nao_expoe_na_pagina(
    user: User,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _clear_desktop_env(monkeypatch)
    cfg_file = tmp_path / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))
    capture_system_env_vars()

    register_pages(service=FakeHistoryService())  # type: ignore[arg-type]

    await user.open("/configuracoes")
    await user.should_see("Configurações")
    await user.should_see("https://openalex.org/settings/api")
    await user.should_see("https://www.semanticscholar.org/product/api#api-key-form")
    await user.should_see("página de configurações da conta do NCBI")
    await user.should_see("https://dev.elsevier.com/apikey/manage")
    await user.should_see("https://developer.clarivate.com/apis/wos-starter")
    await user.should_see("só funcionam com a assinatura de quem usa ou da instituição")
    await user.should_see(
        "trocá-la faz o app e o Claude Desktop olharem pastas diferentes"
    )

    oa_status = user.find(marker="status-OPENALEX_API_KEY").elements.pop()
    assert oa_status.text == "não configurada"

    secret_key = "segredo-super-confidencial-oa-9999"
    user.find(marker="input-OPENALEX_API_KEY").type(secret_key)
    user.find(marker="input-RSL_CONTACT_EMAIL").type("pesquisador@universidade.br")
    user.find(marker="save-settings").click()

    # 1. Gravou no arquivo e aplicou no ambiente do processo
    saved = load_settings()
    assert saved.values["OPENALEX_API_KEY"] == secret_key
    assert saved.values["RSL_CONTACT_EMAIL"] == "pesquisador@universidade.br"
    assert os.environ.get("OPENALEX_API_KEY") == secret_key
    assert os.environ.get("RSL_CONTACT_EMAIL") == "pesquisador@universidade.br"

    # 2. Mostra "salvo", o caminho do arquivo e atualiza situação para "configurada"
    await user.should_see("salvo")
    await user.should_see(str(cfg_file))
    oa_status = user.find(marker="status-OPENALEX_API_KEY").elements.pop()
    assert oa_status.text == "configurada"

    # 3. Depois de salvar, o valor da chave não aparece em nenhum elemento da página
    await user.should_not_see(secret_key)
    _assert_secret_absent_from_page(user, secret_key)

    # 4. Mesmo reabrindo a tela de configurações, o campo continua vazio e a chave não aparece
    await user.open("/configuracoes")
    await user.should_not_see(secret_key)
    _assert_secret_absent_from_page(user, secret_key)
    oa_status_reopened = user.find(marker="status-OPENALEX_API_KEY").elements.pop()
    assert oa_status_reopened.text == "configurada"


# FR-18, D-026, NFR-03: Botão "Remover" apaga a chave do arquivo e de os.environ
async def test_fr18_d026_nfr03_configuracoes_remover_apaga_chave(
    user: User,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _clear_desktop_env(monkeypatch)
    cfg_file = tmp_path / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))
    capture_system_env_vars()

    secret_s2 = "chave-s2-para-remover-7777"
    initial = DesktopSettings(values={"SEMANTIC_SCHOLAR_API_KEY": secret_s2})
    save_settings(initial)
    apply_to_environ(initial)
    assert os.environ.get("SEMANTIC_SCHOLAR_API_KEY") == secret_s2

    register_pages(service=FakeHistoryService())  # type: ignore[arg-type]

    await user.open("/configuracoes")
    await user.should_not_see(secret_s2)
    _assert_secret_absent_from_page(user, secret_s2)

    s2_status = user.find(marker="status-SEMANTIC_SCHOLAR_API_KEY").elements.pop()
    assert s2_status.text == "configurada"

    user.find(marker="remove-SEMANTIC_SCHOLAR_API_KEY").click()

    assert "SEMANTIC_SCHOLAR_API_KEY" not in load_settings().values
    assert secret_s2 not in cfg_file.read_text(encoding="utf-8")
    assert "SEMANTIC_SCHOLAR_API_KEY" not in os.environ
    assert s2_status.text == "não configurada"


# FR-18, D-026, NFR-03: Variável vinda do ambiente do sistema não é sobrescrita e aparece como "definida no sistema"
async def test_fr18_d026_nfr03_configuracoes_variavel_do_sistema_nao_sobrescrita(
    user: User,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _clear_desktop_env(monkeypatch)
    cfg_file = tmp_path / "desktop.json"
    monkeypatch.setenv("RSL_DESKTOP_CONFIG", str(cfg_file))

    sys_secret = "chave-sistema-intocavel-5555"
    monkeypatch.setenv("OPENALEX_API_KEY", sys_secret)
    monkeypatch.setenv("RSL_CONTACT_EMAIL", "sistema@instituicao.br")
    capture_system_env_vars()

    register_pages(service=FakeHistoryService())  # type: ignore[arg-type]

    await user.open("/configuracoes")
    await user.should_see("definida no sistema; o valor do sistema vale")
    await user.should_not_see(sys_secret)
    _assert_secret_absent_from_page(user, sys_secret)

    oa_status = user.find(marker="status-OPENALEX_API_KEY").elements.pop()
    assert oa_status.text == "definida no sistema; o valor do sistema vale"

    # Tenta sobrescrever pelo campo e salvar, além de acionar Remover
    attempted_key = "chave-nova-tentativa-sobrescrever-1111"
    user.find(marker="input-OPENALEX_API_KEY").type(attempted_key)
    user.find(marker="save-settings").click()

    assert os.environ.get("OPENALEX_API_KEY") == sys_secret
    assert os.environ.get("RSL_CONTACT_EMAIL") == "sistema@instituicao.br"
    assert "OPENALEX_API_KEY" not in load_settings().values
    await user.should_not_see(attempted_key)
    await user.should_not_see(sys_secret)
    _assert_secret_absent_from_page(user, attempted_key)
    _assert_secret_absent_from_page(user, sys_secret)

    user.find(marker="remove-OPENALEX_API_KEY").click()
    assert os.environ.get("OPENALEX_API_KEY") == sys_secret
    assert oa_status.text == "definida no sistema; o valor do sistema vale"
