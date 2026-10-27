# Agente externo: el cliente pone su agente, Atentina la voz

Una empresa que ya tiene su agente (con su prompt, sus herramientas y su estado) quiere atender
llamadas sin armar el pipeline de voz. Este plan agrega el motor **`external`**: el agente de la
plataforma pone el número, la telefonía, el VAD, los turnos, las interrupciones, el STT, el TTS, la
grabación y los minutos, y en cada turno le pide la respuesta al endpoint del cliente, que habla
**API de OpenAI** (`POST /chat/completions` con `stream: true`). Es el patrón "custom LLM" de Vapi
y Retell.

Estado (25-oct-2026): **fases 1 y 2 (UI) implementadas, sin desplegar** (migración 0030; secciones 10 y 11).
Documentación de la landing (6.1) y gestión por API key y MCP hechas el 25-oct-2026 (sección 12), sin desplegar ni publicar.

> **26-oct-2026:** ya no es un motor. Hay un solo motor y "Tu propio agente" es tener `external` en la definición
> (una opción del agente, que se prende desde su sección); `engine` ya no existe y `AgentOut.engine` pasó a
> `own_agent`. `end_call` y `transfer_call` son las herramientas de plataforma de todos los agentes. Donde este
> plan dice "motor `external`", `engine: "external"` o compara con `classic`/`assistant`, es historia: ver la
> sección 13 y [`LIMPIEZA_PLAN.md`](LIMPIEZA_PLAN.md).

## 1. Alcance

- **Canales:** todos los que pasan por `ConversationEngine.process_turn`, sin trabajo extra: llamadas
  entrantes y salientes (Anura y WhatsApp), link para llamar, campañas, WhatsApp de mensajería y
  `/api/v1/conversations`.
- **Lo pone el cliente:** un endpoint https público compatible con OpenAI, con streaming. Puede
  envolver cualquier cosa: su agente en LangGraph, un asistente de OpenAI, un n8n o su backend.
- **Lo pone Atentina:** la apertura (de la definición, como hoy; puede ir pregenerada), la voz, el
  tope de duración, los minutos del tier, la grabación, el resumen por email, los eventos y la
  derivación a personas.
- **Fuera de alcance:** audio crudo por WebSocket (para eso el cliente tiene que armar el pipeline) y
  el WebSocket de eventos de texto (opción 2 del análisis: si un cliente lo pide).

## 2. Por qué sale casi armado

- **Conexión:** ya existe `llm_connections` de BYOK (`docs/BYOK_LLM_PLAN.md`). Una conexión
  `openai_compatible` guarda la URL, la key cifrada (Fernet con `WA_TOKEN_KEY`), el modelo y el
  chequeo SSRF (https y host público para un cliente). Además ya tiene la prueba (`POST /{id}/test`)
  y la invalidación en ≤ 30 s. Se reutiliza tal cual.
- **Motor:** `process_turn` ya despacha por `workflow.engine` (`structured`, `classic` y `assistant`).
  `external` es una cuarta rama que devuelve el mismo `AgentTurn`: `assistant_message`, `status`,
  `end_reason` y `handoff`.
- **Worker:** `llm_node` ya pasa el texto al TTS a medida que llega (`on_message`), corta cuando
  `status == "completed"` y deriva con `turn.handoff`. No cambia.

## 3. Contrato con el endpoint del cliente

### Pedido (Atentina → cliente)

`POST {base_url}/chat/completions`, con `Authorization: Bearer <key de la conexión>`:

```json
{
  "model": "<modelo de la conexión, o lo que el cliente quiera>",
  "stream": true,
  "messages": [
    {"role": "assistant", "content": "Hola, soy Sofía de Acme. ¿En qué te ayudo?"},
    {"role": "user", "content": "Quería saber si tienen turno el jueves."}
  ],
  "tools": [{"type": "function", "function": {"name": "end_call", "...": "..."}}],
  "user": "<conversation_id>"
}
```

Headers: `X-Atentina-Conversation-Id`, `-Channel` (`voice`, `whatsapp`), `-Mode` (`entrante`, `saliente`,
`web`, `prueba`...), `-From`, `-To`, `-Agent` (slug), `-Turn` (1 = el primer mensaje de la persona) y, si hay,
`-Contact` (JSON de la campaña) y `-Context` (motivo de una saliente). Los que no tienen valor no van.

