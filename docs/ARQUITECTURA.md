# Arquitectura

Plataforma multi-cliente de agentes con IA que atienden por teléfono, WhatsApp y navegador, con inferencia
propia. Este documento es la referencia técnica de la app (API, UI, worker de voz, base). La infraestructura
(GPUs, servicios de inferencia, hosts) está en [`INFRA.md`](INFRA.md), la capacidad en
[`capacity/`](capacity/README.md), el uso de la UI en [`GUIA_UI.md`](GUIA_UI.md) y el detalle de cada función en
[`features/`](features/).

## Componentes

```text
                     ┌──────────────┐  cookie de sesión / API key / OAuth (MCP)
  navegador ────────►│  app :8011   │◄──────────── sistemas y agentes de IA del cliente
  (SPA web/dist)     │  FastAPI     │◄──────────── Meta (/wa/webhook), Mercado Pago (/mp/billing/webhook)
                     │  /api/v1     │── dispatch ──┐
                     └──────┬───────┘              ▼
                            │               ┌─────────────┐   SIP    ┌──────────┐   SIP   ┌───────┐
                     ┌──────▼───────┐       │  LiveKit    │◄────────►│ Asterisk │◄──────►│ Anura │◄── PSTN
                     │ PostgreSQL   │◄──────│  + SIP      │          └────┬─────┘        └───────┘
                     │ (db)         │       └─────┬───────┘               └── TLS :5061 ◄── Meta (llamadas de WhatsApp)
                     └──────▲───────┘             │ job (room)
                            │              ┌──────▼───────┐   HTTP (API OpenAI)
                            └──────────────│ agent        │──────────► vllm-llm, stt-parakeet, vllm-tts
                                           │ worker de voz│──────────► tools-runner (código del cliente)
                                           └──────────────┘
```

| Proceso | Código | Qué hace |
|---|---|---|
| `migrate` | `migrations/`, `app/cli.py` | Una vez antes de `app` y `agent`: `alembic upgrade head` y el seed idempotente. |
| `app` | `app/main.py`, `app/api/` | API `/api/v1`, la SPA, el MCP (`/mcp`), OAuth, los webhooks de WhatsApp y Mercado Pago, las páginas de `llamar.` y `telefono.`. Crea conversaciones y llamadas, admite por tier y despacha el worker a una room de LiveKit. Loops en el lifespan: barrido de WhatsApp, campañas, webhook de campañas, cobros y resumen por email. |
| `agent` | `app/voice/worker.py` | Worker de LiveKit Agents: STT → motor → TTS. Salientes (metadata del despacho) y entrantes (dispatch rule, sin metadata). Las llamadas directas del equipo (sin agente) van por `app/voice/direct.py`. |
| `db` | `app/models/` | PostgreSQL 16: tenencia, agentes, conversaciones, llamadas, todo. |
| `tools-runner` + `tools-egress` | `tools-runner/` | Sandbox Deno para las herramientas de código, con salida a internet solo por Smokescreen ([`features/HERRAMIENTAS.md`](features/HERRAMIENTAS.md)). |
| `crm` | `crm/` | CRM de ventas propio, base `crm` aparte ([`features/CRM.md`](features/CRM.md)). |

`app` y `agent` son la misma imagen (`Dockerfile` multi-etapa: Node compila la SPA y Python la sirve) con
distinto comando. **Un solo worker de uvicorn:** el debounce y el lock por contacto de WhatsApp, el cupo de ritmo
del dialer, los límites de login y el `api_limiter` viven en memoria; con más de un worker se rompen.

## Código

```text
app/
  main.py            create_app(): routers en /api/v1, webhooks, MCP, OAuth, hosts llamar./telefono., SPA; lifespan con los loops
  config.py          Settings (pydantic-settings, .env)
  db.py              Base, jsonb, engine y sessionmaker
  runtime.py         ConversationEngine compartido por API y worker
  cli.py             seed (tier Interno, cliente atentina, agentes de referencia, número de Anura), create-admin, create-api-key
  api/
    deps.py          sesión de base, Principal (usuario, API key, OAuth, soporte), require_admin, require_not_support,
                     scoped_client_id, client_ip, rate_limit, inference_access
    http.py          middlewares: tope de cuerpo, CSRF por Origin, HTTPS, headers (CSP, HSTS)
    schemas.py       contratos pydantic (fuente del OpenAPI y de los tipos de la UI)
    errors.py        ServiceError -> JSON {detail, code, errors}; 500 sin detalles internos
    oauth.py         OAuth 2.1 del MCP: metadata .well-known, /oauth/authorize|register|token|revoke, grants
    call_link_host.py, phone_app_host.py   páginas públicas de llamar.<dominio>/<token> y telefono.<dominio>
    internal_metrics.py  /internal/metrics para Prometheus
    routers/         un archivo por recurso (ver "API")
  services/          negocio sin HTTP (lo usan la API, el MCP y el worker)
    quota.py         admisión con lock, consumo del mes, saldo en curso, canales de Anura, derivaciones
    limits.py        límites efectivos (tier + ajustes) y check_* por función del plan
    features.py      TIER_HAS y plan_features (GET /plan/features)
    calls.py         salientes, pruebas, loadtest y entrantes (start_inbound); borrado
    livekit.py       despacho, tokens de participante, trunks SIP en caliente
    agents.py        alta, validación, versionado, archivo
    phone_numbers.py, phones.py      inventario de números; normalización E.164 única
    contacts.py, blocked_numbers.py  agenda, bajas por canal, números bloqueados
    campaigns.py, campaign_calls.py, campaign_reports.py, campaign_callbacks.py   campañas (común, intentos de voz, reportes, webhook)
    handoff.py, events.py            equipo, áreas, horario; registro de eventos
    direct_calls.py  llamadas directas: saliente, presencia, timbre del panel, respaldo al agente
    call_links.py    link público para llamar
    tools.py         herramientas, secretos y credenciales del cliente
    llm_connections.py  conexiones de LLM del cliente (BYOK)
    reports.py, report_stats.py      lista y detalle de conversaciones; reportes agregados en SQL
    inference.py, api_usage.py, api_requests.py   gateway de la API de inferencia, cupos y log por pedido
    oauth.py, mcp_usage.py           OAuth 2.1 del MCP; uso por herramienta
    branding.py      marca blanca: colores, contraste, logo
    signup.py, legal.py, legal_gate.py   registro autoservicio; aceptaciones y pedidos de baja; corte por condiciones
    security.py, profile.py, session_switch.py, ratelimit.py   argon2, JWT, API keys; perfil; pase de sesión panel↔teléfono; topes en memoria
    wa_routing.py    ruteo por contacto de WhatsApp
    system_status.py, platform_metrics.py   pantalla Sistema del admin; métricas para Prometheus
    tts.py, voices.py, demo.py, contact.py  prueba de voz, catálogo, demo y formulario de la landing
    errors.py        NotFound, Forbidden, Conflict, Invalid, QuotaExceeded, Upstream
  models/            ORM SQLAlchemy 2: tenancy, agents, conversations, calls, campaigns, handoff, whatsapp, tools,
                     llm, oauth, billing, legal, call_links, contact
  conversation/      el motor: engine, models (Workflow = definición), workflow (validación), store, contact
                     (datos de campaña y motivo), opening_audio, recordings
  agents/            templates/asistente.json (plantilla), reference/*.json (agentes de referencia),
                     definitions.py (DbDefinitions), templates.py (GENERIC_RULES, en blanco, referencia)
  llm/               client.py (OpenAI, tools nativos, streaming), anthropic_client.py, resolver.py (qué LLM por turno),
                     prompt.py, params.py (hiperparámetros), platform_tools.py (end_call, transfer_call), external.py (tu propio agente)
  tools/             herramientas del cliente: schema, runtime (http, code, SSRF), conversation (el turno con herramientas)
  voice/             worker.py, latency.py, speech_text.py (texto a palabras para el TTS, es-AR), handoff.py (transferencia),
                     listen.py (VAD + STT por frase), direct.py (llamadas directas)
  whatsapp/          webhook (firma), graph.py (Cloud API), store.py, service.py (turnos, barrido), audio.py (notas de voz),
                     signup.py (Embedded Signup), own_app.py (app de Meta del cliente), crypto.py, campaigns.py, sender.py
  campaigns/         loop.py (por canal), dialer.py (voz), voicemail.py (contestador), callbacks.py (webhook)
  billing/           service.py (ciclo del plan), mp.py (Mercado Pago), webhook.py, loop.py (vencimientos)
  legal/             texts/ (condiciones y privacidad con versión), sync.py (copia a la landing)
  mail/              Resend: sender, layout, messages (bienvenida, número, clave), notify, call_summary (loop del resumen)
  mcp/               server.py (POST /mcp), catalog.py (herramientas), guides.py (resources y prompts), docs.py (genera el catálogo)
web/                 SPA React (ver "Frontend")
crm/                 FastAPI propio: routes (leads, outreach, reminders), services (Resend, GA, envío), migrations
tools-runner/        server.ts (POST /run) y runner.js (un proceso Deno por ejecución); egress/ (Smokescreen)
landing/             sitio público Astro ([`features/LANDING.md`](features/LANDING.md))
migrations/          Alembic, 0001 a 0042
tests/               pytest, solo con LLM falso
scripts/             ops, capacidad, loadtest, evals, dev_backend.sh
```

