#!/usr/bin/env python3
"""Create deterministic scalar Tableau stamps for supported branch elements."""
from __future__ import annotations

import argparse
import cmath
import json
import math
import sys
from pathlib import Path
from typing import Any

from build_circuit_model import load_circuit


class ElementStampError(ValueError):
    """Raised when an element cannot be stamped for the requested analysis."""


def _complex_record(value: complex) -> dict[str, float]:
    return {"real": float(value.real), "imag": float(value.imag)}


def _source_value(branch: Any, analysis: str) -> complex:
    if not isinstance(branch.source_kind, str) or branch.source_kind not in {"DC", "AC"}:
        raise ElementStampError(
            f"{branch.component_name}: source_kind must be 'DC' or 'AC'"
        )
    if not math.isfinite(branch.value_si):
        raise ElementStampError(f"{branch.component_name}: source value must be finite")
    if branch.source_kind != analysis:
        return 0.0 + 0.0j
    if analysis == "DC":
        return complex(branch.value_si)
    magnitude = branch.ac_magnitude
    phase_deg = branch.ac_phase_deg
    if magnitude is None or not math.isfinite(float(magnitude)) or float(magnitude) < 0:
        raise ElementStampError(
            f"{branch.component_name}: AC source magnitude must be finite and nonnegative"
        )
    if phase_deg is None:
        phase_deg = 0.0
    if not math.isfinite(float(phase_deg)):
        raise ElementStampError(f"{branch.component_name}: AC source phase must be finite")
    return cmath.rect(float(magnitude), math.radians(float(phase_deg)))


def _stamp(
    branch: Any,
    analysis: str,
    omega_rad_s: float,
) -> tuple[complex, complex, complex, str, str, str, str]:
    element_type = branch.element_type
    if element_type == "R":
        if not math.isfinite(branch.value_si) or branch.value_si <= 0:
            raise ElementStampError(
                f"{branch.component_name}: resistance must be finite and positive"
            )
        return 1.0, -branch.value_si, 0.0, "dimensionless", "ohm", "volt", "V - R*I = 0"
    if element_type == "C":
        if not math.isfinite(branch.value_si) or branch.value_si <= 0:
            raise ElementStampError(
                f"{branch.component_name}: capacitance must be finite and positive"
            )
        if analysis == "DC":
            return (
                0.0,
                1.0,
                0.0,
                "siemens",
                "dimensionless",
                "ampere",
                "I = 0 (capacitor abierto en DC)",
            )
        return (
            1j * omega_rad_s * branch.value_si,
            -1.0,
            0.0,
            "siemens",
            "dimensionless",
            "ampere",
            "j*omega*C*V - I = 0",
        )
    if element_type == "L":
        if not math.isfinite(branch.value_si) or branch.value_si <= 0:
            raise ElementStampError(
                f"{branch.component_name}: inductance must be finite and positive"
            )
        if analysis == "DC":
            return (
                1.0,
                0.0,
                0.0,
                "dimensionless",
                "ohm",
                "volt",
                "V = 0 (inductor en cortocircuito ideal en DC)",
            )
        return (
            1.0,
            -1j * omega_rad_s * branch.value_si,
            0.0,
            "dimensionless",
            "ohm",
            "volt",
            "V - j*omega*L*I = 0",
        )
    if element_type == "V":
        return 1.0, 0.0, _source_value(branch, analysis), "dimensionless", "ohm", "volt", "V = E"
    if element_type == "I":
        return (
            0.0,
            1.0,
            _source_value(branch, analysis),
            "siemens",
            "dimensionless",
            "ampere",
            "I = J",
        )
    raise ElementStampError(
        f"{branch.component_name}: unsupported element type {element_type!r}; "
        "supported types are R, C, L, V, I"
    )


def build_element_stamps(
    circuit: Any,
    analysis: str,
    frequency_hz: float | None = None,
) -> dict[str, Any]:
    """Return one traceable equation stamp per circuit branch.

    Stamps use Y*V_branch + Z*I_branch = W. AC sources with DC-only
    definitions, and DC sources in AC analysis, are represented by zero.
    """
    normalized_analysis = analysis.upper()
    if normalized_analysis not in {"DC", "AC"}:
        raise ElementStampError("analysis must be either 'DC' or 'AC'")
    if normalized_analysis == "AC":
        if frequency_hz is None or not math.isfinite(frequency_hz) or frequency_hz < 0:
            raise ElementStampError("AC analysis requires a finite, nonnegative frequency in Hz")
        omega = 2.0 * math.pi * frequency_hz
    else:
        if frequency_hz is not None:
            raise ElementStampError("frequency_hz is only valid for AC analysis")
        omega = 0.0

    stamps = []
    for branch in circuit.branches:
        y, z, w, y_unit, z_unit, w_unit, equation = _stamp(
            branch, normalized_analysis, omega
        )
        stamps.append(
            {
                "branch_id": branch.id,
                "component_name": branch.component_name,
                "element_type": branch.element_type,
                "source_kind": branch.source_kind,
                "node_from": branch.node_from,
                "node_to": branch.node_to,
                "source_line": branch.source_line,
                "line_number": branch.line_number,
                "equation": equation,
                "Y": _complex_record(y),
                "Z": _complex_record(z),
                "W": _complex_record(w),
                "Y_unit": y_unit,
                "Z_unit": z_unit,
                "W_unit": w_unit,
            }
        )
    return {
        "schema_version": "1.0",
        "source_name": circuit.source_name,
        "analysis": normalized_analysis,
        "frequency_hz": frequency_hz,
        "omega_rad_s": omega,
        "equation_convention": "Y*V_branch + Z*I_branch = W",
        "branch_order": [branch.id for branch in circuit.branches],
        "stamps": stamps,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create traceable Tableau stamps for circuit branches"
    )
    parser.add_argument("circuit_json", help="Circuit JSON generated by build_circuit_model.py")
    parser.add_argument("-o", "--output", required=True, help="Element stamps JSON")
    parser.add_argument("--analysis", choices=("DC", "AC"), required=True)
    parser.add_argument("--frequency", type=float, help="AC frequency in Hz")
    args = parser.parse_args()

    try:
        circuit = load_circuit(args.circuit_json)
        data = build_element_stamps(circuit, args.analysis, args.frequency)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: cannot build element stamps: {exc}", file=sys.stderr)
        return 1
    try:
        Path(args.output).write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        print(f"ERROR: cannot write element stamps {args.output!r}: {exc}", file=sys.stderr)
        return 2

    print(f"Built {len(data['stamps'])} {data['analysis']} element stamps -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
