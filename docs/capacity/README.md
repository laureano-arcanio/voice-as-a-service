# Test de capacidad con calidad percibida

Mide cuántas llamadas soporta el pipeline con una calidad dada, qué etapa se degrada primero
y con qué recurso, y cómo escala la memoria de cada parte. Diseño en
[`../CAPACITY_TEST_PLAN.md`](../CAPACITY_TEST_PLAN.md). Código en `scripts/capacity/`; los runs
crudos quedan en `scripts/capacity/runs/` (no versionado).

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
`_comun.yml`. Con el piso actual (~1,7 s) el SLO de 1,5 s no se cumple en ningún escalón. Por eso
el análisis también informa la carga máxima con p95 ≤ 2, 3, 4 y 5 s.

## Prueba de humo (2026-09-25, este host como cliente)

5 llamadas (2 en serie + Poisson con objetivo 3):
- espera p50 1,65–1,67 s, e2e del server ~1,0 s, saludo p50 1,0 s;
- WER 0,31: el "Sí." se transcribió como "C";
- 86 % de las respuestas con algún silencio de 0,3–0,56 s. Probablemente sean pausas entre oraciones; se compara contra `base`.

Memoria: el agente sube **~94 MB por llamada simultánea** (PSS, r² 0,97). vLLM y STT no cambian
(RAM y VRAM reservadas al arrancar). El resto no escala.

## Índice por hardware

| Run | hw_id | config_id | Perfil | Capacidad al SLO | p95 ≤ 3 s | Cuello | Piso p50 | Cores/llamada | MB/llamada (agente) |
|---|---|---|---|---|---|---|---|---|---|
| — | 351644b6 (2 × 3090, Ryzen 7 5700X) | — | — | — | — | — | — | — | — |
