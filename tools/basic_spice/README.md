# Herramientas Python del agente SPICE educativo

Author: Dr. Francisco E. Rangel-Patiño

Este paquete contiene quince herramientas deterministas implementadas. Los scripts mencionados en los planes o skills que no aparecen aquí siguen pendientes.

## Herramientas incluidas

1. `parse_netlist.py`
2. `validate_netlist.py`
3. `build_circuit_model.py`
4. `build_oriented_graph.py`
5. `build_incidence_matrix.py`
6. `stamp_elements.py`
7. `build_constitutive_matrices.py`
8. `build_tableau_system.py`
9. `build_nodal_system.py`
10. `solve_linear_system.py`
11. `validate_solution.py`
12. `solve_ac_sweep.py`
13. `compare_reference.py`
14. `generate_report.py`
15. `plot_results.py`

## Preparación y prueba

Ejecuta estos comandos desde la raíz del workspace:

```powershell
python -m pip install -r tools/basic_spice/requirements.txt
python -m unittest discover -s tests -v
```

Las pruebas están organizadas por propósito: `tests/unit/` contiene pruebas
por herramienta y `tests/integration/` valida el flujo completo.

## Flujo de ejemplo

El ejemplo resuelve el circuito resistivo incluido. Los artefactos se guardan bajo `artifacts/`.

```powershell
New-Item -ItemType Directory -Force artifacts | Out-Null
python tools/basic_spice/parse_netlist.py tools/basic_spice/examples/current_source_resistive.cir -o artifacts/parsed.json
python tools/basic_spice/validate_netlist.py artifacts/parsed.json -o artifacts/validation.json
python tools/basic_spice/build_circuit_model.py artifacts/parsed.json -o artifacts/circuit.json
python tools/basic_spice/build_oriented_graph.py artifacts/circuit.json -o artifacts/topology.json --image artifacts/graph.png
python tools/basic_spice/build_incidence_matrix.py artifacts/circuit.json -o artifacts/incidence.json --markdown artifacts/incidence.md --npz artifacts/incidence.npz
python tools/basic_spice/stamp_elements.py artifacts/circuit.json --analysis DC -o artifacts/stamps.json
python tools/basic_spice/build_constitutive_matrices.py artifacts/circuit.json artifacts/stamps.json -o artifacts/constitutive.json
python tools/basic_spice/build_nodal_system.py artifacts/circuit.json artifacts/incidence.json -o artifacts/nodal.json
python tools/basic_spice/solve_linear_system.py artifacts/nodal.json artifacts/circuit.json -o artifacts/results.json
```

El circuito con fuente ideal de voltaje se resuelve mediante el flujo Tableau:

```powershell
python tools/basic_spice/parse_netlist.py tools/basic_spice/examples/voltage_source_divider.cir -o artifacts/tableau_parsed.json
python tools/basic_spice/validate_netlist.py artifacts/tableau_parsed.json -o artifacts/tableau_validation.json
python tools/basic_spice/build_circuit_model.py artifacts/tableau_parsed.json -o artifacts/tableau_circuit.json
python tools/basic_spice/build_incidence_matrix.py artifacts/tableau_circuit.json -o artifacts/tableau_incidence.json
python tools/basic_spice/stamp_elements.py artifacts/tableau_circuit.json --analysis DC -o artifacts/tableau_stamps.json
python tools/basic_spice/build_constitutive_matrices.py artifacts/tableau_circuit.json artifacts/tableau_stamps.json -o artifacts/tableau_constitutive.json
python tools/basic_spice/build_tableau_system.py artifacts/tableau_circuit.json artifacts/tableau_incidence.json artifacts/tableau_constitutive.json -o artifacts/tableau.json
python tools/basic_spice/solve_linear_system.py --tableau artifacts/tableau.json -o artifacts/tableau_results.json
python tools/basic_spice/validate_solution.py artifacts/tableau.json artifacts/tableau_results.json -o artifacts/tableau_solution_validation.json
```

El barrido AC y la función de transferencia del filtro RC usan los mismos pasos de modelado y Tableau para cada frecuencia:

```powershell
python tools/basic_spice/parse_netlist.py tools/basic_spice/examples/rc_lowpass_ac_sweep.cir -o artifacts/ac_parsed.json
python tools/basic_spice/validate_netlist.py artifacts/ac_parsed.json -o artifacts/ac_netlist_validation.json
python tools/basic_spice/build_circuit_model.py artifacts/ac_parsed.json -o artifacts/ac_circuit.json
python tools/basic_spice/build_incidence_matrix.py artifacts/ac_circuit.json -o artifacts/ac_incidence.json
python tools/basic_spice/solve_ac_sweep.py artifacts/ac_circuit.json artifacts/ac_incidence.json --input-node 1 --output-node 2 -o artifacts/ac_sweep.json
```

La directiva opcional `.PROBE AC V(entrada) V(salida)` permite declarar los dos nodos ordenados en el netlist; por ejemplo, `.PROBE AC V(IN) V(OUT)`. Si está presente, los argumentos `--input-node` y `--output-node` pueden omitirse; el primero es la referencia de entrada y el segundo la salida para `H=Vout/Vin`. Sin `.PROBE`, ambos argumentos siguen siendo necesarios. También se permiten frecuencias explícitas repetidas con `--frequency 10 --frequency 100`, pero no junto con `.AC`. Las tensiones se miden respecto a tierra. Cada punto contiene tensión fasorial de entrada/salida, transferencia compleja, ganancia dB, fase y estado de validación. Los puntos singulares o con entrada cero quedan registrados como fallidos, y el comando devuelve código distinto de cero si falla alguno. Para `H=0`, dB y fase se guardan como `null` porque no están definidos. Frecuencia cero no se incluye: DC se trata por separado.

