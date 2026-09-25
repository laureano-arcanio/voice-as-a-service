# EXP-005 — Simulación: STT + TTS en una GPU de 16 GB

- **Fecha:** 2026-09-21
- **Pregunta:** ¿STT y TTS entran juntos en una GPU de 16 GB (ej. RTX 5060 Ti 16 GB), con el LLM solo en otra?
- **Cambio respecto de:** EXP-002 (mismo reparto, pero con la memoria de STT y TTS recortada al presupuesto de 16 GB)
- **Resultado:** entran, pero justo: 16,1 GB sobre ~16,3 GB. No hubo preemptions ni OOM y el rendimiento fue igual al de EXP-002. **TTS no entra en 8 GB:** su piso es ~9 GB.

## Configuración

| GPU | Servicio | Modelo | Imagen (versión) | `--gpu-memory-utilization` | Otros flags |
|---|---|---|---|---|---|
| 0 | vllm-tts | Qwen/Qwen3-TTS-12Hz-1.7B-Base, voz `sofia_ar` | vllm/vllm-omni:v0.28.0 | 0.255 | max-model-len 2048 |
| 0 | vllm-stt | Qwen/Qwen3-ASR-1.7B | qwenllm/qwen3-asr:latest (vLLM 0.14.0) | 0.25 | max-model-len 4096 |
| 1 | vllm-llm | Qwen/Qwen3.5-4B (BF16) | vllm/vllm-openai:latest (vLLM 0.29.0) | 0.55 | max-model-len 32768, max-num-seqs 32 |

- Compose: `docker-compose.yml` + `docker-compose.sim16gb.yml`.
- VRAM real en la GPU 0: TTS 9,0 GB (stage 0 con 5,5 GB y Code2Wav con 3,5 GB fijos), STT 6,9 GB. Total de 15,9 GB en reposo y 16,1 GB bajo carga.
- Arranque: con TTS en 0.245 no arranca (0,31 GiB de KV cache contra 0,44 GiB que pide una secuencia de 4096).
- KV cache: TTS con 5.072 tokens, STT con 5.376.
- Host: server de validación (ver [README](../README.md#entorno-de-validación)).
- Loadtest: cliente remoto por ngrok, tandas de 16 y 32. Warm-up: no aparente (TTFT del stage 0 de TTS en 162 ms en la tanda de 16).
- Run crudo (local): `scripts/loadtest/monitor/run_20260921_163832_sim16gb`.

## Resultados

### 16 sesiones

Ventana `1790020919`–`1790021034`: 115 s activos.

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| vllm-llm | 0.7 | 77 | 13.4 | 523 | 0 | 0.3 / 3 | 10 | 0 |
| vllm-stt | 0.7 | 89 | 12.2 | 228 | 0 | 0.1 / 2 | 3 | 0 |
| vllm-tts s0 | 1.6 | 162 | 25.4 | 1234 | 0 | 2.4 / 11 | 22 | 0 |
| vllm-tts s1 | 1.6 | 287 | 468.7 | 1181 | 158 | 2.5 / 11 | 0 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 71% | 70% | 16147 | 243 / 318 | 75 °C | VLLM::EngineCor 11% 6906, VLLM::StageEngi 59% 5666, VLLM::StageEngi 15% 3530 |
| 1 | 29% | 24% | 13488 | 183 / 338 | 77 °C | VLLM::EngineCor 38% 11994, nautilus 3% 15 |

Host: CPU 15% prom. / 29% máx; cores >90%: máx 0; RAM usada máx 36.5 GB; swap máx 0.0 GB.

| Contenedor | CPU cores p95 / máx | RAM máx GB | thread más cargado (p95 % de un core) |
|---|---|---|---|
| vllm-llm | 0.30 / 0.64 | 4.3 | VLLM::EngineCor 24% |
| vllm-stt | 0.57 / 0.97 | 4.2 | VLLM::EngineCor 30% |
| vllm-tts | 2.11 / 2.24 | 6.1 | VLLM::StageEngi 63% |

### 32 sesiones

Ventana `1790021054`–`1790021179`: 124 s activos.

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| vllm-llm | 0.9 | 68 | 13.7 | 519 | 0 | 0.4 / 3 | 12 | 0 |
| vllm-stt | 0.9 | 98 | 12.1 | 244 | 0 | 0.1 / 2 | 3 | 0 |
| vllm-tts s0 | 2.1 | 80 | 28.6 | 1433 | 0 | 3.1 / 9 | 22 | 0 |
| vllm-tts s1 | 2.1 | 200 | 554.0 | 1390 | 101 | 3.3 / 9 | 0 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 86% | 83% | 16147 | 262 / 333 | 73 °C | VLLM::EngineCor 16% 6906, VLLM::StageEngi 60% 5666, VLLM::StageEngi 21% 3530 |
| 1 | 36% | 31% | 13435 | 209 / 341 | 80 °C | VLLM::EngineCor 42% 11994, Xorg 3% 556, gnome-shell 4% 258, code 4% 186 |

Host: CPU 20% prom. / 42% máx; cores >90%: máx 1; RAM usada máx 36.8 GB; swap máx 0.0 GB.

| Contenedor | CPU cores p95 / máx | RAM máx GB | thread más cargado (p95 % de un core) |
|---|---|---|---|
| vllm-llm | 0.33 / 0.37 | 4.3 | VLLM::EngineCor 24% |
| vllm-stt | 0.79 / 1.09 | 4.1 | VLLM::EngineCor 40% |
| vllm-tts | 2.14 / 2.20 | 6.0 | VLLM::StageEngi 65% |

### Latencia de punta a punta (cliente)

No registrada.

Reporte completo: [analyze-16.txt](analyze-16.txt), [analyze-32.txt](analyze-32.txt).

## Análisis

- **Rendimiento con 32:** igual a EXP-002 o mejor (TTS 28,6 ms entre tokens, STT 98 ms de TTFT). Recortar la memoria no costó nada.
- **KV cache recortado:** alcanzó. TTS ≤ 22%, STT ≤ 3%, sin requests esperando en el stage 0.
- **Margen:** la GPU creció ~200 MiB bajo carga. Sobre los 16.311 MiB de una 5060 Ti quedarían ~160 MiB, menos lo que reserve el driver. Un cambio de versión o un audio largo puede impedir el arranque.
- **Qué no simula:** la velocidad. La 5060 Ti tiene ~la mitad del ancho de banda de memoria de la 3090 y TTS ya satura una 3090. Estimación sin medir: 50–60 ms o más entre tokens con 32 sesiones, cerca del tope de 83 ms.
- **LLM solo en la otra GPU:** 12 GB de VRAM, sin cola, KV cache ≤ 12%. Entra cómodo en 16 GB.

## Conclusión

No poner STT + TTS juntos en una GPU de 16 GB. El LLM solo en 16 GB es viable. TTS necesita una GPU de 24 GB clase 3090 (o dedicada). Pendiente: medir en una 5060 Ti real.
