---
name: basic-spice-educational-agent-methodology
description: Guides GitHub Copilot when designing, implementing, reviewing, testing, or documenting an educational SPICE-like custom agent that converts linear circuit netlists into deterministic graph, matrix, solver, validation, and explainable-report workflows. Activate for work involving the Basic SPICE Educational Agent, netlist parsing, circuit graphs, incidence matrices, nodal analysis, Tableau formulation, AC analysis, solver verification, or the repository architecture supporting these capabilities.
---

# Basic SPICE Educational Agent Methodology

## Objective

Develop an educational SPICE-like agent that interprets user requests, coordinates reusable knowledge modules, executes deterministic Python tools, and explains every result from the original netlist through the mathematical solution and validation evidence.

The agent is an orchestrator and explainer. Python tools are the computational source of truth.

## Core Principle

Use this separation of responsibilities:

- **Agent:** interpret the request, select the workflow, invoke tools, and explain results.
- **Skills:** preserve domain theory, shared conventions, decision rules, and methodology.
- **Python tools:** parse, normalize, model, assemble, solve, validate, compare, and export deterministically.
- **Tests:** establish mathematical and software correctness.
- **Reports:** expose inputs, equations, matrices, results, warnings, and traceability.

Never invent matrices, numerical results, or validation status in natural-language output. Do not present a computed solution unless the deterministic workflow has completed and the solution has passed the configured checks.

## Activation Conditions

Use this skill when the request involves one or more of the following:

- Creating or modifying the Basic SPICE Educational Agent.
- Planning implementation work for the SPICE-like educational repository.
- Interpreting `.cir`, `.sp`, or `.net` files.
- Defining nodes, branches, component orientation, or circuit topology.
- Creating a directed graph or an incidence matrix.
- Implementing classical nodal, Tableau, or AC-frequency analysis.
- Defining deterministic Python interfaces for circuit calculations.
- Reviewing skills, prompts, tests, reports, or acceptance criteria.
- Diagnosing singular systems, floating nodes, inconsistent sources, or unsupported elements.
- Producing an auditable explanation of an already computed solution.

Do not activate this skill for production signoff, semiconductor-device modeling, general-purpose transient simulation, transmission-line/RF modeling, or complete compatibility with commercial SPICE dialects.

## MVP Scope

The initial implementation supports:

- Linear lumped circuits.
- Resistors and conductances.
- Capacitors and inductors.
- Independent sources.
- Classical nodal analysis for compatible circuits.
- Single-frequency AC analysis and frequency sweeps.
- Tableau formulation for educational use.
- NumPy-based linear-system solution.
- Directed-graph visualization.
- KCL, KVL, constitutive-equation, and global-residual validation.

The initial implementation excludes:

- Complete semiconductor models.
- Newton-Raphson nonlinear analysis.
- General-purpose transient analysis.
- Distributed parasitics, transmission lines, and advanced RF models.
- Complete compatibility with all SPICE dialects.
- Replacement of commercial simulators or production-design certification.

Expand scope only after the existing core has automated tests, approved documentation, and reference results.

## Required Workflow

Follow this order unless a narrowly scoped user request requires only one stage:

1. Read the netlist without modifying it.
2. Validate syntax, supported elements, unique identifiers, and ground definition.
3. Normalize engineering values and physical units.
4. Create the internal circuit model.
5. Enumerate nodes and branches deterministically.
6. Build the directed circuit graph.
7. Build the complete and reduced incidence matrices.
8. Select a compatible formulation.
9. Assemble matrices and right-hand-side vectors.
10. Solve the linear system with a numerical solver.
11. Recover node and branch physical variables.
12. Validate topology, linear residuals, KCL, KVL, and constitutive equations.
13. Compare against an approved analytical or simulator reference when provided.
14. Generate a traceable Markdown report and requested artifacts.

Stop at the first blocking error. Report the affected stage, evidence, likely cause, and corrective action.

## Shared Data Contract

Every component record must preserve at least:

```yaml
name: R1
type: resistor
node_from: "1"
node_to: "2"
value_si: 1000.0
unit: ohm
branch_id: B2
source_line: "R1 1 2 1k"
```

Requirements:

- `name` is unique.
- `type` uses the repository's normalized vocabulary.
- `node_from` and `node_to` define the approved branch orientation.
- `value_si` contains the SI-converted numeric value.
- `unit` preserves the physical dimension.
- `branch_id` follows deterministic branch ordering.
- `source_line` retains traceability to the original netlist.

