"""Tests for report generation from already-computed circuit artifacts."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "basic_spice"))

from build_circuit_model import build_circuit, circuit_to_dict
from build_constitutive_matrices import build_constitutive_matrices
from build_incidence_matrix import build_incidence_matrices
from build_oriented_graph import build_graph, graph_to_dict
from build_tableau_system import build_tableau_system
from compare_reference import compare_reference
from circuit_identity import circuit_signature
from generate_report import ReportGenerationError, generate_report
from parse_netlist import parse_netlist_text
from solve_ac_sweep import solve_ac_sweep
from solve_linear_system import solve_tableau_system
from stamp_elements import build_element_stamps
from validate_solution import validate_tableau_solution


class GenerateReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.netlist = (
            "* Voltage divider\n"
            "V1 1 0 DC 10\n"
            "R1 1 2 1k\n"
            "R2 2 0 2k\n"
            ".OP\n"
            ".END\n"
        )
        self.parsed = parse_netlist_text(self.netlist, "report_test.cir")
        self.model = build_circuit(self.parsed)
        self.circuit = circuit_to_dict(self.model)
        self.incidence = build_incidence_matrices(self.model)
        self.graph = graph_to_dict(build_graph(self.model), self.model)
        self.stamps = build_element_stamps(self.model, "DC")
        self.constitutive = build_constitutive_matrices(self.model, self.stamps)
        self.system = build_tableau_system(
            self.model,
            self.incidence,
            self.constitutive,
        )
        self.solution = solve_tableau_system(self.system)
        self.validation = validate_tableau_solution(self.system, self.solution)

    def test_tableau_report_includes_validated_results_and_reproducibility(self) -> None:
        report = generate_report(
            self.parsed,
            self.circuit,
            self.incidence,
            self.netlist,
            graph=self.graph,
            stamps=self.stamps,
            constitutive=self.constitutive,
            system=self.system,
            solution=self.solution,
            validation=self.validation,
            input_hashes={"netlist": "a" * 64},
        )
        for expected in (
            "**Estado del reporte: PASS.**",
            "## 2. Netlist original",
            "## 6. Grafo orientado",
            "## 7. Matriz de incidencia",
            "## 8. Ecuaciones constitutivas",
            "## 9. Matrices de análisis",
            "## 11. Resultados",
            "## 12. Validaciones",
            "## 13. Advertencias, limitaciones y elementos no soportados",
            "## 14. Archivos generados y reproducibilidad",
            "V(N2)",
            "a" * 64,
        ):
            self.assertIn(expected, report)

    def test_report_rejects_netlist_that_differs_from_parsed_source(self) -> None:
        with self.assertRaisesRegex(ReportGenerationError, "does not match parsed source"):
            generate_report(
                self.parsed,
                self.circuit,
                self.incidence,
                self.netlist.replace("1k", "2k"),
            )

    def test_report_rejects_mismatched_solution_validation_metadata(self) -> None:
        validation = copy.deepcopy(self.validation)
        validation["analysis"] = "AC"
        with self.assertRaisesRegex(ReportGenerationError, "analysis does not match"):
            generate_report(
                self.parsed,
                self.circuit,
                self.incidence,
                self.netlist,
                system=self.system,
                solution=self.solution,
                validation=validation,
            )

    def test_ac_report_includes_sweep_and_identified_reference_comparison(self) -> None:
        netlist = (
            "V1 1 0 AC 1\n"
            "R1 1 2 1k\n"
            "C1 2 0 1u\n"
            ".AC LIN 3 100 1000\n"
            ".END\n"
        )
        parsed = parse_netlist_text(netlist, "rc_report.cir")
        model = build_circuit(parsed)
        circuit = circuit_to_dict(model)
        incidence = build_incidence_matrices(model)
        sweep = solve_ac_sweep(model, incidence, "1", "2")
        reference = {
            "schema_version": "1.0",
            "simulator": "Approved analytical reference fixture",
            "simulator_version": None,
            "analysis": "AC",
            "frequency_unit": "Hz",
            "circuit_signature": circuit_signature(model),
            "input_node": "1",
            "output_node": "2",
            "results": [
                {
                    "frequency_hz": point["frequency_hz"],
                    "gain_db": point["gain_db"],
                    "phase_deg": point["phase_deg"],
                }
                for point in sweep["points"]
            ],
        }
        comparison = compare_reference(sweep, reference, model)
        report = generate_report(
            parsed,
            circuit,
            incidence,
            netlist,
            sweep=sweep,
            comparison=comparison,
        )
        self.assertIn("**Estado del reporte: PASS.**", report)
        self.assertIn("V(N2) / V(N1)", report)
        self.assertIn("Fuente: `Approved analytical reference fixture`", report)
        self.assertIn(
            "| Frecuencia (Hz) | Vin (V, fasor) | Vout (V, fasor) | H(jω) |",
            report,
        )
        reference["results"][0]["gain_db"] += 1.0
        failed_comparison = compare_reference(
            sweep,
            reference,
            model,
            max_gain_error_db=0.1,
        )
        failed_report = generate_report(
            parsed,
            circuit,
            incidence,
            netlist,
            sweep=sweep,
            comparison=failed_comparison,
        )
        self.assertIn("**Estado del reporte: FAIL.**", failed_report)

    def test_report_without_results_is_marked_not_validated(self) -> None:
        report = generate_report(
            self.parsed,
            self.circuit,
            self.incidence,
            self.netlist,
        )
        self.assertIn("**Estado del reporte: NOT_VALIDATED.**", report)
        self.assertIn("No se proporcionó un resultado calculado.", report)

    def test_netlist_code_fence_preserves_literal_backticks(self) -> None:
        netlist = self.netlist.replace("* Voltage divider", "* ```")
        report = generate_report(
            self.parsed,
            self.circuit,
            self.incidence,
            netlist,
        )
        self.assertIn("````spice\n* ```", report)

    def test_ac_report_rejects_a_sweep_from_another_circuit(self) -> None:
        sweep = solve_ac_sweep(self.model, self.incidence, "1", "2", frequencies=[100.0])
        sweep["circuit_signature"] = "0" * 64
        with self.assertRaisesRegex(ReportGenerationError, "fingerprint"):
            generate_report(
                self.parsed,
                self.circuit,
                self.incidence,
                self.netlist,
                sweep=sweep,
            )


if __name__ == "__main__":
    unittest.main()
