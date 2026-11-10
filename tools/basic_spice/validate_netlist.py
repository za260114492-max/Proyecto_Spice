#!/usr/bin/env python3
"""Validate semantic and topology rules in parsed educational SPICE data."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


EXPECTED_UNITS = {
    "R": "ohm",
    "C": "farad",
    "L": "henry",
    "V": "volt",
    "I": "ampere",
    "E": "dimensionless",
    "O": "dimensionless",
}
PASSIVE_TYPES = {"R", "C", "L"}
SOURCE_TYPES = {"V", "I"}


def _issue(
    code: str,
    message: str,
    *,
    line_number: int | None = None,
    component: str | None = None,
    node: str | None = None,
    suggestion: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {"code": code, "message": message}
    if line_number is not None:
        result["line_number"] = line_number
    if component is not None:
        result["component"] = component
    if node is not None:
        result["node"] = node
    if suggestion is not None:
        result["suggestion"] = suggestion
    return result


def _finite_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def validate_netlist(parsed: dict[str, Any]) -> dict[str, Any]:
    """Validate parsed data without repeating the parser's lexical checks."""
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if parsed.get("schema_version") != "1.0":
        errors.append(
            _issue(
                "INVALID_SCHEMA",
                f"Versión de esquema no soportada: {parsed.get('schema_version')!r}.",
                suggestion="Vuelve a generar el JSON con la versión actual de parse_netlist.py.",
            )
        )
    elements = parsed.get("elements")
    directives = parsed.get("directives", [])

    if not isinstance(elements, list) or not elements:
        errors.append(
            _issue(
                "NO_ELEMENTS",
                "El netlist analizado no contiene elementos.",
                suggestion="Agrega al menos un componente soportado.",
            )
        )
        elements = []
    if not isinstance(directives, list):
        errors.append(
            _issue(
                "INVALID_DIRECTIVES",
                "El campo 'directives' debe ser una lista.",
                suggestion="Vuelve a generar el JSON con parse_netlist.py.",
            )
        )
        directives = []

    nodes: set[str] = set()
    names: set[str] = set()
    adjacency: dict[str, set[str]] = {}
    for index, element in enumerate(elements):
        if not isinstance(element, dict):
            errors.append(
                _issue(
                    "INVALID_ELEMENT",
                    f"El elemento en la posición {index} no es un objeto.",
                )
            )
            continue

        name = element.get("name")
        kind = element.get("type")
        line_number = element.get("line_number")
        line_number = line_number if isinstance(line_number, int) and line_number > 0 else None
        if not isinstance(name, str) or not name.strip():
            errors.append(
                _issue(
                    "INVALID_NAME",
                    "El elemento no tiene un nombre válido.",
                    line_number=line_number,
                )
            )
            continue
        component = name.strip()
        if component.upper() in names:
            errors.append(
                _issue(
                    "DUPLICATE_COMPONENT",
                    f"El identificador {component!r} está repetido.",
                    line_number=line_number,
                    component=component,
                    suggestion="Asigna un nombre único a cada componente.",
                )
            )
        names.add(component.upper())

        if not isinstance(kind, str) or kind not in EXPECTED_UNITS:
            errors.append(
                _issue(
                    "UNSUPPORTED_ELEMENT",
                    f"El elemento {component!r} tiene tipo no soportado: {kind!r}.",
                    line_number=line_number,
                    component=component,
                    suggestion="Usa R, C, L, V, I, E o un OpAmp ideal O.",
                )
            )
            continue
        if not component.upper().startswith(kind):
            errors.append(
                _issue(
                    "TYPE_NAME_MISMATCH",
                    f"El nombre {component!r} no corresponde al tipo {kind}.",
                    line_number=line_number,
                    component=component,
                    suggestion=f"Usa un identificador que comience con {kind}.",
                )
            )
        if element.get("unit") != EXPECTED_UNITS[kind]:
            errors.append(
                _issue(
                    "UNIT_MISMATCH",
                    f"{component!r} debe usar la unidad {EXPECTED_UNITS[kind]!r}.",
                    line_number=line_number,
                    component=component,
                )
            )

        node_from = element.get("node_from")
        node_to = element.get("node_to")
        if not isinstance(node_from, str) or not node_from.strip():
            errors.append(
                _issue(
                    "INVALID_NODE",
                    f"{component!r} no tiene un nodo inicial válido.",
                    line_number=line_number,
                    component=component,
                )
            )
            continue
        if not isinstance(node_to, str) or not node_to.strip():
            errors.append(
                _issue(
                    "INVALID_NODE",
                    f"{component!r} no tiene un nodo final válido.",
                    line_number=line_number,
                    component=component,
                )
            )
            continue
        node_from, node_to = node_from.strip(), node_to.strip()
        nodes.update((node_from, node_to))
        adjacency.setdefault(node_from, set()).add(node_to)
        adjacency.setdefault(node_to, set()).add(node_from)
        if node_from == node_to:
            errors.append(
                _issue(
                    "SELF_CONNECTED_BRANCH",
                    f"La rama {component!r} conecta el nodo {node_from!r} consigo mismo.",
                    line_number=line_number,
                    component=component,
                    node=node_from,
                    suggestion="Conecta el componente entre dos nodos distintos.",
                )
            )

        value = element.get("value_si")
        if not _finite_number(value):
            errors.append(
                _issue(
                    "INVALID_VALUE",
                    f"El valor SI de {component!r} debe ser un número finito.",
                    line_number=line_number,
                    component=component,
                    suggestion="Corrige el valor y vuelve a ejecutar parse_netlist.py.",
                )
            )
        elif kind in PASSIVE_TYPES and value <= 0:
            errors.append(
                _issue(
                    "NONPOSITIVE_PASSIVE_VALUE",
                    f"El valor de {component!r} debe ser positivo.",
                    line_number=line_number,
                    component=component,
                    suggestion="Usa un valor pasivo mayor que cero.",
                )
            )

        if kind == "E":
            control_plus = element.get("control_node_plus")
            control_minus = element.get("control_node_minus")
            if (
                not isinstance(control_plus, str)
                or not control_plus.strip()
                or not isinstance(control_minus, str)
                or not control_minus.strip()
            ):
                errors.append(
                    _issue(
                        "INVALID_CONTROL_NODES",
                        f"La fuente controlada {component!r} requiere dos nodos de control.",
                        line_number=line_number,
                        component=component,
                    )
                )
            else:
                control_plus = control_plus.strip()
                control_minus = control_minus.strip()
                nodes.update((control_plus, control_minus))
                if control_plus == control_minus:
                    errors.append(
                        _issue(
                            "INVALID_CONTROL_NODES",
                            f"Los nodos de control de {component!r} deben ser distintos.",
                            line_number=line_number,
                            component=component,
                            node=control_plus,
                        )
                    )

        if kind == "O":
            role = element.get("opamp_role")
            if role not in {"differential", "output"}:
                errors.append(
                    _issue(
                        "INVALID_OPAMP_ROLE",
                        f"{component!r} debe declarar rol diferencial u output.",
                        line_number=line_number,
                        component=component,
                    )
                )

        if kind in SOURCE_TYPES:
            source_kind = element.get("source_kind")
            if not isinstance(source_kind, str) or source_kind not in {"DC", "AC", "DC_AC"}:
                errors.append(
                    _issue(
                        "INVALID_SOURCE_KIND",
                        f"La fuente {component!r} debe indicar source_kind DC, AC o DC_AC.",
                        line_number=line_number,
                        component=component,
                    )
                )
            dc_value = element.get("dc_value_si")
            if dc_value is not None and not _finite_number(dc_value):
                errors.append(
                    _issue(
                        "INVALID_DC_VALUE",
                        f"El valor DC de {component!r} debe ser finito.",
                        line_number=line_number,
                        component=component,
                    )
                )
            if isinstance(source_kind, str) and source_kind in {"AC", "DC_AC"}:
                magnitude = element.get("ac_magnitude")
                phase = element.get("ac_phase_deg")
                if not _finite_number(magnitude) or magnitude < 0:
                    errors.append(
                        _issue(
                            "INVALID_AC_MAGNITUDE",
                            f"La magnitud AC de {component!r} debe ser finita y no negativa.",
                            line_number=line_number,
                            component=component,
                        )
                    )
                if phase is not None and not _finite_number(phase):
                    errors.append(
                        _issue(
                            "INVALID_AC_PHASE",
                            f"La fase AC de {component!r} debe ser finita.",
                            line_number=line_number,
                            component=component,
                        )
                    )

    if "0" not in nodes:
        errors.append(
            _issue(
                "MISSING_GROUND",
                "No se encontró el nodo de referencia 0/GND.",
                suggestion="Conecta explícitamente el circuito al nodo 0 o GND.",
            )
        )
    elif nodes:
        reached = {"0"}
        pending = ["0"]
        while pending:
            current = pending.pop()
            for neighbor in adjacency.get(current, set()) - reached:
                reached.add(neighbor)
                pending.append(neighbor)
        for node in sorted(nodes - reached):
            errors.append(
                _issue(
                    "DISCONNECTED_NODE",
                    f"El nodo {node!r} no está conectado al nodo de referencia 0.",
                    node=node,
                    suggestion="Revisa la topología y conecta la subred a tierra.",
                )
            )

    ac_directive_count = 0
    op_directive_count = 0
    end_directives = 0
    for index, directive in enumerate(directives):
        if not isinstance(directive, dict):
            errors.append(
                _issue(
                    "INVALID_DIRECTIVE",
                    f"La directiva en la posición {index} no es un objeto.",
                )
            )
            continue
        command = directive.get("command")
        line_number = directive.get("line_number")
        line_number = line_number if isinstance(line_number, int) and line_number > 0 else None
        if command == "AC":
            ac_directive_count += 1
            points = directive.get("points")
            start = directive.get("f_start_hz")
            stop = directive.get("f_stop_hz")
            if (
                not isinstance(directive.get("sweep"), str)
                or directive.get("sweep") not in {"LIN", "DEC"}
                or not isinstance(points, int)
                or isinstance(points, bool)
                or points <= 0
                or not _finite_number(start)
                or not _finite_number(stop)
                or start <= 0
                or stop < start
            ):
                errors.append(
                    _issue(
                        "INVALID_AC_DIRECTIVE",
                        "La directiva .AC tiene barrido o rango de frecuencias inválido.",
                        line_number=line_number,
                        suggestion=(
                            "Usa .AC LIN|DEC puntos f_inicio f_fin con valores "
                            "positivos y f_fin >= f_inicio."
                        ),
                    )
                )
        elif isinstance(command, str) and command in {"PROBE", "PRINT"}:
            observables = directive.get("observables")
            if observables is None and command == "PROBE":
                observables = [
                    {"kind": "V", "node": node}
                    for node in directive.get("voltage_nodes", [])
                ]
            if (
                directive.get("analysis") != "AC"
                or not isinstance(observables, list)
                or not observables
            ):
                errors.append(
                    _issue(
                        f"INVALID_{command}_DIRECTIVE",
                        f"La directiva .{command} debe contener mediciones AC.",
                        line_number=line_number,
                        suggestion=f"Usa .{command} AC con V(nodo) o I(componente).",
                    )
                )
                continue
            for observable in observables:
                if not isinstance(observable, dict):
                    errors.append(
                        _issue(
                            f"INVALID_{command}_OBSERVABLE",
                            f"La directiva .{command} contiene una medición inválida.",
                            line_number=line_number,
                        )
                    )
                    continue
                kind = observable.get("kind")
                if kind == "V":
                    node = observable.get("node")
                    if not isinstance(node, str) or not node.strip():
                        errors.append(
                            _issue(
                                f"INVALID_{command}_OBSERVABLE",
                                f"La medición de tensión de .{command} no tiene nodo.",
                                line_number=line_number,
                            )
                        )
                    elif node not in nodes:
                        errors.append(
                            _issue(
                                "UNKNOWN_PROBE_NODE",
                                f"La directiva .{command} referencia el nodo inexistente {node!r}.",
                                line_number=line_number,
                                node=node,
                                suggestion="Usa nodos presentes en los componentes del circuito.",
                            )
                        )
                elif kind == "I":
                    component = observable.get("component")
                    if (
                        not isinstance(component, str)
                        or component.strip().upper() not in names
                    ):
                        errors.append(
                            _issue(
                                "UNKNOWN_PROBE_COMPONENT",
                                f"La directiva .{command} referencia un componente inexistente: {component!r}.",
                                line_number=line_number,
                                component=component if isinstance(component, str) else None,
                            )
                        )
                else:
                    errors.append(
                        _issue(
                            f"INVALID_{command}_OBSERVABLE",
                            f"Tipo de medición no soportado en .{command}: {kind!r}.",
                            line_number=line_number,
                        )
                    )
        elif command == "OPTION":
            options = directive.get("options")
            if (
                not isinstance(options, dict)
                or not options
                or any(
                    not isinstance(key, str)
                    or not key.strip()
                    or not isinstance(value, str)
                    or not value.strip()
                    for key, value in options.items()
                )
            ):
                errors.append(
                    _issue(
                        "INVALID_OPTION_DIRECTIVE",
                        "La directiva .OPTION debe contener ajustes NAME=VALUE.",
                        line_number=line_number,
                    )
                )
        elif command == "OP":
            op_directive_count += 1
        elif command == "END":
            end_directives += 1
        else:
            errors.append(
                _issue(
                    "UNSUPPORTED_DIRECTIVE",
                    f"Directiva no soportada en los datos analizados: {command!r}.",
                    line_number=line_number,
                    suggestion="Usa .OP, .AC, .PROBE/.PRINT AC, .OPTION y .END.",
                )
            )
    if ac_directive_count > 1:
        errors.append(
            _issue(
                "DUPLICATE_AC",
                "Se encontró más de una directiva .AC.",
                suggestion="Conserva una sola directiva .AC.",
            )
        )
    if op_directive_count > 1:
        errors.append(
            _issue(
                "DUPLICATE_OP",
                "Se encontró más de una directiva .OP.",
                suggestion="Conserva una sola directiva .OP.",
            )
        )
    if end_directives > 1:
        errors.append(
            _issue(
                "DUPLICATE_END",
                "El JSON contiene más de una directiva .END.",
                suggestion="Conserva una sola directiva .END al final del netlist.",
            )
        )
    parser_warnings = parsed.get("warnings", [])
    if not isinstance(parser_warnings, list):
        parser_warnings = []
    for message in parser_warnings:
        if isinstance(message, str) and message.strip():
            if message.strip() == ".END directive not found; parsed to end of file":
                continue
            warnings.append(_issue("PARSER_WARNING", message.strip()))
    if not any(
        directive.get("command") == "END"
        for directive in directives
        if isinstance(directive, dict)
    ):
        warnings.append(
            _issue(
                "MISSING_END",
                "No se encontró .END; el parser procesó el archivo hasta el final.",
                suggestion="Agrega .END para delimitar explícitamente el netlist.",
            )
        )

    status = "FAIL" if errors else ("WARN" if warnings else "PASS")
    return {
        "schema_version": "1.0",
        "source_name": parsed.get("source_name", "<unknown>"),
        "status": status,
        "element_count": len(elements),
        "node_count": len(nodes),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate semantic and topology rules in parsed netlist JSON"
    )
    parser.add_argument("parsed_json", help="JSON generated by parse_netlist.py")
    parser.add_argument("-o", "--output", required=True, help="Validation report JSON")
    args = parser.parse_args()

    try:
        parsed = json.loads(Path(args.parsed_json).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read parsed netlist {args.parsed_json!r}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(parsed, dict):
        print("ERROR: parsed netlist JSON root must be an object.", file=sys.stderr)
        return 2

    result = validate_netlist(parsed)
    try:
        serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        Path(args.output).write_text(serialized, encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot write validation report {args.output!r}: {exc}", file=sys.stderr)
        return 2

    print(f"Netlist validation: {result['status']} -> {args.output}")
    for error in result["errors"]:
        print(f"ERROR [{error['code']}]: {error['message']}", file=sys.stderr)
    for warning in result["warnings"]:
        print(f"WARNING [{warning['code']}]: {warning['message']}")
    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
