# Arquitectura

Plataforma de agentes de voz telefónicos multi-cliente con inferencia propia. Este documento cubre
la app (API, UI, worker de voz, base). La infraestructura (GPUs, servicios de inferencia,
capacidad) está en [`AGENTS.md`](../AGENTS.md) y el uso de la UI en [`GUIA_UI.md`](GUIA_UI.md).

## Componentes

```text
                     ┌──────────────┐  cookie de sesión / API key
  navegador ────────►│  app :8011   │◄──────────── sistemas del cliente
  (SPA web/dist)     │  FastAPI     │
                     │  /api/v1     │── dispatch ──┐
                     └──────┬───────┘              ▼
                            │               ┌─────────────┐   SIP    ┌──────────┐   SIP   ┌───────┐
                     ┌──────▼───────┐       │  LiveKit    │◄────────►│ Asterisk │◄──────►│ Anura │◄── PSTN
                     │ PostgreSQL   │◄──────│  + SIP      │          └──────────┘        └───────┘
                     │ (db)         │       └─────┬───────┘
                     └──────▲───────┘             │ job (room)
                            │              ┌──────▼───────┐   HTTP (API OpenAI)
                            └──────────────│ agent        │──────────► vllm-llm, stt-parakeet, vllm-tts
                                           │ worker de voz│
                                           └──────────────┘
```

| Proceso | Código | Qué hace |
|---|---|---|
| `migrate` | `migrations/`, `app/cli.py` | Una vez antes de `app` y `agent`: `alembic upgrade head` y el seed idempotente. |
| `app` | `app/main.py`, `app/api/` | API REST `/api/v1` y la SPA. Crea conversaciones y llamadas, admite por tier y despacha el worker a una room de LiveKit. Recibe el webhook de WhatsApp (`/wa/webhook`) y responde los mensajes en segundo plano. |
| `agent` | `app/voice/worker.py` | Worker de LiveKit Agents: STT → motor conversacional → TTS. Atiende salientes (con metadata del despacho) y entrantes (por dispatch rule, sin metadata). Las llamadas directas del equipo (sin agente) toman otra rama, `app/voice/direct.py`. |
| `db` | `app/models/` | PostgreSQL 16. Estado de todo: tenencia, agentes, conversaciones y llamadas. |

`app` y `agent` son la misma imagen (`Dockerfile`, multi-etapa: Node compila la SPA y Python la
sirve) con distinto comando.

## Código

```text
app/
  main.py            create_app(): routers en /api/v1, manejo de errores, headers de seguridad, SPA
  config.py          Settings (pydantic-settings, .env); config.X sigue funcionando para scripts
  db.py              Base, jsonb, engine y sessionmaker cacheados
  runtime.py         ConversationEngine compartido por API y worker
  cli.py             seed, create-admin, create-api-key
  models/            ORM (SQLAlchemy 2): tenancy, agents, conversations, calls
  api/
    deps.py          sesión de base, Principal (usuario o API key), require_admin, scoped_client_id,
                     client_ip, request_is_https, rate_limit
    http.py          middlewares: tope de cuerpo, CSRF y headers (CSP, HSTS)
    schemas.py       contratos pydantic (fuente del OpenAPI y de los tipos de la UI)
    errors.py        ServiceError -> JSON {detail, code, errors}; 500 JSON sin detalles internos
    routers/         auth, tiers, clients, phone_numbers, agents, users, api_keys, calls,
                     conversations, voices, whatsapp (cuentas), inference, demo, contacts, campaigns,
                     handoff (equipo, áreas, música de espera y eventos), direct_calls (llamadas directas,
                     presencia y timbre del panel)
                     (más wa_campaigns: el alias de /whatsapp/campaigns y /whatsapp/optouts)
  services/          negocio sin HTTP (lo usan la API y el worker)
    quota.py         límites del tier: admisión con lock, consumo del mes, saldo en curso
    limits.py        límites efectivos de un cliente: el tier más sus ajustes vigentes (`effective_limits`)
    calls.py         iniciar salientes/pruebas (prepare_call + dispatch), entrantes (start_inbound) y borrado
    phone_numbers.py inventario: carga, asignación con tope, liberación, ruteo a agente
    wa_routing.py    ruteo por contacto de WhatsApp (wa_routes): normaliza los wa_id, resuelve el
                     agente de un contacto y reemplaza las reglas de una cuenta
    agents.py        alta, validación de la definición, versionado, archivo
    reports.py       lista de llamadas, detalle, indicadores y serie diaria (filtros y zona horaria)
    phones.py        teléfonos a E.164, único para los dos canales (el wa_id de Meta sale de ahí)
    contacts.py      agenda: upsert por teléfono, archivar, import CSV, bajas por canal, tope del tier
    campaigns.py     lógica común de campañas: estados, horario, programación, variables, plan, progreso
    campaign_calls.py resultado SIP de un intento de voz, reintentos, recuperación y baja por outcome
    campaign_reports.py report.csv y stats por campaña
    campaign_callbacks.py cola (outbox) y firma del webhook de campañas
    handoff.py       equipo y áreas: horario, orden de llamado, mensajes, validación del agente y las áreas
                     de una llamada (call_areas)
    events.py        registro de eventos (tabla events, tipos en TYPES)
    direct_calls.py  llamadas directas del equipo (docs/LLAMADAS_DIRECTAS_PLAN.md): saliente desde el panel o
                     por API (token o join_url), presencia, timbre y atender/rechazar en el panel, respaldo al
                     agente y aviso de grabación
    security.py      argon2, JWT HS256, API keys (SHA-256), token de alta de clave
    api_usage.py     consumo y límites de la API de inferencia (cupos del mes, check/record, reporte)
    inference.py     gateway de la API de inferencia: reenvío a LLM, STT y TTS y medición del consumo
  mail/              mails por Resend: sender, layout.py + templates/layout.html (cabecera y pie),
                     messages.py (bienvenida con plan, número asignado) y notify.py (a quién llega)
    livekit.py       despacho a LiveKit y link de la llamada de prueba
    tts.py, voices.py prueba de voz (WAV completo, o PCM en streaming desde el SSE del motor) y catálogo (tts/finetune/voces.tsv)
    errors.py        NotFound, Forbidden, Conflict, Invalid, QuotaExceeded, Upstream
  agents/
    templates/       asistente.json: la plantilla de la UI (asistente básico)
    reference/*.json agentes de referencia (seed, eval, tests)
    definitions.py   DbDefinitions: versiones de la base, cacheadas (son inmutables)
    templates.py     plantilla, agente en blanco y ReferenceDefinitions (agentes de referencia)
  conversation/      motor (uno solo desde el 26-oct-2026): engine, models (Workflow = definición),
                     workflow (validación), store
  llm/               cliente y prompts del LLM; platform_tools.py (end_call y transfer_call, herramientas
                     de la plataforma) y external.py (tu propio agente)
  tools/             herramientas del cliente (docs/TOOLS_PLAN.md): schema, runtime (http, code, SSRF) y
                     conversation (el turno con herramientas)
  campaigns/         loop único de campañas (loop.py: delega por canal), dialer de voz (dialer.py),
                     contestador por heurística (voicemail.py) y entrega del webhook (callbacks.py)
  voice/             worker de LiveKit, latencia por turno, speech_text.py (texto del LLM a palabras para el
                     TTS: números, horas, fechas, plata, emails, teléfonos, códigos; es-AR) y handoff.py
                     (transferencia a una persona: Transfer es la lógica, RoomLine el lado de LiveKit),
                     listen.py (captura y transcripción por frase, VAD + STT, común a la derivación y las
                     directas) y direct.py (llamadas directas: saliente del equipo y entrante a un número
                     que atiende el equipo, sin AgentSession ni LLM)
  whatsapp/          webhook (firma), graph.py (Cloud API y media), store.py (tablas wa_*), service.py (turnos),
                     audio.py (notas de voz: STT, TTS y OGG/Opus con PyAV), signup.py (Embedded Signup,
                     registro, plantillas), crypto.py (tokens y PIN cifrados), campaigns.py y sender.py
                     (campañas de WhatsApp por plantilla, bajas y seguimiento de las de voz)
migrations/          Alembic: 0001 esquema anterior (idempotente), 0002 tenencia, 0003 inventario de números,
                     0004 WhatsApp, 0005 Embedded Signup y session_version, …, 0008 campañas de WhatsApp,
                     …, 0013 apps por cliente y operadores de WhatsApp, 0015 ruteo por contacto de WhatsApp,
                     0017 agenda y campañas unificadas (WhatsApp y voz), …, 0023 equipo, áreas y eventos,
                     0024 tramos de las derivaciones (handoff_legs), …, 0032 herramientas del cliente,
                     0033 un solo motor (borra apps, app_links, app_job_runs y wa_operators; tool_versions),
                     …, 0039 llamadas directas (personas por número, presencia, timbres, tiers.direct_calls)
web/                 SPA React (ver "Frontend")
tests/               pytest: API, límites, motor, campañas (test_campaigns, _dialer, _vars, _integration)
```

**Capas:** los routers validan la entrada, resuelven permisos y llaman a `services/`; los servicios
tienen la lógica y levantan `ServiceError`, sin saber de HTTP; los modelos son solo persistencia.
El worker de voz usa los mismos servicios que la API.

## Modelo de datos

```text
tiers 1───* clients 1───* agents 1───* agent_versions
                │ 1          │ 1
                │            └───* phone_numbers (agent_id, SET NULL)
                ├───* phone_numbers (client_id, SET NULL: vuelve al inventario)
                ├───* users (rol client)            users (rol admin: sin cliente)
                ├───* api_keys
                ├───* client_limit_adjustments (ajustes de límites del tier, CASCADE)
                ├───* contacts (agenda, archivable) 1───* campaign_contacts
                ├───* contact_optouts (bajas por teléfono y canal)
                ├───* campaigns (whatsapp | voice) 1───* campaign_contacts ───* call_logs (intentos de voz)
                │                                  1───* campaign_callbacks (cola del webhook)
                ├───* team_members ───* handoff_area_members *─── handoff_areas (equipo, CASCADE)
                │          └──────* phone_number_members *─── phone_numbers (quién atiende un número, CASCADE)
                ├───* user_presence (Disponible en el panel, 1 por usuario)
                ├───* events (registro; conversation_id, CASCADE)
                ├───* tools (herramientas del cliente) 1───* tool_versions
                ├───* wa_accounts (agent_id, RESTRICT) 1───* wa_routes (ruteo por contacto)
                │                                      1───* wa_threads
                └───* conversations 1───1 call_logs        (voz)
                         │          1───1 wa_threads       (whatsapp)
                         │          1───* wa_messages
                         │          1───* handoff_legs     (tramos a personas)
                         │          1───* call_rings       (timbre en el panel, directas entrantes)
                         └── agent_id + agent_version (la versión con que corrió)
```

