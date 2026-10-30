"""Integration test for the deterministic DC analysis workflow."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "basic_spice"))

from build_circuit_model import build_circuit, circuit_to_dict
from build_constitutive_matrices import build_constitutive_matrices
from build_incidence_matrix import build_incidence_matrices
from build_nodal_system import build_nodal_system
from build_oriented_graph import build_graph, graph_to_dict
from build_tableau_system import build_tableau_system
from parse_netlist import parse_netlist_file
from solve_linear_system import solve_nodal_system, solve_tableau_system
from solve_ac_sweep import solve_ac_sweep
from generate_report import generate_report
from stamp_elements import build_element_stamps
from validate_solution import validate_tableau_solution


class BasicSpiceWorkflowTests(unittest.TestCase):
    def test_current_source_resistive_circuit(self) -> None:
        example = (
            Path(__file__).resolve().parents[2]
            / "tools"
            / "basic_spice"
            / "examples"
            / "current_source_resistive.cir"
        )
        parsed = parse_netlist_file(example)
        circuit = build_circuit(parsed)
        graph = build_graph(circuit)
        self.assertEqual(graph.number_of_edges(), 4)

        incidence = build_incidence_matrices(circuit)
        system = build_nodal_system(circuit, incidence)
        result = solve_nodal_system(system, circuit)
        values = {item["label"]: item["real"] for item in result["node_voltages"]}

        self.assertAlmostEqual(values["V(N1)"], 0.75, delta=1e-10)
        self.assertAlmostEqual(values["V(N2)"], 0.25, delta=1e-10)
        self.assertEqual(result["status"], "PASS")
        print(json.dumps({"status": result["status"], "node_voltages": values}, indent=2))

    def test_ac_constitutive_matrix_workflow(self) -> None:
        example = (
            Path(__file__).resolve().parents[2]
            / "tools"
            / "basic_spice"
            / "examples"
            / "rc_ac.cir"
        )
        circuit = build_circuit(parse_netlist_file(example))
        stamps = build_element_stamps(circuit, "AC", 1000.0)
        matrices = build_constitutive_matrices(circuit, stamps)

        self.assertEqual(matrices["analysis"], "AC")
        self.assertEqual(matrices["frequency_hz"], 1000.0)
        self.assertEqual(matrices["shapes"]["Y"], [3, 3])
        self.assertEqual(matrices["shapes"]["Z"], [3, 3])
        self.assertEqual(matrices["shapes"]["W"], [3])
        self.assertEqual(matrices["row_order"], ["B1", "B2", "B3"])

    def test_voltage_source_tableau_solve_and_validation(self) -> None:
        circuit = build_circuit(
            parse_netlist_file(
                Path(__file__).resolve().parents[2]
                / "tools"
                / "basic_spice"
                / "examples"
                / "voltage_source_divider.cir"
            )
        )
        incidence = build_incidence_matrices(circuit)
        stamps = build_element_stamps(circuit, "DC")
        constitutive = build_constitutive_matrices(circuit, stamps)
        tableau = build_tableau_system(circuit, incidence, constitutive)
        solution = solve_tableau_system(tableau)
        validation = validate_tableau_solution(tableau, solution)

        values = {item["label"]: item["real"] for item in solution["node_voltages"]}
        self.assertAlmostEqual(values["V(N1)"], 10.0, delta=1e-10)
        self.assertAlmostEqual(values["V(N2)"], 20.0 / 3.0, delta=1e-10)
        self.assertEqual(validation["status"], "PASS")

    def test_rc_lowpass_ac_sweep_end_to_end(self) -> None:
        example = (
            Path(__file__).resolve().parents[2]
            / "tools"
            / "basic_spice"
            / "examples"
            / "rc_lowpass_ac_sweep.cir"
        )
        parsed = parse_netlist_file(example)
        circuit = build_circuit(parsed)
        incidence = build_incidence_matrices(circuit)
        result = solve_ac_sweep(circuit, incidence, "1", "2")

        self.assertEqual(result["status"], "PASS")
        self.assertGreater(result["frequency_count"], 1)
        self.assertEqual(result["points"][0]["frequency_hz"], 10.0)
        self.assertEqual(result["points"][-1]["frequency_hz"], 100000.0)
        self.assertTrue(all(point["status"] == "PASS" for point in result["points"]))

        report = generate_report(
            parsed,
            circuit_to_dict(circuit),
            incidence,
            example.read_text(encoding="utf-8"),
            graph=graph_to_dict(build_graph(circuit), circuit),
            sweep=result,
        )
        self.assertIn("**Estado del reporte: PASS.**", report)
        self.assertIn("## 12. Validaciones", report)
        self.assertIn("La herramienta de barrido no exporta corrientes de rama", report)
        self.assertIn("| 10 |", report)


if __name__ == "__main__":
    unittest.main()
