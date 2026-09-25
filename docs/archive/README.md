# Archivo: mediciones con el loadtest (21 al 25 de septiembre de 2026)

Mediciones hechas con `scripts/loadtest/` (`make loadtest`) antes del test de capacidad. Quedan
como historia de las decisiones: el reparto de GPU, los modelos descartados, LiveKit propio y el
motor `classic` salen de acá. **Para capacidad y latencia vigentes, ver
[`../capacity/README.md`](../capacity/README.md).**

| Archivo | Qué tiene |
|---|---|
| [`experiments/`](experiments/README.md) | EXP-001 a 013: cada configuración medida, con índice comparativo y el procedimiento de registro del loadtest |
| [`LOADTEST_CAPACITY.md`](LOADTEST_CAPACITY.md) | Conclusiones de capacidad y arquitectura candidata hasta EXP-013 |

## Por qué se reemplazó

El loadtest usa un modelo cerrado: N callers fijos, tandas separadas y un número fijo de turnos. Si el
sistema se frena, los callers también, y la carga baja sola. Además mide solo el inicio de la
respuesta, y registra el hardware de forma parcial. El test de capacidad
([`../CAPACITY_TEST_PLAN.md`](../CAPACITY_TEST_PLAN.md)) resuelve esto:

- llegadas Poisson por escalón;
- calidad por turno y por llamada;
- SLO;
- ficha de hardware y config con `hw_id`/`config_id`;
- RAM por componente.

## Cómo leer estos números hoy

- Los EXP miden con **otro cliente** (tandas, `--turns` fijos): no se comparan número a número con los CAP.
- **EXP-001 a 008** usan otra config: LLM Qwen3.5-4B, STT Qwen3-ASR o Whisper, TTS Base, LiveKit Cloud o ngrok.
- **EXP-006 a 010** tienen el tope de ~20 llamadas del despacho de LiveKit Cloud (ver EXP-011).
- **Hasta EXP-013** las GPUs corrían sin tope de potencia (350 W). Desde el 25-sep-2026 corren a 280 W con clocks limitados (ver `AGENTS.md`, Hosts).

`scripts/loadtest/` sigue en el repo: el test de capacidad reutiliza su caller y su sampler.
