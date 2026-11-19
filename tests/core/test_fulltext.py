"""Testes do módulo de recuperação legal de texto completo em acesso aberto (FR-34, D-045)."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from rslapp.core.fulltext import (
    FullTextRecord,
    download_fulltext_pdf,
    resolve_open_access_pdf,
)
from rslapp.core.models import Work
from rslapp.store import Store


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _make_work(doi: str | None = None, pmc: str | None = None) -> Work:
    source_ids = {}
    if pmc:
        source_ids["pmc"] = pmc
    return Work(
        title="Estudo Teste OA",
        doi=doi,
        year=2024,
        type="article",
        venue="Revista Aberta",
        abstract="Resumo de teste",
        keywords=["teste"],
        authors=[],
        references=[],
        references_count=0,
        citations=1,
        source_ids=source_ids,
    )


# FR-34, D-045: Resolução direta de PDF para artigos no PubMed Central
@pytest.mark.anyio
async def test_fr34_resolve_pmc() -> None:
    work = _make_work(doi="10.1234/exemplo", pmc="PMC9999999")
    rec = await resolve_open_access_pdf(work)
    assert rec.status == "available"
    assert rec.oa_url == "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9999999/pdf/"
    assert rec.repository == "PubMed Central"


# FR-34, D-045: Resolução Unpaywall para artigo em acesso aberto
@pytest.mark.anyio
async def test_fr34_resolve_unpaywall_oa() -> None:
    work = _make_work(doi="10.1038/s41586-024-0001")

    def unpaywall_handler(request: httpx.Request) -> httpx.Response:
        assert "10.1038/s41586-024-0001" in str(request.url)
        return httpx.Response(
            200,
            json={
                "is_oa": True,
                "best_oa_location": {
                    "url_for_pdf": "https://nature.com/articles/s41586-024-0001.pdf",
                    "license": "cc-by",
                    "repository_institution": "Nature Publishing Group",
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(unpaywall_handler)) as client:
        rec = await resolve_open_access_pdf(work, client=client)

    assert rec.status == "available"
    assert rec.oa_url == "https://nature.com/articles/s41586-024-0001.pdf"
    assert rec.license == "cc-by"
    assert rec.repository == "Nature Publishing Group"


# FR-34, D-045: Resolução Unpaywall para artigo sob paywall (restrito)
@pytest.mark.anyio
async def test_fr34_resolve_unpaywall_paywall() -> None:
    work = _make_work(doi="10.1016/j.fechado.2024")

    def unpaywall_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"is_oa": False, "best_oa_location": None})

    async with httpx.AsyncClient(transport=httpx.MockTransport(unpaywall_handler)) as client:
        rec = await resolve_open_access_pdf(work, client=client)

    assert rec.status == "restricted_paywall"
    assert rec.oa_url == "https://doi.org/10.1016/j.fechado.2024"


# FR-34, D-045: Download atômico com validação do cabeçalho binário %PDF
@pytest.mark.anyio
async def test_fr34_download_pdf_valido_e_invalido(tmp_path: Path) -> None:
    dest_dir = tmp_path / "pdfs"

    # 1. Resposta com PDF válido
    valid_pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

    def pdf_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=valid_pdf_content, headers={"Content-Type": "application/pdf"})

    rec = FullTextRecord(work_id="work-01", status="available", oa_url="https://exemplo.org/artigo.pdf")
    async with httpx.AsyncClient(transport=httpx.MockTransport(pdf_handler)) as client:
        downloaded = await download_fulltext_pdf(rec, dest_dir=dest_dir, client=client)

    assert downloaded.status == "downloaded"
    assert downloaded.pdf_path is not None
    saved_file = Path(downloaded.pdf_path)
    assert saved_file.exists()
    assert saved_file.read_bytes() == valid_pdf_content

    # 2. Resposta que é HTML (falso PDF / erro 200 de login de paywall)
    fake_pdf_content = b"<!DOCTYPE html><html><body>Login requerido</body></html>"

    def html_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=fake_pdf_content, headers={"Content-Type": "text/html"})

    rec_fake = FullTextRecord(work_id="work-02", status="available", oa_url="https://exemplo.org/login")
    async with httpx.AsyncClient(transport=httpx.MockTransport(html_handler)) as client:
        failed_dl = await download_fulltext_pdf(rec_fake, dest_dir=dest_dir, client=client)

    assert failed_dl.status == "failed"
    assert not (dest_dir / "work-02.pdf").exists()


# FR-34, D-045: Persistência no Store e manifesto da lista
def test_fr34_store_manifest(tmp_path: Path) -> None:
    store = Store(data_dir=tmp_path)
    rec1 = FullTextRecord(work_id="w1", status="downloaded", pdf_path="/tmp/w1.pdf").to_dict()
    rec2 = FullTextRecord(work_id="w2", status="restricted_paywall").to_dict()

    store.save_fulltext_record("l-001", rec1)
    store.save_fulltext_record("l-001", rec2)

    manifest = store.get_fulltext_manifest("l-001")
    assert manifest["list_id"] == "l-001"
    assert len(manifest["records"]) == 2
    assert manifest["records"]["w1"]["status"] == "downloaded"
    assert manifest["records"]["w2"]["status"] == "restricted_paywall"
