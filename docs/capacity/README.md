# Capacidad: resultados vigentes y test

Cuántas llamadas soporta el pipeline con una calidad dada, qué etapa se degrada primero y con qué
recurso, y cómo escala la memoria de cada parte. Se mide con el test de capacidad (diseño en
[`../CAPACITY_TEST_PLAN.md`](../CAPACITY_TEST_PLAN.md), código en `scripts/capacity/`). Las
mediciones anteriores con el loadtest (EXP-001 a 013) están en [`../archive/`](../archive/README.md).

## Resultados vigentes ([CAP-001](CAP-001-2x3090-pl280-classic/), 2026-09-25)

Server de validación: 2 × RTX 3090 a 280 W, núcleo ≤ 1800 MHz, memoria 9501 MHz; Ryzen 7 5700X.
Reparto de `AGENTS.md`, motor `classic`, LiveKit propio, agente en el mismo host.

| Llamadas simultáneas | Espera del cliente p50 / p95 | Qué pasa |
|---|---|---|
| 1 (piso) | 1,61 / 1,99 s | e2e del server 0,90 s; el cliente espera ~0,7 s más |
| ~20 | 1,86 / 2,38 s | Holgado: GPUs al 71 / 84 %, CPU 44 % |
| **~32 (codo)** | **2,27 / 3,03 s** | **Las dos GPUs saturadas** (> 90 % de los segundos al ≥ 95 %). Sin cola en LLM ni TTS |
| ~70 | 5,83 / 8,25 s | CPU del host al 99,8 %: VAD del agente atrasado, STT con 364 ms de cola |
| ~130 | colapso | 64 % de llamadas fallidas, saludo de 12,8 s |

- **Capacidad:** ~20 llamadas con p95 ≤ 2,4 s y ~32 con p95 ≤ 3 s. El SLO del plan (90 % de turnos ≤ 1,5 s) no se cumple ni con 1 llamada: el piso es 1,6 s de p50.
- **Primer cuello: GPU.** Con ~32 llamadas las dos GPUs llegan al 93–97 % (el LLM en la 0; TTS + STT en la 1).
- **Segundo cuello: CPU del host.** El agente usa ~0,11–0,14 cores por llamada, y con 64 llamadas el host de 16 hilos se satura.
- **Memoria:** solo escala el agente, **~104 MB por llamada** (r² 0,99), más ~5 MB de LiveKit.
  - Con 128 llamadas el agente usaría ~14 GB.
  - LLM, TTS y STT reservan su RAM y VRAM al arrancar: 22,7 + 13,1 + 2,1 GB de VRAM, y 3,4 + 5,9 + 1,3 GB de RAM más el caché de sus pesos.
- **Potencia:** sin tope, las 2 GPUs llegaron a 660 W sostenidos (con picos mayores) y el server se apagó con ~32 llamadas. Con 280 W y clocks limitados, el máximo fue 559 W.
- **Calidad:**
  - El saludo es lo primero que se degrada: p95 1,4 s con 1 llamada y 3,9 s con 32 (arrancar el job compite por la CPU).
  - WER 0,1–0,2: "Sí." se transcribe como "C".
- **Para producción:** el cómputo de GPU y la CPU del agente se dimensionan por separado. Con este hardware, ~32 llamadas por par de 3090 con p95 ≤ 3 s. La CPU del agente, a ~0,12 cores y ~0,1 GB por llamada, conviene en otro host.

## Índice

| CAP | Fecha | hw_id | Config | Perfiles | p95 ≤ 3 s | Codo | Cuello | Piso p50 | Cores / MB por llamada |
|---|---|---|---|---|---|---|---|---|---|
| [001](CAP-001-2x3090-pl280-classic/) | 2026-09-25 | `8489259f` (2 × 3090 a 280 W) | `3c35f6bd`: classic, LLM solo en GPU 0 | base, rampa | ~32 | ~32 | GPUs; con 64, CPU | 1,61 s | 0,12 / 104 |


## Cómo correrlo

1. **Server** (este host), antes de la carga:
   ```bash
   make capacity-monitor PERFIL=rampa
   ```
   - Escribe la ficha de hardware y config (`hw_server.json`, con `hw_id` y `config_id`).
   - Deja corriendo `monitor.py` en `scripts/capacity/runs/monitor_<fecha>_<perfil>/`.
2. **Cliente** (la PC del loadtest, con LiveKit propio en su `.env`):
   ```bash
   make capacity PERFIL=rampa ARGS="--base-url http://192.168.1.99:8011" PING=192.168.1.99
   ```
   Escribe su ficha (`hw_cliente.json`) y el run en `scripts/capacity/runs/<fecha>_<perfil>/`: `calls.csv`, `turns.csv`, `client.csv` y `run.json`.
