# App Review de Meta (app Atentina)

Paquete para el envío de la revisión de la app `Atentina` (ID 2192489028351511, portafolio 897731003277295):
permisos `whatsapp_business_messaging`, `whatsapp_business_management` y `public_profile`. Contexto en
[`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md), 3.3 y 5.3. Armado el 25-oct-2026, **sin enviar**: una vez enviado,
Meta no deja editarlo ni cancelarlo, y revisa la app entera (ícono, nombre, URLs de privacidad y de
eliminación de datos).

Los textos para Meta van en inglés (los revisores no siempre leen español); la UI está en español, así que
los videos llevan subtítulos en inglés.

## 1. Estado del formulario (25-oct-2026)

Asistente en developers.facebook.com → Revisar → Revisión de la app → solicitud 2192520205015060.

| Paso | Estado | Qué falta |
|---|---|---|
| Verificación | Negocio verificado; Tech Provider **en revisión** desde el 1-oct | Nada de nuestro lado |
| Configuración de la app | Incompleta (barra a medias) | **Agregar una plataforma** (Sitio web) en Configuración → Básica: sin eso no se pueden cargar las instrucciones para revisores. Revisar ícono, categoría y correo de contacto |
| Uso permitido | Llamadas de prueba a la API: hechas (las dos) | Descripción, video y confirmación de cada permiso (secciones 2 a 4) |
| Tratamiento de datos | Sin responder | Sección 6 |
| Instrucciones para revisores | Bloqueado por la plataforma | Sección 5, con un usuario para los revisores |

**Bloqueos antes de enviar:**

1. **Plataforma:** Configuración → Básica → Agregar plataforma → Sitio web, URL `https://app.atentina.com.ar/`.
2. **Usuario para los revisores** en `app.atentina.com.ar`: un cliente de prueba (por ejemplo "Meta App
   Review", tier con WhatsApp) con un usuario y clave propios, el agente de demo y el número de WhatsApp de
   Atentina visibles. Lo crea el usuario; la clave va solo en el formulario de Meta, no en el repo.
3. **Política de privacidad:** `landing/src/pages/privacidad.astro` lista Meta, Cloudflare, Render y Google,
   pero no **Resend** (manda los resúmenes de llamada con la transcripción) ni **Amazon Web Services** (copia
   cifrada del backup en S3). Meta compara la política con las respuestas de tratamiento de datos: agregarlos
   antes de enviar.
4. **Embedded Signup** no se puede completar hasta que Meta apruebe el Tech Provider (popup: "Atentina no
   puede registrar clientes en este momento"). El video de `whatsapp_business_management` muestra el botón
   y el popup de Meta, y el resto con nuestro número (plantillas, estado, calidad). Si Meta lo pide completo,
   reenviar cuando aprueben el Tech Provider.

## 2. `whatsapp_business_messaging`

**Descripción (campo "Describe cómo tu app usa este permiso"):**

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
> the transcript, take over, or block a number. Without this permission the product cannot answer the
> business's customers on WhatsApp, which is its core function. We do not use message content for
> advertising or sell it; data is used only to provide the service to the business that owns the number.

**Confirmación:** marcar "Si se aprueba, confirmo que cualquier información…".

**Video (2–3 min), guion:**

| # | Pantalla | Subtítulo en inglés |
|---|---|---|
| 1 | Navegador: `https://app.atentina.com.ar/login`, entrar con el usuario de revisores | "A business logs in to its Atentina dashboard." |
| 2 | Menú WhatsApp: número de Atentina conectado, estado, calidad y agente asignado | "The business's WhatsApp number is connected and assigned to an AI assistant." |
| 3 | Teléfono (o WhatsApp Web) de una persona: escribe al +54 9 351 700-2592 "Hola, quiero saber cómo funciona" | "An end user writes to the business on WhatsApp." |
| 4 | La respuesta del agente llega al teléfono (texto); después una nota de voz y su respuesta | "The assistant replies through the WhatsApp Cloud API (text and voice notes)." |
| 5 | Dashboard → Conversaciones: la conversación aparece con la transcripción | "The business sees the full conversation in its dashboard." |
| 6 | Campañas (WhatsApp): elegir una plantilla aprobada y un contacto propio, enviar | "The business sends an approved template to a contact who opted in." |
| 7 | El mensaje de plantilla llega al teléfono | "The template message is delivered." |

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

**Video (2–3 min), guion:**

| # | Pantalla | Subtítulo en inglés |
|---|---|---|
| 1 | Login en `app.atentina.com.ar` | "A business logs in to Atentina." |
| 2 | WhatsApp → botón "Conectar WhatsApp" → abre el popup de Meta (Facebook Login for Business / Embedded Signup) | "The business connects its own WhatsApp Business Account with Embedded Signup." |
| 3 | Mientras el Tech Provider no esté aprobado, cortar en el popup; con la aprobación, completar el alta con un número de prueba y mostrar la fila nueva | "After signup, the number appears in the dashboard and is subscribed to our webhooks." |
| 4 | Tabla de números: estado, calidad, límite; acción "Releer de Meta" | "We read the number's status, quality rating and messaging limit from Meta." |
| 5 | Sección Plantillas: lista con estado; "Nueva plantilla" de Utilidad con una variable y su ejemplo, enviar | "The business creates and manages its message templates." |
| 6 | La plantilla aparece como pendiente / aprobada | "Template status is updated from Meta." |

## 4. `public_profile`

Solo pide la confirmación. Lo usa Facebook Login for Business dentro del Embedded Signup (identifica a la
persona que conecta la cuenta); no guardamos datos del perfil.

## 5. Instrucciones para revisores (inglés)

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

Nombres de menú verificados en `web/src/components/nav.ts`: "Conversaciones" (`/calls`), "WhatsApp" y
"Campañas". Las campañas dependen del plan: el cliente de revisores tiene que tener un tier que las incluya.

## 6. Tratamiento de datos (respuestas propuestas)

Son respuestas legales: las decide el usuario.

| Pregunta | Propuesta |
|---|---|
| ¿Encargados del tratamiento con acceso a los Datos de la plataforma? | **Sí**: Cloudflare (red y túnel por donde entra el webhook), Amazon Web Services (copia de respaldo cifrada en S3), Resend (envío de correos con el resumen de la conversación al cliente). Si el cliente lo elige, su proveedor de LLM (OpenAI, Anthropic u OpenRouter); ahí el responsable es el cliente |
| Responsable de los datos | Laureano Martín Arcanio (CUIT 20-30745718-1), titular de la marca Atentina |
| País | Argentina |
| ¿Datos a autoridades por seguridad nacional en 12 meses? | No |
| Procesos ante pedidos de autoridades | Revisión obligatoria de la legalidad; recusar si son ilícitos; minimización de datos; documentación de los pedidos (marcar solo los que se vayan a cumplir de verdad) |

## 7. Checklist del envío

- [ ] Plataforma Sitio web agregada (1.1).
- [ ] Usuario de revisores creado y probado (1.2).
- [ ] Privacidad con Resend y AWS, publicada en la landing (1.3).
- [ ] Video de `whatsapp_business_messaging` grabado (MP4, subtítulos en inglés).
- [ ] Video de `whatsapp_business_management` grabado.
- [ ] Textos de las secciones 2, 3 y 5 pegados; casillas de confirmación.
- [ ] Tratamiento de datos respondido (sección 6).
- [ ] Revisión final con el usuario y **Enviar para revisión** (lo hace el usuario).
