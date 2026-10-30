# Landing (atentina.com.ar)

Sitio estático en `landing/` (Astro + Tailwind CSS v4), compilado en el build de Render (`render.yaml`). La demo
(llamar a un agente desde el navegador, sintetizar texto), el formulario de contacto y el registro usan la API
pública `/api/v1/demo` de `app`, expuesta por Cloudflare Tunnel. Estado: en producción desde el 1-oct-2026.
Diseño, textos y voz: [`DESIGN_GUIDELINE.md`](../DESIGN_GUIDELINE.md).

## Páginas

Canónico `https://atentina.com.ar/`. `www.atentina.com.ar` (Render), `atentina.com` y `www.atentina.com`
(Redirect Rule de Cloudflare) redirigen con 301.

| Ruta | Para quién / qué es | Archivo |
|---|---|---|
| `/` | Quien compra (los desarrolladores van a `/desarrolladores`). En orden: portada de resultado ("Agentes con IA que atienden a tus clientes por teléfono y WhatsApp", "Empezar gratis" y "Para desarrolladores", demo `CallWidget`; sin superlativos); video de la plataforma (`#video`, `AutoVideo`, `landing-plataforma` v1); canales (`Channels`: íconos propios en SVG de WhatsApp, teléfono y web, poco texto, y las industrias); el panel (`PlatformBuilder`, con el video mudo `landing-panel` v2, vertical 4:5); voces; un servicio en lugar de seis proveedores (`Costs compact`) como entrada de los precios (con Free); tu asistente de IA (`AgentIntegration`); preguntas del comprador (`faqHome`) y contacto. "Una plataforma, tres capas" y "Cada conversación termina en datos" quedaron fuera de la home (en `/plataforma` y en el punto de datos del panel). | `src/pages/index.astro` |
| `/desarrolladores` | Quien integra: hero `AgentTerminal`, API compatible con OpenAI (`CodeTabs`), integración agéntica (`AgenticSection`), voces, precios, FAQ de la API. | `src/pages/desarrolladores/index.astro` |
| `/desarrolladores/docs` | Portada de la documentación: "MCP o API" y "Cómo funciona". Un script manda los links viejos con ancla a `/docs/api` (y `#mcp` a `/docs/mcp`). | `desarrolladores/docs/index.astro` |
| `/desarrolladores/docs/mcp` | Conectar Claude, ChatGPT, Cursor u otro agente por MCP; qué incluye cada plan; herramientas por grupo. Datos de `src/data/mcp-tools.json`. | `desarrolladores/docs/mcp.astro` |
| `/desarrolladores/docs/api` | API de inferencia, llamadas, contactos, campañas, webhook, llamadas directas, reportes; tabla de planes. | `desarrolladores/docs/api.astro` |
| `/desarrolladores/docs/tu-propio-agente` | Contrato del agente externo (endpoint compatible con OpenAI del cliente). | `desarrolladores/docs/tu-propio-agente.astro` |
| `/casos-de-uso` y `/casos-de-uso/<slug>` | Quien tiene un problema de atención. Verticales `turnos` (verde azulado), `cobranzas` (violeta), `municipios` (ámbar), con su `data-theme`. En `/casos-de-uso`, debajo de la portada, el video de atención punta a punta (`#video`, `AutoVideo`): propio en `public/videos/` (v2 de `marketing/videos/proyectos/atencion-punta-a-punta`, recomprimida: 2,7 MB, 1080p, audio 96 kb/s), arranca solo y mudo al entrar en pantalla y se lee por los subtítulos quemados; mientras carga, fondo blanco con las barras del logo y el video entra con un fundido (empieza en blanco: sin salto); el poster solo sin autoplay; los archivos llevan la versión en el nombre (`<proyecto>-vN.mp4`) porque Cloudflare y el navegador los guardan horas (un 404 pedido durante un deploy quedó en caché 5 min); botón de pausa, sin autoplay con `prefers-reduced-motion`, y "Escuchar con sonido" lo reinicia con audio y controles (evento `video_sound`). En YouTube: `k-Fpnre1rd0`. Planes sin Free. | `casos-de-uso/[vertical].astro` + `verticals` en `site.ts` |
| `/canales` y `/canales/<canal>` | Por dónde atiende el agente, para que se entienda (sobre todo WhatsApp, que se busca mucho): `whatsapp` (mensajes, notas de voz con respuesta en audio, llamadas de WhatsApp, pase a una persona en las llamadas, campañas; en el hero una conversación de WhatsApp animada en HTML, `WhatsAppDemo.astro`), `llamadas-telefonicas` (agente, herramientas, derivación en orden o rotación con música y aviso, si nadie atiende toma el mensaje, salientes, teléfono del equipo) y `llamadas-web` (link para llamar). Resumen de WHATSAPP, EQUIPO_TELEFONIA, LINK_LLAMADA, HERRAMIENTAS y CAMPANAS: solo lo que está en producción (en WhatsApp la derivación es solo en llamadas, no en mensajes). Se listan con un ícono chico en el menú ("Por canal"), en `/casos-de-uso#industrias` y en el footer. | `canales/[canal].astro` + `src/data/channels.ts` |
| `/casos-de-uso/<industria>` | Una página por rubro para posicionar por búsqueda: `automotriz`, `educacion`, `inmobiliario`, `retail`, `salud`, `seguros`, `servicios`. H1 con el término de búsqueda (`h1`, "Agentes con IA para …") y el beneficio como bajada (`headline`); qué hace el agente en el rubro, cómo funciona, una llamada de ejemplo (`SampleResult`), voces con un saludo del rubro, preguntas frecuentes del rubro (FAQPage), precios y contacto; enlaza las páginas por necesidad que aplican. Solo lo que la plataforma hace hoy. Con la misma plantilla, "Otros usos": `traduccion-en-tiempo-real` (el agente hace de intérprete en la llamada; se ofrece mientras se termina de implementar, sin producción todavía), `creadores-de-contenido` (locuciones con las voces para redes y publicidad, y traducción de guiones) y `transcripcion-de-llamadas` (llamadas del equipo desde el panel, transcriptas en vivo sin agente); sin demo de agente, la portada ofrece pedir una demo y escuchar las voces. Se listan en el menú, en `/casos-de-uso#industrias` y en el footer. | `IndustryPage.astro` (servida por `casos-de-uso/[vertical].astro`) + `src/data/industries.ts` |
| `/plataforma` y `/plataforma/<slug>` | Una página por capacidad para posicionar por término: `voces-argentinas`, `transcripcion`, `whatsapp`, `telefonia`, `telefono-del-equipo`. Sin nav propio: se llega por el footer, las tarjetas de `Platform` y los `Feature.href` de las verticales. | `plataforma/[slug].astro` + `capabilities` en `site.ts` |
| `/registro` | Registro (Free o plan pago con `?plan=<nombre>`). `noindex`. | `registro.astro`, `src/scripts/signup.ts` |
| `/laureano-arcanio` | Perfil del fundador con `Person` en JSON-LD. Fuera del nav, en el sitemap. | `laureano-arcanio.astro` |
| `/privacidad`, `/terminos` (+ `/privacidad/<versión>`, `/terminos/<versión>`) | Textos legales con versión, copiados de `app/legal/texts/` por `make legal-sync` a `src/data/legal/`. Ver [`LEGAL.md`](LEGAL.md). | `LegalDoc.astro`, `src/data/legal.ts` |
| `/eliminacion-de-datos` | La pide Meta para WhatsApp. | `eliminacion-de-datos.astro` |
| `/arrepentimiento`, `/baja` | Botón de arrepentimiento y de baja (`ConsumerRequest` con `kind` `revocation` / `cancellation`) → `POST /api/v1/demo/consumer-requests`. | `src/components/ConsumerRequest.astro` |
| `404.html` | Render la sirve para toda URL inexistente. `noindex`. | `404.astro` |

