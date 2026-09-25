# Plan: test de capacidad con calidad percibida

Test nuevo, separado de `make loadtest` (que queda como está). Responde:

1. **¿Cuántas llamadas soporta el pipeline** (simultáneas y por minuto) **con una calidad dada?**
2. **¿Qué etapa se degrada primero y qué recurso la limita?** (CPU, GPU, VRAM, red)
3. **¿Cómo se compara contra otro hardware o config?** El server se va a actualizar:
   cada run tiene que llevar el registro completo de hardware y config para comparar.

## 1. Por qué un test nuevo

| Hoy (`loadtest`) | Problema | Test nuevo |
|---|---|---|
| N callers fijos (modelo cerrado) | Si el sistema se frena, los callers también y la carga baja sola: esconde la saturación | Llegadas por tasa (Poisson), como el tráfico real |
| Tandas separadas de 16, 32, ... | No da un límite, solo "anduvo o no" | Escalones con criterio de capacidad (SLO) |
| Mide el inicio de la respuesta | No ve cortes del audio, errores de STT ni conversaciones rotas | Calidad por turno y por llamada |
| Frases sueltas al azar | El agente reacciona fuera de guion; la carga no es realista | Caller que responde lo que el agente pregunta |
| `meta.json` con hardware parcial del server | Sin cliente, PCIe, frecuencias, red ni versión del código | Registro de hardware y config completo, en todos los hosts |

Datos medidos que condicionan el diseño (2026-09-25):

- **Piso de la espera con 1 llamada: 1,8–2,4 s** (`client_latency_s`). El fin de turno (`eou`) se lleva 0,4–1,0 s: es config del VAD y del turn detector, no carga.
- **Límite actual: CPU del host**, no la GPU. Con 64 llamadas el host va al 93–97 % y el agente usa 8,7 cores (~0,135 por llamada). El agente registró "VAD inference is slower than realtime".
- **Con 32 llamadas** (EXP-012): e2e p50 2,0 s, sin cola en la inferencia.

## 2. Definiciones

### Espera percibida (métrica principal)

Desde que termina el audio del usuario hasta el primer audio del agente, medida en el cliente.
Se reporta también la **espera agregada por la carga**: la percibida menos la mediana con 1 llamada,
en el mismo hardware y config. La primera mide la experiencia; la segunda, la capacidad.

### Buckets

| Espera percibida | Categoría |
|---|---|
| < 0,5 s | óptimo |
| 0,5–0,8 s | excelente |
| 0,8–1,0 s | bueno |
| 1,0–1,5 s | aceptable |
| 1,5–2,0 s | regular *(a confirmar: faltaba en la propuesta)* |
| 2,0–3,0 s | malo |
| > 3,0 s | pésimo |

Los cortes van en el perfil de carga (sección 4), no en el código. Con el piso actual (1,8–2,4 s),
los dos primeros buckets no se alcanzan con ninguna carga: el reporte lo muestra tal cual.

### Calidad de una llamada

Una llamada es **buena** si cumple todo:

- el agente saludó en ≤ 3 s desde que el caller entró a la room;
- ningún turno en "pésimo" y a lo sumo 1 en "malo";
- ningún turno sin respuesta ni respuesta cortada;
- el resultado del workflow es el esperado por el guion (sección 5).

### Criterio de capacidad (SLO, configurable)

**Capacidad = la mayor carga sostenida en la que:**

- ≥ 90 % de los turnos quedan en ≤ 1,5 s y ≤ 1 % pasan de 3 s;
- ≥ 95 % de las llamadas son buenas;
- ≤ 1 % de las llamadas fallan (sin saludo, cortadas, error);
- el cliente está sano (sección 6.3).

Se reporta en **llamadas simultáneas** (define cuántos canales) y en **llamadas por minuto**
(depende de la duración de llamada). Se relacionan por la ley de Little: simultáneas ≈ llegadas/min × duración media en min.

## 3. Modelo de carga

