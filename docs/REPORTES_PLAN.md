# Reportes y estadísticas (27-oct-2026)

Reportes por cliente (los ve el cliente y el admin eligiendo uno) y un resumen de toda la
plataforma para el admin. Solo lo que ayuda a decidir algo o a ver si la plataforma anda bien.
Estado: **implementado (27-oct-2026), sin desplegar**: migración 0036, API `/api/v1/reports/*`, UI
`/reports` y herramientas del MCP; cómo desplegar y qué falta, en la sección 10. El contrato está en la
sección 9; las secciones 1 a 8 son el análisis y las decisiones de origen.

## 1. Qué muestra Inicio hoy

`GET /calls/stats` y `/calls/stats/daily` (`app/services/reports.py`): total, llamadas,
finalizadas, fallidas, rechazadas, completadas y % de objetivo (`Outcome.goal`), minutos,
duración media, latencia media, WhatsApp; gráfico diario de total, % completadas y % objetivo;
llamadas en curso. Filtros: cliente (admin), agente, período.

Los indicadores se calculan en Python cargando todas las conversaciones del período (fila por
fila, con la definición del agente para el resultado): con el volumen actual (35 conversaciones)
alcanza; con miles por mes, no.

## 2. Qué datos tenemos (y no mostramos)

| Fuente | Qué hay | Hoy en la UI |
|---|---|---|
| `call_logs` | modo (entrante, saliente, web, prueba, loadtest), estado, `sip_status`, `ended_reason` (cortó el cliente, fuera de tema, cortada por el usuario, timeout, error), inicio/fin, duración, número de la línea, link, campaña, estado del mail de resumen | Solo totales |
| `call_logs.latency` | por turno: STT, fin de turno (EOU), LLM, TTS, total y e2e; promedio y máximo | Promedio global; detalle por llamada |
| `conversations` | canal, agente y versión, datos capturados (`fields`), resultado (`progress.outcome`, con `goal` y `no_contact`), errores del agente externo, mensajes con hora (desde el 23-oct) | Resultado por conversación |
| `messages[].llm` (trazas) | por turno: ms del LLM, proveedor y modelo (propio, BYOK, externo); por herramienta: slug, ms, salida, resultado | Solo en el detalle |
| `wa_messages` / `wa_threads` / `wa_accounts` | entrantes/salientes, texto o audio, enviado/entregado/leído/fallido con error de Meta; hilos, pausa, cierre; calidad y límite de la cuenta | Nada agregado |
| `campaigns` / `campaign_contacts` | por contacto: intentos, resultado, código SIP o error de Meta, enviado/respondido, seguimiento; bajas (`contact_optouts`) | Stats por campaña |
| `handoff_legs` / `events` | derivaciones: pedida, sonando, atendida, no atendió, ocupado, contestador, conectada, vuelve a la IA, fuera de horario; segundos facturados; primera respuesta del vendedor en WhatsApp | Línea de tiempo por llamada |
| `api_usage_daily` / `api_requests` / `mcp_tool_usage` | inferencia por API (tokens, segundos de STT, caracteres de TTS) y uso del MCP por herramienta | Uso de inferencia, MCP |
| `subscriptions` / `billing_payments` / `tiers` / `client_limit_adjustments` | plan, vencimiento, pagos, precio, ajustes de cupo | Ficha del cliente |
| `contacts`, `blocked_numbers`, `call_links`, `legal_acceptances`, `consumer_requests` | agenda, bloqueados, links, aceptaciones, bajas | Listados |

**Lo que no se guarda** (y haría falta para algunos reportes, sección 6): tokens del LLM por
conversación, ejecuciones de herramientas en una tabla (hoy solo dentro del JSON de mensajes),
concurrencia en el tiempo (se puede reconstruir de inicio/fin) y la hora de cada mensaje antes
del 23-oct.

## 3. Reportes del cliente

