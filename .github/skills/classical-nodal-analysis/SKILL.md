---
name: classical-nodal-analysis
description: Construye y resuelve la formulación nodal clásica para circuitos lineales compatibles. Usar cuando todas las ramas puedan representarse por admitancias y fuentes de corriente.
license: Academic use
---

# classical-nodal-analysis

## Objetivo

Obtener voltajes nodales mediante un sistema reducido y recuperar corrientes y voltajes de rama con trazabilidad.

## Condiciones de activación

Usar después de validar netlist, topología, matriz de incidencia y modelos. Activar sólo si el circuito no contiene ramas incompatibles con nodal clásico.

## Compatibilidad

Compatible con resistores, conductancias, capacitores en AC, inductores en AC no nula bajo el modelo aprobado y fuentes independientes de corriente. Una fuente ideal de voltaje entre nodos desconocidos requiere supernodo o, preferentemente en este proyecto, Tableau/MNA.

## Formulación

Con la convención del curso, construir la ecuación nodal aprobada, por ejemplo `A @ Y @ A.T @ Vn = -A @ J`. El signo exacto del vector fuente debe derivarse de la orientación común y mantenerse idéntico en código, tests y reportes.

## Procedimiento

1. Clasificar ramas compatibles.
2. Construir A reducida.
3. Construir Y diagonal o por bloques según modelos aprobados.
4. Construir J con orientación consistente.
5. Ensamblar M y b.
6. Diagnosticar conectividad, rango y condición.
7. Resolver `M @ Vn = b` con NumPy.
8. Recuperar `Vb = A.T @ Vn`.
9. Recuperar corrientes de rama por modelos constitutivos.
10. Validar KCL y el residuo.

## Entradas requeridas

Circuito estructurado, A reducida, frecuencia si aplica, modelos de admitancia, vector de fuentes y tolerancias.

## Salida esperada

Voltajes nodales y de rama, corrientes, matriz M, vector b, métricas numéricas y diagnóstico.

## Tools relacionadas

`build_nodal_system.py`, `solve_linear_system.py`, `validate_solution.py`, `matrix_formatter.py`.

## Validaciones

`||M Vn-b||`, `||A I||`, ecuaciones constitutivas, valores finitos, rango completo y condición reportada.

## Error obligatorio

Si existe una fuente ideal de voltaje no tratable, no crear una admitancia ficticia. Informar que se requiere Tableau o MNA.

## Ejemplo

Una red resistiva excitada por fuente de corriente es compatible. Un divisor excitado por fuente ideal de voltaje requiere una formulación que represente esa rama especial.

## Criterio de terminación

Se obtuvo una solución validada o un diagnóstico explícito de incompatibilidad/singularidad.

## Referencias

- Material del curso: `Matematicas_Lectura05_WW40'26-B`.
- Repositorio del proyecto y contrato común de datos.
- Este skill no sustituye la ejecución de las tools deterministas.
