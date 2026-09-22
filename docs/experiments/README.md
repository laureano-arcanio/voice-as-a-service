# Registro de experimentos de capacidad

Cada experimento mide una configuración de inferencia (modelos, reparto de
GPU, flags de vLLM) con el mismo loadtest, para definir el hardware de
producción. Conclusiones vigentes: [`../LOADTEST_CAPACITY.md`](../LOADTEST_CAPACITY.md).
Hardware: [`../SERVER_HARDWARE.md`](../SERVER_HARDWARE.md).

## Índice (32 sesiones)

Modelos si no se indica otra cosa: LLM `Qwen/Qwen3.5-4B`, STT `Qwen/Qwen3-ASR-1.7B`,
TTS `Qwen/Qwen3-TTS-12Hz-1.7B-Base`.

| EXP | Fecha | Qué se probó | TTS req/s | TTS entre tokens | TTS primer audio | STT inferencia | LLM TTFT / entre tokens | Veredicto |
|---|---|---|---|---|---|---|---|---|
| [001](EXP-001-baseline-tts-stt-compartida/) | 2026-09-21 | STT + TTS en una 3090 con escritorio; LLM sola | 1,7 | 28,0 ms | 297 ms | 297 ms | 68 / 13,2 ms | Línea base |
| [002](EXP-002-swap-gpus/) | 2026-09-21 | STT + TTS en la 3090 sin escritorio; LLM con el escritorio | 1,8 | 31,8 ms | 330 ms | 314 ms | 74 / 14,7 ms | Sin mejora: el escritorio no era el cuello |
| [003](EXP-003-tts-gpu-dedicada/) | 2026-09-21 | TTS sola en una 3090; LLM + STT en la otra | **2,8** | 31,7 ms | 324 ms | **228 ms** | 83 / 16,4 ms | **Mejor. Configuración vigente** |
| [004](EXP-004-tts-2-replicas-misma-gpu/) | 2026-09-21 | Como 003, con 2 réplicas de TTS en la misma GPU | 2,7 (total) | 71 ms | ~730 ms | 240 ms | 87 / 17,1 ms | Peor: no usar |
| [005](EXP-005-sim-stt-tts-16gb/) | 2026-09-21 | Simulación: STT + TTS limitados a 16 GB; LLM sola | 2,1 | 28,6 ms | 301 ms | 244 ms | 68 / 13,7 ms | Entra justo (16,1 GB); no simula velocidad |

- **TTS primer audio:** en vLLM-Omni es el TTFT más la cola del stage 1 (Code2Wav). En un TTS de un solo stage es el TTFT.
- **Comparar con cuidado:** la carga que llega no es idéntica entre runs, así que la latencia hay que leerla junto con req/s.

## Entorno de validación

- **Host:** Ryzen 7 5700X (8 cores / 16 threads), 64 GB DDR4, 2 × RTX 3090 24 GB (driver 580).
- **GPU 1:** además dibuja el escritorio (Xorg, gnome-shell, Chrome, VS Code), que ocupa ~1,3 GB y 5–15% de SM.
- **Otros proyectos:** corren ~15 contenedores ajenos, con carga de CPU baja.
- **Térmica:** las dos 3090 hacen thermal y power throttling bajo carga (hasta 85 °C).
- **Loadtest:** `scripts/loadtest/run.py` corre en otra PC (`make up-remote`) contra los vLLM por ngrok, en tandas de 16 y 32 sesiones.

## Cómo registrar un experimento

1. **Configurar.** Preferir un override `docker-compose.<nombre>.yml` (como
   `docker-compose.sim16gb.yml`) antes que editar el compose principal. Levantar
   solo inferencia y túnel:
   ```bash
   docker compose [-f docker-compose.yml -f docker-compose.<nombre>.yml] --profile ngrok \
     up -d vllm-llm vllm-stt vllm-tts proxy ngrok
   ```
2. **Arrancar el monitoreo**, antes del warm-up:
   ```bash
   M=scripts/loadtest/monitor; RUN=$M/run_$(date +%Y%m%d_%H%M%S)_<nombre>
   mkdir -p $RUN && nohup python3 $M/sampler.py $RUN > $RUN/sampler.log 2>&1 &
   ```
   - Muestrea a 1 Hz.
   - Guarda en `meta.json` las imágenes, versiones, args y GPU de cada servicio.
   - Se corta solo tras 10 minutos sin tráfico, o con `pkill -f sampler.py`.
3. **Warm-up** con algunas llamadas, y marcar el inicio: `echo "$(date +%s) inicio" >> $RUN/marks.txt`.
4. **Loadtest** en la PC cliente: tanda de 16 y después de 32
   (`make loadtest ARGS="--levels 16,32 --turns <N>"`). Guardar el CSV y el
   resumen por tanda que imprime.
5. **Analizar:**
   ```bash
   python3 $M/timeline.py $RUN                     # ubicar t0/t1 de cada tanda
   python3 $M/analyze.py $RUN <t0> <t1> > analyze-32.txt   # reporte completo
   python3 $M/analyze.py $RUN <t0> <t1> --md               # tablas del registro
   ```
6. **Registrar:**
   - Copiar [`TEMPLATE.md`](TEMPLATE.md) a `EXP-NNN-<slug>/README.md`.
   - Guardar en esa carpeta `analyze-16.txt`, `analyze-32.txt`, `meta.json` y el CSV del cliente.
   - Agregar la fila al índice.
   - Si cambia alguna conclusión, actualizar `LOADTEST_CAPACITY.md`.

Los runs crudos (`scripts/loadtest/monitor/run_*`) no se versionan (`.gitignore`).
Quedan solo en el server de validación.

## Métricas

Salen de `/metrics` de cada vLLM y cuentan solo los segundos activos (con avance de tokens).

- **req/s:** requests terminados por segundo.
- **TTFT:** tiempo al primer token de salida.
- **Entre tokens:** latencia media entre tokens de salida.
  - En TTS define si el audio llega en tiempo real.
  - Con el códec de 12 Hz de Qwen3-TTS el tope es 83 ms por token.
  - Para otro TTS, el tope es 1 / (frames por segundo de su códec).
- **Inferencia:** tiempo de cómputo por request. En STT es lo que tarda la transcripción completa.
- **Cola:** espera antes de empezar el cómputo.
- **En vuelo:** requests running + waiting (promedio / máximo).
- **KV máx:** uso máximo del KV cache. Si se acerca a 100% aparecen preemptions.
- **Stages de vLLM-Omni:** s0 es el talker (códigos de audio) y s1 es Code2Wav (audio).
- **GPU, seg. ≥95%:** fracción de segundos con la GPU al 95% o más, que indica saturación.
- **Thread más cargado:** p95 del thread con más CPU. Si se acerca a 100%, el cuello es un solo core.
- **Proceso ajeno:** proceso del host fuera del stack con 20% o más de un core (`procs.csv`, runs desde el 2026-09-22).

## Reglas para comparar

- **Mismo loadtest:** mismos niveles, turnos, cliente y red, siempre con 16 y 32 sesiones.
- **Warm-up antes de medir:** sin él, la primera tanda infla el TTFT por captura de CUDA graphs (ver la tanda de 16 de EXP-002 y EXP-005).
- **Server compartido:** revisar el proceso ajeno más cargado. En EXP-003 un proceso fuera del stack ocupó un core al 100% durante ~45% de la tanda.
- **Simulación de VRAM ≠ velocidad:** limitar la memoria de una 3090 simula otra GPU en VRAM, no en velocidad.
- **Latencia de punta a punta:** sale del CSV del cliente, que no se registró hasta EXP-005.
