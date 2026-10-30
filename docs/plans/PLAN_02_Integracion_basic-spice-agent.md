# PLAN 02 - Integración de 15 Tools + 10 Skills en `basic-spice-agent`

## Proyecto
**basic-spice-agent - Matemáticas Avanzadas, Unidad I**

## Suposición de entrada
En esta fase se asume que **los 15 scripts Python están terminados** y que los **10 skills Markdown están disponibles**.

## Objetivo de este PLAN
Crear el plan de ingeniería para:

**15 tools + 10 skills → `basic-spice-agent` → validación final con el circuito de Unidad I**

> **Importante:** En esta etapa GitHub Copilot debe analizar la integración antes de modificar archivos o implementar el agente.

---

# Prompt para GitHub Copilot - PLAN Mode

```text
We are developing an educational GitHub Copilot Custom Agent called:

basic-spice-agent

Assume that ALL 15 Python tools and ALL 10 skills required by the
project have already been developed.

Your task in this stage is ONLY TO CREATE AN INTEGRATION,
VALIDATION, TESTING, AND CUSTOM-AGENT DEVELOPMENT PLAN.

DO NOT write new Python scripts.
DO NOT rewrite existing Python scripts.
DO NOT create basic-spice-agent.agent.md yet.
DO NOT modify repository files.
DO NOT start implementation.

First inspect the complete repository and determine how the system
actually works.

==================================================
1. INSPECT THE COMPLETE REPOSITORY
==================================================

Review:

A. The methodological guide.
B. The Unit 1 project specification.
C. All 10 SKILL.md files.
D. All 15 Python tools.
E. README files.
F. requirements.txt.
G. Example netlists.
H. Unit tests.
I. Integration tests.
J. Reference SPICE data.
K. Generated JSON/CSV/Markdown/NPZ/PNG/SVG artifacts.
L. Existing GitHub Copilot configuration.

Do not infer completeness from filenames.
Inspect actual implementations and interfaces.

==================================================
2. INVENTORY THE 15 PYTHON TOOLS
==================================================

The expected tool architecture includes:

1. parse_netlist.py
2. validate_netlist.py
3. build_circuit_model.py
4. build_oriented_graph.py
5. build_incidence_matrix.py
6. stamp_elements.py
7. build_constitutive_matrices.py
8. build_nodal_system.py
9. build_tableau_system.py
10. solve_linear_system.py
11. solve_ac_sweep.py
12. validate_solution.py
13. compare_reference.py
14. generate_report.py
15. plot_results.py

For every tool identify:

- Purpose
- Inputs
- Outputs
- Public functions/classes
- CLI interface
- Internal dependencies
- External packages
- JSON/data schemas
- Generated artifacts
- Supported elements
- Supported analyses
- Error handling
- Validation behavior
- Existing tests
- Known limitations

Identify duplicated or overlapping functionality.

==================================================
3. INVENTORY THE 10 SKILLS
==================================================

Inspect:

1. spice-netlist-fundamentals
2. circuit-graph-theory
3. incidence-matrix-method
4. component-constitutive-models
5. classical-nodal-analysis
6. tableau-formulation
7. ac-frequency-analysis
8. engineering-units-and-conventions
9. solver-validation
10. explainable-circuit-reporting

For each skill identify:

- Activation condition
- Domain knowledge
- Decision rules
- Python tool(s) it should invoke
- Upstream skill dependencies
- Downstream skill dependencies
- Validation requirements
- Error/limitation rules

Produce a SKILL → TOOL(S) mapping.

==================================================
4. AUDIT THE DATA CONTRACTS
==================================================

Determine how data actually flows through the 15 tools.

Audit contracts for:

- Parsed netlist
- Validated netlist
- Circuit
- Node
- Branch
- Components
- Independent sources
- Directed graph
- Incidence matrices
- Component stamps
- Y, Z, W
- Nodal system
- Tableau system
- Unknown vector/index maps
- Frequency vector
- Complex voltages
- Complex currents
- Vi(jω)
- Vo(jω)
- H(jω)
- Gain_dB
- Phase_deg
- Validation report
- SPICE reference data
- Comparison metrics
- Plot artifacts
- Final report

Create an end-to-end data-flow diagram.

Example:

Netlist
  ↓
parse_netlist.py
  ↓
parsed representation
  ↓
validate_netlist.py
  ↓
validated representation
  ↓
build_circuit_model.py
  ↓
Circuit / Node / Branch

Continue through the final report.

Identify incompatible interfaces.
Do not fix them yet.

==================================================
5. AUDIT ENGINEERING CONVENTIONS
==================================================

Verify consistency across skills and tools for:

- Reference node
- Node ordering
- Branch ordering
- Branch orientation
- Voltage polarity
- Current direction
- Incidence-matrix signs
- Engineering prefixes
- SI units
- Complex-number representation
- Frequency units
- Matrix row/column labels
- Numerical tolerances
- AC magnitude
- AC phase
- Phase wrapping/unwrapping
- Gain calculation

Pay particular attention to:

+1 = branch leaves the node
-1 = branch enters the node

Do not silently resolve conflicting conventions.
List each discrepancy explicitly.

==================================================
6. IDENTIFY INTEGRATION GAPS
==================================================

Classify each actual integration gap as:

BLOCKER
MAJOR
MINOR

Possible categories include:

- Incompatible JSON contracts
- Node-order mismatch
- Branch-order mismatch
- Sign-convention mismatch
- Tool without CLI
- Tool without callable API
- Missing output metadata
- Skill/tool mismatch
- Missing test
- Missing ideal-OpAmp support
- Missing AC observable definition
- Inconsistent H(jω) calculation
- Inconsistent dB calculation
- Inconsistent phase handling
- Missing SPICE reference format
- Missing report artifact

Only report gaps actually found in the repository.

==================================================
7. DESIGN THE FINAL AGENT WORKFLOW
==================================================

Plan the orchestration for:

User
  ↓
Netlist
  ↓
basic-spice-agent
  ↓
Netlist Parsing
  ↓
Netlist Validation
  ↓
Circuit Model
  ↓
Oriented Graph
  ↓
Incidence Matrix
  ↓
Component Models
  ↓
Formulation Selection
  ↓
Nodal / Tableau
  ↓
Linear-System Solution
  ↓
AC Frequency Sweep
  ↓
Solution Validation
  ↓
SPICE Comparison
  ↓
Plots
  ↓
Explainable Report

For every stage identify:

- Agent decision
- Skill
- Python tool
- Input artifact
- Output artifact
- Validation gate
- Failure behavior

==================================================
8. FORMULATION-SELECTION LOGIC
==================================================

The agent must select the formulation based on circuit properties.

Plan decision logic for:

- Classical Nodal Analysis
- Tableau formulation

Also identify where Modified Nodal Analysis would be required if
added later.

The agent must not create artificial approximations merely to force
a circuit into Classical Nodal Analysis.

Define how ideal voltage sources and the ideal operational amplifier
in the Unit 1 circuit are handled by the approved project
methodology.

==================================================
9. AC ANALYSIS WORKFLOW
==================================================

Plan the complete AC workflow:

frequency
    ↓
ω = 2πf
    ↓
s = jω
    ↓
frequency-dependent component models
    ↓
matrices
    ↓
linear-system solution
    ↓
Vi(jω)
    ↓
Vo(jω)
    ↓
H(jω) = Vo(jω)/Vi(jω)
    ↓
Gain_dB = 20*log10(abs(H(jω)))
    ↓
Phase_deg = angle(H(jω))*180/pi

Audit handling of:

- Single frequency
- LIN sweep
- DEC sweep
- f = 0
- Complex values
- Failed frequency points
- Phase wrapping
- Phase unwrapping
- Input node selection
- Output node selection

==================================================
10. VALIDATION ARCHITECTURE
==================================================

Plan mandatory validation gates.

When applicable verify:

Linear solver:

M @ x - b ≈ 0

KCL:

A @ I ≈ 0

Branch/node voltage relation:

Vb - A.T @ Vn ≈ 0

Constitutive equations:

Y @ Vb + Z @ I - W ≈ 0

Tableau:

T @ X - W' ≈ 0

Also audit:

- Matrix rank
- Condition number
- NaN / Inf
- Floating nodes
- Disconnected circuits
- Missing component models
- Incompatible sources

Define PASS / WARN / FAIL behavior.

The agent must not present an unvalidated solution as correct.

==================================================
11. SPICE REFERENCE COMPARISON
==================================================

Plan comparison against reference SPICE results using equivalent:

- Circuit topology
- Component values
- Input source
- Frequency sweep
- Output observable
- Analysis conditions

Compare quantitatively:

Frequency
Agent Gain_dB
SPICE Gain_dB
Gain Error

and:

Frequency
Agent Phase_deg
SPICE Phase_deg
Phase Error

Determine:

- Reference file schema
- Frequency alignment/interpolation policy
- Absolute error
- Relative error where meaningful
- Phase difference treatment
- Summary metrics
- Plot-overlay behavior

Plots that only look similar are not sufficient validation.

==================================================
12. DESIGN basic-spice-agent
==================================================

Based on the repository audit, propose the structure of:

.github/agents/basic-spice-agent.agent.md

DO NOT create the file yet.

Plan these sections:

- Agent identity
- Purpose
- Scope
- Responsibilities
- Supported analyses
- Skills available
- Tools available
- Skill-selection logic
- Tool-selection logic
- Workflow
- Validation gates
- Failure handling
- Report requirements
- Guardrails

The agent must ORCHESTRATE deterministic Python tools.

The agent must not manually calculate:

- Matrices
- Linear-system solutions
- Voltages
- Currents
- H(jω)
- Gain_dB
- Phase_deg

==================================================
13. AGENT ORCHESTRATION MAP
==================================================

Create this table:

| Step | Agent Decision | Skill | Python Tool | Input | Output | Gate | Failure Action |

Cover the complete path from user request to final report.

==================================================
14. END-TO-END TEST PLAN
==================================================

Plan progressive qualification with:

A. Resistive network
B. RC circuit
C. RL circuit
D. RLC circuit
E. Current-source circuit
F. Ideal voltage-source circuit
G. Circuit requiring Tableau
H. AC sweep
I. Singular circuit
J. Floating-node circuit
K. Invalid netlist
L. SPICE-reference comparison
M. Final Unit 1 circuit

For each test specify:

- Purpose
- Netlist characteristics
- Expected behavior
- Expected artifacts
- Validation gate
- Pass criterion

==================================================
15. FINAL UNIT 1 QUALIFICATION
==================================================

The final qualification target is the instructor's Unit 1 circuit.

The completed basic-spice-agent must demonstrate:

1. Read the official circuit netlist.
2. Validate the netlist.
3. Identify all nodes.
4. Identify all branches.
5. Generate the oriented graph.
6. Generate the incidence matrix.
7. Generate constitutive models.
8. Handle the ideal operational amplifier according to the approved
   methodology.
9. Build the appropriate mathematical formulation.
10. Execute the requested AC sweep.
11. Solve voltages and currents.
12. Obtain Vi(jω).
13. Obtain Vo(jω).
14. Calculate H(jω).
15. Calculate Gain_dB.
16. Calculate Phase_deg.
17. Validate the mathematical solution.
18. Compare results against SPICE.
19. Generate Gain_dB vs frequency.
20. Generate Phase_deg vs frequency.
21. Generate the final explainable report.

==================================================
16. RECOMMENDED INTEGRATION SEQUENCE
==================================================

Do not plan individual tool development.
The tools already exist.

Plan system integration stages such as:

Stage 1 - Repository and interface audit
Stage 2 - Convention alignment
Stage 3 - Tool-to-tool integration
Stage 4 - Skill-to-tool mapping
Stage 5 - Nodal workflow qualification
Stage 6 - Tableau workflow qualification
Stage 7 - AC workflow qualification
Stage 8 - Validation workflow qualification
Stage 9 - SPICE comparison qualification
Stage 10 - Reporting/plot qualification
Stage 11 - Custom Agent integration
Stage 12 - Unit 1 final qualification

Adjust the order based on actual repository findings.

==================================================
17. DEFINITION OF DONE
==================================================

The project is NOT complete merely because:

- all 15 Python scripts exist,
- all 10 skills exist,
- or basic-spice-agent.agent.md exists.

The project is complete when the complete workflow operates
reproducibly from:

USER + NETLIST

through:

PARSE
VALIDATE
MODEL
GRAPH
MATRICES
SOLVE
AC SWEEP
VALIDATE
COMPARE
PLOT
REPORT

to:

VERIFIED CIRCUIT ANALYSIS + EXPLAINABLE REPORT

For the Unit 1 circuit, completion must include:

- H(jω)
- Gain_dB
- Phase_deg
- Mathematical validation
- SPICE comparison
- Gain plot
- Phase plot
- Explainable report

==================================================
18. REQUIRED PLAN OUTPUT
==================================================

Return ONLY the engineering integration PLAN.

Organize the response as:

1. Repository Assessment
2. Architecture Found
3. Python Tool Inventory
4. Skill Inventory
5. Skill-to-Tool Mapping
6. Data Contract Audit
7. Convention Audit
8. Integration Gaps
9. Final Agent Workflow
10. Formulation Selection Logic
11. AC Analysis Workflow
12. Validation Architecture
13. SPICE Comparison Strategy
14. Custom Agent Design Plan
15. Agent Orchestration Map
16. End-to-End Test Plan
17. Recommended Integration Sequence
18. Unit 1 Final Qualification
19. Risks and Open Technical Decisions
20. Definition of Done

End with:

TABLE A

| Stage | Objective | Inputs | Outputs | Validation Gate |

TABLE B

| Agent Step | Skill | Tool | Input | Output | Failure Action |

IMPORTANT:

DO NOT WRITE PYTHON CODE.
DO NOT REWRITE EXISTING TOOLS.
DO NOT CREATE basic-spice-agent.agent.md YET.
DO NOT MODIFY FILES.
DO NOT START IMPLEMENTATION.

ONLY inspect the complete repository and produce the integration,
validation, testing, and Custom Agent development PLAN.
```

---

## Resultado esperado de esta etapa

El producto debe ser un **plan de integración y calificación del sistema completo**. El énfasis ya no está en desarrollar scripts individuales, sino en demostrar que los 15 tools y los 10 skills pueden operar como un único `basic-spice-agent` y completar de manera trazable el análisis del circuito final de la Unidad I.
