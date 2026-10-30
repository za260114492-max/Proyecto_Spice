"""Unit tests for deterministic AC frequency sweeps and transfer response."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "basic_spice"))

from build_circuit_model import build_circuit
from build_incidence_matrix import build_incidence_matrices
from parse_netlist import parse_netlist_text
from solve_ac_sweep import (
    ACSweepError,
    frequencies_from_directive,
    solve_ac_sweep,
)


class ACFrequencyVectorTests(unittest.TestCase):
    def test_linear_sweep_includes_endpoints_and_requested_point_count(self) -> None:
        directive = {
            "sweep": "LIN",
            "points": 5,
            "f_start_hz": 10.0,
            "f_stop_hz": 90.0,
        }
        frequencies = frequencies_from_directive(directive)
        self.assertEqual(len(frequencies), 5)
        self.assertEqual(frequencies[0], 10.0)
        self.assertEqual(frequencies[-1], 90.0)
        self.assertEqual(frequencies, sorted(frequencies))

    def test_decade_sweep_uses_points_per_decade_and_includes_stop(self) -> None:
        directive = {
            "sweep": "DEC",
            "points": 10,
            "f_start_hz": 10.0,
            "f_stop_hz": 100.0,
        }
        frequencies = frequencies_from_directive(directive)
        self.assertEqual(len(frequencies), 11)
        self.assertEqual(frequencies[0], 10.0)
        self.assertEqual(frequencies[-1], 100.0)
        self.assertTrue(all(a < b for a, b in zip(frequencies, frequencies[1:])))

    def test_one_point_linear_sweep_requires_equal_endpoints(self) -> None:
        with self.assertRaises(ACSweepError):
            frequencies_from_directive({
                "sweep": "LIN",
                "points": 1,
                "f_start_hz": 1.0,
                "f_stop_hz": 10.0,
            })

    def test_invalid_sweep_name_is_rejected(self) -> None:
        with self.assertRaises(ACSweepError):
            frequencies_from_directive({
                "sweep": ["DEC"],
                "points": 10,
                "f_start_hz": 1.0,
                "f_stop_hz": 10.0,
            })


class ACSweepTests(unittest.TestCase):
    def test_rc_lowpass_reports_validated_transfer_per_frequency(self) -> None:
        parsed = parse_netlist_text(
            "V1 1 0 AC 1 0\nR1 1 2 1k\nC1 2 0 1u\n"
            ".AC LIN 3 10 1000\n.END\n"
        )
        circuit = build_circuit(parsed)
        incidence = build_incidence_matrices(circuit)
        result = solve_ac_sweep(circuit, incidence, "1", "2")

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["frequency_count"], 3)
        self.assertEqual(result["transfer_definition"], "V(N2) / V(N1)")
        first = result["points"][0]
        omega_rc = 2 * math.pi * 10.0 * 1e-3
        expected = 1 / complex(1, omega_rc)
        self.assertEqual(first["status"], "PASS")
        self.assertAlmostEqual(first["transfer_function"]["real"], expected.real)
        self.assertAlmostEqual(first["transfer_function"]["imag"], expected.imag)
        self.assertAlmostEqual(first["gain_db"], 20 * math.log10(abs(expected)))
        self.assertTrue(all(point["validation"]["status"] == "PASS" for point in result["points"]))

    def test_probe_directive_supplies_transfer_nodes_for_decade_sweep(self) -> None:
        parsed = parse_netlist_text(
            "V1 IN 0 AC 1\nR1 IN OUT 1k\nC1 OUT 0 1u\n"
            ".PROBE AC V(IN) V(OUT)\n.AC DEC 100 1 1MEG\n.END\n"
        )
        circuit = build_circuit(parsed)
        incidence = build_incidence_matrices(circuit)
        result = solve_ac_sweep(circuit, incidence)

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["input_node"], "IN")
        self.assertEqual(result["output_node"], "OUT")
        self.assertEqual(result["frequency_count"], 601)
        self.assertEqual(result["points"][0]["frequency_hz"], 1.0)
        self.assertEqual(result["points"][-1]["frequency_hz"], 1e6)
        self.assertTrue(all(point["status"] == "PASS" for point in result["points"]))

    def test_probe_directive_requires_both_nodes_when_overriding(self) -> None:
        parsed = parse_netlist_text(
            "V1 1 0 AC 1\nR1 1 2 1k\nC1 2 0 1u\n"
            ".PROBE AC V(1) V(2)\n.AC LIN 2 1 10\n.END\n"
        )
        circuit = build_circuit(parsed)
        with self.assertRaises(ACSweepError):
            solve_ac_sweep(circuit, build_incidence_matrices(circuit), "1")

    def test_explicit_frequency_list_is_supported_without_ac_directive(self) -> None:
        parsed = parse_netlist_text(
            "V1 1 0 AC 1\nR1 1 2 1k\nC1 2 0 1u\n.END\n"
        )
        circuit = build_circuit(parsed)
        result = solve_ac_sweep(
            circuit,
            build_incidence_matrices(circuit),
            "1",
            "2",
            frequencies=[100.0, 1000.0],
        )
        self.assertEqual(result["sweep"], "EXPLICIT")
        self.assertEqual(
            [point["frequency_hz"] for point in result["points"]],
            [100.0, 1000.0],
        )
        self.assertEqual(result["status"], "PASS")

    def test_zero_frequency_is_rejected(self) -> None:
        parsed = parse_netlist_text(
            "V1 1 0 AC 1\nR1 1 2 1k\nC1 2 0 1u\n.END\n"
        )
        circuit = build_circuit(parsed)
        with self.assertRaises(ACSweepError):
            solve_ac_sweep(
                circuit,
                build_incidence_matrices(circuit),
                "1",
                "2",
                frequencies=[0.0],
            )

    def test_failed_frequency_is_reported_without_hiding_other_points(self) -> None:
        parsed = parse_netlist_text(
            "I1 0 1 AC 1m\nR1 2 0 1k\n.END\n"
        )
        circuit = build_circuit(parsed)
        result = solve_ac_sweep(
            circuit,
            build_incidence_matrices(circuit),
            "1",
            "2",
            frequencies=[10.0, 100.0],
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["failed_points"], 2)
        self.assertTrue(all(point["status"] == "FAIL" for point in result["points"]))
        self.assertTrue(all(point["error"] for point in result["points"]))

    def test_ac_directive_and_explicit_frequencies_are_not_combined(self) -> None:
        parsed = parse_netlist_text(
            "V1 1 0 AC 1\nR1 1 0 1k\n.AC LIN 2 1 10\n.END\n"
        )
        circuit = build_circuit(parsed)
        with self.assertRaises(ACSweepError):
            solve_ac_sweep(
                circuit,
                build_incidence_matrices(circuit),
                "1",
                "1",
                frequencies=[10.0],
            )

    def test_input_node_must_exist_and_not_be_ground(self) -> None:
        parsed = parse_netlist_text(
            "V1 1 0 AC 1\nR1 1 0 1k\n.END\n"
        )
        circuit = build_circuit(parsed)
        incidence = build_incidence_matrices(circuit)
        with self.assertRaises(ACSweepError):
            solve_ac_sweep(circuit, incidence, "0", "1", frequencies=[10.0])
        with self.assertRaises(ACSweepError):
            solve_ac_sweep(circuit, incidence, "missing", "1", frequencies=[10.0])


if __name__ == "__main__":
    unittest.main()