Para comparar el barrido con una referencia identificada, prepara un JSON según [el esquema de referencia AC](../../docs/reference/AC_REFERENCE_DATA_SCHEMA.md). Debe incluir datos de la misma topología y condiciones, la huella `circuit_signature` copiada de `ac_sweep.json`, los mismos nodos de entrada/salida y una fila por frecuencia, sin interpolación:

```powershell
python tools/basic_spice/compare_reference.py artifacts/ac_sweep.json artifacts/ac_reference.json artifacts/ac_circuit.json -o artifacts/ac_comparison.json --csv artifacts/ac_comparison.csv
```

Los límites iniciales son 0.1 dB y 1 grado, ajustables con `--max-gain-error-db` y `--max-phase-error-deg`. El CSV detalla errores firmado/absoluto en dB, relativo en ganancia lineal y error de fase circular. Un fallo de tolerancia produce estado `FAIL` y código de salida no cero.

Genera las curvas de ganancia/fase y, opcionalmente, superpone una comparación aceptada:

```powershell
python tools/basic_spice/plot_results.py artifacts/ac_sweep.json --comparison artifacts/ac_comparison.json --output-prefix artifacts/rc_lowpass --format png
```

Produce `rc_lowpass_gain.png`, `rc_lowpass_phase.png` y `rc_lowpass_plot_manifest.json`. También acepta `--format svg`. Si un barrido tiene puntos fallidos, las gráficas individuales los omiten explícitamente y el manifiesto los enumera; una comparación con referencia fallida se rechaza.

Genera un reporte Markdown al final del flujo, a partir del netlist original y artefactos conservados. Para incluir el grafo, expórtalo primero; no hace falta incluir una referencia para reportar los resultados del barrido:

```powershell
python tools/basic_spice/build_oriented_graph.py artifacts/ac_circuit.json -o artifacts/ac_topology.json --image artifacts/ac_topology.png
python tools/basic_spice/generate_report.py tools/basic_spice/examples/rc_lowpass_ac_sweep.cir artifacts/ac_parsed.json artifacts/ac_circuit.json artifacts/ac_incidence.json -o artifacts/ac_report.md --graph-json artifacts/ac_topology.json --ac-sweep-json artifacts/ac_sweep.json --plot-manifest-json artifacts/rc_lowpass_plot_manifest.json
```

Para reportar un punto Tableau, añade `--stamps-json`, `--constitutive-json`, `--tableau-json`, `--solution-json` y `--validation-json` con los artefactos correspondientes. Para el análisis nodal se puede usar `--nodal-json` y `--solution-json`. `--comparison-json` acepta sólo la comparación asociada al mismo barrido. El generador comprueba identidad y órdenes de nodos/ramas, coteja las líneas del netlist original con el parseo, registra huellas SHA-256 y **no recalcula**. Si falta un artefacto estructural, se declara en el reporte; un reporte sin resultados validados queda `NOT_VALIDATED` y el comando devuelve código distinto de cero.

## Límite del MVP

`build_nodal_system.py` rechaza intencionalmente fuentes ideales de voltaje porque el análisis nodal clásico no representa directamente su corriente desconocida. Para circuitos soportados con esas fuentes, utiliza el flujo Tableau descrito arriba.

`validate_netlist.py` consume el JSON de `parse_netlist.py`: comprueba referencia a tierra, conectividad, coherencia semántica y directivas. Los errores sintácticos y elementos no soportados se detienen antes, durante el parseo. Ante estado `FAIL`, no continúes con el modelo.

`stamp_elements.py` produce una ecuación por rama con la convención `Y*V_branch + Z*I_branch = W`. Selecciona explícitamente el modo. Ejemplo AC a 1 kHz:

```powershell
python tools/basic_spice/stamp_elements.py artifacts/circuit.json --analysis AC --frequency 1000 -o artifacts/ac_stamps.json
```

Los stamps se consumen para construir el bloque constitutivo y el sistema Tableau, pero no los usa el ensamblador nodal clásico. En análisis DC estacionario, el capacitor ideal queda abierto y el inductor ideal en cortocircuito. En análisis AC, las fuentes definidas como DC se representan por fasor cero y viceversa.

`build_constitutive_matrices.py` consume el modelo del circuito y los stamps. Produce matrices diagonales `Y` y `Z` y el vector `W`, según `Y @ Vb + Z @ I = W`. El orden de ramas se conserva y cada fila incluye ecuación, componente, línea de origen y unidades.

`build_tableau_system.py` combina la incidencia y el bloque constitutivo en `T @ X = W_prime`, con `X = [Vb; I; Vn]`. `solve_linear_system.py --tableau` resuelve ese sistema sin invertir la matriz y marca el resultado `SOLVED_NOT_VALIDATED`. `validate_solution.py` vuelve a calcular, de forma independiente, los residuos global, KCL, rama-nodo y constitutivo, además del rango y el número de condición. `solve_ac_sweep.py` usa este flujo validado en cada punto. Solo presenta estado `PASS` cuando los residuos cumplen las tolerancias configuradas; un resultado resuelto no equivale por sí mismo a uno validado.

## Convención de signos

- La orientación de cada rama sigue el orden de nodos escrito en el netlist.
- `+1` en la matriz de incidencia significa que la rama sale del nodo.
- `-1` significa que la rama entra al nodo.
- Los valores de fuentes de corriente usan la misma orientación de rama.
