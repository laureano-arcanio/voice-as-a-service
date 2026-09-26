# CAP-002 — TTS en RTX 5060 Ti 8 GB, LLM + STT en RTX 3090: codo en ~34 llamadas

- **Fecha:** 2026-09-25
- **Perfiles:** `base` (10 llamadas de a una) y `rampa` (escalones de 2 min: 4, 8, 16, 32, 64, 96)
- **Cambio respecto de [CAP-001](../CAP-001-2x3090-pl280-classic/):** la primera 3090 se reemplazó por una RTX 5060 Ti 8 GB, que pasa a correr el TTS solo. El LLM y el STT comparten la 3090, como antes de EXP-013.
- **Resultado:**
  - Piso con 1 llamada: espera p50 1,66 s / p95 2,04 s (+0,05 s contra CAP-001).
  - ~15 llamadas con p95 ≤ 2,4 s (~20 en CAP-001); ~34 con p95 ≤ 3,4 s (~32 con 3,0 s en CAP-001).
  - Con ~34 llamadas se satura la 5060 Ti (TTS); con 64, la CPU del host, como en CAP-001.
  - Las GPUs consumen menos: 419 W de pico contra 559 W, y 0,19 contra 0,28 Wh por llamada-minuto con ~32 llamadas.

## Hardware (`hw_id 03dfeb24`)

| | CAP-002 (`03dfeb24`) | CAP-001 (`8489259f`) |
|---|---|---|
| CPU / RAM / placa | Ryzen 7 5700X (8 núcleos / 16 hilos), 62,7 GB, ASRock B550M Pro SE (BIOS P3.40) | igual |
| GPU 0, slot `04:00.0` (chipset: PCIe gen3 x4) | **RTX 5060 Ti 8 GB**, 180 W (sin límite), x4 de x8 | RTX 3090 24 GB, 280 W, x4 de x16 |
| GPU 1, slot `07:00.0` (CPU: PCIe gen4 x16) | RTX 3090 24 GB, **280 W**, núcleo ≤ 1800 MHz, memoria 9501 MHz, x16 | igual |
| Escritorio | en la 3090 (~0,5 GB) | igual |
| Driver | 580.178.04 | igual |

- **Qué corre en cada placa:**
  - CAP-002: la 5060 Ti tiene el TTS; la 3090, el LLM y el STT.
  - CAP-001: la GPU 0 tenía el LLM; la GPU 1, el TTS y el STT.
- **Consumo medido:** en la 3090, 280 W de máximo, contra el tope de 280 W. El núcleo llega a ~1695 MHz, porque primero toca el tope de potencia.
- Fichas completas: [base-hw-server.json](base-hw-server.json), [rampa-hw-server.json](rampa-hw-server.json), [hw-cliente.json](hw-cliente.json).

## Configuración

Override [`docker-compose.gpu-5060.yml`](docker-compose.gpu-5060.yml) (copia del que se usó), sumado a `COMPOSE_FILE`.

| Servicio | Placa | Memoria y topes |
|---|---|---|
| `vllm-tts` | 5060 Ti | Etapa 0 (talker): 0.58, 32 síntesis, largo máx. 2048, batches de 512 tokens. Etapa 1 (Code2Wav): 0.36, 16 síntesis, sin CUDA graphs. Usa 7,66 de 8,15 GB; KV del talker: 2.736 tokens |
| `vllm-llm` | 3090 | 0.70 (KV 4,8 GiB), 64 secuencias (con 0.70 no arranca con 128) |
| `stt-parakeet` | 3090 | batch 8; arranca después del LLM |

- **Resto:** igual que CAP-001. Motor `classic` (`demo_booking_classic`), voz `sofia`, LiveKit propio, `app` + `agent` en este host, callers en la laptop por la LAN.
- `config_id`: `76d0bb12` (`base`) y `458ae12f` (`rampa`). Solo difieren en el perfil, que forma parte del `config_id`.
- Runs: `20260926_003647_base` y `20260926_005553_rampa`.

### Cómo se hizo entrar el TTS en 8 GB

