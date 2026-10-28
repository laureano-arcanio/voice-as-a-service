# Infraestructura

Agente de voz con inferencia propia: LLM, STT y TTS corren en las GPUs de este server, sin proveedores
externos. Este doc cubre el host, los servicios del compose, el reparto de GPU, la telefonía, el
arranque, los backups y la exposición a internet. Estado: en producción desde el 2-oct-2026.

Docs relacionados: [`TELEFONIA_ANURA.md`](TELEFONIA_ANURA.md) (Anura, Asterisk, LiveKit),
[`MIGRACION_SERVER.md`](MIGRACION_SERVER.md) (server nuevo, router, corte),
[`OBSERVABILIDAD.md`](OBSERVABILIDAD.md) (métricas y alertas), [`capacity/`](capacity/README.md)
(capacidad medida), [`TTS_FINETUNE.md`](TTS_FINETUNE.md) (voces).

## Host y hardware

| Pieza | Valor |
|---|---|
| CPU, RAM, placa | Ryzen 7 5700X (8/16), 64 GB, ASRock B550M Pro SE |
| GPU 0 | RTX 3090 24 GB, `04:00.0`, slot del chipset, PCIe Gen3 x4 |
| GPU 1 | RTX 3090 24 GB, `07:00.0`, slot de la CPU, Gen4 x16; también dibuja el escritorio |
| Red | IP fija pública `181.104.113.28`; LAN `192.168.1.99` (reserva DHCP) |
| Discos | NVMe de 465 GB en `/` (Docker) y NVMe de 1,8 TB en `/home` (repo, checkpoint, backups) |

- **Topes de las 3090 en cada arranque:** 280 W, núcleo ≤ 1800 MHz, memoria 9501 MHz y *persistence mode*
  (`deploy/gpu-limits.sh`, `atentina-gpu-limits.service`). Sin tope, dos 3090 apagaron el server por un
  pico de consumo. `scripts/ops/healthcheck.sh` avisa si faltan. El tope cambia el `hw_id` del test de capacidad.
- En el host corren contenedores de otros proyectos (Dify, sim-poc): no tocarlos. Compiten por CPU y RAM.
- La 5060 Ti de CAP-002 y CAP-004 fue una prueba: no se usa.

**Reglas de hardware (para un server nuevo):**
- Sin tensor parallel el PCIe casi no importa: por el bus viajan IDs de tokens y audio (~1 MB/s con 32
  llamadas). El ancho del slot solo cambia cuánto tarda en cargar el modelo. El LLM corre en Gen3 x4 y alcanza.
- En una B550 la topología es fija: un x16 de la CPU, un x4 del chipset (Gen3, con el enlace del chipset
  compartido) y un M.2 de la CPU que con adaptador sirve de segundo x4.
- Risers: alimentados por PCIe de 6 pines, nunca por SATA; los de minería por USB fallan en Gen4 (forzar
  Gen3 en la BIOS). Una 5060 Ti por riser x1 tuvo errores de enlace y el TTS se cayó (CAP-004). Verificar
  con `nvidia-smi -q | grep -i -A2 replay` y `sudo dmesg | grep -iE 'aer|xid'`.
- El orden de las GPUs sigue el bus PCI y el compose fija `device_ids` por índice: el escritorio tiene que
  quedar en el índice 1 (ver [`MIGRACION_SERVER.md`](MIGRACION_SERVER.md), 2).

## Servicios

`COMPOSE_FILE=docker-compose.yml:docker-compose.livekit.yml:docker-compose.gemma4-26b.yml` en `.env`: todos
los targets de `make` usan el compose principal, LiveKit propio y el LLM Gemma. `make up` levanta todo y
termina con `make livekit-sip`. Por partes: `make up-agent`, `make up-app`, `make up-inference`, `make up-stt`,
`make up-nginx`, `make up-pbx`, `make up-tools`, `make up-tunnel`, `make up-monitoring`, `make crm-up`.

