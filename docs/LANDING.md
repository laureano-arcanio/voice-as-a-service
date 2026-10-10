# Landing (atentina.com.ar)

Sitio estático en [`landing/`](../landing/): Astro + Tailwind CSS v4, compilado en el build de
Render ([`render.yaml`](../render.yaml)). La demo (llamar a un agente desde el navegador y
sintetizar texto) usa la API pública `/api/v1/demo` de la app de este server, expuesta por
Cloudflare Tunnel. No hay backend aparte ni base nueva: costo adicional cero.

- **Canónico:** `https://atentina.com.ar/`. `www.atentina.com.ar`, `atentina.com` y
  `www.atentina.com` redirigen ahí con 301.
- **Páginas** (reestructuración del 9-oct-2026: tres puertas, cada una con su público y su vocabulario; los desarrolladores van primero):
  - `/` (**Home** en el nav), para quien evalúa. Propuesta de valor: la telefonía resuelta y sus costos asociados. Orden: hero (demo de llamada y dos
    botones: "Construir con la API" y "Un agente para mi empresa") → **costos** (un servicio en lugar de seis proveedores) → plataforma en
    tres capas → resultado de una llamada → voces → **precios** (la escalera completa: Free "para probar e integrar" y los planes "con telefonía incluida") → preguntas frecuentes → contacto.
    Sin código ni endpoints.
  - `/desarrolladores`, para quien integra: hero con la animación del agente de programación (`AgentTerminal`) → tres formas de integrarlo →
    API compatible con OpenAI (`CodeTabs` con pedidos reales) → integración agéntica (skills y lo que puede hacer) → voces → **precios** (Free + planes con telefonía) → preguntas frecuentes de la API → pedir acceso.
  - `/desarrolladores/docs`: documentación pública **básica** (URL base, keys y alcances, endpoints, streaming, límites, errores), de
    [`API_INFERENCIA.md`](API_INFERENCIA.md) sin lo que es solo para quien opera. **Pendiente:** la referencia completa de pedidos y respuestas y la API de
    agentes y llamadas (la página lo dice). Al cambiar `API_INFERENCIA.md`, actualizarla.
  - `/casos-de-uso`, para quien tiene un problema de atención: hero y demo → rubros (con "¿Tu caso es otro?") → producto → cómo empieza →
    planes con telefonía (sin Free) → preguntas de negocio → demo con tu caso. Las verticales viven bajo `/casos-de-uso/<slug>`, con su tema de acento:
    `/casos-de-uso/turnos` (verde azulado), `/casos-de-uso/cobranzas` (violeta) y `/casos-de-uso/municipios` (ámbar), desde `src/pages/casos-de-uso/[vertical].astro` con los datos de
    `src/data/site.ts`, y un "← Casos de uso" arriba.
  - Legales (las pide Meta para WhatsApp): `/privacidad`, `/terminos` y `/eliminacion-de-datos`, con el layout `Legal.astro`.
  - Cada página lleva sus precios y su FAQ (`faqGeneral`, `faqBusiness`, `faqDev` en `site.ts`): la unidad es distinta (minutos y números contra
    tokens y pedidos). Los links `/#api` y similares de antes pasaron a `/desarrolladores#api`. Las URL viejas `/turnos`, `/cobranzas` y `/municipios` redirigen (301) a las nuevas, por `render.yaml`.
- **Plan Free (provisorio):** API y panel web, sin telefonía; es la primera tarjeta de precios en `/desarrolladores` (y en `/`, que muestra la escalera completa; `/casos-de-uso` y las verticales solo muestran los planes con telefonía, sin la línea "Todo lo que ofrece Free") (`freePlan` en `site.ts`, mismo
  formato que los demás planes): 20 minutos por mes, llamadas web, acceso a la plataforma web y acceso a la API. Mostrador y
  Sucursal arrancan con "Telefonía incluida" y "Todo lo que ofrece Free". Es contenido de la landing: el tier real se crea
  en Tiers (`max_phone_numbers` en 0; el tope de pedidos por minuto de la API, los cupos `api_*` y la cantidad de agentes
  están por definir). Planes: Mostrador, Sucursal y Red (Central se quitó).
