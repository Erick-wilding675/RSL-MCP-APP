"""Testes dos modelos e erros do miolo (core)."""

from __future__ import annotations

import pytest

from rslapp.core.errors import ERROR_CODES, RSLError
from rslapp.core.models import Affiliation, Author, SourceResult, Work


# FR-03, FR-14, D-004, D-010: Conversão de ida e volta to_dict/from_dict sem perda de dados
def test_fr03_fr14_d004_d010_modelos_from_dict_to_dict_preserva_tudo() -> None:
    aff = Affiliation(
        name="Universidade de São Paulo",
        ids={"openalex": "I17974374", "ror": "https://ror.org/036rp1748"},
        country_code="BR",
    )
    assert Affiliation.from_dict(aff.to_dict()) == aff

    author = Author(
        name="Maria Silva",
        orcid="0000-0002-1825-0097",
        ids={"openalex": "A5023888391"},
        position="first",
        is_corresponding=True,
        affiliations=[aff],
        raw_affiliations=["Universidade de São Paulo, Brasil"],
    )
    assert Author.from_dict(author.to_dict()) == author

    work = Work(
        title="Interpretability in Machine Learning",
        doi="10.1234/ml.2024.01",
        year=2024,
        type="article",
        venue="Journal of AI Research",
        abstract="We study interpretability methods for deep models.",
        keywords=["machine learning", "interpretability"],
        authors=[author],
        references=["W2741809807", "W2100837269"],
        references_count=2,
        citations={"openalex": 17},
        source_ids={"openalex": "W4390000001"},
    )
    assert Work.from_dict(work.to_dict()) == work

    source_res = SourceResult(
        name="openalex",
        status="ok",
        reason=None,
        query="search=machine learning · per_page=100 · páginas 1-1",
        found=412,
        fetched=1,
        works=[work],
    )
    assert SourceResult.from_dict(source_res.to_dict()) == source_res


# FR-03, FR-14: Campos opcionais vazios ou nulos preservam igualdade no ciclo to_dict/from_dict
def test_fr03_fr14_modelos_opcionais_vazios_from_dict_to_dict() -> None:
    aff = Affiliation()
    assert Affiliation.from_dict(aff.to_dict()) == aff

    author = Author(name="João Souza")
    assert Author.from_dict(author.to_dict()) == author

    work = Work(title="Artigo Mínimo")
    assert Work.from_dict(work.to_dict()) == work

    res = SourceResult(name="openalex", status="missing_key", reason="sem chave")
    assert SourceResult.from_dict(res.to_dict()) == res


# FR-06, D-002: RSLError valida os códigos do contrato (incluindo empty_list) e preserva código e mensagem
def test_fr06_d002_rsl_error_codigos_do_contrato() -> None:
    assert "empty_list" in ERROR_CODES
    for code in ERROR_CODES:
        err = RSLError(code, "detalhe do erro")
        assert err.code == code
        assert err.message == "detalhe do erro"
        assert str(err) == f"{code}: detalhe do erro"

    with pytest.raises(ValueError, match="Código de erro fora do contrato"):
        RSLError("codigo_inexistente", "mensagem")
