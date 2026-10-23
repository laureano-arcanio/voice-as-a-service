# Plan: derivación a personas (llamadas y WhatsApp), registro de eventos y costos

El agente pasa la conversación a una persona del cliente: **la llamada**, a su teléfono (bridge por Anura),
y **el WhatsApp**, a su WhatsApp, con el puente por la bandeja (`WHATSAPP_PLAN.md`, 5.8, variante A). Todo
queda en un registro de eventos que el cliente ve en el panel y recibe por webhook. Diseño del 23-oct-2026;
fase 1 desplegada el 23-oct-2026 (sección 12); fase 2 (transferencia de llamadas) desplegada el 23-oct-2026
(sección 13).

Alcance decidido con Laureano (23-oct-2026):

- **Transferencia atendida por LiveKit** (no la ciega por REFER), desde los tres orígenes: entrante de Anura,
  entrante de WhatsApp (Calling API) y web (link para llamar, demo).
- **Destinos por área y horario**, con **fallback** (si no atiende, vuelve el agente y toma el mensaje).
- **Grabación y transcripción del tramo con la persona.**
- **Persona → IA** y **softphone web** (pedido de CIMEPA).
- **WhatsApp: variante A**, puente por la bandeja.
- **Timeline de eventos y panel de derivaciones**, **webhook y API de eventos**, **test SIP automatizado** y
  **costo por llamada y por mensaje**.

## 1. Quién lo pide

| Requerimiento | Prometido en la propuesta | Detectado |
|---|---|---|
| Transferir la llamada en vivo a una persona | Goldman, SQL, CIMEPA | Simepa, Erpwoosync |
| Si no atiende, la IA vuelve y toma el mensaje | CIMEPA | Goldman |
| Destino por área, marca o zona, con horario y número por persona | Goldman, BAIC, SQL, CIMEPA | Erpwoosync (3 áreas) |
| WhatsApp → WhatsApp del vendedor, con registro | Goldman, SQL | BAIC, Erpwoosync |
| Panel: a quién se derivó, cuánto tardó en tomarla, sin tomar | Goldman, BAIC, SQL, CIMEPA | — |
| Panel por canal, fuera de horario y primera respuesta | Goldman, BAIC, SQL | — |
| Webhook, API y CSV de eventos | CIMEPA, Axioma, Zennon (Power BI) | BAIC (CRM) |
| Grabación de la llamada entera, también el tramo humano | CIMEPA | — |
| Persona → IA y softphone web | CIMEPA | — |

Fuentes: `docs/mercado/demos/*.md` y `marketing/documentos/proyectos/*-propuesta/`. La fecha que aprieta es
la de **Goldman**: si no llega a noviembre, el piloto arranca con derivación por ficha
(`isaiasgoldman.md:349`).

## 2. Qué hay hoy

| Pieza | Estado |
|---|---|
| Saliente del worker por Anura (`create_sip_participant`, `app/voice/worker.py:622`), trunk `anura-asterisk-outbound`, solo números argentinos (`[from-livekit]`) | Hecho |
| Cortar desde la API (`POST /calls/{id}/hangup`) y por marca `[CORTAR]` en `classic` | Hecho |
| Transferir, sumar un tercero a una llamada en curso, REFER, `Dial`/`Bridge` a un celular | **No** |
| Ruteo de WhatsApp: operador > respuesta a campaña > `wa_routes` > agente por defecto | Hecho |
| `wa_threads.paused` | Existe, pero nada lo prende |
| Derivación (`handoff`) o bandeja en WhatsApp | **No** |
| `call_logs` (estado, `ended_reason`, `latency` por turno), `wa_messages` con estados, resumen por email | Hecho |
| Eventos por llamada, hora por mensaje, tiempo de timbre o espera, costo | **No** |
| Grabación | Un WAV por mensaje, no la llamada entera |
| Tests con fakes (unos 833), loadtest y eval por WebRTC | Hecho |
| Test automatizado de SIP | **No** (la telefonía se prueba a mano) |

## 3. Destinos: el equipo del cliente

Una sola tabla para llamadas y WhatsApp (los "vendedores" de 5.8 son las mismas personas):

- **`team_members`** (por cliente): nombre, `phone` (E.164, argentino), `whatsapp`, `user_id` opcional (para
  el softphone web), activo.
- **`handoff_areas`** (por cliente): nombre ("Ventas", "Posventa"), miembros en orden, horario semanal con
  feriados, estrategia (`sequential` o `round_robin`), segundos de timbre por miembro (default 20) y qué hacer
  fuera de horario o si nadie atiende (`take_message`, `whatsapp_ficha` o `email`).
- **En la definición del agente** (versionada, editable en la UI): qué áreas puede usar y cuándo, en lenguaje
  natural ("Ventas: precios, presupuestos, visitas"). Es lo que lee el LLM para elegir.

