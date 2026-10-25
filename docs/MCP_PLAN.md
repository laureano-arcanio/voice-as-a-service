# Plan: servidor MCP de Atentina

Un servidor MCP (Model Context Protocol) que expone la plataforma como herramientas, para que el agente
de IA de un cliente (Claude, ChatGPT, Cursor, Claude Code, un agente propio) cree y edite agentes de voz,
los pruebe, mire llamadas y transcripciones, cargue contactos, lance campañas y arme el equipo de
derivación, todo sin abrir el panel. Cada herramienta respeta el plan del cliente, y una de ellas
(`get_plan_tools`) le dice al agente qué puede usar y qué plan haría falta para el resto. Diseño del
24-oct-2026; fases 0 a 3 (lectura, plan, API key `mcp`, escritura y OAuth) en producción desde el 24-oct-2026;
fase 4 (publicación) preparada: el registro oficial, publicado el 25-oct-2026; falta la landing (sección 12). Catálogo vigente: [`MCP_HERRAMIENTAS.md`](MCP_HERRAMIENTAS.md), generado.

## 1. Decisiones

| Tema | Decisión | Por qué |
|---|---|---|
| Transporte | **Servidor remoto** Streamable HTTP en `https://mcp.atentina.com.ar/mcp`, sin estado y con respuestas JSON | No se instala nada: el cliente pega una URL. Es lo que aceptan los conectores de Claude.ai/Desktop y ChatGPT; Claude Code, Cursor y VS Code también. Un paquete local (npm/PyPI) sería otra cosa a versionar y dejaría la key en texto plano en un archivo de config |
| Dónde corre | Dentro de `app` (FastAPI), en `POST /mcp`, **sin el SDK** (JSON-RPC propio, sin estado, respuestas JSON), como el cliente de `app/apps/client.py` | Comparte base, servicios, límites y auth; no suma un contenedor ni una dependencia con su propia versión de Starlette. El protocolo sin estado y sin SSE son ~150 líneas. Si se suman SSE, `resources` o `prompts` con estado, reconsiderar el SDK |
| Cómo ejecuta | Cada herramienta llama a la **misma API `/api/v1`** en proceso (cliente `httpx` con `ASGITransport`, sin red), con el token de quien pide | El corte de verdad (tier, quota, `limits.check_*`, permisos por cliente) queda en un solo lugar. Un MCP que llame a los servicios por su cuenta terminaría divergiendo de la API. Costo: ~1 ms por llamada interna, a medir |
| Catálogo | **Herramientas curadas** (~75, por dominio), no generadas de las 180 rutas del OpenAPI | Las generadas salen con nombres y esquemas pensados para HTTP (paths, `client_id`), y con 180 los modelos eligen mal. Se reusan los esquemas Pydantic de `app/api/schemas.py` |
| Grupos | `toolsets` por URL (`/mcp?toolsets=agents,calls`); por defecto todas desde el 25-oct-2026 (antes `core`) | El directorio de conectores publica una sola URL, sin `?toolsets=`: con `core` no tendría contactos, campañas ni equipo. Las 87 ocupan ~72k caracteres (~18k tokens) contra ~21k (~5k) de `core`; quien ande justo de contexto pide `?toolsets=core` u otros grupos |
| Auth | **OAuth 2.1** (PKCE, Client ID Metadata Documents y registro dinámico) para conectores, y **API key** con scope nuevo `mcp` para Claude Code, Cursor y scripts | Claude.ai y ChatGPT solo conectan servidores remotos con OAuth (o sin auth). La API key es lo que ya tienen los clientes |
| Plan | Las herramientas del plan **se listan igual**, con el plan que las incluye en la descripción; al usarlas sin el plan devuelven `feature_not_in_plan` con el motivo de `features.plan_features` | El agente puede explicar qué falta y ofrecer "Mejorar mi plan". Ocultarlas no deja descubrirlas, y la lista cambiaría al pagar |
| Admin | Las de admin (tiers, clientes, inventario de números, cobros, apps) **no se listan** a un cliente; a un admin, solo con `toolsets=admin` | Un cliente no las puede usar nunca: no es una cuestión de plan |
| Fuente de verdad | Un catálogo (`app/mcp/catalog.py`): cada herramienta con su toolset, la función del plan (`features.TIER_HAS`), el rol y si escribe | De ahí salen `tools/list`, `get_plan_tools`, la tabla de la sección 6 y la página de la landing; un test verifica que coincidan |
| Pagos | El MCP **no cobra**: `subscribe` devuelve el link a `/plan/pagar` | La tarjeta va por los campos seguros de Mercado Pago, en el navegador |
| Idioma | Nombres de herramientas en inglés (`snake_case`, como la API); descripciones y errores en español | Los nombres siguen las rutas; lo que lee el modelo y el usuario, en el idioma del cliente |

## 2. Qué hay hoy (y se reusa)

