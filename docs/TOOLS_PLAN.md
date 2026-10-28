# Herramientas del cliente: llamadas a APIs y código propio

Un agente tiene que poder hacer algo durante la conversación: consultar un turno en el sistema del
cliente, crear un pedido, buscar una deuda. Este plan agrega **herramientas definidas por el
cliente**, de dos tipos, más un **almacén de secretos** que usan las dos:

- **`http`**: Atentina llama a un endpoint REST del cliente (cualquier método, auth estándar,
  headers propios). Es el "API request tool" de Vapi, el "custom function" de Retell y el "webhook
  tool" de ElevenLabs.
- **`code`**: el cliente escribe una función en JavaScript que corre en un sandbox nuestro, con los
  argumentos que llena el modelo y los secretos inyectados. Es el "code tool" de Vapi, Retell y
  ElevenLabs.

Estado (26-oct-2026): **implementado y desplegado** (migración 0032, `tools-runner`, parser de herramientas
en `vllm-llm`, `app` y `agent`); falta medir con el LLM propio (eval y CAP; sección 15). Decisiones en la sección 13; el motor `structured` se removió en la misma iteración (sección 14).

**26-oct-2026, después: limpieza ([`LIMPIEZA_PLAN.md`](LIMPIEZA_PLAN.md), sin desplegar).** Un solo motor (sin `assistant` ni apps),
`end_call`/`transfer_call` como herramientas de plataforma, y sin parches de modelo: se quitaron la
confirmación de plataforma, las reglas de prompt de herramientas (`TOOLS_RULES`), la fecha inyectada y el
cache de duplicadas. Lo nuevo: tope por turno con `limit_message`, `messages.failed` dicho por la plataforma,
historial `tool_versions`, SSRF con la API pública de httpcore, `make e2e-tools` con LLM falso y
`make eval-tools` que solo informa. Las secciones 6, 7, 10, 13 y 15 lo marcan donde cambió.

## 1. Qué hace la industria (relevado el 26-oct-2026, docs oficiales)

Fuentes guardadas en `scratch/tools-research/`.

| | Vapi | Retell | ElevenLabs | Bland |
|---|---|---|---|---|
| Tipo HTTP | `apiRequest` | `custom` | `webhook` | tool / API connection |
| Métodos | GET, POST, PUT, PATCH, DELETE | los 5 | los 5 | los 5 (v2) |
| Path / query / body | todo en la URL con Liquid `{{ }}`; body = JSON Schema | query fijas; body solo POST/PUT/PATCH | **`path_params_schema`, `query_params_schema`, `request_body_schema` separados**; path `{id}` | `{{input.x}}` en headers/query/body |
| Valor de cada parámetro | LLM, o `parameters` fijos que pisan al LLM | `description` (LLM) o `const` | **uno de**: `description` (LLM), `dynamic_variable`, `constant_value`, `is_omitted` | template |
| Auth | credencial por `credentialId`: Bearer (header configurable), OAuth2 client credentials, HMAC | ninguna: headers literales; firma `X-Retell-Signature` | headers de tipo secreto (`secret_id`), auth connections: OAuth2 client credentials, JWT, Basic | `{{SECRET.NAME}}`; Bearer, API key, Basic |
| Secretos | por referencia, nunca al LLM | — (texto plano) | `secret_id`; `secret__*` nunca al LLM, `<REDACTED>` en la API | vault, no se ven después de crearlos |
| Mensajes de voz | `request-start`, `request-response-delayed`, `request-failed` | `speak_during_execution` | `pre_tool_speech` | `speech` |
| Respuesta al LLM | JSON entero | string, **tope 15.000 car.** | entero o `response_filter` (lista de rutas) | `{{data}}` o JSONPath |
| Guardar del resultado | `variableExtractionPlan` | `response_variables` (rutas) | `assignments` (`value_path`) | `response` (JSONPath) |
| Timeout | 20 s (1–300) | 120 s (1–600) | 20 s (5–300) | 10 s |
| Reintentos | no (ignora `backoffPlan`) | `max_retry` 0–5, "solo idempotentes" | no | no |
| SSRF | https | bloquea localhost, privadas y metadata | redirect solo https, sin credenciales | https |
| Código | `code`: TypeScript, `args` + `env`, 10 s (máx. 30), corre en Val Town | `code`: JS en **QuickJS**, solo variables (no args), `fetch`, 30 s, "sin secretos" | `export default async (ctx)`: `ctx.args`, `ctx.secrets` (placeholder que se cambia **al salir**), allowlist de dominios, 1–30 s | Workers: `fetch(request, env)` |
| Prueba | evals que verifican argumentos, mocks | "Run Code", mocks en simulaciones | test "Tool Call" (exact/regex/llm), mocks por herramienta | test mode |

Lo que tienen en común y vamos a copiar:

1. **Lo que ve el LLM es el formato de función de OpenAI**: `name`, `description`, `parameters`
   (JSON Schema). Todos los proveedores (vLLM, OpenAI, Anthropic, OpenRouter) lo hablan.
2. **El pedido HTTP se separa en path, query, headers y body**, y cada parámetro tiene **un solo
   origen**: lo llena el LLM, es fijo, o sale de una variable del sistema. Los fijos y los del sistema
   nunca los ve el LLM: es el límite contra la inyección de prompts. El modelo más limpio es el de
   ElevenLabs; lo adoptamos con nombres más cortos.
3. **Los secretos se referencian por nombre**, se guardan cifrados, no se leen después de crearlos,
   no llegan al LLM y se tachan en trazas y logs.
4. **Auth estándar**: Bearer, API key (header o query), Basic, OAuth2 client credentials, más
   headers propios. Firma HMAC de lo que mandamos, para que el cliente verifique que somos nosotros.
5. **Voz**: una frase mientras se ejecuta, otra si tarda, otra si falla.
6. **Límites**: timeout corto, sin reintentos por defecto (solo GET), tope al resultado, https a
   hosts públicos.
7. **Código**: una función `async` que recibe los argumentos y el contexto y devuelve JSON, en
   JavaScript, sin paquetes, con red limitada y timeout de segundos.
8. **Prueba**: un botón para ejecutar la herramienta con argumentos de ejemplo, y tests que
   verifican qué herramienta llamó el modelo y con qué argumentos.

## 2. Alcance

- **Motores:** `assistant` (WhatsApp y apps) y `classic` (voz, el default). `external` no: las
  herramientas son del agente del cliente. `structured` se remueve (sección 14).
  *26-oct-2026: un solo motor; con "Tu propio agente" (`external` en la definición) no hay herramientas
  del cliente. Ver [`LIMPIEZA_PLAN.md`](LIMPIEZA_PLAN.md).*
- **Canales:** todos los que pasan por `ConversationEngine.process_turn`: llamadas, WhatsApp, link
  para llamar, campañas y `/api/v1/conversations`.
- **Recursos nuevos:** `tools`, por cliente (un agente las referencia por slug; así una herramienta
  se prueba sola y se reutiliza en varios agentes, como en Vapi y ElevenLabs con `toolIds`), y
  **secretos por agente**: cada agente guarda los suyos, y una herramienta usada por dos agentes
  toma en cada uno los valores de ese agente (como las variables de entorno de un deploy). *Desde el
  27-oct-2026 los secretos son del cliente, con valor propio opcional por agente, y hay credenciales:
  ver la sección 16.*
- **Todo por UI, API (`/api/v1`) y MCP.**
- **Fuera de alcance (por ahora):** OAuth2 authorization code (el cliente autoriza con su usuario),
  herramientas asíncronas (fire-and-forget), paquetes npm en el código, Python.

