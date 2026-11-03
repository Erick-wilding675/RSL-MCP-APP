"""Testes do miolo de trabalhos relacionados (run_related)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from rslapp.core.errors import RSLError
from rslapp.core.models import Author, SourceResult, Work
from rslapp.core.related import run_related
from rslapp.sources.crossref import CrossrefSource
from rslapp.store import Store


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class FakeRelatedSource:
    """Fonte simulada para testes do miolo sem rede."""

    def __init__(
        self,
        name: str,
        result: SourceResult,
        origin_work_info: tuple[dict[str, Any] | None, str | None, str | None] | None = None,
    ) -> None:
        self.name = name
        self.needs_key = True
        self._result = result
        self._origin_work_info = origin_work_info
        self.related_calls: list[tuple[str, str, int]] = []
        self.origin_calls: list[str] = []

    def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
        return {"query": query, "max_results": max_results}

    async def get_origin_work(
        self, doi_or_id: str
    ) -> tuple[dict[str, Any] | None, str | None, str | None]:
        self.origin_calls.append(doi_or_id)
        if self._origin_work_info is not None:
            return self._origin_work_info
        return {"id": "https://openalex.org/W100", "doi": "https://doi.org/10.1234/test"}, None, None

    async def related(
        self,
        doi_or_id: str,
        direction: str,
        max_results: int = 1000,
        origin_data: dict[str, Any] | None = None,
    ) -> SourceResult:
        self.related_calls.append((doi_or_id, direction, max_results))
        return self._result


# FR-15, UC-04, D-005: Validações de entradas inválidas
@pytest.mark.anyio
async def test_fr15_entradas_invalidas(tmp_path: Path) -> None:
    store = Store(tmp_path)
    src = FakeRelatedSource("openalex", SourceResult(name="openalex", status="ok", query="", found=0, fetched=0, works=[]))

    # direction inválida
    with pytest.raises(RSLError) as exc1:
        await run_related(store, [src], direction="invalid", doi="10.1234/test")
    assert exc1.value.code == "invalid_input"

    # Nenhum nem ambos doi e work_id
    with pytest.raises(RSLError) as exc2:
        await run_related(store, [src], direction="references")
    assert exc2.value.code == "invalid_input"

    with pytest.raises(RSLError) as exc3:
        await run_related(store, [src], direction="references", doi="10.1234/test", work_id="W123")
    assert exc3.value.code == "invalid_input"

    # doi vazio
    with pytest.raises(RSLError) as exc4:
        await run_related(store, [src], direction="references", doi="   ")
    assert exc4.value.code == "invalid_input"

    # work_id vazio
    with pytest.raises(RSLError) as exc5:
        await run_related(store, [src], direction="references", work_id="   ")
    assert exc5.value.code == "invalid_input"

    # max_results fora do intervalo ou bool
    with pytest.raises(RSLError) as exc6:
        await run_related(store, [src], direction="references", doi="10.1234/test", max_results=0)
    assert exc6.value.code == "invalid_input"

    with pytest.raises(RSLError) as exc7:
        await run_related(store, [src], direction="references", doi="10.1234/test", max_results=True)  # type: ignore[arg-type]
    assert exc7.value.code == "invalid_input"


# FR-15, UC-04, D-005: As citações e referências viram lista própria ligada ao artigo de origem no log
@pytest.mark.anyio
@pytest.mark.parametrize("direction,expected_label", [("citations", "citações"), ("references", "referências")])
async def test_fr15_uc04_d005_lista_propria_ligada_ao_artigo_origem(
    tmp_path: Path, direction: str, expected_label: str
) -> None:
    store = Store(tmp_path)
    fake_work = Work(
        title="Related Work Sample",
        doi="10.1234/rel.1",
        year=2023,
        venue="Journal of Testing",
        authors=[Author(name="Alan Turing")],
        citations={"openalex": 10},
        source_ids={"openalex": "W201"},
    )
    oa_res = SourceResult(
        name="openalex",
        status="ok",
        reason=None,
        query="related_test",
        found=1,
        fetched=1,
        works=[fake_work],
    )
    src = FakeRelatedSource(
        "openalex",
        oa_res,
        origin_work_info=({"id": "https://openalex.org/W100", "doi": "https://doi.org/10.1234/origem"}, None, None),
    )

    out = await run_related(
        store,
        [src],
        direction=direction,
        doi="10.1234/origem",
        request_summary="Busca teste",
    )

    assert out["status"] == "complete"
    assert out["total"] == 1
    assert len(out["works"]) == 1
    assert out["works"][0]["title"] == "Related Work Sample"
    list_id = out["list_id"]
    search_id = out["search_id"]

    # Confere gravação da busca em searches/
    saved_search = store.get_search(search_id)
    assert saved_search["kind"] == "related"
    assert saved_search["origin"] == {"work": "10.1234/origem", "direction": direction}
    assert saved_search["params"]["direction"] == direction
    assert saved_search["params"]["doi"] == "10.1234/origem"

    # Confere gravação da lista em lists/
    saved_list = store.get_list(list_id)
    assert saved_list["status"] == "complete"
    assert saved_list["total"] == 1

    # Confere entrada no log.md
    log_text = (tmp_path / "log.md").read_text(encoding="utf-8")
    assert f"Artigo de origem: 10.1234/origem · direção: {expected_label}" in log_text
    assert f"## {search_id} ·" in log_text
    assert expected_label in log_text


# FR-08, FR-15: Crossref aparece como not_supported e Semantic Scholar sem DOI também
@pytest.mark.anyio
async def test_fr08_fr15_crossref_e_s2_sem_doi_not_supported(tmp_path: Path) -> None:
    store = Store(tmp_path)
    crossref = CrossrefSource()

    work1 = Work(
        title="OpenAlex Only Work",
        doi=None,
        year=2021,
        authors=[Author(name="Author One")],
        source_ids={"openalex": "W501"},
    )
    oa_res = SourceResult(
        name="openalex",
        status="ok",
        reason=None,
        query="oa_test",
        found=1,
        fetched=1,
        works=[work1],
    )
    # Artigo de origem sem DOI no OpenAlex
    oa_src = FakeRelatedSource(
        "openalex",
        oa_res,
        origin_work_info=({"id": "https://openalex.org/W100", "doi": None}, None, None),
    )

    s2_res = SourceResult(name="semantic_scholar", status="ok", query="", found=0, fetched=0, works=[])
    s2_src = FakeRelatedSource("semantic_scholar", s2_res)

    out = await run_related(
        store,
        [oa_src, crossref, s2_src],
        direction="references",
        work_id="W100",
    )

    # Crossref e Semantic Scholar devem ser not_supported; lista sai incompleta (FR-08)
    assert out["status"] == "incomplete"
    src_statuses = {s["name"]: s["status"] for s in out["sources"]}
    assert src_statuses["crossref"] == "not_supported"
    assert src_statuses["semantic_scholar"] == "not_supported"
    assert src_statuses["openalex"] == "ok"

    # Nenhum campo é preenchido com valor suposto
    cr_entry = next(s for s in out["sources"] if s["name"] == "crossref")
    assert cr_entry["found"] is None
    assert cr_entry["fetched"] == 0

    s2_entry = next(s for s in out["sources"] if s["name"] == "semantic_scholar")
    assert s2_entry["reason"] == "artigo de origem sem DOI"
    assert s2_entry["found"] is None
    assert s2_entry["fetched"] == 0


# FR-15, D-002: Artigo de origem não achado devolve work_not_found e nada é gravado
@pytest.mark.anyio
async def test_fr15_artigo_origem_nao_achado_work_not_found_nada_gravado(tmp_path: Path) -> None:
    store = Store(tmp_path)
    oa_src = FakeRelatedSource(
        "openalex",
        SourceResult(name="openalex", status="failed", reason="HTTP 404", query="", found=None, fetched=0, works=[]),
        origin_work_info=(None, "failed", "HTTP 404"),
    )
    s2_src = FakeRelatedSource(
        "semantic_scholar",
        SourceResult(name="semantic_scholar", status="failed", reason="HTTP 404", query="", found=None, fetched=0, works=[]),
    )

    # Com DOI inexistente em ambas
    with pytest.raises(RSLError) as exc:
        await run_related(store, [oa_src, s2_src], direction="citations", doi="10.9999/naoexiste")
    assert exc.value.code == "work_not_found"

    # Com work_id inexistente
    with pytest.raises(RSLError) as exc2:
        await run_related(store, [oa_src, s2_src], direction="references", work_id="W9999")
    assert exc2.value.code == "work_not_found"

    # Nada deve ter sido gravado na pasta
    assert not (tmp_path / "searches").exists() or list((tmp_path / "searches").glob("*.json")) == []
    assert not (tmp_path / "lists").exists() or list((tmp_path / "lists").glob("*.json")) == []
    assert not (tmp_path / "log.md").exists()


# FR-04, FR-14: Trabalhos de duas fontes são juntados e deduplicados pela regra da 03-03
@pytest.mark.anyio
async def test_fr04_fr14_juncao_e_deduplicacao_entre_fontes(tmp_path: Path) -> None:
    store = Store(tmp_path)
    # Mesmo artigo vindo do OpenAlex e da Semantic Scholar
    work_oa = Work(
        title="A Universal Paper on AI",
        doi="10.1234/ai.2023",
        year=2023,
        venue="AI Review",
        abstract="Abstract from OpenAlex.",
        authors=[Author(name="Ada Lovelace")],
        citations={"openalex": 50},
        source_ids={"openalex": "W111"},
    )
    work_s2 = Work(
        title="A Universal Paper on AI",
        doi="10.1234/ai.2023",
        year=2023,
        venue="AI Review",
        abstract=None,
        authors=[Author(name="Ada Lovelace")],
        citations={"semantic_scholar": 45},
        source_ids={"semantic_scholar": "s2-111"},
    )

    oa_src = FakeRelatedSource(
        "openalex",
        SourceResult(name="openalex", status="ok", query="oa", found=1, fetched=1, works=[work_oa]),
        origin_work_info=({"id": "https://openalex.org/W100", "doi": "https://doi.org/10.1234/ai.2023"}, None, None),
    )
    s2_src = FakeRelatedSource(
        "semantic_scholar",
        SourceResult(name="semantic_scholar", status="ok", query="s2", found=1, fetched=1, works=[work_s2]),
    )

    out = await run_related(
        store,
        [oa_src, s2_src],
        direction="citations",
        doi="10.1234/ai.2023",
    )

    assert out["status"] == "complete"
    assert out["total"] == 1  # Deduplicado para 1 artigo
    assert len(out["works"]) == 1
    merged_work = out["works"][0]
    assert merged_work["citations"] == {"openalex": 50, "semantic_scholar": 45}

    # Verifica metadados de junção
    saved_search = store.get_search(out["search_id"])
    assert saved_search["merge"]["merged"] == 1


# D-010: Quando trabalhos passam do teto, lista sai incomplete com o motivo
@pytest.mark.anyio
async def test_d010_teto_incompleta_com_motivo(tmp_path: Path) -> None:
    store = Store(tmp_path)
    oa_res = SourceResult(
        name="openalex",
        status="ok",
        reason="teto de 1.000 atingido",
        query="oa",
        found=1500,
        fetched=1000,
        works=[Work(title=f"Work {i}", year=2020) for i in range(1000)],
    )
    oa_src = FakeRelatedSource(
        "openalex",
        oa_res,
        origin_work_info=({"id": "https://openalex.org/W100", "doi": "https://doi.org/10.1234/teto"}, None, None),
    )

    out = await run_related(
        store,
        [oa_src],
        direction="references",
        doi="10.1234/teto",
        max_results=1000,
    )

    assert out["status"] == "incomplete"
    assert out["sources"][0]["reason"] == "teto de 1.000 atingido"