- **API `/api/v1`** con OpenAPI (`web/openapi.json`, 180 operaciones): casi todo lo del panel ya es API.
- **Principal** (`app/api/deps.py`): sesión de usuario o API key; `scoped_client_id` limita al cliente propio;
  `UserPrincipal` exige sesión (API keys, cobros, conexiones de LLM, parámetros); `AdminPrincipal`, admin.
- **API keys** con scopes (`calls`, `llm`, `stt`, `tts`) y `last_used_at`; registro de pedidos (`api_requests`).
- **Plan:** `features.plan_features` (lo que incluye, con el motivo en lenguaje del cliente y los planes que
  lo tienen) y `GET /plan/features`; límites efectivos (tier + ajustes) en `limits.effective_limits`.
- **Errores con código** (`app/services/errors.py`): `campaign_channel_not_in_plan`, `scope_missing`, cuotas.
- **MCP ya lo hablamos** como cliente con las apps (`app/apps/client.py`, protocolo 2025-06-18): el
  servidor sería el primero.
- **Túnel** de Cloudflare con rutas por host, y el login del panel (`app.atentina.com.ar`) para el OAuth.

## 3. Arquitectura

```
Agente del cliente ──HTTPS──▶ Cloudflare ──túnel──▶ app :8011
 (Claude, ChatGPT,            mcp.atentina.com.ar      ├─ /mcp              servidor MCP (FastMCP, sin estado)
  Cursor, Claude Code)                                 │     └─ herramienta ─▶ /api/v1/... en proceso (ASGITransport)
                                                       ├─ /.well-known/oauth-protected-resource
                              app.atentina.com.ar ────▶├─ /oauth/{authorize,token,register,revoke}
                                                       └─ /.well-known/oauth-authorization-server
```

- `app/mcp/server.py`: arma el FastMCP desde el catálogo, lo monta en `/mcp` y valida el token
  (`TokenVerifier` del SDK) contra `api_keys` u `oauth_tokens`.
- `app/mcp/catalog.py`: la lista de herramientas (sección 5) con sus metadatos.
- `app/mcp/tools/<dominio>.py`: una función por herramienta; arma el pedido a `/api/v1` y devuelve
  `structuredContent` (el JSON de la API) y un texto corto para el modelo.
- `app/api/oauth.py` + pantalla de consentimiento en `web/src/features/oauth/`.
- Sin estado entre pedidos: varias réplicas de `app` no cambian nada (hoy hay una).

