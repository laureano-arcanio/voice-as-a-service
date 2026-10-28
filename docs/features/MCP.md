# MCP

Servidor MCP remoto que expone la plataforma como herramientas para el agente de IA del cliente (Claude, ChatGPT,
Cursor, Claude Code, un agente propio): crear y probar agentes, ver llamadas, cargar contactos, armar campañas y el
equipo, sin abrir el panel. Estado: en producción desde el 24-oct-2026. Plan: todos; cada herramienta pide la función
de `services/features.TIER_HAS` que corresponda. Catálogo generado: [`MCP_HERRAMIENTAS.md`](../MCP_HERRAMIENTAS.md).

- URL: `https://app.atentina.com.ar/mcp` (Streamable HTTP, sin estado, respuestas JSON, sin SSE).
- Registro oficial: `ar.com.atentina/atentina` (`deploy/mcp/server.json`, versión 1.0.1). Documentación pública en
  `/desarrolladores/docs/mcp` de la landing.

## Modelo de datos

| Tabla | Qué guarda | Migración |
|---|---|---|
| `api_keys.scopes` | alcances `mcp` (lectura y escritura) y `mcp_read` (solo lectura) | — |
| `oauth_clients` | clientes OAuth: registro dinámico o Client ID Metadata Document (`id` = URL, `fetched_at`) | 0028 |
| `oauth_grants` | permiso de un usuario a una app: `user_id`, `client_id` (null = "Toda la plataforma"), `resource`, `session_version`, `last_used_at`, `revoked_at` | 0028, 0029 |
| `oauth_codes`, `oauth_tokens` | código (hash, PKCE) y tokens access/refresh (SHA-256, vencimiento, revocación) | 0028 |
| `mcp_tool_usage` | por día, cliente y herramienta: `calls`, `errors`, `total_ms` | 0029 |

## API

| Ruta | Qué hace |
|---|---|
| `POST /mcp` | JSON-RPC 2.0: `initialize` (versiones 2025-06-18, 2025-03-26, 2025-11-25), `ping`, `tools/list`, `tools/call`, `resources/list|read`, `prompts/list|get`; notificaciones → 202 |
| `GET /mcp` | 405 (sin stream de avisos) |
| `/mcp?toolsets=a,b` | elige grupos; `all` = todos los de cliente, `core` = `account`, `agents`, `calls` |
| `/.well-known/oauth-protected-resource[/mcp]`, `/.well-known/oauth-authorization-server` | metadata OAuth (RFC 9728 y 8414) |
| `/oauth/authorize` → `/oauth/consent` (SPA) | login del panel y consentimiento |
| `/oauth/register`, `/oauth/token`, `/oauth/revoke` | registro dinámico (20/h por IP), token (120/min por IP), revocación |
| `GET/DELETE /api/v1/oauth/grants[/{id}]` | "Agentes conectados" (exige sesión del panel) |
| `GET /api/v1/mcp/usage` | uso por herramienta (el cliente, el suyo; el admin, uno o todos) |

**Catálogo** (`app/mcp/catalog.py`): 154 herramientas (85 de lectura, 31 destructivas).

| Grupo | Herramientas | Por defecto |
|---|---|---|
| `account`, `agents`, `calls` (`core`) | 10 + 46 + 11 | sí |
| `reports`, `call_links`, `whatsapp`, `contacts`, `campaigns`, `team` | 6 + 5 + 6 + 11 + 14 + 13 | sí |
| `inference` | 3 (`transcribe_audio`, `synthesize_speech`, `get_inference_usage`) | no |
| `admin` | 29 (`admin_*`, `get_report_technical`, `get_report_platform`) | solo token "Toda la plataforma" |

Sin parámetro: 122 herramientas (~18k tokens de contexto); `core`: 67. Resources: `atentina://agents/schema` y tres
guías; prompts: `crear_agente`, `revisar_llamadas`, `lanzar_campana` (`app/mcp/guides.py`).

