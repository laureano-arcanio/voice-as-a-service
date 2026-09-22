# AGENTS.md — infraestructura

Agente de voz telefónico con **inferencia propia**: LLM, STT y TTS corren en
vLLM sobre GPUs locales, sin proveedores externos. Este archivo describe la
infraestructura. La app (flujo de la llamada, scoring, dashboard) está en
[`README.md`](README.md).

## Servicios (`docker-compose.yml`)

| Servicio | Qué es | Imagen | Puerto host | GPU | Perfil |
|---|---|---|---|---|---|
| `db` | MySQL 8 | mysql:8.0 | 3306 | — | — |
| `app` | FastAPI: dashboard y API; despacha el agente a una room de LiveKit | build | 8011 | — | — |
| `agent` | Worker de LiveKit Agents (STT → LLM → TTS); sale a LiveKit Cloud | build | — | — | — |
| `vllm-llm` | `Qwen/Qwen3.5-4B` | vllm/vllm-openai:latest | 127.0.0.1:8101 | 1 | — |
| `vllm-stt` | `Qwen/Qwen3-ASR-1.7B` | qwenllm/qwen3-asr:latest | 127.0.0.1:8102 | 1 | — |
| `vllm-tts` | `Qwen/Qwen3-TTS-12Hz-1.7B-Base`, voz clonada `sofia_ar` | vllm/vllm-omni:v0.28.0 (fijada) | 127.0.0.1:8103 | 0 | — |
| `vllm-tts-2` | Segunda réplica de TTS; solo con GPU propia | ídem | 127.0.0.1:8104 | 0 (cambiar) | `tts2` |
| `stt-parakeet`, `stt-whisper`, `stt-moonshine` | STT candidatos para evaluar | build / vllm-openai | 127.0.0.1:8105–8107 | `STT_EVAL_GPU` (0) | `stt-eval` |
| `proxy` + `ngrok` | Único túnel público; nginx rutea `/llm`, `/stt` y `/tts` a cada vLLM | nginx:alpine, ngrok | — | — | `ngrok` |
| `asterisk` | Puente SIP Anura ↔ LiveKit (`network_mode: host`) | build | — | — | `pbx` |

- Los vLLM hablan API OpenAI y exigen `Authorization: Bearer $VLLM_API_KEY`. Los puertos 810x son solo para debug local.
- `make up` no levanta los servicios con perfil.
- Modo remoto: `app` + `agent` pueden correr en otra PC (`make up-remote`) contra los vLLM por ngrok. Así se corre el loadtest.

## Hosts

- **Server de validación (este):**
  - Hardware: Ryzen 7 5700X, 64 GB, 2 × RTX 3090 24 GB.
  - La GPU 1 también dibuja el escritorio.
  - Corren contenedores de otros proyectos: no tocarlos.
  - Sirve solo para validar; no es producción.
- **smartcron:** deploy de la app (ver README, "Deploy").
- **Producción:** hardware en definición. Ver [`docs/LOADTEST_CAPACITY.md`](docs/LOADTEST_CAPACITY.md).

## Reparto de GPU vigente (EXP-003)

| GPU | Servicios | `--gpu-memory-utilization` |
|---|---|---|
| 0 | `vllm-tts` sola | 0.4 |
| 1 | `vllm-llm` + `vllm-stt` + escritorio | 0.55 + 0.30 |

## Reglas y trampas

- **TTS nunca comparte GPU**, ni con STT ni con otra réplica: satura la GPU sola (EXP-001 a 004). Escalar TTS es sumar GPUs.
- **`--gpu-memory-utilization`** es una fracción de la memoria **total** de la GPU. Los que comparten GPU tienen que sumar menos de ~0.95, descontando el escritorio.
- **Arranque de servicios que comparten GPU:** no pueden arrancar a la vez, porque compiten por la memoria libre. Por eso `depends_on` los encadena (`vllm-stt` espera a `vllm-llm`).
- **Perfil `stt-eval`:** usa la GPU 0 por defecto y compite con TTS. Apagarlo (`make stt-eval-down`) antes de medir capacidad.
- **Flags del LLM:** `--max-cudagraph-capture-size=32` evita que su VRAM crezca con el tráfico, y `--max-num-seqs=32` es por el cache Mamba de Qwen3.5. Ver los comentarios del compose.
- **vLLM-Omni:** fijada en v0.28.0, porque `latest` no arranca. Deja `num_requests_running` en 1 sin tráfico, así que la actividad se detecta por los contadores de tokens.
- **Voz clonada:** vive en el volumen `vllm_tts_speakers`. Si se pierde el volumen, hay que volver a subirla (README, "Voz clonada").
- **Comentarios del compose:** explican el porqué medido de cada flag. Mantenerlos al día al cambiar valores.

## Experimentos de capacidad

Todo cambio de modelo (STT, TTS o LLM), de reparto de GPU o de flags de memoria
se mide con el loadtest y se registra en [`docs/experiments/`](docs/experiments/README.md),
donde está el procedimiento y el índice comparativo.

- **Monitoreo:** `scripts/loadtest/monitor/`
  - `sampler.py`: muestrea a 1 Hz y guarda `meta.json` con la config efectiva.
  - `timeline.py`: ubica las fases del loadtest.
  - `analyze.py`: reporte completo, o tablas markdown con `--md`.
- **Overrides:** cada experimento usa un override `docker-compose.<nombre>.yml` (ej. `docker-compose.sim16gb.yml`), no el compose principal.
- **Volver a la config vigente:** `docker compose --profile ngrok up -d vllm-llm vllm-stt vllm-tts proxy ngrok`, sin el `-f` extra.
- **Runs crudos:** `run_*` no se versionan.

## Cómo trabajar en este server

- Puede haber otras sesiones de agente trabajando en paralelo en el repo y en los contenedores. Mirar `git status` y `docker ps` antes de cambiar algo, y no revertir cambios ajenos.
- No reiniciar servicios ni lanzar pruebas que nadie pidió: el stack se usa en vivo.
- Docs y comentarios en español, breves y con datos medidos.

## Documentación

- [`README.md`](README.md): la app, operación y deploy.
- [`docs/LOADTEST_CAPACITY.md`](docs/LOADTEST_CAPACITY.md): conclusiones de capacidad y arquitectura candidata.
- [`docs/experiments/`](docs/experiments/README.md): registro de experimentos.
- [`docs/SERVER_HARDWARE.md`](docs/SERVER_HARDWARE.md): elección de placas, CPU y PCIe.
- [`docs/TELEFONIA_ANURA.md`](docs/TELEFONIA_ANURA.md): telefonía (Anura + Asterisk + LiveKit).
