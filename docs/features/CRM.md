# CRM de ventas

CRM interno y local de Atentina: leads (empresas) con personas, contactos y fuentes, campañas y plantillas,
envío y recepción de mails por Resend, visitas de Google Analytics y recordatorios en Google Calendar. Lo usan el
usuario (UI) y el agente `ventas` (API, contrato en [`CRM_API.md`](CRM_API.md)). Estado: en producción desde el
21-oct-2026. No es parte del producto: no tiene tiers ni clientes.

## Arquitectura

- Servicio `crm` de `docker-compose.yml` (misma imagen que `app`, `uvicorn crm.main:app`), en
  `127.0.0.1:8030`, sin túnel ni regla en el router. Base `crm` en el mismo contenedor `db`, con migraciones propias
  (`crm/migrations/`, `crm/alembic.ini`).
- Separado de `app` a propósito: `app` es multi-cliente y público en `app.atentina.com.ar`; el CRM no hereda su CSP,
  tiers ni auth y se puede borrar sin tocar el producto.
- Un proceso: API, UI y cinco loops asyncio idempotentes: `send_loop` y `events_loop` (`crm/services/sending.py`),
  `inbound_loop` (`inbound.py`), `ga_loop` (`ga.py`) y `gcal_loop` (`gcal.py`). Estado chico de los loops en la
  tabla `kv`. `CRM_LOOPS=false` los apaga (tests).
- Código: `crm/main.py`, `config.py` (variables `CRM_*` en `.env`), `auth.py`, `models.py`, `schemas.py`,
  `routes/{leads,outreach,reminders}.py`, `services/{leads,templates,messages,sending,resend,inbound,ga,gcal,reminders}.py`.
  UI en `web/src/crm/` (entrada `web/crm.html`, build de `web/`, la sirve `crm`). Tests en `tests/test_crm*.py`.
- Auth: `Authorization: Bearer`. `CRM_API_KEY` (usuario y UI, que la pide una vez y la guarda en el navegador;
  `make crm-key` la muestra) y `CRM_AGENT_API_KEY` (agentes: no aprueban envíos, no cargan historial, no borran,
  no sincronizan GA). Así "el agente no envía" queda en el servidor.

## Modelo de datos

| Tabla | Campos clave | Notas |
|---|---|---|
| `leads` | `slug` (= `utm_content`, único), `name`, `domain` (único, clave de dedupe), `website`, `description`, `kind` (`cliente`/`canal`), `industry`, `tags`, ubicación, `stage`, `stage_changed_at`, `next_action`, `next_action_at`, `do_not_contact`, `notes`, `legacy_ref`, `created_by` | Una fila por empresa |
| `people` | `lead_id`, `name`, `title`, `is_decision_maker`, `linkedin_url`, `source_id` | |
| `contact_points` | `lead_id`, `person_id` (nulo = de la empresa), `kind` (`email`/`phone`/`whatsapp`/`linkedin`/`form`), `value` normalizado, `label`, `is_primary` (★), `status` (`ok`/`bounced`/`suppressed`/`unverified`), `source_id` | Único por (`kind`, `value`) |
| `sources` | `lead_id`, `url`, `title`, `seen_at`, `note` | De dónde salió cada dato (solo datos publicados) |
| `blocklist` | `value` (email o dominio), `reason` (`bounce`/`complaint`/`opt_out`/`manual`) | El envío la consulta siempre |
| `campaigns` | `slug` (= `utm_campaign`), `name`, `channel`, `segment`, `from_addr`, `status` (`draft`/`active`/`done`), `sequence` (JSON: pasos de seguimiento) | Cada tanda es una campaña |
| `templates` | `name`, `kind` (`first`/`follow_up`/`other`), `subject`, `body` (a "ustedes"), `body_personal` (tuteo), `archived` | Variables `{{saludo}}`, `{{nombre}}`, `{{empresa}}`, `{{link}}`; falta una → error |
| `messages` | `lead_id`, `campaign_id`, `template_id`, `kind`, `step` (0 el primero), `direction` (`out`/`in`), `status` (`draft`/`queued`/`sent`/`delivered`/`bounced`/`complained`/`failed`/`canceled`/`received`), `resend_id`, `message_id`, `in_reply_to`, `utm_*`, `analysis` (JSON de la clasificación), `error` | Saliente y entrante juntos; guarda el texto final (cambiar la plantilla no reescribe lo enviado) |
| `activities` | `lead_id`, `person_id`, `kind` (`note`/`call`/`meeting`/`linkedin`/`stage_change`/`task`), `at`, `text`, `data`, `done` | Línea de tiempo y tareas |
| `reminders` | `lead_id`, `person_id`, `kind` (`reminder`/`meeting`), `title`, `starts_at`, `duration_min`, `location`, `status` (`pending`/`done`/`no_show`/`canceled`), `outcome`, `gcal_event_id`, `gcal_state`, `gcal_error` | Migración 0006 |
| `ga_visits` | (`date`, `source_medium`, `utm_campaign`, `utm_content`) único, `active_users`, `sessions`, `events`, `lead_id`, `campaign_id` | `lead_id` nulo = sin match |
| `inbound_emails` | `resend_id` (único), remitente, asunto, texto, `headers`, `received_at`, `status` (`assigned`/`unassigned`/`ignored`), `reason`, `lead_id`, `message_id` | Migración 0005 |

