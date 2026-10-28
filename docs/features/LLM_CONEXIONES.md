# Conexiones de LLM y tu propio agente

El cliente conecta su proveedor de LLM con su key (BYOK) y cada agente elige qué LLM contesta desde qué turno, con
el servidor propio de respaldo; o conecta su propio agente (un endpoint compatible con OpenAI) y Atentina pone la voz,
la telefonía y los minutos. También: los hiperparámetros de generación por agente. Estado: conexiones en producción
desde el 15-oct-2026; "Tu propio agente", desde el 26-oct-2026. Plan: las conexiones BYOK, en todos los planes;
"Tu propio agente", con `tiers.external_agent` (clave `external_agent` de `TIER_HAS`; hoy Sucursal e Interno).

## Modelo de datos

- `llm_connections` (migración 0016): `client_id`, `name`, `kind` (`openai_compatible` \| `openrouter` \|
  `anthropic`), `base_url`, `api_key_enc` (Fernet con `WA_TOKEN_KEY`), `last4`, `default_model`, `json_mode`,
  `created_by`, `last_test_at`/`_ok`/`_detail`, `revoked_at` (baja lógica).
- `tiers.external_agent` (migración 0030): booleano del plan, sin ajuste por cliente.
- En la definición versionada del agente (`app/conversation/models.py`):

```json
"llm": {
  "stages": [
    {"from_turn": 1},
    {"from_turn": 4, "connection": "<id>", "model": "gpt-4.1-mini", "generation": {"params": {"temperature": 0.3}}}
  ],
  "fallback_local": true
},
"generation": {"params": {"temperature": 0.7, "max_tokens": 400}},
"external": {
  "connection": "<id>", "model": null, "system": null,
  "first_token_timeout_ms": 4000, "error_message": "Disculpá, se me cortó. ¿Me lo repetís?",
  "max_errors": 2, "on_errors": "hang_up"
}
```

- `llm` (`LlmPlan`): hasta 3 etapas; la primera empieza en el turno 1 y `from_turn` crece. Una etapa sin
  `connection` es el servidor propio; con `connection`, `model` es obligatorio. Sin `llm`, el propio en todos los
  turnos.
- **Turno** = el N-ésimo mensaje del usuario (la apertura no cuenta), derivado de `state.messages`: sobrevive a
  reinicios y es igual en voz, WhatsApp y campañas. En WhatsApp cuenta por conversación.
- Cambiar etapas o modelo es una versión nueva del agente; las conversaciones en curso siguen con la suya.
- `external` (`ExternalConfig`): `model` vacío = `default_model` de la conexión; `system` (hasta 20.000) se antepone
  si está; `first_token_timeout_ms` 500 a 20.000; `max_errors` 1 a 10; `on_errors` `hang_up` o `transfer:<área>`
  (el área tiene que estar en `handoff.areas`). Un agente con `external` no lleva `tools` del cliente.

## API

`app/api/routers/llm_connections.py`, prefijo `/api/v1/clients/{client_id}/llm-connections`. Cliente: las suyas
(sesión o API key `calls`/`mcp`; `mcp_read` solo lee); admin: las de cualquiera.

| Ruta | Qué hace |
|---|---|
| `GET` | conexiones vigentes, con `used_by` (agentes que la usan) |
| `POST` | crea: `name`, `kind`, `base_url` (solo `openai_compatible`), `api_key`, `default_model` |
| `PATCH /{id}` | renombra, cambia URL o modelo, rota la key |
| `POST /{id}/test` | `{model?, mode}`. `mode: llm`: pedido real con salida `json_schema`; guarda el resultado y `json_mode`. `mode: external`: un turno en streaming con `end_call`, mide el primer texto ("streaming · primer texto N ms") |
| `GET /{id}/models` | modelos del proveedor |
| `DELETE /{id}` | baja (`revoked_at`); los agentes que la usan caen al propio si tienen `fallback_local`, si no el turno falla |

- `GET /api/v1/llm/params` (`app/api/routers/llm_params.py`): catálogo de parámetros por proveedor y los defaults del
  servidor propio, para el editor.
