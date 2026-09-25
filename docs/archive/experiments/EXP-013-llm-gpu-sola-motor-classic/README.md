# EXP-013 — LLM solo en una GPU y motor classic: 48 llamadas con p95 de 4,1 s

- **Fecha:** 2026-09-25
- **Pregunta:** ¿qué limita pasar de 32 llamadas (EXP-012), y cuánto mejoran el reparto de GPU y el motor `classic`?
- **Cambio respecto de:** EXP-012 (LiveKit propio, LLM + STT en la GPU 1, TTS sola en la GPU 0, motor `structured`).
- **Resultado:**
  - Con el reparto de EXP-012 el LLM satura en 64 llamadas: con 32 secuencias encola y con 64 llena el KV cache.
  - LLM solo en la GPU 0 (0.90, KV el doble) + motor `classic`: espera del cliente p50 2,86 s / p95 4,14 s con 48 llamadas, lo mismo que 32 con `structured`.
  - El techo pasa a ser la CPU del host: con 64 llamadas los 16 threads al 98 % y el VAD atrasado. **Config vigente desde este experimento.**

## Configuración

| Corrida | Reparto de GPU | LLM `--max-num-seqs` / memoria | TTS `max_num_seqs` | Motor | Tandas | Run crudo |
|---|---|---|---|---|---|---|
| A | GPU 1: LLM + STT + escritorio; GPU 0: TTS | 32 / 0.70 (KV 4,8 GiB) | 64 | `structured` | 48, 64 (96 inválida) | `run_20260925_125756_48_64_96` |
| B | ídem A | 64 / 0.70 | 64 | `structured` | 64 | `run_20260925_150246_capacidad_env` |
| C | **GPU 0: LLM solo; GPU 1: TTS + STT + escritorio** | 128 / 0.90 (KV 9,4 GiB) | 128 | `structured` | 32, 48, 64, 96 | `run_20260925_152522_gpu_llm_solo_seqs128` |
| D | ídem C | 128 / 0.90 | 128 | **`classic`** | 32, 48, 64, 96 | `run_20260925_164023_classic` |

- Modelos como EXP-012: LLM `RedHatAI/Qwen3.5-9B-quantized.w4a16`, STT Parakeet TDT 0.6B v3 (batch 8), TTS Qwen3-TTS `multi41`. Config efectiva: [A](meta-a-compartida.json), [C](meta-c-llm-sola.json), [D](meta-d-classic.json).
- LiveKit propio, `app` + `agent` en este host. Callers en la laptop por la LAN, 6 turnos, workflow `demo_booking` (A, B, C) y `demo_booking_classic` (D, el mismo con `engine: classic`).
- Warm-up antes de B y C; D sin warm-up.

## Resultados

### Espera del cliente (fin de su habla → primer audio del agente)

De [cliente-c-structured.csv](cliente-c-structured.csv) y [cliente-d-classic.csv](cliente-d-classic.csv) (`client_latency_s`). A: del CSV del mismo día, no guardado.

| Llamadas | A `structured`, GPU compartida | C `structured`, LLM solo | **D `classic`, LLM solo** |
|---|---|---|---|
| 32 | — | 2,66 / 4,01 s | **2,15 / 3,42 s** |
| 48 | 3,90 / 6,07 s | 3,69 / 5,82 s | **2,86 / 4,14 s** |
| 64 | 7,56 / 12,29 s | 5,82 / 10,17 s | 4,74 / 7,05 s |
| 96 | inválida (la laptop creó 60) | 6,32 / 13,86 s, 174 turnos sin respuesta | 3,51 / 13,20 s, 133 sin respuesta |

p50 / p95. Con 96 los percentiles no cuentan los turnos sin respuesta en 15 s: la espera real es peor.

| D `classic` | Turnos > 3 s | > 5 s | > 10 s |
|---|---|---|---|
| 32 | 24 de 192 | 0 | 0 |
| 48 | 117 de 288 | 3 | 0 |
| 64 | 342 de 383 | 161 | 0 |

### e2e del server (`call.latency`, p50 / p95)

| Llamadas | A | B (64 secuencias) | C | D |
|---|---|---|---|---|
| 32 | — | — | 1,77 / 2,87 s | 1,19 / 1,94 s |
| 48 | 2,71 / 4,96 s | — | 2,51 / 4,59 s | 1,47 / 2,48 s |
| 64 | 6,71 / 11,54 s | 7,60 / 17,16 s | 4,45 / 8,71 s | 2,86 / 4,68 s |
| 96 | — | — | 6,26 / 10,14 s | 4,50 / 8,55 s |

El cliente espera ~0,9 s más que la e2e aun sin carga (red, buffers de WebRTC y la detección del caller).

### LLM

| Corrida, llamadas | req/s | TTFT | entre tokens | cola | en vuelo máx. | KV máx. | preempt. |
|---|---|---|---|---|---|---|---|
| A, 48 | 4,4 | 226 ms | 38,7 ms | 0 | 31 | 52 % | 0 |
| A, 64 | 4,7 | 2.221 ms | 67,4 ms | 1.883 ms | 62 | 53 % | 0 |
| B, 64 | 3,8 | 1.122 ms | 129,0 ms | 357 ms | 88 | **100 %** | **16** |
| C, 64 | 6,2 | 335 ms | 63,3 ms | 1 ms | 56 | 45 % | 0 |
| D, 64 | 3,4 | 288 ms | 29,7 ms | 0 | 20 | 16 % | 0 |

