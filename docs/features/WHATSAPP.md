# WhatsApp

El mismo agente (misma definición, mismo motor) atiende por WhatsApp: mensajes de texto, notas de voz y
llamadas. Cloud API de Meta directa, sin intermediario, con la app `Atentina` de Meta o con la app propia del
cliente. Estado: en producción desde el 1-oct-2026 (llamadas por SIP con el número de Atentina). Plan:
`tiers.whatsapp` (`TIER_HAS["whatsapp"]`); las campañas, `campaign_channels` (ver [CAMPANAS.md](CAMPANAS.md)).

| Parte | Estado |
|---|---|
| Texto y notas de voz | En producción con el número de Atentina (+54 9 351 700-2592, agente `atentina_comercial`) |
| Número con la app de Meta propia del cliente (`own_app`) | Desplegado; falta probar con un número real |
| Embedded Signup (alta con la app de Atentina) | Código desplegado, apagado con `WA_EMBEDDED_SIGNUP=false` hasta que Meta apruebe el Tech Provider |
| Llamadas de WhatsApp por SIP | En producción, solo con el número de Atentina |
| Ruteo por contacto (`wa_routes`) | En producción |

Revisión de Meta (Tech Provider y App Review): [META_APP_REVIEW.md](META_APP_REVIEW.md).

## Modelo de datos

Modelos en `app/models/whatsapp.py`. El texto de los mensajes no está acá: va en `conversations.messages`, con
`conversations.channel = 'whatsapp'`.

| Tabla | Qué guarda | Migración |
|---|---|---|
| `wa_accounts` | Un número conectado: `client_id`, `agent_id` (agente por defecto), `phone_number_id` (único), `waba_id`, `display_phone_number`, `access_token` (cifrado; NULL = `WA_ACCESS_TOKEN`), `status` (`connected`, `pending`, `disconnected`) y `status_reason`, `quality_rating`, `messaging_limit`, `source` (`manual`, `embedded_signup`, `coexistence`, `own_app`), `pin_enc`; en `own_app`, `app_secret` y `verify_token` cifrados y `webhook_key` única | 0004, 0005, 0038 |
| `wa_threads` | Una fila por conversación de WhatsApp: `account_id`, `wa_id` (como lo manda Meta, `549…`), `contact_name`, `last_user_at`, `closed_at` (cerrada: el próximo mensaje abre otra). `paused` existe y nada lo pone en true | 0004, 0007 |
| `wa_messages` | Por `wamid` (único): dedupe y estados. `direction` (`in`/`out`), `type` (`text`, `audio`, `template`…), `status` (entrante: `received`, `answered`, `ignored`, `error`; saliente: `sent`, `delivered`, `read`, `failed`), `error` de Meta | 0004 |
| `wa_routes` | Ruteo por contacto: `account_id`, `agent_id` y `contacts` (lista de `wa_id`) | 0015 |
| `wa_account_status_log` | Historial de estado, calidad y límite de cada cuenta (para Reportes) | 0036 |
| `tiers.whatsapp` | Si el plan incluye WhatsApp (cuentas, mensajes y llamadas) | 0025 |
| `Workflow.wa_session_minutes` | Ventana de contexto por agente (en la definición, no es columna) | — |

## API

Bajo `/api/v1/whatsapp` (`app/api/routers/whatsapp.py`). El cliente ve lo suyo; registro, `/refresh` y plantillas
de una cuenta sin token propio (alta manual, WABA de Atentina) son solo de admin.

| Ruta | Qué hace |
|---|---|
| `GET /config` | Si Embedded Signup está disponible y por qué no (`enabled`, `reason`), `app_id`, `config_id` |
| `GET/POST /accounts`, `PATCH /accounts/{id}` | Lista; alta manual (admin); cambiar agente o nombre |
| `POST /accounts/{id}/deactivate` | Desactiva el número (deja de atender) |
| `POST /accounts/own-app` | Alta con la app de Meta del cliente: devuelve URL de webhook y verify token |
| `POST /signup` | Alta por Embedded Signup (solo sesión de usuario, tope `WA_SIGNUP_PER_HOUR` por cliente) |
| `POST /accounts/{id}/register` | Reintenta suscripción y registro (PIN opcional) sin repetir el popup |
| `POST /accounts/{id}/refresh` | Relee de Meta nombre, calidad y límite |
| `GET/POST /accounts/{id}/templates` | Plantillas en vivo contra Meta (sin tabla); alta con tope `WA_TEMPLATES_PER_HOUR` |
| `PUT /accounts/{id}/routes` | Reemplaza la lista completa de reglas de ruteo |
| `POST /threads/{conversation_id}/close` | Cierra la conversación: el próximo mensaje abre otra con la versión vigente del agente |

