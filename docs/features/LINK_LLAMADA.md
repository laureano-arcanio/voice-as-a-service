# Link para llamar

Una URL por agente (`https://llamar.atentina.com.ar/<token>`) para que cualquiera hable con el agente del cliente
desde el navegador, con una pantalla tipo llamada telefónica: "un número de teléfono en forma de link" para la bio,
una firma de mail o la web del cliente. Estado: en producción desde el 19-oct-2026. Plan: `tiers.max_call_links`
(`TIER_HAS["call_links"]`; `NULL` sin tope, `0` no incluido; Free 1).

## Modelo de datos

| Tabla / columna | Qué es | Migración |
|---|---|---|
| `call_links` | `client_id`, `agent_id`, `token` (único, 12 caracteres de `secrets.token_urlsafe(9)`, 72 bits), `display_name` (default el agente), `company_name` (default el cliente), `subtitle`, `max_call_seconds` (300, ≤ `CALL_MAX_DURATION_SECONDS`), `max_concurrent` y `daily_minutes` (nulos: sin tope propio), `paused`, `created_by`, `revoked_at` | 0018 |
| Índice `uq_call_links_agent_active` | Un link activo por agente (`agent_id` donde `revoked_at` es nulo) | 0018 |
| `tiers.max_call_links` | Links activos por cliente | 0018 |
| `call_logs.call_link_id` | Por qué link entró la llamada (filtros y uso) | 0018 |
| `call_links.image` | Logo o foto propia, en `storage/call-links/` (`CALL_LINK_IMAGES_DIR`, en el backup) | 0019 |

- `CallMode.web`: consume **minutos entrantes** (`MINUTE_MODES`). La conversación sigue en el canal `voice`.

## API

Del cliente (`/api/v1`, sesión o API key con acceso al agente; en el panel, pestaña **Link para llamar** del
agente, `web/src/features/agents/CallLinkTab.tsx`):

| Ruta | Qué hace | MCP |
|---|---|---|
| `GET /agents/{id}/call-link` | El link (o null) con URL completa, uso de hoy y del mes, y lo que permite el plan | `get_call_link` |
| `POST /agents/{id}/call-link` | Crea (`display_name`, `company_name`, `subtitle`, `max_call_seconds`, `max_concurrent`, `daily_minutes`, `paused`); 409 si ya hay uno, 429 `call_links_limit` por el plan | `create_call_link` |
| `PATCH /agents/{id}/call-link` | Textos, topes y `paused` (un tope en null queda sin tope propio) | `update_call_link` |
| `POST /agents/{id}/call-link/rotate` | Revoca y crea otro con la misma config y la misma imagen: el viejo da 404 | `rotate_call_link` |
| `DELETE /agents/{id}/call-link` | Revoca (y borra la imagen) | `delete_call_link` |
| `PUT /agents/{id}/call-link/image` | Multipart PNG, JPG o WebP de hasta 5 MB (`BodyLimitMiddleware` deja pasar ese path) | — |
| `DELETE /agents/{id}/call-link/image` | Quita la imagen | — |

Pública (sin auth):

| Ruta | Qué hace |
|---|---|
| `GET /llamar/{token}` (en el host del link, `/<token>`) | La página, con `og:*` y los datos completados en el server; 404 propia si no existe o está revocado |
| `GET /api/v1/public/call-links/{token}` | `{display_name, company_name, subtitle, max_call_seconds, records_audio, available}` |
| `GET /api/v1/public/call-links/{token}/image` | La imagen (también `og:image`) |
| `POST /api/v1/public/call-links/{token}/calls` | `{turnstile_token}` → `{livekit_url, token, max_call_seconds}`. 403 `captcha_failed`, 404 `link_not_found`, 429 `busy` / `rate_limited`, 503 `unavailable` |

## Flujo

Código: `app/services/call_links.py`, `app/api/routers/call_links.py`, `app/api/call_link_host.py` (página y
`CallLinkHostMiddleware`), `web/llamar.html` + `web/src/llamar/` (TS sin React, `livekit-client`, segunda entrada
del build de Vite, con los tokens de la marca de la landing en `llamar.css`).

1. `GET /<token>`: HTML con nombre ("Gaby, asistente de" y la empresa), subtítulo, imagen o iniciales, y "La
   llamada se graba." si el agente tiene `record_audio`. Precarga `livekit-client` y Turnstile.
