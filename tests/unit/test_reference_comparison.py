"""Tests for SPICE/analytical reference alignment and error metrics."""
from __future__ import annotations

import copy
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "basic_spice"))

from build_circuit_model import build_circuit
from build_incidence_matrix import build_incidence_matrices
from circuit_identity import circuit_signature
from compare_reference import (
    ReferenceComparisonError,
    compare_reference,
    write_comparison_csv,
)
from parse_netlist import parse_netlist_text
from solve_ac_sweep import solve_ac_sweep


class ReferenceComparisonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.circuit = build_circuit(
            parse_netlist_text(
                "V1 1 0 AC 1\nR1 1 2 1k\nC1 2 0 1u\n.END\n",
                "rc_reference_test.cir",
            )
        )
        self.sweep = solve_ac_sweep(
            self.circuit,
            build_incidence_matrices(self.circuit),
            "1",
            "2",
            frequencies=[100.0, 1000.0, 10000.0],
        )
        self.reference = {
            "schema_version": "1.0",
            "simulator": "Approved analytical RC solution",
            "simulator_version": None,
            "analysis": "AC",
            "frequency_unit": "Hz",
            "circuit_signature": circuit_signature(self.circuit),
            "input_node": "1",
            "output_node": "2",
            "results": [
                {
                    "frequency_hz": point["frequency_hz"],
                    "gain_db": point["gain_db"],
                    "phase_deg": point["phase_deg"],
                }
                for point in self.sweep["points"]
            ],
        }

    def test_exact_reference_passes_and_reports_quantitative_errors(self) -> None:
        result = compare_reference(self.sweep, self.reference, self.circuit)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["passed_points"], 3)
        self.assertEqual(result["failed_points"], 0)
        for row in result["rows"]:
            self.assertAlmostEqual(row["gain_absolute_error_db"], 0.0)
            self.assertAlmostEqual(row["gain_relative_error"], 0.0)
            self.assertAlmostEqual(row["phase_error_deg"], 0.0)

    def test_phase_error_wraps_across_plus_minus_180(self) -> None:
        reference = copy.deepcopy(self.reference)
        reference["results"][0]["phase_deg"] += 360.0
        result = compare_reference(self.sweep, reference, self.circuit)
        self.assertAlmostEqual(result["rows"][0]["phase_error_deg"], 0.0)

    def test_frequency_alignment_respects_relative_tolerance(self) -> None:
        reference = copy.deepcopy(self.reference)
        reference["results"][1]["frequency_hz"] *= 1.0 + 5e-10
        result = compare_reference(self.sweep, reference, self.circuit)
        self.assertEqual(result["status"], "PASS")
        self.assertNotEqual(result["rows"][1]["frequency_error_hz"], 0.0)

    def test_out_of_tolerance_comparison_fails(self) -> None:
        reference = copy.deepcopy(self.reference)
        reference["results"][1]["gain_db"] += 1.0
        result = compare_reference(
            self.sweep,
            reference,
            self.circuit,
            max_gain_error_db=0.1,
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["failed_points"], 1)

    def test_reference_frequency_mismatch_is_rejected_without_interpolation(self) -> None:
        reference = copy.deepcopy(self.reference)
        reference["results"][1]["frequency_hz"] = 1100.0
        with self.assertRaises(ReferenceComparisonError):
            compare_reference(self.sweep, reference, self.circuit)

    def test_wrong_circuit_signature_is_rejected(self) -> None:
        reference = copy.deepcopy(self.reference)
        reference["circuit_signature"] = "0" * 64
        with self.assertRaises(ReferenceComparisonError):
            compare_reference(self.sweep, reference, self.circuit)

    def test_wrong_sweep_circuit_signature_is_rejected(self) -> None:
        sweep = copy.deepcopy(self.sweep)
        sweep["circuit_signature"] = "1" * 64
        with self.assertRaises(ReferenceComparisonError):
            compare_reference(sweep, self.reference, self.circuit)

    def test_reference_nodes_must_match(self) -> None:
        reference = copy.deepcopy(self.reference)
        reference["output_node"] = "1"
        with self.assertRaises(ReferenceComparisonError):
            compare_reference(self.sweep, reference, self.circuit)

    def test_csv_export_contains_comparison_fields(self) -> None:
        result = compare_reference(self.sweep, self.reference, self.circuit)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "comparison.csv"
            write_comparison_csv(path, result)
            with path.open(encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source))
            self.assertEqual(len(rows), 3)
            self.assertIn("gain_absolute_error_db", rows[0])
            self.assertIn("agent_gain_linear", rows[0])
            self.assertIn("reference_gain_linear", rows[0])
            self.assertIn("phase_error_deg", rows[0])


if __name__ == "__main__":
    unittest.main()