- **Llegadas Poisson** a tasa λ por escalón. Cada llamada dura lo que su guion (sección 5), no un número fijo de turnos.
- El perfil se escribe en **concurrencia objetivo** (4, 8, 16, ...) y el test la convierte en λ con la duración media medida en la línea base.
- La concurrencia real se mide (ventanas de vida de cada llamada) y es la que se usa en el análisis.
- **Escalón ≥ 2–3 × la duración media de llamada**, descartando el primer minuto (transitorio). Con escalones de 1 min el sistema no se estabiliza y se mide el pico de arranques. Arrancar una llamada cuesta CPU: el agente carga modelos ONNX por job.

### Perfiles

| Perfil | Escalones | Duración | Para qué |
|---|---|---|---|
| `base` | 1 llamada a la vez, 10 llamadas | ~10 min | Piso de latencia y de calidad; duración media de llamada |
| `rampa` | 4 → 8 → 16 → 32 → 64 → 96, 2 min c/u | ~12 min | Ubicar el codo rápido |
| `fina` | +8 alrededor del codo (ej. 32, 40, 48, 56), 4 min c/u | ~16–20 min | El número de capacidad |
| `sostenida` | 80 % de la capacidad | 15–20 min | Estabilidad térmica y de memoria. En EXP-012 las GPUs ya entraban en thermal slowdown |

Cada run arranca con 1 min de warm-up (no se mide) y termina dejando cerrar las llamadas en curso,
sin llegadas nuevas (tampoco se mide).

Formato del perfil (versionado en el repo; la versión va al registro):

```yaml
nombre: fina
version: 1
workflow: demo_booking
voz: sofia
guiones: demo_booking            # scripts/capacity/guiones/demo_booking/
warmup_s: 60
escalones:                       # concurrencia objetivo -> lambda con la duracion base
  - {concurrencia: 32, duracion_s: 240}
  - {concurrencia: 40, duracion_s: 240}
  - {concurrencia: 48, duracion_s: 240}
  - {concurrencia: 56, duracion_s: 240}
descartar_s: 60                  # transitorio al inicio de cada escalon
buckets_s: [0.5, 0.8, 1.0, 1.5, 2.0, 3.0]
slo: {p_ok: 0.90, ok_s: 1.5, p_pesimo: 0.01, llamadas_buenas: 0.95, fallas: 0.01}
```

## 4. Tráfico realista

### Caller reactivo por campo (fase 5)

Hoy el caller dice frases al azar. El nuevo responde lo que el agente pide, **sin LLM** en el cliente
(usaría la misma GPU que se mide):

- Cada guion tiene, por campo del workflow, varias respuestas pregrabadas con TTS (con el texto guardado) y de distinto largo, más respuestas de relleno ("¿cómo?", "dale", una pregunta fuera de tema).
- Antes de cada turno el caller lee `GET /api/calls/{id}` (campos pendientes) y elige la respuesta al primer campo requerido sin valor. Con una probabilidad configurable mete un relleno.
- La llamada termina sola cuando el workflow se completa: la duración y la carga por llamada salen realistas.
- Cada guion define la **persona** (valores de los campos) y, con eso, el **resultado esperado**.
- Mix de largos del usuario (STT) y pausa de pensar: los de hoy (50 % cortas / 25 % medianas / 25 % largas; lognormal con mediana 2,5 s), configurables.

Hasta tener los guiones (fases 2–4), el test usa el corpus actual (`scripts/loadtest/audio/`, 9 frases)
con el flag `loadtest` y un número de turnos por llamada sorteado.

### Workflow sintético de benchmark (fase 6, opcional)

Para comparar hardware con una carga idéntica y sin depender del motor: un workflow `capacity_bench`
cuya respuesta tiene largo fijo según una marca en lo que dice el usuario (1, 2 o 3 frases).
Se registran caracteres de TTS y tokens por turno para verificar que el perfil de carga se cumplió.
Los guiones reales dan la capacidad de producción; el sintético, una unidad de carga comparable.

## 5. Calidad percibida: qué se mide

### Por turno

