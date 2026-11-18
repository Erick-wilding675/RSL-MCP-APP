"""Motor de extração de redes bibliométricas e geradores VOSviewer e Gephi (FR-31, D-042).

Suporta extração de coautoria, periódicos/veículos e coocorrência de termos,
com exportação nativa nos formatos VOSviewer (.map e .network) e Gephi GEXF (.gexf).
"""

from __future__ import annotations

import html
import itertools
from collections import Counter
from typing import Any

from rslapp.core.errors import RSLError

VALID_NETWORK_TYPES: frozenset[str] = frozenset(
    {"coauthorship", "source_coupling", "keyword_cooccurrence"}
)

NETWORK_TYPE_LABELS: dict[str, str] = {
    "coauthorship": "Rede de Coautoria (Autores)",
    "source_coupling": "Rede de Periódicos / Fontes",
    "keyword_cooccurrence": "Rede de Coocorrência de Palavras-Chave",
}


def _extract_work_authors(work: Any) -> list[str]:
    """Extrai lista de nomes de autores de um dicionário ou objeto Work."""
    authors_data = work.get("authors") if isinstance(work, dict) else getattr(work, "authors", [])
    if not authors_data:
        return []

    names: list[str] = []
    for a in authors_data:
        if isinstance(a, str) and a.strip():
            names.append(a.strip())
        elif isinstance(a, dict) and a.get("name") and isinstance(a["name"], str):
            names.append(a["name"].strip())
        elif hasattr(a, "name") and isinstance(a.name, str) and a.name.strip():
            names.append(a.name.strip())
    # Remove duplicatas locais mantendo a ordem
    return list(dict.fromkeys(names))


def _extract_work_venue(work: Any) -> str | None:
    """Extrai nome limpo do periódico/veículo."""
    venue = work.get("venue") if isinstance(work, dict) else getattr(work, "venue", None)
    if isinstance(venue, str) and venue.strip():
        return venue.strip()
    return None


def _extract_work_keywords(work: Any) -> list[str]:
    """Extrai palavras-chave normalizadas do trabalho."""
    keywords_raw = (
        work.get("keywords") if isinstance(work, dict) else getattr(work, "keywords", [])
    ) or []
    personal_kw = (
        work.get("personal_keywords")
        if isinstance(work, dict)
        else getattr(work, "personal_keywords", [])
    ) or []

    combined: list[str] = []
    for kw in list(keywords_raw) + list(personal_kw):
        if isinstance(kw, str) and kw.strip():
            clean = kw.strip().lower()
            if len(clean) > 2 and clean not in combined:
                combined.append(clean)
    return combined


# FR-31, D-042: Extração de nós e arestas de rede bibliométrica
def extract_bibliometric_network(
    works: list[Any],
    network_type: str = "coauthorship",
    *,
    min_node_weight: int = 1,
    min_edge_weight: int = 1,
    max_nodes: int = 500,
) -> dict[str, Any]:
    """Extrai o grafo bibliométrico de uma lista de artigos.

    Levanta RSLError('invalid_input') se network_type for inválido ou works estiver vazio.
    """
    clean_type = str(network_type).strip().lower()
    if clean_type not in VALID_NETWORK_TYPES:
        raise RSLError(
            "invalid_input",
            f"Tipo de rede inválido: '{network_type}'. Esperado um de: {sorted(VALID_NETWORK_TYPES)}",
        )

    if not works:
        return {
            "network_type": clean_type,
            "label": NETWORK_TYPE_LABELS[clean_type],
            "nodes": [],
            "edges": [],
            "total_nodes": 0,
            "total_edges": 0,
        }

    node_counter: Counter[str] = Counter()
    edge_counter: Counter[tuple[str, str]] = Counter()

    if clean_type == "coauthorship":
        for w in works:
            authors = _extract_work_authors(w)
            for a in authors:
                node_counter[a] += 1
            if len(authors) >= 2:
                for a1, a2 in itertools.combinations(sorted(authors), 2):
                    edge_counter[(a1, a2)] += 1

    elif clean_type == "source_coupling":
        author_venues: dict[str, set[str]] = {}
        for w in works:
            v = _extract_work_venue(w)
            if v:
                node_counter[v] += 1
                authors = _extract_work_authors(w)
                for a in authors:
                    author_venues.setdefault(a, set()).add(v)

        for venues in author_venues.values():
            if len(venues) >= 2:
                for v1, v2 in itertools.combinations(sorted(venues), 2):
                    edge_counter[(v1, v2)] += 1

    elif clean_type == "keyword_cooccurrence":
        for w in works:
            kws = _extract_work_keywords(w)
            for kw in kws:
                node_counter[kw] += 1
            if len(kws) >= 2:
                for k1, k2 in itertools.combinations(sorted(kws), 2):
                    edge_counter[(k1, k2)] += 1

    # Filtra e seleciona os top nós por peso
    eligible_nodes = [
        (label, count)
        for label, count in node_counter.most_common()
        if count >= min_node_weight
    ][:max_nodes]

    label_to_id: dict[str, int] = {}
    nodes: list[dict[str, Any]] = []
    for idx, (label, count) in enumerate(eligible_nodes, start=1):
        label_to_id[label] = idx
        nodes.append({"id": idx, "label": label, "weight": count})

    # Filtra as arestas conectando nós selecionados
    edges: list[dict[str, Any]] = []
    edge_id = 1
    for (src_label, tgt_label), weight in edge_counter.items():
        if weight >= min_edge_weight and src_label in label_to_id and tgt_label in label_to_id:
            edges.append({
                "id": edge_id,
                "source": label_to_id[src_label],
                "target": label_to_id[tgt_label],
                "weight": weight,
            })
            edge_id += 1

    return {
        "network_type": clean_type,
        "label": NETWORK_TYPE_LABELS[clean_type],
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }


# FR-31, D-042: Gerador do arquivo de mapa do VOSviewer (.map)
def format_vosviewer_map(nodes: list[dict[str, Any]]) -> str:
    """Gera o arquivo de mapa do VOSviewer no padrão oficial delimitado por tabulação."""
    lines: list[str] = ["id\tlabel\tweight<Occurrences>"]
    for n in nodes:
        clean_label = str(n.get("label", "")).replace("\t", " ").replace("\n", " ").strip()
        lines.append(f"{n.get('id', 0)}\t{clean_label}\t{n.get('weight', 1)}")
    return "\n".join(lines) + "\n"


# FR-31, D-042: Gerador do arquivo de rede do VOSviewer (.network)
def format_vosviewer_network(edges: list[dict[str, Any]]) -> str:
    """Gera o arquivo de rede do VOSviewer delimitado por tabulação com triplas source-target-weight."""
    lines: list[str] = []
    for e in edges:
        lines.append(f"{e.get('source')}\t{e.get('target')}\t{e.get('weight', 1)}")
    return "\n".join(lines) + ("\n" if lines else "")


# FR-31, D-042: Gerador do formato Gephi GEXF (.gexf XML v1.2)
def format_gephi_gexf(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    title: str = "Bibliometric Network",
) -> str:
    """Gera o documento XML padrão Gephi GEXF v1.2 com grafo estático não-direcionado."""
    safe_title = html.escape(title)
    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">',
        '  <meta lastmodifieddate="">',
        "    <creator>RSL.app</creator>",
        f"    <description>{safe_title}</description>",
        "  </meta>",
        '  <graph mode="static" defaultedgetype="undirected">',
        '    <attributes class="node" mode="static">',
        '      <attribute id="0" title="occurrences" type="integer"/>',
        "    </attributes>",
        "    <nodes>",
    ]

    for n in nodes:
        nid = n.get("id")
        nlabel = html.escape(str(n.get("label", "")))
        w = n.get("weight", 1)
        lines.extend([
            f'      <node id="{nid}" label="{nlabel}">',
            "        <attvalues>",
            f'          <attvalue for="0" value="{w}"/>',
            "        </attvalues>",
            "      </node>",
        ])

    lines.append("    </nodes>")
    lines.append("    <edges>")

    for e in edges:
        eid = e.get("id")
        src = e.get("source")
        tgt = e.get("target")
        weight = e.get("weight", 1)
        lines.append(
            f'      <edge id="{eid}" source="{src}" target="{tgt}" weight="{weight}"/>'
        )

    lines.extend([
        "    </edges>",
        "  </graph>",
        "</gexf>\n",
    ])

    return "\n".join(lines)
