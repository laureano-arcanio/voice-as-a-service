# Plan: link para llamar a un agente

Un cliente comparte una URL (`https://llamar.atentina.com.ar/k7Qm2xPa9fRt`) y quien la abre habla con su
agente desde el navegador, como en la demo de la landing pero con el agente, el nombre y la empresa del
cliente. Es "un número de teléfono en forma de link": sirve para la bio de Instagram, una firma de mail,
un QR en el mostrador o un botón en la web del cliente. Diseño del 19-oct-2026; fase 1 implementada el
19-oct-2026 y desplegado ese día (`app`, `agent`, migración 0018 y ruta del túnel `llamar.`); falta una
llamada real de punta a punta (sección 11: desvíos y cómo desplegar).

## 1. Decisiones

| Tema | Decisión | Por qué |
|---|---|---|
| Qué es | Entidad `call_links`, como `phone_numbers`: un link apunta a un agente del cliente | Se revoca y se regenera sin tocar el agente; mismo modelo mental que un número |
| Cuántos | Uno activo por agente (índice único parcial) | Pedido: "una URL por agente". Regenerar = revocar + crear |
| URL | Host propio `llamar.atentina.com.ar/<token>`, token aleatorio de 12 caracteres (`secrets.token_urlsafe(9)`, 72 bits) | Host aparte: sin la cookie de sesión del panel ni su CSP. Token aleatorio: un link revocado no se reemplaza por otro adivinable |
| Quién la sirve | `app`, por el túnel (como `apps.`), con un middleware de host como `AppsHostMiddleware` | La página necesita `og:title` con el agente y la empresa (vista previa en WhatsApp): HTML renderizado en el server, cosa que la landing estática de Render no puede |
| Tipo de llamada | `CallMode.web` nuevo, que **consume minutos entrantes** (`MINUTE_MODES`) | Es una entrante más. `prueba` no consume: si se reusara, un link público sería minutos gratis |
| Plan | Campo de tier `max_call_links` (`NULL` ilimitado, `0` no incluido) | La landing ya ofrece "llamadas web" en Free; se decide por tier sin código |
| Abuso | Turnstile + límites por IP + topes por link + los del tier | El link es público: cualquiera puede gastar los minutos del cliente |
| Qué ve quien llama al final | Duración y "Volver a llamar"; **no** los datos que tomó el agente | Los campos son del cliente, no del que llama (la demo los muestra porque vende el producto) |
| Diseño | Guía de la marca ([`DESIGN_GUIDELINE.md`](DESIGN_GUIDELINE.md)), no la del panel | La ve el cliente final, no un usuario del panel |

## 2. Qué hay hoy (y se reusa)

- **Demo de la landing** (`app/services/demo.py`, `landing/src/scripts/call.ts`): Turnstile → sesión JWT →
  `calls.start_call` → token de LiveKit para la room → el navegador entra con `livekit-client`. Topes por IP
  (`RateLimiter`), por grupo de agentes (`group_max_concurrent`) y cupo diario.
- **LiveKit para navegadores de internet:** ya anuncia la IP pública (`LIVEKIT_NODE_IP`), con UDP 7882 y TCP 7881
  en el router y `rtc.atentina.com.ar` por el túnel. No hay TURN por TLS/443: redes corporativas que bloquean
  UDP y el 7881 no conectan (riesgo, sección 9).
- **Worker:** la room `call-<id>` con la metadata de la llamada; `join_timeout_seconds` corta si nadie entra.
- **Apertura pregenerada** (`conversation.opening_audio`): el link la aprovecha igual que la demo.

La lógica de `demo.py` se generaliza en `app/services/web_calls.py` (sesión, topes por IP, token de LiveKit);
la demo pasa a usarla con su configuración de siempre.

## 3. Modelo de datos (migración 0018)

### 3.1 `call_links`

| Columna | Tipo | Nota |
|---|---|---|
| `id` | uuid | |
| `client_id` | FK `clients`, CASCADE | |
| `agent_id` | FK `agents`, CASCADE | Del mismo cliente (se valida al guardar) |
| `token` | `String(16)`, único | Lo que va en la URL |
| `display_name` | `String(64)` | Nombre que se ve; default `agent.name` |
| `company_name` | `String(128)` | Default `client.name` |
| `subtitle` | `String(120)` | Opcional: "Turnos y consultas", "Atención 24 h" |
| `logo_path` | `String`, nullable | Fase 2. Sin logo: iniciales de la empresa |
| `max_call_seconds` | int, default 300 | ≤ `CALL_MAX_DURATION_SECONDS` |
| `max_concurrent` | int, nullable | Tope de este link, además del del tier |
| `daily_minutes` | int, nullable | Cupo diario del link (`NULL`: solo el del tier) |
| `paused` | bool | Pausado: la página dice "no disponible", el link se conserva |
| `created_at`, `revoked_at` | | Revocado = 404 para siempre |

