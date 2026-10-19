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
| `agent` | `app/voice/worker.py` | Worker de LiveKit Agents: STT → motor conversacional → TTS. Atiende salientes (con metadata del despacho) y entrantes (por dispatch rule, sin metadata). |
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
                     conversations, voices, whatsapp (cuentas), inference, demo, contacts, campaigns
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
  conversation/      motor: engine, models (Workflow = definición), workflow (validación), store,
                     assistant.py (motor assistant: pasos con herramientas, confirmación y controles)
  apps/              apps por cliente (docs/APPS_PLAN.md): client.py (HTTP y MCP mínimo), registry.py
                     (registro, contrato, salud), tools.py (herramientas de un agente), links.py
                     (links firmados) y gateway.py (vistas por APPS_PUBLIC_HOST)
  llm/               cliente y prompts del LLM
  campaigns/         loop único de campañas (loop.py: delega por canal), dialer de voz (dialer.py),
                     contestador por heurística (voicemail.py) y entrega del webhook (callbacks.py)
  voice/             worker de LiveKit y latencia por turno
  whatsapp/          webhook (firma), graph.py (Cloud API y media), store.py (tablas wa_*), service.py (turnos),
                     audio.py (notas de voz: STT, TTS y OGG/Opus con PyAV), signup.py (Embedded Signup,
                     registro, plantillas), crypto.py (tokens y PIN cifrados), campaigns.py y sender.py
                     (campañas de WhatsApp por plantilla, bajas y seguimiento de las de voz)
migrations/          Alembic: 0001 esquema anterior (idempotente), 0002 tenencia, 0003 inventario de números,
                     0004 WhatsApp, 0005 Embedded Signup y session_version, …, 0008 campañas de WhatsApp,
                     …, 0013 apps por cliente y operadores de WhatsApp, 0015 ruteo por contacto de WhatsApp,
                     0017 agenda y campañas unificadas (WhatsApp y voz)
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
                ├───* apps (client_id, SET NULL: vuelve al inventario) 1───* app_links
                ├───* contacts (agenda, archivable) 1───* campaign_contacts
                ├───* contact_optouts (bajas por teléfono y canal)
                ├───* campaigns (whatsapp | voice) 1───* campaign_contacts ───* call_logs (intentos de voz)
                │                                  1───* campaign_callbacks (cola del webhook)
                ├───* wa_accounts (agent_id, RESTRICT) 1───* wa_routes (ruteo por contacto)
                │                                      1───* wa_threads
                │                                      1───* wa_operators (client_id + agent_id propios)
                └───* conversations 1───1 call_logs        (voz)
                         │          1───1 wa_threads       (whatsapp)
                         │          1───* wa_messages
                         └── agent_id + agent_version (la versión con que corrió)
