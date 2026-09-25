# EXP-001 — Línea base: STT + TTS en una 3090 con escritorio

- **Fecha:** 2026-09-21
- **Pregunta:** ¿qué recurso limita con 16 y 32 sesiones?
- **Cambio respecto de:** — (configuración original del compose)
- **Resultado:** la GPU de STT + TTS es el único cuello. CPU, RAM y la GPU del LLM sobran.

## Configuración

| GPU | Servicio | Modelo | Imagen (versión) | `--gpu-memory-utilization` | Otros flags |
|---|---|---|---|---|---|
| 0 | vllm-llm | Qwen/Qwen3.5-4B (BF16) | vllm/vllm-openai:latest (vLLM 0.29.0) | 0.75 | max-model-len 32768, max-num-seqs 32 |
| 1 | vllm-stt | Qwen/Qwen3-ASR-1.7B | qwenllm/qwen3-asr:latest (vLLM 0.14.0) | 0.35 | max-model-len 8192 |
| 1 | vllm-tts | Qwen/Qwen3-TTS-12Hz-1.7B-Base, voz `sofia_ar` | vllm/vllm-omni:v0.28.0 | 0.4 | max-model-len 4096 |

- Compose: `docker-compose.yml` de ese momento. La GPU 1 además dibuja el escritorio.
- Host: server de validación (ver [README](../README.md#entorno-de-validación)).
- Loadtest: cliente remoto por ngrok, tandas de 16 y 32. Warm-up: no.
- Run crudo (local): `scripts/loadtest/monitor/run_20260921_114618`.
- Notas:
  - Se perdieron ~40 s del inicio de la tanda de 16 (reinicio del sampler).
  - Se asume que la primera tanda fue la de 16 (pico de 12 requests en vuelo) y la segunda la de 32 (pico de 21).
  - Las versiones se relevaron después: el sampler todavía no guardaba `meta.json`.

## Resultados

### 16 sesiones

Ventana `1790001980`–`1790002070`: 86 s activos.

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| vllm-llm | 0.5 | 75 | 12.8 | 538 | 0 | 0.3 / 2 | 3 | 0 |
| vllm-stt | 0.5 | 94 | 13.6 | 258 | 0 | 0.1 / 2 | 1 | 0 |
| vllm-tts s0 | 1.0 | 46 | 20.5 | 1129 | 0 | 1.6 / 6 | 2 | 0 |
| vllm-tts s1 | 1.0 | 150 | 398.8 | 1115 | 65 | 1.6 / 6 | 0 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 21% | 16% | 16847 | 180 / 318 | 75 °C | VLLM::EngineCor 27% 16812 |
| 1 | 60% | 55% | 23632 | 247 / 329 | 84 °C | VLLM::EngineCor 14% 9318, VLLM::StageEngi 58% 9312, VLLM::StageEngi 17% 3646, Xorg 4% 566, gnome-shell 6% 281, chrome --type=g 5% 155 |

Host: CPU 15% prom. / 36% máx; cores >90%: máx 0; RAM usada máx 33.4 GB; swap máx 0.0 GB.

| Contenedor | CPU cores p95 / máx | RAM máx GB | thread más cargado (p95 % de un core) |
|---|---|---|---|
| vllm-llm | 0.26 / 0.31 | 4.8 | VLLM::EngineCor 21% |
| vllm-stt | 0.57 / 0.90 | 4.1 | VLLM::EngineCor 33% |
| vllm-tts | 2.05 / 2.15 | 6.2 | VLLM::StageEngi 55% |

### 32 sesiones

Ventana `1790002070`–`1790002220`: 140 s activos.

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| vllm-llm | 0.7 | 68 | 13.2 | 495 | 0 | 0.5 / 3 | 4 | 0 |
| vllm-stt | 0.7 | 108 | 14.4 | 297 | 0 | 0.1 / 4 | 1 | 0 |
| vllm-tts s0 | 1.7 | 75 | 28.0 | 1360 | 0 | 2.6 / 10 | 3 | 0 |
| vllm-tts s1 | 1.7 | 202 | 542.0 | 1324 | 95 | 2.8 / 10 | 0 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 36% | 32% | 16847 | 193 / 348 | 74 °C | VLLM::EngineCor 47% 16812 |
| 1 | 68% | 64% | 23563 | 252 / 330 | 85 °C | VLLM::EngineCor 19% 9318, VLLM::StageEngi 56% 9312, VLLM::StageEngi 25% 3646, Xorg 6% 566, gnome-shell 7% 291, chrome --type=g 13% 101 |

Host: CPU 16% prom. / 26% máx; cores >90%: máx 0; RAM usada máx 33.4 GB; swap máx 0.0 GB.

| Contenedor | CPU cores p95 / máx | RAM máx GB | thread más cargado (p95 % de un core) |
|---|---|---|---|
| vllm-llm | 0.32 / 0.43 | 4.8 | VLLM::EngineCor 25% |
| vllm-stt | 0.88 / 1.14 | 4.2 | VLLM::EngineCor 50% |
| vllm-tts | 2.12 / 2.33 | 6.2 | VLLM::StageEngi 58% |

### Latencia de punta a punta (cliente)

No registrada.

Reporte completo: [analyze-16.txt](analyze-16.txt), [analyze-32.txt](analyze-32.txt).

## Análisis

- **GPU 1 (STT + TTS):** reparto de SM entre el talker de TTS (~57%), Code2Wav (~22%), STT (~17%) y el escritorio (10–20%).
- **TTS se degrada de 16 a 32:** entre tokens pasa de 20,5 a 28 ms y el primer audio (TTFT + cola del stage 1) de 215 a 297 ms.
- **LLM:** sin cola, KV cache ≤ 4%, GPU 0 trabaja en ráfagas.
- **CPU:** ~3,5 cores para todo el stack; ningún thread pasa de 58%.
- **RAM:** ~15 GB entre los 3 vLLM, constante.
- **Térmica:** la GPU 1 llega a 85 °C con thermal y power slowdown.

## Conclusión

Dimensionar por la GPU de TTS. Siguiente prueba: sacar el escritorio de esa GPU (EXP-002).
