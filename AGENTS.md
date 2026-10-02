# AGENTS.md — infraestructura

Agente de voz telefónico con **inferencia propia**: LLM, STT y TTS corren
sobre GPUs locales, sin proveedores externos. Este archivo describe la
infraestructura. La app (plataforma multi-cliente: clientes, tiers, agentes versionados en JSON,
números; API `/api/v1`, UI React en `web/` y worker de voz) está en [`README.md`](README.md).

## Pedidos frecuentes

| Pedido | Qué hacer |
|---|---|
| "Voy a correr el test de capacidad (con <config>), registralo" | Seguir [`docs/capacity/README.md`](docs/capacity/README.md): aplicar los límites de GPU, `make capacity-monitor PERFIL=<perfil>` en el server antes de la carga y avisar; el usuario corre `make capacity` en la laptop y pasa el run empaquetado; `make capacity-monitor-stop`, `make capacity-analyze` y registrar `docs/capacity/CAP-NNN-<slug>/`. |
| "Entrená / reentrená la voz <voz> del TTS" | Delegar al agente [`tts-finetune`](.claude/agents/tts-finetune.md), que sigue [`docs/TTS_FINETUNE.md`](docs/TTS_FINETUNE.md). Entrenar el 1.7B necesita parar `vllm-tts`: confirmar antes. |
| "Probá <modelo o reparto de GPU>" | Override `docker-compose.<nombre>.yml` y confirmar antes de reiniciar servicios; después, el mismo procedimiento. |
| "Creá un cliente / tier / agente / número" | Por la UI o la API (`/api/v1`, OpenAPI en `/api/v1/docs`), no a mano en la base. Números: se cargan al inventario, se asignan a un cliente (tope `max_phone_numbers` del tier) y se rutean a un agente; después de cargar o borrar, `make livekit-sip`. |
| "Seguí con WhatsApp" / "probá el webhook de WhatsApp" | Seguir [`docs/WHATSAPP_PLAN.md`](docs/WHATSAPP_PLAN.md): fases 0 y 1, y la 2 (Embedded Signup, 5.3, con sus pasos de deploy pendientes). Código en `app/whatsapp/`, variables `WA_*` en `.env` (diff enmascarado antes de reiniciar). |
| "Cambiá la landing" / "probá la demo de la landing" | Seguir [`docs/LANDING.md`](docs/LANDING.md): Astro + Tailwind en `landing/` (`npm run dev`), demo por `/api/v1/demo`. Todo cambio visual o de texto sigue [`docs/DESIGN_GUIDELINE.md`](docs/DESIGN_GUIDELINE.md) (tokens, componentes, voz). Los agentes de la demo son los del cliente `landing`: editarlos por la UI o la API. |
| "Evaluá la calidad del LLM <modelo>" / "compará modelos" | Seguir [`docs/eval/README.md`](docs/eval/README.md): `make eval-llm` (cliente simulado con `EVAL_LLM_API_KEY`, o `--cliente guion`), `make eval-llm-juez`, y registrar `docs/eval/EVAL-NNN-<slug>/`. Otro modelo local va con su override, como arriba. |

## Servicios (`docker-compose.yml`)

`make up` levanta todo. Por partes: `make up-agent` (db + migrate + app + agent), `make up-inference`
(los 3 de inferencia), `make up-nginx` (proxy) y `make up-pbx` (Asterisk). `make help` lista el resto.

| Servicio | Qué es | Imagen | Puerto host | GPU |
|---|---|---|---|---|
| `db` | PostgreSQL 16 | postgres:16-alpine | 127.0.0.1:5432 | — |
| `migrate` | Una vez antes de `app`/`agent`: `alembic upgrade head` + seed idempotente (`app/cli.py`) | build | — | — |
| `app` | FastAPI: API `/api/v1` y la UI (`web/dist`); despacha el agente a una room de LiveKit | build | 8011 | — |
| `agent` | Worker de LiveKit Agents (STT → LLM → TTS); sale a LiveKit Cloud | build | — | — |
| `vllm-llm` | LLM `RedHatAI/Qwen3.5-9B-quantized.w4a16` (Qwen3.5-9B en 4 bits) | vllm/vllm-openai:latest | 127.0.0.1:8101 | 0 |
| `stt-parakeet` | STT `nvidia/parakeet-tdt-0.6b-v3`, servidor propio (`stt/server.py`) | build | 127.0.0.1:8102 | 1 |
| `vllm-tts` | TTS Qwen3-TTS 1.7B-Base con fine-tuning, 41 voces en un checkpoint (`multi41`) | vllm/vllm-omni:v0.28.0 (fijada) | 127.0.0.1:8103 | 1 |
| `proxy` | Entrada pública por IP fija; nginx rutea `/llm`, `/stt` y `/tts` | nginx:alpine | 0.0.0.0:8100 (`PROXY_PORT`) | — |
| `asterisk` | Puente SIP Anura ↔ LiveKit (`network_mode: host`) | build | — | — |
| `tunnel` | Cloudflare Tunnel de la demo de la landing (`docker-compose.tunnel.yml`, `make up-tunnel`): `api.` → `/api/v1/demo/*`, `rtc.` → LiveKit, `wa.` → `/wa/webhook`, `app.` → todo `app` (dashboard; pendiente de crear) | cloudflare/cloudflared | — | — |
| `livekit`, `livekit-sip`, `livekit-redis` | LiveKit propio (desarrollo, `docker-compose.livekit.yml`), en lugar de Cloud | livekit-server v1.13.7, sip v1.17.0 | 7880, 7881, 7882/udp, 5060 | — |

