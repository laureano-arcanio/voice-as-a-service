# Tutorial agente Free en el celular (vertical)

Video para un cliente con plan Free: cómo crear un agente básico (una parrilla, con precios), probarlo desde el
navegador del celular, compartir el link para llamar y ver la transcripción en el portal; al final, qué traen los
planes pagos. Capturas reales del panel (`web/`) a 390 px con un cliente Free.

## Pedido

> crear un video de cómo crear un agente y cómo probarlo desde la vista mobile para un plan free. El workflow:
> iniciar la aplicación, ir a Agentes, crear un agente básico, por ejemplo para un restaurante con algunas opciones
> de precios. Mostrar también que se puede copiar el link y compartirlo para que otras personas lo usen, que no
> necesitan hacer nada más, y que con eso ya pueden atender llamadas y ver las transcripciones en el portal.
> Explicar también que las funcionalidades más avanzadas, como transferencias de llamadas y registro de pedidos,
> turnos, etc., están en los planes Mostrador y Central. Un video corto y práctico.

(Textual resumido, tal como llegó del agente que delegó.) Formato de referencia: `primeros-pasos` y `derivaciones`.

## Público y mensaje

Cliente recién registrado en el Free. Mensaje: en un par de minutos tenés un agente que atiende por un link, sin
número ni instalación, y ves cada conversación en el panel; lo avanzado está en los planes pagos.

Formato 1080 × 1920 (9:16), 62,5 s, una sola voz (`paula`) y música propia.

## Guion

| Escena | Voz | Qué se dice | Qué se ve |
|---|---|---|---|
| `intro` | f1 | Con el plan Free, armás tu agente y lo probás desde el celular. Te muestro cómo. | Fondo oscuro, logo, "PLAN FREE · PRIMEROS PASOS", "Tu agente, creado y probado **desde el celular.**" |
| `agentes` | f2 | Entrá a la aplicación, abrí el menú, Agentes, y tocá Nuevo agente. | Inicio → menú (candados en Canales y Organización) → Agentes → Mis agentes (vacío) → toque en Nuevo agente. |
| `nombre` | f3 | Ponele un nombre, por ejemplo, para una parrilla, y creá el agente con el asistente básico. | Modal Nuevo agente: "Atención El Fogón", descripción "Menú, precios y horarios", Asistente básico; acercamiento del 12 % y Crear agente. |
| `definicion` | f4 | Contale quién es, y en la base de conocimiento cargá el menú, los precios y los horarios. Después, guardá. | Rol "asistente virtual de la parrilla El Fogón"; Base de conocimiento que se escribe línea a línea (horarios, parrillada $ 38.000, menú del día $ 14.000, docena de empanadas $ 18.000), con acercamiento; Guardar versión nueva → "Versión 2 guardada." |
| `probar` | f5 | Para probarlo, abrí Probar y tocá Probar agente. Le hablás desde el navegador, como si fueras un cliente. | Pestaña Probar → Probar por voz → toque en Probar agente → Llamada de prueba (Hablando…, Silenciar, Cortar) y la conversación. |
| `link` | f6 | En Link para llamar, creá el link y copialo. Compartilo por donde quieras. | Pestaña Link para llamar → Crear link → URL con copiar → "Link copiado" y un mensaje genérico con el link. Subtítulo: "Usa los minutos del plan: 20 por mes en Free." |
| `quien` | f7 | Quien lo abre, toca Llamar y habla con tu agente. No tiene que instalar nada ni registrarse. | Página pública del link: "Sofía, asistente de El Fogón", Disponible, Llamar → en llamada 00:24 con subtítulos. |
| `conversaciones` | f8 | Con eso, tu agente ya atiende. Cada llamada queda en Conversaciones, con su transcripción. | Conversaciones (4) → detalle: origen Link web, Consulta resuelta, datos obtenidos y la conversación completa. |
| `planes` | f9 | Para pasar llamadas a tu equipo, tener tu propio número o atender por WhatsApp, están los planes pagos: Mostrador, Sucursal y Central. | Menú con candados y "Free" junto a Plan → Equipo con el aviso "Tu plan Free no incluye el equipo… Mostrador, Sucursal y Central" → Mejorar mi plan → Planes (Mostrador y Sucursal). |
| `cierre` | f10 | Creá tu primer agente hoy, gratis. | Fondo oscuro, logo, "Creá tu primer agente. **Gratis.**", `app.atentina.com.ar`. |