| Tabla | Claves y reglas |
|---|---|
| `tiers` | `max_concurrent_calls`, `max_calls_per_hour`, `max_calls_per_day`, `max_calls_per_month` (llamadas entrantes y salientes por hora, día y mes calendario), `inbound_minutes`, `outbound_minutes`, `max_phone_numbers`; NULL = ilimitado. Campañas: `campaign_channels` (`[]`, `["whatsapp"]`, `["voice"]` o los dos), `max_campaigns_per_month`, `max_campaign_contacts`, `max_campaign_concurrency`, `max_contacts` (contactos activos de la agenda; NULL = ilimitado, 0 = no incluido) y `campaign_followup`. API de inferencia: `api_llm_input_tokens`, `api_llm_output_tokens`, `api_tts_minutes`, `api_stt_minutes` (por mes) y `api_rate_limit` (pedidos por minuto); NULL = ilimitado, 0 = no incluido. Equipo: `max_team_members` (personas para las derivaciones; NULL = ilimitado). `direct_calls` (llamadas directas: llamar y atender sin agente; migración 0039, en los planes con precio y a medida, no en el Free). |
| `clients` | `slug` único, `tier_id` (RESTRICT: un tier en uso no se borra), `active`, `direct_recording_notice` (aviso "Esta llamada está siendo grabada" en las directas; apagado). |
| `client_limit_adjustments` | Ajuste de un límite del tier para un cliente: `field` (uno de los 18 numéricos de `tiers`), `mode` (`add` suma, `set` reemplaza; `value` NULL = ilimitado solo con `set`), `starts_on`/`ends_on` (inclusive, en `BILLING_TIMEZONE`; sin fechas, permanente), `note`, `created_by`. Se resuelven en `services/limits.py`. |
| `agents` | `(client_id, slug)` único; `version` y `definition` vigentes (copia de la última versión); `archived_at`. |
| `agent_versions` | `(agent_id, version)`; inmutables, con `created_by`. |
| `phone_numbers` | `e164` único; `client_id` NULL = libre; `agent_id` solo si hay cliente (CHECK); `provider`, `assigned_at`. Quién atiende las entrantes (migración 0039): `answer_mode` (`team` o `agent`; los números que ya existían quedaron en `agent`, los nuevos y los liberados arrancan en `team`), y para `team`: `ring_first` (`phone` o `panel`, dónde suena primero), `ring_seconds` (timbre por persona, 5 a 60, default 20), `schedule` (NULL = siempre; el mismo formato que las áreas), `team_fallback` (`agent`, `voicemail` o `hangup`: qué pasa si nadie atiende o está fuera de horario) y `team_fallback_message`. Las personas, en `phone_number_members`. |
| `users` | `email` único; `role` admin o client (CHECK: client ⇔ `client_id`); hash argon2. |
| `api_keys` | SHA-256 de la clave (`key_hash` único), `prefix` visible, `revoked_at`, `scopes` (`calls`, `llm`, `stt`, `tts`, separados por coma: una key de inferencia no usa la API de llamadas ni al revés). |
| `api_usage_daily` | Consumo de la API de inferencia por `(client_id, api_key_id, day)` (día en `BILLING_TIMEZONE`): pedidos, tokens de entrada y salida del LLM y segundos de TTS y STT. Se suma con un UPDATE que incrementa. Sin contenido de los pedidos. |
| `conversations` | Estado del motor (datos, mensajes, progreso), `client_id`, `agent_id` + `agent_version` (RESTRICT: un cliente o agente con historial no se borra). `legacy_workflow_id` para las anteriores a los agentes. |
| `call_logs` | Una por conversación: modo, estado, teléfono del otro lado, `phone_number_id` del cliente, inicio, fin, duración, latencia. Base del consumo. `campaign_contact_id` ata el intento de una campaña de voz; `sip_status`, el código SIP de una saliente fallida. `room`, la room de LiveKit (la deja el worker): con ella `POST /calls/{id}/hangup` corta la llamada (`ended_reason=hangup_by_user`, que `finalize` no pisa). Directas (0039): `user_id` (quién llamó o atendió, FK `users`, SET NULL), `answered_by` (`agent` o `team` en las entrantes) y `opted_out_confirmed` (se llamó a un contacto dado de baja con confirmación); `mode=directa` es la saliente de una persona del equipo. |
| `conversations.channel` | `voice` o `whatsapp`; se fija al crearla. Cambia el prompt (reglas por canal), no el agente. |
| `wa_accounts` | Un número de WhatsApp: `phone_number_id` único (ID de Meta), `waba_id`, número visible, `client_id`, `agent_id`, `access_token` (NULL = `WA_ACCESS_TOKEN`; cifrado con `WA_TOKEN_KEY`, prefijo `fernet:`), `pin_enc`, `active`, `status` (`connected`, `pending`, `disconnected`) con motivo, `quality_rating`, `messaging_limit`, `source` (`manual`, `embedded_signup`, `coexistence`), `connected_by`. Sin borrado: se desactiva. |
| `wa_routes` | Ruteo por contacto de una cuenta (`account_id` + `agent_id` únicos): `contacts` (wa_id como los manda Meta) que atiende ese agente en los mensajes y las llamadas de WhatsApp, en vez del agente por defecto. Un contacto está en una sola regla; el agente es del cliente de la cuenta y no archivado. Se resuelve en `services/wa_routing.py`. |
| `wa_threads` | Una por conversación de WhatsApp (como `call_logs`): cuenta, `wa_id` tal cual llega (`549…`), nombre del perfil, `last_user_at` (ventana de sesión), `paused` (fase 3). |
| `contacts` | Agenda del cliente: `phone` (E.164) único por `client_id`, `name`, `email`, `notes` (nota libre, hasta 2000 caracteres), `source` (`manual`, `csv`, `api`, `campaign`, `inbound`) y `archived_at`. **No se borran, se archivan**; un archivado no se desarchiva solo al recargarlo. `max_contacts` cuenta los activos. |
| `blocked_numbers` | Teléfonos (E.164) que un cliente no atiende, por `(client_id, phone)`, con `note` y `created_by`: sus entrantes se cortan sin atender. No toca las salientes (eso son las bajas). API `/blocked-numbers`. |
| `contact_optouts` | Bajas por `(client_id, phone, channel)` con `channel` `whatsapp`, `voice` o `all` y `source` (`keyword`, `outcome`, `manual`). Aparte de `contacts` a propósito: sigue aunque el contacto se archive o no exista. Reemplaza a `wa_optouts`. |
| `campaigns` | Campaña de un cliente con `channel` `whatsapp` o `voice` (un CHECK exige los campos de cada canal), `status` (`draft`, `scheduled`, `running`, `paused`, `done`, `cancelled`) con motivo, `rate_per_minute`, horario (`window_start`, `window_end`, `weekdays`), programación (`starts_at`, `ends_at`), `started_at`/`finished_at`, `purpose` (`comercial`, `cobranza`, `turnos`, `aviso`) con `no_call_confirmed_at`, y `callback_url` / `callback_secret` (cifrado). WhatsApp: número (`account_id`), copia de la plantilla y `template_param_names`. Voz: `from_number_id`, `voice`, `concurrency` (1 = secuencial), `max_attempts`, `retry_minutes`, `retry_on` y `followup` (JSON, NULL = apagado). Reemplaza a `wa_campaigns`; las existentes conservan su id. |
| `campaign_contacts` | Un contacto en una campaña (`campaign_id` + `contact_id` únicos): `vars` (copia de sus datos al agregarlo; WhatsApp guarda los parámetros en `vars["params"]`), `status` (`pending`, `in_progress`, `retry`, `done`, `failed`, `skipped`), `result` (WhatsApp: `sent`; voz: `answered`, `no_answer`, `busy`, `voicemail`, `invalid`, `rejected`, `failed`), `error`, `conversation_id`, y según el canal `wamid`/`sent_at`/`replied_at` o `attempts`/`next_attempt_at`/`last_attempt_at` y el seguimiento (`followup_status`, `followup_wamid`, `followup_sent_at`, `followup_error`, `followup_conversation_id`). Entregado y leído salen de `wa_messages`. Reemplaza a `wa_campaign_recipients`. |
| `campaign_callbacks` | Cola del webhook (outbox): `campaign_id`, `event` (`contact.finished`, `contact.followup`, `campaign.finished`), cuerpo, `status` (`pending`, `sent`, `failed`), intentos y próximo intento. Se escribe en la misma transacción que el evento. |
| `contact_requests` | Pedidos del formulario de contacto de la landing (`POST /api/v1/demo/contact`), con `email_status` (`sent`, `failed`, `disabled`) y `email_error`; se guardan aunque Resend falle ([`LANDING.md`](LANDING.md)). |
| `tools` | Herramienta del cliente ([`TOOLS_PLAN.md`](TOOLS_PLAN.md)): `client_id` + `slug` únicos, `type` (`http` o `code`), `definition`, `revision` y el resultado de la última prueba (`last_test_*`). Cada revisión queda en `tool_versions` (migración 0033; `GET /clients/{id}/tools/{slug}/versions`). |
| `agent_secrets` | Secretos de un agente para sus herramientas: `agent_id` + `name` únicos, `value_enc` (cifrado), `last4`, `description`. |
| `team_members` | Persona del equipo del cliente: `name`, `phone` (E.164, al que se le pasa la llamada), `whatsapp` (único por cliente, para el puente de la fase 3), `user_id` opcional, `active`. Tope `tiers.max_team_members` (NULL = ilimitado). |
| `handoff_areas` | Área del equipo (Ventas, Soporte): `description`, `active`, `strategy` (`sequential` o `round_robin`, con `last_member_id`), `ring_seconds` por miembro, `schedule` (NULL = siempre abierta), `fallback`, `on_person_hangup` (`resume` o `goodbye`), `return_digits` (default `2`, nunca `*`), `messages` (los textos que pisan los de `handoff.DEFAULT_MESSAGES`). Un área que usa un agente no se borra (409 `area_in_use`). Miembros y orden en `handoff_area_members` (`position`). |
| `handoff_legs` | Un intento de pasarle la llamada a una persona: `area_id`, `team_member_id`, `phone`, `result` (`dialing`, `connected`, `no_answer`, `busy`, `machine`, `not_confirmed`, `failed`), `sip_status`, `answered_at`, `connected_at`, `ended_at` y `billed_seconds` (desde que atendió, solo si se conectó). Base de los minutos salientes de las derivaciones. |
| `phone_number_members` | Las personas que atienden un número con `answer_mode=team`: `(phone_number_id, member_id)` y `position` (el orden en que suenan). Solo del equipo del mismo cliente y con celular o usuario del panel; liberar el número las borra. |
| `user_presence` | Disponible en el panel para atender: `user_id` (PK), `client_id` y `last_seen`, el último pulso (`PUT /me/presence`, cada ~20 s). Disponible = pulso en los últimos `PRESENCE_TTL_SECONDS` (60); ocupado = tiene una llamada activa con su `user_id`. |
| `call_rings` | El timbre en el panel de una entrante al equipo: `conversation_id`, `user_id`, `status` (`ringing`, `answered`, `declined`, `cancelled`), `created_at` y `ended_at`; uno por usuario y llamada (`uq_call_rings_conversation_user`). El primero que atiende (`UPDATE` condicional sobre `ringing`) se queda con la llamada. |
| `events` | Registro de lo que pasa (`id` incremental, `at`, `type` de `services/events.TYPES`, `actor`, `conversation_id`, `area_id`, `team_member_id`, `data`): `call.ringing`, `call.answered`, `call.ended` y los `handoff.*` y `hold.*`. Se lee por `GET /events` con cursor `after_id`. |
| `wa_messages` | Uno por `wamid` (unique: dedupe de reenvíos de Meta), entrante o saliente, tipo (`text`, `audio`, ...), estado y error de Meta. Sin texto ni audio: el texto está en `conversations.messages`, donde `voice_note` marca la transcripción de una nota de voz o la respuesta enviada como nota de voz. |

