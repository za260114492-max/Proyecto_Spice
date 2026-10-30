"""Unit tests for traceable Tableau constitutive matrix assembly."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "basic_spice"))

from build_circuit_model import build_circuit
from build_constitutive_matrices import (
    ConstitutiveMatrixError,
    build_constitutive_matrices,
)
from parse_netlist import parse_netlist_text
from stamp_elements import build_element_stamps


class ConstitutiveMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        parsed = parse_netlist_text(
            "R1 1 0 1k\nC1 1 2 1u\nL1 2 0 2m\n"
            "I1 0 1 DC 3m\nV1 2 0 DC 5\n.END\n"
        )
        self.circuit = build_circuit(parsed)
        self.stamps = build_element_stamps(self.circuit, "DC")

    def test_builds_diagonal_y_z_and_w_with_ordered_traceability(self) -> None:
        result = build_constitutive_matrices(self.circuit, self.stamps)

        self.assertEqual(result["equation_convention"], "Y @ Vb + Z @ I = W")
        self.assertEqual(result["row_order"], ["B1", "B2", "B3", "B4", "B5"])
        self.assertEqual(result["shapes"], {"Y": [5, 5], "Z": [5, 5], "W": [5]})
        self.assertEqual(
            [row["component_name"] for row in result["row_equations"]],
            ["R1", "C1", "L1", "I1", "V1"],
        )
        y_diagonal = [result["Y"][i][i]["real"] for i in range(5)]
        z_diagonal = [result["Z"][i][i]["real"] for i in range(5)]
        self.assertEqual(y_diagonal, [1.0, 0.0, 1.0, 0.0, 1.0])
        self.assertEqual(z_diagonal, [-1000.0, 1.0, 0.0, 1.0, 0.0])
        self.assertEqual(
            [result["W"][i]["real"] for i in range(5)],
            [0.0, 0.0, 0.0, 0.003, 5.0],
        )
        for matrix_name in ("Y", "Z"):
            matrix = result[matrix_name]
            for row in range(5):
                for column in range(5):
                    if row != column:
                        self.assertEqual(matrix[row][column], {"real": 0.0, "imag": 0.0})

    def test_ac_matrices_preserve_complex_entries_and_frequency(self) -> None:
        parsed = parse_netlist_text("R1 1 0 1k\nC1 1 0 1u\n.END\n")
        circuit = build_circuit(parsed)
        stamps = build_element_stamps(circuit, "AC", 1000.0)
        result = build_constitutive_matrices(circuit, stamps)

        self.assertEqual(result["analysis"], "AC")
        self.assertEqual(result["frequency_hz"], 1000.0)
        self.assertAlmostEqual(result["Y"][1][1]["imag"], 2 * 3.141592653589793 * 1000 * 1e-6)
        self.assertEqual(result["Z"][1][1], {"real": -1.0, "imag": 0.0})
        self.assertEqual(result["row_units"]["Y"], ["dimensionless", "siemens"])

    def test_branch_order_mismatch_is_rejected(self) -> None:
        stamps = copy.deepcopy(self.stamps)
        stamps["branch_order"].reverse()
        with self.assertRaises(ConstitutiveMatrixError):
            build_constitutive_matrices(self.circuit, stamps)

    def test_component_traceability_mismatch_is_rejected(self) -> None:
        stamps = copy.deepcopy(self.stamps)
        stamps["stamps"][0]["source_line"] = "R1 1 0 2k"
        with self.assertRaises(ConstitutiveMatrixError):
            build_constitutive_matrices(self.circuit, stamps)

    def test_nonfinite_stamp_value_is_rejected(self) -> None:
        stamps = copy.deepcopy(self.stamps)
        stamps["stamps"][0]["Y"]["real"] = float("nan")
        with self.assertRaises(ConstitutiveMatrixError):
            build_constitutive_matrices(self.circuit, stamps)

    def test_stamp_count_mismatch_is_rejected(self) -> None:
        stamps = copy.deepcopy(self.stamps)
        stamps["stamps"].pop()
        with self.assertRaises(ConstitutiveMatrixError):
            build_constitutive_matrices(self.circuit, stamps)

    def test_inconsistent_angular_frequency_is_rejected(self) -> None:
        parsed = parse_netlist_text("R1 1 0 1k\n.END\n")
        circuit = build_circuit(parsed)
        stamps = build_element_stamps(circuit, "AC", 1000.0)
        stamps["omega_rad_s"] = 1.0
        with self.assertRaises(ConstitutiveMatrixError):
            build_constitutive_matrices(circuit, stamps)

    def test_missing_row_units_are_rejected(self) -> None:
        stamps = copy.deepcopy(self.stamps)
        del stamps["stamps"][0]["Y_unit"]
        with self.assertRaises(ConstitutiveMatrixError):
            build_constitutive_matrices(self.circuit, stamps)

    def test_invalid_analysis_type_is_reported_as_contract_error(self) -> None:
        stamps = copy.deepcopy(self.stamps)
        stamps["analysis"] = ["DC"]
        with self.assertRaises(ConstitutiveMatrixError):
            build_constitutive_matrices(self.circuit, stamps)


if __name__ == "__main__":
    unittest.main()
