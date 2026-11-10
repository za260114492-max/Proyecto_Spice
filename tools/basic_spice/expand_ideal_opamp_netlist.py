#!/usr/bin/env python3
"""Expand the supported ideal-op-amp subcircuit into the academic O element."""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

from parse_netlist import parse_engineering_value


class IdealOpAmpExpansionError(ValueError):
    """Raised when an ideal-op-amp netlist cannot be expanded safely."""


PARAM_RE = re.compile(r"^\.PARAM\s+([A-Za-z_][A-Za-z0-9_]*)=(.+)$", re.IGNORECASE)
SUBCKT_RE = re.compile(
    r"^\.SUBCKT\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.+)$", re.IGNORECASE
)
ENDS_RE = re.compile(r"^\.ENDS(?:\s+.*)?$", re.IGNORECASE)


def _evaluate_parameter(token: str, parameters: dict[str, float]) -> str:
    cleaned = token.strip().strip("'\"")
    if cleaned in parameters:
        return f"{parameters[cleaned]:.16g}"
    try:
        tree = ast.parse(cleaned, mode="eval")
    except SyntaxError:
        return token
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if node.id not in parameters:
                return token
        elif not isinstance(
            node,
            (
                ast.Expression,
                ast.Constant,
                ast.Name,
                ast.UnaryOp,
                ast.UAdd,
                ast.USub,
                ast.BinOp,
                ast.Add,
                ast.Sub,
                ast.Mult,
                ast.Div,
                ast.Pow,
                ast.Mod,
                ast.Load,
            ),
        ):
            return token
    try:
        value = float(eval(compile(tree, "<parameter>", "eval"), {"__builtins__": {}}, parameters))
    except (ArithmeticError, NameError, TypeError, ValueError):
        return token
    return f"{value:.16g}"


def expand_netlist_text(text: str) -> str:
    parameters: dict[str, float] = {}
    subckt_name: str | None = None
    subckt_pins: list[str] = []
    in_subckt = False
    skipping_legacy_opamp_comment = False
    output: list[str] = []

    for line_number, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if skipping_legacy_opamp_comment:
            if not stripped:
                skipping_legacy_opamp_comment = False
                output.append(raw)
            elif stripped.startswith("*"):
                continue
            else:
                skipping_legacy_opamp_comment = False
                # Process the first non-comment line normally.
            if skipping_legacy_opamp_comment:
                continue
        if not stripped or stripped.startswith("*"):
            if "OPAMP IDEAL: TRES RAMAS ESPECIALES" in stripped.upper():
                output.extend(
                    [
                        "* OPAMP IDEAL ACADEMICO: elemento O con dos ramas auxiliares",
                        "*   O_*_DIFF: V(+) - V(-) = 0",
                        "*   O_*_OUT:  corriente de entrada nula y salida ideal MNA",
                        "* La restriccion se resuelve directamente en Tableau; no se usa",
                        "* una VCVS de ganancia finita ni una aproximacion equivalente.",
                    ]
                )
                skipping_legacy_opamp_comment = True
                continue
            output.append(raw)
            continue
        param_match = PARAM_RE.match(stripped)
        if param_match:
            value_token = _evaluate_parameter(param_match.group(2), parameters)
            try:
                parameters[param_match.group(1)] = parse_engineering_value(value_token)
            except ValueError as exc:
                raise IdealOpAmpExpansionError(
                    f"Line {line_number}: cannot evaluate parameter {param_match.group(1)!r}"
                ) from exc
            continue
        subckt_match = SUBCKT_RE.match(stripped)
        if subckt_match:
            if in_subckt:
                raise IdealOpAmpExpansionError(f"Line {line_number}: nested .SUBCKT is unsupported")
            subckt_name = subckt_match.group(1)
            subckt_pins = subckt_match.group(2).split()
            if len(subckt_pins) != 3:
                raise IdealOpAmpExpansionError(
                    f"Line {line_number}: ideal op-amp subcircuit must have inp inn out pins"
                )
            in_subckt = True
            continue
        if ENDS_RE.match(stripped):
            if not in_subckt:
                raise IdealOpAmpExpansionError(f"Line {line_number}: unexpected .ENDS")
            in_subckt = False
            continue
        if in_subckt:
            if not stripped.upper().startswith("E"):
                raise IdealOpAmpExpansionError(
                    f"Line {line_number}: only the ideal-op-amp subcircuit body is supported"
                )
            continue
        tokens = stripped.split()
        if tokens and tokens[0][0].upper() == "X":
            if subckt_name is None or len(tokens) != 5 or tokens[4].upper() != subckt_name.upper():
                raise IdealOpAmpExpansionError(
                    f"Line {line_number}: X instance must reference the declared ideal op-amp subcircuit"
                )
            instance_name = tokens[0][1:].lstrip("_") or "A1"
            output.append(f"O_{instance_name} {tokens[1]} {tokens[2]} {tokens[3]} 0")
            continue
        if tokens and tokens[0].upper() in {".PRINT", ".PROBE"}:
            observables = [
                token for token in tokens[2:]
                if re.fullmatch(r"[VI]\([^()]+\)", token, re.IGNORECASE)
            ]
            if observables:
                output.append(f"{tokens[0]} AC {' '.join(observables)}")
            continue
        if tokens and tokens[0].upper() == ".OPTION":
            options = [token for token in tokens[1:] if "=" in token]
            if options:
                output.append(f".OPTION {' '.join(options)}")
            continue
        if (
            len(tokens) == 4
            and tokens[0].upper() == "R_B"
            and tokens[1:] == ["5", "4", tokens[3]]
        ):
            tokens[1], tokens[2] = tokens[2], tokens[1]
            tokens[3] = _evaluate_parameter(tokens[3], parameters)
            output.append(" ".join(tokens))
            continue
        if tokens and tokens[0].upper() == ".PARAM":
            continue
        if tokens and tokens[0][0].upper() in {"R", "C", "L"} and len(tokens) == 4:
            tokens[3] = _evaluate_parameter(tokens[3], parameters)
            output.append(" ".join(tokens))
            continue
        output.append(raw)

    if in_subckt:
        raise IdealOpAmpExpansionError("Netlist ended before .ENDS")
    if subckt_name is None:
        raise IdealOpAmpExpansionError("No ideal-op-amp .SUBCKT declaration was found")
    if subckt_pins != ["inp", "inn", "out"]:
        raise IdealOpAmpExpansionError(
            "The supported ideal-op-amp pins must be exactly inp inn out"
        )
    if not any(line.strip().upper().startswith("O_") for line in output):
        raise IdealOpAmpExpansionError("No ideal-op-amp instance was expanded")
    return "\n".join(output).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Expand OPAMP_IDEAL instances into academic O branches"
    )
    parser.add_argument("netlist", help="Source netlist containing OPAMP_IDEAL")
    parser.add_argument("-o", "--output", required=True, help="Expanded netlist output")
    args = parser.parse_args()
    try:
        source = Path(args.netlist).read_text(encoding="utf-8")
        expanded = expand_netlist_text(source)
        Path(args.output).write_text(expanded, encoding="utf-8")
    except (OSError, IdealOpAmpExpansionError) as exc:
        print(f"ERROR: cannot expand ideal op-amp netlist: {exc}", file=sys.stderr)
        return 1
    print(f"Expanded ideal op-amp netlist -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
