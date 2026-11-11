"""Testes unitários e de integração do exportador BibTeX (FR-06, D-014)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
import pytest

from rslapp import config, server
from rslapp.auth import AuthStore
from rslapp.core.errors import RSLError
from rslapp.core.models import Author, SourceResult, Work
from rslapp.exporters import BibTeXExporter, get_exporter, run_export
from rslapp.exporters.bibtex import (
    _clean_doi,
    _extract_author_key,
    _extract_title_key_word,
    _extract_year_key,
    _format_author_for_bibtex,
    escape_latex,
)
from rslapp.sources.base import Source
from rslapp.store import Store

ENV_VARS = (
    "RSL_DATA_DIR",
    "RSL_EXPORT_DIR",
    "RSL_CACHE_DAYS",
    "OPENALEX_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "RSL_CONTACT_EMAIL",
    "RSL_PUBLIC_URL",
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    """Isola variáveis de ambiente e configura diretórios temporários."""
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    data_dir = tmp_path / "rsl_data"
    export_dir = tmp_path / "rsl_exports"
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("RSL_EXPORT_DIR", str(export_dir))
    monkeypatch.setenv("RSL_PUBLIC_URL", "https://rsl.example.com")
    return data_dir, export_dir


class FakeBibTeXSource(Source):
    name = "openalex"

    def cache_query(self, query: str, max_results: int) -> dict[str, Any]:
        return {"search": query.strip(), "max_results": max_results}

    async def search(self, query: str, max_results: int = 100) -> SourceResult:
        work = Work(
            title="Fake Bibliometric Study",
            doi="10.1234/fake.001",
            year=2024,
            type="article",
            venue="Fake Journal of Informatics",
            authors=[Author(name="Ada Lovelace")],
            source_ids={"openalex": "W12345"},
        )
        return SourceResult(
            name="openalex",
            status="ok",
            query=f"search={query} · per_page={max_results}",
            found=1,
            fetched=1,
            works=[work],
        )


def _extract_jsonrpc_body(resp: httpx.Response) -> dict[str, Any]:
    if "text/event-stream" in resp.headers.get("content-type", ""):
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[len("data:") :].strip())
    return resp.json()


# FR-06, D-014: get_exporter localiza BibTeXExporter registrado e sua extensão é .bib
def test_fr06_d014_get_exporter_bibtex() -> None:
    exporter = get_exporter("bibtex")
    assert isinstance(exporter, BibTeXExporter)
    assert exporter.format == "bibtex"
    assert exporter.extension == "bib"


# FR-06: Escapa caracteres especiais do LaTeX, mantém acentos UTF-8 e converte quebras de linha em espaço
def test_fr06_escape_latex_completo() -> None:
    text = "AI & ML: 100% of {Special} $10 #1 _Features_ ^2 ~3 \\ Test\nNova linha\r\nOutra linha"
    escaped = escape_latex(text)
    assert r"\&" in escaped
    assert r"\%" in escaped
    assert r"\{" in escaped
    assert r"\}" in escaped
    assert r"\$" in escaped
    assert r"\#" in escaped
    assert r"\_" in escaped
    assert r"\textasciicircum{}" in escaped
    assert r"\textasciitilde{}" in escaped
    assert r"\textbackslash{}" in escaped
    assert "\n" not in escaped
    assert "\r" not in escaped

    # UTF-8 acentuado preservado sem escape
    accented = "Acentuação em Português: á é í ó ú ã õ ç"
    assert escape_latex(accented) == accented


# FR-06: Formatação de autor individual e corporativo
def test_fr06_format_author_for_bibtex() -> None:
    # Pessoa com Nome Sobrenome
    assert _format_author_for_bibtex(Author(name="Ada Lovelace")) == "Lovelace, Ada"
    # Pessoa já com Sobrenome, Nome
    assert _format_author_for_bibtex(Author(name="Silva, José")) == "Silva, José"
    # Pessoa com um único nome
    assert _format_author_for_bibtex(Author(name="Plato")) == "Plato"
    # Organização detectada por palavra-chave
    assert (
        _format_author_for_bibtex(Author(name="World Health Organization"))
        == "{World Health Organization}"
    )
    # Organização com caracteres LaTeX para escapar
    assert (
        _format_author_for_bibtex(Author(name="Research & Development Group"))
        == r"{Research \& Development Group}"
    )
    # Organização explícita em dict
    assert (
        _format_author_for_bibtex({"name": "Custom Consortium", "is_organization": True})
        == "{Custom Consortium}"
    )


# FR-06: Extração de chaves de citação (autor, ano, título)
def test_fr06_citation_key_parts() -> None:
    assert _extract_author_key([Author(name="José da Silva")]) == "silva"
    assert _extract_author_key([Author(name="Lovelace, Ada")]) == "lovelace"
    assert _extract_author_key([Author(name="World Health Organization")]) == "world"
    assert _extract_author_key([]) == "anon"
    assert _extract_author_key(None) == "anon"

    assert _extract_year_key(2021) == "2021"
    assert _extract_year_key("2024") == "2024"
    assert _extract_year_key(None) == "nd"
    assert _extract_year_key(0) == "nd"

    assert _extract_title_key_word("Machine Learning in Healthcare") == "machine"
    assert _extract_title_key_word("The Machine Learning Approach") == "machine"
    assert _extract_title_key_word("A Survey on Deep Learning") == "survey"
    assert _extract_title_key_word("O Aprendizado Profundo") == "aprendizado"
    assert _extract_title_key_word("") == "untitled"
    assert _extract_title_key_word(None) == "untitled"


# FR-06: Limpeza de prefixos de URL de DOI
def test_fr06_clean_doi() -> None:
    assert _clean_doi("https://doi.org/10.1234/test.1") == "10.1234/test.1"
    assert _clean_doi("http://dx.doi.org/10.1234/test.2") == "10.1234/test.2"
    assert _clean_doi("10.1234/plain.3") == "10.1234/plain.3"
    assert _clean_doi(None) is None
    assert _clean_doi("") is None


# FR-06, D-014: Teste campo a campo com artigo de periódico, preprint sem periódico,
# autor organização, título com &, %, _ e {, resumo com quebra de linha e artigo sem autor e sem ano
def test_fr06_d014_exportacao_bibtex_artigos_diversos_campo_a_campo() -> None:
    # 1. Artigo de periódico completo
    w1 = {
        "title": "Machine Learning in Healthcare",
        "doi": "https://doi.org/10.1000/182",
        "year": 2021,
        "type": "article",
        "venue": "Nature Medicine",
        "abstract": "A comprehensive study on medical AI.",
        "keywords": ["artificial intelligence", "healthcare"],
        "authors": [
            {"name": "José da Silva"},
            {"name": "Ada Lovelace"},
        ],
        "source_ids": {"openalex": "W100", "pubmed": "PM100"},
    }

    # 2. Preprint sem periódico
    w2 = {
        "title": "Preprint on Quantum Algorithms",
        "doi": "10.1000/183",
        "year": 2023,
        "type": "preprint",
        "venue": None,
        "authors": [{"name": "Alan Turing"}],
    }

    # 3. Autor organização
    w3 = {
        "title": "Global Health Guidelines",
        "year": 2020,
        "type": "report",
        "venue": "WHO Press",
        "authors": [{"name": "World Health Organization"}],
    }

    # 4. Título com &, %, _ e {
    w4 = {
        "title": "AI & Deep Learning: 100% of {Special} _Features_",
        "year": 2022,
        "type": "article",
        "venue": "AI Review",
        "authors": [{"name": "Claude Shannon"}],
    }

    # 5. Resumo com quebra de linha
    w5 = {
        "title": "Abstract With Newlines",
        "year": 2019,
        "type": "journal article",
        "venue": "Journal of Testing",
        "abstract": "First line of abstract.\nSecond line.\r\nThird line.",
        "authors": [{"name": "Grace Hopper"}],
    }

    # 6. Artigo sem autor e sem ano
    w6 = {
        "title": "Anonymous Technical Report",
        "type": "misc",
    }

    list_data = {"id": "l-test-01", "works": [w1, w2, w3, w4, w5, w6]}
    exporter = BibTeXExporter()
    rendered = exporter.render(list_data)

    entries = [e.strip() for e in rendered.strip().split("\n\n")]
    assert len(entries) == 6

    # Entrada 1: @article com journal, doi, url, title {{...}}, autor Sobrenome, Nome, note com Fontes
    e1 = entries[0]
    assert e1.startswith("@article{silva2021machine,")
    assert "  title = {{Machine Learning in Healthcare}}," in e1
    assert "  author = {Silva, José da and Lovelace, Ada}," in e1
    assert "  year = {2021}," in e1
    assert "  journal = {Nature Medicine}," in e1
    assert "  doi = {10.1000/182}," in e1
    assert "  url = {https://doi.org/10.1000/182}," in e1
    assert "  abstract = {A comprehensive study on medical AI.}," in e1
    assert "  keywords = {artificial intelligence, healthcare}," in e1
    assert "  note = {Fontes: openalex, pubmed}," in e1

    # Entrada 2: preprint sem periódico -> @misc, sem journal e sem howpublished
    e2 = entries[1]
    assert e2.startswith("@misc{turing2023preprint,")
    assert "journal = " not in e2
    assert "howpublished = " not in e2
    assert "  author = {Turing, Alan}," in e2
    assert "  year = {2023}," in e2

    # Entrada 3: autor organização -> {World Health Organization}, tipo @misc com howpublished
    e3 = entries[2]
    assert e3.startswith("@misc{world2020global,")
    assert "  author = {{World Health Organization}}," in e3
    assert "  howpublished = {WHO Press}," in e3
    assert "journal = " not in e3

    # Entrada 4: título com &, %, _ e { escapados
    e4 = entries[3]
    assert e4.startswith("@article{shannon2022ai,")
    assert r"  title = {{AI \& Deep Learning: 100\% of \{Special\} \_Features\_}}," in e4

    # Entrada 5: resumo com quebras de linha substituídas por espaço
    e5 = entries[4]
    assert e5.startswith("@article{hopper2019abstract,")
    assert "  abstract = {First line of abstract. Second line. Third line.}," in e5

    # Entrada 6: sem autor (anon) e sem ano (nd)
    e6 = entries[5]
    assert e6.startswith("@misc{anonndanonymous,")
    assert "author = " not in e6
    assert "year = " not in e6


# FR-06: Duas entradas com a mesma chave base viram …a e …b
def test_fr06_duas_entradas_mesma_chave_base_ganham_sufixos_a_e_b() -> None:
    w1 = {
        "title": "Machine Learning Approaches",
        "year": 2021,
        "type": "article",
        "venue": "Journal A",
        "authors": [{"name": "José da Silva"}],
    }
    w2 = {
        "title": "Machine Learning Methods",
        "year": 2021,
        "type": "article",
        "venue": "Journal B",
        "authors": [{"name": "José da Silva"}],
    }
    w3 = {
        "title": "Deep Learning Techniques",
        "year": 2021,
        "type": "article",
        "venue": "Journal C",
        "authors": [{"name": "Ada Lovelace"}],
    }

    list_data = {"id": "l-test-dups", "works": [w1, w2, w3]}
    rendered = BibTeXExporter().render(list_data)

    assert "@article{silva2021machinea," in rendered
    assert "@article{silva2021machineb," in rendered
    # O trabalho com chave única não ganha sufixo
    assert "@article{lovelace2021deep," in rendered


# FR-06: O arquivo lido de volta com um analisador simples tem uma entrada por artigo e chaves balanceadas
def test_fr06_analisador_simples_contagem_arrobas_e_chaves_balanceadas() -> None:
    works = [
        {
            "title": "Interpretable Machine Learning in Healthcare",
            "doi": "10.1234/iml.2024.001",
            "year": 2024,
            "type": "article",
            "venue": "Nature Machine Intelligence",
            "abstract": "We propose a novel framework for explainable AI with {nested} concepts.",
            "keywords": ["artificial intelligence", "healthcare & medicine"],
            "authors": [
                {"name": "Ada Lovelace"},
                {"name": "Research & Development Consortium", "is_organization": True},
            ],
            "source_ids": {"openalex": "W1", "crossref": "CR1"},
        },
        {
            "title": "Preprint on Complex Networks: 100% of _Nodes_",
            "year": 2023,
            "type": "preprint",
            "authors": [{"name": "Alan Turing"}],
        },
        {
            "title": "Guidelines on Health & Safety",
            "year": 2022,
            "type": "report",
            "venue": "Official Bulletin",
            "authors": [{"name": "World Health Organization"}],
        },
    ]

    rendered = BibTeXExporter().render({"works": works})
    assert rendered.endswith("\n")

    # Analisador simples: contagem de @ e balanceamento de chaves
    assert rendered.count("@") == len(works)

    # Divide em blocos iniciados por @
    raw_entries = [p for p in rendered.split("@") if p.strip()]
    assert len(raw_entries) == len(works)

    for entry in raw_entries:
        open_braces = entry.count("{")
        close_braces = entry.count("}")
        assert open_braces == close_braces, f"Chaves desbalanceadas na entrada:\n{entry}"
        assert open_braces >= 2  # Pelo menos @tipo{chave, ... }


# FR-06, D-014: export_list(format="bibtex") grava <list_id>.bib no stdio
def test_fr06_export_list_stdio_grava_arquivo_bib(
    isolated_env: tuple[Path, Path],
) -> None:
    data_dir, export_dir = isolated_env
    store = Store(data_dir)
    work = Work(
        title="Estudo Bibliométrico de Redes",
        doi="10.1000/184",
        year=2024,
        type="article",
        venue="Revista de Ciência da Informação",
        authors=[Author(name="Ada Lovelace")],
        source_ids={"openalex": "W99999"},
    )
    _search, saved_list = store.record_search(
        {
            "kind": "terms",
            "query": "bibliometria",
            "sources": [{"name": "openalex", "status": "ok", "query": "q", "found": 1, "fetched": 1}],
        },
        {"status": "complete", "works": [work.to_dict()]},
    )
    list_id = str(saved_list["id"])

    # Executa exportação via run_export e export_list
    res = run_export(store, list_id, "bibtex", export_dir)
    assert res["format"] == "bibtex"
    assert res["count"] == 1
    assert res["path"] == str(export_dir / f"{list_id}.bib")

    bib_path = export_dir / f"{list_id}.bib"
    assert bib_path.is_file()
    content = bib_path.read_text(encoding="utf-8")
    assert content.startswith("@article{lovelace2024estudo,")
    assert "  title = {{Estudo Bibliométrico de Redes}}," in content
    assert "  author = {Lovelace, Ada}," in content
    assert "  journal = {Revista de Ciência da Informação}," in content

    # Chamada direta da ferramenta MCP server.export_list
    server_res = server.export_list(list_id=list_id, format="bibtex")
    assert server_res["format"] == "bibtex"
    assert server_res["count"] == 1
    assert server_res["path"] == str(bib_path)


# FR-06, D-014: No modo HTTP, o download de .bib devolve application/x-bibtex; charset=utf-8
@pytest.mark.anyio
async def test_fr06_d014_export_list_http_download_tipo_mime(
    monkeypatch: pytest.MonkeyPatch,
    isolated_env: tuple[Path, Path],
) -> None:
    data_dir, _ = isolated_env
    monkeypatch.setattr(server, "_build_sources", lambda: [FakeBibTeXSource()])

    from rslapp import people

    if people.get("maria", data_dir=data_dir) is None:
        people.add("maria", data_dir=data_dir)

    access_token = AuthStore(data_dir=data_dir).issue_token_pair(
        person_id="maria",
        client_id="c-maria",
        scopes=["rsl"],
        resource="https://rsl.example.com/mcp",
    ).access_token

    http_cfg = config.HttpConfig(host="127.0.0.1", port=8000, public_url="https://rsl.example.com")
    app = server.create_http_app(http_cfg)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://rsl.example.com") as client,
    ):
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        init_resp = await client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"},
                },
            },
            headers=headers,
        )
        assert init_resp.status_code == 200
        call_headers = dict(headers)
        if session_id := init_resp.headers.get("mcp-session-id"):
            call_headers["mcp-session-id"] = session_id

        s_resp = await client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "search_works", "arguments": {"query": "bibliometrics", "sources": ["openalex"]}},
            },
            headers=call_headers,
        )
        assert s_resp.status_code == 200

        exp_resp = await client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "export_list", "arguments": {"list_id": "l-0001", "format": "bibtex"}},
            },
            headers=call_headers,
        )
        assert exp_resp.status_code == 200
        exp_data = _extract_jsonrpc_body(exp_resp)
        payload = exp_data["result"]["structuredContent"]
        assert "path" not in payload
        assert payload["format"] == "bibtex"
        assert payload["count"] == 1
        assert payload["download_url"].startswith("https://rsl.example.com/downloads/")
        assert "expires_at" in payload

        dl_path = urlsplit(payload["download_url"]).path
        dl_resp = await client.get(dl_path)
        assert dl_resp.status_code == 200
        assert dl_resp.headers.get("content-type") == "application/x-bibtex; charset=utf-8"
        assert 'filename="l-0001.bib"' in dl_resp.headers.get("content-disposition", "")
        assert dl_resp.content.startswith(b"@article{lovelace2024fake,")


# FR-06: export_list com formato desconhecido continua dando o mesmo erro invalid_input
def test_fr06_export_list_formato_desconhecido_continua_com_mesmo_erro(
    isolated_env: tuple[Path, Path],
) -> None:
    data_dir, export_dir = isolated_env
    store = Store(data_dir)
    work = Work(title="Qualquer Obra")
    _search, saved_list = store.record_search(
        {
            "kind": "terms",
            "query": "qualquer",
            "sources": [{"name": "openalex", "status": "ok", "query": "q", "found": 1, "fetched": 1}],
        },
        {"status": "complete", "works": [work.to_dict()]},
    )
    list_id = str(saved_list["id"])

    with pytest.raises(RSLError) as exc_info:
        run_export(store, list_id, "formato_inexistente", export_dir)
    assert exc_info.value.code == "invalid_input"
    assert "Formato inválido ou não suportado" in exc_info.value.message


# FR-06: Lista vazia não exporta em bibtex e não cria arquivo
def test_fr06_export_list_vazia_em_bibtex_recusa_com_empty_list(
    isolated_env: tuple[Path, Path],
) -> None:
    data_dir, export_dir = isolated_env
    store = Store(data_dir)
    _search, saved_list = store.record_search(
        {
            "kind": "terms",
            "query": "sem resultados",
            "sources": [{"name": "openalex", "status": "ok", "query": "q", "found": 0, "fetched": 0}],
        },
        {"status": "complete", "works": []},
    )
    list_id = str(saved_list["id"])

    with pytest.raises(RSLError) as exc_info:
        run_export(store, list_id, "bibtex", export_dir)
    assert exc_info.value.code == "empty_list"
    assert not (export_dir / f"{list_id}.bib").exists()
