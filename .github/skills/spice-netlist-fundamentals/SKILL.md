---
name: spice-netlist-fundamentals
description: Interpreta y valida el subconjunto educativo de netlists SPICE. Usar cuando el usuario proporcione o solicite analizar archivos .cir, .sp o .net.
license: Academic use
---

# spice-netlist-fundamentals

## Objetivo

Definir la gramática mínima, las reglas léxicas y los mensajes de error para convertir un netlist en una representación estructurada reproducible.

## Condiciones de activación

Usar al recibir un netlist, una línea SPICE, una solicitud de listar componentes o una petición de preparar el circuito para análisis.

## Alcance MVP

Soportar inicialmente:
- `R`: resistor.
- `G`: conductancia explícita del proyecto, sólo si la gramática del curso la habilita.
- `C`: capacitor.
- `L`: inductor.
- `I`: fuente independiente de corriente DC o AC.
- `V`: fuente independiente de voltaje DC o AC.
- `E`: fuente de voltaje controlada por voltaje (VCVS).
- Directivas `.AC`, `.OP` y `.END` en el subconjunto documentado.
- Directivas `.PRINT AC` y `.PROBE AC` para `V(nodo)` e `I(componente)`.
- Directiva `.OPTION` con ajustes `NAME=VALUE`, conservados como metadatos.
- Comentarios cuyo primer carácter significativo es `*`.

No soportar inicialmente subcircuitos, modelos de semiconductores, parámetros, expresiones arbitrarias, análisis transitorio general ni dialectos propietarios.

## Gramática mínima

```text
R<id> <n+> <n-> <value>
C<id> <n+> <n-> <value>
L<id> <n+> <n-> <value>
I<id> <n+> <n-> DC <value>
I<id> <n+> <n-> AC <magnitude> [phase_deg]
I<id> <n+> <n-> DC <value> AC <magnitude> [phase_deg]
V<id> <n+> <n-> DC <value>
V<id> <n+> <n-> AC <magnitude> [phase_deg]
V<id> <n+> <n-> DC <value> AC <magnitude> [phase_deg]
E<id> <n+> <n-> <nc+> <nc-> <gain>
.AC LIN <points> <f_start> <f_stop>
.AC DEC <points_per_decade> <f_start> <f_stop>
.PRINT AC V(node) I(component) ...
.PROBE AC V(node) I(component) ...
.OPTION NAME=VALUE ...
.OP
.END
```

## Procedimiento

1. Conservar cada línea original y su número.
2. Eliminar líneas vacías y comentarios completos.
3. Separar tokens sin destruir el texto fuente.
4. Identificar tipo por el primer carácter del nombre.
5. Validar número de tokens por variante.
6. Normalizar nodos y valores mediante `engineering-units-and-conventions`.
7. Detectar identificadores duplicados.
8. Detectar ausencia del nodo `0`.
9. Crear objetos estructurados; no construir matrices todavía.
10. Emitir errores con número de línea, token y corrección sugerida.

`.OP` puede coexistir con `.AC`; el flujo de barrido ejecuta `.AC`. `.OPTION`
se valida y conserva, pero no activa funciones específicas de simuladores
externos.

## Contrato de salida

Cada elemento debe contener `name`, `type`, `node_from`, `node_to`, `value_si`, `unit`, `source_kind`, `dc_value_si`, `ac_magnitude`, `ac_phase_deg`, `source_line` y `line_number`, según corresponda. Una `E` también contiene `control_node_plus` y `control_node_minus`.

## Reglas de decisión

Si una línea usa un elemento no soportado, detener el análisis y reportarlo. No omitir silenciosamente. Si falta `.END`, emitir advertencia configurable; si falta tierra, emitir error. No aceptar más de una directiva `.AC`. Las mediciones de corriente usan identificadores existentes y las de tensión, nodos existentes.

## Tools relacionadas

`parse_netlist.py`, `validate_netlist.py`, `engineering_values.py`, `build_circuit_model.py`.

## Validaciones

Identificadores únicos, nodo de referencia presente, nodos distintos cuando el elemento lo requiera, valor permitido, directiva coherente y ausencia de tokens sobrantes no reconocidos.

## Ejemplo válido

```spice
* Divisor resistivo
V1 1 0 DC 10
R1 1 2 1k
R2 2 0 2k
.OP
.END
```

## Ejemplos inválidos

```spice
R1 1 2       ; valor faltante
R1 2 0 1k    ; nombre duplicado si ya existe R1
Q1 1 2 0 MOD ; transistor no soportado por el MVP
```

## Criterio de terminación

El netlist se transforma en un modelo estructurado sin pérdida de trazabilidad y todos los errores bloqueantes han sido resueltos.

## Referencias

- Material del curso: `Matematicas_Lectura05_WW40'26-B`.
- Repositorio del proyecto y contrato común de datos.
- Este skill no sustituye la ejecución de las tools deterministas.
