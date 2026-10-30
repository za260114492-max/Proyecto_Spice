#!/usr/bin/env python3
"""Assemble traceable Tableau Y, Z, and W from scalar branch stamps."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

from build_circuit_model import Circuit, load_circuit


class ConstitutiveMatrixError(ValueError):
    """Raised when branch stamps cannot form consistent constitutive matrices."""


def _is_finite_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _read_complex(value: Any, label: str) -> complex:
    if not isinstance(value, dict) or set(value) != {"real", "imag"}:
        raise ConstitutiveMatrixError(f"{label} must contain exactly 'real' and 'imag'")
    real, imag = value["real"], value["imag"]
    if (
        not _is_finite_number(real)
        or not _is_finite_number(imag)
    ):
        raise ConstitutiveMatrixError(f"{label} must contain finite numeric values")
    return complex(real, imag)


def _complex_record(value: complex) -> dict[str, float]:
    return {"real": float(value.real), "imag": float(value.imag)}


def _complex_matrix_records(matrix: np.ndarray) -> list[list[dict[str, float]]]:
    return [
        [_complex_record(complex(value)) for value in row]
        for row in matrix
    ]


def _complex_vector_records(vector: np.ndarray) -> list[dict[str, float]]:
    return [_complex_record(complex(value)) for value in vector]


def build_constitutive_matrices(
    circuit: Circuit,
    stamps_data: dict[str, Any],
) -> dict[str, Any]:
    """Build diagonal constitutive matrices in circuit branch order.

    The resulting relation is ``Y @ Vb + Z @ I = W``. Each row represents
    one branch equation; its metadata retains the source and equation trace.
    """
    if stamps_data.get("schema_version") != "1.0":
        raise ConstitutiveMatrixError(
            f"Unsupported stamp schema: {stamps_data.get('schema_version')!r}"
        )
    if stamps_data.get("source_name") != circuit.source_name:
        raise ConstitutiveMatrixError("Stamp source_name does not match the circuit")
    analysis = stamps_data.get("analysis")
    if not isinstance(analysis, str) or analysis not in {"DC", "AC"}:
        raise ConstitutiveMatrixError("Stamp analysis must be 'DC' or 'AC'")
    if stamps_data.get("equation_convention") != "Y*V_branch + Z*I_branch = W":
        raise ConstitutiveMatrixError("Stamp equation convention is missing or unsupported")
    expected_frequency = stamps_data.get("frequency_hz")
    if analysis == "DC":
        if expected_frequency is not None:
            raise ConstitutiveMatrixError("DC stamps must not define frequency_hz")
        expected_omega = 0.0
    elif (
        not _is_finite_number(expected_frequency)
        or expected_frequency < 0
    ):
        raise ConstitutiveMatrixError("AC stamps require a finite, nonnegative frequency_hz")
    else:
        expected_omega = 2.0 * math.pi * expected_frequency
    omega = stamps_data.get("omega_rad_s")
    if (
        not _is_finite_number(omega)
        or not math.isclose(omega, expected_omega, rel_tol=1e-12, abs_tol=1e-12)
    ):
        raise ConstitutiveMatrixError("Stamp omega_rad_s does not match the analysis frequency")

    branches = circuit.branches
    expected_order = [branch.id for branch in branches]
    stamp_order = stamps_data.get("branch_order")
    if stamp_order != expected_order:
        raise ConstitutiveMatrixError(
            "Stamp branch_order does not match circuit branch order"
        )
    stamps = stamps_data.get("stamps")
    if not isinstance(stamps, list) or len(stamps) != len(branches):
        raise ConstitutiveMatrixError(
            "Stamp count does not match the number of circuit branches"
        )

    size = len(branches)
    y_matrix = np.zeros((size, size), dtype=complex)
    z_matrix = np.zeros((size, size), dtype=complex)
    w_vector = np.zeros(size, dtype=complex)
    equation_rows: list[dict[str, Any]] = []
    seen_branch_ids: set[str] = set()

    for row_index, (branch, stamp) in enumerate(zip(branches, stamps)):
        if not isinstance(stamp, dict):
            raise ConstitutiveMatrixError(
                f"Stamp at row {row_index} must be an object"
            )
        branch_id = branch.id
        if branch_id in seen_branch_ids:
            raise ConstitutiveMatrixError(f"Duplicate circuit branch id {branch_id!r}")
        seen_branch_ids.add(branch_id)
        expected_metadata = {
            "branch_id": branch.id,
            "component_name": branch.component_name,
            "element_type": branch.element_type,
            "node_from": branch.node_from,
            "node_to": branch.node_to,
            "source_line": branch.source_line,
            "line_number": branch.line_number,
        }
        for key, expected_value in expected_metadata.items():
            if stamp.get(key) != expected_value:
                raise ConstitutiveMatrixError(
                    f"Stamp metadata mismatch for {branch_id}: {key}"
                )
        for key in ("Y_unit", "Z_unit", "W_unit"):
            unit = stamp.get(key)
            if not isinstance(unit, str) or not unit.strip():
                raise ConstitutiveMatrixError(
                    f"Stamp {branch_id} must define a non-empty {key}"
                )
        equation = stamp.get("equation")
        if not isinstance(equation, str) or not equation.strip():
            raise ConstitutiveMatrixError(
                f"Stamp {branch_id} must include a non-empty equation"
            )
        y_value = _read_complex(stamp.get("Y"), f"{branch_id}.Y")
        z_value = _read_complex(stamp.get("Z"), f"{branch_id}.Z")
        w_value = _read_complex(stamp.get("W"), f"{branch_id}.W")
        y_matrix[row_index, row_index] = y_value
        z_matrix[row_index, row_index] = z_value
        w_vector[row_index] = w_value
        equation_rows.append(
            {
                "row_index": row_index,
                "branch_id": branch.id,
                "component_name": branch.component_name,
                "element_type": branch.element_type,
                "equation": equation,
                "source_line": branch.source_line,
                "line_number": branch.line_number,
                "Y_unit": stamp.get("Y_unit"),
                "Z_unit": stamp.get("Z_unit"),
                "W_unit": stamp.get("W_unit"),
            }
        )

    return {
        "schema_version": "1.0",
        "source_name": circuit.source_name,
        "analysis": analysis,
        "frequency_hz": expected_frequency,
        "omega_rad_s": omega,
        "equation_convention": "Y @ Vb + Z @ I = W",
        "unknown_order": {
            "branch_voltage": expected_order,
            "branch_current": expected_order,
        },
        "row_order": expected_order,
        "row_equations": equation_rows,
        "Y": _complex_matrix_records(y_matrix),
        "Z": _complex_matrix_records(z_matrix),
        "W": _complex_vector_records(w_vector),
        "shapes": {
            "Y": list(y_matrix.shape),
            "Z": list(z_matrix.shape),
            "W": [size],
        },
        "row_units": {
            "Y": [row["Y_unit"] for row in equation_rows],
            "Z": [row["Z_unit"] for row in equation_rows],
            "W": [row["W_unit"] for row in equation_rows],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assemble traceable Tableau constitutive matrices Y, Z, and W"
    )
    parser.add_argument("circuit_json", help="Circuit JSON from build_circuit_model.py")
    parser.add_argument("stamps_json", help="Branch stamps JSON from stamp_elements.py")
    parser.add_argument("-o", "--output", required=True, help="Constitutive matrices JSON")
    args = parser.parse_args()

    try:
        circuit = load_circuit(args.circuit_json)
        stamps_data = json.loads(
            Path(args.stamps_json).read_text(encoding="utf-8")
        )
        if not isinstance(stamps_data, dict):
            raise ConstitutiveMatrixError("Stamps JSON root must be an object")
        matrices = build_constitutive_matrices(circuit, stamps_data)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: cannot build constitutive matrices: {exc}", file=sys.stderr)
        return 1

    try:
        Path(args.output).write_text(
            json.dumps(matrices, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print(
            f"ERROR: cannot write constitutive matrices {args.output!r}: {exc}",
            file=sys.stderr,
        )
        return 2

    print(
        f"Built constitutive matrices for {len(matrices['row_order'])} branches "
        f"-> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
