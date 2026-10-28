# API del CRM (contrato para agentes)

CRM de ventas de Atentina ([`CRM.md`](CRM.md)). Local: `http://127.0.0.1:8030`. OpenAPI
completo en `/api/docs` y `/api/openapi.json`; acá, lo que un agente necesita para trabajar.

## Reglas

- **Auth:** `Authorization: Bearer $CRM_AGENT_API_KEY` (agentes) o `$CRM_API_KEY` (el usuario).
  La key de agente **no puede aprobar envíos, cargar historial, borrar ni sincronizar GA**: devuelve 403.
  El agente deja borradores; el usuario los aprueba en la UI y salen por la cola.
- **JSON** en todo. Fechas ISO 8601 (`2026-10-21`, `2026-10-21T10:00:00-03:00`); las respuestas van en UTC sin zona.
- **Errores:** `application/problem+json` con `status`, `title`, `detail` y, si aplica, `field` o
  `errors: [{field, msg}]`. 401 sin key, 403 no permitido, 404 no existe, 409 conflicto (duplicado,
  blocklist, no contactar), 422 datos inválidos. Leer `detail`: dice qué corregir.
- **Solo datos publicados:** con la key de agente, todo email, teléfono o WhatsApp lleva `source_url`
  (la página donde figura). Sin eso, 422.
- **Listas:** `?limit=` (≤500) y `?offset=`; responden `{total, items}`.

## Modelo en una línea

Un **lead** es una empresa (único por dominio) con **personas** (directivos), **contactos** (emails,
teléfonos, WhatsApp, LinkedIn, formulario; uno marcado `is_primary`, el ★) y **fuentes**. Tiene una
**etapa**: `nuevo`, `contactado`, `seguimiento`, `respondio`, `charla_agendada`, `charla_hecha`,
`propuesta`, `piloto`, `cliente`, `sin_respuesta`, `no_interesa`, `descartado`. Una **campaña** es una
tanda (su `slug` es el `utm_campaign` de los links); una **plantilla** es el texto con variables; un
**mensaje** es un mail (borrador → cola → enviado, o recibido); la **actividad** es la línea de tiempo
(notas, llamadas, charlas, LinkedIn, tareas).

Etapas automáticas: sale el primer mail → `contactado`; sale el seguimiento → `seguimiento`; se registra
una respuesta → `respondio` (y se cancela lo pendiente); rebota el único email → `descartado`. Las demás,
a mano (`PATCH`).

## Tareas

Las variables del shell: `K=$CRM_AGENT_API_KEY`, `U=http://127.0.0.1:8030/api`.

### 1. ¿Ya lo tenemos? (antes de investigar una empresa)

```bash
curl -s -H "Authorization: Bearer $K" "$U/leads/check?domain=empresa.com.ar&email=info@empresa.com.ar"
# {"lead": {"id": 12, "name": "Empresa SA", "stage": "contactado"} | null, "blocked": "bounce" | null}
```

### 2. Cargar o completar un lead

`POST /leads` crea o actualiza: busca por dominio (de `domain` o `website`). Suma personas, contactos y
fuentes sin borrar los existentes. Responde 201 `{"result": "created", "lead": {...}}` o 200 `updated`.

```bash
curl -s -X POST -H "Authorization: Bearer $K" -H "Content-Type: application/json" "$U/leads" -d '{
  "name": "Empresa SA",
  "website": "https://www.empresa.com.ar",
  "description": "Software de gestión para mutuales, Córdoba",
  "kind": "canal",
  "industry": "software",
  "tags": ["mutuales", "córdoba"],
  "province": "Córdoba", "city": "Córdoba",
  "notes": "Gancho: tienen app de autogestión para asociados (sitio, /productos)",
  "sources": [{"url": "https://www.empresa.com.ar/nosotros", "seen_at": "2026-10-21"}],
  "people": [{"name": "Pablo Pérez", "title": "Socio gerente", "is_decision_maker": true,
              "linkedin_url": "https://www.linkedin.com/in/pabloperez/",
              "source_url": "https://www.empresa.com.ar/nosotros", "source_seen_at": "2026-10-21"}],
  "contacts": [
    {"kind": "email", "value": "pablo@empresa.com.ar", "label": "persona", "person": "Pablo Pérez",
     "is_primary": true, "source_url": "https://www.empresa.com.ar/nosotros", "source_seen_at": "2026-10-21"},
    {"kind": "email", "value": "info@empresa.com.ar", "label": "atencion",
     "source_url": "https://www.empresa.com.ar/contacto"},
    {"kind": "whatsapp", "value": "+54 9 351 555-1234", "source_url": "https://www.empresa.com.ar/contacto"}
  ]
}'
```

