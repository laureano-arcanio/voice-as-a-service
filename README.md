# Atentina — agentes de IA que atienden a tus clientes

Plataforma multi-cliente de agentes de IA que **atienden y hacen llamadas** (teléfono, navegador y WhatsApp) y
contestan mensajes de WhatsApp, con **inferencia propia**: LLM, STT y TTS corren en GPUs locales. Cada cliente tiene
sus números, sus agentes, su equipo y un **tier** con límites mensuales; todo se administra por la UI, la API
(`/api/v1`) y el MCP.

La conversación no es un guion: la **definición del agente** (JSON versionado) fija qué datos obtener, las reglas y
las herramientas, y el LLM conversa a partir de ella. Un solo motor: texto libre, herramientas del cliente (APIs y
código) y de la plataforma (`end_call`, `transfer_call`), y extracción de datos al terminar.

- Arquitectura y detalles técnicos: [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md).
- Infraestructura (host, GPUs, servicios): [`docs/INFRA.md`](docs/INFRA.md).
- Cada función: [`docs/features/`](docs/features/). Cómo usar la UI: [`docs/GUIA_UI.md`](docs/GUIA_UI.md).
- Índice para agentes de IA: [`AGENTS.md`](AGENTS.md).

## Entidades

| Entidad | Qué es |
| --- | --- |
| Tier | Límites (llamadas simultáneas, por hora, día y mes; minutos entrantes y salientes por mes calendario en `BILLING_TIMEZONE`; números, campañas, herramientas, links) y funciones del plan (`TIER_HAS`). Vacío = ilimitado. Planes: Free, Mostrador, Sucursal, Red (a medida) e Interno (nosotros). |
| Cliente | Tenant: un tier, sus números, agentes, equipo, usuarios y API keys. Inactivo: no llama ni atiende. |
| Agente | Definición JSON (`GET /api/v1/agents/schema`), **versionada**: cada cambio es una versión inmutable y cada conversación guarda la suya. Se crea en blanco o desde la plantilla (`app/agents/templates/asistente.json`) y se edita por formulario. |
| Número | Inventario de números de Anura (E.164). El admin los carga, los asigna a un cliente (tope del tier) y se rutean a un agente o al equipo (`answer_mode`). Cargar o borrar actualiza los trunks SIP de LiveKit en caliente. |
| Usuario | `admin` (opera la plataforma en `/admin/*` y entra a un cliente en modo soporte) o `client` (lo de su cliente). |

**Límites (corte duro):** `POST /api/v1/calls` responde 429 (`concurrency_limit`, `calls_per_hour`,
`calls_per_day`, `calls_per_month`, `outbound_minutes`, `inbound_minutes`, `client_inactive`) si no hay lugar, cupo
o minutos; una entrante sin lugar escucha `QUOTA_REJECT_MESSAGE` y se corta. En curso, el worker revisa el saldo
cada `QUOTA_CHECK_SECONDS` (15 s) y corta al agotarse. La admisión toma un lock de fila del cliente: con 20 pedidos
simultáneos y tope 3 entran exactamente 3 (medido en PostgreSQL). Detalle en ARQUITECTURA, "Límites por tier".

**API:** `/api/v1`, OpenAPI en `/api/v1/docs` (solo admin con sesión, salvo `API_DOCS=public`) y versionado en
`web/openapi.json`. La UI usa cookie de sesión; los sistemas del cliente, `Authorization: Bearer vaas_...`.

```bash
curl -X POST http://<host>:8011/api/v1/calls -H "Authorization: Bearer $VAAS_API_KEY" \
  -H 'Content-Type: application/json' -d '{"agent_id": "<id>", "phone": "+5491155551234"}'
```

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic (PostgreSQL; SQLite en los tests), pydantic-settings,
  argon2 y sesiones JWT.
- **Frontend:** React 19 + TypeScript + Vite, Mantine, TanStack Query, tipos generados del OpenAPI (`web/`).
- **Voz:** LiveKit Agents (worker propio en `app/voice/worker.py`, contenedor `agent`) con LiveKit propio, y
  Asterisk de puente con Anura (teléfono) y Meta (llamadas de WhatsApp).
- **Inferencia** (API compatible con OpenAI, `Authorization: Bearer $VLLM_API_KEY`):

