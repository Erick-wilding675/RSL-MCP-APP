"""Testes unitários do modelo e armazenamento de Protocolos Metodológicos (FR-30, D-041)."""

import zipfile
from pathlib import Path

import pytest

from rslapp.core.errors import RSLError
from rslapp.core.protocols import (
    format_protocol_markdown,
    generate_protocol_id,
    sanitize_protocol_id,
    validate_protocol_data,
)
from rslapp.core.reproducibility import build_reproducibility_package
from rslapp.store import Store


def test_sanitize_and_generate_protocol_id():
    pid = generate_protocol_id()
    assert pid.startswith("prot_")
    assert len(pid) > 5

    clean = sanitize_protocol_id("Protocolo: 2026/01 *Final*")
    assert clean == "protocolo__2026_01__final_"


def test_validate_protocol_data_valid():
    data = validate_protocol_data(
        title="Impacto de IA na Educação Médica",
        framework="pico",
        question="Qual o impacto de agentes conversacionais no aprendizado clínico?",
        subquestions=["Há melhora no diagnóstico?", "Qual a percepção dos estudantes?"],
        components={
            "population": "Estudantes de medicina em internato",
            "intervention": "Uso de tutores baseados em IA",
            "comparison": "Ensino tradicional sem IA",
            "outcome": "Acurácia diagnóstica e retenção de conteúdo",
        },
        inclusion_criteria=["Ensaios clínicos randomizados", "Estudos quase-experimentais"],
        exclusion_criteria=["Opiniões de especialistas sem dados empíricos"],
        planned_sources=["openalex", "pubmed"],
        search_strategy="('artificial intelligence' OR 'LLM') AND 'medical education'",
        languages=["pt", "en"],
        date_range={"start_year": 2018, "end_year": 2026},
        authors=["Erick Mendes", "Orientador"],
        status="registered",
        registration_platform="PROSPERO",
        registration_number="CRD42026999999",
        ai_assisted=True,
        ai_model="Claude 3.5 Sonnet",
    )

    assert data["title"] == "Impacto de IA na Educação Médica"
    assert data["framework"] == "pico"
    assert data["version"] == 1
    assert len(data["subquestions"]) == 2
    assert data["components"]["population"] == "Estudantes de medicina em internato"
    assert "study_design" in data["components"]  # Chave esperada preenchida como vazia
    assert data["status"] == "registered"
    assert data["registration_number"] == "CRD42026999999"
    assert data["ai_assisted"] is True
    assert data["ai_model"] == "Claude 3.5 Sonnet"


def test_validate_protocol_data_invalid():
    # Título vazio
    with pytest.raises(RSLError) as exc:
        validate_protocol_data(title="", question="Pergunta?")
    assert exc.value.code == "invalid_input"

    # Pergunta vazia
    with pytest.raises(RSLError) as exc:
        validate_protocol_data(title="Título", question="")
    assert exc.value.code == "invalid_input"

    # Framework desconhecido
    with pytest.raises(RSLError) as exc:
        validate_protocol_data(title="Título", question="Pergunta?", framework="desconhecido")
    assert exc.value.code == "invalid_input"

    # Status inválido
    with pytest.raises(RSLError) as exc:
        validate_protocol_data(title="Título", question="Pergunta?", status="invalid_status")
    assert exc.value.code == "invalid_input"


def test_format_protocol_markdown():
    protocol = validate_protocol_data(
        protocol_id="prot_teste_01",
        title="Protocolo de Revisão de Escopo sobre RSL com IA",
        framework="pcc",
        question="Como ferramentas de IA apoiam revisões de literatura científica?",
        components={
            "population": "Pesquisadores e pós-graduandos",
            "concept": "Sistemas de síntese baseados em LLM",
            "context": "Ambiente acadêmico global",
        },
        inclusion_criteria=["Artigos revisados por pares"],
        exclusion_criteria=["Editoriais"],
        planned_sources=["openalex", "semanticscholar", "bdtd"],
        search_strategy="AI AND 'systematic review'",
        ai_assisted=True,
        ai_model="Gemini 1.5 Pro",
    )

    md = format_protocol_markdown(protocol)
    assert "# Protocolo de Revisão de Escopo sobre RSL com IA" in md
    assert "PCC (População, Conceito, Contexto - Padrão JBI)" in md
    assert "Como ferramentas de IA apoiam revisões de literatura científica?" in md
    assert "Pesquisadores e pós-graduandos" in md
    assert "Critérios de Inclusão" in md
    assert "[x] Artigos revisados por pares" in md
    assert "[ ] Editoriais" in md
    assert "OPENALEX, SEMANTICSCHOLAR, BDTD" in md
    assert "Gemini 1.5 Pro" in md