La placa tiene 7,53 GiB utilizables y los pesos del talker ocupan 3,91 GiB. En orden:
1. Con 0.55 en la etapa 0, no quedaba KV cache.
2. Con 0.62 y batches de 8.192 tokens quedaban 0,28 GiB, menos que los 0,44 que pide un pedido de 4.096 tokens.
3. Con 0.66 y largo máximo 2048 entraba la etapa 0, pero Code2Wav se quedaba sin memoria con CUDA graphs.
4. Entró con la configuración de la tabla:
   - largo máximo 2048: una frase de 15 s son ~200–400 tokens;
   - batches de 512, como recomienda el deploy de la imagen;
   - Code2Wav sin graphs; necesita sus 65.536 tokens de batch.

## Resultados

### Espera del cliente por escalón (`rampa`), contra CAP-001

p50 / p95. Agregada: p95 del escalón menos el p95 del `base` del mismo hardware.

| Llamadas reales | CAP-002: 5060 Ti + 3090 | Agregada p95 | Sin resp. | CAP-001: 2 × 3090 | Llamadas reales CAP-001 |
|---|---|---|---|---|---|
| 1 (`base`) | 1,66 / 2,04 s | — | 0 | 1,61 / 1,99 s | 1 |
| 3,7 | 1,74 / 2,01 s | −0,03 s | 0 | 1,61 / 2,12 s | 7,2 |
| 14,8 | 1,89 / 2,39 s | +0,35 s | 0 | 1,86 / 2,38 s | 19,9 |
| **34,2 (codo)** | **2,51 / 3,36 s** | +1,31 s | 0 | 2,27 / 3,03 s | 31,6 |
| 68,6 | 7,08 / 11,1 s | +9,0 s | 8 | 5,83 / 8,25 s | 70,3 |
| 109 | 9,64 / 14,0 s | colapso | 65 | 10,7 / 14,4 s | 133 |

La concurrencia real de cada escalón no coincide entre los dos runs (llegadas Poisson, escalones de 2 min). Hay que comparar a igual concurrencia real, no a igual escalón.

### TTS en la 5060 Ti contra la 3090

| Llamadas (CAP-002 / CAP-001) | Primer audio p50 | Entre tokens (tope 83 ms) | En vuelo máx. | KV máx. | GPU del TTS: seg. ≥ 95 % |
|---|---|---|---|---|---|
| 3,7 / 7,2 | 68 / 45 ms | 17,4 / 15,2 ms | 3 / 4 | 7 % / 0,8 % | 28 / 40 % |
| 14,8 / 19,9 | 112 / 82 ms | 20,7 / 21,3 ms | 5 / 8 | 14 % / 2 % | 82 / 82 % |
| 34,2 / 31,6 | **228 / 126 ms** | 36,1 / 29,2 ms | 14 / 11 | 39 % / 3 % | **95** / 97 % |
| 68,6 / 70,3 | 872 / 403 ms | **79,0** / 58,5 ms | 34 / 23 | 87 % / 5 % | 80 / 67 % |

En CAP-001 la GPU del TTS también corría el STT, por eso su porcentaje de segundos saturados es comparable pero no igual.

### Resto de los recursos (`rampa`)

| Llamadas | 3090 (LLM + STT) seg. ≥ 95 % | LLM en vuelo / cola | STT cola | CPU host p95 | Agente, cores | Avisos "VAD atrasado" |
|---|---|---|---|---|---|---|
| 3,7 | 18 % | 2 / 0 | 0 | 19,5 % | 0,39 | 0 |
| 14,8 | 63 % | 3 / 0 | 11 ms | 36 % | 1,65 | 0 |
| 34,2 | 85 % | 9 / 0 | 21 ms | 72 % | 4,25 | 0 |
| 68,6 | 83 % | 13 / 0,2 ms | **326 ms** | **99,7 %** | 9,11 | **2.730** |
| 109 | 80 % | 14 / 0,5 ms | 577 ms | 99,9 % | 10,2 | 12.130 |

### Consumo y energía

| | CAP-002 | CAP-001 |
|---|---|---|
| Potencia de las 2 GPUs, máx. / p95 | **419 / 414 W** (5060 Ti máx. 141 W; 3090 281 W) | 559 / 553 W |
| Wh de GPU por llamada-minuto con ~32 llamadas | **0,19** | 0,28 |
| Con ~65 llamadas | 0,10 | 0,13 |
| Temperatura máx. | 5060 Ti 61 °C; 3090 74 °C | 76 °C |