Sección nueva **Reportes** en el panel, con pestañas. Solo lo de su negocio: llamadas,
mensajes, resultados, conversiones, transferencias y consumo del plan. **Nada técnico**
(latencia, errores internos, herramientas): eso es del admin (sección 4). Filtros comunes:
período (con comparación contra el período anterior), agente, canal, línea. Sin `loadtest`;
las pruebas, fuera salvo con el filtro "Incluir pruebas". Horas en la zona del cliente.

### 3.1 Resumen y consumo del plan
- **Lo primero que se ve** (lo que más les interesa a los clientes): **consultas por día**
  (llamadas y conversaciones de WhatsApp, apiladas por canal) y **cuántas terminaron en una
  transferencia** a una persona (pedidas y atendidas), en número y en % de las consultas, en el
  mismo gráfico.
- **KPIs con variación vs. el período anterior:** conversaciones (voz, WhatsApp, web), % de
  conversión (resultado completo), % derivadas, minutos, duración media.
- **Consumo del plan:** minutos entrantes y salientes usados vs. el cupo, con **proyección a fin
  de mes** al ritmo actual; mensajes de WhatsApp del período; llamadas **rechazadas por límite**
  (concurrencia o minutos): son clientes que no atendimos.
- **Para qué sirve:** ver de un vistazo si el agente cumple y si el plan le alcanza.

### 3.2 Llamadas
- Serie diaria por modo (entrantes, salientes, web).
- **Mapa de calor día de la semana × hora**: cuándo llaman. Sirve para los horarios de las
  áreas de derivación y de las campañas.
- Por línea y por agente (tabla con volumen, % de conversión, duración).
- Duración (distribución) y **cómo terminan:** cortó el cliente, terminó el agente, fuera de
  tema, cortada desde el panel, bloqueada; cortes tempranos (menos de 15 s).
- **Recurrentes:** llamantes nuevos vs. que vuelven en el período (por teléfono o `wa_id`);
  los que más vuelven (puede indicar un problema sin resolver).

### 3.3 Resultados y conversiones
- **Conversión:** cada conversación queda en **completa** (todos los datos requeridos; dentro,
  las de resultado objetivo), **parcial** (algún dato, sin completar: `incompleta`) o **sin
  datos**. Serie diaria y por agente.
- **Distribución de resultados por agente** (los `outcomes` que define el cliente), con los de
  objetivo resaltados; evolución en el tiempo.
- **Embudo:** atendidas → con algún dato → completas → resultado objetivo.
- **Datos capturados por campo:** % de conversaciones en que se obtuvo cada dato requerido.
  Muestra qué pregunta se pierde.
- Por versión del agente: comparar antes/después de un cambio en la definición.

### 3.4 Mensajes (WhatsApp)
- Mensajes entrantes y salientes, texto vs. nota de voz, por día; mapa de calor por hora.
- Conversaciones por día, mensajes por conversación, conversión (como 3.3).
- Entrega: enviados, entregados, leídos, fallidos.
- Estado de la cuenta: calidad (verde/amarillo/rojo) y límite de mensajería.

### 3.5 Transferencias (derivaciones)
- Pedidas, atendidas por una persona, no atendidas, fuera de horario o sin miembros; por área.
- Por persona del equipo: atendidas, no atendidas, tiempo hasta atender, minutos.
- WhatsApp: tiempo hasta la primera respuesta del vendedor, reasignaciones.
- **Para qué sirve:** ver si el equipo responde y si los horarios del área están bien.

### 3.6 Campañas
- Comparativo de campañas: contactos, intentos, atendidas, conversión, bajas, minutos.
- Embudo por campaña (voz: marcado → atendió → completa → objetivo; WhatsApp: enviado →
  entregado → leído → respondido → objetivo).
- Motivos de no contacto (ocupado, no atiende, contestador, número inválido).
- **Mejor horario:** % de atendidas por hora y día.

## 4. Admin: un cliente

El admin ve lo del cliente (sección 3) eligiendo el cliente en un selector, más lo técnico:
- Latencia: tiempo de respuesta p50/p95 por día y desglose por etapa (STT, fin de turno, LLM,
  TTS) y por proveedor del LLM.
