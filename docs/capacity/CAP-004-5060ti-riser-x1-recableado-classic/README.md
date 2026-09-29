# CAP-004 — 5060 Ti por riser PCIe x1, recableado: rinde como en x4 (~21 llamadas con p95 3 s) y el TTS no se cae

- **Fecha:** 2026-09-28
- **Perfil:** `rampa` (escalones de 2 min: 4, 8, 16, 32, 64, 96). Sin `base` (duración media del perfil, 109,7 s): sin piso ni espera agregada.
- **Cambio respecto de [CAP-002](../CAP-002-5060ti-tts-3090-llm-stt-classic/):** la 5060 Ti va por un riser PCIe gen3 x1 en lugar del slot del chipset (x4), y las GPU cambian de orden por bus. Antes de esta corrida se volvió a enchufar el riser y la placa (una primera rampa con el enlace con errores se descartó). El software es el mismo.
- **Resultado:**
  - Codo: p95 2,2 s con 9,4 llamadas, 2,4 s con 13,9, 4,6 s con 41,6 y 7,6 s con 59. Interpolando, **~21 llamadas con p95 3 s** (CAP-002: ~22, medido con `fina`).
  - Con ~42 llamadas el p95 es 4,6 s (CAP-002: 4,2 s con ~42, con `fina`), y con 34 llamadas 3,35 s.
  - Con ~100 llamadas: 32 % de fallas, 40 turnos sin respuesta y CPU del host al 99,9 %, como CAP-002. **El TTS no se cayó**.
  - Cuello: la GPU 1 (5060 Ti, TTS) con 92 % de los segundos al ≥ 95 % en el escalón de 32, y la CPU del host desde 64.
- **Conclusión:** un riser x1 **bien conectado** no penaliza el TTS de forma medible con esta carga: el p50 del TTS es igual que en x4 con 4–14 llamadas. Una primera rampa, con el enlace con errores (46.804 replays PCIe), dio ~7 llamadas y el TTS se cayó con 44: se descartó.

## Hardware (`hw_id 4af4cd18`) y config (`config_id a0c9f377`)

- Ryzen 7 5700X, 62,7 GB, ASRock B550M Pro SE. GPU 0 (`04:00.0`): RTX 3090, 280 W, núcleo ≤ 1800 MHz (medido 1635–1665 MHz), memoria 9501 MHz. GPU 1 (`06:00.0`): RTX 5060 Ti 8 GB, 180 W, gen3 x1 por riser.
- Config de software igual que CAP-002; ids de GPU por `GPU_TTS_ID=1` y `GPU_LLM_ID=0` en `.env`, con el override [`docker-compose.gpu-5060.yml`](docker-compose.gpu-5060.yml). Run: `20260928_224032_rampa`.
- **Antes de la rampa:** burn de 2 minutos en la 5060 Ti (cómputo fp16 34,8 TFLOPS y 800 MB/s de copias CPU↔GPU): 140 W promedio, 161 W máximo, 67 °C máximo, sin throttle, sin errores en el kernel, 21 replays PCIe. Fichas: [rampa-hw-server.json](rampa-hw-server.json), [hw-cliente.json](hw-cliente.json).

## Resultados (`rampa`), contra CAP-002

Llamadas reales, espera p50 / p95, TTS p50 / p95. Las llamadas reales difieren por las llegadas Poisson.

| Escalón | CAP-002 (x4) | CAP-004 (x1, recableado) |
|---|---|---|
| 4 | 3,7: 1,74 / 2,01 s, TTS 0,07 / 0,13 | 3,9: 1,65 / 1,87 s, TTS 0,07 / 0,13 |
| 8 | 3,1: 1,80 / 2,19 s, TTS 0,07 / 0,11 | 9,4: 1,86 / 2,20 s, TTS 0,10 / 0,19 |
| 16 | 14,8: 1,89 / 2,39 s, TTS 0,11 / 0,19 | 13,9: 1,91 / 2,44 s, TTS 0,11 / 0,19 |
| 32 | 34,2: 2,51 / 3,35 s, TTS 0,23 / 0,41 | 41,6: 3,20 / 4,57 s, TTS 0,33 / 0,59 |
| 64 | 68,6: 7,08 / 11,06 s | 59,0: 4,94 / 7,61 s, TTS 0,62 / 1,29 |
| 96 | 109,4: 9,64 / 13,96 s, 14 % de fallas | 102,5: 6,44 / 14,11 s, 32 % de fallas |

- **TTS:** con 14 llamadas p50 0,11 s, idéntico a CAP-002. Con 42 llamadas el talker da 48,5 ms entre tokens, sin cola.
- **Potencia de la 5060 Ti:** con más de 80 % de uso, 116 W promedio y 140 W máximo (CAP-002: 131 W promedio y 141 W máximo). Wh de GPU por escalón: 0,89 a 2,21 (CAP-002: 0,78 a 2,19).
- **Errores del enlace:** el contador de replays de la 5060 Ti pasó de 23 a 5.056 durante la corrida (unos 45 min, mayormente bajo carga), contra 46.804 en ~80 min antes de recablear. Mejoró unas 10 veces por hora, pero **no es cero**: el riser sigue con algo de ruido. Sin Xid ni AER en el kernel.
- **CPU:** 75,6 % de p95 con 42 llamadas y 99,6 % con 59 (CAP-002: el mismo cuello, desde ~55). Agente: 0,107–0,14 cores por llamada.
- **Con ~102 llamadas** el TTS aguantó, pero no se corrió `fina` ni `sostenida`.

## Pendiente

- No hay `base`, `fina` ni `sostenida`: el número fino (~21) es interpolado de dos escalones.
- Repetir con un riser distinto o con el slot x4 para bajar los replays a 0 y confirmar que la equivalencia con x4 es exacta.