### Por tanda en C y D

| Corrida, llamadas | TTS entre tokens | STT inferencia / cola | eou p50 | GPU 0 / 1 uso | CPU host p95 | agente cores máx. | "VAD slower than realtime" |
|---|---|---|---|---|---|---|---|
| C, 32 | 26,3 ms | 178 / 42 ms | 0,64 s | 82 / 86 % | 58 % | 4,6 | 0 |
| C, 48 | 36,2 ms | 239 / 79 ms | 0,80 s | 85 / 88 % | 83 % | 7,4 | 0 |
| C, 64 | 44,4 ms | 525 / 241 ms | 1,25 s | 87 / 92 % | 98 % | 10,4 | 495 |
| C, 96 | 48,2 ms | 814 / 415 ms | 2,25 s | 82 / 79 % | 99,7 % | 11,1 | 16.273 |
| D, 32 | 30,7 ms | 170 / 37 ms | 0,61 s | 72 / 84 % | 61 % | 5,0 | 0 |
| D, 48 | 41,7 ms | 223 / 73 ms | 0,74 s | 67 / 76 % | 83 % | 8,6 | 0 |
| D, 64 | 54,8 ms | 599 / 279 ms | 1,42 s | 78 / 74 % | 98,7 % | 10,2 | 928 |
| D, 96 | 61,3 ms | 795 / 396 ms | 1,92 s | 81 / 76 % | 99,7 % | 11,3 | 16.635 |

Temperatura máx. 80 °C, sin HW slowdown. Reportes completos: `analyze-{a,b,c,d}-<tanda>.txt`.

### Dónde se va la espera con 32 llamadas (D, p50 2,15 s)

~0,3 s de silencio para el VAD (`min_silence_duration`), ~0,2 s de STT (transcribe al final, sin
parciales), 0,17 s del LLM hasta el primer texto, ~0,3–0,6 s hasta tener la primera oración
completa y su primer audio, y ~0,9 s entre server y cliente. Sin carga (1–2 llamadas) el cliente
espera 1,8–2,0 s: la carga de 32 llamadas suma poco.

## Análisis

- **A: con el LLM en la GPU compartida, 64 llamadas saturan el LLM.** Con 32 secuencias hay 62 pedidos para 32 lugares, 1,9 s de cola y la CPU del host al 97 %.
- **B: subir a 64 secuencias con la misma memoria empeora.**
  - El KV cache (4,8 GiB) llega al 100 %, con 16 preemptions, y el entre tokens se duplica (129 ms).
  - Las 4 llamadas que quedaron `en_curso` las mató el agente al cortar, esperando la extracción.
- **C: el LLM solo en la GPU 0 (0.90) duplica el KV cache (9,4 GiB).** Con 64 llamadas, 56 pedidos en vuelo, KV 45 %, sin cola ni preemptions. La espera con 64 baja de 7,56 a 5,82 s p50. El techo pasa a la CPU del host.
- **D: el motor `classic` hace la mitad de pedidos al LLM y más cortos** (texto directo, sin JSON).
  - LLM hasta el primer texto: 0,30 → 0,17 s con 32 llamadas y 0,94 → 0,44 s con 64.
  - Espera del cliente: −0,5 s con 32 y −0,8 s con 48 (p50). 48 llamadas quedan como 32 con `structured`.
- **TTS + STT en la misma GPU (C, D):** hasta 48 llamadas el STT no se resiente (223–239 ms, contra ~220 ms solo con el LLM). Con 64 sube a 525–599 ms, por la GPU compartida y la CPU saturada (thread principal del STT al 74–85 %). La regla "TTS nunca comparte GPU" (EXP-001 a 004) se midió con Qwen3-ASR (7 GB, vLLM); con Parakeet vale hasta ~48 llamadas.
- **El techo ahora es la CPU del host.**
  - El agente usa ~0,12–0,17 cores por llamada (hasta 11 cores con 64–96), más ~5,5 cores de la inferencia.
  - Con 64 llamadas los 16 threads llegan al 98 %: el VAD se atrasa (928 avisos en D) y el fin de turno pasa de 0,6 a 1,4 s.
  - Las GPUs quedan al 74–81 % con 64 en D.
- **El pico de GPU al arrancar cada tanda** es el TTS con todos los saludos juntos (hasta 22 síntesis en los primeros 16 s). No encola. Es propio del loadtest, que abre todas las llamadas en ~16 s.

## Conclusión

Vigente desde este experimento:
- LLM solo en la GPU 0 con 0.90 y 128 secuencias.
- TTS (128 por etapa) + STT en la GPU 1.
- Motor `classic` (`WORKFLOW_ID=demo_booking_classic`).

Capacidad de este host: ~32 llamadas con p95 ≤ 3,5 s y ~48 con p95 ≤ 4,2 s. Con 64 la CPU satura.

Siguiente paso:
1. **Más llamadas:** el agente en otra máquina, o más CPU. El VAD en `prewarm`.
2. **Menos espera:** que el TTS arranque antes de la primera oración completa, y STT con parciales. Estimado ~1,3–1,5 s de p50 con 32 llamadas.