**Etapas** (`leads.stage`): `nuevo` → `contactado` → `seguimiento` → `respondio` → `charla_agendada` →
`charla_hecha` → `propuesta` → `piloto` → `cliente`; cierres `sin_respuesta`, `no_interesa`, `descartado`.

| Evento automático (queda como `activity` `stage_change`) | Etapa |
|---|---|
| Sale el primer mail de una campaña | `nuevo` → `contactado` |
| Sale un paso posterior | → `seguimiento` |
| Llega o se registra una respuesta | → `respondio` y se cancela lo pendiente |
| Rebota el único email del lead | → `descartado`; el email va a `blocklist` |

Las demás etapas son a mano (UI o API).

## Envío (cola de Resend)

1. Los borradores salen de una plantilla para varios leads de una campaña (`POST /api/campaigns/{id}/drafts`), de un
   mail suelto o de los seguimientos que vencen (`POST /api/followups/drafts`). Con campaña `active` y paso con
   plantilla, `events_loop` arma solo los borradores de seguimiento. **Todo mail es borrador hasta que el usuario
   lo aprueba** (UI: Leads, filtro Pendiente, o `POST /api/messages/approve`); pasa a `queued`.
2. `send_loop` manda **un `queued` por ventana** (`CRM_SEND_WINDOW_SECONDS`, 120) en un momento al azar, con al
   menos `CRM_SEND_MIN_GAP_SECONDS` (30) entre dos, solo en `CRM_SEND_HOURS` (9–18, lunes a viernes,
   `America/Argentina/Buenos_Aires`) y hasta `CRM_SEND_DAILY_MAX` (50) por día. Antes de cada uno revisa blocklist,
   `do_not_contact` y que el lead no haya respondido. `CRM_SEND_ENABLED=false` frena la cola.
3. `POST /emails` de Resend con `Idempotency-Key` = id del mensaje, `In-Reply-To`/`References` del último mensaje
   del hilo (el seguimiento cae en el mismo hilo), `bcc` a `CRM_MAIL_BCC` (el hilo queda en Gmail: lo que sale por
   API no aparece en "Enviados") y texto + HTML. Remitente por campaña; default `CRM_MAIL_FROM`
   (`laureano@atentina.net`, dominio verificado en Resend).
4. `events_loop` (cada `CRM_EVENTS_INTERVAL_SECONDS`, 600) lee `GET /emails/{id}` de lo enviado en los últimos
   `CRM_EVENTS_DAYS` (14): entregas, rebotes y quejas, sin webhook. `POST /api/events/check` lo corre ya.

