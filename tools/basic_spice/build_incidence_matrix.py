#!/usr/bin/env python3
"""
build_incidence_matrix.py

Purpose:
    Construct complete and reduced incidence matrices using the course
    convention: +1 when a branch leaves a node, -1 when it enters.

Author: Dr. Francisco E. Rangel-Patiño
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from build_circuit_model import Circuit, load_circuit


class IncidenceMatrixError(ValueError):
    """Raised when an incidence matrix fails structural validation."""


def build_incidence_matrices(circuit: Circuit) -> dict[str, Any]:
    node_order_full = [n.id for n in circuit.nodes]
    node_order_reduced = [n.id for n in circuit.nodes if not n.is_reference]
    branch_order = [b.id for b in circuit.branches]
    component_order = [b.component_name for b in circuit.branches]
    full_index = {node: i for i, node in enumerate(node_order_full)}
    reduced_index = {node: i for i, node in enumerate(node_order_reduced)}

    a_full = np.zeros((len(node_order_full), len(branch_order)), dtype=int)
    a_reduced = np.zeros((len(node_order_reduced), len(branch_order)), dtype=int)
    for branch in circuit.branches:
        j = branch.index
        a_full[full_index[branch.node_from], j] += 1
        a_full[full_index[branch.node_to], j] -= 1
        if branch.node_from != circuit.reference_node:
            a_reduced[reduced_index[branch.node_from], j] += 1
        if branch.node_to != circuit.reference_node:
            a_reduced[reduced_index[branch.node_to], j] -= 1

    validate_incidence(a_full, a_reduced, circuit)
    return {
        "schema_version": "1.0",
        "source_name": circuit.source_name,
        "reference_node": circuit.reference_node,
        "node_order_full": node_order_full,
        "node_order_reduced": node_order_reduced,
        "branch_order": branch_order,
        "component_order": component_order,
        "A_full": a_full.tolist(),
        "A_reduced": a_reduced.tolist(),
        "shape_full": list(a_full.shape),
        "shape_reduced": list(a_reduced.shape),
    }


def validate_incidence(a_full: np.ndarray, a_reduced: np.ndarray, circuit: Circuit) -> None:
    if a_full.shape[1] != len(circuit.branches):
        raise IncidenceMatrixError("Column count does not match branch count")
    if not set(np.unique(a_full)).issubset({-1, 0, 1}):
        raise IncidenceMatrixError("Incidence matrix contains invalid values")
    for j, branch in enumerate(circuit.branches):
        column = a_full[:, j]
        if np.count_nonzero(column == 1) != 1 or np.count_nonzero(column == -1) != 1:
            raise IncidenceMatrixError(f"Invalid complete incidence column for {branch.id}")
        if int(column.sum()) != 0:
            raise IncidenceMatrixError(f"Column sum is not zero for {branch.id}")
    expected_reduced = len(circuit.nodes) - 1
    if a_reduced.shape != (expected_reduced, len(circuit.branches)):
        raise IncidenceMatrixError("Reduced incidence matrix has incorrect dimensions")


def markdown_matrix(data: dict[str, Any], reduced: bool = True) -> str:
    matrix = data["A_reduced" if reduced else "A_full"]
    nodes = data["node_order_reduced" if reduced else "node_order_full"]
    columns = [f"{b} ({c})" for b, c in zip(data["branch_order"], data["component_order"])]
    lines = ["| Node | " + " | ".join(columns) + " |", "|---|" + "---|" * len(columns)]
    for node, row in zip(nodes, matrix):
        lines.append(f"| N{node} | " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build complete and reduced incidence matrices")
    parser.add_argument("circuit_json", help="Circuit JSON")
    parser.add_argument("-o", "--output", required=True, help="Output incidence JSON")
    parser.add_argument("--markdown", help="Optional reduced matrix Markdown")
    parser.add_argument("--npz", help="Optional NumPy binary output")
    args = parser.parse_args()
    circuit = load_circuit(args.circuit_json)
    data = build_incidence_matrices(circuit)
    Path(args.output).write_text(json.dumps(data, indent=2), encoding="utf-8")
    if args.markdown:
        Path(args.markdown).write_text(markdown_matrix(data), encoding="utf-8")
    if args.npz:
        np.savez(
            args.npz,
            A_full=np.array(data["A_full"], dtype=int),
            A_reduced=np.array(data["A_reduced"], dtype=int),
        )
    print(f"Built A_reduced{tuple(data['shape_reduced'])} -> {args.output}")


if __name__ == "__main__":
    main()