Las fechas se guardan en UTC sin zona; la API las devuelve con zona (`+00:00`/`Z`).

**Migraciones:** el esquema lo manejan las migraciones de Alembic (`make migrate`). Un cambio de
modelo va con una migración nueva en `migrations/versions/` (probada de ida y vuelta en PostgreSQL
y SQLite); `alembic check` tiene que decir que no hay diferencias. `create_all` queda solo para
SQLite en tests y el eval.

## Definición de un agente

La definición es un workflow en JSON (`app/conversation/models.py`, clase `Workflow`; JSON Schema en
`GET /api/v1/agents/schema`):

```json
{
  "id": "ventas", "version": 3, "record_audio": false,
  "generation": {"params": {"temperature": 0.5, "enable_thinking": false}},
  "agent": {"name": "Sofía", "role": "asesora comercial", "language": "es-AR", "voice": "sofia"},
  "objective": {"description": "…"},
  "conversation": {"opening": "Hola, te habla Sofía…", "rules": ["…"]},
  "knowledge": "…",
  "fields": {
    "contact_name": {"priority": 10, "description": "Nombre", "type": "string", "required": true,
                     "question": "¿Con quién hablo?"},
    "wants_demo": {"priority": 20, "description": "Quiere una demo", "type": "boolean", "required": true,
                   "question": "¿Te interesa ver una demo?"}
  },
  "completion": {"outcomes": [
    {"id": "demo", "label": "Pide demo", "when": {"wants_demo": true}, "message": "…", "goal": true},
    {"id": "otro", "label": "Sin demo", "message": "…"}
  ]}
}
```

- `id` y `version` los fija la app: el slug del agente y el número de versión. Van al prompt.
- **`generation`** (opcional): parámetros de generación del LLM (temperatura, `top_p`/`top_k`/`min_p`,
  razonamiento y su tope, `max_tokens`, esfuerzo), con un default para todo el agente
  (`Workflow.generation`) y override por etapa (`LlmStage.generation`). Son las claves del catálogo
  (`app/llm/params.py`): el proveedor activo manda solo las que soporta y descarta el resto
  (`enable_thinking`/`top_k` solo el servidor propio, `effort` solo Anthropic, `reasoning_effort`
  OpenAI/OpenRouter). Sin `generation`, rigen los defaults de la configuración
  (`LLM_THINKING`/`LLM_THINKING_BUDGET` y `LLM_TEMPERATURE`/`LLM_TOP_P`/`LLM_TOP_K`/`LLM_MIN_P`; los de
  Gemma, en su override de compose; desde el 26-oct-2026 no hay muestreo por familia en el código). El editor los agrega y quita, con los defaults del
  proveedor (`GET /api/v1/llm/params`). Ver [`BYOK_LLM_PLAN.md`](BYOK_LLM_PLAN.md).
- **Un solo motor** (26-oct-2026, [`LIMPIEZA_PLAN.md`](LIMPIEZA_PLAN.md)): `engine` ya no existe; el de
  una definición vieja (`classic`, `structured`, `assistant`, `external`) se ignora al leerla, igual que las
  herramientas de apps (`{app, tools}`). Los motores `structured` y `assistant` se quitaron ese día.
- **`tools`** y **`tool_settings`**: las herramientas del cliente por slug (`[{"tool": "<slug>"}]`,
  [`TOOLS_PLAN.md`](TOOLS_PLAN.md)) y, opcional, `max_calls_per_turn` (default 3, hasta 10) y
  `limit_message`: al llegar al tope, el turno termina con ese mensaje sin volver al modelo. No van con
  `external`.
- **`external`** (opcional): "Tu propio agente" ([`AGENTE_EXTERNO_PLAN.md`](AGENTE_EXTERNO_PLAN.md)). Cada
  turno lo contesta el endpoint del cliente (`connection`, `model`, `system`, `first_token_timeout_ms`,
  `error_message`, `max_errors`, `on_errors` `hang_up` o `transfer:<area_id>`), sin el prompt de la
  definición ni extracción. Es una opción del agente, no un motor; solo en los planes con
  `tiers.external_agent`.
- **Variables `{{today}}` y `{{now}}`**: la fecha no se inyecta en el prompt; el agente la tiene si sus
  reglas, su base de conocimiento o su objetivo usan esas variables.
- `fields.<campo>.label` (opcional): nombre del dato para mostrarlo (resultado de la demo de la
  landing). No va al prompt.
- **`conversation.opening_audio`** (default `false`) y **`conversation.opening_delay_ms`**
  (default 200): en las llamadas, la apertura pregenerada y la espera antes de que hable el agente.
  En vivo, el TTS de LiveKit sintetiza frase por frase y cada una suena sin el contexto de las
  otras; con la bandera, al crear o guardar el agente `app` sintetiza la apertura entera en un solo
  pedido (en segundo plano, después de responder) y la deja en
  `storage/openings/<agent_id>/<versión>-<voz>.wav` (`OPENING_AUDIO_DIR`). El worker la reproduce
  si coinciden versión, voz y texto; si no (falló el TTS, todavía se genera, la llamada eligió
  otra voz, la apertura tiene `{{variables}}`), la sintetiza en vivo. Se graba igual que la
  apertura en vivo. Al cambiar el checkpoint del TTS hay que borrar `storage/openings/` o volver a
  guardar los agentes. Código en `app/conversation/opening_audio.py`.
- **`call_summary_email`** (default `false`): al terminar cada llamada (entrante, saliente suelta o por el
  link, que se conectó; no las de campaña, prueba ni loadtest), Atentina le manda al cliente un email
  con los datos tomados, el resultado, la conversación (hasta `CALL_SUMMARY_TRANSCRIPT_CHARS`) y el link a
  la llamada. El worker deja `call_logs.summary_email = pending` y un loop de `app` lo manda por Resend
  (`app/mail/call_summary.py`, cada `CALL_SUMMARY_TICK_SECONDS`), con 4 intentos (ya, 1 min, 10 min, 1 h)
  e `Idempotency-Key` por llamada y destino. El cliente lo apaga para todos sus agentes y elige los
  destinos en Mi cuenta (`clients.call_emails`, `clients.call_emails_to`; vacío = sus usuarios
  activos; API `GET/PUT /api/v1/clients/{id}/call-emails`). Estados: `sent`, `disabled` (sin
  `RESEND_API_KEY`), `skipped` (apagado o sin destinos) y `failed`.
  El email lleva el teléfono: el de la llamada o, por el link (sin número), el que dio la persona en un
  dato de tipo `phone`. Ese tipo se precarga con el número de la otra punta en las entrantes y salientes
  (`engine.new_conversation(phone=...)`, va a `progress.preloaded`) y el agente no lo pregunta; por el link
  queda vacío y lo pide. Al prender el resumen en el editor se agrega el dato `telefono` si el agente no
  tiene uno. Sin recordatorio oculto desde el 26-oct-2026: el teléfono es un dato más del agente. Con el
  recordatorio (`PHONE_REMINDER`, quitado) Gemma 4 26B lo pedía 9 de 10 al cierre; sin él, 0 de 10
  (20-oct-2026); sin medir con las reglas genéricas de la plantilla.
- **`record_audio`** (default `false`): graba el audio, un WAV mono de 16 kHz por mensaje,
  localmente (`CALL_RECORDINGS_DIR`, default `storage/recordings/<conversation_id>/NNN.wav`;
  `storage/` montado en `agent`, no versionado). Lo escribe `app/conversation/recordings.py`
  (lo comparten los dos caminos). Aplica a:
  - **Llamadas** (telefónica o de WhatsApp, mismo agente de voz): un WAV por lado. El cliente y
    el agente van en archivos separados: uno con lo que dijo el cliente desde el turno anterior y
    otro con esta respuesta (o la apertura, en el primer turno); el número queda en el
    `Message.recording` de cada uno para escucharlo en el chat (`app/voice/worker.py`,
    `WorkflowAgent.stt_node`/`tts_node` y `_tag_recording`). El stream del cliente es continuo (el
    micrófono, con o sin voz), así que el WAV se recorta a lo que el VAD marcó como habla
    (`user_state_changed`, con 0,3 s de pre-roll): sin el playout del agente antes ni la latencia y
    la síntesis de la respuesta después. Si el cliente interrumpe una respuesta
    recién empezada, el motor deshace ese turno (`settle_last_reply`, caso de `c5fa81cd`) y el WAV
    pendiente se descarta: ese audio del cliente vuelve al turno siguiente en vez de quedar en un
    archivo aparte. Si al cortar quedó audio del cliente que el motor no procesó, se guarda igual,
    sin mensaje asociado.
  - **WhatsApp (mensajería)**: el audio entrante que se transcribe y la nota de voz que se manda
    (`app/whatsapp/service.py`). El entrante queda en el `Message.recording` del mensaje del
    usuario (el PCM que devuelve el STT, sin decodificar dos veces) y la nota de voz saliente en el
    de la respuesta; si la respuesta sale en texto (TTS caído, o un turno sin audio en `mirror`),
    no hay WAV del agente. Un turno con varios audios del cliente los une en un solo WAV (van en un
    mismo mensaje del motor).

  Con backup desde el 21-oct-2026 (`storage/` en `scripts/ops/backup.sh`). Se escucha desde el dashboard:
  `ChatView` (web/) muestra el reproductor en la burbuja de cada mensaje grabado, servido por
  `GET /api/v1/calls/{conversation_id}/recordings/{n}` con el mismo control de acceso que el
  resto del detalle (`CallDetail.recordings` sigue listando los archivos).
- **`recording_notice`** (default `false`, desde el 23-oct-2026): con `record_audio`, el agente dice
  "Esta llamada está siendo grabada." antes de la apertura (`RECORDING_NOTICE` en `app/voice/worker.py`), en
  todas las llamadas del agente; no se agrega al contexto del LLM. Sin `record_audio` no hace nada (la UI
  muestra el switch "Avisar que la llamada se graba" solo con la grabación prendida). En WhatsApp
  (mensajería) no aplica.
- **`handoff`** (desde el 23-oct-2026): las áreas
  (`area_id` y `when`, el cuándo en texto libre; vacío usa la descripción del área), hasta 10 y sin repetir, y la
  música de espera (`hold_music`: `enabled`, `track` de `GET /hold-music`, `volume`). Al guardar se valida que
  cada área sea del cliente del agente y que el tema exista. El modelo deriva con la herramienta de
  plataforma `transfer_call` (también con `external`). Ver "Derivación a una persona" en Flujos.
- **Validación al guardar:**
  - nombres de campo en minúsculas;
  - `choice` con `options`;
  - `required_if` y `when` sobre campos existentes;
  - ids de resultado únicos;
  - el último resultado sin `when` (es el default);
  - `agent.voice` en el catálogo, y nunca `default`, que tumba el TTS.