3. **Server**, al terminar:
   ```bash
   make capacity-monitor-stop
   make capacity-analyze RUN=<run del cliente copiado acá> MON=scripts/capacity/runs/monitor_<...> [BASE=<summary.json de un run base>]
   ```
   Genera en el directorio del run: `summary.json` (ficha de capacidad), `steps.csv`, `windows.csv`, `memoria.csv` y `report.html`.

Perfiles en `scripts/capacity/perfiles/`:

| Perfil | Para qué |
|---|---|
| `humo` | Verificar el test, ~3 min |
| `base` | Piso de latencia y duración media de llamada: 10 llamadas de a una |
| `rampa` | Ubicar el codo, de 4 a 96 |
| `fina` | Precisar la capacidad alrededor del codo |
| `sostenida` | Estabilidad térmica y de memoria |

Los comunes (workflow, voz, buckets, SLO, llamada buena) están en `_comun.yml`.

Primero se corre `base`. Su `summary.json` se pasa como `--base` en el cliente (tasa de llegadas)
y como `BASE=` en el análisis (espera agregada por la carga).

## Qué mide

- **Por turno** (cliente): espera percibida, bucket, duración de la respuesta, cortes (silencios de 0,3–1,5 s dentro de la respuesta), sin respuesta y WER de la transcripción. Si coinciden los turnos, también el desglose del server (eou, stt, llm, tts, e2e).
- **Por llamada:** tiempo hasta el saludo, llamada buena (sección 2 del plan), fallas y atraso del micrófono del cliente.
- **Server** (`monitor.py`, 1 Hz):
  - El `sampler.py` de siempre: CPU, GPU y vLLM.
  - **RAM por componente:** memoria del cgroup de cada servicio (anon, file, shmem, kernel, swap), PSS (agente y `app`; los contenedores de root solo dan RSS), host y lo que queda fuera del stack.
  - Memoria de cada proceso del agente, por rol (`main`, `forkserver`, `job`).
  - VRAM por componente.
  - Frecuencia y temperatura de la CPU, tráfico PCIe, red y UDP.
  - Contadores de avisos del agente: VAD atrasado, event loop bloqueado, sin proceso precalentado, job matado.
- **Análisis:**
  - Por escalón, sin el transitorio: SLO, capacidad, codo, cuello de botella, cores por llamada y Wh de GPU por llamada-minuto.
  - Memoria de cada componente contra llamadas simultáneas (base + MB por llamada, r²), con proyección a 64 y 128 llamadas. Con r² < 0,5 el componente se marca "no escala".

## Estado (2026-09-25)

| Fase del plan | Estado |
|---|---|
| 1. Ficha de hardware y config | Hecha. Sin sudo quedan vacíos la velocidad de la RAM (`dmidecode`) y RAPL |
| 2. Llegadas Poisson, perfiles, `turns.csv`/`calls.csv` | Hecha |
| 3. Calidad y recursos | Hecha, salvo: cortes del lado del agente (factor de tiempo real por frase), métricas de LiveKit (falta `prometheus_port` en `livekit/livekit.yaml`, requiere reiniciar LiveKit) y análisis del tráfico PCIe (se guarda en `dmon.log`) |
| 4. Análisis, `report.html`, `summary.json` | Hecha |
| 5. Caller reactivo con guiones | Pendiente: hoy usa el corpus de 9 frases con turnos sorteados |
| 6. Workflow sintético `capacity_bench` | Pendiente |
| 7. Varias PCs cliente coordinadas | Pendiente |

Decisiones pendientes del plan (buckets y SLO): se usan los valores propuestos, configurables en
`_comun.yml`. Con el piso actual (p50 1,6 s) el SLO de 1,5 s no se cumple en ningún escalón. Por eso
el análisis también informa la carga máxima con p95 ≤ 2, 3, 4 y 5 s.

## Trampas

- **Potencia:** sin tope, las 3090 pueden apagar el server por picos de consumo. Aplicar los límites de GPU antes de medir (ver `AGENTS.md`, Hosts): no sobreviven a un reinicio.
- **Tras un reinicio,** la inferencia no vuelve sola (`Exited (128)`): `make up-inference`.
- **Escalones de 2 min (`rampa`)** con llamadas de ~115 s: la concurrencia real no sigue a la objetivo. Para el número fino, `fina` (4 min).
- **Turnos desfasados** (después de uno sin respuesta) **y solapados** (espera negativa): el análisis los excluye de los percentiles y los cuenta aparte (`turnos_desfasados`, `turnos_solapados`).
- **Memoria:** `memory.current` del cgroup incluye el caché de archivos (pesos del modelo). El análisis usa la memoria usada (anon + shmem + kernel) y reporta el caché aparte.
- **Empaquetar el run del cliente por nombre** (`tar czf ... -C scripts/capacity/runs <run>`): con `ls -t | head -1` se toma el run equivocado.
