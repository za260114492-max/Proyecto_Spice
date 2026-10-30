---
name: engineering-units-and-conventions
description: Normaliza unidades, prefijos SPICE, fasores, signos, orientación, tolerancias y orden de nodos y ramas. Usar antes de interpretar valores, construir grafos, matrices o reportes.
license: Academic use
---

# engineering-units-and-conventions

## Objetivo

Establecer una única convención transversal para todos los skills y tools del simulador educativo. Ningún otro skill debe redefinir estas reglas localmente.

## Condiciones de activación

Usar cuando una solicitud incluya netlists, valores con prefijos, unidades, fasores, polaridades, nodos, ramas, matrices o tolerancias numéricas.

## Alcance

Incluye unidades SI, prefijos de ingeniería, convención de corriente y voltaje de rama, nodo de referencia, orden determinista, representación compleja y tolerancias. No interpreta la sintaxis completa del netlist ni resuelve circuitos.

## Convenciones obligatorias

1. El nodo de referencia es `0`. También puede aceptarse `GND`, pero debe normalizarse a `0`.
2. Los nodos no de referencia se ordenan de forma determinista: numéricos en orden ascendente y después alfanuméricos en orden lexicográfico.
3. Las ramas conservan el orden de aparición del netlist, a menos que el usuario solicite expresamente otro orden.
4. Cada componente de dos terminales define una rama orientada desde el primer nodo declarado al segundo.
5. La corriente positiva circula del primer nodo al segundo. El voltaje de rama es positivo del primer nodo al segundo.
6. Matriz de incidencia: `+1` si la rama sale del nodo, `-1` si entra y `0` si no incide.
7. Unidades base: ohm, siemens, farad, henry, volt, ampere, hertz y segundo.
8. Prefijos aceptados, sin distinguir mayúsculas salvo conflicto documentado: `t`, `g`, `meg`, `k`, `m`, `u`, `n`, `p`, `f`.
9. En sintaxis SPICE, `m` significa mili y `meg` significa mega. No interpretar `M` como mega sin una regla explícita del parser.
10. En AC usar `s = j*omega = j*2*pi*f` y números complejos de doble precisión.

## Tabla de factores

| Prefijo | Factor |
|---|---:|
| t | 1e12 |
| g | 1e9 |
| meg | 1e6 |
| k | 1e3 |
| m | 1e-3 |
| u | 1e-6 |
| n | 1e-9 |
| p | 1e-12 |
| f | 1e-15 |

## Tolerancias

Usar tolerancia absoluta y relativa configurables. Valor inicial sugerido para casos académicos: `atol=1e-10`, `rtol=1e-8`. No declarar un resultado válido únicamente con una de ellas. Reportar número de condición cuando el sistema sea sensible.

## Entradas requeridas

Texto del valor, unidad esperada, contexto de análisis y, cuando corresponda, orientación de la rama.

## Salida esperada

Valor normalizado en SI, unidad, texto original, convención aplicada y advertencias. Nunca descartar el texto original.

## Tools relacionadas

`engineering_values.py`, `build_circuit_model.py`, `matrix_formatter.py`, `validate_solution.py`.

## Validaciones

Verificar dimensiones físicas, valores finitos, prefijos reconocidos, nodos válidos, orientación consistente y ausencia de colisiones de identificadores.

## Ejemplos

Válidos:
- `1k` -> `1000.0 ohm`
- `10u` -> `1e-5 farad`
- `3.3meg` -> `3.3e6 ohm`

Inválidos:
- `10x` -> prefijo no soportado.
- `R1 1 2` -> valor faltante.

## Criterio de terminación

La salida está normalizada, conserva trazabilidad al valor original y no contiene ambigüedades de signo, unidad u orden.

## Referencias

- Material del curso: `Matematicas_Lectura05_WW40'26-B`.
- Repositorio del proyecto y contrato común de datos.
- Este skill no sustituye la ejecución de las tools deterministas.
