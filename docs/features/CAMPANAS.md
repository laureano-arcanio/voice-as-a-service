# Campañas y contactos

Agenda de contactos por cliente y campañas salientes a una lista: por **WhatsApp** (una plantilla aprobada por un
número conectado) o por **voz** (el agente llama solo, de a uno o en paralelo, con reintentos). Una sola tabla para
los dos canales, desde la UI, la API o el MCP, con polling, reporte y webhook. Estado: en producción desde el
7-oct-2026 (WhatsApp) y el 19-oct-2026 (voz). Plan: `tiers.campaign_channels` (`TIER_HAS["campaigns_voice"]`,
`["campaigns_whatsapp"]`), `max_campaigns_per_month`, `max_campaign_contacts`, `max_campaign_concurrency`,
`campaign_followup`; agenda: `max_contacts` (`TIER_HAS["contacts"]`). Hoy las de voz están en Sucursal (de a 1) e
Interno (valores en la pantalla Tiers).

## Modelo de datos

Modelos en `app/models/campaigns.py` (migración 0017; `contacts.notes` en la 0040).

| Tabla | Columnas clave |
|---|---|
| `contacts` | `client_id`, `phone` (E.164, **único por cliente**, lo único obligatorio), `name`, `email`, `notes` (nota libre), `source` (`manual`, `csv`, `api`, `campaign`, `inbound`), `archived_at` (NULL = activo; no se borran) |
| `contact_optouts` | PK `(client_id, phone, channel)`; `channel` `whatsapp`, `voice` o `all`; `source` `keyword`, `outcome`, `manual`. Aparte de `contacts`: la baja es del teléfono, sigue aunque se archive y se carga sin ficha |
| `campaigns` | Comunes: `client_id`, `agent_id` (NULL en WhatsApp = el del número), `name`, `channel`, `status` (`draft`, `scheduled`, `running`, `paused`, `done`, `cancelled`), `status_reason`, `rate_per_minute`, `window_start`/`window_end` (horas locales de `BILLING_TIMEZONE`, default 9–20), `weekdays` (0 = lunes; NULL = todos), `starts_at`/`ends_at`, `purpose` (`comercial`, `cobranza`, `turnos`, `aviso`), `no_call_confirmed_at`, `callback_url`, `callback_secret` (cifrado). WhatsApp: `account_id`, `template_name`/`language`/`category`/`body`/`params`, `template_param_names`. Voz: `from_number_id`, `voice`, `concurrency` (1 = secuencial), `max_attempts`, `retry_minutes`, `retry_on`, `followup` (JSON; NULL = apagado). Un `CHECK` por canal exige sus campos |
| `campaign_contacts` | `campaign_id`, `contact_id` (único por par), `vars` (copia de nombre, teléfono y email al agregarlo, más `params`), `status` (`pending`, `in_progress`, `retry`, `done`, `failed`, `skipped`), `result`, `error`, `conversation_id`. WhatsApp: `wamid`, `sent_at`, `replied_at`. Voz: `attempts`, `next_attempt_at`, `last_attempt_at`, `followup_status`/`wamid`/`sent_at`/`error`/`conversation_id` |
| `campaign_callbacks` | Cola del webhook: `event`, `status` (`pending`, `sent`, `failed`), `attempts`, `next_attempt_at`, `last_status_code` |
| `call_logs` | `campaign_contact_id` (cada intento de voz es una `CallRow`) y `sip_status` |

**Resultados** (`campaign_contacts.result`): WhatsApp guarda `sent`; `delivered`, `read` y `replied` salen de
`wa_messages` (por `wamid`) y `replied_at`. Voz: `answered`, `no_answer`, `busy`, `voicemail`, `invalid`,
`rejected`, `failed`.

## API

`/api/v1`. El cliente ve lo suyo (usuario o API key); un admin pasa `client_id`.

**Contactos** (`app/api/routers/contacts.py`, `app/services/contacts.py`):

| Ruta | Qué hace |
|---|---|
| `GET /contacts?q=&archived=` | Lista paginada; `archived`: `false` (default), `true`, `all` |
| `POST /contacts` | Uno o una lista, *upsert* por teléfono |
| `POST /contacts/import` | CSV como JSON `{csv}` (upsert): creados, actualizados, archivados e inválidos con fila y motivo |
| `GET/PATCH /contacts/{id}` | Ficha; edita nombre, email y nota |
| `GET /contacts/{id}/campaigns` | Campañas del contacto |
| `POST /contacts/{id}/archive`, `/unarchive`; `POST /contacts/archive` | Archivar uno, desarchivar, archivar en lote (`contact_ids`). No hay DELETE |
| `GET/POST /contacts/optouts`, `DELETE /contacts/optouts/{phone}` | Bajas por teléfono y canal |