- **Versionado:** `PUT /agents/{id}/definition` crea la versión N+1 si cambió algo (con lock del
  agente). La conversación guarda `agent_version` y el motor carga siempre esa versión
  (`DbDefinitions`, cacheada por `(agent_id, version)`). Editar un agente no afecta las llamadas en
  curso ni el historial.
- **Alta:** en blanco (`blank_definition`: un dato y el resultado por defecto) o desde la única
  plantilla, `app/agents/templates/asistente.json`, con las reglas genéricas de comportamiento
  (`GENERIC_RULES` en `app/agents/templates.py`: una pregunta por turno, no inventar, cuándo cortar o derivar),
  editables como cualquier regla. El prompt de sistema sale siempre de la definición y del protocolo
  (herramientas y su resultado), sin frases de comportamiento en el código; `POST /agents/prompt` lo devuelve sin guardar. La UI la edita por formulario (`web/src/features/agents/DefinitionForm.tsx`,
  `draft.ts`), con el JSON como alternativa.
- **Quién los crea:** un admin, en el cliente de `client_id`; un usuario o API key de un cliente, en
  el suyo (`client_id` se omite; el de otro cliente da 404). Todo pedido sobre un agente pasa por
  `get_agent` (`app/api/routers/agents.py`): el de otro cliente responde 404 y no cambia. En la UI el
  cliente usa el mismo formulario, sin cliente, slug, JSON ni prompt, que son internos. La UI no
  pregunta motor; `AgentOut.own_agent` dice si el agente usa "Tu propio agente". `POST /agents/prompt`
  sigue solo para admin.
- **Agentes de referencia:** `app/agents/reference/<id>.json`, para el seed, el eval y los tests (sin
  base); no se ofrecen en la UI. El sufijo `_classic` se acepta por compatibilidad
  (`demo_booking_classic` es `demo_booking.json`). El seed solo crea, en
  el cliente `atentina`, `atentina_comercial`, `demo_booking_classic` (test de capacidad) y las
  `landing_*` (demo).

## Flujos

### Llamada saliente o de prueba (`POST /api/v1/calls`)

1. El router resuelve el `Principal`. `services/calls.prepare_call` corre en un thread, porque la
   base es bloqueante. Valida el agente (visible y no archivado), el teléfono E.164 y la voz, y elige
   el caller ID (el número pedido o el primero del cliente). Con `contact_id` (pantalla Llamadas), el
   contacto tiene que ser del cliente del agente y estar activo: sin `phone`, marca el suyo, y sus datos van
   como los `vars` de una campaña. Un teléfono en las bajas de voz del cliente da 409 (`opted_out`), salvo en
   campañas, que filtran antes.
2. `engine.new_conversation(session=s)` arma el estado con la versión vigente, sin guardarlo. `context` (el
   motivo, hasta 2000 caracteres) queda en `Progress.context` y va al prompt y al de
   extracción como "MOTIVO DEL LLAMADO" (`conversation/contact.py`); se ve en el detalle y en el resumen por email.
3. `quota.admit(s, client, mode)` toma el lock del cliente (`SELECT … FOR NO KEY UPDATE OF clients`).
   Verifica que el cliente esté activo, que haya lugar en el tope de simultáneas, que no se hayan
   agotado los topes de llamadas por hora, día y mes (solo entrantes y salientes; cuenta `call_logs`
   por `created_at` sin las `rechazada`) y que queden minutos de esa modalidad. Devuelve los segundos que quedan.
4. En la misma transacción se guardan la conversación y la `call_logs` (`pendiente`), y el commit
   suelta el lock. Todo va por una sola conexión: pedir otra con el lock tomado agotaba el pool bajo
   carga.
5. `livekit.dispatch_call` crea el dispatch con la metadata `{conversation_id, phone, voice,
   loadtest, max_duration_seconds, from_number}`. Si falla, la llamada queda `fallida`
   (`dispatch_failed`) y la API responde 502.
6. El worker marca por SIP (`create_sip_participant` con `max_call_duration` y `sip_number`) o, en
   prueba, espera al participante del navegador.
7. Estados de la llamada: `sonando` → `en_curso` → `finalizada` (con duración y latencia) o `fallida`; la directa que el usuario corta antes de que atiendan queda `cancelada`.

### Campaña de llamadas (`/api/v1/campaigns`, `channel: voice`)

1. Se crea en `draft` (agente, número de origen, voz, horario, `concurrency`, reintentos) y se le suman
   contactos de la agenda (`contact_ids`), una lista o un CSV. `start` valida el plan del tier,
   el agente, el número y el horario; una campaña `comercial` pide además confirmar el Registro No Llame.
2. `app/campaigns/loop.py` (en el lifespan de `app`) delega por canal: el `CampaignSender` de WhatsApp
   cada `WA_CAMPAIGN_TICK_SECONDS` y el **dialer** cada `CALL_CAMPAIGN_TICK_SECONDS` (2 s).
3. El dialer, por cada campaña de voz `running`: activa las `scheduled` y cierra las vencidas, respeta
   horario, días y feriados, y toma `min(concurrency − en curso, crédito de rate_per_minute,
   CALL_CAMPAIGN_MAX_CONCURRENT − en curso global)` contactos `pending`/`retry` con `FOR UPDATE SKIP LOCKED`.
   Saltea bajas de voz y archivados, y llama a `start_call` (el flujo de arriba, con `quota.admit`) con
   `campaign_contact_id` y `vars`. Sin lugar por concurrencia el contacto vuelve a `pending` sin gastar el
   intento; sin minutos, tope de llamadas, agente archivado o número suspendido, la campaña se pausa con el motivo.
4. `prepare_call` ata la `CallRow` al contacto y `engine.new_conversation(..., contact=vars)` reemplaza
   `{{variable}}` en la apertura, precarga los campos con nombre igual y pasa el resto al prompt
   (solo en llamadas de campaña).
5. El worker marca con `ringing_timeout` (`CALL_RINGING_TIMEOUT_SECONDS`) y clasifica el error SIP
   (`sip_status_code`) en `no_answer`, `busy`, `invalid`, `rejected` o `failed`; un detector de contestador
   sobre las primeras transcripciones cierra el intento como `voicemail`. `services/campaign_calls.py` deja
   el contacto en `done`, `retry` (a los `retry_minutes`) o `failed`, y si el outcome está marcado
   `no_contact` agrega la baja de voz. Sin nada pendiente, la campaña pasa a `done`.
6. Los `in_progress` sin llamada activa vuelven a `retry` al arrancar `app` y cada 60 s. N intentos
   `failed` seguidos (`CALL_CAMPAIGN_FAILURE_STREAK`) pausan la campaña.
7. Con `followup`, a quien no atendió se le manda por el `CampaignSender` una plantilla de WhatsApp;
   su respuesta abre la conversación (5.5 de [`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md) y
   [`LLAMADAS_SALIENTES_PLAN.md`](LLAMADAS_SALIENTES_PLAN.md), sección 14). Con `callback_url`, cada
   contacto terminado y el cierre de la campaña se entregan por `callback_loop` (POST con firma
   `X-Atentina-Signature`, https y host público, reintentos de 30 s a 6 h).

### Demo de la landing (`/api/v1/demo`)

Llamada de prueba sin usuario, para la landing (ver [`LANDING.md`](LANDING.md)):

1. `POST /demo/sessions` valida el token de Cloudflare Turnstile y devuelve una sesión JWT
   (`aud=atentina-demo`, firmada con `AUTH_SECRET`; no sirve como sesión de la UI).
2. `POST /demo/calls` aplica los límites por IP (en memoria) y el cupo diario de minutos, y llama a
   `calls.start_call` con un `Principal` del cliente `DEMO_CLIENT` (`atentina`), solo para los agentes
   de `DEMO_AGENTS`, con tope de `DEMO_MAX_CONCURRENT_CALLS` entre ellos: misma admisión por tier y misma
   metadata, más `max_duration_seconds` (`DEMO_CALL_MAX_SECONDS`) y `join_timeout_seconds`.
3. Devuelve el token de LiveKit del visitante (con vencimiento) y un `result_token` (JWT con el id de
   la conversación) para `GET /demo/calls/{id}`.
4. En llamadas sin teléfono, el worker corta al llegar a `max_duration_seconds` con
   `QUOTA_END_MESSAGE` (`ended_reason=max_duration`).

El formulario de contacto de la landing (`POST /demo/contact`, misma sesión) guarda el pedido en
`contact_requests` y avisa por mail con Resend (`app/services/contact.py`).

### Llamada entrante

1. Anura → Asterisk → trunk entrante de LiveKit → la dispatch rule crea una room `anura-*` y
   despacha el worker sin metadata.
2. El worker espera al participante SIP y lee el número marcado (`sip.trunkPhoneNumber`).
   `calls.start_inbound` lo busca en `phone_numbers`:
   - **libre, o sin agente y sin equipo que atienda:** se corta (`number_without_agent`);
   - **el que llama está bloqueado por el cliente** (`blocked_numbers`, por el caller o el `wa.wacid`,
     normalizados): se corta sin atender y queda `rechazada` (`blocked_number`);
   - **sin lugar o sin minutos:** queda `rechazada` y el que llama escucha `QUOTA_REJECT_MESSAGE`;
   - **número con `answer_mode=team`** (y personas, plan con `direct_calls` y condiciones `2026-10-28` o posteriores aceptadas): conversación **sin agente**
     (`answered_by=team`), `InboundCall.team` con el ruteo y el worker toma la rama de las llamadas directas
     (ver "Llamadas directas"). Sin personas, si el plan perdió la función o el cliente no aceptó las condiciones `2026-10-28` o posteriores (`legal_gate`), va al agente del número; una
     regla de `wa_routes` que elige agente gana sobre el equipo;
   - **si no:** conversación con el agente del número y llamada `entrante` (`answered_by=agent`).
   En una llamada de WhatsApp el inbound trunk mapea el header `X-WA-Meta-Wacid` al atributo `wa.wacid`
   (lo agrega el predial de Asterisk) y, si el llamante tiene regla de ruteo en la cuenta de ese número,
   la atiende el agente de la regla; sin regla, el del número (ver "Mensaje de WhatsApp").
3. Anura manda el número marcado (formato nacional con 0) y Asterisk lo pasa a LiveKit como `+54` + 10
   dígitos; sin un número válido usa `+54<ANURA_DID>`. Un número que no está en el inbound trunk
   (`make livekit-sip`) da 404 (ver [`TELEFONIA_ANURA.md`](TELEFONIA_ANURA.md), sección 1).

### Mensaje de WhatsApp

1. Meta → túnel (`wa.atentina.com.ar/wa/webhook`) → `app`. Se valida la firma
   (`X-Hub-Signature-256`, 403 si no) y se responde 200 sin esperar a la base ni al LLM.
2. `WhatsAppService` registra el `wamid` (si ya estaba, es un reenvío y termina), busca la cuenta por
   `phone_number_id` (inactiva, cliente inactivo o desconocida: `ignored`) y junta los textos del
   contacto durante `WA_DEBOUNCE_SECONDS`. Un audio se baja por la API de media, se pasa a WAV de
   16 kHz con PyAV y se transcribe con `stt-parakeet`; el texto entra al mismo debounce, marcado como
   nota de voz, y el turno espera a que termine.
3. Con el lock del contacto: el hilo abierto (`WhatsAppService._active_thread`, sobre `store.open_thread`:
   sin cerrar, sin pausar y dentro de su ventana de contexto temporal) o uno nuevo sin apertura,
   `process_turn`, `send_text` y `mark_read`. La ventana es `Workflow.wa_session_minutes` del agente
   que abrió el hilo si la definió (en minutos), o si no el default global `WA_SESSION_HOURS`
   (1440 min = 24 hs, `WhatsAppService._session_minutes`): pasados esos minutos sin mensaje del
   contacto, el siguiente mensaje abre otra conversación, sin el historial anterior. Se edita por
   agente en la UI (sección "Voz" del editor, en minutos) o en su `definition`. Que el agente haya
   dado la conversación por completada (`end_call`) **no**
   cierra el hilo: un mensaje después del cierre la retoma con el historial y la misma versión del
   agente. Un hilo nuevo usa la versión vigente del agente del número, o la del agente de la campaña
   si el contacto responde a una (ver [`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md), 5.5).
   El motor trabaja igual que en una llamada (el clásico no extrae en cada turno). El equivalente del
   corte es el fin del chat: cerrarlo desde el dashboard, llegar a `WA_MAX_TURNS` o vencer su ventana
   de contexto (barrido cada 5 min en el lifespan de `app`, `WhatsAppService.sweep`: mira todos los
   hilos abiertos y cierra el que venció según el agente que lo abrió). Los
   tres cierran el hilo (`wa_threads.closed_at`) y llaman a `engine.finish`, la extracción final.
   Si el turno tuvo audio (`WA_AUDIO_REPLY=mirror`), `process_turn` recibe `TurnMedia` (el mensaje del usuario va marcado como
   nota de voz) y la respuesta sale como nota de voz: normalizador de texto (`app/voice/speech_text.py`) →
   `vllm-tts` → OGG/Opus → subida →
   mensaje `audio`. Si algo falla, va en texto.
