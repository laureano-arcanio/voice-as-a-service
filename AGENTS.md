# AGENTS.md — infraestructura

Agente de voz telefónico con **inferencia propia**: LLM, STT y TTS corren
sobre GPUs locales, sin proveedores externos. Este archivo describe la
infraestructura. La app (motor conversacional por workflow YAML, API y worker de voz) está en
[`README.md`](README.md).

## Pedidos frecuentes

| Pedido | Qué hacer |
|---|---|
| "Voy a correr el test de capacidad (con <config>), registralo" | Seguir [`docs/capacity/README.md`](docs/capacity/README.md): aplicar los límites de GPU, `make capacity-monitor PERFIL=<perfil>` en el server antes de la carga y avisar; el usuario corre `make capacity` en la laptop y pasa el run empaquetado; `make capacity-monitor-stop`, `make capacity-analyze` y registrar `docs/capacity/CAP-NNN-<slug>/`. |
| "Entrená / reentrená la voz <voz> del TTS" | Delegar al agente [`tts-finetune`](.claude/agents/tts-finetune.md), que sigue [`docs/TTS_FINETUNE.md`](docs/TTS_FINETUNE.md). Entrenar el 1.7B necesita parar `vllm-tts`: confirmar antes. |
| "Probá <modelo o reparto de GPU>" | Override `docker-compose.<nombre>.yml` y confirmar antes de reiniciar servicios; después, el mismo procedimiento. |

## Servicios (`docker-compose.yml`)

`make up` levanta todo. Por partes: `make up-agent` (db + app + agent), `make up-inference`
(los 3 de inferencia), `make up-nginx` (proxy) y `make up-pbx` (Asterisk). `make help` lista el resto.

| Servicio | Qué es | Imagen | Puerto host | GPU |
|---|---|---|---|---|
| `db` | MySQL 8 | mysql:8.0 | 127.0.0.1:3306 | — |
| `app` | FastAPI: API del motor conversacional; despacha el agente a una room de LiveKit | build | 8011 | — |
| `agent` | Worker de LiveKit Agents (STT → LLM → TTS); sale a LiveKit Cloud | build | — | — |
| `vllm-llm` | LLM `RedHatAI/Qwen3.5-9B-quantized.w4a16` (Qwen3.5-9B en 4 bits) | vllm/vllm-openai:latest | 127.0.0.1:8101 | 1 (3090) |
| `stt-parakeet` | STT `nvidia/parakeet-tdt-0.6b-v3`, servidor propio (`stt/server.py`) | build | 127.0.0.1:8102 | 1 (3090) |
| `vllm-tts` | TTS Qwen3-TTS 1.7B-Base con fine-tuning, 41 voces en un checkpoint (`multi41`) | vllm/vllm-omni:v0.28.0 (fijada) | 127.0.0.1:8103 | 0 (5060 Ti) |
| `proxy` | Entrada pública por IP fija; nginx rutea `/llm`, `/stt` y `/tts` | nginx:alpine | 0.0.0.0:8100 (`PROXY_PORT`) | — |
| `asterisk` | Puente SIP Anura ↔ LiveKit (`network_mode: host`) | build | — | — |
| `livekit`, `livekit-sip`, `livekit-redis` | LiveKit propio (desarrollo, `docker-compose.livekit.yml`), en lugar de Cloud | livekit-server v1.13.7, sip v1.17.0 | 7880, 7881, 7882/udp, 5060 | — |

- La inferencia habla API OpenAI y exige `Authorization: Bearer $VLLM_API_KEY`. Los puertos 810x son solo para debug local.
- Modo remoto: `app` + `agent` pueden correr en otra PC (`make up-agent`) contra la inferencia por el proxy: `http://181.104.113.28:8100/{llm,stt,tts}/v1` (IP fija `PUBLIC_HOST`; el router redirige 8100 a 192.168.1.99). Así se corre el loadtest. Es HTTP plano: la auth es solo `VLLM_API_KEY`.

## Hosts

