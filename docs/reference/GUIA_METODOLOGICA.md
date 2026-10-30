# Guia metodologica del agente SPICE educativo

> Conversion estructurada y completa de [la guia original en DOCX](./originals/Guia_Metodologica_Custom_Agent_SPICE_Educativo.docx). Use esta version Markdown como copia consultable y editable; el DOCX original se conserva para referencia de formato.

: GUÍA METODOLÓGICA

Desarrollo de un Custom Agent educativo para simulación de circuitos tipo SPICE

Netlist → Grafo orientado → Matrices → Solución → Validación

| Propósito del documento Orientar a los estudiantes en la construcción gradual, verificable y explicable de un agente basado en GitHub Copilot que analice netlists y ejecute un motor determinista de simulación desarrollado en Python. |
| --- |

Profesor: Dr. Francisco E. Rangel-Patiño

Matemáticas Avanzadas · Programa 2026 Maestría en Ingeniería Electrónica Tecnológico Superior de Jalisco

Versión metodológica para uso académico

## Cómo utilizar esta guía

Esta guía organiza el proyecto como una experiencia de ingeniería basada en evidencia. El objetivo no es pedirle a un modelo de lenguaje que calcule matrices, sino construir un agente que orqueste herramientas deterministas, explique el procedimiento y entregue resultados verificables.

| Principio rector El agente interpreta, coordina y explica. Los scripts de Python procesan, ensamblan, resuelven y validan. Ningún resultado matricial debe depender únicamente de generación de texto. |
| --- |

| Audiencia | Uso recomendado |
| --- | --- |
| Estudiantes | Implementar por equipos los skills, scripts, pruebas y documentación. |
| Profesor | Definir convenciones, aprobar el alcance, revisar entregables y validar la metodología. |
| Revisores | Evaluar trazabilidad, rigor matemático, reproducibilidad y claridad pedagógica. |

## Resumen ejecutivo

El proyecto propone un Custom Agent educativo de GitHub Copilot inspirado en el flujo de los primeros simuladores de circuitos. A partir de un netlist, el sistema deberá identificar componentes, nodos y ramas; construir un grafo orientado; generar la matriz de incidencia; ensamblar formulaciones nodales o Tableau; resolver el sistema con NumPy; validar las leyes de Kirchhoff y las ecuaciones constitutivas; y producir un reporte explicable.

| Capa | Responsabilidad | Resultado principal |
| --- | --- | --- |
| Agente | Orquestar el flujo, seleccionar skills/tools y explicar resultados. | Respuesta trazable y pedagógica. |
| Skills | Conservar teoría, reglas, convenciones y metodología. | Decisiones consistentes. |
| Tools Python | Procesar y calcular de forma determinista. | Matrices y solución reproducibles. |
| Pruebas | Comparar contra casos analíticos y simuladores de referencia. | Evidencia de corrección. |
| Reportes | Presentar datos, ecuaciones, matrices y diagnósticos. | Entregable legible y auditable. |

## Alcance del proyecto

### Alcance inicial (MVP: Producto Mínimo Viable)

1. No buscamos desarrollar un simulador completo tipo HSPICE, Spectre, ADS, o LTspice, porque eso tomaría años. Buscamos desarrollar la versión mínima funcional que demuestre que la arquitectura funciona.
- Netlists lineales y concentrados.
- Resistores, conductancias, capacitores, inductores y fuentes independientes.
- Análisis nodal clásico para circuitos compatibles.
- Análisis AC en una frecuencia y barrido en frecuencia.
- Formulación Tableau para fines educativos.
- Solución con NumPy y visualización del grafo.
- Validación de KCL, KVL, ecuaciones constitutivas y residuos del sistema.
### Fuera del alcance inicial

- Modelos completos de semiconductores.
- Análisis no lineal con Newton-Raphson.
- Análisis transitorio de propósito general.
- Parasitismos distribuidos, líneas de transmisión y modelos RF avanzados.
- Compatibilidad completa con todos los dialectos SPICE.
- Sustituir simuladores comerciales o certificarse para diseño de producción.
| Criterio de expansión La funcionalidad se amplía únicamente cuando el núcleo anterior tiene pruebas automatizadas, resultados de referencia y documentación aprobada. |
| --- |

## 1. Arquitectura metodológica

La arquitectura se divide en cinco capas. Esta separación evita mezclar razonamiento del agente con cálculos numéricos y permite asignar trabajo a equipos independientes.

