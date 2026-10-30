#!/usr/bin/env python3
"""Generate deterministic Bode plots for AC sweeps and reference comparisons."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


class PlotResultsError(ValueError):
    """Raised when AC plot inputs are malformed or cannot be aligned."""


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PlotResultsError(f"{label} must be a numeric value")
    result = float(value)
    if not math.isfinite(result):
        raise PlotResultsError(f"{label} must be finite")
    return result


def _validated_points(sweep: dict[str, Any]) -> tuple[list[dict[str, Any]], list[float]]:
    if sweep.get("schema_version") != "1.0" or sweep.get("analysis") != "AC":
        raise PlotResultsError("Input must be an AC sweep result with schema_version 1.0")
    points = sweep.get("points")
    if not isinstance(points, list) or not points:
        raise PlotResultsError("Sweep must contain at least one frequency point")
    valid: list[dict[str, Any]] = []
    failed_frequencies: list[float] = []
    seen: set[float] = set()
    previous_frequency = 0.0
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            raise PlotResultsError(f"Sweep point {index} must be an object")
        frequency = _finite_number(point.get("frequency_hz"), f"points[{index}].frequency_hz")
        if frequency <= 0 or frequency <= previous_frequency:
            raise PlotResultsError(
                "Sweep frequencies must be positive, strictly increasing, and unique"
            )
        previous_frequency = frequency
        if point.get("status") == "FAIL":
            failed_frequencies.append(frequency)
            continue
        if point.get("status") not in {"PASS", "WARN"}:
            raise PlotResultsError(
                f"Sweep point at {frequency:g} Hz has no accepted validation status"
            )
        gain_db = _finite_number(point.get("gain_db"), f"points[{index}].gain_db")
        phase_deg = _finite_number(point.get("phase_deg"), f"points[{index}].phase_deg")
        if frequency in seen:
            raise PlotResultsError("Sweep contains duplicate frequencies")
        seen.add(frequency)
        valid.append(
            {
                "frequency_hz": frequency,
                "gain_db": gain_db,
                "phase_deg": phase_deg,
                "status": point["status"],
            }
        )
    if not valid:
        raise PlotResultsError("No validated AC points are available to plot")
    return valid, failed_frequencies


def _reference_series(
    comparison: dict[str, Any],
    valid_points: list[dict[str, Any]],
    sweep: dict[str, Any],
) -> dict[float, dict[str, float]]:
    if comparison.get("schema_version") != "1.0" or comparison.get("analysis") != "AC":
        raise PlotResultsError("Comparison input must use AC comparison schema_version 1.0")
    for key in ("source_name", "input_node", "output_node", "transfer_definition"):
        if comparison.get(key) != sweep.get(key):
            raise PlotResultsError(f"Comparison and sweep metadata mismatch: {key}")
    if comparison.get("status") == "FAIL":
        raise PlotResultsError("Cannot plot a failed reference comparison")
    rows = comparison.get("rows")
    if not isinstance(rows, list) or not rows:
        raise PlotResultsError("Comparison must contain reference rows")
    expected = {point["frequency_hz"] for point in valid_points}
    series: dict[float, dict[str, float]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise PlotResultsError(f"Comparison row {index} must be an object")
        frequency = _finite_number(
            row.get("frequency_hz"), f"comparison.rows[{index}].frequency_hz"
        )
        if frequency in series:
            raise PlotResultsError("Comparison contains duplicate frequencies")
        gain = _finite_number(
            row.get("reference_gain_db"),
            f"comparison.rows[{index}].reference_gain_db",
        )
        phase = _finite_number(
            row.get("reference_phase_deg"),
            f"comparison.rows[{index}].reference_phase_deg",
        )
        series[frequency] = {"gain_db": gain, "phase_deg": phase}
    if set(series) != expected:
        raise PlotResultsError(
            "Comparison frequencies must match the validated sweep points exactly"
        )
    return series


def plot_results(
    sweep: dict[str, Any],
    output_prefix: str | Path,
    comparison: dict[str, Any] | None = None,
    image_format: str = "png",
) -> dict[str, Any]:
    """Write gain/phase figures and a manifest of plotted and omitted points."""
    normalized_format = image_format.lower()
    if normalized_format not in {"png", "svg"}:
        raise PlotResultsError("image_format must be 'png' or 'svg'")
    valid_points, failed_frequencies = _validated_points(sweep)
    reference = (
        _reference_series(comparison, valid_points, sweep)
        if comparison is not None
        else None
    )
    output = Path(output_prefix)
    output.parent.mkdir(parents=True, exist_ok=True)
    gain_path = output.with_name(f"{output.name}_gain.{normalized_format}")
    phase_path = output.with_name(f"{output.name}_phase.{normalized_format}")
    frequencies = [point["frequency_hz"] for point in valid_points]
    gains = [point["gain_db"] for point in valid_points]
    phases = [point["phase_deg"] for point in valid_points]
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.grid": True,
            "grid.alpha": 0.3,
            "figure.dpi": 120,
            "savefig.dpi": 160,
        }
    )

    fig, axis = plt.subplots(figsize=(8, 5))
    axis.semilogx(frequencies, gains, marker="o", markersize=3, label="Agente")
    if reference is not None:
        axis.semilogx(
            frequencies,
            [reference[frequency]["gain_db"] for frequency in frequencies],
            marker="x",
            markersize=4,
            linestyle="--",
            label=str(comparison["simulator"]),
        )
    axis.set_xlabel("Frecuencia (Hz)")
    axis.set_ylabel("Ganancia (dB)")
    axis.set_title(
        f"Respuesta en ganancia: {sweep['transfer_definition']}"
        + (
            f" — puntos fallidos omitidos: {len(failed_frequencies)}"
            if failed_frequencies
            else ""
        )
    )
    axis.legend()
    fig.tight_layout()
    fig.savefig(gain_path, format=normalized_format)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(8, 5))
    axis.semilogx(frequencies, phases, marker="o", markersize=3, label="Agente")
    if reference is not None:
        axis.semilogx(
            frequencies,
            [reference[frequency]["phase_deg"] for frequency in frequencies],
            marker="x",
            markersize=4,
            linestyle="--",
            label=str(comparison["simulator"]),
        )
    axis.set_xlabel("Frecuencia (Hz)")
    axis.set_ylabel("Fase (grados)")
    axis.set_title(
        f"Respuesta en fase: {sweep['transfer_definition']}"
        + (
            f" — puntos fallidos omitidos: {len(failed_frequencies)}"
            if failed_frequencies
            else ""
        )
    )
    axis.legend()
    fig.tight_layout()
    fig.savefig(phase_path, format=normalized_format)
    plt.close(fig)

    manifest = {
        "schema_version": "1.0",
        "source_name": sweep.get("source_name"),
        "analysis": "AC",
        "status": "WARN" if failed_frequencies else "PASS",
        "gain_plot": str(gain_path),
        "phase_plot": str(phase_path),
        "image_format": normalized_format,
        "input_node": sweep.get("input_node"),
        "output_node": sweep.get("output_node"),
        "transfer_definition": sweep.get("transfer_definition"),
        "plotted_frequency_count": len(valid_points),
        "plotted_frequencies_hz": frequencies,
        "omitted_failed_frequencies_hz": failed_frequencies,
        "reference_overlay": comparison.get("simulator") if comparison else None,
    }
    manifest_path = output.with_name(f"{output.name}_plot_manifest.json")
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Plot AC sweep gain/phase and optional reference overlays"
    )
    parser.add_argument("sweep_json", help="AC sweep result JSON")
    parser.add_argument("-o", "--output-prefix", required=True, help="Output file prefix")
    parser.add_argument(
        "--comparison",
        help="Optional comparison JSON from compare_reference.py",
    )
    parser.add_argument("--format", choices=("png", "svg"), default="png")
    args = parser.parse_args()

    try:
        sweep = json.loads(Path(args.sweep_json).read_text(encoding="utf-8"))
        comparison = (
            json.loads(Path(args.comparison).read_text(encoding="utf-8"))
            if args.comparison
            else None
        )
        if not isinstance(sweep, dict):
            raise PlotResultsError("Sweep JSON root must be an object")
        if comparison is not None and not isinstance(comparison, dict):
            raise PlotResultsError("Comparison JSON root must be an object")
        manifest = plot_results(sweep, args.output_prefix, comparison, args.format)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: cannot plot AC results: {exc}", file=sys.stderr)
        return 2
    print(
        f"Plots {manifest['status']}: {manifest['plotted_frequency_count']} points -> "
        f"{manifest['gain_plot']}, {manifest['phase_plot']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