- `label`: `persona` (de alguien con nombre), `area` (`comercial@`, `gerencia@`), `atencion` (`info@`).
- `is_primary` marca el ★: el destinatario. Se elige en este orden: (1) la persona que decide sobre lo que tocamos
  (atención, cobranza, comercial, sistemas) o el número uno, con fuente de 2024 en adelante; (2) otra persona
  directiva con fuente reciente, o la del punto 1 con fuente vieja; (3) una casilla de área de atención, cobranza o
  comercial; (4) la de atención. Si el mail ya salió a otra dirección, el ★ es a quién sumar en el seguimiento
  (mismo hilo). No se cargan emails de recursos humanos, búsquedas laborales ni sucursales sueltas.
- `slug` (el `utm_content`) sale del nombre si no se pasa.
- Un email que está en la blocklist se guarda con `status: "bounced"` y no se usa para enviar.

Para sumar una cosa suelta: `POST /leads/{id}/contacts`, `/leads/{id}/people`, `/leads/{id}/sources`.

### 3. Buscar leads

```bash
curl -s -H "Authorization: Bearer $K" "$U/leads?stage=contactado,seguimiento&has_clicks=true"
```

Filtros: `q` (nombre, dominio, email, rubro o `#` viejo), `stage` (varias con coma), `tag`, `industry`,
`kind`, `campaign_id`, `has_clicks`, `next_action_due` y `pending` (`draft`: con borrador, `queued`: en
cola, `follow_up`: le toca seguimiento). Cada item trae `primary_email`, `last_out_at`, `last_in_at`,
`ga_users`, `draft_ids`, `queued` y `follow_up_step`. El detalle (`GET /leads/{id}`) suma `people`, `contacts` y `sources`, y
`GET /leads/{id}/timeline` da mails, actividad y visitas de GA en orden.

### 4. Armar una tanda (borradores)

```bash
# Campaña (slug = utm_campaign, único)
curl -s -X POST -H "Authorization: Bearer $K" -H "Content-Type: application/json" "$U/campaigns" \
  -d '{"slug": "mutuales7", "name": "Mutuales de Córdoba, tanda 7", "segment": "Mutuales con app", "started_at": "2026-10-22"}'

# Plantilla: {{saludo}} ("Hola, Pablo:" o "Hola:"), {{nombre}}, {{empresa}}, {{link}} (el sitio con UTM).
# body va a "ustedes"; body_personal (opcional) tutea cuando el ★ es una persona con nombre.
curl -s -X POST -H "Authorization: Bearer $K" -H "Content-Type: application/json" "$U/templates" -d '{
  "name": "Mutuales 7 - primer mail", "kind": "first", "subject": "IA aplicada a {{empresa}}",
  "body": "{{saludo}}\n\n...\n\n{{link}}\n\n¿Qué llamadas hacen hoy a mano?\n\nSaludos,\nLaureano",
  "body_personal": "{{saludo}}\n\n...\n\n{{link}}\n\n¿Qué llamadas hacen hoy a mano?\n\nSaludos,\nLaureano"}'

# Ver cómo queda para un lead
curl -s -X POST -H "Authorization: Bearer $K" -H "Content-Type: application/json" "$U/templates/3/preview" \
  -d '{"lead_id": 12, "campaign_id": 5}'

# Borradores para varios leads: los que no pueden van en skipped con el motivo
curl -s -X POST -H "Authorization: Bearer $K" -H "Content-Type: application/json" "$U/campaigns/5/drafts" \
  -d '{"lead_ids": [12, 13, 14], "template_id": 3, "kind": "first"}'
# {"created": [{"id": 101, "to_addr": "pablo@empresa.com.ar", "subject": "...", "status": "draft"}, ...],
#  "skipped": [{"lead_id": 14, "reason": "info@x.com: en la blocklist"}]}
```

