# EXP-002 — STT + TTS en la GPU sin escritorio

- **Fecha:** 2026-09-21
- **Pregunta:** ¿el escritorio (Xorg, gnome-shell, Chrome) en la GPU de TTS es lo que la satura?
- **Cambio respecto de:** EXP-001 (se intercambian las GPUs: STT + TTS a la 0, LLM a la 1 con el escritorio)
- **Resultado:** sin mejora. El escritorio no era la causa: TTS satura la GPU por sí solo.

## Configuración

| GPU | Servicio | Modelo | Imagen (versión) | `--gpu-memory-utilization` | Otros flags |
|---|---|---|---|---|---|
| 0 | vllm-stt | Qwen/Qwen3-ASR-1.7B | qwenllm/qwen3-asr:latest (vLLM 0.14.0) | 0.35 | max-model-len 8192 |
| 0 | vllm-tts | Qwen/Qwen3-TTS-12Hz-1.7B-Base, voz `sofia_ar` | vllm/vllm-omni:v0.28.0 | 0.4 | max-model-len 4096 |
| 1 | vllm-llm | Qwen/Qwen3.5-4B (BF16) | vllm/vllm-openai:latest (vLLM 0.29.0) | 0.75 | max-model-len 32768, max-num-seqs 32 |

- Compose: `docker-compose.yml` con los `device_ids` intercambiados.
- Host: server de validación (ver [README](../README.md#entorno-de-validación)).
- Loadtest: cliente remoto por ngrok, tandas de 16 y 32. Warm-up: no (los vLLM recién arrancados).
- Run crudo (local): `scripts/loadtest/monitor/run_20260921_132234_swap`.

## Resultados

### 16 sesiones

Ventana `1790007956`–`1790008081`: 124 s activos.

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| vllm-llm | 0.7 | 68 | 13.8 | 498 | 0 | 0.3 / 2 | 3 | 0 |
| vllm-stt | 0.7 | 97 | 14.2 | 260 | 0 | 0.1 / 3 | 1 | 0 |
| vllm-tts s0 | 1.5 | 160 | 24.4 | 1252 | 0 | 2.2 / 13 | 4 | 0 |
| vllm-tts s1 | 1.5 | 302 | 451.7 | 1210 | 156 | 2.3 / 13 | 0 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 75% | 71% | 22097 | 255 / 334 | 73 °C | VLLM::EngineCor 12% 9316, VLLM::StageEngi 62% 9194, VLLM::StageEngi 15% 3542 |
| 1 | 35% | 26% | 18185 | 192 / 343 | 75 °C | VLLM::EngineCor 31% 16746, Xorg 4% 566, chrome --type=g 4% 302, gnome-shell 6% 286, code 7% 91 |

Host: CPU 16% prom. / 30% máx; cores >90%: máx 0; RAM usada máx 33.6 GB; swap máx 0.0 GB.

| Contenedor | CPU cores p95 / máx | RAM máx GB | thread más cargado (p95 % de un core) |
|---|---|---|---|
| vllm-llm | 0.30 / 0.39 | 4.6 | VLLM::EngineCor 23% |
| vllm-stt | 0.74 / 1.18 | 4.9 | VLLM::EngineCor 36% |
| vllm-tts | 2.05 / 2.43 | 7.6 | VLLM::StageEngi 57% |

### 32 sesiones

Ventana `1790008091`–`1790008221`: 128 s activos.

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| vllm-llm | 0.8 | 74 | 14.7 | 557 | 0 | 0.4 / 7 | 7 | 0 |
| vllm-stt | 0.8 | 136 | 16.0 | 314 | 0 | 0.3 / 11 | 2 | 0 |
| vllm-tts s0 | 1.8 | 84 | 31.8 | 1547 | 0 | 3.2 / 13 | 4 | 0 |
| vllm-tts s1 | 1.8 | 220 | 607.6 | 1499 | 110 | 3.3 / 13 | 0 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 68% | 66% | 22101 | 237 / 328 | 72 °C | VLLM::EngineCor 18% 9316, VLLM::StageEngi 61% 9194, VLLM::StageEngi 19% 3546 |
| 1 | 28% | 23% | 18096 | 190 / 343 | 80 °C | VLLM::EngineCor 40% 16746, gnome-shell 5% 293, chrome --type=g 4% 201, missioncenter 10% 31 |

Host: CPU 15% prom. / 30% máx; cores >90%: máx 0; RAM usada máx 33.6 GB; swap máx 0.0 GB.

| Contenedor | CPU cores p95 / máx | RAM máx GB | thread más cargado (p95 % de un core) |
|---|---|---|---|
| vllm-llm | 0.31 / 0.52 | 4.6 | VLLM::EngineCor 24% |
| vllm-stt | 0.93 / 1.30 | 4.9 | VLLM::EngineCor 44% |
| vllm-tts | 2.16 / 2.27 | 7.5 | VLLM::StageEngi 68% |

### Latencia de punta a punta (cliente)

No registrada.

Reporte completo: [analyze-16.txt](analyze-16.txt), [analyze-32.txt](analyze-32.txt).

## Análisis

- **TTS:** sigue la misma curva que en EXP-001 (~20 ms de base + ~3,5 ms entre tokens por cada síntesis en vuelo). Llegó algo más de carga (1,8 contra 1,7 req/s).
- **Tanda de 16:** incluye el arranque en frío (TTFT del stage 0 en 160 ms por captura de CUDA graphs). No es comparable.
- **LLM junto al escritorio:** paga ~10% en entre tokens (13,2 → 14,7 ms). Sigue sin cola.
- **STT:** empeora con 32 (TTFT 136 ms), porque sus picos (hasta 11 en vuelo) compiten con TTS.
- **Térmica:** la GPU 0 reporta hardware slowdown con el núcleo a 73 °C. La sospecha, no verificada, es la temperatura de la memoria GDDR6X.

## Conclusión

Sacar el escritorio no alcanza: TTS necesita la GPU para él solo. Siguiente prueba: TTS sola y STT junto al LLM (EXP-003).
