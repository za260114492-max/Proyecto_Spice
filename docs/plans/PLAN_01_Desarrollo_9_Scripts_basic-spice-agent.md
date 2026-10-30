# PLAN 01 - Desarrollo de los 9 Scripts Python Restantes

## Proyecto
**basic-spice-agent - Matemáticas Avanzadas, Unidad I**

## Objetivo de este PLAN
Crear un plan de ingeniería para desarrollar los **9 scripts Python restantes** del `basic-spice-agent`, partiendo de la arquitectura, los 10 skills y los 6 scripts Python ya existentes.

> **Importante:** En esta etapa GitHub Copilot debe **analizar y planear**, no implementar.

---

# Prompt para GitHub Copilot - PLAN Mode

```text
We are developing an educational GitHub Copilot Custom Agent called:

basic-spice-agent

Your task in this stage is ONLY TO CREATE A DEVELOPMENT PLAN for the
9 remaining Python tools.

DO NOT write Python code yet.
DO NOT create the 9 missing scripts yet.
DO NOT modify the existing scripts.
DO NOT redesign the project from scratch.

Before creating the plan, inspect the actual repository.

==================================================
1. REVIEW THE EXISTING PROJECT
==================================================

First review:

1. The methodological guide for the basic-spice-agent project.
2. The Unit 1 project specification.
3. All 10 SKILL.md files.
4. The 6 Python scripts already provided:

   parse_netlist.py
   build_circuit_model.py
   build_oriented_graph.py
   build_incidence_matrix.py
   build_nodal_system.py
   solve_linear_system.py

5. README files.
6. Existing examples and netlists.
7. Existing tests.
8. requirements.txt.
9. Existing JSON, CSV, Markdown, NPZ, PNG, or SVG artifacts.

Do not assume how these files work.
Inspect their actual implementation.

For the existing code identify:

- Inputs
- Outputs
- Classes
- Functions
- CLI interfaces
- Data structures
- JSON schemas
- Naming conventions
- Node ordering
- Branch ordering
- Branch orientation
- Voltage polarity
- Current direction
- Incidence-matrix sign convention
- Units
- Complex-number representation
- Numerical tolerances
- Error handling
- Internal dependencies

The new scripts must remain compatible with the existing architecture
whenever possible.

==================================================
2. UNDERSTAND THE FINAL OBJECTIVE
==================================================

The final basic-spice-agent must support a traceable workflow:

Netlist
   ↓
Validation
   ↓
Circuit Model
   ↓
Oriented Graph
   ↓
Incidence Matrix
   ↓
Component Constitutive Models
   ↓
Nodal / Tableau Formulation
   ↓
Linear-System Solution
   ↓
AC Frequency Sweep
   ↓
Circuit Response
   ↓
Validation
   ↓
SPICE Comparison
   ↓
Plots
   ↓
Explainable Report

For AC analysis, the final system must calculate:

H(jω) = Vo(jω) / Vi(jω)

Gain_dB = 20*log10(abs(H(jω)))

Phase_deg = angle(H(jω))*180/pi

The final output must include:

- Gain in dB versus frequency
- Phase in degrees versus frequency
- Validation metrics
- Comparison against SPICE reference results

==================================================
3. PLAN THESE 9 PYTHON TOOLS
==================================================

Create the development plan for:

1. validate_netlist.py

Purpose:
Detailed netlist validation, supported syntax, reference node,
duplicates, component values, directives, unsupported elements,
and actionable error reporting.

2. stamp_elements.py

Purpose:
Deterministic component stamps for supported linear elements and
special branches required by the approved mathematical formulation.

3. build_constitutive_matrices.py

Purpose:
Construct traceable Y, Z, and W matrices from component constitutive
equations.

4. build_tableau_system.py

Purpose:
Assemble the Tableau system, including T, W', and index maps for the
unknown vector X.

5. solve_ac_sweep.py

Purpose:
Execute the AC frequency sweep, solve each frequency point, obtain
Vi and Vo, and calculate H(jω), Gain_dB, and Phase_deg.

6. validate_solution.py

Purpose:
Perform mathematical, electrical, and numerical validation using
residuals, KCL, KVL, constitutive equations, matrix rank, condition
number, and finite-value checks.

7. compare_reference.py

Purpose:
Quantitatively compare calculated results against analytical and/or
SPICE reference results.

8. generate_report.py

Purpose:
Generate reproducible Markdown/JSON reports containing netlist
interpretation, topology, matrices, equations, results, validation,
warnings, and limitations.

9. plot_results.py

Purpose:
Generate presentation-quality plots for:

- Gain_dB vs frequency
- Phase_deg vs frequency
- Agent results vs SPICE reference results

==================================================
4. DETERMINE THE DEPENDENCY GRAPH
==================================================

Do not simply implement scripts in numerical order.

Determine the real dependency order among:

- the 6 existing scripts,
- the 9 new scripts,
- and the 10 skills.

For each new script identify:

- Existing scripts it consumes
- Skills that define its methodology
- Data structures it consumes
- Artifacts it produces
- Downstream tools that depend on it

Produce a dependency graph.

==================================================
5. DEFINE EACH SCRIPT BEFORE IMPLEMENTATION
==================================================

For EACH of the 9 scripts define:

A. PURPOSE

What engineering problem does the script solve?

B. INPUTS

Identify:

- Input files
- Python objects
- JSON structures
- CLI arguments
- Required metadata

C. OUTPUTS

Identify:

- Python objects
- JSON files
- CSV files
- Markdown
- Images
- Status/error information

D. CORE FUNCTIONS

Propose the main Python functions/classes.
Do not implement them yet.

E. ALGORITHM

Describe the mathematical/computational procedure.

F. DEPENDENCIES

Identify internal modules and external Python packages.

G. ERROR CONDITIONS

Define expected failures and actionable error messages.

H. VALIDATION

Define how the script will prove that its own output is correct.

I. UNIT TESTS

List the minimum unit tests.

J. INTEGRATION TESTS

Explain how the script will be tested with upstream and downstream
tools.

K. DEFINITION OF DONE

Provide measurable completion criteria.

==================================================
6. PRESERVE ENGINEERING CONVENTIONS
==================================================

Extract conventions from the repository instead of inventing new
ones.

Audit:

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
- Matrix labels
- Numerical tolerances
- AC magnitude
- AC phase

Pay particular attention to the incidence convention:

+1 = branch leaves the node
-1 = branch enters the node

If repository files disagree, report the inconsistency.
Do not silently choose one convention.

==================================================
7. COMPONENT STAMP ARCHITECTURE
==================================================

For stamp_elements.py, explicitly plan support for the component
models required by the Unit 1 project.

For every supported component identify:

- Electrical constitutive equation
- Branch orientation
- Voltage/current sign convention
- Nodal contribution, when applicable
- Tableau Y contribution
- Tableau Z contribution
- Tableau W contribution
- Frequency dependence
- Unit test

Do not invent unsupported semiconductor models.

==================================================
8. TABLEAU ARCHITECTURE
==================================================

The plan for build_constitutive_matrices.py and
build_tableau_system.py must preserve the course formulation.

Use the repository conventions to verify the intended form.

Conceptually, the system includes:

A.T @ Vn - Vb = 0

Y @ Vb + Z @ I = W

A @ I = 0

and an assembled system such as:

X = [Vb; I; Vn]

T @ X = W'

Do not assume signs or block ordering if the repository specifies a
different convention.

The plan must specify matrix dimensions and index maps.

==================================================
9. AC ANALYSIS PLAN
==================================================

For solve_ac_sweep.py, plan:

Frequency specification
    ↓
ω = 2πf
    ↓
s = jω
    ↓
Frequency-dependent component models
    ↓
Matrix construction
    ↓
Linear-system solution
    ↓
Vi(jω)
    ↓
Vo(jω)
    ↓
H(jω)
    ↓
Gain_dB
    ↓
Phase_deg

Define handling of:

- Single frequency
- LIN sweep
- DEC sweep
- Complex values
- f = 0
- Failed frequency points
- Phase wrapping/unwrapping
- Input/output observable selection

==================================================
10. SOLUTION VALIDATION PLAN
==================================================

Plan mandatory checks for validate_solution.py.

At minimum evaluate, when applicable:

Linear-system residual:

M @ x - b ≈ 0

KCL:

A @ I ≈ 0

Branch/node voltage relation:

Vb - A.T @ Vn ≈ 0

Constitutive equations:

Y @ Vb + Z @ I - W ≈ 0

Tableau residual:

T @ X - W' ≈ 0

Also inspect:

- Matrix rank
- Condition number
- NaN / Inf
- Floating nodes
- Disconnected circuits
- Missing component models
- Incompatible sources

Define PASS / WARN / FAIL criteria.

==================================================
11. SPICE COMPARISON PLAN
==================================================

For compare_reference.py, define a consistent reference-data format.

The comparison must align:

- Frequency
- Input source
- Output node
- Component values
- Circuit topology
- Analysis conditions

Compare at minimum:

Frequency
Agent Gain_dB
SPICE Gain_dB
Gain absolute error
Gain relative error

and:

Frequency
Agent Phase_deg
SPICE Phase_deg
Phase error

Plots that merely look similar are not sufficient validation.

==================================================
12. REPORT AND PLOT PLAN
==================================================

For generate_report.py, plan a report containing:

1. Original netlist
2. Parsed components
3. Nodes
4. Branches
5. Oriented graph
6. Incidence matrix
7. Constitutive equations
8. Analysis matrices
9. Frequency sweep
10. Voltages and currents
11. H(jω)
12. Gain_dB
13. Phase_deg
14. Validation results
15. SPICE comparison
16. Warnings and limitations
17. Reproducibility information

For plot_results.py plan:

- Log-frequency axis where appropriate
- Gain_dB vs frequency
- Phase_deg vs frequency
- Agent vs SPICE overlay
- Units and legends
- Export to deterministic file names

==================================================
13. TEST STRATEGY
==================================================

Plan tests for:

A. Netlist validation
B. Component stamps
C. Constitutive matrices
D. Tableau assembly
E. Resistive circuit
F. RC circuit
G. RL circuit
H. RLC circuit
I. Current-source circuit
J. Ideal voltage-source circuit
K. AC sweep
L. Singular circuit
M. Floating node
N. Invalid netlist
O. SPICE comparison
P. Final Unit 1 project circuit

Use simple analytical circuits before the final circuit.

==================================================
14. FINAL UNIT 1 TARGET
==================================================

The completed toolchain must eventually enable the basic-spice-agent
to analyze the instructor's Unit 1 circuit.

It must support this final workflow:

1. Read the netlist.
2. Validate it.
3. Build the circuit model.
4. Build the oriented graph.
5. Build the incidence matrix.
6. Build constitutive matrices.
7. Build the appropriate circuit formulation.
8. Execute the AC sweep.
9. Solve voltages and currents.
10. Obtain Vi(jω).
11. Obtain Vo(jω).
12. Calculate H(jω).
13. Calculate Gain_dB.
14. Calculate Phase_deg.
15. Validate the solution.
16. Compare with SPICE.
17. Plot gain and phase.
18. Generate an explainable report.

==================================================
15. REQUIRED PLAN OUTPUT
==================================================

Return the engineering development PLAN using these sections:

1. Repository Assessment
2. Existing Architecture
3. Existing Data Contracts
4. Convention Inventory
5. Gap Analysis
6. Dependency Graph
7. Recommended Implementation Order
8. validate_netlist.py Plan
9. stamp_elements.py Plan
10. build_constitutive_matrices.py Plan
11. build_tableau_system.py Plan
12. solve_ac_sweep.py Plan
13. validate_solution.py Plan
14. compare_reference.py Plan
15. generate_report.py Plan
16. plot_results.py Plan
17. Unit Test Strategy
18. Integration Test Strategy
19. SPICE Comparison Strategy
20. Final Unit 1 Qualification
21. Risks and Technical Decisions
22. Definition of Done

End with this table:

| Order | Script | Depends On | Main Output | Validation Gate |

IMPORTANT:

DO NOT WRITE PYTHON CODE.
DO NOT CREATE THE 9 SCRIPTS.
DO NOT MODIFY EXISTING FILES.
DO NOT IMPLEMENT THE CUSTOM AGENT.

ONLY inspect the repository and produce the engineering development
PLAN for the 9 remaining Python scripts.
```

---

## Resultado esperado de esta etapa

El producto de este prompt debe ser un **plan técnico de implementación**, no código. Una vez aprobado ese plan, los estudiantes podrán pasar a implementación de los nueve scripts manteniendo compatibilidad con los seis scripts y los diez skills ya proporcionados.
