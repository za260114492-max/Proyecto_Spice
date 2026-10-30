# Proyecto SPICE educativo

Agente educativo para analizar netlists lineales mediante herramientas Python deterministas. El agente interpreta y explica; las herramientas calculan y producen los artefactos reproducibles.

## Estructura

- `.github/agents/Spice_Expert.agent.md`: agente especializado para VS Code/Copilot.
- `.github/skills/`: diez skills con teoría, convenciones y procedimientos por dominio.
- `tools/basic_spice/`: quince herramientas Python actualmente implementadas y ejemplos.
- `tests/unit/`: pruebas unitarias, ordenadas por herramienta.
- `tests/integration/`: pruebas del flujo completo.
- `docs/reference/`: especificación académica y guías de metodología.
- `docs/plans/`: planes para las herramientas y fases de integración futuras.
- `docs/source-archives/`: ZIP originales recibidos; se conservan como referencia.

## Alcance implementado

El proyecto incluye un flujo nodal y un flujo Tableau: el segundo ensambla `T @ X = W_prime`, puede resolver fuentes ideales de voltaje y valida de forma independiente los residuos y el condicionamiento. También ejecuta barridos AC, compara contra referencias documentadas, genera curvas de ganancia y fase, y produce un reporte Markdown auditable desde artefactos existentes. La ruta nodal sigue rechazando fuentes ideales de voltaje.

## Preparación y prueba

Desde la raíz del repositorio, instala las dependencias y ejecuta todas las pruebas:

```powershell
python -m pip install -r tools/basic_spice/requirements.txt
python -m unittest discover -s tests -v
```

Para ejecutar el flujo completo de ejemplo y consultar las opciones de cada herramienta, sigue [tools/basic_spice/README.md](tools/basic_spice/README.md). Los artefactos deben guardarse en `artifacts/`.

## Documentación

- [Índice y fuente de verdad documental](docs/reference/README.md)
- [Guía metodológica completa (Markdown)](docs/reference/GUIA_METODOLOGICA.md)
- [Especificación de la Unidad I (Markdown)](docs/reference/ESPECIFICACION_UNIDAD_1.md)
- [Originales PDF/DOCX](docs/reference/originals/)
- [Planes de desarrollo e integración](docs/plans/)
