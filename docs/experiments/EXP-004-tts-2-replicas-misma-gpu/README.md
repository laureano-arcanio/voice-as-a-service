# EXP-004 — Dos réplicas de TTS en la misma GPU

- **Fecha:** 2026-09-21
- **Pregunta:** ¿el límite de TTS es la GPU o el thread único del engine? Una segunda réplica agrega otro juego de threads y streams CUDA.
- **Cambio respecto de:** EXP-003 (`vllm-tts-2` en la GPU 0 junto a `vllm-tts`, nginx balanceando `/tts/` con `least_conn`)
- **Resultado:** **peor que una réplica.** Mismo throughput total con más del doble de latencia. El límite es la GPU.

## Configuración

| GPU | Servicio | Modelo | Imagen (versión) | `--gpu-memory-utilization` | Otros flags |
|---|---|---|---|---|---|
| 0 | vllm-tts | Qwen/Qwen3-TTS-12Hz-1.7B-Base, voz `sofia_ar` | vllm/vllm-omni:v0.28.0 | 0.28 | max-model-len 4096 |
| 0 | vllm-tts-2 | ídem | ídem | 0.28 | ídem |
| 1 | vllm-llm | Qwen/Qwen3.5-4B (BF16) | vllm/vllm-openai:latest (vLLM 0.29.0) | 0.55 | max-model-len 32768, max-num-seqs 32 |
| 1 | vllm-stt | Qwen/Qwen3-ASR-1.7B | qwenllm/qwen3-asr:latest (vLLM 0.14.0) | 0.30 | max-model-len 8192 |

- Compose: `docker-compose.yml` con `vllm-tts-2` activo (hoy es el perfil opt-in `tts2`) y `vllm-tts-2` en el upstream `tts` de `ngrok/proxy.conf`.
- VRAM: GPU 0 con 19,7 GB. KV cache de ~10.600 tokens por réplica.
- Host: server de validación (ver [README](../README.md#entorno-de-validación)).
- Loadtest: cliente remoto por ngrok, tandas de 16 y 32. Warm-up: sí; llegó a las dos réplicas (74 y 80 requests).
- Run crudo (local): `scripts/loadtest/monitor/run_20260921_140116_tts_x2`.

## Resultados

### 16 sesiones

Ventana `1790010277`–`1790010412`: 135 s activos.

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| vllm-llm | 0.7 | 77 | 15.0 | 636 | 0 | 0.4 / 4 | 12 | 0 |
| vllm-stt | 0.7 | 63 | 9.1 | 172 | 0 | 0.1 / 3 | 1 | 0 |
| vllm-tts s0 | 0.9 | 121 | 43.3 | 2134 | 0 | 2.3 / 7 | 7 | 0 |
| vllm-tts s1 | 0.9 | 282 | 851.6 | 2057 | 155 | 2.4 / 7 | 0 | 0 |
| vllm-tts-2 s0 | 0.9 | 120 | 42.0 | 2098 | 0 | 2.2 / 8 | 10 | 0 |
| vllm-tts-2 s1 | 0.9 | 280 | 795.8 | 2019 | 158 | 2.3 / 8 | 0 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 81% | 79% | 19707 | 254 / 323 | 73 °C | VLLM::StageEngi 41% 6288, VLLM::StageEngi 38% 6282, VLLM::StageEngi 14% 3542, VLLM::StageEngi 13% 3542 |
| 1 | 44% | 34% | 21762 | 209 / 342 | 82 °C | VLLM::EngineCor 40% 12126, VLLM::EngineCor 8% 8196, gnome-shell 9% 263 |

Host: CPU 23% prom. / 37% máx; cores >90%: máx 0; RAM usada máx 40.4 GB; swap máx 0.0 GB.

| Contenedor | CPU cores p95 / máx | RAM máx GB | thread más cargado (p95 % de un core) |
|---|---|---|---|
| vllm-llm | 0.31 / 0.44 | 4.9 | VLLM::EngineCor 23% |
| vllm-stt | 0.55 / 1.24 | 4.1 | VLLM::EngineCor 31% |
| vllm-tts | 1.96 / 2.06 | 6.6 | VLLM::StageEngi 50% |
| vllm-tts-2 | 2.02 / 2.11 | 7.4 | VLLM::StageEngi 52% |

### 32 sesiones

Ventana `1790010432`–`1790010567`: 135 s activos.

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| vllm-llm | 1.4 | 87 | 17.1 | 705 | 0 | 0.9 / 8 | 23 | 0 |
| vllm-stt | 1.4 | 89 | 13.1 | 240 | 0 | 0.3 / 5 | 2 | 0 |
| vllm-tts s0 | 1.3 | 212 | 70.7 | 3475 | 0 | 4.9 / 15 | 18 | 0 |
| vllm-tts s1 | 1.3 | 467 | 1371.5 | 3327 | 271 | 5.0 / 15 | 0 | 0 |
| vllm-tts-2 s0 | 1.4 | 208 | 71.0 | 3416 | 0 | 4.9 / 14 | 17 | 0 |
| vllm-tts-2 s1 | 1.4 | 455 | 1380.7 | 3266 | 272 | 5.1 / 13 | 0 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 85% | 84% | 19727 | 259 / 331 | 73 °C | VLLM::StageEngi 36% 6288, VLLM::StageEngi 39% 6282, VLLM::StageEngi 17% 3556, VLLM::StageEngi 19% 3548 |
| 1 | 57% | 50% | 21795 | 249 / 341 | 84 °C | VLLM::EngineCor 52% 12126, VLLM::EngineCor 20% 8196, gnome-shell 10% 295 |

Host: CPU 27% prom. / 40% máx; cores >90%: máx 0; RAM usada máx 40.5 GB; swap máx 0.0 GB.

| Contenedor | CPU cores p95 / máx | RAM máx GB | thread más cargado (p95 % de un core) |
|---|---|---|---|
| vllm-llm | 0.37 / 0.48 | 4.9 | VLLM::EngineCor 28% |
| vllm-stt | 0.92 / 1.29 | 4.1 | VLLM::EngineCor 48% |
| vllm-tts | 2.13 / 2.29 | 6.6 | VLLM::StageEngi 68% |
| vllm-tts-2 | 2.17 / 2.27 | 7.5 | VLLM::StageEngi 71% |

### Latencia de punta a punta (cliente)

No registrada.

Reporte completo: [analyze-16.txt](analyze-16.txt), [analyze-32.txt](analyze-32.txt).

## Análisis

- **Throughput:** el total fue de 2,7 síntesis/s con 32 sesiones, igual que con una réplica (2,8).
- **Latencia de TTS con 32:** entre tokens de 71 ms (antes 31,7), cerca del tope de tiempo real de 83 ms. El primer audio pasa de ~325 a ~735 ms.
- **Mecanismo, no medido:** probablemente dos procesos sin MPS se turnan la GPU y cada uno arma lotes con la mitad de los requests. Eso pierde la eficiencia del lote grande.
- **Balanceo:** `least_conn` repartió parejo (181 y 185 requests).
- **CPU:** cada réplica usa ~2,1 cores y el thread de Code2Wav sigue en ~70% p95. Duplicar threads no aceleró nada: no era el límite.
- **RAM:** cada réplica suma 6–7 GB (40 GB usados en el host).

## Conclusión

No usar varias réplicas de TTS en la misma GPU. Más réplicas solo sirven con una GPU física por réplica. `vllm-tts-2` queda en el compose como perfil opt-in `tts2`, pensado para otra GPU.
