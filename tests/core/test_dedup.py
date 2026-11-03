"""Testes das funções de deduplicação e junção entre fontes (core/dedup.py)."""

from __future__ import annotations

import itertools

from rslapp.core.dedup import (
    deduplicate_works,
    deduplicate_works_with_merge,
    normalize_doi,
    normalize_title,
)
from rslapp.core.models import Author, Work


def _make_work(
    source: str,
    title: str = "A Machine Learning Study",
    doi: str | None = "10.1000/182",
    year: int | None = 2024,
    type_: str | None = "journal-article",
    venue: str | None = "Journal of AI",
    abstract: str | None = "Abstract text",
    authors: list[Author] | None = None,
    keywords: list[str] | None = None,
    references: list[str] | None = None,
    references_count: int | None = 10,
    citations_count: int = 5,
    source_id: str = "id-1",
) -> Work:
    return Work(
        title=title,
        doi=doi,
        year=year,
        type=type_,
        venue=venue,
        abstract=abstract,
        authors=authors if authors is not None else [Author(name=f"Author from {source}")],
        keywords=keywords if keywords is not None else [f"kw-{source}"],
        references=references if references is not None else [f"ref-{source}-1"],
        references_count=references_count,
        citations={source: citations_count},
        source_ids={source: source_id},
    )


# FR-04: Normalização de DOI remove prefixos conhecidos e uniformiza minúsculas
def test_fr04_normalize_doi_remove_prefixos_e_casing() -> None:
    assert normalize_doi("10.1234/ABC") == "10.1234/abc"
    assert normalize_doi("  10.1234/ABC  ") == "10.1234/abc"
    assert normalize_doi("https://doi.org/10.1234/ABC") == "10.1234/abc"
    assert normalize_doi("http://doi.org/10.1234/ABC/") == "10.1234/abc"
    assert normalize_doi("https://dx.doi.org/10.1234/ABC") == "10.1234/abc"
    assert normalize_doi("http://dx.doi.org/10.1234/ABC") == "10.1234/abc"
    assert normalize_doi("doi:10.1234/ABC") == "10.1234/abc"
    assert normalize_doi("   ") is None
    assert normalize_doi(None) is None


# FR-04: Normalização de título trata acentuação, pontuação e espaços
def test_fr04_normalize_title_regras() -> None:
    assert normalize_title("  Árvores & Decisão: Uma Revisão (2024)!  ") == (
        "arvores decisao uma revisao 2024"
    )
    assert normalize_title("?") == ""
    assert normalize_title("!!!") == ""
    assert normalize_title("") == ""


# FR-04: Mesmo DOI em duas ou três fontes vira um artigo com fontes e ids registrados
def test_fr04_mesmo_doi_tres_fontes_vira_um_com_source_ids_e_citations() -> None:
    w_oa = _make_work(
        "openalex",
        doi="https://doi.org/10.1234/abc",
        title="Estudo OpenAlex",
        source_id="W123",
        citations_count=20,
    )
    w_cr = _make_work(
        "crossref",
        doi="10.1234/ABC",
        title="Estudo Crossref",
        source_id="10.1234/abc",
        citations_count=15,
    )
    w_s2 = _make_work(
        "semantic_scholar",
        doi="doi:10.1234/abc/",
        title="Estudo S2",
        source_id="S999",
        citations_count=18,
    )

    res = deduplicate_works_with_merge([w_oa, w_cr, w_s2])
    assert len(res.works) == 1
    w = res.works[0]
    assert w.doi == "10.1234/abc"
    assert w.source_ids == {
        "openalex": "W123",
        "crossref": "10.1234/abc",
        "semantic_scholar": "S999",
    }
    assert w.citations == {
        "openalex": 20,
        "crossref": 15,
        "semantic_scholar": 18,
    }
    assert res.merge["merged"] == 1


