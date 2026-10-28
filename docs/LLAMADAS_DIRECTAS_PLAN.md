# Llamadas directas: el equipo del cliente llama y atiende sin el agente

27-oct-2026. Parte de la opción C de `docs/mercado/demos/cimepa-telefonia.md` y del "softphone web" de
[`DERIVACIONES_PLAN.md`](DERIVACIONES_PLAN.md), 4.5.

**Estado: desplegado el 27-oct-2026** (migración 0039, `app` y `agent`, landing con las condiciones `2026-10-28`), a pedido, **sin la revisión del abogado ni el aviso por mail con 30 días**. Falta la prueba real (paso 6 de la 14), `make mcp-eval` y el registro del MCP, y el CAP.

| Parte | Estado |
|---|---|
| Backend (fases 1, 3 y 3b): migración 0039, API, presencia y timbre, rama del worker, respaldos | Hecho, con tests (`tests/test_direct_calls.py`, `tests/test_direct_voice.py`, `tests/test_migration_0039.py`) |
| MCP (fase 4): 4 herramientas nuevas y 4 ampliadas, 147 en total | Hecho; falta `make mcp-eval` |
| Prueba SIP aislada | `make e2e-sip` (`tests/e2e_sip/direct.py`): saliente contra un eco del Anura falso y entrante al equipo por celular. El timbre en el panel está solo en los tests con LiveKit falso |
| UI (fase 2), `web/src/features/phone/` | Hecho |
| Documentación (fase 5) | Esta sección y las de `AGENTS.md`, `ARQUITECTURA.md`, `DERIVACIONES_PLAN.md`, `FUNCIONES_POR_PLAN_PLAN.md`, `README.md` y `LLAMADAS_SALIENTES_PLAN.md`; `GUIA_UI.md` también (después de la UI) |
| Landing (sección 10) | `/desarrolladores/docs/api#directas` (con `terms_pending`), `/plataforma/telefono-del-equipo`, menciones en telefonía y home, y "Teléfono del equipo" en los tres planes pagos; `npm run build` en verde, sin publicar |
| Condiciones y privacidad (fase 6) | Texto `2026-10-28` en `app/legal/texts/` y corte por aceptación de esa versión o una posterior (`app/services/legal_gate.py`, 403 `terms_pending`); falta el abogado y el aviso por mail |
| Prueba real y despliegue (fase 7) | Sin hacer: "Cómo desplegar" en la sección 14 |

Dónde el código se aparta del texto de abajo (el contrato de la sección 13 sigue siendo el nombre fijo):

- Por OAuth del MCP, sin `user_id`, llama el usuario que autorizó al agente; con API key sigue siendo obligatorio
  (422 `user_required`).
- Atender, rechazar, volver a entrar y la presencia piden la sesión del panel (403 `panel_user_required` con una
  API key o un admin sin cliente).
- La migración prende `tiers.direct_calls` en los tiers con precio o a medida (`price_ars` mayor que 0 o `NULL`),
  igual que `advanced_reports`; el Free queda apagado.
- Hasta que el cliente acepta las condiciones `2026-10-28` (o una versión posterior), no llama, no atiende ni pone
  un número en `team` (403 `terms_pending`); su entrante a un número del equipo va al agente del número
  (`start_inbound`), como sin el plan. Una versión nueva de las condiciones no lo corta
  (`legal_gate.MIN_DIRECT_CALLS_VERSION`).
- Poner un número en `answer_mode=team` pide el plan (429 `direct_calls_not_in_plan`) y al menos una persona (422
  `members_required`); con respaldo `agent`, un agente en el número (422 `agent_required`).
- `GET /calls` filtra también por `phone` (normalizado a E.164; llamadas y WhatsApp) y `contact_id` (el teléfono
  del contacto): los usan el panel del contacto en Teléfono y el historial de su ficha. `contact_name` (si el agente
  no lo tomó) y `contact_id` salen del contacto de la agenda con ese teléfono, también en el detalle.
- El detalle de una entrante al equipo trae `call.team` (`answered`, `person` que atendió en su celular,
  `fallback` si nadie atendió), del evento nuevo `team.fallback` (respaldo y motivo) y de `handoff.connected`.
- `GET /reports/calls` suma `total` (todas las llamadas: lo que suman `by_type` y `ended`; el KPI "Llamadas") y
  `ended` separa los motivos de las directas (`person_hangup`, `team_no_answer`, `after_hours`, `no_answer`,
  `busy`, `voicemail`, `user_not_joined`, `max_duration`, `quota_exhausted`, `worker_error`).

## 1. Qué es

- **Saliente directa:** un usuario del cliente elige un contacto en el panel y aprieta **Llamar**. Habla desde
  el navegador (micrófono y parlante, como el link para llamar) y el contacto recibe la llamada desde un
  número de Anura del cliente. Ningún agente habla.
- **Entrante directa:** cada número se configura para que lo atienda **el agente** (como hoy, que puede
  derivar con `transfer_call`) o **el equipo**, sin agente: suena en un área y, si nadie atiende o está fuera
  de horario, pasa a lo que el cliente elija (el agente del número, un mensaje grabado o cortar).

Las dos quedan como cualquier llamada: en Conversaciones, con transcripción, audio por mensaje, duración,
resultado y minutos descontados.

## 2. Decisiones (27-oct-2026)

| Tema | Decisión |
|---|---|
| Planes | Todos menos Free (`tiers.direct_calls`) |
| Contactos dados de baja | Se pueden llamar, con aviso: "Este contacto pidió no recibir llamadas" y confirmación. Queda registrado quién confirmó |
| Grabación | **Siempre.** El aviso "Esta llamada está siendo grabada" es opcional, por cliente (apagado por default). La responsabilidad de avisar y tener el consentimiento es del cliente: va en una versión nueva de las condiciones (sección 7) |
| Admin en "ver como cliente" | No llama ni atiende (403 `support_read_only`) |
| Atención por número | Configurable: el equipo (personas asignadas al número, **por defecto**) o el agente. Los números ya ruteados a un agente siguen con el agente |
| Dónde suena el equipo | Configurable por número: primero el celular (**por defecto**) o primero el panel, y si no atiende, el otro |

## 3. Qué se reutiliza

