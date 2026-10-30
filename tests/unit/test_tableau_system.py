"""Unit tests for full Tableau assembly and solution validation."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "basic_spice"))

from build_circuit_model import build_circuit
from build_constitutive_matrices import build_constitutive_matrices
from build_incidence_matrix import build_incidence_matrices
from build_tableau_system import TableauAssemblyError, build_tableau_system
from parse_netlist import parse_netlist_text
from solve_linear_system import solve_tableau_system
from stamp_elements import build_element_stamps
from validate_solution import SolutionValidationError, validate_tableau_solution


def build_system(netlist: str, analysis: str = "DC", frequency_hz: float | None = None):
    circuit = build_circuit(parse_netlist_text(netlist))
    incidence = build_incidence_matrices(circuit)
    stamps = build_element_stamps(circuit, analysis, frequency_hz)
    constitutive = build_constitutive_matrices(circuit, stamps)
    tableau = build_tableau_system(circuit, incidence, constitutive)
    return circuit, incidence, constitutive, tableau


class TableauSystemTests(unittest.TestCase):
    def test_builds_expected_tableau_blocks_and_index_map(self) -> None:
        _, _, _, tableau = build_system(
            "V1 1 0 DC 10\nR1 1 2 1k\nR2 2 0 2k\n.END\n"
        )
        self.assertEqual(tableau["shape"], [8, 8])
        self.assertEqual(
            tableau["index_map"],
            {"Vb": [0, 3], "I": [3, 6], "Vn": [6, 8]},
        )
        self.assertEqual(tableau["row_blocks"], {
            "KVL": [0, 3],
            "constitutive": [3, 6],
            "KCL": [6, 8],
        })
        self.assertEqual(tableau["unknown_order"]["X"], ["Vb", "I", "Vn"])
        self.assertEqual(tableau["T"][0][0], {"real": 1.0, "imag": 0.0})
        self.assertEqual(tableau["T"][0][6], {"real": -1.0, "imag": 0.0})

    def test_incidence_matrix_with_wrong_orientation_is_rejected(self) -> None:
        circuit = build_circuit(
            parse_netlist_text("V1 1 0 DC 10\nR1 1 0 1k\n.END\n")
        )
        incidence = build_incidence_matrices(circuit)
        incidence["A_reduced"][0][0] *= -1
        constitutive = build_constitutive_matrices(
            circuit, build_element_stamps(circuit, "DC")
        )
        with self.assertRaises(TableauAssemblyError):
            build_tableau_system(circuit, incidence, constitutive)

    def test_inconsistent_constitutive_row_is_rejected(self) -> None:
        circuit = build_circuit(
            parse_netlist_text("V1 1 0 DC 10\nR1 1 0 1k\n.END\n")
        )
        incidence = build_incidence_matrices(circuit)
        constitutive = build_constitutive_matrices(
            circuit, build_element_stamps(circuit, "DC")
        )
        constitutive["row_equations"][0]["component_name"] = "R-wrong"
        with self.assertRaises(TableauAssemblyError):
            build_tableau_system(circuit, incidence, constitutive)

    def test_solves_voltage_source_circuit_and_passes_all_residuals(self) -> None:
        _, _, _, tableau = build_system(
            "V1 1 0 DC 10\nR1 1 2 1k\nR2 2 0 2k\n.END\n"
        )
        solution = solve_tableau_system(tableau)
        validation = validate_tableau_solution(tableau, solution)

        self.assertEqual(solution["status"], "SOLVED_NOT_VALIDATED")
        self.assertEqual(validation["status"], "PASS")
        self.assertAlmostEqual(solution["node_voltages"][0]["real"], 10.0)
        self.assertAlmostEqual(solution["node_voltages"][1]["real"], 20.0 / 3.0)
        self.assertTrue(all(item["passed"] for item in validation["residuals"].values()))

    def test_ac_tableau_preserves_complex_solution(self) -> None:
        _, _, _, tableau = build_system(
            "I1 0 1 AC 1m\nR1 1 0 1k\nC1 1 0 1u\n.END\n",
            "AC",
            1000.0,
        )
        solution = solve_tableau_system(tableau)
        validation = validate_tableau_solution(tableau, solution)
        self.assertEqual(validation["status"], "PASS")
        self.assertEqual(solution["frequency_hz"], 1000.0)
        self.assertNotEqual(solution["raw"]["Vn"][0]["imag"], 0.0)

    def test_inconsistent_candidate_fails_residual_checks(self) -> None:
        _, _, _, tableau = build_system(
            "V1 1 0 DC 10\nR1 1 2 1k\nR2 2 0 2k\n.END\n"
        )
        solution = solve_tableau_system(tableau)
        invalid_solution = copy.deepcopy(solution)
        invalid_solution["raw"]["X"][0]["real"] += 1.0
        invalid_solution["raw"]["Vb"][0]["real"] += 1.0
        validation = validate_tableau_solution(tableau, invalid_solution)
        self.assertEqual(validation["status"], "FAIL")
        self.assertTrue(validation["errors"])

    def test_solution_metadata_mismatch_is_rejected(self) -> None:
        _, _, _, tableau = build_system(
            "V1 1 0 DC 10\nR1 1 0 1k\n.END\n"
        )
        solution = solve_tableau_system(tableau)
        solution["frequency_hz"] = 60.0
        with self.assertRaises(SolutionValidationError):
            validate_tableau_solution(tableau, solution)

    def test_high_condition_number_warns_when_residuals_pass(self) -> None:
        _, _, _, tableau = build_system(
            "V1 1 0 DC 10\nR1 1 2 1k\nR2 2 0 2k\n.END\n"
        )
        solution = solve_tableau_system(tableau)
        validation = validate_tableau_solution(
            tableau,
            solution,
            condition_warning=1.0,
        )
        self.assertEqual(validation["status"], "WARN")
        self.assertTrue(all(item["passed"] for item in validation["residuals"].values()))

    def test_rank_deficient_tableau_fails_even_with_a_candidate(self) -> None:
        _, _, _, tableau = build_system(
            "V1 1 0 DC 10\nR1 1 2 1k\nR2 2 0 2k\n.END\n"
        )
        solution = solve_tableau_system(tableau)
        singular = copy.deepcopy(tableau)
        for column in range(len(singular["T"])):
            singular["T"][0][column] = {"real": 0.0, "imag": 0.0}
        validation = validate_tableau_solution(singular, solution)
        self.assertEqual(validation["status"], "FAIL")
        self.assertLess(validation["rank"], validation["size"])
        self.assertTrue(any("rank deficient" in error for error in validation["errors"]))


if __name__ == "__main__":
    unittest.main()