Un borrador suelto (texto propio): `POST /messages` con `lead_id`, `campaign_id`, `kind`, y
`template_id` o `subject` + `text`. Se edita con `PATCH /messages/{id}` mientras es borrador y se
descarta con `POST /messages/{id}/cancel`, o varios con `POST /messages/cancel {"ids": [...]}` (todos o
ninguno; en la UI, Leads → "Descartar borradores").

### 5. Seguimientos y secuencias

Cada campaña tiene una **secuencia** de seguimientos: `sequence: [{"days": 4, "template_id": 7},
{"days": 5, "template_id": 8}]` (en `POST`/`PATCH /campaigns`). Cada paso toca `days` días hábiles
después del **último** mail enviado al lead, si no respondió y no tiene nada pendiente de salir. Sin
secuencia: un solo seguimiento a los 4 días hábiles, sin plantilla. Un lead en etapa `seguimiento` sin
ninguno registrado cuenta como que ya tuvo uno (se mandó por fuera del CRM).

`GET /today` → `follow_ups_due`: a quién le toca, con `step` (1, 2, ...) y `template_id` del paso.
`POST /followups/drafts {"lead_ids": [...], "template_id": null}` arma el borrador del paso de cada uno
(con la plantilla del paso, o la que se pase); los que no pueden van a `skipped`. El seguimiento va
**en el hilo** del último mail (`Re: <asunto>`, `In-Reply-To`) y al mismo destinatario; el asunto de la
plantilla se ignora. Cada mensaje lleva `step` (0 el primero).

`GET /today` → `reply_rates`: por nivel (`step`, 0 el primer mail) y campaña (`campaign_slug`; `null` = todas),
`reached` (leads que lo recibieron, sin rebote), `replied` y `rate`. Respondió = mensaje entrante o etapa de
respuesta en adelante, como `replied` de `/stats`; cuenta para el último mail enviado antes de la respuesta (o del
cambio de etapa; sin fecha, el último mail).

Si el paso tiene plantilla y la campaña está **activa**, el servidor arma solo el borrador (cada 10 min,
`created_by: "sistema"`); igual queda para aprobar (en Leads, filtro Pendiente).

### 6. Registrar lo que pasa

