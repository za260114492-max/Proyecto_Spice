#!/usr/bin/env python3
"""Independently validate a solved Tableau system and its electrical laws."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np


class SolutionValidationError(ValueError):
    """Raised when validation inputs violate the declared Tableau contract."""


def _is_finite_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _complex_value(value: Any, label: str) -> complex:
    if not isinstance(value, dict) or set(value) != {"real", "imag"}:
        raise SolutionValidationError(f"{label} must contain exactly 'real' and 'imag'")
    if not _is_finite_number(value["real"]) or not _is_finite_number(value["imag"]):
        raise SolutionValidationError(f"{label} must contain finite numeric values")
    return complex(value["real"], value["imag"])


def _matrix(data: Any, label: str) -> np.ndarray:
    if not isinstance(data, list) or any(not isinstance(row, list) for row in data):
        raise SolutionValidationError(f"{label} must be a matrix")
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
        raise SolutionValidationError(f"{label} has inconsistent row lengths") from exc
    if result.ndim != 2:
        raise SolutionValidationError(f"{label} must be two-dimensional")
    return result


def _vector(data: Any, label: str) -> np.ndarray:
    if not isinstance(data, list):
        raise SolutionValidationError(f"{label} must be a vector")
    return np.array(
        [_complex_value(value, f"{label}[{index}]") for index, value in enumerate(data)],
        dtype=complex,
    )


def _metric(residual: np.ndarray, scale: float, atol: float, rtol: float) -> dict[str, Any]:
    norm = float(np.linalg.norm(residual))
    tolerance = float(atol + rtol * scale)
    return {
        "norm": norm,
        "scale": float(scale),
        "tolerance": tolerance,
        "passed": bool(norm <= tolerance),
    }


def validate_tableau_solution(
    system: dict[str, Any],
    solution: dict[str, Any],
    atol: float = 1e-10,
    rtol: float = 1e-8,
    condition_warning: float = 1e12,
) -> dict[str, Any]:
    """Check dimensions, finite values, rank/conditioning, and four residuals."""
    for label, value in (
        ("atol", atol),
        ("rtol", rtol),
        ("condition_warning", condition_warning),
    ):
        if not _is_finite_number(value) or value < 0:
            raise SolutionValidationError(f"{label} must be finite and nonnegative")
    if condition_warning == 0:
        raise SolutionValidationError("condition_warning must be greater than zero")
    if system.get("schema_version") != "1.0":
        raise SolutionValidationError("Unsupported Tableau system schema")
    if system.get("equation") != "T @ X = W_prime":
        raise SolutionValidationError("Unsupported Tableau equation convention")
    if solution.get("schema_version") != "1.0":
        raise SolutionValidationError("Unsupported solution schema")
    for key in ("source_name", "analysis", "frequency_hz"):
        if solution.get(key) != system.get(key):
            raise SolutionValidationError(f"Solution and Tableau system mismatch: {key}")

    matrix = _matrix(system.get("T"), "T")
    rhs = _vector(system.get("W_prime"), "W_prime")
    if matrix.shape[0] != matrix.shape[1] or rhs.shape != (matrix.shape[0],):
        raise SolutionValidationError("Tableau matrix and W_prime dimensions are inconsistent")
    if system.get("shape") != list(matrix.shape):
        raise SolutionValidationError("Tableau shape metadata does not match T")
    if not np.isfinite(matrix).all() or not np.isfinite(rhs).all():
        raise SolutionValidationError("Tableau system contains NaN or infinite values")

    blocks = system.get("blocks")
    index_map = system.get("index_map")
    if not isinstance(blocks, dict) or not isinstance(index_map, dict):
        raise SolutionValidationError("Tableau blocks or index_map are missing")
    a = np.asarray(blocks.get("A_reduced"), dtype=float)
    y = _matrix(blocks.get("Y"), "Y")
    z = _matrix(blocks.get("Z"), "Z")
    w = _vector(blocks.get("W"), "W")
    if not np.isfinite(a).all():
        raise SolutionValidationError("A_reduced contains NaN or infinite values")
    branch_count = y.shape[0]
    if (
        y.shape != (branch_count, branch_count)
        or z.shape != (branch_count, branch_count)
        or w.shape != (branch_count,)
        or a.ndim != 2
        or a.shape[1] != branch_count
    ):
        raise SolutionValidationError("A, Y, Z, or W dimensions are inconsistent")
    node_count = a.shape[0]
    expected_size = 2 * branch_count + node_count
    if matrix.shape != (expected_size, expected_size):
        raise SolutionValidationError(
            f"T must have shape {(expected_size, expected_size)}"
        )
    if system.get("index_map") != {
        "Vb": [0, branch_count],
        "I": [branch_count, 2 * branch_count],
        "Vn": [2 * branch_count, expected_size],
    }:
        raise SolutionValidationError("Tableau index_map is inconsistent with block dimensions")

    raw = solution.get("raw")
    if not isinstance(raw, dict):
        raise SolutionValidationError("Solution raw variables are missing")
    unknowns = _vector(raw.get("X"), "solution.raw.X")
    if unknowns.shape != (expected_size,) or not np.isfinite(unknowns).all():
        raise SolutionValidationError("Solution X has invalid dimensions or non-finite values")
    vb = unknowns[:branch_count]
    currents = unknowns[branch_count : 2 * branch_count]
    node_voltages = unknowns[2 * branch_count :]

    for key, expected in (("Vb", vb), ("I", currents), ("Vn", node_voltages)):
        reported = _vector(raw.get(key), f"solution.raw.{key}")
        if reported.shape != expected.shape or not np.allclose(
            reported, expected, atol=atol, rtol=rtol
        ):
            raise SolutionValidationError(
                f"Solution raw.{key} does not match the corresponding slice of X"
            )

    rank = int(np.linalg.matrix_rank(matrix))
    condition = float(np.linalg.cond(matrix))
    if not np.isfinite(condition):
        condition = float("inf")
    global_residual = matrix @ unknowns - rhs
    global_scale = float(
        np.linalg.norm(matrix) * np.linalg.norm(unknowns) + np.linalg.norm(rhs)
    )
    global_norm = float(np.linalg.norm(global_residual))
    normalized_residual = global_norm / global_scale if global_scale else global_norm
    residuals = {
        "global": _metric(global_residual, global_scale, atol, rtol),
        "kcl": _metric(
            a @ currents,
            float(np.linalg.norm(a) * np.linalg.norm(currents)),
            atol,
            rtol,
        ),
        "branch_voltage": _metric(
            vb - a.T @ node_voltages,
            float(np.linalg.norm(vb) + np.linalg.norm(a.T @ node_voltages)),
            atol,
            rtol,
        ),
        "constitutive": _metric(
            y @ vb + z @ currents - w,
            float(
                np.linalg.norm(y @ vb)
                + np.linalg.norm(z @ currents)
                + np.linalg.norm(w)
            ),
            atol,
            rtol,
        ),
    }
    residuals["tableau"] = _metric(
        global_residual,
        global_scale,
        atol,
        rtol,
    )

    failures: list[str] = []
    warnings: list[str] = []
    if rank < matrix.shape[0]:
        failures.append(
            f"Tableau matrix is rank deficient ({rank}/{matrix.shape[0]})."
        )
    for name, result in residuals.items():
        if not result["passed"]:
            failures.append(
                f"{name} residual {result['norm']:.3e} exceeds "
                f"tolerance {result['tolerance']:.3e}."
            )
    if condition > condition_warning:
        warnings.append(
            f"Condition number {condition:.3e} exceeds warning threshold "
            f"{condition_warning:.3e}; limit reported precision."
        )
    status = "FAIL" if failures else ("WARN" if warnings else "PASS")
    return {
        "schema_version": "1.0",
        "source_name": system.get("source_name"),
        "analysis": system.get("analysis"),
        "frequency_hz": system.get("frequency_hz"),
        "status": status,
        "rank": rank,
        "size": matrix.shape[0],
        "condition_number": condition if np.isfinite(condition) else None,
        "condition_warning_threshold": condition_warning,
        "residuals": residuals,
        "normalized_residual": normalized_residual,
        "atol": atol,
        "rtol": rtol,
        "errors": failures,
        "warnings": warnings,
        "diagnostics": [
            "Rank deficiency may indicate floating nodes, disconnected topology, "
            "redundant equations, or incompatible ideal-source constraints."
        ]
        if failures and rank < matrix.shape[0]
        else [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Tableau solution residuals and numerical conditioning"
    )
    parser.add_argument("tableau_json", help="Tableau JSON from build_tableau_system.py")
    parser.add_argument("solution_json", help="Solved JSON from solve_linear_system.py --tableau")
    parser.add_argument("-o", "--output", required=True, help="Validation report JSON")
    parser.add_argument("--atol", type=float, default=1e-10)
    parser.add_argument("--rtol", type=float, default=1e-8)
    parser.add_argument("--condition-warning", type=float, default=1e12)
    args = parser.parse_args()

    try:
        system = json.loads(Path(args.tableau_json).read_text(encoding="utf-8"))
        solution = json.loads(Path(args.solution_json).read_text(encoding="utf-8"))
        if not isinstance(system, dict) or not isinstance(solution, dict):
            raise SolutionValidationError("Input JSON roots must be objects")
        report = validate_tableau_solution(
            system,
            solution,
            args.atol,
            args.rtol,
            args.condition_warning,
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        report = {
            "schema_version": "1.0",
            "status": "FAIL",
            "errors": [str(exc)],
            "warnings": [],
            "diagnostics": [],
        }

    try:
        Path(args.output).write_text(
            json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: cannot write validation report {args.output!r}: {exc}", file=sys.stderr)
        return 2
    print(f"Solution validation: {report['status']} -> {args.output}")
    for error in report.get("errors", []):
        print(f"ERROR: {error}", file=sys.stderr)
    for warning in report.get("warnings", []):
        print(f"WARNING: {warning}")
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
