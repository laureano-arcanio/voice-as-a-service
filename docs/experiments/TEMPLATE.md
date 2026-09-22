# EXP-NNN — <qué se probó, en pocas palabras>

- **Fecha:** AAAA-MM-DD
- **Pregunta:** <qué se quiere saber>
- **Cambio respecto de:** EXP-NNN (<qué cambia: modelo, reparto de GPU, flags>)
- **Resultado:** <una línea>

## Configuración

| GPU | Servicio | Modelo | Imagen (versión) | `--gpu-memory-utilization` | Otros flags |
|---|---|---|---|---|---|
| | | | | | |

- Compose: `docker-compose.yml` [+ `docker-compose.<nombre>.yml`]
- Host: server de validación (ver [README](README.md#entorno-de-validación)) | <otro>
- Loadtest: `<comando>`; warm-up: sí/no
- Run crudo (local): `scripts/loadtest/monitor/run_…`; config efectiva en [meta.json](meta.json)

## Resultados

### 16 sesiones

<salida de `analyze.py <run> <t0> <t1> --md`>

### 32 sesiones

<ídem>

### Latencia de punta a punta (cliente)

<resumen que imprime `run.py` por tanda, o "no registrada">

Reporte completo: [analyze-16.txt](analyze-16.txt), [analyze-32.txt](analyze-32.txt).

## Análisis

- <qué limita, qué sobra, qué cambió respecto de la referencia>

## Conclusión

<decisión y siguiente paso>
