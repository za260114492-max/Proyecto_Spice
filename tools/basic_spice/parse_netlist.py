#!/usr/bin/env python3
"""
parse_netlist.py

Purpose:
    Parse the educational SPICE subset used by the Basic SPICE Educational
    Agent. The parser preserves source-line traceability and converts values
    to SI units.

Supported MVP elements:
    R, C, L, independent sources V/I, and voltage-controlled voltage source E.
Supported directives:
    .OP, .AC LIN/DEC, .PRINT/.PROBE AC V(node)/I(component), .OPTION, .END

Author: Dr. Francisco E. Rangel-Patiño
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

VALUE_RE = re.compile(
    r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([a-zA-Z]+)?$"
)
PREFIXES = {
    "": 1.0,
    "t": 1e12,
    "g": 1e9,
    "meg": 1e6,
    "k": 1e3,
    "m": 1e-3,
    "u": 1e-6,
    "n": 1e-9,
    "p": 1e-12,
    "f": 1e-15,
}
UNITS = {
    "R": "ohm",
    "C": "farad",
    "L": "henry",
    "V": "volt",
    "I": "ampere",
    "E": "dimensionless",
}
OBSERVABLE_RE = re.compile(r"^([VI])\(([^()]+)\)$", re.IGNORECASE)
OPTION_RE = re.compile(r"^([A-Z][A-Z0-9_]*)=(\S+)$", re.IGNORECASE)


class NetlistParseError(ValueError):
    """Raised when a netlist line cannot be parsed safely."""


def parse_engineering_value(token: str) -> float:
    """Convert an engineering value such as 1k, 10u, or 3.3meg to SI."""
    cleaned = token.strip().replace("µ", "u")
    match = VALUE_RE.fullmatch(cleaned)
    if not match:
        raise NetlistParseError(f"Invalid engineering value: {token!r}")
    number = float(match.group(1))
    suffix = (match.group(2) or "").lower()
    # Permit a trailing unit-like suffix only when its leading prefix is known.
    if suffix in PREFIXES:
        factor = PREFIXES[suffix]
    else:
        candidates = [p for p in PREFIXES if p and suffix.startswith(p)]
        if not candidates:
            raise NetlistParseError(f"Unsupported engineering suffix: {suffix!r}")
        prefix = max(candidates, key=len)
        factor = PREFIXES[prefix]
    value = number * factor
    if not math.isfinite(value):
        raise NetlistParseError(f"Non-finite value: {token!r}")
    return value


def normalize_node(token: str) -> str:
    """Normalize ground aliases while preserving other node labels."""
    node = token.strip()
    if not node:
        raise NetlistParseError("Empty node identifier")
    return "0" if node.lower() in {"0", "gnd"} else node


def _parse_source(tokens: list[str], line_number: int, source_line: str) -> dict[str, Any]:
    if len(tokens) < 4:
        raise NetlistParseError(f"Line {line_number}: source requires at least 4 tokens")
    name, n_plus, n_minus = tokens[:3]
    rest = tokens[3:]
    dc_value: float | None = None
    ac_magnitude: float | None = None
    phase_deg = 0.0
    if rest[0].upper() not in {"DC", "AC"}:
        if len(rest) != 1:
            raise NetlistParseError(
                f"Line {line_number}: use DC or AC before additional source tokens"
            )
        dc_value = parse_engineering_value(rest[0])
    else:
        index = 0
        seen_modes: set[str] = set()
        while index < len(rest):
            mode = rest[index].upper()
            if mode not in {"DC", "AC"}:
                raise NetlistParseError(
                    f"Line {line_number}: expected DC or AC before {rest[index]!r}"
                )
            if mode in seen_modes:
                raise NetlistParseError(f"Line {line_number}: duplicate {mode} source value")
            seen_modes.add(mode)
            index += 1
            if index >= len(rest) or rest[index].upper() in {"DC", "AC"}:
                raise NetlistParseError(f"Line {line_number}: {mode} source value is missing")
            value = parse_engineering_value(rest[index])
            index += 1
            if mode == "DC":
                dc_value = value
            else:
                ac_magnitude = value
                if index < len(rest) and rest[index].upper() not in {"DC", "AC"}:
                    try:
                        phase_deg = float(rest[index])
                    except ValueError as exc:
                        raise NetlistParseError(
                            f"Line {line_number}: invalid AC phase {rest[index]!r}"
                        ) from exc
                    if not math.isfinite(phase_deg):
                        raise NetlistParseError(
                            f"Line {line_number}: AC phase must be finite"
                        )
                    index += 1

    if dc_value is None and ac_magnitude is None:
        raise NetlistParseError(f"Line {line_number}: source value is missing")
    if ac_magnitude is not None and ac_magnitude < 0:
        raise NetlistParseError(f"Line {line_number}: AC magnitude must be nonnegative")
    kind = (
        "DC_AC"
        if dc_value is not None and ac_magnitude is not None
        else ("DC" if dc_value is not None else "AC")
    )
    value = dc_value if dc_value is not None else ac_magnitude
    return {
        "name": name,
        "type": name[0].upper(),
        "node_from": normalize_node(n_plus),
        "node_to": normalize_node(n_minus),
        "value_si": value,
        "unit": UNITS[name[0].upper()],
        "source_kind": kind,
        "dc_value_si": dc_value if dc_value is not None else 0.0,
        "ac_magnitude": ac_magnitude,
        "ac_phase_deg": phase_deg if ac_magnitude is not None else None,
        "source_line": source_line,
        "line_number": line_number,
    }


def _parse_controlled_voltage_source(
    tokens: list[str],
    line_number: int,
    source_line: str,
) -> dict[str, Any]:
    if len(tokens) != 6:
        raise NetlistParseError(
            f"Line {line_number}: E source requires: name node+ node- control+ control- gain"
        )
    name, n_plus, n_minus, control_plus, control_minus, gain_token = tokens
    gain = parse_engineering_value(gain_token)
    if normalize_node(n_plus) == normalize_node(n_minus):
        raise NetlistParseError(f"Line {line_number}: E source output nodes must differ")
    if normalize_node(control_plus) == normalize_node(control_minus):
        raise NetlistParseError(f"Line {line_number}: E source control nodes must differ")
    return {
        "name": name,
        "type": "E",
        "node_from": normalize_node(n_plus),
        "node_to": normalize_node(n_minus),
        "control_node_plus": normalize_node(control_plus),
        "control_node_minus": normalize_node(control_minus),
        "value_si": gain,
        "unit": UNITS["E"],
        "source_kind": None,
        "ac_magnitude": None,
        "ac_phase_deg": None,
        "source_line": source_line,
        "line_number": line_number,
    }


def parse_component(tokens: list[str], line_number: int, source_line: str) -> dict[str, Any]:
    """Parse one supported component line."""
    if not tokens or not tokens[0]:
        raise NetlistParseError(f"Line {line_number}: empty component line")
    designator = tokens[0][0].upper()
    if designator not in UNITS:
        raise NetlistParseError(
            f"Line {line_number}: unsupported element {tokens[0]!r}; supported: R, C, L, V, I, E"
        )
    if designator in {"V", "I"}:
        return _parse_source(tokens, line_number, source_line)
    if designator == "E":
        return _parse_controlled_voltage_source(tokens, line_number, source_line)
    if len(tokens) != 4:
        raise NetlistParseError(
            f"Line {line_number}: {designator} element requires: name node+ node- value"
        )
    name, n_plus, n_minus, value_token = tokens
    value = parse_engineering_value(value_token)
    if value <= 0:
        raise NetlistParseError(f"Line {line_number}: passive component value must be positive")
    return {
        "name": name,
        "type": designator,
        "node_from": normalize_node(n_plus),
        "node_to": normalize_node(n_minus),
        "value_si": value,
        "unit": UNITS[designator],
        "source_kind": None,
        "dc_value_si": None,
        "ac_magnitude": None,
        "ac_phase_deg": None,
        "source_line": source_line,
        "line_number": line_number,
    }


def parse_directive(tokens: list[str], line_number: int, source_line: str) -> dict[str, Any]:
    command = tokens[0].upper()
    if command in {".END", ".OP"}:
        if len(tokens) != 1:
            raise NetlistParseError(f"Line {line_number}: {command} does not accept arguments in this MVP")
        return {"command": command[1:], "source_line": source_line, "line_number": line_number}
    if command in {".PROBE", ".PRINT"}:
        if len(tokens) < 3 or tokens[1].upper() != "AC":
            raise NetlistParseError(
                f"Line {line_number}: expected {command} AC followed by V(node) or I(component)"
            )
        observables: list[dict[str, str]] = []
        for token in tokens[2:]:
            match = OBSERVABLE_RE.fullmatch(token)
            if not match or not match.group(2).strip():
                raise NetlistParseError(
                    f"Line {line_number}: expected observables in the form V(node) or I(component)"
                )
            kind, target = match.group(1).upper(), match.group(2).strip()
            observables.append(
                {
                    "kind": kind,
                    "node" if kind == "V" else "component": (
                        normalize_node(target) if kind == "V" else target
                    ),
                }
            )
        return {
            "command": command[1:],
            "analysis": "AC",
            "observables": observables,
            "voltage_nodes": [item["node"] for item in observables if item["kind"] == "V"],
            "source_line": source_line,
            "line_number": line_number,
        }
    if command == ".OPTION":
        if len(tokens) < 2:
            raise NetlistParseError(f"Line {line_number}: .OPTION requires one or more NAME=VALUE settings")
        options: dict[str, str] = {}
        for token in tokens[1:]:
            match = OPTION_RE.fullmatch(token)
            if not match:
                raise NetlistParseError(
                    f"Line {line_number}: invalid .OPTION setting {token!r}; expected NAME=VALUE"
                )
            name, value = match.group(1).upper(), match.group(2)
            if name in options:
                raise NetlistParseError(f"Line {line_number}: duplicate .OPTION setting {name}")
            options[name] = value
        return {
            "command": "OPTION",
            "options": options,
            "source_line": source_line,
            "line_number": line_number,
        }
    if command == ".AC":
        if len(tokens) != 5 or tokens[1].upper() not in {"LIN", "DEC"}:
            raise NetlistParseError(
                f"Line {line_number}: expected .AC LIN|DEC points start stop"
            )
        points = int(tokens[2])
        f_start = parse_engineering_value(tokens[3])
        f_stop = parse_engineering_value(tokens[4])
        if points <= 0 or f_start <= 0 or f_stop < f_start:
            raise NetlistParseError(f"Line {line_number}: invalid AC sweep range")
        return {
            "command": "AC",
            "sweep": tokens[1].upper(),
            "points": points,
            "f_start_hz": f_start,
            "f_stop_hz": f_stop,
            "source_line": source_line,
            "line_number": line_number,
        }
    raise NetlistParseError(f"Line {line_number}: unsupported directive {tokens[0]!r}")


def parse_netlist_text(text: str, source_name: str = "<memory>") -> dict[str, Any]:
    """Parse netlist text into a JSON-serializable intermediate representation."""
    elements: list[dict[str, Any]] = []
    directives: list[dict[str, Any]] = []
    warnings: list[str] = []
    names: set[str] = set()
    saw_end = False

    for line_number, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("*"):
            continue
        # The teaching subset intentionally avoids inline comments to prevent ambiguity.
        tokens = stripped.split()
        if stripped.startswith("."):
            directive = parse_directive(tokens, line_number, raw)
            directives.append(directive)
            if directive["command"] == "END":
                saw_end = True
                break
            continue
        element = parse_component(tokens, line_number, raw)
        canonical_name = element["name"].upper()
        if canonical_name in names:
            raise NetlistParseError(f"Line {line_number}: duplicate component name {element['name']!r}")
        names.add(canonical_name)
        elements.append(element)

    if not elements:
        raise NetlistParseError("The netlist contains no supported elements")
    if not saw_end:
        warnings.append(".END directive not found; parsed to end of file")
    all_nodes = {e["node_from"] for e in elements} | {e["node_to"] for e in elements}
    for element in elements:
        all_nodes.update(
            node
            for node in (
                element.get("control_node_plus"),
                element.get("control_node_minus"),
            )
            if node is not None
        )
    nodes = sorted(
        all_nodes,
        key=lambda x: (x != "0", 0, int(x)) if x.isdigit() else (True, 1, x.lower()),
    )
    if "0" not in nodes:
        warnings.append("Ground node 0/GND is not present; later validation should reject the circuit")
    return {
        "schema_version": "1.0",
        "source_name": source_name,
        "elements": elements,
        "directives": directives,
        "nodes": nodes,
        "warnings": warnings,
    }


def parse_netlist_file(path: str | Path) -> dict[str, Any]:
    input_path = Path(path)
    return parse_netlist_text(input_path.read_text(encoding="utf-8"), input_path.name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse an educational SPICE netlist")
    parser.add_argument("netlist", help="Input .cir/.sp/.net file")
    parser.add_argument("-o", "--output", required=True, help="Output parsed JSON file")
    args = parser.parse_args()
    parsed = parse_netlist_file(args.netlist)
    Path(args.output).write_text(json.dumps(parsed, indent=2), encoding="utf-8")
    print(f"Parsed {len(parsed['elements'])} elements -> {args.output}")
    for warning in parsed["warnings"]:
        print(f"WARNING: {warning}")


if __name__ == "__main__":
    main()