- Para sumar una capacidad o una vertical: un objeto más en `capabilities` / `verticals` de `site.ts`; el footer y
  `/plataforma` la toman solos.
- Redirecciones 301 en `render.yaml`: `/turnos`, `/cobranzas`, `/municipios` → `/casos-de-uso/<slug>`;
  `/asistentes` → `/`; `/desarrolladores/mcp` → `/desarrolladores/docs/mcp`.
- Navegación de la documentación: `DocsPage.astro` + `src/data/docs-nav.ts` (los `id` son los de cada `<section>`);
  al sumar o renombrar una sección, cambiarla ahí.
- Cada página lleva sus precios y su FAQ (`faqGeneral`, `faqBusiness`, `faqDev` en `site.ts`): la unidad cambia
  (minutos y números contra tokens y pedidos). `/` muestra la escalera completa (`freePlan` + planes con
  telefonía); `/casos-de-uso` y las verticales, solo los planes con telefonía.

### Documentación de desarrolladores: mantenerla al día

| Si cambia... | Actualizar |
|---|---|
| Herramientas del MCP o sus descripciones | `make mcp-docs` (regenera `src/data/mcp-tools.json`; `tests/test_mcp.py` falla si queda viejo). No editar el JSON a mano. |
| Un tier (precio, funciones, `advanced_reports`, `direct_calls`, `external_agent`, ...) | Tabla de planes de `/docs/api`, `/docs/mcp` (vía `make mcp-docs`) y `/docs/tu-propio-agente`; tarjetas de planes en `site.ts`. |
| Reportes (`/api/v1/reports/*`) | Sección "Reportes" de `/docs/api` y las tarjetas de `site.ts` ("Reportes básicos" / "Reportes completos"). |
| API de inferencia ([`API_INFERENCIA.md`](../API_INFERENCIA.md)), llamadas, campañas o llamadas directas | Su sección en `/docs/api`. La referencia completa es el OpenAPI del panel. |
| Contrato del agente externo (`app/llm/external.py`) | `/docs/tu-propio-agente`. |