- **Historial completo en cada turno**, sin system prompt nuestro: el prompt es del cliente. Con
  `external.system` en la definición se antepone uno (para quien prefiere configurar el prompt en el
  panel).
- **Los datos de la llamada, solo en headers.** El cuerpo lleva solo campos estándar, porque un
  endpoint que reenvía el pedido a OpenAI recibiría un 400 por un campo desconocido (`metadata`
  exige `store`). Los textos que no son ASCII van con escapes JSON.
- **Herramientas de la plataforma** (`tools`): `end_call` (`outcome` opcional, uno de
  `completion.outcomes`) y, en una llamada con áreas, `transfer_call` (`area`). Las ejecuta
  Atentina. Si el endpoint las ignora, la llamada termina cuando corta el que llama, o por el tope
  de duración.

### Respuesta (cliente → Atentina)

- SSE de chat completions estándar. `delta.content` va al TTS a medida que llega, y lo que venga de
  razonamiento se descarta.
- `delta.tool_calls` con `end_call` hace `status = completed`: se corta cuando termina de sonar lo
  dicho, como el `[CORTAR]` del clásico. Con `transfer_call` se deriva (`AgentTurn.handoff`).
  Otras herramientas se ignoran y quedan en la traza.
- **El streaming es obligatorio:** una respuesta en JSON completo (sin SSE) da `endpoint_error`.
- Una respuesta sin texto ni herramientas es un error (`empty_response`).

### Lo que el integrador tiene que saber

- **La latencia es suya.** Cuenta desde que llega el pedido hasta el primer token: si pasa de ~1 s,
  la llamada se siente lenta. El objetivo se fija con la medición de la fase 1.
- **Turnos deshechos.** Si el que llama sigue hablando y la respuesta no llegó a sonar, Atentina
  deshace ese turno (`retract_last_turn`) y el siguiente pedido trae el mensaje completo. Por eso el
  historial que mandamos es la fuente de verdad. Si guardan estado propio, lo deben indexar por
  `conversation_id` y tolerar que un turno se repita con otro texto.
- **Interrupción.** Si el que llama interrumpe, Atentina cierra el stream: el endpoint ve la
  desconexión.
- En WhatsApp `channel` es `whatsapp`. La respuesta puede salir como texto o como nota de voz,
  según el canal y la configuración actual.

## 4. Definición del agente

```json
"external": {
  "connection": "<id de llm_connections>",
  "model": "acme-agent",
  "system": null,
  "first_token_timeout_ms": 4000,
  "error_message": "Disculpá, se me cortó. ¿Me repetís?",
  "max_errors": 2,
  "on_errors": "hang_up"
}
```

- No exige `fields` ni extracción (26-oct-2026: sin `engine`; tener `external` alcanza). `completion.outcomes` sigue teniendo un
  default, que es el que se usa si `end_call` no trae `outcome`.
- La validación al guardar es la de BYOK: la conexión tiene que ser del cliente, estar vigente y ser
  `openai_compatible`. `on_errors: transfer:<área>` exige que el área esté en `handoff.areas`.
- `handoff` vale con y sin `external`.

## 5. Errores

- **Sin primer token en `first_token_timeout_ms`, o un error HTTP:** se dice `error_message` y el
  turno queda en la traza con el error. Después de `max_errors` seguidos, `on_errors` decide:
  `hang_up` (cortar con `ended_reason=external_error`) o `transfer:<área>`.
- **No hay respaldo con el LLM propio:** no tiene el prompt del cliente, así que contestaría
  cualquier cosa. Si el endpoint ya había empezado a hablar, no se repite nada, igual que en
  `TurnLLM`.
- **Sin circuito por conexión:** un endpoint caído falla rápido (conexión rechazada), y uno colgado
  cuesta `first_token_timeout_ms` por turno, hasta `max_errors`. Si hace falta, se agrega el de BYOK.
- Si se corta después de empezar a hablar, queda lo dicho y el error va a la traza (no cuenta como error).

## 6. Cambios

