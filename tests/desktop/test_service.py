"""Testes do DesktopService (FR-16, FR-17) com fontes falsas e sem importar nicegui."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from rslapp.core.errors import RSLError
from rslapp.core.models import Author, SourceResult, Work
from rslapp.desktop import service as service_mod
from rslapp.desktop.service import DesktopService

ENV_VARS = (
    "RSL_DATA_DIR",
    "RSL_EXPORT_DIR",
    "RSL_CACHE_DAYS",
    "OPENALEX_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "NCBI_API_KEY",
    "SCOPUS_API_KEY",
    "SCOPUS_INSTTOKEN",
    "WOS_STARTER_API_KEY",
    "RSL_CONTACT_EMAIL",
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    data_dir = tmp_path / "rsl_data"
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))
    return data_dir


class FakeDesktopSource:
    """Fonte falsa para testar o serviço do app desktop."""

    def __init__(self, name: str, works: list[Work] | None = None) -> None:
        self.name = name
        self.needs_key = False
        self.works = works if works is not None else []
        self.calls: list[tuple[str, int, bool]] = []

    def cache_query(
        self,
        query: str,
        max_results: int,
        include_peer_review: bool = False,
    ) -> dict[str, Any]:
        return {
            "source": self.name,
            "query": query,
            "max": max_results,
            "pr": include_peer_review,
        }

    async def search(
        self,
        query: str,
        max_results: int,
        include_peer_review: bool = False,
    ) -> SourceResult:
        self.calls.append((query, max_results, include_peer_review))
        return SourceResult(
            name=self.name,
            status="ok",
            query=f"query={query}",
            found=len(self.works),
            fetched=len(self.works),
            works=self.works,
        )


# FR-16, FR-07, D-023: list_sources devolve as 7 fontes no formato do stdio
def test_fr16_d023_service_list_sources_sete_fontes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = DesktopService()
    sources_before = svc.list_sources()
    assert [s["name"] for s in sources_before] == [
        "openalex",
        "crossref",
        "semantic_scholar",
        "europe_pmc",
        "pubmed",
        "scopus",
        "web_of_science",
    ]
    assert sources_before[0]["status"] == "missing_key"
    assert sources_before[5]["status"] == "missing_key"

    monkeypatch.setenv("OPENALEX_API_KEY", "fake-oa")
    monkeypatch.setenv("SCOPUS_API_KEY", "fake-scopus")
    sources_after = svc.list_sources()
    assert sources_after[0]["status"] == "ok"
    assert sources_after[5]["status"] == "ok"
    assert "nicegui" not in sys.modules


# FR-16, FR-17: Fluxo de search, get_list, export, list_searches, repeat e log_path
@pytest.mark.anyio
async def test_fr16_fr17_service_search_get_list_export_repeat_e_log(
    monkeypatch: pytest.MonkeyPatch,
    isolated_env: Path,
) -> None:
    work = Work(
        title="Systematic Review Automation",
        doi="10.1000/rsl-desktop-1",
        year=2025,
        venue="Journal of Bibliometrics",
        authors=[Author(name="Ada Lovelace")],
        source_ids={"openalex": "W100"},
    )
    fake_oa = FakeDesktopSource("openalex", works=[work])
    fake_cr = FakeDesktopSource("crossref", works=[])
    monkeypatch.setattr(
        service_mod,
        "build_sources",
        lambda include_paid=True: [fake_oa, fake_cr],
    )

    svc = DesktopService()
    res = await svc.search(
        query="systematic review",
        sources=["openalex"],
        max_results=20,
        include_peer_review=True,
    )
    assert res["total"] == 1
    assert fake_oa.calls == [("systematic review", 20, True)]

    list_id = res["list_id"]
    search_id = res["search_id"]

    # get_list devolve a lista gravada
    saved_list = svc.get_list(list_id)
    assert saved_list["id"] == list_id
    assert saved_list["total"] == 1
    assert saved_list["works"][0]["title"] == "Systematic Review Automation"

    # list_searches devolve a busca com request_summary="app desktop"
    searches = svc.list_searches()
    assert len(searches) == 1
    assert searches[0]["id"] == search_id
    assert searches[0]["request_summary"] == "app desktop"

    # export grava na pasta de exportação configurada
    export_res = svc.export(list_id, "ris")
    exported_path = Path(export_res["path"])
    assert exported_path.is_file()
    assert exported_path.parent == isolated_env / "exports"
    assert "Systematic Review Automation" in exported_path.read_text(encoding="utf-8")

    # repeat repete a busca salva e gera nova entrada
    repeat_res = await svc.repeat(search_id)
    assert repeat_res["repeated_from"] == search_id
    assert repeat_res["search_id"] != search_id
    assert len(svc.list_searches()) == 2

    # log_path aponta para o log.md na pasta de dados
    log_file = svc.log_path()
    assert log_file == isolated_env / "log.md"
    assert log_file.is_file()


# FR-16: Erros do núcleo (RSLError) sobem sem tradução
@pytest.mark.anyio
async def test_fr16_service_propaga_rsl_error() -> None:
    svc = DesktopService()

    with pytest.raises(RSLError) as exc_search:
        await svc.search(query="   ", sources=["openalex"], max_results=10, include_peer_review=False)
    assert exc_search.value.code == "invalid_input"

    with pytest.raises(RSLError) as exc_list:
        svc.get_list("l-9999")
    assert exc_list.value.code == "list_not_found"

    with pytest.raises(RSLError) as exc_export:
        svc.export("l-9999", "ris")
    assert exc_export.value.code == "list_not_found"
