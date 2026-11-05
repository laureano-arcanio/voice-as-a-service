# Herramientas

Lo que un agente puede hacer durante la conversación: llamar a una API del cliente (`http`) o correr una función
JavaScript suya en un sandbox (`code`), con secretos cifrados y credenciales del cliente, más las herramientas de
plataforma `end_call` y `transfer_call`. Todo por function calling nativo. Además, dos herramientas automáticas que el
modelo no ve: antes y después de la conversación (ver Workflows). Estado: en producción desde el
26-oct-2026 (secretos del cliente y credenciales, desde el 27-oct-2026). Plan: `tiers.max_tools` y
`tiers.code_tools` (claves `custom_tools` y `code_tools` de `services/features.TIER_HAS`).

## Modelo de datos

| Tabla (migración) | Columnas clave |
|---|---|
| `tools` (0032) | `client_id`, `slug` (único por cliente), `type` (`http` \| `code`), `definition` (JSON), `revision`, `last_test_at`/`_ok`/`_detail` |
| `tool_versions` (0033) | `tool_id`, `revision`, `type`, `definition`, `created_by`, `created_at`: una fila por cada versión guardada |
| `client_secrets` (0035) | `client_id`, `name` (único por cliente), `value_enc`, `last4`, `description` |
| `agent_secrets` (0032) | `agent_id`, `name`, `value_enc`, `last4`, `description`: valor propio del agente, pisa al del cliente |
| `credentials` (0035) | `client_id`, `slug`, `name`, `description`, `auth` (JSON de un `Auth`, sin valor: `auth.secret` es el nombre del secreto) |
| `tool_runs` (0036) | una fila por ejecución en una conversación: `slug`, `type`, `ok`, `status_code`, `ms`, `error` (reportes del admin) |
| `tiers` (0032) | `max_tools` (`NULL` = sin tope, `0` = no incluido), `code_tools` |
| `conversations.post_call_status`, `_attempts`, `_next_at`, `_note` (0048) | Estado del post-call de la conversación (ver Workflows) |

- Secretos: nombre `^[A-Z][A-Z0-9_]{1,63}$`, valor hasta 10.000 caracteres, cifrado con Fernet y `WA_TOKEN_KEY`
  (`app/whatsapp/crypto.py`, el mismo de `llm_connections`). La API nunca devuelve el valor (solo `last4`).
  Topes: 100 por cliente, 50 por agente, 50 credenciales por cliente (`app/services/tools.py`).
- Valores de una conversación: los del cliente pisados por los propios del agente (`services/tools.secret_values`).
- En el agente (definición versionada): `tools: [{"tool": "<slug>"}]` y
  `tool_settings: {"max_calls_per_turn": 3, "limit_message": "Disculpá, no pude completar eso."}` (1 a 10). Un
  agente con `external` no lleva `tools` (las herramientas son de su agente; ver [LLM_CONEXIONES.md](LLM_CONEXIONES.md)).
- El agente referencia la herramienta por slug: editarla cambia todos los agentes que la usan sin versión nueva del
  agente. La traza de cada ejecución guarda `revision`.
- Valores de plan en la base hoy (editables en Tiers): Free `0`; Mostrador `3` con código; Sucursal `10` con código;
  Interno sin tope, con código.

## Herramienta `http`

Formato en `app/tools/schema.py` (`HttpTool`), ejecución en `app/tools/runtime.py`.

```json
{
  "description": "Busca turnos libres de una sucursal para una fecha.",
  "confirm": false,
  "http": {
    "method": "GET",
    "url": "https://api.acme.com/v1/sucursales/{sucursal}/turnos",
    "path":  {"sucursal": {"type": "string", "enum": ["centro", "norte"], "description": "Sucursal elegida"}},
    "query": {"fecha": {"type": "string", "format": "date", "description": "AAAA-MM-DD", "required": true},
              "telefono": {"type": "string", "value": "{{call.from}}"}},
    "headers": {"X-Tenant": "acme"},
    "body": null,
    "content_type": "application/json",
    "auth": {"type": "credential", "credential": "api_acme"},
    "timeout_ms": 8000, "retries": 0, "sign": false
  },
  "response": {"pick": ["turnos", "sucursal.nombre"], "max_chars": 4000},
  "assign": [{"var": "turno_id", "path": "turnos[0].id", "hide": false}],
  "messages": {"start": "Dame un segundo.", "delayed": {"after_ms": 3000, "text": "Sigo buscando."},
               "failed": "No pude consultar los turnos ahora."}
}
```

