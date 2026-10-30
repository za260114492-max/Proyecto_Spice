# Proyecto de la Unidad I

## Desarrollo de un Custom Agent para simulación explicable de circuitos

**Flujo:** Netlist → grafo → matrices → análisis AC → ganancia → validación  
**Curso:** Matemáticas Avanzadas · Programa 2026  
**Programa:** Maestría en Ingeniería Electrónica, Tecnológico Superior de Jalisco  
**Profesor:** Dr. Francisco E. Rangel-Patiño

> Transcripción consultable de [la especificación original en PDF](./originals/Proyecto_Unidad_1_Agente_SPICE_Educativo.pdf). Esta versión Markdown es la referencia textual editable. Las imágenes originales del circuito y de la comparación SPICE se conservan en el PDF.

## Reto central

Completar las herramientas faltantes, integrar los 10 skills y construir un agente de GitHub Copilot capaz de analizar el filtro activo mostrado, obtener su respuesta en frecuencia y comparar magnitud y fase contra un simulador SPICE.

## 1. Propósito del proyecto

El proyecto integra álgebra lineal, teoría de grafos, formulación nodal, Tableau, análisis fasorial y desarrollo de agentes. El resultado final será un agente educativo que reciba un netlist, construya los artefactos matemáticos del circuito, resuelva el análisis AC y explique cómo obtuvo cada resultado.

### Resultado esperado

El agente no debe funcionar como una caja negra. Cada voltaje, corriente, matriz, gráfica y métrica de validación deberá conservar trazabilidad hasta el netlist y las ecuaciones constitutivas.

## 2. Circuito objetivo

El circuito objetivo es un filtro activo con dos capacitores de entrada, una red de realimentación mediante G₁, una conductancia G₂ a tierra y un amplificador operacional no inversor con resistores Rₐ y Rᵦ. El agente deberá modelar el amplificador operacional ideal mediante la formulación aprobada en el curso.

La especificación original incluye una figura conceptual del circuito. Los valores de C₁, C₂, G₁, G₂, Rₐ, Rᵦ, la excitación Vᵢ y el barrido de frecuencia deberán definirse en el netlist oficial del proyecto; no deberán codificarse dentro de los scripts.

## 3. Referencia del resultado esperado

La salida final deberá incluir dos gráficas de Bode: ganancia en decibeles y fase en grados. La especificación original contiene una imagen de referencia que compara los resultados de la implementación matemática con los de un simulador SPICE.

## 4. Objetivos de aprendizaje

- Aplicar teoría de grafos y matrices a un circuito electrónico real.
- Convertir un netlist en un modelo computacional reproducible.
- Construir matrices de incidencia y formulaciones de circuito.
- Implementar análisis nodal, Tableau y análisis AC con NumPy.
- Diseñar tools deterministas para un Custom Agent de GitHub Copilot.
- Aplicar validación matemática, eléctrica y numérica.
- Comparar resultados contra un simulador SPICE y comunicar diferencias.

## 5. Requerimientos funcionales del agente

El agente deberá:

- Recibir como entrada un netlist compatible con el subconjunto documentado.
- Validar sintaxis, unidades, nodo de referencia y componentes soportados.
- Identificar componentes, nodos, ramas y orientación.
- Generar y mostrar el grafo orientado.
- Generar la matriz de incidencia completa y reducida con encabezados.
- Construir las matrices constitutivas requeridas por el método seleccionado.
- Modelar las ramas especiales asociadas con la fuente de entrada y el amplificador operacional ideal.
- Ensamblar y resolver el sistema lineal para cada frecuencia.
- Calcular H(jω) = Vₒ(jω) / Vᵢ(jω).
- Calcular ganancia en dB y fase en grados.
- Generar gráficas comparables con SPICE.
- Validar residuos, KCL, KVL y ecuaciones constitutivas.
- Generar un reporte explicable y reproducible.

## 6. Cálculos obligatorios y entregables

```text
H(jω) = Vₒ(jω) / Vᵢ(jω)
Ganancia_dB = 20 log10(|H(jω)|)
Fase_deg = angle(H(jω)) · 180 / π
```

La fase deberá desenvolverse cuando sea necesario para evitar saltos artificiales de ±180°. Las gráficas deberán usar frecuencia en escala logarítmica e incluir unidades, títulos, leyendas y etiquetas claras.

| Resultado | Contenido mínimo |
| --- | --- |
| Grafo | Nodos, ramas, orientación e identificador de componente. |
| Matriz A | Forma completa. |
| Matrices de análisis | Y, Z, W y/o bloques MNA, según el método implementado. |
| Respuesta AC | Vᵢ, Vₒ, H(jω), magnitud, dB y fase. |
| Validación | Residuo, KCL, KVL, ecuaciones constitutivas, rango y condición. |
| Comparación | Curvas propias y SPICE en condiciones equivalentes. |