| Dónde | Qué |
|---|---|
| `app/conversation/models.py` | `engine` con `external`; `ExternalConfig`; el validador acepta `handoff` con `external`. |
| `app/llm/external.py` (nuevo) | Arma el pedido (mensajes, metadata, headers y tools), lee el stream (texto y `tool_calls`), aplica el timeout del primer token y devuelve `AgentTurn`. Reutiliza el `AsyncOpenAI` de la conexión. |
| `app/conversation/engine.py` | Rama `external` en `process_turn`: guarda los mensajes y la traza (`provider: external`, ms al primer token, error) y no extrae. Con `end_call`, `progress.outcome`. |
| `app/services/agents.py` | Valida `external.connection` al guardar, igual que `llm.stages`, y que el plan incluya la función (429 `external_agent_not_in_plan`, como `whatsapp_not_in_plan`). |
| Migración (`tiers.external_agent`) | Booleano por plan, como `tiers.whatsapp` (0025): `false` por defecto, y `true` en Central e Interno (desde el 26-oct-2026, con Central borrado: Sucursal e Interno). Sale del tier, sin ajuste por cliente (los ajustes son solo numéricos). Entra en `limits.effective_limits`, en `features.TIER_HAS` y `plan_features` (`external_agent`), en `app/mcp/docs.FEATURES` y en el editor de tiers. |
| `web/src/features/agents/` | Motor "Agente externo" en el editor, con la sección Conexión: elegir o crear una, modelo, timeout, mensaje de error y qué hacer después. Cumple `docs/DESIGN_GUIDELINE_APP.md`. |
| `POST /llm-connections/{id}/test` | Con `?mode=external`: chequea el streaming, mide el primer token y ve si entiende `tools`. |
| `examples/agente-externo/` | Endpoint mínimo (FastAPI, ~60 líneas) que envuelve un LLM y usa `end_call`, para los integradores y para las pruebas. |
| Landing | Ver la sección 6.1. |
| MCP | `create_agent`/`update_agent` toman `external` desde el modelo Pydantic. Correr `make mcp-docs`. |

### 6.1 Landing

Se publica con la fase 2, nunca antes de que el motor esté en producción. Todo sigue
`docs/DESIGN_GUIDELINE.md`.

| Dónde | Qué |
|---|---|
| `pages/privacidad.astro`, "Dónde se procesan" | **Obligatorio antes de habilitarlo con un cliente.** La excepción BYOK no alcanza, por tres razones. Primero, el destino es un sistema del cliente, no solo un proveedor de LLM. Segundo, además del texto viajan datos de la llamada: el número que llama, el número marcado y los datos de campaña. Tercero, no hay respaldo con nuestro modelo, y hoy la excepción dice que puede haberlo. Agregar una excepción propia, "Agente del cliente". |
| `pages/desarrolladores/docs/agente-externo.astro` (nueva) | El contrato para integradores. Secciones: qué es, cómo funciona (un diagrama), pedido, respuesta, `end_call` y `transfer_call`, latencia y turnos deshechos, errores, configurar (panel y API), ejemplo (`examples/agente-externo/`), costos y privacidad. |
| `data/docs-nav.ts` y `layouts/DocsPage.astro` | Grupo nuevo, "Tu propio agente": la `key` suma `"external"` en la unión de tipos. |
| `pages/desarrolladores/docs/index.astro` | En "Cómo funciona", el paso 2 ("el modelo de lenguaje arma la respuesta") y "Los motores" nombran la opción y enlazan la página nueva. |
| `pages/desarrolladores/docs/api.astro` | En `#byok`, una línea para distinguirlo: BYOK cambia el modelo, y el agente externo cambia todo el agente. En `#derivaciones`, "Por ahora solo con el motor `classic`" pasa a `classic` o `external`. En `planFeatures`, la fila "Tu propio agente": No, No, No, Sí (Central; desde el 26-oct-2026, Sí en Sucursal y Red). Al cambiar los planes, actualizarla. |
| `data/site.ts`, `devCapabilities` | Una cuarta tarjeta, "Tu agente, nuestra voz", y en `pages/desarrolladores/index.astro` el título pasa de "Tres formas de integrarlo" a "Cuatro formas". |
| `data/mcp-tools.json` | Lo regenera `make mcp-docs`. No se edita a mano. |
| Opcional | Una página en `pages/plataforma/` para buscadores ("Voz para tu agente de IA") y el video, con el agente `videos`. |

`pages/terminos.astro` no habla de proveedores: no cambia.

## 7. Fases