## Planes y registro

- Planes en la landing: Free, Mostrador, Sucursal (con precio) y Red (a medida, la cotiza un asesor, no es un tier).
  Free: API y panel, sin telefonía, 20 minutos por mes de llamadas web. Los precios que se cobran salen de
  `tiers.price_ars` (`GET /api/v1/demo/plans`); son finales, sin "IVA aparte".
- `/registro`: Free en un paso (empresa, nombre, email, celular, clave, Turnstile) y al panel (al asistente de
  primera vez, [`PRIMERA_VEZ.md`](PRIMERA_VEZ.md)). Plan pago: paso 1 los datos,
  paso 2 la tarjeta con los **campos seguros de Mercado Pago** (SDK v2, Core Methods, `src/scripts/mercadopago.ts`);
  el token va como `card_token_id` a `POST /demo/signup` y la cuenta se crea con el pago aprobado. Ver
  [`COBROS.md`](COBROS.md).
- No se usa el Card Payment Brick: para tarjetas en las que MP marca el código de seguridad como opcional
  (Mastercard, Mastercard Prepaid de MP, Naranja) el Brick no lo pide y la suscripción rechaza el token
  ("Card token was generated without cvv validation"). Los campos propios lo piden siempre.
- La landing no tiene CSP en Render; si se agrega una, sumar los dominios de `MP_HOSTS` (`app/api/http.py`).

## Demo: API y flujo

Código: `app/api/routers/demo.py`, `app/services/demo.py`; en la landing `src/scripts/{api,call,voices,contact}.ts`.
Sin cuentas: el navegador resuelve Turnstile y canjea el token por una sesión corta. Sin `TURNSTILE_SECRET_KEY`
la demo responde 503.

