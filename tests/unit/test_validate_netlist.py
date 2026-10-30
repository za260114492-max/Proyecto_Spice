"""Unit tests for semantic and topology validation."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "basic_spice"))

from parse_netlist import parse_netlist_text
from validate_netlist import validate_netlist


class ValidateNetlistTests(unittest.TestCase):
    def test_valid_netlist_passes(self) -> None:
        parsed = parse_netlist_text("I1 0 1 DC 1m\nR1 1 0 1k\n.OP\n.END\n")
        result = validate_netlist(parsed)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["errors"], [])

    def test_ac_voltage_probe_directive_passes(self) -> None:
        parsed = parse_netlist_text(
            "V1 IN 0 AC 1\nR1 IN OUT 1k\nC1 OUT 0 1u\n"
            ".PROBE AC V(IN) V(OUT)\n.AC DEC 100 1 1MEG\n.END\n"
        )
        result = validate_netlist(parsed)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["errors"], [])
        probe = next(d for d in parsed["directives"] if d["command"] == "PROBE")
        self.assertEqual(probe["voltage_nodes"], ["IN", "OUT"])

    def test_unknown_probe_node_fails(self) -> None:
        parsed = parse_netlist_text(
            "V1 IN 0 AC 1\nR1 IN OUT 1k\nC1 OUT 0 1u\n"
            ".PROBE AC V(IN) V(MISSING)\n.AC LIN 2 1 10\n.END\n"
        )
        result = validate_netlist(parsed)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("UNKNOWN_PROBE_NODE", {error["code"] for error in result["errors"]})

    def test_malformed_probe_directive_is_rejected(self) -> None:
        from parse_netlist import NetlistParseError

        with self.assertRaises(NetlistParseError):
            parse_netlist_text("R1 1 0 1k\n.PROBE AC V(1)\n.END\n")

    def test_missing_ground_fails(self) -> None:
        parsed = parse_netlist_text("R1 1 2 1k\n.END\n")
        result = validate_netlist(parsed)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("MISSING_GROUND", {error["code"] for error in result["errors"]})

    def test_disconnected_subcircuit_fails(self) -> None:
        parsed = parse_netlist_text("R1 1 0 1k\nR2 2 3 2k\n.END\n")
        result = validate_netlist(parsed)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("DISCONNECTED_NODE", {error["code"] for error in result["errors"]})

    def test_conflicting_analysis_directives_fail(self) -> None:
        parsed = parse_netlist_text("R1 1 0 1k\n.OP\n.AC LIN 2 1 10\n.END\n")
        result = validate_netlist(parsed)
        self.assertIn("CONFLICTING_ANALYSES", {error["code"] for error in result["errors"]})

    def test_duplicate_names_in_malformed_parsed_data_fail(self) -> None:
        parsed = parse_netlist_text("R1 1 0 1k\nR2 1 0 2k\n.END\n")
        parsed["elements"][1]["name"] = "r1"
        result = validate_netlist(parsed)
        self.assertIn("DUPLICATE_COMPONENT", {error["code"] for error in result["errors"]})

    def test_self_connected_branch_fails(self) -> None:
        parsed = parse_netlist_text("R1 1 1 1k\nR2 1 0 1k\n.END\n")
        result = validate_netlist(parsed)
        self.assertIn("SELF_CONNECTED_BRANCH", {error["code"] for error in result["errors"]})

    def test_invalid_ac_directive_fails(self) -> None:
        parsed = parse_netlist_text("R1 1 0 1k\n.AC LIN 2 1 10\n.END\n")
        parsed["directives"][0]["f_start_hz"] = float("nan")
        result = validate_netlist(parsed)
        self.assertIn("INVALID_AC_DIRECTIVE", {error["code"] for error in result["errors"]})

    def test_malformed_element_type_is_reported_not_raised(self) -> None:
        parsed = parse_netlist_text("R1 1 0 1k\n.END\n")
        parsed["elements"][0]["type"] = ["R"]
        result = validate_netlist(parsed)
        self.assertIn("UNSUPPORTED_ELEMENT", {error["code"] for error in result["errors"]})

    def test_missing_end_is_warning_not_failure(self) -> None:
        parsed = parse_netlist_text("R1 1 0 1k\n")
        result = validate_netlist(parsed)
        self.assertEqual(result["status"], "WARN")
        self.assertIn("MISSING_END", {warning["code"] for warning in result["warnings"]})
        self.assertEqual(len(result["warnings"]), 1)


if __name__ == "__main__":
    unittest.main()