```

| Tabla | Claves y reglas |
|---|---|
| `tiers` | `max_concurrent_calls`, `max_calls_per_hour`, `max_calls_per_day`, `max_calls_per_month` (llamadas entrantes y salientes por hora, día y mes calendario), `inbound_minutes`, `outbound_minutes`, `max_phone_numbers`; NULL = ilimitado. Campañas: `campaign_channels` (`[]`, `["whatsapp"]`, `["voice"]` o los dos), `max_campaigns_per_month`, `max_campaign_contacts`, `max_campaign_concurrency`, `max_contacts` (contactos activos de la agenda; NULL = ilimitado, 0 = no incluido) y `campaign_followup`. API de inferencia: `api_llm_input_tokens`, `api_llm_output_tokens`, `api_tts_minutes`, `api_stt_minutes` (por mes) y `api_rate_limit` (pedidos por minuto); NULL = ilimitado, 0 = no incluido. |
| `clients` | `slug` único, `tier_id` (RESTRICT: un tier en uso no se borra), `active`. |
| `client_limit_adjustments` | Ajuste de un límite del tier para un cliente: `field` (uno de los 16 numéricos de `tiers`), `mode` (`add` suma, `set` reemplaza; `value` NULL = ilimitado solo con `set`), `starts_on`/`ends_on` (inclusive, en `BILLING_TIMEZONE`; sin fechas, permanente), `note`, `created_by`. Se resuelven en `services/limits.py`. |
| `agents` | `(client_id, slug)` único; `version` y `definition` vigentes (copia de la última versión); `archived_at`. |
| `agent_versions` | `(agent_id, version)`; inmutables, con `created_by`. |
| `phone_numbers` | `e164` único; `client_id` NULL = libre; `agent_id` solo si hay cliente (CHECK); `provider`, `assigned_at`. |
| `users` | `email` único; `role` admin o client (CHECK: client ⇔ `client_id`); hash argon2. |
| `api_keys` | SHA-256 de la clave (`key_hash` único), `prefix` visible, `revoked_at`, `scopes` (`calls`, `llm`, `stt`, `tts`, separados por coma: una key de inferencia no usa la API de llamadas ni al revés). |
| `api_usage_daily` | Consumo de la API de inferencia por `(client_id, api_key_id, day)` (día en `BILLING_TIMEZONE`): pedidos, tokens de entrada y salida del LLM y segundos de TTS y STT. Se suma con un UPDATE que incrementa. Sin contenido de los pedidos. |
| `conversations` | Estado del motor (datos, mensajes, progreso), `client_id`, `agent_id` + `agent_version` (RESTRICT: un cliente o agente con historial no se borra). `legacy_workflow_id` para las anteriores a los agentes. |
| `call_logs` | Una por conversación: modo, estado, teléfono del otro lado, `phone_number_id` del cliente, inicio, fin, duración, latencia. Base del consumo. `campaign_contact_id` ata el intento de una campaña de voz; `sip_status`, el código SIP de una saliente fallida. |
| `conversations.channel` | `voice` o `whatsapp`; se fija al crearla. Cambia el prompt (reglas por canal), no el agente. |
| `wa_accounts` | Un número de WhatsApp: `phone_number_id` único (ID de Meta), `waba_id`, número visible, `client_id`, `agent_id`, `access_token` (NULL = `WA_ACCESS_TOKEN`; cifrado con `WA_TOKEN_KEY`, prefijo `fernet:`), `pin_enc`, `active`, `status` (`connected`, `pending`, `disconnected`) con motivo, `quality_rating`, `messaging_limit`, `source` (`manual`, `embedded_signup`, `coexistence`), `connected_by`. Sin borrado: se desactiva. |
| `wa_routes` | Ruteo por contacto de una cuenta (`account_id` + `agent_id` únicos): `contacts` (wa_id como los manda Meta) que atiende ese agente en los mensajes y las llamadas de WhatsApp, en vez del agente por defecto. Un contacto está en una sola regla; el agente es del cliente de la cuenta y no archivado. Se resuelve en `services/wa_routing.py`. |
| `wa_threads` | Una por conversación de WhatsApp (como `call_logs`): cuenta, `wa_id` tal cual llega (`549…`), nombre del perfil, `last_user_at` (ventana de sesión), `paused` (fase 3). |
| `contacts` | Agenda del cliente: `phone` (E.164) único por `client_id`, `name`, `email`, `external_id`, `attributes` (JSON libre: las columnas extra del CSV), `tags` (minúsculas ASCII), `source` (`manual`, `csv`, `api`, `campaign`, `inbound`) y `archived_at`. **No se borran, se archivan**; un archivado no se desarchiva solo al recargarlo. `max_contacts` cuenta los activos. |
| `contact_optouts` | Bajas por `(client_id, phone, channel)` con `channel` `whatsapp`, `voice` o `all` y `source` (`keyword`, `outcome`, `manual`). Aparte de `contacts` a propósito: sigue aunque el contacto se archive o no exista. Reemplaza a `wa_optouts`. |
| `campaigns` | Campaña de un cliente con `channel` `whatsapp` o `voice` (un CHECK exige los campos de cada canal), `status` (`draft`, `scheduled`, `running`, `paused`, `done`, `cancelled`) con motivo, `rate_per_minute`, horario (`window_start`, `window_end`, `weekdays`), programación (`starts_at`, `ends_at`), `started_at`/`finished_at`, `purpose` (`comercial`, `cobranza`, `turnos`, `aviso`) con `no_call_confirmed_at`, y `callback_url` / `callback_secret` (cifrado). WhatsApp: número (`account_id`), copia de la plantilla y `template_param_names`. Voz: `from_number_id`, `voice`, `concurrency` (1 = secuencial), `max_attempts`, `retry_minutes`, `retry_on` y `followup` (JSON, NULL = apagado). Reemplaza a `wa_campaigns`; las existentes conservan su id. |
| `campaign_contacts` | Un contacto en una campaña (`campaign_id` + `contact_id` únicos): `vars` (copia de sus datos al agregarlo; WhatsApp guarda los parámetros en `vars["params"]`), `status` (`pending`, `in_progress`, `retry`, `done`, `failed`, `skipped`), `result` (WhatsApp: `sent`; voz: `answered`, `no_answer`, `busy`, `voicemail`, `invalid`, `rejected`, `failed`), `error`, `conversation_id`, y según el canal `wamid`/`sent_at`/`replied_at` o `attempts`/`next_attempt_at`/`last_attempt_at` y el seguimiento (`followup_status`, `followup_wamid`, `followup_sent_at`, `followup_error`, `followup_conversation_id`). Entregado y leído salen de `wa_messages`. Reemplaza a `wa_campaign_recipients`. |
| `campaign_callbacks` | Cola del webhook (outbox): `campaign_id`, `event` (`contact.finished`, `contact.followup`, `campaign.finished`), cuerpo, `status` (`pending`, `sent`, `failed`), intentos y próximo intento. Se escribe en la misma transacción que el evento. |
| `contact_requests` | Pedidos del formulario de contacto de la landing (`POST /api/v1/demo/contact`), con `email_status` (`sent`, `failed`, `disabled`) y `email_error`; se guardan aunque Resend falle ([`LANDING.md`](LANDING.md)). |
| `apps` | App de un cliente (contenedor de atentina-apps, [`APPS_PLAN.md`](APPS_PLAN.md)): `slug` único, `client_id` (NULL = inventario), `base_url` (`http://app-<slug>:8000`), `token_enc` (APP_TOKEN cifrado con `WA_TOKEN_KEY`), `version`, `manifest` (copia del último válido: vistas y herramientas), `status` (`ok`, `down`, `invalid`), `last_error`, `last_health_at`. |
| `app_links` | Link firmado a una vista: `token_hash` (SHA-256; el token no se guarda), `app_id`, `view`, `params`, `expires_at` (`APPS_LINK_TTL_DAYS`), `revoked_at`, `created_by` (`wa:<wa_id>`, `user:<id>`), `opens`. |
| `wa_operators` | Dueño de un negocio que le habla a su asistente por un número compartido: `account_id` + `wa_id` únicos, `client_id` y `agent_id` propios (los del número no se usan), `name`, `active`. |
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
  "id": "ventas", "version": 3, "engine": "classic", "record_audio": false,
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
  OpenAI/OpenRouter). Sin `generation`, rigen los defaults de la plataforma (muestreo por familia
  del modelo y `LLM_THINKING`/`ASSISTANT_*`). El editor los agrega y quita, con los defaults del
  proveedor (`GET /api/v1/llm/params`). Ver [`BYOK_LLM_PLAN.md`](BYOK_LLM_PLAN.md).