`CRM_RESEND_API_KEY` es de acceso completo (lee eventos y recibidos); la de `app` sigue siendo de solo envío. Los
links llevan UTM (`utm_source=email`, `utm_campaign` = campaña, `utm_content` = slug del lead), armados por
`services/templates.py` sobre `CRM_SITE_URL`.

## Entrante

`laureano@atentina.com.ar` y `.net` tienen MX en Cloudflare Email Routing. Cada casilla tiene una regla con el
**Email Worker** `deploy/crm-email-worker.js`, que hace dos `forward()`: a Gmail y a `crm@in.atentina.net`. El
subdominio `in.atentina.net` tiene Resend Receiving (MX solo en el subdominio). `inbound_loop` lee
`GET /emails/receiving` cada `CRM_INBOUND_INTERVAL_SECONDS` (120) con `CRM_INBOUND_ENABLED=true` (sin webhook).

- **Ignora** lo de `CRM_OWN_DOMAINS` (copias BCC) y los rebotes (los ve `events_loop`).
- **Asocia** por hilo (`In-Reply-To`/`References` contra `messages.message_id`), si no por remitente y si no por
  dominio (salvo correo gratuito). Sin lead queda en "Respuestas sin asignar" del Tablero
  (`POST /api/inbox/{id}/assign` o `/ignore`).
- **Clasifica** con el LLM local (`CRM_LLM_URL`, default `vllm-llm`; modelo y key de `VLLM_*`) solo lo que escribió,
  sin lo citado: intención, resumen, próxima acción, fecha y persona derivada. JSON pedido en el prompt, no salida
  guiada: con guided decoding Gemma se colgaba en espacios en 3 de 5; así, 8 de 9 bien en 0,5–0,9 s. La etapa la
  decide el código:

| Intención | Qué cambia (además de mensaje `in`, `respondio` y lo pendiente cancelado) |
|---|---|
| interesado, agendar, pide info | Próxima acción y fecha (la propuesta u hoy); con `CRM_REMINDERS_FROM_REPLIES`, recordatorio |
| derivado | Lo mismo, y la persona y su email como contacto nuevo |
| más adelante | Próxima acción a la fecha que digan, o en 90 días |
| no interesa | `no_interesa` |
| baja | `no_interesa`, `do_not_contact` y el email a la blocklist (`opt_out`) |
| autorespuesta | Nada (ni etapa ni cancelación); si dice hasta cuándo, próxima acción ese día |

- LLM caído, confianza < `CRM_LLM_MIN_CONFIDENCE` (0,7) u "otro": solo `respondio`, marcado "Sin analizar" o
  "Revisar". Todo queda en `messages.analysis` y en una nota de la línea de tiempo.
- Aviso por mail a `CRM_NOTIFY_TO` de cada respuesta (no autorespuestas) y de cada una sin asignar, directo por
  Resend (fuera de la cola). Nunca contesta solo.
- Una respuesta también se puede registrar a mano: `POST /api/leads/{id}/inbound`.
- Los recibidos cuentan en el cupo del plan de Resend igual que los enviados.

## Google Analytics

Cuenta de servicio con "Google Analytics Data API", Lector en la propiedad: `CRM_GA_PROPERTY_ID` y
`CRM_GA_CREDENTIALS` (`/app/secrets/ga.json`, montado desde `secrets/`, no versionado).

- `ga_loop` una vez por día (`CRM_GA_INTERVAL_SECONDS`) baja los últimos 3 días (GA consolida tarde) con `date`,
  `sessionSourceMedium`, `sessionCampaignName`, `sessionManualAdContent` → `ga_visits`. A pedido:
  `POST /api/ga/sync`. Histórico a mano: `POST /api/ga/visits`.
- Match: `utm_content` → `leads.slug`; `utm_campaign` → `campaigns.slug` (`follow_up_<x>` → campaña `<x>`, paso
  de seguimiento). En la ficha, visitas por día y por mail; en la lista, filtro "hizo clic y no respondió".
