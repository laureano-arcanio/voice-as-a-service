# Plan: WhatsApp en el mismo agente (mensajería)

Diseño (2026-09-28). **Estado: Fase 0 completa (1-oct-2026): ida y vuelta real con el número de prueba (plantilla saliente por la Graph API y mensaje entrante por el webhook firmado, vía el túnel). El agente todavía no responde: fase 1.** El plan de salida al mercado
([`mercado/plan-salida-al-mercado.md`](mercado/plan-salida-al-mercado.md), secciones 4 y 7) pone
WhatsApp texto en el mes 5 y Calling en el 6: es donde el cliente de cobranzas sigue la conversación
y el canal que Vapi no tiene y Botmaker sí
([`competencia/`](competencia/botmaker/botmaker-canales-integracion.md)).

**Fase 1 implementada (1-oct-2026), pendiente de deploy:** el agente responde texto por WhatsApp con
el mismo motor. Detalle y pasos de deploy en [5.1](#51-fase-1-lo-implementado).

Responde:

1. **Cómo hablan los agentes (definición JSON versionada en la base) por WhatsApp** con el mismo motor
   (`ConversationEngine`), sin voz: mensaje entrante → turno → respuesta.
2. **Cómo se registra un número:** el de Anura (fijo, sin SMS: verificación por llamada de voz,
   atendida por nuestro propio pipeline) y el que trae cada cliente.
3. **Qué hace falta con Meta** para que un cliente conecte su número desde nuestro dashboard
   (Tech Provider, Embedded Signup) y **cuánto cobra Meta** por mensaje.

## 1. Decisiones

| Decisión | Elección | Por qué |
|---|---|---|
| Vía de acceso | **Cloud API de Meta, directo**, con nuestra app como *Tech Provider* | Sin intermediario por mensaje (un BSP como 360dialog, Twilio o Infobip cobra un margen sobre Meta y agrega otra dependencia). Meta es inevitable: WhatsApp es de Meta. Es la única dependencia externa nueva del stack |
| Librerías no oficiales (Baileys, whatsapp-web.js) | **Descartadas** | Violan los términos; Meta banea el número. Inaceptable con el número de un cliente |
| Motor | **El mismo `ConversationEngine` y los mismos YAML**, con reglas por canal | `POST /conversations/{id}/turn` ya conversa por texto; el eval de calidad (`docs/eval/`) corre así. Cambia el prompt de canal, no el motor |
| Dónde corre | En `app` (FastAPI), no en `agent` | El webhook es HTTP; no hay room, STT ni TTS. `agent` sigue siendo solo voz |
| Datos | Mensajes y estado en PostgreSQL, como las llamadas | El dashboard muestra la conversación igual que una llamada, con origen "WhatsApp" |
| Salientes | Solo con plantillas aprobadas por Meta (categoría *utility* para recordatorios y confirmaciones) | Fuera de la ventana de 24 h Meta no entrega texto libre. Es la regla de la plataforma, no una limitación nuestra |

## 2. Cómo encaja en la app

```text
cliente final (WhatsApp)  <->  Meta Cloud API  <->  Cloudflare Tunnel  <->  app: /wa/webhook
                                                                               |
                                                     app/whatsapp/service.py: turno = ConversationEngine.process_turn
                                                                               |
                                                     app/whatsapp/graph.py: POST /{phone_number_id}/messages
```

**Un turno por WhatsApp.** Llega el webhook `messages` → se responde 200 al instante y se procesa en
segundo plano (Meta reintenta si no recibe 200, y con el LLM tardando ~0,6–0,9 s por turno no se
puede responder en línea) → se descarta si el `wamid` ya se procesó (Meta reenvía) → se busca la
conversación activa de `(phone_number_id, wa_id)` o se crea una → `process_turn` → se manda la
respuesta por la Graph API → se guarda el `wamid` de salida para seguir `sent/delivered/read` por el
webhook `statuses`. Igual que la voz, un turno a la vez (lock por contacto, `(phone_number_id, wa_id)`);
si el cliente manda tres mensajes seguidos en 2 s, se juntan en un turno (el equivalente de
`CONTINUATION_WINDOW` del agente de voz), ordenados por el timestamp de Meta.

**Entrante vs. saliente.**
- *Entrante* (el cliente final escribe): hoy `start_conversation` guarda la apertura del workflow como
  primer mensaje del agente, pensado para una llamada donde el agente habla primero. Por WhatsApp
  escribe primero el cliente: se crea la conversación sin apertura y el primer mensaje es el turno 1,
  así el LLM saluda y contesta lo que preguntó: `new_conversation(..., opening=False)`.
- *Saliente* (el negocio inicia): `POST /wa/messages {to, template, workflow_id, params}` manda la
  plantilla y crea la conversación con el texto de la plantilla como apertura. La respuesta del
  cliente es el turno 1 y abre la ventana de 24 h. Sirve para cobranza, turnos y recordatorios; es
  la campaña mínima de la sección 4 del plan de mercado, por texto.

**Fin de conversación.** El `[FIN]` del motor clásico corta la llamada; por WhatsApp solo marca
`completed` y dispara la extracción, como ahora. Un mensaje nuevo después de completada, o tras N
horas sin actividad (configurable, sugerido 24 h), abre otra conversación con el mismo workflow. La
derivación a humano queda como resultado del workflow (`outcome` con `handoff: true`): la app deja de
responder en esa conversación y avisa (webhook del cliente o email).

**Reglas por canal.** Las reglas de voz están en los YAML ("números en palabras", "correos como se
dicen", "dos frases por turno") y en `SYSTEM_PROMPT` ("agente conversacional telefónico"). El canal
se guarda en la conversación (`conversations.channel`, `voice | whatsapp`, default `voice`), no en el
workflow, y `prompt.py` suma el bloque base del canal:
por WhatsApp, números en cifras, emails como dirección, hasta ~300 caracteres, sin markdown pesado
(WhatsApp solo renderiza `*negrita*` y `_cursiva_`), y el extractor sabe que lee texto escrito, no una
transcripción. El mismo agente atiende voz y WhatsApp: no hay variantes por canal.

**Tablas nuevas** (modelos en `app/models/whatsapp.py`, migración de Alembic nueva en `migrations/versions/`):

| Tabla | Qué guarda |
|---|---|
| `wa_accounts` | Una por número conectado: `waba_id`, `phone_number_id`, número visible, nombre, token de acceso (cifrado con una clave de `.env`), `agent_id` por defecto, `client_id` (tenant), estado |
| `wa_threads` | `(phone_number_id, wa_id)` → `conversation_id` activa, último mensaje del cliente (para la ventana de 24 h), `paused` (derivado a humano) |
| `wa_messages` | `wamid`, dirección, `conversation_id`, tipo (texto, audio, imagen, plantilla), estado (`sent/delivered/read/failed`), error de Meta, timestamps. Idempotencia y costos |

`conversations` sigue guardando el estado y los mensajes; `wa_threads` es a WhatsApp lo que
`call_logs` es a la telefonía. La UI lista origen `whatsapp` junto a `api`, `entrante` y
`saliente`, y `/calls/<id>` muestra el chat igual que una llamada (sin latencia por turno de STT/TTS).
Los mensajes cuentan contra el tier del cliente (a definir: conversaciones o mensajes por mes).

**Archivos:**

```text
app/whatsapp/
  graph.py        cliente de la Graph API: enviar texto/plantilla, marcar leído, bajar media, request_code/verify_code/register
  webhook.py      GET /wa/webhook (challenge) y POST /wa/webhook (firma X-Hub-Signature-256 con el app secret)
  service.py      del webhook al motor y de vuelta: dedupe, lock, juntar mensajes, ventana de 24 h, audios
  store.py        acceso a wa_accounts, wa_threads, wa_messages (modelos en app/models/whatsapp.py)
  verify.py       registro del número: pedir código por voz, capturarlo de la llamada, verificar, registrar con PIN
app/api/routers/whatsapp.py  API de cuentas, registro y prueba de envío (/api/v1/whatsapp/...)
web/src/features/whatsapp/   UI: cuentas conectadas, estado del número, registro, prueba de envío
(el agente es el mismo de la base; una variante para chat es otra versión o agente del cliente)
tests/test_whatsapp.py      webhook con payloads reales grabados + FakeLLM; firma inválida; wamid repetido; ventana de 24 h
```

**Variables de `.env`:** `WA_APP_ID`, `WA_APP_SECRET`, `WA_VERIFY_TOKEN`, `WA_ACCESS_TOKEN` (system user
de nuestro portafolio, fases 0 y 1), `WA_PUBLIC_URL` (`https://wa.atentina.com.ar`, el webhook por el túnel), `WA_PHONE_NUMBER_ID` (solo `scripts/wa.py`),
los de la fase 1 (`WA_SESSION_HOURS`, `WA_DEBOUNCE_SECONDS`, `WA_UNSUPPORTED_REPLY`, `WA_MAX_REPLY_CHARS`,
`WA_MAX_TURN_CHARS`, `WA_MAX_TURNS`; ver `.env.example`) y `WA_TOKEN_KEY` (fase 2: cifrado de los
tokens de clientes en `wa_accounts`). Como `VLLM_API_KEY`, el chequeo de
[`.env`](../AGENTS.md) antes de reiniciar.

**HTTPS.** Meta exige webhook por HTTPS con certificado válido. Sale por el Cloudflare Tunnel que ya
usa la landing (`docker-compose.tunnel.yml`, [`LANDING.md`](LANDING.md)): hostname
`wa.atentina.com.ar`, regla de path `^/wa/webhook` hacia `http://localhost:8011` y certificado de
Cloudflare. No se abre el 443 en el router ni hay certbot. Lo que no coincide con la regla da 404
en el túnel. El proxy `:8100` (`/llm`, `/stt`, `/tts`) sigue HTTP plano, aparte (la clave del modo
remoto viaja en claro: es otro tema).

**Audios.** El cliente final manda notas de voz (`type: audio`, ogg/opus): se baja por la API de
media, se pasa a 16 kHz mono (ffmpeg) y va a `stt-parakeet`; el texto entra como turno normal. Es el
mismo STT de las llamadas, y el audio de WhatsApp es mejor que el telefónico (ver WER `clean16k` en
el README). Responder con audio de `vllm-tts` (wav → ogg/opus) queda opcional, fase 3: el usuario de
WhatsApp espera texto. Imágenes y documentos: el agente dice que no los puede ver (regla del canal).

**Capacidad.** Un turno de WhatsApp es un pedido al LLM, sin STT ni TTS: carga solo la 3090. En
CAP-002 el cuello es el TTS en la 5060 Ti, no el LLM, así que el texto convive con las llamadas hasta
que se mida. Un perfil `whatsapp` del test de capacidad (`scripts/capacity/perfiles/`) que pegue al
webhook con payloads sintéticos y mida la respuesta p95 por turno, registrado como `CAP-NNN`.

## 3. Números

### 3.1 El número de Anura (el nuestro): registro por llamada de voz

Meta acepta fijos y VoIP; el código de verificación va por SMS o por **llamada de voz** (una locución
lee 6 dígitos). Anura no tiene SMS, así que es por voz. Después de registrado, el número **sigue
recibiendo llamadas comunes**: el mismo número atiende llamadas (Asterisk → LiveKit → agente) y
WhatsApp (Cloud API). Un número que ya tiene cuenta en la app de WhatsApp no se puede registrar sin
borrarla antes; el de Anura no la tiene.

La llamada de Meta entra como cualquier entrante: Anura → Asterisk → LiveKit → `agent`, que hoy
arranca el workflow por defecto y responde. Restricción de Meta: la llamada no navega IVR y tiene que
poder atenderla "una persona". Nuestro agente atiende al primer ring, así que sirve. Dos etapas:

1. **Prueba de humo, sin código:** pedir el código por voz (desde WhatsApp Manager o con
   `POST /{phone_number_id}/request_code {code_method: "VOICE", language: "es"}`) con el agente
   corriendo. El STT transcribe lo que dice la locución y queda en el transcript de `/calls/<id>`,
   que se actualiza cada segundo; se lee el código ahí y se carga en `verify_code`. El agente va a
   contestarle a la locución, no importa: la locución repite el código varias veces. Confirma que
   Anura acepta la llamada internacional de Meta y que Parakeet la transcribe.
2. **Modo verificación** (`verify.py`): un botón en la UI (`web/src/features/whatsapp/`) deja una marca
   `wa_verification_pending` (en la base). Mientras está puesta, `agent` trata la entrante sin
   metadata como verificación: no habla, transcribe hasta 60 s, saca los 6 dígitos (regex sobre
   cifras y sobre dígitos en palabras, con `scripts/stt_corpus/entity_match.py`), los guarda y corta.
   La app llama a `verify_code` y a `register` (con el PIN de verificación en dos pasos) sola. Sirve
   para reverificar sin que nadie mire el transcript.

Anotar el resultado en [`TELEFONIA_ANURA.md`](TELEFONIA_ANURA.md) (nueva sección): si Anura acepta
o no la llamada internacional de Meta, en qué idioma habla la locución y cuánto tarda en llegar.

### 3.2 El cliente trae su número

Tres casos, según el número:

| Número del cliente | Cómo se registra | Trampas |
|---|---|---|
| Nuevo o sin WhatsApp (celular o fijo) | Verificación por SMS o voz **que recibe el cliente** dentro de Embedded Signup (3.3) | Si es un fijo con IVR, Meta no lo navega: alguien tiene que atender la llamada |
| Ya en la app de WhatsApp Business | **Coexistencia**: el mismo número en la app y en la API (Embedded Signup con QR desde la app) | La app tiene que abrirse cada 13 días; sin llamadas, grupos ni catálogo; 20 mensajes/s fijos. Si el número tiene poca historia en la app, Meta puede rechazarlo |
| Ya en WhatsApp personal | Borrar la cuenta de la app (pierde la historia) y registrar como nuevo | El cliente tiene que aceptar perder el historial; casi siempre conviene un número nuevo |

Límites de Meta por cuenta del cliente (WABA): 2 números hasta verificar el negocio, 20 después;
envíos iniciados por el negocio a ~250 destinatarios únicos por día sin verificación, y de ahí
escalones de 1.000, 10.000 y 100.000 según verificación y calidad (confirmar los valores vigentes en
el alta del primer cliente). Recibir mensajes no tiene tope.

### 3.3 Tech Provider y Embedded Signup (Meta)

Para que el cliente conecte su número **desde nuestro dashboard** sin pasar por Meta a mano:

1. **Verificación del negocio** (nuestro) en Meta Business: razón social, domicilio, teléfono, sitio
   y documentos si no nos encuentra. Días a semanas: arrancar el día uno.
2. **App de Meta** con el producto WhatsApp, configuración de *Facebook Login for Business* y
   **App Review** con acceso avanzado a `whatsapp_business_messaging` (mandar mensajes por el cliente)
   y `whatsapp_business_management` (ver su WABA, plantillas, número). Piden videos del flujo de
   mensajes y de creación de plantillas. Meta dice ~24 h de revisión; en la práctica hay idas y
   vueltas.
3. **Embedded Signup v4** (la v2 se discontinúa el 15-oct-2026) en la UI (`web/src/features/whatsapp/`): el
   cliente entra con su cuenta de Facebook en un popup, crea o elige su portafolio y su WABA, carga
   el número y lo verifica (SMS o voz); el popup devuelve un código que `app` cambia por un *business
   token* del cliente y los `waba_id` y `phone_number_id`. Con eso `app` suscribe nuestra app a los
   webhooks de esa WABA, registra el número (PIN) y lo guarda en `wa_accounts`. Un solo webhook
   (`/wa/webhook`) recibe los mensajes de todas las cuentas; se enruta por `phone_number_id`.
4. Cada cliente pone **su medio de pago** en su WABA: los mensajes se los cobra Meta a él, no a
   nosotros (ver sección 4). Nosotros cobramos el agente.

Sin esto (fases 0 y 1) solo podemos operar números de **nuestro** portafolio: el de Anura y, para un
piloto, el de un cliente cargado en una WABA nuestra a su nombre (él recibe el código y nos lo pasa),
con el nombre visible de su negocio. Es aceptable para 1 o 2 pilotos; no para vender.

## 4. Lo que cobra Meta

Por mensaje entregado, según categoría y país del destinatario (Argentina tiene tarifa propia y
desde abril de 2026 se puede facturar en pesos). Valores publicados para Argentina, en USD por
mensaje, a confirmar contra el rate card de Meta al armar la calculadora:

| Categoría | Cuándo | Precio |
|---|---|---|
| Servicio (texto libre dentro de las 24 h desde el último mensaje del cliente) | Toda respuesta del agente a un cliente que escribió | **Gratis hasta el 30-sep-2026.** Desde el 1-oct-2026 se cobra como *utility*, con **1.000 gratis por mes por número** (no se acumulan) |
| Utility (plantilla) | Recordatorio, confirmación, aviso de cuenta | ~0,012 |
| Autenticación (plantilla) | Códigos | ~0,022 |
| Marketing (plantilla) | Promociones | ~0,062, sin descuento por volumen |
| Punto de entrada gratis | El cliente escribe desde un anuncio de Facebook o Instagram | 72 h sin cargo |

Con estos números, una gestión de cobranza por WhatsApp (1 plantilla + ~6 respuestas) cuesta
~USD 0,08 de Meta desde octubre, contra ~3 minutos de llamada por Anura. **Sin medio de pago cargado
antes del 30-sep-2026 Meta deja de entregar los mensajes de servicio el 1-oct.** Va en la calculadora
de costos ([`calculadora-costos.html`](calculadora-costos.html)) como canal aparte.

**Calling API** (llamadas de voz por WhatsApp, fase 5): las que inicia el usuario son gratis; las
que inicia el negocio se cobran por minuto en pulsos de 6 s, por país y con escalones por volumen
(rate card de Argentina desde abril de 2026; el plan de mercado estimó ~USD 0,011 por minuto),
más el mensaje de pedido de permiso, que se cobra como mensaje. Requisito que hoy no cumplimos:
límite de envío de al menos **2.000 destinatarios por día**, o sea negocio verificado y calidad.

## 5. Fases

| Fase | Qué queda | Entregable medible | Esfuerzo |
|---|---|---|---|
| **0. Cuenta y número** | Meta Business + verificación del negocio (empieza acá, tarda), app con WhatsApp, medio de pago, webhook por el túnel (`wa.atentina.com.ar`), webhook GET/POST con firma, número de Anura registrado por voz (3.1, prueba de humo), primer "hola" enviado y recibido | Un mensaje ida y vuelta con el número de Anura; resultado de la llamada de Meta anotado en `TELEFONIA_ANURA.md` | 1 semana de trabajo; la verificación de Meta corre en paralelo |
| **1. El motor por WhatsApp** | `app/whatsapp/` (2), tablas, reglas por canal (sin variante `_wa` del agente, ver 5.1), dashboard con origen WhatsApp, saliente por plantilla, tests con payloads grabados, modo verificación (3.1, etapa 2), `make wa-send` para probar | El agente de demo conversa por WhatsApp de punta a punta; eval de calidad corrido con `channel: whatsapp` (`make eval-llm`) y comparado con voz | 2 semanas |
| **2. Clientes con su número** | Tech Provider, App Review, Embedded Signup v4, `wa_accounts` multi-cliente con tokens cifrados, coexistencia, alta desde el dashboard | Un cliente conecta su número sin tocar Meta a mano; un piloto con número del cliente | 2 semanas de trabajo + tiempos de Meta (semanas) |
| **3. Operación** | Notas de voz por STT, derivación a humano con aviso, plantillas gestionadas desde la app, `wa_messages` con costo por cliente en el dashboard, perfil `whatsapp` del test de capacidad y `CAP-NNN`, webhook de resultado para el software del cliente | Reporte por campaña con costo de Meta por gestión; capacidad medida | 2 semanas |
| **4. Campañas** | Carga por CSV o API, ventana horaria, reintentos, opt-out ("no me escriban más" → no volver a mandar plantillas), lo mismo que pide la sección 4 del plan de mercado para voz | Campaña de cobranza por WhatsApp con un piloto | Se comparte con la campaña de voz |
| **5. Calling API** | Llamadas de WhatsApp por SIP (Meta ofrece SIP con TLS además de WebRTC) → Asterisk → LiveKit: el mismo agente de voz, sin telefonía. Requiere el límite de 2.000 destinatarios por día | Una llamada entrante de WhatsApp atendida por el agente de voz | 1–2 semanas, después de tener el límite |

Orden: 0 y 1 dan valor con el número propio; 2 destraba la venta; 3 y 4 son lo que pide el piloto de
cobranzas; 5 cuando la cuenta lo permita.

### 5.1 Fase 1: lo implementado

Estado al 1-oct-2026: código y tests listos (`tests/test_whatsapp_*.py`, con FakeLLM y payloads con
la forma de Meta en `tests/fixtures/wa/`). **No está desplegado.**

- **Entrante de texto:** el webhook responde 200 sin esperar y `app/whatsapp/service.py` sigue en segundo
  plano: dedupe por `wamid` (unique en `wa_messages`), cuenta por `phone_number_id`, conversación activa
  del contacto o una nueva **sin apertura** (el primer mensaje del cliente es el turno 1), junta lo que
  llega en `WA_DEBOUNCE_SECONDS` (2 s) en un turno, un turno a la vez por contacto, `send_text` y
  `mark_read`. Si llega texto mientras responde el LLM, deshace el turno y responde todo junto.
- **Topes:** `WA_MAX_TURN_CHARS` (2000) por turno, lo que pase se descarta; `WA_MAX_TURNS` (40) por
  conversación, después sigue en otra. Así un contacto o un bot no pasa el contexto del LLM (32768).
  Los turnos por la API (`/conversations/{id}/turns`) a una conversación de WhatsApp dan 409.
- **Statuses:** `sent < delivered < read` no retrocede; `failed` gana y guarda el error de Meta. Un
  envío fallido (ej. 131047, fuera de las 24 h) se guarda y no se reintenta.
- **No texto** (audio, imagen, documento...): `WA_UNSUPPORTED_REPLY`, una vez por ventana, sin LLM.
- **Fin:** `completed` del motor cierra la conversación; el mensaje siguiente, o uno después de
  `WA_SESSION_HOURS` (24) sin actividad, abre otra con el mismo agente. La vencida queda `active`
  ("Incompleto"), igual que una llamada que se corta antes de terminar.
- **Reglas por canal:** el canal sale de la conversación (`conversations.channel`); con `whatsapp` el
  prompt pide texto escrito (cifras, emails como dirección, ~300 caracteres, solo `*negrita*`) y pisa
  las reglas de voz de la definición. No hace falta un `demo_booking_wa`.
- **Cuentas:** `wa_accounts` (número → cliente y agente; token NULL = `WA_ACCESS_TOKEN`). API admin
  `/api/v1/whatsapp/accounts`, página **WhatsApp** de la UI y `make wa-account`.
- **Dashboard:** las conversaciones de WhatsApp salen en la lista con origen "WhatsApp" y el `wa_id`;
  el detalle muestra el chat, el número del negocio, el último mensaje y los envíos fallidos.
- **Tier:** solo se exige el cliente activo. Consumo por mensajes y costo de Meta: pendiente (fase 3).

**Para desplegar** (con la app y el número de prueba ya suscriptos):
1. `make migrate` (0004: `wa_accounts`, `wa_threads`, `wa_messages` y `conversations.channel`).
2. Recrear `app` con la imagen nueva (compila la UI).
3. `make wa-account PNID=1376760278849754 WABA=1763082738667089 NUMBER="+1 555 145 6632" AGENT=<slug>`
   (cliente `interno` por defecto), o desde la página WhatsApp.
4. Escribirle al número de prueba y ver la conversación en el dashboard.

**Queda de la fila de la fase 1:** saliente por plantilla desde la app (fase 3), modo verificación
(3.1, etapa 2) y el eval con canal `whatsapp` comparado con voz.

## 6. Riesgos y trampas

- **Meta manda los tiempos:** verificación del negocio y App Review no tienen plazo garantizado.
  Empezar la fase 0 antes que cualquier código.
- **El 1-oct-2026 cambia el costo:** los mensajes de servicio pasan a cobrarse. Toda estimación de
  precio al cliente tiene que ser con el costo nuevo, no con el gratis de hoy.
- **Calidad del número:** Meta baja el límite de envío si los usuarios bloquean o reportan. Plantillas
  sobrias, opt-out respetado y no mandar marketing desde el número de cobranzas.
- **Un número, un negocio:** el nombre visible de la WABA tiene que ser el del negocio que escribe.
  Números de clientes dentro de nuestro portafolio solo para pilotos.
- **Tokens de clientes** en la base: cifrados, nunca en logs, y renovables (el business token de
  Embedded Signup no vence, pero el cliente puede revocarlo: manejar el 401 como "cuenta
  desconectada" en el dashboard).
- **Webhooks duplicados y fuera de orden:** dedupe por `wamid`; `statuses` pueden llegar antes que
  el `sent` propio.
- **El motor en texto no es el de voz:** sin turn detector ni endpointing, pero con mensajes
  partidos ("hola" / "quería saber el precio"): juntar los que llegan en ~2 s.
- **Ventana de 24 h:** si el LLM quiere escribir fuera de la ventana (por ejemplo la extracción
  final tardó), el envío falla con error de Meta; guardar el error en `wa_messages` y no reintentar
  con texto libre.
- **Coexistencia** no soporta llamadas: un cliente que quiera el mismo número para Calling API tiene
  que salir de la app.
- **El webhook depende del túnel:** si `tunnel` está caído, Meta no entrega (reintenta un tiempo y
  después desactiva el webhook). Sin 443 ni certificados propios que renovar.
- **Verificación del negocio:** no aparece en el Centro de seguridad hasta que un producto la pida;
  se inicia desde la app de developers al pedir acceso avanzado (fase 2). Portafolio de Meta:
  `Atentina` (ID 897731003277295). Sin verificar: 2 números por WABA.
- **Cuentas de Meta creadas (1-oct-2026):** app `Atentina` (ID 2192489028351511, caso de uso
  WhatsApp, Graph API v25.0), WABA 1763082738667089 y número de prueba +1 555 145 6632
  (`phone_number_id` 1376760278849754; gratis 90 días, hasta 5 destinatarios verificados). El
  portafolio lo creó la identidad de Instagram; la cuenta de Facebook entró como admin invitada,
  porque developers.facebook.com no acepta sesiones solo de Instagram.
- **El número de prueba nace sin registrar** (`status: PENDING`, `platform_type: NOT_APPLICABLE`):
  todo envío da `133010 Account not registered` hasta `POST /{phone_number_id}/register` con un PIN de
  6 dígitos (`scripts/wa.py register`). El PIN queda en `.env` (`WA_REGISTRATION_PIN`): Meta lo pide al
  re-registrar. Registrado, pasa a `CONNECTED` / `CLOUD_API`; primer `hello_world` aceptado el 1-oct-2026.
- **Celulares de Argentina:** se envía a `54351...` y Meta devuelve `wa_id` `549351...` (con el 9). El
  webhook trae el `wa_id` con 9: es la clave de `wa_threads`, pero responder a `549…` da `131030` (no está
  en la lista de destinatarios de prueba). `service.recipient()` manda sin el 9, que Meta entrega igual.
- **Webhook verificado y `messages` suscripto (1-oct-2026):** Meta valida el GET por el túnel y el POST
  de prueba del panel llega con firma válida (200, una línea `wa webhook:` en el log de `app`). El access
  log de uvicorn tapa `hub.verify_token` (`RedactVerifyToken`).
- **App sin publicar = solo webhooks de prueba:** Meta no entrega mensajes reales (ni de admins) hasta
  publicar la app, y para publicar pide URLs reales de privacidad, condiciones y eliminación de datos.
- **Publicar no alcanza: la WABA tiene que tener la app suscripta.** Configurar el webhook en el panel
  no la suscribe (`GET /{waba_id}/subscribed_apps` daba `[]`); sin eso no llega ningún mensaje real.
  `POST /{waba_id}/subscribed_apps` con el token del system user. Con Embedded Signup (fase 2) va en el
  alta de cada cuenta. App publicada el 1-oct-2026, con las páginas legales de la landing.
- **Dónde se verifica:** con la app publicada, developers.facebook.com → app → Revisar → Verificación
  (`/apps/<app_id>/verification/`): primero "Verificación del negocio" y después "Verificación de acceso"
  (Tech Provider, Meta responde en ~5 días). Antes de publicar no aparece en ningún lado.
- **Verificación del negocio enviada (1-oct-2026):** como *Sole Proprietorship* registrada, nombre legal
  ARCANIO LAUREANO MARTIN y nombre alternativo "Atentina". **Verificado** el mismo día.
- **Verificación de acceso (Tech Provider) enviada (1-oct-2026):** Plataforma SaaS, un solo portafolio,
  sitio atentina.com.ar. En revisión (~5 días). Plazo de Meta para completarla: 30-nov-2026, si no restringe la app.
- **Titular persona física (monotributo), no sociedad:** en la fase 2 puede chocar el nombre legal
  (la persona) con el nombre visible "Atentina" en la verificación y en el perfil del número.

## 7. Fuentes (consultadas el 28-sep-2026)

- Meta, números de negocio (tipos, verificación por SMS o voz, límites por WABA, llamadas comunes
  después del registro): https://developers.facebook.com/documentation/business-messaging/whatsapp/business-phone-numbers/phone-numbers
- Meta, `request_code` (`code_method: SMS | VOICE`, `language`): https://developers.facebook.com/documentation/business-messaging/whatsapp/reference/whatsapp-business-phone-number/phone-number-verification-request-code-api
- Meta, Tech Providers (verificación del negocio, App Review, permisos): https://developers.facebook.com/documentation/business-messaging/whatsapp/solution-providers/get-started-for-tech-providers
- Meta, coexistencia con la app de WhatsApp Business: https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-business-app-users/
- Meta, precios por mensaje y cambios de octubre de 2026: https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing y https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing/non-template-messages
- 360dialog, cobro de mensajes de servicio desde el 1-oct-2026 (1.000 gratis por mes, medio de pago antes del 30-sep): https://360dialog.com/blog/whatsapp-service-message-charging-october-2026/
- Meta, Calling API (WebRTC o SIP con TLS, webhook `calls`, requisito de 2.000 por día) y precios: https://developers.facebook.com/documentation/business-messaging/whatsapp/calling y https://developers.facebook.com/documentation/business-messaging/whatsapp/calling/pricing
- Tarifas de Argentina por categoría (agregador, a confirmar con el rate card): https://ominiflow.com/whatsapp-api-pricing/argentina
- Infobip y Twilio, guías del programa Tech Provider y Embedded Signup v4: https://www.infobip.com/docs/whatsapp/tech-provider-program y https://www.twilio.com/docs/whatsapp/isv/tech-provider-program/integration-guide
- Restricción de IVR en la llamada de verificación: https://sanuker.com/landline-whatsapp-business-platform-en/
