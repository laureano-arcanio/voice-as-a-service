# Botmaker: canales de integración y requisitos (relevado 26-sep-2026)

Fuente: https://botmaker.com/es/canales/todos-los-canales/ (18 canales), páginas por canal, centro de ayuda (help.botmaker.com) y documentación del proveedor subyacente donde Botmaker no documenta.

## Generalidades

- Todos se conectan desde Configuración > Canales de la plataforma. Los self-service (WhatsApp, redes de Meta, Telegram, Webchat, Mercado Libre, Teams, Slack, TikTok, LinkedIn, Email) los activa el cliente solo; Apple Messages y, en la práctica, SMS/RCS/Google Chat/WorkVivo pasan por soporte (support@botmaker.com).
- Botmaker no cobra por canal: planes por "conversaciones" de 24 h (Standard 3.000 por USD 149/mes, Scale 5.000 por 249, Pro 10.000 por 499, Enterprise) más alta de WhatsApp USD 99. Los costos del proveedor (plantillas de Meta, SMS, RCS) van aparte.
- Botmaker actúa como app ya aprobada ante Meta, LinkedIn, TikTok y Apple: el cliente no tramita App Review ni revisión de partner, solo autoriza con OAuth.
- Sin documentación pública (solo tarjeta de marketing): Google Chat, WorkVivo, RCS. SMS tiene un solo artículo operativo.

## Mensajería a clientes

**WhatsApp.** Botmaker es BSP oficial de Meta; el alta es Embedded Signup (login con Facebook, portafolio comercial, perfil de WhatsApp Business, número validado por SMS/llamada). Requisitos: Business Manager de Meta (verificado para subir límites de envío), número nuevo sin cuenta de WhatsApp (móvil, fijo sin IVR o 0800; Botmaker puede proveer uno), alta ~3 días, USD 99 de setup. Fuera de la ventana de 24 h solo plantillas aprobadas por Meta con opt-in documentado, cobradas por Meta según categoría y país más 20 % de Botmaker. Límites por nivel: 250 clientes únicos/día sin verificar, hasta 100.000 con verificación y calidad. Variante Coexistence: mismo número en la app del celular vía QR (hay que abrir la app cada 14 días).

**SMS.** Botmaker no documenta proveedor, países, precio ni alta. Lo único documentado es el envío masivo (notificaciones por API con `channelId` SMS) con respuesta que cae al bot. Las líneas que vende la plataforma son solo para llamadas. Inferencia: se activa por soporte; el opt-in y la cobertura dependen del agregador y la regulación del país.

**RCS.** Solo tarjeta de marketing; no hay ayuda, la página da 500 y Botmaker no figura en el directorio de partners RBM de Google. Requisitos del proveedor (Google): agente RBM con verificación de marca, lanzamiento por país y operadora (las carrier-managed exigen acuerdo comercial directo), cuestionario con opt-in/opt-out y video del flujo, 1 a 3 días hábiles de aprobación. Cobertura LATAM prioritaria: Brasil y México. Solo Android con Google Messages; sin RCS hay que caer a SMS.

**Telegram.** Self-service: crear bot en BotFather, pegar el token en Canales > Telegram. Requisito: una cuenta de Telegram con número. Sin costo ni aprobación. El bot no puede iniciar conversaciones con quien nunca le escribió.

**Webchat.** Widget propio: snippet JS en el sitio (`init.js` con el id del bot), variables externas por `BOTMAKER_VAR` y métodos `bmShow/bmHide/bmSendMessage`. Requisito: solo la cuenta de Botmaker con el canal activo y publicado. Personalizable desde la plataforma, varios webchats por cuenta. Sin SDK nativo iOS/Android documentado: para apps, WebView o la API.

**Email.** Producto "Mailbots": se conecta una casilla existente por IMAP/SMTP con usuario y contraseña (Gmail con 2FA y contraseña de aplicación, Outlook, Yahoo u otro). Requisito: casilla profesional (rechazan @gmail.com y @hotmail.com gratuitas). Es conversación, no mailing: solo responde correos recibidos, agrupados en hilos. Las "campañas de mailing" de la landing no las respalda el help center.

**Apple Messages for Business.** No es self-service: se pide a soporte. Botmaker actúa como Messaging Service Provider; la empresa se registra en Apple Business Register con Apple Account corporativa, elige a Botmaker como MSP, pasa la aprobación de marca y una revisión de experiencia de Apple (primera respuesta ≤ 5 s, escalación a humano obligatoria). Apple no cobra. Solo dispositivos Apple, solo el cliente inicia, sin grupos. Entry points: botón web/app, QR/NFC, Apple Maps, Wallet.

**Central.chat.** App de mensajería del ecosistema Botmaker (web + iOS/Android, cifrado). No hay nada que dar de alta: cada cuenta de Botmaker ya tiene su canal Central. Uso principal: derivar WhatsApp a Central para evitar el cobro por mensaje de servicio de Meta desde el 1-oct-2026 (invitación con enlace de un solo uso al primer mensaje; la conversación sigue en Central con el mismo usuario y bot). Requisito: una línea de WhatsApp. Sin costo adicional. API pública "coming soon".

## Redes sociales y marketplace

