# Equipo y telefonía

El equipo del cliente (personas, áreas, horarios) atiende llamadas de dos formas: el agente le **deriva** una
llamada en curso (transferencia atendida) o el número lo **atiende el equipo** sin agente; además, el equipo
**llama** desde el panel o la app `telefono.` con el número de la empresa. Todo queda en Conversaciones, con
transcripción, audio por frase, minutos y eventos. Una derivación también puede avisar por WhatsApp a las personas del
equipo, y por WhatsApp de texto se rota entre ellas con plantillas ([WHATSAPP.md](WHATSAPP.md#derivación-a-personas-del-equipo)).

Estado: en producción (derivación desde el 23-oct-2026; llamadas directas desde el 27-oct-2026; app `telefono.`
desde el 28-oct-2026). La derivación está probada con llamadas reales en producción (30-oct-2026); las llamadas
directas y la entrante al equipo, todavía no. Plan: `tiers.max_team_members` (`TIER_HAS["team"]`; Free 0,
Mostrador 1, Sucursal 5, Interno sin tope) y `tiers.direct_calls` (`TIER_HAS["direct_calls"]`; todos menos Free; la
saliente necesita además `outbound_calls`).

## Modelo de datos

| Tabla / columna | Qué es | Migración |
|---|---|---|
| `team_members` | Persona del cliente: `name`, `phone` (E.164 argentino), `user_id` (usuario del panel, opcional), `active`, `whatsapp_notify` (le llegan por WhatsApp, a su `phone`, los avisos y la rotación). Necesita teléfono o usuario | 0023, 0042, 0048 |
| `handoff_areas` | Área ("Ventas"): `description`, `active`, `strategy` (`sequential`/`round_robin`, con `last_member_id`), `ring_seconds` (20), `schedule`, `fallback` (`take_message`), `on_person_hangup` (`resume`/`end`), `return_digits` (`2`), `messages` (JSON, pisa los default); a qué área pasa fuera de horario (`after_hours_area_id`) o si nadie acepta (`no_answer_area_id`, del mismo cliente y no ella misma); `delivery` (`call` o `whatsapp`: solo aviso) y `whatsapp` (`account_id`, `template`, `call_template`, `wait_seconds`) | 0023, 0048 |
| `handoff_area_members` | Personas del área, con `position` | 0023 |
| `events` | Línea de tiempo: `client_id`, `at`, `type`, `actor`, `conversation_id`, `area_id`, `team_member_id`, `data` | 0023 |
| `tiers.max_team_members` | Tope de personas (`NULL` sin tope, `0` no incluido) | 0023 |
| `handoff_legs` | Un tramo por intento a una persona: `area_id` (nulo en las entrantes al equipo), `team_member_id`, `phone`, `result` (también `whatsapp_sent` e `interrupted` en la rotación por WhatsApp), `sip_status`, `created_at`/`answered_at`/`connected_at`/`ended_at`, `billed_seconds`, `wamid` (la plantilla enviada; único) | 0024, 0048 |
| `call_logs.user_id`, `answered_by` (`agent`/`team`), `opted_out_confirmed` | Quién llamó o atendió; quién atendió la entrante; se llamó a una baja con confirmación | 0039 |
| `phone_numbers.answer_mode` (`team`/`agent`), `ring_first` (`phone`/`panel`), `ring_seconds` (5-60, 20), `schedule`, `team_fallback` (`agent`/`voicemail`/`hangup`), `team_fallback_message` | Quién atiende el número y cómo (default `agent`, 0045) | 0039 |
| `phone_numbers.strategy` (`sequential`/`round_robin`, default `sequential`), `last_member_id` (FK `team_members`, SET NULL) | Orden de los celulares del número, como en las áreas: la última que atendió en su celular | 0050 |
| `phone_number_members` | Personas del número, en orden | 0039 |
| `user_presence` | `user_id`, `client_id`, `last_seen`: Disponible en el panel | 0039 |
| `call_rings` | Timbre por usuario y entrante en el panel: `status` `ringing`/`answered`/`declined`/`cancelled` (único por conversación y usuario) | 0039 |
| `tiers.direct_calls`, `clients.direct_recording_notice` | Función del plan; aviso de grabación en las directas (apagado) | 0039 |

- `CallMode.directa` (saliente de una persona) es un valor de `call_logs.mode` (texto, sin cambio de esquema). La
  entrante al equipo sigue siendo `entrante`, con `answered_by=team` y la conversación sin agente.
- En la definición del agente (versionada): `handoff.areas` (`area_id` y `when`, hasta 10, sin repetir) y
  `handoff.hold_music` (`enabled`, `track` = `default` o un `.ogg` de `storage/hold-music/`, `volume` 0,05-1,
  default 0,3). `external.on_errors` puede ser `transfer:<area_id>` de una de esas áreas. `workflows` (herramientas
  automáticas antes y después de la conversación) está en [HERRAMIENTAS.md](HERRAMIENTAS.md).
- En los mensajes de la conversación: `Message.at` (hora), `handoff_leg` (tramo) y `person` (nombre de la persona;
  el panel muestra "Ana (equipo)").
- Horario (`schedule`, el mismo en áreas y números): `{tz, week: {mon: [["09:00","18:00"]], ...}, closed:
  ["AAAA-MM-DD"]}`; `null` = siempre. Validado en `services/handoff.validate_schedule`.

## API

Todo bajo `/api/v1`. La UI usa la misma API; el MCP tiene una herramienta por fila (`app/mcp/catalog.py`).

| Ruta | Qué hace | MCP |
|---|---|---|
| `GET/POST /team`, `PATCH/DELETE /team/{id}` | Personas del equipo, con `whatsapp_notify` | `list_team`, `create_team_member`, `update_team_member`, `delete_team_member` |
| `GET/POST /handoff-areas`, `GET/PATCH/DELETE /handoff-areas/{id}` | Áreas con miembros, horario, mensajes, rutas y `whatsapp`. Borrar un área que usa un agente o a la que pasa otra: 409 `area_in_use`. `after_hours_area_id`, `no_answer_area_id` y `whatsapp` en `null` quitan la ruta o las plantillas. Un mensaje con una variable no admitida o largo da 422 con `detail` (la clave) y `errors[{path: "messages.<clave>", message}]` | `*_handoff_area`, `list_handoff_areas` |
| `GET /handoff-areas/defaults` | Mensajes por defecto, sus variables, y qué mensajes salen antes de aceptar (`pre_accept_messages`) con las únicas variables que admiten (`pre_accept_variables`: `area`, `persona`, `horario`) | `get_handoff_area_defaults` |
| `GET /hold-music` | Temas de espera (`default` y los `.ogg`) | `list_hold_music` |
| `GET /events` | Eventos por `conversation_id`, `type` (exacto o prefijo `handoff.`), `since`/`until`, cursor `after_id` | `list_events` |
| `POST /direct-calls` | Saliente directa `{contact_id \| phone, from_number_id?, confirm_opted_out?, user_id?}` → `{conversation_id, room, status, livekit_url, token?, join_url?}` | `start_direct_call` (destructiva) |
| `POST /direct-calls/{id}/join` | Token nuevo para volver a entrar (mismo usuario, llamada activa) | — |
| `POST /direct-calls/{id}/answer`, `/decline` | Atender o rechazar una entrante en el panel | — |
| `PUT /me/presence` `{available}`, `GET /me/ringing` | Pulso de Disponible; entrantes que le suenan | — |
| `GET /team/presence` | Quién está Disponible u ocupado | `list_team_presence` |
| `GET/PUT /clients/{id}/direct-call-settings` `{recording_notice}` | Aviso de grabación en las directas | `get_/update_direct_call_settings` |
| `PATCH /phone-numbers/{id}` | `answer_mode`, `member_ids` (reemplaza, en orden), `strategy`, `ring_first`, `ring_seconds`, `schedule`, `team_fallback`, `team_fallback_message` | `route_phone_number` |
| `GET /calls` | Filtros `mode`, `user_id`, `answered_by`, `phone`, `contact_id`; `CallOut` con `user_id`, `user_name`, `answered_by`, `opted_out_confirmed`, `contact_id`; el detalle trae `call.team` (`answered`, `person`, `fallback`) | `list_calls`, `get_call` |
| `POST /calls/{id}/hangup` | Cortar (también las directas) | `hangup_call` |
| `GET /reports/transfers` | Panel de derivaciones (Reportes > Transferencias, `advanced_reports`); `/reports/calls` separa agente, directa y equipo, por usuario | `get_report_*` ([REPORTES.md](REPORTES.md)) |

Errores de las directas (`app/services/direct_calls.py`, `limits.py`, `legal_gate.py`, `phone_numbers.py`):

| Código | Cuándo |
|---|---|
| 429 `direct_calls_not_in_plan` | El plan no la incluye (llamar, atender, poner un número en `team`) |
| 403 `terms_pending` | El cliente no aceptó condiciones y privacidad `2026-10-28` o posteriores |
| 403 `support_read_only` | Admin en "ver como cliente": no llama, no atiende ni se pone Disponible |
| 403 `panel_user_required` | Atender, rechazar, volver a entrar y presencia con API key o admin sin cliente |
| 422 `user_required` / `invalid_user` | `POST /direct-calls` por API key sin `user_id` o con uno que no es usuario activo del cliente. Por OAuth del MCP llama el usuario que autorizó |
| 409 `opted_out` | Contacto dado de baja sin `confirm_opted_out: true` |
| 403 `blocked_number`; 409 `no_phone_number`; 429 `number_suspended` | Número bloqueado; el cliente sin números; el elegido suspendido por el plan |
| 429 `no_channel` y los de cuota (`outbound_minutes`, ...) | Sin canal de Anura libre o sin minutos |
| 403 `not_your_call`; 409 `call_not_active`, `already_answered`, `not_ringing` | `join` de otro usuario o llamada terminada; `answer` tarde o ya rechazada |
| 422 `members_required`, `agent_required` | Número en `team` sin personas; respaldo `agent` sin agente en el número |

## Flujo

### Derivación (`transfer_call`)

Código: `app/voice/handoff.py` (`Transfer` es la lógica, `RoomLine` el lado de LiveKit), `app/voice/listen.py`
(captura y STT por frase, común con las directas), `app/services/handoff.py` (áreas, horario, orden, mensajes),
`app/llm/platform_tools.py` (herramienta).

1. Al empezar la llamada, `services/handoff.call_areas` deja las áreas del agente en `Progress.handoff_areas`. El
   modelo ve `transfer_call` con `area` como `enum` de los nombres; la descripción lleva cada área con su `when`,
   su horario y si atiende ahora. Vale para todos los agentes, también con `external`. La respuesta que derivó
   guarda el área (`Message.handoff`) y el historial del LLM la reconstruye como `tool_calls` + resultado `tool`
   (`prompt.classic_history`; con Anthropic queda solo el texto); los avisos que siguen van en otro mensaje. Sin
   eso el modelo veía "te paso con X" sin herramienta y en la segunda derivación no la llamaba.
2. El worker dice lo que el modelo escribió en ese turno (si no dijo nada, el mensaje `transfer`) y revisa el
   área (activa, en horario, con miembros con teléfono) y `quota.handoff_check` (cliente activo, minutos
   salientes, canal libre). Si no se puede: evento `handoff.unavailable` y el mensaje que corresponde.
3. Música de espera solo al cliente (`BackgroundAudioPlayer`, tema y volumen del agente) mientras pide el resumen
   del whisper al LLM del turno (JSON `{"resumen"}`, sin razonamiento; si tarda más de 4 s o falla: "una
   consulta").
4. Llama a cada miembro (`services/handoff.candidates`: orden o round robin, en horario) con
   `create_sip_participant`, el timbre del área y el número de la empresa como caller ID (el DID por el que entró
   o salió; en WhatsApp y web, el primero del cliente). Identidad `persona-<n>`; los permisos de pistas se fijan
   antes de marcar, así el cliente no oye el timbre ni el whisper.
5. Al atender, en paralelo: STT de los primeros 3 s contra las frases de buzón (`app/campaigns/voicemail.py`) y el
   whisper solo a la persona. Después, `HANDOFF_CONFIRM_SECONDS` (8) para marcar 1. Buzón: `machine`; otra tecla,
   cortar o no marcar: `not_confirmed`; siguiente miembro.
6. Con el 1: conecta las dos pistas y el worker queda en **modo escucha** (sin LLM ni TTS): VAD + STT de cada lado
   en la conversación (`handoff_leg`, `person`) y un WAV por frase si el agente tiene `record_audio`. El LLM ve ese
   tramo como mensajes con su rol y nombre.
7. Termina con: el código de vuelta del área (`return_digits`, `2`) → el agente vuelve con `resume`; la persona
   corta → `resume` o `goodbye` y corta, según `on_person_hangup`; el cliente corta → se borra la room; sin
   minutos salientes.
8. Si nadie atiende: `busy` si el último intento dio ocupado, si no `no_answer`. El texto queda en la conversación
   y el modelo toma el mensaje en el turno siguiente (regla de la plantilla, no del código).

No derivan: loadtest, campañas (metadata `handoff` en `services/calls.py`), la respuesta por WhatsApp a una campaña,
agentes sin áreas (por WhatsApp de texto, sin áreas con plantilla) y la demo de la landing salvo con `DEMO_HANDOFF=true`.
El WhatsApp de texto deriva por su cuenta ([WHATSAPP.md](WHATSAPP.md#derivación-a-personas-del-equipo)).

Mensajes por área (`DEFAULT_MESSAGES` en `app/services/handoff.py`; variables `{{area}}`, `{{persona}}`,
`{{cliente}}`, `{{resumen}}`, `{{horario}}`, `{{nombre}}` y las que traiga la herramienta de «Antes de la conversación»
del agente, por su nombre; hasta 500 caracteres). Las de la derivación (`area`, `persona`, `cliente`, `resumen`,
`horario`) no las pisa una variable del pre-call, una que falta queda vacía y `{{vars.x}}` no vale acá:

| Clave | Default |
|---|---|
| `transfer` | "Te paso con {{area}}, un momento por favor." |
| `whisper` | "Derivación de {{area}}: {{resumen}}. Marcá 1 para atender." |
| `no_answer` | "No pude comunicarte con {{area}} en este momento. Si querés, te tomo el mensaje y te contactan más tarde." |
| `busy` | "En este momento {{area}} está ocupado. Podés volver a llamar en 10 minutos, o te tomo los datos y te contacta alguien del equipo." |
| `after_hours` | "{{area}} atiende {{horario}}. Te tomo el mensaje y te contactan." |
| `resume` / `goodbye` | "¿Te puedo ayudar con algo más?" / "Gracias por comunicarte, que tengas un buen día." |
| `notified` | "Ya le avisé a {{area}}. Te van a contactar." (área de aviso) |
| `post_call_failed` | "No se pudo confirmar el registro." (en lugar de la nota del post-call, por texto) |
| `operator_ack` | "Recibido. Estamos confirmando, te paso los datos en un momento." (al operador que tocó, por texto) |
| `operator_contact` | "Contacto: {{nombre}}, {{cliente}}. Motivo: {{resumen}}. Ya podés responderle desde tu WhatsApp." |
| `accepted` | "{{persona}} recibió tu pedido y te va a contactar. Lo que escribas acá también le llega." (a la persona, por texto) |
| `relay_failed` | "No pude hacerle llegar tu mensaje a {{persona}}. Escribime de nuevo si necesitás avisarle a otra persona." |
| `tap_wait` / `tap_taken` / `tap_closed` | "Estamos confirmando, te paso los datos en un momento." / "Ya la tomó {{persona}}." / "Esta solicitud ya se cerró." (respuestas al toque) |

`operator_ack`, `tap_wait`, `tap_taken` y `tap_closed` salen **antes de que alguien acepte**: un operador que no tomó el
pedido no ve datos de la persona, así que solo admiten `{{area}}`, `{{persona}}` y `{{horario}}`; con otra variable, la
API responde 422 (`errors` con `path` `messages.<clave>`) y la UI marca el campo.

### Rutas, avisos y WhatsApp al equipo

Código: `Transfer` en `app/voice/handoff.py` (voz) y `app/whatsapp/team_notify.py` (envío de plantillas, común a voz y
texto).

- **Rutas:** `Transfer.run` es un bucle sobre las áreas con un conjunto de visitadas. Fuera de horario sigue por
  `after_hours_area_id`; si nadie acepta, no hay personas, no hay canal o faltan minutos salientes, por
  `no_answer_area_id`. La música sigue entre pases y el mensaje (`no_answer`, `after_hours`) sale solo al final. Un ciclo
  se corta al volver a un área ya visitada, y una ruta a un área inactiva o de otro cliente se ignora. Cada pase emite
  `handoff.rerouted`, no `handoff.unavailable`; sin rutas, todo queda como antes. El modelo ve un área cerrada que
  redirige como "atiende ahora". Un rango de horario no cruza la medianoche: para cubrir la noche, el área diurna pasa
  fuera de horario a un área sin horario (`schedule: null`).
- **Área de aviso** (`delivery=whatsapp`, por voz o por texto): no llama ni espera aceptación. Manda una plantilla a
  **una** persona, la primera de las candidatas con «Recibe WhatsApp» (si Meta la rechaza, a la siguiente), y el agente
  dice `notified` solo si salió; si no, sigue por `no_answer_area_id` o dice `no_answer`. Por voz corre en una tarea
  propia que sobrevive a la derivación: si el cliente corta antes o durante el envío, el aviso sale igual (de mejor
  esfuerzo: `finalize` espera esas tareas hasta 8 s). Antes de enviar se relee a cada persona; quien se fue se saltea, y si
  no se intentó con nadie el resultado es `no_members`, y si la relectura falla, `internal` y no se envía.
- **Complemento de la llamada** (`call_template`, sin botón): a cada persona a la que se llama, una vez por derivación, sin
  demorar el marcado. Va sin botón para que no toquen «Aceptar» en vez de atender.
- **Plantillas** (`handoff_areas.whatsapp`): `params` es una lista ordenada (Meta recibe por posición): `area`, `persona`,
  `cliente`, `resumen`, `horario` o cualquier nombre `[a-z][a-z0-9_]*` de una variable del pre-call; sin valor va `-`.
  `cliente` (el teléfono) solo en la plantilla de un área de aviso: se rechaza en `call_template` y en la `template` de un
  área de llamada, porque antes de aceptar no se entrega el teléfono. Con menos de 8 dígitos (caller oculto), `cliente`
  va `-`. El resumen del LLM (hasta 4 s) solo se pide si la plantilla lo lleva. El envío usa la cuenta del área, que tiene
  que ser del cliente, estar activa y conectada, con plan con WhatsApp; tope de 20 s. Si falla, queda
  `handoff.whatsapp_failed` con el motivo y la derivación sigue: nada de esto lanza.
- **Datos del pre-call en la voz:** los mensajes y las plantillas leen `progress.tool_vars` en cada área. Un whisper como
  `Derivación de {{area}}: {{resumen}}. {{nota_operador}}. Marcá 1 para atender.` le dice al operador quién es y si está
  al día; **no oye si se cobró**. Un mensaje `whisper` con `{{cliente}}` da el teléfono antes del 1 (comportamiento previo).
- **Post-call:** al marcar 1 y conectar, la derivación arma el post-call `handoff_accepted` ([HERRAMIENTAS.md](HERRAMIENTAS.md)).
  Un área de aviso no lo arma.
- **Reportes:** el pase a un área de llamada no suma como pedida en esa área; la emergencia cuenta una vez, donde terminó.
  A un área de aviso no es un pase: el pedido quedó sin atender y esa área lo cuenta ([REPORTES.md](REPORTES.md)).
- **Por texto:** `transfer_call` solo con áreas con `template`; la rotación y el reenvío están en
  [WHATSAPP.md](WHATSAPP.md#derivación-a-personas-del-equipo).
- **Límite aceptado, voz:** un operador desactivado mientras suena la cadena todavía puede ser llamado, oír el whisper con el
  resumen y recibir la plantilla con el resumen y las variables del pre-call (nunca `cliente`). Sale de leer el código; no
  se reprodujo.

### Saliente directa

Código: `app/services/direct_calls.py`, `app/api/routers/direct_calls.py`, `app/voice/direct.py` (rama al
principio de `entrypoint` en `app/voice/worker.py`), `web/src/features/phone/`.

1. Un usuario aprieta **Llamar** (contacto o número) y elige el número de salida. `POST /direct-calls` valida
   (plan, condiciones, soporte, bloqueado, baja), admite con `quota.admit(..., CallMode.directa)`, crea la
   conversación sin agente y `call_logs.user_id`, despacha el worker y devuelve token de LiveKit. Por API key o
   MCP, en vez de token, `join_url` = `<APP_URL>/telefono/llamada/<id>`: lo abre ese usuario con su sesión
   (click to call desde un CRM o el agente de IA del cliente).
2. El worker espera al usuario en la room (`user-<user_id>`): 30 s desde el panel, 120 s por API/MCP; si no entra,
   `fallida` / `user_not_joined`. Después marca al contacto (`contact`) con un timbre de 40 s y publica el estado
   por datos de la room (tema `call_status`: `joining`, `dialing`, `ringing`, `active`, `ended` con `result`).
3. Al atender: `en_curso`, minutos salientes desde ahí, el aviso de grabación si el cliente lo prendió (WAV
   sintetizado una vez en `storage/notices/<voz>.wav`). Cada frase es un mensaje con su WAV: el contacto como
   `user`, el usuario como `assistant` con `person`; también al panel por el tema `transcript`.
4. Termina cuando corta cualquiera, por la duración máxima o sin minutos. Si el usuario sale (recarga, red), se lo
   espera `PANEL_REJOIN_GRACE_SECONDS` (30) para **Volver a entrar**. Al salir alguien se le pasa silencio al VAD
   y se esperan 3 s el STT de su última frase.

Resultado en `call_logs`: atendida → `finalizada` (`customer_hangup`, `person_hangup`, `max_duration`,
`quota_exhausted` o `hangup_by_user`); cortada antes de que atiendan → `cancelada`; sin atender → `fallida`
(`user_not_joined`, `no_answer`, `busy`, `sip_call_failed` con `sip_status`); el worker sin poder arrancar →
`fallida` / `worker_error`.

### Entrante al equipo

1. `services/calls.start_inbound` ve `answer_mode=team` y arma `InboundCall.team` (`TeamRoute`: personas activas
   con celular o usuario, en orden o rotadas, `ring_first`, `ring_seconds`, horario, respaldo). Sin personas, sin
   el plan o sin las condiciones aceptadas, la llamada va al agente del número, como siempre.
2. El worker toma la rama directa (sin LLM): aviso de grabación si está prendido, música y hace sonar según
   `ring_first`:
   - `phone`: a cada persona en su celular, en orden (`Transfer.run_team`, sin área ni código de vuelta; tramos en
     `handoff_legs` con `area_id` nulo y eventos `handoff.*`). Whisper: "Llamada a {{linea}} de {{cliente}}.
     Marcá 1 para atender." Si nadie atiende, en el panel a los Disponibles.
   - `panel`: a todos los Disponibles a la vez (`call_rings`, atiende el primero); si nadie atiende o no hay nadie,
     a los celulares en orden.
   - Una persona sin celular suena solo en el panel; una sin usuario, solo en el celular.
   - El orden de los celulares es `strategy`: `sequential`, siempre desde la primera; `round_robin`, desde la
     siguiente a `last_member_id` (`handoff.rotate`, la misma de las áreas; si ya no está en el número, desde la
     primera). El panel suena a todos a la vez, sin orden.
3. Atiende alguien: se apagan los demás timbres, se conectan y se graba y transcribe como la saliente. Si corta
   la persona, termina (no hay agente al que volver). Atendida en el celular, queda el `user_id` de la persona si
   tiene usuario y se anota en `phone_numbers.last_member_id` (con cualquier `strategy`; solo si el número sigue
   siendo del cliente y la persona existe; un error al anotar se loguea y la llamada sigue). Atender en el panel
   no cuenta como la última.
4. Nadie atiende (`team_no_answer`) o fuera de horario (`after_hours`): evento `team.fallback` y el respaldo:
   - `agent`: `direct_calls.fallback_to_agent` pasa la conversación al agente del número (`answered_by=agent`) y el
     worker arranca la sesión en la misma room; con el agente archivado, toma el mensaje.
   - `voicemail` (default): mensaje (el del número o "Ahora no podemos atenderte. Dejá tu mensaje y te llamamos.")
     y graba hasta 120 s con transcripción.
   - `hangup`: mensaje y corta.
5. Las llamadas de WhatsApp al mismo DID siguen el mismo ruteo; una regla de `wa_routes` que elige agente manda.
   La entrante usa `VLLM_TTS_VOICE` (no hay voz por cliente).

### Presencia y timbre en el panel

- **Disponible:** switch en la barra de llamada. Pulso cada ~20 s (`PUT /me/presence`); sin pulso por
  `PRESENCE_TTL_SECONDS` (60) deja de estarlo. Ocupado = tiene una llamada activa con su `user_id`.
- El panel consulta `GET /me/ringing` cada ~2 s mientras está Disponible. El pulso y el sondeo corren en un Worker
  (`web/src/features/phone/ticker.ts`) porque Chrome frena los timers de una pestaña oculta a uno por minuto.
- `answer` toma el timbre con un `UPDATE` condicional (solo si sigue `ringing`). `answer`, `ring_panel`,
  `cancel_rings` y `release_answer` bloquean primero la fila de la llamada (`FOR UPDATE`) y después `call_rings`:
  mismo orden, sin deadlock. Si atendió y su navegador no entra en `PANEL_JOIN_GRACE_SECONDS` (10), la llamada se
  libera y si entra tarde se lo saca. Un timbre de más de `RING_MAX_SECONDS` (90) no suena ni se atiende.

### UI

- **Tu equipo** (`web/src/features/team/`): personas y áreas con horario, orden, mensajes, tecla de vuelta y qué
  hacer si la persona corta; punto verde de presencia. La persona tiene el interruptor **Recibe WhatsApp** (necesita
  teléfono). El área elige **Cómo se avisa** (**Se llama** o **Solo aviso por WhatsApp**), **Fuera de horario, pasa a**,
  **Si nadie acepta, pasa a** y su WhatsApp: el número que envía, la plantilla (de rotación con botón de respuesta
  rápida, de la llamada o del aviso, sin botón), el valor de cada `{{n}}` (una variable base o un dato de la herramienta
  de «Antes de la conversación»; si no llega, va «-») y la espera por persona. En un área de aviso no se validan ni se
  envían como inválidos el timbre, la tecla ni los mensajes ocultos: se conserva lo guardado. La ayuda de los cuatro
  mensajes de antes de aceptar dice qué variables admiten.
- **Teléfono del equipo** (Canales, `/telefono`, `PlanGate direct_calls`): agenda con búsqueda, "marcá un número",
  bajas con confirmación, bloqueados apagados; `/telefono/llamada/:id` entra a una llamada creada por API o MCP.
- **Barra de llamada** (`CallProvider` en `AppLayout`, hooks `useDirectCall` y `usePresence`): estados, silenciar,
  teclado DTMF (`publishDtmf`), transcripción en vivo, Atender/Rechazar. El panel sale de la room en `pagehide`, no
  con `disconnectOnPageLeave` de LiveKit (cortaba en `beforeunload` cancelado y en `freeze` del celular).
- **Números:** "Atiende: el agente / el equipo" con personas, **En orden** o **Rotativa**, dónde suena primero, timbre, horario y respaldo.
  **Mi cuenta:** "Avisar que la llamada se graba" para las directas. **Tus clientes:** Llamar (directa) junto a
  Llamar con un agente. Ver [GUIA_UI.md](../GUIA_UI.md).

### App `telefono.`

El mismo teléfono (saliente, atender, presencia, timbre, volver a entrar, tonos, subtítulos, guardar contacto) en
una página tipo app de teléfono de Android, para el celular: Favoritos (en el navegador), Recientes
(`GET /calls?user_id=`), Contactos, búsqueda, ficha, teclado (`+` manteniendo el 0, sin `*`) y menú de cuenta. Sin
backend de llamadas propio: usa la API y el `CallProvider` de siempre, con las mismas reglas.

- Código: `web/telefono.html` (entrada aparte del build), `web/src/telefono/`, `web/public/telefono.webmanifest`;
  `app/api/phone_app_host.py`: `GET /movil` en cualquier host y, con el Host de `PHONE_APP_BASE_URL`, `/` es la app
  y solo pasan `/api/v1/` (sin docs), `/assets/` y los íconos; lo demás, 404.
- Sesión: la cookie no lleva `Domain`. `POST /auth/switch {target: phone|panel}` da una URL con un pase de un solo
  uso (60 s, `jti` en memoria del único `app`) en el fragmento `#sesion=`; el destino lo canjea con
  `POST /auth/switch/redeem`. Entrando directo sin sesión, `GET /auth/switch/start` prueba una vez con la del
  panel. Código en `app/services/session_switch.py`, `web/src/features/auth/switch.ts`.
- `telefono` sin tilde: un subdominio con "é" es `xn--...` y complica el certificado.

## Reglas y trampas

- **DTMF `*` en Anura:** marcar `*9` hace que Anura corte la otra llamada activa de la cuenta (~0,3 s, 4 de 4) y a
  veces el `*` no llega. Los códigos para personas van con `#` o un dígito solo (`#9` y `1` probados); nunca `*`.
  Un cliente final que marca `*` + dígito durante una derivación podría cortar el tramo de la persona.
- **Canales de Anura: 10** (`ANURA_CHANNELS`). `quota.busy_channels` cuenta las llamadas activas `entrante`,
  `saliente` y `directa` más los tramos de `handoff_legs` abiertos. Una derivada ocupa 2; una saliente directa, 1;
  una entrante al equipo, 2 si atiende en el celular y 1 en el panel. Con ~5 derivaciones a la vez no quedan
  canales. Sin canal: la derivación no se intenta (`handoff.unavailable`), la saliente da `no_channel` y la
  entrante va al respaldo.
- **Minutos:** el tramo del cliente consume los de su tipo toda la llamada; el de la persona, salientes desde que
  atiende (`quota.handoff_seconds` suma `handoff_legs`). Ej.: 3 min con la IA y 5 con la persona = 8 entrantes y
  5 salientes. Sin atender, ocupado, buzón o sin confirmar no se descuentan (Anura sí cobra un minuto si atendió un
  buzón). Con 0 salientes en el plan no se deriva. `directa` está en `MINUTE_MODES` como `outbound`; en el panel la
  entrante del equipo no gasta salientes ni canal extra.
- **Buzón con Claro (spike con dos celulares):** sin atender, el buzón atiende a los 33,5 s; con un timbre por
  miembro de 20-25 s se corta antes, sin minuto de Anura. Rechazar (doble toque en iPhone) no da ocupado: Claro lo
  manda al buzón, que atiende a los 5,4 s, y el detector por frases lo marcó `machine`. El 486 no se ve nunca con
  Claro. Sin atender, `create_sip_participant` falla con `sip request timed out` (nuestro timeout), no con un código
  de Anura.
- **Tiempos medidos (spike):** timbre hasta atender 6-13,6 s; whisper hasta el 1 6-10,7 s más 3 s de escucha: el
  cliente espera ~18 s desde "te paso". La persona entra a la room al empezar a sonar (8-11 s antes de atender):
  hay que aislarla al publicarse su pista, no al atender (`update_subscriptions` se aplica en 2-3 ms).
- **`AudioSource`:** cancelar una tarea en medio de `capture_frame` deja la fuente en `InvalidState` y el audio
  siguiente no sale. La música se corta con una bandera entre frames y `clear_queue()`.
- **Grabación:** la derivación graba el tramo humano solo con `record_audio` del agente (aviso opcional
  `recording_notice`); sin eso, transcribe sin audio. Las directas y las entrantes del equipo graban y transcriben
  **siempre**, sin mirar `record_audio`; el aviso es `clients.direct_recording_notice` (apagado) y avisar y tener el
  consentimiento es del cliente (condiciones `2026-10-28`). ~1,9 MB por minuto de habla en `storage/recordings/`.
- **Gate legal:** `legal_gate.client_accepted_direct_calls` pide, de cada documento, `MIN_DIRECT_CALLS_VERSION`
  (`2026-10-28`) o posterior, aceptada por cualquier usuario del cliente. Una versión nueva no apaga la función. Sin
  aceptar: 403 `terms_pending` y las entrantes de números `team` van al agente. La UI lo muestra con link al modal
  (`/auth/me` trae `legal_pending`).
- **Dos entrantes a la vez** en un número `round_robin` leen el mismo `last_member_id` y arrancan por la misma
  persona, como en las áreas (sin lock en la admisión de la llamada).
- **Números nuevos o liberados arrancan en `agent`** (0045), con `strategy=sequential` y sin `last_member_id`:
  atienden apenas se les elige el agente; el equipo se elige a mano. Un `team` que se queda sin personas manda la
  entrante al agente del número, y sin agente no atiende nadie (`number_without_agent`).
- **Transcripción por frase:** si hablan a la vez, los mensajes quedan ordenados por fin de frase. Sin auriculares
  la voz del contacto puede volver al micrófono. Con la pantalla bloqueada iOS puede cortar el micrófono del panel:
  para recibir, el celular (default) es lo que anda siempre.
- **Contestador de la saliente directa:** los códigos SIP del contacto salen de `campaign_calls.classify_error`,
  sin verificar con Anura.
- **Demo de la landing:** con `DEMO_HANDOFF=true` (prendida), cualquiera de internet hace sonar al equipo de
  `atentina_comercial`, con los topes de la demo (4 llamadas por hora y 10 por día por IP, 120 min diarios) y
  `DEMO_CALL_MAX_SECONDS` (180 s) incluyendo la charla con la persona.
- Un área que usa un agente no se borra (409). Si se borra un `.ogg` en uso, la llamada usa `default` pero el
  agente no se guarda hasta cambiar el tema.

## Desplegar y probar

- Tests (LLM y teléfono falsos): `tests/test_handoff.py`, `test_handoff_transfer.py`, `test_direct_calls.py`,
  `test_direct_voice.py`, `test_phone_app_host.py`, `test_whatsapp_team_notify.py`, `test_whatsapp_handoffs.py`,
  `test_voice_wiring.py` y `test_migration_0023/0024/0039.py`, en `make test`. La 0050 (`strategy` del número)
  solo agrega columnas; `make migrate-test` la sube y la baja.
- **`make e2e-sip`**: stack aislado (`docker-compose.e2e-sip.yml`, `tests/e2e_sip/`): LiveKit, `livekit-sip` y
  nuestro Asterisk con la config de producción contra un Anura falso, en una red interna sin puertos del host ni
  llamadas reales. Señalización (atiende y marca 1 y 2, ocupado 486, no atiende, buzón, congestión 503, atiende y
  corta, dos tramos aislados), `transfer.py` (`Transfer` y `RoomLine` reales, también la cadena de áreas por `no_answer_area_id`: música continua, sin mensaje intermedio, un solo `rerouted`, corte de ciclos, el whisper con las variables del pre-call y el post-call `handoff_accepted` armado solo si la persona marca 1) y `direct.py` (saliente contra un eco
  del Anura falso y entrante al equipo por celular). El timbre en el panel está solo en los tests con LiveKit falso.
- Desplegar un cambio: `make migrate-test` si hay migración, `make migrate`, `make calls-active && make up-agent`
  (recrea `app` y `agent`; la imagen de `app` compila `web/`).
- App `telefono.`: `PHONE_APP_BASE_URL=https://telefono.atentina.com.ar` en `.env` (diff enmascarado), ruta
  `telefono.atentina.com.ar` → `http://localhost:8011` en el túnel (la crea el usuario) y recrear `app`. Sin la
  ruta, se prueba en `app.atentina.com.ar/movil`.
- Volver atrás la 0039: tiene `downgrade` (probado en `tests/test_migration_0039.py`): `make migrate-down REV=0038`,
  con la imagen que todavía tiene la 0039 y antes de volver el código.
- Rutas, avisos y rotación por WhatsApp (0048 y 0049, con `downgrade`): vuelta atrás en [WHATSAPP.md](WHATSAPP.md#desplegar-y-probar).

## Pendientes

- **Llamada real con dos celulares propios**, revisando cada caso en Conversaciones:
  - saliente directa: atiende, no atiende, ocupado, inválido, corta cada lado, recarga y Volver a entrar, cerrar la
    pestaña, sin minutos, sin canales, baja con y sin confirmar, bloqueado, con y sin aviso;
  - entrante al equipo: celular (marcando 1), no atiende, fuera de horario, los tres respaldos, `phone` y `panel`
    primero con el paso al otro, dos usuarios Disponibles (el segundo ve 409), rechazar, nadie Disponible, el
    WhatsApp del mismo DID y un cliente sin las condiciones aceptadas (va al agente);
  - por API y MCP con `join_url` (el usuario y otro, 403); Free (429) y admin en soporte (403);
  - app `telefono.` en el celular: micrófono con la pantalla bloqueada, eco sin auriculares, salir al cambiar de
    app; y un link a la app desde el Teléfono del panel.
- **Sin probar con LiveKit, Chrome y PostgreSQL reales:** dos que atienden a la vez (locks), Volver a entrar (que
  LiveKit saque la conexión vieja), el silencio al VAD al cortar, el pulso con la pestaña oculta más de 5 min. Los
  tests de directas corren en SQLite (`TEST_DB_DSN` solo cambia el fixture `store`).
- **Eval de `transfer_call`:** no hay escenario en `make eval-llm` que mida si el modelo deriva cuando corresponde
  y no cuando no. También `make mcp-eval` con `start_direct_call` contra `start_call`.
- **CAP corto** de directas y derivaciones mezcladas con llamadas del agente hasta los 10 canales (workers en
  escucha y STT por frase).
- **Retención de grabaciones:** las directas graban siempre y sin retención el disco crece con el uso.
- **Códigos SIP de Anura** (no atiende, ocupado, inexistente) sin verificar con llamadas reales; ocupado y buzón
  en otras operadoras (Personal, Movistar) sin medir. Anura no respondió qué códigos `*` interpreta.
- **Canales de WhatsApp:** las llamadas de WhatsApp cuentan como `entrante` en `busy_channels` aunque no usan un
  canal de Anura: se cuentan de más.
