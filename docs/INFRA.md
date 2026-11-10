# Infraestructura

Agente de voz con inferencia propia: LLM, STT y TTS corren en GPUs propias, sin proveedores externos. Este doc
cubre los hosts, los servicios del compose, el reparto de GPU, la telefonía, el arranque, los backups y la
exposición a internet.

**Dos servers (desde el 2-nov-2026):** server2 (`192.168.1.98`) es el principal y corre todo, y atiende solo la
inferencia de producción: sin respaldo de inferencia. El otro (`192.168.1.99`) es el entorno de desarrollo, en un stack
aparte ([`DESARROLLO.md`](DESARROLLO.md)); sus tres modelos no reciben producción: su réplica está en `disabled` en el
balanceador ([`features/LLM_REPLICAS.md`](features/LLM_REPLICAS.md)). Salvo que se indique, "este host" en este doc es server2.

Docs relacionados: [`TELEFONIA_ANURA.md`](TELEFONIA_ANURA.md) (Anura, Asterisk, LiveKit),
[`MIGRACION_SERVER.md`](MIGRACION_SERVER.md) (server nuevo, router, corte),
[`OBSERVABILIDAD.md`](OBSERVABILIDAD.md) (métricas y alertas), [`capacity/`](capacity/README.md)
(capacidad medida), [`TTS_FINETUNE.md`](TTS_FINETUNE.md) (voces).

## Host y hardware

| Pieza | server2 (`atentina-region-2`), principal | 192.168.1.99, desarrollo (modelos fuera del reparto) |
|---|---|---|
| CPU, RAM, placa | Ryzen 7 5700 (8/16), 30 GB, Gigabyte B550 Eagle WIFI6 (PCIe Gen3) | Ryzen 7 5700X (8/16), 64 GB, ASRock B550M Pro SE |
| GPU del LLM | RTX 3090 24 GB, índice 0, `01:00.0`, Gen3 x16, 350 W | RTX 3090 24 GB, índice 1, `07:00.0`, Gen4 x16, 350 W; también dibuja el escritorio |
| GPU de TTS + STT | RTX 3080 Ti 12 GB, índice 1, `05:00.0`, slot del chipset **x1** (Gen3), 350 W | RTX 3080 Ti 12 GB, índice 0, `04:00.0`, Gen3 x4, 350 W |
| Red | LAN `192.168.1.98` (reserva DHCP). IP pública `181.104.113.28`: los reenvíos del router van acá | LAN `192.168.1.99` (reserva DHCP) |
| Discos | NVMe de 477 GB en `/` (Docker, repo, base); HDD 750 GB en `/mnt/storage-server-region-2` (audios y backups); HDD 1 TB con datos personales, sin montar al arrancar | NVMe de 465 GB en `/` y NVMe de 1,8 TB en `/home` |

- **Enlace x1 de la 3080 Ti de server2:** 0 replays PCIe en la prueba de 5 llamadas (2-nov-2026); falta medirlo con
  carga. Un enlace x1 con errores ya tiró el TTS (CAP-004): vigilar `nvidia-smi -q | grep -i replay`.
- **RAM de server2:** 13,5 GB usados con todo arriba y 17,6 GB disponibles con 3 llamadas (2-nov-2026); sin medir con carga.
- En la réplica corren contenedores de otros proyectos (`app-sugym-gestion`, `delinquency-postgres`): no tocarlos.
- La 5060 Ti de CAP-002 y CAP-004 fue una prueba: no se usa.

**Reglas de hardware (para un server nuevo):**
- Sin tensor parallel el PCIe casi no importa: por el bus viajan IDs de tokens y audio (~1 MB/s con 32
  llamadas). El ancho del slot solo cambia cuánto tarda en cargar el modelo. El LLM corre en Gen3 x4 y alcanza.
- En una B550 la topología es fija: un x16 de la CPU, un x4 del chipset (Gen3, con el enlace del chipset
  compartido) y un M.2 de la CPU que con adaptador sirve de segundo x4.
- Risers: alimentados por PCIe de 6 pines, nunca por SATA; los de minería por USB fallan en Gen4 (forzar
  Gen3 en la BIOS). Una 5060 Ti por riser x1 tuvo errores de enlace y el TTS se cayó (CAP-004). Verificar
  con `nvidia-smi -q | grep -i -A2 replay` y `sudo dmesg | grep -iE 'aer|xid'`.
- El orden de las GPUs sigue el bus PCI. El reparto vigente toma los índices de `GPU_LLM_ID` (3090, con el
  escritorio) y `GPU_TTS_ID` (3080 Ti) en `.env`, por `docker-compose.gpu-3080ti.yml`.

## Servicios

