# Casos de prueba de un agente

**Estado:** implementado (backend, UI y MCP). Pendiente: cargar los casos de La Estrella en producción y correr el
`qa` de la función completa antes del deploy (nivel 3).

Un caso es una conversación grabada hasta un turno del usuario, con los resultados de herramienta que recibió el
modelo en ese turno y chequeos deterministas. Se corre N veces contra la versión guardada del agente o contra los
cambios sin guardar, y dice **pasa X/N**. Informa; nunca bloquea y nunca ejecuta una herramienta real.

## Cómo se usa

- **Desde una llamada:** en el detalle, cada respuesta del agente con un mensaje del usuario justo antes tiene
  «Crear caso de prueba». No aparece en la apertura ni en lo que habló una persona del equipo.
- **Desde Probar:** el chat de prueba del agente ofrece la misma acción.
- **Pestaña Pruebas** del agente: lista los casos con su «pasa X/N», corre todos y abre el detalle (chequeos,
  resultado grabado, historial, respuestas y borrar). Abajo, **Última corrida**: la más nueva del agente venga de
  donde venga (la pestaña, el editor, la API o el MCP), con su estado en castellano, el progreso mientras corre y
  las respuestas al terminar. Con una en curso, **Cancelar** pide confirmación y deja «Cancelando…» hasta que
  termina; después queda **Cancelada** con lo que alcanzó a correr (no cuenta para el «pasa X/N»).
- **Editor del agente:** «Correr pruebas» compara los cambios sin guardar contra la publicada. Al guardar avisa si
  no se corrieron o si algún caso empeora; nunca impide guardar. **Ver comparación** reabre la última corrida de
  esos cambios (o la que se acaba de lanzar) sin volver a correr. Si ya hay una corrida en curso, el 409 lleva a
  Pruebas sin perder lo editado.
- **Herramientas:** al guardar una revisión nueva de una herramienta usada por agentes, un aviso lleva a las
  pruebas de cada uno.
- **MCP:** `list_agent_test_cases`, `create_agent_test_case`, `run_agent_tests` (no destructiva: no llama ni manda
  nada), `get_agent_test_run` y `cancel_agent_test_run`, en el grupo `agents` y solo Admin del cliente
  ([`MCP.md`](MCP.md)).

Está en todos los planes, sin columna nueva en el tier: los topes son fijos (arriba).

## Modelo

`agent_test_cases`: copia del caso, por cliente y agente.

| Campo | Qué guarda |
|---|---|
| `snapshot` | `{messages, user_message, user_message_at, progress, channel, handoff}`. Los mensajes van sin `llm` ni `recording`; `progress` sin las variables de fuente `tool:*` (las asignó una herramienta después del turno y no estaban en el prompt). |
| `tool_results` | `[{name, arguments, result}]` del turno. Si `Message.tools` venía recortado a 4000, se toma la salida completa de la traza `herramienta`. |
| `checks` | Los chequeos normalizados. |
| `known_failure` | Falla conocida: se muestra aparte y no se espera que pase. |
| `source_conversation_id` | La llamada de origen. Si se borra la llamada queda en null: el caso conserva su copia. |

`agent_test_runs`: `status` (queued/running/done/failed/cancelled), `repetitions`, `variants` (publicada y, si hay
cambios, borrador con su definición), copia de nombre y chequeos de cada caso, `results`, `summary` (`pasa X/N` por
variante, sin las respuestas), `done/total`, tokens, revisiones de herramientas, error, fechas y
`cancel_requested_at` (el pedido de cancelación de una corrida en curso). Un índice único parcial deja una sola
corrida queued/running por agente; `cancelled` no es activa.

## API

Todas las rutas van por `get_agent` y después por `agent_id` + id: un caso o una conversación de otro cliente o de
otro agente da 404. La lectura la puede hacer cualquier principal del cliente; escribir y correr, solo un Admin del
cliente (la API key de un cliente y el admin en soporte cuentan).

| Ruta | Qué hace |
|---|---|
| `POST /api/v1/agents/{id}/test-cases/preview` | `{conversation_id, message_index}` → la copia, la respuesta original y los chequeos sugeridos. No guarda. |
| `POST /api/v1/agents/{id}/test-cases` | Crea el caso. `messages`, `user_message` y `tool_results` pisan lo generado. |
| `GET /api/v1/agents/{id}/test-cases` | Lista con `last_run` (pasa X/N y fecha). |
| `GET/PATCH/DELETE /api/v1/agents/{id}/test-cases/{case_id}` | Detalle con historial, edición y borrado. |
| `POST /api/v1/agents/{id}/test-runs` | `{repetitions=5, definition?, case_ids?, draft_case?}` → 202. Sin `case_ids`, todos los casos; `draft_case` prueba un caso sin guardar. |
| `POST /api/v1/agents/{id}/test-runs/{run_id}/cancel` | 200. En cola la cancela en el acto (`cancelled`, sin `started_at`); en curso deja el pedido en `cancel_requested_at` y la cola no manda más turnos. Una terminada vuelve sin cambios. |
| `GET /api/v1/agents/{id}/test-runs[/{run_id}]` | Progreso y resultados. `limit` (1–30, default 30) e `include_results` (default `true`): en `false` no trae `results` ni la definición del borrador (`variants`), para mirar el progreso liviano. |