| Endpoint | Auth | Qué hace |
|---|---|---|
| `POST /api/v1/demo/sessions` | token de Turnstile | Valida con `siteverify` y devuelve una sesión JWT de `DEMO_SESSION_MINUTES` (30). |
| `POST /api/v1/demo/calls` | sesión | `{agent, voice?}`: llamada `prueba` con un agente de `DEMO_AGENTS` del cliente `DEMO_CLIENT`. Devuelve `livekit_url`, token del participante y `result_token`. |
| `GET /api/v1/demo/calls/{id}` | `result_token` | Estado, `outcome`, datos extraídos con su `label` y transcripción. |
| `POST /api/v1/demo/tts` | sesión | `{voice, text, format}`, hasta `TTS_PREVIEW_MAX_CHARS` (200, el mismo de la prueba del dashboard). Lo que llega al motor queda en Uso de la API del cliente Atentina como `voice_test_landing`. `pcm` (lo que usa la landing): 16 bits mono 24 kHz en streaming; `wav` (default): archivo completo. |
| `POST /api/v1/demo/contact` | sesión | Formulario de contacto. 204. |
| `GET /api/v1/demo/plans` | — | Planes y precios públicos. |
| `POST /api/v1/demo/signup/check`, `/signup` | Turnstile | Registro (ver arriba). |
| `GET /api/v1/demo/legal` | — | Versiones vigentes de los textos legales. |
| `POST /api/v1/demo/consumer-requests` | — | Arrepentimiento y baja (`consumer_requests`). |

Flujo de una llamada: pide el micrófono → sesión → `POST /calls` → conecta a LiveKit (`wss://rtc.atentina.com.ar`,
`DEMO_LIVEKIT_URL`) y publica el micrófono; el worker atiende como una llamada de prueba. La transcripción en vivo
sale de los text streams `lk.transcription`. Al cortar, la página consulta el resultado cada 1 s hasta que queda
finalizada. `livekit-client` (~550 KB) se descarga recién al llamar. El micrófono exige `localhost` o HTTPS.

**Agentes de la demo** (`DEMO_AGENTS`, default `atentina_comercial,turnos,cobranzas,reclamos`, todos del cliente
`atentina`): la home ofrece `atentina_comercial` (el mismo de la línea 0800-220-1233 y el WhatsApp), con botón a
WhatsApp y link a las verticales; las verticales usan `turnos`, `cobranzas` y `reclamos`, sin línea propia. Otro
agente de `atentina` da 404. El seed los crea desde `app/agents/reference/`; después se editan por UI o API
(versión nueva por cambio). El 0800 va en formato nacional (`tel:08002201233`): con +54 no lo enrutan todas las
compañías.

**Demo de voces en streaming:** `voices.ts` pide `format: "pcm"` y reproduce con Web Audio (`pcm-player.ts`). El
reproductor junta 0,5 s antes de empezar para no cortar entre el primer bloque (~80 ms) y el segundo (2 s): suena a
los ~0,6 s en producción (primer bloque a 168 ms, síntesis completa a 1,7 s; Cloudflare no acumula). La primera vez
de cada visita, ~2,6 s (incluye Turnstile y sesión). Repetir sale del `AudioBuffer`, sin otro pedido.
`pcm-player.ts` es copia de `web/src/lib/pcmPlayer.ts`: `pcmPlayer.parity.test.ts` falla si se desvían.

**Menú:** "Casos de uso" es un link a `/casos-de-uso` y, en escritorio, con el mouse encima o el foco adentro despliega
las industrias y las páginas por necesidad (solo CSS; Tailwind aplica el hover solo con mouse, así que Chrome headless
no lo abre sin `--blink-settings=primaryHoverType=2,availableHoverTypes=2`). En celular, el link de siempre.

**Sección de voces** (`Voices.astro`, `#voces`; el nav tiene "Voces" y lleva ahí): las 12 destacadas (`voices` en
`site.ts`) en tarjetas chicas de tres por fila con su retrato, y al lado un reproductor compacto con el retrato de la
elegida. Las 41 voces tienen retrato (`public/voces/<voz>.svg`): son los mismos del dashboard y
de cada voz en toda la aplicación: los genera `make voces-retratos` (`scripts/brand/voces_retratos.py`) en las dos
carpetas; una voz nueva con retrato va también en `PORTRAITS` de `web/src/features/voices/names.ts`.

