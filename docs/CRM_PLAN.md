# Plan: CRM de ventas propio (leads, campañas, envíos y seguimiento)

Diseño (21-oct-2026). **Estado: primera versión implementada el 21-oct-2026** (sección 10): backend `crm/`, UI `web/src/crm/`, importación `scripts/mercado/crm_import.py`; contrato en [`CRM_API.md`](CRM_API.md). Reemplaza el seguimiento en Markdown
(`docs/mercado/seguimiento.md`, `envios/*.md|csv`, `blacklist.md`) por una app local con base de
datos, API para agentes y envío y recepción por Resend, cruzada con Google Analytics.

## 0. Qué resuelve y qué no

Hoy el registro es un `.md` de ~1.150 líneas y 340 contactos que se edita a mano o con scripts
(`scratch/seg-pendientes/`, `scripts/mercado/enviar_seguimientos.py`). Lo que se repitió en octubre:

- Estados que no coinciden con lo enviado (el 21-oct, Resend mostró seguimientos "del 15-oct" que
  salieron el 14, dos que nunca salieron y mails duplicados).
- Clics de GA copiados a mano, sin vínculo con el contacto ni con el envío.
- Cada tanda nueva es un `.md` + `.csv` + HTML para copiar a Gmail, y el estado se actualiza aparte.

**Objetivo:** una sola fuente de verdad por lead, con su información, el historial de mails (salientes
y entrantes), las visitas de GA y la etapa actual; campañas y plantillas; un workflow simple de
pasos; y una API que el agente `ventas` usa en lugar de editar archivos.

**Fuera de alcance (a propósito):** multiusuario, permisos, pipeline de oportunidades con montos,
tracking de aperturas (un pixel en mails de 5 líneas baja la entregabilidad), enriquecimiento
automático de datos, editor visual de flujos, acceso desde internet.

## 1. Decisiones

| Decisión | Elección | Por qué |
|---|---|---|
| Dónde vive | **Servicio aparte `crm`** en este repo (`crm/` + `web/src/crm/`), no dentro de `app` | `app` es el producto multi-cliente y está publicado en `app.atentina.com.ar`; el CRM es interno y local. Separado no hereda la CSP, los tiers ni la auth de clientes, y se puede borrar sin tocar el producto |
| Stack | El mismo de `app`: FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL; UI React + Mantine | Cero tecnología nueva. La UI reusa `web/src/theme.ts` y `web/src/components/` (guía [`DESIGN_GUIDELINE_APP.md`](DESIGN_GUIDELINE_APP.md), vista interna) |
| Base | **Base `crm` en el mismo contenedor `db`**, con migraciones propias (`crm/migrations/`) | Sin otro contenedor; base separada para que nada del producto la toque. Se suma a `scripts/ops/backup.sh` |
| Acceso | Puerto `127.0.0.1:8030`, sin túnel ni regla en el router. La UI y la API piden `Authorization: Bearer` (`CRM_API_KEY` el usuario, `CRM_AGENT_API_KEY` los agentes) (la UI la pide una vez y la guarda en el navegador) | Uso local, de una persona. Una key alcanza; sin login ni usuarios |
| Modelo de CRM | **Cuenta (empresa) + personas + puntos de contacto**, como HubSpot o Pipedrive | Patrón conocido: el agente y cualquier persona lo entienden sin explicación |
| Etapa del lead | Columna `stage` con una lista cerrada (sección 3), que cambia sola con los eventos (envío, respuesta, rebote) y a mano | Es lo que hoy es la columna "Estado" del `.md` |
| Saliente | **API de Resend** desde la app, una cola con un envío por ventana de ~2 min con pausa al azar, horario hábil y tope diario | Lo mismo que `enviar_seguimientos.py` (21-oct), pero con estado en la base. Copia a la casilla propia por `bcc` para que el hilo esté en Gmail |
| Hilos | `In-Reply-To` y `References` con el `message_id` del mail anterior del lead | Así se hizo el 21-oct; el seguimiento cae en el mismo hilo aunque salga de otra casilla |
| Entrante | **A mano en la primera versión** (`POST /api/leads/{id}/inbound` o botón en la ficha). Después: Resend Receiving en un subdominio + polling (6) | Hoy son pocas respuestas; el polling evita exponer un webhook |
| Eventos de entrega | Polling de `GET /emails/{id}` cada 10 min: los "enviados" de los últimos 14 días y los entregados de los últimos 3 | Rebote, queja y entrega sin webhook. Con más volumen se pasa al webhook (`email.bounced`, `email.delivered`, `email.complained`), firmado por Svix |
| GA | **Google Analytics Data API** (`runReport`), cuenta de servicio con rol Lector, una vez por día y a pedido | Reemplaza el copiado del reporte. Se cruza por `utm_content` (lead) y `utm_campaign` (campaña y paso) |
| Plantillas | Texto con variables `{{saludo}}`, `{{nombre}}`, `{{empresa}}`, `{{link}}`; el mail guarda el texto final | Sin motor de plantillas: reemplazo simple y error si falta una variable. El link con UTM lo arma la app |
| Workflow | **Secuencia por campaña** (desde el 21-oct-2026): pasos de seguimiento con días hábiles desde el último mail y plantilla opcional. **"Hoy"** lista a quién le toca qué paso; con plantilla y campaña activa, el borrador se arma solo y espera aprobación | Cubre lo que hacemos (primer mail → seguimientos → llamada) sin un motor de flujos |
| Revisión | **Todo mail es borrador hasta que el usuario lo aprueba** (la key de agente no puede aprobar) | Igual que hoy: el usuario mira antes de mandar |
| Importación | **Script de una sola vez** que lee los `.md`/`.csv`, la blacklist y el historial de Resend y carga todo por la API (9) | Después del corte, todo entra por la API o la UI |