## Flujo

- `app/mcp/server.py`: JSON-RPC propio, sin el SDK. Valida `Origin` contra `APP_ORIGINS` si viene (DNS rebinding).
- Cada herramienta es un pedido a `/api/v1` en el mismo proceso (`httpx` + `ASGITransport`, sin red; 10-17 ms por
  herramienta) con la credencial de quien pide: permisos, plan y quota los corta la API. El MCP solo adelanta el
  chequeo de plan para dar el motivo claro.
- `Tool` en el catálogo: `method`, `path`, `features` (claves de `TIER_HAS`; vacío = todos), `body` (modelo Pydantic
  de la ruta: el `inputSchema` sale del OpenAPI, con los `$ref` en `$defs`), `body_arg` (cuerpo lista), `session`
  (solo OAuth), `api_key_only` (inferencia), `upload` (multipart en base64), `audio`, `text` (CSV).
- Campos que nunca se exponen: `client_id`, `loadtest`, `access_token`, `password` (`OMIT`). `{client_id}` lo pone el
  servidor desde el token.
- Anotaciones: `readOnlyHint`, `destructiveHint` (borrar, cancelar, cortar, llamar, mandar), `idempotentHint` (PUT y
  DELETE).
- Errores como resultado con `isError: true`: `feature_not_in_plan` (con `reason` de `features.plan_features` y
  `upgrade_url`), `needs_oauth`, `needs_api_key`, `invalid_arguments`, `audio_too_large` (>5 MB) y los de la API
  (`code` o `http_<status>`; 422 como "campo: motivo").
- `get_plan_tools` va siempre: herramientas disponibles, no disponibles (con motivo), `needs_oauth`, `needs_api_key` y
  el consumo de `/clients/{id}/usage`. Mira los límites efectivos (tier + ajustes), no el nombre del plan.
- Después de cada `tools/call`, `mcp_usage.record` anota la herramienta; si falla, no corta la respuesta.

### Autenticación

- **API key** `mcp` (o `mcp_read`): `Authorization: Bearer vaas_...`. Una key `calls` no abre `/mcp`. Con `mcp_read` se
  listan y usan solo las de lectura; por fuera del MCP esa key solo hace `GET`. Las `session` responden `needs_oauth`.
- **OAuth 2.1** (`app/services/oauth.py`, `app/api/oauth.py`): PKCE S256 obligatorio, registro dinámico (RFC 7591) y
  Client ID Metadata Documents (URL https, sin redirects, hasta 16 KB, cache de un día). `redirect_uri`: https, http a
  loopback o esquema propio. Código de 10 min y un uso (reusarlo revoca el permiso); access 1 h, refresh 30 días con
  rotación (reusar uno rotado revoca). `iss` en la respuesta (RFC 9207).
- **Emisor por host:** el emisor es el host que sirve `/mcp`; el `resource` del token es `<host>/mcp` y se verifica.
  El 401 de `/mcp` lleva `WWW-Authenticate: Bearer resource_metadata=...`: el cliente descubre el login solo.
- **El token OAuth no abre `/api/v1`:** `deps.get_principal` lo acepta solo con el header interno `x-atentina-mcp`
  (secreto aleatorio por proceso, no sale de `app`). Cambiar la clave o cerrar sesión (`session_version`) corta los
  agentes del usuario.
- Consentimiento: muestra la app (identificada o registro sin verificar), a dónde vuelve y qué va a poder hacer. Un
  admin elige un cliente (el token actúa con rol de cliente) o **"Toda la plataforma"**: `oauth_grants.client_id`
  null, ve `admin` y todas las de cliente (151 por defecto); estas piden `client_id` en cada llamada y van con
  `x-atentina-mcp-client` (solo vale con el secreto interno). Vale mientras el usuario siga siendo admin.
- UI: tarjeta "Agentes de IA (MCP)" en Desarrolladores (`web/src/features/oauth/McpAccess.tsx`): URL, comando de
  Claude Code, "Agentes conectados" con "Desconectar" y "Uso por herramienta".

