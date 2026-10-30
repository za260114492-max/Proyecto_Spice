#!/usr/bin/env python3
"""Assemble the full educational Tableau system T @ X = W_prime."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

from build_circuit_model import load_circuit


class TableauAssemblyError(ValueError):
    """Raised when circuit, incidence, and constitutive data are inconsistent."""


def _is_finite_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _complex_value(value: Any, label: str) -> complex:
    if not isinstance(value, dict) or set(value) != {"real", "imag"}:
        raise TableauAssemblyError(f"{label} must contain exactly 'real' and 'imag'")
    if not _is_finite_number(value["real"]) or not _is_finite_number(value["imag"]):
        raise TableauAssemblyError(f"{label} must contain finite numeric values")
    return complex(value["real"], value["imag"])


def _matrix(data: Any, label: str) -> np.ndarray:
    if not isinstance(data, list) or any(not isinstance(row, list) for row in data):
        raise TableauAssemblyError(f"{label} must be a matrix represented as nested lists")
    try:
        result = np.array(
            [
                [
                    _complex_value(value, f"{label}[{row},{column}]")
                    for column, value in enumerate(values)
                ]
                for row, values in enumerate(data)
            ],
            dtype=complex,
        )
    except ValueError as exc:
        raise TableauAssemblyError(f"{label} has inconsistent row lengths") from exc
    if result.ndim != 2:
        raise TableauAssemblyError(f"{label} must be two-dimensional")
    return result


def _vector(data: Any, label: str) -> np.ndarray:
    if not isinstance(data, list):
        raise TableauAssemblyError(f"{label} must be a list")
    return np.array(
        [_complex_value(value, f"{label}[{index}]") for index, value in enumerate(data)],
        dtype=complex,
    )


def _complex_record(value: complex) -> dict[str, float]:
    return {"real": float(value.real), "imag": float(value.imag)}


def _matrix_records(matrix: np.ndarray) -> list[list[dict[str, float]]]:
    return [
        [_complex_record(complex(value)) for value in row]
        for row in matrix
    ]


def _vector_records(vector: np.ndarray) -> list[dict[str, float]]:
    return [_complex_record(complex(value)) for value in vector]


def build_tableau_system(
    circuit: Any,
    incidence_data: dict[str, Any],
    constitutive_data: dict[str, Any],
) -> dict[str, Any]:
    """Build the square system using X=[Vb; I; Vn] and reduced incidence A."""
    branches = circuit.branches
    branch_order = [branch.id for branch in branches]
    node_order = [node.id for node in circuit.nodes if not node.is_reference]
    branch_count = len(branches)
    node_count = len(node_order)

    if incidence_data.get("schema_version") != "1.0":
        raise TableauAssemblyError("Unsupported incidence schema")
    if incidence_data.get("source_name") != circuit.source_name:
        raise TableauAssemblyError("Incidence source_name does not match the circuit")
    if incidence_data.get("reference_node") != circuit.reference_node:
        raise TableauAssemblyError("Incidence reference node does not match the circuit")
    if incidence_data.get("branch_order") != branch_order:
        raise TableauAssemblyError("Incidence branch order does not match the circuit")
    if incidence_data.get("node_order_reduced") != node_order:
        raise TableauAssemblyError("Incidence node order does not match the circuit")
    try:
        a = np.asarray(incidence_data.get("A_reduced"), dtype=float)
    except (TypeError, ValueError) as exc:
        raise TableauAssemblyError("A_reduced must be a rectangular numeric matrix") from exc
    if a.shape != (node_count, branch_count) or not np.isfinite(a).all():
        raise TableauAssemblyError(
            f"A_reduced must have shape {(node_count, branch_count)} and finite entries"
        )
    expected_a = np.zeros((node_count, branch_count), dtype=float)
    node_indices = {node: index for index, node in enumerate(node_order)}
    for branch in branches:
        if branch.node_from != circuit.reference_node:
            expected_a[node_indices[branch.node_from], branch.index] += 1
        if branch.node_to != circuit.reference_node:
            expected_a[node_indices[branch.node_to], branch.index] -= 1
    if not np.array_equal(a, expected_a):
        raise TableauAssemblyError(
            "A_reduced entries do not match circuit branch orientation and node order"
        )

    if constitutive_data.get("schema_version") != "1.0":
        raise TableauAssemblyError("Unsupported constitutive-matrix schema")
    if constitutive_data.get("source_name") != circuit.source_name:
        raise TableauAssemblyError("Constitutive source_name does not match the circuit")
    analysis = constitutive_data.get("analysis")
    if not isinstance(analysis, str) or analysis not in {"DC", "AC"}:
        raise TableauAssemblyError("Constitutive analysis must be 'DC' or 'AC'")
    if constitutive_data.get("row_order") != branch_order:
        raise TableauAssemblyError("Constitutive row order does not match circuit branch order")
    expected_unknown_order = {
        "branch_voltage": branch_order,
        "branch_current": branch_order,
    }
    if constitutive_data.get("unknown_order") != expected_unknown_order:
        raise TableauAssemblyError("Constitutive unknown order does not match circuit branches")

    y = _matrix(constitutive_data.get("Y"), "Y")
    z = _matrix(constitutive_data.get("Z"), "Z")
    w = _vector(constitutive_data.get("W"), "W")
    expected_matrix_shape = (branch_count, branch_count)
    if y.shape != expected_matrix_shape or z.shape != expected_matrix_shape:
        raise TableauAssemblyError(
            f"Y and Z must both have shape {expected_matrix_shape}"
        )
    if w.shape != (branch_count,):
        raise TableauAssemblyError(f"W must have shape {(branch_count,)}")
    if constitutive_data.get("shapes") != {
        "Y": list(y.shape),
        "Z": list(z.shape),
        "W": [branch_count],
    }:
        raise TableauAssemblyError("Constitutive shape metadata does not match matrix data")
    row_equations = constitutive_data.get("row_equations")
    if not isinstance(row_equations, list) or len(row_equations) != branch_count:
        raise TableauAssemblyError(
            "Constitutive row equation count does not match the branch count"
        )
    for branch, equation_row in zip(branches, row_equations):
        if not isinstance(equation_row, dict) or any(
            equation_row.get(key) != expected_value
            for key, expected_value in (
                ("row_index", branch.index),
                ("branch_id", branch.id),
                ("component_name", branch.component_name),
                ("source_line", branch.source_line),
                ("line_number", branch.line_number),
            )
        ):
            raise TableauAssemblyError(
                f"Constitutive equation row does not match branch {branch.id}"
            )

    size = 2 * branch_count + node_count
    tableau = np.zeros((size, size), dtype=complex)
    rhs = np.zeros(size, dtype=complex)
    vb_slice = slice(0, branch_count)
    current_slice = slice(branch_count, 2 * branch_count)
    node_slice = slice(2 * branch_count, size)

    # KVL: Vb - A.T @ Vn = 0
    tableau[vb_slice, vb_slice] = np.eye(branch_count)
    tableau[vb_slice, node_slice] = -a.T

    # Constitutive equations: Y @ Vb + Z @ I = W
    tableau[current_slice, vb_slice] = y
    tableau[current_slice, current_slice] = z
    rhs[current_slice] = w

    # KCL: A @ I = 0
    tableau[node_slice, current_slice] = a

    row_labels = (
        [f"KVL:{branch_id}" for branch_id in branch_order]
        + [f"CONSTITUTIVE:{branch_id}" for branch_id in branch_order]
        + [f"KCL:N{node_id}" for node_id in node_order]
    )
    column_labels = (
        [f"Vb:{branch_id}" for branch_id in branch_order]
        + [f"I:{branch_id}" for branch_id in branch_order]
        + [f"Vn:N{node_id}" for node_id in node_order]
    )
    return {
        "schema_version": "1.0",
        "source_name": circuit.source_name,
        "analysis": constitutive_data["analysis"],
        "frequency_hz": constitutive_data.get("frequency_hz"),
        "equation": "T @ X = W_prime",
        "unknown_order": {
            "X": ["Vb", "I", "Vn"],
            "branch_voltage": branch_order,
            "branch_current": branch_order,
            "node_voltage": node_order,
        },
        "index_map": {
            "Vb": [0, branch_count],
            "I": [branch_count, 2 * branch_count],
            "Vn": [2 * branch_count, size],
        },
        "row_order": row_labels,
        "column_order": column_labels,
        "row_blocks": {
            "KVL": [0, branch_count],
            "constitutive": [branch_count, 2 * branch_count],
            "KCL": [2 * branch_count, size],
        },
        "block_equations": {
            "KVL": "Vb - A.T @ Vn = 0",
            "constitutive": "Y @ Vb + Z @ I = W",
            "KCL": "A @ I = 0",
        },
        "blocks": {
            "A_reduced": a.tolist(),
            "Y": _matrix_records(y),
            "Z": _matrix_records(z),
            "W": _vector_records(w),
        },
        "T": _matrix_records(tableau),
        "W_prime": _vector_records(rhs),
        "shape": list(tableau.shape),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble the complete Tableau system")
    parser.add_argument("circuit_json", help="Circuit JSON from build_circuit_model.py")
    parser.add_argument("incidence_json", help="Incidence JSON from build_incidence_matrix.py")
    parser.add_argument(
        "constitutive_json",
        help="Constitutive matrices JSON from build_constitutive_matrices.py",
    )
    parser.add_argument("-o", "--output", required=True, help="Tableau system JSON")
    args = parser.parse_args()

    try:
        circuit = load_circuit(args.circuit_json)
        incidence = json.loads(Path(args.incidence_json).read_text(encoding="utf-8"))
        constitutive = json.loads(Path(args.constitutive_json).read_text(encoding="utf-8"))
        if not isinstance(incidence, dict) or not isinstance(constitutive, dict):
            raise TableauAssemblyError("Input JSON roots must be objects")
        result = build_tableau_system(circuit, incidence, constitutive)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: cannot assemble Tableau system: {exc}", file=sys.stderr)
        return 1

    try:
        Path(args.output).write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"ERROR: cannot write Tableau system {args.output!r}: {exc}", file=sys.stderr)
        return 2
    print(f"Built Tableau system {tuple(result['shape'])} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