### Memoria por componente (`rampa`, 29 ventanas de 30 s)

| Componente | Base | Por llamada | Con 64 / 128 llamadas |
|---|---|---|---|
| Agente (usada) | 0,58 GB | **113 MB** (r² 0,99) | 7,7 / 14,7 GB |
| Agente (PSS) | 0,65 GB | 110 MB (r² 0,99) | 7,5 / 14,4 GB |
| LiveKit | 0,06 GB | 5 MB (r² 0,81) | 0,39 / 0,73 GB |
| Host (usada) | 19,0 GB | 124 MB (r² 0,99) | 26,7 / 34,5 GB |
| vLLM LLM | 3,5 GB usada + 9,9 GB caché | no escala | VRAM 15,6 GB fija |
| vLLM TTS | 6,3 GB usada | no escala | VRAM 7,66 GB fija (5060 Ti) |
| STT | 1,3 GB usada | no escala | VRAM 1,6–1,9 GB |

### Línea base (`base`, 1 llamada)

| Métrica | CAP-002 | CAP-001 |
|---|---|---|
| Espera p50 / p95 / p99 | 1,66 / 2,04 / 2,13 s | 1,61 / 1,99 / 2,17 s |
| e2e del server p50 | 0,92 s | 0,90 s |
| TTS primer audio p50 / entre tokens | 69 ms / 17,0 ms | 44 ms / 14,2 ms |
| LLM TTFT / entre tokens | 120 ms / 11,9 ms | 126 ms / 11,9 ms |
| Saludo p50 / p95 | 0,96 / 1,14 s | 0,91 / 1,41 s |
| Llamadas buenas | 100 % | 90 % |
| WER | 0,09 | 0,12 |
| Duración media de llamada | 85,2 s | 91,6 s |

## Análisis

- **Una 5060 Ti 8 GB alcanza para el TTS hasta ~34 llamadas**, con +0,25 s de p50 y +0,3 s de p95 respecto de una 3090. Es la mitad de ancho de banda de memoria y 8 GB en lugar de 24.
  - El TTS entrega el primer audio en el doble de tiempo (228 contra 126 ms con ~33 llamadas).
  - Esa diferencia es casi toda la que se ve en la espera del cliente.
- **Con ~34 llamadas la 5060 Ti es el primer cuello** (95 % de los segundos saturada). Con 64 llamadas el TTS queda al límite del tiempo real: 79 ms entre tokens, contra un tope de 83. La 3090 con LLM + STT queda holgada: el LLM no encola.
- **La memoria de la 5060 Ti alcanza:** el KV del talker llega al 39 % con 34 llamadas y al 87 % con 64, sin preemptions. Con 64 llamadas el talker llegó a 34 síntesis en vuelo para 32 lugares: 3,5 ms de cola en promedio.
- **El segundo cuello no cambia:** con ~65 llamadas la CPU del host (agente) se satura igual que en CAP-001: VAD atrasado, STT con 326 ms de cola y 8 turnos sin respuesta.
- **Consumo:** la 5060 Ti usa como máximo 141 W, contra ~280 W de la 3090 que reemplaza. Las GPUs bajan de 559 a 419 W de pico, y la energía por llamada-minuto cae ~30 %.
- **Arranque:** el primer pedido al TTS después de arrancar tarda más de 20 s, probablemente por la compilación de kernels para Blackwell; los siguientes salen en menos de 1 s. Sin un pedido de calentamiento, la primera llamada no recibe el saludo.

## Conclusión

Para ~30 llamadas, una 5060 Ti 8 GB para el TTS más una 3090 para LLM + STT da casi la misma
latencia que dos 3090 (p95 +0,3 s), con ~140 W menos de pico. Por encima de ~34 llamadas el TTS
en la 5060 Ti y la CPU del agente son los límites.

Siguiente paso:
1. Pedido de calentamiento al TTS en el arranque.
2. `fina` entre 20 y 40 llamadas, para el número exacto con este hardware.
