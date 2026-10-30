---
name: circuit-graph-theory
description: Convierte un modelo de circuito en un grafo orientado con nodos, ramas y conectividad. Usar después de validar el netlist y antes de construir matrices.
license: Academic use
---

# circuit-graph-theory

## Objetivo

Representar la topología del circuito de forma independiente a los valores de los componentes y conservar una relación uno-a-uno entre componente y rama.

## Condiciones de activación

Usar cuando exista un modelo de circuito válido y se solicite grafo, conectividad, nodos, ramas, matriz de adyacencia o preparación de la matriz de incidencia.

## Conceptos

Un nodo eléctrico es un vértice. Cada componente de dos terminales es una rama orientada. La orientación es una referencia matemática y no implica que la corriente física final sea positiva en ese sentido.

## Procedimiento

1. Obtener la lista normalizada de nodos.
2. Confirmar el nodo de referencia `0`.
3. Asignar `B1...Bb` conservando el orden del netlist.
4. Orientar cada rama desde `node_from` hacia `node_to`.
5. Crear la tabla componente-rama.
6. Construir un multigrafo dirigido para conservar ramas paralelas.
7. Verificar conectividad del circuito respecto al nodo de referencia.
8. Exportar topología y representación visual.

## Diferencia entre matrices

La matriz de adyacencia relaciona nodo con nodo y puede perder la identidad de ramas paralelas. La matriz de incidencia relaciona nodos con ramas y conserva la identidad requerida para KCL, KVL y Tableau.

## Manejo de elementos multiterminales

No descomponer automáticamente un elemento multiterminal sin un modelo aprobado. La expansión debe estar definida por `component-constitutive-models` y debe crear ramas auxiliares trazables.

## Entradas requeridas

Modelo del circuito, orden de componentes, nodos normalizados y reglas de expansión de elementos.

## Salida esperada

`topology.json`, tabla de nodos, tabla de ramas, lista de aristas, componentes por rama y `graph.svg` o `graph.png`.

## Tools relacionadas

`build_circuit_model.py`, `build_oriented_graph.py`, NetworkX para visualización y análisis de conectividad.

## Validaciones

Cada componente soportado tiene una rama, cada rama tiene dos extremos válidos, no hay ramas sin componente, se conservan paralelos y todos los nodos relevantes están conectados al circuito esperado.

## Ejemplo

Para `R1 1 2 1k`, crear `B1: N1 -> N2`. Si la corriente calculada es negativa, la corriente física circula en sentido opuesto a la orientación de referencia.

## Errores y limitaciones

Circuitos desconectados, nodos aislados y elementos multiterminales sin expansión aprobada deben bloquear el siguiente paso.

## Criterio de terminación

La topología es determinista, conserva todas las ramas y puede reconstruirse desde el artefacto exportado.

## Referencias

- Material del curso: `Matematicas_Lectura05_WW40'26-B`.
- Repositorio del proyecto y contrato común de datos.
- Este skill no sustituye la ejecución de las tools deterministas.