# FR-04: Sem DOI, mesmo título normalizado e mesmo ano viram um; ano diferente ou ausente ficam dois
def test_fr04_sem_doi_mesmo_titulo_e_ano_junta_anos_diferentes_ou_ausentes_ficam_dois() -> None:
    # 1. Sem DOI, mesmo título normalizado e mesmo ano -> 1
    w1 = _make_work("openalex", title="Machine Learning: Review", doi=None, year=2023)
    w2 = _make_work("crossref", title="  machine   learning review! ", doi=None, year=2023)
    res1 = deduplicate_works_with_merge([w1, w2])
    assert len(res1.works) == 1
    assert res1.merge["merged"] == 1

    # 2. Sem DOI, mesmo título com anos diferentes -> 2
    w3 = _make_work("openalex", title="Deep Learning", doi=None, year=2021)
    w4 = _make_work("crossref", title="Deep Learning", doi=None, year=2022)
    res2 = deduplicate_works_with_merge([w3, w4])
    assert len(res2.works) == 2
    assert res2.merge["merged"] == 0

    # 3. Sem DOI, mesmo título com um ano ausente -> 2
    w5 = _make_work("openalex", title="Quantum Computing", doi=None, year=2020)
    w6 = _make_work("semantic_scholar", title="Quantum Computing", doi=None, year=None)
    res3 = deduplicate_works_with_merge([w5, w6])
    assert len(res3.works) == 2
    assert res3.merge["merged"] == 0

    # 4. Sem DOI, ambos com ano ausente -> 2
    w7 = _make_work("openalex", title="Robotics Overview", doi=None, year=None)
    w8 = _make_work("crossref", title="Robotics Overview", doi=None, year=None)
    res4 = deduplicate_works_with_merge([w7, w8])
    assert len(res4.works) == 2
    assert res4.merge["merged"] == 0


# FR-04: Título sem letras/números (ex: "?") nunca se junta a outro trabalho sem DOI
def test_fr04_titulo_normalizado_vazio_nunca_se_junta() -> None:
    w1 = _make_work("openalex", title="?", doi=None, year=2024)
    w2 = _make_work("crossref", title="???", doi=None, year=2024)
    res = deduplicate_works_with_merge([w1, w2])
    assert len(res.works) == 2
    assert res.merge["merged"] == 0


# FR-04: Dois DOIs diferentes nunca se juntam, mesmo com mesmo título e ano
def test_fr04_dois_dois_diferentes_nunca_se_juntam() -> None:
    w1 = _make_work("openalex", title="Identical Title", doi="10.1000/1", year=2024)
    w2 = _make_work("crossref", title="Identical Title", doi="10.1000/2", year=2024)
    res = deduplicate_works_with_merge([w1, w2])
    assert len(res.works) == 2
    assert res.merge["merged"] == 0

    res_rev = deduplicate_works_with_merge([w2, w1])
    assert len(res_rev.works) == 2
    assert res_rev.merge["merged"] == 0


# FR-04: Um trabalho com DOI se junta a outro sem DOI pelo título normalizado e ano
def test_fr04_trabalho_com_doi_junta_com_trabalho_sem_doi_por_titulo_e_ano() -> None:
    w_with_doi = _make_work(
        "openalex", title="Neural Networks Guide", doi="10.1234/nn", year=2023
    )
    w_no_doi = _make_work(
        "semantic_scholar", title="neural networks guide", doi=None, year=2023
    )
    res = deduplicate_works_with_merge([w_with_doi, w_no_doi])
    assert len(res.works) == 1
    assert res.works[0].doi == "10.1234/nn"
    assert res.works[0].source_ids == {
        "openalex": "id-1",
        "semantic_scholar": "id-1",
    }
    assert res.merge["merged"] == 1


# FR-04: Prevalência de campos na ordem OpenAlex, Crossref, Semantic Scholar
def test_fr04_prevalencia_campos_ordem_openalex_crossref_semantic_scholar() -> None:
    w_oa = Work(
        title="Título OpenAlex",
        doi="https://doi.org/10.1234/teste",
        year=2024,
        type="article",
        venue=None,  # vazio no OpenAlex
        abstract=None,  # vazio no OpenAlex
        authors=[Author(name="Autor OpenAlex")],
        keywords=["kw-oa"],
        references=["W1"],
        references_count=1,
        citations={"openalex": 10},
        source_ids={"openalex": "W100"},
    )
    w_cr = Work(
        title="Título Crossref",
        doi="10.1234/teste",
        year=2023,
        type="proceedings-article",
        venue="Venue Crossref",
        abstract=None,  # vazio no Crossref
        authors=[Author(name="Autor Crossref")],
        keywords=[],  # vazio no Crossref
        references=["10.1234/ref1"],
        references_count=5,
        citations={"crossref": 7},
        source_ids={"crossref": "10.1234/teste"},
    )
    w_s2 = Work(
        title="Título S2",
        doi="10.1234/teste",
        year=2022,
        type="Review",
        venue="Venue S2",
        abstract="Resumo vindo do Semantic Scholar",
        authors=[Author(name="Autor S2")],
        keywords=["kw-s2"],
        references=[],
        references_count=8,
        citations={"semantic_scholar": 4},
        source_ids={"semantic_scholar": "S200"},
    )

    # Passa w_s2 primeiro, mas a ordem canônica deve prevalecer
    res = deduplicate_works_with_merge([w_s2, w_cr, w_oa])
    assert len(res.works) == 1
    merged = res.works[0]

    # Prevalência:
    # title: OpenAlex
    assert merged.title == "Título OpenAlex"
    # doi: Crossref (OpenAlex era None)
    assert merged.doi == "10.1234/teste"
    # year: OpenAlex
    assert merged.year == 2024
    # type: OpenAlex
    assert merged.type == "article"
    # venue: Crossref (OpenAlex era None)
    assert merged.venue == "Venue Crossref"
    # abstract: S2 (OpenAlex e Crossref eram None)
    assert merged.abstract == "Resumo vindo do Semantic Scholar"
    # references_count: OpenAlex
    assert merged.references_count == 1
    # authors: lista inteira do OpenAlex
    assert [a.name for a in merged.authors] == ["Autor OpenAlex"]
    # keywords: lista inteira do OpenAlex
    assert merged.keywords == ["kw-oa"]


