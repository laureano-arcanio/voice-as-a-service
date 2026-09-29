# Capacidad: resultados vigentes y test

Cuántas llamadas soporta el pipeline con una calidad dada, qué etapa se degrada primero y con qué
recurso, y cómo escala la memoria de cada parte. Se mide con el test de capacidad (diseño en
[`../CAPACITY_TEST_PLAN.md`](../CAPACITY_TEST_PLAN.md), código en `scripts/capacity/`). Las
mediciones anteriores con el loadtest (EXP-001 a 013) están en [`../archive/`](../archive/README.md).

## Resultados vigentes ([CAP-002](CAP-002-5060ti-tts-3090-llm-stt-classic/), 2026-09-25)

Server de validación actual (`hw_id 03dfeb24`): Ryzen 7 5700X, 64 GB, ASRock B550M Pro SE.
- **TTS solo en una RTX 5060 Ti 8 GB** (slot del chipset, PCIe gen3 x4, 180 W).
- **LLM + STT en una RTX 3090** (slot de la CPU, gen4 x16, a 280 W).
- Motor `classic`, LiveKit propio, agente en el mismo host.

| Llamadas simultáneas | Espera del cliente p50 / p95 | Qué pasa |
|---|---|---|
| 1 (piso) | 1,66 / 2,04 s | e2e del server 0,92 s; el cliente espera ~0,7 s más |
| ~13 | 1,91 / 2,43 s | Holgado: 5060 Ti al 71 % de los segundos saturada, CPU 36 % |
| **~22 (codo)** | **2,12 / 2,81 s** | **5060 Ti (TTS) saturada** (91 %). LLM y STT sin cola |
| ~42 | 2,99 / 4,16 s | TTS con 311 ms hasta el primer audio; CPU 84 % |
| ~56 | 4,85 / 6,84 s | CPU del host al 98,6 %: VAD atrasado, STT con 191 ms de cola |
| ~110 (`rampa`) | colapso | 65 turnos sin respuesta; el talker del TTS se cayó en el drenaje |

Números de `fina` (escalones de 4 min), salvo el piso (`base`) y el colapso (`rampa`).

- **Capacidad:** ~13 llamadas con p95 ≤ 2,4 s, ~22 con p95 ≤ 2,8 s y ~32 con p95 ~3,4 s. El SLO del plan (90 % de turnos ≤ 1,5 s) no se cumple ni con 1 llamada: el piso es 1,66 s de p50.
- **Primer cuello: la 5060 Ti con el TTS,** desde ~22 llamadas.
- **Segundo cuello: la CPU del host,** desde ~55 llamadas. El agente usa ~0,11–0,13 cores por llamada.
- **Memoria:** solo escala el agente, **~113 MB por llamada** (r² 0,99), más ~5 MB de LiveKit.
  - LLM, STT y TTS reservan todo al arrancar.
  - VRAM: 15,6 GB el LLM y 1,6 GB el STT en la 3090; 7,66 GB el TTS en la 5060 Ti.
- **Potencia:** 419 W de pico entre las dos GPUs (la 5060 Ti, 141 W).
- **Arranque:** el primer pedido al TTS después de arrancarlo tarda más de 20 s. Hay que calentarlo antes de atender llamadas.
- **Estabilidad:** 20 min con ~30 llamadas (`sostenida`, p95 3,5 s) sin degradarse ni perder memoria. Con ~110 llamadas (sobrecarga) el talker del TTS se cayó y no se recupera solo; hasta 62 llamadas, no.

## Comparación por hardware

Mismo perfil (`rampa`), mismo cliente y misma config de modelos y motor.

