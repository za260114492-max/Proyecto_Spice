#!/usr/bin/env python3
"""Solve and validate an AC frequency sweep using the Tableau workflow."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

from circuit_identity import circuit_signature
from build_circuit_model import Circuit, load_circuit
from build_constitutive_matrices import build_constitutive_matrices
from build_incidence_matrix import build_incidence_matrices
from build_tableau_system import build_tableau_system
from solve_linear_system import LinearSystemError, solve_tableau_system
from stamp_elements import build_element_stamps
from validate_solution import validate_tableau_solution


class ACSweepError(ValueError):
    """Raised when an AC sweep request is invalid or ambiguous."""


def frequencies_from_directive(directive: dict[str, Any]) -> list[float]:
    """Create a deterministic LIN/DEC frequency vector, including both endpoints."""
    sweep = directive.get("sweep")
    points = directive.get("points")
    start = directive.get("f_start_hz")
    stop = directive.get("f_stop_hz")
    if not isinstance(sweep, str) or sweep not in {"LIN", "DEC"}:
        raise ACSweepError("AC sweep directive must use LIN or DEC")
    if (
        not isinstance(points, int)
        or isinstance(points, bool)
        or points <= 0
        or isinstance(start, bool)
        or not isinstance(start, (int, float))
        or not math.isfinite(start)
        or isinstance(stop, bool)
        or not isinstance(stop, (int, float))
        or not math.isfinite(stop)
        or start <= 0
        or stop < start
    ):
        raise ACSweepError("AC sweep points and frequency endpoints are invalid")
    if sweep == "LIN":
        if points == 1:
            if start != stop:
                raise ACSweepError("A one-point LIN sweep requires identical start and stop")
            return [float(start)]
        values = [float(value) for value in np.linspace(start, stop, points)]
        if any(not math.isfinite(value) or value <= 0 for value in values) or any(
            left >= right for left, right in zip(values, values[1:])
        ):
            raise ACSweepError("LIN sweep frequencies must be finite, positive, and increasing")
        return values

    if start == stop:
        return [float(start)]
    log_start = math.log10(start)
    intervals = (math.log10(stop) - log_start) * points
    full_steps = int(math.floor(intervals + 1e-12))
    values = [float(start)]
    for step in range(1, full_steps + 1):
        value = float(10.0 ** (log_start + step / points))
        if not math.isfinite(value) or value <= values[-1]:
            raise ACSweepError("DEC sweep generated a non-finite or repeated frequency")
        values.append(value)
    if not math.isclose(values[-1], stop, rel_tol=1e-12, abs_tol=0.0):
        values.append(float(stop))
    else:
        values[-1] = float(stop)
    if any(
        not math.isfinite(value) or value <= 0
        for value in values
    ) or any(left >= right for left, right in zip(values, values[1:])):
        raise ACSweepError("DEC sweep frequencies must be finite, positive, and increasing")
    return values


def _resolve_frequencies(
    circuit: Circuit,
    explicit_frequencies: list[float] | None,
) -> tuple[list[float], str]:
    if explicit_frequencies:
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
            for value in explicit_frequencies
        ):
            raise ACSweepError("Every explicit AC frequency must be finite and greater than zero")
        frequencies = [float(value) for value in explicit_frequencies]
        if frequencies != sorted(frequencies):
            raise ACSweepError("Explicit AC frequencies must be in ascending order")
        if len(set(frequencies)) != len(frequencies):
            raise ACSweepError("Explicit AC frequencies must not contain duplicates")
        if any(
            right - left <= max(abs(left), abs(right)) * 1e-14
            for left, right in zip(frequencies, frequencies[1:])
        ):
            raise ACSweepError("Adjacent AC frequencies are too close to distinguish numerically")
        if any(not math.isfinite(2 * math.pi * value) for value in frequencies):
            raise ACSweepError("AC angular frequency overflows for a requested frequency")
        if any(directive.get("command") == "AC" for directive in circuit.directives):
            raise ACSweepError(
                "Do not combine explicit --frequency values with a netlist .AC directive"
            )
        return frequencies, "EXPLICIT"

    directives = [
        directive
        for directive in circuit.directives
        if directive.get("command") == "AC"
    ]
    if len(directives) != 1:
        raise ACSweepError(
            "Provide exactly one .AC directive in the circuit or one or more --frequency values"
        )
    frequencies = frequencies_from_directive(directives[0])
    return frequencies, str(directives[0]["sweep"])


def _node_voltage(solution: dict[str, Any], node_order: list[str], node: str) -> complex:
    if node == "0":
        return 0.0 + 0.0j
    try:
        index = node_order.index(node)
        record = solution["raw"]["Vn"][index]
        return complex(record["real"], record["imag"])
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ACSweepError(f"Cannot recover voltage for node {node!r}") from exc


def _observable_record(value: complex, unit: str) -> dict[str, float]:
    return {
        "real": float(value.real),
        "imag": float(value.imag),
        "magnitude": float(abs(value)),
        "phase_deg": float(np.degrees(np.angle(value))),
        "unit": unit,
    }


def _resolve_observable_nodes(
    circuit: Circuit,
    input_node: str | None,
    output_node: str | None,
) -> tuple[str, str]:
    if (input_node is None) != (output_node is None):
        raise ACSweepError("Provide both input and output nodes, or neither")
    if input_node is None and output_node is None:
        probe_directives = [
            directive
            for directive in circuit.directives
            if directive.get("command") == "PROBE"
        ]
        if len(probe_directives) != 1:
            raise ACSweepError(
                "Provide --input-node and --output-node or one .PROBE AC V(input) V(output) directive"
            )
        probe_nodes = probe_directives[0].get("voltage_nodes")
        if (
            not isinstance(probe_nodes, list)
            or len(probe_nodes) != 2
            or any(not isinstance(node, str) or not node.strip() for node in probe_nodes)
        ):
            raise ACSweepError("The .PROBE directive must contain exactly two voltage nodes")
        input_node, output_node = probe_nodes
    if not isinstance(input_node, str) or not isinstance(output_node, str):
        raise ACSweepError("Input and output nodes must be strings")
    return input_node, output_node


def solve_ac_sweep(
    circuit: Circuit,
    incidence_data: dict[str, Any],
    input_node: str | None = None,
    output_node: str | None = None,
    frequencies: list[float] | None = None,
    atol: float = 1e-10,
    rtol: float = 1e-8,
    condition_warning: float = 1e12,
) -> dict[str, Any]:
    """Solve each AC point, validate it, and calculate node-voltage transfer."""
    input_node, output_node = _resolve_observable_nodes(circuit, input_node, output_node)
    if input_node not in {node.id for node in circuit.nodes}:
        raise ACSweepError(f"Input node {input_node!r} is not present in the circuit")
    if output_node not in {node.id for node in circuit.nodes}:
        raise ACSweepError(f"Output node {output_node!r} is not present in the circuit")
    if input_node == circuit.reference_node:
        raise ACSweepError("Input node cannot be the reference node")
    frequency_values, sweep_kind = _resolve_frequencies(circuit, frequencies)
    incidence = incidence_data
    points: list[dict[str, Any]] = []

    for frequency in frequency_values:
        point: dict[str, Any] = {"frequency_hz": frequency}
        try:
            stamps = build_element_stamps(circuit, "AC", frequency)
            constitutive = build_constitutive_matrices(circuit, stamps)
            tableau = build_tableau_system(circuit, incidence, constitutive)
            solution = solve_tableau_system(tableau, atol, rtol)
            validation = validate_tableau_solution(
                tableau,
                solution,
                atol,
                rtol,
                condition_warning,
            )
            point["solution_status"] = solution["status"]
            point["validation"] = validation
            point["status"] = validation["status"]
            if validation["status"] == "FAIL":
                point["error"] = "La solución no pasó las validaciones del sistema Tableau."
                points.append(point)
                continue

            node_order = tableau["unknown_order"]["node_voltage"]
            vin = _node_voltage(solution, node_order, input_node)
            vout = _node_voltage(solution, node_order, output_node)
            if abs(vin) == 0.0:
                point["status"] = "FAIL"
                point["error"] = (
                    f"La tensión de entrada en el nodo {input_node!r} es cero; "
                    "H(jw)=Vout/Vin no está definida."
                )
                points.append(point)
                continue

            transfer = vout / vin
            magnitude = float(abs(transfer))
            gain_db = (
                float(20.0 * math.log10(magnitude))
                if magnitude > 0.0
                else None
            )
            phase_deg = (
                float(np.degrees(np.angle(transfer)))
                if magnitude > 0.0
                else None
            )
            point["input_voltage"] = _observable_record(vin, "volt")
            point["output_voltage"] = _observable_record(vout, "volt")
            point["transfer_function"] = _observable_record(transfer, "dimensionless")
            point["gain_db"] = gain_db
            point["phase_deg"] = phase_deg
            if magnitude == 0.0:
                point["observable_warning"] = (
                    "H(jw)=0: la ganancia en dB y la fase no están definidas."
                )
            points.append(point)
        except (
            ACSweepError,
            LinearSystemError,
            ValueError,
            TypeError,
            KeyError,
            OverflowError,
            np.linalg.LinAlgError,
            FloatingPointError,
        ) as exc:
            point["status"] = "FAIL"
            point["error"] = str(exc)
            points.append(point)

    failed_points = sum(point.get("status") == "FAIL" for point in points)
    warning_points = sum(point.get("status") == "WARN" for point in points)
    status = "FAIL" if failed_points else ("WARN" if warning_points else "PASS")
    return {
        "schema_version": "1.0",
        "source_name": circuit.source_name,
        "circuit_signature": circuit_signature(circuit),
        "analysis": "AC",
        "sweep": sweep_kind,
        "transfer_definition": f"V(N{output_node}) / V(N{input_node})",
        "input_node": input_node,
        "output_node": output_node,
        "reference_node": circuit.reference_node,
        "frequency_count": len(frequency_values),
        "status": status,
        "failed_points": failed_points,
        "warning_points": warning_points,
        "atol": atol,
        "rtol": rtol,
        "condition_warning_threshold": condition_warning,
        "points": points,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Solve a validated Tableau AC sweep and compute Vout/Vin"
    )
    parser.add_argument("circuit_json", help="Circuit JSON from build_circuit_model.py")
    parser.add_argument("incidence_json", help="Incidence JSON from build_incidence_matrix.py")
    parser.add_argument("-o", "--output", required=True, help="AC sweep results JSON")
    parser.add_argument(
        "--input-node",
        help="Input voltage node measured to ground; defaults to the first node in .PROBE AC",
    )
    parser.add_argument(
        "--output-node",
        help="Output voltage node measured to ground; defaults to the second node in .PROBE AC",
    )
    parser.add_argument(
        "--frequency",
        type=float,
        action="append",
        help="Explicit AC frequency in Hz; repeat for a list (cannot combine with .AC)",
    )
    parser.add_argument("--atol", type=float, default=1e-10)
    parser.add_argument("--rtol", type=float, default=1e-8)
    parser.add_argument("--condition-warning", type=float, default=1e12)
    args = parser.parse_args()

    try:
        circuit = load_circuit(args.circuit_json)
        incidence = json.loads(
            Path(args.incidence_json).read_text(encoding="utf-8")
        )
        if not isinstance(incidence, dict):
            raise ACSweepError("Incidence JSON root must be an object")
        result = solve_ac_sweep(
            circuit,
            incidence,
            args.input_node,
            args.output_node,
            args.frequency,
            args.atol,
            args.rtol,
            args.condition_warning,
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: cannot run AC sweep: {exc}", file=sys.stderr)
        return 2

    try:
        Path(args.output).write_text(
            json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: cannot write AC sweep results {args.output!r}: {exc}", file=sys.stderr)
        return 2
    print(
        f"AC sweep {result['status']}: {result['frequency_count']} points, "
        f"{result['failed_points']} failed -> {args.output}"
    )
    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