1. **Backend + ejemplo.** Motor, contrato, errores y traza, con tests contra un endpoint simulado.
   Llamada de prueba con `examples/agente-externo/` corriendo en `scratch/`. Medir el agregado de
   latencia frente al motor `classic` con el mismo LLM detrás, para fijar el objetivo de la
   sección 3.
2. **UI y documentación pública.** Editor, prueba de la conexión, página de la landing y MCP.
3. **Opcionales, si los piden:**
   - Frase de relleno ("un segundo…") si el primer token tarda.
   - Firma HMAC del pedido (`X-Atentina-Signature`), además del Bearer.
   - `end_call` con `data` para cargar campos (el resumen por email y los eventos los mostrarían).
   - Apertura pedida al endpoint (turno 0).

## 8. Impacto

- **Capacidad:** no carga la GPU 0 (LLM). Sí carga STT y TTS, igual que una llamada normal.
  `CAP-001` no cambia.
- **Costos y plan:** se cuentan los minutos del tier, como en cualquier llamada. Por ahora **solo en
  Central** (e Interno, para nuestras pruebas; decisión del 25-oct-2026). Después se prende o apaga por
  plan desde el editor de tiers, sin código. **26-oct-2026:** Central se borró; está en Sucursal e Interno,
  y en Red (a medida).
- **Corte:** sin la función en el plan, no se guarda un agente `external`. Si el plan la pierde después
  (baja de plan), ese agente atiende con `error_message` y corta (`ended_reason=external_agent_not_in_plan`),
  y el panel lo marca con el aviso de función bloqueada (`docs/FUNCIONES_POR_PLAN_PLAN.md`).
- **Después de la llamada:** el integrador recibe el fin y el resultado por el webhook de eventos
  (`call.ended`, `app/services/events.py`) o los lee por `/api/v1/calls`. Verificar que `call.ended`
  lleve la transcripción o el link.

## 9. Decisiones abiertas

- **Planes:** solo Central por ahora (25-oct-2026); el resto se decide después. Resuelto el 26-oct-2026:
  Sucursal y Red (Central se borró).
- **Precio:** el cliente no gasta nuestro LLM. ¿Mismo precio por minuto o uno menor?
- **Nombre en la UI y en la landing:** "Agente externo" o "Tu propio agente".

## 10. Fase 1: lo hecho (25-oct-2026)

- **Código:** `app/llm/external.py` (`ExternalAgents`: conexión y plan cacheados 30 s, pedido, stream y
  herramientas), la rama `_external_turn` en `app/conversation/engine.py` (errores, `on_errors` y
  `progress.external_errors`, que vuelve a 0 con un turno bueno), `ExternalConfig` en
  `app/conversation/models.py`, la validación en `app/services/agents.py` y la migración 0030.
- **Tests:** `tests/test_external_agent.py` (endpoint simulado con `httpx.MockTransport`: historial,
  headers, `end_call` con y sin `outcome`, `transfer_call`, error HTTP, timeout del primer token, corte
  por `max_errors` y plan sin la función) y `tests/test_migration_0030.py`.
- **Ejemplo:** `examples/agente-externo/server.py` (FastAPI) reenvía a un LLM compatible con OpenAI con su
  propio prompt y las herramientas de la plataforma. Probado con el cliente real (`scratch/agente-externo/smoke.py`)
  y DeepSeek V4.1 Flash por OpenRouter: dos turnos, el segundo con `end_call` y `outcome`; primer token de
  1.672 ms (el primero) y 482 ms. El LLM propio no sirve detrás del ejemplo: vLLM no tiene
  `--enable-auto-tool-choice` y rechaza los pedidos con `tools`.
- **Falta de la fase 1:** la llamada real y la medición contra `classic`. Hace falta desplegar:
  `make migrate` y `make calls-active && make up-agent` (recrea `app` y `agent`). El ejemplo tiene que quedar
  accesible por https para un cliente, o por http si la conexión la carga un admin.
- **Antes de la fase 2:** `make mcp-docs` ya sumó la fila "Agente propio" en `landing/src/data/mcp-tools.json`.
  No publicar la landing con ese cambio antes de desplegar el motor y cambiar `/privacidad`.

## 11. Fase 2: la UI (25-oct-2026)