**Parámetros.** `path` y `query` son mapas de parámetros escalares (`string`, `integer`, `number`, `boolean`; en
query también `array`). `body` es un JSON Schema de tipo `object` (anidados permitidos; con `x-www-form-urlencoded`,
solo valores simples). Cada parámetro tiene un solo origen:

- con `description` y sin `value`: lo llena el modelo; es lo único que entra en el esquema que ve;
- con `value`: fijo, literal o template; el modelo no lo ve ni lo puede pisar (límite contra inyección de prompt).

Los de `path` son siempre obligatorios; los de query, con `"required": true`; los del body, por su `required`. Las
`{variables}` de la URL y `path` tienen que coincidir, y un mismo nombre no puede repetirse entre path, query y body
(se valida al guardar). Los argumentos del modelo se validan con `jsonschema` antes de ejecutar; si no valen, vuelve
`{"ok": false, "error": "argumentos inválidos: ..."}` y el modelo decide.

**Templates** (en URL, valores fijos, headers, `auth.username`, `auth.client_id`):

| Template | Valor |
|---|---|
| `{{secrets.NOMBRE}}` | secreto del cliente o del agente |
| `{{call.id}}`, `{{call.channel}}`, `{{call.mode}}`, `{{call.from}}`, `{{call.to}}`, `{{call.phone}}` | conversación, canal (`voice`, `whatsapp`, `web`), modo (`entrante`, `saliente`, `whatsapp`...), números E.164; `phone` es siempre la otra punta (el menú Variables lo ofrece y la prueba lo llena) |
| `{{agent.slug}}`, `{{agent.version}}` | agente |
| `{{now}}`, `{{today}}` | fecha y hora en `AGENT_TIMEZONE` |
| `{{fields.x}}`, `{{contact.x}}`, `{{vars.x}}` | dato obtenido, contacto de campaña, valor guardado por otra herramienta (`assign`) |

El host de la URL no puede tener variables. Un parámetro de path o uno fijo obligatorio sin valor da
`missing_variable` sin llamar; un secreto que falta, `missing_secret`.

**Autenticación** (`http.auth`):

| `type` | Campos | Qué manda |
|---|---|---|
| `none` | | nada |
| `credential` | `credential` (slug) | lo de la credencial del cliente, resuelta al ejecutar (`schema.resolve`); sin ella, `missing_credential` |
| `bearer` | `secret`, `header` (default `Authorization`), `prefix` (default `Bearer `) | `<header>: <prefix><secreto>` |
| `api_key` | `secret`, `in` (`header` \| `query`), `name` | header o parámetro de query |
| `basic` | `username` (literal o template), `secret` | `Authorization: Basic base64(user:clave)` |
| `oauth2_client_credentials` | `token_url`, `client_id`, `secret`, `scope`, `audience`, `client_auth` (`body` \| `basic`) | pide el token (RFC 6749 4.4), lo cachea en memoria hasta `expires_in − 60 s` y lo vuelve a pedir una vez ante un 401 |

**Headers.** Los propios aceptan templates. No se permiten `Host`, `Content-Length`, `Transfer-Encoding`,
`Connection`, `User-Agent`, `Idempotency-Key`, `X-Atentina-*` ni el que ya pone `auth`. La plataforma manda siempre
`User-Agent: Atentina-Tools/1`, `X-Atentina-Conversation-Id`, `X-Atentina-Tool` y, en todo método que no es GET,
`Idempotency-Key: <conversation_id>:<tool_call_id>`.

**Firma** (`sign: true`): `X-Atentina-Signature: t=<unix>,v1=<hex>`, HMAC-SHA256 de `"<t>.<cuerpo crudo>"` con el
secreto `ATENTINA_SIGNING_SECRET` (formato de Stripe). Es un secreto más: tiene que estar cargado.

**Pedido.** GET y DELETE sin body. `timeout_ms` 500 a 30.000 (default 8000). `retries` 0 a 2, con backoff
300 ms × 2ⁿ, ante error de red, timeout, 429 o 5xx. No se siguen redirects (un 3xx es error). Respuesta leída hasta
1 MB.