- **Herramientas:** por herramienta, usos, % de error, tiempo p50/p95, último error (la API del
  cliente caída o lenta alarga la espera en la llamada).
- Turnos por conversación, llamadas con error o caídas, códigos SIP de las campañas.
- Errores técnicos con su texto (`call_logs.error`), mails de resumen fallidos, webhooks de
  campaña fallidos.
- Plan, pagos, ajustes de cupo y uso de API de inferencia y MCP.

## 5. Admin: toda la plataforma

Selector de cliente con la opción **Todos** (por defecto). Con "Todos", además:

### 5.1 Clientes
- **Tabla por cliente** (ordenable): plan, conversaciones, minutos, % del cupo, % objetivo,
  errores, latencia p95, último uso, variación vs. el período anterior.
- **Alertas (primera versión):** cerca del cupo (≥ 80 % de los minutos: oportunidad de mejorar
  el plan) e inactivo (14 días sin conversaciones: riesgo de baja). Después, quizá: rechazos por
  límite, cuenta de WhatsApp en amarillo o rojo, herramientas fallando.

### 5.2 Negocio
- Clientes por plan y su evolución; altas por registro (landing), conversión Free → pago.
- Ingreso mensual recurrente (`subscriptions` × `tiers.price_ars`), pagos del mes, vencidos y
  en gracia, caídas al Free.
- Minutos y conversaciones totales de la plataforma por día, por canal y por plan.
- Demo de la landing: llamadas por día, minutos del cupo diario, por agente de la demo.

### 5.3 Operación
- **Latencia por etapa** p50/p95 por día y por hora, y contra la cantidad de llamadas en curso.
- **Concurrencia:** pico de llamadas simultáneas por hora vs. la capacidad medida (cuando haya
  CAP con Gemma). Es la señal para sumar GPUs.
- **Fallas:** fallidas por motivo (`parent process shutdown` = reinicio del worker, timeout,
  error de LiveKit/SIP), rechazadas por motivo, por día.
- **LLM:** turnos por proveedor (propio, BYOK, externo), tiempo y errores; tokens cuando se
  guarden.
- **Costos variables:** minutos salientes (campañas y derivaciones: `billed_seconds`),
  plantillas de WhatsApp enviadas por categoría.

## 6. Cómo se implementa (propuesta)

- **API:** `GET /api/v1/reports/<reporte>?client_id=&agent_id=&from=&to=&channel=&compare=1`.
  El cliente ve solo el suyo (como hoy); `client_id` vacío = todos, solo admin. También al MCP
  (una herramienta `get_report`).
- **Consultas en SQL** (agregados en la base, no fila por fila en Python). El resultado de una
  conversación se guarda al terminar (`progress.outcome`), con su `goal`: se puede agregar sin
  cargar la definición. Para las anteriores sin `outcome` guardado, un backfill una vez.
- **Rollup diario** (`report_daily`: cliente × agente × día × canal × modo con contadores y
  sumas) solo si las consultas se ponen lentas; con el volumen actual no hace falta.
- **Datos nuevos a guardar:**
  1. tokens de entrada/salida por turno en la traza (el `usage` de la respuesta);
  2. `tool_runs` (herramienta, conversación, ms, ok, código HTTP) en lugar de leer el JSON;
  3. columna `outcome`/`goal` en `conversations` (índice para agregar rápido);
  4. historial de calidad de las cuentas de WhatsApp (hoy solo el valor actual).
- **UI:** `web/src/features/reports/`, Mantine Charts, siguiendo `DESIGN_GUIDELINE_APP.md`.
  Inicio queda como está (o con un link a Reportes).
- **Fases:**
  1. Datos nuevos (los 4 de arriba, para que empiece a juntarse historia), API en SQL, Resumen,
     Llamadas y Resultados para cliente y admin, corte por plan y CSV. El gráfico de consultas
     por día con las transferencias (3.1) va en esta fase, en todos los planes.
  2. Mensajes, Transferencias, Campañas y lo técnico del admin por cliente (latencia, herramientas).
  3. Admin, toda la plataforma: Clientes, Negocio, Operación y costos estimados.

