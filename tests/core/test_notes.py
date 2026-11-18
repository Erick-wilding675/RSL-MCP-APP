"""Testes unitários para o módulo de fichamento científico (FR-29, D-040)."""

from __future__ import annotations

from pathlib import Path

import pytest

from rslapp.core.errors import RSLError
from rslapp.core.notes import (
    format_note_markdown,
    format_notes_compilation,
    sanitize_filename_id,
    validate_note_data,
)
from rslapp.core.reproducibility import build_reproducibility_package
from rslapp.store import Store


def test_sanitize_filename_id() -> None:
    assert sanitize_filename_id("10.1000/182:xyz") == "10.1000_182_xyz"
    assert sanitize_filename_id("  W12345  ") == "W12345"


def test_validate_note_data_valid() -> None:
    note = validate_note_data(
        list_id="l-0001",
        work_id="W1",
        title="Estudo sobre IA na Educação",
        authors=["Silva, J.", "Santos, M."],
        year=2024,
        doi="10.1234/edu.2024",
        objective="Analisar o impacto de LLMs no ensino superior.",
        methodology="Estudo de caso qualitativo com 50 estudantes.",
        sample="50 estudantes de graduação em Pedagogia.",
        results="Aumento de 35% no engajamento autorrelatado.",
        limitations="Amostra restrita a uma única universidade.",
        personal_keywords=["inteligência artificial", "ensino superior", "pedagogia"],
        synthesis="Artigo fundamental para a seção de discussão da tese.",
        direct_quotes=[
            {"quote": "A IA não substitui o docente, mas amplifica sua mediação.", "page": "14", "comment": "Citação-chave para o capítulo 2"},
        ],
        source="ai_suggested",
        ai_model="Claude 3.5 Sonnet",
    )

    assert note["list_id"] == "l-0001"
    assert note["work_id"] == "W1"
    assert note["year"] == 2024
    assert note["source"] == "ai_suggested"
    assert note["ai_model"] == "Claude 3.5 Sonnet"
    assert len(note["direct_quotes"]) == 1
    assert note["direct_quotes"][0]["page"] == "14"
    assert len(note["personal_keywords"]) == 3


def test_validate_note_data_invalid_source() -> None:
    with pytest.raises(RSLError) as exc:
        validate_note_data(
            list_id="l-0001",
            work_id="W1",
            source="alien_source",
        )
    assert exc.value.code == "invalid_input"
    assert "alien_source" in exc.value.message


def test_validate_note_data_missing_ids() -> None:
    with pytest.raises(RSLError) as exc1:
        validate_note_data(list_id="", work_id="W1")
    assert exc1.value.code == "invalid_input"

    with pytest.raises(RSLError) as exc2:
        validate_note_data(list_id="l-0001", work_id="   ")
    assert exc2.value.code == "invalid_input"


def test_store_notes_crud(tmp_path: Path) -> None:
    store = Store(tmp_path)
    # Cria lista de teste
    store.record_search(
        {
            "id": "s-0001",
            "request_summary": "Revisão sobre IA",
            "kind": "terms",
            "terms": "AI",
            "sources": [{"name": "openalex", "status": "complete", "total": 1, "works": 1}],
        },
        {
            "id": "l-0001",
            "search_id": "s-0001",
            "query": "AI",
            "status": "complete",
            "total": 1,
            "works": [{"id": "W1", "title": "Paper 1", "year": 2024}],
        },
    )

    # 1. Salvar nota
    saved = store.save_note(
        "l-0001",
        {
            "work_id": "W1",
            "objective": "Objetivo do Paper 1",
            "source": "ai_suggested",
            "ai_model": "Gemini 1.5 Pro",
        },
    )
    assert saved["work_id"] == "W1"
    assert saved["objective"] == "Objetivo do Paper 1"

    # 2. Ler nota
    retrieved = store.get_note("l-0001", "W1")
    assert retrieved is not None
    assert retrieved["objective"] == "Objetivo do Paper 1"
    assert retrieved["source"] == "ai_suggested"

    # 3. Listar notas
    all_notes = store.list_notes("l-0001")
    assert len(all_notes) == 1
    assert all_notes[0]["work_id"] == "W1"

    # 4. Atualizar nota para human_reviewed
    updated = store.save_note(
        "l-0001",
        {
            "work_id": "W1",
            "objective": "Objetivo revisado",
            "source": "human_reviewed",
            "reviewed_by": "Dr. Erick Mendes",
        },
    )
    assert updated["source"] == "human_reviewed"
    assert updated["reviewed_by"] == "Dr. Erick Mendes"

    # 5. Deletar nota
    deleted = store.delete_note("l-0001", "W1")
    assert deleted is True
    assert store.get_note("l-0001", "W1") is None
    assert len(store.list_notes("l-0001")) == 0