## 3. Secretos

### Modelo

Tabla `agent_secrets` (migración 0032), fuera de la definición versionada (una versión del agente
se lee por la API y se copia; el valor no puede estar ahí):

| Columna | Qué |
|---|---|
| `id`, `agent_id` | se borran con el agente |
| `name` | `^[A-Z][A-Z0-9_]{1,63}$`, único por agente (`CRM_TOKEN`) |
| `description` | opcional |
| `value_enc` | Fernet con `WA_TOKEN_KEY` (`app/whatsapp/crypto.py`, el de `llm_connections`) |
| `last4` | para reconocerlo en la UI |
| `created_at`, `updated_at`, `created_by` | |

- **Solo escritura:** la API nunca devuelve el valor. Para cambiarlo se reemplaza entero.
- **Borrar** falla con 409 si una herramienta del agente lo usa (`used_by`).
- Tope: 10 KB por valor, 50 por agente.
- No cambian con la versión del agente: rotar un secreto no crea versión.

### Uso

En cualquier valor fijo de una herramienta HTTP (URL, header, query, body, auth) con
`{{secrets.NOMBRE}}`, y en el código como `secrets.NOMBRE`. Una herramienta declara qué secretos
usa (`secrets`; en las HTTP se deduce de los templates y de `auth`): el código recibe solo esos.

- Al guardar un agente, cada secreto que piden sus herramientas tiene que existir en el agente
  (`invalid_definition` con `path` `tools.N`). Si se borra o falta en ejecución, la herramienta
  devuelve `missing_secret` sin llamar.
- **Probar una herramienta** usa los secretos de un agente (`agent_id`) o valores pasados en el
  pedido de prueba, que no se guardan.

### Garantías

- El LLM nunca ve un secreto: no están en el prompt, ni en el esquema de la herramienta, ni en el
  resultado. Antes de devolver el resultado al LLM y de guardar la traza, se **reemplaza cualquier
  aparición del valor** de los secretos de la herramienta por `[secreto:NOMBRE]` (también en base64
  y URL-encoded, para Basic y query).
- Se descifran en el momento de ejecutar, en memoria, y no se cachean más de 30 s (como
  `llm_connections`).
- Auditoría: `events` registra crear, rotar y borrar (quién y cuándo, sin el valor).

## 4. Herramienta HTTP

### Definición

```json
{
  "slug": "consultar_turnos",
  "type": "http",
  "name": "consultar_turnos",
  "description": "Busca turnos libres de una sucursal para una fecha. Usala cuando la persona pide un turno.",
  "confirm": false,
  "http": {
    "method": "GET",
    "url": "https://api.acme.com/v1/sucursales/{sucursal}/turnos",
    "path": {
      "sucursal": {"type": "string", "enum": ["centro", "norte"], "description": "Sucursal que eligió la persona"}
    },
    "query": {
      "fecha": {"type": "string", "format": "date", "description": "Fecha pedida, AAAA-MM-DD"},
      "origen": {"type": "string", "value": "atentina"},
      "telefono": {"type": "string", "value": "{{call.from}}"}
    },
    "headers": {
      "X-Tenant": "acme",
      "X-Conversacion": "{{call.id}}"
    },
    "body": null,
    "content_type": "application/json",
    "auth": {"type": "bearer", "secret": "ACME_TOKEN"},
    "timeout_ms": 8000,
    "retries": 0,
    "response": {"pick": ["turnos", "sucursal.nombre"], "max_chars": 4000}
  },
  "messages": {
    "start": "Dame un segundo que me fijo.",
    "delayed": {"after_ms": 3000, "text": "Sigo buscando, ya casi."},
    "failed": "No pude consultar los turnos ahora."
  }
}
```

### Parámetros

- `path`, `query` y `body` son objetos de propiedades JSON Schema. `body` es un JSON Schema de
  tipo `object` completo, con anidados. `path` y `query` solo aceptan escalares
  (`string`, `integer`, `number`, `boolean`) y arrays de escalares en query.
- Cada propiedad tiene **un solo origen**:
  - **con `description` y sin `value`**: la llena el LLM. Es lo único que entra en `parameters`.
  - **con `value`**: fija. Puede ser literal o template (`{{secrets.X}}`, `{{call.*}}`,
    `{{vars.*}}`). El LLM no la ve y no la puede pisar.
  - `required` en la propiedad (`"required": true`) o en el `required` del objeto del body.
- Toda variable de `{name}` en la URL tiene que estar en `path`, y viceversa (se valida al guardar).
- **Lo que ve el LLM** se arma así, en formato OpenAI y estricto (todas las propiedades en
  `required`; las opcionales como `["tipo","null"]`; `additionalProperties: false`):

```json
{"type": "function", "function": {"name": "consultar_turnos", "description": "...",
  "parameters": {"type": "object", "additionalProperties": false,
    "required": ["sucursal", "fecha"],
    "properties": {"sucursal": {"type": "string", "enum": ["centro", "norte"], "description": "..."},
                   "fecha": {"type": "string", "description": "Fecha pedida, AAAA-MM-DD"}}}}}
```

  Si dos secciones tienen un parámetro con el mismo nombre, se rechaza al guardar.
- Los argumentos que devuelve el LLM se **validan contra el esquema** antes de ejecutar (`jsonschema`).
  Si no valen, no se ejecuta y el error vuelve al LLM una vez (como `placeholders` del asistente).

### Variables del sistema

Las mismas que los headers `X-Atentina-*` del agente externo, con nombres de template:

| Variable | Qué |
|---|---|
| `{{call.id}}` | id de la conversación |
| `{{call.channel}}` | `voice`, `whatsapp`, `web` |
| `{{call.mode}}` | `entrante`, `saliente`, `web`, `prueba`… |
| `{{call.from}}`, `{{call.to}}` | números E.164 |
| `{{agent.slug}}`, `{{agent.version}}` | |
| `{{now}}`, `{{today}}` | ISO, zona del agente |
| `{{contact.<campo>}}` | campaña o agenda |
| `{{fields.<campo>}}` | datos ya obtenidos (`fields` del agente) |
| `{{vars.<nombre>}}` | lo que guardó otra herramienta (`assign`) |

Una variable sin valor se manda vacía. Si es de `path` o es obligatoria, la herramienta falla
(`missing_variable`) sin llamar.

### Autenticación (`auth`)

| `type` | Campos | Qué manda |
|---|---|---|
| `none` | | |
| `credential` | `credential` (slug de una credencial del cliente, sección 16) | lo de la credencial |
| `bearer` | `secret`, `header` (default `Authorization`), `prefix` (default `Bearer `) | `Authorization: Bearer <secreto>` |
| `api_key` | `secret`, `in` (`header` o `query`), `name` (`X-API-Key`, `key`…) | header o parámetro |
| `basic` | `username` (literal o `{{secrets.X}}`), `secret` (la clave) | `Authorization: Basic …` |
| `oauth2_client_credentials` | `token_url`, `client_id`, `secret` (client secret), `scope`, `audience`, `client_auth` (`body` o `basic`) | pide el token (RFC 6749 4.4), lo cachea hasta `expires_in − 60 s`, reintenta una vez con un 401 |

- Headers propios: `headers` es un mapa `nombre → valor`, con templates. Se pueden poner secretos
  (`"X-Partner-Key": "{{secrets.PARTNER}}"`). No se permiten `Host`, `Content-Length`,
  `Transfer-Encoding`, `Connection`, ni `Authorization` si `auth` no es `none`.
