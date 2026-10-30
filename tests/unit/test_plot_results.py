"""Tests for generated gain/phase figures and optional reference overlays."""
from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "basic_spice"))

from build_circuit_model import build_circuit
from build_incidence_matrix import build_incidence_matrices
from circuit_identity import circuit_signature
from compare_reference import compare_reference
from parse_netlist import parse_netlist_text
from plot_results import PlotResultsError, plot_results
from solve_ac_sweep import solve_ac_sweep


class PlotResultsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.circuit = build_circuit(
            parse_netlist_text(
                "V1 1 0 AC 1\nR1 1 2 1k\nC1 2 0 1u\n.END\n",
                "rc_plot_test.cir",
            )
        )
        self.sweep = solve_ac_sweep(
            self.circuit,
            build_incidence_matrices(self.circuit),
            "1",
            "2",
            frequencies=[100.0, 1000.0, 10000.0],
        )

    def _comparison(self):
        reference = {
            "schema_version": "1.0",
            "simulator": "Reference simulator",
            "simulator_version": "1.0",
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
        return compare_reference(self.sweep, reference, self.circuit)

    def test_writes_gain_phase_png_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "bode" / "rc"
            manifest = plot_results(self.sweep, prefix)
            gain = Path(manifest["gain_plot"])
            phase = Path(manifest["phase_plot"])
            manifest_path = prefix.with_name("rc_plot_manifest.json")
            self.assertTrue(gain.is_file())
            self.assertGreater(gain.stat().st_size, 0)
            self.assertTrue(phase.is_file())
            self.assertGreater(phase.stat().st_size, 0)
            self.assertTrue(manifest_path.is_file())
            self.assertEqual(manifest["plotted_frequency_count"], 3)
            self.assertIsNone(manifest["reference_overlay"])

    def test_reference_overlay_uses_comparison_results(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = plot_results(
                self.sweep,
                Path(directory) / "rc",
                self._comparison(),
            )
            self.assertEqual(manifest["reference_overlay"], "Reference simulator")
            self.assertTrue(Path(manifest["gain_plot"]).is_file())
            self.assertTrue(Path(manifest["phase_plot"]).is_file())

    def test_failed_points_are_reported_as_omitted(self) -> None:
        sweep = copy.deepcopy(self.sweep)
        sweep["points"][1]["status"] = "FAIL"
        sweep["points"][1]["gain_db"] = None
        sweep["points"][1]["phase_deg"] = None
        with tempfile.TemporaryDirectory() as directory:
            manifest = plot_results(sweep, Path(directory) / "partial")
        self.assertEqual(manifest["status"], "WARN")
        self.assertEqual(manifest["plotted_frequency_count"], 2)
        self.assertEqual(manifest["omitted_failed_frequencies_hz"], [1000.0])

    def test_rejects_unsorted_sweep(self) -> None:
        sweep = copy.deepcopy(self.sweep)
        sweep["points"][0], sweep["points"][1] = sweep["points"][1], sweep["points"][0]
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(PlotResultsError):
                plot_results(sweep, Path(directory) / "invalid")

    def test_rejects_comparison_for_different_nodes(self) -> None:
        comparison = self._comparison()
        comparison["output_node"] = "1"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(PlotResultsError):
                plot_results(
                    self.sweep,
                    Path(directory) / "invalid",
                    comparison,
                )


if __name__ == "__main__":
    unittest.main()