**Anotaciones MCP** en cada herramienta: `readOnlyHint` en las de lectura, `destructiveHint` en borrar,
cancelar, cortar y revocar, `idempotentHint` donde aplica. Los clientes piden confirmación al usuario con
las destructivas. Las que mueven plata o llaman a personas (`start_call`, `start_campaign`) llevan además
`destructiveHint` y un resumen de lo que va a pasar en la descripción ("llama a N contactos, gasta minutos
salientes").

**Contenido que no es JSON:** grabaciones y vista previa de voz como contenido `audio` (WAV, con tope de
tamaño; si se pasa, link firmado); el reporte de una campaña como texto CSV; imágenes del link para
llamar, por URL o base64.

## 4. Autenticación

### 4.1 API key (fase 1)

- Scope nuevo `mcp` en `api_keys.scopes` (como `calls`): se elige al crear la key en la UI. Una key `calls`
  no abre el MCP, para que el cliente decida qué puede hacer un agente de IA.
- Principal `api_key` del cliente: no puede usar lo que hoy exige sesión (API keys, cobros, conexiones de
  LLM). Esas herramientas responden "Conectá con OAuth (iniciando sesión) para usar esta herramienta".
- Config: `claude mcp add --transport http atentina https://mcp.atentina.com.ar/mcp --header "Authorization: Bearer vaas_..."`.

### 4.2 OAuth 2.1 (fase 3)

Según la especificación de autorización de MCP:

- `mcp.atentina.com.ar/.well-known/oauth-protected-resource` (RFC 9728) apunta al servidor de autorización
  `app.atentina.com.ar`; un 401 sin token devuelve `WWW-Authenticate` con ese metadata.
- `app.atentina.com.ar/.well-known/oauth-authorization-server` (RFC 8414), `/oauth/authorize` (código +
  PKCE S256), `/oauth/token` (código y refresh), `/oauth/revoke`; clientes por **Client ID Metadata
  Document** (la URL del cliente es su `client_id`) y por registro dinámico (RFC 7591) para los que aún no
  lo soportan. `resource` (RFC 8707) obligatorio: el token solo sirve para `mcp.atentina.com.ar`.
- `/oauth/authorize` usa el login existente (con sus límites por IP) y muestra **consentimiento**: qué app
  pide acceso, a qué cliente y los grupos (lectura / escritura). Un admin elige con qué cliente actúa.
- Migración: `oauth_clients` (metadata, `redirect_uris`) y `oauth_tokens` (SHA-256 del token como las API
  keys, `user_id`, `client_id`, scopes, `expires_at`, `refresh_hash`, `revoked_at`, `last_used_at`).
  Acceso 1 h, refresh 30 días con rotación.
- El token actúa **como el usuario** (Principal `user`, mismo rol), así que cubre también lo que exige
  sesión. Se invalida con `users.session_version` (cambio de clave, baja del usuario).
- UI: en Mi cuenta, "Agentes conectados" (app, último uso, revocar), junto a las API keys.

## 5. Catálogo de herramientas

Toolset `core` = `account` + `agents` + `calls`. Columna Plan: la función de `features` que la habilita
(vacía = todos los planes); el detalle por plan, en la sección 6.

| Toolset | Herramientas | Plan | API |
|---|---|---|---|
| `account` | `whoami`, `get_plan_tools`, `get_plan_features`, `get_usage` (minutos, llamadas y límites del mes), `list_api_requests` | — | `/auth/me`, `/plan/features`, `/clients/{id}/usage`, `/clients/{id}/limits` |
| `account` | `list_users`, `invite_user`, `update_user`, `delete_user`; `get_call_emails`, `update_call_emails` | — | `/users`, `/clients/{id}/call-emails` |
| `account` (OAuth) | `list_api_keys`, `create_api_key`, `revoke_api_key`; `get_billing`, `update_fiscal`, `get_payment_link` | — | `/clients/{id}/api-keys`, `/clients/{id}/billing` |
| `agents` | `list_agents`, `get_agent`, `create_agent` (en blanco o desde plantilla), `update_agent`, `update_agent_definition`, `delete_agent`, `list_agent_versions`, `get_agent_version` | — | `/agents` |
| `agents` | `get_agent_schema`, `validate_agent_definition`, `preview_agent_prompt`, `list_agent_templates`, `list_voices`, `preview_voice` (audio), `list_llm_params` | — | `/agents/schema`, `/agents/validate`, `/agents/prompt`, `/voices`, `/tts/preview`, `/llm/params` |
| `agents` | `test_agent_start`, `test_agent_turn`: conversación de prueba por texto con el agente | — | `/conversations` |
| `agents` (OAuth) | `list_llm_connections`, `create_llm_connection`, `test_llm_connection`, `revoke_llm_connection` | — | `/clients/{id}/llm-connections` |
| `calls` | `list_calls`, `get_call` (transcripción y datos tomados), `get_recording` (audio), `hangup_call`, `delete_calls`, `get_stats`, `get_daily_stats` | — | `/calls`, `/stats` |
| `calls` | `start_call` (saliente a un número) | `outbound_calls` | `POST /calls` |
| `calls` | `list_phone_numbers`, `route_phone_number` (a qué agente va) | — | `/phone-numbers` |
| `calls` | `list_blocked_numbers`, `block_number`, `unblock_number` | — | `/blocked-numbers` |
| `call_links` | `get_call_link`, `create_call_link`, `update_call_link`, `rotate_call_link`, `delete_call_link`, `set_call_link_image` | `call_links` | `/agents/{id}/call-link` |
| `whatsapp` | `list_whatsapp_accounts`, `update_whatsapp_account`, `set_whatsapp_routes`, `list_whatsapp_templates`, `create_whatsapp_template`, `close_whatsapp_thread`, `list_wa_operators`, `create_wa_operator`, `update_wa_operator`, `delete_wa_operator`, `get_whatsapp_signup_link` | `whatsapp` | `/whatsapp/*`, `/wa-operators` |
| `contacts` | `list_contacts`, `get_contact`, `upsert_contacts`, `import_contacts` (CSV en texto), `update_contact`, `archive_contacts`, `unarchive_contact`, `list_optouts`, `add_optout`, `remove_optout` | `contacts` | `/contacts` |
| `campaigns` | `get_campaign_plan`, `list_campaigns`, `get_campaign`, `create_campaign`, `update_campaign`, `delete_campaign`, `add_campaign_contacts`, `list_campaign_contacts`, `start_campaign`, `pause_campaign`, `resume_campaign`, `cancel_campaign`, `get_campaign_stats`, `get_campaign_report` (CSV) | `campaigns_voice` / `campaigns_whatsapp` según el canal | `/campaigns` |
| `team` | `list_team`, `create_team_member`, `update_team_member`, `delete_team_member`, `list_handoff_areas`, `get_handoff_area_defaults`, `create_handoff_area`, `update_handoff_area`, `delete_handoff_area`, `list_hold_music`, `list_events` | `team` | `/team`, `/handoff-areas`, `/hold-music`, `/events` |
| `inference` | `chat`, `transcribe_audio`, `synthesize_speech`, `get_inference_usage` | `inference` (nuevo: tokens o minutos de API ≠ 0) | `/inference/*` |
| `admin` | tiers, clientes, ajustes de límites, inventario y asignación de números, cobros y pagos, apps, operadores | rol admin | `/tiers`, `/clients`, `/phone-numbers`, `/billing`, `/apps` |

**Fuera del MCP** (con link al panel, por diseño): pagar con tarjeta, Embedded Signup de WhatsApp (popup
de Facebook), atender una llamada de prueba con micrófono (`/calls/{id}/join`) y la demo pública.

**Resources:** `atentina://agents/schema` (esquema de la definición), `atentina://docs/{tema}` (guías
cortas: cómo armar un agente, campañas, derivaciones). **Prompts:** "Crear un agente para mi negocio",
"Revisar las llamadas de ayer", "Lanzar una campaña": el flujo de herramientas en orden.

**Paginación y tamaño:** las de listar devuelven a lo sumo 50 y un `cursor`; las transcripciones largas,
recortadas con `truncated: true`. Una respuesta grande gasta el contexto del agente del cliente.

## 6. Herramientas por plan

Sale de `features.TIER_HAS` y de los valores de `tiers` (consultados el 24-oct-2026). Se genera con
`make mcp-docs` y se publica en la landing; esta tabla es la foto de hoy.

| Grupo | Free | Mostrador | Sucursal | Central | Función del plan |
|---|---|---|---|---|---|
| Cuenta, usuarios, plan, uso, resumen por email | ✓ | ✓ | ✓ | ✓ | — |
| Agentes, voces, prueba por texto, LLM propio (BYOK) | ✓ | ✓ | ✓ | ✓ | — |
| Llamadas: ver, transcripciones, grabaciones, cortar, estadísticas, bloquear | ✓ | ✓ | ✓ | ✓ | — |
| Números: ver y rutear | — (0 números) | ✓ (1) | ✓ (3) | ✓ (6) | `max_phone_numbers` |
| `start_call` (saliente) | — | ✓ (300 min) | ✓ (1.200 min) | ✓ (5.000 min) | `outbound_calls` |
| Link para llamar | ✓ (1) | ✓ | ✓ | ✓ | `call_links` |
| WhatsApp | — | ✓ | ✓ | ✓ | `whatsapp` |
| Contactos | — | ✓ (500) | ✓ (5.000) | ✓ (sin tope) | `contacts` |
| Equipo y derivaciones | — | ✓ (1 persona) | ✓ (2) | ✓ (sin tope) | `team` |
| Campañas de WhatsApp | — | — | ✓ | ✓ | `campaigns_whatsapp` |
| Campañas de llamadas | — | — | ✓ (de a 1) | ✓ (hasta 3) | `campaigns_voice` |
| API de inferencia | ✓ (262k tokens) | ✓ | ✓ | ✓ (2M) | `inference` |
| Admin | — | — | — | — | rol admin (Interno) |

- Los números entre paréntesis son topes del tier: la herramienta está, pero corta al llegar
  (`quota_exceeded` y su motivo), como la API.
- Los ajustes por cliente (`limit-adjustments`) pueden habilitar algo que su tier no trae: por eso
  `get_plan_tools` mira los límites **efectivos**, no el nombre del plan.
- Al cambiar un tier: `make mcp-docs` y publicar la landing (igual que `/desarrolladores/docs`, sección 6
  de [`FUNCIONES_POR_PLAN_PLAN.md`](FUNCIONES_POR_PLAN_PLAN.md)).

### 6.1 `get_plan_tools`

Sin parámetros (un admin puede pasar `client_id`). Lee `features.plan_features` y el catálogo. Devuelve:

```json
{
  "plan": "Mostrador",
  "free": false,
  "tools": {
    "available": ["list_agents", "create_agent", "start_call", "list_contacts", "..."],
    "unavailable": [
      {"name": "create_campaign", "feature": "campaigns_voice",
       "reason": "Disponible en los planes Sucursal y Central."}
    ],
    "needs_oauth": ["create_api_key", "get_billing"]
  },
  "limits": {"outbound_minutes": {"limit": 300, "used": 42}, "max_contacts": {"limit": 500, "used": 120}},
  "upgrade_url": "https://app.atentina.com.ar/plan"
}
```

- La descripción le pide al modelo llamarla **al empezar** y antes de proponer algo que el plan no tenga.
- `needs_oauth`: solo con API key; con OAuth va vacío.
- Mismo texto de `reason` que la UI (aviso amarillo): una sola redacción.

### 6.2 Error al usar una herramienta sin el plan

Resultado con `isError: true` (no un error de protocolo, para que el modelo lo lea y se lo explique al
usuario) y `structuredContent`:

```json
{"code": "feature_not_in_plan", "feature": "contacts",
 "message": "Tu plan Free no incluye contactos.", "reason": "Disponible en los planes Mostrador, Sucursal y Central.",
 "upgrade_url": "https://app.atentina.com.ar/plan"}
```

El chequeo previo es en el MCP (del catálogo, para dar el motivo claro); el corte real sigue en la API,
y sus 429/403 se traducen al mismo formato.

## 7. Publicación e instalación

La forma más sencilla para el cliente es **una URL y un login**: sin instalar nada, sin copiar keys.

| Dónde | Cómo lo instala el cliente |
|---|---|
| Claude.ai / Claude Desktop | Configuración → Conectores → Agregar conector personalizado → `https://mcp.atentina.com.ar/mcp` → inicia sesión. Después, en el **Directorio de conectores** de Anthropic (envío con su formulario; exige OAuth, políticas y descripciones de herramientas) aparece con un clic |
| ChatGPT | Conectores / apps en modo desarrollador con la misma URL (OAuth) |
| Claude Code | `claude mcp add --transport http atentina https://mcp.atentina.com.ar/mcp` (abre el login) o con `--header` y una API key |
| Cursor, VS Code | Botón "Agregar a Cursor" / "Agregar a VS Code" (deeplinks de instalación) en la landing |
| Clientes solo stdio | `npx -y mcp-remote https://mcp.atentina.com.ar/mcp` (puente estándar, sin paquete nuestro) |
| Agentes propios (SDK de Anthropic/OpenAI) | Conector MCP de la API (`mcp_servers` con URL y token) o cualquier cliente MCP |

Pasos de publicación:

1. **Ruta del túnel** `mcp.` → `localhost:8011` (la crea el usuario), como `api.` y `app.`.
2. **Página** `landing/src/pages/desarrolladores/mcp.astro`: qué es, botones por cliente, la tabla de la
   sección 6 (generada) y el catálogo con descripciones. Sigue [`DESIGN_GUIDELINE.md`](DESIGN_GUIDELINE.md).
3. **Registro oficial de MCP** (`registry.modelcontextprotocol.io`): `server.json` con `remotes`
   (`streamable-http`, la URL) y el namespace `com.atentina/atentina`, verificado por DNS. Los directorios
   (PulseMCP, Glama, Smithery y otros) se alimentan de ahí.
4. **Directorio de conectores de Anthropic** y, si hay demanda, el de ChatGPT: después de la fase 3.
5. Panel: en Mi cuenta → "Conectar con un agente de IA", con la URL, los botones y la creación de la key
   `mcp`.

## 8. Seguridad y abuso

- **Aislamiento por cliente:** el token define el cliente; ninguna herramienta de cliente acepta
  `client_id` (lo pone el MCP). Un test recorre el catálogo con un token de otro cliente.
- **Validación de `Origin`** en `/mcp` (la especificación lo pide contra DNS rebinding) y solo `Bearer`,
  sin cookies: la CSRF por `Origin` del panel no aplica y no se relaja.
- **Límite de pedidos** por token con el `rate_limit` existente (p. ej. 120/min), aparte de `api_rate_limit`
  de inferencia. Cada herramienta queda en `api_requests` con `source=mcp` y el nombre.
- **Inyección de prompts:** transcripciones, nombres de contactos y mensajes de WhatsApp los escribe gente
  de afuera y van al LLM del cliente. Se devuelven como datos (`structuredContent`, campos marcados
  `untrusted` en la descripción), nunca como instrucciones; las acciones que llaman o mandan mensajes
  quedan con `destructiveHint` para que el cliente confirme.
- **Datos personales:** con el MCP las transcripciones y grabaciones salen hacia el proveedor de LLM del
  cliente, por decisión del cliente. Términos y privacidad de la landing lo tienen que decir antes de
  publicar (como con BYOK).
- **Topes duros sin cambios:** `CALL_CAMPAIGN_MAX_CONCURRENT`, la quota y los límites del tier aplican
  igual; un agente en bucle no salta nada que la API no deje.
- **Revocación:** API key desde la UI; tokens OAuth desde "Agentes conectados" o cambiando la clave.

## 9. Pruebas

- `tests/test_mcp_catalog.py`: cada herramienta apunta a una ruta del OpenAPI que existe; cada función de
  plan existe en `features.TIER_HAS`; la tabla de la doc y la de la landing coinciden con el catálogo.
- `tests/test_mcp_plan.py`: con un cliente de cada tier, `get_plan_tools` y el error `feature_not_in_plan`
  dan lo mismo que `GET /plan/features`.
- `tests/test_mcp_auth.py`: sin token 401 con `WWW-Authenticate`; key `calls` rechazada; aislamiento entre
  clientes; flujo OAuth con PKCE y `resource`.
- De punta a punta, con el cliente `atentina`: Claude Code con la key, y Claude.ai con OAuth — crear un
  agente desde cero, probarlo por texto, leer una llamada real. Nunca `start_call` ni campañas a números
  ajenos: con números propios.
- `make mcp-inspect`: abre el MCP Inspector contra el server de desarrollo (`:8111`).

## 10. Fases

| Fase | Qué | Criterio de cierre |
|---|---|---|
| 0. Spike | FastMCP montado en `/mcp`, 3 herramientas de lectura (`whoami`, `list_agents`, `get_call`) por ASGI interno, API key `calls` provisoria | Funciona desde Claude Code; medir el costo del pedido interno |
| 1. Lectura + plan | Catálogo, scope `mcp` (UI de API keys), todas las de lectura, `get_plan_tools`, errores de plan, `make mcp-docs`, tests de catálogo y plan | Un cliente Free y uno Mostrador ven lo correcto |
| 2. Escritura | Agentes, prueba por texto, contactos, campañas, equipo, WhatsApp, links, bloqueados; anotaciones; `toolsets`; resources y prompts | Crear y probar un agente y armar (sin lanzar) una campaña solo por MCP. **Hecho el 24-oct-2026** |
| 3. OAuth | Servidor de autorización, consentimiento en `web/`, migración `oauth_*`, "Agentes conectados", ruta `mcp.` del túnel | Conector en Claude.ai con login y revocación. **En producción desde el 24-oct-2026**; falta la primera conexión real |
| 4. Publicación | Página `/desarrolladores/mcp`, botones de instalación, `server.json` en el registro, envío al directorio de Anthropic, privacidad actualizada | Instalación en un clic desde la landing. **Preparada el 24-oct-2026**: falta publicar (sección 12) |
| 5. Extras | `inference` y `admin`; métricas de uso del MCP por herramienta | Según uso real |

## 11. Abierto

- **Versión del SDK** `mcp` y de la especificación (2025-06-18 o la siguiente): fijarlas en el spike;
  la autorización cambió entre versiones (Client ID Metadata Documents).
- **Cuántas herramientas por defecto:** las 87 desde el 25-oct-2026 (`core`, 39, con `?toolsets=core`). Medir con Claude y Cursor si eligen bien.
- **Escritura con API key:** ¿un scope `mcp:read` aparte, para conectar un agente que solo mire?
- **Herramientas de cliente final** (que un agente de un tercero llame a "turnos de X" por MCP): es otro
  producto (un MCP por agente, público), no este.

## 12. Avance

**24-oct-2026: fases 0 y 1** (sin desplegar).

- `app/mcp/server.py`: `POST /mcp` (JSON-RPC 2.0: `initialize` con versiones 2025-06-18, 2025-03-26 y
  2025-11-25, `ping`, `tools/list`, `tools/call`, `resources/list` y `prompts/list` vacíos; notificaciones →
  202; `GET` → 405), `Origin` validado contra `APP_ORIGINS`, `?toolsets=`.
- `app/mcp/catalog.py`: 36 herramientas de lectura en 8 grupos (`core` = `account`, `agents`, `calls`), con la
  función del plan de cada una. Cada una es un pedido a `/api/v1` en proceso con la misma key.
- `get_plan_tools` y el error `feature_not_in_plan` (con `reason` de `features.plan_features` y
  `upgrade_url`); los `*_not_in_plan` de la API salen con el mismo formato. Validación de argumentos
  (desconocidos o faltantes) antes de pedir; los 422 de la API, como "campo: motivo".
- Scope `mcp` en las API keys (`api_usage.SCOPE_MCP`): abre `/mcp` y también la API de llamadas (las
  herramientas la usan por dentro). UI: alcance "Agentes de IA (MCP)" con el ejemplo de `claude mcp add`.
- `make mcp-docs` → [`MCP_HERRAMIENTAS.md`](MCP_HERRAMIENTAS.md); `tests/test_mcp.py` (12): protocolo, auth,
  aislamiento entre clientes, plan Free, catálogo contra el OpenAPI y doc al día.

**Desvíos del diseño:**

- Sin el SDK (sección 1). Sin `mcp.` en el túnel por ahora: `app.atentina.com.ar/mcp` ya llega a `app` (la
  ruta del túnel es todo el host), así que sirve para probar. `mcp.` queda para la fase 3 (OAuth).
- Fuera del catálogo de cliente, porque la API los deja solo a admin: usuarios (`/users`), operadores de
  WhatsApp (`/wa-operators`), límites efectivos (`/clients/{id}/limits`), borrar llamadas y vista previa
  del prompt. Van al toolset `admin` (fase 5) o se abren en la API si se decide que el cliente los use.
- `get_plan_tools` devuelve el consumo de `/clients/{id}/usage` (incluye los límites), no `limits`.

**Cómo desplegar:** sin migración. `make calls-active && make up-agent` (recrea `app` y `agent`; el
cambio es solo de `app`, pero el target es ese) y crear una key con el alcance MCP en el panel. Probar con
`claude mcp add --transport http atentina https://app.atentina.com.ar/mcp --header "Authorization: Bearer vaas_..."`.

**24-oct-2026: fase 2** (sin desplegar).

- 83 herramientas (35 en `core`): 44 de lectura y 39 de escritura, 13 de ellas para confirmar
  (`destructiveHint`: borrar, cancelar, cortar, regenerar el link, `start_call`, `create_campaign` con
  `start`, `start_campaign`, `resume_campaign`). Anotaciones `readOnlyHint`, `destructiveHint` e
  `idempotentHint` (PUT y DELETE).
- **Esquemas desde el OpenAPI:** cada herramienta de escritura nombra el modelo Pydantic del cuerpo
  (`body`) y el `inputSchema` sale de `app.openapi()`, con los `$ref` en `$defs`; sin `client_id`,
  `loadtest` ni `access_token`. Las que mandan una lista (`upsert_contacts`, `set_whatsapp_routes`) la
  reciben en un argumento (`body_arg`). El test compara cada herramienta con su ruta y su cuerpo.
- Prueba por texto (`test_agent_start`, `test_agent_turn`), `preview_voice` (audio), reporte de campaña
  como CSV en texto.
- Resources: `atentina://agents/schema` y tres guías (`agentes`, `campanas`, `derivaciones`). Prompts:
  `crear_agente`, `revisar_llamadas`, `lanzar_campana` (`app/mcp/guides.py`; un test verifica que las
  herramientas que nombran existan).
- `tests/test_mcp.py` (19). Probado además con uvicorn real (puerto aparte y SQLite en `scratch/`): 10–17 ms
  por herramienta con el pedido interno.

**Desvíos de la fase 2:**

- Sin `set_call_link_image` (la API la recibe como multipart) ni `get_whatsapp_signup_link` (el alta es
  por el popup de Facebook, en el panel).
- Sin `create_api_key`, cobros ni conexiones de LLM: la API los deja solo con sesión de usuario; llegan
  con OAuth (fase 3).
- `start_call` sin `phone` obligatorio: también llama al contacto de `contact_id`. Sin ninguno de los dos,
  la API crea una llamada de prueba por navegador (inútil desde un agente, pero sin costo).

**24-oct-2026: fase 3, OAuth 2.1** (sin desplegar; migración 0028).

- `app/services/oauth.py` (lógica) y `app/api/oauth.py` (rutas). Metadata `/.well-known/oauth-protected-resource[/mcp]`
  y `/.well-known/oauth-authorization-server`; el 401 de `/mcp` lleva `WWW-Authenticate: Bearer
  resource_metadata="…"`, así el cliente MCP descubre el login solo.
- **Emisor = el mismo host que sirve `/mcp`** (hoy `app.atentina.com.ar`, mañana `mcp.`): login, consentimiento
  y token en el mismo origen, sin configuración. El `resource` del token es `<host>/mcp` y se verifica.
- Clientes: registro dinámico (RFC 7591; públicos con PKCE o confidenciales con `client_secret_basic`/`_post`)
  y Client ID Metadata Documents (el `client_id` es una URL https; se lee con `resolve_public`, sin redirects,
  hasta 16 KB, y se guarda un día). `redirect_uri`: https, http solo a loopback (cualquier puerto, RFC 8252)
  o esquema propio (`cursor://`).
- `/oauth/authorize` → `/oauth/consent` (SPA, con sesión; el login vuelve ahí). La pantalla muestra la app,
  si está identificada (metadata document) o es un registro sin verificar, a dónde vuelve y qué va a poder
  hacer. Un admin elige el cliente: el token actúa **con rol de cliente** en ese cliente, nunca como admin.
- Código de 10 min y un solo uso (reusarlo revoca el permiso), PKCE S256 obligatorio, `iss` en la respuesta
  (RFC 9207). Access 1 h, refresh 30 días con rotación (reusar uno rotado revoca el permiso). `/oauth/revoke`
  (RFC 7009). Cambiar la clave o cerrar sesión (`session_version`) corta los agentes del usuario.
- **El token OAuth no abre la API:** `deps.get_principal` lo acepta solo con el header interno que pone el MCP
  (`x-atentina-mcp`, un secreto aleatorio por proceso que no sale de `app`). Las rutas de consentimiento y de
  agentes conectados exigen sesión del panel (`SessionPrincipal`).
- Con OAuth se suman `get_billing`, `list_api_keys`, `list_llm_params` y `list_llm_connections` (`session` en
  el catálogo, 87 herramientas); con API key responden `needs_oauth` y `get_plan_tools` las lista aparte.
- UI: tarjeta "Agentes de IA (MCP)" en Desarrolladores (y en el detalle del cliente para el admin): URL,
  comando de Claude Code y "Agentes conectados" con "Desconectar".
- Tests: `tests/test_oauth.py` (17), `tests/test_migration_0028.py`, `OAuthConsentPage.test.tsx` (3). De punta
  a punta contra uvicorn real (`scratch/oauth_smoke.py`): 401 → metadata → registro → consentimiento → token →
  herramientas (incluida `get_billing`); el mismo token contra `/api/v1` da 401.

**Desvíos de la fase 3:**

- Sin la ruta `mcp.` del túnel: con el emisor por host no hace falta para empezar. Si se crea, el conector
  nuevo usa `https://mcp.atentina.com.ar/mcp` y sus tokens valen solo ahí.
- Sin CORS en `/mcp` ni en `/oauth/*`: los clientes que hacen OAuth desde el navegador (el MCP Inspector en
  modo directo) no andan; Claude.ai, ChatGPT, Claude Code y Cursor lo hacen del lado del servidor o de la app.
- Un solo alcance (`mcp`): lectura y escritura. `mcp:read` queda abierto (sección 11).

**Cómo desplegar:**

1. `make migrate-test` (0028 contra una copia del backup).
2. `make calls-active && make up-agent` (migra y recrea `app` y `agent`; corta llamadas en curso).
3. Probar: en Claude.ai, Configuración → Conectores → Agregar conector personalizado →
   `https://app.atentina.com.ar/mcp`; o `claude mcp add --transport http atentina https://app.atentina.com.ar/mcp`.

**Desplegado el 24-oct-2026:** `make migrate-test` (0024 → 0028 sobre la copia del backup, ida y vuelta),
`make calls-active && make up-agent` (la base en vivo estaba en 0027 y quedó en 0028). Verificado por el túnel:
metadata con emisor `https://app.atentina.com.ar`, 401 de `/mcp` con `resource_metadata` y `/oauth/consent`.
Falta la primera conexión real desde Claude.ai o Claude Code (la hace el usuario con su login).

**24-oct-2026: fase 4, publicación** (preparada; el registro, publicado el 25-oct-2026; la landing espera publicarse).

- Landing: `/desarrolladores/mcp` (desde el 25-oct-2026 en `/desarrolladores/docs/mcp`, con la portada y la API en
  `/desarrolladores/docs/api`; la URL vieja redirige) (pasos para Claude, ChatGPT, Claude Code, Cursor y VS Code con botones de
  instalación, `mcp-remote`, API key, funciones por plan, herramientas plegadas por grupo, seguridad, guías). Sale
  de `landing/src/data/mcp-tools.json` (`make mcp-docs`; test de sincronía). Links desde el footer, "Integración
  agéntica" de `/desarrolladores` y la sección nueva "Agentes de IA (MCP)" de la documentación (más el alcance
  `mcp` en su tabla de keys). Layout compartido `DocsPage.astro` con `/desarrolladores/docs`; de paso se arregló el
  desborde horizontal de 50 px que la documentación ya tenía en 375 px (una URL en `code`).