## 2. Arquitectura

```text
navegador (127.0.0.1:8030) ──┐
agente ventas (curl/httpx) ──┼─> crm (FastAPI) ── PostgreSQL (base crm, contenedor db)
                             │      │  loops: cola de envío · eventos de Resend · GA
                             │      ├─> Resend: POST /emails, GET /emails/{id}, GET /emails/receiving
                             │      └─> Google Analytics Data API: runReport
```

Un solo proceso: la API y tres loops de fondo (asyncio, como los de `app`): cola de envío, estado de
lo enviado en Resend y GA. Cada uno es idempotente.

```text
crm/
  main.py            FastAPI: /api, /api/docs, la UI (web/dist/crm.html) y los loops
  config.py          CRM_DB_DSN, CRM_API_KEY, CRM_AGENT_API_KEY, CRM_RESEND_API_KEY, CRM_MAIL_*, CRM_SEND_*, CRM_GA_*
  auth.py            las dos keys
  models.py          tablas (sección 3)
  schemas.py         contrato de la API (Pydantic): lo que ve el agente
  routes/leads.py    leads, personas, contactos, fuentes, actividad, respuestas, línea de tiempo
  routes/outreach.py campañas, plantillas, mensajes y cola, blocklist, GA, hoy, tablero
  services/
    leads.py         alta/upsert por dominio, normalización, etapa, blocklist
    templates.py     variables y link con UTM
    messages.py      borradores, hilo, aprobación, envío/rebote/respuesta, seguimientos que vencen
    sending.py       cola (ventana con jitter, horario, tope) y eventos de Resend
    resend.py        enviar con encabezados de hilo y leer el estado
    ga.py            runReport → ga_visits → match
  migrations/        Alembic propio (alembic.ini en crm/)
web/src/crm/         UI (entrada web/crm.html, como web/src/llamar/)
scripts/mercado/crm_import.py   importación inicial, por la API
tests/test_crm.py
docs/CRM_API.md      contrato para agentes
```

Compose: servicio `crm` (misma imagen que `app`, otro comando), `127.0.0.1:8030`, depende de `db`.
Targets: `make crm-up`, `make crm-migrate`, `make crm-db`, `make crm-logs`, `make crm-psql`.

## 3. Modelo de datos

Nombres en inglés en la base y la API (como `app`); textos de la UI en español.

