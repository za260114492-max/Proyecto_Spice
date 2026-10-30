#!/usr/bin/env python3
"""
build_nodal_system.py

Purpose:
    Assemble the classical nodal system for compatible linear circuits.
    The MVP supports passive admittances (R, C, L in AC) and independent
    current sources. Ideal voltage sources are explicitly rejected because
    they require Tableau or Modified Nodal Analysis.

Author: Dr. Francisco E. Rangel-Patiño
"""
from __future__ import annotations

import argparse
import cmath
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from build_circuit_model import Circuit, load_circuit


class NodalCompatibilityError(ValueError):
    """Raised when classical nodal analysis cannot represent the circuit."""


def complex_to_json(value: complex) -> dict[str, float]:
    return {"real": float(value.real), "imag": float(value.imag)}


def complex_matrix_to_json(matrix: np.ndarray) -> list[list[dict[str, float]]]:
    return [[complex_to_json(complex(v)) for v in row] for row in matrix]


def complex_vector_to_json(vector: np.ndarray) -> list[dict[str, float]]:
    return [complex_to_json(complex(v)) for v in vector.reshape(-1)]


def phasor(magnitude: float, phase_deg: float | None) -> complex:
    return cmath.rect(magnitude, math.radians(phase_deg or 0.0))


def branch_admittance(element_type: str, value: float, frequency_hz: float | None) -> complex:
    if element_type == "R":
        return 1.0 / value
    if element_type == "C":
        if frequency_hz is None:
            # DC steady state: capacitor is open.
            return 0.0 + 0.0j
        return 1j * 2.0 * math.pi * frequency_hz * value
    if element_type == "L":
        if frequency_hz is None or frequency_hz == 0:
            raise NodalCompatibilityError("Ideal inductor at DC requires a dedicated DC/MNA treatment")
        return 1.0 / (1j * 2.0 * math.pi * frequency_hz * value)
    raise NodalCompatibilityError(f"Element type {element_type} is not an admittance branch")


def build_nodal_system(
    circuit: Circuit,
    incidence_data: dict[str, Any],
    frequency_hz: float | None = None,
) -> dict[str, Any]:
    """Build M*Vn=b using A*Y*A.T and orientation-consistent current injections."""
    a = np.array(incidence_data["A_reduced"], dtype=float)
    branch_order = incidence_data["branch_order"]
    if branch_order != [b.id for b in circuit.branches]:
        raise NodalCompatibilityError("Incidence branch order does not match circuit branch order")
    b_count = len(circuit.branches)
    y_diag = np.zeros(b_count, dtype=complex)
    current_branch = np.zeros(b_count, dtype=complex)
    unsupported: list[str] = []

    for branch in circuit.branches:
        if branch.element_type in {"R", "C", "L"}:
            y_diag[branch.index] = branch_admittance(branch.element_type, branch.value_si, frequency_hz)
        elif branch.element_type == "I":
            if frequency_hz is None:
                current_branch[branch.index] = branch.value_si if branch.source_kind == "DC" else 0.0
            else:
                current_branch[branch.index] = (
                    phasor(branch.ac_magnitude or 0.0, branch.ac_phase_deg)
                    if branch.source_kind == "AC"
                    else branch.value_si
                )
        elif branch.element_type == "V":
            unsupported.append(f"{branch.component_name}: ideal voltage source")
        else:
            unsupported.append(f"{branch.component_name}: type {branch.element_type}")
    if unsupported:
        raise NodalCompatibilityError(
            "Classical nodal analysis cannot directly represent: " + ", ".join(unsupported)
            + ". Use Tableau or MNA."
        )

    y = np.diag(y_diag)
    # Each current source value follows branch orientation node_from -> node_to.
    # KCL with A(+ leaving, - entering): A*(Y*A.T*Vn + J) = 0.
    # Therefore A*Y*A.T*Vn = -A*J.
    m = a @ y @ a.T
    rhs = -(a @ current_branch)
    if m.shape[0] != m.shape[1]:
        raise NodalCompatibilityError("Nodal system matrix is not square")
    return {
        "schema_version": "1.0",
        "source_name": circuit.source_name,
        "analysis": "AC" if frequency_hz is not None else "DC",
        "frequency_hz": frequency_hz,
        "node_order": incidence_data["node_order_reduced"],
        "branch_order": branch_order,
        "component_order": incidence_data["component_order"],
        "A_reduced": incidence_data["A_reduced"],
        "Y_branch": complex_matrix_to_json(y),
        "J_branch": complex_vector_to_json(current_branch),
        "M": complex_matrix_to_json(m),
        "rhs": complex_vector_to_json(rhs),
        "shape": list(m.shape),
    }


def load_incidence(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble a classical nodal system")
    parser.add_argument("circuit_json")
    parser.add_argument("incidence_json")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--frequency", type=float, help="Frequency in Hz; omit for DC")
    args = parser.parse_args()
    circuit = load_circuit(args.circuit_json)
    data = build_nodal_system(circuit, load_incidence(args.incidence_json), args.frequency)
    Path(args.output).write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Built {data['analysis']} nodal system {tuple(data['shape'])} -> {args.output}")


if __name__ == "__main__":
    main()