**Capas:** los routers validan la entrada, resuelven permisos y llaman a `services/`; los servicios tienen la
lógica y levantan `ServiceError` sin saber de HTTP; los modelos son solo persistencia. El worker de voz y el MCP
usan los mismos servicios (el MCP, por dentro de `/api/v1`).

**Migraciones principales:** 0002 tenencia, 0003 inventario de números, 0004-0005 WhatsApp y Embedded Signup,
0009 API de inferencia, 0011 ajustes de límites, 0012 cobros, 0015 ruteo de WhatsApp, 0016 conexiones de LLM,
0017 agenda y campañas, 0018-0019 links para llamar, 0020 resumen por email, 0021 números bloqueados, 0022
`api_requests`, 0023-0024 equipo, derivaciones y eventos, 0025-0026 funciones por plan, 0028-0029 OAuth y uso
del MCP, 0030 agente propio por plan, 0031 legal, 0032 herramientas, 0033 un solo motor y `tool_versions`, 0034
marca blanca, 0035 secretos y credenciales del cliente, 0036 reportes, 0037 `tiers.internal`, 0038 app de Meta
propia, 0039 llamadas directas, 0040-0041 agenda, 0042 limpieza (columnas sin uso y slug `demo_booking`).

## Modelo de datos

```text
tiers 1───* clients 1───* agents 1───* agent_versions
                │            ├───* agent_secrets
                │            └───1 call_links
                ├───1 client_branding, ───* subscriptions, ───* billing_payments
                ├───* phone_numbers (SET NULL al liberar) ───* phone_number_members
                ├───* users (rol client)              users (rol admin: sin cliente)
                ├───* api_keys ───* api_usage_daily, api_requests
                ├───* client_limit_adjustments
                ├───* contacts, contact_optouts, blocked_numbers
                ├───* campaigns 1───* campaign_contacts ───* call_logs (intentos)
                │              1───* campaign_callbacks
                ├───* team_members ───* handoff_area_members *─── handoff_areas
                ├───* user_presence, events
                ├───* tools 1───* tool_versions; tool_runs
                ├───* client_secrets, credentials, llm_connections
                ├───* wa_accounts 1───* wa_routes, wa_threads, wa_account_status_log
                └───* conversations 1───1 call_logs        (voz y web)
                         │          1───1 wa_threads       (WhatsApp)
                         │          1───* wa_messages, handoff_legs, call_rings
                         └── agent_id + agent_version (la versión con que corrió)
users ───* oauth_grants ───* oauth_codes, oauth_tokens;  oauth_clients;  mcp_tool_usage
legal_acceptances, consumer_requests, contact_requests (sueltas, con client_id opcional)
```

Las fechas se guardan en UTC sin zona; la API las devuelve con zona. NULL en un límite es ilimitado y 0, no
incluido.

### Tenencia, planes y acceso

| Tabla | Claves y reglas |
|---|---|
| `tiers` | Límites de llamadas: `max_concurrent_calls`, `max_calls_per_hour`/`_day`/`_month`, `inbound_minutes`, `outbound_minutes`, `max_phone_numbers`. Campañas y agenda: `campaign_channels` (`[]`, `whatsapp`, `voice`), `max_campaigns_per_month`, `max_campaign_contacts`, `max_campaign_concurrency`, `max_contacts`, `campaign_followup`. Inferencia: `api_llm_input_tokens`, `api_llm_output_tokens`, `api_tts_minutes`, `api_stt_minutes`, `api_rate_limit`. Funciones: `max_call_links`, `max_team_members`, `max_tools`, `code_tools`, `whatsapp`, `external_agent`, `white_label`, `advanced_reports`, `direct_calls`. Venta: `price_ars` (NULL = no se vende por el dashboard, 0 = el gratis del registro), `public` (se ofrece en el registro y en Plan), `sort`. `internal`: el tier de Atentina, no se ofrece ni cuenta en las estadísticas. Ver "Funciones por plan". |
| `clients` | `slug` único, `tier_id` (RESTRICT), `active`, `created_via`, datos fiscales (`legal_name`, `tax_id`, `tax_condition`), resumen por email (`call_emails`, `call_emails_to`), `direct_recording_notice`. |
| `client_limit_adjustments` | Ajuste de un límite numérico del tier para un cliente: `field`, `mode` (`add`/`set`), `value`, `starts_on`/`ends_on` (inclusive, `BILLING_TIMEZONE`), `note`, `created_by`. Ver "Límites por tier". |
| `client_branding` | 1:1 con el cliente (PK `client_id`): `enabled`, `logo`, `logo_ratio`, `color_primary`, `color_header`, `color_accent`, `powered_by`, `updated_by`. Ver "Marca blanca". |
| `users` | `email` único; `role` admin o client (CHECK: client ⇔ `client_id`); hash argon2; `session_version`; `welcomed_at`; `last_login_at`. |
| `api_keys` | SHA-256 (`key_hash` único), `prefix` visible, `revoked_at`, `last_used_at`, `scopes` (ver "Autenticación"). |
| `api_usage_daily`, `api_requests` | Consumo de la API de inferencia por día y key (pedidos, tokens, segundos de TTS/STT) y un registro por pedido (`kind`, `status`, `http_status`, `duration_ms`, `ttfb_ms`, tokens, segundos, `voice`), sin contenido ([`API_INFERENCIA.md`](API_INFERENCIA.md)). |
| `subscriptions`, `billing_payments` | Plan pago: `method`, `status` (`pending`, `active`, `past_due`...), `current_period_end`, `grace_until`, `pending_tier_id`, `cancel_at_period_end`, `mp_preapproval_id`; pagos con `amount_ars`, `paid_on`, `period_end`, `mp_payment_id`, `recorded_by` ([`features/COBROS.md`](features/COBROS.md)). |
| `legal_acceptances`, `consumer_requests` | Cada aceptación (`document`, `version`, `sha256`, `statement`, `channel` `signup`/`panel`, IP, user agent) y los botones de arrepentimiento y de baja (`kind`, `code`, `status`) ([`features/LEGAL.md`](features/LEGAL.md)). |
| `oauth_clients`, `oauth_grants`, `oauth_codes`, `oauth_tokens`, `mcp_tool_usage` | OAuth 2.1 del MCP (registro dinámico o por documento, permiso por usuario y cliente con `scope` y `resource`, PKCE) y uso por día, cliente y herramienta ([`features/MCP.md`](features/MCP.md)). |

### Agentes, conversaciones y llamadas

| Tabla | Claves y reglas |
|---|---|
| `agents` | `(client_id, slug)` único; `version` y `definition` vigentes (copia de la última versión); `archived_at`. |
| `agent_versions` | `(agent_id, version)`; inmutables, con `created_by`. |
| `conversations` | Estado del motor (`fields`, `messages`, `progress`), `client_id`, `agent_id` + `agent_version` (RESTRICT; `agent_id` nulo en las directas), `channel` (`voice` o `whatsapp`, fijo al crearla), `status`. Al terminar: `outcome`, `goal`, `conversion` (`complete`, `partial`, `empty`), `llm_input_tokens`/`llm_output_tokens`. `legacy_workflow_id` para las anteriores a los agentes. |
| `call_logs` | Una por conversación de voz: `mode` (`saliente`, `entrante`, `prueba`, `web`, `loadtest`, `directa`), `status` (`pendiente`, `sonando`, `en_curso`, `finalizada`, `fallida`, `rechazada`, `cancelada`), `phone`, `phone_number_id`, inicio, fin, `duration_seconds`, `latency`, `ended_reason`, `sip_status`, `room` (para cortar), `campaign_contact_id`, `call_link_id`, `summary_email`, `user_id` y `answered_by` (`agent`/`team`), `opted_out_confirmed`. Base del consumo. |
| `phone_numbers` | `e164` único; `client_id` NULL = libre; `agent_id` solo con cliente (CHECK); `label`, `provider`, `assigned_at`, `suspended_at`. Quién atiende: `answer_mode` (`team` o `agent`), `ring_first`, `ring_seconds`, `schedule`, `team_fallback`, `team_fallback_message`; personas en `phone_number_members`. |
| `call_links` | Un link por agente: `token`, textos de la página, `image`, `max_call_seconds`, `max_concurrent`, `daily_minutes`, `paused`, `revoked_at` ([`features/LINK_LLAMADA.md`](features/LINK_LLAMADA.md)). |
| `blocked_numbers` | `(client_id, phone)` con `note`: sus entrantes (línea o WhatsApp) se cortan sin atender. API `/blocked-numbers`. |
| `contact_requests` | Formulario de contacto de la landing, con `email_status`. |

