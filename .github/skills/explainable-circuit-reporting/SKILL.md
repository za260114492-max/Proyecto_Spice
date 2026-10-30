---
name: explainable-circuit-reporting
description: Estandariza reportes explicables de circuitos con netlist, topología, matrices, resultados, validaciones y limitaciones. Usar sólo después de disponer de artefactos calculados.
license: Academic use
---

# explainable-circuit-reporting

## Objetivo

Permitir que un estudiante siga la cadena completa desde el netlist hasta el resultado y distinga hechos calculados, convenciones y advertencias.

## Condiciones de activación

Usar cuando se solicite reporte, explicación, resumen de simulación, matrices o comparación con referencia.

## Regla principal

Este skill no recalcula. Consume artefactos generados y validados por las tools. Si falta un artefacto obligatorio, debe solicitar su generación mediante la tool correspondiente.

## Estructura obligatoria

1. Objetivo y método seleccionado.
2. Netlist original.
3. Tabla de componentes normalizados.
4. Tabla de nodos y nodo de referencia.
5. Tabla de ramas y orientación.
6. Grafo orientado.
7. Matriz de incidencia con encabezados.
8. Ecuaciones constitutivas.
9. Matrices Y/Z/W o sistema nodal.
10. Sistema ensamblado.
11. Resultados con unidades.
12. Validaciones y tolerancias.
13. Advertencias, limitaciones y elementos no soportados.
14. Archivos generados y reproducibilidad.

## Formato de matrices

Mostrar encabezados de filas y columnas. Para matrices grandes, incluir dimensiones, resumen y archivo adjunto completo; no truncar silenciosamente.

## Lenguaje

Usar español técnico claro, definir siglas en su primera aparición y separar interpretación física de resultados numéricos. No afirmar exactitud absoluta; reportar tolerancias.

## Tools relacionadas

`generate_report.py`, `matrix_formatter.py`, `plot_results.py`, `export_results.py`.

## Validaciones

Confirmar que todos los valores del reporte provienen de artefactos de la misma ejecución, que las unidades son consistentes y que el estado de validación se muestra.

## Ejemplo de cierre

`Resultado aceptado: PASS. El residuo nodal y KCL están dentro de las tolerancias configuradas. El circuito pertenece al alcance lineal AC del MVP.`

## Errores y limitaciones

No inventar imágenes, ecuaciones faltantes ni resultados de referencia. No presentar comparación con SPICE si no existe archivo o ejecución documentada.

## Criterio de terminación

El reporte es autocontenido, auditable, reproducible y distingue claramente entrada, cálculo, validación e interpretación.

## Referencias

- Material del curso: `Matematicas_Lectura05_WW40'26-B`.
- Repositorio del proyecto y contrato común de datos.
- Este skill no sustituye la ejecución de las tools deterministas.
