---
name: ac-frequency-analysis
description: Aplica análisis fasorial AC en una frecuencia o barrido, con magnitud, fase y decibeles. Usar para circuitos lineales con C y L.
license: Academic use
---

# ac-frequency-analysis

## Objetivo

Definir un proceso reproducible para actualizar modelos dependientes de frecuencia, resolver cada punto y reportar respuestas complejas.

## Condiciones de activación

Usar con directiva `.AC`, solicitudes de frecuencia, Bode, magnitud, fase, impedancia o ganancia.

## Fundamentos

- `omega = 2*pi*f`.
- `s = j*omega`.
- `Y_C = s*C`.
- `Z_L = s*L` y `Y_L = 1/(s*L)` cuando se use formulación nodal.
- Magnitud en dB: `20*log10(abs(H))` para relación de voltajes/corrientes; documentar cualquier otra convención.
- Fase en grados: `angle(H)*180/pi`.

## Tipos de barrido

- Punto único.
- `LIN`: puntos uniformes entre inicio y fin.
- `DEC`: puntos por década.
- `OCT`: opcional en versiones posteriores.

## Procedimiento

1. Validar frecuencias positivas para AC, salvo tratamiento explícito de DC.
2. Construir el vector de frecuencias.
3. Para cada frecuencia, calcular s.
4. Actualizar stamps dependientes de s.
5. Ensamblar y resolver el sistema.
6. Validar el punto.
7. Extraer observables solicitados.
8. Calcular magnitud, fase y dB.
9. Exportar datos y gráficas con unidades.

## Manejo de f=0

No evaluar automáticamente `1/(sL)` en `f=0`. Separar el análisis DC o aplicar el modelo límite definido. Informar singularidades físicas o numéricas.

## Entradas requeridas

Circuito, formulación seleccionada, frecuencias, observables y tolerancias.

## Salida esperada

Resultados complejos por frecuencia, magnitud, fase, dB, unidades y validaciones por punto.

## Tools relacionadas

`solve_ac_sweep.py`, `stamp_elements.py`, `plot_results.py`, `export_results.py`.

## Validaciones

Frecuencias ordenadas, resultados finitos, residuos por punto, continuidad razonable sin usarla como sustituto de validación, y consistencia de unidades.

## Ejemplo

Para un filtro RC, reportar `Vout/Vin`, magnitud, fase y valores de R/C empleados. No presentar sólo la gráfica.

## Criterio de terminación

Todos los puntos válidos han sido resueltos y los puntos fallidos están identificados con diagnóstico.

## Referencias

- Material del curso: `Matematicas_Lectura05_WW40'26-B`.
- Repositorio del proyecto y contrato común de datos.
- Este skill no sustituye la ejecución de las tools deterministas.