```bash
# Respuesta del lead (pegada desde el mail): etapa -> respondio y cancela lo que estaba por salir
curl -s -X POST -H "Authorization: Bearer $K" -H "Content-Type: application/json" "$U/leads/12/inbound" \
  -d '{"from_addr": "pablo@empresa.com.ar", "subject": "Re: IA aplicada a Empresa SA", "text": "...", "at": "2026-10-22T11:05:00-03:00"}'
# Por otro canal: channel = email (default), phone, agent u other; from_addr es opcional (a veces solo el nombre)
curl -s -X POST ... "$U/leads/12/inbound" -d '{"channel": "phone", "from_addr": "Marta", "text": "Llamó, quiere una demo"}'
# Corregir una respuesta ya cargada (canal, from_addr, subject, text, at); no cambia la etapa
curl -s -X PATCH ... "$U/messages/230" -d '{"channel": "agent", "text": "Habló con el agente: pidió precios"}'

# Charla, llamada, nota, LinkedIn o tarea
curl -s -X POST -H "Authorization: Bearer $K" -H "Content-Type: application/json" "$U/leads/12/activities" \
  -d '{"kind": "meeting", "text": "Charla con Pablo: usan Twilio, quieren probar voz", "at": "2026-10-22T15:00:00-03:00"}'
curl -s -X POST ... "$U/leads/12/activities" -d '{"kind": "task", "text": "Llamar a Pablo", "due_at": "2026-10-24"}'

# Recordatorio ("llamame el lunes") o reunión: va al Google Calendar y pasa a ser la próxima acción.
# starts_at sin zona = hora de Argentina; solo fecha = a las 10. Reunión: etapa -> charla_agendada.
curl -s -X POST ... "$U/leads/12/reminders" -d '{"starts_at": "2026-10-27", "person_id": 5}'
curl -s -X POST ... "$U/leads/12/reminders" \
  -d '{"kind": "meeting", "starts_at": "2026-10-27T11:00", "duration_min": 30, "location": "https://meet.google.com/..."}'
curl -s -X PATCH ... "$U/reminders/7" -d '{"starts_at": "2026-10-28T10:00"}'          # reprogramar
curl -s -X POST ... "$U/reminders/7/done" -d '{"outcome": "Atendió: quiere la propuesta"}'   # o no_show: true
curl -s -X POST ... "$U/reminders/7/cancel"                                           # borra el evento

# Etapa y próxima acción
curl -s -X PATCH -H "Authorization: Bearer $K" -H "Content-Type: application/json" "$U/leads/12" \
  -d '{"stage": "charla_hecha", "next_action": "Mandar propuesta de piloto", "next_action_at": "2026-10-24"}'

# No mandar más: a la blocklist (email o dominio) o el lead como no contactar
curl -s -X POST ... "$U/blocklist" -d '{"value": "info@empresa.com.ar", "reason": "opt_out"}'
curl -s -X PATCH ... "$U/leads/12" -d '{"do_not_contact": true}'
```

### Respuestas recibidas por mail

Con `CRM_INBOUND_ENABLED` el CRM lee las respuestas de Resend, las asocia, las clasifica con el LLM local y
actualiza el lead solo ([`CRM.md`](CRM.md), "Entrante"). El mensaje entrante trae `analysis`
(`status`: `ok`, `low_confidence` o `error`; `intencion`, `resumen`, `applied`, `matched_by`). Las que no se
pudieron asociar: `GET /inbox` (también en `/today` → `inbox`); `POST /inbox/{id}/assign {"lead_id": 12}`
la procesa como las automáticas y `POST /inbox/{id}/ignore` la descarta.

### Recordatorios y reuniones

Cada uno es un evento en el calendario "Atentina" de Google (`CRM_GCAL_CALENDAR_ID`, compartido con la
cuenta de servicio de GA), con aviso a la hora (recordatorio) o 30 min antes (reunión), y la ficha del lead
en la descripción. La próxima acción del lead sigue al pendiente más cercano. `gcal_state`: `ok`,
`pending`, `error` (se reintenta cada minuto; `POST /reminders/sync` lo fuerza) u `off` (sin calendario).
Hecha una reunión, la etapa pasa a `charla_hecha`; lo que pasó queda en la línea de tiempo. Las respuestas
por mail con próxima acción y fecha ("llamame el lunes") crean el recordatorio solas (`created_by:
sistema`; se apaga con `CRM_REMINDERS_FROM_REPLIES=false`). `GET /reminders` (por defecto los pendientes;
`lead_id`, `until`) y `/today` → `agenda` (vencidos y próximos 7 días).

### 7. Números

`GET /stats` (por etapa, contactados, con seguimiento, respondieron, rebotes, con clics, enviados en 7
días), `GET /campaigns` (cada una con `stats`), `GET /queue` (cola: en espera, enviados hoy, tope,
horario, próximo envío), `GET /ga/visits?unmatched=true` (visitas de GA sin lead), `GET /ga/site` (tráfico
del sitio, solo de Argentina).

## Envío (lo hace el servidor)

