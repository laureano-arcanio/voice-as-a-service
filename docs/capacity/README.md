# Capacidad: resultados vigentes y test

Cuántas llamadas simultáneas soporta el pipeline (STT → LLM → TTS + agente) con una calidad dada, qué etapa se
degrada primero y con qué recurso, y cómo escala la memoria. Código en `scripts/capacity/`; las mediciones
anteriores con el loadtest (EXP-001 a 013) están en [`../archive/experiments/`](../archive/experiments/README.md).

## Capacidad vigente

Hardware: **2 × RTX 3090 a 280 W** (LLM solo en la GPU 0; TTS + STT en la GPU 1), Ryzen 7 5700X, 64 GB.

- **LLM vigente, Gemma 4 26B-A4B** (`docker-compose.gemma4-26b.yml`, 32 secuencias, contexto 16384): **sin
  medir.** Falta un CAP. Su KV cache es ~5 veces menor que el del Qwen3.5-9B (63.013 tokens para todas las
  llamadas, según `vllm:cache_config_info`), así que el techo va a ser más bajo que el de CAP-001. No usar los números de abajo como capacidad
  actual.
- **Última referencia del hardware actual, [CAP-001](CAP-001-2x3090-pl280-classic/)** (Qwen3.5-9B, `base` y
  `rampa`, sin `fina` ni `sostenida`):
  - ~20 llamadas con p95 ≤ 2,4 s y **~32 con p95 ≤ 3 s** (codo); con ~32 se saturan las dos GPUs.
  - Con ~64, además la CPU del host (agente, ~0,12 cores y ~104 MB por llamada): p95 8,3 s, colapso.
  - Piso con 1 llamada: p50 1,61 s / p95 1,99 s. Potencia de las dos GPUs: 559 W de pico.

## Índice por hardware

| CAP | Hardware (`hw_id`) | Reparto | Perfiles | p95 ≤ 3 s | Cuello | Piso p50 | Cores / MB por llamada |
|---|---|---|---|---|---|---|---|
| [001](CAP-001-2x3090-pl280-classic/) | 2 × 3090 a 280 W (`8489259f`), **vigente** | LLM en una 3090; TTS + STT en la otra | base, rampa | ~32 (Qwen3.5-9B) | GPUs; con 64, CPU | 1,61 s | 0,12 / 104 |
| [002](CAP-002-5060ti-tts-3090-llm-stt-classic/) | 5060 Ti 8 GB + 3090 (`03dfeb24`), descartado | TTS en la 5060 Ti; LLM + STT en la 3090 | base, rampa, fina, sostenida | ~22 con p95 2,8 s; cuello la 5060 Ti | 5060 Ti; con ~55, CPU | 1,66 s | 0,12 / 113 |
| [004](CAP-004-5060ti-riser-x1-recableado-classic/) | 5060 Ti en riser x1 + 3090 (`4af4cd18`), descartado | Igual que CAP-002, la 5060 Ti por x1 | rampa | ~21 (interpolado) | 5060 Ti; con 59, CPU | - | 0,11 / 103 |

- CAP-002: la 5060 Ti con el TTS cuesta ~0,3 s de p95 contra una 3090 hasta ~30 llamadas, con ~140 W menos;
  con ~110 el talker del TTS se cayó y no se recupera solo.
- CAP-004: un riser x1 bien conectado rinde como x4; con el enlace con errores (46.804 replays PCIe) dio ~7
  llamadas y el TTS se cayó.

La calculadora de costos por server está en [`../../comercial/calculadora-costos.html`](../../comercial/calculadora-costos.html).

## Definiciones

- **Espera percibida** (métrica principal): fin del audio del usuario → primer audio del agente, medida en el
  cliente. **Espera agregada por la carga:** la percibida menos la mediana con 1 llamada (run `base`) en el mismo
  hardware y config.
- **Buckets** (`buckets_s` en `_comun.yml`): < 0,5 óptimo, 0,5–0,8 excelente, 0,8–1,0 bueno, 1,0–1,5
  aceptable, 1,5–2,0 regular, 2,0–3,0 malo, > 3,0 s pésimo.
- **Llamada buena** (`llamada_buena`): saludo en ≤ 3 s, ningún turno pésimo, a lo sumo 1 malo y ningún turno sin
  respuesta.
- **SLO / capacidad** (`slo`): la mayor carga sostenida con ≥ 90 % de turnos ≤ 1,5 s, ≤ 1 % > 3 s, ≥ 95 % de
  llamadas buenas y ≤ 1 % de fallas, con el cliente sano (p95 del atraso del micrófono ≤ 0,1 s y CPU ≤ 85 %).
  Con el piso actual (p50 ~1,6 s) el SLO de 1,5 s no se cumple ni con 1 llamada: el análisis informa también la
  carga máxima con p95 ≤ 2, 3, 4 y 5 s, que es la que se usa.
- **Codo:** primer escalón con espera agregada p95 > +0,5 s o más de 5 % de turnos en malo/pésimo.
- **Cuello:** en el codo, el primer recurso saturado (CPU del host ≥ 90 %, GPU ≥ 95 % de uso el 90 % de los
  segundos, cola de vLLM o STT > 100 ms, VRAM o KV cerca del 100 %).
- Simultáneas y llamadas por minuto se relacionan por Little: simultáneas ≈ llegadas/min × duración media (min).
- **`hw_id` / `config_id`:** hash de CPU, RAM, placa, GPUs con su slot PCIe y tope de potencia / hash de
  commit, imágenes y flags, variables de capacidad de `.env`, agente, voz y perfil.

## Procedimiento