## 7. Decisiones (27-oct-2026)

- **Sección nueva "Reportes"** con pestañas; Inicio queda como resumen del día con un link.
- **Por plan:** Free ve Resumen y Llamadas; Resultados, Mensajes, Transferencias y Campañas,
  en los planes pagos (aviso "Mejorar mi plan" como el resto,
  `FUNCIONES_POR_PLAN_PLAN.md`; clave nueva en `tiers`).
- **Exportar:** CSV por reporte. Sin PDF ni mail periódico por ahora.
- **Negocio y operación del admin:** en Reportes, en pestañas que solo ve el admin, con el
  selector de cliente en "Todos".
- **Pruebas:** las llamadas de prueba (navegador, Playground) quedan fuera por defecto, con un
  filtro "Incluir pruebas"; el loadtest, siempre fuera.
- **El cliente no ve nada técnico:** ni latencia ni herramientas ni errores internos. Ve
  llamadas, mensajes, resultados, conversiones (completa/parcial), transferencias, campañas y
  consumo del plan. Lo técnico es del admin (sección 4).
- **Costos estimados** por conversación (Anura, plantillas de Meta, tokens BYOK): solo el admin,
  fase 3, con las tarifas en la config.
- **Datos nuevos** (tokens por turno, `tool_runs`, resultado en columna, historial de calidad de
  WhatsApp): desde la fase 1.

- **Prioridad de los clientes** (sin pedidos concretos todavía): consultas por día y cuántas
  terminaron en transferencia; van arriba del Resumen y en la fase 1, también en Free.
- **Alertas del admin:** "cerca del cupo" al 80 % del cupo de minutos; "inactivo" a los 14 días
  sin conversaciones. Por ahora solo esas dos (las demás de 5.1 quedan para después).
- **Período por defecto:** últimos 30 días.

## 8. Preguntas abiertas

Ninguna por ahora; lo que surja al detallar la fase 1.

## 9. Implementación (27-oct-2026)

### 9.1 Datos (migración 0036)

- `conversations.outcome` (id del `Outcome`), `goal`, `conversion` (`complete` | `partial` | `empty`)
  y `llm_input_tokens`/`llm_output_tokens` (suma de los turnos). Los completa el motor al guardar;
  las anteriores, `make reports-backfill` (idempotente).
  - `complete`: todos los datos requeridos (la conversación completó con un resultado que no es
    `incompleta` ni `fuera_de_tema`).
  - `partial`: algún dato capturado (`fields` con algún valor no vacío) sin completar.
  - `empty`: ningún dato.
- `tool_runs`: una fila por ejecución de una herramienta del cliente (ok, código HTTP, ms, error).
- `wa_account_status_log`: una fila por cambio de estado, calidad o límite de una cuenta de WhatsApp.
- `tiers.advanced_reports`: Resultados, Mensajes, Transferencias y Campañas (clave `advanced_reports`
  de `services/features.TIER_HAS`). Free: no; pagos e Interno: sí.

### 9.2 API (`/api/v1/reports/*`, `app/api/routers/reports.py`, `app/services/report_stats.py`)

Filtros comunes (query): `client_id` (admin; vacío = todos los clientes, solo admin; el cliente
siempre el suyo, `scoped_client_id`), `agent_id`, `channel` (`voice` | `whatsapp` | `web`),
`phone_number_id`, `date_from`/`date_to` (días locales, inclusive; por defecto los últimos 30 días
hasta hoy), `tz` (por defecto `BILLING_TIMEZONE`), `include_tests` (bool, default false: sin
`prueba` ni conversaciones por API/Playground; el `loadtest` nunca).

Consultas en SQL agregadas (nada de cargar conversación por conversación). Fechas en UTC naive en
la base; los días y horas se agrupan en `tz`.

"Consulta" = una conversación de cliente (llamada atendida o no, o conversación de WhatsApp).
"Transferencia" = conversación con al menos un evento `handoff.requested` (voz) o
`wa.handoff.assigned` (WhatsApp); "atendida" = con `handoff.connected` o `wa.handoff.first_reply`.