Errores: 404 conversación o caso de otro cliente/agente, 409 `test_run_in_progress` con el `run_id` de la corrida
activa, 422 `external_agent_not_supported`, `too_many_cases`, `no_test_cases`, `invalid_checks` o
`invalid_definition`, 429 por el tope de corridas. Un agente `external` no tiene casos: su prompt y sus herramientas
son de su endpoint.

## Chequeos

| Tipo | Campos | Pasa cuando |
|---|---|---|
| `usa_herramienta` | `tool`, `argumentos_contienen?` | el turno llamó a esa herramienta y sus argumentos contienen el texto |
| `no_usa_herramienta` | `tool?` | no llamó a esa herramienta (sin tool: a ninguna) |
| `deriva_a` | `area` | el turno derivó a esa área |
| `no_deriva` | | el turno no derivó |
| `dice` | `text` | el texto del LLM (o como lo dice el TTS) contiene el texto |
| `no_dice` | `text` | no lo contiene |
| `empieza_con` | `text` | el texto del LLM empieza con el texto (salvo signos de apertura) |
| `datos_de_la_herramienta` | | toda hora `H:MM` y todo importe `$N` del texto está entre los resultados que recibió el modelo |

El texto se compara sin tildes, en minúsculas y con espacios colapsados. Una coincidencia no vale pegada a una letra
o un dígito, ni a un `.`/`,` seguido de dígito: `130` no está en `1.130` ni en `130.000`. `datos_de_la_herramienta`
recorre el JSON de los resultados (números y cifras dentro de strings, en formato argentino y plano) y resalta el
texto que falla. Lo dicho en palabras no se controla: «ciento treinta mil» no se compara con `$130.000`.

**Límite conocido:** por el lado hablado, `no_dice "130"` puede dar falso positivo con «ciento treinta mil», porque
`to_speech("130")` es «ciento treinta» y aparece como palabras. Queda como límite documentado, no se corrige con una
lista de palabras.

## La corrida

Por caso, variante y repetición, en memoria y sin `process_turn`:

- Arma el `ConversationState` con el canal, los mensajes y el `progress` grabados, `system_prompt=None` (se arma con
  la versión probada y las variables grabadas) y `agent_version` = la probada.
- Si el caso puede derivar, carga las áreas de la versión probada con el horario **congelado a la hora del mensaje
  grabado**: abierta → sin horario; cerrada → semana vacía. Así el LLM ve «cerrada ahora» aunque la corrida sea en
  horario de atención.
- Resuelve el LLM con un `LLMResolver` propio de las pruebas: una falla de un proveedor BYOK no abre el circuito de
  las llamadas en vivo. Usa `for_turn` con el turno del usuario y `converse` en streaming, como la voz.
- Las herramientas son `RecordedTools` (`TurnTools`): devuelven el k-ésimo resultado grabado de ese nombre, o
  `{"ok": false, "error": "sin resultado grabado en el caso"}`. Nunca llaman a `run`, no escriben `tool_runs` y no
  leen secretos. Una herramienta que no se puede cargar es un error visible de la repetición.
- Después aplica `_use_last_reply` (la repetición sin texto repite la última respuesta) y corre los chequeos.

La cola corre en la app (`agent_tests_loop`), una corrida a la vez, con hasta `AGENT_TESTS_CONCURRENCY` turnos al LLM
en paralelo (default 2) y 90 s por turno. Al arrancar, las corridas `running` sin pedido de cancelación pasan a
`failed` («se reinició la app»): no se repiten tokens. No descuenta minutos ni suma tokens a la conversación de
origen.

**Cancelar:** una corrida en cola pasa a `cancelled` en el acto y la cola la salta. Una en curso recibe el pedido
(`cancel_requested_at`) y un vigía de la cola lo mira en cada tick (`AGENT_TESTS_TICK_SECONDS`, 2 s): no se manda
ningún turno nuevo y los que ya están en el LLM terminan (como mucho `AGENT_TESTS_CONCURRENCY`, hasta 90 s). Queda
`cancelled` con `done` y los `results` de lo que alcanzó a correr; la variante guarda de `total` las repeticiones
ejecutadas. Un pedido que llega con todo corrido termina `done`. Si el agente se borra en el medio, la corrida se
corta igual; si la app se reinicia, una `running` con pedido queda `cancelled`.

Una cancelada no entra en el `pasa X/N` de la lista ni en el historial del caso: esas consultas solo miran las
`done`.

**Topes:** 30 casos por agente, 10 repeticiones por corrida, 30 corridas por hora por cliente, 200 mensajes y 256 KB
por caso, 20 resultados de herramienta de hasta 50.000 caracteres. Se guardan las últimas 30 corridas por agente.

## Afuera

Consultar herramientas reales, juez LLM, casos creados desde cero, correr casos en el worker de voz y los agentes
`external`. Se puede probar el LLM de desarrollo; no se puede probar en local la carga junto a llamadas reales.

## Deploy

Solo `app` (`make up-app`: migra y recrea; no corta llamadas). `agent` no se recrea. Vuelta atrás: `git revert` y
`make up-app`; las tablas quedan sin uso. `AGENT_TESTS_CONCURRENCY` es opcional (default 2).