- La inferencia habla API OpenAI y exige `Authorization: Bearer $VLLM_API_KEY`. Los puertos 810x son solo para debug local.
- Modo remoto: `app` + `agent` pueden correr en otra PC (`make up-agent`) contra la inferencia por el proxy: `http://181.104.113.28:8100/{llm,stt,tts}/v1` (IP fija `PUBLIC_HOST`; el router redirige 8100 a 192.168.1.99). Así se corre el loadtest. Es HTTP plano: la auth es solo `VLLM_API_KEY`.

## Hosts

- **Este server, en camino a producción** (2-oct-2026, [`docs/PRODUCCION.md`](docs/PRODUCCION.md)): IP fija, inferencia y base locales.
  - Hardware: Ryzen 7 5700X, 64 GB, ASRock B550M Pro SE, **2 × RTX 3090 24 GB**.
    - GPU 0: `04:00.0`, slot del chipset, PCIe gen3 x4.
    - GPU 1: `07:00.0`, slot de la CPU, gen4 x16. También dibuja el escritorio.
    - La 5060 Ti (CAP-002, CAP-004) fue una prueba: no se usa.
  - Corren contenedores de otros proyectos (Dify, sim-poc): no tocarlos; sacarlos del host es un pendiente de producción.
  - **Límites de las 3090:** sin tope, dos 3090 apagaron el server por un pico de consumo (25-sep-2026).
    - 280 W, núcleo ≤ 1800 MHz y memoria 9501 MHz, en cada arranque, por `atentina-gpu-limits.service` (`deploy/gpu-limits.sh`, instalado el 2-oct-2026). El chequeo de `scripts/ops/healthcheck.sh` avisa si faltan.
    - El tope de potencia cambia el `hw_id` del test de capacidad.
  - **Arranque:** `atentina-stack.service` (`deploy/boot.sh`) levanta el compose sin build, el túnel y los trunks SIP, y calienta el TTS.
  - **Backup** diario (03:30) y **chequeo** cada 2 min, por cron del usuario (`scripts/ops/`). Logs en `~/atentina-ops/`, backups en `~/atentina-backups/`.

## Reparto de GPU vigente (CAP-001, desde el 2-oct-2026)

Compose principal, sin override (`COMPOSE_FILE=docker-compose.yml:docker-compose.livekit.yml`). Los valores de capacidad de la 5060 Ti quedaron comentados en `.env`.

| GPU | Servicios | Memoria |
|---|---|---|
| 0: 3090 | `vllm-llm` solo | 0.90, 128 secuencias (~21 GB usados) |
| 1: 3090 | `vllm-tts` + `stt-parakeet` + escritorio | TTS 0.4 (talker ~9,6 GB + Code2Wav ~3,5 GB), 128 por etapa; STT ~1,6 GB (~15,7 GB usados) |

- **Motor por defecto:** `classic` (`WORKFLOW_ID=demo_booking_classic`).
- **Capacidad medida** ([CAP-001](docs/capacity/CAP-001-2x3090-pl280-classic/), con los topes):
  - ~20 llamadas con p95 ≤ 2,4 s y **~32 con p95 ≤ 3 s** (codo); con ~32 se saturan las dos GPUs.
  - Con 64, además la CPU del host (agente, ~0,12 cores por llamada), y el servicio colapsa.
  - Potencia de las dos GPUs: 559 W de pico.
- **TTS en la 3090:** el primer pedido después de arrancar tardó 0,8 s (en la 5060 Ti, más de 20 s).
- Con sobrecarga (~110 llamadas, CAP-002) el talker del TTS se cayó y no se recupera solo: recrear `vllm-tts` y calentarlo.
- **Override de la 5060 Ti** (`docker-compose.gpu-5060.yml`): para repetir la prueba; ver CAP-002 y CAP-004.

