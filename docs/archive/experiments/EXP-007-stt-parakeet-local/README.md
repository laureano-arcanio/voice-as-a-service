# EXP-007 — STT con Parakeet TDT 0.6B v3, loadtest local sin ngrok

- **Fecha:** 2026-09-22
- **Pregunta:** ¿cómo rinde Parakeet TDT 0.6B v3 como STT, en el lugar de Qwen3-ASR, junto a la LLM?
- **Cambio respecto de:** EXP-006. El STT pasa a Parakeet (servidor propio `stt/server.py`, sin batching). Además cambia el modo del loadtest: `app`, `agent` y callers corren en este host, sin ngrok, porque la cuenta de ngrok agotó su ancho de banda mensual (`ERR_NGROK_725`) en el primer intento.
- **Resultado:** Parakeet transcribe en 101–130 ms con 1,6 GB de VRAM, la menor de los tres STT. Sin ngrok, la latencia que mide el agente baja ~0,4–0,5 s por turno. No se compara de igual a igual con EXP-006: cambió la red y esta vez el scoring cargó el LLM.

## Configuración

| GPU | Servicio | Modelo | Imagen (versión) | `--gpu-memory-utilization` | Otros flags |
|---|---|---|---|---|---|
| 0 | vllm-tts | Qwen/Qwen3-TTS-12Hz-1.7B-Base, voz `sofia_ar` | vllm/vllm-omni:v0.28.0 | 0.4 | max-model-len 4096 |
| 1 | vllm-llm | Qwen/Qwen3.5-4B (BF16) | vllm/vllm-openai:latest (vLLM 0.29.0) | 0.55 | max-model-len 32768, max-num-seqs 32, max-cudagraph-capture-size 32 |
| 1 | stt-parakeet | nvidia/parakeet-tdt-0.6b-v3 | build `stt-parakeet` (`stt/server.py`, transformers 5.16.1) | — | 1 instancia (`STT_WORKERS` sin definir), sin batching |
| — | agent, app, db | — | build (livekit-agents 1.8.2) | — | `agent` en modo `start` |