| Pieza | Dónde está | Para qué |
|---|---|---|
| Marcar por Anura con caller ID del cliente | `RoomLine.dial` en `app/voice/handoff.py` | Saliente al contacto; entrante a los teléfonos del equipo |
| Hacer sonar un área (orden, timbre, horario, "marcá 1 para atender", respaldo) | `Transfer` en `app/voice/handoff.py`, `HandoffArea`, `TeamMember`, `handoff_legs` | La entrante directa: es una derivación sin el tramo previo del agente |
| Transcribir a una persona con VAD + STT | `RoomLine._capture` / `_transcribe` (modo escucha) | Transcripción de los dos lados |
| Audio por mensaje y mensajes de una persona | `app/conversation/recordings.py`, `Message.recording`, `Message.person` | El chat del panel los muestra sin cambios ("Ana (equipo)") |
| Entrar a una room desde el navegador | `TestCallPage.tsx` (`livekit-client`), `web/src/llamar/` | El teléfono del panel |
| Admisión, minutos y canales | `quota.admit`, `MINUTE_MODES`, `busy_channels`/`ANURA_MODES` | Topes del tier y los 10 canales de Anura |
| Errores SIP | `campaign_calls.classify_error` | Ocupado, no atiende, falló |
| Bajas y bloqueados | `is_opted_out`, `blocked_numbers` | Aviso en la saliente; corte en la entrante (como hoy) |
| Agenda | `contacts`, `/api/v1/contacts`, `useContacts` | La lista para elegir |

## 4. Saliente directa

1. El usuario aprieta **Llamar** (contacto o número suelto) y elige desde qué número sale.
2. `POST /api/v1/direct-calls` valida (contacto del cliente, bloqueado, plan). Si el contacto está dado de
   baja y no vino `confirm_opted_out: true`, responde 409 `opted_out` y el panel pide confirmación. Admite
   con `quota.admit(…, CallMode.directa)`, crea la conversación **sin agente** (`agent_id` nulo, ya se
   permite) y la fila de `call_logs` con el usuario, despacha el worker y devuelve la URL de LiveKit y un
   token.
3. El navegador entra a la room. El worker espera al usuario (~30 s; si no, `fallida`, `user_not_joined`) y
   marca al contacto con `wait_until_answered=False`, para que el panel muestre el estado SIP
   (`sip.callStatus`: `dialing`, `ringing`, `active`).
4. Al atender: `en_curso`, minutos salientes desde ahí; si el cliente lo prendió, el aviso de grabación (WAV
   pregenerado con la voz del cliente). Por cada frase (fin de habla del VAD) un mensaje: el contacto como
   `user`, el usuario como `assistant` con `person`, cada uno con su WAV.
5. Termina cuando corta cualquiera (botón, contacto, cierre de la pestaña), por el tope de duración o sin
   minutos (`quota_watchdog`). Resultado: `completed`, `no_answer`, `busy`, `failed`.

## 5. Entrante: equipo o agente, por número

### Configuración (pantalla Números del cliente, por número)

```
Número +54 11 5555-0000 · Ventas
Atiende:  (•) El equipo   Personas: [ Ana ✕ ] [ Pedro ✕ ] [+ Agregar]   (en orden)
              Suena primero:  (•) En su celular   ( ) En el panel
              Timbre por persona: [ 20 ] s     Horario: [ L a V 9-18 ▾ ] (opcional)
              Si nadie atiende o fuera de horario:  [ Pasa al agente ▾ ]  (agente / mensaje / cortar)
              Agente de respaldo: [ Atentina comercial ▾ ]
              Mensaje: "Ahora no podemos atenderte. Dejá tu mensaje después de la señal."
          ( ) El agente   [ Atentina comercial ▾ ]   (puede derivar al equipo con sus áreas, como hoy)
```

- `phone_numbers.answer_mode`: `team` o `agent`. **Por defecto, `team`**: un número que se asigna a un
  cliente desde ahora va a las personas asignadas. Los números ya ruteados a un agente quedan en `agent` (la
  migración los marca así; decisión del 27-oct-2026).
- `phone_number_members` (número, miembro de Equipo, orden): las personas asignadas al número. Con `team`,
  hace falta al menos una.
- `phone_numbers.ring_first`: `phone` (default) o `panel`. Suena primero ahí y, si no atiende, en el otro:
  - **`phone`:** a cada persona en su celular (`TeamMember.phone`), en orden; si ninguna atiende, en el panel
    a las que estén **Disponibles**.
  - **`panel`:** en el panel a las que estén Disponibles (a todas a la vez, atiende la primera); si ninguna
    atiende o no hay nadie conectado, a sus celulares en orden.
  - Una persona sin celular solo suena en el panel; una sin usuario del panel (`TeamMember.user_id`), solo en
    el celular.
- `phone_numbers.ring_seconds` (20 por default) y `schedule` (opcional, el mismo formato que las áreas).
- `phone_numbers.team_fallback`: `agent` (el agente del número, `agent_id`, arranca con la apertura y el
  contexto "nadie del equipo atendió"), `voicemail` (mensaje por TTS y graba lo que dice el que llama, con
  transcripción) o `hangup` (mensaje y corta). Default: `voicemail`; `agent` si el número tiene agente.
- WhatsApp (llamadas de Meta al mismo DID): mismo ruteo. La regla por contacto de `wa_routes` sigue mandando
  cuando elige un agente.

### Flujo

1. Entra la llamada: `start_inbound` ve `answer_mode=team`, admite como `entrante` y crea la conversación sin
   agente (`answered_by=team`).
