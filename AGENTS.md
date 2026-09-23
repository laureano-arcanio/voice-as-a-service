# AGENTS.md — infraestructura

Agente de voz telefónico con **inferencia propia**: LLM, STT y TTS corren
sobre GPUs locales, sin proveedores externos. Este archivo describe la
infraestructura. La app (flujo de la llamada, scoring, dashboard) está en
[`README.md`](README.md).

## Pedidos frecuentes

| Pedido | Qué hacer |
|---|---|
| "Voy a correr el loadtest (con <config>), registralo" | Seguir [Registrar un loadtest](docs/experiments/README.md#registrar-un-loadtest). Arrancar el monitoreo antes del warm-up y avisar. Cuando el usuario diga que terminó: cortarlo, ubicar las tandas, analizar y crear `docs/experiments/EXP-NNN-<slug>/`. |
| "Registrá el último run" | El mismo procedimiento desde el paso 4, con el `scripts/loadtest/monitor/run_*` más reciente. |
| "Entrená / reentrená la voz <voz> del TTS" | Delegar al agente [`tts-finetune`](.claude/agents/tts-finetune.md), que sigue [`docs/TTS_FINETUNE.md`](docs/TTS_FINETUNE.md). Entrenar el 1.7B necesita parar `vllm-tts`: confirmar antes. |
| "Probá <modelo o reparto de GPU>" | Override `docker-compose.<nombre>.yml` y confirmar antes de reiniciar servicios; después, el mismo procedimiento. |

## Servicios (`docker-compose.yml`)

`make up` levanta todo. Por partes: `make up-agent` (db + app + agent), `make up-inference`
(los 3 de inferencia), `make up-nginx` (proxy) y `make up-pbx` (Asterisk). `make help` lista el resto.

| Servicio | Qué es | Imagen | Puerto host | GPU |
|---|---|---|---|---|
| `db` | MySQL 8 | mysql:8.0 | 127.0.0.1:3306 | — |
| `app` | FastAPI: dashboard y API; despacha el agente a una room de LiveKit | build | 8011 | — |
| `agent` | Worker de LiveKit Agents (STT → LLM → TTS); sale a LiveKit Cloud | build | — | — |
| `vllm-llm` | LLM `Qwen/Qwen3.5-4B` | vllm/vllm-openai:latest | 127.0.0.1:8101 | 1 |
| `stt-parakeet` | STT `nvidia/parakeet-tdt-0.6b-v3`, servidor propio (`stt/server.py`) | build | 127.0.0.1:8102 | 1 |
| `vllm-tts` | TTS Qwen3-TTS 1.7B-Base con fine-tuning, voz `arf_03034` | vllm/vllm-omni:v0.28.0 (fijada) | 127.0.0.1:8103 | 0 |
| `proxy` | Entrada pública por IP fija; nginx rutea `/llm`, `/stt` y `/tts` | nginx:alpine | 0.0.0.0:8100 (`PROXY_PORT`) | — |
| `asterisk` | Puente SIP Anura ↔ LiveKit (`network_mode: host`) | build | — | — |

- La inferencia habla API OpenAI y exige `Authorization: Bearer $VLLM_API_KEY`. Los puertos 810x son solo para debug local.
- Modo remoto: `app` + `agent` pueden correr en otra PC (`make up-agent`) contra la inferencia por el proxy: `http://181.104.113.28:8100/{llm,stt,tts}/v1` (IP fija `PUBLIC_HOST`; el router redirige 8100 a 192.168.1.99). Así se corre el loadtest. Es HTTP plano: la auth es solo `VLLM_API_KEY`.

## Hosts

- **Server de validación (este):**
  - Hardware: Ryzen 7 5700X, 64 GB, 2 × RTX 3090 24 GB.
  - La GPU 1 también dibuja el escritorio.
  - Corren contenedores de otros proyectos: no tocarlos.
  - Sirve solo para validar; no es producción.
- **smartcron:** deploy de la app (ver README, "Deploy").
- **Producción:** hardware en definición. Ver [`docs/LOADTEST_CAPACITY.md`](docs/LOADTEST_CAPACITY.md).

## Reparto de GPU vigente (EXP-003 y EXP-008)

| GPU | Servicios | Memoria |
|---|---|---|
| 0 | `vllm-tts` sola | `--gpu-memory-utilization` 0.4 |
| 1 | `vllm-llm` + `stt-parakeet` + escritorio | 0.55 + ~1,6 GB + ~1,4 GB |

El TTS sirve el checkpoint fine-tuneado de `TTS_FT_CKPT` (default `arf_03034`, lr 2e-6,
época 5). Ver [`docs/TTS_FINETUNE.md`](docs/TTS_FINETUNE.md).

## Reglas y trampas

- **TTS nunca comparte GPU**, ni con STT ni con otra réplica: satura la GPU sola (EXP-001 a 004). Escalar TTS es sumar GPUs.
- **`--gpu-memory-utilization`** es una fracción de la memoria **total** de la GPU. Los que comparten GPU tienen que sumar menos de ~0.95, descontando el escritorio.
- **Arranque de servicios que comparten GPU:** no pueden arrancar a la vez, porque compiten por la memoria libre. Por eso `depends_on` los encadena (`stt-parakeet` espera a `vllm-llm`).
- **Servicios descartados (sep-2026):** Qwen3-ASR (`vllm-stt`), Whisper Turbo, CosyVoice 3 y la segunda réplica de TTS salieron del compose; quedan en el historial de git y en `docs/experiments/`. Para probar uno de nuevo, override `docker-compose.<nombre>.yml`.
- **Servidor propio de STT (`stt/server.py`, Parakeet):** expone `/metrics` con nombres de vLLM para que lo lea el sampler. Batching dinámico: junta lo que llega mientras la GPU trabaja, hasta `STT_MAX_BATCH` (8). Un pedido solo tarda lo mismo que sin batching (~60 ms). Con 16 clientes en paralelo rinde ×4,7 (76 contra 16 req/s) y la p50 baja de 996 a 204 ms. Batch 16 da ×5,4 a costa de ~150 ms por batch.
- **Flags del LLM:** `--max-cudagraph-capture-size=32` evita que su VRAM crezca con el tráfico, y `--max-num-seqs=32` es por el cache Mamba de Qwen3.5. Ver los comentarios del compose.
- **vLLM-Omni:** fijada en v0.28.0, porque `latest` no arranca. Deja `num_requests_running` en 1 sin tráfico, así que la actividad se detecta por los contadores de tokens.
- **Voz del TTS:** está dentro del checkpoint fine-tuneado (`tts/finetune/work/`, no versionado), no en un volumen. Si se pierde `tts/finetune/work/`, hay que reentrenar. El volumen `vllm_tts_speakers` tiene la voz clonada anterior (`sofia_ar`, para el checkpoint Base) y ya no se monta.
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
- **Volver a la config vigente:** `make up-inference`, sin el `-f` extra.
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