4. Los statuses actualizan `wa_messages`. No se crea `call_logs` ni se pasa por `quota.admit`.

**Ruteo por contacto (`wa_routes`):** debajo de las campañas, si el `wa_id` está en la regla
de un agente de esa cuenta, lo atiende ese agente, en los mensajes y las llamadas de WhatsApp. Un
hilo abierto con otro agente se corta y sigue en una conversación nueva; uno
abierto por una campaña no se pisa. Un agente archivado se saltea y vuelve el de la cuenta. Los operadores
de WhatsApp (`wa_operators`), que ganaban sobre todo esto, se quitaron el 26-oct-2026 con las apps.

### Herramientas del cliente

Diseño, formato y mediciones en [`TOOLS_PLAN.md`](TOOLS_PLAN.md); lo que se quitó el 26-oct-2026 (motor
`assistant` y apps por cliente, con su historia en [`archive/APPS.md`](archive/APPS.md)), en
[`LIMPIEZA_PLAN.md`](LIMPIEZA_PLAN.md). En corto:

- El modelo ve, por function calling nativo, las herramientas del cliente (`http` y `code`, `app/tools/`) y
  las de la plataforma (`end_call` y, en una llamada con áreas, `transfer_call`; `app/llm/platform_tools.py`).
- La plataforma no confirma ni interpreta: `confirm` solo agrega a la descripción que se pida confirmación;
  el resultado (`ok`, `error`) vuelve al modelo. `messages.failed` lo dice la plataforma por el TTS.
- Tope de rondas por turno (`tool_settings.max_calls_per_turn`): al llegar, el turno termina con
  `limit_message`. Las duplicadas las protege el `Idempotency-Key`.
- Seguridad: SSRF con un backend de red propio en un `httpcore.AsyncConnectionPool` (API pública de
  httpcore): resuelve y conecta a una IP global ya validada, sin redirects ni proxies del entorno.
  `runtime.PRIVATE_HOSTS` deja pasar hosts internos solo en los tests y el e2e (`TOOLS_PRIVATE_HOSTS` ya
  no es configuración). Secretos cifrados por agente y el sandbox `tools-runner` con salida por
  `tools-egress`.