- **Server de validación (este):**
  - Hardware (desde el 25-sep-2026): Ryzen 7 5700X, 64 GB, ASRock B550M Pro SE.
    - GPU 0: RTX 5060 Ti 8 GB, en el slot del chipset (`04:00.0`, PCIe gen3 x4).
    - GPU 1: RTX 3090 24 GB, en el slot de la CPU (`07:00.0`, gen4 x16).
    - Antes eran 2 × 3090 (CAP-001).
  - La 3090 (GPU 1) también dibuja el escritorio.
  - Corren contenedores de otros proyectos: no tocarlos.
  - Sirve solo para validar; no es producción.
  - **Límites de la 3090** (desde el 25-sep-2026): sin tope, dos 3090 apagaron el server por un pico de consumo durante el test de capacidad.
    - Se aplican a mano con sudo, solo a la 3090: `nvidia-smi -i 00000000:07:00.0 -pl 280`, techo del núcleo a 1800 MHz (`-lgc 210,1800`) y memoria a 9501 MHz (`-lmc 405,9501`).
    - La 5060 Ti va sin límite: consume como máximo 141 W.
    - No sobreviven a un reinicio. El tope de potencia cambia el `hw_id` del test.
    - Tras un reinicio, la inferencia queda en `Exited (128)`: `make up-inference`.
- **Producción:** hardware en definición. Ver [`docs/capacity/README.md`](docs/capacity/README.md).

## Reparto de GPU vigente (CAP-002)

Override `docker-compose.gpu-5060.yml`, sumado a `COMPOSE_FILE` en `.env`. Sin el override, el compose principal tiene el reparto de 2 × 3090 (EXP-013, CAP-001).

| GPU | Servicios | Memoria |
|---|---|---|
| 0: 5060 Ti 8 GB | `vllm-tts` solo | Etapa 0 (talker) 0.58, largo máx. 2048, batches de 512; etapa 1 (Code2Wav) 0.36 sin CUDA graphs. Usa 7,66 de 8,15 GB |
| 1: 3090 24 GB | `vllm-llm` + `stt-parakeet` + escritorio | 0.70 (KV 4,8 GiB) + ~1,6 GB + ~0,5 GB (~18 GB usados) |

- **Topes de concurrencia:** LLM 64 secuencias (con 0.70 no arranca con 128); TTS 32 síntesis en el talker y 16 en Code2Wav.
- **Motor por defecto:** `classic` (`WORKFLOW_ID=demo_booking_classic`).
- **Capacidad medida** ([CAP-002](docs/capacity/CAP-002-5060ti-tts-3090-llm-stt-classic/)):
  - ~15 llamadas con espera del cliente p95 ≤ 2,4 s; ~34 con p95 ≤ 3,4 s;
  - con ~34 se satura la 5060 Ti (TTS), y con 64 la CPU del host (agente).
  - Con 2 × 3090 (CAP-001): ~20 y ~32 con p95 ≤ 3 s.

El TTS sirve el checkpoint fine-tuneado de `TTS_FT_CKPT` (default `multi41`, lr 2e-6, época 2)
con el nombre `qwen3-tts-ft`. Tiene 41 voces de OpenSLR 61 (28 mujeres, 13 hombres) con nombres
argentinos (`sofia`, `martin`, ...). El catálogo, con género, WER y car/s por voz, es
[`tts/finetune/voces.tsv`](tts/finetune/voces.tsv).

La voz va en `voice` en cada pedido. El agente usa, en orden:
1. la elegida en el dashboard para la llamada;
2. `agent.voice` del workflow;
3. `VLLM_TTS_VOICE`.

Ver [`docs/TTS_FINETUNE.md`](docs/TTS_FINETUNE.md).

## Reglas y trampas

- **TTS no comparte GPU con el LLM ni con otra réplica** (EXP-001 a 004). Con el STT Parakeet sí se probó: hasta ~48 llamadas el STT no se resiente, y con 64 sube a ~0,5–0,6 s (EXP-013). Escalar TTS es sumar GPUs.
- **TTS en la 5060 Ti:**
  - El primer pedido después de arrancarlo tarda más de 20 s, probablemente por la compilación de kernels para Blackwell. Sin calentarlo, la primera llamada no recibe el saludo.
  - En 8 GB entra justo; cambiar sus fracciones de memoria rompe el arranque. Ver `docker-compose.gpu-5060.yml` y CAP-002.
