#!/usr/bin/env python3
"""Compare validated AC sweep results with aligned analytical/SPICE reference data."""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

from circuit_identity import circuit_signature
from build_circuit_model import Circuit, load_circuit


class ReferenceComparisonError(ValueError):
    """Raised when simulation and reference datasets cannot be compared safely."""


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReferenceComparisonError(f"{label} must be a numeric value")
    result = float(value)
    if not math.isfinite(result):
        raise ReferenceComparisonError(f"{label} must be finite")
    return result


def _phase_error_deg(calculated: float, reference: float) -> float:
    return (calculated - reference + 180.0) % 360.0 - 180.0


def _validate_reference(
    reference: dict[str, Any],
    circuit: Circuit,
    input_node: str,
    output_node: str,
) -> tuple[list[dict[str, float]], str]:
    if reference.get("schema_version") != "1.0":
        raise ReferenceComparisonError("Unsupported reference schema_version")
    simulator = reference.get("simulator")
    if not isinstance(simulator, str) or not simulator.strip():
        raise ReferenceComparisonError("Reference must identify its simulator or analytical source")
    simulator_version = reference.get("simulator_version")
    if simulator_version is not None and not isinstance(simulator_version, str):
        raise ReferenceComparisonError("simulator_version must be a string or null")
    if reference.get("analysis") != "AC" or reference.get("frequency_unit") != "Hz":
        raise ReferenceComparisonError(
            "Reference must declare analysis='AC' and frequency_unit='Hz'"
        )
    if reference.get("input_node") != input_node or reference.get("output_node") != output_node:
        raise ReferenceComparisonError("Reference input/output nodes do not match the AC sweep")
    expected_signature = circuit_signature(circuit)
    if reference.get("circuit_signature") != expected_signature:
        raise ReferenceComparisonError(
            "Reference circuit_signature does not match normalized component values, "
            "topology, orientation, and source definitions"
        )
    rows = reference.get("results")
    if not isinstance(rows, list) or not rows:
        raise ReferenceComparisonError("Reference results must be a non-empty list")
    normalized_rows: list[dict[str, float]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ReferenceComparisonError(f"Reference row {index} must be an object")
        frequency = _finite_number(
            row.get("frequency_hz"), f"reference[{index}].frequency_hz"
        )
        gain_db = _finite_number(row.get("gain_db"), f"reference[{index}].gain_db")
        phase_deg = _finite_number(row.get("phase_deg"), f"reference[{index}].phase_deg")
        if frequency <= 0:
            raise ReferenceComparisonError(f"Reference frequency at row {index} must be positive")
        normalized_rows.append(
            {"frequency_hz": frequency, "gain_db": gain_db, "phase_deg": phase_deg}
        )
    frequencies = [row["frequency_hz"] for row in normalized_rows]
    if any(left >= right for left, right in zip(frequencies, frequencies[1:])):
        raise ReferenceComparisonError(
            "Reference frequencies must be strictly increasing and unique"
        )
    return normalized_rows, simulator.strip()


def compare_reference(
    sweep: dict[str, Any],
    reference: dict[str, Any],
    circuit: Circuit,
    max_gain_error_db: float = 0.1,
    max_phase_error_deg: float = 1.0,
    frequency_rtol: float = 1e-9,
) -> dict[str, Any]:
    """Align frequency points within tolerance and quantify gain/phase errors."""
    for label, threshold in (
        ("max_gain_error_db", max_gain_error_db),
        ("max_phase_error_deg", max_phase_error_deg),
        ("frequency_rtol", frequency_rtol),
    ):
        value = _finite_number(threshold, label)
        if value < 0:
            raise ReferenceComparisonError(f"{label} must be nonnegative")
    if sweep.get("schema_version") != "1.0" or sweep.get("analysis") != "AC":
        raise ReferenceComparisonError("Input must be an AC sweep result with schema_version 1.0")
    if sweep.get("status") == "FAIL":
        raise ReferenceComparisonError("Cannot compare a sweep whose overall status is FAIL")
    input_node = sweep.get("input_node")
    output_node = sweep.get("output_node")
    if not isinstance(input_node, str) or not isinstance(output_node, str):
        raise ReferenceComparisonError("Sweep input/output node metadata is missing")
    signature = circuit_signature(circuit)
    if sweep.get("circuit_signature") != signature:
        raise ReferenceComparisonError(
            "Sweep circuit_signature does not match the normalized circuit"
        )
    reference_rows, simulator = _validate_reference(
        reference, circuit, input_node, output_node
    )
    points = sweep.get("points")
    if not isinstance(points, list) or not points:
        raise ReferenceComparisonError("Sweep must contain at least one frequency point")
    normalized_sweep: dict[float, dict[str, Any]] = {}
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            raise ReferenceComparisonError(f"Sweep point {index} must be an object")
        frequency = _finite_number(point.get("frequency_hz"), f"sweep[{index}].frequency_hz")
        if frequency <= 0:
            raise ReferenceComparisonError(f"Sweep frequency at point {index} must be positive")
        if point.get("status") == "FAIL":
            raise ReferenceComparisonError(
                f"Sweep point at {frequency:g} Hz failed; compare only a fully validated sweep"
            )
        if point.get("status") not in {"PASS", "WARN"}:
            raise ReferenceComparisonError(
                f"Sweep point at {frequency:g} Hz has no accepted validation status"
            )
        gain = _finite_number(point.get("gain_db"), f"sweep[{index}].gain_db")
        phase = _finite_number(point.get("phase_deg"), f"sweep[{index}].phase_deg")
        if frequency in normalized_sweep:
            raise ReferenceComparisonError("Sweep contains duplicate frequencies")
        normalized_sweep[frequency] = {
            "frequency_hz": frequency,
            "gain_db": gain,
            "phase_deg": phase,
            "status": point["status"],
        }

    reference_frequencies = [row["frequency_hz"] for row in reference_rows]
    matched_reference: dict[float, dict[str, float]] = {}
    matched_indices: set[int] = set()
    for frequency in sorted(normalized_sweep):
        matches = [
            (index, reference_frequency)
            for index, reference_frequency in enumerate(reference_frequencies)
            if abs(frequency - reference_frequency)
            <= frequency_rtol * max(abs(frequency), abs(reference_frequency))
        ]
        if len(matches) != 1:
            raise ReferenceComparisonError(
                f"Expected exactly one reference frequency aligned to {frequency:g} Hz; "
                "interpolation is not performed."
            )
        reference_index, _ = matches[0]
        if reference_index in matched_indices:
            raise ReferenceComparisonError(
                "Multiple sweep points match the same reference frequency"
            )
        matched_indices.add(reference_index)
        matched_reference[frequency] = reference_rows[reference_index]
    if len(matched_indices) != len(reference_rows):
        unmatched = [
            frequency
            for index, frequency in enumerate(reference_frequencies)
            if index not in matched_indices
        ]
        raise ReferenceComparisonError(
            f"Reference contains unmatched frequencies: {unmatched}. "
            "Interpolation is not performed."
        )

    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for frequency in sorted(normalized_sweep):
        calculated = normalized_sweep[frequency]
        expected = matched_reference[frequency]
        frequency = calculated["frequency_hz"]
        gain_error = calculated["gain_db"] - expected["gain_db"]
        phase_error = _phase_error_deg(
            calculated["phase_deg"], expected["phase_deg"]
        )
        try:
            agent_linear_gain = 10.0 ** (calculated["gain_db"] / 20.0)
            reference_linear_gain = 10.0 ** (expected["gain_db"] / 20.0)
        except OverflowError as exc:
            raise ReferenceComparisonError(
                f"Gain dB magnitude overflows linear conversion at {frequency:g} Hz"
            ) from exc
        relative_gain_error = (
            abs(agent_linear_gain - reference_linear_gain) / reference_linear_gain
            if reference_linear_gain > 0.0
            else None
        )
        passed = (
            abs(gain_error) <= max_gain_error_db
            and abs(phase_error) <= max_phase_error_deg
        )
        if not passed:
            failures.append(
                f"{frequency:g} Hz: gain_error={gain_error:.6g} dB, "
                f"phase_error={phase_error:.6g} deg"
            )
        rows.append(
            {
                "frequency_hz": frequency,
                "agent_gain_db": calculated["gain_db"],
                "reference_gain_db": expected["gain_db"],
                "gain_absolute_error_db": abs(gain_error),
                "gain_signed_error_db": gain_error,
                "gain_relative_error": relative_gain_error,
                "agent_gain_linear": agent_linear_gain,
                "reference_gain_linear": reference_linear_gain,
                "agent_phase_deg": calculated["phase_deg"],
                "reference_phase_deg": expected["phase_deg"],
                "phase_error_deg": phase_error,
                "frequency_error_hz": frequency - expected["frequency_hz"],
                "agent_validation": calculated["status"],
                "passed": passed,
            }
        )
    status = "FAIL" if failures else (
        "WARN" if any(row["agent_validation"] == "WARN" for row in rows) else "PASS"
    )
    return {
        "schema_version": "1.0",
        "source_name": circuit.source_name,
        "analysis": "AC",
        "simulator": simulator,
        "simulator_version": reference.get("simulator_version"),
        "input_node": input_node,
        "output_node": output_node,
        "transfer_definition": sweep.get("transfer_definition"),
        "circuit_signature": signature,
        "status": status,
        "frequency_count": len(rows),
        "passed_points": sum(row["passed"] for row in rows),
        "failed_points": len(failures),
        "thresholds": {
            "max_gain_error_db": max_gain_error_db,
            "max_phase_error_deg": max_phase_error_deg,
            "frequency_rtol": frequency_rtol,
        },
        "errors": failures,
        "rows": rows,
    }


def write_comparison_csv(path: str | Path, comparison: dict[str, Any]) -> None:
    fieldnames = [
        "frequency_hz",
        "agent_gain_db",
        "reference_gain_db",
        "gain_absolute_error_db",
        "gain_signed_error_db",
        "gain_relative_error",
        "agent_gain_linear",
        "reference_gain_linear",
        "agent_phase_deg",
        "reference_phase_deg",
        "phase_error_deg",
        "frequency_error_hz",
        "agent_validation",
        "passed",
    ]
    with Path(path).open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(comparison["rows"])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare validated AC results against aligned reference data"
    )
    parser.add_argument("sweep_json", help="AC sweep results JSON")
    parser.add_argument("reference_json", help="Reference JSON using schema_version 1.0")
    parser.add_argument("circuit_json", help="Circuit JSON used for the sweep")
    parser.add_argument("-o", "--output", required=True, help="Comparison JSON output")
    parser.add_argument("--csv", required=True, help="Comparison CSV output")
    parser.add_argument("--max-gain-error-db", type=float, default=0.1)
    parser.add_argument("--max-phase-error-deg", type=float, default=1.0)
    parser.add_argument("--frequency-rtol", type=float, default=1e-9)
    args = parser.parse_args()

    try:
        sweep = json.loads(Path(args.sweep_json).read_text(encoding="utf-8"))
        reference = json.loads(Path(args.reference_json).read_text(encoding="utf-8"))
        if not isinstance(sweep, dict) or not isinstance(reference, dict):
            raise ReferenceComparisonError("Sweep and reference JSON roots must be objects")
        circuit = load_circuit(args.circuit_json)
        comparison = compare_reference(
            sweep,
            reference,
            circuit,
            args.max_gain_error_db,
            args.max_phase_error_deg,
            args.frequency_rtol,
        )
        Path(args.output).write_text(
            json.dumps(comparison, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        write_comparison_csv(args.csv, comparison)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: cannot compare AC reference: {exc}", file=sys.stderr)
        return 2
    print(
        f"Reference comparison {comparison['status']}: "
        f"{comparison['passed_points']}/{comparison['frequency_count']} points "
        f"-> {args.output}, {args.csv}"
    )
    for error in comparison["errors"]:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1 if comparison["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
