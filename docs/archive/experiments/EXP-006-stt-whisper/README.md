# EXP-006 — STT con Whisper Large v3 Turbo en lugar de Qwen3-ASR

- **Fecha:** 2026-09-22
- **Pregunta:** ¿cuánto cambian la latencia y el uso de recursos de STT si se reemplaza Qwen3-ASR-1.7B por Whisper Large v3 Turbo?
- **Cambio respecto de:** EXP-003 (sale `vllm-stt`; entra `stt-whisper` en la misma GPU 1, junto a la LLM, con `--gpu-memory-utilization` 0.16)
- **Resultado:** STT transcribe en menos de la mitad de tiempo (96 contra 228 ms con 32 sesiones), con la mitad de VRAM y ~1/6 de CPU. No cambia el cuello, que sigue siendo la GPU de TTS. Falta medir la calidad en llamadas reales.

## Configuración

| GPU | Servicio | Modelo | Imagen (versión) | `--gpu-memory-utilization` | Otros flags |
|---|---|---|---|---|---|
| 0 | vllm-tts | Qwen/Qwen3-TTS-12Hz-1.7B-Base, voz `sofia_ar` | vllm/vllm-omni:v0.28.0 | 0.4 | max-model-len 4096 |
| 1 | vllm-llm | Qwen/Qwen3.5-4B (BF16) | vllm/vllm-openai:latest (vLLM 0.29.0) | 0.55 | max-model-len 32768, max-num-seqs 32, max-cudagraph-capture-size 32 |
| 1 | stt-whisper | openai/whisper-large-v3-turbo | build `stt-whisper` (vLLM 0.29.0) | 0.16 | max-num-seqs 32, max-cudagraph-capture-size 32 |

