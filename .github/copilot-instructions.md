# Workspace instructions

## Project map and source of truth

This is an educational SPICE-like circuit-analysis project. The organized implementation is in `tools/basic_spice/`; the ten discoverable domain skills are in `.github/skills/`; the workspace agent is in `.github/agents/Spice_Expert.agent.md`. Consultable academic references are in `docs/reference/`; original PDF/DOCX files are in `docs/reference/originals/`; plans are in `docs/plans/`; and the original ZIPs are in `docs/source-archives/`.

Use `docs/reference/README.md` as the documentation index and precedence guide. `ESPECIFICACION_UNIDAD_1.md` is the canonical academic requirements document and `GUIA_METODOLOGICA.md` is the canonical full methodology conversion. Their PDF/DOCX originals are preserved for provenance and visual references. Plans describe intended future work and are not proof that a script or feature exists. Inspect current source files before claiming availability.

## Current implementation

The fifteen available Python tools are:

1. `tools/basic_spice/parse_netlist.py`
2. `tools/basic_spice/validate_netlist.py`
3. `tools/basic_spice/build_circuit_model.py`
4. `tools/basic_spice/build_oriented_graph.py`
5. `tools/basic_spice/build_incidence_matrix.py`
6. `tools/basic_spice/stamp_elements.py`
7. `tools/basic_spice/build_constitutive_matrices.py`
8. `tools/basic_spice/build_tableau_system.py`
9. `tools/basic_spice/build_nodal_system.py`
10. `tools/basic_spice/solve_linear_system.py`
11. `tools/basic_spice/validate_solution.py`
12. `tools/basic_spice/solve_ac_sweep.py`
13. `tools/basic_spice/compare_reference.py`
14. `tools/basic_spice/generate_report.py`
15. `tools/basic_spice/plot_results.py`

Tests are organized under `tests/unit/` (one module per tool) and `tests/integration/` (end-to-end workflows). Dependencies are listed in `tools/basic_spice/requirements.txt`. From the workspace root:

```powershell
python -m pip install -r tools/basic_spice/requirements.txt
python -m unittest discover -s tests -v
```

The full CLI example is documented in `tools/basic_spice/README.md`. Store generated files under `artifacts/`; do not overwrite user inputs.

`validate_netlist.py` checks semantic/topological rules in the parsed JSON; syntax errors are still raised by the parser. `stamp_elements.py` emits traceable per-branch equations, `build_constitutive_matrices.py` assembles `Y`/`Z`/`W`, and `build_tableau_system.py` creates the full `T @ X = W_prime` system. `solve_linear_system.py --tableau` solves it; `validate_solution.py` is the independent acceptance gate. `solve_ac_sweep.py` executes `.AC LIN/DEC` or explicit-frequency sweeps and records per-point transfer and validation. `compare_reference.py` aligns the circuit fingerprint, nodes, and frequencies before comparison; `plot_results.py` produces gain/phase figures with optional reference overlays. `generate_report.py` consumes the source netlist and outputs from the completed stages to create an auditable Markdown report; it never recalculates results and marks missing artifacts. AC reference schema: `docs/reference/AC_REFERENCE_DATA_SCHEMA.md`. Do not claim unexecuted stages ran.

## Responsibility and error handling

The agent interprets and explains; skills define domain methodology; Python tools are the computational source of truth; tests establish correctness. Do not invent matrices or numerical results. Stop at the first blocking error, report the stage and tool evidence, and do not present partial output as a validated solution.

## Shared electrical conventions

- Ground aliases `0` and `GND` normalize to `0`.
- Node ordering is deterministic: numeric nodes ascending, followed by alphanumeric nodes lexicographically.
- Branch orientation is from the first node in the netlist line to the second; branch order follows netlist order.
- Incidence entries are `+1` where a branch leaves a node, `-1` where it enters, and `0` otherwise.
- Preserve original values and lines alongside SI-normalized values. `m` means milli and `meg` means mega; follow the parser's implemented prefix behavior.
- Use the `engineering-units-and-conventions` skill as the shared authority. Specialized skills must not redefine units, ordering, signs, or tolerances.
- Use a numerical solver such as `numpy.linalg.solve`, not an explicit matrix inverse. A solver result alone does not establish electrical or numerical validity.