**Respuesta al modelo.** 2xx: `{"ok": true, "status": 200, "data": ...}`. Error: `{"ok": false, "status": 404,
"error": "<cuerpo recortado a 500>"}` o `"error": "timeout"`. Orden: `assign` (guarda en `vars`; con `hide` se saca
del resultado), `response.pick` (rutas con puntos y `[i]`), tachado de secretos y recorte a `response.max_chars`
(200 a 15.000, default 4000).

**Red (SSRF).** Solo https, puertos 443 u 8443. El host se resuelve y se conecta a esa misma IP, validada como
pública, en un pool de httpcore con backend propio (`SafeBackend`): un DNS que cambia entre el chequeo y la conexión no
burla el filtro. Sin proxies del entorno. `runtime.PRIVATE_HOSTS` deja pasar hosts internos solo en tests y e2e (no
hay configuración para habilitarlo).

## Herramienta `code`

```json
{
  "description": "Busca la deuda de una persona por DNI.",
  "parameters": {"type": "object", "properties": {"dni": {"type": "string", "description": "DNI sin puntos"}},
                 "required": ["dni"]},
  "code": "export default async function ({ args, secrets, call, vars }) { ... }",
  "secrets": ["CRM_TOKEN"],
  "allowed_hosts": ["api.crm-ejemplo.com"],
  "timeout_ms": 5000
}
```

- Módulo ES (JavaScript o TypeScript, hasta 20.000 caracteres) con `export default async function`. Recibe `args`
  (validados contra `parameters`), `secrets` (solo los declarados en `secrets`), `call` y `vars`. La plantilla sale de
  `GET /tools/code-template`.
- Retorno: cualquier valor JSON → `{"ok": true, "data": ...}`. Una excepción o `return {ok: false, error}` →
  `{"ok": false, "error": ...}`. `console.*` va a la traza y a la prueba (hasta 200 líneas de 2000 caracteres), no al
  modelo.
- `allowed_hosts`: dominios exactos, con puerto si no es 443; sin comodines ni IPs (hasta 20).
- `timeout_ms` 500 a 30.000 (default 5000). Mismo `response`, `assign` y `messages` que `http`.

**Sandbox** (`tools-runner/`, Deno 2.8.3 fijado):

- `app` y `agent` llaman `POST $TOOLS_RUNNER_URL/run` (`http://tools-runner:8080`) con `Bearer $TOOLS_RUNNER_TOKEN`.
  Sin `TOOLS_RUNNER_URL`, la herramienta devuelve `runner_unavailable`; `GET /tools/status` le avisa a la UI.
- `server.ts` lanza un proceso Deno nuevo por función: `deno run --no-prompt --no-config --no-npm --no-remote
  --v8-flags=--max-old-space-size=64 --allow-net=<allowed_hosts> runner.js`, con el entorno vacío. Sin permisos de
  lectura, env, procesos ni FFI. El código entra por stdin y se importa desde un `data:` URL; se mata con SIGKILL al
  pasar `timeout_ms`.
- `runner.js` envuelve `fetch` con tope de 1 MB por respuesta.
- Concurrencia: `TOOLS_RUNNER_CONCURRENCY` (8); el resto espera hasta su timeout y si no entra devuelve "sandbox
  ocupado".
- Contenedor `read_only`, `tmpfs /tmp` de 128 MB, `cap_drop: ALL`, `no-new-privileges`, 1 GB, 2 CPU, 256 pids.
- **Red, dos capas:** `--allow-net` de Deno a los `allowed_hosts`, y la red `atentina-tools` es interna: la única
  salida es `tools-egress` (Smokescreen v0.1.0, por `HTTPS_PROXY`), que niega IPs privadas, loopback, link-local y
  metadata.
- Los secretos llegan como valor (no como placeholder): solo pueden salir hacia los `allowed_hosts` que declaró el
  mismo cliente que los cargó.

## Secretos y credenciales

- Referencia por nombre: `{{secrets.X}}` en `http`, `secrets.X` en `code`. Los secretos que pide una herramienta se
  deducen de sus templates, de `auth` (o de la credencial) y de `sign`; en `code`, de `secrets`.