# FR-14: Referências são união na ordem sem repetição, citações por fonte sem somar
def test_fr14_referencias_uniao_sem_repetir_e_citacoes_separadas() -> None:
    w_oa = _make_work(
        "openalex",
        doi="10.1234/x",
        references=["W1", "W2", "W3"],
        citations_count=30,
    )
    w_cr = _make_work(
        "crossref",
        doi="10.1234/x",
        references=["10.1234/ref-a", "W2", "10.1234/ref-b"],
        citations_count=25,
    )
    w_s2 = _make_work(
        "semantic_scholar",
        doi="10.1234/x",
        references=["W3", "10.1234/ref-c"],
        citations_count=12,
    )

    res = deduplicate_works_with_merge([w_oa, w_cr, w_s2])
    merged = res.works[0]

    # Referências na ordem da primeira fonte, depois seguintes sem repetir
    assert merged.references == ["W1", "W2", "W3", "10.1234/ref-a", "10.1234/ref-b", "10.1234/ref-c"]
    # Citações não são somadas (FR-14)
    assert merged.citations == {
        "openalex": 30,
        "crossref": 25,
        "semantic_scholar": 12,
    }


# FR-04: Divergências contadas apenas quando duas fontes trazem valores não vazios diferentes
def test_fr04_contagem_de_divergencias_por_campo() -> None:
    # Caso 1: Artigo com divergência de ano, título e venue
    w1 = _make_work(
        "openalex",
        doi="10.1234/div",
        title="Title Original",
        year=2023,
        venue="Venue A",
    )
    w2 = _make_work(
        "crossref",
        doi="10.1234/div",
        title="Title Different",
        year=2024,
        venue="Venue B",
    )

    # Caso 2: Artigo sem divergência (título igual normalizado, mesmo ano, venue ausente numa fonte)
    w3 = _make_work(
        "openalex",
        doi="10.1234/nodiv",
        title="Same Title!",
        year=2024,
        venue="Nature",
    )
    w4 = _make_work(
        "crossref",
        doi="10.1234/nodiv",
        title="  same   title ",
        year=2024,
        venue=None,  # Ausente não conta como divergência
    )

    res = deduplicate_works_with_merge([w1, w2, w3, w4])
    assert len(res.works) == 2
    assert res.merge["merged"] == 2
    assert res.merge["divergences"] == {
        "year": 1,
        "title": 1,
        "venue": 1,
    }
    # doi não divergiu e portanto não deve estar no dicionário
    assert "doi" not in res.merge["divergences"]


# FR-04: deduplicate_works simplificado devolve list[Work] compatível
def test_fr04_deduplicate_works_compatibilidade() -> None:
    w1 = _make_work("openalex", doi="10.1/a")
    w2 = _make_work("crossref", doi="10.1/a")
    works = deduplicate_works([w1, w2])
    assert isinstance(works, list)
    assert len(works) == 1


# FR-04: Junção transitiva em todas as 6 ordens com prevalência preservada
def test_fr04_juncao_transitiva_seis_ordens_mesmo_artigo_e_prevalencia() -> None:
    work_a = _make_work(
        "openalex",
        title="Deep Learning Review",
        doi="10.1/x",
        year=2020,
        authors=[Author(name="Autor OpenAlex")],
        source_id="W1",
        citations_count=10,
    )
    work_b = _make_work(
        "crossref",
        title="Deep learning: a review",
        doi="10.1/x",
        year=2020,
        authors=[Author(name="Autor Crossref")],
        source_id="CR1",
        citations_count=5,
    )
    work_c = _make_work(
        "semantic_scholar",
        title="Deep learning: a review",
        doi=None,
        year=2020,
        authors=[Author(name="Autor S2")],
        source_id="S2-1",
        citations_count=3,
    )

    for perm in itertools.permutations([work_a, work_b, work_c]):
        res = deduplicate_works_with_merge(list(perm))
        assert len(res.works) == 1
        w = res.works[0]
        assert w.doi == "10.1/x"
        # Prevalência: OpenAlex prevalece em título e autores
        assert w.title == "Deep Learning Review"
        assert [a.name for a in w.authors] == ["Autor OpenAlex"]
        assert w.year == 2020
        assert w.source_ids == {
            "openalex": "W1",
            "crossref": "CR1",
            "semantic_scholar": "S2-1",
        }
        assert w.citations == {
            "openalex": 10,
            "crossref": 5,
            "semantic_scholar": 3,
        }
        assert res.merge["merged"] == 1