- **Motor `assistant`** ([`APPS.md`](APPS.md)): sin datos a extraer (`fields` puede ir vacío)
  y con `tools: [{"app": "<slug>", "tools": ["*"]}]`, las herramientas de las apps del cliente. Al
  guardar se valida que cada app sea del cliente y tenga esas herramientas.
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

  Sin backup todavía (`scripts/ops/backup.sh` no lo cubre). Se escucha desde el dashboard:
  `ChatView` (web/) muestra el reproductor en la burbuja de cada mensaje grabado, servido por
  `GET /api/v1/calls/{conversation_id}/recordings/{n}` con el mismo control de acceso que el
  resto del detalle (`CallDetail.recordings` sigue listando los archivos).
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
  plantilla, `app/agents/templates/asistente.json`, con el motor elegido (`engine` pisa el de la
  definición). La definición es la misma con los dos motores: solo cambia cómo se le pide la
  respuesta al LLM. El prompt de sistema sale siempre de la definición; `POST /agents/prompt` lo
  devuelve sin guardar (classic: el prompt entero; structured: el fijo y la definición en YAML que va
  en cada turno). La UI la edita por formulario (`web/src/features/agents/DefinitionForm.tsx`,
  `draft.ts`), con el JSON como alternativa.
- **Quién los crea:** un admin, en el cliente de `client_id`; un usuario o API key de un cliente, en
  el suyo (`client_id` se omite; el de otro cliente da 404). Todo pedido sobre un agente pasa por
  `get_agent` (`app/api/routers/agents.py`): el de otro cliente responde 404 y no cambia. En la UI el
  cliente usa el mismo formulario, sin cliente, slug, motor, JSON ni prompt, que son internos: sus
  agentes nacen con el motor de la plantilla (`classic`). La API no restringe `engine` al cliente: no
  es un permiso, solo no se muestra. `POST /agents/prompt` sigue solo para admin.
