"""Testes do pacote store/: listas, buscas, log.md, cache e gravação atômica."""

from __future__ import annotations

import multiprocessing
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from rslapp.store import Store, compute_cache_key
from rslapp.store._atomic import atomic_write_exclusive, strip_url_credentials


def _src(
    name: str = "openalex", query: str = "machine learning interpretability",
    status: str = "ok", reason: str | None = None, found: int | None = 10,
    fetched: int | None = 10, from_cache: bool = False, fetched_at: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "name": name, "query": query, "status": status, "reason": reason,
        "found": found, "fetched": fetched, "from_cache": from_cache,
        "fetched_at": fetched_at, **extra,
    }


def _search(
    kind: str = "terms",
    request_summary: str = "Artigos sobre interpretabilidade de modelos de aprendizado de máquina",
    sources: list[dict[str, Any]] | None = None, created_at: str = "2026-11-02T16:41:00Z",
    repeated_from: str | None = None, origin: dict[str, Any] | None = None, **extra: Any,
) -> dict[str, Any]:
    return {
        "created_at": created_at, "kind": kind, "request_summary": request_summary,
        "repeated_from": repeated_from, "origin": origin,
        "sources": [_src()] if sources is None else sources, **extra,
    }


def _list(
    status: str = "complete", total: int = 1, works: list[dict[str, Any]] | None = None,
    created_at: str = "2026-11-02T16:41:00Z", **extra: Any,
) -> dict[str, Any]:
    default_works = [{"doi": "10.1234/ex1", "title": "Revisão sistemática de ML"}]
    return {
        "created_at": created_at, "status": status, "total": total,
        "works": default_works if works is None else works, **extra,
    }


def _mp_worker(args: tuple[str, int, int]) -> list[tuple[str, str]]:
    data_dir, worker_id, count = args
    st = Store(data_dir)
    out: list[tuple[str, str]] = []
    for i in range(count):
        s, lst = st.record_search(
            _search(request_summary=f"Proc {worker_id}-{i}", sources=[_src(query=f"q={worker_id}.{i}")]),
            _list(total=1),
        )
        out.append((s["id"], lst["id"]))
    return out


# FR-05, FR-09, FR-12, FR-13, D-007: Gravar lista, busca e log e lê-las de volta iguais à entrada
def test_fr05_fr09_fr12_fr13_d007_gravar_e_ler_lista_busca_e_log_iguais_a_entrada(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "data", cache_days=7)
    work_item = {
        "doi": "10.1234/ex1",
        "title": "Does machine learning work? A systematic review",
        "abstract": "Estudo sobre revisão sistemática com limiar key=0.5 e acentuação.",
        "key": "W-001",
        "custom_meta": {"score": 0.95, "tags": ["ml", "x=1?y=2"]},
    }
    search_in = _search(
        request_summary="Does machine learning work? Revisão com key=0.5 e token=abc",
        sources=[_src(query="title:Does machine learning work? key=0.5", extra_src_flag=True)],
        extra_search_field=42,
    )
    list_in = _list(status="incomplete", total=187, works=[work_item], extra_list_field="ok")

    saved_search, saved_list = store.record_search(search_in, list_in)
    expected_search = {**search_in, "id": "s-0001", "list_id": "l-0001"}
    expected_list = {**list_in, "id": "l-0001", "search_id": "s-0001"}
    assert saved_search == expected_search
    assert saved_list == expected_list
    assert store.get_search("s-0001") == expected_search
    assert store.get_list("l-0001") == expected_list

    cache_file = store.set_cache(
        "openalex", {"q": "interpretação"}, {"nota": "coração"}, fetched_at="2026-11-02T10:00:00Z"
    )
    for path, word in (
        (store.lists_dir / "l-0001.json", "revisão"),
        (store.searches_dir / "s-0001.json", "Revisão"),
        (store.log_path, "Revisão"),
        (cache_file, "coração"),
    ):
        raw_bytes = path.read_bytes()
        assert b"\r\n" not in raw_bytes
        assert word.encode("utf-8") in raw_bytes


