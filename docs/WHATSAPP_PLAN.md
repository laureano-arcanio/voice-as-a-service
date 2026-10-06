# Plan: WhatsApp en el mismo agente (mensajería)

Diseño (2026-09-28). **Estado (1-oct-2026): fases 0 y 1 en producción con el número de prueba (el agente responde por texto) y notas de voz de entrada y salida (fase 3 parcial). Fase 2 (Tech Provider): verificación del negocio aprobada y de acceso en revisión; el código de Embedded Signup está implementado y sin desplegar ([5.3](#53-fase-2-implementada)).** El plan de salida al mercado
([`mercado/plan-salida-al-mercado.md`](mercado/plan-salida-al-mercado.md), secciones 4 y 7) pone
WhatsApp texto en el mes 5 y Calling en el 6: es donde el cliente de cobranzas sigue la conversación
y el canal que Vapi no tiene y Botmaker sí
([`competencia/`](competencia/botmaker/botmaker-canales-integracion.md)).

**Fase 1 en vivo (1-oct-2026):** el agente responde texto por WhatsApp con el mismo motor. Detalle en
[5.1](#51-fase-1-lo-implementado).

**Audios (parte de la fase 3) implementados (1-oct-2026), pendientes de deploy:** las notas de voz entran
por el STT y la respuesta puede salir como nota de voz por el TTS. Ver [5.2](#52-fase-3-parcial-audios).

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
| Dónde corre | En `app` (FastAPI), no en `agent` | El webhook es HTTP y no hay room; los audios van al STT y al TTS por HTTP, como la prueba de voz. `agent` sigue siendo solo voz |
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

**Fin de conversación.** El motor trabaja igual que en una llamada: el clásico extrae al despedirse
(`[FIN]`) o al terminar la conversación, nunca en cada turno. El fin de un chat (cerrado desde el
dashboard, tope de turnos o 24 h sin mensajes, que detecta un barrido cada 5 min) cierra el hilo y
llama a `engine.finish`, como el corte de una llamada. Por WhatsApp el `[FIN]` solo marca `completed`. El chat sigue en la misma conversación (con el
historial) mientras haya mensajes dentro de las 24 h; tras 24 h sin actividad, el siguiente abre otra.
La conversación corre con la versión del agente con que empezó: para que un contacto pase a la versión
vigente sin esperar 24 h, **Cerrar conversación** en el detalle (`POST /api/v1/whatsapp/threads/{id}/close`,
`wa_threads.closed_at`) hace que su próximo mensaje abra otra. La
derivación a humano queda como resultado del workflow (`outcome` con `handoff: true`): la app deja de
responder en esa conversación y avisa (webhook del cliente o email).

**Reglas por canal.** Las reglas de voz están en los YAML ("números en palabras", "correos como se
dicen", "dos frases por turno") y en `SYSTEM_PROMPT` ("agente conversacional telefónico"). El canal
se guarda en la conversación (`conversations.channel`, `voice | whatsapp`, default `voice`), no en el
workflow, y `prompt.py` suma el bloque base del canal:
por WhatsApp, números en cifras, emails como dirección, hasta ~300 caracteres, sin markdown pesado
(WhatsApp solo renderiza `*negrita*` y `_cursiva_`), y el extractor sabe que lee texto escrito, salvo
los mensajes marcados como nota de voz (5.2). El mismo agente atiende voz y WhatsApp: no hay variantes
por canal.

**Tablas nuevas** (modelos en `app/models/whatsapp.py`, migración de Alembic nueva en `migrations/versions/`):

| Tabla | Qué guarda |
|---|---|
| `wa_accounts` | Una por número conectado: `waba_id`, `phone_number_id`, número visible, nombre, token de acceso (cifrado con una clave de `.env`), `agent_id` por defecto, `client_id` (tenant), estado |
| `wa_threads` | `(phone_number_id, wa_id)` → `conversation_id` activa, último mensaje del cliente (para la ventana de 24 h), `paused` (derivado a humano), `closed_at` (cerrada desde el dashboard: el próximo mensaje abre otra) |
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
  audio.py        notas de voz: OGG/Opus -> WAV 16 kHz -> STT; TTS -> WAV -> OGG/Opus (PyAV)
  store.py        acceso a wa_accounts, wa_threads, wa_messages (modelos en app/models/whatsapp.py)
  signup.py       fase 2: Embedded Signup (código → token, suscripción, registro), refresco y plantillas
  crypto.py       fase 2: tokens y PIN cifrados con WA_TOKEN_KEY (Fernet)
  verify.py       registro del número: pedir código por voz, capturarlo de la llamada, verificar, registrar con PIN
app/api/routers/whatsapp.py  API de cuentas, registro y prueba de envío (/api/v1/whatsapp/...)
web/src/features/whatsapp/   UI: cuentas conectadas, estado del número, registro, prueba de envío
(el agente es el mismo de la base; una variante para chat es otra versión o agente del cliente)
tests/test_whatsapp.py      webhook con payloads reales grabados + FakeLLM; firma inválida; wamid repetido; ventana de 24 h
```

**Variables de `.env`:** `WA_APP_ID`, `WA_APP_SECRET`, `WA_VERIFY_TOKEN`, `WA_ACCESS_TOKEN` (system user
de nuestro portafolio, fases 0 y 1), `WA_PUBLIC_URL` (`https://wa.atentina.com.ar`, el webhook por el túnel), `WA_PHONE_NUMBER_ID` (solo `scripts/wa.py`),
los de la fase 1 (`WA_SESSION_HOURS`, `WA_DEBOUNCE_SECONDS`, `WA_UNSUPPORTED_REPLY`, `WA_MAX_REPLY_CHARS`,
`WA_MAX_TURN_CHARS`, `WA_MAX_TURNS`; ver `.env.example`), los de audios (`WA_AUDIO_*`, 5.2) y
`WA_TOKEN_KEY` y `WA_CONFIG_ID` (fase 2: cifrado de los
tokens y PIN de clientes en `wa_accounts`, y la configuración de Embedded Signup; ver 5.3). Como `VLLM_API_KEY`, el chequeo de
[`.env`](../AGENTS.md) antes de reiniciar.

**HTTPS.** Meta exige webhook por HTTPS con certificado válido. Sale por el Cloudflare Tunnel que ya
usa la landing (`docker-compose.tunnel.yml`, [`LANDING.md`](LANDING.md)): hostname
`wa.atentina.com.ar`, regla de path `^/wa/webhook` hacia `http://localhost:8011` y certificado de
Cloudflare. No se abre el 443 en el router ni hay certbot. Lo que no coincide con la regla da 404
en el túnel. El proxy `:8100` (`/llm`, `/stt`, `/tts`) sigue HTTP plano, aparte (la clave del modo
remoto viaja en claro: es otro tema).

**Audios.** El cliente final manda notas de voz (`type: audio`, ogg/opus) o archivos de audio
(mp3, m4a, amr; `voice: false`): se baja por la API de media, se pasa a WAV mono de 16 kHz con PyAV
(sin ffmpeg del sistema) y va a `stt-parakeet`; el texto entra al mismo turno, marcado como nota de
voz. Es el mismo STT de las llamadas, y el audio de WhatsApp es mejor que el telefónico (ver WER
`clean16k` en el README). La respuesta sale como nota de voz si el cliente mandó audio
(`WA_AUDIO_REPLY=mirror`): `vllm-tts` con la voz del agente, WAV → OGG/Opus mono con PyAV. Imágenes,
videos y documentos: respuesta fija (`WA_UNSUPPORTED_REPLY`). Detalle en 5.2.

**Capacidad.** Un turno de texto es un pedido al LLM, sin STT ni TTS: carga solo la 3090. En CAP-002
el cuello es el TTS en la 5060 Ti, no el LLM, así que el texto convive con las llamadas hasta que se
mida. **Un turno con audio usa además STT y TTS:**
- la síntesis de la respuesta entera corre en la 5060 Ti, que en CAP-002 se satura desde ~22 llamadas;
- una nota de 120 s llena sola un batch del STT (`STT_MAX_BATCH_SECONDS=120`) y retrasa el STT de las
  llamadas en curso;
- la conversión de 20 s de audio tarda 30–80 ms de CPU (prototipo con un seno, no con voz).

`WA_AUDIO_CONCURRENCY` (4) limita los pedidos simultáneos desde WhatsApp, por separado al STT y al TTS
(un TTS lento no frena la transcripción); cada pedido tiene un tope total con la espera incluida (STT
45 s, TTS 90 s; si se pasa, respuesta fija o texto). Son guardas, sin medir. **TODO:** perfiles `whatsapp` y `whatsapp-audio` del test de capacidad
(`scripts/capacity/perfiles/`) que peguen al webhook con payloads sintéticos (texto, y audio con Graph
simulado) junto con llamadas, y midan la respuesta p95 por turno y el efecto en la espera de las
llamadas, registrados como `CAP-NNN`.

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
escalones de 2.000, 10.000 y 100.000 según verificación y calidad (Meta sacó el de 1.000; el límite es
por portfolio de negocio, no por número). Recibir mensajes no tiene tope.
- **Atentina, 6-oct-2026:** Meta avisó por mail que el portfolio subió a **2.000 conversaciones iniciadas
  por el negocio cada 24 h**, más números (según calidad) y más WABAs. El número todavía muestra
  `TIER_250` por la API (calidad `GREEN`): el campo por número va atrasado o ya no manda.

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

**Lo verificado en la documentación de Meta (1-oct-2026)** está en
[3.4](#34-embedded-signup-v4-lo-confirmado-y-lo-no-confirmado).

Sin esto (fases 0 y 1) solo podemos operar números de **nuestro** portafolio: el de Anura y, para un
piloto, el de un cliente cargado en una WABA nuestra a su nombre (él recibe el código y nos lo pasa),
con el nombre visible de su negocio. Es aceptable para 1 o 2 pilotos; no para vender.

### 3.4 Embedded Signup v4: lo confirmado y lo no confirmado

Consultado en developers.facebook.com el 1-oct-2026 (fuentes en la sección 7).

**Confirmado:**
- **Versión:** "Embedded signup v2 will be deprecated on October 15, 2026. Migrate your integration to v4".
- **SDK:** `https://connect.facebook.net/<locale>/sdk.js` y `FB.init({appId, autoLogAppEvents: true,
  xfbml: true, version: 'v25.0'})`.
- **Lanzamiento:** `FB.login(cb, {config_id, response_type: 'code', override_default_response_type: true,
  extras: {setup: {}}})`. El código llega en `response.authResponse.code` y vence a los **30 s**.
- **Mensaje del popup** (`window.postMessage`): JSON con `type: 'WA_EMBEDDED_SIGNUP'` y `event`:
  - `FINISH`: `data` trae `{phone_number_id, waba_id, business_id}`;
  - `FINISH_ONLY_WABA` (sin número), `FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING` (coexistencia),
    `FINISH_OBO_MIGRATION`, `FINISH_GRANT_ONLY_API_ACCESS`;
  - `CANCEL` con `current_step`, o con `{error_message, error_code, session_id, timestamp}` si hubo error.
- **Dominios:** "Only domains that have enabled HTTPS are supported". Van en *Allowed domains* y en
  *Valid OAuth redirect URIs* de Facebook Login for Business. Desde `http://localhost` no se puede probar.
- **Intercambio:** `GET /<ver>/oauth/access_token?client_id=<APP_ID>&client_secret=<APP_SECRET>&code=<CODE>`.
- **Suscripción:** `POST /<WABA_ID>/subscribed_apps` con el business token → `{"success": true}`.
- **Registro:** `POST /<PHONE_NUMBER_ID>/register {"messaging_product": "whatsapp", "pin": "<6 dígitos>"}`.
  El PIN es el de verificación en dos pasos.
- **Medio de pago:** como Tech Provider, "onboarded business customers must add a payment method to their
  WhatsApp Business account", en `https://business.facebook.com/wa/manage/home/`. Recién ahí quedan
  "fully onboarded". La línea de crédito compartida es de Solution Partners, no nuestra.
- **Coexistencia:** `FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING` trae en `data` solo `waba_id`, **sin
  `phone_number_id`**. "skip the phone number registration step"; hay 24 h para pedir la sincronización
  ("otherwise they must be offboarded"): `POST /<PHONE_NUMBER_ID>/smb_app_data {"messaging_product":
  "whatsapp", "sync_type": "smb_app_state_sync"}` (contactos) y lo mismo con `"history"`. La pantalla de
  coexistencia aparece sola cuando la app está suscrita a los campos `history`, `smb_app_state_sync` y
  `smb_message_echoes` (no por un parámetro de `FB.login`).
- **Webhooks de cuenta:**
  - `account_update` con `value.event` (`PARTNER_REMOVED`, `PARTNER_APP_UNINSTALLED`, `ACCOUNT_OFFBOARDED`,
    `ACCOUNT_DELETED`, `DISABLED_UPDATE`, `ACCOUNT_RESTRICTION`, `ACCOUNT_RECONNECTED`, ...). La tabla de
    parámetros dice que `entry[].id` es la WABA, pero en los ejemplos con `value.waba_info.waba_id`
    (`PARTNER_REMOVED`, `PARTNER_APP_UNINSTALLED`) `entry[].id` es otro ID: el código usa primero
    `waba_info.waba_id` y cae a `entry[].id` solo sin él (como en `DISABLED_UPDATE`).
  - `DISABLED_UPDATE` trae `ban_info.waba_ban_state`: `DISABLE` (WABA dada de baja), `SCHEDULE_FOR_DISABLE`
    (aviso: sigue andando) o `REINSTATE` (rehabilitada). En el ejemplo es un texto; se acepta también lista.
  - `phone_number_quality_update` con `{display_phone_number, event, current_limit}`, **sin `phone_number_id`**:
    se busca por WABA y dígitos del número.
  - `message_template_status_update` con `{event, message_template_id, message_template_name, reason}`.
  - Se suscriben en App Dashboard → WhatsApp → Configuración.
- **Errores:** `190` token vencido o inválido; `10` permiso no otorgado o quitado; `133005` PIN incorrecto;
  `133010` número sin registrar; `133016` límite de intentos de registro.
- **Plantillas:** `POST /{WABA_ID}/message_templates {name, category, language, components}` → `{id, status,
  category}`. Categorías MARKETING, UTILITY y AUTHENTICATION; nombre en minúsculas, números y `_`; hasta 100
  altas por hora por WABA.
- **Configuración de Facebook Login for Business:** *Create from template* con la plantilla "WhatsApp
  Embedded Signup Configuration With 60 Expiration Token", o *Create configuration* con la variante
  "WhatsApp Embedded Signup". En *Client OAuth settings* van activados "Client OAuth login", "Web OAuth
  login", "Enforce HTTPS", "Embedded Browser OAuth Login", "use Strict Mode for redirect URIs" y "Login
  with the JavaScript SDK".

**No confirmado:**
- La forma de la respuesta de `oauth/access_token` (se espera `{access_token, token_type}`).
- **Si el business token vence.** La doc no lo dice, y la plantilla se llama "With 60 Expiration Token":
  puede ser un token de 60 días. Si vence, Meta da 190, la cuenta queda `disconnected` y el cliente la
  reconecta con el mismo botón. Confirmarlo en el primer alta (`GET /debug_token`, campo `expires_at`).
- El status HTTP del 190 (la app desconecta por `code == 190` o por 401).
- Si v4 usa `extras.featureType` o `sessionInfoVersion`: el ejemplo vigente solo trae `setup: {}`.
- Si el intercambio necesita `redirect_uri`: el ejemplo no lo usa.
- El formato de `example` del cuerpo de una plantilla: usamos el posicional `{"body_text": [[...]]}`.
- Si Meta mira el Referer (la app manda `strict-origin-when-cross-origin`).
- Si cloudflared llega a `app` desde `172.24.0.1` (ver el access log al publicar).
- Qué es `entry[].id` en `account_update` cuando falta `waba_info` (la tabla y los ejemplos no coinciden).
- Si `smb_app_data` se puede repetir (el reintento de una cuenta de coexistencia lo vuelve a pedir).

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
Cumplido desde el 6-oct-2026 (mail de Meta, 3.2).

## 5. Fases

| Fase | Qué queda | Entregable medible | Esfuerzo |
|---|---|---|---|
| **0. Cuenta y número** | Meta Business + verificación del negocio (empieza acá, tarda), app con WhatsApp, medio de pago, webhook por el túnel (`wa.atentina.com.ar`), webhook GET/POST con firma, número de Anura registrado por voz (3.1, prueba de humo), primer "hola" enviado y recibido | Un mensaje ida y vuelta con el número de Anura; resultado de la llamada de Meta anotado en `TELEFONIA_ANURA.md` | 1 semana de trabajo; la verificación de Meta corre en paralelo |
| **1. El motor por WhatsApp** | `app/whatsapp/` (2), tablas, reglas por canal (sin variante `_wa` del agente, ver 5.1), dashboard con origen WhatsApp, saliente por plantilla, tests con payloads grabados, modo verificación (3.1, etapa 2), `make wa-send` para probar | El agente de demo conversa por WhatsApp de punta a punta; eval de calidad corrido con `channel: whatsapp` (`make eval-llm`) y comparado con voz | 2 semanas |
| **2. Clientes con su número** | Tech Provider, App Review, Embedded Signup v4, `wa_accounts` multi-cliente con tokens cifrados, coexistencia, alta desde el dashboard | Un cliente conecta su número sin tocar Meta a mano; un piloto con número del cliente | 2 semanas de trabajo + tiempos de Meta (semanas) |
| **3. Operación** | Notas de voz por STT y respuesta en audio (hechas, 5.2), derivación a humano con aviso, plantillas gestionadas desde la app, `wa_messages` con costo por cliente en el dashboard, perfil `whatsapp` del test de capacidad y `CAP-NNN`, webhook de resultado para el software del cliente | Reporte por campaña con costo de Meta por gestión; capacidad medida | 2 semanas |
| **4. Campañas** | Carga por CSV o API, ventana horaria, reintentos, opt-out ("no me escriban más" → no volver a mandar plantillas), lo mismo que pide la sección 4 del plan de mercado para voz | Campaña de cobranza por WhatsApp con un piloto | Se comparte con la campaña de voz |
| **5. Calling API** | Llamadas de WhatsApp por SIP (Meta ofrece SIP con TLS además de WebRTC) → Asterisk → LiveKit: el mismo agente de voz, sin telefonía. Requiere el límite de 2.000 destinatarios por día | Una llamada entrante de WhatsApp atendida por el agente de voz | 1–2 semanas, después de tener el límite |

Orden: 0 y 1 dan valor con el número propio; 2 destraba la venta; 3 y 4 son lo que pide el piloto de
cobranzas; 5 cuando la cuenta lo permita.

### 5.1 Fase 1: lo implementado

Estado al 1-oct-2026: en vivo con el número de prueba. Tests en `tests/test_whatsapp_*.py`, con
FakeLLM y payloads con la forma de Meta en `tests/fixtures/wa/`.

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
- **No texto** (imagen, video, documento...): `WA_UNSUPPORTED_REPLY`, una vez por ventana, sin LLM. Los
  audios se transcriben desde 5.2.
- **Fin:** `completed` del motor marca la conversación y calcula el resultado, pero un mensaje dentro de
  `WA_SESSION_HOURS` (24) la retoma con el historial (2-oct-2026: un "sí" después del cierre abría otra y
  el agente saludaba de cero). Después de 24 h sin actividad, o con el tope de turnos, abre otra con el
  mismo agente. La vencida queda como estaba: `completed`, o `active` ("Incompleto") si no terminó.
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
   (cliente `atentina` por defecto), o desde la página WhatsApp.
4. Escribirle al número de prueba y ver la conversación en el dashboard.

**Queda de la fila de la fase 1:** saliente por plantilla desde la app (fase 3), modo verificación
(3.1, etapa 2) y el eval con canal `whatsapp` comparado con voz.

### 5.2 Fase 3 parcial: audios

Estado al 1-oct-2026: código y tests listos (`tests/test_whatsapp_audio.py` y los de service y graph,
con Graph, STT y TTS simulados). **No está desplegado.** Sin migración: `wa_messages.type` ya admite
`audio` y `conversations.messages` es JSON.

- **Entrada** (`service._on_audio`, `audio.transcribe`): `GET /{media_id}` sin `phone_number_id` (Meta
  lo compara con el número que *subió* el media; url que vence a los 5 min, `file_size`) → si pasa
  `WA_AUDIO_MAX_BYTES` (4 MB), respuesta de audio largo sin bajarlo → descarga con el mismo Bearer,
  solo por https a un dominio de Meta (`graph.MEDIA_HOSTS`; si no, error y se loguea el host), cortada
  en el tope → PyAV a WAV mono de 16 kHz (si la cabecera dice más de
  `WA_AUDIO_MAX_SECONDS`, 120, se corta antes de decodificar) → `POST {VLLM_STT_BASE_URL}/audio/transcriptions`.
  El texto entra al debounce como un mensaje más, marcado `voice_note`; el turno no sale mientras haya
  un audio transcribiéndose, así un texto que llega junto con un audio va en el mismo turno. En un turno
  mezclado, solo las líneas transcriptas llevan `[nota de voz transcripta]` y el mensaje no se marca
  `voice_note`: lo escrito no se trata como error de reconocimiento.
- **Respuestas fijas, sin LLM:** audio largo (`WA_AUDIO_TOO_LONG_REPLY`), transcripción vacía
  (`WA_AUDIO_EMPTY_REPLY`) y STT o descarga caídos (`WA_AUDIO_ERROR_REPLY`, con warning en el log).
  Una por texto y ventana de debounce: varias fotos dan una respuesta, pero una foto no tapa el aviso
  de un audio.
- **Salida:** `WA_AUDIO_REPLY` = `mirror` (default: nota de voz si el turno tuvo algún audio),
  `always` o `never`. Voz: `agent.voice` si está en el catálogo, si no `VLLM_TTS_VOICE`; nunca vacía ni
  `default` (mata `vllm-tts`). TTS → WAV → OGG/Opus mono 32 kbps (PyAV) → `POST /{pnid}/media` →
  mensaje `audio` con `"voice": true` (`WA_AUDIO_VOICE_FLAG`). Respuestas de más de
  `WA_AUDIO_MAX_REPLY_CHARS` (600) salen en texto.
- **Fallback:** si falla el TTS, la conversión, la subida o el envío, la misma respuesta va en texto.
  Un rechazo de Meta queda en `wa_messages` como `audio` `failed`.
- **Prompt:** con el canal `whatsapp`, el sistema trae siempre el bloque `NOTA DE VOZ` (estático, por
  el prefix caching). El turno marca el mensaje transcripto (`[nota de voz transcripta]` en classic,
  `NEW USER MESSAGE (nota de voz transcripta)` en structured) y, si la respuesta sale en audio, pide
  formato para escuchar (números en palabras, sin emojis ni asteriscos, frases cortas). La voz
  telefónica no cambia: verificado byte a byte.
- **Registro:** `Message.voice_note` en `conversations.messages`, para el mensaje transcripto y para
  la respuesta enviada como nota de voz; el detalle de la UI lo muestra con un rótulo. `wa_messages`
  guarda el tipo `audio`, sin el audio ni el texto. Logs con `stt_ms`, `tts_ms`, bytes y segundos, sin
  texto ni teléfonos.

**Para desplegar:**
1. Recrear `app` con la imagen nueva: trae `av` (PyAV) y la UI con el rótulo. Verificar en el build que
   el `av` de la imagen tenga `libopus` (`python -c "import av; av.codec.Codec('libopus','w')"`).
2. Si el `.env` tiene `WA_UNSUPPORTED_REPLY` con el texto viejo ("solo puedo leer mensajes de texto"),
   cambiarlo (diff enmascarado antes de reiniciar): ahora los audios se escuchan.
3. Mandar una nota de voz al número de prueba y verificar:
   - si Meta acepta la subida con `audio/ogg` o hace falta `audio/ogg; codecs=opus` (anotarlo acá);
   - el tamaño del OGG con voz del TTS: una respuesta de 600 caracteres tiene que quedar bajo 512 KB
     (con más, WhatsApp la muestra para descargar en lugar de con play);
   - que llegue como nota de voz (con `"voice": true`);
   - el host de la url de `GET /{media_id}` (se espera `lookaside.fbsbx.com`): si es otro, el log dice
     "url de media fuera de Meta" y hay que sumarlo a `graph.MEDIA_HOSTS`.

**Probado en vivo (1-oct-2026), número de prueba con `landing/turnos` y voz `sofia`:** Meta aceptó la
subida con `audio/ogg`, la respuesta llegó como nota de voz y el host del media pasó el filtro. Dos turnos:

| Nota entrante | STT | Respuesta | TTS | OGG | Total del turno |
|---|---|---|---|---|---|
| 3,8 s (8,6 KB) | 417 ms (primera, en frío) | 107 car. | 1132 ms | 24 KB | 2,9 s |
| 2,8 s (5,1 KB) | 80 ms | 198 car. | 2119 ms | 47 KB | 4,2 s |

Conversión WAV → OGG/Opus: 58–105 ms. ~240 bytes de OGG por carácter: 600 caracteres ≈ 140 KB, bajo
los 512 KB. El TTS domina el turno; la capacidad con carga sigue sin medir.

### 5.3 Fase 2 implementada

Estado al 1-oct-2026: código y tests listos, **sin desplegar**. Falta la aprobación de acceso de Meta
(Tech Provider) y el App Review de `whatsapp_business_management` y `whatsapp_business_messaging`.

- **Alta por el cliente** (`POST /api/v1/whatsapp/signup`, `app/whatsapp/signup.py`): cualquier usuario
  con sesión (no API keys), límite `WA_SIGNUP_PER_HOUR` por cliente. Pasos: código → business token,
  el número tiene que ser de esa WABA, `subscribed_apps`, `register` con el PIN pedido o uno nuevo (no en
  coexistencia), y alta o actualización de `wa_accounts` con token y PIN cifrados. Si falla la suscripción
  o el registro, la cuenta queda `pending` con el motivo y se reintenta con
  `POST /accounts/{id}/register` sin repetir el popup.
- **Errores:** número de otro cliente 409; `FINISH_ONLY_WABA` 400 `signup_no_phone`; número de otra WABA
  400 `signup_mismatch`; código vencido 400 `signup_code_expired`; rechazo de Meta 502 `meta_error` con
  `meta_code`; sin `WA_APP_ID`, `WA_APP_SECRET` o `WA_CONFIG_ID` 503 `wa_signup_disabled`; sin
  `WA_TOKEN_KEY` 503 `wa_token_key_missing`.
- **Estados** (`wa_accounts.status`): `connected`, `pending` y `disconnected`. Un 190 o 401 con el token del
  cliente la desconecta y deja de responder; `account_update` con `PARTNER_REMOVED`,
  `PARTNER_APP_UNINSTALLED`, `ACCOUNT_OFFBOARDED`, `ACCOUNT_DELETED` o `DISABLED_UPDATE` con `DISABLE`
  también; `DISABLED_UPDATE` con `REINSTATE` reconecta lo que desconectó un `DISABLE`, y con
  `SCHEDULE_FOR_DISABLE` solo se loguea.
- **PIN:** al reconectar un número se registra con el PIN guardado (ya tiene la verificación en dos pasos
  con ese); un PIN que falla no pisa el guardado. En cuentas de alta manual (sin token propio, número de
  nuestro portafolio) el reintento usa el PIN pedido o `WA_REGISTRATION_PIN`, nunca uno al azar.
- **Cuentas de alta manual:** usan `WA_ACCESS_TOKEN` contra nuestra WABA, compartida entre pilotos.
  Registro, `/refresh` y plantillas en esas cuentas son solo de admin (403 al cliente; la UI no los
  ofrece). El reintento de registro tiene tope de `WA_SIGNUP_PER_HOUR` por cliente.
  `phone_number_quality_update` guarda `messaging_limit`; `quality_rating` se relee con `/refresh`.
- **Cifrado:** `WA_TOKEN_KEY` (Fernet, varias separadas por coma para rotar). Los tokens viejos en claro
  se siguen leyendo. Cuentas sin token propio siguen con `WA_ACCESS_TOKEN`.
- **Plantillas:** se listan y crean en vivo contra Meta (no hay tabla), límite `WA_TEMPLATES_PER_HOUR` por
  cliente. Texto con variables `{{1}}`… y un ejemplo por variable; encabezado y pie sin variables. La UI
  ofrece Utilidad y Marketing: Autenticación tiene texto fijo de Meta (código y botón) y no entra en el
  formulario. `message_template_status_update` solo se loguea: la lista se lee en vivo.
- **UI** (`web/src/features/whatsapp/`): página WhatsApp para admin y cliente. "Conectar WhatsApp" carga el
  SDK a demanda con `app_id` y `config_id` de `GET /whatsapp/config` (deshabilitado con el motivo si falta
  algo), junta el código de `FB.login` y el `FINISH` (hasta 10 s entre uno y otro) y llama a `/signup`
  enseguida. El origen del mensaje se compara exacto (`facebook.com` o `*.facebook.com`, por https), no con
  el `endsWith` del ejemplo de Meta. Tabla con estado, calidad y límite, agente editable, reintentar
  registro (PIN opcional), releer de Meta y desactivar; sección de plantillas. El admin además ve el
  cliente, el token y el alta manual. Después del alta, aviso para cargar el medio de pago.
- **Decisiones pendientes:**
  - **Tope del tier:** no se aplica. `max_phone_numbers` cuenta DID de Anura, que nos cuestan; los números
    de WhatsApp del cliente no. Hoy rige el límite de Meta (2 por WABA sin verificar).
  - **Coexistencia:** el número sale de `GET /{waba_id}/phone_numbers` (el único de la WABA; con varios,
    400 `signup_no_phone`) y el alta pide las dos sincronizaciones (si fallan, queda `pending`). No está
    implementado leer `history`, `smb_app_state_sync` ni `smb_message_echoes`: mientras no se suscriban
    esos campos, Meta no ofrece la pantalla de coexistencia.

**Hecho el 2-oct-2026:** migración 0005, `app` recreada, `WA_TOKEN_KEY` y `CSP_REPORT_ONLY=true` en `.env`.
En Meta: Facebook Login for Business con OAuth de navegador integrado y SDK de JS, `https://app.atentina.com.ar/`
en URIs de redirección y dominios del SDK, `atentina.com.ar` en dominios de la app, webhooks `account_update`,
`phone_number_quality_update` y `message_template_status_update` suscriptos, y configuración de Embedded Signup
`WA_CONFIG_ID=2936386673383943`. **La única forma de crearla fue la plantilla "con un token que caduca en 60
días"**: la creación manual solo ofrece la variante General, sin "Registro insertado de WhatsApp" (probablemente
hasta que aprueben la verificación de acceso). Con ese token, cada cliente queda desconectado a los 60 días
(190 → "Desconectado", se reconecta con el botón). Pendiente: recrear la configuración sin vencimiento cuando
aparezca la variante, o renovar el token. Sin App Review, solo personas con rol en la app pueden completar el alta.

**Prueba del 2-oct-2026 por `https://app.atentina.com.ar`:** el popup de Meta abre (SDK, `config_id`, dominio y
CSP bien) y responde "Atentina no puede registrar clientes en este momento": sin la verificación de acceso
(Tech Provider) aprobada, Embedded Signup no deja completar el alta, ni a personas con rol en la app. Se
retoma cuando Meta la apruebe.

**Número propio de Atentina (2-oct-2026):** el DID de Anura +54 351 700-2592 quedó en WhatsApp como
"Atentina" (`phone_number_id` 1320624701139500, WABA 1106296902266123, sin revisión de nombre, TIER_250).
- Agregarlo por API a la WABA de prueba dio `2388386 Phone Numbers Count Exceeded Limit Per Business`; el
  asistente "Agregar número de teléfono" de developers.facebook.com lo creó en una WABA nueva.
- **Verificación por llamada de voz probada (3.1):** la llamada de Meta entró por Anura → Asterisk → LiveKit y
  la atendió el agente; el STT transcribió "uno, dos, uno … dos, ocho, nueve" en dos fragmentos (con un "tres"
  espurio) y el código 121289 fue correcto. Meta lo muestra como +54 **9** 351…, aunque es un fijo.
- Después: asignar la WABA nueva al system user (lo hace el usuario: dar permisos está bloqueado para el
  agente), `subscribed_apps`, `register` con `WA_REGISTRATION_PIN` y `make wa-account` → `interno/atentina_comercial` (desde el 2-oct-2026, cliente `atentina`).
- Lo atiende el agente `atentina_comercial` (plantilla en `app/agents/templates/`), por WhatsApp y por llamada.
- Medio de pago: Visa en la cuenta de pago "Atentina" (ARS), sin aviso de "Payment method missing" (visto el 6-oct-2026).

**Para desplegar (todo pendiente):**

1. **Meta, configuración de Embedded Signup** (developers.facebook.com → app `Atentina`):
   1. *Facebook Login for Business* → *Settings* → *Client OAuth settings*: activar "Client OAuth login",
      "Web OAuth login", "Enforce HTTPS", "Embedded Browser OAuth Login", "use Strict Mode for redirect
      URIs" y "Login with the JavaScript SDK".
   2. En la misma pantalla, `app.atentina.com.ar` en *Allowed domains* y
      `https://app.atentina.com.ar/` en *Valid OAuth redirect URIs*.
   3. *Facebook Login for Business* → *Configurations* → *Create from template* → "WhatsApp Embedded Signup
      Configuration With 60 Expiration Token" (o *Create configuration* con la variante "WhatsApp Embedded
      Signup", pidiendo solo `whatsapp_business_management` y `whatsapp_business_messaging`). Copiar el
      **configuration ID**: es `WA_CONFIG_ID`.
   4. *Settings* → *Basic*: `atentina.com.ar` en *App domains* si no está.
   5. *WhatsApp* → *Configuration* → Webhook fields: suscribir `account_update`,
      `phone_number_quality_update` y `message_template_status_update` (además de `messages`).
2. **`.env`:** `WA_CONFIG_ID` y `WA_TOKEN_KEY` (generarla con
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`), con diff
   enmascarado contra el backup antes de reiniciar. Guardar la clave aparte: sin ella los tokens de los
   clientes no se pueden leer. Para el primer despliegue, `CSP_REPORT_ONLY=true` y revisar la consola en el
   alta real; después volver a `false`.
3. **Migración 0005** y recrear `app`: el servicio `migrate` la corre solo (`make up-agent`). Las sesiones
   viejas siguen valiendo hasta que vencen.
4. **Cloudflare:** crear el hostname `app.atentina.com.ar` → `http://localhost:8011` (sin path) en el túnel,
   ver [`LANDING.md`](LANDING.md), paso 5. Sin Cloudflare Access: la app se defiende sola.
5. **Prueba:** entrar a `https://app.atentina.com.ar` con un usuario de cliente, "Conectar WhatsApp" con
   un número de prueba, y anotar acá lo no confirmado de 3.4 (forma del token, vencimiento, IP de
   cloudflared en el access log).

## 6. Riesgos y trampas

- **Meta manda los tiempos:** verificación del negocio y App Review no tienen plazo garantizado.
  Empezar la fase 0 antes que cualquier código.
- **El 1-oct-2026 cambia el costo:** los mensajes de servicio pasan a cobrarse. Toda estimación de
  precio al cliente tiene que ser con el costo nuevo, no con el gratis de hoy.
- **Calidad del número:** Meta baja el límite de envío si los usuarios bloquean o reportan. Plantillas
  sobrias, opt-out respetado y no mandar marketing desde el número de cobranzas.
- **Un número, un negocio:** el nombre visible de la WABA tiene que ser el del negocio que escribe.
  Números de clientes dentro de nuestro portafolio solo para pilotos.
- **Tokens de clientes** en la base: cifrados, nunca en logs. No está confirmado que el business
  token no venza (la plantilla de configuración dice "60 Expiration Token", ver 3.4); el cliente además
  puede revocarlo. Un 190 o 401 deja la cuenta "Desconectado" en el dashboard y se reconecta con el
  mismo botón.
- **El ejemplo de Meta valida el origen con `endsWith('facebook.com')`:** acepta `evilfacebook.com`, que
  podría inyectar un `waba_id` y `phone_number_id` falsos. La UI compara el hostname exacto. El backend
  igual comprueba que el número sea de esa WABA con el token del cliente.
- **Embedded Signup solo anda por HTTPS** desde un dominio declarado en la app de Meta: en
  `http://localhost:8011` el popup falla (la UI lo avisa).
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
- **Notas de voz de Meta:** para que se vea como nota de voz, OGG con Opus y mono, y `"voice": true` en
  el mensaje; hasta 16 MB, sin duración máxima documentada. Hasta 512 KB se muestra con play; con más,
  para descargar. El webhook trae `audio.voice` (nota grabada en WhatsApp) y, desde nov-2025 y no en
  todas las cuentas, `audio.url`: no se usa, `GET /{media_id}` da `file_size` para rechazar antes de bajar.
- **Fallback a texto duplicado:** si el envío del audio llega a Meta pero la respuesta se corta, el
  texto de respaldo sale igual y el cliente recibe las dos. Fuera de la ventana de 24 h (131047)
  fallan los dos y quedan dos filas `failed`.
- **La respuesta en audio puede salir en texto con números en palabras:** si el prompt pidió formato
  para escuchar y después el TTS falla, el fallback manda ese mismo texto. Es aceptable.
- **Titular persona física (monotributo), no sociedad:** en la fase 2 puede chocar el nombre legal
  (la persona) con el nombre visible "Atentina" en la verificación y en el perfil del número.

## 7. Fuentes (consultadas el 28-sep-2026)

Fase 2, consultadas el 1-oct-2026: [implementación de Embedded Signup](https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/implementation),
[onboarding como Tech Provider](https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-customers-as-a-tech-provider),
[resumen de Embedded Signup](https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/overview/),
[webhooks](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview/)
([account_update](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/reference/account_update),
[phone_number_quality_update](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/reference/phone_number_quality_update),
[message_template_status_update](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/reference/message_template_status_update)),
[plantillas](https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/overview),
[códigos de error](https://developers.facebook.com/documentation/business-messaging/whatsapp/support/error-codes) y
[changelog](https://developers.facebook.com/documentation/business-messaging/whatsapp/changelog).


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
- Meta, mensajes de audio (`voice: true`, OGG/Opus mono, 16 MB, play hasta 512 KB) y API de media
  (`GET /{media_id}`, url de 5 min, subida multipart): referencia de la Cloud API, consultada el 1-oct-2026.
