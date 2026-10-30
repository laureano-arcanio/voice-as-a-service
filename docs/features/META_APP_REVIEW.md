# App Review de Meta (app Atentina)

Paquete para enviar la revisión de la app `Atentina` (ID 2192489028351511, portafolio 897731003277295): acceso
avanzado a `whatsapp_business_messaging` y `whatsapp_business_management`. Sin esto (y sin el Tech Provider) un
cliente no conecta su número con la app de Atentina: ver [WHATSAPP.md](WHATSAPP.md). **Sin enviar**: una vez
enviado, Meta no deja editarlo ni cancelarlo, y revisa la app entera (ícono, nombre, URLs de privacidad y de
eliminación de datos). El envío lo hace el usuario.

Los textos para Meta van en inglés; la UI está en español (sin i18n), así que los videos llevan subtítulos en inglés.

Fuentes oficiales: [App Review para WhatsApp](https://developers.facebook.com/documentation/business-messaging/whatsapp/solution-providers/app-review),
[Tech Providers](https://developers.facebook.com/documentation/business-messaging/whatsapp/solution-providers/get-started-for-tech-providers),
[guía de envío](https://developers.facebook.com/docs/app-review/submission-guide) y
[grabaciones de pantalla](https://developers.facebook.com/docs/app-review/submission-guide/screen-recordings).

## 1. Estado

| Paso | Estado | Qué falta |
|---|---|---|
| Verificación del negocio | Verificada (como *Sole Proprietorship*, nombre legal del titular, nombre alternativo "Atentina") | — |
| Verificación de acceso (Tech Provider) | **En revisión** desde el 1-oct-2026. Al 27-oct-2026 seguía en revisión, sin pedidos de Meta. Plazo de Meta para completarla: 26-dic-2026 (si no, restringe la app) | Nada de nuestro lado ([pregunta en el foro](https://developers.facebook.com/community/threads/1312250158648768/)) |
| Configuración de la app | Sin confirmar | Ícono, política de privacidad, categoría y correo de contacto (Meta los pide antes de la revisión) |
| Uso permitido | Llamadas de prueba a la API: hechas | Descripción, video y confirmación de cada permiso (secciones 3 y 4) |
| Tratamiento de datos | Sin responder | Sección 6 |

Asistente: developers.facebook.com → Revisar → Revisión de la app → solicitud 2192520205015060.

**Lo que tiene la app hoy** (revisado en el código y la base el 29-oct-2026):

- Un solo número de WhatsApp activo: **+54 9 351 700-2592**, del cliente Atentina (tier Interno, con WhatsApp y
  campañas de WhatsApp), alta **manual** con el token del portafolio (`WA_ACCESS_TOKEN`), sin token propio.
- Plantillas, "Releer datos de Meta" y "Reintentar registro" de un número sin token propio dan 403 a un usuario del
  cliente (`_get_managed` en `app/api/routers/whatsapp.py`); solo los ve un admin o un admin que entró como el
  cliente. Por eso **los videos se graban como admin entrando como el cliente Atentina** (sección 2).
- **Embedded Signup apagado** (`WA_EMBEDDED_SIGNUP` sin definir, default `false`): el botón "Conectar WhatsApp" no
  aparece. Aunque se prenda, el popup no completa el alta hasta que Meta apruebe el Tech Provider. La guía de
  WhatsApp no lo pide en estos videos: **se graba sin él**.
- El alta que sí ve un cliente es "Conectar con mi app de Meta" (`own_app`): usa la app y el token de Meta del
  cliente, no la nuestra, así que no demuestra estos permisos y no va en los videos.

## 2. Requisitos de los videos (oficiales)

**De la página de App Review para WhatsApp:**

1. **`whatsapp_business_messaging`**: la app mandando un mensaje a un número de WhatsApp, y el cliente de WhatsApp
   (web o celular) recibiéndolo y mostrándolo. Alternativa: el script cURL de *WhatsApp → API Setup* mandando a un
   número de prueba.
2. **`whatsapp_business_management`**: la app (o WhatsApp Manager) creando una plantilla de mensaje.
3. **Un video por permiso**: "Do not submit a video that includes multiple permissions supporting different use
   cases."
4. **Grabación real**, no capturas. Descripción escrita y video en cada permiso: sin texto, rechazo.
5. Con solo estos dos permisos, **las instrucciones para revisores no son obligatorias**.

**De la guía general de grabaciones:** UI en inglés o, si no, subtítulos y tooltips en inglés; arrancar con la
sesión cerrada y mostrar el login; mostrar qué hace la app con los datos (el resultado de cada acción); 1080p o
más; ventana de 1440 px de ancho o menos; solo la ventana de la app; mouse en vez de teclado y cursor agrandado;
anotaciones y zoom donde se usa el permiso; sin audio (no lo escuchan). No fija formato, peso ni duración.

**Nuestros:** sin datos de terceros (ni conversaciones de prospectos ni clientes); solo acciones reales.

**Cuenta para grabar:** login de admin → Clientes → Atentina → "Entrar como el cliente". Arriba queda el botón
"Volver a administración"; subtitularlo como *"Atentina's own business account"*.

## 3. `whatsapp_business_messaging`

**Descripción:**

> Atentina (https://atentina.com.ar) is a SaaS platform from Argentina that lets businesses (clinics, gyms,
> collection agencies, retailers) answer their customers with an AI assistant over phone calls and WhatsApp.
> As a Tech Provider, businesses connect their own WhatsApp Business number to Atentina through Embedded Signup,
> and Atentina sends and receives messages on that number on the business's behalf.
>
> We use whatsapp_business_messaging to:
> 1. Receive the messages (text and voice notes) that end users send to the business's WhatsApp number,
>    via our webhook, and download their media (voice notes are transcribed).
> 2. Send the assistant's replies to those end users, as text or as a voice note, inside the 24-hour
>    customer service window. Example: a patient writes "I need an appointment for Tuesday" and the
>    assistant replies with the available times and books it.
> 3. Send approved template messages that the business triggers itself from its dashboard (WhatsApp
>    campaigns): appointment reminders, payment reminders and follow-ups to its own contacts who opted in.
>    End users can opt out by replying "stop" or tapping the "No me interesa" button, and we stop messaging them.
> 4. Register the business's phone number with the Cloud API after Embedded Signup (two-step verification PIN).
>
> Every conversation is shown to the business in its Atentina dashboard (Conversations), where it can read
> the transcript and close the conversation. Without this permission the product cannot answer the
> business's customers on WhatsApp, which is its core function. We do not use message content for
> advertising or sell it; data is used only to provide the service to the business that owns the number.

**Confirmación:** marcar "Si se aprueba, confirmo que cualquier información…".

**Video (1–2 min):** el panel (Chrome, 1440 px) y WhatsApp Web de un número propio, lado a lado o alternados.

| # | Qué se graba | Subtítulo |
|---|---|---|
| 1 | Sesión cerrada → `https://app.atentina.com.ar/login` → Clientes → Atentina → "Entrar como el cliente" | "A business logs in to its Atentina dashboard." |
| 2 | Canales → WhatsApp: el número +54 9 351 700-2592, estado "Conectado" y su agente | "The business's WhatsApp number is connected to an AI assistant." |
| 3 | Canales → Campañas → Nueva campaña → "Por WhatsApp": nombre, número que envía, plantilla aprobada, agente, CSV con el número propio como único contacto → crear | "The business sends an approved template message to a contact who opted in." |
| 4 | La campaña en borrador → "Iniciar campaña" | "Atentina sends it through the WhatsApp Cloud API." |
| 5 | WhatsApp Web: llega la plantilla, con la hora y el remitente a la vista | "The WhatsApp client receives and displays the message." |
| 6 | WhatsApp Web: el contacto contesta; llega la respuesta del asistente | "The customer replies and the assistant answers on the business's behalf." |
| 7 | Conversaciones → esa conversación | "The business sees the conversation in its dashboard." |

El paso 3 necesita una plantilla aprobada en la WABA de Atentina y manda un mensaje real (lo cobra Meta) a un
número propio: confirmar antes de grabar.

## 4. `whatsapp_business_management`

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
>    with header, body variables and examples, footer and buttons, and see their approval status. These
>    templates are then used for the campaigns the business sends.
> 4. Receive account_update, phone_number_quality_update and message_template_status_update webhooks, so
>    that a disconnected, disabled or offboarded account stops being used immediately.
>
> Only users of the business that owns the WABA can see or change it in Atentina. Tokens are stored
> encrypted. Without this permission businesses would have to configure everything by hand in WhatsApp
> Manager and share credentials with us, which is exactly what Embedded Signup avoids.

**Confirmación:** marcar la casilla.

**Video (1–2 min):**

| # | Qué se graba | Subtítulo |
|---|---|---|
| 1 | Sesión cerrada → login → Clientes → Atentina → "Entrar como el cliente" | "A business logs in to its Atentina dashboard." |
| 2 | Canales → WhatsApp: menú del número → "Releer datos de Meta"; columnas Estado y Calidad | "We read the number's status, quality rating and messaging limit from Meta." |
| 3 | Menú del número → "Plantillas" → "Nueva plantilla": nombre, idioma, categoría Utilidad, cuerpo con `{{1}}` y su ejemplo → "Crear" | "The business creates a message template from Atentina." |
| 4 | La plantilla en la lista con estado "En revisión" (y "Aprobada" al releer, si Meta ya la aprobó) | "The template is submitted to Meta; its approval status is shown in the dashboard." |

El paso 3 crea una plantilla real en la WABA de Atentina: confirmar nombre y texto antes de grabar. Alternativa
oficial si algo falla: grabar la creación en WhatsApp Manager.

## 5. Instrucciones para revisores

No son obligatorias con solo estos dos permisos. Un usuario del cliente no puede crear plantillas sobre el número de
Atentina (403, sección 1), así que no se crea usuario para revisores. Si el formulario las pide:

> Atentina is a web dashboard (https://app.atentina.com.ar), in Spanish; the screen recordings have English
> captions. To see messaging working, send a WhatsApp message from any phone to +54 9 351 700-2592 (for example
> "Hello, what does Atentina do?"): the AI assistant replies within a few seconds, by text or voice note.

## 6. Tratamiento de datos (respuestas propuestas)

Son respuestas legales: las decide el usuario. Coinciden con la política de privacidad vigente
(`app/legal/texts/privacidad/2026-10-28.md`).

| Pregunta | Propuesta |
|---|---|
| ¿Encargados con acceso a los Datos de la plataforma? | **Sí**: Cloudflare (red y túnel del webhook), Amazon Web Services (copia de respaldo cifrada), Resend (correos con el resumen de la conversación). Si el cliente lo elige, su proveedor de LLM (OpenAI, Anthropic u OpenRouter); ahí el responsable es el cliente |
| Responsable de los datos | Laureano Martín Arcanio (CUIT 20-30745718-1), titular de la marca Atentina |
| País | Argentina |
| ¿Datos a autoridades por seguridad nacional en 12 meses? | No |
| Procesos ante pedidos de autoridades | Revisión obligatoria de la legalidad; recusar si son ilícitos; minimización de datos; documentación de los pedidos (marcar solo los que se cumplan de verdad) |

## 7. Checklist del envío

- [ ] Configuración de la app completa (ícono, privacidad, categoría, contacto).
- [ ] Plantilla aprobada en la WABA de Atentina para el video de mensajería.
- [ ] Video de `whatsapp_business_messaging` (sección 3) que cumpla la sección 2.
- [ ] Video de `whatsapp_business_management` (sección 4) que cumpla la sección 2.
- [ ] Textos de las secciones 3 y 4 pegados; casillas de confirmación.
- [ ] Tratamiento de datos respondido (sección 6).
- [ ] Revisión final con el usuario y **Enviar para revisión** (lo hace el usuario; un borrador no se revisa).