def test_store_protocol_crud_and_versioning(tmp_path: Path):
    store = Store(data_dir=tmp_path / "data")

    # 1. Criação da primeira versão
    p1 = store.save_protocol({
        "id": "p_meta_01",
        "title": "Versão Inicial do Protocolo",
        "framework": "pico",
        "question": "Pergunta inicial?",
        "inclusion_criteria": ["Critério 1"],
    })

    assert p1["id"] == "p_meta_01"
    assert p1["version"] == 1
    assert p1["title"] == "Versão Inicial do Protocolo"

    # Verifica get_protocol
    retrieved = store.get_protocol("p_meta_01")
    assert retrieved is not None
    assert retrieved["version"] == 1

    # 2. Atualização do protocolo gerando versão 2 e arquivando histórico
    p2 = store.save_protocol({
        "id": "p_meta_01",
        "title": "Protocolo Atualizado com Novos Critérios",
        "framework": "pico",
        "question": "Pergunta refinada?",
        "inclusion_criteria": ["Critério 1", "Critério 2"],
    })

    assert p2["version"] == 2
    assert p2["title"] == "Protocolo Atualizado com Novos Critérios"
    assert len(p2["history"]) == 1
    assert p2["history"][0]["version"] == 1

    # Recupera versão atual
    cur = store.get_protocol("p_meta_01")
    assert cur["version"] == 2
    assert cur["title"] == "Protocolo Atualizado com Novos Critérios"

    # Recupera versão antiga arquivada
    v1 = store.get_protocol("p_meta_01", version=1)
    assert v1 is not None
    assert v1["version"] == 1
    assert v1["title"] == "Versão Inicial do Protocolo"

    # 3. Lista de protocolos
    store.save_protocol({
        "id": "p_outro_02",
        "title": "Outro Estudo",
        "framework": "spider",
        "question": "Outra pergunta?",
    })

    protocols = store.list_protocols()
    assert len(protocols) == 2
    assert {p["id"] for p in protocols} == {"p_meta_01", "p_outro_02"}

    # 4. Exclusão de protocolo e histórico
    assert store.delete_protocol("p_meta_01") is True
    assert store.get_protocol("p_meta_01") is None
    assert store.get_protocol("p_meta_01", version=1) is None
    assert len(store.list_protocols()) == 1


def test_reproducibility_package_includes_protocol(tmp_path: Path):
    store = Store(data_dir=tmp_path / "data")

    # Cria protocolo
    store.save_protocol({
        "id": "prot_rep_01",
        "title": "Protocolo Integrado de Reprodutibilidade",
        "framework": "pico",
        "question": "Pergunta de teste para o pacote?",
        "inclusion_criteria": ["Apenas ensaios clínicos"],
    })

    # Cria busca e lista associada
    list_data = {
        "query": "teste reprodutibilidade",
        "protocol_id": "prot_rep_01",
        "status": "complete",
        "works": [
            {
                "id": "w1",
                "title": "Paper de Teste",
                "authors": [{"name": "Autor Um"}],
                "year": 2024,
                "sources": [{"name": "openalex", "id": "W1"}],
            }
        ],
    }
    search_data = {
        "kind": "terms",
        "query": "teste reprodutibilidade",
        "request_summary": "teste reprodutibilidade",
        "protocol_id": "prot_rep_01",
        "sources": [{"name": "openalex", "status": "ok", "query": "q", "count": 1}],
    }
    _saved_search, saved_list = store.record_search(search_data, list_data)
    list_id = saved_list["id"]

    export_dir = tmp_path / "exports"
    result = build_reproducibility_package(list_id, store, export_dir=export_dir)

    zip_file_path = Path(result["path"])
    assert zip_file_path.exists()

    with zipfile.ZipFile(zip_file_path, "r") as zf:
        names = zf.namelist()
        assert "protocol.md" in names
        assert "protocol.json" in names
        assert "checksums.sha256" in names

        checksums = zf.read("checksums.sha256").decode("utf-8")
        assert "protocol.md" in checksums
        assert "protocol.json" in checksums

        md_content = zf.read("protocol.md").decode("utf-8")
        assert "Protocolo Integrado de Reprodutibilidade" in md_content