- **Registro (`/registro`):** "Empezar gratis" y los planes con precio llevan a `/registro` (los pagos, con
  `?plan=<nombre>`); "A medida" sigue yendo al contacto. Free: un paso (empresa, nombre, email, clave, Turnstile) y
  al panel. Plan pago con Mercado Pago: paso 1 los datos y paso 2 el pago con tarjeta (Card Payment Brick, sin
  otras opciones); la cuenta se crea con el pago aprobado y va al inicio del panel. Usa `/api/v1/demo/plans`,
  `/demo/signup/check` y `/demo/signup`. Ver [`SUSCRIPCIONES_PLAN.md`](SUSCRIPCIONES_PLAN.md). Los precios son
  finales (sin "IVA aparte"); los que se cobran salen de la base (`tiers.price_ars`).
  - La landing no tiene CSP en Render, así que el SDK de MP (`sdk.mercadopago.com`) carga sin cambios. Si se
    agrega una, sumar los dominios de `MP_HOSTS` (`app/api/http.py`).
- **Publicar:** push a la rama que sigue Render; solo los cambios en `landing/` despliegan.
- **Diseño:** tokens, componentes, patrones y voz en [`DESIGN_GUIDELINE.md`](DESIGN_GUIDELINE.md).
- **`og.png`, favicon y logos (`docs/brand/`):** se generan con `scripts/brand/`: `python scripts/brand/build_atentina.py` (con `fonttools`) escribe los SVG
  en `docs/brand/`, y `og.html` da `og.png` con Chrome headless a 1200 × 630
  (`google-chrome --headless --window-size=1200,630 --screenshot=landing/src/assets/og.png scripts/brand/og.html`), con los colores de la guía. El contenido de `og.png` va
  centrado, dentro del cuadrado central, para que no lo corten las miniaturas cuadradas.

## Desarrollo

```bash
cd landing
cp .env.example .env          # PUBLIC_API_URL y PUBLIC_TURNSTILE_SITE_KEY (la de prueba)
npm ci
npm run dev                   # http://localhost:4321
npm run build                 # dist/
```

Desde la raíz, `make landing-dev` hace `npm install` y `npm run dev`. Con `HOST=1` la sirve en la red, para abrirla desde el celular.

| Archivo | Qué es |
|---|---|
| `src/styles/global.css` | Tokens del diseño (`@theme`) y el acento de cada vertical (`[data-theme]`). |
| `src/data/site.ts` | Agentes de la demo, voces, planes y contenido de cada vertical. |
| `src/components/` | Secciones (`CallWidget`, `Voices`, `Pricing`, …). |
| `src/scripts/api.ts` | Cliente de `/api/v1/demo`: sesión con Turnstile, llamadas, resultado y voz. |
| `src/scripts/call.ts` | Llamada con `livekit-client` (se descarga recién al llamar, ~550 KB). |
| `src/scripts/voices.ts` | Síntesis y reproducción con Web Audio API. |
| `src/scripts/analytics.ts` | Eventos de Google Analytics (ver abajo). |

Para probar la demo en local contra una app con el código nuevo: la app con
`TURNSTILE_SECRET_KEY=1x0000000000000000000000000000000AA` y
`DEMO_ALLOWED_ORIGINS=http://localhost:4321`, y la landing con `PUBLIC_API_URL` apuntando a ella.
El micrófono exige contexto seguro: `localhost` o HTTPS.

**Google Analytics (GA4, `G-VB4V3RVVD3`):** el tag se carga desde `Base.astro` solo si hay
`PUBLIC_GA_ID`, que fija `render.yaml`. En local no se define, así que no se mide. Eventos propios
(GA → Informes → Interacción → Eventos; marcar `generate_lead` y `demo_call_start` como eventos clave):

| Evento | Cuándo | Parámetros |
|---|---|---|
| `demo_call_start` | La llamada de la demo conecta | `agent`, `page` |
| `generate_lead` | Se envía el formulario de contacto | `method`, `page` |
| `contact_click` | Clic en WhatsApp, mail o teléfono | `method` (`whatsapp`, `email`, `telefono`), `page` |
| `voice_sample_play` | Se reproduce una voz de muestra | `voice` |

