#!/usr/bin/env python3
"""Generate an auditable Markdown report from validated SPICE artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


class ReportGenerationError(ValueError):
    """Raised when supplied artifacts are incomplete or inconsistent."""


_UNSET = object()


def _read_json(path: str | Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReportGenerationError(f"Cannot read JSON artifact {str(path)!r}: {exc}") from exc
    if not isinstance(data, dict):
        raise ReportGenerationError(f"JSON artifact {str(path)!r} must contain an object")
    return data


def _md(value: Any) -> str:
    return str(value).replace("|", r"\|").replace("\r\n", "<br>").replace("\n", "<br>")


def _code_fence(content: str) -> str:
    longest = max((len(run) for run in re.findall(r"`+", content)), default=0)
    return "`" * max(3, longest + 1)


def _fmt_number(value: Any) -> str:
    if value is None:
        return "no definido"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return _md(value)
    if not math.isfinite(float(value)):
        raise ReportGenerationError("Non-finite values cannot be written to a report")
    return f"{float(value):.8g}"


def _fmt_complex(value: Any) -> str:
    if isinstance(value, dict) and "real" in value and "imag" in value:
        real = _fmt_number(value["real"])
        imag = _fmt_number(value["imag"])
        sign = "+" if float(value["imag"]) >= 0 else "−"
        return f"{real} {sign} j{_fmt_number(abs(float(value['imag'])))}"
    return _fmt_number(value)


def _source_name(data: dict[str, Any], label: str, expected: str) -> None:
    if data.get("schema_version") != "1.0":
        raise ReportGenerationError(f"{label} must use schema_version 1.0")
    if data.get("source_name") != expected:
        raise ReportGenerationError(
            f"{label} source_name does not match the circuit: "
            f"{data.get('source_name')!r} != {expected!r}"
        )


def _check_system_metadata(
    artifact: dict[str, Any],
    label: str,
    source_name: str,
    analysis: str | None = None,
    frequency_hz: Any = _UNSET,
) -> None:
    _source_name(artifact, label, source_name)
    if analysis is not None and artifact.get("analysis") != analysis:
        raise ReportGenerationError(f"{label} analysis does not match its associated result")
    if frequency_hz is not _UNSET and artifact.get("frequency_hz") != frequency_hz:
        raise ReportGenerationError(f"{label} frequency does not match its associated result")


def _matrix_table(
    title: str,
    matrix: Any,
    row_labels: list[Any],
    column_labels: list[Any],
) -> list[str]:
    if not isinstance(matrix, list) or len(matrix) != len(row_labels):
        raise ReportGenerationError(f"{title} matrix row count does not match its labels")
    if any(not isinstance(row, list) or len(row) != len(column_labels) for row in matrix):
        raise ReportGenerationError(f"{title} matrix column count does not match its labels")
    lines = [f"#### {title} ({len(row_labels)} × {len(column_labels)})", ""]
    lines.append("| Ecuación / variable | " + " | ".join(_md(x) for x in column_labels) + " |")
    lines.append("|---|" + "---|" * len(column_labels))
    for label, row in zip(row_labels, matrix):
        lines.append(
            "| "
            + _md(label)
            + " | "
            + " | ".join(_fmt_complex(value) for value in row)
            + " |"
        )
    lines.append("")
    return lines


def _format_vector(values: Any, labels: list[Any], title: str) -> list[str]:
    if not isinstance(values, list) or len(values) != len(labels):
        raise ReportGenerationError(f"{title} vector length does not match its labels")
    lines = [f"#### {title}", "", "| Variable | Valor |", "|---|---|"]
    lines.extend(
        f"| {_md(label)} | {_fmt_complex(value)} |"
        for label, value in zip(labels, values)
    )
    lines.append("")
    return lines


def _render_results(
    lines: list[str],
    solution: dict[str, Any] | None,
    validation: dict[str, Any] | None,
    sweep: dict[str, Any] | None,
) -> list[str]:
    lines.extend(["## 11. Resultados", ""])
    if solution is not None:
        lines.extend(
            [
                f"Solución de punto único: **{_md(solution.get('status', 'desconocido'))}**; "
                f"análisis `{_md(solution.get('analysis', 'no especificado'))}`; "
                f"frecuencia `{_fmt_number(solution.get('frequency_hz'))}` Hz.",
                "",
            ]
        )
        for key, title in (
            ("node_voltages", "Tensiones nodales"),
            ("branch_voltages", "Tensiones de rama"),
            ("branch_currents", "Corrientes de rama"),
        ):
            values = solution.get(key)
            if isinstance(values, list):
                lines.extend(
                    [
                        f"### {title}",
                        "",
                        "| Variable | Real | Imaginaria | Magnitud | Fase (°) | Unidad |",
                        "|---|---:|---:|---:|---:|---|",
                    ]
                )
                for item in values:
                    lines.append(
                        f"| {_md(item.get('label'))} | {_fmt_number(item.get('real'))} | "
                        f"{_fmt_number(item.get('imag'))} | {_fmt_number(item.get('magnitude'))} | "
                        f"{_fmt_number(item.get('phase_deg'))} | "
                        f"{_md(item.get('unit', ''))} |"
                    )
                lines.append("")
    if sweep is not None:
        lines.extend(
            [
                f"Barrido AC: **{_md(sweep.get('status'))}**, "
                f"{_md(sweep.get('frequency_count'))} puntos, "
                f"{_md(sweep.get('failed_points'))} fallidos, "
                f"{_md(sweep.get('warning_points'))} con advertencia.",
                "",
                f"Función de transferencia: `{_md(sweep.get('transfer_definition'))}`.",
                "",
                "La herramienta de barrido no exporta corrientes de rama; "
                "este reporte no las infiere.",
                "",
                "| Frecuencia (Hz) | Vin (V, fasor) | Vout (V, fasor) | H(jω) | |H| | "
                "Ganancia (dB) | Fase (°) | Estado |",
                "|---:|---:|---:|---:|---:|---:|---:|---|",
            ]
        )
        for point in sweep.get("points", []):
            vin = point.get("input_voltage", {})
            vout = point.get("output_voltage", {})
            transfer = point.get("transfer_function", {})
            vin_text = (
                f"{_fmt_number(vin.get('real'))} + j{_fmt_number(vin.get('imag'))}"
                if vin
                else "no disponible"
            )
            vout_text = (
                f"{_fmt_number(vout.get('real'))} + j{_fmt_number(vout.get('imag'))}"
                if vout
                else "no disponible"
            )
            transfer_text = (
                f"{_fmt_number(transfer.get('real'))} + j{_fmt_number(transfer.get('imag'))}"
                if transfer
                else _md(point.get("error", "no disponible"))
            )
            lines.append(
                f"| {_fmt_number(point.get('frequency_hz'))} | {vin_text} | {vout_text} | "
                f"{transfer_text} | {_fmt_number(transfer.get('magnitude'))} | "
                f"{_fmt_number(point.get('gain_db'))} | "
                f"{_fmt_number(point.get('phase_deg'))} | {_md(point.get('status'))} |"
            )
        lines.append("")
    lines.extend(["## 12. Validaciones", ""])
    if validation is not None:
        lines.extend(
            [
                f"Validación independiente: **{_md(validation.get('status', 'desconocido'))}**.",
                "",
                f"- Rango: `{_md(validation.get('rank', 'no informado'))}` / "
                f"`{_md(validation.get('size', 'no informado'))}`.",
                f"- Número de condición: `{_fmt_number(validation.get('condition_number'))}`.",
                f"- Tolerancias: `atol={_fmt_number(validation.get('atol'))}`, "
                f"`rtol={_fmt_number(validation.get('rtol'))}`.",
                f"- Residuo normalizado: `{_fmt_number(validation.get('normalized_residual'))}`.",
                "",
            ]
        )
        for name, result in validation.get("residuals", {}).items():
            lines.append(
                f"- Residuo {_md(name)}: norma `{_fmt_number(result.get('norm'))}`, "
                f"tolerancia `{_fmt_number(result.get('tolerance'))}`, "
                f"pasa: `{_md(result.get('passed'))}`."
            )
        for item in validation.get("errors", []):
            lines.append(f"- **Error de validación:** {_md(item)}")
        for item in validation.get("warnings", []):
            lines.append(f"- **Advertencia numérica:** {_md(item)}")
    elif solution is not None and solution.get("status") in {"PASS", "WARN"}:
        lines.append(
            "El artefacto de solución nodal reporta validación interna "
            f"**{_md(solution.get('status'))}**; no se proporcionó validación independiente."
        )
    elif sweep is not None:
        lines.extend(
            [
                "Cada punto del barrido incluye su propio estado y artefacto de validación.",
                "",
                f"Tolerancias del barrido: `atol={_fmt_number(sweep.get('atol'))}`, "
                f"`rtol={_fmt_number(sweep.get('rtol'))}`; umbral de condición: "
                f"`{_fmt_number(sweep.get('condition_warning_threshold'))}`.",
                "",
                "| Frecuencia (Hz) | Estado | Residuo normalizado | Número de condición |",
                "|---:|---|---:|---:|",
            ]
        )
        for point in sweep.get("points", []):
            point_validation = point.get("validation", {})
            lines.append(
                f"| {_fmt_number(point.get('frequency_hz'))} | "
                f"{_md(point.get('status', 'FAIL'))} | "
                f"{_fmt_number(point_validation.get('normalized_residual'))} | "
                f"{_fmt_number(point_validation.get('condition_number'))} |"
            )
    else:
        lines.append("No se proporcionó un artefacto de validación.")
    lines.append("")
    if solution is None and sweep is None:
        lines.extend(["No se proporcionó un resultado calculado.", ""])
    return lines


def generate_report(
    parsed: dict[str, Any],
    circuit: dict[str, Any],
    incidence: dict[str, Any],
    netlist_text: str,
    *,
    graph: dict[str, Any] | None = None,
    stamps: dict[str, Any] | None = None,
    constitutive: dict[str, Any] | None = None,
    system: dict[str, Any] | None = None,
    solution: dict[str, Any] | None = None,
    validation: dict[str, Any] | None = None,
    sweep: dict[str, Any] | None = None,
    comparison: dict[str, Any] | None = None,
    plot_manifest: dict[str, Any] | None = None,
    input_hashes: dict[str, str] | None = None,
    limitations: list[str] | None = None,
    invocation: str | None = None,
) -> str:
    """Render a report using supplied artifacts only; this function never solves."""
    source_name = circuit.get("source_name")
    if not isinstance(source_name, str) or not source_name:
        raise ReportGenerationError("Circuit source_name is required")
    for label, data in (("parsed netlist", parsed), ("incidence matrix", incidence)):
        _source_name(data, label, source_name)
    if circuit.get("schema_version") != "1.0":
        raise ReportGenerationError("Circuit model must use schema_version 1.0")
    elements = parsed.get("elements")
    branches = circuit.get("branches")
    nodes = circuit.get("nodes")
    if not all(
        isinstance(value, list)
        for value in (elements, branches, nodes)
    ):
        raise ReportGenerationError("Parsed elements, circuit branches, and nodes must be lists")
    if parsed.get("source_name") != source_name:
        raise ReportGenerationError("Parsed source_name does not match the circuit model")
    if len(elements) != len(branches):
        raise ReportGenerationError(
            "Parsed element count does not match the circuit branch count"
        )
    source_lines = netlist_text.splitlines()
    for element, branch in zip(elements, branches):
        for source_key, model_key in (
            ("name", "component_name"),
            ("type", "element_type"),
            ("node_from", "node_from"),
            ("node_to", "node_to"),
            ("value_si", "value_si"),
            ("unit", "unit"),
            ("source_kind", "source_kind"),
            ("ac_magnitude", "ac_magnitude"),
            ("ac_phase_deg", "ac_phase_deg"),
            ("source_line", "source_line"),
            ("line_number", "line_number"),
        ):
            if element.get(source_key) != branch.get(model_key):
                raise ReportGenerationError(
                    f"Parsed element {element.get('name')!r} does not match the circuit model"
                )
        line_number = element.get("line_number")
        if (
            isinstance(line_number, bool)
            or not isinstance(line_number, int)
            or not 1 <= line_number <= len(source_lines)
        ):
            raise ReportGenerationError(
                f"Parsed element {element.get('name')!r} has an invalid source line number"
            )
        if source_lines[line_number - 1] != element.get("source_line"):
            raise ReportGenerationError(
                f"Original netlist line {line_number} does not match parsed source data"
            )
    node_order = [node.get("id") for node in nodes]
    branch_order = [branch.get("id") for branch in branches]
    if incidence.get("node_order_full") != node_order:
        raise ReportGenerationError("Incidence node order does not match the circuit model")
    if incidence.get("branch_order") != branch_order:
        raise ReportGenerationError("Incidence branch order does not match the circuit model")
    if incidence.get("reference_node") != circuit.get("reference_node"):
        raise ReportGenerationError("Incidence reference node does not match the circuit model")

    if graph is not None:
        _source_name(graph, "oriented graph", source_name)
        if [item.get("id") for item in graph.get("nodes", [])] != node_order:
            raise ReportGenerationError("Graph nodes do not match the circuit model")
        if len(graph.get("edges", [])) != len(branches):
            raise ReportGenerationError("Graph edges do not match the circuit branches")
        if {edge.get("key") for edge in graph.get("edges", [])} != set(branch_order):
            raise ReportGenerationError("Graph branch IDs do not match the circuit model")

    if system is not None:
        _check_system_metadata(system, "analysis system", source_name)
        if system.get("branch_order") is not None and system["branch_order"] != branch_order:
            raise ReportGenerationError("Analysis system branch order does not match the circuit")
        system_nodes = system.get("node_order")
        if system_nodes is None:
            system_nodes = system.get("unknown_order", {}).get("node_voltage")
        if system_nodes is not None and system_nodes != incidence.get("node_order_reduced"):
            raise ReportGenerationError("Analysis system node order does not match incidence data")
    context = system or constitutive or stamps
    for label, artifact in (("stamps", stamps), ("constitutive matrices", constitutive)):
        if artifact is not None:
            _check_system_metadata(
                artifact,
                label,
                source_name,
                context.get("analysis") if context else None,
                context.get("frequency_hz", None) if context else _UNSET,
            )
            if label == "stamps" and artifact.get("branch_order") != branch_order:
                raise ReportGenerationError("Stamp branch order does not match the circuit")
            if label == "constitutive matrices" and artifact.get("row_order") != branch_order:
                raise ReportGenerationError("Constitutive row order does not match the circuit")
    if solution is not None:
        if system is None:
            raise ReportGenerationError(
                "A point solution requires its nodal or Tableau system artifact"
            )
        _check_system_metadata(
            solution,
            "solution",
            source_name,
            system.get("analysis"),
            system.get("frequency_hz"),
        )
        if system.get("equation") == "T @ X = W_prime" and validation is None:
            raise ReportGenerationError(
                "A Tableau solution requires its independent validation artifact"
            )
    if validation is not None:
        if system is None or solution is None:
            raise ReportGenerationError(
                "Validation requires both its system and solution artifacts"
            )
        _check_system_metadata(
            validation,
            "solution validation",
            source_name,
            system.get("analysis"),
            system.get("frequency_hz"),
        )
        if validation.get("status") not in {"PASS", "WARN", "FAIL"}:
            raise ReportGenerationError("Solution validation has an unsupported status")

    if sweep is not None:
        _source_name(sweep, "AC sweep", source_name)
        from circuit_identity import circuit_signature
        from build_circuit_model import load_circuit
        import tempfile

        # The signature is checked against the normalized model through the same
        # canonical helper used by the sweep and comparison tools.
        with tempfile.TemporaryDirectory() as temporary_directory:
            circuit_path = Path(temporary_directory) / "circuit.json"
            circuit_path.write_text(json.dumps(circuit), encoding="utf-8")
            model = load_circuit(circuit_path)
        expected_signature = circuit_signature(model)
        if sweep.get("circuit_signature") != expected_signature:
            raise ReportGenerationError("AC sweep fingerprint does not match the circuit model")
        if sweep.get("status") not in {"PASS", "WARN", "FAIL"}:
            raise ReportGenerationError("AC sweep has an unsupported status")
        node_ids = set(node_order)
        if (
            sweep.get("input_node") not in node_ids
            or sweep.get("output_node") not in node_ids
            or sweep.get("reference_node") != circuit.get("reference_node")
        ):
            raise ReportGenerationError("AC sweep node metadata does not match the circuit")
        points = sweep.get("points")
        if not isinstance(points, list) or not points:
            raise ReportGenerationError("AC sweep must contain at least one result point")
        if any(not isinstance(point, dict) for point in points):
            raise ReportGenerationError("Every AC sweep point must be an object")
        if sweep.get("frequency_count") != len(points):
            raise ReportGenerationError("AC sweep frequency_count does not match its points")
        failed_points = sum(point.get("status") == "FAIL" for point in points)
        warning_points = sum(point.get("status") == "WARN" for point in points)
        if sweep.get("failed_points") != failed_points:
            raise ReportGenerationError("AC sweep failed_points does not match its point states")
        if sweep.get("warning_points") != warning_points:
            raise ReportGenerationError(
                "AC sweep warning_points does not match its point states"
            )
        expected_status = (
            "FAIL"
            if failed_points
            else "WARN"
            if warning_points
            else "PASS"
        )
        if sweep.get("status") != expected_status:
            raise ReportGenerationError("AC sweep overall status does not match its points")
        frequencies: list[float] = []
        for index, point in enumerate(points):
            if not isinstance(point, dict):
                raise ReportGenerationError(f"AC sweep point {index} must be an object")
            frequency = point.get("frequency_hz")
            if (
                isinstance(frequency, bool)
                or not isinstance(frequency, (int, float))
                or not math.isfinite(frequency)
                or frequency <= 0
            ):
                raise ReportGenerationError(
                    f"AC sweep point {index} frequency must be finite and positive"
                )
            frequencies.append(float(frequency))
            if point.get("status") not in {"PASS", "WARN", "FAIL"}:
                raise ReportGenerationError(f"AC sweep point {index} has an invalid status")
            point_validation = point.get("validation")
            if point.get("status") in {"PASS", "WARN"}:
                if not isinstance(point_validation, dict):
                    raise ReportGenerationError(
                        f"Accepted AC point {index} is missing its validation artifact"
                    )
                if point_validation.get("status") != point.get("status"):
                    raise ReportGenerationError(
                        f"AC point {index} status does not match its validation"
                    )
                for observable in (
                    "input_voltage",
                    "output_voltage",
                    "transfer_function",
                ):
                    if not isinstance(point.get(observable), dict):
                        raise ReportGenerationError(
                            f"Accepted AC point {index} is missing {observable}"
                        )
        if any(left >= right for left, right in zip(frequencies, frequencies[1:])):
            raise ReportGenerationError("AC sweep frequencies must be strictly increasing")

    if comparison is not None:
        if sweep is None:
            raise ReportGenerationError("Reference comparison requires its associated AC sweep")
        _source_name(comparison, "reference comparison", source_name)
        for key in ("circuit_signature", "input_node", "output_node", "transfer_definition"):
            if comparison.get(key) != sweep.get(key):
                raise ReportGenerationError(f"Comparison and sweep metadata mismatch: {key}")
        if comparison.get("analysis") != "AC":
            raise ReportGenerationError("Reference comparison must declare AC analysis")
        if comparison.get("status") not in {"PASS", "WARN", "FAIL"}:
            raise ReportGenerationError("Reference comparison has an unsupported status")
        comparison_rows = comparison.get("rows")
        if not isinstance(comparison_rows, list):
            raise ReportGenerationError("Reference comparison rows must be a list")
        if any(not isinstance(row, dict) for row in comparison_rows):
            raise ReportGenerationError("Every reference comparison row must be an object")
        if [row.get("frequency_hz") for row in comparison_rows] != [
            point.get("frequency_hz") for point in sweep["points"]
        ]:
            raise ReportGenerationError(
                "Reference comparison points do not align with the associated sweep"
            )
        thresholds = comparison.get("thresholds")
        if not isinstance(thresholds, dict):
            raise ReportGenerationError("Reference comparison thresholds must be an object")
        passed_points = sum(row.get("passed") is True for row in comparison_rows)
        failed_points = len(comparison_rows) - passed_points
        if (
            comparison.get("passed_points") != passed_points
            or comparison.get("failed_points") != failed_points
        ):
            raise ReportGenerationError("Reference comparison counters do not match its rows")
        expected_comparison_status = (
            "FAIL"
            if failed_points
            else "WARN"
            if any(row.get("agent_validation") == "WARN" for row in comparison_rows)
            else "PASS"
        )
        if comparison.get("status") != expected_comparison_status:
            raise ReportGenerationError(
                "Reference comparison status does not match its point results"
            )
    if plot_manifest is not None:
        if sweep is None:
            raise ReportGenerationError("Plot manifest requires its associated AC sweep")
        _source_name(plot_manifest, "plot manifest", source_name)
        for key in ("analysis", "input_node", "output_node", "transfer_definition"):
            if plot_manifest.get(key) != sweep.get(key):
                raise ReportGenerationError(f"Plot manifest and sweep metadata mismatch: {key}")

    result_states: list[str] = []
    if solution is not None:
        if validation is not None:
            result_states.append(validation["status"])
        elif solution.get("status") in {"PASS", "WARN", "FAIL"}:
            result_states.append(solution["status"])
        else:
            result_states.append("NOT_VALIDATED")
    if sweep is not None:
        result_states.append(sweep["status"])
    if comparison is not None:
        result_states.append(comparison["status"])
    report_status = (
        "NOT_VALIDATED"
        if not result_states or "NOT_VALIDATED" in result_states
        else "FAIL"
        if "FAIL" in result_states
        else "WARN"
        if "WARN" in result_states
        else "PASS"
    )

    fence = _code_fence(netlist_text)
    selected_method = (
        system.get("equation", "no especificado")
        if system is not None
        else "Tableau AC por punto"
        if sweep is not None
        else "no especificado"
    )
    selected_analysis = (
        system.get("analysis")
        if system is not None
        else sweep.get("analysis")
        if sweep is not None
        else "no especificado"
    )
    lines = [
        f"# Reporte explicable de análisis SPICE: {_md(source_name)}",
        "",
        f"**Estado del reporte: {report_status}.**",
        "",
        "## 1. Objetivo y método seleccionado",
        "",
        "Reporte reproducible generado exclusivamente a partir de los artefactos "
        "proporcionados; no recalcula el circuito.",
        "",
        f"- Circuito: `{_md(source_name)}`.",
        f"- Método: `{_md(selected_method)}`.",
        f"- Análisis: `{_md(selected_analysis)}`.",
        "",
        "## 2. Netlist original",
        "",
        f"{fence}spice",
        netlist_text.rstrip("\r\n"),
        fence,
        "",
        "## 3. Componentes normalizados",
        "",
        "| Componente | Tipo | Valor SI | Unidad | Fuente | Magnitud AC | "
        "Fase AC (°) | Línea original |",
        "|---|---|---:|---|---:|---:|---|---|",
    ]
    for element in elements:
        lines.append(
            f"| {_md(element.get('name'))} | {_md(element.get('type'))} | "
            f"{_fmt_number(element.get('value_si'))} | {_md(element.get('unit'))} | "
            f"{_md(element.get('source_kind') or '')} | "
            f"{_fmt_number(element.get('ac_magnitude'))} | "
            f"{_fmt_number(element.get('ac_phase_deg'))} | "
            f"{_md(element.get('source_line', ''))} |"
        )
    lines.extend(
        [
            "",
            "## 4. Nodos y referencia",
            "",
            "| Nodo | Índice completo | Índice reducido | Referencia |",
            "|---|---:|---:|---|",
        ]
    )
    for node in nodes:
        lines.append(
            f"| N{_md(node.get('id'))} | {_md(node.get('index_full'))} | "
            f"{_md(node.get('index_reduced'))} | "
            f"{'Sí' if node.get('is_reference') else 'No'} |"
        )
    lines.extend(["", f"Nodo de referencia: **N{_md(circuit.get('reference_node'))}**.", ""])
    lines.extend(
        [
            "## 5. Ramas y orientación",
            "",
            "| Rama | Componente | Orientación | Tipo | Valor SI | Unidad |",
            "|---|---|---|---|---:|---|",
        ]
    )
    for branch in branches:
        lines.append(
            f"| {_md(branch.get('id'))} | {_md(branch.get('component_name'))} | "
            f"N{_md(branch.get('node_from'))} → N{_md(branch.get('node_to'))} | "
            f"{_md(branch.get('element_type'))} | {_fmt_number(branch.get('value_si'))} | "
            f"{_md(branch.get('unit'))} |"
        )
    lines.extend(["", "## 6. Grafo orientado", ""])
    if graph is None:
        lines.append("No se proporcionó el artefacto del grafo; no se reconstruye en el reporte.")
    else:
        lines.extend(
            [
                f"Conectado: `{_md(graph.get('is_connected'))}`.",
                "",
                "| Arista | Nodo inicial | Nodo final | Componente |",
                "|---|---|---|---|",
            ]
        )
        for edge in graph.get("edges", []):
            lines.append(
                f"| {_md(edge.get('key'))} | N{_md(edge.get('node_from'))} | "
                f"N{_md(edge.get('node_to'))} | {_md(edge.get('component'))} |"
            )
    lines.extend(
        [
            "",
            "## 7. Matriz de incidencia",
            "",
            "Convención del proyecto: +1 si la rama sale del nodo y −1 si entra.",
            "",
        ]
    )
    lines.extend(
        _matrix_table(
            "A completa",
            incidence.get("A_full"),
            incidence.get("node_order_full", []),
            [
                f"{branch_id} ({component})"
                for branch_id, component in zip(
                    incidence.get("branch_order", []),
                    incidence.get("component_order", []),
                )
            ],
        )
    )
    lines.extend(
        _matrix_table(
            "A reducida",
            incidence.get("A_reduced"),
            incidence.get("node_order_reduced", []),
            [
                f"{branch_id} ({component})"
                for branch_id, component in zip(
                    incidence.get("branch_order", []),
                    incidence.get("component_order", []),
                )
            ],
        )
    )
    lines.extend(["## 8. Ecuaciones constitutivas", ""])
    if stamps is None:
        lines.append("No se proporcionó el artefacto de stamps; no se infieren ecuaciones.")
    else:
        lines.extend(
            [
                f"Convención: `{_md(stamps.get('equation_convention'))}`; "
                f"análisis `{_md(stamps.get('analysis'))}`, "
                f"frecuencia `{_fmt_number(stamps.get('frequency_hz'))}` Hz.",
                "",
                "| Rama | Componente | Ecuación | Y (unidad) | Z (unidad) | W (unidad) |",
                "|---|---|---|---|---|---|",
            ]
        )
        for stamp in stamps.get("stamps", []):
            lines.append(
                f"| {_md(stamp.get('branch_id'))} | {_md(stamp.get('component_name'))} | "
                f"`{_md(stamp.get('equation'))}` | {_fmt_complex(stamp.get('Y'))} "
                f"({_md(stamp.get('Y_unit'))}) | {_fmt_complex(stamp.get('Z'))} "
                f"({_md(stamp.get('Z_unit'))}) | {_fmt_complex(stamp.get('W'))} "
                f"({_md(stamp.get('W_unit'))}) |"
            )
    lines.extend(["", "## 9. Matrices de análisis", ""])
    if constitutive is None:
        lines.append("No se proporcionó el artefacto de matrices constitutivas.")
    else:
        constitutive_order = constitutive.get("row_order", [])
        for key in ("Y", "Z"):
            lines.extend(
                _matrix_table(
                    key,
                    constitutive.get(key),
                    constitutive_order,
                    constitutive_order,
                )
            )
        lines.extend(_format_vector(constitutive.get("W"), constitutive_order, "W"))
    lines.extend(["", "## 10. Sistema ensamblado", ""])
    if system is not None:
        if system.get("equation") == "T @ X = W_prime":
            lines.extend(
                _matrix_table(
                    "Sistema Tableau T",
                    system.get("T"),
                    system.get("row_order", []),
                    system.get("column_order", []),
                )
            )
            lines.extend(
                _format_vector(
                    system.get("W_prime"),
                    system.get("row_order", []),
                    "Vector W_prime",
                )
            )
        else:
            order = system.get("node_order", [])
            lines.extend(_matrix_table("Sistema nodal M", system.get("M"), order, order))
            lines.extend(_format_vector(system.get("rhs"), order, "Vector de excitación"))
    else:
        lines.append("No se proporcionó un sistema nodal o Tableau ensamblado.")
    lines.extend(_render_results(lines, solution, validation, sweep))
    lines.extend(["### Comparación con referencia", ""])
    if comparison is None:
        lines.append(
            "No se proporcionó una comparación; no se afirma validación contra LTspice/SPICE."
        )
    else:
        lines.extend(
            [
                f"Fuente: `{_md(comparison.get('simulator'))}` "
                f"({_md(comparison.get('simulator_version') or 'versión no especificada')}); "
                f"estado **{_md(comparison.get('status'))}**.",
                "",
                f"Puntos aprobados: {_md(comparison.get('passed_points'))}; "
                f"fallidos: {_md(comparison.get('failed_points'))}.",
                "",
                f"Umbrales: ganancia ≤ "
                f"`{_fmt_number(comparison.get('thresholds', {}).get('max_gain_error_db'))}` dB; "
                f"fase ≤ "
                f"`{_fmt_number(comparison.get('thresholds', {}).get('max_phase_error_deg'))}`°.",
                "",
            ]
        )
        lines.extend(
            [
                "| Frecuencia (Hz) | Ganancia agente (dB) | Referencia (dB) | "
                "Error (dB) | Fase agente (°) | Referencia (°) | Error (°) | "
                "Error relativo | Pasa |",
                "|---:|---:|---:|---:|---:|---:|---:|---:|---|",
            ]
        )
        for row in comparison.get("rows", []):
            lines.append(
                f"| {_fmt_number(row.get('frequency_hz'))} | "
                f"{_fmt_number(row.get('agent_gain_db'))} | "
                f"{_fmt_number(row.get('reference_gain_db'))} | "
                f"{_fmt_number(row.get('gain_signed_error_db'))} | "
                f"{_fmt_number(row.get('agent_phase_deg'))} | "
                f"{_fmt_number(row.get('reference_phase_deg'))} | "
                f"{_fmt_number(row.get('phase_error_deg'))} | "
                f"{_fmt_number(row.get('gain_relative_error'))} | "
                f"{_md(row.get('passed'))} |"
            )
        for error in comparison.get("errors", []):
            lines.append(f"- **Punto fuera de tolerancia:** {_md(error)}")
    lines.extend(["", "## 13. Advertencias, limitaciones y elementos no soportados", ""])
    warnings = list(parsed.get("warnings", [])) + list(circuit.get("warnings", []))
    if validation is not None:
        warnings.extend(validation.get("warnings", []))
        warnings.extend(validation.get("errors", []))
    if sweep is not None:
        warnings.extend(
            point.get("error") for point in sweep.get("points", []) if point.get("error")
        )
        warnings.extend(
            point.get("observable_warning")
            for point in sweep.get("points", [])
            if point.get("observable_warning")
        )
    warnings.extend(limitations or [])
    if comparison is None:
        warnings.append("No hay datos de referencia externa asociados.")
    if plot_manifest is None:
        warnings.append("No se proporcionó manifiesto de gráficas.")
    if warnings:
        lines.extend(f"- {_md(item)}" for item in dict.fromkeys(warnings))
    else:
        lines.append("No se registraron advertencias en los artefactos suministrados.")
    lines.extend(["", "## 14. Archivos generados y reproducibilidad", ""])
    if plot_manifest is not None:
        lines.extend(
            [
                f"- Gráfica de ganancia: `{_md(plot_manifest.get('gain_plot'))}`.",
                f"- Gráfica de fase: `{_md(plot_manifest.get('phase_plot'))}`.",
                f"- Formato: `{_md(plot_manifest.get('image_format'))}`; "
                f"puntos graficados: `{_md(plot_manifest.get('plotted_frequency_count'))}`.",
                "",
            ]
        )
    if input_hashes:
        lines.extend(["SHA-256 de las entradas:", ""])
        lines.extend(f"- `{_md(name)}`: `{digest}`" for name, digest in input_hashes.items())
    else:
        lines.append("No se proporcionaron rutas para registrar huellas SHA-256.")
    if invocation:
        fence = _code_fence(invocation)
        lines.extend(["", "Invocación:", "", f"{fence}powershell", invocation, fence])
    lines.extend(
        [
            "",
            "La reproducibilidad depende de conservar el netlist y los artefactos de entrada "
            "identificados por sus huellas; cada resultado y estado se cita desde esos "
            "artefactos, con sus unidades y tolerancias cuando están disponibles.",
            "",
        ]
    )
    return "\n".join(lines)


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate an auditable Markdown report from circuit result artifacts"
    )
    parser.add_argument("netlist", help="Original source netlist")
    parser.add_argument("parsed_json", help="Parsed netlist JSON")
    parser.add_argument("circuit_json", help="Normalized circuit model JSON")
    parser.add_argument("incidence_json", help="Incidence matrices JSON")
    parser.add_argument("-o", "--output", required=True, help="Markdown report output")
    parser.add_argument("--graph-json", help="Optional oriented graph JSON")
    parser.add_argument("--stamps-json", help="Optional element stamps JSON")
    parser.add_argument("--constitutive-json", help="Optional Y/Z/W matrices JSON")
    systems = parser.add_mutually_exclusive_group()
    systems.add_argument("--tableau-json", help="Optional assembled Tableau system JSON")
    systems.add_argument("--nodal-json", help="Optional assembled nodal system JSON")
    parser.add_argument("--solution-json", help="Optional point solution JSON")
    parser.add_argument("--validation-json", help="Independent Tableau validation JSON")
    parser.add_argument("--ac-sweep-json", help="Optional validated AC sweep JSON")
    parser.add_argument("--comparison-json", help="Optional reference comparison JSON")
    parser.add_argument("--plot-manifest-json", help="Optional plot manifest JSON")
    parser.add_argument(
        "--limitation",
        action="append",
        default=[],
        help="Additional documented limitation; may be supplied more than once",
    )
    args = parser.parse_args()

    paths = {
        "netlist": args.netlist,
        "parsed": args.parsed_json,
        "circuit": args.circuit_json,
        "incidence": args.incidence_json,
    }
    for key in (
        "graph_json",
        "stamps_json",
        "constitutive_json",
        "tableau_json",
        "nodal_json",
        "solution_json",
        "validation_json",
        "ac_sweep_json",
        "comparison_json",
        "plot_manifest_json",
    ):
        value = getattr(args, key)
        if value:
            paths[key] = value
    try:
        netlist_text = Path(args.netlist).read_text(encoding="utf-8")
        read_artifacts = {
            "parsed": _read_json(args.parsed_json),
            "circuit": _read_json(args.circuit_json),
            "incidence": _read_json(args.incidence_json),
        }
        for key, attribute in (
            ("graph_json", "graph"),
            ("stamps_json", "stamps"),
            ("constitutive_json", "constitutive"),
            ("tableau_json", "system"),
            ("nodal_json", "system"),
            ("solution_json", "solution"),
            ("validation_json", "validation"),
            ("ac_sweep_json", "sweep"),
            ("comparison_json", "comparison"),
            ("plot_manifest_json", "plot_manifest"),
        ):
            path = getattr(args, key)
            if path:
                read_artifacts[attribute] = _read_json(path)
        report = generate_report(
            read_artifacts["parsed"],
            read_artifacts["circuit"],
            read_artifacts["incidence"],
            netlist_text,
            graph=read_artifacts.get("graph"),
            stamps=read_artifacts.get("stamps"),
            constitutive=read_artifacts.get("constitutive"),
            system=read_artifacts.get("system"),
            solution=read_artifacts.get("solution"),
            validation=read_artifacts.get("validation"),
            sweep=read_artifacts.get("sweep"),
            comparison=read_artifacts.get("comparison"),
            plot_manifest=read_artifacts.get("plot_manifest"),
            input_hashes={
                str(Path(path)): _sha256(path)
                for path in paths.values()
            },
            limitations=args.limitation,
            invocation=subprocess.list2cmdline([sys.executable, *sys.argv]),
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: cannot generate report: {exc}", file=sys.stderr)
        return 2
    status_line = next(
        (line for line in report.splitlines() if line.startswith("**Estado del reporte:")),
        "**Estado del reporte: NOT_VALIDATED.**",
    )
    status = status_line.split(":", 1)[1].split(".", 1)[0].strip().rstrip("*")
    print(f"Report {status}: {output}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
