# CAP-001 — 2 × 3090 con tope de potencia, motor classic: ~32 llamadas con p95 de 3 s

- **Fecha:** 2026-09-25
- **Perfiles:** `base` (10 llamadas de a una) y `rampa` (escalones de 2 min: 4, 8, 16, 32, 64, 96)
- **Resultado:**
  - Piso con 1 llamada: espera p50 1,59 s / p95 1,89 s.
  - ~20 llamadas con p95 ≤ 2,4 s; ~32 con p95 ≤ 3,0 s.
  - Con ~32 llamadas se saturan las dos GPUs; con 64 además la CPU del host, y el servicio colapsa.
  - El agente usa ~104 MB y ~0,12 cores por llamada.

## Configuración

| | `base` | `rampa` |
|---|---|---|
| `hw_id` | `351644b6` (GPUs a 350 W, sin límites) | `8489259f` (GPUs a **280 W**, núcleo ≤ 1800 MHz, memoria 9501 MHz) |
| `config_id` | `4b7525ae` | `3c35f6bd` |
| Run | `20260925_205642_base` | `20260925_225825_rampa` |

- **Hardware:** Ryzen 7 5700X, 64 GB, 2 × RTX 3090 (GPU 0 en PCIe gen3 x16, GPU 1 en gen4 **x4**). Fichas completas en [base-hw-server.json](base-hw-server.json), [rampa-hw-server.json](rampa-hw-server.json) y [hw-cliente.json](hw-cliente.json).
- **Inferencia:** reparto vigente de `AGENTS.md`.
  - GPU 0: LLM Qwen3.5-9B w4a16, 0.90, 128 secuencias.
  - GPU 1: TTS `multi41` (128 por etapa) + STT Parakeet (batch 8).
- **Agente y LiveKit:** LiveKit propio, `app` + `agent` en este host.
- **Motor y llamadas:** workflow `demo_booking_classic`, voz `sofia`. Callers en la laptop por la LAN, con 4 a 8 turnos por llamada del corpus de 9 frases.
- **Límites de GPU:** se aplicaron entre los dos runs. Un primer intento de `rampa` sin límites apagó el server con ~32 llamadas: las GPUs sumaban 600–660 W sostenidos, con picos de más. Con los límites, el máximo medido fue 559 W y no hubo cortes.
- **Piso:** el `base` se midió sin límites. Los escalones de 4 y 8 llamadas de `rampa` (p50 1,58–1,61 s, p95 2,12 s) sirven de piso con límites. Conviene repetir `base` con límites.

## Resultados

### Espera del cliente por escalón (`rampa`)

Espera: desde que el caller termina de hablar hasta el primer audio del agente.

| Llamadas reales (objetivo) | Espera p50 / p95 | Agregada p95 | Sin respuesta | Saludo p50 / p95 | e2e server p50 / p95 | Buckets > 2 s |
|---|---|---|---|---|---|---|
| 7,2 (4) | 1,61 / 2,12 s | +0,22 s | 0 | 3,31 / 3,71 s (*) | 1,00 / 1,30 s | 13 % |
| 6,2 (8) | 1,58 / 2,12 s | +0,23 s | 0 | 0,97 / 2,79 s | 0,98 / 1,41 s | 9 % |
| 19,9 (16) | 1,86 / 2,38 s | +0,48 s | 0 | 1,32 / 3,12 s | 1,09 / 1,55 s | 35 % |
| **31,6 (32), codo** | **2,27 / 3,03 s** | +1,14 s | 0 | 1,54 / 3,86 s | 1,20 / 1,72 s | 71 % |
| 70,3 (64) | 5,83 / 8,25 s | +6,4 s | 7 | 4,71 / 6,84 s | 3,40 / 5,05 s | 99 % |
| 133 (96) | 10,7 / 14,4 s | colapso | 56 | 12,8 / 17,9 s | 6,37 / 11,7 s | 64 % de llamadas fallidas |

(*) El primer escalón arrancó con los modelos en frío: el warm-up (llegadas Poisson de tasa baja) no
generó ninguna llamada. Corregido: el warm-up ahora hace 3 llamadas a intervalos fijos.

- **Llamadas reales contra objetivo:** con escalones de 2 min y llamadas de ~115 s, la concurrencia real no sigue a la objetivo en los primeros escalones y la supera con 64 y 96.
- **Turnos excluidos:** los desfasados (después de uno sin respuesta) y los solapados (espera negativa) no entran en los percentiles.
- Tablas completas en [rampa-steps.csv](rampa-steps.csv) y [base-steps.csv](base-steps.csv); gráficos en [rampa-report.html](rampa-report.html).

### Recursos por escalón