| Tabla | Campos principales | Notas |
|---|---|---|
| `leads` | `id`, `slug` (= `utm_content`, único), `name`, `legal_name`, `domain` (único, clave de dedupe), `website`, `description` (rubro), `kind` (`cliente`/`canal`), `industry`, `tags` (text[]), `country`, `province`, `city`, `stage`, `stage_changed_at`, `next_action`, `next_action_at`, `do_not_contact`, `notes`, `legacy_ref` (el `#` del `.md`), `created_by` (`usuario`/`agente`), timestamps | Una fila por empresa. Categorías e industrias como texto + tags: sin tablas de catálogo |
| `people` | `id`, `lead_id`, `name`, `title`, `is_decision_maker`, `linkedin_url`, `notes`, `source_id` | Directivos y personas asociadas |
| `contact_points` | `id`, `lead_id`, `person_id` (nulo = de la empresa), `kind` (`email`/`phone`/`whatsapp`/`linkedin`/`form`), `value` (normalizado: email en minúsculas, teléfono E.164), `label` (`persona`/`area`/`atencion`), `is_primary` (el ★), `status` (`ok`/`bounced`/`suppressed`/`unverified`), `verified_at`, `source_id` | Todos los emails y teléfonos encontrados. Único por (`kind`, `value`) |
| `sources` | `id`, `lead_id`, `url`, `title`, `seen_at`, `note` | De dónde salió cada dato (regla del agente: solo publicados). Persona y contacto apuntan a su fuente |
| `blocklist` | `value` (email o dominio), `reason` (`bounce`/`complaint`/`opt_out`/`manual`), `created_at` | Reemplaza `blacklist.md`. El envío la consulta siempre |
| `campaigns` | `id`, `slug` (= `utm_campaign`, único), `name`, `channel` (`email`/`linkedin`/`phone`), `segment`, `from_addr`, `status` (`draft`/`active`/`done`), `started_at`, `notes` | "Qué se hizo y cuándo": cada tanda es una campaña |
| `templates` | `id`, `name`, `kind` (`first`/`follow_up`/`other`), `subject`, `body` (a "ustedes"), `body_personal` (tuteo), `archived` | Editables; el mensaje guarda el texto final, así un cambio no reescribe lo enviado |
| `messages` | `id`, `lead_id`, `campaign_id`, `template_id`, `kind` (`first`/`follow_up`/`other`), `direction` (`out`/`in`), `from_addr`, `to_addr`, `subject`, `text`, `html`, `status` (`draft`/`queued`/`sent`/`delivered`/`bounced`/`complained`/`failed`/`canceled`/`received`), `resend_id`, `message_id`, `in_reply_to`, `queued_at`, `sent_at`, `last_event_at`, `utm_campaign`, `utm_content`, `error` | Saliente y entrante en una sola tabla: el hilo del lead es un `ORDER BY` |
| `activities` | `id`, `lead_id`, `person_id`, `kind` (`note`/`call`/`meeting`/`linkedin`/`stage_change`/`task`), `at`, `text`, `data` (JSON), `done` | La línea de tiempo: llamadas, charlas (hoy "Conversaciones") y tareas |
| `ga_visits` | `date`, `source_medium`, `utm_campaign`, `utm_content`, `active_users`, `sessions`, `events`, `lead_id`, `campaign_id` | Único (`date`, `source_medium`, `utm_campaign`, `utm_content`). `lead_id` nulo = sin match |

**Etapas** (`leads.stage`), las mismas que el `.md` ("Cómo se llena"):
`nuevo` → `contactado` → `seguimiento` → `respondio` → `charla_agendada` → `charla_hecha` →
`propuesta` → `piloto` → `cliente`; cierres: `sin_respuesta`, `no_interesa`, `descartado`.

Cambios automáticos (cada uno queda como `activity` `stage_change`):

| Evento | Etapa |
|---|---|
| Sale el primer mail de una campaña | `nuevo` → `contactado` |
| Sale un paso posterior | → `seguimiento` |
| Se registra una respuesta del lead | → `respondio` (y se cancela lo pendiente) |
| Rebota el único email del lead | → `descartado`; el email va a `blocklist` |

Las demás (charla, propuesta, piloto, cliente, no interesa) son a mano o por la API.

## 4. API (contrato para agentes)