### Formulario de contacto

`Cta` de cada página → `POST /demo/contact` con la sesión de Turnstile (`app/services/contact.py`,
`src/scripts/contact.ts`). Guarda en `contact_requests` (página e IP) y avisa por Resend a `CONTACT_TO` desde
`CONTACT_FROM`, con `Reply-To` del interesado. Si Resend falla queda `email_status=failed` con `email_error`; sin
`RESEND_API_KEY`, `disabled`. Campo oculto `website` como trampa: con valor responde 204 sin guardar.

### Control de abuso

| Capa | Límite (default) | Dónde |
|---|---|---|
| Captcha | Turnstile invisible (`interaction-only`), una vez por sesión | `POST /demo/sessions` |
| Sesiones por IP | `DEMO_IP_SESSIONS_PER_HOUR` (20) | memoria |
| Llamadas por IP | `DEMO_IP_CALLS_PER_HOUR` (4), `DEMO_IP_CALLS_PER_DAY` (10) | memoria |
| Contactos por IP | `CONTACT_IP_PER_HOUR` (3), `CONTACT_IP_PER_DAY` (10) | memoria |
| Síntesis por IP | `DEMO_IP_TTS_PER_HOUR` (30); caché de las últimas 32 frases por formato | memoria |
| Simultáneas | `DEMO_MAX_CONCURRENT_CALLS` (3) entre los agentes de la demo (el tier de `atentina` no tiene tope) | `calls.prepare_call`, lock del cliente |
| Minutos por día | `DEMO_DAILY_MINUTES` (120) entre esos agentes | `call_logs` |
| Duración | `DEMO_CALL_MAX_SECONDS` (180): el agente avisa y corta | worker |
| Derivación | `DEMO_HANDOFF` (default `false`, `true` en producción): los agentes con áreas (`atentina_comercial` → Ventas) transfieren al equipo; suenan teléfonos reales y gasta minutos y canales de Anura; la charla entra en `DEMO_CALL_MAX_SECONDS`. Ver [`EQUIPO_TELEFONIA.md`](EQUIPO_TELEFONIA.md). | `calls.start_call` + worker |
| Conexión | `DEMO_JOIN_TIMEOUT_SECONDS` (60); token de LiveKit con vencimiento | worker |

- IP real de `CF-Connecting-IP` (la pone el túnel); IPv6 se limita por /64. Un 429 trae `Retry-After`.
- Los límites por IP viven en memoria: se pierden al reiniciar `app` (un solo proceso).
- CORS: solo `DEMO_ALLOWED_ORIGINS` (default `https://atentina.com.ar,https://www.atentina.com.ar`).
- Caché de síntesis: una frase de 107 caracteres tarda 1,6 s la primera vez y 6 ms repetida.

## Infraestructura

```text
navegador ──HTTPS──► atentina.com.ar (Render, estático)
    ├──HTTPS──► api.atentina.com.ar ─┐
    ├──WSS────► rtc.atentina.com.ar ─┴─ Cloudflare Tunnel ─► app :8011 (/api/v1/demo/*), LiveKit :7880
    └──UDP 7882 / TCP 7881 ─────────── router (IP fija) ─► LiveKit (audio WebRTC)
```

- **Render:** Blueprint `render.yaml`, sitio `atentina-landing`, `rootDir: landing` (solo los cambios en `landing/`
  despliegan), `npm ci && npm run build`, Node 22. Variables: `PUBLIC_API_URL=https://api.atentina.com.ar`,
  `PUBLIC_TURNSTILE_SITE_KEY` (en el dashboard de Render), `PUBLIC_GA_ID`. Headers de seguridad y caché de
  `/_astro/*` en el mismo archivo. Publicar: push a la rama que sigue Render.