1. **Server**, con los topes de GPU aplicados (`nvidia-smi`; los pone `atentina-gpu-limits.service`) y el TTS
   caliente, antes de la carga:
   ```bash
   make capacity-monitor PERFIL=rampa
   ```
   Escribe `hw_server.json` y deja `monitor.py` (1 Hz) en `scripts/capacity/runs/monitor_<fecha>_<perfil>/`.
2. **Cliente** (la laptop del loadtest; `VAAS_API_KEY` en su `.env`, de `make api-key CLIENT=atentina
   NAME=capacidad` en el server):
   ```bash
   make capacity PERFIL=rampa ARGS="--base-url http://192.168.1.99:8011" PING=192.168.1.99
   ```
   Deja `hw_cliente.json`, `calls.csv`, `turns.csv`, `client.csv` y `run.json` en
   `scripts/capacity/runs/<fecha>_<perfil>/`. El usuario empaqueta el run y lo pasa al server.
3. **Server**, al terminar:
   ```bash
   make capacity-monitor-stop
   make capacity-analyze RUN=<run del cliente> MON=scripts/capacity/runs/monitor_<...> [BASE=<summary.json de base>]
   ```
   Genera `summary.json` (ficha de capacidad), `steps.csv`, `windows.csv`, `memoria.csv` y `report.html`.
4. **Registrar** `docs/capacity/CAP-NNN-<slug>/` (README con config, comando, tabla por escalón y hallazgos;
   `summary.json` y `report.html`), sumar la fila al índice y, si cambia la capacidad vigente, `AGENTS.md`.

Orden en un hardware o config nuevos: `base` → `rampa` → `fina` → `sostenida`. El `summary.json` de `base` va
como `--base` en el cliente (tasa de llegadas) y como `BASE=` en el análisis. `scripts/capacity/runs/` no se
versiona.

## Perfiles (`scripts/capacity/perfiles/`)

| Perfil | Escalones | Para qué |
|---|---|---|
| `humo` | corto, ~3 min | Verificar el test |
| `base` | 10 llamadas de a una | Piso de latencia y duración media de llamada |
| `rampa` | 4 → 8 → 16 → 32 → 64 → 96, 2 min c/u | Ubicar el codo |
| `fina` | +8 alrededor del codo, 4 min c/u | El número de capacidad |
| `sostenida` | ~80 % de la capacidad, 15–20 min | Estabilidad térmica y de memoria |

Lo común (agente, voz `sofia`, turnos sorteados entre 4 y 8, warm-up, buckets, SLO, llamada buena, cliente sano)
está en `_comun.yml`; el perfil pisa lo que defina. Llegadas Poisson por escalón; se descarta el primer minuto
de cada uno.

## Qué mide

- **Por turno** (cliente): espera percibida y bucket, cortes (silencios de 0,3–1,5 s dentro de la respuesta),
  sin respuesta, WER de la transcripción y, si coinciden los turnos, el desglose del server (eou, stt, llm, tts).
- **Por llamada:** tiempo hasta el saludo, llamada buena, fallas, atraso del micrófono del cliente.
- **Server** (`monitor.py`): CPU, GPU y vLLM (`sampler.py` del loadtest); RAM por componente (cgroup y PSS), por
  proceso del agente y VRAM por servicio; frecuencia y temperatura de CPU, PCIe, red y UDP; avisos del agente
  (VAD atrasado, event loop bloqueado, sin proceso precalentado).
- **Análisis:** por escalón sin transitorio, capacidad, codo, cuello, cores por llamada, Wh de GPU por
  llamada-minuto y memoria de cada componente contra llamadas (base + MB por llamada; r² < 0,5 = "no escala").

## Trampas

- **Empaquetar el run del cliente por nombre** (`tar czf ... -C scripts/capacity/runs <run>`): con
  `ls -t | head -1` se toma el run equivocado.
- **Memoria:** `memory.current` del cgroup incluye el caché de archivos (pesos del modelo). El análisis usa
  anon + shmem + kernel y reporta el caché aparte.
- **Topes de GPU:** sin ellos las 3090 apagaron el server; además cambian el `hw_id`. Confirmarlos antes de medir.
- **Tras un reinicio,** `atentina-stack.service` levanta el stack y calienta el TTS (~2 min). Si algo de la
  inferencia quedó en `Exited`, `make up-inference`.
- **Escalones de 2 min (`rampa`)** con llamadas de ~115 s: la concurrencia real no sigue a la objetivo. El número
  fino sale de `fina` (4 min).
- **Turnos desfasados** (después de uno sin respuesta) **y solapados** (espera negativa): fuera de los
  percentiles, contados aparte.
- **Cliente saturado:** un proceso de asyncio no sostiene más de ~16 callers; con 64+ llamadas mirar la CPU del
  cliente. LiveKit Cloud despacha ~20–24 llamadas como máximo (EXP-011): medir con LiveKit propio.
- **`POST /api/v1/calls` con timeout:** no reintentar; puede dejar un job del agente esperando 5 min en una room
  vacía.
- **Stack en vivo:** el test no reinicia servicios; cambiar la config (override `docker-compose.<nombre>.yml` o
  variables de capacidad de `.env`) es un paso previo y queda en el `config_id`.

## Pendientes

- Medir Gemma 4 26B en 2 × 3090: `base`, `rampa`, `fina` y `sostenida` (próximo CAP).
- Caller reactivo con guiones por campo: hoy usa el corpus de 9 frases de `scripts/loadtest/audio/` con turnos
  sorteados.
- Cortes del lado del agente (factor de tiempo real por frase), métricas de LiveKit (falta `prometheus_port` en
  `livekit/livekit.yaml`) y análisis del tráfico PCIe (queda en `dmon.log`).
- Varias PCs cliente coordinadas, para cargas de 64+ llamadas.
- Sin sudo quedan vacíos la velocidad de la RAM (`dmidecode`) y RAPL en la ficha.