REST en `/api`, JSON, OpenAPI en `/api/docs`, errores en `application/problem+json` (RFC 9457). El
contrato, con ejemplos de `curl` para cada tarea del agente, está en [`CRM_API.md`](CRM_API.md).

- Alta de leads por `POST /api/leads`: crea o actualiza por dominio y suma personas, contactos y
  fuentes sin borrar. Con la key de agente, un email o teléfono sin `source_url` da 422.
- Dos keys: `CRM_API_KEY` (el usuario y la UI) y `CRM_AGENT_API_KEY` (agentes: sin aprobar envíos,
  cargar historial, borrar ni sincronizar GA). Así "el agente no envía" queda en el servidor.
- `.claude/agents/ventas.md` usa la API en vez de los `.md`.

## 5. Envío

1. Los borradores salen de una plantilla para varios leads de una campaña (`POST
   /api/campaigns/{id}/drafts`; el agente o la UI) o de un mail suelto. El seguimiento se arma desde
   "Hoy", que lista los leads con el primer mail enviado hace 4 días hábiles sin seguimiento ni
   respuesta. El usuario aprueba y pasan a `queued`.
2. El loop de envío manda **un mensaje `queued` por ventana** (`CRM_SEND_WINDOW_SECONDS`, 120) en un
   momento al azar dentro de ella, con al menos 30 s entre dos, solo en horario hábil
   (`CRM_SEND_HOURS`, 9–18 de lunes a viernes, hora de Argentina) y hasta `CRM_SEND_DAILY_MAX` (50)
   por día. Antes de cada uno vuelve a chequear la blocklist, `do_not_contact` y que el lead no
   haya respondido.
3. `POST https://api.resend.com/emails` con `Idempotency-Key` = id del mensaje, `In-Reply-To` y
   `References` del último mensaje del hilo, `bcc` a la casilla propia y texto + HTML (el link
   largo como "atentina.com.ar", como hoy).
4. Remitente por campaña (`laureano@atentina.net` por default). El dominio tiene que estar verificado
   en Resend para envío.

La key de Resend del CRM (`CRM_RESEND_API_KEY`) es de acceso completo, porque lee eventos y recibidos.
La de `app` sigue siendo de solo envío.

## 6. Entrante

En producción desde el 22-oct-2026 (`CRM_INBOUND_ENABLED=true`; pasos 1 a 3 hechos, probado con un mail reenviado).
Código en `crm/services/inbound.py`; migración `0005`; tests en `tests/test_crm_inbound.py`.

Hoy `laureano@atentina.com.ar` y `.net` tienen MX en Cloudflare Email Routing, que reenvía a Gmail.
Para que el CRM vea las respuestas sin perder la casilla:

1. **Resend:** activar la recepción para `in.atentina.net` (Domains → Receiving) y cargar en Cloudflare
   el MX que indica, **solo en el subdominio** (la raíz sigue con Email Routing).
2. **Cloudflare:** cambiar la regla de cada casilla por un **Email Worker** ([`deploy/crm-email-worker.js`](../deploy/crm-email-worker.js)) que haga dos
   `message.forward()`: a Gmail, como hoy, y a `crm@in.atentina.net`. Cubre también las respuestas a lo
   ya enviado (poner `Reply-To` no, y además rompería el hilo en Gmail). Plan B, sin Worker: un filtro de
   Gmail que reenvía a esa dirección.
3. **`.env`:** `CRM_INBOUND_ENABLED=true` y `CRM_NOTIFY_TO` (el aviso), y `make crm-up`.

Cómo procesa cada recibido (cada `CRM_INBOUND_INTERVAL_SECONDS`, 120; `GET /emails/receiving`, sin webhook):

- **Ignora** lo que viene de nuestros dominios (`CRM_OWN_DOMAINS`: las copias BCC de cada envío) y los
  rebotes (los ven los eventos).
- **Asocia** por el hilo (`In-Reply-To`/`References` contra `messages.message_id`), si no por la
  dirección del remitente y si no por el dominio (salvo correo gratuito). Sin lead queda en
  **"Respuestas sin asignar"** del Tablero, para asignarlo a mano (`POST /api/inbox/{id}/assign`) o ignorarlo.