`COMPOSE_FILE=docker-compose.yml:docker-compose.livekit.yml:docker-compose.gpu-3080ti.yml:docker-compose.llm-lb.yml`
en el `.env` de server2: todos los targets de `make` usan el compose principal (con el LLM Qwen3.5-9B), LiveKit propio, el reparto de GPU y el balanceador.
La réplica usa `docker-compose.yml:docker-compose.gpu-3080ti.yml:docker-compose.replica.yml`
y `STACK_ROLE=replica`: solo levanta los modelos y `make up*` se niega. En server2, `make up` levanta todo y
termina con `make livekit-sip`. Por partes: `make up-agent`, `make up-app`, `make up-inference`, `make up-stt`,
`make up-nginx`, `make up-pbx`, `make up-tools`, `make up-tunnel`, `make up-monitoring`, `make crm-up`,
`make registros-up`.

| Servicio | Qué es | Imagen | Puerto host | GPU |
|---|---|---|---|---|
| `db` | PostgreSQL 16 (base de la app y bases `crm` y `registros`) | postgres:16-alpine | 127.0.0.1:5432 | — |
| `migrate` | Una vez antes de `app`/`agent`: `alembic upgrade head` + seed idempotente (`app/cli.py`) | build | — | — |
| `app` | FastAPI: API `/api/v1`, UI (`web/dist`), MCP, webhooks y loops de fondo | build | 8011 (todas las interfaces) | — |
| `agent` | Worker de LiveKit Agents (STT → LLM → TTS) contra el LiveKit propio | build | — | — |
| `crm` | CRM de ventas: API y UI ([`features/CRM.md`](features/CRM.md)) | build | 127.0.0.1:8030 | — |
| `registros` | App de fichas (`apps/registros/`, [`features/REGISTROS.md`](features/REGISTROS.md)): perfil de compose `registros`, sin `.env` de la plataforma, rol y base propios, pool de 7 conexiones | build (`apps/registros/`) | 127.0.0.1:8040 | — |
| `tools-runner` | Sandbox de las herramientas de código: un proceso Deno por función, solo en la red interna `atentina-tools` | build (`tools-runner/`) | — | — |
| `tools-egress` | Única salida de `tools-runner`: Smokescreen, niega IPs privadas, loopback y metadata | build | — | — |
| `vllm-llm` | LLM `RedHatAI/Qwen3.5-9B-quantized.w4a16`, parser de herramientas `qwen3_coder` | vllm/vllm-openai:latest | 127.0.0.1:8101 | 0 |
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
| `docker-compose.gemma4-26b.yml` | LLM alternativo: Gemma 4 26B-A4B AWQ-INT4 desde `/home/laureano/Models`, flags fijos, parser `gemma4` y muestreo de Gemma para `app`/`agent` |
| `docker-compose.livekit.yml` | LiveKit propio (vigente) |
| `docker-compose.tunnel.yml` | Túnel de Cloudflare (`make up-tunnel`, también lo levanta `deploy/boot.sh`) |
| `docker-compose.monitoring.yml` | Prometheus, node-exporter, blackbox y Alertmanager (`make up-monitoring`) |
| `docker-compose.gemma4-e4b.yml` | Prueba: Gemma 4 E4B (Google QAT w4a16) en lugar del LLM vigente |
| `docker-compose.llm-defaults.yml` | Prueba: defaults de muestreo y sin razonamiento en el servidor (para clientes que no los mandan), con Qwen |
| `docker-compose.gpu-3080ti.yml` | Reparto vigente: LLM en la 3090 (`GPU_LLM_ID`), TTS + STT en la 3080 Ti (`GPU_TTS_ID`), con una fracción de memoria por etapa del TTS |
| `docker-compose.llm-lb.yml` | Balanceador de LLM, STT y TTS (server2) |
| `docker-compose.replica.yml` | Host réplica: publica los modelos en la LAN y deja el resto fuera con un perfil |
| `docker-compose.gpu-5060.yml` | Reparto con una 5060 Ti 8 GB para el TTS (CAP-002, CAP-004); no vigente |
| `docker-compose.e2e-sip.yml` | Prueba SIP aislada (`make e2e-sip`): LiveKit, Asterisk y un Anura falso, sin puertos del host |

## Reparto de GPU y capacidad

| GPU | Servicios | Memoria |
|---|---|---|
| 3090 (`GPU_LLM_ID`: 0 en server2, 1 en .99) | `vllm-llm` (en .99, + escritorio) | 0.90, 128 secuencias, contexto 32768; 11,4 GB de pesos y 9,4 GiB de KV cache, 21,0 GB la placa (EXP-013) |
| 3080 Ti (`GPU_TTS_ID`: 1 en server2, 0 en .99) | `vllm-tts` + `stt-parakeet` | talker 0.40 (6,0 GB reales, KV de 6.096 tokens, largo 2048, batches de 512) + Code2Wav 0.28 (3,5 GB), 128 por etapa; STT 1,6 GB; 11,1 de 12,3 GB (31-oct-2026) |