| Usuario / Netlist ↓ Custom Agent de GitHub Copilot ↓ selecciona skills y ejecuta tools Parser → Modelo del circuito → Grafo → Matrices → Solver → Validación ↓ Reporte explicable + artefactos + diagnóstico |
| --- |

| Capa | Contenido | Regla de diseño |
| --- | --- | --- |
| Interfaz | Custom Agent, prompt files y respuestas. | No realiza cálculos críticos de memoria. |
| Conocimiento | 10 skills metodológicos. | Las convenciones deben ser únicas y compartidas. |
| Dominio | Modelo de circuito, nodos, ramas y componentes. | Cada objeto conserva identidad y unidades. |
| Cálculo | Matrices y solver NumPy. | Funciones puras, deterministas y probadas. |
| Verificación | Pruebas, residuos y comparación. | No entregar resultados que no hayan pasado validación. |

### 1.1 Flujo funcional obligatorio

1. Leer y validar el netlist.
1. Normalizar valores y unidades.
1. Crear el modelo interno del circuito.
1. Enumerar nodos y ramas con un orden determinista.
1. Construir el grafo orientado.
1. Construir la matriz de incidencia completa y reducida.
1. Seleccionar la formulación compatible.
1. Ensamblar matrices y vectores.
1. Resolver el sistema lineal.
1. Recuperar variables físicas.
1. Ejecutar validaciones matemáticas y eléctricas.
1. Generar el reporte trazable.
### 1.2 Contrato común de datos

Todos los skills y tools deben compartir el mismo contrato de datos. Como mínimo, cada componente debe conservar los campos siguientes:

| Campo | Descripción | Ejemplo |
| --- | --- | --- |
| name | Identificador único del componente. | R1 |
| type | Tipo normalizado. | resistor |
| node_from | Nodo positivo o de origen. | 1 |
| node_to | Nodo negativo o destino. | 2 |
| value_si | Valor convertido a SI. | 1000.0 |
| unit | Unidad física. | ohm |
| branch_id | Rama asignada. | B2 |
| source_line | Línea original del netlist. | R1 1 2 1k |

## 2. Paquete de 10 skills de conocimiento

Cada skill debe vivir en una carpeta independiente y contener un archivo obligatorio SKILL.md. El archivo debe incluir nombre, descripción, condiciones de uso, conocimiento del dominio, procedimiento, restricciones, ejemplos y referencias a tools. GitHub describe los skills como módulos reutilizables de instrucciones que pueden acompañarse de scripts y recursos.

| # | Skill | Objetivo | Entregable mínimo |
| --- | --- | --- | --- |
| 1 | spice-netlist-fundamentals | Definir el subconjunto de netlist aceptado, comentarios, directivas, nodos, referencias, nombres y prefijos. | Gramática documentada, ejemplos válidos/no válidos y mensajes de error esperados. |
| 2 | circuit-graph-theory | Transformar nodos en vértices y componentes en ramas orientadas; diferenciar incidencia y adyacencia. | Reglas de orientación, numeración y manejo de ramas paralelas. |
| 3 | incidence-matrix-method | Definir la matriz completa/reducida y su convención de signos. | Procedimiento reproducible y verificaciones estructurales. |
| 4 | component-constitutive-models | Documentar el modelo de cada elemento y su contribución matricial. | Biblioteca de ecuaciones y stamps aprobados. |
| 5 | classical-nodal-analysis | Definir compatibilidad, ensamble y solución de la formulación nodal. | Flujo para obtener Vn y recuperar variables de rama. |
| 6 | tableau-formulation | Ensamblar KCL, KVL y ecuaciones constitutivas. | Construcción trazable de Y, Z, W, T y W'. |
| 7 | ac-frequency-analysis | Definir fasores, s=jω, barridos, magnitud, fase y dB. | Reglas para frecuencia única, barridos y f=0. |
| 8 | engineering-units-and-conventions | Normalizar unidades, prefijos, polaridades, tolerancias y formato complejo. | Convenciones únicas para todo el repositorio. |
| 9 | solver-validation | Definir residuos, singularidad, condición y diagnósticos. | Criterios de aceptación y rechazo. |
| 10 | explainable-circuit-reporting | Estandarizar cómo se presentan datos, ecuaciones, matrices y advertencias. | Plantilla de reporte Markdown auditable. |

### 2.1 Plantilla obligatoria de cada SKILL.md

