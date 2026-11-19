"""Recuperação legal de texto completo em acesso aberto (Open Access)."""

from __future__ import annotations

import copy
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from rslapp.core.models import Work

UNPAYWALL_BASE_URL = "https://api.unpaywall.org/v2"
DEFAULT_EMAIL = "rslapp@sinteselabs.com"
MAX_PDF_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
PDF_MAGIC_BYTES = b"%PDF"


def _clean_id(raw_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-\.]", "_", raw_id)


# FR-34, D-045: Registro de status do texto completo por artigo
@dataclass
class FullTextRecord:
    work_id: str
    status: str  # "available", "downloaded", "restricted_paywall", "failed", "not_found"
    oa_url: str | None = None
    pdf_path: str | None = None
    license: str | None = None
    repository: str | None = None
    checked_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FullTextRecord:
        return cls(
            work_id=data.get("work_id", ""),
            status=data.get("status", "not_found"),
            oa_url=data.get("oa_url"),
            pdf_path=data.get("pdf_path"),
            license=data.get("license"),
            repository=data.get("repository"),
            checked_at=data.get("checked_at"),
        )


# FR-34, D-045: Resolve localização de acesso aberto de um Work
async def resolve_open_access_pdf(
    work: Work,
    work_id: str | None = None,
    email: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> FullTextRecord:
    """Tenta resolver a URL de PDF de acesso aberto legal para o artigo."""
    contact_email = email.strip() if email and email.strip() else DEFAULT_EMAIL
    now_iso = datetime.now(timezone.utc).isoformat()
    clean_wid = str(work_id).strip() if work_id is not None else (_clean_id(work.doi) if work.doi else "unknown_work")

    # 1. Verifica se já temos PMC / Europe PMC
    pmc_id = work.source_ids.get("pmc") or (
        work.source_ids.get("europe_pmc") if work.source_ids.get("europe_pmc", "").startswith("PMC") else None
    )
    if pmc_id:
        clean_pmc = pmc_id if pmc_id.startswith("PMC") else f"PMC{pmc_id}"
        pmc_pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{clean_pmc}/pdf/"
        return FullTextRecord(
            work_id=clean_wid,
            status="available",
            oa_url=pmc_pdf_url,
            license="open_access_pmc",
            repository="PubMed Central",
            checked_at=now_iso,
        )

    # 2. Resolução via Unpaywall se houver DOI
    if work.doi:
        doi_clean = work.doi.strip()
        url = f"{UNPAYWALL_BASE_URL}/{doi_clean}?email={contact_email}"
        try:
            if client is not None:
                resp = await client.get(url, timeout=15.0)
            else:
                async with httpx.AsyncClient(timeout=15.0) as default_client:
                    resp = await default_client.get(url)

            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and data.get("is_oa"):
                    best_oa = data.get("best_oa_location")
                    if isinstance(best_oa, dict):
                        pdf_url = best_oa.get("url_for_pdf") or best_oa.get("url")
                        oa_license = best_oa.get("license")
                        repo = best_oa.get("repository_institution") or "Unpaywall Open Access"
                        if pdf_url:
                            return FullTextRecord(
                                work_id=clean_wid,
                                status="available",
                                oa_url=pdf_url,
                                license=oa_license,
                                repository=repo,
                                checked_at=now_iso,
                            )
                    # Caso seja OA mas sem PDF direto
                    oa_locations = data.get("oa_locations", [])
                    for loc in oa_locations:
                        if isinstance(loc, dict) and loc.get("url_for_pdf"):
                            return FullTextRecord(
                                work_id=clean_wid,
                                status="available",
                                oa_url=loc["url_for_pdf"],
                                license=loc.get("license"),
                                repository=loc.get("repository_institution") or "Unpaywall",
                                checked_at=now_iso,
                            )
                # Artigo registrado mas restrito
                return FullTextRecord(
                    work_id=clean_wid,
                    status="restricted_paywall",
                    oa_url=f"https://doi.org/{doi_clean}",
                    license=None,
                    repository=None,
                    checked_at=now_iso,
                )
        except (httpx.HTTPError, ValueError):
            return FullTextRecord(
                work_id=clean_wid,
                status="failed",
                oa_url=f"https://doi.org/{doi_clean}",
                license=None,
                repository=None,
                checked_at=now_iso,
            )

    return FullTextRecord(
        work_id=clean_wid,
        status="not_found",
        oa_url=f"https://doi.org/{work.doi}" if work.doi else None,
        license=None,
        repository=None,
        checked_at=now_iso,
    )


# FR-34, D-045: Download atômico do PDF com conferência binária
async def download_fulltext_pdf(
    record: FullTextRecord,
    dest_dir: Path,
    client: httpx.AsyncClient | None = None,
) -> FullTextRecord:
    """Baixa o PDF do artigo de forma atômica para a pasta indicada."""
    if not record.oa_url or record.status not in ("available", "failed"):
        return record

    dest_dir.mkdir(parents=True, exist_ok=True)
    clean_name = _clean_id(record.work_id)
    target_path = dest_dir / f"{clean_name}.pdf"
    temp_path = dest_dir / f".{clean_name}.tmp"

    try:
        if client is not None:
            resp = await client.get(record.oa_url, follow_redirects=True, timeout=30.0)
        else:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as default_client:
                resp = await default_client.get(record.oa_url)

        if resp.status_code != 200:
            rec = copy.deepcopy(record)
            rec.status = "failed"
            return rec

        content = resp.content
        if len(content) > MAX_PDF_SIZE_BYTES:
            rec = copy.deepcopy(record)
            rec.status = "failed"
            return rec

        # Validação: deve começar com %PDF ou conter cabeçalho PDF
        if not content.startswith(PDF_MAGIC_BYTES) and b"%PDF" not in content[:1024]:
            rec = copy.deepcopy(record)
            rec.status = "failed"
            return rec

        temp_path.write_bytes(content)
        temp_path.replace(target_path)

        rec = copy.deepcopy(record)
        rec.status = "downloaded"
        rec.pdf_path = str(target_path)
        return rec
    except Exception:  # noqa: BLE001
        if temp_path.exists():
            temp_path.unlink()
        rec = copy.deepcopy(record)
        rec.status = "failed"
        return rec