- **Editor del agente:** sección "Tu propio agente" (`web/src/features/agents/ExternalSection.tsx`), para el
  cliente y el admin, dentro de `PlanGate` (`external_agent`). El switch pasa el motor a `external` (y al
  apagarlo, a `classic`); se elige el endpoint entre las conexiones `openai_compatible`, el modelo, el prompt
  opcional, el mensaje de error, la espera, los errores seguidos y qué hacer después (cortar o un área de la
  derivación). El selector de motor del admin se oculta con `external`, igual que Modelo de lenguaje, Reglas,
  Base de conocimiento y Datos. Los resultados dicen "Lo elige tu agente" en lugar de condiciones.
- **Arreglo:** `toDraft` pasaba a `classic` cualquier motor que no conocía; guardar un agente `external` desde
  la UI lo habría cambiado de motor sin avisar.
- **Probar el endpoint:** `POST /llm-connections/{id}/test` con `mode: "external"` manda un turno en streaming
  con `end_call` y guarda "streaming · primer texto N ms" en la conexión (no cambia `json_mode`).
- **Tiers:** switch "Agente propio" en el editor y "con agente propio" en la tabla.
- **Tests:** `ExternalSection.test.tsx`, `draft.test.ts` (motor external) y
  `test_connection_test_as_agent_endpoint`. Capturas con el backend de desarrollo (`scratch/shots/ext-*.png`).
- **Desplegar (fases 1 y 2):** `make migrate-test` y `make calls-active && make up-agent` (que migra)
  (recrea `app`, con `web/dist`, y `agent`).

## 12. Todo por API y MCP, y la documentación (25-oct-2026)

- **Nombre:** "Tu propio agente" (en otros proveedores, *custom LLM*; la etiqueta va en la página para que se encuentre).
- **API:** las rutas de `llm-connections` aceptan API keys (`CurrentPrincipal`: `calls` y `mcp` escriben, `mcp_read`
  solo lee). Antes exigían sesión de usuario. Una key no puede apuntar a una red interna (solo un admin);
  `created_by` queda vacío.
- **MCP:** `list_llm_connections` sin OAuth obligatorio, `create_llm_connection` (destructiva: la API key del endpoint
  pasa por la conversación, el cliente MCP la confirma) y `test_llm_connection` (`mode: external`). 121 herramientas.
  Falta `make mcp-eval` (gasta tokens de OpenRouter).
- **Traza:** `LlmCall` devuelve `first_token_ms` y `error`, y el chat los muestra ("primer texto N ms" y el error).
- **Landing:** página `/desarrolladores/docs/tu-propio-agente` (grupo `propio` en `data/docs-nav.ts`), enlaces desde la
  portada de la documentación y desde `/docs/api` (`#byok`, `#derivaciones` y la fila de la tabla de planes), cuarta
  tarjeta en `/desarrolladores` (grilla 2 × 2 en `Platform.astro` con 4 tarjetas) y la excepción "Agente del cliente"
  en `/privacidad` (`#agente-propio`). Revisada con capturas a 1440 y 390 px, sin scroll horizontal.
- **Desplegar:** `make calls-active && make up-agent` (sin migración nueva). Publicar la landing después.

## 13. Un solo motor (26-oct-2026)

Con la limpieza de [`LIMPIEZA_PLAN.md`](LIMPIEZA_PLAN.md), sin desplegar:

- `engine` deja de existir en la definición (el de una definición vieja se ignora al leerla): "Tu propio agente" es
  `external` en la definición. `ConversationEngine` despacha a `_external_turn` si está, y si no al turno con el
  LLM de Atentina (o BYOK).
- La UI no pregunta motor: el switch de la sección "Tu propio agente" agrega o quita `external`. La API devuelve
  `AgentOut.own_agent` en lugar de `engine`, y `engine` salió de `AgentCreate`, `TemplateOut` y `PromptOut`.
- `end_call` y `transfer_call` (`app/llm/platform_tools.py`) son las mismas herramientas para todos los agentes;
  con tu propio agente, `end_call` lleva `outcome` (los ids de `completion.outcomes`) en lugar de `motivo`.
- Un agente con `external` no lleva `tools` del cliente: las herramientas son las de su agente.
- Desde el 26-oct-2026 `vllm-llm` corre con `--enable-auto-tool-choice --tool-call-parser=gemma4`: el LLM propio ya
  acepta pedidos con `tools` (lo que en la sección 10 impedía usarlo detrás del ejemplo). Sin probar detrás del ejemplo.