| --- name: <skill-name> description: <qué hace y cuándo debe activarse> --- # Objetivo # Alcance # Entradas requeridas # Convenciones # Procedimiento # Reglas de decisión # Validaciones # Errores y limitaciones # Ejemplos # Tools relacionadas # Referencias |
| --- |

| Regla de consistencia Los skills no deben redefinir convenciones locales. Deben referenciar engineering-units-and-conventions para unidades, signos, orientación, orden, tolerancias y formato de salida. |
| --- |

### 2.2 Criterios de calidad para aprobar un skill

- Tiene una condición de activación específica.
- Distingue conocimiento de instrucciones ejecutables.
- Usa la misma notación que el curso.
- Incluye al menos un ejemplo positivo y uno negativo.
- Indica qué tool debe ejecutar el agente.
- Define fallas esperadas y mensajes claros.
- No solicita al LLM efectuar cálculos críticos sin tool.
- Incluye criterios verificables de terminación.
## 3. Tools: motor determinista en Python

Los scripts son la fuente de verdad computacional. Cada tool debe ofrecer una interfaz por línea de comandos y, de ser posible, funciones importables para pruebas unitarias.

| # | Script | Responsabilidad |
| --- | --- | --- |
| 1 | parse_netlist.py | Interpretar archivos .cir/.sp/.net y producir datos estructurados. |
| 2 | validate_netlist.py | Detectar sintaxis, duplicados, tierra faltante y elementos no soportados. |
| 3 | build_circuit_model.py | Crear Circuit, Node, Branch, Element, Source y AnalysisCommand. |
| 4 | build_oriented_graph.py | Generar topología, tabla de conectividad y visual PNG/SVG. |
| 5 | build_incidence_matrix.py | Crear matrices de incidencia completa y reducida con etiquetas. |
| 6 | stamp_elements.py | Aplicar stamps por tipo de componente. |
| 7 | build_constitutive_matrices.py | Construir Y, Z y W con trazabilidad por renglón. |
| 8 | build_nodal_system.py | Construir el sistema nodal y evaluar compatibilidad. |
| 9 | build_tableau_system.py | Construir T, W' y el mapa de índices de X. |
| 10 | solve_linear_system.py | Resolver con NumPy y calcular métricas numéricas. |
| 11 | solve_ac_sweep.py | Ejecutar frecuencia única y barridos. |
| 12 | validate_solution.py | Validar KCL, KVL, constitutivas y residuo global. |
| 13 | compare_reference.py | Comparar contra solución analítica o simulador de referencia. |
| 14 | generate_report.py | Crear reporte Markdown reproducible. |
| 15 | plot_results.py | Crear grafo, magnitud, fase y comparaciones. |

### 3.1 Tools de soporte

| Script | Uso |
| --- | --- |
| engineering_values.py | Conversión robusta de 1k, 10u, 3.3meg y otros valores. |
| matrix_formatter.py | Presentación con encabezados en Markdown, LaTeX y CSV. |
| diagnose_singularity.py | Diagnóstico de nodos flotantes, redundancias y fuentes incompatibles. |
| export_results.py | Exportación JSON, CSV, Markdown y NPZ. |

### 3.2 Interfaz estándar de una tool

| python -m src.build_incidence_matrix \ --circuit artifacts/circuit.json \ --output artifacts/incidence.json \ --markdown artifacts/incidence.md |
| --- |

Toda tool debe regresar código de salida distinto de cero ante una falla y producir mensajes accionables. Los archivos de salida deben incluir versión del esquema, parámetros de ejecución y trazabilidad hacia el netlist original.

### 3.3 Reglas de implementación

- Python 3 y NumPy como base numérica.
- NetworkX sólo para representación y análisis del grafo, no para sustituir la lógica eléctrica.
- Dataclasses o modelos equivalentes para el dominio.
- Funciones pequeñas con tipos y docstrings.
- Sin estado global mutable.
- Orden determinista de nodos y ramas.
- Errores de dominio específicos.
- No calcular inversas explícitas; usar solve o métodos equivalentes.
- Guardar unidades y no mezclar valores normalizados con texto original.
## 4. Configuración del Custom Agent

### 4.1 Archivo basic-spice-agent.agent.md

El agente define identidad, alcance, guardrails, tools disponibles y orden de trabajo. El agente debe rechazar silenciosamente la tentación de calcular matrices a partir de texto y apoyarse siempre en tools.

