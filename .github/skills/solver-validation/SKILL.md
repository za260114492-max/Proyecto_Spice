---
name: solver-validation
description: Valida resultados matemáticos, eléctricos y numéricos antes de que el agente los entregue. Usar después de cualquier solución y ante singularidad o mal condicionamiento.
license: Academic use
---

# solver-validation

## Objetivo

Convertir la validación en un gate obligatorio. El agente no debe aceptar una solución sólo porque NumPy regresó un vector.

## Condiciones de activación

Usar después de `solve_linear_system.py`, en cada punto AC, al comparar formulaciones o ante errores de rango/condición.

## Métricas obligatorias

- Residuo global: `r = M@x-b`.
- Residuo normalizado: `||r|| / (||M||*||x|| + ||b||)`.
- KCL: `||A@I||`.
- Relación rama-nodo: `||Vb-A.T@Vn||`.
- Constitutivas: `||Y@Vb+Z@I-W||`.
- Tableau: `||T@X-Wp||`.
- Rango y número de condición.
- Error absoluto y relativo contra referencia, si existe.

## Procedimiento

1. Verificar dimensiones y valores finitos.
2. Calcular rango y número de condición.
3. Intentar solución sólo si el sistema es apropiado.
4. Calcular residuos correspondientes a la formulación.
5. Comparar con `atol` y `rtol` comunes.
6. Clasificar: PASS, WARN o FAIL.
7. Ejecutar diagnóstico topológico si hay singularidad.
8. Emitir evidencias y no sólo una etiqueta.

## Diagnósticos

Buscar nodo flotante, circuito desconectado, ecuación duplicada, rama sin modelo, fuente ideal incompatible, fuentes en conflicto, componente con valor cero/no finito y orden de índices inconsistente.

## Reglas de aceptación

PASS cuando todas las métricas obligatorias están dentro de tolerancia. WARN cuando los residuos pasan pero la condición es alta o existe limitación conocida. FAIL ante residuo excedido, matriz singular, NaN/Inf o inconsistencia física/estructural.

## Tools relacionadas

`validate_solution.py`, `diagnose_singularity.py`, `compare_reference.py`, `solve_linear_system.py`.

## Salida esperada

Reporte JSON/Markdown con métricas, tolerancias, clasificación, diagnósticos y acciones sugeridas.

## Ejemplo

`numpy.linalg.solve` devuelve valores, pero `cond(M)` es muy alta: marcar WARN y limitar cifras significativas; no declarar el circuito plenamente confiable.

## Error obligatorio

Nunca ocultar una validación fallida ni reemplazarla con una explicación narrativa.

## Criterio de terminación

Existe un reporte de validación legible por máquina y por persona, asociado a la ejecución.

## Referencias

- Material del curso: `Matematicas_Lectura05_WW40'26-B`.
- Repositorio del proyecto y contrato común de datos.
- Este skill no sustituye la ejecución de las tools deterministas.
