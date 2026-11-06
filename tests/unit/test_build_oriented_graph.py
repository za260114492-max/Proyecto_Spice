"""Tests for required oriented graph artifacts."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "basic_spice"))

from build_circuit_model import build_circuit, circuit_to_dict
from build_oriented_graph import build_graph, draw_graph, graph_to_dict, main
from parse_netlist import parse_netlist_text


class BuildOrientedGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.circuit = build_circuit(
            parse_netlist_text(
                "V1 1 0 AC 1\nR1 1 2 1k\nR2 2 0 2k\n.END\n",
                "oriented_graph_test.cir",
            )
        )

    def test_graph_json_preserves_branch_direction_and_parallel_edges(self) -> None:
        circuit = build_circuit(
            parse_netlist_text(
                "V1 1 0 AC 1\nR1 1 2 1k\nR2 1 2 2k\nR3 2 0 3k\n.END\n",
                "parallel_graph_test.cir",
            )
        )
        graph = build_graph(circuit)
        artifact = graph_to_dict(graph, circuit)

        self.assertTrue(artifact["is_connected"])
        self.assertEqual(len(artifact["edges"]), len(circuit.branches))
        parallel_edges = [
            edge
            for edge in artifact["edges"]
            if edge["node_from"] == "1" and edge["node_to"] == "2"
        ]
        self.assertEqual(len(parallel_edges), 2)

    def test_graph_image_is_generated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "graph.png"
            draw_graph(build_graph(self.circuit), image)
            self.assertTrue(image.is_file())
            self.assertGreater(image.stat().st_size, 0)

    def test_cli_writes_topology_and_required_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            circuit_path = root / "circuit.json"
            topology_path = root / "topology.json"
            image_path = root / "graph.png"
            circuit_path.write_text(
                json.dumps(circuit_to_dict(self.circuit)),
                encoding="utf-8",
            )
            with patch(
                "sys.argv",
                [
                    "build_oriented_graph.py",
                    str(circuit_path),
                    "-o",
                    str(topology_path),
                    "--image",
                    str(image_path),
                ],
            ), contextlib.redirect_stdout(io.StringIO()):
                main()

            topology = json.loads(topology_path.read_text(encoding="utf-8"))
            self.assertTrue(topology["is_connected"])
            self.assertEqual(len(topology["edges"]), len(self.circuit.branches))
            self.assertTrue(image_path.is_file())
            self.assertGreater(image_path.stat().st_size, 0)

    def test_cli_requires_graph_image(self) -> None:
        with patch(
            "sys.argv",
            ["build_oriented_graph.py", "circuit.json", "-o", "topology.json"],
        ), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                main()
        self.assertEqual(error.exception.code, 2)

    def test_cli_rejects_unsupported_image_extension(self) -> None:
        with patch(
            "sys.argv",
            [
                "build_oriented_graph.py",
                "circuit.json",
                "-o",
                "topology.json",
                "--image",
                "graph.jpg",
            ],
        ), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                main()
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
