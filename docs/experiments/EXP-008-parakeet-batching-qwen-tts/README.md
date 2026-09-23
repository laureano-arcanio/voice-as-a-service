# EXP-008 — Parakeet con batching dinámico + Qwen3-TTS, loadtest local

- **Fecha:** 2026-09-23
- **Pregunta:** ¿el batching dinámico de `stt/server.py` cambia algo bajo el loadtest de 16 y 32 sesiones?
- **Cambio respecto de:** EXP-007. Misma config (Parakeet + Qwen3-TTS 1.7B-Base + Qwen3.5-4B, loadtest local sin ngrok). Solo cambia el servidor de STT: batching dinámico hasta `STT_MAX_BATCH=8`, en lugar de un request por vez.
- **Resultado:** igual que EXP-007, dentro del ruido. A esta carga (0,6 req/s de STT) casi nunca llegan dos transcripciones a la vez: 233 requests en 232 batches. El batching no molesta, pero tampoco se ejercita.

## Configuración

| GPU | Servicio | Modelo | Imagen (versión) | `--gpu-memory-utilization` | Otros flags |
|---|---|---|---|---|---|
| 0 | vllm-tts | Qwen/Qwen3-TTS-12Hz-1.7B-Base, voz `sofia_ar` | vllm/vllm-omni:v0.28.0 | 0.4 | max-model-len 4096 |
| 1 | vllm-llm | Qwen/Qwen3.5-4B (BF16) | vllm/vllm-openai:latest | 0.55 | max-model-len 32768, max-num-seqs 32, max-cudagraph-capture-size 32 |
| 1 | stt-parakeet | nvidia/parakeet-tdt-0.6b-v3 | build `stt-parakeet` (`stt/server.py` con batching, transformers 5.16.1) | — | `STT_MAX_BATCH=8`, `STT_MAX_BATCH_SECONDS=120` |
| — | agent, app, db | — | build | — | `agent` en modo `start` |