- El modelo nunca ve un secreto: no están en el prompt, el esquema ni el resultado. Antes de devolver el resultado y
  de guardar la traza se reemplaza todo valor de secreto (literal, URL-encoded y base64) y el token OAuth2 por
  `[secreto:NOMBRE]`.
- Se descifran al ejecutar, con caché de 30 s por agente (`app/tools/conversation.py`): rotar rige en ≤ 30 s.
- Una credencial (`bearer`, `api_key`, `basic` u `oauth2_client_credentials`) es la autenticación de una API del
  cliente; la herramienta la usa con `{"type": "credential", "credential": "<slug>"}`. Cambiarla rige en todas las
  herramientas que la usan sin subir su `revision`. Al crearla o editarla con `value`, el valor va al secreto
  `auth.secret` (lo crea o lo reemplaza).

**Reglas al guardar o borrar** (`app/services/tools.py`):

- Agente: cada herramienta existe, es del cliente, el plan la incluye y cada secreto que pide está en el cliente o en
  el agente (`invalid_definition` con `path` `tools.N.tool`).
- Herramienta o credencial que pasa a pedir un secreto nuevo: cada agente que la usa lo tiene, o 422 `missing_secret`.
  La credencial tiene que existir y su header no puede chocar con los de la herramienta.
- Borrar un secreto del cliente: 409 si lo usa una credencial o una herramienta de un agente sin valor propio. Borrar
  el propio de un agente: vuelve al del cliente; 409 solo si el cliente no lo tiene y una herramienta lo usa.
- Borrar una credencial: 409 si una herramienta la usa (el secreto queda). Borrar una herramienta: 409
  `tool_in_use` si la usa un agente no archivado.
- Pasar al cliente (`promote`): crea el secreto del cliente con el valor del agente y borra el propio de todos los
  agentes con ese mismo valor; 409 si el cliente ya tiene uno con otro valor.
- Plan: crear con `max_tools = 0` → 429 `tools_not_in_plan`; código sin `code_tools` → `code_tools_not_in_plan`;
  al llegar al tope → `tools_limit`.

## Herramientas de plataforma

`app/llm/platform_tools.py`. Las ve el modelo junto con las del cliente; no se ejecutan: cambian el estado del turno
y el worker corta o deriva después de decir el texto de ese mensaje. Sus nombres (`end_call`, `transfer_call`) están
reservados para los slugs del cliente.

| Herramienta | Cuándo | Parámetros | Efecto |
|---|---|---|---|
| `end_call` | siempre | `motivo`: `terminada` \| `fuera_de_tema` (con tu propio agente, `outcome`: un id de `completion.outcomes`) | `status = completed`; `fuera_de_tema` → `ended_reason=off_topic` y resultado "Fuera de tema" |
| `transfer_call` | llamada de voz con áreas de derivación (`progress.handoff_areas`), o WhatsApp de texto con áreas con plantilla | `area` (enum de las áreas; la descripción dice cuándo pasar a cada una y si atiende ahora) | `AgentTurn.handoff`; si también vino `end_call`, gana cortar |

## Workflows: antes y después de la conversación

Herramientas del cliente que corre la plataforma sola, **sin que el modelo las vea**. Sirven para traer datos de la
persona al empezar y para registrar algo al terminar, sin que dependan de lo que el modelo decida. En la definición
del agente (versionada):

```json
"workflows": {
  "pre_call":  {"tool": "buscar_ficha", "timeout_ms": 1500},
  "post_call": {"tool": "registrar_cobro", "when": "handoff_accepted"}
}
```

- `timeout_ms`: 200 a 5000 (1500). `when`: `handoff_accepted` (una persona del equipo aceptó la derivación) o `always`. Un solo
  post-call por agente. Sin el bloque, todo sigue igual. Un agente con «tu propio agente» también los lleva.
- **Reglas al guardar** (`check_agent_tools`, errores con `path` `workflows.<pre_call|post_call>.tool`): la herramienta
  existe, es del cliente, el plan la incluye y sus secretos están; **no tiene parámetros que complete el modelo** (todos
  sus valores van fijos); no está también en `tools`; no es la misma en el pre-call y el post-call; y el post-call tiene que
  ser `http` con método distinto de `GET`, porque es lo único que lleva `Idempotency-Key`. Borrar una herramienta que usa
  un workflow: 409 `tool_in_use`.