| Rol | Modelo | Servicio |
| --- | --- | --- |
| LLM | Gemma 4 26B-A4B en 4 bits (`cyankiwi/gemma-4-26B-A4B-it-qat-AWQ-INT4`, override `docker-compose.gemma4-26b.yml`) | `vllm-llm` |
| STT | `nvidia/parakeet-tdt-0.6b-v3`, servidor propio con batching (`stt/server.py`) | `stt-parakeet` |
| TTS | Qwen3-TTS 1.7B con fine-tuning, 41 voces argentinas en un checkpoint (`multi41`, [`tts/finetune/voces.tsv`](tts/finetune/voces.tsv)) | `vllm-tts` |

Reparto de GPU, capacidad y trampas: [`docs/INFRA.md`](docs/INFRA.md). Voces: [`docs/TTS_FINETUNE.md`](docs/TTS_FINETUNE.md).
La voz de cada llamada sale, en orden, de la elegida al lanzarla, de `agent.voice` y de `VLLM_TTS_VOICE`.
**Nunca pedir TTS sin `voice` ni con `voice="default"`:** mata el engine de `vllm-tts`.

## Correr con Docker Compose

```bash
make setup   # crea .env desde .env.example; completar credenciales (ver "Claves")
make up      # todo: agente + inferencia + proxy + asterisk + LiveKit propio
```

Server nuevo (host desde cero, restaurar base y checkpoint, router, corte):
[`docs/MIGRACION_SERVER.md`](docs/MIGRACION_SERVER.md). Ahí el `.env` sale del backup, no de `make setup`.

`make up` y `make up-agent` corren antes `make migrate`: migraciones y un seed idempotente (tier Interno sin
límites, cliente `atentina` con sus agentes, `ANURA_DID` atendido por `WORKFLOW_ID` y el admin `ADMIN_EMAIL`).
Otro admin: `make create-admin EMAIL=...`; API key de un cliente: `make api-key CLIENT=<slug> NAME=<nombre>`.

| Target | Servicios |
| --- | --- |
| `make up` | todos |
| `make up-agent` | `db` + `migrate` + `app` (`:8011`, UI y API) + `agent`, sin la inferencia |
| `make up-inference` | `vllm-llm` + `stt-parakeet` + `vllm-tts` (espera a que estén healthy) |
| `make up-stt` | solo el STT |
| `make up-nginx` | `proxy` (inferencia por la IP fija, `PROXY_PORT`; en producción no se reenvía en el router) |
| `make up-pbx` | `asterisk` (lo recrea para releer `.env` y `asterisk/conf/`) |
| `make up-tunnel`, `make up-monitoring`, `make crm-up` | túnel de Cloudflare, observabilidad, CRM |

`make logs S=<servicio>`, `make health` y `make help` para el resto. `make restart` no relee `.env`: después de
editarlo, `make up-pbx` o `make up`. Antes de recrear algo que corta llamadas, `make calls-active`.

Desarrollo de la UI: `make web-dev` (Vite en :5173 contra la API de :8011), ver [`web/README.md`](web/README.md).
Tests: `make test` (LLM falso, sin servicios reales).

## Claves (`.env`)

1. `AUTH_SECRET` (`openssl rand -hex 32`): firma de las sesiones; sin ella `app` no arranca. `ADMIN_EMAIL` /
   `ADMIN_PASSWORD` para el primer admin.
2. `LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` del LiveKit propio
   ([`docs/TELEFONIA_ANURA.md`](docs/TELEFONIA_ANURA.md)). `LIVEKIT_SIP_TRUNK_ID` vacío: el agente busca el trunk
   saliente por nombre.
3. `VLLM_API_KEY` (clave real siempre) y `PUBLIC_HOST`.
4. Telefonía (`ANURA_*`, `LIVEKIT_SIP_*`), demo, WhatsApp (`WA_*`), túnel, correo (Resend), Mercado Pago, backup y
   monitoreo: tabla completa (de dónde sale cada una y cuál no se puede regenerar, como `WA_TOKEN_KEY`) en
   [`docs/MIGRACION_SERVER.md`](docs/MIGRACION_SERVER.md), 3.2.

`.env.example` todavía trae defaults viejos (LiveKit Cloud, Qwen): el `.env` de producción es la referencia.
