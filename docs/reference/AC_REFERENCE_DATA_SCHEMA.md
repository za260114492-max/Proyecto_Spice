# Esquema de referencia para comparación AC

`compare_reference.py` consume un archivo JSON con este contrato (`schema_version`
`1.0`). Los datos de referencia deben proceder de una ejecución analítica aprobada
o de un simulador identificado; no se deben completar con resultados inventados.

| Campo | Requisito |
|---|---|
| `schema_version` | `"1.0"` |
| `simulator` | Nombre del simulador o fuente analítica aprobada |
| `simulator_version` | Versión como texto, o `null` si no aplica/no se conoce |
| `analysis` | `"AC"` |
| `frequency_unit` | `"Hz"` |
| `circuit_signature` | Huella del circuito normalizado, copiada de `ac_sweep.json` |
| `input_node`, `output_node` | Nodos que definen \(H=V_{out}/V_{in}\), deben coincidir con el barrido |
| `results` | Filas no vacías, ordenadas por frecuencia, con frecuencia en Hz, ganancia en dB y fase en grados |

Estructura:

```json
{
  "schema_version": "1.0",
  "simulator": "Nombre del simulador o referencia analítica",
  "simulator_version": "versión",
  "analysis": "AC",
  "frequency_unit": "Hz",
  "circuit_signature": "<circuit_signature de ac_sweep.json>",
  "input_node": "1",
  "output_node": "2",
  "results": [
    {
      "frequency_hz": 100.0,
      "gain_db": -0.17,
      "phase_deg": -32.1
    }
  ]
}
```

Los valores de la fila anterior sólo ilustran el formato y **no son una referencia
válida para un circuito concreto**. Deben sustituirse por datos documentados de la
misma topología, valores de componentes, fuentes, nodos y condiciones de análisis.
La huella incluye conexiones orientadas, tipos, valores SI y definiciones de fuentes.
Se puede copiar directamente del campo `circuit_signature` del resultado del barrido.

La comparación exige una correspondencia uno a uno de frecuencias dentro de
`--frequency-rtol`; no interpola ni extrapola. Por defecto, clasifica `PASS` si
cada punto queda dentro de `0.1 dB` y `1 grado`, parámetros configurables por CLI.
El error relativo de ganancia se calcula en escala lineal a partir de los valores en
dB. El error de fase es circular, por lo que considera la periodicidad de 360 grados.

La comparación produce JSON y CSV. El CSV incluye los valores del agente y de
referencia, errores absoluto/firmado/relativo, estado de validación del punto y
resultado de aceptación.
