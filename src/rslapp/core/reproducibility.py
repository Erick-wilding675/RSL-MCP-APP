"""Geração do Pacote de Reprodutibilidade Científica com manifesto criptográfico SHA-256 (FR-28, D-039)."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from rslapp import __version__
from rslapp.core.ai_disclosure import render_ai_disclosure
from rslapp.core.errors import RSLError
from rslapp.core.prisma import (
    calculate_prisma_flow,
    render_prisma_markdown,
    render_prisma_svg,
)
from rslapp.exporters import get_exporter
from rslapp.store import Store
from rslapp.store._atomic import atomic_write_bytes


# FR-28, D-039: Constrói o pacote completo de reprodutibilidade científica da revisão em arquivo .zip
def build_reproducibility_package(
    list_id: str,
    store: Store,
    export_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Empacota todos os artefatos de dados, busca, triagem e declarações com manifesto SHA-256.

    Gera um arquivo reproducibility_{list_id}.zip contendo 11 arquivos metodológicos e o checksums.sha256.
    """
    try:
        list_data = store.get_list(list_id)
    except FileNotFoundError as err:
        raise RSLError("list_not_found", f"Lista não encontrada: {list_id}") from err

    works = list_data.get("works", [])
    if not works:
        raise RSLError("empty_list", f"A lista {list_id} está vazia; impossível gerar pacote de reprodutibilidade.")

    search_id = list_data.get("search_id", "")
    search_rec: dict[str, Any] | None = None
    if search_id:
        try:
            search_rec = store.get_search(search_id)
        except (RSLError, FileNotFoundError, ValueError):
            search_rec = None

    screening_data = store.get_screening(list_id)
    screening_summary = store.get_screening_summary(list_id)

    # 1. PRISMA 2020 e Checklist PRISMA-S
    flow = calculate_prisma_flow(list_data, screening_summary, search_record=search_rec)
    svg_content = render_prisma_svg(flow)
    prisma_md = render_prisma_markdown(flow)

    # 2. Declarações éticas de IA (COPE/ICMJE/SciELO)
    query_str = (
        search_rec.get("request_summary", "")
        if search_rec
        else list_data.get("query", "Revisão Sistemática")
    )
    disclosure_pt = render_ai_disclosure(
        list_id=list_id,
        search_query=query_str,
        total_works=len(works),
        screening_summary=screening_summary,
        lang="pt",
    )
    disclosure_en = render_ai_disclosure(
        list_id=list_id,
        search_query=query_str,
        total_works=len(works),
        screening_summary=screening_summary,
        lang="en",
    )

    # 3. Exportações tabulares e bibliográficas
    csv_content = get_exporter("csv").render(list_data)
    ris_content = get_exporter("ris").render(list_data)
    bib_content = get_exporter("bibtex").render(list_data)
    abnt_content = get_exporter("abnt").render(list_data)

    # 4. Metadados e Log metodológico
    now_utc = datetime.now(timezone.utc).isoformat()

    # FR-30, D-041: Protocolo metodológico pré-busca associado ou único
    protocol_id = list_data.get("protocol_id") or (
        search_rec.get("protocol_id") if search_rec else None
    )
    protocol: dict[str, Any] | None = None
    if protocol_id:
        protocol = store.get_protocol(str(protocol_id))
    if not protocol:
        protocols = store.list_protocols()
        if len(protocols) == 1:
            protocol = protocols[0]
        elif protocols:
            for p in protocols:
                if p.get("title", "").strip().lower() == query_str.strip().lower():
                    protocol = p
                    break

    metadata = {
        "rslapp_version": __version__,
        "package_type": "reproducibility_bundle",
        "standard_spec": "FR-28 / D-039",
        "list_id": list_id,
        "search_id": search_id,
        "created_at": list_data.get("created_at"),
        "exported_at": now_utc,
        "total_works": len(works),
        "search_query": query_str,
        "sources": [s.get("name") for s in search_rec.get("sources", [])] if search_rec else [],
        "screening_stats": {
            "screened": screening_summary.get("screened", 0),
            "included": screening_summary.get("included", 0),
            "excluded": screening_summary.get("excluded", 0),
        },
    }
    if protocol:
        metadata["protocol_id"] = protocol.get("id")
        metadata["protocol_version"] = protocol.get("version")

    metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
    screening_json = json.dumps(screening_data, ensure_ascii=False, indent=2) + "\n"

    # Log da busca
    search_log = store.read_log()
    if not search_log and search_rec:
        search_log = f"# Search Log: {list_id}\n\nQuery: {query_str}\nCreated: {list_data.get('created_at')}\n"

    # Arquivos que irão compor o pacote
    files_to_pack: dict[str, bytes] = {
        "metadata.json": metadata_json.encode("utf-8"),
        "search_log.md": search_log.encode("utf-8"),
        "works.csv": csv_content.encode("utf-8"),
        "works.ris": ris_content.encode("utf-8"),
        "works.bib": bib_content.encode("utf-8"),
        "references_abnt.txt": abnt_content.encode("utf-8"),
        "screening.json": screening_json.encode("utf-8"),
        "prisma_2020.svg": svg_content.encode("utf-8"),
        "prisma_s_checklist.md": prisma_md.encode("utf-8"),
        "ai_disclosure_pt.md": disclosure_pt.encode("utf-8"),
        "ai_disclosure_en.md": disclosure_en.encode("utf-8"),
    }

    # FR-29, D-040: Inclui fichamento científico se houver fichas salvas
    notes = store.list_notes(list_id)
    if notes:
        from rslapp.core.notes import format_notes_compilation

        notes_md = format_notes_compilation(notes, list_id=list_id, list_title=query_str)
        notes_json = json.dumps(notes, ensure_ascii=False, indent=2) + "\n"
        files_to_pack["notes.md"] = notes_md.encode("utf-8")
        files_to_pack["notes.json"] = notes_json.encode("utf-8")

    # FR-30, D-041: Inclui protocolo metodológico se disponível
    if protocol:
        from rslapp.core.protocols import format_protocol_markdown

        protocol_md = format_protocol_markdown(protocol)
        protocol_json = json.dumps(protocol, ensure_ascii=False, indent=2) + "\n"
        files_to_pack["protocol.md"] = protocol_md.encode("utf-8")
        files_to_pack["protocol.json"] = protocol_json.encode("utf-8")

    # 5. Cálculo dos hashes SHA-256 e manifesto
    checksum_lines: list[str] = []
    for fname, data in files_to_pack.items():
        file_sha256 = hashlib.sha256(data).hexdigest()
        checksum_lines.append(f"{file_sha256}  {fname}")

    checksums_content = "\n".join(checksum_lines) + "\n"
    files_to_pack["checksums.sha256"] = checksums_content.encode("utf-8")

    # 6. Criação do arquivo .zip em memória
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fname, data in files_to_pack.items():
            zf.writestr(fname, data)

    zip_bytes = zip_buffer.getvalue()
    zip_sha256 = hashlib.sha256(zip_bytes).hexdigest()

    # 7. Gravação segura no destino se export_dir fornecido
    dest_path: Path | None = None
    if export_dir is not None:
        target_dir = Path(export_dir)
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            dest_path = target_dir / f"reproducibility_{list_id}.zip"
            # Gravação segura em binário
            atomic_write_bytes(dest_path, zip_bytes)
        except (PermissionError, OSError) as err:
            raise RSLError(
                "export_folder_not_writable",
                f"Pasta de exportação não aceita gravação: {target_dir}",
            ) from err

    return {
        "list_id": list_id,
        "path": str(dest_path.resolve()) if dest_path else None,
        "filename": f"reproducibility_{list_id}.zip",
        "file_count": len(files_to_pack),
        "size_bytes": len(zip_bytes),
        "sha256": zip_sha256,
        "zip_bytes": zip_bytes,
    }