Se gestiona por la UI y por la API (`/api/v1/team`, `/api/v1/handoff-areas`). El tope de miembros va por
tier.

## 4. Transferencia de llamada (atendida)

### 4.1 Flujo

1. **El agente decide derivar.**
   - En `classic`, con una marca `[DERIVAR:<área>]` (como `[CORTAR]`, en `app/llm/prompt.py` y
     `MarkerFilter`).
   - En `assistant`, con una tool de plataforma `derivar(area, motivo)` junto a `abrir_vista`
     (`app/apps/tools.py`). Hace falta un canal de vuelta del motor al worker: `execute` hoy no llega al
     `JobContext`.
2. **Le dice al cliente** "Te paso con Ventas, un momento" (mensaje configurable, 4.7) y lo deja **en
   espera**, con música si está prendida (4.8).
3. **Llama al destino.** El worker hace `create_sip_participant` al primer miembro del área en horario, con
   `wait_until_answered` y el timbre del área. El cliente no escucha ese tramo: la pista del destino no se
   le publica hasta que atiende.
4. **Detecta si atendió una máquina.** Escucha los primeros segundos del destino con el STT y la lista de
   frases de buzón que ya usan las campañas (`app/campaigns/voicemail.py`: "deje su mensaje", "el abonado no
   está disponible"...). Si suena a buzón, no conecta: es `machine`. La lista de frases falla cuando el
   buzón no dice nada reconocible (un pitido, música o un saludo grabado por el dueño), y por eso está el
   paso 5. Un detector de audio (AMD de Asterisk en el tramo saliente, con `Dial(...,U())`) queda como
   mejora, a medir en el spike.
5. **Le pasa el resumen al que atiende** (*whisper*), solo para el destino: "Derivación de Atentina: Juan
   Pérez, consulta por un split, quiere visita. Marcá 1 para atender." Hasta que marca 1, el destino no se
   conecta. Si no marca en N segundos (default 8) o marca otra cosa, es `not_confirmed`: un contestador que
   no se detectó en el paso 4 termina acá.
6. **Conecta.** Publica las dos pistas entre sí y el agente se calla, pero no sale de la room (4.2).
7. **Si no se pudo conectar:** con más miembros en el área, prueba con el siguiente. Cuando se acaban,
   el agente vuelve con el cliente y le dice el mensaje que corresponde al último resultado (4.7). Después
   ofrece tomar el mensaje y deja la ficha (WhatsApp o email al área). Cada intento queda como evento
   (`handoff.no_answer`, `handoff.busy`, `handoff.machine`, `handoff.not_confirmed`).

### 4.2 El worker se queda en modo escucha

Después de conectar, el worker sigue en la room sin hablar. Resuelve tres cosas a la vez:

- **Grabación y transcripción del tramo humano:** cada pista, con el STT propio, en el mismo historial
  (`Message` con `role: "human"` y el `team_member_id`) y la misma API. No hace falta LiveKit Egress.
- **Cierre:** cuando cuelga cualquiera de los dos, corta al otro y cierra la room, como hoy.
- **Persona → IA (4.4):** sigue escuchando los DTMF.

Lo que cuesta: un worker por llamada transferida. No usa ni el LLM ni el TTS, pero sí el STT si se transcribe.
Hay que medir cuánto ocupa (CPU y STT) en el test de capacidad.

### 4.3 Por origen

| Origen | Qué cambia |
|---|---|
| Entrante de Anura | Nada: se suma un tramo saliente por el mismo trunk |
| Entrante de WhatsApp | El tramo del cliente es SIP/TLS con Meta; el del destino sale por Anura. **Spike:** que el audio cruce bien (PCMA en los dos) |
| Web (link, demo) | El cliente está por WebRTC; el destino, por PSTN. En la demo de la landing, solo con `DEMO_HANDOFF=true` (prendida desde el 23-oct-2026, con `atentina_comercial` → Ventas): cualquiera de internet hace sonar al equipo, con los topes de la demo (4 llamadas por hora y 10 por día por IP, 120 min diarios) y el corte de `DEMO_CALL_MAX_SECONDS` (180 s) incluyendo la charla con la persona |
| Saliente o campaña | Igual que la entrante. En campañas, opcional por campaña |

### 4.4 Persona → IA

- **Por teléfono (decidido, 23-oct-2026):** la persona marca **`2`**, configurable por área (nunca con `*`: Anura toma `*` + dígito como código de su central, 11.2). Se escucha solo la pista de la persona, así que un 2 del cliente no cuenta. Un solo dígito no está probado en la conversación (`1` y `#9` sí): medirlo en la fase 2; el agente vuelve con el contexto (transcripción completa,
  incluido el tramo humano) y la persona sale. LiveKit SIP entrega los DTMF como eventos: **spike**.
- **Desde el softphone web (4.5):** botón "Pasarle a la IA".

### 4.5 Softphone web (fase posterior, CIMEPA)

Es el diseño de `docs/mercado/demos/cimepa-telefonia.md` ("todo en nuestra webapp"):

- Página del panel, logueada, con la agenda `contacts`.
- "Llamar" crea la room, suma al empleado por WebRTC y marca al contacto desde el número de la empresa.
- El mismo worker escucha y graba.
- Más adelante, el destino de una derivación puede ser el web client si el empleado está en línea
  (presencia), antes que su celular.

### 4.6 Límites y admisión

- **Canales de Anura:** son 10 (según `rtp.conf`) y una transferencia ocupa **2** mientras dura. Hace falta un
  contador global de canales en `quota` (hoy solo hay topes por cliente). Sin canal libre, la derivación cae
  al fallback.
- **Llamadas simultáneas del tier:** una transferida cuenta como una.
- **Minutos (decidido, 23-oct-2026): cada tramo se descuenta del plan.**
  - El tramo del cliente consume minutos de su tipo (entrantes, si entró por la línea) por toda la duración.
  - El tramo a la persona consume minutos **salientes**, desde que atiende.
  - Ejemplo: 3 min con la IA y 5 min con el vendedor son 8 entrantes y 5 salientes.
  - Los intentos sin atender, ocupados o con contestador no consumen: Anura no cobra sin atención.
  - Un tramo que atiende una máquina y se corta en el paso 4 o 5 sí lo cobra Anura (un minuto entero), pero
    no se descuenta al cliente: queda en el costo del admin.
  - Con los minutos salientes del tier agotados (o en 0), la derivación no se intenta: el agente usa el
    mensaje de "no disponible" y toma el mensaje.
- **Caller ID que ve el destino (decidido):** el número de la empresa por el que entró la llamada (el DID
  de Anura; en las llamadas de WhatsApp y web, el primer número del cliente). Así la persona sabe de qué
  línea viene. El número del cliente final va en el whisper (paso 4) y en la ficha.
- **Sin canales extra por ahora (decidido):** el contador global de canales igual hace falta; sin canal
  libre, la derivación cae al fallback y queda el evento.
- **Grabación (decidido):** usa el `record_audio` del agente, apagado por default; lo prende el cliente. Con
  la grabación prendida, el agente dice al inicio "Esta llamada está siendo grabada" y graba también el tramo
  humano. Con la grabación apagada, el modo escucha transcribe pero no guarda audio.

### 4.7 Mensajes configurables

Por área, con un texto por defecto, editable en la UI y versionado con el agente. Aceptan `{{area}}`,
`{{persona}}` y `{{cliente}}`. Si el agente tiene `opening_audio`, los textos sin variables también se
pregeneran, como la apertura.

| Momento | Default |
|---|---|
| Antes de transferir | "Te paso con {{area}}, un momento por favor." |
| Whisper al destino | "Derivación de {{area}}: {{resumen}}. Marcá 1 para atender." |
| No atiende (`no_answer`) o máquina (`machine`, `not_confirmed`) | "No pude comunicarte con {{area}} en este momento. Si querés, te tomo el mensaje y te contactan más tarde." |
| Ocupado (`busy`) | "En este momento {{area}} está ocupado. Podés volver a llamar en 10 minutos, o te tomo los datos y te contacta alguien del equipo." |
| Fuera de horario | "{{area}} atiende de {{horario}}. Te tomo el mensaje y te contactan." |
| La persona corta estando conectada | Por defecto el agente vuelve: "¿Te puedo ayudar con algo más?". Configurable por área: despedirse y cortar ("Gracias por comunicarte, que tengas un buen día.") |
| Sin canal libre o sin minutos | El mismo que "no atiende" |

### 4.8 Música de espera

- Se usa siempre que el cliente espera: mientras llama al destino, durante el whisper, y en el motor
  `assistant` cuando una tool tarda más de N segundos (default 2).
- **Configurable por agente:** prendida o apagada (default prendida), tema y volumen.
- **Temas:** un catálogo con licencia libre en `storage/hold-music/` más uno propio que sube el cliente, con
  el mismo tratamiento que las imágenes de los links (`storage/call-links/`).
- **Cómo:** `BackgroundAudioPlayer` de LiveKit Agents (versión 1.8.8 en el contenedor `agent`, que ya trae
  `BuiltinAudioClip.HOLD_MUSIC`), solo hacia la pista del cliente. Se corta apenas conecta el destino o
  vuelve el agente.

## 5. WhatsApp: puente por la bandeja (5.8, variante A)

1. **El agente decide derivar** con la misma marca o tool. El hilo queda `handoff`: `paused` en true, con el
   `team_member_id` asignado.
2. **Al vendedor le llega desde la bandeja:**
   - un encabezado (cliente, número, área, resumen de lo hablado);
   - después, cada mensaje del cliente reenviado.
   - Medios: se bajan y se vuelven a subir, como los audios de 5.2.
3. **El vendedor responde citando el mensaje** (`context.id` → cliente). Sin cita, va al último cliente que le
   escribió y se le avisa a quién se mandó.
4. **Comandos:**
   - `#cerrar`: devuelve el contacto al agente.
   - `#pasar <nombre>`: reasigna.
   - `#ia`: el agente retoma con el contexto (persona → IA).
5. **Si el vendedor no contesta en N minutos** (por área, default 10): reasigna al siguiente o avisa al área.
   Fuera de horario, el agente atiende y deja la ficha.
6. **Ventana de 24 h con el vendedor:** fuera de ella, plantilla utility "Tenés un cliente nuevo". Hay que
   darla de alta en Meta.

Prioridad, como en 5.6: un número de `team_members` se reconoce antes que el ruteo (como un operador), y un
contacto con vendedor asignado ya no lo atiende el agente.

**Antes de implementar** (lo pide 5.8): probar A con dos números propios, medir la demora del reenvío y ver
cómo queda el chat del vendedor con 3 clientes a la vez.

## 6. Registro de eventos y observabilidad

### 6.1 Tabla `events`

Una fila por evento: `client_id`, `conversation_id`, `call_log_id`/`wa_thread_id`, `type`, `at` (ms),
`actor` (`agent`, `customer`, `team_member:<id>`, `system`) y `data` JSON.

| Tipo | Cuándo |
|---|---|
| `call.ringing`, `call.answered`, `call.ended` | Timbre y atención de la llamada (hoy solo se deduce de `started_at - created_at`) |
| `handoff.requested` | El agente pide derivar (área, motivo) |
| `handoff.dialing`, `handoff.answered`, `handoff.confirmed`, `handoff.no_answer`, `handoff.busy`, `handoff.machine`, `handoff.not_confirmed` | Por miembro, con el timbre y la demora de la confirmación medidos |
| `handoff.connected`, `handoff.returned_to_ai`, `handoff.ended` | Tramo humano |
| `hold.started`, `hold.ended` | Espera del cliente |
| `wa.handoff.assigned`, `wa.handoff.first_reply`, `wa.handoff.reassigned`, `wa.handoff.closed` | Puente de WhatsApp |
| `message.*` | Opcional: los mensajes ya viven en `conversations` |

Además, `Message` gana `at` (hora del mensaje), que hoy no tiene.

### 6.2 Panel del cliente

- **Detalle de la llamada o del hilo:** una línea de tiempo con esperas, intentos y quién atendió, junto a
  la transcripción (con el tramo humano marcado).
- **Derivaciones**, por persona y por área: recibió, la tomó, tiempo hasta tomarla (mediana), sin tomar,
  duración del tramo humano y vueltas a la IA.
- **Resumen** por canal (línea, WhatsApp, web): resueltas por la IA contra derivadas, fuera de horario y
  primera respuesta.

Es lo que prometen las propuestas de Goldman, BAIC y SQL. Sigue `docs/DESIGN_GUIDELINE_APP.md`.

### 6.3 Webhook y API

- **`client_webhooks`:** URL, secreto y los eventos que se mandan.
- Outbox con reintentos y firma HMAC, generalizando `campaign_callbacks`.
- `GET /api/v1/events` con filtros, y CSV.
- **Power BI** (Zennon): por el CSV o la API, sin conector propio en esta etapa.

### 6.4 Costo por llamada y por mensaje

- **`cost_rates`:** el minuto saliente de Anura y las categorías de Meta, con fecha de vigencia.
- **`call_logs.cost`** (JSON por tramo) y **`wa_messages.cost`**, calculados al cerrar.
- Solo los ve el admin (decidido). El cliente sigue viendo su consumo de minutos como hoy.
- Sirve para cotizar: hoy **ninguna propuesta lleva precio**.

## 7. Costos

| Concepto | Dato | Fuente |
|---|---|---|
| Minuto saliente de Anura (tramo al destino) | $25, facturado por minuto entero | `docs/calculadora-costos.html:182`, `anura-terminos-2026.md` |
| Minuto entrante de Anura | $0 | ídem |
| Canales de Anura | 10. Abono: $102.000 por paquete de 5 según la calculadora, $140.000 según `troncal-propia-operador.md`: **confirmar** | `rtp.conf`, `MIGRACION_SERVER.md:501` |
| GPU durante el tramo humano | Sin LLM ni TTS; STT si se transcribe | — |
| Meta, mensaje de servicio dentro de la ventana | 1.000 gratis por mes por número; después, utility ~USD 0,012 | `WHATSAPP_PLAN.md:308-332` |
| Meta, plantilla al vendedor fuera de las 24 h | Utility ~USD 0,012 | ídem |

Ejemplos, con esos datos:

- **Llamada entrante de 3 min con la IA más 5 min con la persona:** $125 de Anura, 2 canales durante 5 min y
  el STT si se graba. Al cliente se le descuentan 8 min entrantes y 5 salientes (13 del plan). Con el plan
  Sucursal (precio de lista $99.000 por 1.200 min, $82,5 por minuto), el tramo con la persona aporta 10 min
  de plan ($825) contra $125 de Anura.
- **WhatsApp derivado con 20 mensajes:** cada mensaje va dos veces (cliente ↔ bandeja y bandeja ↔
  vendedor). Dentro de la ventana y debajo de las 1.000 gratis, $0 de Meta; si no, ~USD 0,012 por mensaje
  de bandeja más la plantilla al vendedor si hace falta.
- **Canales:** con 10, unas 5 derivaciones a la vez dejan sin canales al resto de las llamadas. Antes del
  primer cliente con derivación hay que medir el uso o sumar un paquete.

## 8. Testing de punta a punta

| Nivel | Qué | Cómo |
|---|---|---|
| Unitarios | Elegir el destino (horario, orden, round robin), estados de la derivación, fallback, comandos `#`, costo | pytest con fakes de `SipService` y de Meta, como `test_campaign_dialer.py` |
| Motor | Que el LLM derive cuando corresponde y no cuando no | Escenarios en `make eval-llm` (cliente simulado: "quiero hablar con alguien", "fuera de horario", troll), con Gemma |
| **SIP de punta a punta** | Llamada entra, el agente deriva, el destino atiende, no atiende, da ocupado o atiende un contestador, persona → IA, cuelga cada lado; timeline y costo en la base | Stack aislado `docker-compose.e2e-sip.yml` (proyecto aparte, sin puertos del host): LiveKit, `livekit-sip` y Asterisk propios, más un **Asterisk "falso Anura"** con extensiones que atienden con audio, dan ocupado, no atienden o contestan como buzón, y `app`/`agent` de prueba contra la inferencia por el proxy. El cliente es el caller del loadtest. `make test-e2e-sip`. Nunca contra el Asterisk ni el LiveKit vivos |
| WhatsApp | Puente, cita, sin cita, `#cerrar`, `#pasar`, ventana vencida, medios | Fixtures de webhook (`tests/fixtures/wa/`) más una prueba real con dos números propios |
| Humo antes de desplegar | Una derivación real por Anura y una por WhatsApp | Con números propios, a mano, con checklist |
| Capacidad | Workers en escucha y 2 canales por transferencia | Un perfil del test de capacidad con un % de derivadas: `CAP-NNN` |

## 9. Decisiones

Tomadas con Laureano el 23-oct-2026:

1. **Minutos:** cada tramo se descuenta del plan: el del cliente, por su tipo, y el de la persona, como
   saliente (4.6).
2. **Caller ID que ve el destino:** el número de la empresa (4.6). Anura solo acepta como caller ID un
   número de la cuenta (`asterisk/conf/extensions.conf`, `[to-anura]`, confirmado por Anura el
   29-sep-2026).
3. **Grabación:** opción del cliente, apagada por default, con el aviso "Esta llamada está siendo grabada"
   (4.6). Falta corregir `landing/src/pages/privacidad.astro`, que dice que no se graba audio.
4. **Costos:** solo los ve el admin (6.4).
5. **Canales:** por ahora no se suman.
6. **Contestador:** se detecta automáticamente (paso 4) y, como respaldo, se pide confirmación con un dígito
   (paso 5). Sin confirmación, el agente vuelve con el cliente. El mensaje para "no atiende", "ocupado" y
   "fuera de horario" es configurable (4.7).
7. **Música de espera:** siempre que el cliente espera, con prendido/apagado y tema configurables (4.8).

## 10. Fases

Estimaciones a mano, sin medir.

| Fase | Contenido | Para quién |
|---|---|---|
| 0. Spikes (2-3 días) | Dos tramos a la vez por Anura con transferencia por `create_sip_participant` y pistas sin publicar; DTMF por LiveKit SIP; caller ID del cliente en el tramo; WhatsApp Calling → Anura; puente de WhatsApp con dos números propios | Todas |
| 1. Base (3-4 días) | `team_members`, `handoff_areas` con horarios, tabla `events` y `Message.at`, UI de equipo y áreas, stack `e2e-sip` | Todas |
| 2. Transferencia de llamada (1-1,5 semanas) | Marca y tool `derivar`, espera, whisper, fallback, modo escucha con grabación y transcripción, contador de canales, costo del tramo | Goldman, SQL, CIMEPA |
| 3. Puente de WhatsApp (1 semana) | Hilo en `handoff`, reenvío y cita, comandos, timeout y reasignación, plantilla | Goldman, SQL, BAIC |
| 4. Panel (4-5 días) | Línea de tiempo, Derivaciones por persona y área, resumen por canal y fuera de horario | Goldman, BAIC, SQL |
| 5. Webhook, API y CSV (3 días) | `client_webhooks`, outbox, `/events` | CIMEPA, Axioma, Zennon |
| 6. Persona → IA y softphone web (2-3 semanas) | `2` y `#ia`, web client logueado para salientes del empleado, presencia | CIMEPA |

Con Goldman como primer piloto, las fases 0 a 4 son el camino corto (unas 4 semanas). Si no llega a
noviembre, el piloto arranca con ficha (fallback de la fase 2 sin transferencia) y se suma la transferencia
en vivo después.

## 11. Spike de la transferencia (23-oct-2026)

`scratch/spike-derivacion/spike.py`, contra el LiveKit y el Anura reales, sin el worker: room `spike-*`,
el script hace de agente. Dos celulares propios, en aparatos distintos (cliente y vendedor). Eventos y
WAV de cada corrida en `scratch/spike-derivacion/runs/`.

### 11.1 Resultados

| Qué | Resultado |
|---|---|
| Dos salientes a la vez por Anura en la misma room | Anda |
| Aislar cliente y vendedor (`update_subscriptions`) | Anda; se aplica en 2-3 ms. **El vendedor entra a la room al empezar a sonar** (8-11 s antes de atender): hay que aislar al publicarse su pista, no al atender. Con eso el cliente solo oye la música |
| Pistas propias por destinatario (`set_track_subscription_permissions`) | Anda: el whisper lo oye solo el vendedor, la música solo el cliente |
| Timbre hasta atender | Cliente 7,1-11,2 s; vendedor 6,0-13,6 s (5 corridas) |
| Contestador por STT con el vendedor callado | Sin texto, no lo toma por buzón (correcto). Sin probar con un buzón real |
| DTMF por LiveKit SIP (`sip_dtmf_received`) | Llega, con la identidad de quien marcó |
| Whisper hasta el 1 | 6,0-10,7 s, más 3 s de escucha: el cliente espera ~18 s desde "te paso". A achicar (escuchar en paralelo, whisper más corto) |
| Sin atender en el timbre | `create_sip_participant` falla con `sip request timed out` (nuestro `ringing_timeout`), no con un código de Anura |
| Cuelga el vendedor | El cliente queda en línea: el agente tiene que retomar o despedirse (el spike se despide) |
| Cuelga el cliente | Se cierra todo |
| `#9` del vendedor | Vuelve la IA; el cliente sigue en línea |
| Atiende y no marca 1 | A los 14 s (8 de confirmación + ~6 de whisper) se saca al vendedor y el cliente oye "No pude comunicarte..." |
| Atiende y cuelga durante el whisper | El agente tiene que volver al instante, no al vencer la espera (en el spike daba error al sacar a un participante que ya no estaba: corregido) |
| No atiende, cae al buzón (Claro, iPhone) | El buzón atiende a los **33,5 s**; en los 3 s de escucha el STT dio "Bienvenido al buzón de voz Claro" y la lista de frases lo marcó `machine`: se saca al vendedor sin whisper y el cliente oye el mensaje. **Con un timbre por miembro de 20-25 s se corta antes de que atienda el buzón** (sin minuto de Anura); la detección y el 1 quedan de respaldo |
| Rechaza (Claro, iPhone, doble toque del botón lateral) | **No da ocupado:** Claro lo desvía al buzón, que atiende a los 5,4 s; el detector lo marcó `machine` igual. Con Claro, "ocupado" (486) no se ve nunca: el rechazo cuesta un minuto de Anura y lo resuelve el detector. El mensaje de ocupado queda para operadoras o líneas sin buzón (sin medir) |

### 11.2 Trampa: `*` + dígito en Anura

Marcar **`*9`** en una llamada hace que **Anura corte la otra llamada activa** de la cuenta, ~0,3 s después
(BYE desde Anura: en la consola de Asterisk se va primero el canal `anura-*`). Pasó 4 de 4 veces, desde
cualquiera de los dos teléfonos; a veces el `*` ni llega (solo el 9). Con `#9` no pasa. Se le preguntó a
Anura qué códigos interpreta y si se pueden desactivar.

- Los códigos para la persona van con `#`, nunca con `*`.
- Las campañas no marcan DTMF: no les afecta.
- Un cliente final que marca `*` + dígito en una llamada con derivación podría cortar la del vendedor:
  esperar la respuesta de Anura.

### 11.3 Para la implementación

- `AudioSource`: cancelar la tarea en medio de `capture_frame` deja la fuente en `InvalidState` y el audio
  siguiente no sale. La música se corta con una bandera entre frames y después `clear_queue()`.
- Si el vendedor cuelga durante el whisper o la espera del 1, volver al cliente al instante.
- El detector de buzón por frases es la defensa principal con Claro: un rechazo atiende como buzón a los
  ~5 s y uno sin atender a los ~33 s. Medir otras operadoras (Personal, Movistar) y buzones sin saludo
  antes de confiar solo en él.
- Sin probar todavía: ocupado real (486), otras operadoras, llamada de WhatsApp → Anura y el puente de
  WhatsApp.

## 12. Fase 1: estado y cómo desplegar (23-oct-2026)

Desplegada el 23-oct-2026.

- **Migración `0023`:** `team_members`, `handoff_areas`, `handoff_area_members`, `events` y
  `tiers.max_team_members` (los tiers existentes quedan sin tope). Probada ida y vuelta en SQLite
  (`tests/test_migration_0023.py`) y contra la copia del backup del 23-oct-2026 en PostgreSQL
  (`make migrate-test`: 0022 → 0023 → 0022 → 0023).
- **Backend:** `app/models/handoff.py`, `app/services/handoff.py` (miembros, áreas, horario, orden de llamado,
  mensajes por defecto), `app/services/events.py` y `app/api/routers/handoff.py`: `/api/v1/team`,
  `/api/v1/handoff-areas` (y `/defaults`) y `/api/v1/events` (cursor `after_id`, filtro por tipo o prefijo).
  `services/calls.update_call` registra `call.ringing`, `call.answered` y `call.ended` al cambiar el estado.
  `Message.at`: hora de cada mensaje nuevo. Tests en `tests/test_handoff.py`.
- **UI:** pantalla **Equipo** (`web/src/features/team/`): personas y áreas con horario, orden, mensajes,
  tecla de vuelta y qué hacer si la persona corta; campo "Personas del equipo" en Tiers. Ver
  [`GUIA_UI.md`](GUIA_UI.md).
- **Prueba SIP aislada:** `make e2e-sip` (`docker-compose.e2e-sip.yml`, `tests/e2e_sip/`): LiveKit, `livekit-sip` y
  nuestro Asterisk con la config de producción contra un Anura falso, en una red interna sin puertos del host.
  7 de 7 casos: atiende y marca 1 y 2, ocupado (486), no atiende, buzón, congestión (503), atiende y corta, y dos
  tramos a la vez aislados. Sin inferencia: en la fase 2 se suman `app` y `agent`.

Desplegar: `make migrate-test`, `make migrate`, `make calls-active && make up-agent` (recrea `app` y `agent`).
Sin la fase 2 no cambia nada para quien llama: solo se cargan el equipo y las áreas, y empiezan a registrarse
los eventos de las llamadas.

## 13. Fase 2: transferencia de llamadas (23-oct-2026)

Desplegada el 23-oct-2026 (migración 0024, `app` y `agent`). Falta la prueba con llamadas reales (13.4).

### 13.1 Qué hace

- **Configuración en el agente** (versionada, `Workflow.handoff`): las áreas a las que puede pasar la llamada,
  cada una con "cuándo" en texto libre (vacío: la descripción del área), y la música de espera (prendida por
  defecto, tema y volumen). Solo el motor `classic`; con otro motor y áreas, el guardado da 422. Al guardar se
  valida que cada área sea del cliente del agente y que el tema exista. Temas: `GET /api/v1/hold-music`
  (`default`, el de LiveKit Agents, y los `.ogg` de `storage/hold-music/`; subir uno propio queda para después).
  Un área que usa un agente no se borra (409 `area_in_use`, con los nombres de los agentes). Si se borra un `.ogg`,
  la llamada usa el tema `default`, pero el agente no se puede guardar hasta cambiar el tema.
- **Prompt (`classic`):** sección "PASAR LA LLAMADA A UNA PERSONA" con cada área, su horario y si atiende
  ahora. El LLM responde solo `[DERIVAR:<área>]`; el área se busca sin mayúsculas ni tildes. Fuera de horario,
  el prompt le dice que no derive y tome el mensaje. Las áreas de la llamada quedan en
  `Progress.handoff_areas` al empezar.
- **Cuándo no hay derivación:** loadtest, demo de la landing (salvo con `DEMO_HANDOFF`) y campañas (metadata `handoff`), WhatsApp de
  mensajería (fase 3) y los agentes sin áreas.
- **Flujo** (`app/voice/handoff.py`: `Transfer` es la lógica, `RoomLine` el lado de LiveKit; 4.1):
  1. revisa el área (activa, en horario, con miembros con teléfono), los minutos salientes y los canales;
  2. avisa ("transfer", si el LLM no dijo nada) y pone la música, solo al cliente;
  3. llama a cada miembro con el timbre del área;
  4. al atender, en paralelo: STT de los primeros 3 s contra las frases de buzón y el whisper, solo a la
     persona. Después del whisper, 8 s (`HANDOFF_CONFIRM_SECONDS`) para marcar 1. Otra tecla, cortar o no marcar
     es `not_confirmed`; un buzón por frases, `machine`;
  5. con el 1, los conecta y queda en modo escucha.
- **Modo escucha:** VAD y STT de los dos lados, en la conversación (`Message.handoff_leg` en los dos lados y
  `Message.person` con el nombre de la persona); con `record_audio`, un WAV por frase.
  - El LLM ve ese tramo como una transcripción en un solo mensaje ("Nota del sistema: la llamada se pasó a…").
  - El resumen por email pone "<persona> (equipo)".
  - Termina con:
    - **el código de vuelta** del área (`2` por defecto): el agente vuelve con "resume";
    - **la persona corta:** "resume", o "goodbye" y corta, según el área;
    - **el cliente corta:** se borra la room y no queda la persona sola;
    - **sin minutos salientes.**
- **Si nadie atiende:** el mensaje "busy" si el último intento dio ocupado; si no, "no_answer". El texto queda
  en la conversación: en el turno siguiente el LLM sabe que no se pudo y toma el mensaje.
- **Resumen del whisper:** un pedido al LLM del turno (JSON `{"resumen"}`, sin razonamiento) mientras suena. Si
  tarda más de 4 s o falla, va "una consulta".
- **Caller ID del tramo:** el número de la empresa por el que entró o salió la llamada; en las de WhatsApp y
  web, el primero del cliente. Asterisk igual pone uno de la cuenta.
- **Aviso de grabación:** con `record_audio` y `recording_notice` (opcional, apagado por default, desde el
  23-oct-2026), el agente dice "Esta llamada está siendo grabada." antes de la apertura (decisión 3).

### 13.2 Minutos, canales y registro

- **Migración `0024`: `handoff_legs`**, un tramo por intento: resultado, código SIP, hora de cada paso y
  `billed_seconds`.
- **Minutos salientes:** `quota.used_seconds` (y por lo tanto el consumo de Mi cuenta) suma los tramos
  conectados desde que atendió la persona; los conectados en curso, lo que llevan. Los sin atender, ocupados,
  contestador y sin confirmar no se descuentan.
- **Canales de Anura:** `quota.busy_channels` cuenta las llamadas activas entrantes y salientes (las de
  WhatsApp entran como entrante: se cuentan de más) más los tramos abiertos, contra `ANURA_CHANNELS` (10). Sin
  canal libre o sin minutos salientes, no se intenta (`handoff.unavailable`).
- **Eventos:** `handoff.requested`, `dialing`, `answered`, `busy`, `no_answer`, `failed`, `machine`,
  `not_confirmed`, `confirmed`, `connected`, `ended` (con los segundos), `returned_to_ai`, `person_hung_up` y
  `unavailable` (con el motivo); `hold.started` y `hold.ended`. Salen por `GET /api/v1/events`.

### 13.3 Pruebas

- `tests/test_handoff_transfer.py`, 10 tests con un teléfono falso (incluye que no se borre un área en uso):
  - ocupado y después conecta y vuelve con 2;
  - contestador, sin marcar y corta durante el whisper;
  - la persona corta (`end`);
  - el cliente corta mientras suena;
  - sin minutos, área desconocida y fuera de horario;
  - minutos salientes y canales;
  - la marca partida en el stream;
  - prompt e historial con el tramo humano;
  - validación del agente.
- `make e2e-sip` suma `tests/e2e_sip/transfer.py`, que corre `Transfer` y `RoomLine` reales contra el
  LiveKit, `livekit-sip` y Asterisk aislados y el Anura falso (TTS y STT falsos, base SQLite propia).
  - 2 de 2, unos 15 s cada uno: ocupado, después atiende, 1 y 2, y el cliente sigue en la room; no atiende,
    corta durante el whisper y no marca, y el agente vuelve.
  - Con los 7 de señalización, 9 de 9.
- Fuera de la e2e, contra la inferencia viva: el TTS del plugin da el whisper (4,4 s para la frase de
  ejemplo) y el STT lo transcribe bien. Silero corta las frases y entrega el audio a 16 kHz
  (`scratch/fase2/`).

### 13.4 Falta

- **Llamada real**, con los dos celulares del spike, una vez desplegado:
  - transferencia desde una entrante y desde la prueba web;
  - no atiende, rechaza (buzón de Claro) y cuelga cada lado;
  - el `2` en medio de la conversación;
  - la llamada de WhatsApp a Anura.

  Es lo único que prueba la `AgentSession` real: entrada de audio apagada en la espera, `say` durante la
  derivación, y los permisos de pistas con la pista de RoomIO.
- **Eval del LLM:** que Gemma escriba la marca cuando corresponde y no cuando no (escenarios en `make eval-llm`).
- **Fuera de esta fase:**
  - motor `assistant` (tool `derivar`) y `structured`;
  - derivación en campañas;
  - tema de espera propio subido por el cliente;
  - música mientras una tool tarda;
  - un detector de contestador por audio (LiveKit Agents 1.8.8 trae `voice.amd`, pero clasifica con un LLM y
    un STT de Cloud);
  - el costo por llamada (fase 4).

### 13.5 Cómo desplegar

`make migrate-test`, `make migrate` y `make calls-active && make up-agent` (recrea `app` y `agent`). Sin áreas
en ningún agente no cambia nada para quien llama. El aviso de grabación es opcional (`recording_notice`).