Índice único parcial `(agent_id) WHERE revoked_at IS NULL`.

### 3.2 Otros cambios

- `tiers.max_call_links` (int, nullable). Seed: Free 1, pagos `NULL`, `Interno` `NULL`.
- `CallMode.web = "web"` y `MINUTE_MODES[CallMode.web] = "inbound"`.
- `call_logs.call_link_id` (FK nullable, SET NULL) para filtrar y reportar por link.
- `conversations.channel` sigue en `voice`; el modo de la llamada distingue el link.

## 4. Flujo de una llamada

```
navegador                      app (llamar.)                              LiveKit / worker
GET /k7Qm2xPa9fRt  ──────────▶ HTML con og:*, nombre, empresa
[Llamar] (gesto del usuario)
getUserMedia (micrófono)
Turnstile (invisible)
POST /api/links/<token>/calls ▶ verifica Turnstile, topes por IP y link,
                                quota.admit(cliente, web), crea la llamada ─▶ dispatch del agente
                    ◀────────── {livekit_url, token, max_seconds}
room.connect(...)  ─────────────────────────────────────────────────────────▶ el agente saluda
[Cortar] / tope / el agente corta ─────────────────────────────────────────▶ cierre y reporte
```

- **Una sola llamada a la API para empezar:** Turnstile va en el mismo `POST` (sin la sesión de dos pasos de la
  demo, que existe porque la landing también sintetiza voces). Menos ida y vuelta = menos espera antes del "hola".
- **Micrófono antes del Turnstile y de crear la llamada:** si el permiso se niega no se gasta admisión ni room.
- **Pre-calentamiento:** al cargar la página, `import("livekit-client")` y el widget de Turnstile; el
  `POST` arranca cuando el usuario toca "Llamar".

## 5. API

### 5.1 Del cliente (`/api/v1`, sesión o API key, con acceso al agente)

| Método | Ruta | Qué hace |
|---|---|---|
| `GET` | `/agents/{agent_id}/call-link` | `{link, plan_max, plan_used, enabled, default_display_name, default_company_name}`: el link (o null, con URL completa y uso de hoy y del mes) y lo que permite el plan |
| `POST` | `/agents/{agent_id}/call-link` | Crea `{display_name?, company_name?, subtitle?, max_call_seconds?, max_concurrent?, daily_minutes?, paused?}`; 409 si ya tiene uno; 429 `call_links_limit` por el tier |
| `PATCH` | `/agents/{agent_id}/call-link` | Textos, topes y `paused` (un tope en null queda sin tope propio) |
| `POST` | `/agents/{agent_id}/call-link/rotate` | Revoca y crea otro con la misma config: el link viejo da 404 |
| `DELETE` | `/agents/{agent_id}/call-link` | Revoca |

### 5.2 Pública (sin auth)

| Método | Ruta | Qué hace |
|---|---|---|
| `GET` | `/llamar/<token>` (en el host del link, `/<token>`) | La página, con metas y datos del link. 404 propia si no existe o está revocado |
| `GET` | `/api/v1/public/call-links/<token>` | `{display_name, company_name, subtitle, max_call_seconds, records_audio, available}` |
| `POST` | `/api/v1/public/call-links/<token>/calls` | `{turnstile_token}` → `{livekit_url, token, max_call_seconds}`. Errores: 403 `captcha_failed`, 404 `link_not_found`, 429 `busy` / `rate_limited`, 503 `unavailable` (pausado, cliente inactivo, sin minutos, cupo diario del link o sin configurar) |

- El texto de los errores públicos **no** dice "tu plan" ni "minutos": quien llama no es el cliente. Se mapean a
  tres mensajes (sección 6.3) y el motivo real queda en el log y en el panel.
- `/api/v1/public/call-links/*` no comparte CORS con la demo: es del mismo origen. CSP de la página: `connect-src` a
  `wss://rtc.atentina.com.ar` y `challenges.cloudflare.com`; `frame-ancestors 'none'` (fase 2: lista por link).

## 6. Página pública

Mobile-first (casi todos los links se abren desde el celular), una sola columna de 360–420 px centrada en
escritorio, solo tema claro como la marca. La metáfora es la pantalla de llamada del teléfono: identidad
arriba, estado en el medio, botones redondos abajo.

