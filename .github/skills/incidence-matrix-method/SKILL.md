---
name: incidence-matrix-method
description: Construye y verifica matrices de incidencia completa y reducida a partir del grafo orientado. Usar cuando ya existen nodos y ramas ordenados.
license: Academic use
---

# incidence-matrix-method

## Objetivo

Transformar la topología orientada en una matriz etiquetada compatible con KCL, KVL, análisis nodal y Tableau.

## Condiciones de activación

Usar al solicitar la matriz A o cuando una formulación necesite la relación nodo-rama.

## Convención

Para cada nodo `i` y rama `j`:

```text
A[i,j] = +1 si la rama j sale del nodo i
A[i,j] = -1 si la rama j entra al nodo i
A[i,j] =  0 en otro caso
```

## Procedimiento

1. Usar el orden de nodos y ramas del contrato común.
2. Construir la matriz completa, incluida la fila del nodo `0`.
3. Construir la matriz reducida eliminando sólo la fila del nodo de referencia.
4. Etiquetar filas con nodos y columnas con `B1...Bb` y nombres de componentes.
5. Guardar ambos artefactos y la correspondencia de índices.

## Propiedades estructurales

Cada columna de la matriz completa de una rama de dos terminales debe contener exactamente un `+1`, un `-1` y ceros restantes. La suma de cada columna completa debe ser cero. La matriz reducida tiene `n` filas para `n+1` nodos totales.

## Relaciones usadas

- KCL: `A @ I = 0`.
- Voltajes de rama: `Vb = A.T @ Vn` para la matriz reducida y voltajes nodales respecto a tierra.

## Tools relacionadas

`build_incidence_matrix.py`, `matrix_formatter.py`, `validate_solution.py`.

## Validaciones

Dimensión esperada, contenido en {-1,0,+1}, propiedad de columnas, etiquetas únicas y coincidencia exacta con la tabla de ramas.

## Ejemplo

Para `B1: N1 -> N2`, la columna B1 contiene `+1` en N1 y `-1` en N2. Si N2 es tierra, la matriz reducida conserva sólo `+1` en N1.

## Errores

No corregir automáticamente signos inconsistentes. Reportar la rama, extremos y columna afectada.

## Salida esperada

Matriz completa y reducida en JSON/NPZ, versión Markdown etiquetada y metadatos de orden.

## Criterio de terminación

Las verificaciones estructurales pasan y A usa exactamente el mismo orden de ramas que el resto del flujo.

## Referencias

- Material del curso: `Matematicas_Lectura05_WW40'26-B`.
- Repositorio del proyecto y contrato común de datos.
- Este skill no sustituye la ejecución de las tools deterministas.