Webhook (`app/whatsapp/webhook.py`, fuera de `/api/v1`):

| Ruta | Para qué |
|---|---|
| `GET/POST /wa/webhook` | WABA de Atentina y cuentas de Embedded Signup: challenge con `WA_VERIFY_TOKEN`, firma `X-Hub-Signature-256` con `WA_APP_SECRET` |
| `GET/POST /wa/webhook/{key}` | Una cuenta `own_app`: challenge y firma con el verify token y el app secret de esa cuenta; solo pasa lo de su WABA y su número (`own_app.scoped_payload`) |

MCP: `list_whatsapp_accounts`, `update_whatsapp_account`, `set_whatsapp_routes`, `list_whatsapp_templates`,
`create_whatsapp_template`, `close_whatsapp_thread` ([MCP_HERRAMIENTAS.md](../MCP_HERRAMIENTAS.md)).

## Flujo

```text
cliente final (WhatsApp) <-> Meta Cloud API <-> Cloudflare Tunnel (wa.atentina.com.ar) <-> app: /wa/webhook[/{key}]
                                     app/whatsapp/service.py -> ConversationEngine -> app/whatsapp/graph.py
```

Todo corre en `app` (no en `agent`): el webhook es HTTP y no hay room.

| Archivo | Qué hace |
|---|---|
| `app/whatsapp/webhook.py` | Challenge y firma; responde 200 enseguida y procesa en segundo plano |
| `app/whatsapp/service.py` | Del webhook al motor y de vuelta: dedupe, lock por contacto, debounce, ventana, audios, eventos de cuenta, barrido |
| `app/whatsapp/graph.py` | Cliente de la Graph API (`WA_GRAPH_VERSION`, v25.0): texto, audio, plantillas, media, registro |
| `app/whatsapp/audio.py` | OGG/Opus → WAV 16 kHz → STT; TTS → WAV → OGG/Opus (PyAV, sin ffmpeg) |
| `app/whatsapp/store.py` | Acceso a `wa_accounts`, `wa_threads`, `wa_messages` |
| `app/whatsapp/signup.py` | Embedded Signup: código → token, suscripción, registro, plantillas |
| `app/whatsapp/own_app.py` | Cuentas con la app de Meta del cliente |
| `app/whatsapp/crypto.py` | Tokens, PIN y secretos cifrados con `WA_TOKEN_KEY` (Fernet) |
| `app/services/wa_routing.py` | Ruteo por contacto |
| `web/src/features/whatsapp/` | Página WhatsApp: cuentas, plantillas, ruteo, alta con app propia (`OwnAppModal.tsx`) |

### Mensaje entrante

1. Dedupe por `wamid`; cuenta por `phone_number_id`. Se ignora (queda `ignored`) si la cuenta no existe, está
   inactiva o desconectada, el cliente está inactivo o su plan no incluye WhatsApp.
2. Junta lo que llega en `WA_DEBOUNCE_SECONDS` (2 s) en un turno, ordenado por el timestamp de Meta; un turno a la
   vez por contacto. Si llega texto mientras responde el LLM, deshace el turno y responde todo junto.
3. Conversación activa del contacto, o una nueva **sin apertura** (el primer mensaje del cliente es el turno 1). Si
   el contacto responde a una campaña, la apertura es el cuerpo de la plantilla y atiende el agente de la campaña.
4. `process_turn` con el bloque de canal de `app/llm/prompt.py` (`CHANNEL["whatsapp"]`: texto, solo `*negrita*`,
   audios transcriptos marcados). El mismo agente sirve voz y WhatsApp.