- **Túnel `atentina-demo`** (`docker-compose.tunnel.yml`, `cloudflared` con `network_mode: host`, `make up-tunnel`,
  `CLOUDFLARE_TUNNEL_TOKEN` en `.env`). Las rutas son configuración remota en Cloudflare, no están en el repo; si
  se borra el túnel hay que recrearlas y cambiar el token. Al mudar de server no se toca
  ([`MIGRACION_SERVER.md`](../MIGRACION_SERVER.md)).

  | Hostname | Path | Servicio | Qué es |
  |---|---|---|---|
  | `api.atentina.com.ar` | `^/api/v1/demo/` | `localhost:8011` | Demo, contacto, registro |
  | `rtc.atentina.com.ar` | — | `localhost:7880` | Señalización de LiveKit |
  | `wa.atentina.com.ar` | `^/wa/webhook` | `localhost:8011` | Webhook de WhatsApp ([`WHATSAPP.md`](WHATSAPP.md)) |
  | `app.atentina.com.ar` | — | `localhost:8011` | Panel entero, sin Cloudflare Access: la app se defiende sola ([`ARQUITECTURA.md`](../ARQUITECTURA.md), "Autenticación y permisos") |
  | `llamar.atentina.com.ar` | — | `localhost:8011` | Link para llamar ([`LINK_LLAMADA.md`](LINK_LLAMADA.md)); con `CALL_LINK_BASE_URL`, `app` solo sirve ahí la página y su API |
  | `telefono.atentina.com.ar` | — | `localhost:8011` | Teléfono del equipo ([`EQUIPO_TELEFONIA.md`](EQUIPO_TELEFONIA.md)); con `PHONE_APP_BASE_URL`, ídem |

  En `api.` y `wa.`, lo que no coincide con el path lo responde el túnel con 404. El puerto 8011 no se publica en
  el router. `scripts/ops/healthcheck.sh` vigila `app.` (`/health` → 200) y `wa.` (verificación → 403).
- **LiveKit con IP pública:** el túnel no lleva UDP. LiveKit anuncia `LIVEKIT_NODE_IP` (la IP fija) y, con
  `advertise_internal_ip`, las locales, así el agente y `livekit-sip` no dependen del NAT loopback del router. El
  router reenvía UDP 7882 y TCP 7881 al server. Cambiar `LIVEKIT_NODE_IP` recrea LiveKit, que pierde los trunks:
  después `make livekit-sip` (corta llamadas en curso).
- **DNS** (zona `atentina.com.ar` en Cloudflare; NIC Argentina solo delega a sus nameservers):

  | Tipo | Nombre | Destino | Proxy |
  |---|---|---|---|
  | CNAME | `@`, `www` | `atentina-landing.onrender.com` | sí |
  | CNAME | `api`, `rtc`, `wa`, `app`, `llamar`, `telefono` | `<id del túnel>.cfargotunnel.com` | sí |
  | A | `sip` | IP fija | solo DNS (llamadas de WhatsApp por TLS 5061) |
  | MX/TXT | Email Routing | `hola@atentina.com.ar` → Gmail | — |
  | TXT/MX/CNAME | `resend._domainkey`, `send`, `rsend` | Resend (región `sa-east-1`) | solo DNS |
  | TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:hola@atentina.com.ar` | — |

  `atentina.com`: AAAA `@` y `www` a `100::` con proxy y una Redirect Rule 301 a
  `concat("https://atentina.com.ar", http.request.uri.path)` conservando el query string. "Always Use HTTPS"
  activado en la zona (la app igual redirige `http://` con 308).
- **Turnstile:** widget invisible, hostname `atentina.com.ar` (cubre subdominios). Site key en Render, secret en
  `.env` (`TURNSTILE_SECRET_KEY`). En local, las claves de prueba de Cloudflare (`landing/.env.example`).

## SEO

Palabras clave por página dueña (la que lleva el término en `h1` y `title`; el resto la linkea con ese ancla). Texto:
voseo, sin superlativos, categoría "agentes con IA que atienden a tus clientes" ("agente de voz" solo en `metaTitle`).

