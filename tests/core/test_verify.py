"""Testes de unidade do verificador de referências acadêmicas (FR-21, D-030)."""

from __future__ import annotations

import pytest

from rslapp.core.models import Author, SourceResult, Work
from rslapp.core.verify import (
    parse_references,
    run_verify_references,
)


class FakeVerifySource:
    """Fonte simulada para testes do verificador de referências."""

    def __init__(self, name: str, works: list[Work]) -> None:
        self.name = name
        self.needs_key = False
        self._works = works

    def cache_query(self, query: str, max_results: int = 100) -> dict[str, str]:
        return {"query": query}

    async def search(self, query: str, max_results: int = 10) -> SourceResult:
        query_lower = query.lower()
        matched = [
            w for w in self._works if query_lower in w.title.lower() or w.title.lower() in query_lower
        ]
        return SourceResult(
            name=self.name,
            status="ok",
            found=len(matched),
            fetched=len(matched),
            works=matched[:max_results],
        )

    async def find_by_doi(self, doi: str) -> Work | None:
        doi_clean = doi.lower().strip()
        for w in self._works:
            if w.doi and w.doi.lower().strip() == doi_clean:
                return w
        return None


# FR-21: Testa o parser de referências para BibTeX e texto livre
def test_fr21_parse_references_bibtex_e_texto() -> None:
    # 1. BibTeX
    bibtex_str = """
    @article{vaswani2017attention,
      title = {Attention is All you Need},
      author = {Vaswani, Ashish and Shazeer, Noam and Parmar, Niki},
      year = {2017},
      doi = {10.5555/3295222.3295349}
    }
    @inproceedings{deutsch1985quantum,
      title = {Quantum theory, the Church-Turing principle and the universal quantum computer},
      author = {Deutsch, David},
      year = {1985}
    }
    """
    parsed = parse_references(bibtex_str)
    assert len(parsed) == 2
    assert parsed[0].title == "Attention is All you Need"
    assert parsed[0].year == 2017
    assert parsed[0].doi == "10.5555/3295222.3295349"
    assert len(parsed[0].authors) == 3

    assert parsed[1].title == "Quantum theory, the Church-Turing principle and the universal quantum computer"
    assert parsed[1].year == 1985

    # 2. Texto livre com DOI e numeração
    text_str = (
        "[1] Vaswani, A. et al. (2017). Attention is all you need. NeurIPS. doi: 10.5555/3295222.3295349\n\n"
        "[2] DEUTSCH, D. (1985). Quantum theory and computers. Proceedings of the Royal Society."
    )
    parsed_text = parse_references(text_str)
    assert len(parsed_text) == 2
    assert parsed_text[0].doi == "10.5555/3295222.3295349"
    assert parsed_text[0].year == 2017

    # 3. Lista de dicionários
    dict_list = [
        {"title": "Deep Learning", "author": "LeCun, Yann", "year": 2015, "doi": "10.1038/nature14539"}
    ]
    parsed_dict = parse_references(dict_list)
    assert len(parsed_dict) == 1
    assert parsed_dict[0].title == "Deep Learning"
    assert parsed_dict[0].doi == "10.1038/nature14539"

    # 4. Entrada vazia
    assert parse_references("") == []
    assert parse_references([]) == []


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# FR-21, D-030: Testa a verificação de referências reais, com divergências e alucinações completas
@pytest.mark.anyio
async def test_fr21_d030_run_verify_references() -> None:
    works_db = [
        Work(
            title="Attention is All you Need",
            doi="10.5555/3295222.3295349",
            year=2017,
            venue="NeurIPS",
            authors=[Author(name="Ashish Vaswani"), Author(name="Noam Shazeer")],
        ),
        Work(
            title="Deep Learning and Neural Networks",
            doi="10.1000/dl2015",
            year=2015,
            venue="Nature",
            authors=[Author(name="Yann LeCun"), Author(name="Yoshua Bengio")],
        ),
    ]

    fake_source = FakeVerifySource("openalex", works_db)

    refs_to_check = [
        # 1. Referência confirmada (bate título, autor e ano)
        {
            "title": "Attention is All you Need",
            "authors": ["Vaswani"],
            "year": 2017,
            "doi": "10.5555/3295222.3295349",
        },
        # 2. Referência divergente (título bate, mas ano e autor inventados pela IA)
        {
            "title": "Deep Learning and Neural Networks",
            "authors": ["Silva, Joao"],
            "year": 2023,  # Divergente de 2015
        },
        # 3. Referência totalmente alucinada / inexistente
        {
            "title": "Quantum Blockchain Hyperdimensional Artificial General Intelligence for Space Exploration",
            "authors": ["Fictional, Arthur"],
            "year": 2025,
            "doi": "10.9999/hallucinated.paper.2025",
        },
    ]

    result = await run_verify_references([fake_source], refs_to_check)

    assert result["total"] == 3
    assert result["verified"] == 1
    assert result["divergent"] == 1
    assert result["not_found"] == 1

    items = result["results"]
    assert items[0]["status"] == "verified"
    assert items[0]["doi"] == "10.5555/3295222.3295349"
    assert items[0]["status_label"] == "Confirmada"

    assert items[1]["status"] == "divergent"
    assert items[1]["status_label"] == "Divergência"
    assert len(items[1]["divergence_details"]) >= 1

    assert items[2]["status"] == "not_found"
    assert items[2]["status_label"] == "Não encontrada"


# FR-21: Tolerância de até 1 ano (preprint vs formal) e busca por título sem DOI
@pytest.mark.anyio
async def test_fr21_tolerancia_ano_preprint_e_sem_doi() -> None:
    work = Work(
        title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        doi="10.18653/v1/N19-1423",
        year=2019,
        authors=[Author(name="Jacob Devlin"), Author(name="Ming-Wei Chang")],
    )
    fake_source = FakeVerifySource("crossref", [work])

    # 1. Citado como 2018 (ano do preprint no arXiv), autor Devlin, sem DOI
    res = await run_verify_references(
        [fake_source],
        "Devlin et al. (2018). BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding.",
    )
    assert res["total"] == 1
    assert res["verified"] == 1
    item = res["results"][0]
    assert item["status"] == "verified"
    assert item["doi"] == "10.18653/v1/N19-1423"
    assert item["matched_year"] == 2019
