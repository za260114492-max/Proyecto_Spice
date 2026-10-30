#!/usr/bin/env python3
"""
build_oriented_graph.py

Purpose:
    Build a directed multigraph from the normalized circuit model, verify
    connectivity, and export topology JSON plus an optional PNG/SVG visual.

Author: Dr. Francisco E. Rangel-Patiño
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import networkx as nx

from build_circuit_model import Circuit, load_circuit


class CircuitGraphError(ValueError):
    """Raised for invalid or disconnected circuit topology."""


def build_graph(circuit: Circuit) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph(name=circuit.source_name)
    for node in circuit.nodes:
        graph.add_node(node.id, is_reference=node.is_reference)
    for branch in circuit.branches:
        graph.add_edge(
            branch.node_from,
            branch.node_to,
            key=branch.id,
            branch_id=branch.id,
            component=branch.component_name,
            element_type=branch.element_type,
            value_si=branch.value_si,
            unit=branch.unit,
        )
    undirected = graph.to_undirected()
    if graph.number_of_nodes() and not nx.is_connected(undirected):
        components = [sorted(c) for c in nx.connected_components(undirected)]
        raise CircuitGraphError(f"Circuit graph is disconnected: {components}")
    return graph


def graph_to_dict(graph: nx.MultiDiGraph, circuit: Circuit) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "source_name": circuit.source_name,
        "reference_node": circuit.reference_node,
        "nodes": [
            {"id": node, **graph.nodes[node]} for node in graph.nodes
        ],
        "edges": [
            {
                "node_from": u,
                "node_to": v,
                "key": key,
                **data,
            }
            for u, v, key, data in graph.edges(keys=True, data=True)
        ],
        "is_connected": True,
    }


def draw_graph(graph: nx.MultiDiGraph, output: str | Path) -> None:
    """Draw a deterministic teaching-oriented graph visual."""
    import matplotlib.pyplot as plt

    try:
        pos = nx.planar_layout(graph.to_undirected())
    except nx.NetworkXException:
        pos = nx.spring_layout(graph.to_undirected(), seed=42)
    node_colors = ["#ED7D31" if graph.nodes[n].get("is_reference") else "#5B9BD5" for n in graph.nodes]
    plt.figure(figsize=(9, 6))
    nx.draw_networkx_nodes(graph, pos, node_color=node_colors, node_size=1300, edgecolors="#1F1F1F")
    nx.draw_networkx_labels(graph, pos, labels={n: f"N{n}" for n in graph.nodes}, font_weight="bold")
    nx.draw_networkx_edges(
        graph,
        pos,
        connectionstyle="arc3,rad=0.08",
        arrows=True,
        arrowsize=18,
        edge_color="#595959",
        width=1.8,
    )
    edge_labels = {
        (u, v, key): f"{data['branch_id']}:{data['component']}"
        for u, v, key, data in graph.edges(keys=True, data=True)
    }
    # networkx multiedge labels are version-sensitive; place labels manually.
    for (u, v, _), label in edge_labels.items():
        x = (pos[u][0] + pos[v][0]) / 2
        y = (pos[u][1] + pos[v][1]) / 2
        plt.text(x, y, label, fontsize=9, bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "none"})
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output, dpi=180, bbox_inches="tight")
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an oriented circuit graph")
    parser.add_argument("circuit_json", help="Circuit JSON")
    parser.add_argument("-o", "--output", required=True, help="Topology JSON")
    parser.add_argument("--image", help="Optional graph image (.png or .svg)")
    args = parser.parse_args()
    circuit = load_circuit(args.circuit_json)
    graph = build_graph(circuit)
    Path(args.output).write_text(json.dumps(graph_to_dict(graph, circuit), indent=2), encoding="utf-8")
    if args.image:
        draw_graph(graph, args.image)
    print(f"Built oriented graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} branches")


if __name__ == "__main__":
    main()
