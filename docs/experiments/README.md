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
| [006](EXP-006-stt-whisper/) | 2026-09-22 | STT Whisper Large v3 Turbo en lugar de Qwen3-ASR (GPU 1, con la LLM) | 1,9 | 28,6 ms | 282 ms | **96 ms** | 96 / 15,3 ms | STT 2,4 × más rápido, con la mitad de VRAM; falta calidad en llamadas reales. Con 32: 21/32 llamadas ok, el agente no tomó 11 |
| [007](EXP-007-stt-parakeet-local/) | 2026-09-22 | STT Parakeet TDT 0.6B v3 (GPU 1, con la LLM); loadtest **local, sin ngrok**, con scoring | 1,9 | 28,7 ms | 295 ms | 130 ms | 114 / 15,4 ms | STT con 1,6 GB, sin batching. Sin ngrok el agente gana ~0,4 s por turno; no comparable con 001–006. 20/32 llamadas ok |

- **TTS primer audio:** en vLLM-Omni es el TTFT más la cola del stage 1 (Code2Wav). En un TTS de un solo stage es el TTFT.
- **Comparar con cuidado:** la carga que llega no es idéntica entre runs, así que la latencia hay que leerla junto con req/s.

## Entorno de validación

- **Host:** Ryzen 7 5700X (8 cores / 16 threads), 64 GB DDR4, 2 × RTX 3090 24 GB (driver 580).
- **GPU 1:** además dibuja el escritorio (Xorg, gnome-shell, Chrome, VS Code), que ocupa ~1,3 GB y 5–15% de SM.
- **Otros proyectos:** corren ~15 contenedores ajenos, con carga de CPU baja.
- **Térmica:** las dos 3090 hacen thermal y power throttling bajo carga (hasta 85 °C).
- **Loadtest:** `scripts/loadtest/run.py` corre en otra PC (`make up-remote`) contra los vLLM por ngrok, en tandas de 16 y 32 sesiones.
- **Loadtest local (desde EXP-007):** el plan free de ngrok se quedó sin ancho de banda (1 GB/mes; cada loadtest saca ~135 MB solo de audio de TTS). `app`, `agent` y los callers corren en este host (`make up-remote` + `make loadtest`) y le pegan a los vLLM por la red de compose.
  - La latencia que mide el agente baja ~0,4 s por turno, así que no se compara con EXP-001 a 006.
  - El scoring de cada llamada pasa a cargar el LLM.
  - El sampler registra al contenedor de los callers como `agent-run`.

## Registrar un loadtest

Pedido típico a un agente: *"voy a correr el loadtest con <config>, registralo"*
o *"registrá el último run"*. El loadtest corre en la PC cliente; en este server
el agente monitorea, analiza y registra.

**Quien corre el loadtest:**
1. Avisa al agente antes del warm-up, y qué configuración se prueba.
2. En la PC cliente corre el warm-up y después las tandas de 16 y 32 (`make loadtest ARGS="--levels 16,32 --turns <N>"`).
3. Avisa cuando terminó y, si puede, pasa el CSV y el resumen por tanda que imprime `run.py`.

**El agente, en este server:**

1. **Configurar**, solo si el pedido incluye cambiar la config.
   - Usar un override `docker-compose.<nombre>.yml` (como `docker-compose.sim16gb.yml`), no el compose principal.
   - Levantar solo inferencia y túnel:
     ```bash
     docker compose [-f docker-compose.yml -f docker-compose.<nombre>.yml] --profile ngrok \
       up -d vllm-llm vllm-stt vllm-tts proxy ngrok
     ```
   - Si la config a probar no está arriba y no se pidió levantarla, avisar antes de tocar servicios.
2. **Arrancar el monitoreo**, antes del warm-up:
   ```bash
   M=scripts/loadtest/monitor; RUN=$M/run_$(date +%Y%m%d_%H%M%S)_<slug>
   mkdir -p $RUN && setsid nohup python3 $M/sampler.py $RUN > $RUN/sampler.log 2>&1 &
   sleep 15; cat $RUN/sampler.log     # contenedores y vLLM detectados
   ```
   - Verificar que el log liste los vLLM de la config a probar, y avisar: "monitoreo corriendo, podés arrancar".
   - `setsid nohup` hace que sobreviva a la shell del agente.
   - Muestrea a 1 Hz y guarda `meta.json` con las imágenes, versiones, args y GPU de cada servicio.
   - Se corta solo a los 10 minutos sin tráfico, o a la hora si nunca llega tráfico.
   - Si el usuario avisa el fin del warm-up: `echo "$(date +%s) inicio" >> $RUN/marks.txt`.