### 6.1 Estados

```
 ANTES                 LLAMANDO              EN LLAMADA            TERMINADA
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│                  │  │                  │  │                  │  │                  │
│      ( CS )      │  │    (( CS ))      │  │    ((( CS )))    │  │      ( CS )      │
│                  │  │                  │  │  anillo = voz    │  │                  │
│      Sofía       │  │      Sofía       │  │      Sofía       │  │      Sofía       │
│  Clínica del Sur │  │  Clínica del Sur │  │  Clínica del Sur │  │  Clínica del Sur │
│ Turnos y consultas│ │                  │  │                  │  │                  │
│                  │  │   Llamando…      │  │      02:31       │  │ Llamada finalizada│
│ ● Disponible     │  │                  │  │  Sofía habla…    │  │      02:31       │
│                  │  │                  │  │                  │  │                  │
│                  │  │                  │  │ [Ver subtítulos] │  │                  │
│                  │  │                  │  │                  │  │                  │
│      ( 📞 )      │  │  (🎤)     ( ⏷ )  │  │  (🎤)     ( ⏷ )  │  │ [Volver a llamar]│
│      Llamar      │  │ Silenciar Cortar │  │ Silenciar Cortar │  │                  │
│                  │  │                  │  │                  │  │                  │
│ Usa el micrófono.│  │                  │  │                  │  │                  │
│ Hasta 5 min.     │  │                  │  │                  │  │                  │
│ Atentina         │  │ Atentina         │  │ Atentina         │  │ Atentina         │
└──────────────────┘  └──────────────────┘  └──────────────────┘  └──────────────────┘
```

- **Antes:** avatar (logo o iniciales de la empresa sobre `accent-soft`), nombre del agente en Bricolage,
  empresa en `ink-2`, subtítulo en `muted`, estado "● Disponible" en mono con `ok`. Botón redondo de 72 px en
  `ok` con el ícono de teléfono y la etiqueta "Llamar" debajo. Nota corta: "Usa el micrófono de tu dispositivo.
  La llamada dura hasta 5 minutos." Si el agente graba (`agent.record_audio`): "La llamada se graba."
  Pie: "Con tecnología de Atentina" (link a la landing) + Privacidad.
- **Llamando:** el avatar late (anillo que se expande, 1,2 s); "Llamando…" en mono. Se pasa a "En llamada"
  cuando el agente publica su pista de audio, no al conectar la room.
- **En llamada:** cronómetro `mm:ss` en mono `tabular-nums`; el anillo del avatar sigue el nivel de audio del
  agente (`participant.audioLevel`), así se ve quién habla sin leer. Debajo, "Sofía habla…" / "Te escucha".
  Botones de 64 px: Silenciar (`ghost`, con `aria-pressed`) y Cortar (`warn`). Al faltar 30 s, aviso
  "Queda medio minuto". Subtítulos plegados por defecto ("Ver subtítulos"): la transcripción en vivo
  (`lk.transcription`, como la demo), útil con ruido o hipoacusia.
- **Terminada:** "Llamada finalizada" + duración, "Volver a llamar" (`ghost`). Si cortó el tope: "Se
  alcanzó el tiempo máximo de la llamada."

### 6.2 Micrófono