- **Agentes de referencia:** `app/agents/reference/<id>.json`, para el seed, el eval y los tests (sin
  base); no se ofrecen en la UI. El sufijo `_classic` o `_structured` elige el motor sobre el mismo
  archivo (`demo_booking_classic` es `demo_booking.json` con `engine: classic`). El seed solo crea, en
  el cliente `atentina`, `atentina_comercial`, `demo_booking_classic` (test de capacidad) y las
  `landing_*` (demo).

## Flujos

### Llamada saliente o de prueba (`POST /api/v1/calls`)

1. El router resuelve el `Principal`. `services/calls.prepare_call` corre en un thread, porque la
   base es bloqueante. Valida el agente (visible y no archivado), el teléfono E.164 y la voz, y elige
   el caller ID (el número pedido o el primero del cliente).
2. `engine.new_conversation(session=s)` arma el estado con la versión vigente, sin guardarlo.
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
7. Estados de la llamada: `sonando` → `en_curso` → `finalizada` (con duración y latencia) o `fallida`.

### Campaña de llamadas (`/api/v1/campaigns`, `channel: voice`)

1. Se crea en `draft` (agente, número de origen, voz, horario, `concurrency`, reintentos) y se le suman
   contactos de la agenda (`contact_ids`, `tags`), una lista o un CSV. `start` valida el plan del tier,
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
   - **libre o sin agente:** se corta (`number_without_agent`);
   - **sin lugar o sin minutos:** queda `rechazada` y el que llama escucha `QUOTA_REJECT_MESSAGE`;
   - **si no:** conversación con el agente del número y llamada `entrante`.
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
   agente en la UI (sección "Voz" del editor, en minutos) o en su `definition`. Que el motor haya
   dado la conversación por completada (`[FIN]`) **no**
   cierra el hilo: un mensaje después del cierre la retoma con el historial y la misma versión del
   agente. Un hilo nuevo usa la versión vigente del agente del número, o la del agente de la campaña
   si el contacto responde a una (ver [`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md), 5.5).
   El motor trabaja igual que en una llamada (el clásico no extrae en cada turno). El equivalente del
   corte es el fin del chat: cerrarlo desde el dashboard, llegar a `WA_MAX_TURNS` o vencer su ventana
   de contexto (barrido cada 5 min en el lifespan de `app`, `WhatsAppService.sweep`: mira todos los
   hilos abiertos y cierra el que venció según el agente que lo abrió). Los
   tres cierran el hilo (`wa_threads.closed_at`) y llaman a `engine.finish`, la extracción final.
   Si el turno tuvo audio (`WA_AUDIO_REPLY=mirror`), `process_turn` recibe `TurnMedia` (el prompt pide
   formato para escuchar) y la respuesta sale como nota de voz: `vllm-tts` → OGG/Opus → subida →
   mensaje `audio`. Si algo falla, va en texto.
4. Los statuses actualizan `wa_messages`. No se crea `call_logs` ni se pasa por `quota.admit`.

**Operadores:** si el `wa_id` está en `wa_operators` para ese número (activo), la conversación es del
cliente y del agente del operador, no de los del número, y no se mira la campaña. Así un número de
Atentina atiende a los dueños de varios negocios, cada uno con su asistente. Un hilo abierto con otro
agente (lo hicieron operador a mitad de un chat) empieza una conversación nueva.

**Ruteo por contacto (`wa_routes`):** debajo de operadores y campañas, si el `wa_id` está en la regla
de un agente de esa cuenta, lo atiende ese agente, en los mensajes y las llamadas de WhatsApp. Un
hilo abierto con otro agente se corta y sigue en una conversación nueva, como con los operadores; uno
abierto por una campaña no se pisa. Un agente archivado se saltea y vuelve el de la cuenta.

### Motor assistant y apps

Referencia completa: [`APPS.md`](APPS.md). En corto:

- Un agente `assistant` usa las herramientas de las apps del cliente (contenedores de
  `atentina-apps`, por MCP en la red interna `atentina-apps`), más `abrir_vista` (link firmado).
- `app/conversation/assistant.py` corre hasta 6 pasos por turno con JSON guiado (`reply`, `call`,
  `confirm`, `cancel`), con razonamiento (`ASSISTANT_THINKING`). La respuesta sale siempre en texto.
- Las herramientas `destructive` y `send` se confirman. Un sí o un no claros los resuelve la
  plataforma.
- Controles de la plataforma: ids que salen de un resultado, nada escribe después de una búsqueda
  ambigua, nombres de campo como valor, links (marcas `[[linkN]]`), repeticiones y JSON inválido.
- Operadores (`wa_operators`): por un número compartido, el dueño habla con su asistente.
- Archivos (OCR), outbox (mensajes a terceros; simulado por defecto) y jobs (avisos diarios):
  `app/apps/`.
- Gateway: con `Host: APPS_PUBLIC_HOST`, `app` atiende solo las vistas de las apps, con su propia
  CSP.

**Capacidad:** un turno de texto carga solo el LLM (3090); uno con audio usa además el STT y el TTS,
y la síntesis va a la 5060 Ti, el cuello de CAP-002. `WA_AUDIO_CONCURRENCY` (4, sin medir) limita los
pedidos simultáneos, por separado al STT y al TTS, y cada pedido tiene un tope total (45 y 90 s). Pendiente de medir con un perfil del test de capacidad (ver
[`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md), sección 2).