- **Reparto vigente sin medir con carga.** server2 atiende solo, sin test de capacidad por decisión del usuario
  (5-nov-2026): ver [`capacity/`](capacity/README.md). El KV del talker (6.096 tokens) cubre el máximo medido en la 3090
  (~3.700 con 96 llamadas); queda ~1,1 GB libre en la 3080 Ti para el STT bajo carga. Las fracciones del TTS
  van escritas en `docker-compose.gpu-3080ti.yml`; `VLLM_TTS_GPU_MEMORY_UTILIZATION` no rige.

- Capacidad del LLM: `VLLM_LLM_MAX_NUM_SEQS` y `VLLM_LLM_GPU_MEMORY_UTILIZATION`. El override de Gemma
  fija los suyos (`--gpu-memory-utilization=0.90`, `--max-num-seqs=32`, `--max-cudagraph-capture-size=32`,
  `--max-model-len=16384`) y con él esas dos variables no rigen.
- Las del STT y el TTS: `STT_MAX_BATCH`, `STT_MAX_BATCH_SECONDS`,
  `VLLM_TTS_GPU_MEMORY_UTILIZATION` y `VLLM_TTS_MAX_NUM_SEQS` (las dos etapas, por `--stage-overrides`). Se
  aplican con `make up-inference`, parando antes los tres (el LLM nuevo no entra si el TTS viejo sigue arriba).
- **Capacidad del reparto vigente: sin medir.** CAP-001 midió el Qwen3.5-9B en 2 × 3090 con los topes: ~20
  llamadas con p95 ≤ 2,4 s y ~32 con p95 ≤ 3 s (codo, saturan las dos GPUs); con 64 también la CPU del host (~0,12 cores por llamada) y el
  servicio colapsa; potencia de las dos GPUs, 559 W de pico.
- Con sobrecarga (~110 llamadas, CAP-002) el talker del TTS se cae y no se recupera solo: recrear
  `vllm-tts` y calentarlo. Docker lo sigue viendo `running`. Con server2 solo, HAProxy cicla (503 para todos, 500 en
  los pedidos que pasan) y **nadie avisa**: riesgo aceptado por el usuario (5-nov-2026); ciclo medido y respuesta
  operativa en [`features/LLM_REPLICAS.md`](features/LLM_REPLICAS.md).
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
- `--enable-auto-tool-choice --tool-call-parser=qwen3_coder`: sin el parser del modelo, todo agente da 400
  (`end_call` va siempre). Qwen3.5 escribe las llamadas en el XML de `qwen3_coder` (`<tool_call><function=…>`).
- `--max-cudagraph-capture-size` igual a las secuencias evita que la VRAM crezca con el tráfico.
  `--limit-mm-per-prompt` en 0: el modelo trae encoders de imagen y video que no se usan.
- Muestreo del modelo en `LLM_TEMPERATURE`/`TOP_P`/`TOP_K`/`MIN_P`, no en el código: el de Qwen sin pensamiento
  (0.7 / 0.8 / 20 / 0.0) en `.env`; el generation_config del w4a16 no trae muestreo, así que sin esas variables rige
  el de vLLM (1.0 / 1.0).
- `vllm/vllm-openai:latest` no está fijada: un pull trae otra versión que la medida (digest probado en
  [`MIGRACION_SERVER.md`](MIGRACION_SERVER.md), 5.1).
- Pasar a Gemma 4 26B: sumar `docker-compose.gemma4-26b.yml` a `COMPOSE_FILE` después de `docker-compose.yml`, poner
  `VLLM_LLM_MODEL=cyankiwi/gemma-4-26B-A4B-it-qat-AWQ-INT4`, con los pesos en `~/Models` ([`MIGRACION_SERVER.md`](MIGRACION_SERVER.md),
  4.4), y recrear `vllm-llm`, `app` y `agent`. El override trae su parser (`--tool-call-parser=gemma4`; con `qwen3_coder`
  todo agente da 400) y su muestreo (1.0 / 0.95 / 64 / 0.0), que pisa el del `.env`. Volver: sacarlo y restaurar
  `VLLM_LLM_MODEL=RedHatAI/Qwen3.5-9B-quantized.w4a16`.

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
- `atentina-stack.service` (`deploy/boot.sh`): `docker compose up -d --wait` sin build (hasta 15 min), el
  túnel, `make livekit-sip`, el calentamiento del TTS y, si el `.env` tiene `REGISTROS_HEALTH_URL`, Registros (último paso,
  sin `--wait`: su falla no corta llamadas ni WhatsApp). En la réplica, solo los modelos y el calentamiento.
  En server2 instalado el 2-nov-2026 y validado con un simulacro (`--dry-run`), **sin probar con un reinicio real**.
