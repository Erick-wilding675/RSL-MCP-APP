"""Testes do pacote store/: listas, buscas, log.md, cache e gravação atômica."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from rslapp.store import Store, compute_cache_key


def _sample_search_s0007() -> tuple[dict[str, Any], dict[str, Any]]:
    """Devolve os dicionários de busca e lista correspondentes ao exemplo s-0007 da spec."""
    search_data: dict[str, Any] = {
        "id": "s-0007",
        "created_at": "2026-11-02T16:41:00Z",
        "kind": "terms",
        "request_summary": "Artigos sobre interpretabilidade de modelos de aprendizado de máquina",
        "list_id": "l-0007",
        "repeated_from": None,
        "origin": None,
        "sources": [
            {
                "name": "openalex",
                "query": "machine learning interpretability",
                "status": "ok",
                "reason": None,
                "found": 412,
                "fetched": 100,
                "from_cache": False,
                "fetched_at": None,
            },
            {
                "name": "semantic_scholar",
                "query": "machine learning interpretability",
                "status": "rate_limited",
                "reason": "HTTP 429 depois de 3 tentativas",
                "found": None,
                "fetched": None,
                "from_cache": False,
                "fetched_at": None,
            },
            {
                "name": "crossref",
                "query": "machine learning interpretability",
                "status": "ok",
                "reason": None,
                "found": 230,
                "fetched": 100,
                "from_cache": True,
                "fetched_at": "2026-11-01T09:15:00Z",
            },
        ],
    }
    list_data: dict[str, Any] = {
        "id": "l-0007",
        "search_id": "s-0007",
        "created_at": "2026-11-02T16:41:00Z",
        "status": "incomplete",
        "total": 187,
        "works": [{"doi": "10.1234/ex1", "title": "Interpretability in ML"}],
    }
    return search_data, list_data


# FR-05, FR-09, FR-12, FR-13, D-007: Gravar lista, busca e log e lê-las de volta iguais
def test_fr05_fr09_fr12_fr13_d007_gravar_e_ler_lista_busca_e_log_iguais(tmp_path: Path) -> None:
    store = Store(tmp_path / "data", cache_days=7)
    search_in, list_in = _sample_search_s0007()
    search_in.pop("id")
    search_in.pop("list_id")
    list_in.pop("id")
    list_in.pop("search_id")

    saved_search, saved_list = store.record_search(search_in, list_in)

    assert saved_search["id"] == "s-0001"
    assert saved_search["list_id"] == "l-0001"
    assert saved_list["id"] == "l-0001"
    assert saved_list["search_id"] == "s-0001"

    assert set(saved_search.keys()) == {
        "id",
        "created_at",
        "kind",
        "request_summary",
        "list_id",
        "repeated_from",
        "origin",
        "sources",
    }
    assert set(saved_list.keys()) == {
        "id",
        "search_id",
        "created_at",
        "status",
        "total",
        "works",
    }

    read_back_list = store.get_list("l-0001")
    read_back_search = store.get_search("s-0001")
    assert read_back_list == saved_list
    assert read_back_search == saved_search

    # D-007: Confirma UTF-8 sem escape ASCII e fim de linha \n
    for path in (
        store.lists_dir / "l-0001.json",
        store.searches_dir / "s-0001.json",
        store.log_path,
    ):
        raw_bytes = path.read_bytes()
        assert b"\r\n" not in raw_bytes
        assert "máquina".encode() in raw_bytes or path == store.lists_dir / "l-0001.json"


# FR-13, FR-05, NFR-06: Formato exato do log.md conforme a especificação
def test_fr13_fr05_nfr06_formato_log_md_exato_da_spec(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    search_data, list_data = _sample_search_s0007()

    store.record_search(search_data, list_data)

    expected = (
        "## s-0007 · 2026-11-02 16:41 UTC · busca por termos\n"
        "Pedido: Artigos sobre interpretabilidade de modelos de aprendizado de máquina\n"
        "Lista: l-0007 · incompleta · 187 artigos\n"
        "- openalex · ok · encontrados 412, trazidos 100 · cache: não · string: `machine learning interpretability`\n"
        "- semantic_scholar · rate_limited · HTTP 429 depois de 3 tentativas · string: `machine learning interpretability`\n"
        "- crossref · ok · encontrados 230, trazidos 100 · cache: sim, obtida em 2026-11-01 · string: `machine learning interpretability`\n"
    )
    assert store.read_log() == expected


# FR-05, FR-13, D-007: Ordem de gravação (lista -> busca -> log) e reconstrução byte a byte de log.md
def test_fr05_fr13_d007_ordem_gravacao_e_refazer_log_byte_a_byte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = Store(tmp_path / "data")
    published_order: list[str] = []

    real_link = os.link
    real_replace = os.replace

    def spy_link(src: str | Path, dst: str | Path) -> None:
        published_order.append(f"link:{Path(dst).name}")
        real_link(src, dst)

    def spy_replace(src: str | Path, dst: str | Path) -> None:
        published_order.append(f"replace:{Path(dst).name}")
        real_replace(src, dst)

    monkeypatch.setattr(os, "link", spy_link)
    monkeypatch.setattr(os, "replace", spy_replace)

    s1, l1 = _sample_search_s0007()
    s1.pop("id")
    s1.pop("list_id")
    l1.pop("id")
    l1.pop("search_id")
    store.record_search(s1, l1)

    assert published_order == [
        "link:l-0001.json",
        "link:s-0001.json",
        "replace:log.md",
    ]

    # Grava também busca de artigo, repetição, referências e citações
    extra_searches = [
        (
            {
                "created_at": "2026-11-02T17:00:00Z",
                "kind": "work",
                "request_summary": "Busca pelo artigo base",
                "sources": [
                    {
                        "name": "openalex",
                        "query": "10.1234/base",
                        "status": "ok",
                        "reason": None,
                        "found": 1,
                        "fetched": 1,
                        "from_cache": False,
                        "fetched_at": None,
                    }
                ],
            },
            {"created_at": "2026-11-02T17:00:00Z", "status": "complete", "total": 1, "works": []},
        ),
        (
            {
                "created_at": "2026-11-02T17:10:00Z",
                "kind": "repeat",
                "request_summary": "Repetição da busca inicial",
                "repeated_from": "s-0001",
                "sources": [
                    {
                        "name": "openalex",
                        "query": "machine learning interpretability",
                        "status": "ok",
                        "reason": None,
                        "found": 412,
                        "fetched": 100,
                        "from_cache": True,
                        "fetched_at": "2026-11-02T16:41:00Z",
                    }
                ],
            },
            {"created_at": "2026-11-02T17:10:00Z", "status": "complete", "total": 100, "works": []},
        ),
        (
            {
                "created_at": "2026-11-02T17:20:00Z",
                "kind": "related",
                "request_summary": "Citações do artigo base",
                "origin": {"work": "10.1234/base", "direction": "citations"},
                "sources": [
                    {
                        "name": "openalex",
                        "query": "cites:W123",
                        "status": "ok",
                        "reason": None,
                        "found": 15,
                        "fetched": 15,
                        "from_cache": False,
                        "fetched_at": None,
                    }
                ],
            },
            {"created_at": "2026-11-02T17:20:00Z", "status": "complete", "total": 15, "works": []},
        ),
        (
            {
                "created_at": "2026-11-02T17:30:00Z",
                "kind": "related",
                "request_summary": "Referências do artigo base",
                "origin": {"work": "10.1234/base", "direction": "references"},
                "sources": [
                    {
                        "name": "crossref",
                        "query": "refs:10.1234/base",
                        "status": "not_supported",
                        "reason": "Fonte não entrega referências",
                        "found": None,
                        "fetched": None,
                        "from_cache": False,
                        "fetched_at": None,
                    }
                ],
            },
            {"created_at": "2026-11-02T17:30:00Z", "status": "incomplete", "total": 0, "works": []},
        ),
    ]
    for s_data, l_data in extra_searches:
        store.record_search(s_data, l_data)

    original_bytes = store.log_path.read_bytes()
    original_text = store.read_log()
    assert "Repetida de: s-0001" in original_text
    assert "Artigo de origem: 10.1234/base · direção: citações" in original_text
    assert "Artigo de origem: 10.1234/base · direção: referências" in original_text
    assert "## s-0002 · 2026-11-02 17:00 UTC · busca de artigo" in original_text
    assert "## s-0003 · 2026-11-02 17:10 UTC · repetição" in original_text
    assert "## s-0004 · 2026-11-02 17:20 UTC · citações" in original_text
    assert "## s-0005 · 2026-11-02 17:30 UTC · referências" in original_text

    # Apaga log.md e reconstrói a partir de searches/
    store.log_path.unlink()
    assert not store.log_path.exists()

    rebuilt_text = store.rebuild_log()
    rebuilt_bytes = store.log_path.read_bytes()

    assert rebuilt_text == original_text
    assert rebuilt_bytes == original_bytes


# D-007: Interrupção simulada em os.fsync, os.link e os.replace não deixa arquivo pela metade nem .tmp
def test_d007_interrupcao_fsync_link_replace_nao_deixa_temporario_nem_corrompe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_dir = tmp_path / "data"
    store = Store(data_dir)

    # Grava estado inicial válido para provar que falha posterior preserva o conteúdo anterior
    s0, l0 = _sample_search_s0007()
    s0["id"] = "s-0001"
    s0["list_id"] = "l-0001"
    l0["id"] = "l-0001"
    l0["search_id"] = "s-0001"
    store.record_search(s0, l0)
    store.set_cache("openalex", {"q": "inicial"}, {"items": [1]}, fetched_at="2026-11-02T10:00:00Z")

    initial_log_bytes = store.log_path.read_bytes()
    cache_file = store.cache_path("openalex", {"q": "inicial"})
    initial_cache_bytes = cache_file.read_bytes()

    # 1. Falha em os.fsync
    def fail_fsync(_fd: int) -> None:
        raise OSError("falha simulada em os.fsync")

    monkeypatch.setattr(os, "fsync", fail_fsync)
    with pytest.raises(OSError, match="fsync"):
        store.save_list({"status": "complete", "total": 0, "works": []})
    with pytest.raises(OSError, match="fsync"):
        store.set_cache("openalex", {"q": "inicial"}, {"items": [999]})
    monkeypatch.undo()

    assert not (store.lists_dir / "l-0002.json").exists()
    assert cache_file.read_bytes() == initial_cache_bytes
    assert list(data_dir.rglob("*.tmp")) == []

    # 2. Falha em os.link
    def fail_link(_src: str | Path, _dst: str | Path) -> None:
        raise OSError("falha simulada em os.link")

    monkeypatch.setattr(os, "link", fail_link)
    with pytest.raises(OSError, match="link"):
        store.save_list({"status": "complete", "total": 0, "works": []})
    with pytest.raises(OSError, match="link"):
        store.save_search({"kind": "terms", "request_summary": "x", "sources": []})
    monkeypatch.undo()

    assert not (store.lists_dir / "l-0002.json").exists()
    assert not (store.searches_dir / "s-0002.json").exists()
    assert list(data_dir.rglob("*.tmp")) == []

    # 3. Falha em os.replace
    def fail_replace(_src: str | Path, _dst: str | Path) -> None:
        raise OSError("falha simulada em os.replace")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="replace"):
        store.append_log(s0, l0)
    with pytest.raises(OSError, match="replace"):
        store.set_cache("openalex", {"q": "inicial"}, {"items": [999]})
    monkeypatch.undo()

    assert store.log_path.read_bytes() == initial_log_bytes
    assert cache_file.read_bytes() == initial_cache_bytes
    assert list(data_dir.rglob("*.tmp")) == []

    # Pasta segue utilizável após todas as falhas
    saved = store.save_list({"status": "complete", "total": 0, "works": []})
    assert saved["id"] == "l-0002"
    assert (store.lists_dir / "l-0002.json").exists()


# D-007: No Windows, os.replace tenta novamente em caso de PermissionError transitório
def test_d007_replace_retenta_permission_error_no_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = Store(tmp_path / "data")
    real_replace = os.replace
    attempts = {"count": 0}

    def flaky_replace(src: str | Path, dst: str | Path) -> None:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise PermissionError("arquivo temporariamente em uso")
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", flaky_replace)
    store.set_cache("openalex", {"q": "retry"}, {"ok": True})
    assert attempts["count"] == 3
    assert store.get_cache("openalex", {"q": "retry"}) is not None


# FR-09, FR-12, D-007: Lista e busca já gravadas são imutáveis e não podem ser sobrescritas
def test_fr09_fr12_d007_lista_e_busca_ja_gravadas_nao_podem_ser_alteradas(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    s1, l1 = _sample_search_s0007()
    s1["id"] = "s-0001"
    s1["list_id"] = "l-0001"
    l1["id"] = "l-0001"
    l1["search_id"] = "s-0001"

    saved_search, saved_list = store.record_search(s1, l1)
    original_list_bytes = (store.lists_dir / "l-0001.json").read_bytes()
    original_search_bytes = (store.searches_dir / "s-0001.json").read_bytes()

    # Tentar gravar novamente com mesmo id levanta FileExistsError e preserva o arquivo original
    with pytest.raises(FileExistsError):
        store.save_list(
            {
                "id": "l-0001",
                "search_id": "s-0001",
                "status": "complete",
                "total": 999,
                "works": [],
            }
        )
    with pytest.raises(FileExistsError):
        store.save_search(
            {
                "id": "s-0001",
                "list_id": "l-0001",
                "kind": "terms",
                "request_summary": "Tentativa de sobrescrita",
                "sources": [],
            }
        )
    with pytest.raises(FileExistsError):
        store.record_search(s1, l1)

    assert (store.lists_dir / "l-0001.json").read_bytes() == original_list_bytes
    assert (store.searches_dir / "s-0001.json").read_bytes() == original_search_bytes

    # Mutar o dicionário devolvido em memória não altera o que está salvo
    saved_list["total"] = 0
    saved_list["works"].clear()
    fetched = store.get_list("l-0001")
    assert fetched["total"] == 187
    assert len(fetched["works"]) == 1
    fetched["total"] = 42
    assert store.get_list("l-0001")["total"] == 187
    assert store.get_search("s-0001") == saved_search


# FR-09, D-007: IDs crescem para 5 dígitos após 9999, ordenam numericamente e suportam threads simultâneas
def test_fr09_d007_ids_cinco_digitos_ordenacao_numerica_e_concorrencia_threads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = Store(tmp_path / "data")
    s_base, l_base = _sample_search_s0007()

    for num in (2, 9999):
        s_item = dict(
            s_base, id=f"s-{num:04d}", list_id=f"l-{num:04d}", request_summary=f"Busca {num}"
        )
        l_item = dict(l_base, id=f"l-{num:04d}", search_id=f"s-{num:04d}")
        store.record_search(s_item, l_item)

    # O próximo ID automático após 9999 tem 5 dígitos (10000)
    s_next = dict(s_base)
    s_next.pop("id")
    s_next.pop("list_id")
    s_next["request_summary"] = "Busca 10000"
    l_next = dict(l_base)
    l_next.pop("id")
    l_next.pop("search_id")
    saved_s10000, saved_l10000 = store.record_search(s_next, l_next)
    assert saved_s10000["id"] == "s-10000"
    assert saved_l10000["id"] == "l-10000"

    # A ordenação de searches/ e de rebuild_log é numérica (2, 9999, 10000), não alfabética
    searches = store.list_searches()
    assert [s["id"] for s in searches] == ["s-0002", "s-9999", "s-10000"]
    rebuilt = store.rebuild_log()
    assert rebuilt.index("## s-0002") < rebuilt.index("## s-9999") < rebuilt.index("## s-10000")

    # Se outra gravação criar o mesmo arquivo antes de os.link, tenta o próximo número sem sobrescrever
    race_store = Store(tmp_path / "race")
    real_link = os.link
    injected = {"done": False}

    def colliding_link(src: str | Path, dst: str | Path) -> None:
        dst_path = Path(dst)
        if not injected["done"] and dst_path.name == "l-0001.json":
            injected["done"] = True
            dst_path.write_text('{"id": "l-0001"}\n', encoding="utf-8")
        real_link(src, dst)

    monkeypatch.setattr(os, "link", colliding_link)
    auto_list = race_store.save_list({"status": "complete", "total": 0, "works": []})
    monkeypatch.undo()
    assert auto_list["id"] == "l-0002"
    assert (race_store.lists_dir / "l-0001.json").read_text(encoding="utf-8") == '{"id": "l-0001"}\n'

    # Concorrência com threads em nova pasta
    concurrent_store = Store(tmp_path / "concurrent")

    def worker(idx: int) -> tuple[str, str]:
        s_in = {
            "created_at": "2026-11-02T18:00:00Z",
            "kind": "terms",
            "request_summary": f"Thread {idx}",
            "sources": [
                {
                    "name": "openalex",
                    "query": f"topic {idx}",
                    "status": "ok",
                    "reason": None,
                    "found": 10,
                    "fetched": 10,
                    "from_cache": False,
                    "fetched_at": None,
                }
            ],
        }
        l_in = {"created_at": "2026-11-02T18:00:00Z", "status": "complete", "total": 10, "works": []}
        s_out, l_out = concurrent_store.record_search(s_in, l_in)
        return s_out["id"], l_out["id"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(worker, range(16)))

    search_ids = [r[0] for r in results]
    list_ids = [r[1] for r in results]
    assert len(set(search_ids)) == 16
    assert len(set(list_ids)) == 16
    assert sorted(search_ids) == [f"s-{i:04d}" for i in range(1, 17)]
    assert sorted(list_ids) == [f"l-{i:04d}" for i in range(1, 17)]


# NFR-06, D-007: Cache dentro do prazo devolve resposta com from_cache=True e fetched_at; vencido devolve None
def test_nfr06_d007_cache_no_prazo_vencido_e_validacao_de_fonte(tmp_path: Path) -> None:
    store = Store(tmp_path / "data", cache_days=7)
    query = {"b_param": 2, "a_param": "interpretability"}
    payload = {"results": [{"id": "W1", "title": "Paper 1"}]}

    # Ausente devolve None
    assert store.get_cache("openalex", query) is None

    # Grava com fetched_at conhecido
    cache_path = store.set_cache(
        "openalex",
        query,
        payload,
        fetched_at="2026-11-01T12:00:00Z",
    )
    assert cache_path.exists()

    # Dentro do prazo (6 dias depois)
    hit = store.get_cache("openalex", {"a_param": "interpretability", "b_param": 2}, now="2026-11-07T12:00:00Z")
    assert hit is not None
    assert hit["from_cache"] is True
    assert hit["fetched_at"] == "2026-11-01T12:00:00Z"
    assert hit["response"] == payload

    # Exatamente no instante de expiração (7 dias depois) e após (8 dias depois) -> ignorado (None)
    assert store.get_cache("openalex", query, now="2026-11-08T12:00:00Z") is None
    assert store.get_cache("openalex", query, now="2026-11-09T12:00:00Z") is None

    # Substituição de cache vencido por entrada nova
    store.set_cache("openalex", query, {"results": [{"id": "W2"}]}, fetched_at="2026-11-09T12:00:00Z")
    renewed = store.get_cache("openalex", query, now="2026-11-10T12:00:00Z")
    assert renewed is not None
    assert renewed["response"] == {"results": [{"id": "W2"}]}
    assert renewed["fetched_at"] == "2026-11-09T12:00:00Z"

    # Nome de fonte inválido levanta ValueError para nunca sair da pasta de dados
    for bad_source in ("", "../openalex", "OpenAlex", "open-alex", "a/b", r"a\b", "openalex!"):
        with pytest.raises(ValueError, match="fonte"):
            store.set_cache(bad_source, query, payload)
        with pytest.raises(ValueError, match="fonte"):
            store.get_cache(bad_source, query)


# NFR-03: Chaves de API nunca aparecem em nenhum arquivo gravado nem no nome/chave do cache
def test_nfr03_chave_api_nao_aparece_em_nenhum_arquivo_nem_na_chave_do_cache(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    store = Store(data_dir)

    secrets = [
        "fake-key-123-api_key",
        "fake-key-456-apikey",
        "fake-key-789-dash",
        "fake-key-012-plain",
        "fake-token-345-secret",
        "Bearer fake-auth-678-header",
    ]

    query_with_creds = {
        "search": "machine learning",
        "per_page": 50,
        "api_key": secrets[0],
        "APIKEY": secrets[1],
        "Api-Key": secrets[2],
        "KEY": secrets[3],
        "Token": secrets[4],
        "Authorization": secrets[5],
        "nested": {
            "api_key": secrets[0],
            "filter": "type:article",
        },
    }
    query_with_other_creds = {
        "per_page": 50,
        "search": "machine learning",
        "api_key": "other-fake-key-999",
        "nested": {"filter": "type:article"},
    }
    clean_query = {
        "search": "machine learning",
        "per_page": 50,
        "nested": {"filter": "type:article"},
    }

    # Mesma consulta com chaves diferentes (ou sem chave) gera o mesmo SHA-256 e cai no mesmo cache
    digest_creds, _ = compute_cache_key(query_with_creds)
    digest_other, _ = compute_cache_key(query_with_other_creds)
    digest_clean, _ = compute_cache_key(clean_query)
    assert digest_creds == digest_other == digest_clean

    cache_file = store.set_cache(
        "openalex",
        query_with_creds,
        {"ok": True},
        fetched_at="2026-11-02T10:00:00Z",
    )
    hit = store.get_cache("openalex", query_with_other_creds, now="2026-11-03T10:00:00Z")
    assert hit is not None
    assert hit["from_cache"] is True

    # Grava também busca, lista e log contendo parâmetros de credencial acidentais em URLs/dicts
    s_in, l_in = _sample_search_s0007()
    s_in["sources"][0]["query"] = (
        f"https://api.openalex.org/works?search=ml&api_key={secrets[0]}&apikey={secrets[1]}"
    )
    l_in["works"] = [{"doi": "10.1000/1", "title": "Artigo", "api_key": secrets[0]}]
    store.record_search(s_in, l_in)

    all_files = [p for p in data_dir.rglob("*") if p.is_file()]
    assert len(all_files) >= 4
    assert cache_file in all_files

    for file_path in all_files:
        content = file_path.read_text(encoding="utf-8")
        for secret in secrets:
            assert secret not in file_path.name
            assert secret not in content
        assert "fake-auth-678-header" not in content