- Compose: `docker-compose.yml` + `docker-compose.stt-candidates.yml` (`make servers-parakeet`), y `make up-remote` para `db`, `app` y `agent` en este host.
- `.env` de este host: `VLLM_STT_BASE_URL=http://stt-parakeet:8000/v1` y `AGENT_STT_MODEL=nvidia/parakeet-tdt-0.6b-v3`.
- VRAM de la GPU 1: 15,1 GB como máximo (LLM 12,0 + Parakeet 1,6 + escritorio). Con Whisper eran 17,4 GB (EXP-006) y con Qwen3-ASR 21,6 GB (EXP-003).
- Host: server de validación (ver [README](../README.md#entorno-de-validación)). Además de la inferencia corren acá el `agent` y los callers del loadtest (`agent-run`).
- Loadtest: `make loadtest ARGS="--levels 16,32 --turns 6"` en este host; warm-up `--levels 2 --turns 2`, con fin marcado en `1790084195`.
- Tandas: no hay hueco entre ellas, porque el scoring de las llamadas de 16 sigue cuando arranca la de 32. El corte está en el pico de saludos de TTS (15 → 26 síntesis en vuelo en `1790084375`). Las ventanas coinciden con las del CSV del cliente.
- Run crudo (local): `scripts/loadtest/monitor/run_20260922_103448_parakeet_local`; config efectiva en [meta.json](meta.json).
- Intento previo por ngrok, descartado: `run_20260922_092445_parakeet`. La tanda de 32 se cortó a los ~35 s, cuando ngrok empezó a devolver 403. En la de 16, Parakeet dio 79 ms de inferencia, sin scoring en el LLM.

## Resultados

### 16 sesiones

Ventana `1790084230`–`1790084375`: 145 s activos.

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| stt-parakeet | 0.5 | — | — | 101 | 4 | 0.0 / 1 | 0 | 0 |
| vllm-tts s0 | 1.2 | 44 | 19.2 | 1045 | 0 | 1.6 / 7 | 2 | 0 |
| vllm-tts s1 | 1.2 | 138 | 374.7 | 1028 | 62 | 1.8 / 7 | 0 | 0 |
| vllm-llm | 0.6 | 97 | 14.3 | 1442 | 0 | 0.8 / 5 | 22 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 61% | 61% | 12778 | 232 / 329 | 72 °C | VLLM::StageEngi 69% 9194, VLLM::StageEngi 14% 3544 |
| 1 | 58% | 54% | 15099 | 246 / 343 | 84 °C | VLLM::EngineCor 60% 11994, Xorg 4% 638, gnome-shell 6% 287, missioncenter 3% 28 |

Host: CPU 27% prom. / 68% máx; cores >90%: máx 2; RAM usada máx 38.8 GB; swap máx 7.3 GB; proceso ajeno más cargado: code (app-gnome-code-9838.scope) p95 29% de un core.

| Contenedor | CPU cores p95 / máx | RAM máx GB | thread más cargado (p95 % de un core) |
|---|---|---|---|
| stt-parakeet | 0.32 / 0.49 | 3.8 | python3 18% |
| vllm-tts | 2.10 / 2.18 | 11.3 | VLLM::StageEngi 55% |
| vllm-llm | 0.39 / 0.54 | 12.5 | VLLM::EngineCor 30% |

### 32 sesiones

Ventana `1790084375`–`1790084558`: 183 s activos.

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| stt-parakeet | 0.7 | — | — | 130 | 9 | 0.1 / 2 | 0 | 0 |
| vllm-tts s0 | 1.9 | 74 | 28.7 | 1546 | 0 | 3.2 / 13 | 5 | 0 |
| vllm-tts s1 | 1.9 | 196 | 574.5 | 1509 | 99 | 3.4 / 14 | 0 | 0 |
| vllm-llm | 0.8 | 114 | 15.4 | 2497 | 0 | 2.0 / 9 | 37 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 66% | 64% | 12784 | 220 / 330 | 72 °C | VLLM::StageEngi 74% 9194, VLLM::StageEngi 22% 3550 |
| 1 | 78% | 73% | 15065 | 286 / 341 | 84 °C | VLLM::EngineCor 75% 11994, python3 5% 1630, gnome-shell 8% 250, code 6% 172, missioncenter 7% 66 |

Host: CPU 38% prom. / 76% máx; cores >90%: máx 1; RAM usada máx 40.2 GB; swap máx 7.6 GB; proceso ajeno más cargado: python3 (app-org.chromium.Chromium-9838.scope) p95 100% de un core.

| Contenedor | CPU cores p95 / máx | RAM máx GB | thread más cargado (p95 % de un core) |
|---|---|---|---|
| stt-parakeet | 0.47 / 0.90 | 3.8 | python3 18% |
| vllm-tts | 2.29 / 2.37 | 10.7 | VLLM::StageEngi 69% |
| vllm-llm | 0.49 / 0.65 | 12.0 | VLLM::EngineCor 39% |
| agent | 3.60 / 5.09 (prom. 1.94) | — | — |
| agent-run (callers) | 1.44 / 1.53 (prom. 0.96) | — | — |

### Latencia de punta a punta (cliente)

Calculada del CSV del cliente ([loadtest.csv](loadtest.csv)), en segundos (avg / p50 / p95 / máx). `total_s` = `eou_s` + `ttft_s` + `tts_s`. `stt_s` es el `transcription_delay` de LiveKit, que incluye los 0,3 s de silencio que espera el VAD.

| Métrica | 16 sesiones (12/16 ok, n=72) | 32 sesiones (20/32 ok, n=120) | EXP-006 con 32, por ngrok (avg) |
|---|---|---|---|
| client_latency_s | 1.85 / 2.00 / 2.85 / 2.88 | 2.14 / 2.36 / 3.20 / 3.73 | 2.54 |
| think_time_s | 2.96 / 2.45 / 6.85 / 10.00 | 3.32 / 2.76 / 8.34 / 10.00 | 3.19 |
| eou_s | 0.63 / 0.50 / 1.00 / 1.41 | 0.74 / 0.66 / 1.00 / 1.04 | 0.79 |
| stt_s | 0.43 / 0.42 / 0.57 / 0.58 | 0.47 / 0.45 / 0.60 / 0.72 | 0.68 |
| endpointing_s | 0.20 / 0.01 / 0.63 / 1.02 | 0.27 / 0.12 / 0.62 / 0.63 | 0.11 |
| ttft_s | 0.13 / 0.11 / 0.23 / 0.24 | 0.15 / 0.13 / 0.27 / 0.32 | 0.31 |
| llm_total_s | 0.75 / 0.58 / 1.98 / 2.02 | 0.94 / 0.81 / 2.12 / 2.57 | 1.01 |
| tts_s | 0.15 / 0.13 / 0.23 / 0.73 | 0.22 / 0.20 / 0.43 / 0.93 | 0.37 |
| total_s | 0.91 / 0.79 / 1.43 / 1.79 | 1.11 / 1.23 / 1.57 / 2.16 | 1.48 |

- Llamadas fallidas: 4/16 y 12/32, todas con `TimeoutError: timeout esperando que el agente empiece a responder`.

Reporte completo: [analyze-16.txt](analyze-16.txt), [analyze-32.txt](analyze-32.txt).

## Análisis

- **STT:** la inferencia da 101 ms con 16 sesiones y 130 ms con 32. En el intento por ngrok, sin scoring en el LLM, fueron 79 ms. Es rápido, pero esta vez la GPU 1 estuvo más cargada que en EXP-006 (ver scoring), así que no se puede ordenar contra Whisper (89–96 ms). Sí queda claro que los dos están muy por debajo de Qwen3-ASR (184–228 ms en EXP-003).
- **STT sin batching:** con una sola instancia, los requests se procesan de a uno. La espera en cola tuvo p50 de 0, p95 de 52 ms y máximo de 235 ms (log de Parakeet, las dos tandas). Con 20 llamadas alcanza, pero la cola crece con la concurrencia, y Whisper, que corre sobre vLLM y hace batching, no tiene ese problema. El límite es del servidor, no del modelo: el procesador y `generate` aceptan lotes, pero `stt/server.py` transcribe un audio por llamada. vLLM no sirve Parakeet, porque su decoder es un transducer (TDT), sin KV cache de atención. Con 0,7 req/s de ~130 ms, la instancia está ocupada ~9% del tiempo. La cola pesaría por encima de ~50%, unas 100 llamadas con este patrón (extrapolado). Para más carga: subir `STT_WORKERS` (~1,2 GB por instancia extra, los pesos en bf16) o agregar batching dinámico al servidor.
- **STT, recursos:** usa 1,6 GB de VRAM, contra 3,9 GB de Whisper y 8,2 GB de Qwen3-ASR. En CPU, 0,32–0,47 cores p95, entre Whisper (0,14) y Qwen3-ASR (0,94).
- **Sin ngrok:** la latencia total que mide el agente baja de 1,48 a 1,11 s con 32 sesiones. Cada salto a la inferencia pierde ~0,15–0,2 s: `ttft_s` baja de 0,31 a 0,15 s y `tts_s` de 0,37 a 0,22 s. `stt_s` baja de 0,68 a 0,47 s y ahora es ~0,3 s de VAD + ~0,1 s de inferencia + ~0,03 s de red. Producción se va a parecer más a esta medición que a las anteriores.
- **Scoring en el LLM, que no estuvo en EXP-006:**
  - Al cerrar cada llamada, el agente evalúa el transcript con el LLM (`/v1/chat/completions`, `app/scoring.py`). En EXP-006 no llegó ningún request de ese tipo por ngrok, solo `/v1/responses`, los turnos.
  - Acá fueron 10 requests de scoring en la tanda de 16 y 19 en la de 32, de ~500–1.000 tokens de salida cada uno.
  - Eso explica la inferencia media del LLM (1.442 y 2.497 ms, porque mezcla turnos y scoring), el KV máx de 37% y la GPU 1 más cargada: 73% de los segundos ≥95% con 32 sesiones, contra 27% en EXP-006.
  - Los turnos casi no lo sienten: 15,4 ms entre tokens, igual que en EXP-006, y TTFT de 114 contra 96 ms en el server.
- **TTS:** mismo rendimiento que en EXP-006 con la misma carga: 1,9 síntesis/s con 28,7 ms entre tokens (antes 28,6). El thread de Code2Wav quedó en 69% p95 (antes 70%). Compartir el host con el agente y los callers no lo afectó.
- **Host:** CPU 38% de promedio y 76% de máximo con 32 sesiones (en EXP-006, 17% y 36%). El agente usa 1,9 cores de promedio y 3,6 p95; los callers ~1 core. Nunca hubo más de 1–2 cores >90%. El swap subió a 7,6 GB (antes 4,2), con 40 GB de RAM usada. El proceso ajeno al 100% de un core fueron procesos `python3` cortos de la sesión de escritorio.
- **Llamadas que el agente no toma (4/16 y 12/32):**
  - No es ngrok ni la inferencia: pasa igual en local, y ningún vLLM tuvo errores.
  - De las 50 llamadas (warm-up incluido), el worker registró solo 38 job requests.
  - Los jobs llegan en oleadas: en la tanda de 32, 12 en los primeros 4 s y después en +7,7, +8,0, +8,9, +13, +18, +21, +24, +39, +42 y +204 s. El caller espera el saludo 20 s (`greeting_timeout`), así que los que llegan después de eso fallan. 3 jobs llegaron cuando la sala ya estaba cerrada (`room disconnected while waiting for participant`).
  - Las oleadas encajan con el control de admisión de livekit-agents: el worker responde "no disponible" y LiveKit reofrece el job más tarde. Esos rechazos no se registran, porque el log solo anota los jobs aceptados.
  - Pero la carga que calcula el worker (CPU del contenedor / 16 cores, media de 2,5 s) no pasó de 0,29, y el umbral es 0,7. La causa queda sin confirmar. También puede venir de LiveKit Cloud: el export de telemetría del proyecto recibe `429 Too Many Requests`.

## Conclusión

Parakeet es el STT más liviano de los tres (1,6 GB) y transcribe en 80–130 ms. Whisper usa más VRAM (3,9 GB), pero hace batching, algo que Parakeet no tiene sin sumar instancias. Para elegir entre los dos falta medirlos en las mismas condiciones, y la calidad en llamadas reales. Siguientes pasos:

1. Repetir Whisper y Qwen3-ASR en este modo (local, sin ngrok, con scoring) para tener tres corridas comparables.
2. Resolver las llamadas que el agente no toma. Probar con `load_fnc` o `load_threshold` que no rechacen, o con los logs de disponibilidad del worker, y revisar los límites del plan de LiveKit Cloud. Hasta entonces, la tanda de 32 mide ~20 llamadas.
3. Decidir con el WER sobre recortes de llamadas reales.