- **Ejecución:** `ConversationTools.run_workflow`, con `Idempotency-Key` fija `<conversación>:pre_call` o
  `<conversación>:post_call`. Deja una fila en `tool_runs` y el evento `workflow.pre_call` o `workflow.post_call` (`ok`,
  `status`, `ms`, `slug`; `reason` `not_executable` si no se pudo ejecutar o `max_attempts`). **La respuesta no se guarda**
  en mensajes, traza ni eventos; `tool_runs.error` y `tools[].last_error` de un workflow traen solo el diagnóstico
  (`herramienta automática: <código> | HTTP <n> | falla de conexión: sí/no`). El texto de error de las herramientas que
  llama el modelo sigue guardándose (hasta 255 caracteres; solo el admin lo ve, en `/reports/technical`).
- **`{{call.phone}}`:** siempre la otra punta de la conversación (el teléfono de quien llama, o el de la persona en una
  saliente; en WhatsApp, `+wa_id`). `{{call.from}}` en una saliente es el número de la empresa, así que no sirve para
  identificar a la persona.

**Pre-call.** Reutiliza `assign`: cada valor va a `progress.tool_vars` (disponible para herramientas, mensajes del área y
plantillas) y los de `hide: false` pasan por `contact.preload`: precargan un campo del agente con el mismo nombre y el
resto llega al prompt como «Datos del contacto» (con «tu propio agente», en el header `X-Atentina-Contact`). Los de
`hide: true` nunca llegan al modelo. **Suma, no pisa:** gana lo que ya estaba (datos de campaña, teléfono precargado). La
apertura se renderiza con las variables visibles, también si el pre-call falló (no se lee `{{nombre}}`): en voz reemplaza
la última apertura, y por WhatsApp (que no tiene apertura) va a la guía de apertura del prompt.

| Canal | Cuándo corre | Quién espera |
|---|---|---|
| Voz (todos los modos salvo `loadtest`) | En el worker, antes de `session.start` y de marcar | Una entrante o una llamada de WhatsApp: la persona, hasta `timeout_ms`. Una saliente: nadie |
| WhatsApp de texto | Solo al crear la conversación, antes del primer turno | Nadie, pero retiene el lock de ese contacto hasta `timeout_ms` |
| `POST /conversations/{id}/turns` | No corre: no es un canal real | |

Si falla o vence, la conversación sigue sin datos: la tarea no se cancela (queda su fila en `tool_runs`) y su resultado
tardío se ignora. Si la persona corta durante la espera, la llamada termina sin apertura, sin pasar a `en_curso` y sin
armar el post-call.

**Post-call.** Durable, como el resumen por email (`app/mail/call_summary.py`): el worker o WhatsApp marcan en
`conversations.post_call_*` y un loop de `app` (`post_call_loop`, cada `WORKFLOW_TICK_SECONDS`, 10) lo ejecuta, porque el
worker puede morir con la llamada. Corre **una sola vez por conversación**.

| `post_call_status` | Significa | Pasa a |
|---|---|---|
| `null` | No corresponde o todavía no | `armed` o `pending` |
| `armed` | Se cumplió la condición con la llamada en curso. Si el worker muere, el loop lo toma al vencer `next_at` (duración máxima + 600 s) | `pending` |
| `pending` | Listo para correr, desde `next_at` | `running` |
| `running` | Corriendo; si `app` muere, se retoma al vencer `next_at` (180 s) | `done`, `pending` o `failed` |
| `done` | La herramienta respondió 2xx, diga lo que diga | Final |
| `failed` | Respondió otra cosa, no se pudo ejecutar o se agotó el transporte | Final, con evento |

- **Qué se reintenta (solo transporte):** timeout o error de conexión, 429 y 5xx, también del servidor de tokens. Hasta 4
  intentos en 11 minutos (esperas de 0, 1 y 10 minutos), con la misma `Idempotency-Key`. Un 2xx (incluido `charged: false`),
  un 3xx o un 4xx **nunca** se reintentan. Sin pedido hecho (URL bloqueada, secreto o variable faltante, herramienta
  borrada o editada después a `code` o `GET`): `failed` sin llamar a nada. Cada intento tiene tope de 150 s y el claim
  es condicional, así que dos retomas no corren a la vez.