El TTS sirve el checkpoint fine-tuneado de `TTS_FT_CKPT` (default `multi41`, lr 2e-6, época 2)
con el nombre `qwen3-tts-ft`. Tiene 41 voces de OpenSLR 61 (28 mujeres, 13 hombres) con nombres
argentinos (`sofia`, `martin`, ...). El catálogo, con género, WER y car/s por voz, es
[`tts/finetune/voces.tsv`](tts/finetune/voces.tsv).

La voz va en `voice` en cada pedido. El agente usa, en orden:
1. la elegida en la UI para la llamada;
2. `agent.voice` de la definición del agente;
3. `VLLM_TTS_VOICE`.

Ver [`docs/TTS_FINETUNE.md`](docs/TTS_FINETUNE.md).

## Reglas y trampas

- **TTS no comparte GPU con el LLM ni con otra réplica** (EXP-001 a 004). Con el STT Parakeet sí se probó: hasta ~48 llamadas el STT no se resiente, y con 64 sube a ~0,5–0,6 s (EXP-013). Escalar TTS es sumar GPUs.
- **TTS en la 5060 Ti (prueba, no vigente):** el primer pedido tarda más de 20 s (kernels de Blackwell) y en 8 GB entra justo; cambiar sus fracciones rompe el arranque. Ver `docker-compose.gpu-5060.yml` y CAP-002.
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
- **Loadtest y motor por workflow:** `run.py` crea las llamadas con `POST /api/v1/calls {"loadtest": true}` (`--workflow` = slug del agente, `--voice`), autenticado con `VAAS_API_KEY` (API key del cliente `interno`, sin límites: `make api-key CLIENT=interno NAME=loadtest`). Con ese flag el agente no corta al completar el workflow, así cada llamada dura los `--turns` pedidos, como en EXP-001 a 008. `ttft_s` del CSV es ahora el LLM hasta el primer texto de la respuesta, no el TTFT de vLLM: ver `SERVER_COLUMNS` en `run.py`.
- **LiveKit propio (desarrollo):** con `COMPOSE_FILE` en `.env`, todos los targets usan `docker-compose.livekit.yml`. Las `LIVEKIT_*` de `.env` son las de este host; las de Cloud quedan en `LIVEKIT_CLOUD_*`. Ver `docs/TELEFONIA_ANURA.md`, sección 7.
  - Su Redis no persiste: cada reinicio del host borra los trunks SIP y la dispatch rule, y las entrantes vuelven con 486 `flood` en `livekit-sip` (26-sep-2026). Por eso `make up` termina con `make livekit-sip` cuando el LiveKit es propio. Si se levantó de otra forma, correrlo a mano.
  - `LIVEKIT_SIP_TRUNK_ID` va vacío con LiveKit propio: el ID del trunk saliente cambia cada vez y el agente lo busca por nombre (`anura-asterisk-outbound`).
