# App Review de Meta (app Atentina)

Paquete para enviar la revisión de la app `Atentina` (ID 2192489028351511, portafolio 897731003277295): permisos
`whatsapp_business_messaging`, `whatsapp_business_management` y `public_profile`. Sin esto (y sin el Tech Provider)
un cliente no conecta su número con la app de Atentina: ver [WHATSAPP.md](WHATSAPP.md). **Sin enviar**: una vez
enviado, Meta no deja editarlo ni cancelarlo, y revisa la app entera (ícono, nombre, URLs de privacidad y de
eliminación de datos). El envío lo hace el usuario.

Los textos para Meta van en inglés; la UI está en español, así que los videos llevan subtítulos en inglés.

## 1. Estado

| Paso | Estado | Qué falta |
|---|---|---|
| Verificación del negocio | Verificada (como *Sole Proprietorship*, nombre legal del titular, nombre alternativo "Atentina") | — |
| Verificación de acceso (Tech Provider) | **En revisión** desde el 1-oct-2026 (Plataforma SaaS, un portafolio, sitio atentina.com.ar). Al 27-oct-2026 seguía en revisión, sin pedidos de Meta y con el portafolio sin restricciones. Plazo de Meta para completarla: 26-dic-2026 (si no, restringe la app) | Nada de nuestro lado. El asistente de la Ayuda para empresas no deriva a personas; hay una [pregunta pública en el foro](https://developers.facebook.com/community/threads/1312250158648768/) |
| Configuración de la app | Incompleta | **Agregar una plataforma** (bloqueo 1) y revisar ícono, categoría y correo de contacto |
| Uso permitido | Llamadas de prueba a la API: hechas | Descripción, video y confirmación de cada permiso (secciones 2 a 4) |
| Tratamiento de datos | Sin responder | Sección 6 |
| Instrucciones para revisores | Bloqueadas por la plataforma | Sección 5 |

Asistente: developers.facebook.com → Revisar → Revisión de la app → solicitud 2192520205015060.

**Bloqueos antes de enviar:**

1. **Plataforma:** Configuración → Básica → Agregar plataforma → Sitio web, URL `https://app.atentina.com.ar/`. Sin
   eso no se cargan las instrucciones para revisores.
2. **Usuario para los revisores** en `app.atentina.com.ar`: un cliente de prueba (por ejemplo "Meta App Review") con
   un tier que incluya WhatsApp y campañas de WhatsApp, usuario y clave propios, el agente de demo y el número de
   WhatsApp de Atentina visibles. Lo crea el usuario; la clave va solo en el formulario de Meta.
3. **Embedded Signup** no se completa hasta que Meta apruebe el Tech Provider (el popup dice "Atentina no puede
   registrar clientes en este momento"). Además está apagado en producción: el botón "Conectar WhatsApp" solo
   aparece con `WA_EMBEDDED_SIGNUP=true` (y `WA_APP_ID`, `WA_APP_SECRET`, `WA_CONFIG_ID`, `WA_TOKEN_KEY`): lo decide
   `GET /api/v1/whatsapp/config` y lo muestra `web/src/features/whatsapp/WhatsAppPage.tsx`. Para grabar el video de
   `whatsapp_business_management` hay que prenderlo (editar `.env` con diff enmascarado y
   `make calls-active && make up-agent`) y apagarlo después si Meta todavía no aprobó. Si Meta pide el alta
   completa, reenviar cuando apruebe el Tech Provider.

La política de privacidad vigente (`app/legal/texts/privacidad/2026-10-28.md`, publicada en la landing) ya lista a
Resend y a Amazon Web Services junto con Meta, Cloudflare, Render y Google: coincide con la sección 6.

## 1b. Requisitos de los videos

Fuentes: [guía de grabaciones de pantalla](https://developers.facebook.com/docs/app-review/submission-guide/screen-recordings/)
y [App Review para WhatsApp](https://developers.facebook.com/docs/whatsapp/solution-providers/app-review/).

**Obligatorios (si falta uno, rechazo):**

1. **Grabación de pantalla real**: nada de capturas animadas ni cursor simulado.
2. **Un video por permiso**: mezclar permisos es motivo de rechazo.
3. **`whatsapp_business_messaging`**: la app mandando un mensaje y el cliente de WhatsApp (web o celular)
   recibiéndolo y mostrándolo.
4. **`whatsapp_business_management`**: la app (o WhatsApp Manager) creando una plantilla de mensaje.
5. **Login completo**, desde la sesión cerrada, con el usuario de revisores.
6. **Autorización del permiso**: el botón de login de Meta ("Conectar WhatsApp"), el usuario dando el permiso y la
   función que lo usa (ver bloqueo 3).
7. **Qué hace la app con los datos**: el resultado de cada acción (mensaje recibido, plantilla creada con su estado).
8. **Subtítulos en inglés** que expliquen cada paso y los botones no obvios.

**Recomendados:** 1080p o más; ventana de 1440 px de ancho o menos; solo la ventana del navegador; mouse en vez de
teclado; cursor agrandado; anotaciones donde se usa el permiso; zoom en lo chico; sin audio.

**Nuestros:** sin datos de terceros (ni conversaciones de prospectos); grabar con el usuario de revisores (vista de
cliente, sin el menú de administración); solo acciones reales.

## 2. `whatsapp_business_messaging`

**Descripción:**

> Atentina (https://atentina.com.ar) is a SaaS platform from Argentina that lets businesses (clinics, gyms,
> collection agencies, retailers) answer their customers with an AI assistant over phone calls and WhatsApp.
> Each business connects its own WhatsApp Business number to Atentina through Embedded Signup, and Atentina
> sends and receives messages on that number on the business's behalf.
>
> We use whatsapp_business_messaging to:
> 1. Receive the messages (text and voice notes) that end users send to the business's WhatsApp number,
>    via our webhook, and download their media (voice notes are transcribed).
> 2. Send the assistant's replies to those end users, as text or as a voice note, inside the 24-hour
>    customer service window. Example: a patient writes "I need an appointment for Tuesday" and the
>    assistant replies with the available times and books it.
> 3. Send approved template messages that the business triggers itself: appointment reminders, payment
>    reminders and follow-ups to its own contacts who opted in. End users can reply "BAJA" (stop) to opt out,
>    and we stop messaging them.
> 4. Register the business's phone number with the Cloud API after Embedded Signup (two-step PIN) and read
>    its business profile.
>
> Every conversation is shown to the business in its Atentina dashboard (Conversations), where it can read
> the transcript and close the conversation. Without this permission the product cannot answer the
> business's customers on WhatsApp, which is its core function. We do not use message content for
> advertising or sell it; data is used only to provide the service to the business that owns the number.

**Confirmación:** marcar "Si se aprueba, confirmo que cualquier información…".

**Video (1–2 min):** alternado entre el panel (Chrome, 1440 px) y WhatsApp Web de un número propio.

| # | Qué se graba | Subtítulo |
|---|---|---|
| 1 | Sesión cerrada → `https://app.atentina.com.ar/login` → usuario de revisores | "A business logs in to its Atentina dashboard." |
| 2 | WhatsApp: el número conectado y su agente | "The business's WhatsApp number is connected to an AI assistant." |
| 3 | WhatsApp Web: el número propio escribe al +54 9 351 700-2592 | "A customer writes to the business on WhatsApp." |
| 4 | WhatsApp Web: llega la respuesta (texto y, si se puede, nota de voz) | "Atentina sends the assistant's reply through the WhatsApp Cloud API; the WhatsApp client receives it." |
| 5 | Conversaciones → esa conversación | "The business sees the conversation in its dashboard." |
| 6 | Campañas → Nueva campaña de WhatsApp → plantilla aprobada → el número propio como único contacto → crear e iniciar | "The business sends an approved template to a contact who opted in." |
| 7 | WhatsApp Web: llega la plantilla | "The WhatsApp client receives and displays the message." |

El paso 6 manda un mensaje real (lo cobra Meta) a un número propio: confirmar antes de grabar.

## 3. `whatsapp_business_management`

**Descripción:**

> Atentina is a Tech Provider: businesses connect their own WhatsApp Business Account to our platform with
> Embedded Signup, from the WhatsApp page of their Atentina dashboard ("Conectar WhatsApp").
>
> We use whatsapp_business_management to:
> 1. Complete Embedded Signup: exchange the code for a business token, read the WhatsApp Business Account
>    and its phone numbers (to confirm which number the business selected), and subscribe our app to the
>    WABA's webhooks.
> 2. Show the business the status of its number in the dashboard: display name, quality rating, messaging
>    limit and connection status, refreshed from Meta on demand.
> 3. Let the business list and create its message templates (Utility and Marketing) from the dashboard,
>    with variables and examples, and see their approval status. These templates are then used for the
>    reminders and campaigns the business sends.
> 4. Receive account_update, phone_number_quality_update and message_template_status_update webhooks, so
>    that a disconnected, disabled or offboarded account stops being used immediately.
>
> Only users of the business that owns the WABA can see or change it in Atentina. Tokens are stored
> encrypted. Without this permission businesses would have to configure everything by hand in WhatsApp
> Manager and share credentials with us, which is exactly what Embedded Signup avoids.

**Confirmación:** marcar la casilla.

**Video (1–2 min)**, con `WA_EMBEDDED_SIGNUP=true` (bloqueo 3):

| # | Qué se graba | Subtítulo |
|---|---|---|
| 1 | Sesión cerrada → login con el usuario de revisores | "A business logs in to its Atentina dashboard." |
| 2 | WhatsApp → "Conectar WhatsApp" → ventana de Meta → da el permiso, elige cuenta y número → vuelve con el número conectado | "The business connects its own WhatsApp Business Account with Embedded Signup and grants Atentina access." |
| 3 | Tabla de números: estado, calidad y límite; "Releer de Meta" | "We read the number's status and quality from Meta." |
| 4 | Plantillas → Nueva plantilla → Utilidad, variables y ejemplos → **Crear** | "The business creates a message template from Atentina." |
| 5 | La plantilla en la lista, "En revisión" (y "Aprobada" al releer) | "The template is submitted to Meta; its approval status is shown live." |

El paso 2 solo se graba completo con el Tech Provider aprobado. El 4 crea una plantilla real en la WABA del
número: confirmar nombre y texto antes de grabar.

## 4. `public_profile`

Solo pide la confirmación. Lo usa Facebook Login for Business dentro del Embedded Signup (identifica a la persona
que conecta la cuenta); no se guardan datos del perfil.

## 5. Instrucciones para revisores

> Atentina is a web dashboard: https://app.atentina.com.ar
>
> Test account: user `<email del usuario de revisores>`, password `<clave>`. It belongs to a test business
> with a WhatsApp number already connected.
>
> 1. Log in. Open "WhatsApp" in the left menu: you will see the connected number (status, quality rating,
>    messaging limit, assigned assistant) and the "Plantillas" (templates) section, where you can create a
>    template. The "Conectar WhatsApp" button starts Embedded Signup.
> 2. To test messaging, send a WhatsApp message from any phone to +54 9 351 700-2592 (for example
>    "Hello, what does Atentina do?"). The AI assistant replies within a few seconds, by text or voice note.
> 3. Open "Conversaciones" (Conversations) in the dashboard to see that conversation and its transcript.
> 4. Open "Campañas" (Campaigns) to see how the business sends an approved template to its own contacts.
>
> The dashboard is in Spanish; the screen recordings have English captions. No special hardware or
> geography is needed.

Menús en `web/src/components/nav.ts`: "Conversaciones" (`/calls`), "WhatsApp" (grupo Canales, `feature: whatsapp`)
y "Campañas" (según `campaign_channels` del plan). El paso 1 menciona "Conectar WhatsApp": si al revisar
`WA_EMBEDDED_SIGNUP` está en false, el botón no aparece; ajustar el texto o dejarlo prendido mientras dure la
revisión.

## 6. Tratamiento de datos (respuestas propuestas)

Son respuestas legales: las decide el usuario.

| Pregunta | Propuesta |
|---|---|
| ¿Encargados con acceso a los Datos de la plataforma? | **Sí**: Cloudflare (red y túnel del webhook), Amazon Web Services (copia de respaldo cifrada en S3), Resend (correos con el resumen de la conversación). Si el cliente lo elige, su proveedor de LLM (OpenAI, Anthropic u OpenRouter); ahí el responsable es el cliente |
| Responsable de los datos | Laureano Martín Arcanio (CUIT 20-30745718-1), titular de la marca Atentina |
| País | Argentina |
| ¿Datos a autoridades por seguridad nacional en 12 meses? | No |
| Procesos ante pedidos de autoridades | Revisión obligatoria de la legalidad; recusar si son ilícitos; minimización de datos; documentación de los pedidos (marcar solo los que se cumplan de verdad) |

## 7. Checklist del envío

- [ ] Plataforma Sitio web agregada (bloqueo 1).
- [ ] Usuario de revisores creado y probado (bloqueo 2).
- [x] Privacidad con Resend y AWS publicada (versión `2026-10-28`).
- [ ] `WA_EMBEDDED_SIGNUP=true` para grabar (bloqueo 3).
- [ ] Video de `whatsapp_business_messaging` que cumpla 1b.
- [ ] Video de `whatsapp_business_management` que cumpla 1b (con el Embedded Signup completo).
- [ ] Textos de las secciones 2, 3 y 5 pegados; casillas de confirmación.
- [ ] Tratamiento de datos respondido (sección 6).
- [ ] Revisión final con el usuario y **Enviar para revisión** (lo hace el usuario).