**Campañas** (`app/api/routers/campaigns.py`):

| Ruta | Qué hace |
|---|---|
| `POST /campaigns` | Crea en `draft` con `channel` y su config; opcional `contacts` y `"start": true` en el mismo cuerpo |
| `GET /campaigns?channel=&status=` | Lista con contadores |
| `GET /campaigns/plan` | Qué permite el plan y cuánto se usó |
| `GET /campaigns/{id}` | **Polling**: `status`, `in_window`, `total`, `percent`, `eta_minutes` (ritmo de los últimos 15 min), `progress`, `results`, `goal` (voz), `minutes_used` (voz), `followup` |
| `PATCH /campaigns/{id}`, `DELETE /campaigns/{id}` | Editar; borrar solo en borrador (si empezó, se cancela) |
| `POST /campaigns/{id}/contacts` | Suma por `contact_ids`, `contacts` o `csv` (los nuevos entran en la agenda), en borrador o pausada |
| `GET /campaigns/{id}/contacts?status=&result=` | Paginado, con `conversation_id` |
| `GET /campaigns/{id}/stats` | `attempts`, `reached`, `contact_rate`, `goal`, `goal_rate`, `avg_duration_seconds`, `minutes`, `results`, `by_hour` |
| `GET /campaigns/{id}/report.csv` | Una fila por contacto (UTF-8 con BOM; celdas que Excel tomaría por fórmula con `'`) |
| `POST /campaigns/{id}/start`, `/resume`, `/pause`, `/cancel` | `start`/`resume` validan plan, agente, número o plantilla, horario y, en `comercial`, `no_call_registry_checked: true` |

Alias de WhatsApp (`app/api/routers/wa_campaigns.py`): `/whatsapp/campaigns/*` (con `recipients` posicionales) y
`/whatsapp/optouts`. `campaign_id` filtra también `GET /calls`, `/stats` y `/stats/daily`.

MCP: `list_contacts`, `get_contact`, `update_contact`, `import_contacts`, `archive_contacts`, `unarchive_contact`,
`get_contact_campaigns`, `list_optouts`, `add_optout`, `create_campaign`, `update_campaign`, `delete_campaign`,
`add_campaign_contacts`, `start_campaign`, `pause_campaign`, `resume_campaign`, `cancel_campaign`, `list_campaigns`,
`get_campaign`, `get_campaign_plan`, `list_campaign_contacts`, `get_campaign_stats`, `get_campaign_report`.

UI: `web/src/features/contacts/` (Agenda → Contactos: búsqueda, filtro Activos/Archivados/Todos, CSV con vista
previa, archivar en lote, ficha con campañas) y `web/src/features/campaigns/` (Canales → Campañas: alta de
WhatsApp y de llamadas, `VoiceCampaignModal`, detalle con avance, resultados, atendidas por hora, contactos y
polling cada 5 s).

## Flujo

Un solo loop en `app` (`app/campaigns/loop.py`) delega por canal: el sender de WhatsApp cada
`WA_CAMPAIGN_TICK_SECONDS` (5 s) y el dialer de voz cada `CALL_CAMPAIGN_TICK_SECONDS` (2 s). Los dos activan las
`scheduled` cuyo `starts_at` llegó y cierran las que pasaron `ends_at` (`roll_schedule`). Lógica común (estado,
plan, variables, seguimiento) en `app/services/campaigns.py`.

### Contactos

- **Carga:** a mano, CSV o API; *upsert* por teléfono (lo que no viene no se pisa). CSV con encabezado: una
  columna de teléfono (`telefono`, `celular`, `phone`, `whatsapp`), `nombre`, `email` y `notas` opcionales; las demás
  se ignoran; separador coma, punto y coma o tab.
- **Teléfono:** `app/services/phones.py` normaliza a E.164. Un argentino sin el 9 se toma como celular (`+549`);
  no se detectan fijos. El `wa_id` de Meta es el E.164 sin `+`.
- **Archivar:** no se puede agregar a una campaña nueva; sus intentos pendientes en campañas abiertas pasan a
  `skipped` (`contact_archived`). Recargar un archivado actualiza los datos pero no lo desarchiva (se informa
  aparte). `max_contacts` cuenta solo los activos.

### WhatsApp (`app/whatsapp/campaigns.py`, `app/whatsapp/sender.py`)