| Métrica | Dónde | Cómo |
|---|---|---|
| Espera percibida y bucket | cliente | Fin del audio enviado → primer audio del agente (como hoy) |
| Desglose eou / stt / llm / tts / e2e | agente | `call.latency` (`app/latency.py`), apareado al turno |
| Cortes dentro de la respuesta | agente + cliente | Agente: por frase, audio generado contra tiempo de síntesis (factor de tiempo real < 1 = corte). Cliente: silencios de 0,3–1,5 s dentro de una respuesta, en exceso sobre la línea base |
| Sin respuesta / respuesta cortada | cliente | Timeout esperando el inicio; respuesta que se corta sin que el caller hable |
| Error de transcripción (WER) | cliente + API | Texto conocido de la respuesta pregrabada contra lo que transcribió el agente (mensajes de `/api/calls/{id}`) |
| Frase partida o perdida | API | Turnos del server ≠ turnos del cliente (ya lo detecta `_rows_for_call`) |
| Concurrencia en ese instante | cliente | Llamadas vivas al terminar el turno |

### Por llamada

- Tiempo hasta el saludo (entra el caller → primer audio): despacho + arranque del job. Con CPU saturada es lo primero que sube.
- Peor turno, cantidad de turnos por bucket, llamada buena o no (sección 2).
- Resultado del workflow contra el esperado del guion: campos extraídos correctos.
- Duración, `ended_reason`, errores.
- Atraso máximo del micrófono del caller (`client_mic_lag_s`, ya existe en `caller.py`).

## 6. Registro de hardware, config y recursos

### 6.1 Ficha de hardware (una vez por host y por run)

Script nuevo `hwinfo.py`, que corre en **cada host que participa** con su rol: `inferencia`, `agente`, `livekit`, `cliente`.
Hoy el primero y el segundo son el mismo host, pero con el hardware nuevo pueden separarse.

| Grupo | Datos |
|---|---|
| Host | hostname, rol(es), kernel, distro, versión de Docker y NVIDIA Container Toolkit |
| CPU | modelo, núcleos/hilos, frecuencia base y máx., governor, boost activado, SMT |
| RAM | total, velocidad y canales (`dmidecode`, requiere sudo: si no hay permiso, queda vacío) |
| Placa | fabricante, modelo, versión de BIOS |
| GPU (c/u) | modelo, VRAM, driver, CUDA, VBIOS, power limit (actual y por defecto), clocks máx., PCIe gen y ancho actual y máximo, slot y bus |
| Disco | modelo y tipo del disco donde están los modelos (`hf_cache`) |
| Red | NIC y velocidad del enlace; RTT y pérdida cliente → server medidos al arrancar (ping a LiveKit y a la app) |
| Reloj | offset NTP/chrony. Hace falta para cruzar timestamps entre hosts |
| Ambiente | temperatura ambiente y notas (campo manual del run) |

Con los campos estables (CPU, RAM, placa, GPUs y su slot PCIe, power limit) se calcula un **`hw_id`**
(hash corto) que agrupa los runs del mismo hardware. Cambiar una placa, un power limit o un slot cambia el `hw_id`.

### 6.2 Ficha de config y código

- Commit de git y si hay cambios sin commitear (el diff queda guardado en el run).
- Lo que ya guarda `sampler.py` en `meta.json`: imagen, args y GPU de cada servicio, versiones de vLLM/torch, archivos de compose.
- Variables de capacidad de `.env` (`VLLM_LLM_MAX_NUM_SEQS`, `STT_MAX_BATCH`, ...), con los secretos enmascarados.
- Workflow (id y hash del YAML), checkpoint y voz del TTS, modelo del LLM, versión de LiveKit (server y agents).
- Perfil de carga y guiones (nombre, versión y hash).
- Un **`config_id`** (hash) análogo a `hw_id`.

### 6.3 Recursos durante el run (1 Hz)

Se reutiliza `scripts/loadtest/monitor/sampler.py`, que ya toma: CPU por core, CPU/mem/threads por
contenedor, threads más cargados, procesos ajenos, GPU (uso, VRAM, potencia, temperatura, clocks,
motivos de throttling, PCIe gen) y métricas de vLLM y de STT (cola, en vuelo, TTFT, entre tokens, KV). Se agrega:

| Qué | Para qué |
|---|---|
| Frecuencia real y temperatura de la CPU (`k10temp`/`coretemp`) | Throttling de CPU, que hoy no se ve |
| Tráfico PCIe por GPU (`nvidia-smi dmon -s t`) | Comparar placas/slots (ver `SERVER_HARDWARE.md`) |
| Red: bytes y paquetes por interfaz, errores y descartes UDP | LiveKit con 100+ llamadas |
| Por job del agente: CPU y memoria del proceso | Cores por llamada, el dato que dimensiona el host del agente |
| Contadores de logs del agente por ventana: "VAD inference is slower than realtime", "event loop blocked", "no warmed process available", errores de TTS/STT/LLM | Síntomas de CPU saturada en el agente |
| Métricas de LiveKit (Prometheus del server propio) | Rooms, participantes, pérdida de paquetes |
| En cada host cliente: CPU total y por core, atraso del micrófono | Cliente sano: si el p95 del atraso pasa 100 ms o la CPU del cliente pasa el 85 %, el escalón no vale |
| Energía: integral de `power.draw` de GPUs (y RAPL de CPU si está disponible) | Wh por llamada-minuto para comparar hardware |

## 7. Análisis y reporte

### Por ventana de 30 s y por escalón (sin el transitorio)

- Llegadas/min, llamadas completadas/min, concurrencia real (media y máx.).
- % de turnos por bucket, p50/p95/p99 de espera percibida y de espera agregada.
- % de llamadas buenas y de fallas; WER; cortes por respuesta; tiempo hasta el saludo.
- Desglose eou/stt/llm/tts: **qué etapa sube** cuando sube la espera.
- Recursos: CPU del host y del agente, cores por llamada, GPU (uso, seg. ≥ 95 %, VRAM, throttling), colas de vLLM y STT.

### Detección del límite

- **Capacidad:** el último escalón que cumple el SLO.
- **Codo:** el primer escalón con espera agregada p95 > +0,5 s sobre la línea base, o con más de 5 % de turnos en malo/pésimo.
- **Cuello de botella**, en ese escalón: el primer recurso saturado entre:
  - CPU del host ≥ 90 % o thread principal ≥ 95 %;
  - GPU con ≥ 90 % de los segundos al 95 % de uso;
  - cola de vLLM o de STT > 100 ms sostenida;
  - TTS con más de 83 ms entre tokens;
  - VRAM o KV cerca del 100 %;
  - cliente saturado (invalida el run).

### Salidas

- `report.html`: curvas de espera percibida (p50/p95) y de % por bucket contra la concurrencia real, desglose por etapa, recursos en la misma línea de tiempo y tabla por escalón.
- `summary.json` (la **ficha de capacidad**): `hw_id`, `config_id`, perfil, capacidad (simultáneas y por minuto) al SLO, cuello de botella, piso de latencia, cores por llamada, Wh por llamada-minuto, llamadas por GPU.
- `analyze.py --md`: tablas markdown para el registro, como hoy.

## 8. Comparar hardware

- **Índice por hardware** en `docs/capacity/README.md`, con una fila por run registrado:
  `hw_id` (con nombre legible), `config_id`, perfil, capacidad al SLO, cuello de botella, piso p50, cores/llamada, Wh/llamada-min.
- **Siempre, en cada hardware nuevo:** perfil `base` (el piso cambia con la CPU y la GPU), después `rampa` y `fina` con los mismos guiones y la misma versión de perfil.
- **Mismo cliente y red**, o se registra la diferencia. El cliente no puede ser el cuello de botella en ningún escalón que cuente.
- **Repetir la `sostenida`** al menos dos veces: la variación entre runs da el margen de error de la comparación.
- **Server compartido:** revisar procesos ajenos (hoy corren contenedores de otro proyecto en este host).
- **Separar agente e inferencia cuando el hardware lo permita:** la capacidad del sistema es la menor de las dos, y cada una se dimensiona con hardware distinto (CPU contra GPU).