| Endpoint | Plan | Devuelve |
|---|---|---|
| `GET /reports/summary` | todos | `period {date_from, date_to}`, `kpis` y `previous` (mismo período anterior, misma forma): `conversations`, `by_channel {voice, whatsapp, web}`, `conversion_pct`, `goal_pct`, `transfers`, `transfers_answered`, `transfer_pct`, `minutes`, `avg_duration` (s), `rejected_by_limit`, `wa_messages`; `plan` (null con `client_id` vacío): `inbound_minutes_used`, `inbound_minutes_quota` (null = sin límite), `outbound_minutes_used`, `outbound_minutes_quota`, `projected_inbound_minutes` (al ritmo del mes en curso), `period_start`, `period_end`; `daily: [{date, voice, whatsapp, web, transfers, transfers_answered}]` |
| `GET /reports/calls` | todos | `daily: [{date, entrante, saliente, web, prueba}]`, `heatmap: [{weekday 0=lunes, hour, count}]`, `by_line: [{phone_number_id, number, calls, minutes, conversion_pct}]`, `by_agent: [{agent_id, agent_name, calls, minutes, avg_duration, conversion_pct, goal_pct}]`, `durations: [{bucket: "0-15s"\|"15-60s"\|"1-3m"\|"3-5m"\|"5-10m"\|"10m+", count}]`, `ended: [{reason, count}]` (`customer_hangup`, `agent_end`, `off_topic`, `hangup_by_user`, `blocked_number`, `rejected`, `failed`, `other`), `early_hangups`, `callers {new, returning, top: [{phone, count, last_at}]}` |
| `GET /reports/outcomes` | `advanced_reports` | `conversion_daily: [{date, complete, partial, empty}]`, `by_agent: [{agent_id, agent_name, total, complete, partial, empty, goal}]`, `outcomes: [{agent_id, agent_name, outcome, label, goal, count}]`, `funnel {conversations, with_data, complete, goal}`, `fields: [{agent_id, agent_name, field, label, captured, total, pct}]` (los datos requeridos de la versión vigente del agente), `by_version: [{agent_id, agent_name, version, total, conversion_pct, goal_pct}]` |
| `GET /reports/messages` | `advanced_reports` | `daily: [{date, inbound, outbound, inbound_audio, outbound_audio, conversations}]`, `heatmap` (entrantes), `delivery {sent, delivered, read, failed}`, `failures: [{code, message, count}]`, `per_conversation_avg`, `conversion {complete, partial, empty}`, `accounts: [{account_id, display_phone_number, status, quality_rating, messaging_limit, history: [{at, status, quality_rating, messaging_limit}]}]` |
| `GET /reports/transfers` | `advanced_reports` | `kpis {requested, answered, not_answered, unavailable, answer_pct, avg_answer_seconds, minutes}`, `daily: [{date, requested, answered}]`, `by_area: [{area_id, name, requested, answered, not_answered, unavailable}]`, `by_member: [{team_member_id, name, attempts, answered, not_answered, avg_answer_seconds, minutes}]`, `whatsapp {assigned, first_reply, avg_first_reply_seconds, reassigned}` |
| `GET /reports/campaigns` | `advanced_reports` | `campaigns: [{campaign_id, name, channel, status, contacts, attempts, reached, complete, goal, optouts, minutes}]`, `no_contact: [{reason, count}]` (ocupado, no atiende, contestador, inválido, fallido, otro), `best_hours: [{weekday, hour, attempts, reached}]` |
| `GET /reports/technical` | solo admin | `latency_daily: [{date, p50, p95, stt_p50, eou_p50, llm_p50, tts_p50}]` (de `call_logs.latency.turns[*].total`, etc.), `by_provider: [{provider, model, turns, avg_ms, errors}]`, `tools: [{tool_id, slug, type, runs, errors, error_pct, p50_ms, p95_ms, last_error, last_error_at}]`, `turns_avg`, `errors: [{reason, count}]`, `failed_summary_emails`, `tokens {input, output, by_day: [{date, input, output}]}` |
| `GET /reports/platform` | solo admin (sin `client_id`) | `clients: [{client_id, name, tier, conversations, minutes, quota_pct, conversion_pct, errors, last_activity_at, delta_pct}]`, `alerts: [{client_id, name, kind: "near_quota"\|"inactive", detail}]` (≥ 80 % de los minutos entrantes del mes; 14 días sin conversaciones; clientes activos, sin el interno), `business {clients_by_tier: [{tier, count}], signups: [{date, count}], mrr_ars, payments_month_ars, past_due, free_to_paid}`, `operation {peak_concurrency: [{date, hour, peak}], failures: [{date, reason, count}], rejected: [{reason, count}]}` |