- **Capacidad por motor en `.env`:** `VLLM_LLM_MAX_NUM_SEQS` (también fija el tamaño de CUDA graph), `VLLM_LLM_GPU_MEMORY_UTILIZATION`, `STT_MAX_BATCH`, `STT_MAX_BATCH_SECONDS`, `VLLM_TTS_GPU_MEMORY_UTILIZATION` y `VLLM_TTS_MAX_NUM_SEQS` (las dos etapas, por `--stage-overrides`). Los defaults del compose son el reparto de 2 × 3090 (CAP-001), el vigente; los valores de la 5060 Ti quedaron comentados en `.env`. Se aplican con `make up-inference` (parando antes los tres: el LLM nuevo no entra en la GPU 0 si el TTS viejo sigue ahí).
- **Base y agentes:** el esquema lo manejan las migraciones (`migrations/`, `make migrate`), no `create_all`. Los agentes viven en la base, versionados (cada cambio es una versión nueva; la conversación guarda la suya); `app/agents/templates/*.json` son las plantillas (seed, eval, tests). Editar una plantilla no cambia los agentes ya creados.
- **Límites por tier:** admisión con lock de fila del cliente (`services/quota.py`); una llamada activa de hace más de `CALL_MAX_DURATION_SECONDS` + 10 min se considera colgada y no ocupa lugar. El loadtest y la de prueba ocupan lugar pero no consumen minutos: el cliente `interno` no tiene límites.
- **Auth:** `AUTH_SECRET` es obligatoria (sin ella `app` no arranca). La UI usa cookie de sesión; scripts y sistemas, API keys (`Authorization: Bearer vaas_...`).
- **Demo de la landing:** `/api/v1/demo` es la única parte pública de la API (por el túnel; el 8011 no se publica en el router). Sin `TURNSTILE_SECRET_KEY` responde 503. Ocupa lugar del tier `Landing` (3 simultáneas) y tiene cupo de `DEMO_DAILY_MINUTES` por día. Para que entren navegadores de internet, LiveKit anuncia la IP pública (`LIVEKIT_NODE_IP`) y el router reenvía UDP 7882 y TCP 7881. Ver [`docs/LANDING.md`](docs/LANDING.md).
- **Webhook de WhatsApp:** `/wa/webhook` (GET de verificación y POST con firma `X-Hub-Signature-256`) sale por el mismo túnel que la demo: `wa.atentina.com.ar`, path `^/wa/webhook` → `localhost:8011`, sin 443 en el router. Ver [`docs/WHATSAPP_PLAN.md`](docs/WHATSAPP_PLAN.md).
- **Dashboard público: `app.atentina.com.ar`** (túnel, todo el host → `localhost:8011`, sin Cloudflare Access; la ruta la crea el usuario). La app se defiende sola:
  - sesión revocable (`users.session_version`), límites de login por IP real (`CF-Connecting-IP` solo desde `TRUSTED_PROXY_CIDRS`), CSRF por `Origin`, CSP con hash y SDK de Facebook, HSTS, docs solo admin;
  - código en `app/api/http.py` y `app/api/deps.py`; detalle en `docs/ARQUITECTURA.md`, "Autenticación y permisos".
  - No relajar la CSP, `APP_ORIGINS` ni `TRUSTED_PROXY_CIDRS` sin medir: con `CSP_REPORT_ONLY=true` se prueba sin romper.
  - Embedded Signup de WhatsApp (fase 2) solo anda por ese dominio: ver [`docs/WHATSAPP_PLAN.md`](docs/WHATSAPP_PLAN.md), 5.3.
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
- **Benchmark de GPU:** `make gpubench` (`scripts/gpubench/`) mide memoria y PCIe host↔GPU como % de la especificación, para comparar GPUs y enlaces. Con la GPU sin carga; procedimiento y mediciones en [`docs/gpubench/`](docs/gpubench/README.md).
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
- [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md): arquitectura y detalles técnicos (componentes, modelo de datos, flujos de llamada, límites, auth, API, frontend).
- [`docs/GUIA_UI.md`](docs/GUIA_UI.md): cómo hacer cada acción en la UI (tiers, clientes, agentes, números, usuarios, API keys, llamadas).
- [`docs/capacity/`](docs/capacity/README.md): capacidad vigente, test de capacidad y registro `CAP-NNN`.
- [`docs/CAPACITY_TEST_PLAN.md`](docs/CAPACITY_TEST_PLAN.md): diseño del test de capacidad.
- [`docs/EVAL_LLM_PLAN.md`](docs/EVAL_LLM_PLAN.md) y [`docs/eval/`](docs/eval/README.md): eval de calidad del LLM por tipo de agente y de cliente, y registro `EVAL-NNN`.
- [`docs/LANDING.md`](docs/LANDING.md): landing (Astro + Tailwind en `landing/`, `render.yaml`), demo por `/api/v1/demo` con su control de abuso, túnel, dominios y DNS (Render + Cloudflare).
- [`docs/DESIGN_GUIDELINE.md`](docs/DESIGN_GUIDELINE.md): guía de diseño de la marca, con base en la landing (color y acento por vertical, tipografía, layout, componentes y patrones, estados, voz). Leerla antes de agregar o cambiar una pantalla de la landing.
- [`docs/WHATSAPP_PLAN.md`](docs/WHATSAPP_PLAN.md): plan para WhatsApp en el mismo agente (Cloud API directo, registro del número de Anura por voz, Embedded Signup, costos de Meta). Fases 0, 1 y audios en producción; fase 2 (Embedded Signup) implementada, sin desplegar.
- [`docs/archive/`](docs/archive/README.md): mediciones anteriores con el loadtest (EXP-001 a 013).
- [`docs/PRODUCCION.md`](docs/PRODUCCION.md): plan de producción en este server, hallazgos, checklist y redundancia.
- [`docs/SERVER_HARDWARE.md`](docs/SERVER_HARDWARE.md): elección de placas, CPU y PCIe.
- [`docs/TELEFONIA_ANURA.md`](docs/TELEFONIA_ANURA.md): telefonía (Anura + Asterisk + LiveKit).
- [`docs/TTS_FINETUNE.md`](docs/TTS_FINETUNE.md): fine-tuning de una voz de Qwen3-TTS (procedimiento, criterios, trampas).
