# EXP-011 — Agente en el server; el techo es el despacho de LiveKit Cloud

- **Fecha:** 2026-09-25
- **Pregunta:** ¿el techo de ~20 llamadas de EXP-010 es la CPU del worker del agente?
- **Cambio respecto de:** EXP-010 (misma inferencia; `app` + `agent` pasan de la laptop a este server, junto a la inferencia; los callers siguen en la laptop).
- **Resultado:** no es la CPU. El worker usó ≤4 cores y nunca se declaró lleno. LiveKit Cloud dejó jobs en `JS_PENDING` sin asignarlos, con el caller ya en la room: se atendieron 19 y 24 de 32. La inferencia con 24 llamadas simultáneas sigue sin cola.

## Configuración

Inferencia igual que [EXP-010](../EXP-010-loadtest-9b-motor-workflow/) (sin override); config efectiva en [meta.json](meta.json), idéntica en los dos runs.

- `app` + `agent` (LiveKit Agents 1.8.3, `start`, `load_threshold` 0.7 por defecto) en este host. Le pegan a la inferencia por la red de compose, sin el proxy.
- Callers (`run.py`) en la laptop: `--base-url http://192.168.1.99:8011 --turns 6 --workflow demo_booking` (`engine: structured`).
- LiveKit Cloud, plan Build (gratuito). Un solo worker registrado (`AW_aVGBJ36tJ3G3`).
- Runs crudos (local), sin warm-up:
  - **A**, tandas 4/8/16/32: `scripts/loadtest/monitor/run_20260925_112244_agente_local`.
  - **B**, tandas 16/32: `scripts/loadtest/monitor/run_20260925_115714_16_32_dispatch`, con el vigía de despachos `scripts/loadtest/monitor/dispatch_watch.py` → [dispatch_watch.jsonl](dispatch_watch.jsonl).

## Resultados

### Llamadas atendidas (base de la `app`)

| Tanda | Atendidas | Nunca despachadas | Despachadas tarde (caller ya se había ido) | Máx. simultáneas |
|---|---|---|---|---|
| A 4 | 4 | 0 | 0 | |
| A 8 | 8 | 0 | 0 | |
| A 16 | 13 | 2 | 1 | |
| A 32 | 19 | 11 | 2 | **19** |
| B 16 | 16 | 0 | 0 | |
| B 32 | 24 | 7 | 1 | **24** |

### Inferencia por tanda (server)

| Tanda | STT req/s | LLM req/s | LLM TTFT / entre tokens | TTS entre tokens | TTS primer audio | Máx. en vuelo LLM / TTS | GPU 0 / 1 uso | Agente, cores prom. / máx |
|---|---|---|---|---|---|---|---|---|
| A 4 | 0,3 | 0,5 | 99 / 12,9 ms | 15,2 ms | 88 ms | 4 / 4 | 22 / 37 % | 0,5 / 1,2 |
| A 8 | 0,5 | 1,0 | 114 / 15,4 ms | 16,5 ms | 111 ms | 5 / 6 | 41 / 54 % | 0,9 / 3,0 |
| A 16 | 0,7 | 1,4 | 123 / 15,7 ms | 16,7 ms | 115 ms | 5 / 7 | 53 / 69 % | 1,5 / 2,9 |
| A 32 | 1,0 | 2,0 | 136 / 18,2 ms | 18,3 ms | 129 ms | 8 / 9 | 62 / 74 % | 2,0 / 3,2 |
| B 16 | 1,0 | 2,0 | 136 / 17,0 ms | 18,9 ms | 139 ms | 9 / 9 | 61 / 76 % | 1,9 / 3,9 |
| B 32 | 1,2 | 2,5 | 143 / 20,3 ms | 21,0 ms | 154 ms | 13 / 9 | 68 / 76 % | 2,5 / 4,0 |

TTS primer audio: TTFT + cola del stage 1. Sin cola en LLM ni TTS s0, cola de STT ≤ 32 ms, sin
preemptions, KV máx 20 %. Reportes completos: `analyze-{a,b}-<tanda>.txt`.

### Latencia por turno (agente, `call.latency`)