Sin el plan: 403 `advanced_reports_not_in_plan` (como `not_in_plan` de la API de inferencia; las
funciones que cortan una acción, como WhatsApp o las herramientas, responden 429 `*_not_in_plan`). La UI
no pide el reporte si el plan no lo incluye (`/plan/features`) y el MCP corta antes con `feature_not_in_plan`. CSV: lo arma la UI con los
datos de cada tabla o gráfico (botón "Descargar CSV").

### 9.3 UI (`web/src/features/reports/`)

Ruta `/reports`, "Reportes" en la navegación (debajo de Inicio). Filtros arriba (admin: selector de
cliente con "Todos"; agente, canal, período con los últimos 30 días por defecto, "Incluir pruebas").
Pestañas: Resumen, Llamadas, Resultados, Mensajes, Transferencias, Campañas; admin: Técnico y,
con "Todos", Plataforma. Las del plan, con el aviso de "Mejorar mi plan". Inicio lleva un link.

### 9.4 MCP

Una herramienta por reporte del cliente (`get_report_summary`, `get_report_calls`,
`get_report_outcomes`, `get_report_messages`, `get_report_transfers`, `get_report_campaigns`) en
`app/mcp/catalog.py`, con `features` según el plan; `technical` y `platform` en el toolset `admin`.

## 10. Cómo desplegar y qué falta

Código: `app/services/report_stats.py` (consultas), `app/api/routers/reports.py` (API),
`web/src/features/reports/` (UI), `app/mcp/catalog.py` (herramientas) y la migración
`migrations/versions/0036_reports.py`. Tests: `tests/test_reports.py`, `tests/test_reports_data.py`,
`tests/test_migration_0036.py`.

Desplegar, en este orden:

1. `make migrate-test`: prueba la 0036 contra una copia del backup en PostgreSQL.
2. `make migrate`: agrega las columnas de `conversations`, `tool_runs`, `wa_account_status_log` y
   `tiers.advanced_reports` (Free `false`; los planes pagos e Interno `true`).
3. `make reports-backfill`: completa `outcome`, `goal` y `conversion` de las conversaciones anteriores
   (idempotente: se puede repetir). Los tokens del LLM y las ejecuciones de herramientas no se
   reconstruyen: juntan historia desde el despliegue.
4. `make calls-active && make up-agent`: recrea `app` y `agent` (**corta las llamadas en curso**; la UI se
   compila en la imagen de `app`).
5. Landing: publicar la sección Reportes de `/desarrolladores/docs/api`, las tarjetas de planes y la
   documentación del MCP (`make mcp-docs`).

Pendientes (no están en esta entrega):

- **Costos estimados** por conversación (Anura, plantillas de Meta, tokens BYOK), solo admin: faltan las
  tarifas en la config.
- **Alertas extra del admin:** rechazos por límite, cuenta de WhatsApp en amarillo o rojo y herramientas
  fallando. Hoy solo "cerca del cupo" e "inactivo".
- **Rollup diario** (`report_daily`): solo si las consultas se ponen lentas con el volumen real; hoy no hace
  falta.
- **PDF y mail periódico**: descartados por ahora; solo CSV desde la UI.
- Comparar con la **concurrencia medida** (CAP con Gemma) en Operación, cuando exista el CAP.
