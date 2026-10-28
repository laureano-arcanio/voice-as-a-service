# Plan: campañas de llamadas salientes (y campañas unificadas)

Un lote de contactos que el agente llama solo, desde la UI o la API, programado, en paralelo o de a
uno, con estado consultable y reportes. **Implementado el 19-oct-2026 (fases 1 a 4), sin desplegar**:
estado por fase, desvíos y cómo desplegar, en la [sección 14](#14-avance).

## 1. Decisiones (19-oct-2026)

1. **Una sola tabla de campañas** (`campaigns`) con `channel`: `whatsapp` o `voice`. Las campañas de
   WhatsApp actuales (`wa_campaigns`, fase 4 de `WHATSAPP_PLAN.md`, en producción) se migran a ella.
2. **Seguimiento por WhatsApp** a quien no atendió: apagado por default, configurable por campaña.
3. **Las campañas entran en el plan:** cada tier dice si las tiene, por qué canal y con qué topes
   (contactos por campaña, campañas por mes, concurrencia...). El tope de campañas es **mensual**
   (`max_campaigns_per_month`), sin tope de campañas activas a la vez.
4. **Agenda de contactos por cliente** (`contacts`): el número es lo único obligatorio; nombre y
   demás datos, opcionales. Las campañas toman sus destinatarios de ahí. **Los contactos no se
   borran: se archivan**, y los archivados se ven con un filtro.

## 2. Qué hay hoy

- **Saliente de una persona del equipo (sin agente):** no es de este plan ni de las campañas: son las llamadas
  directas, `POST /api/v1/direct-calls` ([`LLAMADAS_DIRECTAS_PLAN.md`](LLAMADAS_DIRECTAS_PLAN.md)). Descuentan minutos
  salientes y canales de Anura como las de acá.
- **Saliente individual:** `POST /api/v1/calls {agent_id, phone, from_number_id, voice}`
  (`app/services/calls.py`). `prepare_call` admite con el tier (`quota.admit`, lock de fila del cliente),
  crea conversación + `CallRow(mode=saliente)` y despacha el worker a una room de LiveKit.
- **El worker marca** (`app/voice/worker.py`): `create_sip_participant(wait_until_answered=True)` por
  `anura-asterisk-outbound` → Asterisk → Anura. Todo fallo SIP queda `fallida` /
  `sip_call_failed`, sin distinguir ocupado, no atiende o número inexistente.
- **Campañas de WhatsApp:**
  - `wa_campaigns` + `wa_campaign_recipients` + `wa_optouts`;
  - loop `campaign_loop` (`app/whatsapp/sender.py`), router `/api/v1/whatsapp/campaigns`;
  - UI en `web/src/features/campaigns/`;
  - `app/whatsapp/service.py` las usa para la respuesta a una plantilla y la baja por palabra clave.
  - No las limita el tier.
- **Límites del tier:** `max_concurrent_calls`, `outbound_minutes`, `max_calls_per_{hour,day,month}`.

## 3. Modelo de datos

### 3.1 `contacts`: agenda del cliente

| Campo | Qué es |
|---|---|
| `client_id`, `phone` | E.164 (`+549…` celular, `+54…` fijo). **Único por cliente**. Lo único obligatorio |
| `name`, `email`, `external_id` | Opcionales. `external_id`: id en el sistema del cliente, para cruzar reportes |
| `notes` | Nota libre (hasta 2000 caracteres), como la de un contacto del teléfono. Desde el 27-oct-2026, migración 0040, reemplaza a `attributes` (datos por contacto) y `tags` (etiquetas), que se quitaron: la migración pasó los datos a la nota como líneas `clave: valor` |
| `source` | `manual`, `csv`, `api`, `campaign`, `inbound` |
| `archived_at` | NULL = activo. Archivar no borra (sección 3.1.1) |
| `created_at`, `updated_at` | |

- **Carga:** a mano, CSV o API.
  - Hace *upsert* por teléfono: un contacto existente se actualiza; lo que no viene no se pisa (la nota
    vacía tampoco).
  - La respuesta dice creados, actualizados e inválidos (con fila y motivo).
- **Normalización:** una sola función a E.164 para los dos canales (generalizar
  `campaigns.normalize_phone`). El `wa_id` de Meta sale del E.164 sin el `+`. Un fijo no tiene WhatsApp:
  la campaña de WhatsApp lo saltea con motivo.
- **Tope:** `tiers.max_contacts`.
- **Después (no en la primera fase):**
  - vincular entrantes y conversaciones al contacto por teléfono (`contact_id` en `conversations`), para
    tener la ficha del contacto con su historial;
  - que las reglas de `wa_routes` referencien contactos en vez de una lista de `wa_id`.

#### 3.1.1 Archivar

- **No hay borrado** de contactos, ni por la UI ni por la API: solo archivar y desarchivar. Se conservan
  el historial, los reportes y la relación con campañas y conversaciones.
- **Lista:** por default muestra los activos; el filtro `archived` (`activos`, `archivados`, `todos`)
  muestra el resto.
- **Archivado en una campaña:** no se puede agregar a una campaña nueva. Si ya estaba en una en curso,
  sus intentos pendientes pasan a `skipped` con motivo `contact_archived`. El reporte de las terminadas
  lo conserva (`vars` es copia).
- **Recarga de un archivado:** como el teléfono es único por cliente, un CSV o `POST /contacts` con ese
  número **no lo desarchiva solo**. Actualiza sus datos y lo informa aparte en la respuesta
  ("archivados: N"), para que el usuario decida. Desarchivar es explícito.
- **Tope de la agenda:** `tiers.max_contacts` cuenta solo los activos.
- **Archivar en lote:** por selección.

### 3.2 `contact_optouts`: no contactar

Generaliza `wa_optouts`: `(client_id, phone, channel)` con `channel` en `whatsapp`, `voice` o `all`,
`source` (`keyword`, `outcome`, `manual`) y fecha.

**Tabla aparte de `contacts` a propósito:** la baja es del teléfono, no de la ficha. Sigue aunque el
contacto se archive o se cargue de nuevo con otros datos, y se puede registrar sin crear el contacto
(una baja por palabra clave de alguien que no está en la agenda).

### 3.3 `campaigns`: una tabla, dos canales

Migración: `wa_campaigns` → `campaigns`, con `channel='whatsapp'` en las existentes.

| Campo | Canal | Qué es |
|---|---|---|
| `client_id`, `agent_id`, `name`, `created_by`, `channel` | ambos | |
| `status`, `status_reason` | ambos | `draft`, `scheduled`, `running`, `paused`, `done`, `cancelled` |
| `rate_per_minute` | ambos | Envíos o arranques por minuto |
| `window_start`, `window_end`, `weekdays` | ambos | Horario permitido (hora local, `BILLING_TIMEZONE`). Hoy WhatsApp tiene ventana sin días |
| `starts_at`, `ends_at` | ambos | Programación: no arranca antes, termina después |
| `started_at`, `finished_at` | ambos | |
| `account_id`, `template_*` | whatsapp | Lo de hoy (número conectado y copia de la plantilla) |
| `from_number_id`, `voice` | voice | Caller ID (número del cliente) y voz; NULL = defaults |
| `concurrency` | voice | Llamadas simultáneas de la campaña. **1 = secuencial**, N = paralelo |
| `max_attempts`, `retry_minutes`, `retry_on` | voice | Reintentos por contacto (default 3, 60 min, `no_answer`, `busy`, `voicemail`, `failed`) |
| `followup` | voice | JSON, NULL = apagado (sección 6) |
| `callback_url`, `callback_secret` | ambos | Webhook opcional (sección 8) |

- Un `CHECK` por canal exige los campos de ese canal (`account_id` y `template_name` en WhatsApp;
  `concurrency` en voz).
- **Alternativa descartada:** columnas por canal en JSON (`config`). Pierde las foreign keys
  (`account_id`, `from_number_id`) y los checks; son pocas columnas.

### 3.4 `campaign_contacts`: un contacto en una campaña

Migración: `wa_campaign_recipients` → `campaign_contacts`. Por cada `wa_id` distinto, crear el `contact`
del cliente y apuntarle.

| Campo | Canal | Qué es |
|---|---|---|
| `campaign_id`, `contact_id` | ambos | Único por (`campaign_id`, `contact_id`) |
| `vars` | ambos | Copia de los datos del contacto al agregarlo, más las columnas propias de la campaña. La campaña no cambia si después se edita el contacto |
| `status` | ambos | `pending`, `in_progress`, `retry`, `done`, `failed`, `skipped` |
| `result` | ambos | WhatsApp: `sent`, `delivered`, `read`, `replied`. Voz: `answered`, `no_answer`, `busy`, `voicemail`, `invalid`, `rejected`, `failed` |
| `error` | ambos | JSON con el detalle (código de Meta o SIP) |
| `conversation_id` | ambos | La que abrió la respuesta (WhatsApp) o el último intento (voz) |
| `wamid`, `sent_at`, `replied_at` | whatsapp | Lo de hoy |
| `attempts`, `next_attempt_at`, `last_attempt_at` | voice | |
| `followup_status`, `followup_wamid` | voice | Seguimiento por WhatsApp (sección 6) |

- **Estados actuales de WhatsApp en la migración:** `sending` → `in_progress`; `sent` → `done` con
  `result=sent`; `failed` y `skipped` quedan igual.
- **Intentos de voz:** cada uno es una `CallRow`, atada por la columna nueva
  `call_logs.campaign_contact_id`. También guarda `sip_status`.

### 3.5 Tier

Columnas nuevas en `tiers` (NULL = sin límite, 0 = no incluido, como el resto):

| Campo | Qué limita |
|---|---|
| `campaign_channels` | Canales habilitados: `[]`, `["whatsapp"]`, `["voice"]` o los dos |
| `max_campaigns_per_month` | Campañas iniciadas por mes calendario (`BILLING_TIMEZONE`). Cuenta al pasar de `draft` a `scheduled`/`running`; cancelar no devuelve el cupo |
| `max_campaign_contacts` | Contactos por campaña (hoy `WA_CAMPAIGN_MAX_RECIPIENTS` = 10.000 global, queda como techo) |
| `max_campaign_concurrency` | Tope de `concurrency` de una campaña de voz |
| `max_contacts` | Contactos activos en la agenda (los archivados no cuentan) |
| `campaign_followup` | Si puede activar el seguimiento por WhatsApp |

- **Cuándo se valida:** al crear, al agregar contactos y al iniciar (`services/limits.py`).
- **Las llamadas de campaña** también cuentan como hoy: `outbound_minutes`, `max_calls_per_*` y
  `max_concurrent_calls` (este último, sumando entrantes).
- **Al bajar de plan:** las campañas `running` o `scheduled` de un canal que el tier nuevo no
  incluye pasan a `paused`, con `status_reason`. Mismo criterio que los números suspendidos.
- **Migración:** los tiers actuales quedan con `["whatsapp"]` y sin topes, para no cortar a los
  clientes que ya usan campañas. Después se ajustan plan por plan.
- **Pantallas:** se muestran en la de Tiers y en la comparación de planes de `/plan`.

## 4. Ejecución

El loop `campaign_loop` pasa a ser uno solo y delega por canal:

- **WhatsApp:** el `CampaignSender` actual, con las tablas nuevas.
- **Voz:** un *dialer* nuevo que corre cada ~2 s:
  1. Activa las `scheduled` cuyo `starts_at` llegó y cierra las que pasaron `ends_at`.
  2. Fuera de horario o día: no hace nada (la API informa `in_window=false`).
  3. **Cupo** = `min(concurrency − en curso, crédito de rate_per_minute, CALL_CAMPAIGN_MAX_CONCURRENT − en curso de todas las campañas)`.
  4. Toma contactos `pending`/`retry` con `next_attempt_at <= now`, `FOR UPDATE SKIP LOCKED`, y los
     pasa a `in_progress`. Así no hay doble marcado aunque haya dos copias de `app`.
     - Antes de marcar, revisa `contact_optouts`.
  5. Llama a `services/calls.start_call` con `campaign_contact_id` y `vars`.
     - `QuotaExceeded` por concurrencia: vuelve a `pending` sin gastar intento.
     - Por minutos o tope del mes: pausa la campaña.
- **Cierre del intento:** el worker, en `finalize`/`fail`, clasifica el resultado (sección 5) y deja el
  contacto en `done`, `retry` o `failed`. Cuando no queda nada pendiente, la campaña pasa a `done`.
- **Corte por fallas:** N `failed` seguidos (ej. 10) pausan la campaña. Cubre el trunk saliente
  inexistente tras reiniciar el host (el Redis de LiveKit no persiste) y Anura caído, sin quemar la
  lista. Mismo criterio que `sender.py` con los errores de Meta.
- **Recuperación al arrancar `app`:** los `in_progress` cuya `CallRow` ya no está activa vuelven a `retry`.
- **Variables en la conversación:**
  - La apertura del agente acepta `{{nombre}}`, `{{telefono}}`, `{{email}}` y `{{external_id}}`, etc., reemplazados con `vars`
    (`engine.new_conversation(..., opening=texto)` ya acepta un texto).
  - Los datos cuyo nombre coincide con un campo del workflow precargan `state.fields`: el agente
    no los pregunta (desde el 27-oct-2026 los datos por contacto se quitaron: solo nombre, teléfono, email e id externo).
  - El resto va al prompt como "Datos del contacto".
  - En WhatsApp, `vars` alimenta los parámetros de la plantilla. Hoy son una lista posicional en el
    CSV; el mapeo pasa a ser por nombre: `{{1}}` = `nombre`.
- **Baja por voz:** un `outcome` del agente marcado como "no contactar" (ej. `no_llamar`) agrega
  `contact_optouts(channel='voice')`.

## 5. Resultado de una llamada

`create_sip_participant` levanta `TwirpError` con el código SIP en la metadata (`sip_status_code`):

| SIP | `result` | Reintenta por default |
|---|---|---|
| 200 y habló | `answered` | No |
| 486, 600 | `busy` | Sí |
| 408, 480, 487 / timeout de ring | `no_answer` | Sí |
| 404, 484, 604 | `invalid` | No |
| 403, 603 | `rejected` | No |
| otro, 5xx, despacho | `failed` | Sí |

- Pasar `ringing_timeout` (~30 s) en `CreateSIPParticipantRequest`; hoy no se pasa.
- **A probar con números propios:** qué códigos devuelve Anura de verdad y si Asterisk los pasa sin
  cambiar (`extensions.conf`, `from-livekit`).
- **Contestador:** sin detección, un buzón queda `answered`. Primera versión, heurística: si el STT
  transcribe "deje su mensaje" / "buzón", o no hay voz del cliente en los primeros N s, queda
  `voicemail`, corta y reintenta. AMD real, después de medir cuánto pasa.

## 6. Seguimiento por WhatsApp (opcional por campaña)

`campaigns.followup` = NULL (apagado, default) o:

```json
{"after": ["no_answer", "busy", "voicemail"], "account_id": "…",
 "template_name": "recordatorio_deuda", "template_language": "es_AR",
 "params": ["nombre", "deuda"], "agent_id": null}
```

- Se manda **después del último intento** y solo si el resultado final está en `after`.
- Saltea a los fijos y a los que tienen baja de WhatsApp.
- Lo manda el mismo `CampaignSender`, con el ritmo de la campaña y dentro de su horario. El estado
  queda en `followup_status`/`followup_wamid` del mismo `campaign_contact`.
- La respuesta del contacto abre la conversación como hoy (`campaigns.reply_target`), con `agent_id`
  o, si no hay, el agente de la campaña.
- **Requisitos:** que el tier lo permita (`campaign_followup`) y que el cliente tenga cuenta de
  WhatsApp y la plantilla aprobada. Se valida al iniciar la campaña.

## 7. API

Rutas nuevas bajo `/api/v1`. Mismos permisos que hoy: el cliente ve lo suyo, el admin todo, y las API
keys son del cliente.

**Contactos**

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/contacts?q=&tag=&archived=` | Lista paginada; `archived`: `false` (default), `true` o `all` |
| POST | `/contacts` | Uno, o una lista (upsert) |
| POST | `/contacts/import` | CSV (upsert); devuelve creados, actualizados e inválidos |
| PATCH | `/contacts/{id}` | Edita datos y nota |
| POST | `/contacts/{id}/archive`, `/unarchive` | Sin DELETE: no se borra |
| POST | `/contacts/archive` | En lote, por `contact_ids` |
| GET / POST / DELETE | `/contacts/optouts` | Bajas (reemplaza `/whatsapp/optouts`) |

**Campañas**

| Método | Ruta | Qué hace |
|---|---|---|
| POST | `/campaigns` | Crea en `draft` con `channel` y su config. Opcional en el mismo cuerpo: `contacts` y `"start": true` |
| POST | `/campaigns/{id}/contacts` | Agrega por `contact_ids`, o una lista o CSV (que también hace upsert en la agenda) |
| POST | `/campaigns/{id}/start`, `/pause`, `/resume`, `/cancel` | `start` valida el tier, el agente, el número o la plantilla y el horario |
| GET | `/campaigns?channel=&status=` | Lista con contadores |
| GET | `/campaigns/{id}` | **Polling**: estado y progreso |
| GET | `/campaigns/{id}/contacts?status=&result=` | Paginado, con `conversation_id` |
| GET | `/campaigns/{id}/report.csv` | Reporte por contacto |

`/whatsapp/campaigns/*` y `/whatsapp/optouts` quedan como alias de las nuevas durante una versión, para
no romper integraciones, y después se borran.

**Polling** (`GET /campaigns/{id}`): un `GROUP BY status, result` con índice `(campaign_id, status)`.

```json
{
  "id": "…", "channel": "voice", "status": "running", "status_reason": null, "in_window": true,
  "total": 500, "percent": 33.0, "eta_minutes": 95,
  "progress": {"pending": 310, "in_progress": 5, "retry": 20, "done": 140, "failed": 25, "skipped": 0},
  "results": {"answered": 120, "no_answer": 30, "busy": 8, "voicemail": 10, "invalid": 6, "rejected": 1, "failed": 0},
  "goal": 64, "minutes_used": 212.5,
  "followup": {"sent": 22, "replied": 4},
  "started_at": "…", "updated_at": "…"
}
```

- En WhatsApp, `results` trae `sent`, `delivered`, `read` y `replied`, y no hay `minutes_used`.
- `eta_minutes`: sale del ritmo real de los últimos 15 min.
- `goal`: conversaciones que llegaron al objetivo del agente.

## 8. Webhook (opcional)

Con `callback_url`, un POST firmado (HMAC-SHA256 con `callback_secret`) por cada contacto que termina y
otro al terminar la campaña. Mismos campos que el reporte. Con reintentos y sin bloquear el loop.

## 9. UI (`web/`)

Sigue `docs/DESIGN_GUIDELINE_APP.md`.

- **Contactos** (pantalla nueva):
  - tabla con búsqueda y filtro Activos / Archivados / Todos;
  - archivar y desarchivar, uno o en lote (sin botón de borrar);
  - importar CSV con vista previa de columnas;
  - ficha del contacto con sus campañas (y después, sus conversaciones).
- **Campañas:** la pantalla actual, generalizada, con filtro por canal.
  - **Crear:** canal, agente, destinatarios (selección o CSV), horario y días, inicio
    programado. Voz: número de origen, modo (secuencial / paralelo con N, hasta el tope del tier),
    reintentos y seguimiento por WhatsApp. Lo que el tier no permite aparece deshabilitado, con el
    motivo.
  - **Detalle:** barra de progreso, tarjetas por resultado, tabla de contactos con link a la
    conversación, pausar, reanudar y cancelar, y descarga del reporte. Polling cada 5 s al mismo
    endpoint de la API.
- **Tiers:** los campos de la sección 3.5.

## 10. Reportes

- **Por campaña** (`report.csv`): una fila por contacto con `external_id`, teléfono, `vars`, intentos,
  resultado, duración, `outcome`, objetivo, campos capturados, seguimiento y link.
- **Indicadores:**
  - tasa de contacto (atendidas / llamadas);
  - tasa de objetivo (objetivo / atendidas);
  - duración media y minutos;
  - distribución de resultados;
  - atendidas por hora del día, para elegir el horario.
- **Dashboard general:** filtro por campaña en Llamadas y Estadísticas (`campaign_id` en
  `CallFilter`, `services/reports.py`).

## 11. Capacidad y legal

- **Capacidad:** la de Gemma 4 26B no está medida; con Qwen eran ~32 llamadas con p95 ≤ 3 s. Un tope
  global de salientes de campaña, `CALL_CAMPAIGN_MAX_CONCURRENT` (8 hasta medir), deja lugar a las
  entrantes y la demo.
- **Anura:** confirmar los canales salientes simultáneos y el límite de llamadas por segundo de la
  cuenta. El caller ID tiene que ser un número de la cuenta.
- **Registro No Llame** (Ley 26.951): las llamadas de publicidad a inscriptos están prohibidas.
  - La campaña lleva `purpose` (`comercial`, `cobranza`, `turnos`, `aviso`).
  - Las `comercial` exigen confirmar que la lista se filtró contra el registro.
  - En los términos queda que es responsabilidad del cliente. Validar con un abogado.
- **Horario por default:** 9 a 20, lunes a viernes, sin feriados (lista en config).
- **Grabación:** con `record_audio`, la misma deuda de aviso que en las entrantes.

## 12. Fases

Estado (19-oct-2026): fases 1 a 4 implementadas (backend y UI), sin desplegar; la 5 no se hizo.

1. **Agenda y unificación**, sin cambio visible para WhatsApp:
   - `contacts` y `contact_optouts`;
   - migración de `wa_campaigns` y `wa_campaign_recipients` a `campaigns` y `campaign_contacts`;
   - campos del tier, rutas nuevas con alias.
   - Los tests de `test_whatsapp_campaigns.py`, `test_api.py` y `test_migration_0008.py` tienen que
     seguir pasando. Probar la migración contra una copia del backup de producción antes de aplicarla.
2. **Campañas de voz:**
   - dialer, resultado SIP (con prueba real contra Anura), `ringing_timeout`, reintentos;
   - tope global, corte por fallas, polling;
   - tests con reloj falso, como `sender.py`.
3. **Variables, UI y reportes:** apertura con `{{var}}`, precarga de campos, pantalla Contactos,
   creación de campañas de voz, `report.csv`, filtro por campaña.
4. **Integración:** seguimiento por WhatsApp, webhook, baja por voz, `purpose`, contestador por
   heurística.
5. **Medición:** test de capacidad con entrantes y salientes de campaña mezcladas para fijar
   `CALL_CAMPAIGN_MAX_CONCURRENT` con Gemma.

## 13. Abierto

- Nada por ahora. Cerrado el 19-oct-2026: tope de campañas mensual, sin tope de activas; contactos sin
  borrado, solo archivados.

## 14. Avance

### Estado por fase (19-oct-2026, todo sin desplegar)

| Fase | Estado | Falta |
|---|---|---|
| 1. Agenda y unificación | Implementada: migración `0017`, contactos, bajas, campañas unificadas, límites del tier, `/api/v1/campaigns` con alias de `/whatsapp/*` | Probar la migración contra una copia del backup en PostgreSQL |
| 2. Campañas de voz | Implementada: dialer, `ringing_timeout`, resultado SIP, reintentos, tope global, corte por fallas, polling | Verificar con números propios los códigos SIP que devuelve Anura |
| 3. Variables, UI y reportes | Implementada: `{{var}}`, precarga de campos, `report.csv`, `stats`, filtro `campaign_id`; pantallas Contactos, Campañas (WhatsApp y voz) y Tiers | `npm run build` (la imagen de `app` lo hace sola) |
| 4. Integración | Implementada: seguimiento por WhatsApp, webhook, baja por voz, `purpose`, feriados, contestador por heurística | Medir el contestador con llamadas reales |
| 5. Medición | **No hecha**: `CALL_CAMPAIGN_MAX_CONCURRENT` (8) es un valor provisorio | Test de capacidad con entrantes y salientes mezcladas, con Gemma (`docs/capacity/`) |

### Desvíos respecto del plan

- **Datos de WhatsApp:** `vars` guarda `{"params": [...], ...}`; `delivered`, `read` y `replied` se siguen derivando de `wa_messages` y `replied_at` (en `result` solo queda `sent`). El CSV de `/campaigns` usa el formato de la agenda (columnas extra = atributos, mapeo por `param_names`); el posicional (`{{1}}`, `{{2}}`…) queda en el alias `/whatsapp/campaigns` y en `recipients`.
- **Teléfonos:** un argentino sin el 9 se toma como celular (+549), como antes; no se detectan fijos y `has_whatsapp` no rechaza nada. Etiquetas: minúsculas ASCII `[a-z0-9_.:-]`, hasta 32 caracteres.
- **API:** `POST /contacts` acepta uno o una lista; el import va como JSON `{csv}`, no multipart; los admins pasan `client_id` como query param. Sumados a lo planeado: `GET /campaigns/plan`, `GET /campaigns/{id}/stats` y `GET /contacts/{id}/campaigns`.
- **Resultados:** `rejected` (403/603) termina en `done`, no en `failed` (lo decidió el contacto). La racha de fallas se evalúa al cerrar cada intento, sin columna: al reanudar una campaña pausada por racha, un solo `failed` más la vuelve a pausar mientras los últimos N sigan fallidos.
- **Recuperación:** además de la del arranque, una cada 60 s, para que un worker caído no deje ocupado un cupo de concurrencia.
- **`purpose`:** rige en los dos canales (el plan no lo limitaba a voz).
- **Seguimiento:** puede salir con la campaña de voz ya `done`. Evento extra del webhook, `contact.followup`, que no estaba en el plan.
- **Variables:** una `{{variable}}` que el contacto no tiene queda vacía y el texto se acomoda. Las respuestas de WhatsApp a una campaña no reciben los datos del contacto en la conversación (solo los parámetros de la plantilla).
- **Revisión (19-oct-2026):**
  - retomar una campaña cuenta pendientes, en vuelo y reintentos (antes solo pendientes: una con todos en `retry` no se podía retomar);
  - el tope global `CALL_CAMPAIGN_MAX_CONCURRENT` se reparte por turnos: va primero la campaña que hace más que no marca y cada una toma su parte de los lugares libres;
  - la resolución DNS de `callback_url` corre en un thread (`check_url_async`), no en el event loop;
  - una llamada que termina con la campaña ya `cancelled` o `done` no se reintenta (y en `cancelled` tampoco queda seguimiento);
  - `goal` se guarda en memoria con una huella de las conversaciones (cuántas y cuál se tocó última), no recorre todas en cada consulta;
  - el plan rige también en marcha: el dialer usa `min(concurrency, max_campaign_concurrency)` (con tope 0 pausa) y el sender de seguimientos espera, sin perderlos, mientras el plan no incluya `campaign_followup`.
- **Plan del tier:** `billing.fit_numbers` ahora también pausa las campañas fuera del plan (el nombre ya no lo describe). Los tiers nuevos arrancan con `campaign_channels = []`.

### Cómo desplegar

1. **Antes:** probar la `0017` contra una copia del backup en PostgreSQL (`~/atentina-backups/`); solo se probó ida y vuelta en SQLite. Backup fresco (`scripts/ops/backup.sh`). La migración borra `wa_campaigns`, `wa_campaign_recipients` y `wa_optouts`: los datos pasan a las tablas nuevas; el downgrade los restaura, pero pierde la agenda y las campañas de voz.
2. **Migrar:** `make migrate` (0016 → 0017). Los tiers existentes quedan con `campaign_channels = ["whatsapp"]` y sin topes, así que las campañas de WhatsApp siguen andando. El seed no toca el tier `Interno` ya creado: **editarlo en Tiers** (canales WhatsApp y llamadas, seguimiento) para que `atentina` pueda crear campañas de voz.
3. **Recrear `app` y `agent`** (`make up-agent`; la imagen de `app` compila `web/`). `agent` lleva `ringing_timeout`, el cierre de intentos y el contestador; `app`, el dialer, el sender y el webhook. Recrearlos corta las llamadas en curso: confirmar antes y hacerlo fuera de horario pico.
4. **No hace falta** `make livekit-sip` ni recrear Asterisk: el trunk saliente (`anura-asterisk-outbound`) no cambia. Solo si la prueba con Anura muestra que Asterisk cambia los códigos SIP (`extensions.conf`, `from-livekit`).
5. **`.env`** (todo opcional, ver `.env.example`): `CALL_CAMPAIGN_MAX_CONCURRENT` (8), `CALL_CAMPAIGN_TICK_SECONDS`, `CALL_CAMPAIGN_FAILURE_STREAK` (10), `CALL_RINGING_TIMEOUT_SECONDS` (30), `CAMPAIGN_HOLIDAYS`, `CAMPAIGN_CALLBACK_*`. Si se edita el `.env`: diff enmascarado antes de reiniciar.
6. **Primera prueba:** campaña de voz de 2 o 3 números propios, `concurrency` 1, agente de prueba. Revisar el `sip_status` de cada intento (busy, no atiende, número inexistente) y ajustar la tabla de la sección 5.
7. **Un solo `app`:** el crédito de ritmo (dialer y sender) vive en memoria; con dos copias de `app` el `SKIP LOCKED` evita el doble marcado, pero el ritmo se duplicaría.

### Pendientes

- Probar la migración y `SKIP LOCKED` / `FOR UPDATE OF` en PostgreSQL (SQLite los ignora), y el cupo mensual bajo carrera.
- Limpiar la cola `campaign_callbacks` (los `sent` y `failed` viejos); apagar o rotar el webhook de una campaña terminada (PATCH da 409).
- Pasar los datos del contacto a la conversación que abre la respuesta de WhatsApp (`ReplyTarget`).
- Medir el contestador con llamadas reales (cuántos buzones atrapa, cuántos humanos confunde) antes de pensar en AMD.
- Fase 5 (capacidad). Antes de usarlo con un cliente: texto de términos del Registro No Llame, validado con un abogado, y aviso de grabación si `record_audio`.

### Detalle por etapa

- **Fase 1, datos (19-oct-2026, sin desplegar):**
  - migración `0017` (`contacts`, `contact_optouts`, `campaigns`, `campaign_contacts`, columnas del tier, `call_logs.campaign_contact_id` y `sip_status`); copia los datos de WhatsApp y borra las tablas viejas; probada ida y vuelta en SQLite, **falta probarla contra una copia del backup en PostgreSQL**;
  - WhatsApp (`campaigns.py`, `sender.py`) ya corre sobre las tablas nuevas: `params` va en `vars["params"]`, los estados son `in_progress` y `done` + `result=sent`, y `delivered`/`read`/`replied` siguen saliendo de `wa_messages` y `replied_at`;
  - `services/phones.py` (E.164 único), `services/contacts.py` y `/api/v1/contacts` (incluye `/contacts/optouts`); límites del tier en `services/limits.py` (los cuatro numéricos se ajustan por cliente).
  - Todavía **no se aplican** a las campañas de WhatsApp (`check_campaign_*` y `pause_campaigns_outside_plan` están, sin llamar); `campaign_channels` de los tiers nuevos arranca en `[]`.
  - Un teléfono argentino sin el 9 se toma como celular (+549), como antes: no se detectan fijos.
- **Fase 1, lógica (19-oct-2026, sin desplegar):**
  - `services/campaigns.py`: estado, plan, variables y seguimiento comunes a los dos canales; `whatsapp/campaigns.py` y `sender.py` lo usan. El sender, además, activa las `scheduled` cuyo `starts_at` llegó y termina las que pasaron `ends_at` (`roll_schedule`; el dialer hará lo mismo con voz), y saltea (`contact_archived`) a quien se archivó después de cargarlo;
  - API `/api/v1/campaigns` (sección 7, sin `report.csv`): crear con `channel`, sumar contactos (`contact_ids`, `contacts`, `csv`, y `recipients` posicional en WhatsApp), `start`, `pause`, `resume`, `cancel`, lista, detalle de polling y contactos paginados. Las de voz se crean y validan (agente, número de origen, horario, concurrencia, reintentos), pero no se marcan hasta el dialer. `/whatsapp/campaigns` y `/whatsapp/optouts` siguen igual, sobre el mismo código;
  - variables de la plantilla por dato del contacto (`nombre`, `telefono`, `email`, `external_id`; desde el 27-oct-2026 sin datos propios por contacto) (`template_param_names`, `param_names` al crear): `{{1}}` = el primero. `vars` guarda una copia de los datos del contacto (`nombre`, `telefono`, `email`, `external_id`) más `params`;
  - plan: canal, `max_campaigns_per_month` (al iniciar, solo la primera vez), `max_campaign_contacts` (al sumar y al iniciar) y `max_campaign_concurrency`, también por el alias. Al cambiar el tier de un cliente, o los canales de un tier, las campañas de un canal que ya no incluye pasan a `paused` (`pause_campaigns_outside_plan`, desde `billing.fit_numbers` y los routers de tiers y clientes).
  - Sin hacer todavía: `goal` y `followup` del polling (vienen null), `report.csv`, `callback_*`, `purpose` y `followup` en el alta, y el dialer.
- **Fase 2, campañas de voz (19-oct-2026, sin desplegar):**
  - **Dialer** (`app/campaigns/dialer.py`): lo llama un solo loop (`app/campaigns/loop.py`, el de `main.py`) que delega por canal, WhatsApp cada `WA_CAMPAIGN_TICK_SECONDS` y voz cada `CALL_CAMPAIGN_TICK_SECONDS` (2 s). Activa las `scheduled` y cierra las vencidas (`roll_schedule`), respeta horario y días, y toma `min(concurrency − en curso, crédito de rate_per_minute, CALL_CAMPAIGN_MAX_CONCURRENT − en curso global)` contactos `pending`/`retry` vencidos con `FOR UPDATE SKIP LOCKED`. Saltea bajas de voz y archivados, y llama a `start_call` con `campaign_contact_id` y `vars`.
  - **Tier y fallas:** sin lugar por concurrencia el contacto vuelve a `pending` sin gastar el intento y la campaña espera 10 s; sin minutos, tope de llamadas, cliente inactivo, agente archivado o número de origen suspendido, vuelve a `pending` y la campaña se pausa con el motivo; un teléfono inválido deja ese contacto `failed` (`invalid`); un despacho caído, un intento `failed`. `CALL_CAMPAIGN_FAILURE_STREAK` (10) intentos `failed` seguidos pausan la campaña.
  - **Worker:** `ringing_timeout` (`CALL_RINGING_TIMEOUT_SECONDS`, 30 s) en todo saliente; el error de `create_sip_participant` se clasifica por `sip_status_code` según la tabla de la sección 5 y se guarda en `call_logs.sip_status`. La lógica de cierre vive en `services/campaign_calls.py` (`close_contact`, `close_attempt`): `answered` → `done`; el resultado en `retry_on` con intentos que sobran → `retry` a los `retry_minutes`; si no, `done` (no atendió tras los reintentos, o `rejected`) o `failed` (`invalid`, `failed`). Sin nada pendiente, en vuelo ni por reintentar, la campaña pasa a `done`.
  - **Recuperación:** al arrancar `app` (y cada 60 s, sin tocar lo reclamado hace menos de 2 min) los `in_progress` sin llamada activa vuelven a `retry`; si el dialer ni llegó a llamar, el intento no se cuenta.
  - **Polling:** `GET /campaigns/{id}` suma `goal` en voz (atendidas cuya conversación cumplió el objetivo del agente; solo en el detalle, la lista lo deja en null). El resto (`results` de voz, `minutes_used`, `percent`, `eta_minutes` de los últimos 15 min, `in_window`) venía de la fase 1.
  - **Desvíos:** `vars` viaja en `CallRequest` pero la conversación todavía no lo usa (apertura con `{{var}}` y campos precargados: fase 3). `rejected` queda `done` (el contacto la rechazó, no es una falla). El contestador (`voicemail`) y el seguimiento por WhatsApp siguen en la fase 4. **Falta probar con números propios** qué códigos SIP devuelve Anura y si Asterisk los pasa sin cambiar (sección 5).
- **Fase 3, backend: variables y reportes (19-oct-2026, sin desplegar):**
  - **Variables en la conversación** (`app/conversation/contact.py`): el dialer pasa `vars` a `start_call` y `prepare_call` se las da a `engine.new_conversation(..., contact=vars)`.
    - La apertura reemplaza `{{variable}}` (sin importar mayúsculas ni acentos). Una variable que el contacto no tiene queda **vacía** y el texto se acomoda ("Hola {{nombre}}, soy..." → "Hola, soy..."), para que no se lea "{{deuda}}" en voz alta. Solo se reemplaza en llamadas de campaña (`contact` distinto de `None`): en una entrante o una de prueba el texto no se toca.
    - Los datos que se llaman como un campo del workflow lo precargan en `state.fields` (el valor tiene que pasar la validación del tipo; si no, queda como dato del contacto) y la apertura pregunta por el primer campo que falta. El resto va al prompt como "Datos del contacto".
    - Los datos viajan con la conversación, sin columna nueva: `progress.contact` (el resto) y `progress.preloaded` (los campos cargados). **Classic**: bloques "DATOS DEL CONTACTO" y "DATOS YA CONOCIDOS" en el prompt de sistema (fijos en la conversación). **Structured**: el bloque va en el prompt del turno, antes de la conversación; lo precargado ya está en `known_fields`. **Assistant**: bloque en el prompt de sistema. (26-oct-2026: un solo motor; quedan los bloques del prompt de sistema, ver [`LIMPIEZA_PLAN.md`](LIMPIEZA_PLAN.md).)
  - **`GET /campaigns/{id}/report.csv`**: una fila por contacto, para voz y WhatsApp (UTF-8 con BOM; las celdas que Excel tomaría por fórmula llevan `'` adelante). Columnas fijas: `external_id, telefono, nombre, vars, estado, resultado, intentos, ultimo_intento, duracion_segundos, outcome, objetivo, campos, seguimiento, error, conversation_id, link`; `vars` y `campos` (lo capturado) van como JSON en una celda. La duración es la del último intento (voz); el link es `APP_URL/calls/<id>`.
  - **`GET /campaigns/{id}/stats`**: `attempts` (llamadas con reintentos, o envíos), `reached` (atendidas, o respondieron), `contact_rate`, `goal` y `goal_rate` (objetivo sobre atendidas), `avg_duration_seconds`, `minutes`, `results` y `by_hour` (las 24 horas locales con llamadas y atendidas). En WhatsApp no hay duración ni minutos.
  - **`campaign_id`** en `CallFilter` y en `GET /calls`, `/stats` y `/stats/daily`: los intentos de voz (`call_logs.campaign_contact_id`) y las conversaciones que abrió la respuesta de un contacto de WhatsApp (`campaign_contacts.conversation_id`).
  - **Desvíos:** las variables de las respuestas de WhatsApp a una campaña siguen yendo solo en los parámetros de la plantilla (la conversación no recibe los datos del contacto); falta la pantalla de Contactos y de reportes en `web/`.
- **Fase 4, backend: integración (19-oct-2026, sin desplegar):**
  - **Contestador** (`app/campaigns/voicemail.py`, sección 5): lista de frases ("deje su mensaje", "buzón", "después de la señal", "no está disponible"...) sobre lo que transcribe el STT. `VoicemailDetector` mira las primeras 4 transcripciones finales del cliente, juntas (el saludo de un buzón llega en pedazos); el worker lo conecta a `user_input_transcribed` y, si matchea, cierra el intento como `voicemail` (se reintenta según `retry_on`, que ya lo trae por default), interrumpe y corta. **Límite:** es una lista de frases, no un detector de audio: un humano que dice "no está disponible" en su primer turno se toma por buzón. Medir cuánto pasa antes de pasar a AMD real.
  - **Feriados**: `CAMPAIGN_HOLIDAYS` (fechas `YYYY-MM-DD` separadas por coma, hora de `BILLING_TIMEZONE`). `in_window` de las campañas de voz los cuenta como fuera de horario (el dialer no marca y la API informa `in_window=false`); las de WhatsApp no los miran.
  - **Finalidad** (`purpose`: comercial, cobranza, turnos, aviso, en el alta y en PATCH): una campaña `comercial` se inicia (`start`, `resume` o `start:true` del alta) solo con `no_call_registry_checked: true` (cuerpo opcional de `/start` y `/resume`); sin eso, 422 `no_call_confirmation_required`. Se guarda cuándo se confirmó (`campaigns.no_call_confirmed_at`, `registry_confirmed` en la API) y no se vuelve a pedir al retomar. Cambiar el `purpose` pide la campaña pausada y borra la confirmación. Rige también para WhatsApp.
  - **Baja por voz**: `Outcome.no_contact` (bandera del resultado en la definición del agente; en la UI, "No volver a llamar" en el editor del resultado). Al cerrar una llamada de campaña, si la conversación terminó en un resultado marcado, el teléfono entra en `contact_optouts` (canal `voice`, source `outcome`) y ninguna campaña de voz del cliente lo vuelve a marcar (`campaign_calls.apply_outcome_optout`, desde `finalize` del worker). WhatsApp sigue habilitado.
  - **Seguimiento por WhatsApp** (sección 6): `followup` en el alta/PATCH de una campaña de voz: `{after, account_id, template_name, template_language, params, agent_id}`. Valida el plan (`campaign_followup`), la cuenta (del cliente, conectada), la plantilla aprobada en Meta y que `params` (el dato del contacto de cada `{{n}}`) la complete; se guarda una copia del cuerpo. Al iniciar o retomar se revalida (plan, cuenta, plantilla). Al cerrar el último intento con un resultado de `after` el contacto queda con `followup_status=pending`; lo manda el `CampaignSender` con el ritmo, el horario y los días de la campaña de voz, mientras está en curso o terminada (no pausada ni cancelada; cancelar o `ends_at` saltean los pendientes). Se saltea, con el motivo en `followup_error`, a los fijos, a los de baja de WhatsApp, a los archivados y a los que no completan las variables. Un problema de Meta o de la cuenta frena los seguimientos (1 o 10 min) sin pausar la campaña de voz. La respuesta abre la conversación con la plantilla como apertura, con `followup.agent_id` o el agente de la campaña (`reply_target`: gana la plantilla más reciente entre una campaña de WhatsApp y un seguimiento); queda en `followup_conversation_id` (la del último intento de llamada sigue en `conversation_id`) y en `replied_at`. El polling devuelve `followup: {pending, sent, replied, failed, skipped}` y el reporte, `seguimiento` (incluye `replied`).
  - **Webhook** (sección 8): `callback_url` y `callback_secret` en el alta/PATCH, para los dos canales. Eventos `contact.finished` (contacto terminado: llamada cerrada sin reintento pendiente, envío de WhatsApp, o salteado por baja o archivado), `contact.followup` (el seguimiento se mandó, falló o se salteó) y `campaign.finished` (`done` o `cancelled`; al cancelar en bloque no hay un evento por contacto). Van a una cola (`campaign_callbacks`, en la misma transacción) y una tarea aparte (`callback_loop`, `app/campaigns/callbacks.py`) los entrega: POST JSON con `X-Atentina-Event`, `X-Atentina-Delivery` (el mismo en los reintentos) y `X-Atentina-Signature: sha256=<HMAC-SHA256 del cuerpo>`; el cuerpo trae `campaign` y, por contacto, los campos del reporte (`contact`) o, al terminar, `progress` y `stats`. 2xx es éxito; si no, reintenta a los 30 s, 2 min, 10 min, 1 h y 6 h (`CAMPAIGN_CALLBACK_MAX_ATTEMPTS`, 6 intentos) y queda `failed`. Un evento reclamado queda fuera de la cola 2 min (dos copias de `app` no lo entregan juntas). El secreto va cifrado con `WA_TOKEN_KEY`; si el cliente no manda uno se genera y se muestra una sola vez (`callback_secret` de esa respuesta). **SSRF:** la URL tiene que ser https y de un host público (no loopback, privado ni link-local); al entregar se resuelve el host, se exige una IP pública y se conecta a esa IP con el SNI y el `Host` originales (un DNS que cambia no sirve); sin redirecciones. `CAMPAIGN_CALLBACK_ALLOW_PRIVATE=true` (solo desarrollo) lo relaja.
  - **Migración**: la `0017` suma `campaigns.no_call_confirmed_at`, `campaign_contacts.followup_{sent_at,error,conversation_id}` (con CHECK e índice de `followup_status`) y la tabla `campaign_callbacks`. Misma regla que antes: probada ida y vuelta en SQLite, falta una copia del backup en PostgreSQL.
  - **Falta**: regenerar OpenAPI y `web/src/api/schema.d.ts`; en la UI, el alta de campañas de voz (finalidad con la confirmación, seguimiento, webhook); limpiar la cola `campaign_callbacks` (los `sent` viejos); probar el contestador con llamadas reales (cuántos buzones atrapa y cuántos humanos confunde); apagar un webhook de una campaña ya terminada (hoy PATCH da 409).
- **Fase 3, frontend (19-oct-2026, sin desplegar; falta `npm run build` para que `web/dist` lo sirva):**
  - **Contactos** (`web/src/features/contacts/`, `/contacts` y `/contacts/:id`, en el menú de admin y de cliente): tabla con búsqueda y filtro Activos / Archivados / Todos; alta y edición con nombre, email, ID externo y nota; importar CSV con vista previa de columnas (las mismas reglas de `parse_csv`) y resultado (creados, actualizados, archivados e inválidos con fila y motivo); archivar y desarchivar uno o en lote (por selección), sin botón de borrar; ficha con sus campañas. El desarchivado en lote llama de a uno a `/contacts/{id}/unarchive`.
  - **Campañas** (`features/campaigns/`): ahora sobre `/api/v1/campaigns`. Lista con filtro por canal; "Nueva campaña" elige WhatsApp o llamadas y deshabilita con el motivo lo que el plan no incluye. Alta de llamadas (`VoiceCampaignModal`): agente, número de origen, voz, finalidad con la confirmación del Registro No Llame, destinatarios por etiquetas / contactos elegidos / CSV, horario, días e inicio y fin programados (en la hora de la campaña), modo de a una o en paralelo hasta el tope del plan, reintentos, seguimiento por WhatsApp y webhook (el secreto generado se muestra una vez). Detalle: barra de avance y ritmo, tarjetas por resultado, indicadores y atendidas por hora, seguimiento, tabla de contactos con filtro y link a la conversación, iniciar / retomar / pausar / cancelar, descarga de `report.csv` y polling cada 5 s mientras corre o espera su hora.
  - **Tiers**: canales, topes de campañas, contactos de la agenda y seguimiento en el formulario y en la tabla; los cuatro numéricos también en los ajustes por cliente (`LIMIT_META`). La pantalla Plan lista las campañas del plan.
  - **Conversaciones y Estadísticas**: filtro por campaña (`campaign_id`).
  - **Backend sumado para la UI**: `GET /campaigns/plan` (lo que el plan permite y lo usado: un cliente no puede leer `/clients/{id}/limits`), `GET /contacts/{id}/campaigns` (ficha del contacto) y los campos de campañas en `PlanOut`.
  - **Desvíos**: el alta de WhatsApp y su CSV posicional ({{1}}, {{2}}...) siguen por el alias `/whatsapp/campaigns` (el CSV de `/campaigns` usa el formato de la agenda); las campañas de WhatsApp con variables sin `param_names` solo reciben el CSV posicional. Editar una campaña no cambia el seguimiento ni los destinatarios. `has_whatsapp` no se muestra: no rechaza nada todavía.