- Privacidad (`/privacidad#agentes-conectados`): excepción por los agentes de IA que conecta el cliente, como la
  del LLM propio, y en la lista de proveedores.
- Registro oficial: `deploy/mcp/server.json` (`ar.com.atentina/atentina`, remoto `streamable-http`) y
  `scripts/ops/mcp-registry.sh` con `make mcp-registry-key` y `make mcp-registry-publish`.

**Publicar (lo hace el usuario):**

1. Landing: push a la rama de Render (solo despliega `landing/`).
2. Registro de MCP: `make mcp-registry-key` → cargar el TXT que imprime en el DNS de `atentina.com.ar`
   (Cloudflare, nombre `@`) → `make mcp-registry-publish`. Al cambiar la versión del servidor, subir `version` en
   `server.json` y volver a publicar (repetir la misma versión da 400 `duplicate version`). PulseMCP, Glama y otros
   directorios lo toman del registro. **Hecho el 25-oct-2026:** `ar.com.atentina/atentina@1.0.0`, activo
   (`curl -s "https://registry.modelcontextprotocol.io/v0/servers?search=ar.com.atentina"`). `server.json` quedó en 1.0.1,
   con `websiteUrl` en `/desarrolladores/docs/mcp`, publicada el 25-oct-2026 (es la `isLatest`).
3. Directorio de conectores de Anthropic (formulario de envío): nombre Atentina; URL `https://app.atentina.com.ar/mcp`;
   OAuth 2.1 con registro dinámico y metadata documents; docs `https://atentina.com.ar/desarrolladores/docs/mcp`;
   privacidad `https://atentina.com.ar/privacidad`; herramientas con `readOnlyHint`/`destructiveHint`. Piden una
   cuenta de prueba para la revisión: crear un cliente de prueba con un tier con todo y un agente de ejemplo.
4. ChatGPT: por ahora como conector propio de cada usuario (modo desarrollador); su directorio, si hay demanda.

**Pendiente:** la ruta `mcp.` del túnel (opcional), CORS para clientes de navegador, `mcp:read` y el toolset `admin`
(fase 5).