Para saber qué prospecto entró, los links de los mails llevan UTM
(`?utm_source=email&utm_campaign=<tanda>&utm_content=<empresa>`). En GA se ven en Adquisición.

## Demo: API y flujo

`app/api/routers/demo.py`, `app/services/demo.py`. Sin cuentas: el navegador resuelve Turnstile y
canjea el token por una sesión corta.

| Endpoint | Auth | Qué hace |
|---|---|---|
| `POST /api/v1/demo/sessions` | token de Turnstile | Lo valida con Cloudflare (`siteverify`) y devuelve una sesión JWT de `DEMO_SESSION_MINUTES` (30). |
| `POST /api/v1/demo/calls` | sesión | `{agent, voice?}`: llamada `prueba` con un agente de `DEMO_AGENTS` del cliente `DEMO_CLIENT` (`atentina`). Devuelve `livekit_url`, el token del participante y un `result_token`. |
| `GET /api/v1/demo/calls/{id}` | `result_token` | Estado, resultado (`outcome`), datos extraídos con su `label` y transcripción. |
| `POST /api/v1/demo/tts` | sesión | `{voice, text, format}`, hasta `DEMO_TTS_MAX_CHARS` (300). `format: "pcm"` (lo que usa la landing): audio crudo (16 bits, mono, 24 kHz) que llega mientras el TTS lo genera. `wav` (default): el archivo completo. |
| `POST /api/v1/demo/contact` | sesión | Formulario de contacto (ver abajo). 204. |

1. Al tocar "Iniciar llamada", la página pide el micrófono, abre la sesión y crea la llamada.
2. Se conecta a LiveKit (`wss://rtc.atentina.com.ar`) y publica el micrófono. El worker atiende
   como en una llamada de prueba de la UI.
3. La transcripción se muestra en vivo con los text streams `lk.transcription` que publica el agente.
4. Al cortar (el visitante, el agente al terminar o el tope de duración), la página consulta el
   resultado cada 1 s hasta que la llamada queda finalizada, y muestra el resultado y los datos.

La home ofrece solo `atentina_comercial`, el agente que atiende la línea y el WhatsApp de Atentina, con un
botón a WhatsApp y un link a las verticales ("Hablá con otros agentes"); el "llamá gratis" de la home
muestra esa línea (`phone` del agente en `site.ts`): el 0800-220-1233, con su QR, que Anura manda a
Asterisk y la app rutea a `atentina_comercial` (el WhatsApp sigue en el 351 700-2592). Va en formato
nacional (`tel:08002201233`): con +54 no lo enrutan todas las compañías. Las verticales usan `turnos`,
`cobranzas` y `reclamos`, sin línea propia, así que no ofrecen "llamá gratis".
Todos son del cliente `atentina` (nosotros, el mismo del
WhatsApp y el número propios; hasta el 2-oct-2026 había un cliente `landing` aparte). Solo esos se
pueden llamar desde la landing (`DEMO_AGENTS`): el resto de los agentes de Atentina da 404. El seed
crea los de las verticales desde `app/agents/reference/landing_*.json` y `atentina_comercial` desde el suyo; después se editan como
cualquier agente (UI o API), con versión nueva en cada cambio.

## Formulario de contacto

El `Cta` de cada página lleva un formulario (nombre, empresa, email o teléfono, mensaje) que manda
`POST /api/v1/demo/contact` con la misma sesión de Turnstile que la demo. Código:
`app/services/contact.py`, `landing/src/scripts/contact.ts`.

1. Guarda el pedido en `contact_requests` (migración 0006), con la página y la IP.
2. Avisa por mail con Resend a `CONTACT_TO` (`larcanio@gmail.com`), desde `CONTACT_FROM`, con
   `Reply-To` del interesado: se responde directo desde Gmail.
