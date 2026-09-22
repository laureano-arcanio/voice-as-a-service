# EXP-003 — TTS con GPU dedicada; LLM + STT juntos

- **Fecha:** 2026-09-21
- **Pregunta:** ¿cuánto se gana dándole a TTS una GPU para él solo?
- **Cambio respecto de:** EXP-002 (STT pasa a la GPU del LLM; se bajan las reservas de memoria del LLM y STT para que entren juntos)
- **Resultado:** **la mejor configuración y la vigente.** Con 32 sesiones pasa ~55% más de tráfico que en EXP-002 con la misma latencia de TTS, y STT transcribe ~85 ms más rápido.

## Configuración

| GPU | Servicio | Modelo | Imagen (versión) | `--gpu-memory-utilization` | Otros flags |
|---|---|---|---|---|---|
| 0 | vllm-tts | Qwen/Qwen3-TTS-12Hz-1.7B-Base, voz `sofia_ar` | vllm/vllm-omni:v0.28.0 | 0.4 | max-model-len 4096 |
| 1 | vllm-llm | Qwen/Qwen3.5-4B (BF16) | vllm/vllm-openai:latest (vLLM 0.29.0) | 0.55 | max-model-len 32768, max-num-seqs 32 |
| 1 | vllm-stt | Qwen/Qwen3-ASR-1.7B | qwenllm/qwen3-asr:latest (vLLM 0.14.0) | 0.30 | max-model-len 8192 |

- Compose: `docker-compose.yml` (es la configuración que quedó).
- VRAM: GPU 0 con 12,8 GB; GPU 1 con 21,6 GB (LLM 12,1 + STT 8,2 + escritorio ~1,3).
- KV cache: LLM con 73.000 tokens (antes 206.000), STT con 17.000.
- Host: server de validación (ver [README](../README.md#entorno-de-validación)).
- Loadtest: cliente remoto por ngrok, tandas de 16 y 32. Warm-up: sí.
- Run crudo (local): `scripts/loadtest/monitor/run_20260921_134131_tts_sola`.

## Resultados

### 16 sesiones

Ventana `1790009001`–`1790009136`: 135 s activos.

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| vllm-llm | 0.7 | 73 | 15.4 | 598 | 0 | 0.3 / 2 | 9 | 0 |
| vllm-stt | 0.7 | 66 | 9.9 | 184 | 0 | 0.1 / 2 | 1 | 0 |
| vllm-tts s0 | 1.7 | 57 | 22.9 | 1146 | 0 | 2.2 / 10 | 3 | 0 |
| vllm-tts s1 | 1.7 | 162 | 446.8 | 1121 | 72 | 2.3 / 10 | 0 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 73% | 70% | 12788 | 244 / 337 | 74 °C | VLLM::StageEngi 67% 9194, VLLM::StageEngi 16% 3554 |
| 1 | 41% | 31% | 21605 | 209 / 340 | 80 °C | VLLM::EngineCor 38% 12126, VLLM::EngineCor 11% 8196, Xorg 7% 566, gnome-shell 8% 232, chrome --type=g 8% 223 |

Host: CPU 19% prom. / 32% máx; cores >90%: máx 1; RAM usada máx 34.0 GB; swap máx 0.0 GB.

| Contenedor | CPU cores p95 / máx | RAM máx GB | thread más cargado (p95 % de un core) |
|---|---|---|---|
| vllm-llm | 0.32 / 0.39 | 4.9 | VLLM::EngineCor 24% |
| vllm-stt | 0.65 / 1.04 | 4.1 | VLLM::EngineCor 32% |
| vllm-tts | 2.12 / 2.31 | 6.9 | VLLM::StageEngi 59% |

### 32 sesiones

Ventana `1790009151`–`1790009301`: 142 s activos.

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| vllm-llm | 1.1 | 83 | 16.4 | 657 | 0 | 0.7 / 4 | 12 | 0 |
| vllm-stt | 1.1 | 79 | 12.2 | 228 | 0 | 0.2 / 3 | 1 | 0 |
| vllm-tts s0 | 2.8 | 83 | 31.7 | 1499 | 0 | 4.1 / 14 | 5 | 0 |
| vllm-tts s1 | 2.8 | 219 | 610.9 | 1458 | 105 | 4.3 / 14 | 0 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 83% | 82% | 12794 | 256 / 334 | 73 °C | VLLM::StageEngi 69% 9194, VLLM::StageEngi 23% 3560 |
| 1 | 55% | 46% | 21556 | 234 / 342 | 84 °C | VLLM::EngineCor 47% 12126, VLLM::EngineCor 15% 8196, gnome-shell 10% 291 |

Host: CPU 25% prom. / 37% máx; cores >90%: máx 1; RAM usada máx 34.1 GB; swap máx 0.0 GB.

| Contenedor | CPU cores p95 / máx | RAM máx GB | thread más cargado (p95 % de un core) |
|---|---|---|---|
| vllm-llm | 0.34 / 0.42 | 4.9 | VLLM::EngineCor 24% |
| vllm-stt | 0.94 / 1.31 | 4.1 | VLLM::EngineCor 49% |
| vllm-tts | 2.23 / 2.36 | 6.9 | VLLM::StageEngi 70% |

### Latencia de punta a punta (cliente)

No registrada.

Reporte completo: [analyze-16.txt](analyze-16.txt), [analyze-32.txt](analyze-32.txt).

## Análisis

- **TTS:** con 32 sesiones sostiene 4,1 síntesis en vuelo con los mismos 31,7 ms entre tokens que tenía EXP-002 con 3,2. El costo por síntesis en vuelo baja de ~3,7 a ~2,9 ms (~25% más de capacidad).
- **STT:** ya no compite con TTS y es lo que más gana: la inferencia (lo que tarda la transcripción completa) baja de 314 a 228 ms.
- **LLM:** paga la convivencia con STT y el escritorio, y además hubo 40% más de carga. Inferencia de 657 ms y TTFT de 83 ms, sin cola y con KV cache ≤ 12%.
- **Tráfico:** llegaron ~40% más turnos que en EXP-002 (1,1 contra 0,8 por segundo). No se sabe si el cliente encadena turnos más rápido cuando responde antes, o si cambió el test.
- **CPU:** el thread de Code2Wav (engine del stage 1) llega a 70% p95. Es el próximo límite de CPU con ~1,4 veces más carga en una sola instancia.
- **GPU 0:** sigue saturada (83% promedio, 82% de los segundos al 95% o más): una 3090 da ~2,8 síntesis/s.
- **Interferencia externa:** en la tanda de 32, las CPUs 8 y 13 estuvieron al 100% en ~45% de los segundos. Los threads del stack solo explican 0,06 cores ahí: fue un proceso ajeno de un solo thread, que no se pudo identificar (el sampler todavía no registraba procesos del host). Probablemente no afectó al stack, porque el host tenía cores libres.

## Conclusión

Queda como configuración vigente: TTS nunca comparte GPU. Siguiente prueba: si una segunda réplica de TTS en la misma GPU aprovecha el margen de CPU (EXP-004).
