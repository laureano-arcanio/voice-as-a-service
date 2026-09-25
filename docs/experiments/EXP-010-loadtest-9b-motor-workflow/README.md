# EXP-010 — Loadtest de la config vigente (LLM 9B w4a16 + motor por workflow)

- **Fecha:** 2026-09-25
- **Pregunta:** ¿cuántas llamadas simultáneas aguanta la config vigente (EXP-009) con el motor por workflow, que hace dos pedidos al LLM por turno?
- **Cambio respecto de:** EXP-008 (LLM `Qwen/Qwen3.5-4B` → `RedHatAI/Qwen3.5-9B-quantized.w4a16`, TTS Base con voz clonada → checkpoint fine-tuneado `multi41`, agente de un prompt → motor por workflow `structured`). Primer loadtest remoto por IP fija.
- **Resultado:** hasta 16 sesiones la inferencia sobra (sin cola, GPU ~50–60 %). La tanda de 32 **no es válida**: se atendieron ~20 de 32 llamadas. La causa, corregida en [EXP-011](../EXP-011-agente-en-server-despacho-livekit/), es el despacho de LiveKit Cloud, no la CPU de la laptop.

## Configuración

| GPU | Servicio | Modelo | Imagen (versión) | `--gpu-memory-utilization` | Otros flags |
|---|---|---|---|---|---|
| 0 | `vllm-tts` | Qwen3-TTS 1.7B-Base fine-tuneado `multi41` (`qwen3-tts-ft`) | vllm/vllm-omni:v0.28.0 | 0.4 | `--max-model-len=4096` |
| 1 | `vllm-llm` | `RedHatAI/Qwen3.5-9B-quantized.w4a16` | vllm/vllm-openai:latest (vLLM 0.29.0) | 0.70 | `--max-num-seqs=32`, `--max-cudagraph-capture-size=32`, `--limit-mm-per-prompt` 0 |
| 1 | `stt-parakeet` | `nvidia/parakeet-tdt-0.6b-v3` (`stt/server.py`, batching 8) | build local | — | — |