- **Cuándo se arma.** Por voz, `handoff_accepted`: al marcar 1 la persona y conectarse; `always`: con la llamada
  conectada. `finalize` pasa `armed` a `pending` después de la extracción. Por texto, `handoff_accepted` corre al aceptar el
  operador, **antes de la extracción** (una `{{fields.x}}` va vacía), como paso (b) de la entrega
  ([WHATSAPP.md](WHATSAPP.md#derivación-a-personas-del-equipo)); `always` sin aceptación se arma en la transacción que cierra
  el hilo y pasa a `pending` después de la extracción. No se arma en `prueba`, `loadtest` ni `celular`.
- **Nota para el operador (solo por texto):** si la respuesta es un objeto con `operator_message` de tipo texto no vacío,
  se guarda en `post_call_note` (hasta 1000 caracteres) y va en el mensaje con el contacto. Es lo único de la respuesta que
  se conserva; no se expone en la API ni el MCP. En voz, el operador no oye si se cobró.
- **Límites aceptados:** si `app` muere durante el post-call, la herramienta se vuelve a llamar con la misma clave y evitar
  el doble efecto depende de que la API del cliente la respete; un `kill -9` en ese momento deja al operador leyendo «No se
  pudo confirmar» aunque el cobro haya salido. Un `failed` asíncrono de Meta después de un post-call hecho no lo deshace.
  Con `POST_CALL_WAIT_SECONDS` de 20 o más, el lease de la entrega vence durante una espera sana.

## Flujo de un turno

1. `ConversationTools.turn` (`app/tools/conversation.py`) lee las herramientas del agente de la base en cada turno
   (con las credenciales resueltas), arma el contexto (`call.*` desde `CallRow` o el WhatsApp del que escribe, `fields`,
   `contact`, `vars`, secretos) y devuelve un `TurnTools`.
2. El cliente del LLM (`app/llm/client.py` para OpenAI compatible y vLLM; `app/llm/anthropic_client.py` con
   `tool_use`/`tool_result`) manda `platform_tools.tools_for(state)` + las del cliente en formato OpenAI
   (`schema.openai_tool`: la descripción suma, si `confirm`, "Antes de usarla, confirmá con la persona..." y siempre
   el protocolo `{"ok": true, "data"}`/`{"ok": false, "error"}`), con `tool_choice: auto`, en streaming:
   `delta.content` va al TTS y `delta.tool_calls` se acumulan.
3. Si el modelo pide herramientas del cliente: se dice `messages.start` de la primera que lo tenga (si el modelo no
   habló en esa vuelta), se ejecutan en paralelo, se dice `messages.delayed` si alguna pasa su `after_ms`, y se agregan
   el `assistant` con `tool_calls` y un `tool` por resultado. Se vuelve a llamar al LLM.
4. `messages.failed` lo dice la plataforma por el TTS cuando la herramienta falla (solo voz).
5. Tope: `tool_settings.max_calls_per_turn` cuenta **vueltas** al LLM con herramientas del cliente; al llegar, el
   turno termina con `limit_message` (no se fuerza al modelo a contestar); si en esa vuelta pidió `transfer_call`, la
   derivación se respeta (un `end_call` no).
6. Cada ejecución queda en la traza del mensaje (`Message.llm`: `kind: herramienta`, argumentos, ms, resultado y
   `tool: {slug, type, revision, ok, status, ms}`) y en `tool_runs`.
7. Con un LLM BYOK y respaldo propio: si el proveedor falla después de ejecutar una herramienta, no hay respaldo (la
   repetiría; `app/llm/resolver.py`).
8. Si la persona interrumpe mientras corre una herramienta, la herramienta sigue: el pedido ya salió.

`confirm: true` es solo una frase en la descripción: decide el modelo, no hay confirmación de plataforma.

## API

`app/api/routers/tools.py` (prefijo `/api/v1`). Cliente: las suyas; admin: las de cualquier cliente.

| Ruta | Qué hace |
|---|---|
| `GET /tools/schema` | JSON Schema de la definición (para validar del lado del cliente) |
| `GET /tools/code-template` | la función de ejemplo |
| `GET /tools/status` | `{"code_runner": bool}`: si el sandbox está configurado |
| `GET/POST /clients/{id}/tools` | listar (con `used_by`, última prueba) / crear |
| `GET/PUT/DELETE /clients/{id}/tools/{slug}` | ver / reemplazar (sube `revision`, guarda en `tool_versions`) / borrar (409 si un agente la usa) |
| `GET /clients/{id}/tools/{slug}/versions` | historial |
| `POST /clients/{id}/tools/{slug}/test` | ejecutar con `{args, agent_id?, secrets?, call?}` → `{ok, status, ms, data, error, llm, request, logs, assigned}` (secretos tachados) |
| `POST /clients/{id}/tools/test` | lo mismo con una definición sin guardar (`type`, `definition`) |
| `GET/POST /clients/{id}/secrets`, `PATCH/DELETE /clients/{id}/secrets/{name}` | secretos del cliente |
| `GET/POST /clients/{id}/credentials`, `GET/PUT/DELETE /clients/{id}/credentials/{slug}` | credenciales |
| `GET/POST /agents/{id}/secrets`, `PATCH/DELETE /agents/{id}/secrets/{name}` | valores propios del agente; el GET dice `source` (`agent` \| `client` \| null = falta), `overrides`, `missing`, `used_by` |
| `POST /agents/{id}/secrets/{name}/promote` | pasar al cliente |

- Las pruebas gastan lo mismo que una ejecución real: 30 por minuto por cliente (`rate_limit`). Sin `agent_id` usan
  los secretos del cliente; `agent_id` suma los propios; `secrets` pisa todo y no se guarda.
- Errores de validación con `details[].path` para marcar el campo.

**MCP** (`app/mcp/catalog.py`, `features: ["custom_tools"]`): `list_tools`, `get_tool`, `get_tool_schema`,
`create_tool`, `update_tool`, `delete_tool`, `list_tool_versions`, `test_tool`, `test_tool_draft`,
`list_client_secrets`, `set_client_secret`, `update_client_secret`, `delete_client_secret`, `list_agent_secrets`,
`set_agent_secret`, `update_agent_secret`, `delete_agent_secret`, `promote_agent_secret`, `list_credentials`,
`create_credential`, `update_credential`, `delete_credential`. Los que llevan un valor de secreto lo pasan por el
agente de IA que usa el MCP (lo dice su descripción). Catálogo en [`../MCP_HERRAMIENTAS.md`](../MCP_HERRAMIENTAS.md).

## UI

`web/src/features/tools/`, según [`../DESIGN_GUIDELINE_APP.md`](../DESIGN_GUIDELINE_APP.md).

- **Agentes > Herramientas** (`/tools`, `ToolsPage`): lista (tipo, agentes que la usan, última prueba) y "Nueva":
  "Llamar a una API" o "Escribir código". Bloqueada por plan con `useFeatureLock` (`custom_tools`; `code_tools` para
  código).
- **Editor** (`/tools/new`, `/tools/:slug`, `ToolEditorPage`): HTTP con método, URL y pestañas de parámetros
  (`ParamsEditor`: "lo completa el agente", valor fijo o variable), headers, body, Autenticación (desplegable
  Credencial: ninguna, las del cliente o "Configurada en esta herramienta (avanzado)"; Nueva/Editar credencial en
  `CredentialModal`), respuesta y voz; código con CodeMirror, parámetros, secretos que usa, hosts permitidos y timeout.
  Botón **Variables** (`TemplateInput`) con los secretos y "Nuevo secreto". "Secretos que pide" con Cargado/Falta.
  "Lo que ve el modelo" (esquema generado). **Probar** (`ToolTestPanel`) e historial de versiones (`ToolHistory`).
- **Agentes > Secretos** (`/secrets`, `SecretsPage`): Credenciales y Secretos del cliente (`••••last4`, quién los usa,
  agentes con otro valor, **Falta**).
- **Editor del agente, sección Herramientas** (`web/src/features/agents/`): elegir herramientas, aviso **Falta X**, y
  la tabla de secretos con Del cliente / Propio / Falta, Cargar valor, Usar otro valor acá, Pasar al cliente y Volver
  al del cliente.
- **Editor del agente, sección «Antes y después de la conversación»** (pestaña Herramientas, también con «tu propio
  agente»): elige la herramienta del pre-call, su tiempo máximo de espera, la del post-call y **Cuándo corre**. Solo ofrece
  herramientas con todos sus valores fijos, y avisa si la elegida ya no sirve o si el post-call es `handoff_accepted` y el
  agente no tiene áreas (esa condición nunca se cumple; no mira áreas inactivas ni sin plantilla).
- **Traza** en el chat de prueba y el detalle de la conversación (`web/src/features/calls/ChatView.tsx`): argumentos,
  estado, ms y resultado de cada ejecución.

## Reglas y trampas

- **El LLM propio necesita el parser de herramientas:** `vllm-llm` corre con `--enable-auto-tool-choice
  --tool-call-parser=gemma4` (`docker-compose.gemma4-26b.yml`). Sin ellos un pedido con `tools` da 400, y como
  `end_call` va siempre, **todo agente** da 400. Si se cambia de modelo, el parser tiene que ser el suyo.
- Un proveedor BYOK tiene que soportar `tools` (ver [LLM_CONEXIONES.md](LLM_CONEXIONES.md)).
- Un turno con herramienta son 2 o más pedidos al LLM, con más contexto. Con Gemma el KV cache es de 49.082 tokens
  para todas las llamadas y la capacidad no está medida.
- Sandbox medido (26-oct-2026): una función simple ~25 ms; bucle infinito cortado en el timeout; 64 MB de heap; sin
  acceso a archivos, variables, subprocesos ni imports remotos; host no declarado bloqueado por Deno; `localtest.me` y
  metadata por DNS, 407 del proxy.
- `eval-tools` corrido desde el host no ve el muestreo del override de Gemma (`LLM_TEMPERATURE=1.0`, `LLM_TOP_P=0.95`,
  `LLM_TOP_K=64`, solo en los contenedores): para comparar con producción, pasarlas en el entorno.
- Privacidad: los datos de la conversación que use una herramienta salen hacia los endpoints que configura el
  cliente; él es responsable del destino (condiciones `2026-10-28`, "sistemas conectados").
- Backup: herramientas, secretos y credenciales están en la base (cifrados), ya cubiertos.

## Desplegar y probar

- Sandbox: `make tools-runner-token` (agrega `TOOLS_RUNNER_TOKEN` al `.env`; revisar el diff enmascarado) y
  `make up-tools` (`tools-runner` y `tools-egress`; no corta llamadas). Recrear `app` y `agent` para que lo lean:
  `make calls-active && make up-agent`.
- Migraciones: `make migrate-test` antes de `make migrate`.
- `make test`: `tests/test_tools_http.py`, `test_tools_api.py`, `test_tools_secrets.py`, `test_motor_tools.py`,
  `test_platform_tools.py`, `test_workflows.py` (workflows) y `test_voice_wiring.py` (el worker), con LLM falso.
- `make test-tools-code`: `tests/test_tools_code.py` contra un sandbox de prueba aislado (`scripts/tools/runner_test.sh`,
  lo levanta y lo baja; `make tools-runner-test` lo deja arriba).
- `make e2e-tools`: `tests/test_tools_e2e.py`, todo por la API y por el MCP con LLM falso, la API falsa
  (`scripts/tools/mock_api.py`, exige Bearer y verifica la firma) y el sandbox de prueba. Bloquea si se rompe el código.
- `make eval-tools LLM=local|openrouter REPS=3`: LLM real, agente `app/agents/reference/eval_tools.json`, 15
  escenarios (`scripts/tools/eval.py`), reporte en `scratch/tools-eval/`. Solo informa (termina en 0).
- `make web-check` para la UI; `make mcp-docs` al tocar el catálogo.

## Pendientes

- `make eval-tools LLM=local REPS=3` con el LLM propio y su `EVAL-NNN` (las tasas anteriores no valen: eran con
  reglas de prompt que ya no existen).
- Un CAP con un perfil que use herramientas, antes de ofrecerlas en voz con tráfico.
- Una llamada real con cada tipo de herramienta por un número propio (cuánto agrega a la respuesta y que la frase de
  inicio suene antes del silencio).
- La política de privacidad no nombra las herramientas: solo las condiciones las cubren como "sistemas conectados".
- UI: aviso de cambios sin guardar en el editor de herramientas.