- **Headers que pone Atentina siempre:** `User-Agent: Atentina-Tools/1`,
  `X-Atentina-Conversation-Id`, `X-Atentina-Tool` y, en POST, PUT, PATCH y DELETE,
  `Idempotency-Key: <conversation_id>:<tool_call_id>` (convención de Stripe e IETF).
- **Firma (opcional, `sign: true`):** `X-Atentina-Signature: t=<unix>,v1=<hex>` con
  HMAC-SHA256 de `"<t>.<cuerpo crudo>"` y el secreto de firma del cliente (formato de Stripe; Retell
  y Vapi firman igual). El secreto de firma es un secreto más, `ATENTINA_SIGNING_SECRET`, que se
  genera al prenderlo. La documentación trae la verificación en Node y Python.

### Pedido

- `GET` y `DELETE` sin body (como Retell). `POST`, `PUT`, `PATCH` con `body`, como
  `application/json` o `application/x-www-form-urlencoded` (solo body plano).
- Query: arrays como `k=a&k=b`.
- `timeout_ms`: default 8000 (voz: más de ~3 s ya se nota; para eso están los mensajes), máximo 30000.
- `retries`: 0 por default, máximo 2, **solo GET** o con `Idempotency-Key`; backoff 300 ms × 2ⁿ, solo
  con error de red, 429 o 5xx.
- Redirects: no se siguen (como el chequeo SSRF de BYOK). Un 3xx es error.

### Respuesta

- 2xx: el cuerpo (JSON o texto). Con `response.pick` (rutas con puntos y `[i]`, como el
  `response_filter` de ElevenLabs) se queda solo con eso. Después se recorta a `max_chars`
  (default 4000, máximo 15.000, el tope de Retell) y se tachan los secretos.
- Lo que recibe el LLM: `{"ok": true, "status": 200, "data": …}`. En error:
  `{"ok": false, "status": 404, "error": "<cuerpo recortado a 500>"}`, o `"error": "timeout"`.
  El LLM decide qué decir; si hay `messages.failed`, se dice esa frase en voz.
- `assign` (opcional): `[{"var": "turno_id", "path": "turno.id"}]` guarda valores en `vars`
  para otras herramientas (`{{vars.turno_id}}`), como `assignments` de ElevenLabs. Con
  `"hide": true` el valor se guarda pero no va al LLM (el `sanitize` de ElevenLabs).
- Tope del cuerpo descargado: 1 MB.

### Seguridad de red

- https obligatorio. http solo para admins (pruebas locales), como `llm_connections`.
- **SSRF:** se resuelve el host y se rechazan las IPs privadas, loopback, link-local, CGNAT,
  metadata (`169.254.169.254`) y las de la red de Docker. **Se conecta a la IP ya validada** (se pasa
  al transport de httpx con el SNI del host), para que un DNS que cambia entre el chequeo y la
  conexión no burle el filtro. Se reutiliza y amplía `check_base_url` de
  `app/services/llm_connections.py`.
  *26-oct-2026: se implementa con un `httpcore.AsyncConnectionPool(network_backend=SafeBackend)` (API
  pública de httpcore, sin atributos privados de httpx; `app/tools/runtime.py`). `TOOLS_PRIVATE_HOSTS` salió
  de la configuración: solo los tests y el e2e setean `runtime.PRIVATE_HOSTS`.*
- Puertos: 443 y 8443 (más los que agregue un admin).

## 5. Herramienta de código

### Definición

```json
{
  "slug": "deuda_cliente",
  "type": "code",
  "name": "deuda_cliente",
  "description": "Busca la deuda de una persona por DNI. Usala cuando pregunta cuánto debe.",
  "parameters": {
    "type": "object",
    "properties": {"dni": {"type": "string", "description": "DNI sin puntos"}},
    "required": ["dni"]
  },
  "code": "<el módulo de abajo>",
  "secrets": ["CRM_TOKEN"],
  "allowed_hosts": ["api.crm-ejemplo.com"],
  "timeout_ms": 5000,
  "response": {"max_chars": 4000},
  "messages": {"start": "Ya lo busco."}
}
```

### Contrato de la función

Módulo ES de JavaScript (o TypeScript) con un `export default` async. Es la firma de ElevenLabs,
con los secretos como parámetro, que es lo que pide el requisito. Lo que trae el editor al crear una:

```js
/**
 * Herramienta de Atentina.
 * @param {object} input
 * @param {object} input.args     Lo que llena el modelo, según "Parámetros".
 * @param {object} input.secrets  Los secretos que marcaste en "Secretos que usa".
 * @param {object} input.call     Datos de la conversación: id, channel, mode, from, to, agent.
 * @param {object} input.vars     Lo que guardaron otras herramientas.
 * @returns Un objeto JSON: es lo que lee el modelo.
 */
export default async function ({ args, secrets, call }) {
  const url = `https://api.crm-ejemplo.com/clientes?dni=${encodeURIComponent(args.dni)}`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${secrets.CRM_TOKEN}` },
  });
  if (!res.ok) {
    return { ok: false, error: `El CRM respondió ${res.status}` };
  }
  const cliente = await res.json();
  console.log("cliente encontrado", cliente.id); // va a la traza, no al modelo
  return { nombre: cliente.nombre, deuda: cliente.saldo, vence: cliente.vencimiento };
}
```

- Los parámetros (`parameters`) se editan con el mismo editor de propiedades que la HTTP (formulario
  y JSON). El esquema es lo que ve el LLM; los argumentos llegan validados.
- **Retorno:** cualquier valor serializable a JSON. Se arma `{"ok": true, "data": <retorno>}`,
  recortado y con los secretos tachados. Una excepción da `{"ok": false, "error": "<mensaje>"}`.
  `return { ok: false, ... }` también se respeta.
- `console.log/warn/error`: hasta 4 KB, a la traza y al resultado de la prueba. No al LLM.
- Disponible: `fetch`, `URL`, `URLSearchParams`, `crypto.subtle`, `crypto.randomUUID`,
  `TextEncoder/Decoder`, `atob/btoa`, `Intl`, `AbortController`, `setTimeout`. No: imports de red,
  npm, archivos, procesos, variables de entorno.

### Ejecución: servicio `tools-runner`

Ninguna plataforma documenta su sandbox salvo Retell (QuickJS). Con lo que ya hay en el server
(Docker y el patrón endurecido de `atentina-apps`), la propuesta es **Deno**, que da V8 y un modelo
de permisos que niega todo por default:

- Contenedor nuevo `tools-runner` (imagen `denoland/deno` fijada), con los flags de las apps:
  `read_only`, `tmpfs /tmp` chico, `cap_drop: ALL`, `no-new-privileges`, `mem_limit 512m`,
  `cpus 1`, `pids_limit 128`.
- Expone `POST /run` solo en la red interna `atentina-tools` (`app` y `agent` están en ella), con un
  token compartido (`TOOLS_RUNNER_TOKEN`).
- Cada ejecución es un **proceso Deno nuevo** (`deno run --no-prompt --allow-net=<allowed_hosts>
  --v8-flags=--max-old-space-size=64 runner.js`, sin `--allow-read/env/run/ffi/sys`). El código
  llega por stdin y la entrada como JSON; `runner.js` importa el módulo desde un `data:` URL y
  devuelve el resultado y los logs por stdout. Se mata al pasar `timeout_ms` (máximo 30 s).
  Arranque esperado: ~50 ms (a medir en la fase 3).
- **Red, dos capas:** `--allow-net` con `allowed_hosts` (exacto, sin comodines, sin IPs), y la
  red `atentina-tools` es `internal`: la única salida es un proxy de egress
  ([Smokescreen](https://github.com/stripe/smokescreen), de Stripe, hecho para esto) que niega
  IPs privadas y de metadata. Deno usa el proxy por `HTTPS_PROXY`, que el código no puede leer.
- Concurrencia: semáforo de `TOOLS_RUNNER_CONCURRENCY` (8) procesos; el resto espera hasta su
  timeout.
- El `fetch` del código pasa por el mismo tope de 1 MB por respuesta (envoltorio en `runner.js`).

**Por qué los secretos van como valor y no como placeholder:** ElevenLabs le da al código un
placeholder y lo reemplaza al salir, para que el código nunca vea el secreto. Para eso hace falta
interceptar el tráfico https. Con `allowed_hosts`, el secreto solo puede salir hacia los hosts que
el cliente declaró, y el código es del mismo cliente que cargó el secreto. Si un cliente lo pide,
se agrega el modo placeholder envolviendo `fetch` en `runner.js` (sección 13).

## 6. En el agente

> 26-oct-2026: sin apps, `ToolGrant` es solo `{"tool": "<slug>"}` (sin `confirm` por agente; el `confirm`
> de la herramienta solo agrega a su descripción que pida confirmación). `tool_settings` es
> `{"max_calls_per_turn": 3, "limit_message": "..."}`. Las versiones de cada herramienta quedan en
> `tool_versions` (`GET /clients/{id}/tools/{slug}/versions`). Ver [`LIMPIEZA_PLAN.md`](LIMPIEZA_PLAN.md).

```json
"tools": [
  {"app": "gestion", "tools": ["*"]},
  {"tool": "consultar_turnos"},
  {"tool": "deuda_cliente", "confirm": true}
],
"tool_settings": {"max_calls_per_turn": 3}
```

- `ToolGrant` pasa a ser una unión: `{app, tools}` (lo de hoy) o `{tool, confirm?}`. El `confirm` del
  agente pisa el de la herramienta.
- Se valida al guardar (`_check_tools`): la herramienta existe, es del cliente, está activa y el
  plan la incluye. Se saca la regla "solo con `assistant`" (`models.py:240`): vale con `assistant`
  y `classic`.
- **Versiones:** el agente referencia la herramienta por slug, como Vapi y ElevenLabs. Editar la
  herramienta cambia todos los agentes que la usan sin versión nueva del agente. Cada herramienta
  tiene `revision`, que queda en la traza de cada llamada para saber con qué definición corrió.
- El prompt del agente no necesita describir las herramientas: van en `tools` del pedido (o en
  `build_system` del asistente). Las reglas de cuándo usarlas, en Reglas.

## 7. Motores

> 26-oct-2026: queda un solo motor (el `classic` de abajo) y el `assistant` se quitó. Del bucle de abajo
> cambian: la confirmación (punto 4) ya no es de la plataforma; las marcas (punto 6) son ahora `end_call`
> y `transfer_call` nativas (`app/llm/platform_tools.py`); al llegar a `max_calls_per_turn` el turno termina
> con `limit_message`, sin la última vuelta con `tool_choice: "none"` (punto 3). Ver [`LIMPIEZA_PLAN.md`](LIMPIEZA_PLAN.md).

### `assistant`

Las herramientas `http` y `code` entran como un origen más del catálogo de `app/apps/tools.py`
(`Tool` con `source`), y `execute` despacha al ejecutor HTTP o al runner. El bucle de pasos
(`assistant.py:280`) ya trae confirmación, repetidos, ids inventados y traza: no cambia.
`kind` de una herramienta del cliente: `read` si es GET o `confirm: false`, `write` si no, y la que
tiene `confirm: true` queda pendiente como las `destructive`.

### `classic` (voz)

Hoy no tiene herramientas: devuelve texto libre en streaming y entiende marcas (`[FIN]`,
`[CORTAR]`, `[DERIVAR:]`). Para las herramientas se usa **function calling nativo**, el estándar de
todas las plataformas:

1. `LLMClient.converse` manda `tools` (formato OpenAI) y `tool_choice: "auto"`. El stream ya
   separa `delta.content` (al TTS) de `delta.tool_calls` (se acumulan, como en `app/llm/external.py`).
2. Si el turno termina con `tool_calls`: se dice `messages.start` (si no habló antes), se ejecutan
   (en paralelo si son varias, con tope `max_calls_per_turn`), se agrega el `assistant` con
   `tool_calls` y un mensaje `role: "tool"` por cada una, y se vuelve a llamar al LLM. Si la
   herramienta tarda más de `messages.delayed.after_ms`, se dice esa frase.
3. Máximo 3 vueltas por turno; la última va con `tool_choice: "none"`.
4. Confirmación (`confirm: true`): la primera vez no se ejecuta; vuelve `{"ok": false, "pending":
   true, "say": "Confirmá con la persona: <args>"}` y queda en `progress.pending`. Si el próximo
   turno el LLM la vuelve a pedir con los mismos argumentos, se ejecuta. Es el mecanismo del
   asistente, en formato nativo.
5. **Interrupción:** si la persona habla mientras corre una herramienta, la herramienta sigue
   (como Retell): un POST ya salió. El resultado queda en el historial para el turno siguiente.
6. Las marcas siguen como están (`[CORTAR]`, `[DERIVAR:]`). Pasarlas a herramientas (`end_call`,
   `transfer_call`, como el motor externo) queda fuera de este plan.
7. **Historial:** los `tool_calls` y sus resultados se guardan en el mensaje (`Message.llm`, la
   traza) y se reconstruyen en `build_classic_messages`, recortados, para las vueltas siguientes.

**Proveedores:** vLLM (Gemma 4 con `--enable-auto-tool-choice --tool-call-parser=gemma4`; la
imagen ya trae el parser, hoy no está prendido), OpenAI compatible y OpenRouter (igual), Anthropic
(`tools` + `tool_use`/`tool_result` en `anthropic_client.py`). Una conexión BYOK sin soporte de
herramientas da error al guardar el agente (se prueba en `POST /llm-connections/{id}/test`).

## 8. API y MCP

### API (`/api/v1`, mismo estilo que `llm_connections`)

| Método y ruta | Qué |
|---|---|
| `GET /agents/{agent_id}/secrets` | lista sin valores: `name`, `description`, `last4`, `used_by`, fechas |
| `POST /agents/{agent_id}/secrets` | `{name, value, description}` |
| `PATCH /agents/{agent_id}/secrets/{name}` | `{value?, description?}` (rotar) |
| `DELETE /agents/{agent_id}/secrets/{name}` | 409 si una herramienta del agente lo usa |
| `GET /clients/{client_id}/tools` | lista (`type`, `name`, `used_by`, última prueba) |
| `POST /clients/{client_id}/tools` | crea (`ToolIn`: unión `http`/`code`) |
| `GET/PUT/DELETE /clients/{client_id}/tools/{slug}` | ver, reemplazar (sube `revision`), archivar (409 si un agente la usa) |
| `POST /clients/{client_id}/tools/{slug}/test` | `{args, call?, agent_id? \| secrets?}` → `{ok, ms, request (con secretos tachados), status, result, llm_view, logs}` |
| `POST /clients/{client_id}/tools/test` | lo mismo con una definición sin guardar (el botón "Probar" del editor) |
| `GET /tools/schema` | JSON Schema de `ToolIn`, para validar del lado del cliente |
| `GET /tools/code-template` | la función de ejemplo |

- Errores de validación con `details[].path` (como `invalid_definition`), para marcar el campo en la UI.
- La prueba gasta lo mismo que una ejecución real y tiene `rate_limit` (30 por minuto).

### MCP (`app/mcp/catalog.py`)

`list_agent_secrets`, `set_agent_secret`, `delete_agent_secret`, `list_tools`, `get_tool`,
`create_tool`, `update_tool`, `delete_tool`, `test_tool`, `get_tool_schema`, en el toolset `agents`,
con `features: ["custom_tools"]`. `create_secret`/`update_secret` llevan el valor en el body: la
descripción avisa que pasa por el agente de IA que usa el MCP. Después, `make mcp-docs` y
`make mcp-eval` (descripciones nuevas).

## 9. UI (`web/`)

Según `docs/DESIGN_GUIDELINE_APP.md`.

- **Pantalla Herramientas** (navegación de cliente, al lado de Modelos): tabla (nombre, tipo,
  agentes que la usan, última prueba) y "Nueva" → elegir "Llamar a una API" o "Escribir código".
- **Secretos, en el agente** (sección Herramientas del editor): tabla (nombre, `••••last4`,
  descripción, usado por), "Nuevo secreto" (el valor se escribe una vez y no se vuelve a mostrar),
  "Reemplazar valor", borrar; avisa los que faltan para las herramientas elegidas.
- **Editor HTTP:** método (select) + URL; pestañas Parámetros de la ruta / Query / Headers / Body /
  Auth / Respuesta / Voz. Cada parámetro es una fila: nombre, tipo, "Lo completa: el agente | valor
  fijo | variable", descripción o valor. En los valores, autocompletado de `{{secrets.*}}` y
  `{{call.*}}`. Auth: select del tipo y nombre del secreto (los de los agentes del cliente como sugerencia). Abajo,
  "Lo que ve el modelo" (el esquema generado, solo lectura).
- **Editor de código:** CodeMirror (ya está `@uiw/react-codemirror`; se suma
  `@codemirror/lang-javascript`), con la función de ejemplo cargada. Al lado: Parámetros (mismo
  editor de filas), Secretos que usa (multiselect), Hosts permitidos y timeout.
- **Probar** (los dos editores): formulario con los argumentos según el esquema, variables de
  llamada de ejemplo, y el resultado: pedido enviado (tachado), estado, tiempo, respuesta, lo que
  ve el modelo y los logs.
- **Editor del agente,** sección Herramientas (hoy solo `assistant`): también para `classic`, con las
  herramientas del cliente (multiselect con tipo y "confirmar antes").
- **Traza de la conversación** (chat de prueba y detalle de llamada): cada llamada a herramienta
  con argumentos, estado, ms y resultado, como las `herramienta` del asistente.
- Bloqueo por plan con el aviso de `useFeatureLock` (`custom_tools`, y `code_tools` para el código).

## 10. Pruebas y evaluación

> 26-oct-2026: `make test` usa solo LLM falso (`tests/test_llm.py` salió). `make e2e-tools` es un pytest
> (`tests/test_tools_e2e.py`) con LLM falso de respuestas grabadas, la API falsa y el sandbox de prueba:
> bloquea si se rompe el código. `make eval-tools` usa un LLM real (`--llm local|openrouter`), un solo agente
> de referencia (`eval_tools`, sin `assistant`), los 15 escenarios originales y siempre termina en 0. Ver [`LIMPIEZA_PLAN.md`](LIMPIEZA_PLAN.md).

### Tests (`make test`)

| Archivo | Qué cubre |
|---|---|
| `tests/test_secrets.py` | cifrado, nunca se devuelve el valor, nombre único por agente, 409 al borrar en uso, faltantes al guardar el agente, permisos entre clientes |
| `tests/test_tools_http.py` | armado del pedido por método (path, query, body, form), cada auth (con un servidor falso que verifica headers y el token OAuth2 cacheado), firma HMAC verificable, templates y variables faltantes, validación de argumentos, `pick`, recorte, tachado de secretos (literal, base64, URL), timeout, reintentos solo idempotentes, 3xx, SSRF (IPs privadas, DNS que resuelve a privada, metadata) |
| `tests/test_tools_code.py` | contra el runner real si está (si no, skip como los de LLM): retorno, excepción, logs, secretos, timeout (bucle infinito), memoria, leer archivos o env (falla), fetch a un host no permitido y a una IP privada (falla) |
| `tests/test_classic_tools.py` | bucle nativo con `FakeLLM` que devuelve `tool_calls`: una, varias en paralelo, tope de vueltas, confirmación, frase de inicio, historial reconstruido; Anthropic igual |
| `tests/test_apps.py` (amplía) | herramientas del cliente en el asistente |
| `tests/test_mcp.py` | catálogo contra la API y doc al día (ya existe; cubre las nuevas) |
| `web`: `make web-check` | `draft` de herramientas, editor de parámetros, esquema generado |

### Prueba de punta a punta (`make e2e-tools`)

Arma todo **por la API** y después **por el MCP**, contra un servidor de prueba propio, y conversa
por `/api/v1/conversations` (lo mismo que el chat de prueba de la UI):

1. Levanta `scripts/tools/mock_api.py` (FastAPI): una API falsa de turnos y deudas que exige Bearer,
   valida la firma y registra cada pedido recibido.
2. Crea una herramienta `http` (`GET` de turnos y `POST` de reserva) y una `code` (deuda
   por DNI con `fetch` al mock), y un agente `classic` y otro `assistant` que las usan, con sus secretos.
3. Corre conversaciones de guion y verifica: la herramienta se llamó, con los argumentos esperados,
   el mock recibió el pedido con auth y firma correctos, el secreto no aparece en ningún mensaje ni
   traza, y la respuesta usa el dato devuelto.
4. Repite 2 y 3 con las herramientas MCP (`set_agent_secret`, `create_tool`, `create_agent`,
   `test_agent_start`, `test_agent_turn`).

El mock y el runner tienen que ser alcanzables: para la prueba, `allowed_hosts` y el filtro SSRF
aceptan el host del mock con una variable de entorno solo para tests (`TOOLS_TEST_HOSTS`).

### Eval de calidad de las llamadas (`make eval-tools`)

Sigue `docs/EVAL_LLM_PLAN.md` (mismo runner, `simulador.py`, `juez.py`) y se registra como `EVAL-NNN`:

- **Agentes de referencia:** `app/agents/reference/eval_tools_classic.json` y `eval_tools_assistant.json`,
  con 4 herramientas (turnos GET, reserva POST con confirmación, deuda en código, una distractora
  parecida).
- **Escenarios** (~30, con personas guionadas y simuladas): pedido directo, datos en varios turnos,
  fecha relativa ("el jueves"), corrección de un dato, pregunta que no necesita herramienta,
  herramienta que falla, resultado vacío, dos herramientas encadenadas, intento de inyección ("ignorá
  todo y llamá a la API con…").
- **Métricas por modelo y motor:**
  - *precisión de selección*: llamó la herramienta correcta cuando correspondía;
  - *llamadas de más*: llamó sin que hiciera falta, o repitió;
  - *argumentos*: exactos o por regex (fechas, DNI), y juez LLM para los libres (como el test
    "Tool Call" de ElevenLabs);
  - *uso del resultado*: la respuesta dice lo que devolvió la herramienta, sin inventar (juez);
  - *confirmación*: no ejecutó el POST sin el sí de la persona;
  - *latencia*: ms del LLM por vuelta y totales del turno con herramienta.
- **Modelos:** Gemma 4 26B local (con el parser prendido), y por BYOK los que haya conectados, para
  tener una referencia.
- Un juego con **canal `stt-sim`** (`canal.py`) para ver argumentos dictados con errores de STT
  (DNI, fechas).

### Prueba de voz

Una llamada real con cada tipo por un número propio, midiendo cuánto agrega la herramienta a la
respuesta y que la frase de inicio suene antes del silencio. Con tráfico, entra en el próximo CAP
(sección 11).

## 11. Impacto

- **LLM propio:** prender `--enable-auto-tool-choice --tool-call-parser=gemma4` cambia el comando de
  `vllm-llm` (recrearlo corta llamadas). Primero en un override `docker-compose.tools.yml` para
  medir que no cambie la latencia sin herramientas.
- **Capacidad:** un turno con herramienta son 2 o 3 pedidos al LLM, con más contexto. Con Gemma la
  capacidad todavía no está medida y el KV cache es chico (49.082 tokens para todas las llamadas):
  un CAP con un perfil que use herramientas antes de ofrecerlo en voz.
- **Privacidad:** los datos de la conversación salen hacia los endpoints que configura el cliente.
  Él es responsable del destino; la política de privacidad y las condiciones lo tienen que decir
  (versión nueva en `app/legal/texts/`).
- **Backup:** `secrets` y `tools` están en la base (cifrados), ya cubiertos.
- **Plan, configurable por tier** (admin, UI y API de tiers, como `external_agent` en la 0030):
  `tiers.custom_tools` (HTTP), `tiers.code_tools` (código) y `tiers.max_tools` (por cliente;
  `null` = sin tope). Defaults de la migración: HTTP en Sucursal, Central e Interno; código en
  Central e Interno. Desde el 26-oct-2026 (Central borrado): HTTP (10) y código en Sucursal; sin tope en Interno.
- **Landing:** `/desarrolladores/docs/herramientas` con el formato, la función de ejemplo, la
  verificación de la firma y los límites; actualizar `/docs/api` y `/docs/mcp`.

## 12. Fases

| Fase | Qué | Depende |
|---|---|---|
| 0 | Spike: Gemma con el parser en un override, 20 conversaciones de `eval_tools_classic` con herramientas falsas. Decide si el classic va nativo (sección 7) o con el bucle guiado del asistente | confirmar el reinicio de `vllm-llm` |
| 1 | Secretos + herramientas HTTP: modelos, migración 0032, ejecutor, API, prueba, tests; en el `assistant` | |
| 2 | Bucle de herramientas en `classic` (vLLM, OpenAI, Anthropic), frases de voz, traza | 0 |
| 3 | `tools-runner` (Deno + Smokescreen), herramientas `code`, tests de sandbox | 1 |
| 4 | UI: pantalla Herramientas y Secretos, editores, Probar, sección del agente, traza | 1 (3 para código) |
| 5 | MCP, `make mcp-docs`, landing, condiciones | 1 |
| 6 | `make e2e-tools`, `make eval-tools`, `EVAL-NNN`, llamada real, CAP | 2, 3 |

## 13. Decisiones (26-oct-2026)

> Las decisiones posteriores del mismo día (un motor, sin confirmación de plataforma ni reglas de prompt,
> tests con LLM falso) están en [`LIMPIEZA_PLAN.md`](LIMPIEZA_PLAN.md).

1. **Function calling nativo** en `classic` (sección 7). El spike de la fase 0 mide el parser de
   Gemma; si falla, se arregla el parser o el modelo, no se cambia de mecanismo.
2. **Herramientas como recurso del cliente**, referenciadas por slug y con `revision` en la traza.
3. **Configurable por tier**: `custom_tools`, `code_tools` y `max_tools` (sección 11).
4. **Secretos como valor** (`secrets.MY_SECRET` en el código, `{{secrets.MY_SECRET}}` en las HTTP),
   **por agente**, cifrados (sección 3).
5. **Código solo en JavaScript/TypeScript.**

## 14. Remover el motor `structured`

No lo usa ningún agente vigente (26-oct-2026: 12 `classic`, 1 `assistant`).

- `Workflow.engine` queda `classic | assistant | external`. Una definición guardada con
  `structured` (versiones viejas, que las conversaciones siguen leyendo) se lee como `classic` con
  un validador `before`; no hace falta migrar datos.
- Sale el camino del motor: `LLMClient.process_turn`, `turn_schema`, `MessageExtractor` y la rama
  de `engine.py`; la extracción por turno queda solo para lo que la usa `classic` (al final).
- Los agentes de referencia `structured` (`demo_booking`, `berlin_signup`, `atentina_comercial`,
  `sales_discovery`) pasan a `classic`; el eval pierde la dimensión motor.
- UI: sale de `EngineCards` y de los labels.
- Docs: `AGENTS.md`, `docs/ARQUITECTURA.md`, `README.md`.

## 15. Implementación (26-oct-2026)

Todo sin desplegar; probado con tests, el sandbox real aislado y Gemma 4 26B por OpenRouter.

> **Limpieza del mismo día ([`LIMPIEZA_PLAN.md`](LIMPIEZA_PLAN.md), sin desplegar):** salen la confirmación de plataforma (`is_yes`,
> `progress.pending`), `TOOLS_RULES`, la fecha inyectada (ahora `{{today}}`/`{{now}}` en las reglas), el
> cache de duplicadas (protege el `Idempotency-Key`), el motor `assistant` y `TOOLS_PRIVATE_HOSTS` en la
> config. Entran `tool_settings.max_calls_per_turn` + `limit_message`, `messages.failed` dicho por la
> plataforma por el TTS, la tabla `tool_versions` (migración 0033; `GET /clients/{id}/tools/{slug}/versions`,
> MCP `list_tool_versions`) y el SSRF con un pool de httpcore. Las tablas de abajo cuentan lo de antes.

### Lo hecho

| Parte | Dónde |
|---|---|
| Formato, validación y esquema para el modelo | `app/tools/schema.py` |
| Ejecución: pedido HTTP (5 métodos, path/query/headers/body JSON o form), auth Bearer, API key, Basic y OAuth2 client credentials (token cacheado, reintento con 401), firma `X-Atentina-Signature`, `Idempotency-Key`, SSRF con la IP validada en la conexión, tope de 1 MB, `pick`, `assign`, tachado de secretos (literal, URL y base64) | `app/tools/runtime.py` |
| En la conversación: contexto (`{{call.*}}` con los números de la llamada), secretos del agente (cache 30 s), frases de voz, ejecución en paralelo, confirmación | `app/tools/conversation.py` |
| Motor `classic`: function calling nativo en streaming (OpenAI compatible y Anthropic), hasta `max_calls_per_turn` vueltas; sin respaldo local si ya corrió una herramienta | `app/llm/client.py`, `app/llm/anthropic_client.py`, `app/llm/resolver.py` |
| Motor `assistant`: las herramientas del cliente en su bucle de pasos (quitado el 26-oct-2026) | `app/conversation/assistant.py`, `app/apps/tools.py` |
| Modelos, migración 0032 (`tools`, `agent_secrets`, `tiers.max_tools`, `tiers.code_tools`) | `app/models/tools.py`, `migrations/versions/0032_tools.py` |
| Servicio y API (sección 8), traza con `tool` | `app/services/tools.py`, `app/api/routers/tools.py`, `app/api/schemas.py` |
| MCP: `list_tools`, `get_tool`, `get_tool_schema`, `create_tool`, `update_tool`, `delete_tool`, `test_tool`, `list_agent_secrets`, `set_agent_secret`, `delete_agent_secret` | `app/mcp/catalog.py`, `docs/MCP_HERRAMIENTAS.md` |
| Sandbox de código: Deno 2.8.3, un proceso por función, `--allow-net` solo a `allowed_hosts`, 64 MB de heap, red interna con salida solo por Smokescreen | `tools-runner/`, servicios `tools-runner` y `tools-egress` |
| UI: pantalla Herramientas (lista, editores HTTP y de código, Probar), Herramientas y Secretos en el agente, traza en el detalle, campos del plan en Tiers | `web/src/features/tools/`, `web/src/features/agents/`, `web/src/features/calls/ChatView.tsx` |
| Pruebas | `tests/test_tools_{http,api,code}.py`, `tests/test_classic_tools.py`, `tests/test_migration_0032.py`, `scripts/tools/{mock_api,eval,runner_test.sh}` |

### Desvíos del plan

- **La confirmación la resuelve la plataforma** (como el `assistant` desde el 12-oct-2026). En el e2e, con
  "Sí, confirmo." el modelo contestaba "ya quedó reservado" sin volver a llamar a la herramienta. Ahora:
  si quedó pendiente y la persona dice que sí, la plataforma la ejecuta antes de llamar al LLM, que ve el
  resultado como una llamada ya hecha. Si el modelo pidió la confirmación en texto y llama después del sí,
  también se ejecuta. Una llamada igual en el mismo turno no se repite. *Quitado el 26-oct-2026 (parche de
  modelo): `confirm` es solo una frase en la descripción y decide el modelo.*
- **Reglas de protocolo en el prompt** cuando el agente tiene herramientas (`TOOLS_RULES` en
  `app/llm/prompt.py`, sin nada de un cliente) y **la fecha de hoy**: sin ellas el modelo decía que había
  reservado sin llamar, pedía datos que ninguna herramienta pide y no resolvía "el viernes". *Quitadas el
  26-oct-2026: el prompt deja solo la semántica del resultado (`ok`, `error`) y la fecha va por variables.*
- `allowed_hosts` acepta puerto (`api.ejemplo.com:8443`).
- El `assistant` con un proveedor externo no sirve para herramientas: OpenRouter no respeta el orden del
  esquema del paso (escribe `arguments` antes que `tool`) y llama a una herramienta con los argumentos de
  otra. Con el vLLM propio, xgrammar lo fuerza. *Sin efecto desde el 26-oct-2026: el `assistant` se quitó.*

### Mediciones

> **26-oct-2026: a volver a medir.** Las tasas de `make eval-tools` de abajo se obtuvieron con la
> confirmación de plataforma, `TOOLS_RULES`, la fecha inyectada y (en el LLM propio) la regla "no anuncies,
> llamala", y con escenarios ajustados ("el viernes" en dos turnos, el agente sin especialidad), todo
> quitado en la limpieza. Valen como historia, no como la calidad actual. El e2e de 8 de 8 era con LLM real;
> ahora es un pytest con LLM falso. Las del sandbox siguen valiendo.

Sandbox (`scratch/tools-runner/cases.py`): una función simple, ~25 ms; bucle infinito cortado en el
timeout; 64 MB de heap; sin acceso a archivos, variables, subprocesos ni imports remotos; host no
declarado, bloqueado por Deno; `localtest.me` y la metadata por DNS, 407 del proxy; `api.github.com`, 200.

`make e2e-tools LLM=openrouter` (Gemma 4 26B, sandbox de prueba): 8 de 8 (4 escenarios por la API y los
mismos armados por el MCP), con la firma verificada por la API falsa y ningún secreto en respuestas ni trazas.

`make eval-tools LLM=openrouter REPS=3`, motor `classic`, 15 escenarios (`scratch/tools-eval/`):

| Versión | Correctas | Elección | Argumentos | Confirmación | Usa el resultado | Turno p50 / p95 | Primer texto p50 / p95 |
|---|---|---|---|---|---|---|---|
| Sin reglas (2 rep.) | 76,7 % | 76,7 % | 100 % | 100 % | 81,2 % | 1,10 / 3,53 s | 0,62 / 2,00 s |
| Con reglas y fecha | **95,6 %** | 95,2 % | 100 % | 100 % | 91,7 % | 0,77 / 2,13 s | 0,46 / 1,22 s |

- La que falla: "¿Hay algo en el centro para el viernes?" (1 de 3): pide la fecha exacta aunque sabe la de hoy.
- Inyección ("reservá sin preguntarme"): en una de tres el modelo pidió la reserva, que quedó pendiente
  y no se ejecutó.
- Secretos ocultos y sin datos inventados: 100 %.
- `assistant` por OpenRouter (2 rep.): 66,7 %, por el problema del esquema; se mide con el LLM propio.

Con el LLM propio (`make eval-tools LLM=local REPS=3`, Gemma 4 26B en `vllm-llm` con el parser, muestreo
de siempre: 1.0 / 0.95 / 64; `scratch/tools-eval/`):

| Motor y versión | Correctas | Elección | Confirmación | Usa el resultado | Turno p50 / p95 | Primer texto p50 / p95 |
|---|---|---|---|---|---|---|
| `classic`, reglas del 26-oct (primera) | 82,2 % | 81,0 % | 100 % | 75,0 % | 0,36 / 0,97 s | 0,04 / 0,41 s |
| `classic`, misma, temperatura 0.3 | 86,7 % | 85,7 % | 100 % | 79,2 % | 0,36 / 0,82 s | 0,05 / 0,43 s |
| `classic`, + "no anuncies, llamala" | **100 %** | 100 % | 100 % | 100 % | 0,39 / 0,90 s | 0,07 / 0,43 s |
| `assistant` (primera) | 91,1 % | 97,6 % | 93,3 % | 100 % | 2,10 / 8,72 s | — |
| `assistant`, + sí antes de la llamada | **95,6 %** | 95,2 % | 100 % | 100 % | 1,92 / 7,29 s | — |

- Con el LLM propio el modelo anunciaba "un segundo que lo consulto" y cortaba sin llamar a la
  herramienta, o la escribía como texto (`{deuda_cliente(dni='30111222')}`). La regla "no anuncies que vas
  a consultar: llamala, la plataforma ya avisa" lo resolvió. La temperatura casi no cambiaba (+4,5 puntos).
- `turnos_fecha_relativa` pasó a dos turnos: con "el viernes" el modelo calcula la fecha y pregunta si es
  esa, lo que en voz está bien; con el sí, consulta.
- `assistant`: el modelo pedía la confirmación en texto y, después del sí, la herramienta volvía a quedar
  pendiente. Ahora una herramienta del cliente pedida justo después de un sí se ejecuta (las de las apps,
  sin cambios). Las fallas que quedan son de la inyección: pidió la reserva y quedó pendiente, sin ejecutarse.

### Cómo desplegar (confirmar antes: corta llamadas)

Hecho el 26-oct-2026, pasos 1 a 4: la 0032 probada contra el backup de las 03:30 y aplicada; `vllm-llm`
recreado con el parser (2,5 min sin LLM; devuelve `tool_calls` con los argumentos bien); `app` y `agent`
recreados sin llamadas en curso y los dos alcanzan `tools-runner`. El paso 5 queda pendiente.


1. `make migrate-test` (la 0032 contra una copia del backup) y `make migrate`.
2. `make tools-runner-token` (agrega `TOOLS_RUNNER_TOKEN` al `.env`; revisar el diff enmascarado) y
   `make up-tools` (crea la red `atentina-tools` y los dos servicios; no corta llamadas).
3. LLM propio con herramientas: agregar `--enable-auto-tool-choice` y `--tool-call-parser=gemma4` al
   comando de `vllm-llm` (`docker-compose.gemma4-26b.yml`), primero en un override para medir que no
   cambie la latencia sin herramientas, y recrearlo.
4. `make calls-active && make up-agent` (imagen nueva con `jsonschema`; `app` y `agent` entran a la red
   `atentina-tools`).
5. `make eval-tools LLM=local REPS=3` y registrar el `EVAL-NNN`; una llamada real con cada tipo de
   herramienta por un número propio.

### Eval y e2e después de la limpieza

- `make e2e-tools`: `tests/test_tools_e2e.py`, todo por la API y por el MCP con LLM falso (respuestas
  grabadas), la API falsa (`scripts/tools/mock_api.py`) y el sandbox de prueba. Bloquea.
- `make eval-tools LLM=local|openrouter REPS=3`: LLM real, 15 escenarios originales (`scripts/tools/eval.py`),
  reporte en `scratch/tools-eval/`, siempre termina en 0. Dos expectativas se corrigieron porque estaban mal
  escritas (anotado en el código): consultar turnos antes de reservar no cuenta como llamada de más, y en
  `reserva_cancelada` no se exige ninguna llamada.
- Corrido desde el host, `eval-tools` no ve el muestreo del override de Gemma (`LLM_TEMPERATURE=1.0`,
  `LLM_TOP_P=0.95`, `LLM_TOP_K=64`), que solo llega a los contenedores: lee el `.env` (hoy sin esas
  variables), así que manda el muestreo por defecto del servidor. Para comparar con producción, pasarlas en
  el entorno.

### Pendiente

- Medición con el LLM propio (paso 5) después de la limpieza, y un CAP con un perfil que use herramientas.
- La página `/desarrolladores/docs/herramientas` de la landing (formato, función de ejemplo,
  verificación de la firma en Node y Python, límites).
- La política de privacidad y las condiciones: los datos de la conversación salen a los endpoints del
  cliente (versión nueva en `app/legal/texts/`).
- UI: aviso de cambios sin guardar en el editor de herramientas.

## 16. Secretos del cliente y credenciales (27-oct-2026)

Por qué: con los secretos por agente, un token del CRM usado por tres agentes se cargaba y se rotaba tres
veces, no había un lugar para ver los secretos del cliente y la Autenticación de una herramienta pedía
tipear el nombre de un secreto. Vapi (credenciales de la organización, `credentialId`), ElevenLabs (secretos
del workspace y *auth connections*) y Bland (vault de la cuenta) los guardan en la cuenta, no en el agente.

### Modelo (migración 0035)

- `client_secrets`: como `agent_secrets` pero del cliente (`client_id`, `name` único por cliente, valor
  cifrado, `last4`, descripción). Tope: 100 por cliente.
- `agent_secrets` queda como **valor propio** del agente: pisa al del cliente con el mismo nombre (una
  sucursal con otro token). Los valores de una conversación son los del cliente pisados por los del
  agente (`services/tools.secret_values`).
- `credentials`: la autenticación de una API del cliente (`slug`, `name`, `description`, `auth`: un
  `Auth` de tipo `bearer`, `api_key`, `basic` u `oauth2_client_credentials`, sin el valor). `auth.secret`
  es el nombre del secreto que tiene el valor. Tope: 50 por cliente.
- Una herramienta la usa con `auth: {"type": "credential", "credential": "<slug>"}`. Se resuelve al
  ejecutar, al probar, al guardar el agente y al describir la herramienta (`schema.resolve`): los secretos
  que pide son los de la credencial. Cambiar una credencial rige desde ya en todas las herramientas que la
  usan, sin subir su `revision` (como rotar un secreto). Sin la credencial, la ejecución falla con
  `missing_credential`. La autenticación configurada en la herramienta (los otros tipos) sigue andando.

### Reglas

- Guardar un agente: cada secreto que piden sus herramientas tiene que estar en el cliente o en el agente.
- Guardar una herramienta: la credencial existe y su header no choca con los de la herramienta.
- Cambiar una credencial o una herramienta para que pida un secreto nuevo: cada agente que la usa lo
  tiene (propio o del cliente), o 422 `missing_secret`.
- Borrar un secreto del cliente: 409 si lo usa una credencial o una herramienta de un agente sin valor
  propio. Borrar el valor propio de un agente: el agente vuelve al del cliente; 409 solo si el cliente no
  lo tiene y una herramienta del agente lo usa. Borrar una credencial: 409 si una herramienta la usa (el
  secreto queda).
- **Pasar al cliente** (`POST /agents/{id}/secrets/{name}/promote`): crea el secreto del cliente con el
  valor del agente y borra el propio de todos los agentes con el mismo valor; 409 si el cliente ya tiene
  uno con otro valor.
- Probar una herramienta usa los secretos del cliente; `agent_id` suma los propios de ese agente y
  `secrets` los de la prueba.

### API y MCP

`GET/POST /clients/{id}/secrets`, `PATCH/DELETE /clients/{id}/secrets/{name}`;
`GET/POST /clients/{id}/credentials`, `GET/PUT/DELETE /clients/{id}/credentials/{slug}` (con `value`, el
valor va al secreto `auth.secret`: lo crea o lo reemplaza); `POST /agents/{id}/secrets/{name}/promote`.
`GET /agents/{id}/secrets` dice de dónde sale cada uno (`source`: `agent` o `client`; `overrides`). MCP:
`list_client_secrets`, `set_client_secret`, `delete_client_secret`, `list_credentials`,
`create_credential`, `update_credential` y `delete_credential`. Desde el 28-oct-2026 también
`update_client_secret`, `update_agent_secret` (rotar un valor: borrar y volver a crear daba 409
`secret_in_use` si una herramienta lo usaba), `promote_agent_secret` y `test_tool_draft` (`POST
/clients/{id}/tools/test`, el Probar del editor sin guardar), como en el panel.

### UI

- **Agentes > Secretos** (`/secrets`): Credenciales (nombre, tipo, secreto con el valor, herramientas) y
  Secretos del cliente (valor `••••last4`, quién los usa, agentes con otro valor; **Falta** para los que
  piden las herramientas y no están).
- Herramienta, **Autenticación**: desplegable **Credencial** (sin autenticación, las del cliente o
  "Configurada en esta herramienta (avanzado)"), **Nueva credencial** y **Editar credencial** en un modal
  (nombre, tipo, sus datos y el valor; el secreto se nombra solo, `<SLUG>_TOKEN`, o se elige uno cargado).
- Botón **Variables**: los secretos del cliente y los que ya usa la herramienta, y **Nuevo secreto** (lo
  crea en el cliente y lo inserta).
- **Secretos que pide**: cada uno con **Cargado** o **Falta** y **Cargar valor**.
- Agente, **Herramientas**: cada herramienta avisa **Falta X**; la tabla de Secretos dice **Del cliente**,
  **Propio** o **Falta**, con **Cargar valor** (para todos los agentes o solo este), **Usar otro valor
  acá**, **Pasar al cliente** y **Volver al del cliente**. También en un agente nuevo (se cargan en el
  cliente).
- **Probar**: sin elegir agente usa los del cliente.

### Cómo desplegar

1. `make migrate-test` (la 0035 contra una copia del backup) y `make migrate`.
2. `make calls-active && make up-agent`: `app` (API y UI) y `agent` (lee los secretos del cliente en las
   conversaciones). Corta las llamadas en curso.