La cola manda un mail aprobado por ventana de `CRM_SEND_WINDOW_SECONDS` (120), en un momento al azar,
con al menos 30 s entre dos, de lunes a viernes de 9 a 18 (hora argentina) y hasta `CRM_SEND_DAILY_MAX`
(50) por día. Antes de cada uno vuelve a mirar blocklist, no contactar y si el lead respondió. Rebotes y
quejas se leen de Resend cada 10 min (o ya, con `POST /events/check`, el botón "Revisar entregas y
rebotes" del Tablero; solo el usuario): el email va a la blocklist.

## Endpoints

| Método y ruta | Qué hace | Key de agente |
|---|---|---|
| `GET /leads`, `GET /leads/{id}`, `GET /leads/check` | Listar, ver, chequear duplicado y blocklist | sí |
| `POST /leads` | Crear o actualizar por dominio | sí |
| `PATCH /leads/{id}` | Datos, etapa, próxima acción, no contactar | sí |
| `DELETE /leads/{id}` | Borrar | no |
| `POST /leads/{id}/people` · `PATCH/DELETE /people/{id}` | Personas | sí |
| `POST /leads/{id}/contacts` · `PATCH/DELETE /contacts/{id}` | Contactos | sí |
| `POST /leads/{id}/sources` | Fuentes | sí |
| `GET /leads/{id}/timeline` | Mails, actividad y visitas | sí |
| `POST /leads/{id}/activities` · `GET /activities` · `PATCH /activities/{id}` | Actividad y tareas | sí |
| `POST /leads/{id}/inbound` | Registrar una respuesta | sí |
| `GET/POST /campaigns` · `GET/PATCH /campaigns/{id}` | Campañas | sí |
| `POST /campaigns/{id}/drafts` | Borradores de una plantilla para varios leads | sí |
| `POST /followups/drafts` | Borradores del seguimiento que le toca a cada lead | sí |
| `POST /events/check` | Revisar ya entregas y rebotes en Resend (en segundo plano) | no |
| `GET/POST /templates` · `PATCH /templates/{id}` · `POST /templates/{id}/preview` | Plantillas | sí |
| `GET /messages` · `POST /messages` · `PATCH /messages/{id}` · `POST /messages/{id}/cancel` · `POST /messages/cancel` | Mensajes y borradores | sí |
| `POST /messages/approve` | Aprobar borradores (a la cola) | **no** |
| `POST /messages/import` | Cargar historial | **no** |
| `GET /queue` · `GET /today` · `GET /stats` | Cola, pendientes del día, números | sí |
| `GET/POST /blocklist` · `DELETE /blocklist/{id}` | Blocklist (borrar: solo el usuario) | sí / no |
| `POST /leads/{id}/reminders` · `GET /reminders` · `PATCH /reminders/{id}` · `POST /reminders/{id}/done` · `POST /reminders/{id}/cancel` | Recordatorios y reuniones, con su evento en Google Calendar | sí |
| `POST /reminders/sync` | Subir ya a Calendar lo pendiente o con error | **no** |
| `GET /inbox` · `POST /inbox/{id}/assign` · `POST /inbox/{id}/ignore` | Respuestas recibidas sin asignar (`status`: `unassigned` por defecto, `assigned`, `ignored`): asignar a un lead o descartar | sí |
| `GET /ga/site?days=28` | Tráfico del sitio en GA, solo de Argentina: totales y período anterior, por día, canales, páginas, fuentes, ciudades, dispositivos (cache 10 min, `refresh=true`) | sí |
| `GET /ga/site/detail?kind=&value=&days=28` | Desglose de un ítem de Sitio web (`kind`: `channel`, `source`, `page`, `city`, `device`; `value` tal como lo da `/ga/site`): sesiones por día, fuente/medio, campaña, `utm_content`, página de entrada, ciudad y dispositivo, con el lead y la campaña cruzados (`companies`), y totales por fuente y página de entrada (cache 10 min) | sí |
| `GET /ga/visits` · `POST /ga/sync` · `POST /ga/visits` | Visitas de GA; sincronizar y cargar a mano: solo el usuario | sí / no |