5. Envío (`send_text`, recortado a `WA_MAX_REPLY_CHARS`, 4096) y `mark_read`. Los `statuses` no retroceden
   (`sent < delivered < read`); `failed` gana y guarda el error de Meta. Un envío fallido no se reintenta.

**Topes:** `WA_MAX_TURN_CHARS` (2000) por turno, lo que pase se descarta; `WA_MAX_TURNS` (40) por conversación,
después sigue en otra. Los turnos por `/conversations/{id}/turns` a una conversación de WhatsApp dan 409.

**No texto** (imagen, video, documento): `WA_UNSUPPORTED_REPLY`, una vez por ventana de debounce, sin LLM.

### Notas de voz

- **Entrada:** `GET /{media_id}` (url que vence en 5 min, con `file_size`). Más de `WA_AUDIO_MAX_BYTES` (4 MB) o
  `WA_AUDIO_MAX_SECONDS` (120 s): `WA_AUDIO_TOO_LONG_REPLY` sin bajarlo. Descarga solo por https a un host de Meta
  (`graph.MEDIA_HOSTS`), PyAV a WAV mono 16 kHz, `stt-parakeet`. El texto entra al debounce marcado como nota de
  voz; el turno espera a que terminen las transcripciones en curso.
- **Respuestas fijas sin LLM:** transcripción vacía (`WA_AUDIO_EMPTY_REPLY`), STT o descarga caídos
  (`WA_AUDIO_ERROR_REPLY`).
- **Salida:** `WA_AUDIO_REPLY` = `mirror` (default: nota de voz si el turno tuvo audio), `always` o `never`. Voz:
  `agent.voice` si está en el catálogo, si no `VLLM_TTS_VOICE`. El texto pasa por `app/voice/speech_text.py`,
  TTS → OGG/Opus mono 32 kbps → `POST /{pnid}/media` → mensaje `audio` con `"voice": true`
  (`WA_AUDIO_VOICE_FLAG`). Respuestas de más de `WA_AUDIO_MAX_REPLY_CHARS` (600) salen en texto.