| --- name: Basic SPICE Educational Agent description: Analiza netlists lineales mediante grafos, formulación nodal y Tableau. tools: [read, edit, search, terminal] --- Eres un agente educativo de simulación de circuitos. Usa los skills del repositorio y ejecuta las tools deterministas. No inventes matrices ni resultados. No presentes una solución que no haya pasado validate_solution.py. |
| --- |

### 4.2 Prompt files reutilizables

| Archivo | Uso |
| --- | --- |
| analyze-netlist.prompt.md | Procesar un netlist completo. |
| generate-graph.prompt.md | Generar nodos, ramas, grafo y A. |
| derive-matrices.prompt.md | Generar matrices constitutivas. |
| solve-circuit.prompt.md | Ejecutar análisis completo. |
| validate-circuit.prompt.md | Ejecutar controles matemáticos y eléctricos. |
| explain-result.prompt.md | Explicar un resultado ya calculado, sin recalcular. |

### 4.3 Guardrails obligatorios

- No modificar el netlist original sin declarar el cambio.
- No asumir tierra si no está definida.
- No continuar si aparecen componentes no soportados.
- No ocultar singularidad o mal condicionamiento.
- No reportar más precisión que la soportada por tolerancias y condición numérica.
- No usar fórmulas distintas entre skills y tools.
- No comparar con SPICE sin documentar versión, netlist y condiciones de análisis.
## 5. Plan de desarrollo por fases

| Fase | Enfoque | Trabajo principal | Gate de salida |
| --- | --- | --- | --- |
| Fase 0 | Alineación | Convenciones, alcance, repositorio, casos de referencia. | Documento de decisiones y estructura base. |
| Fase 1 | Núcleo topológico | Parser, validación, modelo interno, grafo y A. | Netlist → grafo → A. |
| Fase 2 | Nodal DC lineal | R/G, fuentes de corriente, solver y KCL. | Divisor/red resistiva reproducible. |
| Fase 3 | Análisis AC | C/L, frecuencia, barridos, magnitud y fase. | Filtros RC/RL/RLC. |
| Fase 4 | Tableau educativo | Y/Z/W, T, recuperación y validaciones. | Circuitos con variables de rama explícitas. |
| Fase 5 | Agente explicable | Skills, prompts, herramientas y reportes. | Experiencia integrada en Copilot. |
| Fase 6 | Extensión MNA | Fuentes de voltaje, ramas especiales, op-amps y controladas. | Comparación Nodal/Tableau/MNA. |

### 5.1 Definición de terminado por fase

- El código está versionado y revisado.
- Las pruebas unitarias y de integración pasan.
- Existe al menos un caso analítico documentado.
- Los residuos quedan debajo de la tolerancia definida.
- La salida es determinista.
- El README y el skill relacionado están actualizados.
- Un integrante distinto al autor puede reproducir el resultado.
### 5.2 Entregables de los estudiantes

| Entrega | Contenido |
| --- | --- |
| D1. Diseño | Arquitectura, convenciones, gramática del netlist y casos de prueba. |
| D2. Topología | Parser, modelo, grafo y matriz de incidencia. |
| D3. Nodal | Ensamble, solver, validación y casos DC. |
| D4. AC/Tableau | Matrices constitutivas, barrido y recuperación de variables. |
| D5. Agent package | Agent, 10 skills, prompts y documentación. |
| D6. Demostración | Netlists, resultados, comparación y reflexión técnica. |

## 6. Estrategia de pruebas y validación

La validación debe desarrollarse al mismo tiempo que el simulador. No se considera terminado un componente únicamente porque produce una matriz o una gráfica.

| Nivel | Casos mínimos | Propósito |
| --- | --- | --- |
| Topología | Resistor a tierra, serie, paralelo, tres nodos, ramas paralelas, desconectado. | Validar nodos, ramas y signos. |
| Nodal | Divisor, red de tres nodos, fuente de corriente, RC, RL, RLC. | Validar ensamble y variables. |
| Tableau | Fuentes V/I, capacitor, inductor, dos fuentes, ejemplo de la lectura. | Validar Y/Z/W/T. |
| Negativos | Nodo flotante, matriz singular, sin tierra, duplicados, sintaxis y tipos no soportados. | Validar diagnóstico seguro. |

### 6.1 Métricas de aceptación