# FR-13, FR-05, NFR-06: Formato exato do log.md, reason em ok, singular, UTC, quebras de linha e validação
def test_fr13_fr05_nfr06_formato_log_md_regras_e_validacao_previa(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    store.lists_dir.mkdir(parents=True, exist_ok=True)
    (store.lists_dir / "l-0006.json").write_text('{"id":"l-0006"}\n', encoding="utf-8")

    s7 = _search(
        sources=[
            _src("openalex", found=412, fetched=100),
            _src(
                "semantic_scholar", status="rate_limited",
                reason="HTTP 429 depois de 3 tentativas", found=None, fetched=None,
            ),
            _src(
                "crossref", found=230, fetched=100,
                from_cache=True, fetched_at="2026-10-31T22:30:00-03:00",
            ),
        ]
    )
    store.record_search(s7, _list(status="incomplete", total=187))
    expected = (
        "## s-0007 · 2026-11-02 16:41 UTC · busca por termos\n"
        "Pedido: Artigos sobre interpretabilidade de modelos de aprendizado de máquina\n"
        "Lista: l-0007 · incompleta · 187 artigos\n"
        "- openalex · ok · encontrados 412, trazidos 100 · cache: não · string: `machine learning interpretability`\n"
        "- semantic_scholar · rate_limited · HTTP 429 depois de 3 tentativas · string: `machine learning interpretability`\n"
        "- crossref · ok · encontrados 230, trazidos 100 · cache: sim, obtida em 2026-11-01 · string: `machine learning interpretability`\n"
    )
    assert store.read_log() == expected

    clean_store = Store(tmp_path / "clean")
    for bad_s, bad_l in (
        (_search(kind="bogus"), _list()),
        (_search(kind="related", origin=None), _list()),
        (_search(), _list(status="bogus")),
        (_search(sources=[{"name": "openalex"}]), _list()),
    ):
        with pytest.raises(ValueError):
            clean_store.record_search(bad_s, bad_l)
    assert not clean_store.lists_dir.exists() or list(clean_store.lists_dir.iterdir()) == []


# FR-05, FR-13, D-007: Ordem lista->busca->log, refazer log byte a byte, lista ausente e quebras
def test_fr05_fr13_d007_ordem_gravacao_e_refazer_log_byte_a_byte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = Store(tmp_path / "data")
    order: list[str] = []
    real_link, real_replace = os.link, os.replace
    monkeypatch.setattr(os, "link", lambda s, d: (order.append(f"link:{Path(d).name}"), real_link(s, d))[1])
    monkeypatch.setattr(os, "replace", lambda s, d: (order.append(f"replace:{Path(d).name}"), real_replace(s, d))[1])

    store.record_search(
        _search(
            kind="work", request_summary="Linha 1\n## s-0099 forjado",
            sources=[_src(query="q1\nq2", reason="teto de 1000\natingido", found=1, fetched=1)],
        ),
        _list(status="complete", total=1),
    )
    assert order == ["link:l-0001.json", "link:s-0001.json", "replace:log.md"]

    store.record_search(_search(kind="repeat", repeated_from="s-0001"), _list(status="complete", total=2))
    store.record_search(
        _search(kind="related", origin={"work": "10.1/a", "direction": "citations"}),
        _list(total=0, status="incomplete"),
    )
    store.record_search(
        _search(kind="related", origin={"work": "10.1/a", "direction": "references"}),
        _list(total=3, status="complete"),
    )

    orig_bytes, orig_text = store.log_path.read_bytes(), store.read_log()
    assert "\n## s-0099" not in orig_text
    assert "Lista: l-0001 · completa · 1 artigo\n" in orig_text
    assert "teto de 1000 atingido" in orig_text
    assert "Repetida de: s-0001" in orig_text
    assert "Artigo de origem: 10.1/a · direção: citações" in orig_text
    assert "Artigo de origem: 10.1/a · direção: referências" in orig_text

    store.log_path.unlink()
    assert store.rebuild_log() == orig_text
    assert store.log_path.read_bytes() == orig_bytes

    (store.lists_dir / "l-0001.json").unlink()
    assert "Lista: l-0001 · arquivo ausente\n" in store.rebuild_log()


# D-007: Interrupção em fsync, link da busca e replace; fallback Windows os.rename e erro POSIX
def test_d007_interrupcoes_record_search_fallback_link_e_retry_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = Store(tmp_path / "data")
    store.record_search(_search(), _list())
    cache_file = store.set_cache("openalex", {"q": "1"}, {"v": 1}, fetched_at="2026-11-02T10:00:00Z")
    init_cache = cache_file.read_bytes()

    monkeypatch.setattr(os, "fsync", lambda _fd: (_ for _ in ()).throw(OSError("fsync falhou")))
    with pytest.raises(OSError, match="fsync"):
        store.record_search(_search(), _list())
    with pytest.raises(OSError, match="fsync"):
        store.set_cache("openalex", {"q": "1"}, {"v": 2})
    monkeypatch.undo()
    assert not (store.lists_dir / "l-0002.json").exists()
    assert cache_file.read_bytes() == init_cache

    real_link = os.link

    def fail_on_search_link(src: str | Path, dst: str | Path) -> None:
        if Path(dst).name == "s-0002.json":
            raise OSError("falha simulada no link da busca")
        real_link(src, dst)

    monkeypatch.setattr(os, "link", fail_on_search_link)
    monkeypatch.setattr(os, "rename", lambda _s, _d: (_ for _ in ()).throw(OSError("falha simulada no link da busca")))
    with pytest.raises(OSError, match="link da busca"):
        store.record_search(_search(), _list())
    monkeypatch.undo()
    assert (store.lists_dir / "l-0002.json").exists()
    assert not (store.searches_dir / "s-0002.json").exists()
    assert list(store.data_dir.rglob("*.tmp")) == []

    s_next, l_next = store.record_search(_search(), _list())
    assert (s_next["id"], l_next["id"]) == ("s-0003", "l-0003")

    log_before = store.log_path.read_bytes()
    monkeypatch.setattr(os, "replace", lambda _s, _d: (_ for _ in ()).throw(OSError("replace falhou")))
    with pytest.raises(OSError, match="replace"):
        store.set_cache("openalex", {"q": "1"}, {"v": 9})
    monkeypatch.undo()
    assert cache_file.read_bytes() == init_cache
    assert store.log_path.read_bytes() == log_before
    assert list(store.data_dir.rglob("*.tmp")) == []

    real_replace, tries = os.replace, {"n": 0}
    monkeypatch.setattr(
        os, "replace",
        lambda s, d: (
            tries.__setitem__("n", tries["n"] + 1),
            (_ for _ in ()).throw(PermissionError("em uso")) if tries["n"] < 3 else real_replace(s, d),
        )[1],
    )
    store.set_cache("openalex", {"q": "retry"}, {"ok": True})
    monkeypatch.undo()
    assert tries["n"] == 3

    monkeypatch.setattr(os, "link", lambda _s, _d: (_ for _ in ()).throw(OSError("exFAT")))
    monkeypatch.setattr(sys, "platform", "win32")
    exfat_dest = tmp_path / "exfat.json"
    atomic_write_exclusive(exfat_dest, '{"ok": true}\n')
    with pytest.raises((FileExistsError, OSError)):
        atomic_write_exclusive(exfat_dest, '{"ok": false}\n')
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(OSError, match="hard links"):
        atomic_write_exclusive(tmp_path / "posix_no_link.json", "{}\n")
    monkeypatch.undo()


# FR-09, FR-12, D-007: Imutabilidade e recusa de sobrescrita no helper de publicação exclusiva
def test_fr09_fr12_d007_imutabilidade_e_recusa_de_sobrescrita(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    saved_s, saved_l = store.record_search(_search(), _list(total=5))
    list_path = store.lists_dir / "l-0001.json"
    orig_bytes = list_path.read_bytes()

    with pytest.raises(FileExistsError):
        atomic_write_exclusive(list_path, '{"id": "l-0001", "total": 999}\n')
    assert list_path.read_bytes() == orig_bytes

    saved_l["total"] = 0
    saved_s["request_summary"] = "alterado"
    assert store.get_list("l-0001")["total"] == 5
    assert store.get_search("s-0001")["request_summary"].startswith("Artigos")
    for invalid_id in ("s-0000", "s-00001", "l-0001", "../s-0001"):
        with pytest.raises(ValueError):
            store.get_search(invalid_id)


# FR-09, D-007: 5 dígitos, colisão em os.link dentro de record_search, threads e multiprocessing
def test_fr09_d007_cinco_digitos_colisao_threads_e_multiprocessing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = Store(tmp_path / "seq")
    store.lists_dir.mkdir(parents=True, exist_ok=True)
    (store.lists_dir / "l-0001.json").write_text('{"id":"l-0001"}\n', encoding="utf-8")
    store.record_search(_search(request_summary="B2"), _list())
    (store.lists_dir / "l-9998.json").write_text('{"id":"l-9998"}\n', encoding="utf-8")
    store.record_search(_search(request_summary="B9999"), _list())

    s10k, l10k = store.record_search(_search(request_summary="B10000"), _list())
    assert (s10k["id"], l10k["id"]) == ("s-10000", "l-10000")
    assert [s["id"] for s in store.list_searches()] == ["s-0002", "s-9999", "s-10000"]

    race_store = Store(tmp_path / "race")
    real_link, collided = os.link, {"done": False}

    def colliding_link(src: str | Path, dst: str | Path) -> None:
        dst_p = Path(dst)
        if not collided["done"] and dst_p.name == "l-0001.json":
            collided["done"] = True
            dst_p.write_text('{"id": "l-0001"}\n', encoding="utf-8")
        real_link(src, dst)

    monkeypatch.setattr(os, "link", colliding_link)
    rs, rl = race_store.record_search(_search(), _list())
    monkeypatch.undo()
    assert (rs["id"], rs["list_id"], rl["id"], rl["search_id"]) == ("s-0002", "l-0002", "l-0002", "s-0002")

    th_store = Store(tmp_path / "threads")
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(lambda i: th_store.record_search(_search(request_summary=f"T{i}"), _list()), range(12)))
    assert th_store.rebuild_log() == th_store.read_log()

    mp_dir = tmp_path / "mp"
    with multiprocessing.get_context("spawn").Pool(3) as mp_pool:
        mp_results = mp_pool.map(_mp_worker, [(str(mp_dir), w, 15) for w in range(3)])
    flat_ids = [pair[0] for sub in mp_results for pair in sub]
    mp_store = Store(mp_dir)
    assert sorted(flat_ids) == [f"s-{i:04d}" for i in range(1, 46)]
    assert [s["id"] for s in mp_store.list_searches()] == [f"s-{i:04d}" for i in range(1, 46)]
    mp_log_bytes = mp_store.log_path.read_bytes()
    assert mp_store.log_path.read_text(encoding="utf-8").count("## s-") == 45
    assert mp_store.rebuild_log().encode("utf-8") == mp_log_bytes


# NFR-06, D-007: Cache no prazo, vencido e validação de fonte
def test_nfr06_d007_cache_prazo_expiracao_e_validacao_fonte(tmp_path: Path) -> None:
    store = Store(tmp_path / "data", cache_days=7)
    q = {"b": 2, "a": "ml"}
    assert store.get_cache("openalex", q) is None
    store.set_cache("openalex", q, {"items": [1]}, fetched_at="2026-11-01T12:00:00Z")

    hit = store.get_cache("openalex", {"a": "ml", "b": 2}, now="2026-11-07T12:00:00Z")
    assert hit == {"response": {"items": [1]}, "from_cache": True, "fetched_at": "2026-11-01T12:00:00Z"}
    assert store.get_cache("openalex", q, now="2026-11-08T12:00:00Z") is None

    for bad in ("", "../x", "OpenAlex", "a-b", "a/b", r"a\b"):
        with pytest.raises(ValueError):
            store.set_cache(bad, q, {})


# NFR-03: Credencial tratada nos 3 pontos (consulta do cache, sources[].query/reason e response do cache)
def test_nfr03_credenciais_nos_tres_pontos_sem_alterar_textos_de_consulta(tmp_path: Path) -> None:
    store = Store(tmp_path / "data")
    secrets = ["fake-key-123", "fake-apikey-456", "fake-tok-789", "fake-auth-012"]

    q1 = {"search": "key=0.5", "api_key": secrets[0], "nested": {"Token": secrets[2], "k": 1}}
    q2 = {"nested": {"k": 1}, "search": "key=0.5", "Authorization": secrets[3]}
    assert compute_cache_key(q1)[0] == compute_cache_key(q2)[0]
    assert compute_cache_key({"search": "key=0.5"})[0] != compute_cache_key({"search": "key=0.9"})[0]

    resp = {
        "next_url": f"https://api.openalex.org/works?cursor=*&api_key={secrets[0]}&per_page=25",
        "items": [{"self": f"http://example.org/p?apikey={secrets[1]}", "note": "key=0.5 intacto"}],
    }
    c_path = store.set_cache("openalex", q1, resp, fetched_at="2026-11-02T10:00:00Z")
    assert c_path.exists()
    cached = store.get_cache("openalex", q2, now="2026-11-03T10:00:00Z")
    assert cached is not None
    assert cached["response"]["next_url"] == "https://api.openalex.org/works?cursor=*&per_page=25"
    assert cached["response"]["items"][0] == {"self": "http://example.org/p", "note": "key=0.5 intacto"}

    raw_q = f"GET https://api.openalex.org/works?search=a+b&api_key={secrets[0]}&key=0.5"
    assert strip_url_credentials(raw_q) == "GET https://api.openalex.org/works?search=a+b"
    assert strip_url_credentials("texto sem url? key=0.5 & token=1") == "texto sem url? key=0.5 & token=1"

    store.record_search(
        _search(
            sources=[
                _src(
                    query=f"https://api.openalex.org/works?search=ml&api_key={secrets[0]}&apikey={secrets[1]}",
                    reason=f"Falha em https://api.openalex.org/works?token={secrets[2]}&page=1 após 3x",
                )
            ]
        ),
        _list(works=[{"doi": "10.1/1", "title": "Artigo key=0.5", "key": "k1"}]),
    )
    for p in [f for f in store.data_dir.rglob("*") if f.is_file()]:
        text = p.read_text(encoding="utf-8")
        for sec in secrets:
            assert sec not in p.name
            assert sec not in text


# FR-13, FR-15: No log.md, fonte ok com found=None mostra "total não informado, trazidos N" e com found=0 mostra "encontrados 0"
def test_fr13_fr15_log_md_total_nao_informado_quando_found_none_e_encontrados_0_quando_zero(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "data")
    search_in = _search(
        kind="related",
        origin={"work": "10.1007/s11192-009-0146-3", "direction": "citations"},
        sources=[
            _src(
                "semantic_scholar",
                query="paper=DOI:10.1007/s11192-009-0146-3/citations · limit=100 · offset=0",
                status="ok",
                found=None,
                fetched=45,
            ),
            _src(
                "openalex",
                query="filter=cites:W1",
                status="ok",
                found=0,
                fetched=0,
            ),
        ],
    )
    store.record_search(search_in, _list(status="complete", total=45))
    log_text = store.read_log()
    assert (
        "- semantic_scholar · ok · total não informado, trazidos 45 · cache: não · "
        "string: `paper=DOI:10.1007/s11192-009-0146-3/citations · limit=100 · offset=0`\n"
    ) in log_text
    assert (
        "- openalex · ok · encontrados 0, trazidos 0 · cache: não · string: `filter=cites:W1`\n"
    ) in log_text


# D-023, FR-13: o log.md tem a linha de crédito quando a busca trouxe dados do Scopus ou do Web of Science, e não tem quando não trouxe
def test_d023_log_md_linha_de_credito_scopus_e_wos(tmp_path: Path) -> None:
    # 1. Busca traz dados do Scopus -> termina com "Dados do Scopus (Elsevier)"
    store1 = Store(tmp_path / "data1")
    s_scopus = _search(
        sources=[
            _src("scopus", found=50, fetched=20, status="ok"),
        ]
    )
    store1.record_search(s_scopus, _list(total=20))
    log1 = store1.read_log()
    assert log1.strip().endswith("Dados do Scopus (Elsevier)")
    assert "Clarivate Analytics" not in log1

    # 2. Busca traz dados do Web of Science -> termina com "Source: Clarivate Analytics (Web of Science)"
    store2 = Store(tmp_path / "data2")
    s_wos = _search(
        sources=[
            _src("web_of_science", found=30, fetched=15, status="ok"),
        ]
    )
    store2.record_search(s_wos, _list(total=15))
    log2 = store2.read_log()
    assert log2.strip().endswith("Source: Clarivate Analytics (Web of Science)")
    assert "Dados do Scopus" not in log2

    # 3. Busca traz dados de ambas as bases pagas -> termina com ambas as linhas de crédito
    store3 = Store(tmp_path / "data3")
    s_both = _search(
        sources=[
            _src("scopus", found=50, fetched=20, status="ok"),
            _src("web_of_science", found=30, fetched=15, status="ok"),
        ]
    )
    store3.record_search(s_both, _list(total=35))
    log3 = store3.read_log()
    assert "Dados do Scopus (Elsevier)\nSource: Clarivate Analytics (Web of Science)" in log3
    assert log3.strip().endswith("Source: Clarivate Analytics (Web of Science)")

    # 4. Busca não traz dados de bases pagas (só fontes abertas) -> sem linha de crédito
    store4 = Store(tmp_path / "data4")
    s_open = _search(
        sources=[
            _src("openalex", found=100, fetched=25, status="ok"),
            _src("crossref", found=50, fetched=10, status="ok"),
        ]
    )
    store4.record_search(s_open, _list(total=35))
    log4 = store4.read_log()
    assert "Dados do Scopus" not in log4
    assert "Clarivate Analytics" not in log4

    # 5. Scopus consultado mas com zero resultados (fetched=0) -> sem linha de crédito
    store5 = Store(tmp_path / "data5")
    s_zero = _search(
        sources=[
            _src("scopus", found=0, fetched=0, status="ok"),
        ]
    )
    store5.record_search(s_zero, _list(total=0, works=[]))
    log5 = store5.read_log()
    assert "Dados do Scopus" not in log5
    assert "Clarivate Analytics" not in log5

    # 6. Scopus com falha ou missing_key (fetched=None) -> sem linha de crédito
    store6 = Store(tmp_path / "data6")
    s_fail = _search(
        sources=[
            _src("scopus", found=None, fetched=None, status="missing_key"),
        ]
    )
    store6.record_search(s_fail, _list(total=0, works=[]))
    log6 = store6.read_log()
    assert "Dados do Scopus" not in log6
    assert "Clarivate Analytics" not in log6