1. El permiso se pide **solo** al tocar "Llamar" (gesto del usuario), nunca al cargar.
2. Denegado: pantalla con la explicación por navegador ("Tocá el candado de la barra de direcciones →
   Micrófono → Permitir") y "Reintentar". Sin micrófono: "No encontramos un micrófono".
3. Navegador sin WebRTC o sin contexto seguro (raro): "Abrí este link en Chrome, Safari o Firefox".
4. In-app browsers (Instagram, Facebook) suelen bloquear el micrófono: se detectan por user agent y se muestra
   "Abrir en el navegador" antes de intentar.

### 6.3 Errores (texto para quien llama)

| Caso | Mensaje | Acción |
|---|---|---|
| Ocupado (`busy`: tope del tier o del link) | "Todas las líneas están ocupadas. Probá en unos minutos." | Reintentar |
| Límite por IP | "Hiciste varias llamadas seguidas. Probá más tarde." | — |
| Sin minutos, cupo diario, cliente inactivo, pausado | "Este canal no está disponible en este momento." | — |
| Revocado o inexistente | 404: "Este link ya no está activo." | — |
| Se cortó la red | "Reconectando…" (reconexión de LiveKit); a los 15 s, "Se cortó la llamada" | Volver a llamar |
| El agente no entró (`join_timeout`) | "No pudimos conectar la llamada." | Reintentar |

### 6.4 Prácticas

- **Accesibilidad:** botones ≥ 48 px con etiqueta visible; `aria-live="polite"` en el estado; foco al botón
  principal de cada estado; contraste AA (ya lo cumplen los tokens); `prefers-reduced-motion` apaga el latido
  y el anillo de voz (queda el texto).
- **Durante la llamada:** Wake Lock (que no se apague la pantalla), `beforeunload` que pide confirmación,
  `pagehide` cuelga (la room no queda abierta). El audio del agente arranca con el gesto de "Llamar";
  si el navegador lo bloquea, botón "Activar sonido" (ya resuelto en la demo).
- **Calidad:** `echoCancellation`, `noiseSuppression` y `autoGainControl` en la pista; en iOS, la salida por el
  parlante del teléfono.
- **Vista previa al compartir:** `og:title` "Hablá con Sofía · Clínica del Sur", `og:description` el subtítulo,
  `og:image` genérica con el logo de Atentina (fase 2: con el logo del cliente). `noindex`: el link es para
  compartir, no para buscadores.
- **Peso:** página sin framework (TS + CSS), `livekit-client` cargado aparte. Objetivo: interactiva en < 1 s en 4G.
- **Sin cookies ni analytics de terceros.**

### 6.5 Dónde va el código

Entrada aparte de Vite en `web/` (`web/llamar.html` + `web/src/llamar/`), sin Mantine, con los tokens de la
marca copiados en un CSS propio (`--color-*` de `landing/src/styles/global.css`, sin Tailwind). La lógica de
la llamada (conectar, transcripción, mute, cronómetro, desbloqueo de audio) se toma de
`landing/src/scripts/call.ts`. `app` sirve el HTML con los `og:*` completados en el server.

## 7. Panel (`web/`)

En la ficha del agente, sección **"Link para llamar"** (sigue [`DESIGN_GUIDELINE_APP.md`](DESIGN_GUIDELINE_APP.md)):

- Sin link: "Creá un link para que tus clientes hablen con este agente desde el navegador" + "Crear link"
  (deshabilitado con el motivo si el tier no lo incluye).
- Con link: la URL en un campo de solo lectura con **Copiar**, **QR** (descarga SVG/PNG), **Abrir** y
  **Pausar**; "Nombre que se ve", "Empresa" y "Subtítulo" con la vista previa de la tarjeta al lado; topes
  ("Duración máxima", "Llamadas a la vez", "Minutos por día") plegados en "Límites".
- "Regenerar link" en un menú, con confirmación: "El link actual deja de funcionar".
- Uso: llamadas y minutos de hoy y del mes por el link.
- Conversaciones: filtro por canal "Link web" (`mode = web`), y en el detalle, "Entró por el link".

## 8. Seguridad y abuso

| Capa | Mecanismo | Valor inicial |
|---|---|---|
| Bots | Turnstile en cada `POST .../calls` | — |
| Por IP | `RateLimiter` por IP real (`CF-Connecting-IP`) y link | 4 llamadas/hora, 10/día |
| Por link | `max_concurrent`, `daily_minutes`, `max_call_seconds` | sin tope, sin tope, 300 s |
| Por cliente | `quota.admit` con `CallMode.web`: concurrencia, llamadas por hora/día/mes y minutos entrantes del tier | los del tier |
| Global | `WEB_CALLS_MAX_CONCURRENT` (nuevo), para que los links no ocupen el lugar de las entrantes por teléfono | 8, como las campañas: sin medir con Gemma |
| Revocación | `rotate` / `DELETE` | inmediata |

- Un link no es secreto: se trata como un número publicado. La protección es de costo, no de acceso.
- El token de LiveKit es solo para esa room, con `can_publish` de audio y TTL de duración + margen (como la demo).
- Nada del link entra al prompt (sin `{{variables}}` por query string en la fase 1: sería inyección de prompt).

## 9. Riesgos y abierto

- **Redes sin UDP:** sin TURN/TLS por 443 no conectan. Medir cuántas fallan (evento `ice_failed`) antes de
  montar TURN (LiveKit lo trae embebido; necesita certificado y el 443 o un puerto TLS).
- **Capacidad:** cada llamada por link es una llamada más del mismo pipeline; con Gemma no hay CAP. El tope
  global de la sección 8 hasta medir.
- **Legal:** el cliente es responsable del tratamiento; los términos lo tienen que decir. Si el agente graba,
  el aviso en la página es obligatorio (y la landing todavía dice que no se graba audio: ver AGENTS.md).
- **Abierto:** alias legibles (`/clinica-sur`), horario de atención por link (fuera de horario: "Atendemos de
  9 a 18"), datos de quien llama antes de la llamada (nombre, teléfono) como campos precargados.

## 10. Fases

1. **Link y página (MVP):** migración 0018, `web_calls.py` (generaliza la demo), API del cliente y pública,
   página con los estados de la sección 6, sección en la ficha del agente, `CallMode.web` en reportes y filtros.
   Tests: admisión (tier, link, IP), revocado/pausado, mapeo de errores públicos.
2. **Compartir mejor:** QR, logo del cliente (subida a `storage/`), `og:image` por link, botón para la web del
   cliente (`<script>` que abre la página en un popup) y `iframe` con `allow="microphone"` y `frame-ancestors`
   por link.
3. **Demo de la landing sobre links:** los agentes de `DEMO_AGENTS` pasan a ser links del cliente `atentina` y
   `demo.py` queda solo para TTS, contacto y registro.

## 11. Avance

### Fase 1 (19-oct-2026, desplegada ese día; falta una llamada real)

- **Backend:** migración `0018` (`call_links`, `tiers.max_call_links`, `call_logs.call_link_id`),
  `app/models/call_links.py`, `app/services/call_links.py`, `app/api/routers/call_links.py` y
  `app/api/call_link_host.py` (página y `CallLinkHostMiddleware`). `CallMode.web` cuenta como entrante en
  `quota.MINUTE_MODES`; `quota.used_seconds` suma las modalidades que gastan los mismos minutos.
- **Worker:** con `call_link_id` en la metadata la llamada es `web`: espera al navegador como la de prueba y
  corre a la vez el corte por minutos del tier y el de duración máxima del link.
- **Página:** `web/llamar.html` + `web/src/llamar/` (TS sin React, `livekit-client`), segunda entrada del build
  de Vite. **Panel:** pestaña "Link para llamar" en la ficha del agente (`CallLinkTab.tsx`), "Links (uno por
  agente)" en Tiers y en los ajustes de límites, y el modo `web` como "Link web" en Conversaciones.
- **Tests:** `tests/test_call_links.py` (14) y `tests/test_migration_0018.py`; capturas de la página y del
  panel con el backend de desarrollo (`scratch/shots/llamar-*.png`).

### Desvíos respecto del diseño

- API del cliente bajo el agente (`/agents/{id}/call-link`, uno por agente) en vez de `/call-links?agent_id=`.
- Pausado responde 503 `unavailable` (no 423): para quien llama es lo mismo que "no disponible".
- Sin QR ni logo en la fase 1 (quedan para la 2). La vista previa al compartir no tiene `og:image`.
- El tope global (`CALL_LINK_MAX_CONCURRENT`) se cuenta con el lock del cliente, no uno global: entre
  clientes distintos puede pasarse por una o dos llamadas.
- Si el navegador no logra entrar a la room después del `POST`, la llamada ocupa lugar hasta que el worker
  la da por fallida (`CALL_LINK_JOIN_TIMEOUT_SECONDS`, 60 s).

### Cómo desplegar

1. `.env`: `CALL_LINK_BASE_URL=https://llamar.atentina.com.ar` y `TURNSTILE_SITE_KEY` (la misma site key de
   la landing). Diff enmascarado contra el backup antes de reiniciar.
2. Cloudflare (lo hace el usuario), **después** del paso 4: ruta del túnel `llamar.atentina.com.ar` → `localhost:8011`,
   path vacío ([`LANDING.md`](LANDING.md), paso 5). Antes del deploy, ese host serviría el panel entero, como `app.`.
   Turnstile no cambia: el widget tiene el hostname `atentina.com.ar`, que cubre los subdominios.
3. Probar la migración `0018` contra una copia del backup en PostgreSQL; después `make migrate`.
4. Rebuild y recrear `app` (la imagen compila `web/`, con la página nueva) y `agent` (cambió el worker).
   Recrear `agent` corta las llamadas en curso: confirmar antes.
5. Habilitar `max_call_links` en los tiers que corresponda (los existentes quedan sin tope) y probar con un
   agente propio: crear el link, abrirlo en el celular (Chrome y Safari) y llamar.
6. Legal: si un agente graba (`record_audio`), la página lo avisa; la política de privacidad de la landing
   todavía dice que no se graba audio.
