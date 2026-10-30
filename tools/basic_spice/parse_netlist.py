#!/usr/bin/env python3
"""
parse_netlist.py

Purpose:
    Parse the educational SPICE subset used by the Basic SPICE Educational
    Agent. The parser preserves source-line traceability and converts values
    to SI units.

Supported MVP elements:
    R, C, L, independent voltage sources V, independent current sources I.
Supported directives:
    .OP, .AC LIN, .AC DEC, .PROBE AC V(input) V(output), .END

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
UNITS = {"R": "ohm", "C": "farad", "L": "henry", "V": "volt", "I": "ampere"}
PROBE_VOLTAGE_RE = re.compile(r"^V\(([^()]+)\)$", re.IGNORECASE)


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
    kind = "DC"
    magnitude_token = rest[0]
    phase_deg = 0.0
    if rest[0].upper() in {"DC", "AC"}:
        kind = rest[0].upper()
        if len(rest) < 2:
            raise NetlistParseError(f"Line {line_number}: {kind} source value is missing")
        magnitude_token = rest[1]
        if kind == "AC" and len(rest) >= 3:
            phase_deg = float(rest[2])
        if len(rest) > (3 if kind == "AC" else 2):
            raise NetlistParseError(f"Line {line_number}: unsupported source tokens: {' '.join(rest)}")
    elif len(rest) > 1:
        raise NetlistParseError(f"Line {line_number}: use DC or AC before additional source tokens")
    value = parse_engineering_value(magnitude_token)
    return {
        "name": name,
        "type": name[0].upper(),
        "node_from": normalize_node(n_plus),
        "node_to": normalize_node(n_minus),
        "value_si": value,
        "unit": UNITS[name[0].upper()],
        "source_kind": kind,
        "ac_magnitude": value if kind == "AC" else None,
        "ac_phase_deg": phase_deg if kind == "AC" else None,
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
            f"Line {line_number}: unsupported element {tokens[0]!r}; supported: R, C, L, V, I"
        )
    if designator in {"V", "I"}:
        return _parse_source(tokens, line_number, source_line)
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
    if command == ".PROBE":
        if len(tokens) != 4 or tokens[1].upper() != "AC":
            raise NetlistParseError(
                f"Line {line_number}: expected .PROBE AC V(input) V(output)"
            )
        nodes: list[str] = []
        for token in tokens[2:]:
            match = PROBE_VOLTAGE_RE.fullmatch(token)
            if not match:
                raise NetlistParseError(
                    f"Line {line_number}: expected voltage probes in the form V(node)"
                )
            nodes.append(normalize_node(match.group(1)))
        return {
            "command": "PROBE",
            "analysis": "AC",
            "voltage_nodes": nodes,
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
    nodes = sorted(
        {e["node_from"] for e in elements} | {e["node_to"] for e in elements},
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