- **`--gpu-memory-utilization`** es una fracción de la memoria **total** de la GPU. Los que comparten GPU tienen que sumar menos de ~0.95, descontando el escritorio.
- **Arranque de servicios que comparten GPU:** no pueden arrancar a la vez, porque compiten por la memoria libre. Por eso `depends_on` los encadena: `stt-parakeet` espera a `vllm-llm` con el override de la 5060 Ti, y a `vllm-tts` en el compose principal.
- **Servicios descartados (sep-2026):** Qwen3-ASR (`vllm-stt`), Whisper Turbo, CosyVoice 3 y la segunda réplica de TTS salieron del compose; quedan en el historial de git y en `docs/archive/experiments/`. Para probar uno de nuevo, override `docker-compose.<nombre>.yml`.
- **Servidor propio de STT (`stt/server.py`, Parakeet):** expone `/metrics` con nombres de vLLM para que lo lea el sampler. Batching dinámico: junta lo que llega mientras la GPU trabaja, hasta `STT_MAX_BATCH` (8). Un pedido solo tarda lo mismo que sin batching (~60 ms). Con 16 clientes en paralelo rinde ×4,7 (76 contra 16 req/s) y la p50 baja de 996 a 204 ms. Batch 16 da ×5,4 a costa de ~150 ms por batch.
- **Flags del LLM:** `--max-cudagraph-capture-size` (igual a `VLLM_LLM_MAX_NUM_SEQS`) evita que su VRAM crezca con el tráfico. `--max-num-seqs` tiene tope por el cache Mamba de Qwen3.5: con 0.70 arranca con 64, el default de 256 no entra. `--limit-mm-per-prompt` en 0 porque el modelo trae un encoder de visión que no se usa. Ver los comentarios del compose.
- **LLM 9B en 4 bits (EXP-009):** mejor que el 4B en los escenarios del motor y más rápido por turno. Capacidad medida en CAP-001 y CAP-002 (antes EXP-012 y 013, archivados). El nombre del modelo en `VLLM_LLM_MODEL` tiene que coincidir entre `vllm-llm` y `app`/`agent`: al cambiarlo, recrear los tres.
- **vLLM-Omni:** fijada en v0.28.0, porque `latest` no arranca. Deja `num_requests_running` en 1 sin tráfico, así que la actividad se detecta por los contadores de tokens.
- **Voces del TTS:** están dentro del checkpoint fine-tuneado (`tts/finetune/work/`, no versionado), no en un volumen. Si se pierde `tts/finetune/work/`, hay que reentrenar. Agregar una voz es reentrenar el checkpoint con todas. El volumen `vllm_tts_speakers` tiene la voz clonada anterior (`sofia_ar`, para el checkpoint Base) y ya no se monta.
- **Nombres de voz:** los `arf_*`/`arm_*` ya no existen, desde `multi41`.
  - Al cambiar de checkpoint, los nombres tienen que coincidir con `VLLM_TTS_VOICE` y con `agent.voice`.
  - También en cualquier host que use este TTS por el proxy (modo remoto).
  - Si una voz no está servida, el agente cae a `VLLM_TTS_VOICE`. Si tampoco está esa, cada frase da 400.
