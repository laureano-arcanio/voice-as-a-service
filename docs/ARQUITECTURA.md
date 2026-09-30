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
| `app` | `app/main.py`, `app/api/` | API REST `/api/v1` y la SPA. Crea conversaciones y llamadas, admite por tier y despacha el worker a una room de LiveKit. |
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
    deps.py          sesión de base, Principal (usuario o API key), require_admin, scoped_client_id
    schemas.py       contratos pydantic (fuente del OpenAPI y de los tipos de la UI)
    errors.py        ServiceError -> JSON {detail, code, errors}; 500 JSON sin detalles internos
    routers/         auth, tiers, clients, phone_numbers, agents, users, api_keys, calls,
                     conversations, voices
  services/          negocio sin HTTP (lo usan la API y el worker)
    quota.py         límites del tier: admisión con lock, consumo del mes, saldo en curso
    calls.py         iniciar salientes/pruebas (prepare_call + dispatch) y entrantes (start_inbound)
    phone_numbers.py inventario: carga, asignación con tope, liberación, ruteo a agente
    agents.py        alta, validación de la definición, versionado, archivo
    reports.py       lista de llamadas, detalle, indicadores y serie diaria (filtros y zona horaria)
    security.py      argon2, JWT HS256, API keys (SHA-256)
    livekit.py       despacho a LiveKit y link de la llamada de prueba
    tts.py, voices.py prueba de voz y catálogo (tts/finetune/voces.tsv)
    errors.py        NotFound, Forbidden, Conflict, Invalid, QuotaExceeded, Upstream
  agents/
    templates/*.json plantillas de agentes (seed, eval, tests)
    definitions.py   DbDefinitions: versiones de la base, cacheadas (son inmutables)
    templates.py     TemplateDefinitions: plantillas del repo
  conversation/      motor: engine, models (Workflow = definición), workflow (validación), store
  llm/               cliente y prompts del LLM
  voice/             worker de LiveKit y latencia por turno
migrations/          Alembic: 0001 esquema anterior (idempotente), 0002 tenencia, 0003 inventario de números
web/                 SPA React (ver "Frontend")
tests/               pytest: API, límites, motor
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
                └───* conversations 1───1 call_logs
                         └── agent_id + agent_version (la versión con que corrió)
```

| Tabla | Claves y reglas |
|---|---|
| `tiers` | `max_concurrent_calls`, `inbound_minutes`, `outbound_minutes`, `max_phone_numbers`; NULL = ilimitado. |
| `clients` | `slug` único, `tier_id` (RESTRICT: un tier en uso no se borra), `active`. |
| `agents` | `(client_id, slug)` único; `version` y `definition` vigentes (copia de la última versión); `archived_at`. |
| `agent_versions` | `(agent_id, version)`; inmutables, con `created_by`. |
| `phone_numbers` | `e164` único; `client_id` NULL = libre; `agent_id` solo si hay cliente (CHECK); `provider`, `assigned_at`. |
| `users` | `email` único; `role` admin o client (CHECK: client ⇔ `client_id`); hash argon2. |
| `api_keys` | SHA-256 de la clave (`key_hash` único), `prefix` visible, `revoked_at`. |
| `conversations` | Estado del motor (datos, mensajes, progreso), `client_id`, `agent_id` + `agent_version` (RESTRICT: un cliente o agente con historial no se borra). `legacy_workflow_id` para las anteriores a los agentes. |
| `call_logs` | Una por conversación: modo, estado, teléfono del otro lado, `phone_number_id` del cliente, inicio, fin, duración, latencia. Base del consumo. |

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
  "id": "ventas", "version": 3, "engine": "classic",
  "agent": {"name": "Sofía", "role": "asesora comercial", "language": "es-AR", "voice": "sofia"},
  "objective": {"description": "…"},
  "conversation": {"opening": "Hola, te habla Sofía…", "rules": ["…"]},
  "knowledge": "…",
  "fields": {
    "contact_name": {"priority": 10, "description": "Nombre", "type": "string", "required": true,
                     "question": "¿Con quién hablo?"}
  },
  "completion": {"outcomes": [
    {"id": "demo", "label": "Pide demo", "when": {"wants_demo": true}, "message": "…", "goal": true},
    {"id": "otro", "label": "Sin demo", "message": "…"}
  ]}
}
```

- `id` y `version` los fija la app: el slug del agente y el número de versión. Van al prompt.
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
- **Plantillas:** `app/agents/templates/<id>.json` se usan para crear agentes, en el seed (el
  cliente `interno` recibe una copia de cada una) y en el eval y los tests, sin base.

## Flujos

### Llamada saliente o de prueba (`POST /api/v1/calls`)

1. El router resuelve el `Principal`. `services/calls.prepare_call` corre en un thread, porque la
   base es bloqueante. Valida el agente (visible y no archivado), el teléfono E.164 y la voz, y elige
   el caller ID (el número pedido o el primero del cliente).
2. `engine.new_conversation(session=s)` arma el estado con la versión vigente, sin guardarlo.
3. `quota.admit(s, client, mode)` toma el lock del cliente (`SELECT … FOR NO KEY UPDATE OF clients`).
   Verifica que el cliente esté activo, que haya lugar en el tope de simultáneas y que queden minutos
   de esa modalidad. Devuelve los segundos que quedan.
4. En la misma transacción se guardan la conversación y la `call_logs` (`pendiente`), y el commit
   suelta el lock. Todo va por una sola conexión: pedir otra con el lock tomado agotaba el pool bajo
   carga.
5. `livekit.dispatch_call` crea el dispatch con la metadata `{conversation_id, phone, voice,
   loadtest, max_duration_seconds, from_number}`. Si falla, la llamada queda `fallida`
   (`dispatch_failed`) y la API responde 502.
6. El worker marca por SIP (`create_sip_participant` con `max_call_duration` y `sip_number`) o, en
   prueba, espera al participante del navegador.
7. Estados de la llamada: `sonando` → `en_curso` → `finalizada` (con duración y latencia) o `fallida`.

### Llamada entrante

1. Anura → Asterisk → trunk entrante de LiveKit → la dispatch rule crea una room `anura-*` y
   despacha el worker sin metadata.
2. El worker espera al participante SIP y lee el número marcado (`sip.trunkPhoneNumber`).
   `calls.start_inbound` lo busca en `phone_numbers`:
   - **libre o sin agente:** se corta (`number_without_agent`);
   - **sin lugar o sin minutos:** queda `rechazada` y el que llama escucha `QUOTA_REJECT_MESSAGE`;
   - **si no:** conversación con el agente del número y llamada `entrante`.
3. Hoy Anura entrega todos los números de una cuenta con el mismo destino, y Asterisk los manda como
   `+54<ANURA_DID>` (ver [`TELEFONIA_ANURA.md`](TELEFONIA_ANURA.md)).

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

Carreras medidas en PostgreSQL:
- 20 llamadas simultáneas con tope 3: entran exactamente 3.
- 5 asignaciones simultáneas de números con tope 2: entran exactamente 2.

## Autenticación y permisos

- **UI:** `POST /auth/login` valida contra argon2 (con tiempo constante si el email no existe) y
  setea la cookie `vaas_session`: un JWT HS256 firmado con `AUTH_SECRET`, httpOnly,
  SameSite=Strict, path `/api` y `Secure` según `AUTH_COOKIE_SECURE`. Hay un límite de 10 intentos
  fallidos por IP y email en 5 min, en memoria del proceso.
- **Sistemas del cliente:** `Authorization: Bearer vaas_…`. Se guarda solo el SHA-256 y
  `last_used_at` se actualiza con resolución de un minuto.
- **Cada pedido relee el usuario de la base:** desactivarlo o cambiarle el rol corta el acceso sin
  esperar a que venza el token.
- **Permisos:**

| Acción | Admin | Usuario cliente | API key |
|---|---|---|---|
| Tiers, clientes (alta, edición, baja), usuarios | Sí | No | No |
| Agentes: crear, editar, versionar, archivar | Sí | Solo ver | Solo ver |
| Números: cargar, asignar, liberar, borrar | Sí | No | No |
| Números: elegir agente y etiqueta | Sí | Los suyos | Los suyos |
| Llamadas, conversaciones, consumo, voces | Todo | Lo suyo | Lo suyo |
| API keys | Sí | Las suyas | No |

- Un recurso de otro cliente responde 404, no 403, para no revelar que existe.
- **Headers:** `X-Content-Type-Options`, `X-Frame-Options: DENY` y `Referrer-Policy`.

## API

- Versionada en `/api/v1`; OpenAPI en `/api/v1/openapi.json` y documentación en `/api/v1/docs`.
- **Errores:** `{"detail": "texto", "code": "snake_case", "errors": [{"path", "message"}]}`.
  - 404 `not_found`, 403 `forbidden`, 409 `conflict`/`agent_in_use`/`phone_numbers_limit`/…,
    422 `invalid`/`invalid_definition`, 429 límites del tier, 502 `upstream_error` (LiveKit, TTS
    o LLM caídos) y 500 `internal_error`, sin detalles (el detalle queda en el log).
  - Los 422 de validación de pydantic mantienen el formato de FastAPI.
- **Listas:** `GET /calls` pagina con `limit`/`offset` y devuelve `{items, total}`; el resto devuelve
  listas simples.
- **Filtros de fecha** (`/calls`, `/stats`, `/stats/daily`): toman días locales de `tz` (zona IANA,
  default `BILLING_TIMEZONE`). `status` se puede repetir.

## Frontend (`web/`)

- **Stack:** React 19 + TypeScript strict + Vite, React Router 7 (rutas con carga diferida por
  página), TanStack Query 5, Mantine 8 (tema Atentina, claro y oscuro), CodeMirror para el JSON y
  Recharts.
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
- **Desarrollo:** `make web-dev` (Vite en :5173 con proxy de `/api` a `VITE_API_PROXY`).
  `scratch/dev_backend.sh` levanta la API sobre SQLite en :8111, sin tocar el stack.

## Tests y calidad

| Qué | Comando | Cubre |
|---|---|---|
| Backend | `make test` (o `.venv/bin/pytest`) | API (auth, permisos, tiers, clientes, agentes y versiones, inventario de números, llamadas y límites, fechas por zona), cuotas, motor con LLM falso y escenarios contra el LLM real (se saltean si no responde). |
| Frontend | `make web-check` | ESLint, tipos y Vitest (formatos, parseo de números, errores de API, guardas por rol, consumo). |
| Migraciones | `alembic upgrade head` / `downgrade` / `check` | Ida y vuelta en PostgreSQL y SQLite. |

## Configuración

Todo por `.env`, leído con `app/config.py` (ver `.env.example`):
- **Obligatorias:** `AUTH_SECRET`, más las de LiveKit e inferencia.
- **Primer admin:** `ADMIN_EMAIL` y `ADMIN_PASSWORD`, que usa el seed.
- **Límites:** `BILLING_TIMEZONE`, `QUOTA_CHECK_SECONDS`, `QUOTA_REJECT_MESSAGE` y
  `QUOTA_END_MESSAGE`.
- **Scripts de carga:** `VAAS_API_KEY` (API key del cliente `interno`).