- Compose: `docker-compose.yml` + `docker-compose.stt-candidates.yml` (`make servers-whisper`).
- VRAM de la GPU 1: 17,4 GB como máximo (LLM 12,0 + Whisper 3,9 + escritorio). En EXP-003 eran 21,6 GB, con Qwen3-ASR en 8,2 GB.
- Host: server de validación (ver [README](../README.md#entorno-de-validación)).
- Loadtest: cliente remoto por ngrok, tandas de 16 y 32. Warm-up: sí (fin marcado en `1790076043`).
- Tandas: sin hueco en buckets de 20 s. Con buckets de 5 s aparece un corte de 10 s en `1790076213`–`1790076223`, seguido del pico de saludos de TTS (25 síntesis en vuelo).
- Run crudo (local): `scripts/loadtest/monitor/run_20260922_080816_whisper`; config efectiva en [meta.json](meta.json).

## Resultados

### 16 sesiones

Ventana `1790076078`–`1790076213`: 135 s activos.

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| stt-whisper | 0.7 | 85 | 1.8 | 89 | 0 | 0.0 / 1 | 2 | 0 |
| vllm-tts s0 | 2.1 | 60 | 25.0 | 1288 | 0 | 2.9 / 13 | 5 | 0 |
| vllm-tts s1 | 2.1 | 165 | 501.3 | 1259 | 80 | 3.1 / 13 | 0 | 0 |
| vllm-llm | 0.7 | 86 | 15.0 | 708 | 0 | 0.4 / 7 | 22 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 77% | 76% | 12792 | 267 / 334 | 71 °C | VLLM::StageEngi 69% 9194, VLLM::StageEngi 19% 3558 |
| 1 | 43% | 39% | 17213 | 202 / 343 | 77 °C | VLLM::EngineCor 46% 11960, VLLM::EngineCor 7% 3922 |

Host: CPU 15% prom. / 30% máx; cores >90%: máx 1; RAM usada máx 38.8 GB; swap máx 4.2 GB; proceso ajeno más cargado: hyte (app-org.chromium.Chromium-9838.scope) p95 100% de un core.

| Contenedor | CPU cores p95 / máx | RAM máx GB | thread más cargado (p95 % de un core) |
|---|---|---|---|
| stt-whisper | 0.13 / 0.29 | 2.8 | VLLM::EngineCor 7% |
| vllm-tts | 2.16 / 2.27 | 5.8 | VLLM::StageEngi 67% |
| vllm-llm | 0.33 / 0.41 | 4.3 | VLLM::EngineCor 26% |

### 32 sesiones

Ventana `1790076223`–`1790076393`: 164 s activos.

| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |
|---|---|---|---|---|---|---|---|---|
| stt-whisper | 0.8 | 87 | 2.4 | 96 | 0 | 0.0 / 2 | 3 | 0 |
| vllm-tts s0 | 1.9 | 74 | 28.6 | 1694 | 0 | 3.4 / 15 | 5 | 0 |
| vllm-tts s1 | 1.9 | 190 | 581.2 | 1659 | 92 | 3.6 / 16 | 0 | 0 |
| vllm-llm | 0.8 | 96 | 15.3 | 724 | 0 | 0.5 / 6 | 22 | 0 |

| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |
|---|---|---|---|---|---|---|
| 0 | 76% | 76% | 12800 | 250 / 334 | 72 °C | VLLM::StageEngi 66% 9194, VLLM::StageEngi 21% 3566 |
| 1 | 37% | 27% | 17382 | 210 / 344 | 81 °C | VLLM::EngineCor 47% 11960, VLLM::EngineCor 8% 3922, gnome-shell 4% 280 |

Host: CPU 17% prom. / 36% máx; cores >90%: máx 1; RAM usada máx 39.1 GB; swap máx 4.2 GB; proceso ajeno más cargado: hyte (app-org.chromium.Chromium-9838.scope) p95 100% de un core.

| Contenedor | CPU cores p95 / máx | RAM máx GB | thread más cargado (p95 % de un core) |
|---|---|---|---|
| stt-whisper | 0.14 / 0.25 | 2.8 | VLLM::EngineCor 8% |
| vllm-tts | 2.19 / 2.34 | 5.8 | VLLM::StageEngi 70% |
| vllm-llm | 0.35 / 0.44 | 4.3 | VLLM::EngineCor 25% |

### Latencia de punta a punta (cliente)

Resumen de `run.py`, 6 turnos por llamada (el CSV no se guardó). Los `*_s` salen de las métricas del agente. `total_s` = `eou_s` + `ttft_s` + `tts_s`, y `eou_s` incluye a `stt_s`.

| Métrica (avg / p50 / p95 / máx, s) | 16 sesiones (16/16 ok, n=96) | 32 sesiones (21/32 ok, n=126) |
|---|---|---|
| client_latency_s | 2.07 / 2.54 / 4.03 / 4.27 | 2.54 / 2.88 / 3.89 / 5.17 |
| think_time_s | 2.78 / 2.15 / 5.79 / 7.53 | 3.19 / 2.78 / 7.06 / 9.27 |
| eou_s | 0.80 / 0.75 / 1.00 / 1.03 | 0.79 / 0.73 / 1.00 / 1.00 |
| stt_s | 0.66 / 0.65 / 0.80 / 0.89 | 0.68 / 0.67 / 0.84 / 0.98 |
| endpointing_s | 0.14 / 0.01 / 0.44 / 0.44 | 0.11 / 0.01 / 0.43 / 0.44 |
| ttft_s | 0.30 / 0.27 / 0.49 / 0.57 | 0.31 / 0.30 / 0.48 / 0.55 |
| llm_total_s | 0.99 / 0.87 / 2.51 / 3.38 | 1.01 / 0.81 / 2.07 / 2.93 |
| tts_s | 0.34 / 0.32 / 0.48 / 0.59 | 0.37 / 0.35 / 0.51 / 0.66 |
| total_s | 1.44 / 1.39 / 1.88 / 2.00 | 1.48 / 1.42 / 1.79 / 2.05 |

- Tanda de 16: 2 min 22 s. Tanda de 32: 3 min 07 s, con 8 procesos de 4 callers y arranque escalonado cada 0,25 s.
- Tanda de 32: 11 llamadas fallaron con `TimeoutError: timeout esperando que el agente empiece a responder` y quedaron sin apareamiento cliente/server (11/32).

Reporte completo: [analyze-16.txt](analyze-16.txt), [analyze-32.txt](analyze-32.txt).

## Análisis

- **STT, latencia:** la inferencia baja de 184 a 89 ms con 16 sesiones y de 228 a 96 ms con 32 (−52% y −58% contra EXP-003), y casi no crece con la carga. El primer token sale algo más tarde (85–87 contra 66–79 ms): en Whisper el encoder hace casi todo el trabajo antes del primer token. Después decodifica a 1,8–2,4 ms por token, contra 9,9–12,2 ms de Qwen3-ASR. Sin cola, y como máximo 2 requests en vuelo.
- **STT, recursos:** 3,9 GB de VRAM contra 8,2 GB, 0,14 cores p95 contra 0,94, y el thread más cargado en 8% contra 49%. En la GPU usa 7–8% de SM, contra 11–15% de Qwen3-ASR.
- **La carga cambió respecto de EXP-003, por el agente o el test y no por el STT:**
  - Los prompts del LLM son ~47% más largos (2.700 contra 1.840 tokens por request) y las respuestas ~18% más largas (43 contra 36 tokens).
  - Por eso sube el LLM, que no depende del STT: TTFT 86–96 ms contra 73–83, inferencia 708–724 contra 598–657 ms y KV máx 22% contra 9–12%. El tiempo entre tokens es el mismo (15 ms).
  - Por eso también la GPU 1 no baja con 16 sesiones (39% de los segundos ≥95% contra 31%), aunque STT consume menos: el LLM pasa de 38% a 46% de SM.
- **Tráfico con 32 sesiones:** solo 21 de las 32 llamadas funcionaron (21 × 6 = 126 turnos, 0,8/s). En EXP-003 hubo 153 turnos (1,1/s), unas 25 llamadas. Con 16 sesiones fue igual (96 contra 97). En la tanda de 32, TTS y la GPU 1 trabajaron con menos carga que en EXP-003: esos números no se comparan de igual a igual.
- **Llamadas fallidas:** en las 11 el agente no llegó a hablar. El problema no está en la inferencia: ningún vLLM tuvo cola, errores ni aborts. Hipótesis sin verificar: el worker del agente corre con `start` (modo producción de livekit-agents 1.8) y el umbral de carga por defecto. En la PC del loadtest, con los 32 callers en la misma máquina, se declararía lleno y LiveKit no le despacharía más llamadas. Revisarlo en los logs del `agent` de esa PC.
- **STT desde el agente:** `stt_s` da 0,66–0,68 s, contra 89–96 ms de inferencia en el server. Los ~0,57 s restantes quedan fuera de la inferencia (ngrok de ida y vuelta, subida del audio, cliente). No hay dato de cliente para Qwen3-ASR (EXP-001 a 005 no lo registraron). Por eso no se sabe cuánto de la mejora de ~130 ms del server llega al agente.
- **TTS:** su GPU no cambió, y lo que mide sigue a la carga. Con 16 sesiones hubo 2,9 síntesis por turno (antes 2,3, por las respuestas más largas): 2,1 síntesis/s con 25,0 ms entre tokens. La GPU 0 estuvo ≥95% en el 76% de los segundos: sigue siendo el cuello.
- **Host:** un proceso ajeno (app Chromium "hyte" del escritorio) ocupó un core al 100% (p95) en las dos tandas. El host tuvo 15–17% de CPU promedio y como mucho un core >90%, así que no debería haber afectado al stack. Hubo 4,2 GB de swap en uso (en EXP-003, 0), con 39 GB de RAM usada sobre 64.
- **Térmica:** la GPU 1 llegó a 81 °C y la GPU 0 a 72 °C.

## Conclusión

En capacidad, Whisper Large v3 Turbo es mejor que Qwen3-ASR en todo lo que se midió: menos de la mitad de latencia, la mitad de VRAM (~4 GB) y ~1/6 de CPU. No cambia la capacidad total del sistema, porque STT no era el cuello. Lo que sí hace es liberar ~4 GB en la GPU del LLM, lo que acerca la opción de LLM + STT en una placa de 16 GB (12 + 4 GB, sin validar).

No se cambia la configuración vigente, porque falta calidad: en el corpus sintético empata con Qwen3-ASR en audio limpio y es mejor en audio telefónico (WER 5,6% contra 7,4%, ver [README](../../../../README.md#probar-otros-stt-perfil-stt-eval-opcional)). Eso es con 9 audios. Siguientes pasos:

- Repetir Qwen3-ASR (`make servers-qwen`) guardando el resumen del cliente, para comparar `stt_s` y `total_s` de punta a punta.
- Medir Parakeet con el mismo procedimiento (`make servers-parakeet`).
- Resolver las llamadas que el agente no toma con 32 sesiones, antes de medir el techo.
- Decidir con WER sobre recortes de llamadas reales.
