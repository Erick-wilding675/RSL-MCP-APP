"""Testes unitários do catálogo e motor de descritores DeCS/MeSH trilíngues (FR-33, D-044)."""

from __future__ import annotations

from rslapp.core.decs import build_multilingual_query, lookup_descriptors


# FR-33, D-044: Consulta de descritor exato e fonético
def test_lookup_descriptors_exato_e_fonetico() -> None:
    # Busca com acentuação
    res = lookup_descriptors("Inteligência Artificial", lang="pt")
    assert len(res) >= 1
    top = res[0]
    assert top["id"] == "D001185"
    assert top["terms"]["pt"] == "Inteligência Artificial"
    assert top["terms"]["en"] == "Artificial Intelligence"
    assert top["terms"]["es"] == "Inteligencia Artificial"

    # Busca sem acentuação e minúscula
    res_sem_acento = lookup_descriptors("inteligencia artificial", lang="pt")
    assert len(res_sem_acento) >= 1
    assert res_sem_acento[0]["id"] == "D001185"


# FR-33, D-044: Consulta a partir de sinônimos conhecidos
def test_lookup_descriptors_por_sinonimo() -> None:
    res = lookup_descriptors("Saúde da Família", lang="pt")
    assert len(res) >= 1
    assert res[0]["id"] == "D011320"  # Atenção Primária à Saúde
    assert res[0]["terms"]["pt"] == "Atenção Primária à Saúde"


# FR-33, D-044: Consulta em inglês e espanhol
def test_lookup_descriptors_outros_idiomas() -> None:
    res_en = lookup_descriptors("Deep Learning", lang="en")
    assert len(res_en) >= 1
    assert res_en[0]["id"] == "D000076242"
    assert res_en[0]["terms"]["pt"] == "Aprendizado Profundo"

    res_es = lookup_descriptors("Revisión Sistemática", lang="es")
    assert len(res_es) >= 1
    assert res_es[0]["id"] == "D016428"


# FR-33, D-044: Construção de query booleana multilíngue com termos e sinônimos
def test_build_multilingual_query() -> None:
    queries = build_multilingual_query(["Inteligência Artificial", "D016428"], operator="OR")

    assert "pt" in queries
    assert "en" in queries
    assert "es" in queries
    assert "combined" in queries

    # Em português deve conter termos e sinônimos
    assert '"Inteligência Artificial"' in queries["pt"]
    assert '"IA"' in queries["pt"]
    assert '"Revisão Sistemática"' in queries["pt"]

    # Em inglês deve conter as traduções oficiais correspondentes
    assert '"Artificial Intelligence"' in queries["en"]
    assert '"Systematic Review"' in queries["en"]

    # Em espanhol
    assert '"Inteligencia Artificial"' in queries["es"]
    assert '"Revisión Sistemática"' in queries["es"]