- Al guardar un agente (`app/services/agents.py`): cada `llm.stages.N.connection` es del cliente y está vigente;
  `external.connection` además es `openai_compatible`, y el plan incluye la función (429
  `external_agent_not_in_plan`). Los parámetros de `generation` se validan contra el catálogo.
- MCP (`app/mcp/catalog.py`): `list_llm_connections`, `create_llm_connection`, `update_llm_connection`,
  `delete_llm_connection`, `test_llm_connection` (con `mode: external`), `list_llm_connection_models`; `external` y
  `llm` entran por `create_agent`/`update_agent`.
- La API de inferencia (`/api/v1/inference`, [`../API_INFERENCIA.md`](../API_INFERENCIA.md)) es solo del servidor
  propio. STT y TTS son siempre propios.

## Flujo: LLM por etapa (BYOK)

`app/llm/resolver.py`, `LLMResolver.for_turn(workflow, turn, client_id)`:

1. Sin plan o etapa local: el `LLMClient` propio con los parámetros del turno (cacheado por combinación, porque las
   opciones se hornean al construirlo).
2. Etapa externa: un `TurnLLM` con el cliente del proveedor y el propio de respaldo.
   - `openai_compatible` y `openrouter` (URL fija `https://openrouter.ai/api/v1`): `LLMClient` con perfil genérico
     (`app/llm/client.py`); sin reintentos del SDK; `max_completion_tokens` en `api.openai.com`.
   - `anthropic` (URL fija): `AnthropicClient` (`app/llm/anthropic_client.py`) sobre la Messages API: `system` aparte,
     la conversación empieza siempre con el usuario, herramientas como `tool_use`/`tool_result`, salida JSON por
     `output_config.format`, streaming con `messages.stream`.
3. El texto va al TTS a medida que llega; las herramientas (de plataforma y del cliente) van por function calling
   nativo (ver [HERRAMIENTAS.md](HERRAMIENTAS.md)). La extracción de datos usa la etapa del turno que la lanza.
4. **Respaldo** (`fallback_local`): si el proveedor falla, ese turno lo contesta el propio y la traza lo marca
   (`provider: local`, `fallback_from`, `fallback_reason`). No hay respaldo si ya empezó a hablar (sonaría doble) ni
   si ya ejecutó una herramienta del cliente (la repetiría): el error sube.
5. **Circuito:** 3 errores seguidos de una conexión (turnos y extracciones) la saltean 30 s. Timeout de 20 s por
   pedido externo.
6. Una conexión revocada, de otro cliente o con la key ilegible no se usa (con respaldo contesta el propio; sin él,
   `LlmUnavailable`). Los cambios llegan a `app` y `agent` en ≤ 30 s (caché de conexiones).

La traza de cada turno (`Message.llm`) dice proveedor y modelo; la UI los muestra en el detalle de la conversación.

## Hiperparámetros por agente

- `Workflow.generation` es el default del agente; `LlmStage.generation` lo pisa en su tramo (también en una etapa
  local). El `temperature` suelto de una etapa vieja se pliega ahí.
- Catálogo en `app/llm/params.py`:

| Parámetro | Proveedores |
|---|---|
| `temperature`, `top_p`, `max_tokens` | todos (Anthropic: `max_tokens` con piso de 2048, porque el razonamiento adaptativo cuenta contra él) |
| `top_k`, `min_p`, `enable_thinking`, `thinking_token_budget` | servidor propio (vLLM, por `extra_body` y `chat_template_kwargs`) |
| `reasoning_effort` (`low`/`medium`/`high`) | `openai_compatible`, `openrouter` |
| `effort` (`low`/`medium`/`high`) | `anthropic` (default `low`) |

- Cada proveedor manda los que soporta y descarta el resto, así una misma definición sirve para cualquiera.
- Anthropic: `output_config.effort` solo en los 4.6+ y 5.x; `temperature`/`top_p` solo en los anteriores a 4.7 (los
  4.7+ y 5.x los rechazan); no se manda `thinking` (algunos modelos no admiten apagarlo); un `refusal` es un error del
  turno (lo toma el respaldo).