## 9. Implementación por fases

Todo nuevo en `scripts/capacity/`; reutiliza `scripts/loadtest/caller.py` (`VirtualCaller`) y
`scripts/loadtest/monitor/sampler.py` sin cambiarles el comportamiento.

```
scripts/capacity/
  run.py            # orquestador: perfil -> llegadas -> procesos de callers
  hwinfo.py         # ficha de hardware (sec. 6.1) y de config (6.2)
  analyze.py        # ventanas, escalones, limite, summary.json
  report.html
  perfiles/         # base.yml, rampa.yml, fina.yml, sostenida.yml
  guiones/<workflow>/   # personas, respuestas por campo, audio pregenerado
  runs/<fecha>_<hw_id>_<perfil>/   # no versionado: hw, config, turns.csv, calls.csv, monitor/
docs/capacity/      # README (indice por hardware) y CAP-NNN-<slug>/ por run registrado
```

| Fase | Entrega | Terminada cuando |
|---|---|---|
| 0 | Confirmar buckets (1,5–2 s), SLO y definición de llamada buena | Decisiones en este doc |
| 1 | `hwinfo.py` + ficha de config + `hw_id`/`config_id`; en server y cliente | Ficha completa en este host y en la PC del loadtest; mismo hardware da el mismo `hw_id` |
| 2 | `run.py`: llegadas Poisson, perfiles YAML, varios procesos, `turns.csv` y `calls.csv` con bucket y concurrencia por turno. Corpus actual | `base` y `rampa` corren de punta a punta; la concurrencia real sigue a la objetivo ±10 % |
| 3 | Calidad: tiempo hasta el saludo, cortes (agente y cliente), sin respuesta, WER, contadores de logs del agente; recursos nuevos del sampler | Métricas en el CSV; con 1 llamada, WER y cortes coinciden con una escucha manual de 5 llamadas |
| 4 | `analyze.py` + `report.html` + `summary.json`; `docs/capacity/` | Un run de `rampa` da capacidad, codo y cuello de botella sin análisis manual |
| 5 | Caller reactivo por campo + guiones de `demo_booking` (≥ 10 personas) | ≥ 95 % de llamadas con resultado correcto con 1 llamada |
| 6 | Workflow sintético `capacity_bench` (opcional) | Caracteres de TTS por turno dentro de ±15 % del perfil |
| 7 | Varias PCs cliente coordinadas: mismo `run_id` y hora de inicio acordada; cada una toma su parte de las llegadas | 2 PCs dan la misma curva que 1 en los escalones donde 1 no se satura |

Las fases 1–4 alcanzan para medir el hardware actual antes de la actualización. La 5 mejora el realismo;
conviene tenerla antes de comparar contra el hardware nuevo, para que las dos mediciones usen los mismos guiones.

## 10. Trampas conocidas (aplican al test nuevo)

- **Cliente saturado:** un proceso de asyncio no sostiene más de ~16 callers (ver `run.py`). Con 64+ llamadas hace falta verificar la CPU del cliente o usar varias PCs (fase 7).
- **LiveKit Cloud** despacha como máximo ~20–24 llamadas (EXP-011): usar LiveKit propio.
- **TTS sin `voice` o con `voice="default"`** mata el engine de `vllm-tts`: el perfil siempre fija una voz del checkpoint.
- **POST /calls que da timeout:** no reintentar, porque puede dejar un job del agente esperando 5 min en una room vacía.
- **Warm-up:** sin él, el primer escalón infla el TTFT por la captura de CUDA graphs.
- **Stack en vivo:** el test no reinicia servicios; cambiar la config es un paso manual previo y queda en la ficha de config.

## Decisiones pendientes

1. El bucket de 1,5–2 s: ¿"regular" o se une a otro?
2. SLO: ¿los valores de la sección 2 sirven como punto de partida?
3. ¿Resultado correcto del workflow como condición de llamada buena desde la fase 5, o solo como métrica?
4. ¿La PC del loadtest es siempre la misma? Si cambia, su ficha de hardware entra en la comparación.