Do not mix normalized numeric values with the original textual representation.

## Shared Conventions

Treat `engineering-units-and-conventions` as the authoritative repository skill for:

- Engineering prefixes and unit conversion.
- Ground-node representation.
- Voltage polarity and current direction.
- Branch orientation.
- Node and branch ordering.
- Matrix sign conventions.
- Complex-number formatting.
- Numerical tolerances.
- Output precision.

A specialized skill may reference these conventions but must not redefine them locally.

## Knowledge Modules

Use the most specific supporting skill available:

1. `spice-netlist-fundamentals`: accepted grammar, comments, directives, identifiers, nodes, prefixes, valid and invalid examples.
2. `circuit-graph-theory`: vertices, directed branches, orientation, numbering, connectivity, incidence versus adjacency, and parallel branches.
3. `incidence-matrix-method`: complete and reduced incidence matrices, sign convention, labels, and structural checks.
4. `component-constitutive-models`: element equations and approved matrix stamps.
5. `classical-nodal-analysis`: compatibility, assembly, node-voltage solution, and branch-variable recovery.
6. `tableau-formulation`: KCL, branch-voltage/KVL relations, constitutive equations, and assembly of `Y`, `Z`, `W`, `T`, and `W_prime`.
7. `ac-frequency-analysis`: phasors, `s = j*omega`, single frequency, sweeps, magnitude, phase, dB, and handling of zero frequency.
8. `engineering-units-and-conventions`: repository-wide conventions.
9. `solver-validation`: residuals, singularity, conditioning, diagnostics, acceptance, and rejection.
10. `explainable-circuit-reporting`: auditable Markdown presentation.

## Deterministic Tools

Map work to these interfaces when they exist in the repository:

| Tool | Responsibility |
|---|---|
| `parse_netlist.py` | Parse `.cir`, `.sp`, and `.net` source into structured data. |
| `validate_netlist.py` | Detect syntax errors, duplicates, missing ground, and unsupported elements. |
| `build_circuit_model.py` | Create circuit, node, branch, element, source, and analysis-command objects. |
| `build_oriented_graph.py` | Build topology, connectivity, and graph visualization. |
| `build_incidence_matrix.py` | Produce labeled complete and reduced incidence matrices. |
| `stamp_elements.py` | Apply approved element stamps. |
| `build_nodal_system.py` | Check nodal compatibility and assemble the nodal system. |
| `build_constitutive_matrices.py` | Construct `Y`, `Z`, and `W` with row-level traceability. |
| `build_tableau_system.py` | Construct `T`, `W_prime`, and the index map for the unknown vector. |
| `solve_linear_system.py` | Solve with NumPy and calculate numerical metrics. |
| `solve_ac_sweep.py` | Execute single-frequency and swept-frequency analyses. |
| `validate_solution.py` | Verify KCL, KVL, constitutive equations, and global residuals. |
| `compare_reference.py` | Compare with approved analytical or simulator reference data. |
| `generate_report.py` | Generate the reproducible Markdown report. |
| `plot_results.py` | Plot topology, magnitude, phase, and comparisons. |

Supporting utilities may include:

- `engineering_values.py`
- `matrix_formatter.py`
- `diagnose_singularity.py`
- `export_results.py`

If an expected tool is unavailable, state that the relevant stage cannot be computed deterministically. Do not replace the missing computation with an LLM-generated result.

## Tool Interface Standard

Prefer command-line interfaces and importable functions. A representative pattern is:

```bash
python -m src.build_incidence_matrix \
  --circuit artifacts/circuit.json \
  --output artifacts/incidence.json \
  --markdown artifacts/incidence.md
```

Each tool must:

- Return a nonzero exit code on failure.
- Produce actionable error messages.
- Record the schema version and execution parameters.
- Retain traceability to the original netlist.
- Produce deterministic output for identical inputs and environment.

## Implementation Rules

- Use Python 3 and NumPy as the numerical foundation.
- Use NetworkX only for graph representation or graph analysis, not as a substitute for electrical formulation.
- Represent domain objects with dataclasses or equivalent typed models.
- Use small functions with type hints and docstrings.
- Avoid mutable global state.
- Maintain deterministic node and branch ordering.
- Define domain-specific exceptions.
- Use `numpy.linalg.solve` or an equivalent solver instead of explicitly computing a matrix inverse.
- Preserve units across all stages.
- Keep calculation, validation, reporting, and visualization as separable concerns.