## 7. Trabajo proporcionado y trabajo por desarrollar

### 7.1 Material proporcionado

| Paquete | Contenido | Uso |
| --- | --- | --- |
| Guía metodológica | Arquitectura, responsabilidades del agente/skills/tools, convenciones, flujo determinista, validación, pruebas y definición de terminado. | Documento rector del proyecto. |
| PLAN_01 | Plan para analizar el repositorio y definir dependencias, interfaces, pruebas y estrategia para los nueve scripts Python restantes. | Planeación de las tools faltantes. |
| PLAN_02 | Plan para integrar 15 tools y 10 skills, definir la orquestación del agente, análisis AC, validación, comparación con SPICE y calificación final. | Integración y construcción del Custom Agent. |
| Paquete de 10 skills | Conocimiento sobre netlists, grafos, matrices de incidencia, modelos constitutivos, análisis nodal, Tableau, AC, convenciones, validación y reporting. | Base de conocimiento y metodología del agente. |
| Paquete de seis tools iniciales | `parse_netlist.py`, `build_circuit_model.py`, `build_oriented_graph.py`, `build_incidence_matrix.py`, `build_nodal_system.py` y `solve_linear_system.py`. | Base ejecutable. |

### 7.2 Primeros seis scripts entregados

| # | Script | Responsabilidad |
| --- | --- | --- |
| 1 | `parse_netlist.py` | Interpretar el subconjunto educativo del netlist. |
| 2 | `build_circuit_model.py` | Crear nodos, ramas y objetos del dominio. |
| 3 | `build_oriented_graph.py` | Construir y exportar el grafo dirigido. |
| 4 | `build_incidence_matrix.py` | Generar A completa y reducida. |
| 5 | `build_nodal_system.py` | Ensamblar el sistema nodal compatible. |
| 6 | `solve_linear_system.py` | Resolver, recuperar variables y validar KCL. |

### 7.3 Nueve scripts por desarrollar

| # | Script requerido | Responsabilidad principal |
| --- | --- | --- |
| 1 | `validate_netlist.py` | Validación detallada, errores y alcance soportado. |
| 2 | `stamp_elements.py` | Stamps deterministas de elementos lineales y ramas especiales. |
| 3 | `build_constitutive_matrices.py` | Construcción trazable de Y, Z y W. |
| 4 | `build_tableau_system.py` | Ensamble de T, W′ y mapas de índices. |
| 5 | `solve_ac_sweep.py` | Barrido de frecuencia y extracción de H(jω). |
| 6 | `validate_solution.py` | Validación matemática, eléctrica y numérica. |
| 7 | `compare_reference.py` | Comparación cuantitativa contra resultados SPICE. |
| 8 | `generate_report.py` | Reporte explicable en Markdown/JSON. |
| 9 | `plot_results.py` | Gráficas de ganancia en dB y fase en grados. |

## 8. Skills que deberá integrar el agente

| # | Skill |
| --- | --- |
| 1 | `spice-netlist-fundamentals` |
| 2 | `circuit-graph-theory` |
| 3 | `incidence-matrix-method` |
| 4 | `component-constitutive-models` |
| 5 | `classical-nodal-analysis` |
| 6 | `tableau-formulation` |
| 7 | `ac-frequency-analysis` |
| 8 | `engineering-units-and-conventions` |
| 9 | `solver-validation` |
| 10 | `explainable-circuit-reporting` |

Los skills contienen el conocimiento y la metodología; los scripts son las tools ejecutables. El agente deberá seleccionar ambos en el orden apropiado y no calcular matrices únicamente mediante generación de texto.

## 9. Flujo de trabajo esperado del agente

```text
Netlist
  ↓
Validación sintáctica y de alcance
  ↓
Modelo del circuito y grafo orientado
  ↓
Matriz de incidencia
  ↓
Modelos constitutivos y ramas especiales
  ↓
Sistema nodal / Tableau / MNA
  ↓
Barrido AC y solución con NumPy
  ↓
H(jω), ganancia dB y fase
  ↓
Validación y comparación con SPICE
  ↓
Reporte explicable
```

## 10. Procedimiento para completar el Basic SPICE Agent

Primero deberá completarse y validarse el motor determinista de simulación. El agente interpreta, selecciona el flujo y explica resultados; los skills contienen conocimiento y metodología; las herramientas Python realizan los cálculos deterministas.