**Un solo worker de uvicorn:** el debounce y el lock por contacto están en memoria; con más de un
worker se rompen. Si se reinicia `app` con mensajes en la ventana, esos entrantes quedan `received`
sin respuesta.

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
- **Contactos** (`/contacts`): `GET` (paginado; `q`, `tag`, `archived` = `false`, `true` o `all`), `POST` (uno o
  una lista, upsert por teléfono), `POST /import` (JSON `{csv, tags}`), `GET|PATCH /{id}`, `GET /{id}/campaigns`,
  `POST /{id}/archive|unarchive`, `POST /archive` (en lote, por `contact_ids` o `tags`) y
  `GET|POST /optouts`, `DELETE /optouts/{phone}`. No hay DELETE de contactos. Los admins pasan `client_id`.
- **Campañas** (`/campaigns`, canal `whatsapp` o `voice`): `GET` (`channel`, `status`), `POST` (con `start: true`
  opcional), `GET /plan` (lo que permite el plan y lo usado), `GET|PATCH|DELETE /{id}` (el `GET` es el
  **polling**: estado, progreso, `results`, `percent`, `eta_minutes`, `in_window`, `goal` y `followup`; el
  `DELETE`, solo de borradores), `POST /{id}/contacts`, `GET /{id}/contacts` (`status`, `result`),
  `GET /{id}/stats`, `GET /{id}/report.csv` y `POST /{id}/start|resume|pause|cancel`. `start` y
  `resume` de una `comercial` piden `no_call_registry_checked: true` (422 `no_call_confirmation_required`).
  `GET /calls`, `/stats` y `/stats/daily` filtran por `campaign_id`.
- **Campañas de WhatsApp** (`/whatsapp`, alias de las anteriores, sobre el mismo código; se borran en una
  versión): `GET|POST /campaigns`, `GET|PATCH|DELETE /campaigns/{id}`, `GET|POST /campaigns/{id}/recipients`
  (lista o CSV posicional), `POST /campaigns/{id}/start|pause|cancel`, `GET|POST /optouts` y
  `DELETE /optouts/{wa_id}`. Envío y reglas en [`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md), 5.5 y
  [`LLAMADAS_SALIENTES_PLAN.md`](LLAMADAS_SALIENTES_PLAN.md).
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
  `/stats` no las cuenta como llamadas (`whatsapp` aparte).
- **Filtros de fecha** (`/calls`, `/stats`, `/stats/daily`): toman días locales de `tz` (zona IANA,
  default `BILLING_TIMEZONE`). `status` se puede repetir.

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
| Backend | `make test` (o `.venv/bin/pytest`) | API (auth, permisos, tiers, clientes, mails y alta de clave (`test_mail.py`), agentes y versiones, inventario de números, llamadas y límites, fechas por zona, cuentas, conversaciones y alta de WhatsApp, plantillas, ruteo por contacto), seguridad del dashboard público (`test_security_public.py`), migración 0005 de ida y vuelta, cuotas, motor con LLM falso, WhatsApp (webhook, service con payloads de Meta y Graph simulado) y escenarios contra el LLM real (se saltean si no responde). |
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