**Instagram.** Instagram Messaging API (DMs) e Instagram Graph API (comentarios), como dos canales: "Instagram Messaging" e "Instagram Wall". Conexión con login de Facebook y selección de la página. Requisitos: cuenta de Instagram business o creator vinculada a una página de Facebook y ser admin de esa página. DMs con ventana de 24 h. Comentarios: respuesta pública, sin menú, máximo 220 caracteres; recomiendan un bot aparte.

**Facebook (comentarios).** Webhook `feed` de la Graph API de Páginas, mismo login OAuth que Messenger. Requisito: página de Facebook con rol de administrador; no piden Business Manager. Token de 60 días, renovar desde la plataforma. Respuesta pública, sin menú, 220 caracteres; los comentarios entran a la bandeja como conversaciones (`isFBPageUser = true`). No documentan respuestas privadas a comentarios.

**Messenger.** Messenger Platform de Meta. Canales > Facebook > Conectar > login en popup > autorizar permisos; varias páginas por bot. Requisito: administrador de la página. Token de 60 días. Ventana de 24 h (Meta); fuera de ella solo message tags o mensajes patrocinados. Botones, carruseles, medios, campañas y derivación a agentes.

**LinkedIn (comentarios).** Community Management API: OAuth como admin de la página de empresa. Requisito: rol ADMINISTRATOR en la página. Solo comentarios en publicaciones públicas de la página, respondidos como la organización; sin mensajería privada (LinkedIn no la ofrece a páginas). Token de 60 días. Costos no documentados.

**TikTok.** Business Messaging API (DMs) más TikTok Ads Manager opcional para Messaging Ads y conversiones. Login OAuth de TikTok for Business. Requisito: cuenta TikTok Business (no personal) con permisos de administrador; Ads Manager solo con campañas pagas. Es mensajería directa, no "búsqueda": el usuario inicia, ventana de 48 h; comentarios no soportados todavía. Sincroniza con la app de TikTok ("efecto eco").

**Mercado Libre.** Self-service: Canales > Mercado Libre > Dar permisos al bot, OAuth 2.0 con la cuenta vendedora (tokens de 6 h con refresh). Cubre preguntas de publicaciones, mensajería posventa y reclamos/mediaciones, cada uno con toggle. Requisito: cuenta vendedora autorizada por el usuario administrador (no un operador), sin validaciones pendientes. Preguntas: solo texto, una respuesta por pregunta. Posventa: el vendedor no puede iniciar; ML modera mensajes automáticos, datos personales y links; conversaciones bloqueadas a los 30 días. En Brasil y Chile los mensajes pasan por un agente de IA de ML desde feb-2026.

## Comunicación interna

**Microsoft Teams.** Documentado paso a paso: habilitar apps personalizadas en el admin center, crear la app en Developer Portal con un bot cuyo endpoint es `https://go.botmaker.com/rest/msbotfwk`, client secret, scopes Personal y Teams, publicar en la organización, y en Entra ID dar consentimiento de admin a `User.Read.All`, `TeamsAppInstallation.ReadWriteForUser.All` y `Chat.ReadBasic.All`. Requisitos: tenant de Microsoft 365 con Teams admin o Global admin y suscripción de Azure (canal Teams sin costo por mensaje). Los permisos sugieren instalación proactiva del bot en usuarios.

**Slack.** Self-service en 5 pasos: crear una Slack app propia, Incoming Webhooks, redirect URL de Botmaker, scopes `app_mentions:read`, `chat:write`, `im:history`, `incoming-webhook`, Event Subscriptions con `app_mention`, `message.channels`, `message.im`, y pegar credenciales en Botmaker. Requisito: permiso para crear e instalar apps en el workspace (aprobación del owner si está activada). Gratis. Funciona en DMs y canales públicos; sin scopes de canales privados. Un workspace por app.

**Google Chat.** Botmaker lo lista como self-service pero no tiene página ni artículo. Requisitos del proveedor: Google Workspace (no Gmail personal), proyecto de Google Cloud con la Chat API habilitada y configurada con endpoint HTTP (sería el de Botmaker), y el admin de Workspace con "Allow users to install Chat apps" activo. Visible solo en el dominio salvo publicación en Marketplace. Sin costo de API.

**WorkVivo.** Solo tarjeta de marketing; Workvivo tampoco lista a Botmaker entre sus integraciones. Lo único posible es el framework de Chat Bots de Workvivo: bot con Callback URL creado por un admin, JWT en cada POST y API con Bearer token. Requisitos del proveedor: licencia de Workvivo con el Chat Add-on (pago), acceso a la API pedido a soporte y rol Developer. DMs por equipos; en grupos solo bots globales activados con @Bot. Presumiblemente se integra con onboarding a medida.

## Huecos de la documentación de Botmaker

- Sin proveedor, países ni precios para SMS y RCS.
- Google Chat y WorkVivo sin ningún paso publicado.
- Apple Messages solo por soporte.
- Sin SDK móvil nativo del webchat; sin detalle de webhook vs. polling en Telegram.
- Varias páginas por canal (Facebook, LinkedIn, TikTok, SMS, RCS, Email, Google Chat, WorkVivo) devolvían HTTP 500 el 26-sep-2026.