- **Pedido al TTS sin `voice` o con `voice="default"`:** mata el engine de `vllm-tts` (busca `vivian`, que el checkpoint no tiene) y todo da 500 hasta reiniciarlo. Mandar siempre una voz del checkpoint.
- **Loadtest y motor por workflow:** `run.py` crea las llamadas con `POST /calls {"loadtest": true}` (`--workflow`, `--voice`). Con ese flag el agente no corta al completar el workflow, así cada llamada dura los `--turns` pedidos, como en EXP-001 a 008. `ttft_s` del CSV es ahora el LLM hasta el primer texto de la respuesta, no el TTFT de vLLM: ver `SERVER_COLUMNS` en `run.py`.
- **LiveKit propio (desarrollo):** con `COMPOSE_FILE` en `.env`, todos los targets usan `docker-compose.livekit.yml`. Las `LIVEKIT_*` de `.env` son las de este host; las de Cloud quedan en `LIVEKIT_CLOUD_*`. Ver `docs/TELEFONIA_ANURA.md`, sección 7.
- **Capacidad por motor en `.env`:** `VLLM_LLM_MAX_NUM_SEQS` (también fija el tamaño de CUDA graph), `VLLM_LLM_GPU_MEMORY_UTILIZATION`, `STT_MAX_BATCH`, `STT_MAX_BATCH_SECONDS`, `VLLM_TTS_GPU_MEMORY_UTILIZATION` y `VLLM_TTS_MAX_NUM_SEQS` (las dos etapas, por `--stage-overrides`). Los defaults del compose son el reparto de 2 × 3090 (EXP-013, CAP-001); con la 5060 Ti, `.env` tiene LLM 0.70 y 64 secuencias. Se aplican con `make up-inference`.
- **Comentarios del compose:** explican el porqué medido de cada flag. Mantenerlos al día al cambiar valores.

## Capacidad

Todo cambio de modelo (STT, TTS o LLM), de reparto de GPU, de flags de memoria o de hardware
se mide con el test de capacidad y se registra en [`docs/capacity/`](docs/capacity/README.md)
(`CAP-NNN`), donde están el procedimiento, los resultados vigentes y el índice por hardware.

- **Código:** `scripts/capacity/`.
  - `hwinfo.py`: ficha de hardware y config, con `hw_id` y `config_id`.
  - `run.py`: cliente, llegadas Poisson por escalón.
  - `monitor.py`: server a 1 Hz, con RAM por componente.
  - `analyze.py`: análisis, `summary.json` y `report.html`.
  - `perfiles/`: los perfiles de carga.
- **Orden:** `base` (piso) → `rampa` (codo) → `fina` (número de capacidad) → `sostenida`.
- **Overrides:** cada prueba de config usa un override `docker-compose.<nombre>.yml` (o las variables de capacidad de `.env`), no el compose principal.
- **Volver a la config vigente:** `make up-inference`, sin el `-f` extra.
- **Runs crudos:** `scripts/capacity/runs/` no se versiona.
- **Archivo:** las mediciones con el loadtest (EXP-001 a 013, `LOADTEST_CAPACITY.md`) están en [`docs/archive/`](docs/archive/README.md). `scripts/loadtest/` sigue: el test reutiliza su caller y su sampler.

## Cómo trabajar en este server

- Puede haber otras sesiones de agente trabajando en paralelo en el repo y en los contenedores. Mirar `git status` y `docker ps` antes de cambiar algo, y no revertir cambios ajenos.
- No reiniciar servicios ni lanzar pruebas que nadie pidió: el stack se usa en vivo.
- Archivos temporales (muestras de audio, scripts de prueba, descargas, clones de repos): siempre en `scratch/` dentro del repo (está en `.gitignore`), nunca en `/tmp` ni fuera del repo, para que el usuario pueda abrirlos.
- Docs y comentarios en español, breves y con datos medidos.

## Documentación

- [`README.md`](README.md): la app, operación y deploy.
- [`docs/capacity/`](docs/capacity/README.md): capacidad vigente, test de capacidad y registro `CAP-NNN`.
- [`docs/CAPACITY_TEST_PLAN.md`](docs/CAPACITY_TEST_PLAN.md): diseño del test de capacidad.
- [`docs/archive/`](docs/archive/README.md): mediciones anteriores con el loadtest (EXP-001 a 013).
- [`docs/SERVER_HARDWARE.md`](docs/SERVER_HARDWARE.md): elección de placas, CPU y PCIe.
- [`docs/TELEFONIA_ANURA.md`](docs/TELEFONIA_ANURA.md): telefonía (Anura + Asterisk + LiveKit).
- [`docs/TTS_FINETUNE.md`](docs/TTS_FINETUNE.md): fine-tuning de una voz de Qwen3-TTS (procedimiento, criterios, trampas).