def test_format_note_markdown_and_compilation() -> None:
    note = {
        "list_id": "l-0001",
        "work_id": "W1",
        "title": "Machine Learning in Systematic Reviews",
        "authors": ["Mendes, E.", "Silva, A."],
        "year": 2024,
        "doi": "10.1016/j.jbi.2024.1001",
        "abnt_reference": "MENDES, E.; SILVA, A. Machine Learning. 2024.",
        "objective": "Avaliar precisão de triagem automatizada.",
        "methodology": "Simulação retrospectiva em 10 revisões Cochrane.",
        "sample": "10.000 títulos e resumos.",
        "results": "Redução de 40% no esforço de triagem mantendo 99% de sensibilidade.",
        "limitations": "Restrito à área biomédica.",
        "personal_keywords": ["automação", "revisão sistemática"],
        "synthesis": "Artigo indispensável para o capítulo metodológico.",
        "direct_quotes": [
            {"quote": "Triagem assistida não elimina o julgamento humano.", "page": "5", "comment": "Citação direta"},
        ],
        "source": "human_reviewed",
        "reviewed_by": "Erick",
        "created_at": "2026-11-18T12:00:00Z",
    }

    md = format_note_markdown(note)
    assert "---" in md
    assert 'title: "Machine Learning in Systematic Reviews"' in md
    assert "authors:" in md
    assert "> **Referência ABNT:** MENDES, E.; SILVA, A." in md
    assert "[!NOTE] Rastro de Autoria: Revisado por Humano" in md
    assert "## 1. Objetivo da Pesquisa" in md
    assert "## 6. Citações Diretas" in md
    assert '`#automação`' in md

    # Compilação
    compilation = format_notes_compilation([note], list_id="l-0001", list_title="Revisão IA")
    assert "# Fichamento Científico Consolidado · Revisão IA" in md or "## Índice das Fichas" in compilation
    assert "1. [Machine Learning in Systematic Reviews](#artigo-W1)" in compilation


def test_reproducibility_package_includes_notes(tmp_path: Path) -> None:
    store = Store(tmp_path)
    store.record_search(
        {
            "id": "s-0001",
            "request_summary": "Revisão com Fichas",
            "kind": "terms",
            "terms": "ML",
            "sources": [{"name": "openalex", "status": "complete", "total": 1, "works": 1}],
        },
        {
            "id": "l-0001",
            "search_id": "s-0001",
            "query": "ML",
            "status": "complete",
            "total": 1,
            "works": [
                {
                    "id": "W100",
                    "title": "Machine Learning Paper",
                    "year": 2023,
                    "doi": "10.1000/1",
                    "authors": [{"name": "Autor Teste"}],
                    "source_ids": {"openalex": "W100"},
                }
            ],
        },
    )

    # Adiciona ficha
    store.save_note(
        "l-0001",
        {
            "work_id": "W100",
            "objective": "Objetivo do estudo",
            "results": "Resultados importantes",
            "source": "human_reviewed",
        },
    )

    export_dir = tmp_path / "exports"
    result = build_reproducibility_package("l-0001", store, export_dir=export_dir)

    assert result["file_count"] == 17  # 11 originais + 3 rede + notes.md + notes.json + checksums.sha256
    zip_path = Path(result["path"])
    assert zip_path.exists()

    # Valida presença e integridade de notes.md no zip
    import zipfile
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert "notes.md" in names
        assert "notes.json" in names
        notes_content = zf.read("notes.md").decode("utf-8")
        assert "Fichamento Científico Consolidado" in notes_content
        checksums = zf.read("checksums.sha256").decode("utf-8")
        assert "notes.md" in checksums
        assert "notes.json" in checksums
