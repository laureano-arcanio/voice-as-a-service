# Plan: email en el mismo agente

Diseño (2-oct-2026). **Estado: análisis, sin código.** Lo que ya existe es el canal de texto por
WhatsApp ([`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md)) y el correo saliente por Resend
([`LANDING.md`](LANDING.md), paso 9). Las estimaciones de esfuerzo son sin desglose, con las 2 semanas
de la fase 1 de WhatsApp como referencia.

Responde:

1. **Cómo atiende un agente por mail** con el mismo motor (`ConversationEngine`): mail entrante →
   turno → respuesta en el mismo hilo.
2. **Cómo entra el correo a la app** y desde qué dirección responde cada cliente.
3. **Qué tiene el mail que WhatsApp no:** hilos, texto citado, autorespuestas, spam y entregabilidad.

## 1. Decisiones

Propuestas, a confirmar antes de la fase 0.

| Decisión | Elección | Por qué |
|---|---|---|
| Correo entrante | **Resend Inbound**, en un subdominio (`in.atentina.com.ar`) | Mismo proveedor que el saliente, con el dominio ya verificado. Avisa por webhook (`email.received`) y el cuerpo se baja por API. La raíz ya tiene los MX de Cloudflare Email Routing (`hola@` → Gmail): Resend recomienda un subdominio para no chocar |
| Alternativa de entrada | Cloudflare Email Worker que manda el mail por POST a la app | Sin proveedor nuevo ni cupo, pero el parseo MIME y la firma del pedido quedan de nuestro lado. Queda como plan B |
| SMTP propio (puerto 25) | **Descartado** | Reputación de la IP, spam y un puerto más abierto en el router |
| Dirección de entrada del cliente | `<cliente>@in.atentina.com.ar`; el cliente reenvía su `info@` ahí | Sin tocar la casilla del cliente ni pedirle credenciales |
| Dirección de respuesta | **El dominio del cliente**, verificado en Resend (DKIM y SPF en su DNS); sin eso, nuestro dominio con `Reply-To` | La respuesta tiene que venir de quien el destinatario le escribió. Además separa reputaciones: un cliente que manda mal no afecta al resto |
| Casilla conectada por OAuth (Gmail, Microsoft 365) | **Después** | Sería el equivalente del Embedded Signup, pero los permisos de lectura de Gmail son *restricted*: Google pide una auditoría CASA anual por un laboratorio externo (4 a 8 semanas; costo según fuentes secundarias, desde ~USD 540 por año) |
| Motor | **El mismo `ConversationEngine`**, con reglas del canal `email` | Igual que WhatsApp: cambia el prompt del canal, no el agente |
| Dónde corre | En `app` (FastAPI) | Webhook HTTP, sin room, sin STT ni TTS |
| Modo de respuesta | Por cuenta: **automático** o **borrador** (el agente redacta, una persona aprueba) | Un error por mail queda escrito y reenviable; en soporte se suele pedir revisión |

## 2. Cómo encaja en la app

```text
cliente final (mail)  ->  info@cliente.com  --reenvío-->  <cliente>@in.atentina.com.ar (MX de Resend)
                                                                    |
                                        webhook email.received  ->  Cloudflare Tunnel  ->  app: /email/webhook
                                                                    |
                                        app/email/service.py: baja el cuerpo, limpia, turno = process_turn
                                                                    |
                                        Resend: POST /emails con In-Reply-To y References  ->  cliente final
```

**Un turno por mail.** Llega el webhook → 200 al instante y se procesa en segundo plano → se descarta
si el `message_id` ya se procesó → se baja el cuerpo y los encabezados por la API (el webhook trae
solo metadatos: `email_id`, `from`, `to`, `cc`, `received_for`, `message_id`, `subject` y la lista de
adjuntos) → filtros (4) → se busca el hilo por `In-Reply-To` / `References` o se crea una
conversación sin apertura → `process_turn` → se manda la respuesta con `In-Reply-To`, `References` y
asunto `Re: ...` → se guarda el `message_id` de salida para seguir entregas, rebotes y quejas por webhook.

**Lo que se reusa:**

- `ConversationEngine` y `conversations.channel` (`String(16)`, sin constraint: no hace falta migrar
  la columna para sumar un valor).
- El patrón de `app/whatsapp/service.py`: dedupe, un turno a la vez por contacto, tope de turnos y
  de caracteres por turno, estados de entrega.
- Resend: dominio verificado, `RESEND_API_KEY` y el cliente HTTP de `app/services/contact.py`.
- El túnel de Cloudflare para el webhook (hoy `wa.atentina.com.ar`, path `^/wa/webhook`).
- El dashboard: lista por origen y detalle con el chat.

**Lo que hay que cambiar en el motor:**

- `Channel = Literal["voice", "whatsapp"]` (`app/conversation/models.py`) suma `email`.
- `CHANNEL_RULES` (`app/llm/prompt.py`) suma el bloque de mail: respuesta completa en un solo
  mensaje, saludo y firma, cifras y direcciones como se escriben, texto plano sin markdown.
- Las comparaciones `== "whatsapp"` de `prompt.py` y `routers/conversations.py` (409 a los turnos
  por API) pasan a ser "canal de texto". El motor no distingue canales: el fin de un hilo de mail
  llama a `engine.finish`, como el de WhatsApp.

**Tablas nuevas** (espejo de las de WhatsApp):

| Tabla | Qué guarda |
|---|---|
| `email_accounts` | Una por dirección atendida: dirección de entrada, remitente de salida, dominio del cliente y su estado en Resend, `agent_id`, `client_id`, modo (automático o borrador), dirección de derivación |
| `email_threads` | `conversation_id` → contacto, asunto, último `message_id` y la cadena de `References` |
| `email_messages` | `message_id`, dirección, tipo, estado (`sent/delivered/bounced/complained/failed`), error. Idempotencia y consumo |

**Archivos:**

```text
app/email/
  webhook.py   POST /email/webhook, firma Svix (svix-id, svix-timestamp, svix-signature) sobre el cuerpo crudo
  resend.py    bajar un mail recibido, enviar con encabezados de hilo, alta y estado de dominios
  service.py   del webhook al motor y de vuelta: dedupe, filtros, hilo, turno, envío o borrador
  clean.py     HTML a texto, recorte del texto citado y de la firma
  store.py     acceso a email_accounts, email_threads y email_messages
app/api/routers/email.py   API de cuentas, dominios y borradores (/api/v1/email/...)
web/src/features/email/    UI: cuentas, registros DNS a cargar, borradores pendientes
```

**Variables de `.env`:** `RESEND_INBOUND_API_KEY` (acceso completo: la actual es de solo envío y no
lee recibidos ni da de alta dominios), `EMAIL_WEBHOOK_SECRET`, `EMAIL_INBOUND_DOMAIN` y los topes
(`EMAIL_MAX_TURN_CHARS`, `EMAIL_MAX_TURNS`, `EMAIL_MAX_REPLIES_PER_SENDER_DAY`).

## 3. Direcciones y dominios

| Caso | Entrada | Salida | Qué hace el cliente |
|---|---|---|---|
| Piloto o demo | `<cliente>@in.atentina.com.ar` | `<cliente>@atentina.com.ar` | Nada |
| Cliente con su dominio | Reenvío de `info@cliente.com` a la dirección de arriba | `info@cliente.com` | Regla de reenvío en su correo y los registros DKIM y SPF que le muestra el dashboard |
| Casilla conectada (después) | OAuth de Gmail o Microsoft 365 | La misma casilla | Un login; a nosotros nos pide CASA (1) |

- **El reenvío cambia el destinatario:** `received_for` trae la dirección a la que llegó de verdad y
  con eso se elige la cuenta; el `to` sigue siendo `info@cliente.com`.
- **Dominios en Resend:** el plan Pro incluye 10 y el Scale 1.000; 100 más cuestan USD 20 por mes.
  Es el tope real de clientes con dominio propio. A confirmar: si `in.atentina.com.ar` cuenta como
  otro dominio.
- **Cupo:** los recibidos cuentan igual que los enviados. El plan gratis da 100 por día y 3.000 por
  mes: alcanza para desarrollo, no para un cliente.

## 4. Lo propio del mail

- **Hilos:** se arman por `Message-ID`, `In-Reply-To` y `References`, no por remitente: una persona
  puede tener dos consultas abiertas. Un mail sin esos encabezados abre una conversación nueva.
- **Texto citado y firmas:** cada respuesta arrastra todo lo anterior. Sin recortarlo, el contexto
  del LLM (32.768 tokens) se llena en pocos mensajes y el agente responde a texto viejo.
- **Bucles:** no responder a `Auto-Submitted`, `Precedence: bulk` o `list`, `List-Unsubscribe`,
  rebotes, `mailer-daemon@` ni `noreply@`. Tope de respuestas por hilo y por remitente por día. Las
  respuestas del agente salen con `Auto-Submitted: auto-replied`.
- **Abuso:** cualquiera puede escribir. Mirar SPF y DKIM del entrante, limitar por remitente y
  tratar el contenido como texto no confiable (inyección de prompt). El agente no tiene herramientas,
  así que el daño posible es lo que escriba.
- **Varias preguntas por mensaje:** un mail trae todo junto y espera una respuesta completa, al
  revés de los turnos cortos para los que están escritos los agentes. El motor `classic` encaja
  mejor que el de pasos.
- **Adjuntos:** respuesta fija al principio, como las imágenes en WhatsApp. El webhook trae solo los
  metadatos.
- **CC y varios destinatarios:** responder solo al remitente, salvo que la cuenta pida mantener el CC.
- **Sin ventana de 24 h ni plantillas:** el saliente es libre, pero una campaña necesita opt-out y
  base legal (Ley 25.326).
- **Latencia:** no importa. No hace falta juntar mensajes en 2 s; sí conviene una espera corta para
  que la respuesta no parezca una autorespuesta.

## 5. Fases

| Fase | Qué queda | Entregable medible | Esfuerzo (est.) |
|---|---|---|---|
| **0. Entrada** | Subdominio con MX de Resend, key de acceso completo, webhook por el túnel con firma, un mail recibido y respondido en el mismo hilo | Ida y vuelta con una casilla de prueba; cómo se ve el hilo en Gmail y Outlook | 2 a 3 días |
| **1. El motor por mail** | `app/email/`, tablas, canal `email`, limpieza, filtros de bucle, dashboard con origen "Email", tests con mails grabados | Un agente responde de punta a punta; eval con `channel: email` (`make eval-llm`) comparado con WhatsApp | 1 a 2 semanas |
| **2. Clientes con su dominio** | Alta de dominio por API, registros DNS en el dashboard, estado de verificación, rebotes y quejas | Un cliente responde como `info@` de su dominio sin que toquemos Resend a mano | 1 semana |
| **3. Operación** | Modo borrador, derivación a humano (reenvío del hilo), consumo por tier, adjuntos, perfil del test de capacidad | Piloto con un cliente; capacidad medida (`CAP-NNN`) | 1 a 2 semanas |
| **4. Casilla conectada** | OAuth de Gmail y Microsoft 365, auditoría CASA | Un cliente conecta su casilla con un login | A decidir según demanda |

## 6. Riesgos y pendientes

- **Calidad sin medir:** el Qwen3.5-9B se evaluó en turnos cortos. Un mail pide una respuesta larga y
  completa; hay que correr el eval con el canal `email` antes de venderlo.
- **Sin integraciones:** el motor no consulta sistemas del cliente (estado de un pedido, una
  factura). En soporte por mail es lo que más se pide; sin eso el agente responde con la base de
  conocimiento o deriva.
- **Reputación:** Resend exige menos de 4 % de rebotes y 0,08 % de quejas por cuenta. Con el
  dominio compartido, un cliente arrastra a todos.
- **DMARC en `p=none`:** antes de mandar volumen desde `atentina.com.ar`, pasarlo a `quarantine`
  (ver [`LANDING.md`](LANDING.md), paso 9).
- **El webhook depende del túnel:** si `tunnel` está caído, Resend reintenta; el plazo de reintentos
  está sin verificar.
- **Límite de la API:** 10 pedidos por segundo por cuenta, entre todas las keys.
- **Consumo por tier:** WhatsApp tampoco lo cuenta todavía. Definir la unidad (conversaciones o
  mensajes por mes) una vez para los dos canales.
- **Capacidad:** un turno es un pedido al LLM (GPU 0), sin STT ni TTS. Se espera poca carga frente a
  las llamadas, pero no está medida.
- **Datos personales:** los mails traen más datos que una llamada (firmas, adjuntos, terceros en
  copia). Definir retención antes del primer cliente.

## 7. Fuentes (consultadas el 2-oct-2026)

- Resend, correo entrante: https://resend.com/docs/dashboard/receiving/introduction,
  [dominios propios](https://resend.com/docs/dashboard/receiving/custom-domains),
  [responder en el hilo](https://resend.com/docs/dashboard/receiving/reply-to-emails) y
  [evento `email.received`](https://resend.com/docs/webhooks/emails/received).
- Resend, [firma de webhooks](https://resend.com/docs/webhooks/verify-webhooks-requests) y
  [cupos y límites](https://resend.com/docs/knowledge-base/account-quotas-and-limits).
- Google, [verificación de permisos restringidos](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification).
  Costo y plazo de CASA: fuentes secundarias (https://deepstrike.io/blog/google-casa-security-assessment-2025).
- Cloudflare Email Workers: límite de 25 MB por mail, según fuentes secundarias; sin consultar la
  documentación oficial.
