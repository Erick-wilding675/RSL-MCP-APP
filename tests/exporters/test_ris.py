"""Testes unitários do exportador RIS e da infraestrutura de exportação."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from rslapp.core.errors import RSLError
from rslapp.core.models import Affiliation, Author, Work
from rslapp.exporters import RISExporter, get_exporter, run_export, save_export_file
from rslapp.store import Store


# FR-06: Renderização linha a linha de trabalho completo com terminadores \r\n e tags RIS padrão
def test_fr06_render_work_completo_linha_a_linha() -> None:
    work = Work(
        title="Interpretable Machine Learning in Healthcare",
        doi="10.1234/iml.2024.001",
        year=2024,
        type="article",
        venue="Nature Machine Intelligence",
        abstract="We propose a novel framework for explainable artificial intelligence.",
        keywords=["artificial intelligence", "interpretability", "healthcare"],
        authors=[
            Author(name="Ada Lovelace"),
            Author(name="Charles Babbage"),
        ],
    )
    list_data = {"id": "l-0001", "works": [work.to_dict()]}
    exporter = RISExporter()
    rendered = exporter.render(list_data)

    expected = (
        "TY  - JOUR\r\n"
        "TI  - Interpretable Machine Learning in Healthcare\r\n"
        "AU  - Ada Lovelace\r\n"
        "AU  - Charles Babbage\r\n"
        "PY  - 2024\r\n"
        "JO  - Nature Machine Intelligence\r\n"
        "AB  - We propose a novel framework for explainable artificial intelligence.\r\n"
        "KW  - artificial intelligence\r\n"
        "KW  - interpretability\r\n"
        "KW  - healthcare\r\n"
        "DO  - 10.1234/iml.2024.001\r\n"
        "ER  - \r\n"
    )
    assert rendered == expected


# FR-06: Suporte completo a acentuação e UTF-8 em títulos, autores, periódicos e resumos
def test_fr06_render_com_acentos_e_utf8() -> None:
    work = {
        "title": "Revisão Sistemática de Métodos em Aprendizado Profundo",
        "doi": "10.1234/rbc.2024.42",
        "year": 2023,
        "type": "article",
        "venue": "Revista Brasileira de Computação Aplicada",
        "abstract": "Apresentamos uma síntese das abordagens probabilísticas e conexionistas.",
        "keywords": ["aprendizado de máquina", "visão computacional"],
        "authors": [
            {"name": "José da Silva"},
            {"name": "Müller, Klaus"},
        ],
    }
    rendered = RISExporter().render({"works": [work]})
    lines = rendered.split("\r\n")

    assert "TI  - Revisão Sistemática de Métodos em Aprendizado Profundo" in lines
    assert "AU  - José da Silva" in lines
    assert "AU  - Müller, Klaus" in lines
    assert "JO  - Revista Brasileira de Computação Aplicada" in lines
    assert "AB  - Apresentamos uma síntese das abordagens probabilísticas e conexionistas." in lines
    assert "KW  - aprendizado de máquina" in lines


# FR-06: Campos ausentes ou vazios não geram tags no arquivo RIS
def test_fr06_render_campos_vazios_nao_sao_escritos() -> None:
    minimal_work = {
        "title": "Minimal Article",
        "type": "article",
    }
    rendered = RISExporter().render({"works": [minimal_work]})
    lines = rendered.split("\r\n")

    assert lines[0] == "TY  - JOUR"
    assert lines[1] == "TI  - Minimal Article"
    assert lines[2] == "ER  - "
    assert not any(line.startswith("AU  - ") for line in lines)
    assert not any(line.startswith("PY  - ") for line in lines)
    assert not any(line.startswith("JO  - ") for line in lines)
    assert not any(line.startswith("AB  - ") for line in lines)
    assert not any(line.startswith("KW  - ") for line in lines)
    assert not any(line.startswith("DO  - ") for line in lines)


# FR-06: Mapeamento de tipo TY para JOUR, CONF ou GEN conforme o spec
@pytest.mark.parametrize(
    ("work_type", "expected_ris_type"),
    [
        ("article", "JOUR"),
        ("journal-article", "JOUR"),
        ("journal_article", "JOUR"),
        ("JournalArticle", "JOUR"),
        ("conference", "CONF"),
        ("proceedings-article", "CONF"),
        ("conference-paper", "CONF"),
        ("Conference", "CONF"),
        ("book", "GEN"),
        ("report", "GEN"),
        ("dissertation", "GEN"),
        ("other", "GEN"),
        (None, "GEN"),
        ("", "GEN"),
    ],
)
def test_fr06_render_mapeamento_tipo_ris(work_type: str | None, expected_ris_type: str) -> None:
    rendered = RISExporter().render({"works": [{"title": "Test Title", "type": work_type}]})
    assert rendered.startswith(f"TY  - {expected_ris_type}\r\n")


# FR-06, D-004: ORCID, afiliações e referências ficam fora do arquivo RIS (sem campo padrão)
def test_fr06_d004_orcid_afiliacoes_e_referencias_ficam_fora_do_ris() -> None:
    work = Work(
        title="Complete Record with Author Details",
        doi="10.1234/test.1",
        year=2024,
        type="article",
        authors=[
            Author(
                name="Ada Lovelace",
                orcid="0000-0001-2345-6789",
                affiliations=[Affiliation(name="University of Oxford", country_code="GB")],
                raw_affiliations=["Oxford University, UK"],
            ),
        ],
        references=["W1000", "W1001"],
        references_count=2,
        citations={"openalex": 10},
    )
    rendered = RISExporter().render({"works": [work.to_dict()]})

    assert "0000-0001-2345-6789" not in rendered
    assert "Oxford" not in rendered
    assert "W1000" not in rendered
    assert "W1001" not in rendered
    assert "citations" not in rendered


# FR-06: Lista com múltiplos artigos gera registros sequenciais delimitados por ER
def test_fr06_render_multiplos_artigos() -> None:
    works = [
        {"title": "Paper One", "type": "article"},
        {"title": "Paper Two", "type": "proceedings-article"},
    ]
    rendered = RISExporter().render({"works": works})

    expected = (
        "TY  - JOUR\r\n"
        "TI  - Paper One\r\n"
        "ER  - \r\n"
        "TY  - CONF\r\n"
        "TI  - Paper Two\r\n"
        "ER  - \r\n"
    )
    assert rendered == expected


# FR-06: Lista vazia devolve string vazia
def test_fr06_render_lista_vazia() -> None:
    assert RISExporter().render({"works": []}) == ""
    assert RISExporter().render({}) == ""


# FR-06: Entrada não dicionário levanta TypeError
def test_fr06_render_invalido_tipo_dados() -> None:
    with pytest.raises(TypeError, match="list_data deve ser um dicionário"):
        RISExporter().render(["não é dict"])  # type: ignore[arg-type]


# FR-06, D-002: get_exporter localiza exportador registrado e rejeita desconhecidos
def test_fr06_d002_get_exporter_registrado() -> None:
    exporter = get_exporter("ris")
    assert isinstance(exporter, RISExporter)
    assert exporter.format == "ris"

    with pytest.raises(RSLError) as exc_info:
        get_exporter("desconhecido")
    assert exc_info.value.code == "invalid_input"

    with pytest.raises(RSLError) as exc_info_type:
        get_exporter(123)  # type: ignore[arg-type]
    assert exc_info_type.value.code == "invalid_input"


# D-007, FR-06: save_export_file grava com UTF-8, cria pastas e substitui na reexportação
def test_d007_fr06_save_export_file_atomico_e_sobrescrita(tmp_path: Path) -> None:
    export_dir = tmp_path / "custom" / "exports"
    filename = "l-0001.ris"
    content_v1 = "TY  - JOUR\r\nTI  - Versão 1\r\nER  - \r\n"
    dest = save_export_file(export_dir, filename, content_v1)

    assert dest.exists()
    assert dest.read_bytes() == content_v1.encode("utf-8")

    content_v2 = "TY  - JOUR\r\nTI  - Versão 2 Atualizada\r\nER  - \r\n"
    dest_v2 = save_export_file(export_dir, filename, content_v2)
    assert dest_v2 == dest
    assert dest.read_bytes() == content_v2.encode("utf-8")


# D-007: Falha de permissão na gravação levanta RSLError('export_folder_not_writable')
def test_d007_save_export_file_pasta_sem_permissao(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    export_dir = tmp_path / "readonly_dir"

    def _fail_write(*_args: Any, **_kwargs: Any) -> None:
        raise PermissionError("Acesso negado simulado")

    monkeypatch.setattr("rslapp.exporters.base.atomic_write_replace", _fail_write)

    with pytest.raises(RSLError) as exc_info:
        save_export_file(export_dir, "l-0001.ris", "conteúdo")
    assert exc_info.value.code == "export_folder_not_writable"
    assert "não aceita gravação" in exc_info.value.message


# FR-06, FR-12, UC-01, D-002: run_export integra leitura do Store, renderização e gravação
def test_fr06_fr12_uc01_d002_run_export_sucesso(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    work = Work(
        title="Artigo para Exportação",
        doi="10.1234/exp.2024",
        year=2024,
        type="article",
        authors=[Author(name="Ada Lovelace")],
    )
    _search, saved_list = store.record_search(
        {
            "kind": "terms",
            "query": "teste",
            "sources": [{"name": "openalex", "status": "ok", "query": "q", "found": 1, "fetched": 1}],
        },
        {"status": "complete", "works": [work.to_dict()]},
    )
    list_id = saved_list["id"]
    export_dir = tmp_path / "exports"

    res = run_export(store, list_id=list_id, export_format="ris", export_dir=export_dir)

    assert res["format"] == "ris"
    assert res["count"] == 1
    dest_file = Path(res["path"])
    assert dest_file == export_dir / f"{list_id}.ris"
    assert dest_file.exists()

    raw_bytes = dest_file.read_bytes()
    assert raw_bytes.startswith(b"TY  - JOUR\r\n")
    assert b"TI  - Artigo para Exporta" in raw_bytes
    assert raw_bytes.endswith(b"ER  - \r\n")

    with open(dest_file, encoding="utf-8", newline="") as f:
        content = f.read()
    assert content.startswith("TY  - JOUR\r\n")
    assert "TI  - Artigo para Exportação\r\n" in content
    assert content.endswith("ER  - \r\n")


# FR-12: Lista inexistente ou identificador malformado levanta RSLError('list_not_found')
@pytest.mark.parametrize("bad_list_id", ["l-9999", "l-invalido", "invalido", ""])
def test_fr12_run_export_lista_inexistente_ou_malformada(tmp_path: Path, bad_list_id: str) -> None:
    store = Store(tmp_path / "data")
    with pytest.raises(RSLError) as exc_info:
        run_export(store, list_id=bad_list_id, export_format="ris", export_dir=tmp_path / "exports")
    assert exc_info.value.code == "list_not_found"


# D-002: Formato desconhecido ou não suportado levanta RSLError('invalid_input')
@pytest.mark.parametrize("unsupported_format", ["xml", "bibtex", "unknown", ""])
def test_d002_run_export_formato_desconhecido(tmp_path: Path, unsupported_format: str) -> None:
    store = Store(tmp_path / "data")
    with pytest.raises(RSLError) as exc_info:
        run_export(store, list_id="l-0001", export_format=unsupported_format, export_dir=tmp_path / "exports")
    assert exc_info.value.code == "invalid_input"