**Capacidad:** un turno de texto carga solo el LLM (3090); uno con audio usa además el STT y el TTS,
y la síntesis va a la 5060 Ti, el cuello de CAP-002. `WA_AUDIO_CONCURRENCY` (4, sin medir) limita los
pedidos simultáneos, por separado al STT y al TTS, y cada pedido tiene un tope total (45 y 90 s). Pendiente de medir con un perfil del test de capacidad (ver
[`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md), sección 2).

**Un solo worker de uvicorn:** el debounce y el lock por contacto están en memoria; con más de un
worker se rompen. Si se reinicia `app` con mensajes en la ventana, esos entrantes quedan `received`
sin respuesta.

### Derivación a una persona (`Workflow.handoff`)

Transferencia atendida dentro de la misma room de LiveKit; diseño, mediciones y pruebas en
[`DERIVACIONES_PLAN.md`](DERIVACIONES_PLAN.md) (secciones 4, 11 y 13).

1. **Al empezar**, el worker guarda las áreas activas del agente en `Progress.handoff_areas`
   (`handoff.call_areas`), salvo en el loadtest, las campañas y la demo sin `DEMO_HANDOFF` (metadata
   `handoff`, de `calls.start_call`). Sin áreas no cambia nada.
2. **Herramienta `transfer_call`:** el modelo la ve con cada área (cuándo pasarla, su horario y si atiende
   ahora) y la llama con `area` (un `enum` con los nombres; sin búsqueda aproximada). El worker dice lo que el
   modelo escribió en ese mensaje y después deriva. Hasta el 26-oct-2026 era la marca `[DERIVAR:<área>]`.
3. **Transferencia** (`app/voice/handoff.py`): revisa el área (activa, en horario, con miembros), los minutos
   salientes y los canales (`quota.handoff_check`); pone música solo al cliente y apaga su entrada de audio;
   llama a cada miembro (`create_sip_participant`, identidad `persona-<n>`, caller ID el número de la empresa)
   con el timbre del área; al atender, detecta buzón por STT (3 s) y le dice el resumen (whisper, solo a la
   persona); con el `1` en `HANDOFF_CONFIRM_SECONDS` (8) los conecta. Cada intento es un `handoff_legs`.
   El aislamiento de audio es por suscripciones y permisos de pistas.
4. **Modo escucha:** el worker transcribe a los dos (VAD + STT) en la conversación, con `Message.handoff_leg`
   y `Message.person`; con `record_audio`, un WAV por frase. Termina con el código de vuelta del área
   (`2`: vuelve la IA con "¿Te puedo ayudar con algo más?"), si la persona corta (`resume` o `goodbye`),
   si corta el cliente (se borra la room) o sin minutos salientes.
5. **Si nadie atiende**, el agente dice el mensaje del área (`no_answer` o `busy`) y el LLM sigue con el
   mensaje en el contexto (toma el recado).

Todo queda en `events` (`handoff.*`, `hold.*`). Los mensajes de cada paso son configurables por área
(`GET /handoff-areas/defaults` trae los de fábrica).

### Llamadas directas (el equipo llama y atiende, sin agente)

Diseño, decisiones y contrato en [`LLAMADAS_DIRECTAS_PLAN.md`](LLAMADAS_DIRECTAS_PLAN.md) (secciones 4, 5 y 13).
No hay `AgentSession` ni LLM: el worker hace VAD y STT por frase (`app/voice/listen.py`, el `Listener` que usa
también el modo escucha de la derivación) y el TTS solo para avisos y mensajes. Pasan por `quota.admit` como
cualquier llamada. Las dos graban **siempre** (un WAV de 16 kHz por frase, `Message.recording`, sin mirar
`record_audio`) y quedan en Conversaciones con transcripción, duración, resultado y minutos.

**Saliente** (`POST /api/v1/direct-calls`, `app/services/direct_calls.py`):

1. Valida plan (`direct_calls`, 429 `direct_calls_not_in_plan`; además `outbound_calls`), que el cliente haya aceptado las
   condiciones `2026-10-28` o posteriores (las que cubren la grabación siempre; 403 `terms_pending`, `app/services/legal_gate.py`), contacto del cliente,
   bloqueado (403 `blocked_number`) y baja de voz (409 `opted_out`, salvo `confirm_opted_out: true`, que queda
   en `call_logs.opted_out_confirmed`). Admite como `CallMode.directa` (minutos **salientes** y un canal de
   Anura), crea la conversación con `agent_id` nulo y la `call_logs` con `user_id`, y despacha el worker con
   metadata `direct`.
2. Quién llama es un usuario del cliente. Con la sesión del panel, la respuesta trae el token de LiveKit
   (`livekit.user_participant_token`, identidad `user-<user_id>`). Con API key o MCP va `user_id` (422
   `user_required` / `invalid_user`; por OAuth del MCP, sin `user_id`, el usuario que autorizó), `token` es nulo y `join_url` es la página del panel
   (`/telefono/llamada/<id>`) que entra con la sesión de ese usuario (otro usuario: 403 `not_your_call`). Volver a
   entrar tras recargar: `POST /direct-calls/{id}/join` (409 `call_not_active`). Cortar: `POST /calls/{id}/hangup`.
3. `direct.run_outbound` espera al usuario en la room (`join_timeout_seconds`: 30 s desde el panel, 120 s por
   API o MCP; si no, `fallida` con `user_not_joined`) y marca al contacto con `wait_until_answered=False`. El
   panel sigue el estado por datos de la room (tema `call_status`: `joining`, `dialing`, `ringing`, `active`,
   `ended`) y la transcripción en vivo (tema `transcript`).
4. Al atender el contacto: `en_curso`, minutos desde ahí y, si el cliente lo prendió, el aviso de grabación
   (WAV sintetizado la primera vez y guardado en `storage/notices/<voz>.wav`, `NOTICE_AUDIO_DIR`). Cada frase
   es un mensaje: el contacto como `user`, el usuario como `assistant` con `person`. Termina por `customer_hangup`,
   `person_hangup`, `max_duration`, `quota_exhausted` o `hangup_by_user`; si el usuario corta antes de que atiendan,
   `cancelada` (`hangup_by_user` o `person_hangup`); sin atender, `fallida` con
   `no_answer`, `busy` o `sip_call_failed` (`campaign_calls.classify_error`).

**Entrante al equipo** (`phone_numbers.answer_mode=team`, `app/voice/direct.py`, `TeamCall`):

1. Si hay aviso de grabación, suena al que llama; fuera de horario (`schedule`), va directo al respaldo
   (`after_hours`). Si no, música de espera (la de la derivación) y suenan las personas del número en el orden
   de `ring_first`:
   - **`phone`:** a cada persona en su celular (`TeamMember.phone`), en orden, con `Transfer.run_team`
     de la derivación: `TeamRing` hace de área, sin agente detrás (sin código de vuelta a la IA ni mensajes de
     vuelta), whisper "Llamada a {{linea}} de {{cliente}}. Marcá 1 para atender." y los tramos en
     `handoff_legs` con `area_id` nulo y los mismos eventos `handoff.*`. Después, el panel.
   - **`panel`:** `direct_calls.ring_panel` crea un `call_rings` a cada usuario Disponible y no ocupado; en el
     panel, `GET /me/ringing` (cada ~2 s) muestra **Atender** / **Rechazar** (`POST /direct-calls/{id}/answer` y
     `/decline`). El primero que atiende se queda con la llamada (409 `already_answered` al resto), `cancel_rings`
     apaga los demás y entra a la room (`PANEL_JOIN_GRACE_SECONDS`: si su navegador no entra, la llamada vuelve a
     quedar sin `user_id`). Después, los celulares.
2. Atiende alguien: se conectan, transcripción y grabación como en la saliente, y la llamada queda con el
   `user_id` de la persona (si tiene usuario). Los minutos corren desde que entra la llamada, y el tramo al
   celular además cuenta como los de la derivación (`handoff_legs`, 2 canales de Anura; en el panel, 1 y sin
   minutos propios de ese tramo). Corta la persona o el que llama y termina la llamada (no hay agente al que volver).
3. Nadie atiende: respaldo del número (`team_no_answer`). `agent`: `direct_calls.fallback_to_agent` pasa la
   conversación al agente del número (`answered_by=agent`) y el worker sigue con el agente en la misma room,
   con la apertura y el contexto "nadie del equipo atendió" (si el agente se archivó, toma el mensaje).
   `voicemail`: mensaje por TTS y graba lo que dice el que llama (hasta `VOICEMAIL_SECONDS`, 120 s), con
   transcripción. `hangup`: mensaje y corta.

**Identidades de la room:** el usuario del panel, `user-<user_id>`; el contacto de la saliente, `contact`; el que
llama en la entrante, la que le pone livekit-sip (`sip_<número>`); la persona atendida por celular, `persona-<n>`
(los permisos de las pistas se fijan por identidad antes de marcar, como en la derivación).

**Presencia:** `PUT /me/presence` (pulso cada ~20 s mientras el switch Disponible está prendido; sin pulso por
60 s deja de estar disponible) y `GET /team/presence` (quién está Disponible y quién ocupado). Un admin en
"ver como cliente" no llama, atiende ni cambia presencia (403 `support_read_only`).

**Mensajes de datos de la room** (`publish_data`): tema `call_status` `{state, result?}` (solo la saliente; en la
entrante el usuario entra ya atendida) y tema `transcript` `{role, person?, text}`.

**Capacidad:** sin LLM, una directa carga solo el STT por frase. Limitan los 10 canales de Anura
(`ANURA_MODES` incluye `directa`) y los minutos. Sin canal libre: 429 `no_channel` en la saliente y el respaldo
en la entrante. Sin CAP todavía mezclada con llamadas del agente.

### Durante la llamada

- **Turnos:** el motor conversacional (ver README, "Motor conversacional").
- **Corte duro por minutos:** para entrantes y salientes, el worker mira
  `calls.call_remaining_seconds` cada `QUOTA_CHECK_SECONDS` (15 s). Cuenta las llamadas terminadas
  del mes más lo que llevan todas las llamadas en curso del cliente. Al llegar a 0 (o si el cliente
  se desactivó), dice `QUOTA_END_MESSAGE`, corta y deja `ended_reason=quota_exhausted`. La saliente
  además sale con `max_call_duration` = minutos que quedan al empezar.
- **Al cortar:** `finalize` espera la extracción pendiente y guarda duración, fin y latencia.

## Límites por tier

| Límite | Dónde se aplica | Qué cuenta |
|---|---|---|
| Simultáneas | `quota.admit` (salientes, pruebas, loadtest, entrantes) | Llamadas del cliente en `pendiente`, `sonando` o `en_curso` creadas hace menos de `CALL_MAX_DURATION_SECONDS` + 10 min. Las más viejas se consideran colgadas y no ocupan lugar. |
| Minutos entrantes / salientes | `quota.admit` y el watchdog del worker | Suma de `duration_seconds` de las llamadas de esa modalidad que empezaron en el mes, más el tiempo de las en curso. Las de prueba y loadtest no consumen. Mes calendario en `BILLING_TIMEZONE`. |
| Números | `phone_numbers.assign`, cambio de tier, cambio del tope | Números con `client_id` del cliente. Asignar toma el mismo lock del cliente y el del número. |
| Campañas | `services/limits.py` (`check_campaign_*`), al crear, sumar contactos, iniciar y retomar | Canal habilitado (`campaign_channels`), campañas iniciadas en el mes (`started_at`; la primera vez que sale de borrador), contactos por campaña y `concurrency` de voz. Las llamadas de campaña también pasan por `quota.admit` (minutos, topes de llamadas, simultáneas). Al cambiar de tier o de canales, las campañas de un canal que ya no entra pasan a `paused`. |
| Agenda | `services/contacts.py` | Contactos activos (`max_contacts`); los archivados no cuentan. |
| Equipo | `services/handoff.py` | Personas del equipo (`max_team_members`). |
| Llamadas directas | `limits.check_direct_calls` (`tiers.direct_calls`), `quota.admit` | La saliente directa y poner un número en `answer_mode=team` piden el plan (429 `direct_calls_not_in_plan`). La saliente cuenta como saliente (`MINUTE_MODES`, minutos desde que atiende el contacto) y ocupa 1 canal de Anura (`ANURA_MODES`); la entrante del equipo, como entrante. |
| Derivaciones | `quota.handoff_check`, antes de cada intento y en el modo escucha | El tramo a la persona gasta **minutos salientes** (`quota.used_seconds` suma `billed_seconds` de `handoff_legs` y lo que llevan los conectados), sea cual sea el origen de la llamada. Canales: `quota.busy_channels` (entrantes y salientes activas más tramos abiertos) contra `ANURA_CHANNELS` (10); sin canal o sin minutos, no se intenta (`handoff.unavailable`). |

**Ajustes por cliente** (`services/limits.py`): para darle a un cliente algo distinto de su tier (una línea más, 10 minutos
más este mes, un tope propio) sin tocar el tier ni clonarlo. Toda la tabla anterior, la API de inferencia y el rate limit leen
`effective_limits(s, client)`, no `client.tier`. Por campo: los `set` vigentes reemplazan el valor del tier (gana el último
cargado) y después se suman los `add`; sobre un valor ilimitado (NULL) un `add` no tiene efecto, y por eso se rechaza al cargarlo
(`already_unlimited`). Un ajuste vale entre `starts_on` y `ends_on`, inclusive; al vencer, el cliente vuelve al valor del tier
sin tocar nada. Cambiar de tier conserva los ajustes. Quitar un ajuste, o cargar un `set` más bajo, se rechaza (409
`phone_numbers_limit`) si deja al cliente con más números de los que permite. Solo el admin los maneja
(`GET /clients/{id}/limits`, `POST /clients/{id}/limit-adjustments`, `DELETE .../{adjustment_id}`); el usuario del cliente
ve el límite efectivo en su consumo. Si se cambia la lógica de un límite del tier, `LIMIT_FIELDS` y `LimitField` de la API
tienen que seguir iguales a las columnas numéricas de `Tier` (lo verifica `tests/test_limits.py`).

**API de inferencia** (`/api/v1/inference`, [`API_INFERENCIA.md`](API_INFERENCIA.md)): LLM, STT y TTS por API key,
con límites mensuales del tier por separado (tokens de entrada y de salida, minutos de síntesis y de transcripción) y
pedidos por minuto. Solo cuenta ese uso, no los agentes integrados. `api_usage.check` rechaza el pedido
antes de llegar al motor si el cupo está agotado y devuelve lo que queda (el chat achica `max_tokens` a ese saldo);
`api_usage.record` suma al terminar lo que informó el motor.

| Límite | Dónde se aplica | Qué cuenta |
|---|---|---|
| Tokens de entrada y salida del LLM | `deps.inference_access("llm")` + `InferenceGateway.chat` | `usage.prompt_tokens` y `completion_tokens` del motor; en un stream cortado, estimados. |
| Minutos de STT | `inference_access("stt")` + `transcribe` | `duration` del motor (se pide `verbose_json`). |
| Minutos de TTS | `inference_access("tts")` + `speech` | Audio que salió: `wav`, los bytes con la frecuencia del encabezado; `pcm`, los bytes decodificados de los eventos SSE del motor (se piden con `stream: true`, así llega a medida que se sintetiza) a 24 kHz. Si el cliente corta, lo ya entregado. |
| Pedidos por minuto | `inference_access(...)` | `api_limiter`, por cliente (todas las keys y motores); en memoria. |

Carreras medidas en PostgreSQL:
- 20 llamadas simultáneas con tope 3: entran exactamente 3.
- 5 asignaciones simultáneas de números con tope 2: entran exactamente 2.

## Autenticación y permisos

El dashboard se publica en `https://app.atentina.com.ar` por el túnel, **sin Cloudflare Access**: todo
lo de esta sección es lo que lo protege.

- **UI:** `POST /auth/login` valida contra argon2 (con tiempo constante si el email no existe) y
  setea la cookie `vaas_session`: un JWT HS256 firmado con `AUTH_SECRET`, httpOnly,
  SameSite=Strict, path `/api`, `Max-Age` de `AUTH_TOKEN_HOURS` y `Secure` si `AUTH_COOKIE_SECURE=true`
  o si el pedido llega por HTTPS (así anda en `http://localhost:8011` y sale Secure por el túnel).
- **Alta de usuario con link por mail** (`POST /clients` con `owner_email`, `POST /users/{id}/invite`): el
  usuario se crea con un hash de una clave al azar (no puede ingresar) y le llega el mail de bienvenida con
  `/set-password?token=…`. El token es un JWT firmado con una clave **derivada** de `AUTH_SECRET` (no vale
  como sesión ni al revés), vence a las `PASSWORD_SETUP_HOURS` (72) y lleva la huella de la clave actual
  (`ph`): al crearla deja de valer, así que es de un solo uso sin tabla. `POST /auth/password-setup/check`
  y `POST /auth/password-setup` son públicos, con tope de 30 pedidos por hora por IP (429); el segundo
  guarda la clave, sube `session_version` y abre la sesión. Link vencido o usado: 422 `invalid_setup_token`.
- **Perfil: cambio de clave o de email con código** (`app/services/profile.py`, pantalla `/profile`):
  `POST /auth/me/password/code` o `POST /auth/me/email/code {email}` mandan un código de 6 dígitos al email
  **actual** y devuelven un desafío (JWT con clave derivada de `AUTH_SECRET`) con el HMAC del código, la huella
  de la clave y el email actuales; `POST /auth/me/password` o `POST /auth/me/email` lo mandan de vuelta con el
  código. Sin tabla: deja de valer al cambiar la clave o el email (un solo uso) o a los `ACCOUNT_CODE_MINUTES`
  (15). Topes por usuario, en memoria: `ACCOUNT_CODE_SENDS_PER_HOUR` (5) mails y `ACCOUNT_CODE_ATTEMPTS_15M`
  (5) intentos, contados antes de verificar (429). Código mal o vencido: 422 `invalid_code`; email ocupado: 409
  `email_taken`; Resend caído: 502 `mail_failed`. Al cambiar sube `session_version` y reabre la cookie de este
  pedido. `PATCH /auth/me` cambia el nombre. Solo con sesión (no API key).
- **Admin dentro de un cliente ("ver como cliente", `docs/ADMIN_SOPORTE_PLAN.md`):** con la sesión de un
  `admin` y el header `X-Atentina-Client: <client_id>`, `get_principal` devuelve un `Principal` con rol
  `client`, ese cliente y `support=True` (`id` sigue siendo el del admin). Una API key o un token OAuth no lo
  pueden usar (el MCP tiene su propio `x-atentina-mcp-client`). `GET /auth/me` responde el cliente con
  `support: true`. Su cuenta, su plan y sus cobros son de solo lectura (`require_not_support`: 403
  `support_read_only`). La UI guarda el cliente por pestaña (`sessionStorage`) y vacía la caché al cambiar.
- **Límites de login fallido** (en memoria del proceso, `services/ratelimit.py`): 5 por IP y email y 10
  por email en 15 min; 20 por IP en 15 min y 100 por día (`LOGIN_FAIL_*`). Se cuentan antes de verificar
  la clave, de forma atómica (pedidos en paralelo no pasan todos), y un login correcto se descuenta y
  limpia el de IP y email. El tope por email solo frena a las IP que ya fallaron en la ventana: así un
  tercero que conoce el email no deja afuera al dueño. Responde 429 `too_many_attempts`.
- **Sesión revocable:** el JWT lleva `sv` = `users.session_version`. El logout, el cambio de clave y
  la desactivación lo incrementan: cierran **todas** las sesiones del usuario, aunque alguien haya
  copiado el token. Los tokens viejos sin `sv` valen como 0 hasta que vencen.
- **IP real:** `deps.client_ip` toma `CF-Connecting-IP` solo si el par TCP está en
  `TRUSTED_PROXY_CIDRS` (por defecto localhost y `gateway`, el gateway por defecto del contenedor, que es
  el de la red de compose por donde llega cloudflared: hoy `172.24.0.1`); si no, el par. Igual con
  `X-Forwarded-Proto` para saber si fue HTTPS. La usan el login y la demo. Por el túnel, un pedido con
  `X-Forwarded-Proto: http` recibe 308 a `https://` (`HttpsRedirectMiddleware`). Límite conocido: un
  contenedor de otro proyecto de este host que entre por el puerto publicado puede llegar enmascarado
  como ese mismo gateway y falsificar `CF-Connecting-IP`.
- **CSRF** (`app/api/http.py`): SameSite=Strict no alcanza, porque la landing, `api.`, `wa.` y `rtc.`
  son *same-site* con `app.`. Un POST, PATCH, PUT o DELETE con la cookie y sin `Authorization` tiene
  que traer `Origin` del mismo host o de `APP_ORIGINS`; sin `Origin`, se rechaza `Sec-Fetch-Site`
  `same-site` o `cross-site`. Si no, 403 `csrf`. Las API keys no pasan por este control.
- **Límites de uso** por usuario o API key y por hora: prueba de voz (`RATE_TTS_PREVIEW_PER_HOUR`),
  conversaciones de texto nuevas y sus turnos (`RATE_CONVERSATIONS_PER_HOUR`, `RATE_TURNS_PER_HOUR`);
  por cliente, altas de WhatsApp y plantillas (`WA_SIGNUP_PER_HOUR`, `WA_TEMPLATES_PER_HOUR`). Cuerpo de
  `/api` hasta `API_MAX_BODY_BYTES` (1 MiB, 413).
- **Loadtest:** `POST /calls {"loadtest": true}` solo para admin o el cliente `LOADTEST_CLIENT`
  (`atentina`); si no, 403 `loadtest_forbidden`.
- **Sistemas del cliente:** `Authorization: Bearer vaas_…`. Se guarda solo el SHA-256 y
  `last_used_at` se actualiza con resolución de un minuto.
- **Cada pedido relee el usuario de la base:** desactivarlo o cambiarle el rol corta el acceso sin
  esperar a que venza el token.
- **Permisos:**

| Acción | Admin | Usuario cliente | API key |
|---|---|---|---|
| Tiers, clientes (alta, edición, baja), ajustes de límites de un cliente, usuarios | Sí | No | No |
| Agentes: crear, editar, versionar, archivar, borrar | Sí | Los suyos | Los suyos |
| Agentes: ver el prompt que arma el motor (`POST /agents/prompt`) | Sí | No | No |
| Números: cargar, asignar, liberar, borrar | Sí | No | No |
| Números: elegir agente y etiqueta | Sí | Los suyos | Los suyos |
| WhatsApp: alta manual, token, número visible | Sí | No | No |
| WhatsApp: conectar por Embedded Signup (`/whatsapp/signup`) | Sí | Los suyos | No |
| WhatsApp: ver, agente, nombre, activar, registro, refresco, plantillas, ruteo por contacto | Todo | Lo suyo | Lo suyo |
| WhatsApp: campañas (crear, contactos, iniciar) | Todo | En sus números con token propio | Ídem |
| WhatsApp: ver, pausar y cancelar campañas; bajas | Todo | Lo suyo | Lo suyo |
| Campañas de llamadas y contactos (crear, iniciar, archivar, bajas, reportes) | Todo | Lo suyo, si el plan incluye el canal | Ídem |
| Llamadas, conversaciones, consumo, voces | Todo | Lo suyo | Lo suyo |
| Llamadas directas: llamar, atender, presencia | No (en soporte, 403 `support_read_only`) | Sí, con el plan | Llamar con `user_id` y `join_url`; atender, rechazar y presencia piden la sesión del panel (403 `panel_user_required`) |
| Números: quién atiende (agente o equipo, personas, respaldo) | Sí | Los suyos | Los suyos |
| Conversaciones: borrar (una o en bulk) | Sí | No | No |
| API keys | Sí | Las suyas | No |

- Un recurso de otro cliente responde 404, no 403, para no revelar que existe.
- **Headers** (`app/api/http.py`):
  - HSTS (`max-age=31536000; includeSubDomains`), solo si el pedido llegó por HTTPS;
  - CSP con el hash sha256 de cada `<script>` inline de `web/dist/index.html` (se recalcula si cambia el
    build) y el SDK de Facebook para Embedded Signup (`connect.facebook.net`, frames y conexiones a
    `*.facebook.com`), `frame-ancestors 'none'`. `CSP_REPORT_ONLY=true` la manda como Report-Only;
  - `Cross-Origin-Opener-Policy: same-origin-allow-popups` (con `same-origin` se rompe el `postMessage`
    del popup de Meta), `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`,
    `X-Content-Type-Options` y `X-Frame-Options: DENY`. Sin header `server` (`--no-server-header`).
- **Errores sin detalle interno:** los 500 y 502 no traen el error de abajo (queda en el log) y los 422 de
  validación salen sin `input` (en el login sería la clave).
- **Demo de la landing:** `/api/v1/demo/*` es lo único público. Sesión por Turnstile, límites por
  IP y por día, y CORS solo para `DEMO_ALLOWED_ORIGINS` (ver [`LANDING.md`](LANDING.md)).

## API

- Versionada en `/api/v1`; OpenAPI en `/api/v1/openapi.json` y documentación en `/api/v1/docs`, solo
  para un admin con sesión (`API_DOCS=admin`; `public` u `off`). `make openapi` usa `app.openapi()` y
  no depende de eso.
- **WhatsApp** (`/whatsapp`): `GET /config` (datos para lanzar Embedded Signup: `app_id`, `config_id`,
  `enabled` y el motivo si falta algo), `GET|POST /accounts`, `PATCH /accounts/{id}`,
  `POST /accounts/{id}/deactivate|register|refresh`, `PUT /accounts/{id}/routes` (ruteo por contacto:
  reemplaza las reglas de la cuenta), `GET|POST /accounts/{id}/templates` y
  `POST /signup`. Detalle en [`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md), 5.3.
- **Contactos** (`/contacts`): `GET` (paginado; `q`, `archived` = `false`, `true` o `all`), `POST` (uno o
  una lista, upsert por teléfono), `POST /import` (JSON `{csv}`), `GET|PATCH /{id}`, `GET /{id}/campaigns`,
  `POST /{id}/archive|unarchive`, `POST /archive` (en lote, por `contact_ids`) y
  `GET|POST /optouts`, `DELETE /optouts/{phone}`. No hay DELETE de contactos. Los admins pasan `client_id`.
- **Campañas** (`/campaigns`, canal `whatsapp` o `voice`): `GET` (`channel`, `status`), `POST` (con `start: true`
  opcional), `GET /plan` (lo que permite el plan y lo usado), `GET|PATCH|DELETE /{id}` (el `GET` es el
  **polling**: estado, progreso, `results`, `percent`, `eta_minutes`, `in_window`, `goal` y `followup`; el
  `DELETE`, solo de borradores), `POST /{id}/contacts`, `GET /{id}/contacts` (`status`, `result`),
  `GET /{id}/stats`, `GET /{id}/report.csv` y `POST /{id}/start|resume|pause|cancel`. `start` y
  `resume` de una `comercial` piden `no_call_registry_checked: true` (422 `no_call_confirmation_required`).
  `GET /calls` filtra por `campaign_id`; los indicadores de la campaña son `GET /{id}/stats`.
- **Campañas de WhatsApp** (`/whatsapp`, alias de las anteriores, sobre el mismo código; se borran en una
  versión): `GET|POST /campaigns`, `GET|PATCH|DELETE /campaigns/{id}`, `GET|POST /campaigns/{id}/recipients`
  (lista o CSV posicional), `POST /campaigns/{id}/start|pause|cancel`, `GET|POST /optouts` y
  `DELETE /optouts/{wa_id}`. Envío y reglas en [`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md), 5.5 y
  [`LLAMADAS_SALIENTES_PLAN.md`](LLAMADAS_SALIENTES_PLAN.md).
- **Llamadas directas** (`app/api/routers/direct_calls.py`): `POST /direct-calls` (`contact_id` o `phone`, `from_number_id`, `confirm_opted_out`, `user_id` con API key), `POST /direct-calls/{id}/join|answer|decline`, `PUT /me/presence`, `GET /me/ringing`, `GET /team/presence` y `GET|PUT /clients/{id}/direct-call-settings` (`recording_notice`). `PATCH /phone-numbers/{id}` suma `answer_mode`, `member_ids` (en orden), `ring_first`, `ring_seconds`, `schedule`, `team_fallback` y `team_fallback_message`; `GET /calls` filtra por `mode`, `user_id`, `answered_by`, `phone` (E.164 normalizado) y `contact_id`; el detalle trae `call.team` (entrante al equipo: si atendió alguien y el respaldo, evento `team.fallback`) y el contacto de la agenda. Errores: `opted_out`, `blocked_number`, `no_channel`, `already_answered`, `terms_pending`, `members_required`, `agent_required`, `direct_calls_not_in_plan`. Detalle en [`LLAMADAS_DIRECTAS_PLAN.md`](LLAMADAS_DIRECTAS_PLAN.md), 13.
- **Equipo y derivaciones**: `GET|POST /team`, `PATCH|DELETE /team/{id}`, `GET|POST /handoff-areas`,
  `GET|PATCH|DELETE /handoff-areas/{id}` (409 `area_in_use` si un agente la usa), `GET /handoff-areas/defaults`
  (mensajes de fábrica), `GET /hold-music` (temas de espera) y `GET /events` (cursor `after_id`, filtro por
  tipo o prefijo). Los admins pasan `client_id`. Detalle en [`DERIVACIONES_PLAN.md`](DERIVACIONES_PLAN.md).
- **Mails** (Resend, `app/mail/`): `POST /clients` con `owner_email` crea el usuario y manda la bienvenida
  (respuesta con `invite.status`: `sent`, `failed` o `disabled`); `POST /users/{id}/invite` la reenvía.
  Al asignar un número (`POST /phone-numbers` con `client_id`, `POST /phone-numbers/{id}/assign`) sale
  un mail a cada usuario activo del cliente, en segundo plano. Todos llevan el link
  `{APP_URL}/login?email=…` (la pantalla de login prellena el email; con sesión abierta va al inicio). Un fallo de
  Resend no corta la operación: queda en el log. Sin `RESEND_API_KEY` no se envía nada (`disabled`).
  Variables: `MAIL_FROM`, `APP_URL`, `SITE_URL`, `SUPPORT_EMAIL` y `PASSWORD_SETUP_HOURS`.
- **Inferencia** (`/inference`, key con alcance `llm`, `stt` o `tts`): `POST /chat/completions`, `POST /audio/transcriptions`,
  `POST /audio/speech` (`wav` completo, o `pcm` en streaming, crudo o como eventos SSE con `stream_format`),
  `GET /voices`, `GET /models` y `GET /usage`; el chat y el TTS en `pcm` transmiten a medida que el motor genera; el consumo por cliente es
  `GET /clients/{id}/inference-usage`. Compatible con el SDK de OpenAI. Las keys llevan alcance (`scopes`):
  `get_principal` rechaza (403 `scope_missing`) una key sin `calls` en la API de llamadas, y la de inferencia
  solo acepta keys (no la cookie). `/audio/transcriptions` admite cuerpos de hasta `INFERENCE_STT_MAX_BYTES`
  (el resto de `/api`, 1 MiB). Detalle y límites en [`API_INFERENCIA.md`](API_INFERENCIA.md).
- **Errores:** `{"detail": "texto", "code": "snake_case", "errors": [{"path", "message"}]}`.
  - 404 `not_found`, 403 `forbidden`, 409 `conflict`/`agent_in_use`/`phone_numbers_limit`/…,
    422 `invalid`/`invalid_definition`, 429 límites del tier, 502 `upstream_error` (LiveKit, TTS
    o LLM caídos) y 500 `internal_error`, sin detalles (el detalle queda en el log).
  - Los 422 de validación de pydantic mantienen el formato de FastAPI.
- **Listas:** `GET /calls` pagina con `limit`/`offset` y devuelve `{items, total}`; el resto devuelve
  listas simples.
- **Borrado de conversaciones** (solo admin): `DELETE /calls/{conversation_id}` y
  `POST /calls/bulk-delete` con `{ids}` (los ids inexistentes se ignoran; devuelve `deleted`).
  Borra la conversación con su llamada (y el consumo del mes), el hilo y los mensajes de WhatsApp,
  el registro de respuesta de campaña y los WAV de las grabaciones; 409 `call_in_progress` si
  alguna tiene una llamada activa. Desde la UI: selección en bulk estilo Gmail en Conversaciones.
- **WhatsApp en `/calls`:** `mode=whatsapp` (sin `call_logs`: `status` null, duración 0, `phone` = `wa_id`);
  `mode=api` son solo las de texto por la API. El detalle trae `whatsapp` en lugar de `call`, y
  los reportes las cuentan como consultas del canal `whatsapp`, no como llamadas.
- **Filtros de fecha** (`/calls`): toman días locales de `tz` (zona IANA,
  default `BILLING_TIMEZONE`). `status` se puede repetir.

## Reportes (`/api/v1/reports`)

Contrato completo en [`REPORTES_PLAN.md`](REPORTES_PLAN.md), sección 9.

- **Datos:** consultas SQL agregadas en `app/services/report_stats.py` (nada de cargar conversación por
  conversación). `conversations` guarda al terminar `outcome`, `goal`, `conversion` (`complete`, `partial` o
  `empty`) y `llm_input_tokens`/`llm_output_tokens`; `tool_runs` tiene una fila por ejecución de una
  herramienta del cliente, y `wa_account_status_log` cada cambio de estado, calidad o límite de una cuenta de
  WhatsApp (migración 0036; `make reports-backfill` completa las conversaciones anteriores). Las fechas
  están en UTC naive y los días y horas se agrupan en la zona `tz` (default `BILLING_TIMEZONE`).
- **Endpoints** (`app/api/routers/reports.py`): `summary`, `calls`, `outcomes`, `messages`, `transfers`,
  `campaigns`, `technical` y `platform`. Filtros comunes: `client_id`, `agent_id`, `channel` (`voice`,
  `whatsapp` o `web`), `phone_number_id`, `date_from`/`date_to` (últimos 30 días por defecto), `tz` e
  `include_tests` (las pruebas fuera por defecto; el `loadtest`, siempre).
- **Alcance por rol:** el cliente ve solo lo suyo (`scoped_client_id`) y nada técnico. Un admin elige el
  cliente o deja `client_id` vacío (todos); `technical` y `platform` son solo del admin.
- **Alcance por plan:** `summary` y `calls` van en todos los planes; `outcomes`, `messages`, `transfers` y
  `campaigns` piden `tiers.advanced_reports` (clave `advanced_reports` de `services/features.TIER_HAS`) y sin
  él dan 403 `advanced_reports_not_in_plan`.
- **UI y MCP:** `web/src/features/reports/` (CSV armado en el navegador) y una herramienta `get_report_*`
  por reporte del cliente en `app/mcp/catalog.py`.

## Frontend (`web/`)

- **Stack:** React 19 + TypeScript strict + Vite, React Router 7 (rutas con carga diferida por
  página), TanStack Query 5, Mantine 8 (tema Atentina, solo claro), CodeMirror para el JSON y
  Recharts. Diseño: [`DESIGN_GUIDELINE_APP.md`](DESIGN_GUIDELINE_APP.md).
- **Cliente de la API:** `openapi-fetch` tipado con `src/api/schema.d.ts`, generado del OpenAPI
  (`make openapi`: exporta `web/openapi.json` y corre `npm run gen:api`). Un cambio de contrato en
  `app/api/schemas.py` se refleja regenerando los tipos, y `npm run typecheck` marca lo que rompe.
- **Organización:** `src/features/<recurso>/`, con páginas, componentes y un `api.ts` de hooks de
  query/mutación que invalidan lo que corresponde. Los filtros, pestañas y el mes de consumo viven en
  la URL.
- **Auth:** `GET /auth/me` al cargar; un 401 en cualquier pedido limpia la sesión y lleva a
  `/login`. Guardas por rol en rutas y navegación.
- **Build:** `web/dist`. FastAPI sirve `/assets/*` y cualquier otra ruta que no sea de la API
  devuelve `index.html` (sin cache; los assets llevan hash).
- **Desarrollo:** `make web-dev` (Vite en :5173 con proxy de `/api` al `app` del stack, :8011) o
  `npm run dev` en `web/` contra `make dev-backend` (API sobre SQLite en :8111, sin tocar el stack). Ver
  [`web/README.md`](../web/README.md).

## Tests y calidad

| Qué | Comando | Cubre |
|---|---|---|
| Backend | `make test` (o `.venv/bin/pytest`) | API (auth, permisos, tiers, clientes, mails y alta de clave (`test_mail.py`), agentes y versiones, inventario de números, llamadas y límites, fechas por zona, cuentas, conversaciones y alta de WhatsApp, plantillas, ruteo por contacto), seguridad del dashboard público (`test_security_public.py`), migración 0005 de ida y vuelta, cuotas, motor con LLM falso, herramientas (`make e2e-tools`: API, MCP, sandbox de prueba y API falsa, con LLM grabado) y WhatsApp (webhook, service con payloads de Meta y Graph simulado). Solo LLM falso desde el 26-oct-2026 (`tests/test_llm.py` salió): lo que mide al modelo real son los evals (`make eval-llm`, `make eval-tools`), que informan y no bloquean. |
| Frontend | `make web-check` | ESLint, tipos y Vitest (formatos, parseo de números, errores de API, guardas por rol, consumo, WhatsApp: origen y mensajes de Embedded Signup, alta con el SDK simulado, plantillas, ruteo por contacto). |
| Migraciones | `alembic upgrade head` / `downgrade` / `check` | Ida y vuelta en PostgreSQL y SQLite. |

## Configuración

Todo por `.env`, leído con `app/config.py` (ver `.env.example`):
- **Obligatorias:** `AUTH_SECRET`, más las de LiveKit e inferencia.
- **Primer admin:** `ADMIN_EMAIL` y `ADMIN_PASSWORD`, que usa el seed.
- **Límites:** `BILLING_TIMEZONE`, `QUOTA_CHECK_SECONDS`, `QUOTA_REJECT_MESSAGE` y
  `QUOTA_END_MESSAGE`.
- **Scripts de carga:** `VAAS_API_KEY` (API key del cliente `atentina`).
- **WhatsApp:** `WA_APP_SECRET`, `WA_VERIFY_TOKEN`, `WA_ACCESS_TOKEN` (system user), `WA_SESSION_HOURS`,
  `WA_DEBOUNCE_SECONDS`, `WA_UNSUPPORTED_REPLY`, `WA_MAX_REPLY_CHARS` y los de audios (`WA_AUDIO_REPLY`,
  `WA_AUDIO_MAX_BYTES`, `WA_AUDIO_MAX_SECONDS`, `WA_AUDIO_MAX_REPLY_CHARS`, `WA_AUDIO_CONCURRENCY`, ...;
  ver [`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md), 5.2) y los de la fase 2 (`WA_CONFIG_ID`, `WA_TOKEN_KEY`,
  `WA_SIGNUP_PER_HOUR`, `WA_TEMPLATES_PER_HOUR`, `WA_SDK_LOCALE`).
- **Campañas** (`docs/LLAMADAS_SALIENTES_PLAN.md`): `CALL_CAMPAIGN_MAX_CONCURRENT` (8, tope global de llamadas de
  campaña; provisorio hasta medir con Gemma), `CALL_CAMPAIGN_TICK_SECONDS`, `CALL_CAMPAIGN_FAILURE_STREAK` (10),
  `CALL_RINGING_TIMEOUT_SECONDS` (30), `CAMPAIGN_HOLIDAYS` y las del webhook (`CAMPAIGN_CALLBACK_TICK_SECONDS`,
  `_TIMEOUT_SECONDS`, `_MAX_ATTEMPTS`, `_ALLOW_PRIVATE`, solo desarrollo).
- **Seguridad del dashboard público:** `AUTH_COOKIE_SECURE`, `TRUSTED_PROXY_CIDRS`, `APP_ORIGINS`,
  `API_DOCS`, `CSP_REPORT_ONLY`, `LOGIN_FAIL_*`, `API_MAX_BODY_BYTES`, `RATE_*` y `LOADTEST_CLIENT`.
