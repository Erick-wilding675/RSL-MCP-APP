"""Testes unitários do motor de redes bibliométricas e exportadores VOSviewer e Gephi (FR-31, D-042)."""

import pytest

from rslapp.core.errors import RSLError
from rslapp.core.network import (
    extract_bibliometric_network,
    format_gephi_gexf,
    format_vosviewer_map,
    format_vosviewer_network,
)


def _sample_works() -> list[dict]:
    return [
        {
            "id": "W1",
            "title": "Machine Learning in Systematic Reviews",
            "authors": [{"name": "Mendes, Erick"}, {"name": "Silva, Ana"}],
            "venue": "Journal of Informatics",
            "keywords": ["machine learning", "systematic review", "automation"],
        },
        {
            "id": "W2",
            "title": "Natural Language Processing for Literature Screening",
            "authors": [
                {"name": "Mendes, Erick"},
                {"name": "Silva, Ana"},
                {"name": "Costa, Carlos"},
            ],
            "venue": "Journal of Informatics",
            "keywords": ["nlp", "systematic review", "screening"],
        },
        {
            "id": "W3",
            "title": "Deep Learning Frameworks",
            "authors": [{"name": "Costa, Carlos"}, {"name": "Oliveira, Pedro"}],
            "venue": "AI Communications",
            "keywords": ["deep learning", "automation"],
        },
    ]


def test_extract_coauthorship_network():
    works = _sample_works()
    net = extract_bibliometric_network(works, "coauthorship")

    assert net["network_type"] == "coauthorship"
    assert net["total_nodes"] == 4  # Mendes, Silva, Costa, Oliveira

    # Mendes tem 2 artigos, Silva tem 2, Costa tem 2, Oliveira tem 1
    nodes_by_label = {n["label"]: n for n in net["nodes"]}
    assert nodes_by_label["Mendes, Erick"]["weight"] == 2
    assert nodes_by_label["Silva, Ana"]["weight"] == 2
    assert nodes_by_label["Costa, Carlos"]["weight"] == 2
    assert nodes_by_label["Oliveira, Pedro"]["weight"] == 1

    # Colaboração Mendes-Silva aparece em W1 e W2 -> peso 2
    mendes_id = nodes_by_label["Mendes, Erick"]["id"]
    silva_id = nodes_by_label["Silva, Ana"]["id"]

    edge_ms = next(
        e
        for e in net["edges"]
        if (e["source"] == mendes_id and e["target"] == silva_id)
        or (e["source"] == silva_id and e["target"] == mendes_id)
    )
    assert edge_ms["weight"] == 2


def test_extract_network_filters():
    works = _sample_works()
    # Filtra nós com pelo menos 2 ocorrências (exclui Oliveira)
    net = extract_bibliometric_network(works, "coauthorship", min_node_weight=2)
    assert net["total_nodes"] == 3
    labels = {n["label"] for n in net["nodes"]}
    assert "Oliveira, Pedro" not in labels

    # Filtra arestas com peso mínimo 2 (apenas Mendes-Silva)
    net_edges = extract_bibliometric_network(works, "coauthorship", min_edge_weight=2)
    assert len(net_edges["edges"]) == 1
    assert net_edges["edges"][0]["weight"] == 2


def test_extract_keyword_cooccurrence():
    works = _sample_works()
    net = extract_bibliometric_network(works, "keyword_cooccurrence")

    assert net["network_type"] == "keyword_cooccurrence"
    assert net["total_nodes"] >= 4
    nodes_by_label = {n["label"]: n for n in net["nodes"]}
    assert "systematic review" in nodes_by_label
    assert nodes_by_label["systematic review"]["weight"] == 2


def test_invalid_network_type():
    with pytest.raises(RSLError) as exc:
        extract_bibliometric_network(_sample_works(), "invalid_type")
    assert exc.value.code == "invalid_input"


def test_format_vosviewer_files():
    nodes = [
        {"id": 1, "label": "Silva, Ana", "weight": 5},
        {"id": 2, "label": "Mendes, Erick", "weight": 3},
    ]
    edges = [{"id": 1, "source": 1, "target": 2, "weight": 2}]

    map_str = format_vosviewer_map(nodes)
    assert "id\tlabel\tweight<Occurrences>" in map_str
    assert "1\tSilva, Ana\t5" in map_str
    assert "2\tMendes, Erick\t3" in map_str

    network_str = format_vosviewer_network(edges)
    assert "1\t2\t2" in network_str


def test_format_gephi_gexf():
    nodes = [{"id": 1, "label": "Silva, Ana", "weight": 5}]
    edges = [{"id": 1, "source": 1, "target": 2, "weight": 2}]

    gexf_str = format_gephi_gexf(nodes, edges, title="Rede de Teste")
    assert '<?xml version="1.0" encoding="UTF-8"?>' in gexf_str
    assert '<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">' in gexf_str
    assert '<node id="1" label="Silva, Ana">' in gexf_str
    assert '<attvalue for="0" value="5"/>' in gexf_str
    assert '<edge id="1" source="1" target="2" weight="2"/>' in gexf_str