| Llamadas | GPU 0 / 1 uso | GPU 0 / 1 seg. ≥ 95 % | CPU host p95 | Agente, cores | LLM en vuelo / cola | STT cola | TTS entre tokens | Avisos "VAD atrasado" |
|---|---|---|---|---|---|---|---|---|
| 7,2 | 42 / 44 % | 38 / 40 % | 22 % | 0,75 | 4 / 0 | 0,5 ms | 15,2 ms | 0 |
| 19,9 | 71 / 84 % | 68 / 82 % | 44 % | 2,22 | 5 / 0 | 11 ms | 21,3 ms | 0 |
| 31,6 | 93 / 97 % | **92 / 97 %** | 63 % | 3,85 | 8 / 0 | 31 ms | 29,2 ms | 0 |
| 70,3 | 96 / 94 % | 87 / 67 % | **99,8 %** | 9,75 | 11 / 0 | **364 ms** | 58,5 ms | **1.917** |
| 133 | 94 / 80 % | 82 / 55 % | 99,9 % | 10,5 | 12 / 0 | 451 ms | 48,0 ms | 14.638 |

- **Consumo:** potencia de las 2 GPUs máx. 559 W (p95 553 W). Temperatura máx.: CPU 71,5 °C, GPUs 76 °C.
- **Energía por llamada:** 0,28 Wh de GPU por llamada-minuto con 32 llamadas y 0,13 con 64.

### Memoria por componente (`rampa`, 29 ventanas de 30 s)

"Usada" = anon + shmem + kernel del cgroup, sin el caché de archivos.

| Componente | Base | Por llamada | Con 64 / 128 llamadas |
|---|---|---|---|
| Agente (usada) | 0,76 GB | **104 MB** (r² 0,99) | 7,3 / 13,8 GB |
| Agente (PSS) | 0,81 GB | 102 MB (r² 0,99) | 7,2 / 13,5 GB |
| LiveKit | 0,08 GB | 5 MB (r² 0,77) | 0,39 / 0,70 GB |
| Host (usada) | 16,8 GB | 111 MB (r² 0,98) | 23,8 / 30,7 GB |
| vLLM LLM | 3,4 GB usada + 11,3 GB caché | no escala | VRAM 22,7 GB fija |
| vLLM TTS | 5,9 GB + 6,8 GB caché | no escala | VRAM 13,1 GB fija |
| STT Parakeet | 1,3 GB + 2,6 GB caché | no escala | VRAM 2,1 GB fija |
| app, db, Asterisk, livekit-sip, redis, proxy | < 0,5 GB c/u | no escala | — |

- **Jobs del agente:** PSS p50 112 MB, p95 131 MB, hasta 132 procesos.
- Detalle en [rampa-memoria.csv](rampa-memoria.csv).

### Línea base (`base`, 1 llamada, sin límites de GPU)

| Métrica | Valor |
|---|---|
| Espera p50 / p95 / p99 | 1,59 / 1,89 / 2,15 s |
| e2e del server p50 | 0,86 s: eou 0,41 + STT 0,38 + LLM 0,13 + TTS 0,05 |
| Diferencia cliente − server | ~0,73 s |
| Saludo p50 / p95 | 0,93 / 3,49 s: 3 de 10 llamadas saludan en más de 3 s |
| Llamadas buenas | 70 %; las 3 que fallan, por el saludo |
| WER | 0,18: "Sí." se transcribe como "C" casi siempre |
| Duración media de llamada | 81,8 s |

## Análisis

- **Con los límites de potencia, las GPUs son el primer cuello, en ~32 llamadas.** Las dos pasan más del 90 % de los segundos al ≥ 95 %.
  - La espera agregada p95 sube de +0,5 s (20 llamadas) a +1,1 s (32).
  - LLM y TTS no encolan: el LLM tiene ≤ 8 pedidos en vuelo y el TTS da 29 ms entre tokens, contra un tope de 83. El STT empieza a encolar (31 ms).
- **Con 64 llamadas se satura la CPU del host (99,8 %):** el VAD del agente se atrasa (1.917 avisos), el STT encola 364 ms y la espera p50 llega a 5,8 s. Con 96 colapsa: el saludo tarda 12,8 s y el 64 % de las llamadas falla.
- **El saludo es lo primero que se degrada.** Con 32 llamadas su p95 ya es 3,9 s, contra 1,72 s del e2e. Incluso con 1 llamada, 3 de 10 saludan en más de 3 s: es el arranque del job.
- **Memoria:** solo escala el agente, ~104 MB por llamada (~0,1 GB), más ~5 MB de LiveKit. Con 128 llamadas el agente necesitaría ~14 GB. Los servicios de inferencia reservan todo al arrancar.
- **CPU del agente:** ~0,11–0,14 cores por llamada. Con 64 llamadas son ~10 cores, lo que satura un host de 16 hilos que además corre la inferencia.

## Conclusión

Este hardware, con los límites de potencia que lo hacen estable, atiende **~20 llamadas con p95 ≤
2,4 s y ~32 con p95 ≤ 3 s**. Para más hace falta más GPU (hoy se saturan las dos en ~32) y el agente
en otro host (CPU).

Siguiente paso:
1. `base` con los límites, para tener el piso del mismo `hw_id`.
2. `fina` entre 20 y 40 llamadas, con escalones de 4 min.
3. Revisar el saludo lento (arranque del job, VAD en `prewarm`).