## Afirmaciones y fuentes

- **Free (tabla `tiers` de producción, leída el 24-oct-2026):** 20 min entrantes, 0 salientes, 0 números, 1 link
  para llamar, sin equipo (`max_team_members=0`), sin WhatsApp, sin campañas ni contactos (migración 0025,
  [`docs/FUNCIONES_POR_PLAN_PLAN.md`](../../../../docs/FUNCIONES_POR_PLAN_PLAN.md)).
- **Equipo/derivaciones, número propio y WhatsApp en Mostrador, Sucursal y Central:** los tres tienen
  `max_team_members` sin tope, `whatsapp=true` y 1, 3 y 6 números. Es el mismo texto del aviso del panel
  (`app/services/features.py`, `_where`). Central no se vende por el panel (`public=false`, sin precio) y no
  aparece en Planes; en la landing el plan grande se llama "Red".
- **Probar agente:** "Hablás con el agente desde el navegador… No marca ningún teléfono ni gasta minutos."
  (`web/src/features/calls/TestCallButton.tsx`).
- **Link para llamar:** quien lo abre habla desde el navegador; usa minutos entrantes del plan
  (`CallLinkTab.tsx`, [`docs/LINK_LLAMADA_PLAN.md`](../../../../docs/LINK_LLAMADA_PLAN.md), desplegado el
  19-oct-2026). "Sin instalar nada ni registrarse": la página pública es web, con Turnstile y el permiso del
  micrófono.
- **Conversaciones con transcripción y datos obtenidos:** `CallDetailPage.tsx`, origen "Link web" (`labels.ts`).
- **Asistente básico, voz `sofia`, apertura y datos por defecto:** `app/agents/templates/asistente.json`.
- **Guardar crea una versión nueva:** GUIA_UI, "Crear el agente".
- **Sin cifras** de latencia ni capacidad.

**Ilustrativo:** la parrilla "El Fogón", la usuaria Marta, el texto de la base de conocimiento y sus precios, el
mensaje con el link, el token del link, la llamada de prueba, la llamada por el link y las cuatro conversaciones
(mocks: `GET /calls` y `GET /calls/<id>` interceptados; la página pública pasada a "en llamada" por el DOM; la
página de la llamada de prueba pasada a "en llamada" por su estado de React). Todo lo demás son capturas reales.

## Capturas

Reales, del panel (`web/`, Vite :5175, con el código del working tree del 24-oct-2026) contra un backend de
desarrollo aislado (SQLite propia, :8113, sin LiveKit, Resend ni WhatsApp; Turnstile y LiveKit con valores de
mentira solo para habilitar la página del link), en Chrome headless a 390 × 844, DPR 2. No se tocó el stack en
vivo ni se creó ninguna llamada (los `POST /calls` se responden o cortan en el navegador). Scripts en
`capturas/`:

1. `capturas/backend.sh` y `VITE_API_PROXY=http://127.0.0.1:8113 npx vite --port 5175` en `web/`.
2. `capturas/seed.py` (tiers como los de producción, cliente Free "El Fogón" y su usuaria).
3. Copiar `tafm_lib.mjs` y `tafm_video.mjs` a `scratch/shots/` (tiene puppeteer) y `node tafm_video.mjs`; las
   capturas van a `public/proyectos/tutorial-agente-free-mobile/capturas/` y los toques a `capturas/taps.json`.

## Decisiones

- **Voz única** `paula`, ortografía normal, sin grafías forzadas.
- **Planes en la locución:** "Mostrador, Sucursal y Central" (lo que dice el panel), no "Mostrador y Central".
- **Sin "registro de pedidos y turnos":** no es una función de ningún tier (ver NOTAS, "A revisar").
- **Toques y zoom:** círculo azul en cada toque; tres acercamientos suaves que vuelven (nombre, base de
  conocimiento, aviso de Equipo).

## Versiones

| Versión | Estado | Qué cambió |
|---|---|---|
| v1 | borrador | Primera versión: diez escenas con capturas reales del panel Free a 390 px, 62,5 s. |