- Sin `generation`, el servidor propio usa `LLM_THINKING`/`LLM_THINKING_BUDGET` y `LLM_TEMPERATURE`/`LLM_TOP_P`/
  `LLM_TOP_K`/`LLM_MIN_P` (`app/config.py`; los de Gemma, 1.0/0.95/64/0.0, en `docker-compose.gemma4-26b.yml`). Un
  proveedor externo solo usa lo de `generation`.

## Flujo: tu propio agente

`app/llm/external.py` (`ExternalAgents`) y `_external_turn` en `app/conversation/engine.py`. El agente del cliente
contesta cada turno; Atentina pone número, telefonía, VAD, turnos, interrupciones, STT, TTS, apertura (de la
definición, puede ir pregenerada), grabación, minutos, resumen por email, eventos y derivación. Vale en todos los
canales que pasan por el motor (llamadas, WhatsApp, link para llamar, campañas, `/api/v1/conversations`).

**Pedido** (Atentina → cliente): `POST {base_url}/chat/completions` con `Authorization: Bearer <key de la conexión>`,
`stream: true`, `model`, `messages` (historial completo en cada turno, sin prompt nuestro salvo `external.system`;
lo que dijo una persona del equipo va como `assistant` con `name`), `tools` y `user: <conversation_id>`.

- Herramientas: `end_call` con `outcome` (enum de `completion.outcomes`; sin él, el último resultado de la lista) y,
  en una llamada de voz con áreas, `transfer_call` con `area` (`app/llm/platform_tools.py`).
- Datos de la llamada **solo en headers** (el cuerpo lleva solo campos estándar: un endpoint que reenvía a OpenAI
  rechazaría los desconocidos): `X-Atentina-Conversation-Id`, `-Channel`, `-Mode`, `-From`, `-To`, `-Agent`, `-Turn`
  (1 = primer mensaje de la persona) y, si hay, `-Contact` (JSON de la campaña) y `-Context` (motivo de una saliente),
  recortados a 2000. Lo no ASCII va con escapes JSON. Los vacíos no van.

**Respuesta** (cliente → Atentina): SSE de chat completions. `delta.content` va al TTS a medida que llega;
`delta.tool_calls` con `end_call` corta después de decir lo escrito, con `transfer_call` deriva. Otras herramientas
se ignoran y quedan en la traza. Los tokens de `usage`, si vienen, se guardan.

**Errores** (sin respaldo con el LLM propio: no tiene el prompt del cliente):

| Caso | Qué pasa |
|---|---|
| Sin primer texto ni herramienta en `first_token_timeout_ms`, error HTTP o respuesta que no es SSE | se dice `error_message`, la traza guarda el error; tope del turno entero 30 s |
| Respuesta sin texto ni herramientas | `empty_response`, igual que un error |
| `max_errors` seguidos (`progress.external_errors`, vuelve a 0 con un turno bueno) | `on_errors`: cortar (`ended_reason=external_error`) o derivar al área |
| Se corta después de empezar a hablar | queda lo dicho, el error va a la traza y no cuenta |
| Conexión revocada, de otro cliente o key ilegible | `connection_unavailable`, cuenta como error |
| El plan ya no incluye la función | dice `error_message` y corta (`ended_reason=external_agent_not_in_plan`) |

Conexión y plan se cachean 30 s. No hay circuito por conexión. Turnos deshechos: si la persona sigue hablando y la
respuesta no llegó a sonar, el turno se deshace y el siguiente pedido trae el mensaje completo; el historial que manda
Atentina es la fuente de verdad (el endpoint que guarde estado lo indexa por `conversation_id` y tolera turnos
repetidos con otro texto). Si la persona interrumpe, se cierra el stream.