- `atentina-hostmon.service`: colector del host para Prometheus (`make monitoring-host-install`), solo server2.
- El monitoreo, el CRM y Registros vuelven por `restart: unless-stopped`.
- **Disco de datos de server2** (`DATA_DISK`, ext4, `/etc/fstab` por UUID, antes de Docker, `nofail`): `audios/`
  (`RECORDINGS_DIR`) y `backups/` (`BACKUP_DIR`). `/etc/hdparm.conf` le saca el reposo: la grabación escribe en el
  event loop del worker. Sin montar, el backup falla a propósito y el chequeo avisa.

**Cron del usuario, solo en server2** (`deploy/crontab`, `make cron-install`; logs en `~/atentina-ops/`):

| Cuándo | Qué |
|---|---|
| 03:30 y cada hora con `--if-due` | `scripts/ops/backup.sh`: base (`pg_dump`), las de `BACKUP_EXTRA_DBS` (`registros`), `.env`, `storage/`, certificado SIP y checkpoint del TTS, 30 días, en `BACKUP_DIR` (el disco de datos, otro que Docker). **Los audios no entran**: están en el mismo disco. La corrida horaria lo recupera si el host estuvo apagado |
| cada 2 min | `scripts/ops/healthcheck.sh`: contenedores, app local, dashboard y webhook por el túnel, certificado SIP (< 14 días), backup completo en 26 h y Registros si hay `REGISTROS_HEALTH_URL`; avisa por ntfy (`ALERT_NTFY_TOPIC`) |
| 04:15 | `scripts/ops/sip-cert-renew.sh`: renueva a 30 días del vencimiento y reinicia Asterisk solo sin llamadas en curso |

- **Copia externa a S3: no activa.** Está implementada (`make backup-key`, `make backup-s3-setup`,
  `make backup-fetch`, `make backup-list`; cifrado con la llave pública `deploy/backup-key.asc`, salvo el
  checkpoint), pero `BACKUP_S3_BUCKET` no está en `.env`. Por decisión del usuario los backups quedan solo en server2:
  perder ese server es perder base, audios, `.env` (con `WA_TOKEN_KEY`) y backups; perder su disco de datos, audios y backups.
- Restauración probada en un Postgres limpio, desde disco y desde un S3 de prueba.

## Exposición a internet

- **Túnel de Cloudflare** (`atentina-demo`): `api.` → `/api/v1/demo/*`, `rtc.` → LiveKit (7880), `wa.` →
  `/wa/webhook`, `app.` → todo `app` (dashboard), `llamar.` y `telefono.` → `app`, `registros.` → `http://127.0.0.1:8040` (Registros; la ruta la crea el usuario al desplegarlo). No hace falta 443
  en el router. Registros se expone sin tope de cuerpo ni límite de login por IP ([`features/REGISTROS.md`](features/REGISTROS.md)).
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
  vencimientos de planes (`billing_loop`), los resúmenes por mail (`call_summary_loop`), el post-call de los agentes
  (`post_call_loop`) y la rotación de derivaciones por WhatsApp (`handoff_loop`). Cada copia de
  `app` los correría todos.
- **Webhook de WhatsApp sin persistencia previa:** `app/whatsapp/webhook.py` devuelve 200 después de
  agendar tareas en memoria (`WhatsAppService.handle_payload`), sin guardar el evento. Un reinicio en ese
  momento pierde el mensaje, y también el que está en debounce, transcripción o LLM; debounce y locks por contacto viven en
  memoria. Solo sobrevive una derivación ya reservada ([`features/WHATSAPP.md`](features/WHATSAPP.md)).
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
- **Energía:** UPS senoidal de 1500–2200 VA (≥ 1000 W reales; el pico de las GPUs bajo carga no está medido) con
  apagado ordenado por NUT.
- **Internet:** segunda conexión; confirmar si la IP fija es plan de empresa y si Anura admite un segundo destino.
- **Host dedicado:** hoy comparte con Dify, sim-poc, desarrollo y sesiones de agentes; el escritorio usa la GPU 1.
- **Firewall del host:** `ufw` apagado y `app` escucha en `0.0.0.0:8011` (la LAN lo ve sin túnel); el
  proxy, en `0.0.0.0:8100`. Dejar solo localhost, el túnel y la LAN de administración, y SIP solo desde Anura.
- **CSP estricta:** hoy `CSP_REPORT_ONLY=true`.
- **Vigilante externo:** `HEALTHCHECKS_PING_URL` vacía.
- **Capacidad del reparto vigente:** medir (CAP-NNN) antes de vender un número de llamadas simultáneas.
- **Versiones fijas:** `vllm/vllm-openai` (compose y `stt/Dockerfile`) y el `apk` de Asterisk.