3. Si Resend falla, el pedido queda igual (`email_status=failed` y `email_error`); sin
   `RESEND_API_KEY`, `disabled`. Pedidos que no llegaron por mail:
   `SELECT * FROM contact_requests WHERE email_status <> 'sent' ORDER BY created_at DESC;`

- Límite por IP: `CONTACT_IP_PER_HOUR` (3) y `CONTACT_IP_PER_DAY` (10).
- Trampa para bots: el campo oculto `website`. Con valor, responde 204 sin guardar.

## Control de abuso

| Capa | Límite | Dónde |
|---|---|---|
| Captcha | Turnstile invisible (`interaction-only`), una vez por sesión | `POST /demo/sessions` |
| Sesiones por IP | `DEMO_IP_SESSIONS_PER_HOUR` (20) | memoria del proceso |
| Llamadas por IP | `DEMO_IP_CALLS_PER_HOUR` (4) y `DEMO_IP_CALLS_PER_DAY` (10) | memoria del proceso |
| Contactos por IP | `CONTACT_IP_PER_HOUR` (3) y `CONTACT_IP_PER_DAY` (10) | memoria del proceso |
| Síntesis por IP | `DEMO_IP_TTS_PER_HOUR` (30); caché de las últimas 32 frases (por formato) | memoria del proceso |
| Simultáneas | `DEMO_MAX_CONCURRENT_CALLS` (3) entre los agentes de la demo (el tier de Atentina no tiene tope) | `calls.prepare_call`, con el lock del cliente |
| Minutos por día | `DEMO_DAILY_MINUTES` (120) entre las llamadas de los agentes de la demo | base (`call_logs`) |
| Duración | `DEMO_CALL_MAX_SECONDS` (180): el agente avisa y corta | worker |
| Conexión | `DEMO_JOIN_TIMEOUT_SECONDS` (60) para entrar a la room; token de LiveKit con vencimiento | worker, token |

- La IP es la de `CF-Connecting-IP` (la pone el túnel); IPv6 se limita por /64. El puerto 8011 no
  se publica en el router: solo se entra por el túnel.
- Un 429 trae `Retry-After`. Los límites por IP se pierden al reiniciar `app` (un solo proceso).
- CORS: solo los orígenes de `DEMO_ALLOWED_ORIGINS`.
- Medido (1-oct-2026): la primera síntesis de una frase de 107 caracteres tarda 1,6 s; repetida
  sale de la caché en 6 ms.

## Infraestructura

```text
navegador ──HTTPS──► atentina.com.ar (Render, estático)
    │
    ├──HTTPS──► api.atentina.com.ar ─┐
    ├──WSS────► rtc.atentina.com.ar ─┴─ Cloudflare Tunnel ─► app :8011 (/api/v1/demo/*), LiveKit :7880
    └──UDP 7882 / TCP 7881 ─────────── router (181.104.113.28) ─► LiveKit (audio WebRTC)

app.atentina.com.ar (dashboard) ──HTTPS── Cloudflare Tunnel ─► app :8011 (todo el host)
```

El túnel no lleva UDP: el audio va directo a la IP fija. LiveKit anuncia la IP pública
(`LIVEKIT_NODE_IP`) y, con `advertise_internal_ip`, también las locales, así el agente y
`livekit-sip` de este host no dependen del NAT loopback del router.

## Alta (una vez)

1. **Render:** New → Blueprint → este repo. Crea el sitio `atentina-landing` con el dominio
   `atentina.com.ar` (y `www`). Cargar `PUBLIC_TURNSTILE_SITE_KEY` en Environment. Anotar el host
   `*.onrender.com` que le asigna.