- Compose: `docker-compose.yml` + `docker-compose.parakeet.yml` (Parakeet en la GPU 1 en lugar de `vllm-stt`). En [meta.json](meta.json) `stt-parakeet` figura creado con `docker-compose.parakeet-cosyvoice.yml`: es la misma definición del servicio (GPU 1), y el contenedor no se recreó al pasar al override nuevo.
- `.env` de este host: `VLLM_STT_BASE_URL=http://stt-parakeet:8000/v1`, `AGENT_STT_MODEL=nvidia/parakeet-tdt-0.6b-v3`, TTS `vllm-tts` con `sofia_ar`.
- Host: server de validación (ver [README](../README.md#entorno-de-validación)). `agent` y los callers corren acá.
- Loadtest: `make loadtest ARGS="--levels 16,32 --turns 6"`; warm-up `--levels 2 --turns 2` (2/2 ok), con fin marcado en `1790172467`.
- Tandas: sin hueco entre ellas. El corte está en el pico de saludos de TTS de la tanda de 32 (17 síntesis en vuelo en `1790172627`).
- Run crudo (local): `scripts/loadtest/monitor/run_20260923_110625_parakeet_batch_qwentts`; config efectiva en [meta.json](meta.json). CSV del cliente: [loadtest.csv](loadtest.csv).

## Resultados

### 16 sesiones

Ventana `1790172467`–`1790172627`: 160 s activos.

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| vllm-tts s0 | 1.2 | 53 | 20.2 | 958 | 0 | 1.6 / 8 | 3 | 0 |
| vllm-tts s1 | 1.2 | 147 | 387.2 | 936 | 65 | 1.7 / 9 | 0 | 0 |
| stt-parakeet | 0.5 | — | — | 112 | 6 | 0.1 / 1 | 0 | 0 |
| vllm-llm | 0.6 | 98 | 13.9 | 1530 | 0 | 0.8 / 4 | 18 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 55% | 53% | 12752 | 216 / 334 | 72 °C | VLLM::StageEngi 67% 9194, VLLM::StageEngi 14% 3518 |
| 1 | 58% | 51% | 14894 | 252 / 343 | 84 °C | VLLM::EngineCor 65% 11992, Xorg 5% 518, gnome-shell 4% 283, chrome --type=g 6% 162 |

Host: CPU 31% prom. / 59% máx; cores >90%: máx 1; RAM usada máx 50.1 GB; swap máx 8.0 GB; proceso ajeno más cargado: code (update-notifier-crash.service) p95 104% de un core.

| Contenedor | CPU cores p95 / máx | RAM máx GB | thread más cargado (p95 % de un core) |
|---|---|---|---|
| vllm-tts | 2.12 / 2.22 | 8.7 | VLLM::StageEngi 56% |
| stt-parakeet | 0.38 / 0.74 | 1.4 | python3 28% |
| vllm-llm | 0.43 / 0.55 | 3.5 | VLLM::EngineCor 33% |

### 32 sesiones

Ventana `1790172627`–`1790172827`: 180 s activos.

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| vllm-tts s0 | 1.6 | 66 | 26.0 | 1236 | 0 | 2.4 / 12 | 4 | 0 |
| vllm-tts s1 | 1.6 | 180 | 498.7 | 1205 | 86 | 2.6 / 12 | 0 | 0 |
| stt-parakeet | 0.6 | — | — | 132 | 16 | 0.1 / 2 | 0 | 0 |
| vllm-llm | 0.7 | 103 | 14.4 | 2003 | 0 | 1.4 / 7 | 28 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 57% | 54% | 12772 | 205 / 333 | 73 °C | VLLM::StageEngi 71% 9194, VLLM::StageEngi 19% 3538 |
| 1 | 60% | 56% | 15050 | 243 / 346 | 85 °C | VLLM::EngineCor 72% 11992, python3 5% 1582, Xorg 3% 518, chrome --type=g 10% 328 |

Host: CPU 34% prom. / 84% máx; cores >90%: máx 1; RAM usada máx 51.8 GB; swap máx 8.0 GB; proceso ajeno más cargado: pytest (app-org.chromium.Chromium-3161385.scope) p95 100% de un core.

| Contenedor | CPU cores p95 / máx | RAM máx GB | thread más cargado (p95 % de un core) |
|---|---|---|---|
| vllm-tts | 2.25 / 2.41 | 8.7 | VLLM::StageEngi 66% |
| stt-parakeet | 0.56 / 1.37 | 1.4 | python3 34% |
| vllm-llm | 0.52 / 0.62 | 3.5 | VLLM::EngineCor 40% |

### Latencia de punta a punta (cliente)

Resumen de `run.py` por tanda, en segundos (avg / p50 / p95 / máx).

| Métrica | 16 sesiones (13/16 ok, n=78) | 32 sesiones (19/32 ok, n=114) | EXP-007 con 32 (avg) |
|---|---|---|---|
| client_latency_s | 1.97 / 2.01 / 3.08 / 3.28 | 2.17 / 2.09 / 3.30 / 3.85 | 2.14 |
| think_time_s | 2.93 / 2.48 / 7.71 / 8.71 | 2.93 / 2.42 / 5.98 / 10.00 | 3.32 |
| eou_s | 0.74 / 0.55 / 1.44 / 1.58 | 0.73 / 0.58 / 1.00 / 1.72 | 0.74 |
| stt_s | 0.45 / 0.44 / 0.55 / 0.68 | 0.48 / 0.45 / 0.72 / 1.01 | 0.47 |
| endpointing_s | 0.29 / 0.10 / 0.98 / 1.14 | 0.25 / 0.01 / 0.63 / 1.24 | 0.27 |
| ttft_s | 0.13 / 0.11 / 0.24 / 0.27 | 0.14 / 0.12 / 0.30 / 0.36 | 0.15 |
| llm_total_s | 0.70 / 0.52 / 1.72 / 2.30 | 0.74 / 0.49 / 2.21 / 2.40 | 0.94 |
| tts_s | 0.17 / 0.14 / 0.33 / 0.81 | 0.22 / 0.17 / 0.50 / 1.08 | 0.22 |
| total_s | 1.03 / 1.06 / 1.84 / 2.13 | 1.09 / 1.00 / 1.99 / 2.33 | 1.11 |

- Llamadas fallidas: 3/16 y 13/32 (EXP-007: 4/16 y 12/32), el mismo patrón de jobs que el agente no toma.

Reporte completo: [analyze-16.txt](analyze-16.txt), [analyze-32.txt](analyze-32.txt).

## Análisis

- **STT:** inferencia 112 ms con 16 y 132 ms con 32 (EXP-007: 101 y 130 ms); cola 6 y 16 ms (EXP-007: 4 y 9). En vuelo, 0,1 de promedio y 2 de máximo: la instancia está ocupada ~8% del tiempo. Desde el deploy, `stt:batches_total` = 232 y `stt:batch_items_total` = 233: una sola vez se juntaron dos. El batching no agrega latencia a los requests solos, que es lo esperado, pero esta carga no llega a necesitarlo.
- **Dónde sí rinde el batching:** en el bench sintético (`scratch/parakeet_batch/`, 300 audios de OpenSLR 61 tel8k, clientes sin pausa) pasó de 16 a 76 req/s con 16 clientes y la p50 bajó de 996 a 204 ms. El loadtest pide 0,6 req/s: haría falta ~100 veces más carga de STT para que se note, del orden de cientos de llamadas.
- **TTS:** 1,6 síntesis/s con 26,0 ms entre tokens con 32 sesiones (EXP-007: 1,9/s y 28,7 ms), porque llegaron 19 llamadas en lugar de 20. Thread de Code2Wav en 66% p95. Sigue siendo lo que limita: es el único servicio con cola (65–86 ms en el stage 1).
- **LLM:** TTFT 98–103 ms y 14 ms entre tokens, igual que EXP-007. Incluye el scoring al cerrar cada llamada (KV máx 28%).
- **GPU 1:** 56% de los segundos ≥95% con 32 sesiones, contra 73% en EXP-007. Es la carga del scoring, que depende de cuántas llamadas cierran dentro de la ventana, no del STT.
- **Cliente:** `total_s` 1,09 s de promedio con 32 (EXP-007: 1,11 s) y `stt_s` 0,48 s (0,47). Sin cambios.
- **Llamadas que el agente no toma:** 13/32, igual que en EXP-007. Sigue sin resolver y limita la tanda de 32 a ~20 llamadas reales.

## Conclusión

El batching de Parakeet queda en la config sin costo: no cambia la latencia con esta carga y da margen para cargas mucho mayores (×4,7 de throughput medido en el bench). Con 20 llamadas reales, el STT no es el cuello: lo es el TTS, y después las llamadas que el agente no toma. Siguientes pasos:

1. Resolver las llamadas que el agente no toma (ver EXP-007), para que la tanda de 32 mida 32.
2. Para ver el batching bajo carga real de STT hace falta un loadtest con muchas más sesiones, que hoy no entran por el TTS.
