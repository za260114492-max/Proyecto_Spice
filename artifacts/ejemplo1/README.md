# Ejemplo 1 reconstruido desde matriz de incidencia

Este directorio contiene el netlist inferido de la matriz reducida entregada (`incidence_source.md`) y del ejemplo `filtro_activo_EA1`. No es un netlist original entregado por el usuario.

## Matriz de incidencia de entrada

`incidence_source.md` es una copia sin cambios de `matriz_A1.md`, el archivo proporcionado por el usuario. Su SHA-256 es `F5D8723D9771F4CE8C0ADB302E7ACC785A4388317A1423BD7E1EF69F93907F21`. `incidence_source.json` conserva exactamente la matriz reducida 5x6, con filas N1-N5 y columnas B2-B7.

El solucionador Tableau requiere las columnas de todas las ramas. `incidence.json` y `incidence.npz` incorporan las columnas B2-B7 directamente de esa matriz y agregan B1 y B8 desde las conexiones explícitas del netlist reconstruido. El ensamblador Tableau verificó que la matriz extendida coincide con los extremos de las ramas. La versión generada anteriormente se preserva como `incidence_generated.json`, `incidence_generated.md` e `incidence_generated.npz`.

## Correspondencia asumida

| Rama | Componente | Terminales | Valor |
|---|---|---|---|
| B2 | C4 | 1 -> 2 | 1 uF |
| B3 | C5 | 2 -> 3 | 1 uF |
| B4 | R1 | 3 -> 0 | 1 kOhm |
| B5 | R2 | 4 -> 0 | 3.3 kOhm |
| B6 | R5 | 4 -> 5 | 1 kOhm |
| B7 | R3 | 2 -> 5 | 3.3 kOhm |

Se añadieron B1 (V1 entre nodo 1 y tierra, AC 10 mV) y B8 (VCVS E_A1 entre nodo 5 y tierra, controlada por la diferencia V(3)-V(4), ganancia 1e6), además del barrido `.AC DEC 100 1 1MEG`, siguiendo el ejemplo EA1. La matriz solo fija la topología orientada de B2-B7; no determina por sí sola el tipo o valor de sus componentes ni los elementos B1/B8.

## Resultado

El barrido Tableau AC produjo 601 puntos; consulta `ac_sweep.json` para la validación individual por frecuencia. El sistema Tableau y la solución independientes de 1 MHz están en `endpoint_tableau.json` y `endpoint_validation.json`. `report.md` reúne la matriz, stamps, sistema, resultados y limitaciones. No se realizó comparación con un simulador externo.