2. El worker toma la rama directa: sin LLM, "Te comunicamos…" (opcional, TTS con la voz del cliente) y música
   de espera, y hace sonar a las personas en el orden de `ring_first`. Reutiliza `Transfer` de la derivación
   (orden, timbre, horario, "marcá 1 para atender" en el celular), con las personas del número en lugar de un
   área y sin resumen del agente. Al celular, el susurro dice la línea y quién llama ("Llamada a Ventas de
   +54 9 11 …, marcá 1 para atender"); en el panel, lo mismo en el timbre.
3. Atiende alguien: se corta el timbre a los demás, se conectan, y transcripción y grabación como en la
   saliente. Si corta la persona, se corta (no hay agente al que volver).
4. Nadie atiende o fuera de horario: respaldo del número.

### Presencia y timbre en el panel

- **Disponible**: switch en la barra de llamada, por usuario. El panel abierto manda un pulso cada ~20 s
  (`PUT /me/presence`); sin pulso por 60 s, deja de estar disponible. Una persona en una llamada está ocupada.
- Timbre: el panel consulta las entrantes que le suenan (`GET /me/ringing`, cada ~2 s mientras está
  Disponible, o SSE) y muestra **Atender** / **Rechazar** con el número, el contacto si está en la agenda y
  la línea. **Atender** pide el token (`POST /direct-calls/{id}/answer`); el primero que atiende se queda con
  la llamada y a los demás se les apaga.
- Costo: en el panel no hay minutos salientes ni canal extra; en el celular, minutos salientes desde que
  atiende y 2 canales de Anura (como la derivación).

## 6. Backend

- **Migración:**
  - `CallMode.directa` (saliente de una persona). La entrante sigue siendo `entrante` y se distingue por
    `conversations.agent_id` nulo o por una columna `call_logs.answered_by` (`agent`/`team`).
  - `call_logs.user_id` (FK a `users`, nulo): quién llamó o quién atendió (en el panel o en su celular, por su `TeamMember.user_id`).
  - `call_logs.opted_out_confirmed` (bool): se llamó a un contacto dado de baja con confirmación.
  - `phone_numbers.answer_mode` (default `team`; los que tienen agente quedan en `agent`), `ring_first`,
    `ring_seconds`, `schedule`, `team_fallback`, `team_fallback_message`.
  - `phone_number_members` (número, miembro, orden).
  - `user_presence` (usuario, último pulso, en llamada): quién está Disponible en el panel.
  - `tiers.direct_calls` (bool): en `true` para todos los tiers salvo Free; en el editor de tiers y en
    `features.TIER_HAS` (además necesita `outbound_calls` para la saliente).
  - `clients.recording_notice_direct` (bool, aviso de grabación en las directas, apagado).
- **Cuotas:** `directa` en `MINUTE_MODES` como `outbound` y en `ANURA_MODES`.
- **API:**
  - `POST /direct-calls` `{contact_id | phone, from_number_id?, confirm_opted_out?}` →
    `{conversation_id, livekit_url, token}`.
  - `POST /direct-calls/{id}/join`: token nuevo para volver a entrar si se recargó la página (el mismo
    usuario, llamada en curso).
  - Cortar: el `POST /calls/{id}/hangup` existente.
  - Números: `PATCH /phone-numbers/{id}` suma `answer_mode`, `members` (ids en orden), `ring_first`, `ring_seconds`,
    `schedule` y `team_fallback`; valida que las personas sean del cliente y tengan celular o usuario del
    panel, que con `team` haya al menos una, y que haya agente si el respaldo es `agent`.
  - Presencia y timbre: `PUT /me/presence`, `GET /me/ringing`, `POST /direct-calls/{id}/answer` y
    `GET /team/presence`.
  - Quién llama: un usuario del cliente. Desde el panel es el de la sesión; por API key o MCP va `user_id`
    (un usuario activo del cliente) y la respuesta trae `join_url`: la página del panel que entra a la llamada
    con la sesión de ese usuario (otro usuario recibe 403). El worker no marca hasta que el usuario entra
    (espera hasta 2 min en las creadas por API o MCP, ~30 s en las del panel). Así un CRM o el agente de IA
    del cliente arman la llamada ("click to call") y la persona habla desde el navegador.
  - El admin en soporte no llama ni atiende (403 `support_read_only`).
- **Worker** (`app/voice/direct.py`): rama al principio de `entrypoint` (metadata `direct` en la saliente;
  `answer_mode=team` en la entrante). Sin `AgentSession` ni LLM: VAD, STT y, para avisos y mensajes, el TTS.
  La captura y la transcripción de `RoomLine` pasan a un módulo común (`app/voice/listen.py`) que usan la
  derivación y las directas. El respaldo `agent` arranca la sesión del agente en la misma room.
- **Grabación siempre:** las directas graban sin mirar `record_audio`. Disco: ~1,9 MB por minuto de habla
  (16 kHz mono); `storage/` ya está en el backup (local y S3 cifrado). Una retención por cliente queda para
  después.
- **Capacidad:** sin LLM, una directa carga solo el STT por frase. Limitan los 10 canales de Anura y los
  minutos. CAP corto mezclada con llamadas del agente antes de desplegar.

## 7. Condiciones y privacidad (con [`TERMINOS_PLAN.md`](TERMINOS_PLAN.md))

- **Condiciones, versión nueva** (archivo nuevo en `app/legal/texts/`, su hash en `tests/test_legal.py`,
  `make legal-sync`): las llamadas que hace y recibe el equipo del cliente por la plataforma se graban y
  transcriben siempre; el cliente es responsable de informar a sus interlocutores y de tener su
  consentimiento (el aviso automático es una herramienta, no lo exime); de llamar a contactos que pidieron no
  recibir llamadas y del Registro Nacional No Llame; y de qué hacen sus usuarios con las grabaciones.
- **Política de privacidad:** hoy la landing dice que no se graba audio (`landing/src/pages/privacidad.astro`).
  Hay que corregirla antes de desplegar: grabación de llamadas, quién es responsable (el cliente) y quién es
  encargado (Atentina), dónde se guardan y por cuánto tiempo.
- Es un cambio importante: se acepta de nuevo en el modal del panel y va el aviso por mail con 30 días. La
  función no se habilita para un cliente hasta que acepte la versión nueva.
- Revisión del abogado, como la versión anterior.
- **Hecho el 27-oct-2026** (sin desplegar; detalle en [`TERMINOS_PLAN.md`](TERMINOS_PLAN.md), sección 8): versión
  `2026-10-28` de las condiciones (resumen y puntos 3, 6, 7 y 10, sin renumerar) y de la privacidad (Grabaciones,
  datos, AWS y conservación), copiadas a la landing. Ninguna otra página de la landing decía que no se graba: lo
  decía el texto de privacidad que muestra `privacidad.astro` ("por defecto guardamos la transcripción, no el
  audio"). Corte en `app/services/legal_gate.py`: sin
  la versión `2026-10-28` (o una posterior) de cada documento aceptada por algún usuario del cliente, llamar, atender y poner un número en el equipo dan
  403 `terms_pending` ("Aceptá las condiciones nuevas para usar el teléfono del equipo") y las entrantes de un
  número del equipo van a su agente. La UI tiene que mostrar ese error con un link al modal (o recargar
  `/auth/me`, que trae `legal_pending`).

## 8. UI (`web/`)

### Pantalla **Teléfono** (nueva, debajo de Contactos)

```
┌ Teléfono ─────────────────────────────────────────── [● Disponible]     ┐
│ Sale desde: [ +54 11 5555-0000 ▾ ]                                       │
├──────────────────────────────┬──────────────────────────────────────────┤
│ 🔍 Buscar contacto…  [tags ▾]│  Juan Pérez · +54 9 11 4444-1234          │
│ ─────────────────────────────│  Tags: cliente, cobranza                  │
│ Juan Pérez         [Llamar]  │  ⚠ Pidió no recibir llamadas (12-oct)     │
│ María Gómez        [Llamar]  │  Última: 12-oct, 4 min (Ana)              │
│ Ferretería Sur     [Llamar]  │          [ 📞 Llamar ]                     │
│ …                            │  Historial: agente y directas, con link   │
│ O marcá un número: [_______] │                                          │
├──────────────────────────────┴──────────────────────────────────────────┤
│ Mis últimas llamadas: hora · contacto · entrante/saliente · duración    │
└─────────────────────────────────────────────────────────────────────────┘
```

- Agenda con búsqueda y tags. Los dados de baja, con la marca y una confirmación al llamar; los bloqueados,
  con el botón apagado.
- "Marcá un número" para uno fuera de la agenda; al terminar, **Guardar como contacto**.
- El número de salida se recuerda por usuario (navegador). Con un solo número, no se muestra.

### Barra de llamada (en todo el panel)

La llamada vive en un provider del layout: el usuario puede abrir la ficha del contacto sin cortar.

```
● En curso 02:31 · Juan Pérez · desde +54 11 5555-0000   [🎤 Silenciar] [⌨ Teclado] [Cortar]
  "…entonces le confirmo el turno para el jueves" (transcripción en vivo, plegable)
```

- Estados: Conectando micrófono → Llamando → Sonando → En curso → Terminada (no atendió, ocupado, falló,
  cortada), con los textos de error de la página del link para llamar.
- Teclado DTMF (`publishDtmf`). Aviso al cerrar la pestaña; al volver, **Volver a entrar**.
- Timbre de entrante (Disponible) con **Atender** / **Rechazar**, el número que llama y el contacto si está en la
  agenda.

### Otros lugares

- **Números:** "Atiende: el agente / el equipo" con área y respaldo (sección 5).
- **Contactos** (lista y ficha): **Llamar** (directa) al lado de **Llamar con un agente**.
- **Conversaciones:** filtro "Atendió: agente / equipo" y "Usuario"; en la ficha, "Llamó: Ana" o
  "Atendió: Ana".
- **Mi cuenta:** switch "Avisar que la llamada se graba" para las directas.
- **Plan:** `PlanGate` con `direct_calls` en Teléfono y en la opción "el equipo" de Números.
- **Reportes:** las directas, aparte en la pestaña Llamadas (por tipo y por usuario).

## 9. Todo por UI, API y MCP

Regla: nada de esta función se configura solo por una vía. La UI usa la misma API; cada herramienta del MCP
es una entrada de `app/mcp/catalog.py` que pide a `/api/v1` (el plan y los permisos los corta la API; el
`inputSchema` de las de escritura sale del modelo Pydantic de la ruta).

| Acción o ajuste | UI | API | MCP (toolset, herramienta) |
|---|---|---|---|
| Llamar a un contacto o número | Teléfono, Contactos, barra de llamada | `POST /direct-calls` (`join_url` con API key) | `calls`, `start_direct_call` (devuelve `join_url`; destructiva: confirmar con el usuario) |
| Volver a entrar a una llamada | Barra de llamada | `POST /direct-calls/{id}/join` | — (es del navegador) |
| Cortar | Barra de llamada, detalle | `POST /calls/{id}/hangup` | `calls`, `hangup_call` (existe) |
| Listar y ver directas | Conversaciones (filtros tipo y usuario), Teléfono | `GET /calls?mode=directa&user_id=`, `GET /conversations/{id}` | `calls`, `list_calls` y `get_call` con los filtros nuevos |
| Escuchar una grabación | Chat del detalle | `GET /calls/{id}/recordings/{n}` | Link en `get_call` (existe) |
| Quién atiende un número (agente o equipo), área, respaldo y mensaje | Números | `PATCH /phone-numbers/{id}` | `calls`, `route_phone_number` (se amplía su body y su descripción) |
| Personas del número, dónde suena primero, timbre y horario | Números | `PATCH /phone-numbers/{id}` | `calls`, `route_phone_number` (se amplía) |
| Personas del equipo (celular y usuario del panel) | Equipo (existe) | `/team/*` (existe) | `team`, herramientas existentes |
| Aviso de grabación en las directas | Mi cuenta | `PUT /clients/{id}/direct-call-settings` (`recording_notice`) | `account`, `get_direct_call_settings` y `update_direct_call_settings` (nuevas) |
| Disponible para atender en el panel | Barra de llamada | `PUT /me/presence` | — (es del navegador) |
| Quién está disponible | Equipo (punto verde por persona) | `GET /team/presence` | `team`, `list_team_presence` (nueva) |
| Atender una entrante en el panel | Timbre de la barra | `GET /me/ringing`, `POST /direct-calls/{id}/answer` | — (es del navegador) |
| `direct_calls` del tier | Editor de tiers (admin) | `PATCH /tiers/{id}` | — (el catálogo no tiene herramientas de tiers) |
| Qué incluye el plan | Plan, `PlanGate` | `GET /plan/features` | `get_plan_tools` (sale de `features`) |
| Reporte de directas | Reportes > Llamadas (por tipo y usuario) | `/reports/calls` con el corte nuevo | `reports`, `get_report_calls` (se amplía) |

- Herramientas nuevas o ampliadas con `features=("direct_calls",)`.
- Después: `make mcp-docs` (regenera `docs/MCP_HERRAMIENTAS.md` y `landing/src/data/mcp-tools.json`),
  `tests/test_mcp.py` y `make mcp-eval` (cambian descripciones: medir que el modelo elija `start_direct_call`
  cuando el usuario quiere hablar él y `start_call` cuando quiere que llame el agente). Subir la versión en
  `deploy/mcp/server.json` y `make mcp-registry-publish`.

## 10. Documentación y landing

| Dónde | Qué |
|---|---|
| `AGENTS.md` | Fila en "Pedidos frecuentes", el plan en "Documentación", trampas (canales de Anura, grabación siempre) |
| `docs/ARQUITECTURA.md` | Modo `directa`, `answer_mode` del número, rama del worker y `listen.py`, flujos saliente y entrante |
| `docs/GUIA_UI.md` | Teléfono, barra de llamada, Números (agente o equipo), Mi cuenta, filtros de Conversaciones |
| `docs/DERIVACIONES_PLAN.md` | 4.5 apunta a este plan; `Transfer` sin agente |
| `docs/FUNCIONES_POR_PLAN_PLAN.md` | `direct_calls` en la tabla de planes |
| `docs/REPORTES_PLAN.md` | El corte por tipo y por usuario |
| `docs/MCP_PLAN.md` | Herramientas nuevas y ampliadas |
| `README.md` | La función en la descripción de la app |
| Landing `/desarrolladores/docs/api` | `POST /direct-calls`, `join_url`, campos nuevos de números y cuenta, filtros, errores (`opted_out`, `support_read_only`, sin canales) y qué plan la incluye |
| Landing `/desarrolladores/docs/mcp` | Sale de `mcp-tools.json` (`make mcp-docs`) |
| Landing `/plataforma` | Página nueva ("Teléfono del equipo": llamar desde el navegador con el número de la empresa, entrantes al equipo o al agente, todo grabado y transcripto) y la mención en la de telefonía |
| Landing, planes (`landing/src/data/site.ts`) | La función en todos los planes pagos |
| Landing `/terminos` y `/privacidad` | Versión nueva (sección 7, `make legal-sync`) |
| Landing, home y casos de uso | Una línea donde hoy dice "entrantes y salientes" (agente + equipo); sin video nuevo por ahora |

Todo cambio visual o de texto de la landing sigue `docs/DESIGN_GUIDELINE.md`; los del panel,
`docs/DESIGN_GUIDELINE_APP.md`.

## 11. Fases

| Fase | Qué | Esfuerzo |
|---|---|---|
| 1. Saliente | Migración, `CallMode.directa`, cuotas, API (con `user_id` y `join_url`), rama del worker con `listen.py` común, prueba en `make e2e-sip` (Anura falso) | 3-4 días |
| 2. UI saliente | Teléfono, provider y barra de llamada, página de `join_url`, botones en Contactos, filtros, gate por plan | 3-4 días |
| 3. Entrante al equipo | `answer_mode`, personas del número, `ring_first`, respaldo, `Transfer` sin agente con personas en lugar de área, buzón de voz, respaldo al agente, pantalla Números, `make e2e-sip` | 3-4 días |
| 3b. Panel para atender | Presencia, timbre, Atender y Rechazar, `ring_first=panel` y el paso al otro | ~1 semana |
| 4. MCP | Herramientas nuevas y ampliadas, `make mcp-docs`, `tests/test_mcp.py`, `make mcp-eval`, versión del registro | 1 día |
| 5. Documentación y landing | Sección 10 | 1-2 días |
| 6. Condiciones | Versión nueva de condiciones y privacidad, revisión del abogado, aviso por mail, habilitar al aceptar | En paralelo; bloquea el despliegue |
| 7. Prueba real y despliegue | Llamadas con números propios (atiende, no atiende, ocupado, corta cada lado, recarga, sin minutos, fuera de horario, respaldo, celular primero y panel primero, por API y MCP con `join_url`), CAP corto, `make migrate`, `make calls-active && make up-agent`, landing publicada | 1-2 días |
| Después | Grabación estéreo de la llamada entera, número por usuario, "Pasarle a la IA", retención de grabaciones | — |

## 12. Riesgos

- **Canales de Anura:** 10 en total. Una saliente directa ocupa 1. Una entrante al teléfono de una persona
  ocupa 2 si atiende en el celular y 1 si atiende en el panel. Sin canal libre: "Todas las líneas están ocupadas" en la saliente y el respaldo en la
  entrante.
- **Celular:** el panel anda en el navegador del celular con la pestaña abierta; con la pantalla bloqueada iOS
  puede cortar el micrófono. Para recibir, el celular (el default) es lo que anda siempre.
- **Transcripción por frase:** si hablan a la vez quedan mensajes cruzados, ordenados por fin de frase. Para
  auditoría, la grabación estéreo.
- **Eco:** sin auriculares la voz del contacto puede volver al micrófono; recomendar auriculares en la
  pantalla.

## 13. Contrato de implementación

Nombres fijos para el backend, el worker, la UI y el MCP. Si un nombre choca con el código existente, se
cambia acá y en el código a la vez.

### Base (migración `0039_direct_calls`)

- `CallMode.directa = "directa"` (saliente de una persona).
- `call_logs`: `user_id` (FK `users`, SET NULL, nulo, índice), `answered_by` (`String(8)`, nulo: `agent`
  o `team` en las entrantes), `opted_out_confirmed` (bool, default false).
- `phone_numbers`: `answer_mode` (`String(8)`, default `team`; la migración pone `agent` en todas las filas
  existentes), `ring_first` (`phone`/`panel`, default `phone`), `ring_seconds` (int, 20), `schedule`
  (JSON, nulo, mismo formato que `handoff_areas.schedule`), `team_fallback` (`agent`/`voicemail`/`hangup`,
  default `voicemail`), `team_fallback_message` (texto, default "").
- `phone_number_members`: `phone_number_id` (FK cascade), `member_id` (FK `team_members` cascade),
  `position` (int); PK (número, miembro).
- `user_presence`: `user_id` (PK, FK cascade), `client_id`, `last_seen` (DateTime). Disponible = pulso en
  los últimos `PRESENCE_TTL_SECONDS` (60). Ocupado = tiene una llamada activa con su `user_id`.
- `call_rings`: `id`, `conversation_id` (FK cascade), `user_id` (FK cascade), `status`
  (`ringing`/`answered`/`declined`/`cancelled`), `created_at`, `ended_at`. Un timbre por usuario y llamada
  entrante al panel (único: `uq_call_rings_conversation_user`).
- `tiers.direct_calls` (bool, default false; la migración lo pone en true en todos los tiers salvo el Free).
- `clients.direct_recording_notice` (bool, default false).

### Permisos y plan

- `features.TIER_HAS["direct_calls"] = bool(t.direct_calls)`. Sin la función: el error de plan que ya usan
  las otras funciones (429 `direct_calls_not_in_plan`, `limits.check_direct_calls`). También al poner un número
  en `answer_mode=team` (`PATCH /phone-numbers/{id}`); si el plan pierde la función, las entrantes de un número
  del equipo van al agente del número (`start_inbound`).
- Una persona del equipo puede tener solo usuario del panel (sin teléfono ni WhatsApp): le suena solo ahí.
- Un admin en soporte: 403 `support_read_only` en llamar, atender, rechazar y presencia.
- `quota`: `directa` en `MINUTE_MODES` (`outbound`) y en `ANURA_MODES`. Un tramo al celular de una persona
  del equipo en una entrante directa cuenta como hoy los de la derivación (`handoff_legs`).

### API (`/api/v1`)

| Método y ruta | Entrada | Salida y errores |
|---|---|---|
| `POST /direct-calls` | `DirectCallIn {contact_id?, phone?, from_number_id?, confirm_opted_out=false, user_id?}` (contacto o teléfono) | 201 `DirectCallOut {conversation_id, room, status, livekit_url, token?, join_url?}`. Con sesión: `token` del usuario. Con API key/MCP: `user_id` obligatorio (usuario activo del cliente), `token` nulo y `join_url` = `<APP_URL>/telefono/llamada/<id>` (la setting que ya arma los links del panel). 409 `opted_out` (con `confirm_opted_out` en false), 409 `no_phone_number` (el cliente sin números), 403 `blocked_number`, 422 `user_required`/`invalid_user`, 429 de cuota (`outbound_minutes`, `direct_calls_not_in_plan`...) o sin canales (`no_channel`) |
| `POST /direct-calls/{id}/join` | — | `{livekit_url, token}`; solo el `user_id` de la llamada (403 `not_your_call`) y llamada activa (409 `call_not_active`) |
| `POST /direct-calls/{id}/answer` | — | `{livekit_url, token}`; toma la llamada si nadie la tomó (409 `already_answered`; 409 `not_ringing` si la rechazó; 404 si no le suena) |
| `POST /direct-calls/{id}/decline` | — | 204 |
| `PUT /me/presence` | `{available: bool}` | `{available, last_seen}` (pulso: la UI lo manda cada 20 s mientras está Disponible; `available=false` borra) |
| `GET /me/ringing` | — | `[RingingOut {conversation_id, phone, contact_id?, contact_name?, number_e164, number_label, started_at}]` |
| `GET /team/presence` | — | `[{user_id, team_member_id?, name, available, busy}]` |
| `GET/PUT /clients/{client_id}/direct-call-settings` | `{recording_notice: bool}` | igual |
| `PATCH /phone-numbers/{id}` | suma `answer_mode`, `member_ids` (ordenados), `ring_first`, `ring_seconds`, `schedule`, `team_fallback`, `team_fallback_message` | `PhoneNumberOut` con esos campos y `members [{id, name, phone, user_id}]` |
| `GET /calls` | filtros nuevos `mode`, `user_id`, `answered_by`, `phone`, `contact_id` | `CallOut` suma `user_id`, `user_name`, `answered_by`, `opted_out_confirmed`, `contact_id` |
| Tiers | `direct_calls` en el modelo de entrada y salida | — |
| Cortar | `POST /calls/{id}/hangup` (existe) | — |

### Worker y LiveKit

- Identidades en la room: el usuario del panel `user-<user_id>`; el contacto de la saliente `contact`; el que
  llama en la entrante, la que le pone livekit-sip (`sip_<número>`, como hoy); una persona del equipo por celular
  `persona-<n>`, la de la derivación (`Transfer`: los permisos de las pistas se fijan por identidad antes de
  marcar y el worker no corta cuando sale una).
- Token del panel: `livekit.user_participant_token(room, identity, name)` (publica y escucha audio, publica
  datos).
- Metadata de una saliente directa: `{"conversation_id", "direct": true, "phone", "from_number",
  "user_identity", "user_name", "max_duration_seconds", "join_timeout_seconds" (30 desde el panel, 120 por
  API/MCP), "recording_notice", "voice"}`.
- Entrante con `answer_mode=team`: `start_inbound` devuelve el ruteo del equipo en `InboundCall.team`
  (`TeamRoute {members: [TeamPerson {member_id, name, phone, user_id}], ring_first, ring_seconds, schedule,
  fallback, fallback_message, agent_id, number_e164, number_label}`; solo las personas activas con celular o
  usuario) y el worker toma la rama directa. Sin personas, va al agente del número (`team` es None).
- Timbre en el panel, para el worker (`services/direct_calls.py`): `ring_panel(s, conversation_id, user_ids)`
  (a los Disponibles y no ocupados; devuelve a quiénes les suena), `cancel_rings(s, conversation_id)`,
  `answered_user(s, conversation_id)`, `available_users(s, client_id, user_ids)` y `release_answer(s,
  conversation_id)` (atendió en el panel y su navegador no entró en `PANEL_JOIN_GRACE_SECONDS`: la llamada
  vuelve a quedar sin `user_id`, y si su navegador entra tarde el worker lo saca de la room: `block`).
  `answer` toma el timbre solo si sigue `ringing` (con un `UPDATE` condicional): después de `cancel_rings`
  nadie más atiende, y el worker mira `answered_user` una vez más al apagar los timbres. `answer`,
  `ring_panel`, `cancel_rings` y `release_answer` bloquean primero la fila de la llamada (`FOR UPDATE`) y
  después `call_rings`: mismo orden en todos, sin deadlock en PostgreSQL. Un timbre de más de
  `RING_MAX_SECONDS` (90) o de una llamada colgada no suena ni se atiende (se cayó el worker).
- Volver a entrar: si sale el usuario del panel (recarga, red), el worker lo espera
  `PANEL_REJOIN_GRACE_SECONDS` (30) antes de cortar con `person_hangup`, también mientras suena. El panel no
  usa `disconnectOnPageLeave` de LiveKit (cortaba en `beforeunload` aunque se cancelara y en `freeze` del
  celular): sale en `pagehide`. El pulso de Disponible y el sondeo del timbre van por un Worker
  (`web/src/features/phone/ticker.ts`): Chrome frena los timers de una pestaña oculta a uno por minuto.
- Cuando sale alguien, el VAD recibe silencio para cerrar la frase en curso y se espera su STT
  (`SETTLE_SECONDS`): la última frase (el "chau", el mensaje del buzón) queda en la conversación.
- Si el worker no puede ni empezar (sin trunk saliente, sin VAD), la llamada queda `fallida` con
  `worker_error` y se borra la room.
- Datos de la room para el panel (`publish_data`, JSON): tema `call_status` `{state: "joining" | "dialing" |
  "ringing" | "active" | "ended", result?}` (solo la saliente: en la entrante el usuario entra ya atendida;
  `result` en `ended`: `completed`, `no_answer`, `busy` o `failed`) y tema `transcript` `{role: "user" |
  "assistant", person?, text}`.
- Cómo termina (`call_logs`): atendida, `finalizada` con minutos desde que atiende el contacto (la saliente) o
  desde que entra (la entrante) y `ended_reason` `customer_hangup` (cortó el contacto o el que llama),
  `person_hangup` (el usuario o la persona), `max_duration`, `quota_exhausted` o `hangup_by_user` (desde la
  API, gana); si el usuario corta antes de que atiendan, la saliente queda `cancelada` (`hangup_by_user` o
  `person_hangup`, no cuenta como falla); sin atender, queda `fallida` con `user_not_joined`, `no_answer`, `busy` o
  `sip_call_failed` (y `sip_status`). La entrante sin nadie que atienda: `after_hours` o `team_no_answer`, con
  el mensaje del respaldo y, en `voicemail`, lo que dejó grabado el que llama. Atendida en el celular, la
  llamada queda con el `user_id` de la persona si tiene usuario.
- Respaldo `agent`: `direct_calls.fallback_to_agent(s, engine, conversation_id, agent_id, phone)` pasa la
  conversación al agente del número (agente, versión, campos y apertura) y la llamada a `answered_by=agent`; el
  worker sigue con el agente en la misma room, con los minutos desde que entró. Si el agente está archivado,
  toma el mensaje (`voicemail`).
- Celulares en la entrante: `Transfer.run_team(TeamRing, personas, whisper, valores)` de la derivación (sin
  área ni código de vuelta a la IA; tramos en `handoff_legs` con `area_id` nulo, mismos eventos `handoff.*`).
  Whisper: "Llamada a {{linea}} de {{cliente}}. Marcá 1 para atender." (`linea`: la etiqueta del número).
- Mensajes: lo del contacto o el que llama, `role="user"`; lo del usuario o la persona del equipo,
  `role="assistant"` con `person` = su nombre. Siempre con su WAV (`Message.recording`), sin mirar
  `record_audio`.
- Código: `app/voice/listen.py` (captura y transcripción por VAD + STT, común con la derivación),
  `app/voice/direct.py` (saliente y entrante del equipo), rama al principio de `entrypoint` en
  `app/voice/worker.py`. El aviso de grabación es un WAV que el worker sintetiza la primera vez y guarda en
  `storage/notices/<voz>.wav` (`NOTICE_AUDIO_DIR`); en la entrante, si el cliente lo prendió, suena al que llama
  antes de la espera. La entrante usa `VLLM_TTS_VOICE` (no hay voz por cliente).
- Prueba SIP aislada: `tests/e2e_sip/direct.py` (servicio `runner-direct`, en `make e2e-sip`): saliente contra un
  eco del Anura falso (`3510000008`) y entrante al equipo por celular.

### UI (`web/`)

- Rutas: `/telefono` (pantalla Teléfono) y `/telefono/llamada/:id` (entra a una llamada creada por API o MCP:
  pide `/join` y abre la barra).
- `CallProvider` en el layout del cliente (`AppLayout`), con la barra de llamada fija abajo; hooks
  `useDirectCall()` (`call(contact|phone, fromNumberId, confirmOptedOut)`, `hangup`, `mute`, `dtmf`,
  estado y transcripción) y `usePresence()`.
- Navegación: "Teléfono" debajo de Contactos, con `PlanGate` `direct_calls`.

### MCP (`app/mcp/catalog.py`)

- Nuevas: `start_direct_call` (`calls`, POST `/direct-calls`, body `DirectCallIn`, `features=("direct_calls",)`,
  destructiva), `list_team_presence` (`team`, GET `/team/presence`), `get_direct_call_settings` y
  `update_direct_call_settings` (`account`); las cuatro con `features=("direct_calls",)`. Con key o MCP,
  `user_id` es obligatorio (422 `user_required`) y la respuesta trae `join_url`.
- Ampliadas: `route_phone_number` (descripción: agente o equipo, personas, dónde suena primero, respaldo),
  `list_calls` (filtros `mode`, `user_id`, `answered_by`), `list_phone_numbers` (quién atiende) y `get_report_calls` (la
  misma respuesta de `/reports/calls`: `daily.directa`, `by_type [{type: agent|direct|team, calls, minutes,
  avg_duration}]` y `by_user [{user_id, user_name, direct, team, calls, minutes, avg_duration}]`). Las directas y
  las entrantes del equipo no tienen agente: cuentan como llamadas y minutos, no en conversión ni embudo. No hay
  herramientas de tiers en el catálogo: `direct_calls` del tier va por la UI o la API.

## 14. Cómo desplegar

Hechos el 27-oct-2026 los pasos 2, 3 y 4 (`make migrate-test` sobre el backup de las 03:30: 0034 → 0039 ida y vuelta; 0039 en la base: los 6 números en `agent`, `direct_calls` en Mostrador, Sucursal e Interno; landing por push a `main`). El 1 quedó a medias: texto publicado sin revisión del abogado ni aviso por mail. En este orden, con el stack en vivo (confirmar cada paso que corta llamadas):

1. **Condiciones y privacidad primero.** La migración enciende `direct_calls` en los planes pagos; el código corta
   a quien no aceptó (403 `terms_pending`), pero el texto tiene que estar publicado antes. Revisión del abogado del texto `2026-10-28` (sección 7),
   `make legal-sync`, aviso por mail a los clientes con 30 días ([`TERMINOS_PLAN.md`](TERMINOS_PLAN.md)); el modal del panel
   pide la versión nueva. Sin aceptar, la función no anda para ese cliente (sección 7).
2. `make migrate-test` (la 0039 contra una copia del backup en PostgreSQL: los números existentes quedan en
   `answer_mode=agent`, los tiers pagos con `direct_calls`).
3. `make migrate` y, sin llamadas en curso, `make calls-active && make up-agent` (recrea `app` y `agent`; la UI
   de `web/` se compila en la imagen de `app`). Los números ya ruteados a un agente siguen igual.
4. Publicar la landing: `/desarrolladores/docs/api` (`POST /direct-calls`, `join_url`, campos nuevos, errores),
   `/plataforma`, planes (`landing/src/data/site.ts`), `/terminos` y `/privacidad` (sección 10).
5. **MCP:** `make mcp-docs` (ya regenerado; repetir si cambia el catálogo), `tests/test_mcp.py`, `make mcp-eval`
   (gasta tokens de OpenRouter), subir `version` en `deploy/mcp/server.json` y `make mcp-registry-publish`.
6. **Prueba real, con números propios** (no con clientes), cada caso se revisa en Conversaciones (transcripción, WAV por
   frase, duración, resultado y minutos):
   - Saliente desde el panel: atiende, no atiende, ocupado, número inválido, corta cada lado, recargar la página
     y **Volver a entrar**, cerrar la pestaña, sin minutos salientes, sin canales libres, contacto dado de baja
     (con y sin confirmar), número bloqueado, con y sin aviso de grabación.
   - Entrante al equipo: una persona atiende en su celular (marcando 1), no atiende, ocupado; fuera de horario; los
     tres respaldos (agente, buzón de voz, corte); celular primero y panel primero, cada uno con el paso al otro;
     atender en el panel con dos usuarios Disponibles (el segundo ve 409 y se le apaga) y rechazar; sin nadie
     Disponible; el WhatsApp del mismo DID.
   - Por API y por MCP: `POST /direct-calls` con `user_id` y `join_url`; abrirlo con la sesión de ese usuario y con
     la de otro (403).
   - El plan: Free (429 `direct_calls_not_in_plan`) y un admin en "ver como cliente" (403 `support_read_only`).
   - `make e2e-sip` en verde antes de empezar.
7. **CAP corto mezclado** con llamadas del agente (sección 6, "Capacidad"): directas y del agente a la vez hasta los
   10 canales de Anura, para ver el STT por frase y el corte por canales. Se registra en `docs/capacity/`.
8. Cuando está estable, avisar a los clientes de pago y, de a uno, ponerles el número en `team` desde Números (o
   desde la API / el MCP, `route_phone_number`).

Volver atrás: la 0039 tiene `downgrade` (probado de ida y vuelta en `tests/test_migration_0039.py`; no hay target
de `make`, se agrega al `Makefile` si hace falta), que borra las columnas y tablas nuevas sin tocar lo que ya había;
después recrear `app` y `agent` con la imagen anterior. Las directas ya hechas se conservan como llamadas sin
`user_id` ni `answered_by`, con sus WAV en `storage/recordings/`.

## 15. Pendientes

- **Sin probar con LiveKit, Chrome y PostgreSQL reales** (en la prueba del paso 6): el orden de los locks
  (`FOR UPDATE`) con dos que atienden a la vez; recargar la pestaña y "Volver a entrar" (se asume que LiveKit saca la
  conexión vieja antes de sumar la nueva); que el silencio al VAD cierre la última frase al cortar; el pulso y el
  timbre con la pestaña oculta más de 5 minutos (`ticker.ts`, sin Worker en jsdom). Si el usuario cierra la pestaña
  sin cortar, el contacto queda hasta 30 s en silencio (`PANEL_REJOIN_GRACE_SECONDS`).
- **Tests en PostgreSQL:** `TEST_DB_DSN` solo cambia el fixture `store`; los de directas (`sessions`/`api`) van
  siempre a SQLite. Se corrieron una vez contra PostgreSQL 16 con un plugin en `scratch/` (39 pasados).
- **Condiciones y privacidad:** revisión del abogado y aviso por mail con 30 días (sección 7). Es lo que bloquea el
  despliegue. La entrante del equipo de un cliente que no aceptó va al agente del número: probarlo en el paso 6.
- **Landing:** hecha en la rama (ver el estado al principio), sin publicar: se publica con las condiciones (paso 1 y 4
  de la sección 14). La página del teléfono describe la UI de la sección 8: revisarla contra `web/` cuando cierre.
- **Medir:** `make mcp-eval` con las herramientas nuevas; CAP corto de directas mezcladas con agente (hoy no hay
  números con Gemma ni con directas); la prueba real del paso 6, en particular el panel en el celular (con la pantalla
  bloqueada iOS puede cortar el micrófono) y el eco sin auriculares.
- **Códigos SIP de Anura:** los de una saliente directa a un contacto (no atiende, ocupado, inexistente) salen de
  `classify_error` y, como en las campañas, no están verificados con llamadas reales. El celular de una persona con
  buzón de voz lo resuelve el detector por STT de la derivación (`DERIVACIONES_PLAN.md`, 11): con Claro, "ocupado"
  no se ve nunca.
- **Después** (de la sección 11): grabación estéreo de la llamada entera, número por usuario, "Pasarle a la IA" y
  retención de grabaciones. Cada directa pesa ~1,9 MB por minuto de habla en `storage/`; sin retención, el disco
  crece con el uso.
- **Reportes:** las directas y las entrantes del equipo cuentan como llamadas y minutos, no en conversión ni
  embudo ([`REPORTES_PLAN.md`](REPORTES_PLAN.md)).