| Métrica | Expresión | Criterio |
| --- | --- | --- |
| Residuo lineal | \|\|Mx-b\|\| | Menor que tolerancia absoluta/relativa definida. |
| KCL | \|\|AI\|\| | Cero numérico dentro de tolerancia. |
| Relación rama-nodo | \|\|Vb-AᵀVn\|\| | Cero numérico. |
| Constitutivas | \|\|YVb+ZI-W\|\| | Cero numérico. |
| Tableau | \|\|TX-W'\|\| | Cero numérico. |
| Referencia | Error absoluto y relativo | Dentro del umbral del caso de prueba. |

### 6.2 Trazabilidad de una prueba

| tests/cases/rc_lowpass/ ├── circuit.cir ├── expected_topology.json ├── expected_matrices.npz ├── expected_results.csv ├── README.md └── test_rc_lowpass.py |
| --- |

## 7. Organización del trabajo estudiantil

### 7.1 Roles sugeridos

| Rol | Responsabilidades |
| --- | --- |
| Arquitectura e integración | Contratos, interfaces, integración y releases. |
| Métodos matemáticos | Convenciones, stamps, formulaciones y casos analíticos. |
| Software científico | NumPy, solver, validación y rendimiento. |
| Agent engineering | Agent, skills, prompts y UX conversacional. |
| Quality engineering | Pruebas, CI, comparación y diagnóstico. |
| Documentación | Guías, ejemplos, reportes y material didáctico. |

### 7.2 Flujo Git recomendado

1. Crear un issue con criterios de aceptación.
1. Trabajar en una rama corta.
1. Agregar o actualizar pruebas antes de integrar.
1. Abrir pull request con evidencia de ejecución.
1. Solicitar revisión técnica y matemática.
1. Integrar únicamente después de cumplir el gate.
### 7.3 Convención para pull requests

- Problema que resuelve.
- Alcance y elementos no soportados.
- Cambios de interfaces o esquemas.
- Pruebas agregadas.
- Resultados antes/después.
- Riesgos conocidos.
- Checklist de documentación.
## 8. Estructura recomendada del repositorio