### Campañas, equipo y herramientas

| Tabla | Claves y reglas | Detalle |
|---|---|---|
| `contacts` | `phone` (E.164) único por cliente, `name`, `email`, `notes`, `source`, `archived_at`. **No se borran, se archivan**; `max_contacts` cuenta los activos. | [`CAMPANAS.md`](features/CAMPANAS.md) |
| `contact_optouts` | Bajas por `(client_id, phone, channel)` (`whatsapp`, `voice`, `all`) y `source`; siguen aunque el contacto se archive. | ídem |
| `campaigns`, `campaign_contacts`, `campaign_callbacks` | Campaña por `channel` (`whatsapp` o `voice`, CHECK por canal) con `status`, horario, programación, `purpose`, webhook (`callback_url`, secreto cifrado); cada contacto con `vars`, `status`, `result`, intentos y seguimiento; cola del webhook. | ídem |
| `team_members`, `handoff_areas`, `handoff_area_members` | Personas (`phone`, `whatsapp`, `user_id`), áreas con estrategia, timbre, horario, respaldo, `return_digits` y mensajes; miembros en orden. | [`EQUIPO_TELEFONIA.md`](features/EQUIPO_TELEFONIA.md) |
| `handoff_legs` | Cada intento de pasar la llamada a una persona (o de sonar el celular en una entrante al equipo): `result`, `sip_status`, tiempos y `billed_seconds` (minutos salientes). | ídem |
| `user_presence`, `call_rings` | Disponible en el panel (pulso, TTL 60 s); timbre de una entrante al equipo por usuario (el primero que atiende se queda). | ídem |
| `events` | Línea de tiempo (`call.*`, `handoff.*`, `hold.*`, `team.*`), `id` incremental para leer con cursor. | ídem |
| `tools`, `tool_versions`, `tool_runs` | Herramienta del cliente (`slug`, `type` `http`/`code`, `definition`, `revision`, última prueba), cada revisión y cada ejecución (`ok`, `status_code`, `ms`). | [`HERRAMIENTAS.md`](features/HERRAMIENTAS.md) |
| `client_secrets`, `agent_secrets`, `credentials` | Secretos del cliente con valor propio opcional por agente (cifrados, `last4`) y credenciales de autenticación de una API. | ídem |
| `llm_connections` | Conexión de LLM del cliente: `kind` (`openai_compatible`, `openrouter`, `anthropic`), `base_url`, `api_key_enc`, `default_model`, `json_mode`, última prueba. | [`LLM_CONEXIONES.md`](features/LLM_CONEXIONES.md) |

### WhatsApp

Detalle en [`features/WHATSAPP.md`](features/WHATSAPP.md).

| Tabla | Claves y reglas |
|---|---|
| `wa_accounts` | Un número: `phone_number_id` único, `waba_id`, `business_id`, número visible, `client_id`, `agent_id` (RESTRICT), `access_token` (NULL = `WA_ACCESS_TOKEN`; cifrado con `WA_TOKEN_KEY`), `pin_enc`, `active`, `status` (`connected`, `pending`, `disconnected`) con motivo, `quality_rating`, `messaging_limit`, `source` (`manual`, `embedded_signup`, `coexistence`, `own_app`), `connected_by`. Con `own_app` (app de Meta del cliente): `app_secret` y `verify_token` cifrados y `webhook_key` (única: su webhook es `/wa/webhook/<clave>`). Sin borrado: se desactiva. |
| `wa_routes` | Ruteo por contacto de una cuenta: `(account_id, agent_id)` con la lista `contacts` (wa_id). Un contacto en una sola regla. |
| `wa_threads` | Una por conversación de WhatsApp: cuenta, `wa_id`, nombre del perfil, `last_user_at`, `closed_at`. |
| `wa_messages` | Uno por `wamid` (dedupe de reenvíos de Meta), dirección, tipo, estado y error de Meta; sin contenido (el texto va en `conversations.messages`). |
| `wa_account_status_log` | Cada cambio de estado, calidad o límite de una cuenta (reportes). |

**Migraciones:** el esquema lo manejan las de Alembic (`make migrate`; antes de desplegar, `make migrate-test`
contra una copia del backup). Un cambio de modelo va con una migración nueva, probada de ida y vuelta en
PostgreSQL y SQLite; `alembic check` no tiene que dar diferencias. `create_all` solo para SQLite en tests y evals.

## Definición de un agente