**Ejemplo:** `examples/agente-externo/server.py` (FastAPI): antepone su prompt y reenvía a cualquier LLM compatible
con OpenAI, pasando `end_call`/`transfer_call` tal cual. La documentación pública está en la landing
(`/desarrolladores/docs/tu-propio-agente`).

## UI

- **Agentes > Modelos** (`/models`, `web/src/features/llm/ModelsPage.tsx`) y la pestaña Modelos de la ficha del
  cliente para el admin (`LlmConnectionsSection.tsx`): alta con prueba automática, rotar la key, baja.
- Editor del agente (`web/src/features/agents/`): sección "Modelo de lenguaje" (`LlmSection.tsx`, etapas por turno y
  respaldo; `GenerationEditor.tsx` para los parámetros) y sección "Tu propio agente" (`ExternalSection.tsx`, dentro de
  `PlanGate` `external_agent`): el switch agrega o quita `external`; se elige la conexión `openai_compatible`, modelo,
  prompt opcional, mensaje de error, espera, errores seguidos y qué hacer después. Con `external` se ocultan Modelo de
  lenguaje, Reglas, Base de conocimiento y Datos, y los resultados dicen "Lo elige tu agente".
- La API devuelve `AgentOut.own_agent` para saber si un agente usa su propio agente.

## Reglas y trampas

- **Requisitos de un proveedor BYOK:** `tools` (function calling nativo; `end_call` va en todo pedido) y salida JSON
  guiada `json_schema` (extracción de datos). Sin `json_schema` la prueba de la conexión falla; no hay modo con el
  esquema en el prompt.
- `base_url` de `openai_compatible`: https y un host que resuelve solo a IPs públicas, para todos (también el admin);
  se valida al crear, editar y probar. No cubre un DNS que cambia después del alta.
- La key nunca sale en respuestas, logs ni trazas; aislamiento entre clientes al guardar el agente y de nuevo al
  resolver en runtime.
- Latencia: se suma el RTT y el primer token del proveedor o del endpoint; con tu propio agente, más de ~1 s al
  primer token ya se siente en voz. Medido con el ejemplo y DeepSeek V4.1 Flash por OpenRouter: 1.672 ms el primer
  turno, 482 ms el segundo.
- Capacidad: un agente BYOK o propio no carga la GPU 0 (sí STT y TTS). Los minutos del tier se cuentan igual; los
  tokens los paga el cliente a su proveedor.
- Privacidad: con un proveedor externo o tu propio agente la conversación sale del server (el texto, no el audio).
  Cubierto en la política de privacidad `2026-10-28` (`app/legal/texts/privacidad/`): "Excepción: modelo de lenguaje
  del cliente" (con el posible respaldo de nuestro modelo) y "Excepción: agente del cliente" (`#agente-propio`: texto,
  números, canal y datos de campaña; sin respaldo).
- Calidad: los prompts de los agentes de referencia se afinaron con modelos propios; medir con `make eval-llm` antes
  de recomendar un modelo externo o valores de `generation`.

## Desplegar y probar

- Requiere `WA_TOKEN_KEY` en `.env`. Cambios de código: `make calls-active && make up-agent` (`app` con `web/dist` y
  `agent`).
- `make test`: `tests/test_llm_byok.py`, `test_llm_anthropic.py` (SDK simulado), `test_llm_generation.py`,
  `test_external_agent.py` (endpoint simulado con `httpx.MockTransport`) y `test_platform_tools.py`.
- `make web-check`: `LlmConnectionsSection.test.tsx`, `LlmSection.test.tsx`, `ExternalSection.test.tsx`, `draft.test.ts`.
- `make eval-llm` (ver [`../eval/README.md`](../eval/README.md)) para comparar modelos.

## Pendientes

- Probar Anthropic con una key real: primer token en voz y un `make eval-llm`.
- Una llamada real con tu propio agente (con `examples/agente-externo/` expuesto por https) y medir la latencia
  agregada frente al LLM de Atentina con el mismo modelo detrás. El ejemplo con el LLM propio detrás, sin probar.
- Verificar que el evento `call.ended` (`app/services/events.py`) le alcance al integrador (transcripción o link).
