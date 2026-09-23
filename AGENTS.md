# AGENTS.md — infraestructura

Agente de voz telefónico con **inferencia propia**: LLM, STT y TTS corren en
vLLM sobre GPUs locales, sin proveedores externos. Este archivo describe la
infraestructura. La app (flujo de la llamada, scoring, dashboard) está en
[`README.md`](README.md).

## Pedidos frecuentes

| Pedido | Qué hacer |
|---|---|
| "Voy a correr el loadtest (con <config>), registralo" | Seguir [Registrar un loadtest](docs/experiments/README.md#registrar-un-loadtest). Arrancar el monitoreo antes del warm-up y avisar. Cuando el usuario diga que terminó: cortarlo, ubicar las tandas, analizar y crear `docs/experiments/EXP-NNN-<slug>/`. |
| "Registrá el último run" | El mismo procedimiento desde el paso 3, con el `scripts/loadtest/monitor/run_*` más reciente. |
| "Entrená / reentrená la voz <voz> del TTS" | Delegar al agente [`tts-finetune`](.claude/agents/tts-finetune.md), que sigue [`docs/TTS_FINETUNE.md`](docs/TTS_FINETUNE.md). Entrenar el 1.7B necesita parar `vllm-tts`: confirmar antes. |
| "Probá <modelo o reparto de GPU>" | Override `docker-compose.<nombre>.yml` y confirmar antes de reiniciar servicios; después, el mismo procedimiento. Para STT candidatos: `make servers-<stt>` (ver [STT candidatos](docs/experiments/README.md#stt-candidatos-parakeet-whisper)). |

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
| `stt-parakeet`, `stt-whisper` | STT candidatos para evaluar | build | 127.0.0.1:8105–8106 | `STT_EVAL_GPU` (0); 1 con `docker-compose.stt-candidates.yml` | `stt-eval` |
| `tts-cosyvoice` | CosyVoice 3 para generar el corpus de eval de STT (no producción) | vllm/vllm-omni:v0.28.0 + `s3tokenizer` | 127.0.0.1:8107 | `TTS_EVAL_GPU` (0) | `tts-eval` |
| `proxy` | Entrada pública por IP fija; nginx rutea `/llm`, `/stt`, `/tts` y `/stt-<candidato>` | nginx:alpine | 0.0.0.0:8100 (`PROXY_PORT`) | — | `proxy` |
| `asterisk` | Puente SIP Anura ↔ LiveKit (`network_mode: host`) | build | — | — | `pbx` |

- Los vLLM hablan API OpenAI y exigen `Authorization: Bearer $VLLM_API_KEY`. Los puertos 810x son solo para debug local.
- `make up` no levanta los servicios con perfil.
- Modo remoto: `app` + `agent` pueden correr en otra PC (`make up-remote`) contra los vLLM por el proxy: `http://181.104.113.28:8100/{llm,stt,tts}/v1` (IP fija `PUBLIC_HOST`; el router redirige 8100 a 192.168.1.99). Así se corre el loadtest. Es HTTP plano: la auth es solo `VLLM_API_KEY`.

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

**En uso en este server (EXP-008):** STT Parakeet con batching en lugar de `vllm-stt`, misma GPU 1 (~1,6 GB). Se levanta con `docker-compose.parakeet.yml`, y el `.env` apunta el agente a `stt-parakeet`. TTS y LLM, como en EXP-003.

**TTS con voz fine-tuneada (sep-2026):** `vllm-tts` puede servir un checkpoint propio (voz `arf_03034`) con `docker-compose.tts-ft.yml`, encima del de Parakeet. Ver [`docs/TTS_FINETUNE.md`](docs/TTS_FINETUNE.md).

## Reglas y trampas

- **TTS nunca comparte GPU**, ni con STT ni con otra réplica: satura la GPU sola (EXP-001 a 004). Escalar TTS es sumar GPUs.
- **`--gpu-memory-utilization`** es una fracción de la memoria **total** de la GPU. Los que comparten GPU tienen que sumar menos de ~0.95, descontando el escritorio.
- **Arranque de servicios que comparten GPU:** no pueden arrancar a la vez, porque compiten por la memoria libre. Por eso `depends_on` los encadena (`vllm-stt` espera a `vllm-llm`).
- **Perfil `tts-eval` (CosyVoice 3):** genera el corpus de datos dictados
  (`make stt-corpus-entities`, ver README). Va a la GPU 0, así que **no convive con
  `vllm-tts`**: hay que parar Qwen3-TTS mientras dura (`docker compose stop vllm-tts`) y
  levantarlo después. Con la GPU para él solo aguanta 4 pedidos en paralelo: con 8 se cuelga
  (deja de responder hasta `/health`) y con 12 el cliente corta por timeout. La reserva de
  memoria está en `tts/cosyvoice3.yaml`, no en el compose. Apagarlo (`make tts-cosyvoice-down`)
  antes de medir capacidad.
- **Perfil `stt-eval`:** se levanta un candidato por vez, nunca los dos juntos (`make stt-eval-up STT=...` baja el otro). Usa la GPU 0 por defecto y compite con TTS. Apagarlo (`make stt-eval-down`) antes de medir capacidad. Para medir con el loadtest: `make servers-whisper` / `make servers-parakeet` (usan `docker-compose.stt-candidates.yml`, que pone el candidato en la GPU 1 en lugar de `vllm-stt`) y `make servers-qwen` para volver a la vigente.
- **Servidor propio de STT (`stt/server.py`, Parakeet):** expone `/metrics` con nombres de vLLM para que lo lea el sampler. Batching dinámico: junta lo que llega mientras la GPU trabaja, hasta `STT_MAX_BATCH` (8). Un pedido solo tarda lo mismo que sin batching (~60 ms). Con 16 clientes en paralelo rinde ×4,7 (76 contra 16 req/s) y la p50 baja de 996 a 204 ms. Batch 16 da ×5,4 a costa de ~150 ms por batch.
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
- **Volver a la config vigente:** `docker compose --profile proxy up -d vllm-llm vllm-stt vllm-tts proxy`, sin el `-f` extra.
- **Runs crudos:** `run_*` no se versionan.

## Cómo trabajar en este server

- Puede haber otras sesiones de agente trabajando en paralelo en el repo y en los contenedores. Mirar `git status` y `docker ps` antes de cambiar algo, y no revertir cambios ajenos.
- No reiniciar servicios ni lanzar pruebas que nadie pidió: el stack se usa en vivo.
- Archivos temporales (muestras de audio, scripts de prueba, descargas, clones de repos): siempre en `scratch/` dentro del repo (está en `.gitignore`), nunca en `/tmp` ni fuera del repo, para que el usuario pueda abrirlos.
- Docs y comentarios en español, breves y con datos medidos.

## Documentación

- [`README.md`](README.md): la app, operación y deploy.
- [`docs/LOADTEST_CAPACITY.md`](docs/LOADTEST_CAPACITY.md): conclusiones de capacidad y arquitectura candidata.
- [`docs/experiments/`](docs/experiments/README.md): registro de experimentos.
- [`docs/SERVER_HARDWARE.md`](docs/SERVER_HARDWARE.md): elección de placas, CPU y PCIe.
- [`docs/TELEFONIA_ANURA.md`](docs/TELEFONIA_ANURA.md): telefonía (Anura + Asterisk + LiveKit).
- [`docs/TTS_FINETUNE.md`](docs/TTS_FINETUNE.md): fine-tuning de una voz de Qwen3-TTS (procedimiento, criterios, trampas).
