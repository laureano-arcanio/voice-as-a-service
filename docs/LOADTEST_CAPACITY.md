# Pruebas de capacidad (21-sep-2026)

Objetivo: definir el hardware de producción (menor costo inicial, buena
latencia a 32 conversaciones, redundancia). Este server (Ryzen 7 5700X, 64 GB,
2 × RTX 3090, con escritorio) es **solo de validación**.

Método: load test remoto por ngrok a 16 y 32 sesiones, midiendo en el server a
1 Hz con `scripts/loadtest/monitor/sampler.py` (CPU por core, CPU/RAM/threads
por contenedor, GPU por proceso, `/metrics` de cada vLLM). Resumen con
`analyze.py <run> [t0 t1]`. Datos crudos en `scripts/loadtest/monitor/run_*`.
No se midió la latencia de punta a punta del cliente (queda en el CSV remoto).

## Experimentos (32 sesiones, media por request)

| # | Reparto | TTS req/s | TTS entre tokens | TTS primer audio (TTFT + cola stage 1) | STT TTFT | LLM TTFT / entre tokens |
|---|---|---|---|---|---|---|
| 1 | LLM en GPU 0; STT + TTS en GPU 1 (con escritorio) | 1,6 | 28 ms | 202 + 96 ms | 108 ms | 68 / 13,2 ms |
| 2 | LLM en GPU 1; STT + TTS en GPU 0 (sin escritorio) | 1,8 | 32 ms | 220 + 110 ms | 136 ms | 74 / 14,7 ms |
| **3** | **TTS sola en GPU 0; LLM + STT en GPU 1** | **2,8** | **32 ms** | **219 + 105 ms** | **79 ms** | 83 / 16,4 ms |
| 4 | Como 3, con 2 réplicas de TTS en la misma GPU 0 (nginx `least_conn`) | 2,7 | **71 ms** | 460 + 271 ms | 89 ms | 87 / 17,1 ms |

- **1 → 2:** sacar el escritorio de la GPU de TTS no cambió nada. No era la causa.
- **3 es la mejor** y quedó configurada: +50% de throughput con la misma
  latencia de TTS, y STT responde ~85 ms antes por turno. El LLM paga ~10 ms de TTFT.
- **4 fue peor:** dos procesos se turnan la GPU y cada uno batchea la mitad.
  71 ms entre tokens roza el tope de tiempo real del códec (12 Hz = 83 ms).
  Más réplicas de TTS solo sirven con **una GPU física por réplica**.
  `vllm-tts-2` quedó en el compose como perfil opt-in `tts2`.

## Qué limita y qué sobra

| Recurso | Medido a 32 sesiones | Conclusión |
|---|---|---|
| **GPU de TTS** | 98% de uso en mediana; una 3090 da ~2,8 síntesis/s | **Único cuello.** Una 3090 dedicada alcanza justo para 32 sesiones |
| GPU de LLM + STT | 55% de uso; LLM sin cola nunca; máx. 8 requests simultáneos | Sobra |
| CPU | Host 25–40%; ningún core > 90%. TTS 2,2 cores, STT 0,9, LLM 0,4 (p95) | 8 cores / 16 hilos sobran. Importa la velocidad por core: el thread del engine de TTS llega a 70% (p95) |
| RAM | ~15 GB entre los 3 vLLM, constante | 32 GB alcanzan |
| VRAM | KV cache máx.: LLM 12% de 73k tokens, TTS 5%, STT 2% | Necesidad real: LLM ~13 GB (BF16), TTS ~10 GB, STT ~8 GB |
| Térmica | Ambas 3090 con thermal/HW slowdown (84 °C; GPU 0 throttlea a 73 °C de núcleo, probable memoria) | Refrigeración es requisito, hoy se pierde rendimiento |

Concurrencia real: 32 sesiones ≠ 32 requests. Picos de 8 en LLM, 5 en STT y
~14 en TTS (2,4 síntesis por turno, ~1,5 s cada una).

## Implicancias para el hardware (ver `SERVER_HARDWARE.md`)

1. **Un modelo por GPU es correcto**, y TTS nunca debe compartir GPU (ni con
   STT, ni con otra réplica de TTS).
2. **El riesgo de la RTX 5060 Ti es TTS, no el LLM.** TTS ya satura una 3090 a
   32 sesiones; el LLM usa la mitad de la suya. Comprar una sola 5060 Ti y
   medir **primero TTS** (criterio: < ~45 ms entre tokens a 32 sesiones; el
   tope duro es 83 ms). Si no llega: 2 GPUs para TTS o una GPU más fuerte solo
   para TTS.
3. **CPU y RAM: ir a lo más barato.** La prueba pendiente de la sección 6 de
   `SERVER_HARDWARE.md` queda cubierta en lo esencial: ~4 cores usados de 16.
   El 5700G es razonable; no se hizo la prueba de bajar frecuencia.
4. **16 GB por GPU alcanzan** para cada modelo por separado. LLM + STT juntos
   (como en la config. 3) no entran en 16 GB en BF16.
5. **Sin escritorio y con buen flujo de aire** (frame abierto ayuda).

## Arquitectura propuesta (costo inicial mínimo)

- **Fase 1:** un nodo nuevo de 3 GPUs (LLM / STT / TTS). Redundancia con **este
  server 2 × 3090 como segundo nodo** (config. 3, ya validada para 32 sesiones):
  costo adicional cero. nginx con upstreams por servicio hace el failover; el
  upstream `tts` con `least_conn` ya está probado en `ngrok/proxy.conf`.
- **Fase 2 (si crece la carga o TTS queda justo):** sumar una GPU solo para TTS.
  Es el único componente que escala con las sesiones.
- Para que un nodo absorba la caída del otro, TTS debe operar a ≤ 50% de su
  capacidad en régimen normal.

## Pendiente

- Benchmark de TTS y LLM (FP8) en una 5060 Ti.
- Cruzar con la latencia de punta a punta del cliente remoto.
- Prueba a 64 sesiones para encontrar el techo real de LLM y STT.
- Confirmar temperatura de memoria de las 3090 (`nvtop`).
- vLLM-Omni deja `num_requests_running` pegado en 1 sin tráfico: no usar ese
  gauge para detectar inactividad (el sampler usa los contadores de tokens).
