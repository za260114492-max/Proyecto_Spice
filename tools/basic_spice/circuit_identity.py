"""Stable identity helpers for matching results to normalized circuit data."""
from __future__ import annotations

import hashlib
import json

from build_circuit_model import Circuit


def circuit_signature(circuit: Circuit) -> str:
    """Hash normalized branch definitions and orientation, excluding the filename."""
    components = [
        {
            "name": branch.component_name.upper(),
            "type": branch.element_type,
            "node_from": branch.node_from,
            "node_to": branch.node_to,
            "value_si": branch.value_si,
            "unit": branch.unit,
            "source_kind": branch.source_kind,
            "ac_magnitude": branch.ac_magnitude,
            "ac_phase_deg": branch.ac_phase_deg,
        }
        for branch in circuit.branches
    ]
    payload = {
        "reference_node": circuit.reference_node,
        "components": components,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
