# BYOK de LLM: el cliente trae su proveedor

Hasta ahora todos los agentes usan el LLM propio (vLLM, sin proveedores externos). Este plan
agrega **conexiones** (la API key del cliente y su proveedor) y que cada **agente elija el LLM por
etapa de la conversación**: por ejemplo, el servidor propio en los primeros turnos y un modelo de
otro proveedor desde el turno N.

Estado (16-oct-2026): **fases 1 y 2 desplegadas** (migración 0016 aplicada; `app` y `agent`
reconstruidos con `anthropic` y recreados, sin llamadas activas). La fase 2 se probó contra un SDK
simulado, **no con una key real**. **Fase 3 (UI) y los parámetros de generación por agente, sin
desplegar** (reconstruir `web/dist` y recrear `app` y `agent`: la definición y el cliente del LLM
tocan los dos). Fase 4 pendiente.

## Alcance

- **Quién:** el cliente carga sus claves y elige modelo; el admin puede hacer lo mismo en cualquier cliente.
  La key no se vuelve a mostrar a nadie (la API devuelve solo los últimos 4 caracteres y quién la cargó).
- **Proveedores:** `openai_compatible` (OpenAI, Groq, Together, DeepSeek, un vLLM propio…), `openrouter`
  (fase 1) y `anthropic` con el SDK nativo (fase 2). Las URLs de `openrouter` y `anthropic` son fijas.
- **Fuera de alcance:** la API de inferencia (`/api/v1/inference`) sigue siendo solo del servidor propio.
  El STT y el TTS siguen propios.

## Diseño

### Datos

- `llm_connections` (migración 0016): `client_id`, `name`, `kind`, `base_url`, `api_key_enc` (Fernet con
  `WA_TOKEN_KEY`, como los tokens de apps y WhatsApp), `last4`, `default_model`, `json_mode`, `created_by`,
  resultado del último test y `revoked_at`.
- `Workflow.llm` (en la definición versionada del agente):

```json
"llm": {
  "stages": [
    {"from_turn": 1},
    {"from_turn": 4, "connection": "<id>", "model": "gpt-…", "temperature": 0.3}
  ],
  "fallback_local": true
}
```

- Sin `llm`, el servidor propio en todos los turnos (como antes). Hasta 3 etapas; la primera empieza en el
  turno 1; `from_turn` crece; una etapa externa necesita `model`. La etapa sin `connection` es el servidor propio.
- **Turno** = el N-ésimo mensaje del usuario (la apertura del agente no cuenta). Se deriva de
  `state.messages`: no hay estado nuevo, sobrevive a reinicios y es igual en voz, WhatsApp y campañas.
  En WhatsApp una conversación puede durar días: el conteo es por conversación.
- Cambiar el umbral o el modelo es una versión nueva del agente; las conversaciones en curso siguen con la suya.
- La extracción de datos usa la etapa del turno que la lanza.

### Motor

- `app/llm/resolver.py`: `LLMResolver.for_turn(workflow, turn, client_id)` devuelve el `LLMClient` propio
  (sin plan o etapa local) o un `TurnLLM` (etapa externa). El motor lo pide por turno y por extracción;
  el motor `assistant` recibe el LLM del turno en `run(..., llm=)`.
- `LLMClient` tiene dos perfiles: `vllm` (igual que siempre) y `generic` (proveedor externo: solo
  temperatura, sin `top_k`/`min_p`/`chat_template_kwargs` que el proveedor rechazaría;
  `max_completion_tokens` en api.openai.com).