2. **Llamar** (gesto del usuario): primero el micrófono (si se niega no se gasta admisión ni room), después
   Turnstile y un solo `POST .../calls`.
3. `call_links.start_call`: límite por IP y link (en memoria, `CALL_LINK_IP_CALLS_PER_HOUR` 4 y
   `_PER_DAY` 10, por `CF-Connecting-IP`), link pausado o cliente inactivo, Turnstile, cupo diario del link y
   `calls.start_call` con `call_link_id`: `quota.admit(..., web)` (tier), `max_concurrent` del link y
   `CALL_LINK_MAX_CONCURRENT` (8) entre todos los links.
4. Token de LiveKit solo para esa room (identidad `web-<id>`), con TTL de espera + duración + 120 s. El worker ve
   `call_link_id` en la metadata: la llamada es `web`, espera al navegador `CALL_LINK_JOIN_TIMEOUT_SECONDS` (60) y
   corta por minutos del tier y por `max_call_seconds` del link. El agente puede derivar como en una entrante.
5. La página pasa a "En llamada" cuando el agente publica su pista; subtítulos plegados (`lk.transcription`),
   silenciar, cortar, aviso a los 30 s del final; al terminar, duración y "Volver a llamar". No muestra los datos
   que tomó el agente.

Errores para quien llama (sin "plan" ni "minutos"; el motivo real queda en el log): ocupado ("Todas las líneas
están ocupadas. Probá en unos minutos."), límite por IP ("Hiciste varias llamadas seguidas. Probá más tarde.") y
todo lo demás ("Este canal no está disponible en este momento.").

## Reglas y trampas

- **Host propio:** con el Host de `CALL_LINK_BASE_URL` solo pasan `/<token>`, `/assets/`, la API pública de links
  y unos íconos: sin la cookie ni el panel. Sin la variable, la página queda en `<host del panel>/llamar/<token>`.
  La página tiene su propia CSP (Turnstile y el LiveKit para navegadores) y es la única que permite el micrófono.
- Un link no es secreto: se trata como un número publicado. La protección es de costo (Turnstile, IP, topes del
  link, del tier y global), no de acceso. Sin `TURNSTILE_SITE_KEY` o `TURNSTILE_SECRET_KEY`, "no disponible".
- `CALL_LINK_MAX_CONCURRENT` (8) sin medir con Gemma: no subirlo sin un CAP. Se cuenta con el lock del cliente, no
  uno global: entre clientes distintos puede pasarse por una o dos.
- Si el navegador no entra después del `POST`, la llamada ocupa lugar hasta 60 s.
- La imagen se recorta al cuadrado, se achica a 512 px y se recodifica con Pillow (PNG con transparencia, si no
  JPEG); no se guarda el original. Tope de 40 Mpx antes de decodificar.
- Nada del link entra al prompt (sin `{{variables}}` por query string: sería inyección de prompt).
- LiveKit anuncia la IP pública (`LIVEKIT_NODE_IP`, UDP 7882 y TCP 7881 en el router, `rtc.` por el túnel). No hay
  TURN por TLS/443: redes que bloquean UDP y el 7881 no conectan.
- La grabación la cubre la política de privacidad `2026-10-28` ([LEGAL.md](LEGAL.md)); la página avisa si el
  agente graba.

## Desplegar y probar

- Tests: `tests/test_call_links.py`, `tests/test_migration_0018.py` y `test_migration_0019.py` (en `make test`).
- `.env`: `CALL_LINK_BASE_URL=https://llamar.atentina.com.ar` y `TURNSTILE_SITE_KEY` (la de la landing; el widget
  con hostname `atentina.com.ar` cubre los subdominios). Diff enmascarado antes de reiniciar.
- Ruta del túnel `llamar.atentina.com.ar` → `localhost:8011` (la crea el usuario, [LANDING.md](LANDING.md)).
- Un cambio en la página o la API: `make up-app` (build, migraciones y recreate de `app`, no corta llamadas). Si
  cambia el worker: `make calls-active && make up-agent`.

## Pendientes

- **Una llamada real de punta a punta:** crear el link, abrirlo en el celular (Chrome y Safari) y llamar.
- **Redes sin UDP:** medir cuántas llamadas fallan por ICE antes de decidir montar TURN por 443 (LiveKit lo trae;
  necesita certificado y el puerto TLS).
