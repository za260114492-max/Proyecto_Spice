---
name: tableau-formulation
description: Construye la formulación Tableau completa combinando KCL, KVL y ecuaciones constitutivas. Usar para análisis educativo con variables de rama explícitas.
license: Academic use
---

# tableau-formulation

## Objetivo

Ensamblar un sistema único que conserve voltajes de rama, corrientes de rama y voltajes nodales para explicar la estructura completa del circuito.

## Condiciones de activación

Usar cuando se soliciten Y, Z, W, T, X; cuando existan fuentes ideales; o cuando el propósito sea mostrar explícitamente KCL, KVL y modelos de rama.

## Ecuaciones base

```text
A.T @ Vn - Vb = 0
Y @ Vb + Z @ I = W
A @ I = 0
```

Con el orden `X = [Vb; I; Vn]`:

```text
T = [[I, 0, -A.T],
     [Y, Z,  0   ],
     [0, A,  0   ]]
Wp = [0; W; 0]
T @ X = Wp
```

## Procedimiento

1. Confirmar `b` ramas y `n` nodos no de referencia.
2. Verificar A de dimensión `n x b`.
3. Construir Y, Z y W con `component-constitutive-models`.
4. Etiquetar filas y columnas con ramas.
5. Ensamblar T de dimensión `(2b+n) x (2b+n)`.
6. Crear mapa de índices para Vb, I y Vn.
7. Diagnosticar rango y condición.
8. Resolver sin invertir T explícitamente.
9. Separar X y validar las tres familias de ecuaciones.

## Trazabilidad

Cada fila de Y/Z/W debe registrar componente, rama, ecuación constitutiva y unidad. Cada bloque de T debe identificarse en el reporte.

## Tools relacionadas

`build_constitutive_matrices.py`, `build_tableau_system.py`, `solve_linear_system.py`, `validate_solution.py`.

## Validaciones

Dimensiones, orden de ramas, `||A I||`, `||Vb-A.T Vn||`, `||Y Vb+Z I-W||` y `||T X-Wp||`.

## Elementos multiterminales

Representarlos sólo mediante bloques aprobados y ramas auxiliares documentadas. Relacionar explícitamente ramas de entrada y salida cuando el modelo lo requiera.

## Ejemplo

Una fuente ideal de voltaje usa `Y=1`, `Z=0`, `W=E` para su ecuación de rama. Su corriente permanece como incógnita dentro de X.

## Errores

No ensamblar T si Y/Z/W no tienen dimensión b x b, si W no tiene b entradas o si las etiquetas no coinciden.

## Criterio de terminación

T y Wp están ensamblados, X ha sido separado correctamente y todos los residuos pasan tolerancia.

## Referencias

- Material del curso: `Matematicas_Lectura05_WW40'26-B`.
- Repositorio del proyecto y contrato común de datos.
- Este skill no sustituye la ejecución de las tools deterministas.