- **Clasifica** con el LLM local (`vllm-llm`, Gemma) lo que escribió, sin el mail citado: intención,
  resumen, próxima acción, fecha y persona a la que deriva. JSON pedido en el prompt: con el esquema
  forzado (guided decoding) Gemma se colgaba en espacios en 3 de 5; así, 8 de 9 bien, 0,5 a 0,9 s
  (`scratch/crm-inbound/`). La etapa la decide el código, no el LLM:

| Intención | Qué cambia en el lead (además de mensaje `in`, etapa `respondio` y lo pendiente cancelado) |
|---|---|
| interesado, agendar, pide info | Próxima acción y su fecha (la que proponen, o hoy) |
| derivado | Lo mismo, y la persona y su email como contacto nuevo |
| más adelante | Próxima acción a la fecha que digan, o en 90 días |
| no interesa | Etapa `no_interesa` |
| baja | `no_interesa`, no contactar y el email a la blocklist (`opt_out`) |
| autorespuesta (por encabezados o LLM) | Nada: ni etapa ni cancelación. Si dice hasta cuándo, próxima acción ese día |

- Con el LLM caído, confianza menor a `CRM_LLM_MIN_CONFIDENCE` (0,7) u "otro": solo `respondio`, marcado
  "Sin analizar" o "Revisar". Todo queda en `messages.analysis` y en una nota de la línea de tiempo.
- **Aviso** por mail a `CRM_NOTIFY_TO` de cada respuesta (no las autorespuestas) y de cada una sin
  asignar, directo por Resend (no por la cola ni su tope diario). Nunca contesta solo.

Cupo: los recibidos cuentan en el plan de Resend igual que los enviados ([`EMAIL_PLAN.md`](EMAIL_PLAN.md), 3).

## 7. Google Analytics

- Cuenta de servicio en Google Cloud con la API "Google Analytics Data API" habilitada, agregada
  como **Lector** en la propiedad. `CRM_GA_PROPERTY_ID` y `CRM_GA_CREDENTIALS` (ruta al JSON, fuera del
  repo, en el backup como `.env`).
- `runReport` por día con dimensiones `date`, `sessionSourceMedium`, `sessionCampaignName`,
  `sessionManualAdContent` y métricas `activeUsers`, `sessions`, `eventCount`. Una vez por día
  (últimos 3 días, GA consolida tarde) y a pedido desde la UI.
- Match: `utm_content` → `leads.slug`; `utm_campaign` → `campaigns.slug`, y `follow_up_<x>` →
  campaña `<x>`, paso de seguimiento. Lo que no matchea va a `GET /api/ga/unmatched` (hoy: `(not set)`).
- En la ficha: visitas por día y por mail (primer mail o seguimiento). En la lista: filtro
  "hizo clic y no respondió", que es la prioridad de seguimiento que hoy se arma a mano.
- **Página Sitio web** (desde el 23-oct-2026, `GET /api/ga/site?days=`): tráfico de todo el sitio,
  solo del país `CRM_GA_COUNTRY` (Argentina), en vivo con `batchRunReports` y 10 min de cache
  (`refresh=true` la saltea). Totales contra el período anterior, por día, canales, páginas,
  fuente/medio, ciudades y dispositivos. El filtro hace falta: en 28 días al 23-oct, 122 usuarios de
  Argentina de 469 en total (271 de EE.UU., casi todo robots).

## 8. UI

Interna, solo claro, con los componentes de `web/src/components/` y la guía de la app.

| Pantalla | Qué muestra |
|---|---|
| **Hoy** | Seguimientos que vencen, borradores para aprobar, tareas abiertas, respuestas de la semana, próximas acciones vencidas y la cola (próximo mail, enviados hoy y tope) |
| **Leads** | Tabla con filtros (etapa, campaña, tags, industria, "con clics", "sin respuesta"), búsqueda, acciones en lote (inscribir en campaña, cambiar etapa) |
| **Ficha del lead** | Datos, personas, contactos (★, estado, fuente), línea de tiempo (mails in/out, actividades, visitas de GA, cambios de etapa), etapa y próxima acción, botón "redactar" |
| **Campañas** | Lista con fechas y números (leads, enviados, seguimientos, respuestas, rebotes, clics); detalle con sus mensajes por estado |
| **Plantillas** | Editor de texto con variables y vista previa con un lead |
| **Mensajes** | Todos los mails, por estado, dirección y campaña |
| **Tablero** | El "Resumen" de hoy, calculado |

