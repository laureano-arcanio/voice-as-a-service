# Reportes

Estadísticas por cliente (las ve el cliente y el admin eligiendo uno) y de toda la plataforma (admin): consultas,
llamadas, resultados, mensajes, transferencias, campañas y consumo del plan. Estado: en producción desde el
27-oct-2026. Plan: Resumen, Consumo y Llamadas en todos; el resto con `tiers.advanced_reports`.

## Definiciones

| Término | Qué cuenta |
|---|---|
| Consulta | una conversación de cliente: llamada (atendida o no) o conversación de WhatsApp |
| Con agente (`with_agent`) | base de los porcentajes: las llamadas directas y las entrantes que atiende el equipo cuentan como consultas, llamadas y minutos, pero no entran en conversión, objetivo, % de transferencia, embudo ni turnos |
| Transferencia | llamada con al menos un evento `handoff.requested`; atendida = `handoff.connected` |
| Resultado | `conversations.outcome` (id del `Outcome` del agente) y `goal` (si ese resultado es objetivo) |
| Conversión | `complete`: completó con un resultado que no es `incompleta` ni `fuera_de_tema`; `partial`: algún dato capturado sin completar; `empty`: ningún dato |

## Modelo de datos (migración 0036)

- `conversations.outcome`, `goal`, `conversion` y `llm_input_tokens`/`llm_output_tokens` (suma de los turnos): los
  completa el motor al guardar.
- `tool_runs`: una fila por ejecución de una herramienta del cliente (ok, código HTTP, ms, error).
- `wa_account_status_log`: una fila por cambio de estado, calidad o límite de una cuenta de WhatsApp.
- `tiers.advanced_reports` (clave `advanced_reports` de `services/features.TIER_HAS`): Free no; pagos e Interno sí.

## API

`app/api/routers/reports.py`; consultas en `app/services/report_stats.py`.

Filtros comunes (query): `client_id` (solo admin; vacío = todos), `agent_id`, `channel` (`voice` | `whatsapp` |
`web`), `phone_number_id`, `date_from`/`date_to` (días locales inclusive; por defecto los últimos 30 días), `tz`
(por defecto `BILLING_TIMEZONE`), `include_tests` (default false: sin `prueba` ni conversaciones por API/Playground;
el `loadtest` nunca entra).

| Ruta | Plan | Devuelve |
|---|---|---|
| `GET /reports/summary` | todos | `kpis` y `previous` (período anterior): consultas por canal (`voice_in`, `voice_out`, `whatsapp`, `web`), `with_agent`, conversiones, objetivos, transferencias, minutos, finalizadas, fallidas, duración media, rechazadas por límite, mensajes de WhatsApp; `daily` |
| `GET /reports/calls` | todos | `daily` por modo, `heatmap` (sin directas), `by_line`, `by_agent`, `by_type` (`agent`, `direct`, `team`), `by_user`, `durations` (solo finalizadas), `total`, `ended` por motivo, `early_hangups`, `callers` (nuevos, recurrentes, top) |
| `GET /reports/outcomes` | `advanced_reports` | conversión diaria y por agente, resultados, embudo, captura de cada dato requerido (versión vigente), por versión del agente |
| `GET /reports/messages` | `advanced_reports` | mensajes por día (texto y audio), heatmap, entrega (`sent`, `delivered`, `read`, `failed`), fallas por código, promedio por conversación, cuentas con historial de calidad |
| `GET /reports/transfers` | `advanced_reports` | KPIs (pedidas, atendidas, no atendidas, sin nadie, tiempo de respuesta, minutos), por día, área y persona; WhatsApp (asignadas, primera respuesta, reasignadas) |
| `GET /reports/campaigns` | `advanced_reports` | por campaña (contactos, intentos, alcanzados, completos, objetivo, bajas, minutos), motivos de no contacto, mejores horarios |
| `GET /reports/technical` | admin | latencia p50/p95 por día y etapa (STT, EOU, LLM, TTS), por proveedor del LLM, herramientas (errores, p50/p95), errores, mails de resumen fallidos, tokens |
| `GET /reports/platform` | admin, sin `client_id` | tabla por cliente, alertas (`near_quota` ≥ 80 % de los minutos entrantes; `inactive` 14 días sin conversaciones), negocio (planes, altas, MRR, pagos, morosos, Free → pago), operación (pico de simultáneas, fallas, rechazos) |

Sin el plan: 403 `advanced_reports_not_in_plan` (el admin no tiene el corte). El consumo del plan no está acá:
`GET /clients/{id}/usage` (con `projected_minutes` a fin de mes).

**MCP** (`app/mcp/catalog.py`, grupo `reports`, también con la key `mcp_read`): `get_report_summary` y
`get_report_calls` en todos los planes; `get_report_outcomes`, `get_report_messages`, `get_report_transfers` y
`get_report_campaigns` con `features=("advanced_reports",)`. `get_report_technical` y `get_report_platform` están
en el toolset `admin`. Ver [`MCP.md`](MCP.md).

## Flujo

- Consultas SQL agregadas, sin cargar conversación por conversación. Fechas en UTC naive en la base; días y horas se
  agrupan en `tz`.
- UI en `web/src/features/reports/`, ruta `/reports` (es la portada del panel: `/` redirige ahí). Filtros arriba
  (admin: selector de cliente con "Todos"; agente, canal, período, "Incluir pruebas").
- Pestañas: Resumen, Consumo (del mes de facturación, con su selector de mes; sin los filtros de período, agente ni
  canal), Llamadas, Resultados, Mensajes, Transferencias, Campañas; admin: Técnico y, con "Todos", Plataforma.
- Las del plan muestran candado y el aviso de "Mejorar mi plan"; la UI no las pide hasta saber el plan
  (`/plan/features`), así no da 403.
- CSV: lo arma el navegador con los datos de cada tabla o gráfico ("Descargar CSV").

## Reglas y trampas

- Nada técnico para el cliente (latencia, proveedores, herramientas, errores, tokens): va en Técnico, solo admin.
- Los tokens del LLM y las ejecuciones de herramientas no se reconstruyen hacia atrás: hay historia desde el
  27-oct-2026.
- Al cambiar un reporte: actualizar la sección Reportes de `/desarrolladores/docs/api` en la landing y, si cambian
  las herramientas, `make mcp-docs`.

## Desplegar y probar

- `make reports-backfill`: completa `outcome`, `goal` y `conversion` de conversaciones anteriores a la 0036
  (idempotente, después de `make migrate`).
- Tests: `tests/test_reports.py`, `tests/test_reports_data.py`, `tests/test_migration_0036.py` y
  `web/src/features/reports/ReportsPage.test.tsx` (`make test`, `make web-check`).
- Cambios en la API o el servicio: `make calls-active && make up-agent` (recrea `app`, que trae la UI).

## Pendientes

- Costos estimados por conversación (Anura, plantillas de Meta, tokens BYOK), solo admin: faltan las tarifas en la
  configuración.