- **Fallback:** si falla TTS, conversión, subida o envío, la misma respuesta va en texto.
- **Grabación:** con `agent.record_audio`, el audio entrante y la nota de voz enviada quedan como WAV por mensaje
  (ver [ARQUITECTURA.md](../ARQUITECTURA.md#definición-de-un-agente)).
- `WA_AUDIO_CONCURRENCY` (4) limita los pedidos simultáneos desde WhatsApp al STT y al TTS por separado; topes
  totales con espera incluida: STT 45 s, TTS 90 s.

Medido en vivo (número de prueba, voz `sofia`): STT 80 ms (417 ms en frío), TTS 1,1–2,1 s, turno total 2,9–4,2 s;
OGG ~240 bytes por carácter (600 caracteres ≈ 140 KB, bajo los 512 KB en que WhatsApp deja de mostrar play).

### Fin de una conversación y ventana de contexto

- `end_call` del agente marca la conversación `completed`, pero un mensaje dentro de la ventana de contexto la
  retoma con el historial (un "sí" después del cierre no abre otra).
- **Ventana de contexto por agente:** `Workflow.wa_session_minutes` (minutos sin mensajes del contacto para dar
  la conversación por terminada); `None` usa `WA_SESSION_HOURS` (24 h). Se edita en la sección Voz del editor del
  agente. `WhatsAppService._session_minutes` la resuelve por el agente que abrió el hilo, al atender un mensaje y en
  el barrido (`sweep`, cada 300 s), que cierra los hilos vencidos y llama a `engine.finish` (extracción final).
- No confundir con la ventana de 24 h de Meta (texto libre vs. plantillas), que aplica Meta.
- La conversación corre con la versión del agente con que empezó: **Cerrar conversación** fuerza la vigente.

### Ruteo por contacto (`wa_routes`)

Cada cuenta tiene su agente por defecto y reglas (un agente + lista de contactos). Aplica a mensajes y llamadas de
WhatsApp; la voz de Anura sigue con el agente del número.

- **Prioridad:** respuesta a campaña > regla > agente por defecto. Un contacto de una regla con un hilo abierto con
  otro agente pasa a una conversación nueva; una conversación abierta por una campaña no se pisa. Un agente de regla
  archivado se saltea.
- **Contactos:** se cargan como `wa_id` (se aceptan `+`, espacios, guiones). Se comparan canonizados: solo dígitos
  y, en Argentina, sin el 9 (Meta manda `549…`, Anura `54…`). Un contacto está en una sola regla de la cuenta; el
  agente tiene que ser del cliente y no estar archivado.
- **Llamadas:** Asterisk pasa `X-WA-Meta-Wacid` en el INVITE (`whatsapp-predial`), el inbound trunk lo mapea al
  atributo `wa.wacid` (`headers_to_attributes`, `scripts/livekit_sip_setup.py`) y el worker lo pasa a
  `calls.start_inbound`.
- UI: WhatsApp → menú de la fila → **Ruteo por contacto** (`RoutesModal.tsx`).

### Alta de un número

| Vía | Quién | Cómo |
|---|---|---|
| Manual | Admin | Número de la WABA de Atentina, token `WA_ACCESS_TOKEN`. `make wa-account PNID=… WABA=… NUMBER=… AGENT=<slug> [CLIENT=…]` o la UI |
| App de Meta propia (`own_app`) | Cliente | WhatsApp → "Conectar con mi app de Meta" (guía en el modal) |
| Embedded Signup | Cliente | WhatsApp → "Conectar WhatsApp"; el botón solo aparece con `GET /config` habilitado |

**App propia del cliente** (`app/whatsapp/own_app.py`): el cliente crea una app tipo Business con WhatsApp, la pasa
a Live, crea un usuario de sistema con token permanente (`whatsapp_business_messaging`,
`whatsapp_business_management`) y carga `phone_number_id`, `waba_id`, el token y el app secret. La app valida con
Graph que el número sea de esa WABA y suscribe su app (`subscribed_apps`; si falla, queda `pending`). Devuelve
`WA_PUBLIC_URL/wa/webhook/<clave>` y el verify token, que el cliente pega en su app y suscribe `messages`. Reenviar
el alta con el mismo número cambia token y secret; URL y verify token no cambian.

**Embedded Signup** (`app/whatsapp/signup.py`, v4): el popup de Meta devuelve un código (vence a los 30 s) y el
`FINISH` con `waba_id` y `phone_number_id`; la UI espera hasta 10 s entre uno y otro y llama a `/signup`. La app
cambia el código por el business token, comprueba que el número sea de esa WABA, suscribe la app, registra el
número con PIN (no en coexistencia) y guarda la cuenta. Errores: número de otro cliente 409; `signup_no_phone`,
`signup_mismatch`, `signup_code_expired` (400); `meta_error` (502, con `meta_code`); `wa_signup_disabled` y
`wa_token_key_missing` (503). En coexistencia (`FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING`) el número sale de
`GET /{waba_id}/phone_numbers` y se piden las dos sincronizaciones (`smb_app_data`) dentro de las 24 h.

**Estados de la cuenta:** un 190 o 401 con el token del cliente la pasa a `disconnected` y deja de responder;
también `account_update` con `PARTNER_REMOVED`, `PARTNER_APP_UNINSTALLED`, `ACCOUNT_OFFBOARDED`, `ACCOUNT_DELETED` o
`DISABLED_UPDATE` con `DISABLE`. `REINSTATE` reconecta lo que desconectó un `DISABLE`; `SCHEDULE_FOR_DISABLE` solo
se loguea. `phone_number_quality_update` guarda `messaging_limit`; `message_template_status_update` solo se loguea.

**Plantillas:** se listan y crean en vivo contra Meta. Variables `{{1}}`… solo en el cuerpo, con un ejemplo por
variable; encabezado y pie fijos; botón de enlace (https fijo) y respuesta rápida "No me interesa". La UI ofrece
Utilidad y Marketing (Autenticación tiene texto fijo de Meta).

### Llamadas de WhatsApp por SIP

```text
WhatsApp → Meta ──SIP/TLS :5061, SRTP (SDES), PCMA──▶ Asterisk ──SIP/UDP, RTP, PCMA──▶ LiveKit → agente
```

Meta ofrece PCMA, el mismo códec de Anura y LiveKit: Asterisk descifra y reenvía, sin transcodificar. SDES y no
DTLS porque Asterisk lo hace sin ICE. Asterisk pasa a LiveKit el DID (`+543517002592`) y atiende el agente de ese
número (o el de la regla de `wa_routes`). Requisito de Meta: límite de envío de 2.000 o más por día (cumplido).

Código: `asterisk/conf/whatsapp/pjsip_whatsapp.conf` (transporte TLS, auth, endpoint), contexto `from-whatsapp` en
`asterisk/conf/extensions.conf`, `asterisk/entrypoint.sh` (lo activa solo con `WA_SIP_PASSWORD` y el certificado;
si falta, arranca sin WhatsApp y lo dice en el log), `res_srtp`, `scripts/wa.py` (`calling-*`, `sip-password`).

**Procedimiento** (otro número u host):

1. **DNS** en Cloudflare: `A` `sip` → IP fija, **DNS only** (el proxy no pasa SIP).
   `dig +short sip.atentina.com.ar @1.1.1.1` tiene que dar la IP fija.
2. **Router:** TCP 5061 → `192.168.1.99`. El audio usa el rango RTP de Anura (UDP 10000-10199), ya reenviado.
3. **Token de Cloudflare** (plantilla *Edit zone DNS*, zona `atentina.com.ar`) en `CLOUDFLARE_DNS_API_TOKEN`.
4. **Certificado:** `make sip-cert` (certbot DNS-01, en `asterisk/letsencrypt/`, Let's Encrypt de 90 días).
5. **Meta:** `make wa-calling-enable [PNID=…]` (llamadas `ENABLED`, SIP a `WA_SIP_HOST:5061`, SDES, PCMA).
   `make wa-calling-status` muestra la config.
6. **Clave SIP:** `make wa-sip-password` la trae a `WA_SIP_PASSWORD` (entre comillas simples), con backup en
   `scratch/` y diff enmascarado. Revisar que solo cambie esa línea.
7. **Asterisk:** `make up-pbx` (**corta las llamadas en curso**). En `make logs S=asterisk`:
   `tls/5061 (WhatsApp, sip.atentina.com.ar)` y `libsrtp2 ... initialized`.
8. **Prueba:** llamar desde un WhatsApp personal; en el log, `Entrante de WhatsApp: <usuario> -> +543517002592`.

Apagar: `make wa-calling-disable` (Meta borra la config SIP y el ícono desaparece).

**Trampas:**

- El primer INVITE llega sin credenciales y Asterisk responde 401 (`No matching endpoint found`, normal); Meta
  reintenta con digest y usuario = número con el 9 y sin `+` (`5493517002592`). Si cambia el número:
  `make pbx-cli` → `pjsip set logger on`, leer el `username` y ponerlo en `WA_SIP_USER`.
- Request-URI con el 9 aunque sea un fijo (`+549…`); el dialplan lo pasa a `+543517002592`.
- **TLS:** sin `method`, pjproject servía solo TLS 1.0; `method=sslv23` da 1.2 y 1.3.
- Con SIP activo, Meta no manda el webhook `calls` ni deja usar los endpoints de llamadas de la Graph API.
- **Certificado:** cron diario 04:15 (`scripts/ops/sip-cert-renew.sh`, log `~/atentina-ops/sip-cert.log`): renueva
  a menos de 30 días del vencimiento y reinicia Asterisk solo sin llamadas en curso (espera hasta 60 min).
  `scripts/ops/healthcheck.sh` falla si el certificado servido vence en menos de 14 días o no hay TLS 1.2. En un
  host nuevo, la línea del cron está en [MIGRACION_SERVER.md](../MIGRACION_SERVER.md).
- El modo automático de Claude Code bloquea crear el registro DNS y `wa-calling-enable`: los corre el usuario.
- Bloqueo de números: `blocked_numbers` corta sin atender las llamadas de WhatsApp de ese número (por `wa.wacid`),
  no los mensajes ([CAMPANAS.md](CAMPANAS.md#bloquear-y-cortar)).

## Reglas y trampas

- **Webhook por el túnel:** `wa.atentina.com.ar`, path `^/wa/webhook` → `localhost:8011` (cubre también
  `/wa/webhook/{key}`); sin 443 en el router ni certificado propio. Si `tunnel` cae, Meta reintenta un tiempo y
  después desactiva el webhook.
- **App suscrita a la WABA:** configurar el webhook en el panel de Meta no la suscribe; sin
  `POST /{waba_id}/subscribed_apps` no llega ningún mensaje real. Alta manual: hacerlo con el token del system user.
- **App sin publicar:** Meta solo manda webhooks de prueba. La app `Atentina` está publicada.
- **Número nuevo sin registrar** (`status: PENDING`): todo envío da `133010` hasta `POST /{pnid}/register` con el PIN
  de 6 dígitos (`WA_REGISTRATION_PIN`, Meta lo pide al re-registrar). Un PIN que falla no pisa el guardado.
- **Celulares de Argentina:** Meta manda `wa_id` `549…`; `service.recipient()` responde sin el 9 (`54…`), que Meta
  entrega igual (a `549…` daba `131030` con el número de prueba).
- **Registro del número de Anura:** sin SMS; Meta verifica por llamada de voz, que entra por Anura → Asterisk →
  LiveKit y la atiende el agente: el código se lee en el transcript de la llamada (probado con el número de
  Atentina; el STT transcribió los 6 dígitos con un "tres" espurio). Ver [TELEFONIA_ANURA.md](../TELEFONIA_ANURA.md).
- **Origen del popup de Embedded Signup:** la UI compara el hostname exacto (`facebook.com` o `*.facebook.com`, por
  https), no `endsWith` como el ejemplo de Meta (aceptaría `evilfacebook.com`). El backend igual valida que el número
  sea de esa WABA con el token del cliente.
- **Embedded Signup solo por HTTPS** desde un dominio declarado en la app de Meta: anda por
  `app.atentina.com.ar`, no por `localhost`. `CSP_REPORT_ONLY=true` hasta el primer alta real.
- **Token de Embedded Signup:** la configuración (`WA_CONFIG_ID`) se creó con la plantilla "with 60 Expiration
  Token" (la única disponible sin Tech Provider): cada cuenta quedaría desconectada a los 60 días (190) y se reconecta
  con el mismo botón.
- **Tokens y secretos** cifrados con `WA_TOKEN_KEY` (varias claves separadas por coma para rotar); sin ella no se
  leen: guardarla aparte. Nunca en logs; el access log tapa `hub.verify_token`.
- **Webhooks duplicados y fuera de orden:** dedupe por `wamid`; un `status` puede llegar antes que el `sent` propio.
- **Fallback a texto duplicado:** si el envío del audio llega a Meta pero la respuesta se corta, sale también el
  texto. Fuera de la ventana de 24 h (131047) fallan los dos.
- **Costo de Meta:** lo paga la WABA del número (cada cliente carga su medio de pago). Desde el 1-oct-2026 los
  mensajes de servicio se cobran como *utility* después de 1.000 gratis por mes por número. La app no los muestra ni
  los topea, y los mensajes no consumen cuota del tier (solo se exige el plan con WhatsApp y el cliente activo).
- **Límites de Meta:** 2 números por WABA hasta verificar el negocio; el portfolio de Atentina tiene 2.000
  conversaciones iniciadas por el negocio cada 24 h (el número todavía dice `TIER_250` por la API).
- **Tope del tier:** `max_phone_numbers` no cuenta los números de WhatsApp (cuenta DID de Anura).
- **Capacidad:** un turno de texto es un pedido al LLM; uno con audio usa además STT y TTS. Una nota de 120 s llena
  sola un batch del STT y demora el STT de las llamadas en curso. Sin medir con carga.

## Variables de `.env`

| Grupo | Variables |
|---|---|
| App y webhook | `WA_APP_ID`, `WA_APP_SECRET`, `WA_VERIFY_TOKEN`, `WA_ACCESS_TOKEN` (system user de Atentina), `WA_PUBLIC_URL` (`https://wa.atentina.com.ar`), `WA_GRAPH_VERSION`, `WA_REGISTRATION_PIN`, `WA_PHONE_NUMBER_ID` (solo `scripts/wa.py`) |
| Embedded Signup y cifrado | `WA_EMBEDDED_SIGNUP` (false), `WA_CONFIG_ID`, `WA_TOKEN_KEY`, `WA_SIGNUP_PER_HOUR`, `WA_TEMPLATES_PER_HOUR`, `WA_SDK_LOCALE` |
| Conversación | `WA_SESSION_HOURS`, `WA_DEBOUNCE_SECONDS`, `WA_UNSUPPORTED_REPLY`, `WA_MAX_REPLY_CHARS`, `WA_MAX_TURN_CHARS`, `WA_MAX_TURNS` |
| Audios | `WA_AUDIO_REPLY`, `WA_AUDIO_MAX_BYTES`, `WA_AUDIO_MAX_SECONDS`, `WA_AUDIO_MAX_REPLY_CHARS`, `WA_AUDIO_CONCURRENCY`, `WA_AUDIO_VOICE_FLAG`, `WA_AUDIO_TOO_LONG_REPLY`, `WA_AUDIO_EMPTY_REPLY`, `WA_AUDIO_ERROR_REPLY` |
| Campañas | `WA_CAMPAIGN_TICK_SECONDS`, `WA_CAMPAIGN_REPLY_DAYS`, `WA_CAMPAIGN_MAX_RECIPIENTS`, `WA_OPTOUT_REPLY` ([CAMPANAS.md](CAMPANAS.md)) |
| Llamadas por SIP | `WA_SIP_HOST`, `WA_SIP_PORT`, `WA_SIP_USER`, `WA_SIP_PASSWORD`, `CLOUDFLARE_DNS_API_TOKEN` |

Al editar `.env`: diff enmascarado contra el backup antes de reiniciar.

## Desplegar y probar

- Cambios de código de WhatsApp: `make calls-active && make up-agent` (recrea `app`; la imagen compila `web/`).
  Migraciones: `make migrate-test` y `make migrate`.
- Cambios del ruteo de llamadas o de Asterisk: `make livekit-sip` y `make up-pbx` (corta las llamadas en curso).
- Tests (`make test`, Meta, STT y TTS simulados): `tests/test_whatsapp_*.py` (webhook, service, audio, signup,
  own_app, templates, prompt, graph, api) con payloads en `tests/fixtures/wa/`.
- A mano: `make wa-send TO=54351… TEXT="hola"`; escribirle al número y ver la conversación en Conversaciones
  (origen "WhatsApp").
- Embedded Signup: `WA_EMBEDDED_SIGNUP=true` con `WA_APP_ID`, `WA_APP_SECRET`, `WA_CONFIG_ID` y `WA_TOKEN_KEY`; en
  Meta, Facebook Login for Business con `app.atentina.com.ar` en dominios y URIs de redirección, y los campos
  `account_update`, `phone_number_quality_update` y `message_template_status_update` suscritos (hecho).

## Pendientes

- **Tech Provider y App Review de Meta:** sin ellos un cliente no completa Embedded Signup ni conecta un número con
  la app de Atentina ([META_APP_REVIEW.md](META_APP_REVIEW.md)). Al aprobarse: primer alta real, confirmar si el
  business token vence (`GET /debug_token`), recrear la configuración sin vencimiento si Meta la ofrece y volver
  `CSP_REPORT_ONLY` a `false`.
- **`own_app` con un número real:** que una app en Live sin App Review reciba los webhooks de sus números, y que un
  número que está en la app WhatsApp Business del celular no se pueda usar por la API sin coexistencia.
- **Coexistencia:** el alta y la sincronización están, pero la app no lee `history`, `smb_app_state_sync` ni
  `smb_message_echoes`; sin suscribir esos campos Meta no ofrece la pantalla de coexistencia.
- **Llamadas de WhatsApp en `call_logs`:** hoy quedan como una entrante de teléfono; el `wa.wacid` ya llega al
  worker, falta marcarlas como de WhatsApp. Las llamadas por SIP siguen solo con el número de Atentina.
- **Capacidad:** perfiles `whatsapp` y `whatsapp-audio` del test de capacidad (texto y audio junto con llamadas,
  p95 por turno y efecto en las llamadas), `CAP-NNN`. `WA_AUDIO_CONCURRENCY` y los topes de STT/TTS son guardas sin
  medir.
- **Consumo:** costo de Meta por cliente en el dashboard y consumo de mensajes en el tier.
- **Eval con canal `whatsapp`** (`make eval-llm`) comparado con voz.