| Grupo | Términos | Página dueña |
|---|---|---|
| Voces argentinas | voces argentinas con IA, TTS en español rioplatense, API de síntesis de voz | `/plataforma/voces-argentinas` |
| Transcripción | transcripción de audio en español, speech to text API | `/plataforma/transcripcion` |
| WhatsApp | WhatsApp con IA para empresas, WhatsApp Business API, campañas por WhatsApp | `/plataforma/whatsapp` |
| Telefonía y SIP | telefonía IP para empresas, 0800 virtual, SIP trunk Argentina, central con IA, llamadas salientes automáticas | `/plataforma/telefonia` |
| Teléfono del equipo | llamar y atender desde el navegador | `/plataforma/telefono-del-equipo` |
| Agentes | agente de voz con IA, agente telefónico, automatizar atención al cliente | `/casos-de-uso` y verticales |
| Industrias | agente de voz con IA para concesionarias, institutos, inmobiliarias, comercios, clínicas, aseguradoras, empresas de servicios | `/casos-de-uso/<industria>` (`metaTitle` de cada una) |
| Canales | atención por WhatsApp con IA, atención telefónica con IA, llamadas web con IA | `/canales/<canal>` (`/plataforma/whatsapp` y `/plataforma/telefonia` quedan con WhatsApp Business API, telefonía IP, 0800 y SIP) |
| Otros usos | traducción de llamadas en tiempo real, voces con IA para publicidad y redes, transcripción de llamadas en vivo | `/casos-de-uso/traduccion-en-tiempo-real`, `/creadores-de-contenido`, `/transcripcion-de-llamadas` |
| API y LLM | API de voz, API compatible con OpenAI, inferencia en Argentina | `/desarrolladores`, `/desarrolladores/docs` |
| Empresas | soluciones de IA para empresas, agentes con IA para empresas | `/` |

- SIP se cuenta como "corre sobre SIP, consultanos si tenés central o proveedor propio", nunca como trunk
  autoservicio (hoy se arma a mano). Las páginas de capacidad tienen 600 a 900 palabras de texto propio.
- **JSON-LD:** `Base.astro` recibe `schema?: object[]` y lo suma a `Organization` (siempre: logo PNG 512 × 512
  `src/assets/logo-512.png`, `contactPoint` con el 0800, email y `areaServed` AR). Helpers en `src/data/schema.ts`:
  `WebSite` (home), `Service` con planes como `Offer` en ARS por mes, `FAQPage` con los mismos `items` que `Faq`,
  `BreadcrumbList` (verticales y capacidades). JSON con `<` escapado. Validar con la prueba de resultados
  enriquecidos de Google después de cada deploy.
- **Sitemap:** `@astrojs/sitemap` en `astro.config.mjs` → `sitemap-index.xml`, sin `lastmod` (con la fecha del
  build todas las páginas cambiaban en cada deploy), sin `/registro`, `/404` ni las versiones de `/terminos` y
  `/privacidad`; `public/robots.txt` apunta ahí.
- **Metas:** `robots` `index, follow, max-image-preview:large` por defecto; prop `noindex` de `Base` (usado en
  `/registro`, el 404 y `/terminos/<versión>` y `/privacidad/<versión>`, que competían con la vigente).
- **Hosts del panel** (`app.`, `telefono.`, `llamar.` y cualquier otro que llegue al app): `web/public/robots.txt`
  con `Disallow: /`. Sin él, la SPA devolvía su `index.html` y Google rastreaba las URLs de la API que aparecen en
  los ejemplos de `/desarrolladores/docs/api` (9 páginas con 401 y 404 en Search Console, oct-2026). `og:image:alt` y `twitter:*` salen de los mismos props. Un `h1` por página, todo dentro de
  `<main>`.
- **Fuentes propias** (`@fontsource-variable/bricolage-grotesque` con eje opsz, `@fontsource-variable/figtree`,
  `@fontsource/ibm-plex-mono` 400 y 500) importadas en `global.css`, con `preload` de los woff2 latinos de
  Bricolage y Figtree en `Base.astro`. Los tokens usan las familias `Bricolage Grotesque Variable` y
  `Figtree Variable`. Medido en `/` (Chrome por CDP, sin caché): con Google Fonts, escritorio LCP ~205 ms y CLS
  0,125; con fuentes propias, LCP 76 a 80 ms y CLS 0. En móvil lento (CPU ×4, 1,6 Mbps) LCP 784 a 840 ms, CLS 0.
  Sin el `preload`, el CLS de escritorio vuelve a 0,13–0,17.
