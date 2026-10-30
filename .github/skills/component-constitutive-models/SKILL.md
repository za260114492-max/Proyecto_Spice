---
name: component-constitutive-models
description: Define ecuaciones constitutivas y stamps para componentes lineales del simulador educativo. Usar al construir Y, Z, W, Y nodal o fuentes.
license: Academic use
---

# component-constitutive-models

## Objetivo

Mantener una biblioteca única de modelos eléctricos para evitar discrepancias entre análisis nodal, Tableau y validación.

## Condiciones de activación

Usar cuando se deba clasificar un componente, generar su ecuación corriente-voltaje o ensamblar matrices.

## Forma general Tableau

Usar `Y*Vb + Z*I = W`, con una ecuación por rama simple o un bloque de ecuaciones aprobado para elementos acoplados.

## Modelos básicos

| Elemento | Ecuación | Y | Z | W |
|---|---|---:|---:|---:|
| Resistor R | V - R I = 0 | 1 | -R | 0 |
| Conductancia G | G V - I = 0 | G | -1 | 0 |
| Capacitor C, AC | s C V - I = 0 | sC | -1 | 0 |
| Inductor L, AC | V - s L I = 0 | 1 | -sL | 0 |
| Fuente de voltaje E | V = E | 1 | 0 | E |
| Fuente de corriente J | I = J | 0 | 1 | J |

## Contribuciones nodales

- Resistor: admitancia `1/R` entre sus nodos.
- Conductancia: admitancia `G`.
- Capacitor en AC: admitancia `s*C`.
- Inductor en AC: admitancia `1/(s*L)` sólo si la formulación y frecuencia lo permiten.
- Fuente de corriente: contribuye al vector de inyección con signo determinado por orientación.
- Fuente ideal de voltaje: no es compatible directamente con nodal clásico; enrutar a Tableau o MNA.

## Procedimiento

1. Identificar el tipo normalizado.
2. Confirmar el modo de análisis.
3. Obtener el modelo aplicable.
4. Generar stamp con índices y unidades.
5. Registrar la ecuación y el componente que originaron cada entrada.
6. Rechazar combinaciones no soportadas.

## Elementos posteriores al MVP

Fuentes controladas y op-amps ideales requieren modelos de bloque y ramas especiales. No improvisar sus stamps. Incorporarlos sólo cuando existan ecuaciones, convenciones, tests y referencias aprobadas.

## Tools relacionadas

`stamp_elements.py`, `build_constitutive_matrices.py`, `build_nodal_system.py`, `build_tableau_system.py`.

## Validaciones

Unidades, dimensiones, signos, dependencia con `s`, consistencia entre modelo y modo, y correspondencia con la rama.

## Ejemplo

Para `R1 1 2 1k`, Tableau registra `V_R1 - 1000*I_R1 = 0`; nodal registra `G=0.001 S` entre N1 y N2.

## Criterio de terminación

Cada componente soportado tiene ecuación, stamp, unidades, prueba positiva y prueba de error.

## Referencias

- Material del curso: `Matematicas_Lectura05_WW40'26-B`.
- Repositorio del proyecto y contrato común de datos.
- Este skill no sustituye la ejecución de las tools deterministas.