## 9. Importación y corte

**Una sola vez**, con un script que carga todo **por la API** (`scripts/mercado/crm_import.py`;
`--dry-run` por defecto, deja el reporte en `scratch/crm/import-report.md`; `--apply` carga). Después
del corte, todo entra por la API o la UI: no hay más importaciones.

| Fuente | Va a |
|---|---|
| `seguimiento.md`, tabla "Contactos" | `leads` (`legacy_ref` = `#`, etapa mapeada), email ★, próxima acción |
| `envios/*.csv` | personas, todos los emails encontrados, teléfonos, LinkedIn, WhatsApp, fuentes (URL y fecha), rubro, gancho como nota |
| "Links con UTM" | `leads.slug` y la campaña de cada lead |
| `envios/*.md` | `campaigns` (una por `utm_campaign`) y `templates` |
| Historial de Resend (`GET /emails`) | `messages` (`POST /api/messages/import`): lo que salió de verdad, con `resend_id`, `message_id` y último evento |
| `blacklist.md` | `blocklist` |
| "Clics en el link" y el reporte de GA del 21-oct | `ga_visits` (`POST /api/ga/visits`) |
| "Conversaciones" y "LinkedIn" | `activities` |

**Corte:** el tablero da los números del "Resumen" del `.md`, salvo las diferencias que explique
Resend (reporte). Después, `seguimiento.md` y `blacklist.md` quedan congelados con una línea arriba que
apunta al CRM, y el agente `ventas` usa la API.

## 10. Fases

**Primera versión (21-oct-2026):** leads con personas, contactos y fuentes; blocklist; campañas;
plantillas con variables; borradores, aprobación y cola de envío por Resend (en el hilo, con `bcc`);
estado de lo enviado (entregas, rebotes, quejas); GA por API y carga manual; seguimientos que vencen
(4 días hábiles) en "Hoy"; respuestas registradas a mano; actividad y tareas; tablero; API con dos keys.

| Después | Qué | Cuándo |
|---|---|---|
| Respuestas automáticas | Resend Receiving en un subdominio + polling (sección 6) | Cuando registrar respuestas a mano pese |
| Pasos de tarea | Una tarea (llamar, LinkedIn) como paso de la secuencia | Si hace falta |
| Webhook de Resend | En vez del polling de eventos (hoy hay botón para revisar ya) | Con más volumen |

**Secuencias (21-oct-2026, migración 0003):** `campaigns.sequence` y `messages.step`; editor en la
campaña, paso en "Hoy" y en los mensajes, borradores automáticos en el loop de eventos, y botón para
revisar entregas y rebotes. Las campañas importadas quedaron como "Terminada": para que arme solos los
borradores, pasarla a "Activa".

Despliegue: `make crm-up` (crea la base `crm`, corre las migraciones y levanta el servicio sin tocar
`app` ni `agent`). Variables `CRM_*` en `.env`; credenciales de GA en `secrets/ga.json`.

## 11. Riesgos y pendientes

- **Entregabilidad:** el dominio es nuevo. La cola mantiene el ritmo de hoy (~30 por hora como máximo y
  tope diario); no subirlo sin mirar rebotes y quejas por semana en el tablero.
- **Gmail:** lo que sale por API no aparece en "Enviados". Con el `bcc` el hilo queda completo en la
  bandeja; si molesta, se apaga por campaña.
- **Ley 25.326 y anti-spam:** son datos de empresas publicados, pero cada mail tiene que dejar
  pedir la baja: una línea al pie ("si no querés más mails, respondé 'baja'") y la palabra "baja"
  en una respuesta → `blocklist` (`opt_out`). A definir el texto.
- **GA:** el reporte por `sessionManualAdContent` depende de que cada link tenga UTM; los mails
  viejos sin UTM (2-oct) no matchean.
- A confirmar: subdominio de recepción (`in.atentina.net` o `in.atentina.com.ar`) y si se usa el
  Worker o el filtro de Gmail.
