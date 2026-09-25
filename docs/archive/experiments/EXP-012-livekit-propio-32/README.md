# EXP-012 — 32 llamadas con LiveKit propio

- **Fecha:** 2026-09-25
- **Pregunta:** sin el techo del despacho de LiveKit Cloud (EXP-011), ¿la config vigente atiende 32 llamadas simultáneas?
- **Cambio respecto de:** EXP-011 (LiveKit Cloud → `livekit-server` v1.13.7 propio en este host, `docker-compose.livekit.yml`; turn detector fijado en `v1-mini` local).
- **Resultado:** 32 de 32 atendidas, 32 simultáneas, despacho en ≤0,7 s. La inferencia no encola: GPUs al 74 %, TTS a 24 ms entre tokens (tope 83). El turno sube: e2e p50 2,02 s (1,77 s con 24).

## Configuración

Inferencia igual que [EXP-010](../EXP-010-loadtest-9b-motor-workflow/) y [EXP-011](../EXP-011-agente-en-server-despacho-livekit/). Config efectiva en [meta.json](meta.json).

- `livekit` (v1.13.7, audio por 7882/udp en mux), `livekit-sip` (v1.17.0) y `livekit-redis` en este host, con `network_mode: host`.
- `app` + `agent` (LiveKit Agents 1.8.3, `start`) en este host, contra `ws://192.168.1.99:7880`. Turn detector `turn-detector-v1-mini` en el proceso.
- Callers (`run.py`) en la laptop, por la LAN: `--base-url http://192.168.1.99:8011 --levels 16,32 --turns 6`, workflow `demo_booking` (`engine: structured`). Sin warm-up aparte (el sistema venía con tráfico).
- Run crudo (local): `scripts/loadtest/monitor/run_20260925_124758_livekit_local`, con el vigía de despachos → [dispatch_watch.jsonl](dispatch_watch.jsonl).

## Resultados

### Llamadas

| Tanda | Atendidas | Máx. simultáneas | Creación → job en el worker |
|---|---|---|---|
| 16 | 16 | 16 | |
| 32 | **32** | **32** | p50 0,2 s, máx. 0,7 s |

El vigía vio las 48 rooms y todas pasaron a `JS_RUNNING`: ninguna quedó en `JS_PENDING`.

### 16 sesiones

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| stt-parakeet | 1.0 | — | — | 156 | 16 | 0.1 / 2 | 0 | 0 |
| vllm-llm | 1.9 | 120 | 17.3 | 1182 | 0 | 2.2 / 10 | 15 | 0 |
| vllm-tts s0 | 1.7 | 40 | 18.6 | 815 | 0 | 1.9 / 9 | 1 | 0 |
| vllm-tts s1 | 1.7 | 71 | 376.6 | 800 | 56 | 2.0 / 9 | 0 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 66% | 62% | 12583 | 243 / 327 | 75 °C | VLLM::StageEngi 66% 9064, VLLM::StageEngi 12% 3480 |
| 1 | 76% | 67% | 18765 | 283 / 347 | 76 °C | VLLM::EngineCor 79% 15864, python3 13% 1678, gnome-shell 12% 209 |

### 32 sesiones

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| stt-parakeet | 1.6 | — | — | 181 | 41 | 0.3 / 5 | 0 | 0 |
| vllm-llm | 3.3 | 179 | 25.2 | 1706 | 0 | 5.3 / 18 | 30 | 0 |
| vllm-tts s0 | 2.6 | 60 | 24.0 | 1134 | 0 | 3.0 / 13 | 2 | 0 |
| vllm-tts s1 | 2.6 | 101 | 487.4 | 1106 | 80 | 3.3 / 12 | 0 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 74% | 72% | 12583 | 249 / 328 | 73 °C | VLLM::StageEngi 78% 9064, VLLM::StageEngi 17% 3480 |
| 1 | 74% | 72% | 18922 | 281 / 346 | 80 °C | VLLM::EngineCor 86% 15864, python3 17% 1678, gnome-shell 4% 257, chrome --type=g 6% 182, missioncenter 7% 49 |

Host: CPU 42 % prom. / 80 % máx. Thread más cargado: `python3` de `stt-parakeet`, 81 % de un core (p95).

| Contenedor (32) | CPU cores prom. / máx |
|---|---|
| agent | 3,0 / 4,6 |
| livekit | 0,2 / 0,5 |
| livekit-sip | 0 (sin llamadas SIP) |

Reportes completos: [analyze-16.txt](analyze-16.txt), [analyze-32.txt](analyze-32.txt).

### Latencia por turno (agente, `call.latency`)

| Tanda | e2e p50 / p95 | total p50 / p95 | eou p50 | LLM hasta el texto p50 / p95 | TTS p50 |
|---|---|---|---|---|---|
| 16 | 1,43 / 2,36 s | 1,01 / 1,36 s | 0,59 s | 0,24 / 0,45 s | 0,07 s |
| 24 (EXP-011, B 32) | 1,77 / 2,59 s | 1,00 / 1,52 s | 0,59 s | 0,28 / 0,54 s | 0,08 s |
| 32 | 2,02 / 3,04 s | 1,27 / 1,75 s | 0,67 s | 0,36 / 0,78 s | 0,10 s |

### Throttling

GPU 0 con thermal slowdown en 51 de 100 s (16) y 86 de 140 s (32), máx. 75 °C. GPU 1 con tope de
potencia en 80 de 100 s y 89 de 140 s, máx. 80 °C. Ninguna con HW slowdown.

## Análisis

- **Confirma EXP-011:** el techo de ~20–24 era el despacho de LiveKit Cloud. Con LiveKit propio, los 32 jobs llegan al worker en ≤0,7 s.
- **Con 32 no hay cola en LLM ni en TTS, pero las dos GPUs están al 72 % de los segundos ≥95 %.**
  - TTS: 2,6 síntesis/s a 24 ms entre tokens, lejos del tope de 83 ms. EXP-003 daba 2,8/s a 31,7 ms con el TTS Base.
  - LLM: TTFT de 120 a 179 ms y entre tokens de 17 a 25 ms de 16 a 32; hasta 18 pedidos en vuelo, KV 30 %.
- **El turno se alarga más de lo que sube la inferencia.** De 24 a 32 llamadas, e2e p50 +0,25 s y "LLM hasta el texto" p95 de 0,54 a 0,78 s. Incluye esperar la extracción del turno anterior (dos pedidos al LLM por turno).
- **STT:** cola de 41 ms y su thread principal al 81 % de un core (p95). Es lo más cerca de un límite de CPU; con más llamadas conviene mirarlo.
- **LiveKit propio casi no usa recursos:** 0,5 core como máximo. El agente usa 4,6 cores con 32 llamadas (~0,15 por llamada).

## Conclusión

La config vigente (2 × 3090: TTS sola; LLM 9B w4a16 + STT) atiende 32 llamadas simultáneas sin cola,
con e2e p50 2,0 s y p95 3,0 s por turno. Para producción, LiveKit va propio (o Cloud pago, sin medir).
Pendiente: ver dónde satura (40–48 llamadas) y el CSV del cliente de este run.