## Formulation Selection

Before assembly, identify the compatible formulation and explain the decision.

### Classical nodal analysis

Use when the circuit belongs to the subset supported by the current nodal implementation. Assemble the nodal system, solve node voltages, and recover branch variables.

Do not silently force unsupported voltage-source or special-branch cases into classical nodal form.

### Tableau formulation

Use when the educational objective requires explicit branch voltages and currents, or when assembling the full set of KCL, branch-voltage, and constitutive equations.

The Tableau workflow must expose:

- Unknown-vector ordering.
- Equation-block ordering.
- Mapping from each matrix row to its physical equation.
- Construction of `Y`, `Z`, `W`, `T`, and `W_prime`.

### AC analysis

For AC work:

- Use phasor-domain element models.
- Derive angular frequency from the requested frequency.
- Preserve complex values internally.
- Report magnitude, phase, and dB only where requested and mathematically valid.
- Explicitly handle the element behavior and formulation at zero frequency.

## Validation Requirements

A result is acceptable only if the applicable checks pass under configured absolute and relative tolerances.

Evaluate:

- Linear-system residual: `norm(M @ x - b)`.
- KCL residual: `norm(A @ I)`.
- Branch/node-voltage relation: `norm(Vb - A.T @ Vn)`.
- Constitutive residual: `norm(Y @ Vb + Z @ I - W)`.
- Tableau residual: `norm(T @ X - W_prime)`.
- Absolute and relative error against approved reference data.

Also inspect:

- Matrix shape and rank.
- Floating nodes or disconnected subcircuits.
- Duplicate or contradictory definitions.
- Ill-conditioning.
- Incompatible ideal sources.
- Unsupported components or directives.

Do not label a value as validated simply because a solver returned an array.

## Error Handling

Use clear domain-oriented diagnostics. At minimum distinguish:

- Invalid netlist syntax.
- Duplicate component identifier.
- Missing ground reference.
- Unsupported element or directive.
- Floating node or disconnected topology.
- Singular matrix.
- Ill-conditioned system.
- Incompatible source constraints.
- Missing artifact or schema mismatch.
- Solver failure.
- Validation failure.
- Reference comparison failure.

An error response must include:

1. Stage where the failure occurred.
2. Relevant component, node, branch, source line, or matrix.
3. Evidence detected by the tool.
4. Corrective action the user can take.

## Guardrails

- Never modify the original netlist without explicitly identifying the proposed change.
- Never infer a ground node that the input does not define.
- Never continue after detecting an unsupported component in the active analysis path.
- Never hide singularity, rank deficiency, or poor conditioning.
- Never report more numerical precision than tolerances and conditioning support.
- Never use inconsistent formulas across skills and tools.
- Never compare results with a SPICE reference without recording the reference simulator, version if available, netlist, and analysis conditions.
- Never let prose override deterministic tool output.
- Never claim validation when required checks were skipped or failed.

## Reporting Contract

A complete Markdown report should contain:

1. Analysis request and source netlist.
2. Supported scope and assumptions.
3. Parsed components with original lines and normalized values.
4. Node and branch ordering.
5. Directed graph or graph artifact reference.
6. Complete and reduced incidence matrices.
7. Selected formulation and compatibility decision.
8. Matrix and vector definitions with labels and units.
9. Solver information and numerical diagnostics.
10. Node voltages and branch variables.
11. Validation metrics with tolerances and pass/fail status.
12. Reference comparison when available.
13. Warnings, limitations, unsupported features, and reproducibility metadata.

Explain calculated results only after reading their generated artifacts. Do not recalculate them in prose.

## Repository Structure

Prefer this layout:

```text
.github/
├── agents/basic-spice-agent.agent.md
├── copilot-instructions.md
├── prompts/*.prompt.md
└── skills/<skill-name>/SKILL.md
src/
├── domain/
├── parsers/
├── graph/
├── formulations/
├── solvers/
├── validation/
└── reporting/
tests/
├── unit/
├── integration/
└── cases/
examples/
artifacts/
docs/
pyproject.toml
README.md
```

Standard artifacts:

- `circuit.json`: components, nodes, branches, units, and source traceability.
- `topology.json`: nodes, branches, orientation, and connectivity.
- `matrices.npz`: matrices plus metadata.
- `results.csv`: frequency, variables, and units.
- `report.md`: explanation, matrices, results, and validation.
- `graph.svg`: labeled directed graph.

