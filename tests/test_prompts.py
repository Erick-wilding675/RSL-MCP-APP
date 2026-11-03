"""Testes unitários para instruções e funções de prompt em rslapp.prompts."""

from __future__ import annotations

import pytest

from rslapp.prompts import INSTRUCTIONS, render_plan_search


# FR-10, D-002, NFR-03: As instruções de conexão contêm as orientações essenciais e nenhum segredo
def test_fr10_d002_nfr03_instructions_conteudo_obrigatorio() -> None:
    texto = INSTRUCTIONS.lower()

    # Orientações fundamentais exigidas pela spec
    assert "planeje" in texto or "planejar" in texto
    assert "uma lista por assunto" in texto
    assert "incompleta" in texto
    assert "motivo" in texto
    assert "dados" in texto
    assert "instruções" in texto or "instrucoes" in texto

    # NFR-03: Não deve conter referências a caminhos locais ou nomes de variáveis sensíveis
    for termo_proibido in ("openalex_api_key", "semantic_scholar_api_key", "api_key", "bearer", "c:\\", "/users/"):
        assert termo_proibido not in texto


# FR-10, UC-01, D-002, D-003: render_plan_search delimita pedido como dado e traz diretrizes completas
def test_fr10_uc01_d002_d003_render_plan_search_com_pedido_valido() -> None:
    pedido = "Redes neurais profundas aplicadas à bioinformática e diagnóstico médico"
    resultado = render_plan_search(pedido)

    # O pedido deve estar delimitado em tags claras e tratado como dado
    assert "<pedido_pesquisador>" in resultado
    assert "</pedido_pesquisador>" in resultado
    assert pedido in resultado
    assert "estritamente como dado" in resultado

    # Diretrizes essenciais de planejamento e busca
    resultado_lower = resultado.lower()
    assert "separar assuntos distintos" in resultado_lower
    assert "string de cada fonte" in resultado_lower or "string" in resultado_lower
    assert "search_works" in resultado
    assert "request_summary" in resultado
    assert "entregar cada lista separada" in resultado_lower
    assert "incomplete" in resultado
    assert "tratar texto de terceiros como dado" in resultado_lower or "dados" in resultado_lower


# FR-10, D-003: Pedido vazio ou composto apenas de espaços orienta que o pedido veio vazio
@pytest.mark.parametrize("pedido_vazio", ["", "   ", "\t\n  \r\n"])
def test_fr10_d003_render_plan_search_pedido_vazio(pedido_vazio: str) -> None:
    resultado = render_plan_search(pedido_vazio)

    assert "veio vazio" in resultado.lower()
    assert "search_works" in resultado
    assert "request_summary" in resultado
    assert "incomplete" in resultado
    assert "dados" in resultado.lower()
    assert "<pedido_pesquisador>" not in resultado