| Servicio | Qué es | Imagen | Puerto host | GPU |
|---|---|---|---|---|
| `db` | PostgreSQL 16 (base de la app y base `crm`) | postgres:16-alpine | 127.0.0.1:5432 | — |
| `migrate` | Una vez antes de `app`/`agent`: `alembic upgrade head` + seed idempotente (`app/cli.py`) | build | — | — |
| `app` | FastAPI: API `/api/v1`, UI (`web/dist`), MCP, webhooks y loops de fondo | build | 8011 (todas las interfaces) | — |
| `agent` | Worker de LiveKit Agents (STT → LLM → TTS) contra el LiveKit propio | build | — | — |
| `crm` | CRM de ventas: API y UI ([`features/CRM.md`](features/CRM.md)) | build | 127.0.0.1:8030 | — |
| `tools-runner` | Sandbox de las herramientas de código: un proceso Deno por función, solo en la red interna `atentina-tools` | build (`tools-runner/`) | — | — |
| `tools-egress` | Única salida de `tools-runner`: Smokescreen, niega IPs privadas, loopback y metadata | build | — | — |
| `vllm-llm` | LLM `cyankiwi/gemma-4-26B-A4B-it-qat-AWQ-INT4`, parser de herramientas `gemma4` | vllm/vllm-openai:latest | 127.0.0.1:8101 | 0 |
| `stt-parakeet` | STT `nvidia/parakeet-tdt-0.6b-v3`, servidor propio (`stt/server.py`) | build | 127.0.0.1:8102 | 1 |
| `vllm-tts` | TTS Qwen3-TTS 1.7B-Base fine-tuneado, 41 voces (`multi41`) | vllm/vllm-omni:v0.28.0 | 127.0.0.1:8103 | 1 |
| `proxy` | nginx que rutea `/llm`, `/stt` y `/tts` (modo remoto y loadtest) | nginx:alpine | 0.0.0.0:8100 (`PROXY_PORT`) | — |
| `asterisk` | Puente SIP Anura ↔ LiveKit y Meta (WhatsApp, TLS 5061) ↔ LiveKit | build (`network_mode: host`) | 5080, 5081, 5061, RTP 10000–10199 | — |
| `livekit`, `livekit-sip`, `livekit-redis` | LiveKit propio (`docker-compose.livekit.yml`): rooms, despacho del agente y SIP | livekit-server v1.13.7, sip v1.17.0, redis:7-alpine | 7880, 7881, 7882/udp, 5060, RTP 20000–20199; Redis 127.0.0.1:6380 | — |
| `tunnel` | Cloudflare Tunnel (`docker-compose.tunnel.yml`, `make up-tunnel`) | cloudflare/cloudflared:2026.9.0 | — | — |
| `prometheus`, `node-exporter`, `blackbox`, `alertmanager` | Observabilidad (`docker-compose.monitoring.yml`) + colector `atentina-hostmon` (systemd) | prom/* fijadas | 127.0.0.1:9090, :9093 | — |

- La inferencia habla API OpenAI y exige `Authorization: Bearer $VLLM_API_KEY`. Los 810x son para debug local.
- Modo remoto: `app` + `agent` en otra PC (`make up-agent`) contra la inferencia por el proxy
  (`http://<host>:8100/{llm,stt,tts}/v1`). Es HTTP plano y la única auth es `VLLM_API_KEY`: el 8100 no
  se reenvía en el router salvo que se abra temporalmente para un loadtest ([`MIGRACION_SERVER.md`](MIGRACION_SERVER.md), 6).

**Overrides en la raíz** (se suman a `COMPOSE_FILE` o con `-f`):

| Archivo | Para qué |
|---|---|
| `docker-compose.gemma4-26b.yml` | LLM vigente: Gemma 4 26B-A4B AWQ-INT4 desde `/home/laureano/Models`, flags fijos y muestreo de Gemma para `app`/`agent` |
| `docker-compose.livekit.yml` | LiveKit propio (vigente) |
| `docker-compose.tunnel.yml` | Túnel de Cloudflare (`make up-tunnel`, también lo levanta `deploy/boot.sh`) |
| `docker-compose.monitoring.yml` | Prometheus, node-exporter, blackbox y Alertmanager (`make up-monitoring`) |
| `docker-compose.gemma4-e4b.yml` | Prueba: Gemma 4 E4B (Google QAT w4a16) en lugar del LLM vigente |
| `docker-compose.llm-defaults.yml` | Prueba: defaults de muestreo y sin razonamiento en el servidor (para clientes que no los mandan), con Qwen |
| `docker-compose.gpu-5060.yml` | Reparto con una 5060 Ti 8 GB para el TTS (CAP-002, CAP-004); no vigente |
| `docker-compose.e2e-sip.yml` | Prueba SIP aislada (`make e2e-sip`): LiveKit, Asterisk y un Anura falso, sin puertos del host |

## Reparto de GPU y capacidad

| GPU | Servicios | Memoria |
|---|---|---|
| 0 | `vllm-llm` solo | 0.90, 32 secuencias, contexto 16384; ~21 GB usados; KV cache de 63.013 tokens para todas las llamadas (medido el 28-oct-2026 por `vllm:cache_config_info`) |
| 1 | `vllm-tts` + `stt-parakeet` + escritorio | TTS 0.4 (talker ~9,6 GB + Code2Wav ~3,5 GB), 128 por etapa; STT ~1,6 GB; ~15,7 GB usados |

- **El override de Gemma fija sus flags:** `--gpu-memory-utilization=0.90`, `--max-num-seqs=32`,
  `--max-cudagraph-capture-size=32` y `--max-model-len=16384` van escritos en
  `docker-compose.gemma4-26b.yml` (reemplaza el `command` entero). `VLLM_LLM_MAX_NUM_SEQS` y
  `VLLM_LLM_GPU_MEMORY_UTILIZATION` de `.env` no se usan con Gemma (hoy están comentadas). Cambiar la
  capacidad del LLM es editar el override.
- Las variables de capacidad que sí rigen: `STT_MAX_BATCH`, `STT_MAX_BATCH_SECONDS`,
  `VLLM_TTS_GPU_MEMORY_UTILIZATION` y `VLLM_TTS_MAX_NUM_SEQS` (las dos etapas, por `--stage-overrides`). Se
  aplican con `make up-inference`, parando antes los tres (el LLM nuevo no entra si el TTS viejo sigue arriba).
- **Capacidad con Gemma: sin medir.** No hay CAP con Gemma; no usar los números del Qwen como capacidad
  actual. Con el Qwen3.5-9B anterior (CAP-001, con los topes): ~20 llamadas con p95 ≤ 2,4 s y ~32 con
  p95 ≤ 3 s (codo, saturan las dos GPUs); con 64 también la CPU del host (~0,12 cores por llamada) y el
  servicio colapsa; potencia de las dos GPUs, 559 W de pico.
- Con sobrecarga (~110 llamadas, CAP-002) el talker del TTS se cae y no se recupera solo: recrear
  `vllm-tts` y calentarlo. Docker lo sigue viendo `running`.
- Todo cambio de modelo, reparto de GPU, flags de memoria o hardware se mide con el test de capacidad
  y se registra en [`capacity/`](capacity/README.md) (`CAP-NNN`), con un override `docker-compose.<nombre>.yml`.
  Volver a lo vigente: `make up-inference` sin `-f` extra.

## Inferencia: reglas y trampas

**General**
- **El TTS no comparte GPU con el LLM ni con otra réplica** (EXP-001 a 004). Con el STT sí: hasta ~48
  llamadas el STT no se resiente; con 64 sube a ~0,5–0,6 s (EXP-013). Escalar TTS es sumar GPUs.
- `--gpu-memory-utilization` es fracción de la memoria **total**: los que comparten GPU suman menos de
  ~0.95, descontando el escritorio.
- Los que comparten GPU no arrancan a la vez (compiten por la memoria libre): `depends_on` encadena
  `stt-parakeet` detrás de `vllm-tts`.
- Los comentarios del compose explican el porqué medido de cada flag: mantenerlos al día.

**LLM (`vllm-llm`)**
- `VLLM_LLM_MODEL` tiene que coincidir entre `vllm-llm` y `app`/`agent` (el override lo fija en los tres):
  al cambiarlo, recrear los tres.
- `--enable-auto-tool-choice --tool-call-parser=gemma4`: sin el parser del modelo, todo agente da 400
  (`end_call` va siempre).
- `--max-cudagraph-capture-size` igual a las secuencias evita que la VRAM crezca con el tráfico.
  `--limit-mm-per-prompt` en 0: el modelo trae encoders de imagen y video que no se usan.
- Muestreo de Gemma (1.0 / 0.95 / 64 / 0.0) en `LLM_TEMPERATURE`/`TOP_P`/`TOP_K`/`MIN_P` del override, no en el código.
- `vllm/vllm-openai:latest` no está fijada: un pull trae otra versión que la medida (digest probado en
  [`MIGRACION_SERVER.md`](MIGRACION_SERVER.md), 5.1).
- Volver al Qwen3.5-9B: sacar el override de `COMPOSE_FILE`, poner `VLLM_LLM_MODEL=RedHatAI/Qwen3.5-9B-quantized.w4a16`
  y recrear `vllm-llm`, `app` y `agent`.

**STT (`stt-parakeet`, `stt/server.py`)**
- Batching dinámico hasta `STT_MAX_BATCH` (8): un pedido solo tarda ~60 ms; con 16 clientes en paralelo
  rinde ×4,7 (76 contra 16 req/s) y la p50 baja de 996 a 204 ms.
- Expone `/metrics` con nombres de vLLM para el sampler y Prometheus.
- Prefijo de idioma: con `language=es` antepone "A ver, te cuento." (`stt/primers/es.wav`) y lo saca del
  texto. Respuestas cortas: WER 28,7 % → 0 %; +9 ms de p50. Se apaga con `STT_PRIMER_WAV=` vacío y
  `make up-stt` (que se niega con llamadas en curso).

**TTS (`vllm-tts`)**
- `vllm/vllm-omni` fijada en v0.28.0: `latest` no arranca. Deja `num_requests_running` en 1 sin tráfico:
  la actividad se mide por los contadores de tokens.
- Sirve el checkpoint de `TTS_FT_CKPT` (default `multi41`, lr 2e-6, época 2) como `qwen3-tts-ft`, con 41
  voces de OpenSLR 61 con nombres argentinos (catálogo en `tts/finetune/voces.tsv`). Las voces están
  dentro del checkpoint (`tts/finetune/work/`, no versionado): si se pierde, hay que reentrenar.
- **Un pedido sin `voice` o con `voice="default"` mata el engine** (busca `vivian`) y todo da 500 hasta
  reiniciarlo. Una voz no servida da 400 por frase. El agente usa la voz elegida para la llamada, si no
  `agent.voice`, si no `VLLM_TTS_VOICE`.
- Al cambiar de checkpoint, los nombres de voz tienen que coincidir con `VLLM_TTS_VOICE`, con `agent.voice`
  y con cualquier host que use este TTS por el proxy; y borrar `storage/openings/` (aperturas pregeneradas).
- El primer pedido después de arrancar tarda 0,8 s en la 3090 (más de 20 s en la 5060 Ti):
  `deploy/boot.sh` lo calienta con `VLLM_TTS_VOICE`.

## LiveKit y telefonía

Anura → Asterisk → `livekit-sip` → `livekit` → room + `agent`, todo en este host. LiveKit propio es el de
producción: LiveKit Cloud no se usa. Detalle, formatos de número, síntomas y seguridad SIP en
[`TELEFONIA_ANURA.md`](TELEFONIA_ANURA.md).

- `livekit-redis` corre sin persistencia (`--save ""`): cada reinicio borra los trunks SIP y la dispatch
  rule, y las entrantes dan 486 `flood` hasta `make livekit-sip` (lo corren `make up` y `deploy/boot.sh`).
- `LIVEKIT_SIP_TRUNK_ID` va vacío: el ID cambia en cada recreación y el agente busca el trunk saliente
  por nombre (`anura-asterisk-outbound`).
- Los navegadores entran por `wss://rtc.atentina.com.ar` (`DEMO_LIVEKIT_URL`, túnel); el audio WebRTC va
  por UDP 7882 / TCP 7881 reenviados en el router, con `LIVEKIT_NODE_IP` = IP pública.
- Llamadas de WhatsApp: Meta → `sip.atentina.com.ar:5061` (TLS) → Asterisk → LiveKit, SRTP (SDES) y PCMA
  sin transcodificar. Certificado de Let's Encrypt (`make sip-cert`), renovado por cron. Ver
  [`features/WHATSAPP.md`](features/WHATSAPP.md).
- Antes de recrear algo que corta llamadas (`agent`, `asterisk`, `stt-parakeet`): `make calls-active`.

## Arranque, backup y cron

**Arranque** (`sudo deploy/install.sh` instala las unidades de `deploy/systemd/`):
- `atentina-gpu-limits.service`: topes de las GPUs.
- `atentina-stack.service` (`deploy/boot.sh`): `docker compose up -d --wait` sin build (hasta 15 min), el
  túnel, `make livekit-sip` y el calentamiento del TTS. Probado en un reinicio: stack listo con el TTS
  caliente en ~2 min. No probado con un corte de luz.
- `atentina-hostmon.service`: colector del host para Prometheus (`make monitoring-host-install`).
- El monitoreo y el CRM vuelven por `restart: unless-stopped`.

**Cron del usuario** (`deploy/crontab`, `make cron-install`; logs en `~/atentina-ops/`):

| Cuándo | Qué |
|---|---|
| 03:30 y cada hora con `--if-due` | `scripts/ops/backup.sh`: base (`pg_dump`), `.env`, `storage/`, certificado SIP y checkpoint del TTS, 30 días, en `~/atentina-backups` (otro disco que Docker). La corrida horaria lo recupera si el host estuvo apagado |
| cada 2 min | `scripts/ops/healthcheck.sh`: contenedores, app local, dashboard y webhook por el túnel, topes de GPU, certificado SIP (< 14 días), backup completo en 26 h; avisa por ntfy (`ALERT_NTFY_TOPIC`) |
| 04:15 | `scripts/ops/sip-cert-renew.sh`: renueva a 30 días del vencimiento y reinicia Asterisk solo sin llamadas en curso |

- **Copia externa a S3: no activa.** Está implementada (`make backup-key`, `make backup-s3-setup`,
  `make backup-fetch`, `make backup-list`; cifrado con la llave pública `deploy/backup-key.asc`, salvo el
  checkpoint), pero `BACKUP_S3_BUCKET` no está en `.env`. Hasta activarla, los backups viven en el mismo
  equipo: perder el server es perder base, `.env` (con `WA_TOKEN_KEY`) y checkpoint.
- Restauración probada en un Postgres limpio, desde disco y desde un S3 de prueba.

## Exposición a internet

- **Túnel de Cloudflare** (`atentina-demo`): `api.` → `/api/v1/demo/*`, `rtc.` → LiveKit (7880), `wa.` →
  `/wa/webhook`, `app.` → todo `app` (dashboard), `llamar.` y `telefono.` → `app`. No hace falta 443 en el router.
- `app.atentina.com.ar` es público sin Cloudflare Access: la app se defiende sola (sesión revocable, límites
  de login por IP real desde `TRUSTED_PROXY_CIDRS`, CSRF por `Origin`, CSP, HSTS). Detalle en
  [`ARQUITECTURA.md`](ARQUITECTURA.md).
- **Router:** reenvía solo RTP de Asterisk (UDP 10000–10199), SIP/TLS de Meta (TCP 5061) y WebRTC (UDP 7882,
  TCP 7881). El 5080 (SIP de LiveKit) no se reenvía: abierto permitía fraude telefónico, y el endpoint
  `livekit` de Asterisk solo acepta loopback y la LAN. El 8100 tampoco. Tabla completa y SIP ALG en
  [`MIGRACION_SERVER.md`](MIGRACION_SERVER.md), 6.
- Nunca dos Asterisk registrados con la misma terminal de Anura ni dos `cloudflared` con el mismo token.

## Límites para escalar

Hechos del código que atan la plataforma a **un solo `app` y un solo server**:

- **Loops de fondo en el proceso HTTP:** el `lifespan` de `app/main.py` arranca el barrido de WhatsApp
  (`sweep_loop`), las campañas (`campaign_loop`), los webhooks de campañas (`callback_loop`), los
  vencimientos de planes (`billing_loop`) y los resúmenes por mail (`call_summary_loop`). Cada copia de
  `app` los correría todos.
- **Webhook de WhatsApp sin persistencia previa:** `app/whatsapp/webhook.py` devuelve 200 después de
  agendar tareas en memoria (`WhatsAppService.handle_payload`), sin guardar el evento. Un reinicio en ese
  momento pierde el mensaje; debounce y locks por contacto viven en memoria.
- **Campañas:** el dialer de voz reclama contactos con `FOR UPDATE SKIP LOCKED`, pero el crédito de ritmo
  vive en memoria (`app/campaigns/dialer.py` supone un solo worker de uvicorn). El envío de WhatsApp
  (`app/whatsapp/sender.py`) lleva el ritmo en memoria y `recover()` marca `failed` todo lo `in_progress`
  al arrancar: una segunda instancia invalidaría envíos vivos de la primera.
- **Limitadores en memoria:** `RateLimiter` (`app/services/ratelimit.py`) guarda los hits en un dict del
  proceso (login, demo, previews, API de inferencia). No hay Redis para la app (el único Redis es el de LiveKit).
- **Admisión:** `quota.admit` cuida los límites del cliente con lock de fila, pero nada tope la capacidad
  total de las GPUs; el worker no declara una función de carga propia a LiveKit.
- **`/health` responde siempre `{"ok": true}`:** no mira base, worker ni inferencia. Un TTS o LLM caído con
  el contenedor `running` lo detectan Prometheus y sus alertas, no el health.
- **Base local:** el worker usa Postgres varias veces por turno; una base remota sumaría idas y vueltas.
- Con dos servers iguales, la capacidad vendible sigue siendo la de uno (N+1), y `app` iría activo-pasivo
  por todo lo anterior.

## Pendientes de producción

- **Copia externa del backup:** crear el bucket y la llave (`make backup-key`, `make backup-s3-setup`) y
  guardar la privada fuera del server.
- **Energía:** UPS senoidal de 1500–2200 VA (≥ 1000 W reales; 2 × 3090 a 280 W + host ~710 W) con
  apagado ordenado por NUT.
- **Internet:** segunda conexión; confirmar si la IP fija es plan de empresa y si Anura admite un segundo destino.
- **Host dedicado:** hoy comparte con Dify, sim-poc, desarrollo y sesiones de agentes; el escritorio usa la GPU 1.
- **Firewall del host:** `ufw` apagado y `app` escucha en `0.0.0.0:8011` (la LAN lo ve sin túnel); el
  proxy, en `0.0.0.0:8100`. Dejar solo localhost, el túnel y la LAN de administración, y SIP solo desde Anura.
- **CSP estricta:** hoy `CSP_REPORT_ONLY=true`.
- **Vigilante externo:** `HEALTHCHECKS_PING_URL` vacía.
- **Capacidad con Gemma:** medir (CAP-NNN) antes de vender un número de llamadas simultáneas.
- **Versiones fijas:** `vllm/vllm-openai` (compose y `stt/Dockerfile`) y el `apk` de Asterisk.
- **`.env.example` desactualizado:** trae LiveKit Cloud (`LIVEKIT_URL=wss://…livekit.cloud`) y el Qwen
  (`VLLM_LLM_MODEL=RedHatAI/Qwen3.5-9B…`) como default; producción usa LiveKit propio y Gemma.
