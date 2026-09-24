# EXP-009 — LLM Qwen3.5-9B en 4 bits en lugar de Qwen3.5-4B

- **Fecha:** 2026-09-24
- **Pregunta:** ¿un modelo más grande resuelve los errores del motor conversacional (el LLM decide el flujo) sin la latencia del pensamiento?
- **Cambio respecto de:** EXP-008 (solo el LLM: `Qwen/Qwen3.5-4B` bf16 → `RedHatAI/Qwen3.5-9B-quantized.w4a16`, `--gpu-memory-utilization` 0.55 → 0.70)
- **Resultado:** 8 de 8 demos cerradas con nombre y contacto (el 4B, 4 de 8), y más rápido por turno (p50 0,90 s contra 1,00 s). Capacidad sin medir.

Es un experimento de calidad, no de capacidad: se midió con `scripts/replay_calls.py`, no con el
loadtest (desactualizado para el agente actual, ver AGENTS.md).

## Configuración

| GPU | Servicio | Modelo | Imagen (versión) | `--gpu-memory-utilization` | Otros flags |
|---|---|---|---|---|---|
| 1 | `vllm-llm` | `RedHatAI/Qwen3.5-9B-quantized.w4a16` (compressed-tensors, w4a16, Marlin) | vllm/vllm-openai:latest (vLLM 0.29.0) | 0.70 | `--max-num-seqs=32`, `--max-cudagraph-capture-size=32`, `--limit-mm-per-prompt={"image":0,"video":0}` |

- Resto como EXP-008: `stt-parakeet` en la GPU 1, `vllm-tts` sola en la GPU 0.
- Memoria: pesos 11,4 GB aunque sea 4 bits (embeddings, `lm_head` y el encoder de visión quedan en bf16). KV cache 4,8 GiB (~141k tokens). GPU 1: 18,0 GB usados (con el 4B, 14,7 GB).
- Pedido al LLM: sin pensamiento, muestreo recomendado por Qwen (temperature 0.7, top_p 0.8, top_k 20, min_p 0), structured output con el JSON del turno.
- Evaluación: `make eval-motor N=3` (6 escenarios armados con llamadas del 2026-09-23, cliente simulado que contesta según `next_objective`), workflow `demo_booking`, contra el mismo motor con el 4B.

## Resultados

| | Qwen3.5-4B (bf16) | Qwen3.5-9B (w4a16) |
|---|---|---|
| Demos cerradas con nombre y contacto válidos | 4 de 8 | **8 de 8** |
| explicame-antes (pide explicación antes de decidir) | 2 de 3 agenda, 11,0 turnos | **3 de 3, 5,7 turnos** |
| email-cortado | 3 de 3 cierran, 2 con contacto | **3 de 3 con contacto** |
| si-pero ("sí, pero antes contame más") | 3 de 3 cierran sin nombre ni contacto | 2 de 3 con datos, 1 sin terminar |
| pregunta-y-duda | 0 de 3 terminan | 0 de 3 |
| buzón de voz | 0 de 3 terminan | 0 de 3 |
| LLM por turno | p50 1,00 s, p90 1,47 s | **p50 0,90 s, p90 1,31 s** |

Detalle: [resumen.txt](resumen.txt); conversaciones completas en [replay-4b.txt](replay-4b.txt) y [replay-9b.txt](replay-9b.txt).

Referencias del mismo día con el 4B: el muestreo anterior (temperature 0.2, resto neutro de vLLM)
dio 1 de 7 demos con datos; el 4B con pensamiento (tope 128 tokens) dio 6 de 6, pero con p50 2,57 s
por turno.

## Análisis

- Los errores del 4B eran de capacidad: respondía una cosa y registraba otra (pide el nombre sin guardar el "sí" a la demo), cerraba sin contacto y guardaba relleno ("no se menciona"). El 9B no los comete en estos escenarios.
- Es más rápido que el 4B bf16 porque por token lee menos memoria (la decodificación en la 3090 está limitada por ancho de banda).
- Lo que sigue fallando es en buena parte del cliente simulado: repite la misma pregunta ("¿Qué es Browix?") o contesta "¿Cómo?" a una pregunta que no tiene en su guion. El buzón de voz no tiene salida en el workflow.
- Con 3 corridas por escenario la muestra es chica: tendencia, no número firme.

## Conclusión

Qwen3.5-9B w4a16 pasa a ser el LLM vigente. Pendiente: medir capacidad (llamadas simultáneas
por GPU) con el loadtest adaptado al agente actual, y un cliente simulado con LLM para evaluar
escenarios abiertos.