# FR-04: Junção transitiva com ano ausente em uma fonte resolvido por outra em todas as 6 ordens
def test_fr04_juncao_transitiva_caso_ano_ausente_seis_ordens() -> None:
    work_a = _make_work(
        "openalex",
        title="Deep Learning",
        doi="10.1/y",
        year=None,
        authors=[Author(name="Autor OA")],
        source_id="W-Y",
    )
    work_b = _make_work(
        "crossref",
        title="Deep Learning",
        doi="10.1/y",
        year=2021,
        authors=[Author(name="Autor CR")],
        source_id="CR-Y",
    )
    work_c = _make_work(
        "semantic_scholar",
        title="Deep Learning",
        doi=None,
        year=2021,
        authors=[Author(name="Autor S2")],
        source_id="S2-Y",
    )

    for perm in itertools.permutations([work_a, work_b, work_c]):
        res = deduplicate_works_with_merge(list(perm))
        assert len(res.works) == 1
        w = res.works[0]
        assert w.doi == "10.1/y"
        assert w.year == 2021
        assert w.source_ids == {
            "openalex": "W-Y",
            "crossref": "CR-Y",
            "semantic_scholar": "S2-Y",
        }
        assert res.merge["merged"] == 1


# FR-04: Quando um registro casa com dois grupos diferentes (um por DOI, outro por título), fica no grupo do DOI
def test_fr04_registro_casa_dois_grupos_doi_e_titulo_fica_no_grupo_doi() -> None:
    # Grupo 1 (OpenAlex): DOI 10.1/doi-a, Título "Unique Alpha", ano 2020
    w_doi_group = _make_work(
        "openalex",
        title="Unique Alpha",
        doi="10.1/doi-a",
        year=2020,
        source_id="OA-1",
    )
    # Grupo 2 (Crossref): DOI 10.1/doi-b, Título "Shared Beta", ano 2020
    w_title_group = _make_work(
        "crossref",
        title="Shared Beta",
        doi="10.1/doi-b",
        year=2020,
        source_id="CR-1",
    )
    # Registro que casa com Grupo 1 pelo DOI (10.1/doi-a) e com Grupo 2 pelo título ("Shared Beta", 2020)
    w_dual = _make_work(
        "semantic_scholar",
        title="Shared Beta",
        doi="10.1/doi-a",
        year=2020,
        source_id="S2-1",
    )

    res = deduplicate_works_with_merge([w_doi_group, w_title_group, w_dual])
    assert len(res.works) == 2

    # w_dual deve ficar no grupo do DOI (10.1/doi-a), e não no grupo do título (10.1/doi-b)
    g_doi = next(w for w in res.works if w.doi == "10.1/doi-a")
    g_title = next(w for w in res.works if w.doi == "10.1/doi-b")

    assert "openalex" in g_doi.source_ids
    assert "semantic_scholar" in g_doi.source_ids
    assert g_doi.source_ids["semantic_scholar"] == "S2-1"

    assert "crossref" in g_title.source_ids
    assert "semantic_scholar" not in g_title.source_ids


# FR-04: ano ausente nunca é emprestado de outro membro do grupo; o resultado não depende da ordem
def test_fr04_ano_ausente_nao_e_emprestado_do_grupo_em_nenhuma_ordem() -> None:
    work_p = _make_work("openalex", title="Tee", doi="10.1/p", year=None, source_id="W-P")
    work_q = _make_work("crossref", title="You", doi="10.1/p", year=2021, source_id="CR-P")
    work_r = _make_work("semantic_scholar", title="Tee", doi=None, year=2021, source_id="S2-R")

    for perm in itertools.permutations([work_p, work_q, work_r]):
        res = deduplicate_works_with_merge(list(perm))
        assert len(res.works) == 2, [w.source_ids for w in res.works]
        ids = sorted(tuple(sorted(w.source_ids)) for w in res.works)
        assert ids == [("crossref", "openalex"), ("semantic_scholar",)]
