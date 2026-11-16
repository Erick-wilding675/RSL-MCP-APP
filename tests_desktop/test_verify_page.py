"""Testes da tela Verificar referências contra alucinação (FR-21, D-030, D-031)."""

from __future__ import annotations

from typing import Any

from nicegui import ui
from nicegui.testing import User

from rslapp.desktop.app import register_pages


class FakeVerifyDesktopService:
    """Serviço desktop simulado para testes da tela /verificar."""

    def __init__(self, result: dict[str, Any] | None = None, should_fail: bool = False) -> None:
        self.result = result if result is not None else {
            "total": 3,
            "verified": 1,
            "divergent": 1,
            "not_found": 1,
            "results": [
                {
                    "status": "verified",
                    "status_label": "Confirmada",
                    "input_ref": "Vaswani et al. (2017). Attention is All you Need.",
                    "matched_title": "Attention is All you Need",
                    "matched_year": 2017,
                    "matched_authors": ["Vaswani, Ashish", "Shazeer, Noam"],
                    "source": "openalex",
                    "divergence_details": [],
                    "doi": "10.5555/3295222.3295349",
                },
                {
                    "status": "divergent",
                    "status_label": "Divergência",
                    "input_ref": "Silva, J. (2023). Deep Learning and Neural Networks.",
                    "matched_title": "Deep Learning and Neural Networks",
                    "matched_year": 2015,
                    "matched_authors": ["LeCun, Yann"],
                    "source": "crossref",
                    "divergence_details": ["Ano divergente: citado 2023 vs encontrado 2015"],
                    "doi": "10.1000/dl2015",
                },
                {
                    "status": "not_found",
                    "status_label": "Não encontrada",
                    "input_ref": "Ghost, W. (2025). Completely Fake Nonexistent Quantum Blockchain.",
                    "matched_title": None,
                    "matched_year": None,
                    "matched_authors": [],
                    "source": None,
                    "divergence_details": ["Referência não encontrada nas bases consultadas."],
                    "doi": None,
                },
            ],
        }
        self.should_fail = should_fail
        self.verify_calls: list[str | list[Any]] = []

    def list_sources(self) -> list[dict[str, Any]]:
        return []

    async def verify_references(self, references: str | list[Any]) -> dict[str, Any]:
        self.verify_calls.append(references)
        if self.should_fail:
            raise RuntimeError("Falha de rede nas bases acadêmicas")
        return self.result


# FR-21, D-030, D-031: Abertura da tela /verificar e estado inicial
async def test_fr21_tela_verificar_abertura_e_estado_inicial(user: User) -> None:
    fake_service = FakeVerifyDesktopService()
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/verificar")
    await user.should_see("Verificar")
    await user.should_see("Verifique se referências citadas existem nas bases reais contra alucinações de IA.")
    await user.should_see("Referências a verificar")
    await user.should_see("Nenhuma verificação realizada")

    # Verifica os botões
    assert user.find(marker="verify-btn")
    assert user.find(marker="verify-clear-btn")
    assert user.find(marker="verify-input")


# FR-21, D-031: Tentar verificar com campo vazio dispara aviso
async def test_fr21_tela_verificar_clique_vazio_aviso(user: User) -> None:
    fake_service = FakeVerifyDesktopService()
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/verificar")
    user.find(marker="verify-btn").click()

    await user.should_see("Por favor, cole pelo menos uma referência para verificar.")
    assert len(fake_service.verify_calls) == 0


# FR-21, D-030, D-031: Verificação bem-sucedida renderiza métricas e tabela com status
async def test_fr21_tela_verificar_execucao_com_resultados(user: User) -> None:
    fake_service = FakeVerifyDesktopService()
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/verificar")
    input_text = "Vaswani (2017)\nSilva (2023)\nGhost (2025)"
    user.find(marker="verify-input").type(input_text)
    user.find(marker="verify-btn").click()

    await user.should_see("Verificação concluída: 1 confirmadas, 1 divergentes, 1 não encontradas.")
    assert len(fake_service.verify_calls) == 1
    assert fake_service.verify_calls[0] == input_text

    # Verifica métricas
    await user.should_see("Total verificado")
    await user.should_see("Confirmadas")
    await user.should_see("Divergências")
    await user.should_see("Não encontradas")

    # Verifica tabela de resultados
    await user.should_see("Resultados da verificação")
    await user.should_see(ui.table)

    # Botão limpar limpa o input
    user.find(marker="verify-clear-btn").click()
    input_elem = user.find(marker="verify-input").elements.pop()
    assert input_elem.value == ""


# FR-21, D-031: Erro durante a consulta exibe mensagem de erro
async def test_fr21_tela_verificar_tratamento_de_erro(user: User) -> None:
    fake_service = FakeVerifyDesktopService(should_fail=True)
    register_pages(service=fake_service)  # type: ignore[arg-type]

    await user.open("/verificar")
    user.find(marker="verify-input").type("Alguma referencia")
    user.find(marker="verify-btn").click()

    await user.should_see("Erro ao verificar referências: Falha de rede nas bases acadêmicas")