| .github/ ├── agents/basic-spice-agent.agent.md ├── copilot-instructions.md ├── prompts/*.prompt.md └── skills/<skill-name>/SKILL.md src/ ├── domain/ ├── parsers/ ├── graph/ ├── formulations/ ├── solvers/ ├── validation/ └── reporting/ tests/ ├── unit/ ├── integration/ └── cases/ examples/ artifacts/ docs/ pyproject.toml README.md |
| --- |

### 8.1 Convenciones de artefactos

| Artefacto | Formato | Contenido mínimo |
| --- | --- | --- |
| circuit.json | JSON | Componentes, nodos, ramas, unidades y fuente. |
| topology.json | JSON | Nodos, ramas, orientación y conectividad. |
| matrices.npz | NumPy | A, Y, Z, W, T y metadatos. |
| results.csv | CSV | Frecuencia, variables y unidades. |
| report.md | Markdown | Explicación, matrices, resultados y validación. |
| graph.svg | SVG | Grafo orientado con etiquetas. |

## 9. Checklist metodológico

| Área | Criterio de revisión | Estado |
| --- | --- | --- |
| Requerimientos | El alcance y los elementos soportados están explícitos. | ☐ |
| Convenciones | Nodo 0, signos, orientación, ramas y unidades son únicos. | ☐ |
| Netlist | La entrada conserva la línea original y normaliza valores. | ☐ |
| Topología | El grafo y A usan el mismo orden de ramas. | ☐ |
| Modelos | Cada renglón matricial se vincula a una ecuación constitutiva. | ☐ |
| Solver | Se usa solución lineal, no inversa explícita. | ☐ |
| Validación | KCL, KVL, constitutivas y residuo son aceptables. | ☐ |
| Agente | El agente ejecuta herramientas y no inventa resultados. | ☐ |
| Reporte | Muestra encabezados, unidades, advertencias y trazabilidad. | ☐ |
| Reproducibilidad | Otro estudiante puede ejecutar el mismo caso y obtener lo mismo. | ☐ |

### 9.1 Riesgos principales y mitigación

| Riesgo | Consecuencia | Mitigación |
| --- | --- | --- |
| Convenciones inconsistentes | Matrices con signos u órdenes incompatibles. | Centralizar convenciones y probarlas. |
| LLM como calculadora | Resultados no reproducibles. | Toda operación crítica se ejecuta en tools. |
| Alcance demasiado amplio | Prototipo incompleto. | MVP lineal y expansión por gates. |
| Pruebas tardías | Defectos difíciles de localizar. | Pruebas por componente desde la Fase 1. |
| Netlist ambiguo | Interpretación incorrecta. | Gramática explícita y errores accionables. |
| Matriz singular | Falla sin diagnóstico. | Diagnóstico topológico y numérico. |

## 10. Rúbrica sugerida de evaluación

| Criterio | Peso | Evidencia esperada |
| --- | --- | --- |
| Corrección matemática | 25% | Matrices, ecuaciones, residuos y casos analíticos. |
| Calidad del software | 20% | Arquitectura, tipos, pruebas, errores y legibilidad. |
| Skills y agente | 20% | Instrucciones, activación, tools y guardrails. |
| Validación | 15% | Comparaciones, tolerancias y casos negativos. |
| Explicabilidad | 10% | Reporte claro, trazable y pedagógico. |
| Documentación y colaboración | 10% | README, PRs, issues y reproducibilidad. |

## 11. Ejemplo de recorrido esperado

El siguiente caso debe usarse como prueba inicial de integración:

| * Divisor resistivo educativo V1 1 0 DC 10 R1 1 2 1k R2 2 0 2k .END |
| --- |

1. El parser identifica una fuente y dos resistores.
1. El modelo registra los nodos 0, 1 y 2.
1. El grafo crea tres ramas orientadas.
1. La matriz de incidencia reducida usa N1 y N2 como filas.
1. El sistema compatible se resuelve mediante la formulación implementada.
1. La validación comprueba KCL y el residuo.
1. El reporte muestra el voltaje del nodo 2, las corrientes de rama y las convenciones utilizadas.
| Resultado pedagógico esperado El estudiante no sólo observa un voltaje final. El estudiante puede seguir la cadena completa desde el netlist hasta la ecuación matricial y verificar por qué el resultado es correcto. |
| --- |

## 12. Referencias y fuentes de consulta

| Fuente | Uso en el proyecto |
| --- | --- |
| Material del curso | Matematicas_Lectura05_WW40'26-B: teoría de circuitos, grafos, matriz de incidencia, formulación nodal, Tableau y MNA. |
| GitHub Docs | Custom agents: perfiles especializados con instrucciones y tools. |
| GitHub Docs | Custom skills: directorios reutilizables con SKILL.md y recursos opcionales. |
| GitHub Copilot Learning Hub | Diferencias entre agents, instructions, prompts y skills. |
| NumPy | Solución de sistemas lineales y operaciones matriciales. |
| NetworkX | Representación y visualización programática de grafos. |

Enlaces recomendados:

- GitHub: Custom agents: https://docs.github.com/en/copilot/tutorials/customization-library/custom-agents
- GitHub: Custom skills: https://docs.github.com/en/copilot/how-tos/copilot-sdk/features/skills
- GitHub Copilot: Custom Agent Developer Guide: https://copilot-academy.github.io/workshops/copilot-customization/custom_agent_developer_guide
## Apéndice A. Matriz de responsabilidades

| Actividad | Skill | Tool | Prueba |
| --- | --- | --- | --- |
| Interpretar netlist | spice-netlist-fundamentals | parse_netlist.py | test_parser.py |
| Validar entrada | spice-netlist-fundamentals | validate_netlist.py | test_invalid_netlists.py |
| Construir grafo | circuit-graph-theory | build_oriented_graph.py | test_topology.py |
| Construir A | incidence-matrix-method | build_incidence_matrix.py | test_incidence.py |
| Construir modelos | component-constitutive-models | stamp_elements.py | test_stamps.py |
| Análisis nodal | classical-nodal-analysis | build_nodal_system.py | test_nodal.py |
| Tableau | tableau-formulation | build_tableau_system.py | test_tableau.py |
| AC | ac-frequency-analysis | solve_ac_sweep.py | test_ac.py |
| Validar | solver-validation | validate_solution.py | test_validation.py |
| Reportar | explainable-circuit-reporting | generate_report.py | test_report.py |

## Apéndice B. Criterios de aceptación del MVP

- Procesa al menos los netlists de ejemplo aprobados.
- Genera el grafo y la matriz de incidencia con etiquetas coherentes.
- Resuelve casos lineales nodales y casos AC definidos para el MVP.
- Produce matrices y resultados deterministas.
- Detecta y explica al menos los principales errores negativos.
- Entrega un reporte Markdown completo.
- Todas las pruebas automatizadas pasan.
- El agente usa skills y tools en el orden metodológico establecido.