- **Quién:** el admin en cualquier número; el cliente solo en los suyos (token propio: `own_app` o Embedded Signup).
- **Plantilla:** se lee de Meta al crear y al iniciar (tiene que estar `APPROVED`) y se guarda el cuerpo. Variables
  solo en el cuerpo: por dato del contacto (`template_param_names`: `nombre`, `telefono` o `email`; `{{1}}` = el
  primero) o posicionales (`vars["params"]`, alias `/whatsapp/campaigns`).
- **Destinatarios:** se saltean con motivo los inválidos, repetidos, archivados, con baja de WhatsApp y los que no
  completan las variables. Techo `WA_CAMPAIGN_MAX_RECIPIENTS` (10.000).
- **Envío:** según `rate_per_minute` (1 a 600, ráfaga máxima de un minuto), dentro del horario y los días. El
  contacto pasa a `in_progress` antes de llamar a Meta: si `app` se reinicia en el medio queda `failed` ("puede
  haber llegado"), no se reenvía.
- **Errores de Meta:** token rechazado, 131031, 131042, 131048, 132001, 132015, 132016 y 368 pausan la campaña con
  el motivo; 4, 80007, 130429 y 131056 la hacen esperar un minuto; el resto deja ese contacto `failed`.
- **Respuesta:** la conversación se crea recién cuando el contacto responde. Dentro de `WA_CAMPAIGN_REPLY_DAYS` (7)
  arranca con el cuerpo de la plantilla como apertura y la atiende el agente de la campaña (o el del número si no
  tiene o está archivado); gana sobre el ruteo por contacto. Queda enlazada al contacto (`replied_at`).
- **Bajas:** un contacto de una campaña que responde "baja", "stop", "no me interesa"… (el mensaje entero, sin
  acentos ni signos: `OPTOUT_TEXTS`) o toca el botón "No me interesa" entra en `contact_optouts` (whatsapp,
  `keyword`), recibe `WA_OPTOUT_REPLY` sin LLM y ninguna campaña le vuelve a escribir. Solo si no hay conversación
  en curso: ahí contesta el agente.

### Voz (`app/campaigns/dialer.py`, `app/services/campaign_calls.py`)

1. Fuera de horario, día o feriado (`CAMPAIGN_HOLIDAYS`) no marca (`in_window=false`).
2. **Cupo** = `min(min(concurrency, max_campaign_concurrency) − en curso, crédito de rate_per_minute,
   CALL_CAMPAIGN_MAX_CONCURRENT − en curso de todas)`; el tope global se reparte por turnos (primero la que hace
   más que no marca).
3. Toma `pending`/`retry` vencidos con `FOR UPDATE SKIP LOCKED`, saltea bajas de voz y archivados y llama a
   `services/calls.start_call` con `campaign_contact_id` y `vars` (pasa por `quota.admit`).
   - Sin lugar por concurrencia: vuelve a `pending` sin gastar intento y la campaña espera 10 s.
   - Sin minutos, tope de llamadas, cliente inactivo, agente archivado o número suspendido: `pending` y la campaña
     se pausa con el motivo. Teléfono inválido: `failed` (`invalid`).
   - `CALL_CAMPAIGN_FAILURE_STREAK` (10) intentos `failed` seguidos pausan la campaña (trunk o Anura caídos).
4. El worker pasa `ringing_timeout` (`CALL_RINGING_TIMEOUT_SECONDS`, 30 s) y clasifica el error de
   `create_sip_participant` por `sip_status_code` (`SIP_RESULTS`): 486/600 `busy`; 408/480/487 o timeout
   `no_answer`; 404/484/604 `invalid`; 403/603 `rejected`; otro `failed`.
5. **Cierre** (`close_contact`, `close_attempt`): `answered` → `done`; resultado en `retry_on` con intentos que
   sobran → `retry` a los `retry_minutes` (default 3 intentos, 60 min, `no_answer`, `busy`, `voicemail`, `failed`);
   si no, `done` (incluye `rejected`) o `failed` (`invalid`, `failed`). Sin nada pendiente, la campaña pasa a `done`.
6. **Recuperación:** al arrancar `app` y cada 60 s (sin tocar lo reclamado hace menos de 2 min), los `in_progress`
   sin llamada activa vuelven a `retry`.

- **Variables en la conversación** (`app/conversation/contact.py`): la apertura reemplaza `{{nombre}}`,
  `{{telefono}}`, `{{email}}` (sin importar mayúsculas ni acentos); una que falta queda vacía y el texto se acomoda.
  Los datos que se llaman como un campo del agente lo precargan; el resto va al prompt como datos del contacto. Solo
  en llamadas de campaña.
- **Contestador** (`app/campaigns/voicemail.py`): lista de frases ("deje su mensaje", "buzón", "después de la
  señal"…) sobre las primeras 4 transcripciones del que atendió; si matchea, `voicemail`, corta y reintenta.
- **Baja por voz:** un resultado del agente con `no_contact` ("No volver a llamar" en el editor) agrega
  `contact_optouts` (voice, `outcome`) al cerrar (`apply_outcome_optout`). WhatsApp sigue habilitado.
- **Seguimiento por WhatsApp** (`followup`: `after`, `account_id`, `template_name`, `template_language`, `params`,
  `agent_id`): requiere `campaign_followup` en el plan, cuenta conectada del cliente y plantilla aprobada (se
  revalida al iniciar y retomar). Al cerrar el último intento con un resultado de `after`, el contacto queda
  `followup_status=pending` y lo manda el sender con el ritmo, horario y días de la campaña (también ya `done`; no
  pausada ni cancelada). Se saltean fijos, bajas de WhatsApp, archivados y los que no completan variables. Un
  problema de Meta frena los seguimientos (1 o 10 min) sin pausar la campaña. La respuesta queda en
  `followup_conversation_id`.

### Plan

- Se valida al crear, al sumar contactos y al iniciar (`app/services/limits.py`). `max_campaigns_per_month` cuenta
  al iniciar por primera vez (mes calendario de `BILLING_TIMEZONE`); cancelar no devuelve el cupo.
- Rige en marcha: con `max_campaign_concurrency` 0 el dialer pausa; los seguimientos esperan mientras el plan no
  incluya `campaign_followup`.
- Al cambiar el tier de un cliente o los canales de un tier, las campañas de un canal que ya no incluye pasan a
  `paused` (`pause_campaigns_outside_plan`, desde `billing.fit_numbers` y los routers de tiers y clientes).
- Las llamadas de campaña cuentan como cualquier saliente: `outbound_minutes`, `max_calls_per_*` y
  `max_concurrent_calls` (sumando entrantes).

### Webhook de la campaña (`app/campaigns/callbacks.py`, `app/services/campaign_callbacks.py`)

- Eventos: `contact.finished`, `contact.followup` y `campaign.finished` (al cancelar en bloque no hay uno por
  contacto). Van a `campaign_callbacks` en la misma transacción y los entrega `callback_loop`.
- POST JSON con `X-Atentina-Event`, `X-Atentina-Delivery` (el mismo en los reintentos) y
  `X-Atentina-Signature: sha256=<HMAC-SHA256 del cuerpo>`. 2xx es éxito; si no, reintenta a los 30 s, 2 min, 10 min,
  1 h y 6 h (`CAMPAIGN_CALLBACK_MAX_ATTEMPTS`, 6) y queda `failed`.
- El secreto va cifrado con `WA_TOKEN_KEY`; si el cliente no manda uno se genera y se muestra una sola vez.
- **SSRF:** solo https a un host público; al entregar se resuelve, se exige IP pública y se conecta a esa IP con el
  SNI y el `Host` originales, sin redirecciones. `CAMPAIGN_CALLBACK_ALLOW_PRIVATE=true` solo en desarrollo.

## Bloquear y cortar

| Ruta | Qué hace |
|---|---|
| `GET/POST /blocked-numbers`, `DELETE /blocked-numbers/{phone}` | `blocked_numbers` (`client_id`, `phone` E.164, `note`; migración 0021): las **llamadas entrantes** de ese número (línea o llamada de WhatsApp, por `wa.wacid`) se cortan sin atender y quedan `rechazada` / `blocked_number` (`services/calls.start_inbound`); una llamada directa a ese número da 403. No toca los mensajes de WhatsApp ni las salientes de campaña (para eso, las bajas) |
| `POST /calls/{conversation_id}/hangup` | Corta una llamada en curso (cierra la room de LiveKit); termina con `hangup_by_user`. 409 si no está en curso |

UI: tarjeta Bloqueados en Contactos (`BlockedNumbersCard.tsx`), **Bloquear número** y **Cortar llamada** en el detalle
de la conversación. MCP: `list_blocked_numbers`, `block_number`, `unblock_number`, `hangup_call`.

## Reglas y trampas

- **Un solo `app`:** el crédito de ritmo (dialer y sender) vive en memoria. Con dos copias, `SKIP LOCKED` evita el
  doble marcado pero el ritmo se duplica.
- **`CALL_CAMPAIGN_MAX_CONCURRENT` (8) sin medir con Gemma:** deja lugar a entrantes y demo. No subirlo sin un CAP.
- **Registro No Llame** (Ley 26.951): una campaña `comercial` no arranca sin `no_call_registry_checked: true`
  (422 `no_call_confirmation_required`); se guarda en `no_call_confirmed_at` y no se vuelve a pedir al retomar.
  Cambiar `purpose` pide la campaña pausada y borra la confirmación. Rige en los dos canales.
- **Contestador:** es una lista de frases, no AMD: un humano que dice "no está disponible" en su primer turno se toma
  por buzón; sin detección, un buzón queda `answered`.
- **Una llamada que termina con la campaña `cancelled` o `done`** no se reintenta (y en `cancelled`, sin seguimiento).
- **Trunk saliente:** tras reiniciar el host sin `make livekit-sip` no existe `anura-asterisk-outbound`; la racha de
  fallas pausa la campaña sin quemar la lista.
- **Costo de Meta:** cada plantilla entregada la cobra Meta a la WABA del número (Marketing ~USD 0,062 en
  Argentina). La app no lo muestra ni lo topea.
- **Calidad del número:** Meta baja el límite si los usuarios bloquean o reportan: plantillas sobrias, bajas
  respetadas, no mandar marketing desde el número de cobranzas.

## Variables de `.env`

`CALL_CAMPAIGN_MAX_CONCURRENT` (8), `CALL_CAMPAIGN_TICK_SECONDS` (2), `CALL_CAMPAIGN_FAILURE_STREAK` (10),
`CALL_RINGING_TIMEOUT_SECONDS` (30), `CAMPAIGN_HOLIDAYS` (`YYYY-MM-DD` separadas por coma),
`CAMPAIGN_CALLBACK_TICK_SECONDS`, `CAMPAIGN_CALLBACK_TIMEOUT_SECONDS`, `CAMPAIGN_CALLBACK_MAX_ATTEMPTS` (6),
`CAMPAIGN_CALLBACK_ALLOW_PRIVATE`, `WA_CAMPAIGN_TICK_SECONDS` (5), `WA_CAMPAIGN_REPLY_DAYS` (7),
`WA_CAMPAIGN_MAX_RECIPIENTS` (10.000), `WA_OPTOUT_REPLY`.

## Desplegar y probar

- Código: `make calls-active && make up-agent` (`app` lleva dialer, sender y webhook; `agent`, el `ringing_timeout`,
  el cierre de intentos y el contestador). Migraciones: `make migrate-test` y `make migrate`.
- No hace falta `make livekit-sip` ni recrear Asterisk salvo que cambie el trunk saliente.
- Tests (`make test`): `test_contacts.py`, `test_campaigns.py`, `test_campaign_dialer.py` (reloj falso),
  `test_campaign_vars.py`, `test_campaign_integration.py`, `test_whatsapp_campaigns.py`, `test_blocked_numbers.py`.
- Prueba de voz: campaña de 2 o 3 números propios, `concurrency` 1, agente de prueba; revisar `call_logs.sip_status`
  de cada intento. De WhatsApp: plantilla aprobada a 2 o 3 números propios.

## Pendientes

- **Códigos SIP reales de Anura:** verificar con números propios qué devuelve Anura (ocupado, no atiende,
  inexistente) y si Asterisk los pasa sin cambiar (`from-livekit`); ajustar `SIP_RESULTS`.
- **Capacidad:** test con entrantes y salientes de campaña mezcladas, con Gemma, para fijar
  `CALL_CAMPAIGN_MAX_CONCURRENT` (`docs/capacity/`).
- **Contestador:** medir con llamadas reales cuántos buzones atrapa y cuántos humanos confunde.
- **PostgreSQL bajo carrera:** `SKIP LOCKED` / `FOR UPDATE OF` y el cupo mensual con pedidos concurrentes.
- **Cola `campaign_callbacks`:** limpiar los `sent` y `failed` viejos; apagar o rotar el webhook de una campaña
  terminada (hoy PATCH da 409).
- **Respuesta de WhatsApp a una campaña:** la conversación no recibe los datos del contacto (solo los parámetros de
  la plantilla).
- **WhatsApp:** reintentos de los fallidos, costo estimado por campaña, plantillas con imagen o variables fuera del
  cuerpo.
- **Legal:** texto de términos sobre el Registro No Llame validado con un abogado, y aviso de grabación si el agente
  graba ([LEGAL.md](LEGAL.md)).