- **Sitio web** (`GET /api/ga/site?days=`): tráfico de todo el sitio filtrado a `CRM_GA_COUNTRY` (Argentina), con
  `batchRunReports` y 10 min de caché (`refresh=true` la saltea). El filtro es necesario: en 28 días, 122 usuarios
  de Argentina de 469 (271 de EE.UU., casi todo robots).
- **Desglose** (`GET /api/ga/site/detail`): por canal, fuente/medio, página, ciudad o dispositivo, las empresas que
  entraron por un link de los mails y las sesiones por día. GA no da visitantes sueltos; entran 7 dimensiones (tope
  9 con los dos filtros). Links con `&amp;` en la URL (GA no los atribuye): el lead y la campaña salen de la URL de
  entrada.

## Recordatorios y reuniones (Google Calendar)

Tabla `reminders`. El calendario "Atentina" del usuario (`CRM_GCAL_CALENDAR_ID`) está compartido con la cuenta de
servicio de GA ("Hacer cambios en los eventos"; `CRM_GCAL_CREDENTIALS` vacío usa la de GA). Sin Google Workspace no
puede invitar al lead: el evento es solo del usuario. Cada cambio se sube al guardar; si Calendar falla,
`gcal_loop` reintenta cada minuto y el recordatorio vale igual en el CRM (`POST /api/reminders/sync` lo fuerza).
Con solo fecha, a las `CRM_REMINDER_HOUR` (10).

## UI

Interna, solo claro, con `web/src/theme.ts` y `web/src/components/` ([`DESIGN_GUIDELINE_APP.md`](../DESIGN_GUIDELINE_APP.md)).

| Pantalla | Qué muestra |
|---|---|
| Tablero (`StatsPage`) | Resumen, Hoy (seguimientos que vencen, borradores para aprobar, tareas, respuestas, próximas acciones vencidas, cola), respuestas sin asignar, Agenda (vencidos, hoy, 7 días) |
| Leads / ficha | Filtros (etapa, campaña, tags, industria, con clics, sin respuesta, Pendiente), acciones en lote; ficha con personas, contactos (★, estado, fuente), línea de tiempo, Agenda, redactar |
| Campañas | Números por campaña, mensajes por estado, editor de la secuencia |
| Plantillas | Editor con variables y vista previa con un lead |
| Mensajes | Todos los mails por estado, dirección y campaña |
| Sitio web | Tráfico de GA y desglose |

## Desplegar y probar

- `make crm-up`: crea la base si falta (`crm-db`), corre las migraciones (`crm-migrate`) y levanta `crm` sin tocar
  `app` ni `agent`. Otros: `make crm-key`, `make crm-logs`, `make crm-psql`.
- `make test` incluye `tests/test_crm.py` y `tests/test_crm_inbound.py` (sin servicios reales).
- Backup: `scripts/ops/backup.sh` vuelca la base `crm` si existe (`db/crm-<fecha>.sql.gz`).
- El Email Worker (`deploy/crm-email-worker.js`) se publica en Cloudflare a mano; si se pierde, el plan B es un
  filtro de Gmail que reenvía a `crm@in.atentina.net`.

## Reglas y trampas

- **Entregabilidad:** dominio nuevo. No subir el ritmo de la cola (~30 por hora como máximo, tope 50 por día) sin
  mirar rebotes y quejas por semana en el Tablero.
- Las campañas cargadas por la importación inicial quedaron en `done`: para que armen solos los borradores, pasar
  la campaña a `active`.
- El match de GA depende de que cada link tenga UTM; los mails sin UTM no matchean. Lo sin match:
  `GET /api/ga/visits?unmatched=true`.

## Pendientes

- **Pie de baja (Ley 25.326 y anti-spam):** ninguna de las 18 plantillas (9 activas) tiene la línea para pedir la
  baja ("si no querés más mails, respondé 'baja'"). La respuesta "baja" ya se procesa (blocklist `opt_out`); falta
  definir el texto y sumarlo a las plantillas.