La definición es un JSON (`app/conversation/models.py`, clase `Workflow`; JSON Schema en
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

- `id` y `version` los fija la app (slug y número de versión).
- **`fields`:** `type` `string`, `integer`, `boolean`, `email`, `email_or_phone`, `choice` (con `options`),
  `digits` o `phone`; `required` o `required_if` (solo igualdades); `question` es una pregunta sugerida;
  `label` (opcional) es el nombre para mostrar y no va al prompt. Un dato `phone` se precarga con el número de la
  otra punta en las entrantes y salientes (`progress.preloaded`) y el agente no lo pregunta.
- **`completion.outcomes`:** gana el primero cuyo `when` se cumple; el último va sin `when` (default);
  `goal: true` marca el objetivo; `message` es un cierre sugerido al LLM.
- **`generation`** (opcional) y **`llm`** (LLM por etapa, desde el turno N): hiperparámetros del catálogo
  `app/llm/params.py` (temperatura, `top_p`/`top_k`/`min_p`, razonamiento y su tope, `max_tokens`, esfuerzo), con
  override por etapa; cada proveedor manda los que soporta. Sin `generation` rigen `LLM_THINKING`,
  `LLM_THINKING_BUDGET`, `LLM_TEMPERATURE`, `LLM_TOP_P`, `LLM_TOP_K`, `LLM_MIN_P` de la configuración. El editor usa
  `GET /api/v1/llm/params` ([`features/LLM_CONEXIONES.md`](features/LLM_CONEXIONES.md)).
- **`tools`** y **`tool_settings`:** herramientas del cliente por slug (`[{"tool": "<slug>"}]`) y, opcional,
  `max_calls_per_turn` (default 3, hasta 10) con `limit_message` ([`features/HERRAMIENTAS.md`](features/HERRAMIENTAS.md)).
- **`external`** ("Tu propio agente", con `tiers.external_agent`): cada turno lo contesta el endpoint del cliente
  (`connection`, `model`, `system`, `first_token_timeout_ms`, `error_message`, `max_errors`, `on_errors`
  `hang_up` o `transfer:<area_id>`), sin el prompt de la definición ni extracción; no va con `tools`.
  `AgentOut.own_agent` lo marca ([`features/LLM_CONEXIONES.md`](features/LLM_CONEXIONES.md)).
- **`handoff`:** áreas (`area_id` y `when`, hasta 10) y música de espera (`hold_music`: `enabled`, `track` de
  `GET /hold-music`, `volume`). Al guardar se valida que cada área sea del cliente. El modelo deriva con
  `transfer_call` ([`features/EQUIPO_TELEFONIA.md`](features/EQUIPO_TELEFONIA.md)).
- **`wa_session_minutes`:** ventana de contexto de WhatsApp del agente (NULL = `WA_SESSION_HOURS`).
- **`{{today}}` y `{{now}}`:** la fecha no se inyecta; el agente la tiene si sus reglas, su base de conocimiento o
  su objetivo usan esas variables.
- **`conversation.opening_audio`** (default `false`) y **`opening_delay_ms`** (200): al guardar, `app` sintetiza
  la apertura entera en un pedido (en segundo plano) y la deja en
  `storage/openings/<agent_id>/<versión>-<voz>.wav` (`OPENING_AUDIO_DIR`); el worker la reproduce si coinciden
  versión, voz y texto, y si no (otra voz, `{{variables}}`, falló el TTS) la sintetiza en vivo frase por frase. Al
  cambiar el checkpoint del TTS, borrar `storage/openings/` o volver a guardar los agentes
  (`app/conversation/opening_audio.py`).
- **`call_summary_email`** (default `false`): al terminar cada llamada conectada (entrante, saliente suelta o por
  el link; no campañas, prueba ni loadtest) se manda al cliente un email con datos, resultado, conversación (hasta
  `CALL_SUMMARY_TRANSCRIPT_CHARS`) y link. El worker deja `call_logs.summary_email = pending` y un loop de `app`
  lo manda por Resend (`app/mail/call_summary.py`, cada `CALL_SUMMARY_TICK_SECONDS`; 4 intentos: ya, 1 min,
  10 min, 1 h; `Idempotency-Key` por llamada y destino). El cliente lo apaga o elige destinos en
  `GET/PUT /clients/{id}/call-emails` (vacío = sus usuarios activos). Estados: `sent`, `disabled` (sin
  `RESEND_API_KEY`), `skipped`, `failed`. Al prenderlo en el editor se agrega un dato `telefono` si no hay uno de
  tipo `phone`. Medido con Gemma 4 26B sin recordatorio en el prompt: pide el teléfono al cierre 0 de 10 si la
  definición no lo tiene como dato.
- **`record_audio`** (default `false`): un WAV mono de 16 kHz por mensaje en
  `storage/recordings/<conversation_id>/NNN.wav` (`CALL_RECORDINGS_DIR`, `app/conversation/recordings.py`), con su
  número en `Message.recording`. En llamadas, cliente y agente por separado; el del cliente recortado a lo que el
  VAD marcó como habla (`user_state_changed`, 0,3 s de pre-roll); si el turno se deshace (ver "Motor"), su audio
  pasa al turno siguiente. En WhatsApp, el audio entrante y la nota de voz enviada (si la respuesta sale en
  texto, no hay WAV del agente). Se escucha en el chat del dashboard por
  `GET /calls/{conversation_id}/recordings/{n}`. `storage/` está en el backup.
- **`recording_notice`** (default `false`): con `record_audio`, "Esta llamada está siendo grabada." antes de la
  apertura (`RECORDING_NOTICE` en `app/voice/worker.py`), fuera del contexto del LLM; no aplica a WhatsApp.
- **Validación al guardar:** nombres de campo en minúsculas, `choice` con `options`, `required_if` y `when` sobre
  campos existentes, ids de resultado únicos, el último sin `when`, `agent.voice` en el catálogo y nunca
  `default` (tumba el TTS), conexiones y áreas del mismo cliente.
- **Versionado:** `PUT /agents/{id}/definition` crea la versión N+1 si cambió algo (con lock del agente). La
  conversación guarda `agent_version` y el motor carga siempre esa (`DbDefinitions`, cacheada por
  `(agent_id, version)`): editar no afecta las llamadas en curso ni el historial.
- **Alta:** en blanco (un dato y el resultado por defecto) o desde la única plantilla,
  `app/agents/templates/asistente.json` (`template_id: "asistente"`), con las reglas genéricas de comportamiento
  (`GENERIC_RULES` en `app/agents/templates.py`: una pregunta por turno, no inventar, cuándo cortar o derivar),
  editables como cualquier regla. La UI la edita por formulario (`web/src/features/agents/DefinitionForm.tsx`,
  `draft.ts`), con el JSON como alternativa.
- **Quién los crea:** un usuario o API key de un cliente, en el suyo; el admin, entrando como el cliente. Todo
  pedido sobre un agente pasa por `get_agent`: el de otro cliente responde 404. `POST /agents/prompt` devuelve el
  prompt armado sin guardar, para cualquiera con acceso al agente.

## Motor conversacional

Uno solo (`app/conversation/engine.py`, `ConversationEngine`), igual para voz, WhatsApp y texto.

- **Turno:** sin estado por turno. El prompt de sistema se arma de la definición (agente, objetivo, reglas,
  datos con su pregunta y condición, base de conocimiento, mensajes de cierre) y del protocolo de la plataforma
  (herramientas y su resultado), sin frases de comportamiento en el código (`app/llm/prompt.py`). La
  conversación va como mensajes multiturno; el LLM responde texto en streaming (`on_message` en
  `app/llm/client.py`): el TTS empieza con la primera frase. Antes del TTS cada frase pasa por el normalizador
  `app/voice/speech_text.py` (números, horas, fechas, plata, emails, teléfonos y códigos a palabras, es-AR).
- **Herramientas:** function calling nativo (OpenAI y Anthropic). El modelo ve las del cliente y las de la
  plataforma (`end_call` con `motivo` `terminada` o `fuera_de_tema`; `transfer_call` con `area`, solo si la
  llamada tiene áreas; `app/llm/platform_tools.py`). La plataforma ejecuta, dice una frase de voz mientras tanto y
  le devuelve el resultado; tope de rondas por turno en `tool_settings`.
- **Qué LLM:** `app/llm/resolver.py` elige por turno entre la inferencia propia (default y respaldo) y una
  conexión del cliente según `Workflow.llm`.
- **Extracción:** una llamada aparte al LLM, con prompt y esquema JSON armados desde los `fields` y la
  conversación completa; una sola vez, al terminar (`end_call`) o al cortar (`ConversationEngine.finish`).
  La app solo valida los datos (campos inexistentes o de tipo inválido no se guardan) y calcula el resultado con
  `completion.outcomes`; si sería el objetivo pero faltan obligatorios, es `incompleta`.
- **Qué decide cada uno:** el LLM decide la respuesta, cuándo termina y si deriva; la app no corrige lo que dice
  (ver "Reglas de desarrollo" en `AGENTS.md`).
- **Voz, interrupciones:** si el cliente sigue hablando y la respuesta sonó menos de `CONTINUATION_WINDOW`
  (1,5 s en `app/voice/worker.py`: ~1 s de respuesta más los 0,5 s de voz que LiveKit exige para interrumpir), es
  la misma frase: `retract_last_turn` deshace el turno (y su extracción) y el siguiente recibe todo junto. Los
  turnos se procesan de a uno, porque LiveKit genera antes de confirmar el fin de turno (preemptive generation).
  Endpointing: 0,4 s si el turn detector cree que la frase terminó y hasta 1 s si duda
  (`VOICE_MIN_ENDPOINTING_DELAY`, `VOICE_MAX_ENDPOINTING_DELAY`).
- **WhatsApp:** junta los mensajes seguidos en un turno (`WA_DEBOUNCE_SECONDS`, el equivalente de la ventana de
  continuación).
- **Agentes de referencia** (`app/agents/reference/*.json`, para seed, evals y tests; no se ofrecen en la UI):
  `atentina_comercial` (la home, la línea y el WhatsApp de Atentina), `demo_booking` (agenda una demo; atiende el número
  de Anura y lo usa el test de capacidad),
  `landing_turnos`, `landing_cobranzas` y `landing_reclamos` (la demo de la landing, sin el prefijo),
  `sales_discovery` y `berlin_signup` (tests) y `eval_*` (eval del LLM y de herramientas).
  Editarlos no cambia los agentes ya creados.
- **Probar por texto:** `POST /api/v1/conversations {"agent_id"}` y `POST /conversations/{id}/turns {"message"}`
  (en la UI, Playground o la pestaña "Probar" del agente); aparecen con origen "API". **Por voz:**
  `POST /api/v1/calls {"agent_id"}` devuelve el `join_url` de la prueba (`POST /calls/{id}/join` da el token); con
  `"phone"` marca por la troncal.
- **Medir** (los evals informan y terminan en 0):

| Comando | Qué mide |
|---|---|
| `make eval-llm`, `make eval-llm-juez` | Calidad del LLM por tipo de agente y de cliente, con cliente simulado y juez ([`eval/`](eval/README.md)). |
| `make eval-tools LLM=...` | Llamadas a herramientas con un LLM real ([`features/HERRAMIENTAS.md`](features/HERRAMIENTAS.md)). |

## Flujos

### Llamada saliente o de prueba (`POST /api/v1/calls`)

1. `services/calls.prepare_call` (en un thread: la base es bloqueante) valida el agente (visible y no archivado),
   el teléfono E.164 y la voz, y elige el caller ID (el pedido o el primero del cliente). Con `contact_id`, el
   contacto tiene que ser del cliente y estar activo; sus datos van como `vars`. Un teléfono en las bajas de voz da
   409 `opted_out` (salvo en campañas, que filtran antes).
2. `engine.new_conversation(session=s)` arma el estado con la versión vigente. `context` (el motivo, hasta 2000
   caracteres) va al prompt y a la extracción como "MOTIVO DEL LLAMADO" (`conversation/contact.py`).
3. `quota.admit(s, client, mode)` toma el lock del cliente (`SELECT … FOR NO KEY UPDATE OF clients`) y verifica
   cliente activo, simultáneas, topes de llamadas por hora, día y mes (cuenta `call_logs` sin las `rechazada`) y
   minutos de esa modalidad. Devuelve los segundos que quedan.
4. En la misma transacción se guardan conversación y `call_logs` (`pendiente`); el commit suelta el lock. Todo
   por una sola conexión: pedir otra con el lock tomado agotaba el pool bajo carga.
5. `livekit.dispatch_call` crea el dispatch con `{conversation_id, phone, voice, loadtest,
   max_duration_seconds, from_number, handoff}`. Si falla: `fallida` (`dispatch_failed`) y 502.
6. El worker marca por SIP (`create_sip_participant` con `max_call_duration` y `sip_number`) o, en prueba, espera
   al participante del navegador.
7. Estados: `sonando` → `en_curso` → `finalizada` (con duración y latencia) o `fallida`.

### Llamada entrante

1. Anura → Asterisk → trunk entrante de LiveKit → la dispatch rule crea una room `anura-*` y despacha el worker
   sin metadata. Anura manda el número marcado en formato nacional y Asterisk lo pasa como `+54` + 10 dígitos
   (sin uno válido, `+54<ANURA_DID>`); un número que no está en el trunk da 404 (`make livekit-sip`,
   [`TELEFONIA_ANURA.md`](TELEFONIA_ANURA.md)).
2. El worker lee el número marcado (`sip.trunkPhoneNumber`) y `calls.start_inbound` lo busca en `phone_numbers`:
   - libre, o sin agente y sin equipo: se corta (`number_without_agent`);
   - el que llama está en `blocked_numbers` (por el caller o el `wa.wacid`): `rechazada` (`blocked_number`);
   - sin lugar o sin minutos: `rechazada` y el que llama escucha `QUOTA_REJECT_MESSAGE`;
   - `answer_mode=team` con personas, plan con `direct_calls` y condiciones aceptadas (`legal_gate`): conversación
     sin agente (`answered_by=team`) y el worker toma la rama de las llamadas directas; si falta algo de eso, va al
     agente del número. Una regla de `wa_routes` que elige agente gana sobre el equipo;
   - si no: conversación con el agente del número, `entrante`, `answered_by=agent`.
3. Llamadas de WhatsApp: Meta → `sip.atentina.com.ar:5061` (TLS, SRTP) → Asterisk → LiveKit. El inbound trunk
   mapea `X-WA-Meta-Wacid` al atributo `wa.wacid`; con regla de ruteo para ese contacto atiende el agente de la
   regla.

### Durante la llamada

- **Turnos:** ver "Motor conversacional".
- **Corte por minutos:** el worker mira `calls.call_remaining_seconds` cada `QUOTA_CHECK_SECONDS` (15 s): las
  terminadas del mes más lo que llevan todas las en curso del cliente. En 0 (o cliente desactivado) dice
  `QUOTA_END_MESSAGE`, corta y deja `ended_reason=quota_exhausted`. La saliente además sale con
  `max_call_duration` = minutos que quedan al empezar. Las llamadas sin teléfono cortan en
  `max_duration_seconds` (`ended_reason=max_duration`).
- **Cortar desde el panel o la API:** `POST /calls/{id}/hangup` cierra la room (`call_logs.room`) y la llamada
  termina con `hangup_by_user`, que `finalize` no pisa.
- **Fin de tema:** con `end_call` y `motivo=fuera_de_tema` el resultado es "Fuera de tema"
  (`ended_reason=off_topic`) y se corta aunque lo interrumpan.
- **Al cortar:** `finalize` espera la extracción y guarda duración, fin, latencia y los datos de reportes.

### Otros flujos (detalle en su doc)

- **Demo de la landing** (`/api/v1/demo`): sesión JWT por Turnstile (`aud=atentina-demo`), límites por IP y cupo
  diario, `calls.start_call` con un `Principal` del cliente `atentina` solo para `DEMO_AGENTS`, tope
  `DEMO_MAX_CONCURRENT_CALLS`. También el formulario de contacto, el registro y los pedidos de baja
  ([`features/LANDING.md`](features/LANDING.md)).
- **Link para llamar** (`llamar.<dominio>/<token>`): `CallMode.web`, gasta minutos entrantes, Turnstile y topes por
  link ([`features/LINK_LLAMADA.md`](features/LINK_LLAMADA.md)).
- **Campañas** (`/campaigns`, `whatsapp` o `voice`): `app/campaigns/loop.py` en el lifespan delega en el sender
  de WhatsApp y el dialer de voz (cada `CALL_CAMPAIGN_TICK_SECONDS`), que respeta horario, `concurrency`,
  `rate_per_minute` y `CALL_CAMPAIGN_MAX_CONCURRENT` (8, global y sin medir con Gemma), y cada llamada pasa por
  `quota.admit`. Resultado SIP, contestador, reintentos, seguimiento por WhatsApp y webhook firmado en
  [`features/CAMPANAS.md`](features/CAMPANAS.md).
- **Mensaje de WhatsApp:** Meta → túnel (`wa.atentina.com.ar/wa/webhook` o `/wa/webhook/<clave>`) → `app`; firma
  `X-Hub-Signature-256`, 200 sin esperar; dedupe por `wamid`, debounce, lock por contacto, hilo abierto dentro de
  la ventana del agente, `process_turn` y respuesta en texto o nota de voz. No pasa por `quota.admit` ni crea
  `call_logs`. Si `app` se reinicia con mensajes en la ventana de debounce, esos quedan `received` sin respuesta
  ([`features/WHATSAPP.md`](features/WHATSAPP.md)).
- **Derivación a una persona** (`transfer_call`): transferencia atendida en la misma room, con música, whisper,
  confirmación con `1`, modo escucha y vuelta a la IA con el código del área; cada intento es un `handoff_legs`
  y gasta minutos salientes y canales de Anura.
- **Llamadas directas:** el equipo llama desde el panel o atiende las entrantes de un número en `team`, sin
  `AgentSession` ni LLM (VAD + STT por frase, `app/voice/listen.py`); se graban y transcriben siempre. Las dos
  últimas, en [`features/EQUIPO_TELEFONIA.md`](features/EQUIPO_TELEFONIA.md).
- **Herramientas del cliente:** `http` (con SSRF por un backend de red propio de httpcore que conecta a una IP
  global ya validada) y `code` (sandbox `tools-runner`); secretos cifrados; resultado `ok`/`error` al modelo y
  `messages.failed` por el TTS ([`features/HERRAMIENTAS.md`](features/HERRAMIENTAS.md)).

## Límites por tier

| Límite | Dónde se aplica | Qué cuenta |
|---|---|---|
| Simultáneas | `quota.admit` (todas las modalidades) | Llamadas del cliente `pendiente`, `sonando` o `en_curso` creadas hace menos de `CALL_MAX_DURATION_SECONDS` + 10 min (las más viejas se consideran colgadas). |
| Llamadas por hora, día y mes | `quota.admit` | Entrantes y salientes por `created_at`, sin las `rechazada`. |
| Minutos entrantes / salientes | `quota.admit` y el watchdog del worker | `duration_seconds` del mes por modalidad más lo que llevan las en curso; prueba y loadtest no consumen. Las salientes suman las directas y los tramos de derivación (`handoff_legs.billed_seconds`). Mes calendario en `BILLING_TIMEZONE`. |
| Canales de Anura | `quota.busy_channels` contra `ANURA_CHANNELS` (10), en la saliente directa y antes de cada derivación | Entrantes, salientes y directas activas más tramos abiertos; sin canal: 429 `no_channel` en la directa, la derivación no se intenta. Las demás llamadas no lo miran. |
| Números | `phone_numbers.assign`, cambio de tier o de tope | Números asignados; asignar toma el lock del cliente y el del número. |
| Campañas | `limits.check_campaign_*` | Canal en `campaign_channels`, campañas iniciadas en el mes, contactos por campaña, `concurrency` de voz, seguimiento. Al perder un canal, sus campañas pasan a `paused`. |
| Agenda, equipo, links, herramientas | `contacts.py`, `handoff.py`, `call_links.py`, `tools.py` | `max_contacts` (activos), `max_team_members`, `max_call_links`, `max_tools` y `code_tools`. |
| Funciones sí/no | `limits.check_*`, `features.py` | Ver "Funciones por plan". |
| API de inferencia | `deps.inference_access` + `InferenceGateway` | Tokens de entrada y salida, minutos de TTS y STT por mes y pedidos por minuto (`api_limiter`, en memoria); solo el uso por API key ([`API_INFERENCIA.md`](API_INFERENCIA.md)). |

**Ajustes por cliente** (`services/limits.py`): darle a un cliente algo distinto de su tier sin tocarlo. Todo lo
anterior lee `effective_limits(s, client)`, no `client.tier`. Por campo, los `set` vigentes reemplazan el valor
(gana el último) y después se suman los `add`; un `add` sobre ilimitado se rechaza (`already_unlimited`). Vale
entre `starts_on` y `ends_on`; al vencer, vuelve al tier solo. Quitar un ajuste o un `set` más bajo que deje al
cliente con más números de los permitidos da 409 `phone_numbers_limit`. Solo admin
(`GET /clients/{id}/limits`, `POST|DELETE /clients/{id}/limit-adjustments`). `LIMIT_FIELDS` tiene que seguir
igual a las columnas numéricas de `Tier` (`tests/test_limits.py`).

Carreras medidas en PostgreSQL: 20 llamadas simultáneas con tope 3 entran exactamente 3; 5 asignaciones de
números con tope 2, exactamente 2.

## Funciones por plan

Qué incluye un plan sale de los campos del tier, nunca del nombre.

- **`TIER_HAS`** (`app/services/features.py`): una clave por función (`outbound_calls`, `campaigns_voice`,
  `campaigns_whatsapp`, `whatsapp`, `contacts`, `team`, `call_links`, `external_agent`, `custom_tools`,
  `code_tools`, `white_label`, `advanced_reports`, `direct_calls`) con la condición sobre el tier. `plan_features`
  aplica lo mismo a los límites efectivos del cliente; `outbound_calls` pide además un número asignado.
- **`GET /api/v1/plan/features`:** `{tier_name, free, features: {clave: {enabled, reason}}}`; `reason` dice en qué
  planes está ("Disponible en los planes Mostrador y Sucursal", de los tiers no internos y no gratis).
- **UI:** `PlanGate`/`PlanAlert` (`web/src/components/PlanGate.tsx`; aviso con borde amarillo, planes que la
  incluyen y "Mejorar mi plan", panel atenuado), `useFeatureLock`, y candado en la navegación por `feature` en
  `components/nav.ts`.
- **Corte real:** en cada servicio, con 429 `QuotaExceeded`: `whatsapp_not_in_plan` (alta de cuentas; los mensajes
  quedan `ignored` y la llamada de WhatsApp se rechaza), `direct_calls_not_in_plan`, `external_agent_not_in_plan`,
  `campaign_channel_not_in_plan`, `campaign_followup_not_in_plan`, `campaign_concurrency`, `tools_not_in_plan`,
  `code_tools_not_in_plan`, `contacts_limit`, `team_members_limit`, `call_links_limit`. Reportes completos: 403
  `advanced_reports_not_in_plan`. La marca blanca no corta: sin `white_label` no se aplica (`branding.available`).
- Una saliente sin número propio no se corta en la API (las campañas y los tests marcan con `ANURA_DID`); solo la
  UI la bloquea.

**Planes vigentes** (tabla `tiers` de producción; se editan en Tiers):

| | Free | Mostrador | Sucursal | Interno |
|---|---|---|---|---|
| Precio/mes | $ 0 (registro) | $ 29.000 | $ 99.000 | no se vende (`internal`) |
| Simultáneas | 1 | 1 | 3 | sin tope |
| Minutos entrantes / salientes | 20 / 0 | 300 / 300 | 1.200 / 1.200 | sin tope |
| Números | 0 | 1 | 3 | sin tope |
| WhatsApp | No | Sí | Sí | Sí |
| Campañas | No | WhatsApp y voz (3/mes, 50 contactos; concurrencia de voz 0) | WhatsApp y voz (concurrencia 1) | sin tope |
| Contactos / equipo / links | 0 / 0 / 1 | 500 / 2 / sin tope | 5.000 / 2 / sin tope | sin tope |
| Herramientas (código) | 0 | 3 (sí) | 10 (sí) | sin tope (sí) |
| Agente propio | No | No | Sí | Sí |
| Marca blanca | No | No | Sí | Sí |
| Reportes completos, llamadas directas | No | Sí | Sí | Sí |
| API de inferencia (tokens LLM entrada y salida / min TTS / min STT / pedidos por min) | 262.144 / 20 / 20 / 10 | 262.144 / 20 / 50 / 50 | 262.144 / 500 / 500 / 10 | sin tope |

**Red** es un plan a medida de la landing (instancia propia que cotiza un asesor), sin tier: en las tablas de la
landing figura con todo y sin tope. **Al cambiar un tier**, actualizar la tabla de planes de
`/desarrolladores/docs/api` y `/desarrolladores/docs/mcp` (`planFeatures`) y las tarjetas de
`landing/src/data/site.ts`.

## Autenticación y permisos

El dashboard se publica en `https://app.atentina.com.ar` por el túnel, **sin Cloudflare Access**: todo lo de
esta sección es lo que lo protege. Código en `app/api/http.py` y `app/api/deps.py`.

- **Sesión de la UI:** `POST /auth/login` valida contra argon2 (tiempo constante si el email no existe) y setea
  `vaas_session`: JWT HS256 con `AUTH_SECRET`, httpOnly, SameSite=Strict, path `/api`, `Max-Age` de
  `AUTH_TOKEN_HOURS`, `Secure` si `AUTH_COOKIE_SECURE=true` o el pedido llegó por HTTPS.
- **Sesión revocable:** el JWT lleva `sv` = `users.session_version`; logout, cambio de clave o de email y
  desactivación lo incrementan y cierran **todas** las sesiones. Cada pedido relee el usuario de la base.
- **Alta con link por mail** (`POST /clients` con `owner_email`, `POST /users/{id}/invite`, registro): el usuario
  se crea con una clave al azar y recibe `/set-password?token=…`, un JWT con clave derivada de `AUTH_SECRET`, que
  vence a las `PASSWORD_SETUP_HOURS` (72) y lleva la huella de la clave (un solo uso, sin tabla).
  `POST /auth/password-setup/check|password-setup` (30 pedidos por hora por IP) y `/auth/password-reset` son
  públicos, con tope por IP (429). Link vencido o usado: 422 `invalid_setup_token`.
- **Perfil** (`app/services/profile.py`, `/profile`): cambio de clave o email con un código de 6 dígitos al email
  actual (desafío JWT sin tabla, vence a los `ACCOUNT_CODE_MINUTES`, 15); topes en memoria de 5 mails por hora y 5
  intentos. Errores `invalid_code`, `email_taken`, `mail_failed`. Solo con sesión.
- **Panel y teléfono del equipo** (`session_switch.py`): la cookie es de cada host; para pasar de `app.` a
  `telefono.` sin volver a ingresar, el origen da un pase de un solo uso (60 s) en el fragmento `#sesion=` y el
  destino lo canjea (`POST /auth/switch/redeem`).
- **Límites de login fallido** (`services/ratelimit.py`, en memoria): 5 por IP y email y 10 por email en 15 min;
  20 por IP en 15 min y 100 por día (`LOGIN_FAIL_*`). Atómicos y contados antes de verificar; el de email solo
  frena a las IP que ya fallaron. 429 `too_many_attempts`.
- **IP real:** `deps.client_ip` toma `CF-Connecting-IP` solo si el par TCP está en `TRUSTED_PROXY_CIDRS` (localhost
  y el gateway de la red de compose por donde llega cloudflared); igual con `X-Forwarded-Proto`. Un pedido por el
  túnel con `http` recibe 308 a `https://`. Límite conocido: un contenedor de otro proyecto del host que entre por
  el puerto publicado puede llegar como ese gateway y falsificar `CF-Connecting-IP`.
- **CSRF:** SameSite=Strict no alcanza (la landing, `api.`, `wa.` y `rtc.` son same-site con `app.`). Un POST,
  PATCH, PUT o DELETE con cookie y sin `Authorization` tiene que traer `Origin` del mismo host o de
  `APP_ORIGINS`; sin `Origin`, se rechaza `Sec-Fetch-Site` `same-site`/`cross-site`. Si no, 403 `csrf`.
- **API keys** (`Authorization: Bearer vaas_…`): se guarda el SHA-256; `last_used_at` con resolución de un minuto.
  `scopes` (separados por coma, `api_usage.ALL_SCOPES`):

| Scope | Qué puede |
|---|---|
| `calls` | La API `/api/v1` (agentes, llamadas, números, campañas...). |
| `mcp` | El MCP con escritura (y la API por dentro). |
| `mcp_read` | El MCP solo lectura: por fuera del MCP, solo GET. |
| `llm`, `stt`, `tts` | Solo `/api/v1/inference` (la de inferencia no acepta cookie). Sin `calls`/`mcp`/`mcp_read`, la API da 403 `scope_missing`. |

- **OAuth 2.1 y MCP:** `POST /mcp` acepta API keys `mcp`/`mcp_read` o un token OAuth (login del panel, PKCE,
  consentimiento en `/oauth/consent`); un token OAuth solo vale para el MCP. Detalle en
  [`features/MCP.md`](features/MCP.md).
- **Otros topes por hora:** prueba de voz (`RATE_TTS_PREVIEW_PER_HOUR`), conversaciones de texto y turnos
  (`RATE_CONVERSATIONS_PER_HOUR`, `RATE_TURNS_PER_HOUR`), altas y plantillas de WhatsApp (`WA_SIGNUP_PER_HOUR`,
  `WA_TEMPLATES_PER_HOUR`). Cuerpo de `/api` hasta `API_MAX_BODY_BYTES` (1 MiB, 413), salvo subidas de imagen y
  STT.
- **Loadtest:** `POST /calls {"loadtest": true}` solo para admin o `LOADTEST_CLIENT` (`atentina`); si no, 403
  `loadtest_forbidden`.
- **Permisos:** un recurso de otro cliente responde 404, no 403.

| Acción | Admin (`/admin`) | Usuario del cliente | API key `calls` |
|---|---|---|---|
| Tiers, clientes, ajustes de límites, usuarios, cobros, marca blanca, Sistema | Sí | No | No |
| Números: cargar, asignar, liberar, borrar | Sí | No | No |
| Conversaciones: borrar (una o en bulk) | Sí | No | No |
| Agentes, herramientas, secretos, conexiones de LLM, WhatsApp, contactos, campañas, equipo, links, números (agente, etiqueta, quién atiende) | Entrando como el cliente | Lo suyo | Lo suyo |
| Llamadas, conversaciones, reportes, consumo, voces | Todo (vistas de todos en `/admin`) | Lo suyo | Lo suyo |
| Reportes `technical` y `platform` | Sí | No | No |
| Llamadas directas: llamar | No | Sí, con el plan | Con `user_id` (y `join_url`) |
| Llamadas directas: atender, rechazar, presencia | No | Sí | No (403 `panel_user_required`) |
| API keys | Sí | Las suyas | No |

- **Headers:** HSTS (`max-age=31536000; includeSubDomains`) solo por HTTPS; CSP con el hash de cada `<script>`
  inline de `web/dist/index.html` y el SDK de Facebook (`connect.facebook.net`, `*.facebook.com`),
  `frame-ancestors 'none'` (`CSP_REPORT_ONLY=true` la manda como Report-Only);
  `Cross-Origin-Opener-Policy: same-origin-allow-popups` (con `same-origin` se rompe el popup de Meta),
  `Referrer-Policy`, `Permissions-Policy`, `X-Content-Type-Options`, `X-Frame-Options: DENY`; sin header `server`.
- **Errores sin detalle interno:** los 500 y 502 no traen el error de abajo (queda en el log) y los 422 de
  validación salen sin `input`.
- **Públicos:** `/api/v1/demo/*` (Turnstile, CORS de `DEMO_ALLOWED_ORIGINS`), `/api/v1/public/*` (link para
  llamar y marca del login), los webhooks y el OAuth.

## Soporte del admin

El admin administra en `/admin/*` y, para operar lo de un cliente (también los agentes propios, del cliente
`atentina`), **entra como el cliente** sin otro login.

- **Backend:** con la sesión de un `admin` y el header `X-Atentina-Client: <client_id>`, `get_principal` devuelve
  `Principal(role=client, client_id=<ese>, support=True)` (`id` sigue siendo el del admin). Una API key o un token
  OAuth no lo pueden usar (el MCP tiene su `x-atentina-mcp-client`). Cliente inexistente: 404 `client_not_found`.
  `GET /auth/me` responde el cliente con `support: true`, sin `legal_pending` ni bienvenida.
- **Solo lectura en soporte** (`require_not_support`, 403 `support_read_only`): `/auth/me/*` (perfil, clave,
  email, condiciones, bienvenida), plan y cobros del cliente (pagar, cambiar, dar de baja, datos fiscales), y
  llamar, atender o cambiar presencia en las llamadas directas. El resto (agentes, WhatsApp, campañas, resúmenes
  por email) se hace como el cliente, sin auditoría aparte.
- **Frontend:** `src/api/client.ts` agrega el header si la pestaña está en un cliente (`src/features/support/`:
  `useSupportSwitch()` con `enter`/`exit`, `useAreaPath()`, `supportUrl()`); el cliente activo vive en
  `sessionStorage` (por pestaña) y al entrar o salir se vacía la caché de TanStack Query. Rutas `/admin/*` con
  `RequireAdminArea` y `ADMIN_NAV`; en soporte `me.role === 'client'` y `useIsAdmin()` es falso: lo de un admin en
  soporte va con `me.support` (`useSupportReadOnly()`). "Volver a administración" es la única salida.
- **`tiers.internal`** marca el tier de Atentina (no se ofrece, no cuenta en las estadísticas de la plataforma).
- WhatsApp con la app de Meta propia del cliente: [`features/WHATSAPP.md`](features/WHATSAPP.md).

## Marca blanca

El panel del cliente con su logo y tres colores. Plan: `tiers.white_label` (`TIER_HAS["white_label"]`); lo
configura el admin en la ficha del cliente, pestaña "Marca blanca" (`app/services/branding.py`,
`app/api/routers/branding.py`, `web/src/branding/`; migración 0034). Themes de clientes en
`comercial/marca-blanca/<slug>/`.

| Ruta | Quién | Qué |
|---|---|---|
| `GET /clients/{id}/branding` | admin | Lo guardado, `available` (si el tier la incluye) y `logo_url`. |
| `PUT /clients/{id}/branding` | admin | `enabled`, `color_primary`, `color_header`, `color_accent`, `powered_by`. |
| `PUT /clients/{id}/branding/logo` | admin | Multipart: PNG, JPG o WebP (hasta 2 MB, se achica a 480 × 120, mínimo 24 px de alto) o SVG (200 KB, sin scripts, eventos ni referencias externas). Errores `logo_format`, `logo_too_large`, `logo_invalid`, `logo_unsafe`. |
| `DELETE /clients/{id}/branding/logo` | admin | Saca el logo (se muestra el nombre del cliente en texto). |
| `GET /auth/me` | todos | `branding` resuelto (fila `enabled` + tier con `white_label` + rol `client`) o `null`. |
| `GET /public/branding/{slug}` | público | `BrandingPublic` (`slug`, `name`, `logo_url`, `logo_ratio`, colores, `powered_by`) para el login; 404 si no está activa, el plan no la incluye o el cliente está inactivo. |
| `GET /public/branding/{slug}/logo?v=` | público | El archivo, cacheado un año (nombre por hash del contenido); el SVG con CSP `default-src 'none'` y `nosniff`. |

- **Contraste** (WCAG 2.1, `branding.contrast` y `web/src/branding/color.ts`, con tests de los dos lados): el
  primario tiene que dar 4,5:1 con blanco; si no, 422 `color_contrast` con el sugerido en `errors[0].suggested` (el
  mismo matiz oscurecido de a 5 %). Ej.: `#fd6421` da 2,99:1 y se rechaza; `#0068fd`, 4,77:1. El encabezado es
  libre (el texto es blanco o tinta según contraste); el acento, libre y solo decorativo.
- **Login:** `/login?c=<slug>` muestra la marca; los mails de alta y de clave arman ese link si el cliente la tiene.
- Logos en `storage/branding/<client_id>/` (en el backup). Los mails siguen con la plantilla de Atentina.
- Cómo se aplica en la UI: [`DESIGN_GUIDELINE_APP.md`](DESIGN_GUIDELINE_APP.md), "Marca blanca".

## API

- Versionada en `/api/v1`; OpenAPI en `/api/v1/openapi.json` y documentación en `/api/v1/docs`, solo para un admin
  con sesión (`API_DOCS=admin`; `public` u `off`). `make openapi` usa `app.openapi()`.
- **Errores:** `{"detail": "texto", "code": "snake_case", "errors": [{"path", "message"}]}`: 404 `not_found`, 403
  `forbidden`/`support_read_only`/`scope_missing`, 409 `conflict`/`agent_in_use`/..., 422
  `invalid`/`invalid_definition`, 429 límites del plan, 502 `upstream_error` (LiveKit, TTS o LLM caídos), 500
  `internal_error`. Los 422 de pydantic mantienen el formato de FastAPI.
- **Listas:** `GET /calls` pagina con `limit`/`offset` y devuelve `{items, total}`; el resto, listas simples. Las
  fechas de `/calls` y `/reports` toman días locales de `tz` (default `BILLING_TIMEZONE`). Los admins pasan
  `client_id` en las rutas de recursos de un cliente.

| Router (`app/api/routers/`) | Rutas | Detalle |
|---|---|---|
| `auth.py` | `/auth`: login, logout, `me` (perfil, bienvenida, condiciones, clave, email), alta y reset de clave, pase de sesión (`/switch*`, `/handoff`) | "Autenticación" |
| `tiers.py`, `clients.py`, `users.py`, `api_keys.py` | `/tiers`, `/clients` (más `call-emails`, `usage`, `inference-usage`, `limits`, `limit-adjustments`), `/users` (`invite`), `/clients/{id}/api-keys` | [`GUIA_UI.md`](GUIA_UI.md) |
| `plan.py` | `GET /plan/features` | "Funciones por plan" |
| `billing.py` | `/clients/{id}/billing/*` (subscribe, cancel, fiscal, payments, suspend), `/billing/subscriptions`, `/billing/payments` | [`COBROS.md`](features/COBROS.md) |
| `branding.py` | `/clients/{id}/branding*`, `/public/branding/{slug}*` | "Marca blanca" |
| `agents.py` | `/agents` (CRUD, `schema`, `validate`, `prompt`, `definition`, `versions`), `/agent-templates` | "Definición de un agente" |
| `conversations.py` | `/conversations` (texto, turnos) | "Motor conversacional" |
| `calls.py` | `/calls` (crear, lista, detalle, `join`, `hangup`, `recordings/{n}`, borrar y `bulk-delete` solo admin) | "Flujos" |
| `voices.py`, `llm_params.py` | `/voices`, `/tts/preview`, `/llm/params` | |
| `phone_numbers.py`, `blocked_numbers.py` | `/phone-numbers` (carga, `bulk`, `assign`, `release`, quién atiende), `/blocked-numbers` | [`EQUIPO_TELEFONIA.md`](features/EQUIPO_TELEFONIA.md) |
| `handoff.py` | `/team`, `/handoff-areas` (y `defaults`), `/hold-music`, `/events` | ídem |
| `direct_calls.py` | `/direct-calls` (`join`, `answer`, `decline`), `/me/presence`, `/me/ringing`, `/team/presence`, `/clients/{id}/direct-call-settings` | ídem |
| `call_links.py` | `/agents/{id}/call-link*`, `/public/call-links/{token}*` | [`LINK_LLAMADA.md`](features/LINK_LLAMADA.md) |
| `contacts.py`, `campaigns.py`, `wa_campaigns.py` | `/contacts` (y `optouts`, `import`, `archive`), `/campaigns` (y `plan`, `contacts`, `stats`, `report.csv`, `start|resume|pause|cancel`); `/whatsapp/campaigns` y `/whatsapp/optouts` son alias de lo mismo | [`CAMPANAS.md`](features/CAMPANAS.md) |
| `whatsapp.py` | `/whatsapp`: `config`, `accounts` (alta, `own-app`, `routes`, `register`, `refresh`, `deactivate`, `templates`), `signup`, `threads/{id}/close` | [`WHATSAPP.md`](features/WHATSAPP.md) |
| `tools.py` | `/tools/schema`, `/tools/code-template`, `/clients/{id}/tools*` (prueba, versiones), `/clients/{id}/secrets`, `/clients/{id}/credentials`, `/agents/{id}/secrets` | [`HERRAMIENTAS.md`](features/HERRAMIENTAS.md) |
| `llm_connections.py` | `/clients/{id}/llm-connections` (prueba, modelos) | [`LLM_CONEXIONES.md`](features/LLM_CONEXIONES.md) |
| `reports.py` | `/reports/summary|calls|outcomes|messages|transfers|campaigns|technical|platform` | [`REPORTES.md`](features/REPORTES.md) |
| `inference.py`, `api_requests.py` | `/inference/chat/completions`, `/audio/transcriptions`, `/audio/speech`, `/models`, `/voices`, `/usage`; `/api-requests` | [`API_INFERENCIA.md`](API_INFERENCIA.md) |
| `mcp_usage.py` (y `app/api/oauth.py`) | `/mcp/usage`; `/oauth/authorize`, `/oauth/grants` | [`MCP.md`](features/MCP.md) |
| `consumer_requests.py` | `/consumer-requests` (arrepentimiento y baja) | [`LEGAL.md`](features/LEGAL.md) |
| `demo.py` | `/demo`: `sessions`, `calls`, `tts`, `contact`, `signup`, `plans`, `legal`, `consumer-requests` | [`LANDING.md`](features/LANDING.md) |
| `system.py` | `/system/now|history|events|peaks` (admin) | [`OBSERVABILIDAD.md`](OBSERVABILIDAD.md) |

Fuera de `/api/v1`: `/wa/webhook` y `/wa/webhook/{key}`, `/mp/billing/webhook`, `POST /mcp`, `/oauth/*` y
`/.well-known/oauth-*`, `/llamar/{token}` (host `llamar.`), `/movil` (teléfono del equipo), `/internal/metrics` y
`/health`.

**Mails** (Resend, `app/mail/`): bienvenida con link de alta, número asignado (a cada usuario activo del cliente),
clave olvidada y resumen de llamada. Un fallo de Resend no corta la operación; sin `RESEND_API_KEY` no se envía
nada (`disabled`). Variables `MAIL_FROM`, `APP_URL`, `SITE_URL`, `SUPPORT_EMAIL`.

## Frontend (`web/`)

- **Stack:** React 19 + TypeScript strict + Vite, React Router 7 (carga diferida por página), TanStack Query 5,
  Mantine 8 (tema Atentina, solo claro), CodeMirror (JSON y código) y Recharts. Diseño:
  [`DESIGN_GUIDELINE_APP.md`](DESIGN_GUIDELINE_APP.md); cómo correrlo: [`web/README.md`](../web/README.md).
- **Entradas** (`web/vite.config.ts`):

| HTML | Código | Qué es | Quién lo sirve |
|---|---|---|---|
| `index.html` | `src/main.tsx`, `src/router.tsx` | El panel: `/admin/*` y el del cliente en `/` | `app`, cualquier ruta que no sea de la API |
| `llamar.html` | `src/llamar/` (sin React) | Página del link para llamar | `app/api/call_link_host.py` (`/llamar/{token}`, host `llamar.`) |
| `telefono.html` | `src/telefono/` | Teléfono del equipo tipo app de Android | `app/api/phone_app_host.py` (`/movil`, host `telefono.`) |
| `crm.html` | `src/crm/` | UI del CRM | servicio `crm` |

- **Organización:** `src/features/<recurso>/` (páginas, componentes y un `api.ts` de hooks de query y mutación),
  `src/components/` (layout, `nav.ts` con `CLIENT_NAV` y `ADMIN_NAV`, `PlanGate`, badges, estados), `src/lib/`
  (formatos es-AR, etiquetas), `src/branding/` (marca blanca), `src/api/` (cliente). Filtros, pestañas y mes de
  consumo viven en la URL.
- **Cliente de la API:** `openapi-fetch` tipado con `src/api/schema.d.ts`, generado del OpenAPI (`make openapi`).
  Un cambio en `app/api/schemas.py` se refleja regenerando los tipos y `npm run typecheck` marca lo que rompe.
- **Auth:** `GET /auth/me` al cargar; un 401 limpia la sesión y lleva a `/login`. Guardas por área
  (`RequireAdminArea`, `RequireClientArea`).
- **Build:** `web/dist`. FastAPI sirve `/assets/*` y cualquier otra ruta devuelve `index.html` (sin cache; los
  assets llevan hash).

## Tests y calidad

| Qué | Comando | Cubre |
|---|---|---|
| Backend | `make test` | API, permisos, límites, motor, campañas, WhatsApp (payloads de Meta y Graph simulado), seguridad del dashboard público, MCP. Solo LLM falso con respuestas grabadas: ningún test depende de un servicio real ni valida lo que contesta un modelo. |
| Herramientas | `make e2e-tools`, `make test-tools-code` | API y MCP de punta a punta con LLM falso, API falsa y sandbox de prueba (bloquea). |
| SIP | `make e2e-sip` | Señalización y transferencia en un entorno SIP aislado. |
| Frontend | `make web-check` | ESLint, tipos y Vitest. |
| Migraciones | `make migrate-test`; `alembic upgrade/downgrade/check` | Copia del backup en PostgreSQL; ida y vuelta en PostgreSQL y SQLite. |
| Modelos | `make eval-*` | Ver "Motor conversacional": informan, no bloquean. |

## Configuración

Todo por `.env`, leído con `app/config.py` (ver `.env.example`):

- **Obligatorias:** `AUTH_SECRET` (sin ella `app` no arranca), las de LiveKit y las de inferencia
  (`VLLM_API_KEY`, URLs y modelos).
- **Primer admin:** `ADMIN_EMAIL`, `ADMIN_PASSWORD` (los usa el seed).
- **Límites:** `BILLING_TIMEZONE`, `QUOTA_CHECK_SECONDS`, `QUOTA_REJECT_MESSAGE`, `QUOTA_END_MESSAGE`,
  `CALL_MAX_DURATION_SECONDS`, `ANURA_CHANNELS`.
- **Voz:** `VOICE_MIN_ENDPOINTING_DELAY`, `VOICE_MAX_ENDPOINTING_DELAY`, `VLLM_TTS_VOICE`, `LLM_*` (muestreo por
  defecto del modelo vigente, en su override de compose).
- **Scripts de carga:** `VAAS_API_KEY` (API key del cliente `atentina`).
- **WhatsApp:** `WA_APP_SECRET`, `WA_VERIFY_TOKEN`, `WA_ACCESS_TOKEN`, `WA_TOKEN_KEY`, `WA_SESSION_HOURS`,
  `WA_DEBOUNCE_SECONDS`, `WA_EMBEDDED_SIGNUP` (apagado), `WA_AUDIO_*` ([`features/WHATSAPP.md`](features/WHATSAPP.md)).
- **Campañas:** `CALL_CAMPAIGN_MAX_CONCURRENT` (8), `CALL_CAMPAIGN_TICK_SECONDS`, `CALL_CAMPAIGN_FAILURE_STREAK`
  (10), `CALL_RINGING_TIMEOUT_SECONDS` (30), `CAMPAIGN_HOLIDAYS`, `CAMPAIGN_CALLBACK_*`
  ([`features/CAMPANAS.md`](features/CAMPANAS.md)).
- **Mails:** `RESEND_API_KEY`, `MAIL_FROM`, `APP_URL`, `SITE_URL`, `SUPPORT_EMAIL`, `CALL_SUMMARY_*`.
- **Demo:** `DEMO_*`, `TURNSTILE_SECRET_KEY` ([`features/LANDING.md`](features/LANDING.md)).
- **Teléfono del equipo:** `PHONE_APP_BASE_URL`.
- **Seguridad del dashboard público:** `AUTH_COOKIE_SECURE`, `TRUSTED_PROXY_CIDRS`, `APP_ORIGINS`, `API_DOCS`,
  `CSP_REPORT_ONLY`, `LOGIN_FAIL_*`, `API_MAX_BODY_BYTES`, `RATE_*`, `LOADTEST_CLIENT`. No relajarlas sin medir.