## Reglas y trampas

- Una herramienta que el plan no incluye se lista igual (con el plan que la trae en la descripción) y responde
  `feature_not_in_plan`: el agente puede explicar qué falta.
- Las de admin dejan afuera, a propósito, borrar clientes, planes y llamadas en masa, crear usuarios y cambiar claves
  (la clave pasaría por el LLM).
- Transcripciones, contactos y mensajes los escriben terceros: se devuelven como datos (`structuredContent`); lo que
  llama o manda mensajes lleva `destructiveHint` para que el cliente confirme.
- Con el MCP las transcripciones salen al proveedor de LLM del cliente: lo cubre `/privacidad#agentes-conectados`.
- Sin CORS en `/mcp` ni `/oauth/*`: clientes OAuth de navegador (MCP Inspector directo) no andan; Claude.ai, ChatGPT,
  Claude Code y Cursor sí.
- Sin límite de pedidos propio en `/mcp`: aplican los de la API y los topes del tier.
- Todas por defecto: con 87 herramientas Claude Sonnet 5.5 eligió bien 32/33 y Haiku 5.5 33/33; con las 39 de `core`,
  18/23 y 20/23 (falta la herramienta y se queda en el plan). Medido el 25-oct-2026.
- `get_plan_tools` y `whoami`: una descripción ambigua de `whoami` ("con su plan") desviaba "¿qué incluye mi plan?".

### Solo en el panel

Login, perfil, clave y condiciones; cobros y plan (el MCP no cobra; `feature_not_in_plan` trae `upgrade_url` a `/plan`); crear o borrar API
keys y permisos OAuth; atender, rechazar y entrar a llamadas directas y la presencia (WebRTC); la imagen del link para
llamar; el alta y la gestión de la cuenta de WhatsApp (tokens de Meta, Embedded Signup); editar `direct_calls` de un
tier.

## Desplegar y probar

- Al cambiar una herramienta o un tier: `make mcp-docs` (regenera `docs/MCP_HERRAMIENTAS.md` y
  `landing/src/data/mcp-tools.json`, sin `admin`) y publicar la landing.
- Tests: `tests/test_mcp.py` (protocolo, auth, aislamiento entre clientes, plan, catálogo contra el OpenAPI, doc al
  día, guías) y `tests/test_oauth.py` (flujo con PKCE y `resource`, admin con toda la plataforma).
- `make mcp-eval [MODELS=...]` (`scripts/mcp/eval_tools.py`, OpenRouter, gasta tokens): 33 pedidos, mide si el modelo
  elige la herramienta correcta. Correrlo si cambian descripciones.
- Probar: `claude mcp add --transport http atentina https://app.atentina.com.ar/mcp` (OAuth) o con
  `--header "Authorization: Bearer vaas_..."`.
- Registro: `make mcp-registry-key` (una vez; imprime el TXT para el DNS de `atentina.com.ar`) y
  `make mcp-registry-publish`. Otra versión: subir `version` en `deploy/mcp/server.json` (repetir da 400
  `duplicate version`).
- Directorio de conectores de Anthropic: enviado el 25-oct-2026 (portal claude.ai/directory/manage/atentina-mcp-server).
  La cuenta de los revisores es el cliente `revision_anthropic` (plan Sucursal, usuario
  `revision-anthropic@atentina.com.ar`, agente Peluquería Demo, contactos `demo`, una campaña en borrador y el área
  Ventas): no borrarla hasta que termine la revisión.

## Pendientes

- `make mcp-eval` con el catálogo actual (154): falta medir, entre otras, que elija `start_direct_call` cuando habla
  la persona y `start_call` cuando llama el agente.
- Subir la versión de `deploy/mcp/server.json` y republicar en el registro.
- Primera conexión OAuth real desde Claude.ai o Claude Code.
- Resultado de la revisión del directorio de Anthropic.
