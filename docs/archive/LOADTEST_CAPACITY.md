# Capacidad: conclusiones vigentes

> **Archivado (25-sep-2026).** Mediciones con el loadtest, reemplazado por el test de capacidad. Resultados vigentes en [`docs/capacity/`](../capacity/README.md).

Objetivo: definir el hardware de producción con menor costo inicial, buena
latencia con 32 conversaciones y redundancia. El server actual (Ryzen 7 5700X,
64 GB, 2 × RTX 3090, con escritorio) es **solo de validación**.

Detalle de cada prueba, método y cómo agregar nuevas:
[`experiments/`](experiments/README.md). Este documento resume lo que se
concluye de todas y se actualiza cuando un experimento lo cambia.

## Resumen de experimentos

| EXP | Qué se probó | Resultado |
|---|---|---|
| 001 | STT + TTS en una 3090 con escritorio | Línea base: la GPU de TTS es el único cuello |
| 002 | STT + TTS en la 3090 sin escritorio | Sin mejora: el escritorio no era la causa |
| **003** | **TTS sola; LLM + STT juntos** | **Mejor y vigente:** ~55% más de throughput de TTS con la misma latencia; STT ~85 ms más rápido |
| 004 | 2 réplicas de TTS en la misma GPU | Peor: 71 ms entre tokens (tope 83 ms), mismo throughput |
| 005 | Simulación: STT + TTS limitados a 16 GB | Entran justo (16,1 GB), sin preemptions; TTS no baja de ~9 GB |
| 006 | STT Whisper Large v3 Turbo en lugar de Qwen3-ASR | STT en 96 ms (antes 228), con 3,9 GB de VRAM (antes 8,2) y ~1/6 de CPU. No cambia el cuello; falta calidad en llamadas reales |
| 007 | STT Parakeet TDT 0.6B v3; loadtest local, sin ngrok | STT en 101–130 ms con 1,6 GB, pero sin batching (cola p95 52 ms con 20 llamadas). Sin ngrok, el agente mide ~0,4 s menos por turno (1,11 s total con 32) |
| 008 | Como 007, con batching dinámico en Parakeet | Sin cambios con 20 llamadas: 0,6 req/s de STT, 233 requests en 232 batches. El batching da ×4,7 de throughput en el bench sintético, para cargas ~100 veces mayores |
| 010 | Config vigente (LLM 9B w4a16, TTS `multi41`, motor por workflow), tandas 4/8/16/32 | Con 16: GPUs al 50–60 %, sin cola, TTS 17 ms entre tokens. La tanda de 32 no midió la inferencia: se atendieron 20 de 32 |
| 011 | Como 010, con el agente en el server de inferencia | El techo de ~20 (también en 006–010) es el despacho de LiveKit Cloud (plan gratuito): jobs en `JS_PENDING` sin asignar, con el worker holgado. Con 24 simultáneas: GPUs al 68/76 %, sin cola. Agente junto a la inferencia: −1,2 s de e2e por turno |
| **012** | **Como 011, con LiveKit propio** | **32/32 atendidas. Sin cola en LLM ni TTS, las dos GPUs al 74 % (72 % de los segundos ≥95 %). TTS 24 ms entre tokens. e2e p50 2,0 s, p95 3,0 s por turno** |
| **013** | **LLM solo en la GPU 0 (0.90), TTS + STT en la GPU 1, motor `classic`** | **Vigente. Espera del cliente p95 3,42 s con 32 llamadas y 4,14 s con 48. Con 64 satura la CPU del host (agente, ~0,15 cores por llamada), no las GPUs (74–81 %)** |

## Qué limita y qué sobra (32 sesiones)

| Recurso | Medido | Conclusión |
|---|---|---|
| **GPU de TTS** | 98% de uso en mediana; una 3090 da ~2,8 síntesis/s | **Único cuello.** Una 3090 dedicada alcanza justo para 32 sesiones |
| GPU de LLM + STT | 55% de uso; LLM nunca encola; máx. 8 requests en vuelo | Sobra |
| CPU | Host 25–40%; TTS 2,2 cores, STT 0,9, LLM 0,4 (p95) | ~4 de 16 threads. Importa la velocidad por core: el thread de Code2Wav llega a 70% (p95) |
| RAM | ~15 GB entre los 3 vLLM, constante; pico de 12 GB al arrancar el LLM | 32 GB por nodo alcanzan |
| VRAM mínima real | LLM ~12 GB (BF16), TTS ~9 GB, STT ~7 GB | 16 GB alcanzan para el LLM solo. STT + TTS juntos quedan al límite |
| Térmica | Las dos 3090 con thermal/HW slowdown (84 °C). Con las GPUs reubicadas (desde EXP-010): máx. 80 °C, −2 a −3 % de clock | Refrigeración y `nvidia-smi -pl 280` son requisito |

Concurrencia real: 32 sesiones no son 32 requests simultáneos. Los picos fueron de 8 en el LLM, 5 en STT y ~14 en TTS (2,4 síntesis por turno, ~1,5 s cada una).

## Reglas de diseño

1. **TTS nunca comparte GPU:** ni con STT ni con otra réplica de TTS. Escalar TTS es sumar GPUs físicas.
2. **El LLM y STT pueden compartir una GPU de 24 GB.** En 16 GB entra solo el LLM.
3. **GPU con ancho de banda de memoria clase 3090 para TTS.** La 5060 Ti tiene la mitad; para TTS no está validada y probablemente no alcance con 32 sesiones.
4. **CPU y RAM: lo más barato que cumpla.** 6–8 cores Zen 3 con buena frecuencia por core (Ryzen 5 5600GT o Ryzen 7 5700) y 32 GB.
5. **Sin escritorio y con buen flujo de aire.**

## Arquitectura candidata (en discusión)

Dos nodos iguales detrás de un balanceador; cada uno soporta solo las 32 sesiones.

| Por nodo | Variante A (recomendada) | Variante B (más barata) |
|---|---|---|
| GPU 1 | 3090: TTS | 3090: TTS + STT (como EXP-002) |
| GPU 2 | 3090: LLM + STT (como EXP-003) | RTX 5060 Ti 16 GB: LLM solo (sin validar) |
| Si cae un nodo | El otro lleva 32 sesiones al nivel de EXP-003 | El otro lleva 32 sesiones al nivel de EXP-002 (degradado, dentro de tiempo real) |

- **Resto por nodo:** Ryzen 5 5600GT o Ryzen 7 5700, Gigabyte B550 Eagle WIFI6 (5 slots x16 físicos, deja aire entre dos GPUs de 3 slots), 32 GB DDR4 y fuente de 1000 W (A) u 850 W (B).
- **Antes de comprar la variante B:** medir el LLM en una sola 5060 Ti (BF16 y FP8) con el mismo loadtest.
- **Escalar:** sumar una GPU dedicada a TTS por nodo.

## Pendiente

- Benchmark del LLM (y de TTS) en una 5060 Ti real.
- Registrar la latencia de punta a punta del cliente en cada experimento.
- Pasar de ~48 llamadas: el agente en otra máquina (o más CPU) y el VAD en `prewarm` (EXP-013).
- Bajar la espera: TTS desde antes de la primera oración completa y STT con parciales (EXP-013).
- Definir LiveKit en producción: Cloud pago (el tope y el comportamiento del despacho están sin verificar) o servidor propio.
- Prueba con 64 sesiones para encontrar el techo real del LLM y STT.
- Confirmar la temperatura de memoria de las 3090 (`nvtop`).