3. **Cuando el usuario avisa que terminó**, cortar el monitoreo y ubicar las tandas:
   ```bash
   M=scripts/loadtest/monitor; RUN=${RUN:-$(ls -td $M/run_* | head -1)}
   pkill -f "sampler.py $RUN"
   python3 $M/timeline.py $RUN
   ```
   - Las tandas son bloques de buckets activos separados por un hueco: la primera es la de 16 y la segunda la de 32.
   - Lo anterior a la marca de `marks.txt` es warm-up. Si hay más de dos bloques o dudas, confirmar con el usuario.
   - **t0:** el `t0=` del primer bucket de la tanda.
   - **t1:** el `t0=` del último bucket de la tanda más 20.
4. **Generar los datos del registro:**
   ```bash
   N=$(printf "%03d" $(( $(ls -d docs/experiments/EXP-* | sed -E 's/.*EXP-0*([0-9]+).*/\1/' | sort -n | tail -1) + 1 )))
   D=docs/experiments/EXP-$N-<slug>; mkdir -p $D
   cp docs/experiments/TEMPLATE.md $D/README.md; cp $RUN/meta.json $D/
   python3 $M/analyze.py $RUN <t0_16> <t1_16> > $D/analyze-16.txt
   python3 $M/analyze.py $RUN <t0_32> <t1_32> > $D/analyze-32.txt
   python3 $M/analyze.py $RUN <t0_16> <t1_16> --md     # tablas para el README
   python3 $M/analyze.py $RUN <t0_32> <t1_32> --md
   ```
5. **Escribir `$D/README.md`** con la plantilla:
   - **Configuración:** sale de `meta.json` (modelos, imágenes y versiones, GPU, flags). `compose_files` dice si hubo override.
   - **Tablas:** las de `--md` para 16 y 32.
   - **Cliente:** el resumen por tanda, y copiar el CSV a `$D` si lo pasó.
   - **Análisis:** comparar con la config vigente (EXP-003) y con el experimento más parecido: qué limita y qué cambió. Revisar preemptions, KV máx, cola, GPU seg. ≥95%, thread más cargado, proceso ajeno y térmica.
   - **Conclusión** y siguiente paso.
6. **Actualizar el resto:**
   - Agregar la fila al índice.
   - Actualizar `LOADTEST_CAPACITY.md` si cambia una conclusión, y `AGENTS.md` si cambia la config vigente.
   - Pasarle al usuario el resumen y la ruta del registro.

Los runs crudos (`scripts/loadtest/monitor/run_*`) no se versionan (`.gitignore`).
Quedan solo en el server de validación.

## STT candidatos (Parakeet, Whisper)

Un experimento por candidato, con el procedimiento de arriba. Cambian el paso 1
y el `.env` de la PC del loadtest. El override `docker-compose.stt-candidates.yml`
pone el candidato en la GPU 1, en el lugar de `vllm-stt`.

**Server**, un target por config (paso 1). Dejan LLM + TTS + ese STT + ngrok,
bajan el otro candidato y paran `app`/`agent` de este host: si la PC del loadtest
usa el mismo proyecto de LiveKit y `LIVEKIT_AGENT_NAME`, LiveKit repartiría las
llamadas entre los dos workers. Al final imprimen lo que va en el `.env` de la PC.
```bash
make servers-whisper     # Whisper Large v3 Turbo (GPU 1, sin vllm-stt)
make servers-parakeet    # Parakeet TDT 0.6B v3 (GPU 1, sin vllm-stt)
make servers-qwen        # Qwen3-ASR, config vigente (línea base)
```
Monitoreo (paso 2) con `RUN=$M/run_$(date +%Y%m%d_%H%M%S)_<stt>`.

**PC del loadtest**, en su `.env` (ahí no corre `vllm-stt`, así que se cambia `VLLM_STT_MODEL`):

| Config | `VLLM_STT_BASE_URL` | `VLLM_STT_MODEL` |
|---|---|---|
| Whisper | `https://$NGROK_DOMAIN/stt-whisper/v1` | `openai/whisper-large-v3-turbo` |
| Parakeet | `https://$NGROK_DOMAIN/stt-parakeet/v1` | `nvidia/parakeet-tdt-0.6b-v3` |
| Qwen3-ASR | `https://$NGROK_DOMAIN/stt/v1` | `Qwen/Qwen3-ASR-1.7B` |

```bash
docker compose up -d --no-deps --force-recreate agent   # relee el .env
make loadtest ARGS="--levels 2 --turns 2"               # warm-up
make loadtest ARGS="--levels 16,32 --turns 4"
```

**Volver al uso normal** (app/agent en este host): `make servers-qwen && make up`.

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
