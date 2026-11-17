"""Testes do formatador e exportador ABNT NBR 6023:2018 (FR-24, D-034)."""

from __future__ import annotations

from pathlib import Path

from rslapp.core.abnt import (
    format_abnt_author_name,
    format_abnt_authors,
    format_abnt_reference,
)
from rslapp.core.models import Author, Work
from rslapp.exporters import get_exporter, run_export
from rslapp.exporters.abnt import ABNTExporter
from rslapp.store import Store


# FR-24, D-034: Formatação de nomes de autores segundo a ABNT
def test_fr24_d034_format_abnt_author_name() -> None:
    assert format_abnt_author_name("Platão") == "PLATÃO"
    assert format_abnt_author_name("Carlos Silva") == "SILVA, Carlos"
    assert format_abnt_author_name("Carlos Alberto da Silva") == "SILVA, Carlos Alberto da"
    assert format_abnt_author_name("João Silva Filho") == "SILVA FILHO, João"
    assert format_abnt_author_name("Antônio Pereira Júnior") == "PEREIRA JÚNIOR, Antônio"
    assert format_abnt_author_name("Silva, Carlos") == "SILVA, Carlos"


# FR-24, D-034: Formatação de lista de autores com 1, 2, 3 e mais autores
def test_fr24_d034_format_abnt_authors() -> None:
    a1 = Author(name="Carlos Silva")
    a2 = Author(name="Maria Santos")
    a3 = Author(name="João Oliveira")
    a4 = Author(name="Ana Souza")

    # 1 autor
    assert format_abnt_authors([a1]) == "SILVA, Carlos"
    # 2 autores
    assert format_abnt_authors([a1, a2]) == "SILVA, Carlos; SANTOS, Maria"
    # 3 autores
    assert format_abnt_authors([a1, a2, a3]) == "SILVA, Carlos; SANTOS, Maria; OLIVEIRA, João"
    # > 3 autores (por padrão na edição 2018, todos os autores são listados)
    assert format_abnt_authors([a1, a2, a3, a4]) == "SILVA, Carlos; SANTOS, Maria; OLIVEIRA, João; SOUZA, Ana"
    # Com et al. explícito
    assert format_abnt_authors([a1, a2, a3, a4], use_et_al_over_three=True) == "SILVA, Carlos et al."


# FR-24, D-034: Referência de artigo de periódico na ABNT NBR 6023:2018
def test_fr24_d034_format_abnt_reference_article() -> None:
    work = Work(
        title="Deep learning in medical imaging: a systematic review",
        doi="10.1016/j.media.2023.102800",
        year=2023,
        type="article",
        venue="Medical Image Analysis",
        authors=[Author(name="Carlos Silva"), Author(name="Maria Santos")],
    )

    # Texto puro
    ref_txt = format_abnt_reference(work)
    assert ref_txt.startswith("SILVA, Carlos; SANTOS, Maria. Deep learning in medical imaging: a systematic review. Medical Image Analysis, 2023.")
    assert "Disponível em: https://doi.org/10.1016/j.media.2023.102800." in ref_txt

    # Markdown (periódico em negrito)
    ref_md = format_abnt_reference(work, markdown=True)
    assert "**Medical Image Analysis**," in ref_md


# FR-24, D-034: Referência de livro na ABNT (destaque no título)
def test_fr24_d034_format_abnt_reference_book() -> None:
    work = Work(
        title="Metodologia da pesquisa científica",
        year=2020,
        type="book",
        venue="Editora Atlas",
        authors=[Author(name="Antônio Carlos Gil")],
    )
    ref_md = format_abnt_reference(work, markdown=True)
    assert "**Metodologia da pesquisa científica**." in ref_md
    assert "GIL, Antônio Carlos." in ref_md


# FR-24, D-032, D-034: Artigo retratado leva nota explícita na referência ABNT
def test_fr24_d032_d034_format_abnt_reference_retracted() -> None:
    work = Work(
        title="Hydroxychloroquine for COVID-19: a multinational registry analysis",
        doi="10.1016/S0140-6736(20)31180-6",
        year=2020,
        type="article",
        venue="The Lancet",
        authors=[Author(name="Mandeep Mehra")],
        is_retracted=True,
    )
    ref = format_abnt_reference(work)
    assert "[Artigo retratado ou com expressão de preocupação oficial]." in ref


# FR-24, D-034: ABNTExporter renderiza lista em ordem alfabética
def test_fr24_d034_abnt_exporter_alfabetico() -> None:
    w_vaswani = Work(
        title="Attention is all you need",
        year=2017,
        authors=[Author(name="Ashish Vaswani")],
    )
    w_berners = Work(
        title="Information management: a proposal",
        year=1989,
        authors=[Author(name="Tim Berners-Lee")],
    )
    w_turing = Work(
        title="Computing machinery and intelligence",
        year=1950,
        authors=[Author(name="Alan Turing")],
    )

    list_data = {"works": [w_vaswani, w_berners, w_turing]}
    exporter = ABNTExporter()
    rendered = exporter.render(list_data)

    paragraphs = [p for p in rendered.split("\n\n") if p.strip()]
    assert len(paragraphs) == 3
    # Ordem alfabética pelo autor: BERNERS-LEE -> TURING -> VASWANI
    assert paragraphs[0].startswith("BERNERS-LEE, Tim.")
    assert paragraphs[1].startswith("TURING, Alan.")
    assert paragraphs[2].startswith("VASWANI, Ashish.")


# FR-24, D-034: Execução via run_export e registro em get_exporter('abnt')
def test_fr24_d034_run_export_abnt(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    export_dir = tmp_path / "exports"

    w = Work(
        title="Revisão Bibliométrica na Saúde",
        year=2024,
        doi="10.1000/rbl.2024.1",
        venue="Revista Brasileira de Saúde",
        authors=[Author(name="Renata Lima")],
    )
    search_data = {
        "kind": "terms",
        "request_summary": "busca teste",
        "created_at": "2026-11-16T12:00:00Z",
        "sources": [{"name": "openalex", "status": "ok", "query": "q", "found": 1, "fetched": 1}],
    }
    list_data = {
        "status": "complete",
        "total": 1,
        "works": [w.to_dict()],
    }
    _, saved_list = store.record_search(search_data, list_data)
    list_id = saved_list["id"]

    assert get_exporter("abnt").format == "abnt"

    res = run_export(store, list_id, "abnt", export_dir)
    assert res["format"] == "abnt"
    assert res["count"] == 1
    assert Path(res["path"]).exists()

    content = Path(res["path"]).read_text(encoding="utf-8")
    assert "LIMA, Renata." in content
    assert "Revista Brasileira de Saúde" in content
