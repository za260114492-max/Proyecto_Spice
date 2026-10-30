#!/usr/bin/env python3
"""
solve_linear_system.py

Purpose:
    Solve the nodal system created by build_nodal_system.py with NumPy,
    compute numerical diagnostics, recover passive/source branch currents,
    and verify the linear-system and KCL residuals.

Author: Dr. Francisco E. Rangel-Patiño
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from build_circuit_model import Circuit, load_circuit


class LinearSystemError(RuntimeError):
    """Raised when a system is singular, malformed, or fails validation."""


def json_to_complex(value: dict[str, float]) -> complex:
    return complex(value["real"], value["imag"])


def json_to_complex_matrix(data: list[list[dict[str, float]]]) -> np.ndarray:
    return np.array([[json_to_complex(v) for v in row] for row in data], dtype=complex)


def json_to_complex_vector(data: list[dict[str, float]]) -> np.ndarray:
    return np.array([json_to_complex(v) for v in data], dtype=complex)


def complex_to_json(value: complex) -> dict[str, float]:
    return {"real": float(value.real), "imag": float(value.imag)}


def vector_records(labels: list[str], values: np.ndarray, unit: str) -> list[dict[str, Any]]:
    return [
        {
            "label": label,
            "real": float(complex(value).real),
            "imag": float(complex(value).imag),
            "magnitude": float(abs(value)),
            "phase_deg": float(np.degrees(np.angle(value))),
            "unit": unit,
        }
        for label, value in zip(labels, values.reshape(-1))
    ]


def solve_nodal_system(
    system: dict[str, Any],
    circuit: Circuit,
    atol: float = 1e-10,
    rtol: float = 1e-8,
) -> dict[str, Any]:
    m = json_to_complex_matrix(system["M"])
    rhs = json_to_complex_vector(system["rhs"])
    a = np.array(system["A_reduced"], dtype=float)
    y = json_to_complex_matrix(system["Y_branch"])
    j_branch = json_to_complex_vector(system["J_branch"])
    if m.shape[0] != m.shape[1] or rhs.shape != (m.shape[0],):
        raise LinearSystemError("Malformed linear-system dimensions")
    rank = int(np.linalg.matrix_rank(m))
    condition = float(np.linalg.cond(m))
    if rank < m.shape[0] or not np.isfinite(condition):
        raise LinearSystemError(
            f"Singular nodal system: rank={rank}, size={m.shape[0]}, condition={condition}"
        )
    try:
        vn = np.linalg.solve(m, rhs)
    except np.linalg.LinAlgError as exc:
        raise LinearSystemError(f"NumPy could not solve the system: {exc}") from exc

    vb = a.T @ vn
    currents = y @ vb + j_branch
    residual = m @ vn - rhs
    kcl = a @ currents
    residual_norm = float(np.linalg.norm(residual))
    kcl_norm = float(np.linalg.norm(kcl))
    scale = float(np.linalg.norm(m) * np.linalg.norm(vn) + np.linalg.norm(rhs))
    normalized_residual = residual_norm / scale if scale else residual_norm
    passed = bool(
        np.allclose(m @ vn, rhs, atol=atol, rtol=rtol)
        and np.allclose(kcl, 0.0, atol=atol, rtol=rtol)
    )
    if not passed:
        raise LinearSystemError(
            f"Solution failed validation: residual={residual_norm:.3e}, KCL={kcl_norm:.3e}"
        )
    branch_labels = [
        f"{branch.id} ({branch.component_name})" for branch in circuit.branches
    ]
    return {
        "schema_version": "1.0",
        "source_name": system["source_name"],
        "analysis": system["analysis"],
        "frequency_hz": system.get("frequency_hz"),
        "status": "PASS",
        "rank": rank,
        "condition_number": condition,
        "residual_norm": residual_norm,
        "normalized_residual": normalized_residual,
        "kcl_norm": kcl_norm,
        "atol": atol,
        "rtol": rtol,
        "node_voltages": vector_records([f"V(N{n})" for n in system["node_order"]], vn, "volt"),
        "branch_voltages": vector_records(branch_labels, vb, "volt"),
        "branch_currents": vector_records(branch_labels, currents, "ampere"),
        "raw": {
            "Vn": [complex_to_json(v) for v in vn],
            "Vb": [complex_to_json(v) for v in vb],
            "I": [complex_to_json(v) for v in currents],
        },
    }


def solve_tableau_system(
    system: dict[str, Any],
    atol: float = 1e-10,
    rtol: float = 1e-8,
) -> dict[str, Any]:
    """Solve a Tableau system and expose branch and node variables.

    The result is marked SOLVED_NOT_VALIDATED. Use validate_solution.py as
    the independent acceptance gate before presenting it as an accepted result.
    """
    try:
        matrix = json_to_complex_matrix(system["T"])
        rhs = json_to_complex_vector(system["W_prime"])
        shape = system["shape"]
        index_map = system["index_map"]
        unknown_order = system["unknown_order"]
    except (KeyError, TypeError, ValueError) as exc:
        raise LinearSystemError(f"Malformed Tableau system: {exc}") from exc

    if (
        not isinstance(shape, list)
        or len(shape) != 2
        or matrix.shape != tuple(shape)
        or matrix.shape[0] != matrix.shape[1]
        or rhs.shape != (matrix.shape[0],)
    ):
        raise LinearSystemError("Malformed Tableau matrix or right-hand-side dimensions")
    if not np.isfinite(matrix).all() or not np.isfinite(rhs).all():
        raise LinearSystemError("Tableau system contains NaN or infinite values")
    if not isinstance(index_map, dict) or not isinstance(unknown_order, dict):
        raise LinearSystemError("Tableau index map or unknown ordering is malformed")

    def variable_slice(name: str) -> slice:
        bounds = index_map.get(name)
        if (
            not isinstance(bounds, list)
            or len(bounds) != 2
            or any(not isinstance(value, int) or isinstance(value, bool) for value in bounds)
        ):
            raise LinearSystemError(f"Invalid Tableau index range for {name}")
        start, stop = bounds
        if start < 0 or stop < start or stop > matrix.shape[1]:
            raise LinearSystemError(f"Out-of-range Tableau index range for {name}")
        return slice(start, stop)

    vb_slice = variable_slice("Vb")
    current_slice = variable_slice("I")
    node_slice = variable_slice("Vn")
    vb_order = unknown_order.get("branch_voltage")
    current_order = unknown_order.get("branch_current")
    node_order = unknown_order.get("node_voltage")
    if not all(isinstance(order, list) for order in (vb_order, current_order, node_order)):
        raise LinearSystemError("Tableau variable labels are malformed")
    if (
        vb_slice.stop - vb_slice.start != len(vb_order)
        or current_slice.stop - current_slice.start != len(current_order)
        or node_slice.stop - node_slice.start != len(node_order)
        or vb_slice.start != 0
        or vb_slice.stop != current_slice.start
        or current_slice.stop != node_slice.start
        or node_slice.stop != matrix.shape[1]
    ):
        raise LinearSystemError("Tableau index map does not match the variable ordering")
    rank = int(np.linalg.matrix_rank(matrix))
    condition = float(np.linalg.cond(matrix))
    if rank < matrix.shape[0] or not np.isfinite(condition):
        raise LinearSystemError(
            f"Singular Tableau system: rank={rank}, size={matrix.shape[0]}, condition={condition}"
        )
    try:
        unknowns = np.linalg.solve(matrix, rhs)
    except np.linalg.LinAlgError as exc:
        raise LinearSystemError(f"NumPy could not solve the Tableau system: {exc}") from exc

    vb = unknowns[vb_slice]
    currents = unknowns[current_slice]
    node_voltages = unknowns[node_slice]
    residual = matrix @ unknowns - rhs
    residual_norm = float(np.linalg.norm(residual))
    residual_scale = float(
        np.linalg.norm(matrix) * np.linalg.norm(unknowns) + np.linalg.norm(rhs)
    )
    normalized_residual = residual_norm / residual_scale if residual_scale else residual_norm
    return {
        "schema_version": "1.0",
        "source_name": system.get("source_name"),
        "analysis": system.get("analysis"),
        "frequency_hz": system.get("frequency_hz"),
        "status": "SOLVED_NOT_VALIDATED",
        "rank": rank,
        "condition_number": condition,
        "residual_norm": residual_norm,
        "normalized_residual": normalized_residual,
        "atol": atol,
        "rtol": rtol,
        "node_voltages": vector_records(
            [f"V(N{node})" for node in node_order], node_voltages, "volt"
        ),
        "branch_voltages": vector_records(
            [f"V({branch})" for branch in vb_order], vb, "volt"
        ),
        "branch_currents": vector_records(
            [f"I({branch})" for branch in current_order], currents, "ampere"
        ),
        "raw": {
            "X": [complex_to_json(value) for value in unknowns],
            "Vb": [complex_to_json(value) for value in vb],
            "I": [complex_to_json(value) for value in currents],
            "Vn": [complex_to_json(value) for value in node_voltages],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Solve a nodal or Tableau linear system")
    parser.add_argument("system_json", nargs="?", help="Nodal system JSON")
    parser.add_argument("circuit_json", nargs="?", help="Circuit JSON (nodal mode)")
    parser.add_argument("--tableau", help="Tableau system JSON (Tableau mode)")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--atol", type=float, default=1e-10)
    parser.add_argument("--rtol", type=float, default=1e-8)
    args = parser.parse_args()
    try:
        if args.tableau:
            if args.system_json or args.circuit_json:
                parser.error("Use --tableau without nodal positional inputs")
            system = json.loads(Path(args.tableau).read_text(encoding="utf-8"))
            result = solve_tableau_system(system, args.atol, args.rtol)
        else:
            if not args.system_json or not args.circuit_json:
                parser.error("Nodal mode requires system_json and circuit_json")
            system = json.loads(Path(args.system_json).read_text(encoding="utf-8"))
            circuit = load_circuit(args.circuit_json)
            result = solve_nodal_system(system, circuit, args.atol, args.rtol)
        Path(args.output).write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        LinearSystemError,
    ) as exc:
        parser.exit(1, f"ERROR: cannot solve linear system: {exc}\n")
    print(f"Solved {result['analysis']} system: {result['status']} -> {args.output}")
    for item in result["node_voltages"]:
        print(
            f"{item['label']} = {item['real']:.9g} + "
            f"j{item['imag']:.9g} {item['unit']}"
        )


if __name__ == "__main__":
    main()
