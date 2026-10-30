"""Unit tests for deterministic DC and AC component stamps."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "basic_spice"))

from build_circuit_model import build_circuit
from parse_netlist import parse_netlist_text
from stamp_elements import ElementStampError, build_element_stamps


class ElementStampTests(unittest.TestCase):
    def test_dc_stamps_cover_supported_components(self) -> None:
        parsed = parse_netlist_text(
            "R1 1 0 1k\nC1 1 0 1u\nL1 1 0 2m\n"
            "I1 0 1 DC 3m\nV1 1 0 DC 5\n.END\n"
        )
        result = build_element_stamps(build_circuit(parsed), "DC")
        stamps = {stamp["component_name"]: stamp for stamp in result["stamps"]}
        self.assertEqual(result["branch_order"], ["B1", "B2", "B3", "B4", "B5"])
        self.assertEqual(stamps["R1"]["Z"]["real"], -1000.0)
        self.assertEqual(stamps["C1"]["Z"]["real"], 1.0)
        self.assertEqual(stamps["L1"]["Y"]["real"], 1.0)
        self.assertAlmostEqual(stamps["I1"]["W"]["real"], 0.003)
        self.assertEqual(stamps["V1"]["W"]["real"], 5.0)

    def test_ac_stamps_use_phasors_and_angular_frequency(self) -> None:
        parsed = parse_netlist_text(
            "R1 1 0 1k\nC1 1 0 1u\nL1 1 0 2m\n"
            "I1 0 1 AC 2m 90\nV1 1 0 AC 5 0\n.END\n"
        )
        result = build_element_stamps(build_circuit(parsed), "AC", 1000.0)
        stamps = {stamp["component_name"]: stamp for stamp in result["stamps"]}
        omega = 2.0 * math.pi * 1000.0
        self.assertEqual(result["omega_rad_s"], omega)
        self.assertAlmostEqual(stamps["C1"]["Y"]["imag"], omega * 1e-6)
        self.assertAlmostEqual(stamps["L1"]["Z"]["imag"], -omega * 2e-3)
        self.assertAlmostEqual(stamps["I1"]["W"]["real"], 0.0, places=14)
        self.assertAlmostEqual(stamps["I1"]["W"]["imag"], 0.002)
        self.assertAlmostEqual(stamps["V1"]["W"]["real"], 5.0)

    def test_dc_defined_source_is_zero_in_ac_analysis(self) -> None:
        parsed = parse_netlist_text("I1 0 1 DC 2m\nR1 1 0 1k\n.END\n")
        result = build_element_stamps(build_circuit(parsed), "AC", 60.0)
        source = result["stamps"][0]
        self.assertEqual(source["W"], {"real": 0.0, "imag": 0.0})

    def test_ac_requires_frequency_and_dc_rejects_it(self) -> None:
        circuit = build_circuit(parse_netlist_text("R1 1 0 1k\n.END\n"))
        with self.assertRaises(ElementStampError):
            build_element_stamps(circuit, "AC")
        with self.assertRaises(ElementStampError):
            build_element_stamps(circuit, "DC", 60.0)

    def test_invalid_frequency_is_rejected(self) -> None:
        circuit = build_circuit(parse_netlist_text("R1 1 0 1k\n.END\n"))
        for frequency in (-1.0, float("nan"), float("inf")):
            with self.subTest(frequency=frequency), self.assertRaises(ElementStampError):
                build_element_stamps(circuit, "AC", frequency)


if __name__ == "__main__":
    unittest.main()