1. **Preparar el repositorio.** Usar la guía metodológica para organizar los 10 skills, los seis scripts iniciales, los documentos suministrados y las áreas de agente, prompts, código fuente, pruebas, ejemplos y artefactos.
2. **Estudiar el material.** Revisar la guía, los 10 `SKILL.md` y los seis scripts. Comprender nodos, ramas, orientación, unidades y matrices; aplicar convenciones compartidas para tierra, polaridad, signos, ordenamiento, números complejos y tolerancias.
3. **Utilizar PLAN_01 antes de programar.** En Plan Mode, pedir a Copilot que inspeccione el repositorio y proponga dependencias, interfaces, entradas/salidas, algoritmos, contratos de datos, pruebas unitarias/de integración y criterios de terminado. No generar aún los nueve scripts. El plan aprobado debe mantener compatibilidad con los seis scripts existentes.
4. **Desarrollar los nueve scripts restantes.** Implementar validación, stamps, matrices constitutivas, Tableau, barrido AC, validación, comparación con SPICE, reporte y gráficas. Resultado esperado: seis tools proporcionadas más nueve desarrolladas, para un total de 15.
5. **Utilizar PLAN_02 para diseñar la integración.** Después de completar las 15 tools, auditar herramientas, skills, contratos, convenciones, interfaces, dependencias, pruebas, flujo AC, validaciones e integración SPICE. Crear explícitamente el mapeo Skill → Tool(s).
6. **Corregir los gaps.** Resolver interfaces incompatibles, discrepancias de orden/signos, metadatos o pruebas faltantes, problemas con el op-amp ideal e inconsistencias en H(jω), dB o fase.
7. **Construir el Basic SPICE Agent.** Crear el agente en `.github/agents/`. Debe interpretar solicitudes, seleccionar skills y tools, ejecutarlas en orden, detenerse ante errores bloqueantes, validar, explicar y generar artefactos. No debe calcular manualmente matrices, voltajes, corrientes, H(jω), ganancia ni fase.
8. **Calificar con el circuito de Unidad I.** Usar el netlist oficial del filtro activo de dos capacitores, realimentación G₁, G₂ a tierra y amplificador operacional no inversor con Rₐ/Rᵦ. El reporte debe incluir netlist, componentes, nodos, ramas, grafo, matriz, formulación, matrices etiquetadas, resultados, ganancia/fase, validación, comparación SPICE, advertencias, limitaciones y datos reproducibles.
9. **Comparar contra SPICE.** Ejecutar el circuito equivalente con la misma topología, fuentes, componentes, modelo ideal del op-amp, condiciones de análisis y frecuencias; comparar magnitud y fase cuantitativamente.

## 11. Validación contra SPICE

La comparación deberá usar el mismo netlist equivalente, valores de componentes, modelo ideal del amplificador operacional, amplitud de entrada y barrido de frecuencia.

| Métrica | Requisito |
| --- | --- |
| Magnitud | Error absoluto y relativo en puntos seleccionados. |
| Fase | Diferencia angular en grados con tratamiento consistente de wrapping. |
| Frecuencia característica | Comparación del punto de transición identificado por ambos métodos. |
| Ganancia de banda | Comparación del valor en la región estable. |
| Residuos | Evidencia de que el sistema matemático satisface las tolerancias. |

## 12. Entregables

| Entregable | Contenido |
| --- | --- |
| Repositorio Git | Código, agente, 10 skills, prompts, pruebas y documentación. |
| Nueve scripts | Implementación completa con encabezado, autor, docstrings y CLI. |
| Netlist final | Circuito objetivo y configuración del barrido AC. |
| Reporte técnico | Matemáticas, arquitectura, resultados, validación y limitaciones. |
| Demo del agente | Ejecución desde netlist hasta reporte final. |
| Comparación SPICE | Datos, gráficas y métricas de diferencia. |
| Presentación final | Resumen ejecutivo y demostración técnica. |

## 13. Estructura mínima del reporte final

- Portada y resumen ejecutivo.
- Definición del problema y circuito.
- Arquitectura del agente.
- Netlist.
- Grafo orientado y matriz de incidencia.
- Matrices de admitancia/impedancia requeridas por el método.
- Formulación matemática seleccionada.
- Implementación de los nueve scripts.
- Respuesta AC: H(jω), dB y fase.
- Validación matemática y numérica.
- Comparación contra SPICE.
- Limitaciones y conclusiones.

## 14. Política de uso de GitHub Copilot

GitHub Copilot podrá utilizarse para planear, implementar, revisar, probar y documentar. Sin embargo, el estudiante es responsable de comprender y defender las ecuaciones, matrices, algoritmos y decisiones. El uso de IA no sustituye la validación matemática ni la revisión humana.