| Tanda | e2e p50 / p95 | total p50 / p95 | eou p50 | LLM hasta el texto p50 / p95 | TTS p50 |
|---|---|---|---|---|---|
| A 4 | 1,17 / 1,69 s | 0,67 / 1,24 s | 0,41 s | 0,20 / 0,31 s | 0,04 s |
| A 8 | 1,53 / 1,93 s | 0,93 / 1,28 s | 0,57 s | 0,24 / 0,32 s | 0,06 s |
| A 16 | 1,49 / 2,12 s | 0,96 / 1,37 s | 0,59 s | 0,23 / 0,37 s | 0,07 s |
| A 32 (19) | 1,52 / 2,26 s | 1,01 / 1,46 s | 0,59 s | 0,25 / 0,53 s | 0,07 s |
| B 16 | 1,56 / 2,36 s | 0,94 / 1,46 s | 0,57 s | 0,25 / 0,42 s | 0,07 s |
| B 32 (24) | 1,77 / 2,59 s | 1,00 / 1,52 s | 0,59 s | 0,28 / 0,54 s | 0,08 s |

### Throttling

GPU 0 con thermal slowdown en 9–53 % de los segundos de cada tanda (máx. 77 °C); GPU 1 con tope de
potencia en 36–77 % (máx. 80 °C). Ninguna con HW slowdown. Mismo efecto que en EXP-010 (−2 a −3 % de clock). GPUs ya reubicadas: la
GPU 1 llega a 80 °C con 76 % de uso, contra 84–85 °C con 55–60 % en EXP-003 y 008.

## Análisis

- **El worker no es el techo.** Con 24 llamadas usó 2,5 cores de promedio y 4 de máximo, de 16. Nunca pasó a `WS_FULL`: no hay ningún `worker is at full capacity` en el log.
- **El techo está en el despacho de LiveKit Cloud:**
  - La `app` creó los 60 y 48 despachos sin error. LiveKit le entregó al worker 47 y 41 jobs.
  - El vigía muestra que las llamadas no atendidas tienen el job en `JS_PENDING`, sin worker ni error, mientras el caller (`loadtest-<id>`) ya está en la room. Siguen así hasta que el caller se va y la room se cierra.
  - Otras llamadas reciben el job tarde, a los ~6, ~16 o ~36 s.
  - En el dashboard, la room `call-ee06e270` (run A) muestra 1 solo participante durante 21 s: el caller que espera el saludo.
  - El techo varía (19 y 24), así que no es un tope fijo documentado. El tope de 5 sesiones del plan Build rige para agentes desplegados en Cloud, y acá hubo 24.
  - No sabemos qué lo dispara. Cada room muestra 2 despachos con un solo job, sin explicación todavía.
- **Corrige EXP-010:** aquel techo de 20 de 32 también era el despacho, no la CPU de la laptop, aunque la laptop además mostraba el VAD atrasado.
- **La inferencia con 24 llamadas simultáneas:**
  - GPU 0 (TTS) al 68 % y GPU 1 al 76 %, sin cola.
  - De 4 a 24 llamadas, el TTS entre tokens pasa de 15 a 21 ms (tope 83 ms) y el TTFT del LLM de 99 a 143 ms.
  - El turno sube poco: total p50 de 0,67 a 1,00 s; e2e p50 de 1,17 a 1,77 s.
- **Agente junto a la inferencia contra agente remoto:** con 16 llamadas, el e2e p50 es de 1,49–1,56 s, contra 2,76 s en EXP-010 con el agente en la laptop por el proxy. Son ~1,2 s por turno.

## Conclusión

La inferencia vigente atiende 24 llamadas simultáneas holgada. La capacidad de 32 o más no se
puede medir mientras el despacho dependa de LiveKit Cloud en el plan gratuito.

Siguiente paso:
1. `livekit-server` propio en este host (override), para medir 32 o más sin Cloud.
2. Opcional: reclamar a soporte de LiveKit con [dispatch_watch.jsonl](dispatch_watch.jsonl).
3. En producción, el agente va en el mismo nodo que la inferencia.