- **`og.png`, favicon y logos** (`docs/brand/`): `python scripts/brand/build_atentina.py` escribe los SVG y
  `scripts/brand/og.html` da `og.png` a 1200 × 630 con Chrome headless
  (`--screenshot=landing/src/assets/og.png`). Contenido centrado en el cuadrado central (miniaturas cuadradas).

## Google Analytics

GA4 (`PUBLIC_GA_ID`, fijado en `render.yaml`); en local no se define y no se mide. Eventos en
`src/scripts/analytics.ts`; marcar `generate_lead` y `demo_call_start` como eventos clave en GA.

| Evento | Cuándo | Parámetros |
|---|---|---|
| `demo_call_start` | Conecta la llamada de la demo | `agent`, `page` |
| `generate_lead` | Se envía el contacto | `method`, `page` |
| `sign_up` | Termina el registro | `method`, `plan` |
| `contact_click` | Clic en WhatsApp, mail o teléfono | `method`, `page` |
| `voice_sample_play` | Suena una voz de muestra | `voice` |

Los mails comerciales llevan UTM (`utm_source=email&utm_campaign=<tanda>&utm_content=<empresa>`); el CRM cruza
esos datos ([`CRM.md`](CRM.md)).

## Desarrollo y prueba

```bash
make landing-dev          # npm install + npm run dev en :4321; HOST=1 la abre en la red (celular)
cd landing && cp .env.example .env && npm run check && npm run build
```

- `.env` de la landing: `PUBLIC_API_URL` y `PUBLIC_TURNSTILE_SITE_KEY` (la de prueba).
- Demo en local contra una app propia: la app con `TURNSTILE_SECRET_KEY=1x0000000000000000000000000000000AA` y
  `DEMO_ALLOWED_ORIGINS=http://localhost:4321`; la landing con `PUBLIC_API_URL` apuntando a ella.
- Chrome automatizado no pasa Turnstile: la demo de voces y la llamada se prueban a mano en un navegador real.
- Al cambiar textos legales: `make legal-sync`. Al cambiar el MCP: `make mcp-docs`.

| Archivo | Qué es |
|---|---|
| `src/styles/global.css` | Tokens (`@theme`) y acento por vertical (`[data-theme]`). |
| `src/data/site.ts` | Agentes de la demo, voces (`voices`, las 12 destacadas con retrato; `allVoices`, las 41 de `tts/finetune/voces.tsv`), planes, verticales, capacidades, `skillTools`. |
| `src/data/schema.ts` | JSON-LD por página. |
| `src/data/mcp-tools.json` | Generado por `make mcp-docs`. |
| `src/data/legal/` | Generado por `make legal-sync`. |
| `src/components/AgentTerminal.astro` | Hero de `/desarrolladores`: terminal estilo agente de programación que opera la API con dos escenas (cobranza, confirmación de turnos). Endpoints reales, cifras de ejemplo; la API no programa horarios (lo agenda el agente del usuario). Colores locales `--term-*`, no tokens de marca. Con `prefers-reduced-motion` o sin JS, la primera escena completa. |

## Pendientes

- **Link "Ingresar" al panel:** el nav (`Nav.astro`) no lo tiene. Tampoco resuelve `app.atentina.com` (falta
  sumarlo a la Redirect Rule hacia `app.atentina.com.ar`).
- **Redes con UDP bloqueado:** sin TURN sobre TLS (443), el audio cae a TCP 7881; si también está bloqueado, la
  llamada no conecta.
- **Search Console:** importar la propiedad en Bing Webmaster Tools.
- **DMARC:** está en `p=none`; endurecer a `p=quarantine` cuando los reportes muestren todo alineado.
