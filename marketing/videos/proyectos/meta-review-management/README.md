# App Review de Meta: `whatsapp_business_management`

Grabación de pantalla para el **App Review de Meta** (app Atentina): muestra cómo el panel
(`https://app.atentina.com.ar`) usa el permiso `whatsapp_business_management`. Hecha **solo con capturas reales del
panel**, con cámara suave, un cursor que va hasta cada botón antes del cambio de pantalla y **subtítulos en inglés**.
**Sin locución** (nuestras voces son en español) y **sin música** (la pista de audio es silencio). Los textos para el
formulario de Meta están en [`docs/features/META_APP_REVIEW.md`](../../../../docs/features/META_APP_REVIEW.md).

## Pedido

> Hacé un video nuevo para el App Review de Meta: proyecto `meta-review-management` (v1), siguiendo marketing/VIDEOS.md
> (...). Contexto: Meta pide una "grabación de pantalla" que muestre cómo nuestra app (Atentina, dashboard en
> https://app.atentina.com.ar) usa el permiso `whatsapp_business_management`. Los revisores de Meta no leen
> español: el video lleva **subtítulos en inglés** grandes y legibles, **sin locución** (nuestras voces son en
> español) y sin música o con música muy baja. Tiene que parecer una grabación de la app real: usá **solo las
> capturas reales** de abajo, a pantalla completa, con movimientos de cámara suaves (zoom/paneo a la parte que
> importa), un cursor animado que va hasta el botón antes de cada cambio de pantalla, y transiciones simples. Nada
> de ilustraciones, personajes ni pantallas inventadas: Meta rechaza lo que no sea la app. 16:9, 1920×1080, MP4,
> entre 60 y 120 s. Al inicio una placa corta en inglés: "Atentina — WhatsApp Business Management
> (whatsapp_business_management)" y al final "Atentina · app.atentina.com.ar".
>
> (Siguen la lista de capturas c00, m01 a m06, con la advertencia de privacidad de Operadores, y el guion de 6
> subtítulos; textual en el pedido del 25-oct-2026, resumido en el guion de abajo.)

## Público, mensaje y formato

- **Público:** los revisores de Meta (App Review), que no leen español.
- **Mensaje:** Atentina usa `whatsapp_business_management` solo para conectar la cuenta propia del negocio
  (Embedded Signup), mostrar el estado de su número y administrar sus plantillas.
- **Formato:** 1920 × 1080, 30 fps, H.264 + AAC (silencio), 80,0 s. No se sube a ningún lado desde acá: el usuario
  lo adjunta en el formulario.

## Capturas

Las originales (PNG del panel, 1784 px de ancho; login 1452 px; ventana de Meta 562 × 670) están en
`scratch/meta-review/caps/`. `capturas/preparar.py` las copia a `public/proyectos/meta-review-management/capturas/`
y **desenfoca (pixelado + gaussiano) las filas de la tabla Operadores** en m01 a m05, que tienen nombres y
teléfonos de personas reales; el modal de m03, m04 y m05 queda nítido. Las copias de `public/` (las que se
versionan) ya no tienen esos datos.

```bash
cd marketing/videos/proyectos/meta-review-management/capturas && python3 preparar.py ../../../../../scratch/meta-review/caps
```

## Guion (subtítulos en inglés)

| # | Tiempo | Captura y movimiento | Cursor | Subtítulo |
|---|---|---|---|---|
| 0 | 0,0–5,0 | Placa oscura: logo, "WhatsApp Business Management", `whatsapp_business_management`, "Screen recording of the Atentina dashboard · app.atentina.com.ar" | — | — |
| 1 | 4,6–11,2 | `c00-login`: zoom al formulario de ingreso | Email → clic en **Ingresar** | A business logs in to its Atentina dashboard. |
| 2a | 10,8–15,8 | `m01-whatsapp`: página entera → zoom arriba a la derecha | Clic en **Conectar WhatsApp** | The business connects its own WhatsApp Business Account with Meta's Embedded Signup. |
| 2a | 15,4–21,8 | `m04-conectar`: zoom al modal (cliente y agente elegidos) | Cliente → Agente → clic en **Conectar WhatsApp** | (sigue) |
| 2b | 21,4–32,0 | `m05-esperando-meta` ("Seguí los pasos en la ventana de Meta…"); la cámara se aleja y entra `m06-popup-meta` como ventana flotante | Va a **Continuar como…** de la ventana de Meta y hace clic | Meta's window: the business authorizes Atentina and picks its WhatsApp Business Account and number. |
| 3 | 31,6–45,6 | `m01-whatsapp`: página → zoom a la tabla de números (estado, calidad, token, alta) → paneo a Plantillas | Número → "Conectado" → Calidad → clic en el selector de número de Plantillas | After signup the number appears connected: / we read its status, quality rating and messaging limit from the WhatsApp Business Management API and subscribe our app to its webhooks. |
| 4 | 45,2–54,8 | `m02-plantillas`: selector en +54 9 351 700-2592 · Atentina, zoom a la fila `hello_world` "Aprobada" | hello_world → Aprobada → clic en **Nueva plantilla** | The business lists its message templates and their approval status, live from Meta. |
| 5 | 54,4–66,8 | `m03-nueva-plantilla`: modal arriba (nombre, categoría, cuerpo) → paneo abajo (ejemplos, **Crear**) | Nombre → Categoría → Cuerpo → Ejemplo {{1}} → Ejemplo {{2}} → se posa en **Crear** (sin clic: no hay captura del resultado) | It creates new templates (Utility or Marketing) with variables and examples; Meta reviews each one. |
| 6 | 66,4–75,4 | `m02-plantillas`: la página entera, alejándose despacio | — | We use whatsapp_business_management only to onboard the business's own account, show its number status and manage its templates. |
| 7 | 75,0–80,0 | Placa oscura: logo y `app.atentina.com.ar` | — | — |

Fundido de 0,4 s entre tomas. Subtítulos en Figtree 600 de 42 px sobre una caja oscura (90 %), abajo al centro.

## Afirmaciones y fuentes

- **Embedded Signup → token, WABA y números, suscripción a webhooks:** `app/whatsapp/signup.py` (`subscribed_apps`,
  líneas ~150 y ~235) y `app/whatsapp/graph.py` (`subscribed_apps`, `phone_numbers` con `quality_rating`).
  Fase 2 de [`docs/features/WHATSAPP.md`](../../../../docs/features/WHATSAPP.md): desplegada, **falta la aprobación de
  acceso de Meta** (por eso este video).
- **Estado, calidad y límite de mensajes del número:** `quality_rating` en `signup.py` y `messaging_limit` en
  `app/whatsapp/service.py` (~914).
- **Plantillas leídas y creadas en Meta:** `graph.py` (`GET`/`POST /{waba_id}/message_templates`); categorías
  Utilidad y Marketing en `web/src/features/whatsapp/Templates.tsx`.
- **Textos del formulario:** [`docs/features/META_APP_REVIEW.md`](../../../../docs/features/META_APP_REVIEW.md).
- **Sin pantallas inventadas:** todo lo que se ve son las capturas; lo único agregado son las placas, el cursor, los
  subtítulos y el desenfoque de Operadores.

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 25-oct-2026 | 80,0 s | Primera versión | borrador |