- **Salida JSON** (`json_mode`, lo detecta el test de la conexión): `json_schema` estricto, `json_object`
  con el esquema en el prompt, o `prompt` (esquema en el prompt y se limpian los ``` de la respuesta).
- **Fallback** (`fallback_local`): si el proveedor falla, ese turno lo contesta el servidor propio y la
  traza lo marca (`provider: local`, `fallback_from`, `fallback_reason`). No hay fallback si el proveedor
  ya había empezado a hablar (en voz sonaría la frase dos veces): el error sube.
- **Circuito:** 3 errores seguidos de una conexión (turnos y extracciones suman) la saltean 30 s.
  Timeout de 20 s por pedido externo y sin reintentos del SDK.
- Una conexión revocada, de otro cliente o con la key ilegible no se usa: con `fallback_local` contesta
  el propio; sin él, el turno falla. Los cambios (revocar, rotar la key) llegan a `app` y `agent` en ≤ 30 s.

### Anthropic (`app/llm/anthropic_client.py`)

Mismos cuatro métodos que `LLMClient`, sobre la Messages API (no el shim OpenAI):

- El `system` va aparte y la conversación empieza siempre con el usuario (si arranca el agente, se antepone
  una línea de arranque).
- Salida estructurada con `output_config.format` (`json_schema`). El schema del motor `assistant` no tiene
  `type: object` en la raíz (`anyOf`): se envuelve en `{result: …}` y se desenvuelve. Si el proveedor rechaza
  un esquema (400), pasa a pedirlo en el prompt y queda así para esa conexión.
- Streaming con `messages.stream`; el primer mensaje sale a medida que llega, igual que con vLLM.
- No manda `thinking` (algunos modelos no admiten apagarlo). `output_config.effort` solo en los 4.6+ y 5.x:
  `low` en voz, `medium` si el motor `assistant` pide razonar. `temperature` solo en los modelos que la
  aceptan (los 4.7+ y 5.x la rechazan: se descarta). `max_tokens` mínimo de 2048, porque el razonamiento
  adaptativo cuenta contra él.
- Un `refusal` del proveedor es un error del turno: lo toma el fallback al servidor propio.
- Sin caché de prompt todavía (los modelos que lo exigen tienen un mínimo de tokens por prefijo).

### Parametros de generacion

Hasta ahora los hiperparametros eran globales por variable de entorno (`LLM_THINKING`, `LLM_SAMPLING`,
`LLM_TEMPERATURE`, `ASSISTANT_THINKING*`, `ASSISTANT_MAX_STEP_TOKENS`). Ahora son por agente, con
override por etapa, y el proveedor activo manda solo los que soporta:

- `Workflow.generation` (`Generation.params`): default del agente para toda la conversacion.
- `LlmStage.generation`: pisa el del agente en ese tramo (funciona tambien en una etapa local; el
  `temperature` suelto de la etapa vieja se pliega aca).
- Catalogo (`app/llm/params.py`, expuesto en `GET /api/v1/llm/params`): `temperature`, `top_p`,
  `top_k`/`min_p` (solo vLLM), `max_tokens`, `enable_thinking`/`thinking_token_budget` (solo vLLM),
  `reasoning_effort` (OpenAI/OpenRouter) y `effort` (Anthropic). El editor los agrega y quita, con los
  defaults del proveedor (para el local, los de la familia del modelo y del motor).
- Traduccion (`app/llm/client.py`, `app/llm/anthropic_client.py`): vLLM arma `extra_body`
  (`chat_template_kwargs`, `top_k`/`min_p`); el generico, `temperature`/`top_p`/`reasoning_effort` y
  `max_completion_tokens` en api.openai.com; Anthropic, `temperature`/`top_p` (si el modelo las
  acepta), `effort` y `max_tokens` con piso de 2048. Lo que el proveedor no soporta se descarta con
  log. Sin `generation`, todo igual que antes (muestreo por familia y razonamiento por motor).
- El resolver cachea un `LLMClient` local por combinacion de parametros (`LLMClient.derive`), porque
  las options se hornean al construirlo y el cliente base es unico por proceso.

### API

`/api/v1/clients/{client_id}/llm-connections` (cliente: el suyo; admin: cualquiera), igual que las API keys:

| Método | Qué hace |
|---|---|
| `GET` | Conexiones vigentes, con `used_by` (agentes que la usan). |
| `POST` | Crea (`name`, `kind`, `base_url`, `api_key`, `default_model`). `openrouter` tiene URL fija. |
| `PATCH /{id}` | Renombra, cambia modelo o URL, rota la key (borra el resultado del último test). |
| `POST /{id}/test` | Pedido real al proveedor: autentica, detecta `json_mode` y mide el tiempo. |
| `GET /{id}/models` | Lista de modelos del proveedor. |
| `DELETE /{id}` | Da de baja. Los agentes que la usan caen al propio (si tienen fallback). |

Al guardar un agente se valida que cada `connection` sea de su cliente y esté vigente
(`errors[].path = llm.stages.N.connection`). Los parametros de `generation` se validan contra el
catalogo (nombre, tipo, rango) y `GET /api/v1/llm/params` devuelve el catalogo para el editor.

### Seguridad

- Key cifrada en reposo; nunca en respuestas, logs ni trazas.
- `base_url` de `openai_compatible`: para un cliente exige https y rechaza hosts que resuelven a redes
  privadas o internas (SSRF); el admin puede apuntar a un servidor propio. Se valida al crear, editar y probar.
  No cubre DNS rebinding después del alta.
- Aislamiento: validación al guardar el agente y de nuevo al resolver en runtime.

## Impacto

- **Privacidad:** `landing/src/pages/privacidad.astro` dice que las conversaciones no se envían a
  proveedores externos. Con BYOK deja de ser cierto para los agentes que lo activen: **reescribir esa
  sección antes de habilitarlo con clientes** (local por defecto; externo solo si el cliente lo configura).
  Lo mismo en `docs/DESIGN_GUIDELINE.md` si cita la frase.
- **Calidad:** los prompts se afinaron con Qwen y Gemma. Medir con `make eval-llm` antes de recomendar un
  modelo externo, sobre todo en el motor `assistant`.
- **Latencia:** se suma el RTT y el TTFT del proveedor; la `LatencyCard` y la traza (`provider`, `model`)
  lo muestran por llamada.
- **Capacidad:** un agente en BYOK no carga la GPU 0. No cambia ningún CAP.
- **Costos:** los tokens los paga el cliente a su proveedor. Los minutos del tier se siguen contando.
- **Editor de la UI:** `fromDraft` reconstruye la definición campo por campo, así que `llm` tiene su propio
  borrador tipado (`web/src/features/agents/draft.ts`): sin etapas externas y con el respaldo activado no se
  guarda (queda el servidor propio, como antes).

## Fases

1. **Backend (hecha):** modelo, migración, cifrado, CRUD y test de conexiones, etapas por turno, resolver con
   fallback y circuito, perfil genérico de `LLMClient` (OpenAI compatible y OpenRouter). Tests:
   `tests/test_llm_byok.py`, `tests/test_migration_0016.py`.
2. **Anthropic (hecha y desplegada):** `AnthropicClient` con el SDK nativo. Tests: `tests/test_llm_anthropic.py`.
   Pendiente: probarla con una key real (latencia de TTFT en voz y un `make eval-llm`).
3. **UI (hecha, sin desplegar):** `web/src/features/llm/` (`ModelsPage` para el cliente,
   `LlmConnectionsSection` también en la pestaña **Modelos** de la ficha del cliente para el admin) y la sección
   "Modelo de lenguaje" del editor del agente (`features/agents/LlmSection.tsx`, etapas por turno). Alta de
   conexión con prueba automática; el resumen del agente muestra el modelo y el detalle de la conversación,
   proveedor, modelo y respaldo. Tests: `LlmConnectionsSection.test.tsx`, `LlmSection.test.tsx`, `draft.test.ts`.
   Guía de uso en [`GUIA_UI.md`](GUIA_UI.md), "Modelos".
4. **Cierre:** texto de privacidad, eval comparativa, `GUIA_UI.md`, `ARQUITECTURA.md`, flag de tier
   (`allow_byok_llm`) si se decide limitarlo a planes pagos.
5. **Parametros de generacion (hecha, sin desplegar):** `Workflow.generation` + `LlmStage.generation`,
   catalogo y traduccion por proveedor (`app/llm/params.py`), `GET /api/v1/llm/params`, editor en
   `web/src/features/agents/{GenerationEditor.tsx,LlmSection.tsx,draft.ts}`. Tests:
   `tests/test_llm_generation.py`, `LlmSection.test.tsx`, `draft.test.ts`. Medir con `make eval-llm`
   antes de recomendar valores (temperatura y razonamiento cambian calidad y latencia).

## Despliegue

- **Fase 1 (15-oct-2026, hecha):** `make up-app` (build, `alembic upgrade head` y recreate de `app`) y
  `docker compose build agent` + recreate de `agent` (sin llamadas activas). `WA_TOKEN_KEY` en `.env`.
- **Fase 2 (15-oct-2026, hecha):** lo mismo, porque la imagen necesita `anthropic` (`requirements.txt`).
  Recrear `agent` corta las llamadas en curso: hacerlo sin llamadas activas.

Las conexiones y el `llm` del agente también se cargan por la API (OpenAPI en `/api/v1/docs`).
- **Fase 3:** `make up-app` (`web/dist` sale del build de la imagen de `app`; ver el Dockerfile) y recrear
  solo `app`.