2. **`atentina.com.ar` en Cloudflare:** agregar el sitio (plan gratis) y, en NIC Argentina,
   delegar el dominio a los dos nameservers que da Cloudflare. NIC solo delega: los registros van
   en Cloudflare.

   | Tipo | Nombre | Destino | Proxy |
   |---|---|---|---|
   | CNAME | `@` | `atentina-landing.onrender.com` | con proxy |
   | CNAME | `www` | `atentina-landing.onrender.com` | con proxy |
   | CNAME | `api` | `<id del túnel>.cfargotunnel.com` | con proxy |
   | CNAME | `rtc` | `<id del túnel>.cfargotunnel.com` | con proxy |
   | CNAME | `wa` | `<id del túnel>.cfargotunnel.com` | con proxy |
   | CNAME | `app` | `<id del túnel>.cfargotunnel.com` | con proxy |
   | A | `sip` | `181.104.113.28` (IP fija) | **solo DNS** (llamadas de WhatsApp, [`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md) 5.4) |

   ID del túnel `atentina-demo`: `16331de8-fb8c-4287-9563-5abd44d6ab3d`. Su configuración (public
   hostnames) es remota: vive en Cloudflare, no en el repo; si se borra el túnel, hay que recrear las
   4 rutas y cambiar el token en `.env`. Al mudar de server no se toca: ver
   [`MIGRACION_SERVER.md`](MIGRACION_SERVER.md), 7.

   `@` y `www` funcionan con proxy (1-oct-2026); si Render no verifica el dominio, pasarlos a
   "solo DNS" hasta que emita el certificado. `api` y `rtc` apuntan al túnel (paso 5).
3. **`atentina.com` en Cloudflare:** no llega a Render, redirige desde Cloudflare.

   | Tipo | Nombre | Destino | Proxy |
   |---|---|---|---|
   | AAAA | `@` | `100::` | con proxy |
   | AAAA | `www` | `100::` | con proxy |

   Rules → Redirect Rules: si el hostname es `atentina.com` o `www.atentina.com`, redirigir 301 a
   `concat("https://atentina.com.ar", http.request.uri.path)`, conservando el query string.
4. **Turnstile:** Cloudflare → Turnstile → Add widget, modo "Invisible", hostname
   `atentina.com.ar` (cubre sus subdominios, `www` incluido). La site key va a Render
   (`PUBLIC_TURNSTILE_SITE_KEY`) y el secret a `.env` del server (`TURNSTILE_SECRET_KEY`). En local
   se usan las claves de prueba de Cloudflare (`landing/.env.example`).
5. **Túnel** (`atentina-demo`, creado el 1-oct-2026; se puede hacer por API con un token con
   permisos Cloudflare Tunnel, Turnstile y DNS): Zero Trust → Networks → Tunnels → Create (cloudflared). Copiar el token a
   `CLOUDFLARE_TUNNEL_TOKEN` en `.env` y `make up-tunnel`. Public hostnames:

   | Hostname | Path | Servicio |
   |---|---|---|
   | `api.atentina.com.ar` | `^/api/v1/demo/` | `http://localhost:8011` |
   | `rtc.atentina.com.ar` | (vacío) | `http://localhost:7880` |
   | `wa.atentina.com.ar` | `^/wa/webhook` | `http://localhost:8011` |
   | `app.atentina.com.ar` | (vacío) | `http://localhost:8011` |

   El mismo túnel sirve el webhook de WhatsApp en `wa.atentina.com.ar` (ver
   [`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md)).

   En `api.` y `wa.`, lo que no coincide con la ruta lo responde el túnel con 404.
   **`app.atentina.com.ar` publica el dashboard entero** (UI, API con sesión o API key y docs solo para
   admin), **sin Cloudflare Access**: la app se defiende sola (límites de login por IP real, sesión
   revocable, CSRF, CSP y HSTS; ver [`ARQUITECTURA.md`](ARQUITECTURA.md), "Autenticación y permisos").
   Creado y en uso (verificado el 6-oct-2026: ingress del túnel y `https://app.atentina.com.ar/health`
   → 200; lo vigila `scripts/ops/healthcheck.sh`). Para recrearlo:
   1. Zero Trust → Networks → Tunnels → `atentina-demo` → Public hostnames → Add: subdominio `app`,
      dominio `atentina.com.ar`, path vacío, servicio HTTP `localhost:8011`. Cloudflare crea el CNAME
      `app` solo; si no, cargarlo a mano (tabla del paso 2).
   2. En la zona `atentina.com.ar`: SSL/TLS → Edge Certificates → **Always Use HTTPS** activado (la app
      igual redirige a `https://` lo que llega por `http://` del túnel, con 308).
   3. Probar: `curl -sI https://app.atentina.com.ar/` trae `strict-transport-security` y
      `content-security-policy`; `curl -sI http://app.atentina.com.ar/` redirige a `https://`; el access
      log de `app` muestra el par `172.24.0.1` (el `gateway` de `TRUSTED_PROXY_CIDRS`) y el login limita
      por la IP de `CF-Connecting-IP`.
   4. En la app de Meta, `app.atentina.com.ar` como dominio de Embedded Signup (ver
      [`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md), 5.3).
6. **Router:** reenviar UDP 7882 y TCP 7881 a 192.168.1.99.
7. **`.env` del server:** `LIVEKIT_NODE_IP=181.104.113.28`, `DEMO_LIVEKIT_URL=wss://rtc.atentina.com.ar`
   y `TURNSTILE_SECRET_KEY`. Aplicar sin tocar la inferencia: `make up-agent` (build de `app` y
   `agent`, migración y seed), `docker compose up -d livekit` y `make livekit-sip` (LiveKit pierde
   los trunks SIP al recrearse). Corta las llamadas en curso.
8. **Correo entrante:** la landing publica `hola@atentina.com.ar`. Cloudflare → `atentina.com.ar`
   → Email → Email Routing → Enable (crea los MX y el SPF; el dominio no tenía, 2-oct-2026).
   Destination addresses: `larcanio@gmail.com`. Routing rules: `hola@` → ese destino (destino y
   regla creados por API el 2-oct-2026), y el catch-all si se quiere todo el dominio. No pasa por
   el server. Activarlo por API pide un token con Zone Settings → Edit, además de Email Routing.
9. **Correo saliente (Resend):** dominio `atentina.com.ar` en Resend, región São Paulo
   (`sa-east-1`), verificado el 2-oct-2026. Se dio de alta por la API de Resend y sus 4 registros se
   cargaron por la API de Cloudflare, en "solo DNS": TXT `resend._domainkey` (DKIM), MX y TXT de
   `send` (rebotes y SPF; no chocan con los MX de Email Routing) y CNAME `rsend`. En `.env`, una key
   de solo envío (`RESEND_API_KEY`) y `CONTACT_TO=larcanio@gmail.com`. Aplicar con `make up-agent`
   (migra la base).
   - **DMARC:** TXT `_dmarc` con `v=DMARC1; p=none; rua=mailto:hola@atentina.com.ar` (solo
     reportes, 2-oct-2026). Endurecer a `p=quarantine` cuando los reportes muestren todo alineado.
   - **Responder como `hola@` desde Gmail:** Configuración → Cuentas → Enviar como → agregar
     `hola@atentina.com.ar`, SMTP `smtp.resend.com`, puerto 465 (SSL), usuario `resend`, clave:
     una API key de Resend. Gmail manda el código de confirmación a `hola@`, que llega por el paso 8.
10. **Google Search Console:** propiedad de dominio `atentina.com.ar` (TXT en Cloudflare) y enviar
   `https://atentina.com.ar/sitemap.xml`.

## Pendiente

- **App:** `app.atentina.com.ar` ya sirve la UI (paso 5). Falta que `app.atentina.com` redirija ahí
  con la misma Redirect Rule (hoy no resuelve) y sumar el link "Ingresar" en la landing.
- **Redes con UDP bloqueado:** sin TURN sobre TLS (443), el audio usa TCP 7881; si también está
  bloqueado, la llamada no conecta.

## Demo de voces con streaming de audio

La demo de voces (`landing/src/scripts/voices.ts`) pide `POST /demo/tts` con `format: "pcm"` y reproduce el audio **a medida
que el TTS lo genera**, con Web Audio (`pcm-player.ts`: lee el stream, pasa Int16 a Float32 y encadena los bloques en el
`AudioContext`). Un `<audio>` no reproduce PCM en streaming.

- **Cuándo suena:** el motor entrega un bloque de ~80 ms y a los ~0,4 s uno de 2 s, y de ahí uno de 2 s cada ~0,4 s (la
  síntesis es ~5 veces más rápida que la reproducción). El reproductor junta 0,5 s de audio antes de empezar para que no
  haya un corte entre el primer bloque y el segundo: suena a los **~0,5 s** (medido en Chrome, 9-oct-2026) en vez de
  esperar la síntesis entera (1,9 s para 189 caracteres, 4,2 s para 420).
- **Repetir:** al terminar de llegar, el audio queda en un `AudioBuffer`; volver a dar play suena al instante, sin otro
  pedido ni otro descuento del límite por IP (con la misma voz y texto). La caché del servidor también guarda el PCM.
- **Mientras se genera** no se sabe cuánto dura: la barra espera y el tiempo muestra `0:02 / …` hasta que llega todo.
- **Si el servidor tarda** más que el audio (GPU saturada), hay un corte hasta que llega el siguiente bloque; el sonido
  sigue apenas llega.
- `pcm-player.ts` es una **copia** de `web/src/lib/pcmPlayer.ts` (la landing es otro paquete): un test del dashboard
  (`pcmPlayer.parity.test.ts`) falla si se desvían. Cambiar los dos juntos.
- **En producción (9-oct-2026, Chrome, `atentina.com.ar` por el túnel `api.`):** el audio llega escalonado (primer bloque a los
  168 ms, síntesis completa a los 1.717 ms) y suena a los 645 ms: Cloudflare no acumula la respuesta.
- **La primera vez de cada visita tarda más (~2,6 s hasta sonar):** incluye el Turnstile y la creación de la sesión. Las
  siguientes ya usan la sesión y suenan a los ~0,6 s. Chrome automatizado no pasa el Turnstile, así que esta demo se prueba
  a mano en un navegador real.

## Animación del hero de `/desarrolladores` (`AgentTerminal.astro`)

Una terminal al estilo de Claude Code (fondo gris cálido, coral, `>` del pedido, `●` de cada acción y `⎿` de su resultado) donde un
agente de programación opera la plataforma. Dos escenas que se alternan (la caja mide la más alta y no cambia de tamaño):

1. **Cobranza (primero):** "En facturas/ tengo los PDF de las facturas vencidas. Programá las llamadas para cobrarles el martes, y
   volvé a llamar en 15 días a los que no hayan pagado". Lee los PDF (64 → 58 clientes), programa las llamadas del martes 10:00
   (`POST /api/v1/calls × 58`, con barra de progreso) y agenda el seguimiento a los 15 días. **La API no programa horarios:** el
   martes y los 15 días los agenda el agente de programación (cron o similar) y la API recibe las llamadas cuando toca.
2. **Confirmación de turnos:** "tengo turnos.csv con 240 pacientes, llamalos a todos para confirmar el turno de mañana", lee el CSV,
   hace `POST /api/v1/calls` por cada número, descarga los resultados con `GET /api/v1/calls?limit=240` y escribe `resultados.csv`
   (198 confirmaron, 31 reagendar, 11 no atendieron).

Los endpoints son reales (con una API key `calls`; la lista admite hasta 500); los nombres, teléfonos y cifras son de ejemplo. Las
llamadas que haga una campaña quedan sujetas a las llamadas a la vez del plan.

- HTML y JS, sin video ni dependencias: ~10 s por escena (~20 s el ciclo), en bucle y solo mientras está a la vista
  (`IntersectionObserver`). Con `prefers-reduced-motion` y sin JavaScript muestra la primera escena completa.
- Los colores de la terminal son locales (`--term-*`): representan otra herramienta y no son tokens de la marca.
- No lleva el logo ni la interfaz exacta de Claude Code, y los nombres de herramientas van solo como texto (sección agéntica).
- **Skills para Claude Code, Cursor y Codex:** la sección `AgenticSection` (debajo de la API) las presenta como disponibles,
  sin marca de "próximamente". Al publicarla, tienen que existir: hoy no hay skills publicadas.
- Va en el hero de `/desarrolladores`; la home (`/`) muestra la demo de llamada (`CallWidget`), coherente con las "llamadas web" del
  plan Free.