- Compose: `docker-compose.yml`, sin override.
- Host: server de validación (ver [README](../README.md#entorno-de-validación)), con las GPUs ya reubicadas para mejor ventilación (primer experimento así).
- Loadtest: remoto por el proxy (`http://181.104.113.28:8100`); `app` + `agent` + callers en una laptop. Tandas de 4, 8, 16 y 32 sesiones, 6 turnos, workflow `demo_booking` (`engine: structured`). Sin warm-up aparte: hubo tráfico 10 min antes (run sin monitorear).
- Run crudo (local): `scripts/loadtest/monitor/run_20260925_105057_qwen9b_workflow`; config efectiva en [meta.json](meta.json).

## Resultados

### Por tanda (server)

| Sesiones | STT req/s | STT por sesión | LLM req/s | LLM TTFT / entre tokens | TTS entre tokens | TTS primer audio | Máx. en vuelo LLM / TTS | GPU 0 / 1 uso |
|---|---|---|---|---|---|---|---|---|
| 4 | 0,2 | 0,05 | 0,5 | 96 / 12,5 ms | 14,0 ms | 71 ms | 3 / 1 | 19 / 38 % |
| 8 | 0,4 | 0,05 | 0,8 | 115 / 13,5 ms | 15,0 ms | 92 ms | 4 / 3 | 33 / 53 % |
| 16 | 0,8 | 0,05 | 1,6 | 133 / 15,9 ms | 17,2 ms | 115 ms | 9 / 6 | 50 / 62 % |
| 32 (inválida) | 0,8 | 0,025 | 1,5 | 150 / 15,7 ms | 17,4 ms | 115 ms | 9 / 6 | 53 / 60 % |

TTS primer audio: TTFT + cola del stage 1 (Code2Wav). Sin cola en STT (≤19 ms), LLM ni TTS s0,
sin preemptions, KV máx 16 %.

### 16 sesiones

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| stt-parakeet | 0.8 | — | — | 135 | 18 | 0.1 / 2 | 0 | 0 |
| vllm-llm | 1.6 | 133 | 15.9 | 1096 | 0 | 1.8 / 9 | 15 | 0 |
| vllm-tts s0 | 1.2 | 36 | 17.2 | 794 | 0 | 1.6 / 6 | 1 | 0 |
| vllm-tts s1 | 1.2 | 65 | 355.8 | 783 | 50 | 1.7 / 6 | 0 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 50% | 48% | 12583 | 213 / 329 | 73 °C | VLLM::StageEngi 56% 9064, VLLM::StageEngi 10% 3480 |
| 1 | 62% | 60% | 18783 | 253 / 348 | 78 °C | VLLM::EngineCor 76% 15864, python3 8% 1678, code 14% 187 |

Host: CPU 11 % prom. / 23 % máx. Thread más cargado: `VLLM::StageEngi` (TTS) 50 % de un core.

### 32 sesiones (inválida: despacho de LiveKit Cloud, ver EXP-011)

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| stt-parakeet | 0.8 | — | — | 140 | 19 | 0.1 / 2 | 0 | 0 |
| vllm-llm | 1.5 | 150 | 15.7 | 1110 | 0 | 1.6 / 9 | 16 | 0 |
| vllm-tts s0 | 1.4 | 36 | 17.4 | 796 | 0 | 1.6 / 6 | 1 | 0 |
| vllm-tts s1 | 1.4 | 64 | 356.1 | 786 | 51 | 1.6 / 6 | 0 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 53% | 50% | 12583 | 230 / 322 | 73 °C | VLLM::StageEngi 62% 9064, VLLM::StageEngi 9% 3480 |
| 1 | 60% | 57% | 18789 | 241 / 348 | 78 °C | VLLM::EngineCor 79% 15864, python3 9% 1678, code 4% 200 |

### Throttling

Segundos de cada tanda con cada motivo (`clocks_throttle_reasons.active`); ninguno con HW slowdown.

| Sesiones | GPU 0 térmico / potencia | GPU 1 térmico / potencia | Temp. máx GPU 0 / 1 |
|---|---|---|---|
| 4 | 8 / 13 de 110 s | 0 / 40 de 110 s | 75 / 70 °C |
| 8 | 16 / 23 de 110 s | 0 / 57 de 110 s | 73 / 74 °C |
| 16 | 39 / 23 de 120 s | 8 / 89 de 120 s | 73 / 78 °C |
| 32 | 53 / 28 de 140 s | 3 / 89 de 140 s | 73 / 78 °C |

Con la GPU a ≥50 % de uso, el clock SM baja 2 % en la GPU 0 con thermal slowdown (1881 contra
1917 MHz) y 3 % en la GPU 1 con tope de 350 W (1814 contra 1874 MHz).

### Latencia de punta a punta (cliente)

De [cliente.csv](cliente.csv), solo turnos apareados cliente-server (en 32, 30 de 221 filas).

| Sesiones | Llamadas atendidas | Con el turno 0 perdido | Latencia cliente p50 / p95 | e2e p50 | LLM hasta el texto p50 | LLM total p50 | eou p50 |
|---|---|---|---|---|---|---|---|
| 4 | 4 de 4 | 1 | 3,37 / 7,26 s | 2,08 s | 0,45 s | 1,08 s | 1,00 s |
| 8 | 8 de 8 | 2 (+1 en el turno 2) | 3,88 / 5,17 s | 2,33 s | 0,61 s | 1,34 s | 1,00 s |
| 16 | 16 de 16 | 3 | 4,57 / 6,05 s | 2,76 s | 0,66 s | 1,45 s | 1,06 s |
| 32 | **20 de 32** | 7 (+1 en el turno 1) | — | — | — | — | — |

Reporte completo: [analyze-4.txt](analyze-4.txt), [analyze-8.txt](analyze-8.txt),
[analyze-16.txt](analyze-16.txt), [analyze-32.txt](analyze-32.txt).

## Análisis

- **Hasta 16 escala lineal y la inferencia sobra.** Cada sesión hace un turno cada ~20 s en las tres tandas. De 4 a 16 el TTFT del LLM pasa de 96 a 133 ms y el TTS entre tokens de 14 a 17 ms (tope de tiempo real: 83 ms). No hay cola en ningún servicio.
- **32 no midió la inferencia.** Carga igual a la de 16 (STT por sesión 0,025). De las 32 llamadas: 9 nunca saludaron (timeout de 20 s) y 3 saludaron pero no respondieron ningún turno. Todas arrancaron después de +3,8 s de la ráfaga.
- **Causa (corregida en [EXP-011](../EXP-011-agente-en-server-despacho-livekit/)): el despacho de LiveKit Cloud.** Acá se la atribuyó a la CPU de la laptop, que corría el agente y los callers. Sus logs, a las 10:57–10:58, mostraban:
  - `assignment for job ... timed out`;
  - `The room connection was not established within 10 seconds`;
  - `VAD inference is slower than realtime` (delay 0,27 s);
  - event loop bloqueado 100–300 ms.

  Pero con el agente en el server, sin saturar (EXP-011), el techo siguió: LiveKit Cloud dejó jobs en `JS_PENDING` sin asignar. La laptop sumaba carga, pero no era el techo. EXP-006 a 008 tuvieron el mismo techo (19–21 de 32 llamadas ok).
- **Turno 0 perdido en 19–25 % de las llamadas hasta 16 sesiones (35 % en 32).** El agente no contesta la primera frase en 15 s y el server registra 5 turnos en vez de 6. Aparece desde 4 sesiones, así que no es por carga: es del loadtest o del agente. Probable (no verificado): el caller publica el micrófono y habla enseguida, y el agente pierde el inicio. Esas llamadas quedan sin aparear en el CSV.
- **Latencia del cliente +1,2 s de 4 a 16, casi toda fuera de vLLM.** El TTFT de vLLM sube 37 ms. "LLM total" sube 0,37 s, porque incluye esperar la extracción del turno anterior. El resto es la diferencia entre cliente y e2e (~1,3–1,8 s): VAD, red y el cliente.
- **Contra EXP-008 (4B, 32 sesiones, 19 ok):**
  - Con carga parecida (TTS s0 1,4 contra 1,6 req/s), el LLM pasa de 103 a 150 ms de TTFT y de 14,4 a 15,7 ms entre tokens, y hace el doble de pedidos por turno (respuesta + extracción).
  - El TTS primer audio baja de 266 a 115 ms, probablemente porque el checkpoint fine-tuneado no lleva audio de referencia en el prompt.
- **Throttling sin efecto medible.** La GPU 0 entra en thermal slowdown con el núcleo a 71–75 °C, debajo del objetivo de 83 °C: probablemente la GDDR6X (su temperatura no se ve con `nvidia-smi`). La GPU 1 está limitada por potencia. Cuesta 2–3 % de clock.

## Conclusión

Con 16 llamadas simultáneas la config vigente usa ~50–60 % de cada GPU, sin cola. El límite de
capacidad de la inferencia no se midió: el despacho de LiveKit Cloud cortó en ~20 sesiones (ver
EXP-011).

Siguiente paso, antes de repetir la tanda de 32:
1. `livekit-server` propio en este host, para medir sin LiveKit Cloud (EXP-011).
2. Cargar el VAD una vez por proceso, en `prewarm`: en la laptop bloqueaba el event loop al entrar 32 jobs juntos.
3. Resolver el turno 0 perdido (esperar a que el agente se suscriba al micrófono antes de hablar), para que el CSV aparee todas las llamadas.