| | [CAP-001](CAP-001-2x3090-pl280-classic/): 2 × 3090 | [CAP-002](CAP-002-5060ti-tts-3090-llm-stt-classic/): 5060 Ti + 3090 |
|---|---|---|
| Reparto | LLM en una 3090; TTS + STT en la otra | TTS en la 5060 Ti; LLM + STT en la 3090 |
| Piso p50 / p95 | 1,61 / 1,99 s | 1,66 / 2,04 s |
| Llamadas con p95 ≤ 2,4 s | ~20 | ~13–15 |
| Espera con ~32 llamadas, p50 / p95 | 2,27 / 3,03 s | 2,51 / 3,36 s |
| Codo | ~32 | ~22 (`fina`); ~34 en la `rampa` |
| Primer cuello | Las dos GPUs | La 5060 Ti (TTS) |
| Con ~65 llamadas | CPU del host; p95 8,3 s | CPU del host; p95 11,1 s |
| TTS primer audio con ~32 llamadas | 126 ms | 228 ms |
| Potencia de GPUs, pico | 559 W | 419 W |
| Wh de GPU por llamada-minuto (~32 llamadas) | 0,28 | 0,19 |
| Agente, MB / cores por llamada | 104 / 0,12 | 113 / 0,12 |

**Conclusión:** hasta ~30 llamadas, el TTS en una 5060 Ti 8 GB cuesta ~0,3 s de p95 contra una 3090,
con ~140 W menos. Con este reparto, el límite de GPU es la 5060 Ti y el de CPU es el agente.

## Índice

| CAP | Fecha | Hardware (`hw_id`) | Config | Perfiles | p95 ≤ 3 s | Codo | Cuello | Piso p50 | Cores / MB por llamada |
|---|---|---|---|---|---|---|---|---|---|
| [001](CAP-001-2x3090-pl280-classic/) | 2026-09-25 | 2 × 3090 a 280 W (`8489259f`) | classic; LLM solo en una 3090, TTS + STT en la otra | base, rampa | ~32 | ~32 | GPUs; con 64, CPU | 1,61 s | 0,12 / 104 |
| [002](CAP-002-5060ti-tts-3090-llm-stt-classic/) | 2026-09-25 | 5060 Ti 8 GB + 3090 a 280 W (`03dfeb24`) | classic; TTS solo en la 5060 Ti, LLM + STT en la 3090 | base, rampa, fina, sostenida | ~22 (p95 2,8 s) | ~22 | 5060 Ti (TTS); con ~55, CPU | 1,66 s | 0,12 / 105–113 |
| [004](CAP-004-5060ti-riser-x1-recableado-classic/) | 2026-09-28 | 5060 Ti en riser PCIe x1 recableado + 3090 a 280 W (`4af4cd18`) | classic; igual que CAP-002, 5060 Ti por x1 | rampa | ~21 (interpolado; p95 2,4 s con 13,9 y 4,6 s con 41,6) | ~21 | 5060 Ti (TTS); con 59, CPU | - | 0,11 / 103 |

## Calculadora de costos

[`calculadora-costos.html`](calculadora-costos.html) (HTML autocontenido, se abre en el navegador): con la capacidad medida por tipo de server y los precios de cada componente, fijos y energía, calcula cuántos servers hacen falta (N+1), el costo por canal y por minuto, y el precio de cada paquete con margen. Todos los valores son editables.

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
   # VAAS_API_KEY en el .env de la laptop: API key del cliente interno (sin límites),
   # `make api-key CLIENT=interno NAME=capacidad` en el server. El agente del perfil
   # (`workflow:`) es el slug de la plantilla, que el seed crea en ese cliente.
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
- **TTS en la 5060 Ti:** el primer pedido después de arrancarlo tarda más de 20 s (compilación de kernels): calentarlo antes de medir.
- **Tras un reinicio,** la inferencia no vuelve sola (`Exited (128)`): `make up-inference`.
- **Escalones de 2 min (`rampa`)** con llamadas de ~115 s: la concurrencia real no sigue a la objetivo. Para el número fino, `fina` (4 min).
- **Turnos desfasados** (después de uno sin respuesta) **y solapados** (espera negativa): el análisis los excluye de los percentiles y los cuenta aparte (`turnos_desfasados`, `turnos_solapados`).
- **Memoria:** `memory.current` del cgroup incluye el caché de archivos (pesos del modelo). El análisis usa la memoria usada (anon + shmem + kernel) y reporta el caché aparte.
- **Empaquetar el run del cliente por nombre** (`tar czf ... -C scripts/capacity/runs <run>`): con `ls -t | head -1` se toma el run equivocado.