## Testing Strategy

Develop validation together with implementation.

### Minimum topology cases

- Resistor connected to ground.
- Series network.
- Parallel network.
- Three-node circuit.
- Parallel branches.
- Disconnected subcircuit.

### Minimum nodal cases

- Resistive divider.
- Three-node resistive network.
- Independent current source.
- RC, RL, and RLC cases within the implemented scope.

### Minimum Tableau cases

- Independent voltage and current sources.
- Capacitor and inductor.
- Multiple sources.
- Approved educational reference example.

### Negative cases

- Floating node.
- Singular matrix.
- Missing ground.
- Duplicate identifiers.
- Invalid syntax.
- Unsupported element type.

A traceable test case should use a structure such as:

```text
tests/cases/rc_lowpass/
├── circuit.cir
├── expected_topology.json
├── expected_matrices.npz
├── expected_results.csv
├── README.md
└── test_rc_lowpass.py
```

## Definition of Done

A phase or feature is complete only when:

- Code is version-controlled and reviewed.
- Unit and integration tests pass.
- At least one analytical or approved reference case is documented.
- Applicable residuals satisfy the configured tolerances.
- Output is deterministic.
- The README and related skill documentation are updated.
- A different contributor can reproduce the result.

## Development Phases

Use these gates for planning:

1. **Alignment:** scope, conventions, repository, and reference cases are approved.
2. **Topological core:** netlist to model to graph to incidence matrix works.
3. **Linear DC nodal:** supported resistive/current-source cases solve and pass KCL.
4. **AC analysis:** supported C/L cases and sweeps produce validated magnitude and phase data.
5. **Educational Tableau:** explicit branch variables and `Y/Z/W/T/W_prime` are traceable and validated.
6. **Explainable agent:** agent, skills, prompts, tools, and reports work as an integrated experience.
7. **MNA extension:** special branches and controlled elements are added only after the MVP gates pass.

## Review Checklist

Before approving a change, verify:

- [ ] Supported scope and unsupported elements are explicit.
- [ ] Ground, signs, orientations, ordering, branches, and units follow shared conventions.
- [ ] Original netlist lines are retained.
- [ ] Graph and incidence matrix use the same branch order.
- [ ] Every matrix row maps to a documented equation or stamp.
- [ ] Linear systems are solved without explicit matrix inversion.
- [ ] KCL, KVL, constitutive, and global residual checks are executed where applicable.
- [ ] The agent invokes deterministic tools instead of generating results.
- [ ] Reports include labels, units, warnings, tolerances, and traceability.
- [ ] Another contributor can reproduce the run.

## Positive Example

Input:

```spice
* Educational resistive divider
V1 1 0 DC 10
R1 1 2 1k
R2 2 0 2k
.END
```

Expected workflow:

1. Validate the supported syntax and ground node.
2. Parse one independent voltage source and two resistors.
3. Preserve nodes `0`, `1`, and `2` and create deterministic branch identifiers.
4. Build the directed graph and labeled reduced incidence matrix.
5. Select a formulation compatible with the implemented handling of the voltage source.
6. Assemble and solve with the deterministic numerical tools.
7. Validate the global residual and applicable circuit laws.
8. Report the node and branch results with units, conventions, and validation evidence.

Do not place expected numeric results in the skill unless they are stored as approved reference data and verified by the test suite.

## Negative Example

Input:

```spice
R1 1 2 1k
R1 2 3 2k
X1 3 0 unsupported_model
.END
```

Expected response:

- Stop during netlist validation.
- Report the duplicate identifier `R1`.
- Report the unsupported element `X1`.
- Report the absence of an explicit ground-connected path if detected by the topology validator.
- Do not assemble a matrix or claim a circuit solution.

## Completion Response Pattern

When the workflow succeeds, summarize:

- Analysis performed.
- Formulation selected.
- Generated artifacts.
- Key results with units.
- Validation metrics and status.
- Warnings or limitations.
- Exact files needed to reproduce the analysis.

When it fails, summarize:

- Blocking stage.
- Evidence.
- Affected source lines or artifacts.
- Required correction.
- Stages not executed.

## References

Use repository-controlled course material and approved project documentation as the primary methodological references. For platform behavior, consult the current official GitHub Copilot documentation. For numerical behavior, use the NumPy version and API declared by the repository. For graph representation, use the declared NetworkX version.
