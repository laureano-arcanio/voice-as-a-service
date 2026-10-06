# Landing (atentina.com.ar)

Sitio estático en [`landing/`](../landing/): Astro + Tailwind CSS v4, compilado en el build de
Render ([`render.yaml`](../render.yaml)). La demo (llamar a un agente desde el navegador y
sintetizar texto) usa la API pública `/api/v1/demo` de la app de este server, expuesta por
Cloudflare Tunnel. No hay backend aparte ni base nueva: costo adicional cero.

- **Canónico:** `https://atentina.com.ar/`. `www.atentina.com.ar`, `atentina.com` y
  `www.atentina.com` redirigen ahí con 301.
- **Páginas:** `/` (hub: agentes de voz, producto, soluciones, voces, precios, desarrolladores, demo) y tres
  verticales con su tema de acento: `/turnos` (verde azulado), `/cobranzas` (violeta) y
  `/municipios` (ámbar). Las verticales salen de `src/pages/[vertical].astro` con los datos de
  `src/data/site.ts`. Legales (las pide Meta para WhatsApp): `/privacidad`, `/terminos` y
  `/eliminacion-de-datos`, con el layout `Legal.astro`.
- **Publicar:** push a la rama que sigue Render; solo los cambios en `landing/` despliegan.
- **Diseño:** tokens, componentes, patrones y voz en [`DESIGN_GUIDELINE.md`](DESIGN_GUIDELINE.md).
- **`og.png`, favicon y logos (`docs/brand/`):** se generan en `scratch/logo/` (`build_atentina.py`, y
  `og.html` con Chrome headless a 1200 × 630), con los colores de la guía. El contenido de `og.png` va
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
| `POST /api/v1/demo/tts` | sesión | `{voice, text}`: WAV del TTS, hasta `DEMO_TTS_MAX_CHARS` (300). |
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
| Síntesis por IP | `DEMO_IP_TTS_PER_HOUR` (30); caché de las últimas 32 frases | memoria del proceso |
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
