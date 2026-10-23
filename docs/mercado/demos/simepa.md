# Simepa: base de conocimiento como prospecto (22-oct-2026)

> **El contacto de WhatsApp del 22-oct-2026 (Pablo) resultó ser de CIMEPA S.A., no de Simepa: ver [`cimepa.md`](cimepa.md)
> (lead #365).** Lo de Pablo en este documento (partes 0, 1, 5 a 8) queda como registro de la confusión; los datos de Simepa
> (partes 2 a 5) sirven para el prospecto aparte, lead #24 del CRM, que sigue en `seguimiento` sin respuesta propia.

**Pablo** nos escribió el 22-oct-2026 a las 10:48 por el WhatsApp de Atentina. Habló con el agente comercial y después con
Laureano. Dijo ser de **"Cimepa"**. El usuario lo asoció a **SIMEPA** (Sistema Médico Pampeano, prepaga del Colegio Médico de
La Pampa), que tiene lead en el CRM (#24, tanda 3, mails del 5 y el 14-oct a `comercial@simepa.com.ar`). Este documento
sirve para preparar la propuesta y la demo que Laureano quedó en mandarle.

- **Fuentes, leídas el 22-oct-2026:**
  - la conversación de WhatsApp con el agente (conversación `4a0e11f1`, base de la app);
  - simepa.com.ar completo: las 27 URLs del sitemap, `robots.txt` (permite todo) y la configuración del widget de WhatsApp;
  - Google Maps de la sede de Santa Rosa, Instagram y Linktree;
  - Boletín Oficial (avisos de CIMEPA S.A. de 2014 y 2019), indicadores.ar (CIMEPA S.A. y Dabra S.A.), cimepa.com y prensa.
  - Los links están en la parte 9.
- **Copia local:** `scratch/prospectos/simepa/raw/`. Tiene el HTML y el texto del sitio (`pages/`, `txt/`), `urls.txt`,
  `resenas.txt`, la conversación (`whatsapp-conversacion-agente.json`) y `cimepa/` (avisos del Boletín Oficial en PDF y texto,
  y cimepa.com).
- **No se encontró:**
  - un Pablo en el sitio de Simepa, ni autoridades o gerentes de Simepa con nombre;
  - LinkedIn de Simepa o de Pablo Brahim;
  - sitio web de CIMEPA S.A.;
  - rastros de Twilio, Vapi, Retell, Aircall ni otra telefonía o IA de voz en el sitio de Simepa.
- **Partes 1 a 5:** datos. Las partes 6 a 8 son nuestras y hay que validarlas con Pablo.

## 0. Resumen para la propuesta

- **Primero, confirmar la empresa.** Hay tres señales de que Pablo **no es de Simepa (La Pampa)**:
  1. Escribió "Cimepa" dos veces. **CIMEPA S.A.** existe: CUIT 33-71547037-9, CABA, constituida en 2014. Su presidente en
     2014 y 2018 fue **Pablo Kevin Brahim** (nacido en 1990), y desde 2026 es director suplente.
  2. Su WhatsApp es **+54 9 11 6163-3436**, un celular del AMBA. Simepa usa números 02954 y 02302.
  3. Dijo que sus empleados son todos remotos y no tienen teléfono. Simepa atiende en 4 sucursales con horario de oficina
     y 14 representantes en el interior.

  La primera frase de Pablo fue: "estamos evaluando una línea de trabajo en Argentina". Eso suena a un negocio nuevo. La
  nota del usuario en el CRM ("probó la demo, quiere reunión") puede ser otro hecho, o la misma conversación asignada a
  Simepa. **Pregunta para Pablo:** "¿Cimepa es la de Pablo Brahim, en CABA, o Simepa, la prepaga de La Pampa?".
- **Qué pidió (literal, por WhatsApp):** un mismo número argentino para:
  1. que personas llamen y atiendan desde la compu o el celular;
  2. que **su propio** asistente de IA haga salientes de seguimiento y atienda, conectado por SIP o por audio en tiempo real;
  3. transferir la llamada entre la IA y la persona, en los dos sentidos;
  4. grabaciones y transcripciones.

  Preguntó además por portabilidad, abono, alta, minutos, llamadas simultáneas, costo de la IA, integración del contexto y
  de los resultados, dónde se guarda el audio y por cuánto tiempo, si se puede apagar la grabación y si hay prueba. Las
  llamadas son tradicionales; WhatsApp, más adelante.
- **Lectura (hipótesis):** el pedido es de **infraestructura de telefonía para un agente propio**, no de un agente nuestro.
  Es una lista de requisitos ordenada, con todos los puntos de una comparación entre proveedores: lo más probable es que se
  la haya mandado igual a varios (Twilio, Telnyx, Vapi, Aircall, Anura). Está en "Plataforma para desarrolladores", el
  segmento donde el plan dice no invertir todavía (sección 2.3). Igual vale la charla para aprender (sección 0).
- **Contra lo que hay hoy** (detalle en 7.4):
  - **sí:** número argentino nuestro, salientes por API, transcripción y detalle por API, grabación opcional, inferencia y
    datos en Argentina;
  - **no:** portabilidad (el número es de Atentina, Anura cl. 26), atender o llamar personas desde la compu o el celular,
    conectar un agente externo por SIP o streaming, y transferir IA ↔ persona.
  - **Ojo:** Laureano ya ofreció la herramienta de transferencia y atender desde la plataforma, y ninguna de las dos existe.
    Según el criterio de "vender antes de construir", se ofrece completo y se construye si interesa, pero la propuesta tiene
    que decir qué está y qué se arma, con plazo.
- **Si es Simepa:** el caso natural es otro (parte 7.6, alternativa): seguimiento de cotizaciones (prometen 24 h hábiles),
  aviso de autorizaciones (48 h hábiles, hoy por WhatsApp o correo) y recordatorio de cuotas. Hay una reseña sobre mensajes
  sin respuesta y débito automático.

## 1. La persona: Pablo

- Nombre de pila "Pablo", empresa "Cimepa", WhatsApp +54 9 11 6163-3436 (dato que él dio). El agente no le pidió el
  apellido ni el cargo.
- **Candidato:** **Pablo Kevin Brahim**, DNI 35.726.186, nacido el 24-dic-1990.
  - Fue socio fundador y presidente de CIMEPA S.A. en 2014, con Melanie Denise Brahim (Boletín Oficial, 20-ene-2014).
  - Fue reelecto presidente por la asamblea del 22-oct-2018 (BO, 11-sep-2019).
  - Desde la asamblea del 20-dic-2024 (publicada el 28-ene-2026) es **director suplente**. Presidenta: Cindy Daniela Brahim;
    vicepresidenta: Nora Beatriz Chervin (indicadores.ar).
  - **No está confirmado** que sea el mismo Pablo: solo coinciden el nombre, la empresa como la escribió y la zona del
    celular.
- **Sin LinkedIn ni prensa** con ese nombre (búsquedas del 22-oct-2026).
- **Su forma de escribir:** formal, técnico y preciso. Usa "SIP", "audio en tiempo real", "streaming de audio
  bidireccional" y "documentación técnica". Rechazó la reunión dos veces ("Me gustaría que me respondan por este medio") y
  aceptó a la tercera. Quiere respuestas concretas y por escrito.

## 2. La empresa

### 2.1 CIMEPA S.A. (candidata por el nombre)

- CUIT 33-71547037-9, IGJ 1.876.473. Escritura del 8-ene-2014. Capital inicial: $120.000.
- **Objeto:** fiduciario (salvo fideicomisos financieros), mandataria y administración de bienes y títulos, inversiones y
  operaciones financieras (BO 2014).
- **Actividad declarada:** servicios inmobiliarios con bienes propios o arrendados (CIIU 681098). **Sin empleados
  registrados.**
- Domicilio fiscal en Washington 4179, CABA. Sede en Av. Córdoba 817/836, CABA, un domicilio que comparten 151 sociedades.
- BCRA: deuda de $497 mil (ago-2026), situación 1.
- **Vínculos (indicadores.ar):** comparte 4 personas con Dabra S.A. y Fabra SA, y 1 con Brahim Hermanos S.A.
  - **Dabra S.A.** es el grupo de Dexter, Stock Center, Moov, Lotto y Tienda River (Modaes). Calzado deportivo, con deuda
    bancaria de unos $9.200 M. La Nación cita a Roberto Daniel Brahim como su presidente.
  - **Que Pablo trabaje en Dabra no está verificado.** Si fuera así, cambia todo: un retailer grande con centro de contacto.
- **No confundir:** cimepa.com es el Circuito Mexicano de Pádel (tienda Shopify, México). No tiene relación.

### 2.2 SIMEPA (el lead del CRM)

- **Qué es:** Sistema Médico Pampeano, medicina prepaga del Colegio Médico de La Pampa, RNEMP 410573.
  - Dice tener "40 años" (en una página dice 30) y más de 1.000 profesionales en cartilla.
  - Toma afiliados directos y derivación de aportes.
  - Cobertura nacional por la Red Argentina de Salud (RAS), emergencias con EMEPA (solo en Santa Rosa) y asistencia al
    viajero con Universal Assistance.
- **Planes:** Plus, Plus Y ("Popular") y 2A. No publica precios: la cotización llega "dentro de las 24 horas hábiles"
  después del formulario.
- **Promoción:** 50 % de descuento para nuevas afiliaciones con derivación de aportes y débito automático, del 1-ago al
  31-dic-2025, de 18 a 45 años. Sigue en la home.
- **Empresas:** "Cuidá a quienes cuidan tu negocio", con 50 % para empleados de empresas y el botón "¿Agendamos una visita?".

### 2.3 Sucursales, horarios y contacto (Simepa)

| Canal | Dato | Nota |
|---|---|---|
| Santa Rosa | Av. San Martín 655, 9 a 14 h, (02954) 431761 | El botón "Contacto" lleva a `prestaciones@simepa.com.ar` |
| General Pico | Calle 11 N° 729, 8 a 15 h, 02302-338800 | El botón lleva a `generalpico@simepa.com.ar` |
| General Acha | Garibaldi 662, 8 a 12 y 17:30 a 20 h, 02952-436608 | — |
| Realicó | Complejo "La Esquina", local 4, 8 a 15 h, 2331-413922 | — |
| Representantes | 14 localidades (Alta Italia, Catriló, Eduardo Castex, Toay, Victorica...) | Con casillas personales de Hotmail o Gmail |
| WhatsApp (widget del sitio) | **+54 2954 828553**, dos "cuentas": "Atención Comercial" (L-V 8 a 20) y "Consultas de Afiliados" (L-V 9 a 14) | El mismo número para ventas y afiliados |
| Urgencias | La Pampa 2954 549110; resto del país 0800 333 3169 | — |
| Emails | `comercial@` (en todas las páginas), `prestaciones@`, `generalpico@`, `app@` (app móvil) | — |
| Formularios | Contacto, cotización y solicitudes (reintegros, afiliación, débito, kinesiología, en tránsito, medicación especial) | No se enviaron |

### 2.4 El sitio y la tecnología (Simepa)

- WordPress 7.1.3 con Elementor Pro, Smart Slider, TablePress, Jetpack, reCAPTCHA y Site Kit de Google (GT-NGPJS9S3).
- Reseñas de Google con el widget de Trustindex y WhatsApp con el plugin "WhatsApp for WordPress" (NinjaTeam).
- Sin chat, sin bot y sin ninguna pista de telefonía en la nube o de IA de voz. Ninguna página nombra Twilio, Vapi, Retell,
  Aircall ni a otro proveedor.
- Queda publicada la entrada "Hola mundo" de 2013. Hay páginas duplicadas en el sitemap ("prestadores-copy",
  "prestadores-duplicado-346").
- **App Simepa** (Android e iOS): credencial digital, pagos con Mercado Pago, autorizaciones (respuesta en 48 h hábiles, que
  avisan "por whatsapp o correo") y reintegros.

### 2.5 Redes (Simepa)

- Instagram @si.me.pa: 791 seguidores, con la bio "La cobertura médica prepaga de los pampeanos".
- Linktree (desde jun-2026): Instagram, WhatsApp, atención comercial, cotizá tu plan y la app.
- Facebook: página "Simepa" (id 494047780744690), enlazada desde el sitio. No se leyó: pide sesión.
- No se encontró LinkedIn.

## 3. Productos y precios de referencia

- **Simepa:** no publica cuotas. La reseña de hace un mes menciona un cobro de $401.510 en un mes (una afiliada mayor).
- **Lo que pidió Pablo es telefonía.** Referencias de mercado (de `docs/mercado/demanda-y-mercado-local.md`):
  - Twilio a celular argentino, USD 0,353/min; DID, USD 6-8 por mes;
  - plataformas BYOK: Vapi USD 0,05/min, Retell 0,07 y Twilio ConversationRelay 0,07, sin telefonía ni modelos.
- **Nuestros planes publicados** (`landing/src/data/site.ts`):
  - Mostrador: $29.000 por mes, 300 min, 1 llamada a la vez, 1 número;
  - Sucursal: $99.000 por mes, 1.200 min, 3 a la vez, 3 números, llamadas programadas;
  - Red: a medida.
  - Ninguno contempla "solo telefonía para un agente de otro".

## 4. Competencia y contexto

### 4.1 Lo que evaluaría Pablo (el pedido de infraestructura)

Hipótesis, sin verificar con él:

| Alternativa | Qué resuelve de su lista | Contra |
|---|---|---|
| Twilio (Elastic SIP, Media Streams, ConversationRelay, Voice SDK) | Todo: softphone web y móvil, agente propio por streaming, transferencias y grabación | Caro a celular argentino (USD 0,353/min); números argentinos con requisitos de documentación |
| Telnyx, Vonage, Plivo | Lo mismo que Twilio | Igual: terminación internacional |
| Vapi o Retell con SIP propio (BYO) | Agente propio no; agente "de ellos" con su prompt y transferencias | Cobran en USD; hay que sumarles la telefonía |
| Aircall, Ringover, Zadarma | Softphone, números y grabación; integraciones de IA | El agente de IA externo es secundario |
| Anura (o IPLAN) directo | Número argentino, central virtual, softphone y troncal SIP | El agente propio lo conectan ellos; Anura no se puede revender (nuestra cl. 26) |
| LiveKit (Cloud o propio) + troncal local | Es nuestro stack: agente propio en una room, SIP y transferencias | Lo tienen que armar ellos |

### 4.2 Competencia de Simepa (si el lead es Simepa)

Google Maps, en la misma búsqueda, el 22-oct-2026:
- SEMPRE, la obra social provincial: 4,0 con 162 reseñas;
- Emepa (emergencias, su socio): 3,7 con 12;
- Nobis Medical: 3,7 con 3;
- Synergia Salud: 3,9 con 8.

Las nacionales con presencia en La Pampa (OSDE, Sancor Salud, Swiss Medical) no se relevaron.

## 5. Dolores detectados (con evidencia)

Del pedido de Pablo:
- **D1. No tienen telefonía:** "una persona haga y reciba llamadas desde su computadora o celular", con empleados remotos y
  sin teléfono (WhatsApp, 22-oct).
- **D2. Ya tienen o arman su propio agente** y buscan dónde enchufarlo: "Necesitamos conectar un asistente propio que
  gestione la conversación de voz en tiempo real".
- **D3. Quieren que todo quede grabado:** "que las conversaciones queden grabadas", y preguntan si se puede desactivar.
- **D4. Quieren respuestas por escrito:** rechazó la reunión dos veces. Nuestro agente esquivó las preguntas técnicas tres
  veces ("un asesor técnico puede confirmarte").

De Simepa (si fuera Simepa):
- **D5. Mensajes sin respuesta:** "no contestan mensajes, pedis que te saquen del debito automatico y seguis en debito
  automatico" (Google, 1 estrella, hace un año).
- **D6. Contacto solo para cobrar:** "el unico contacto que llevamos por varios meses es para enviar el pago" (Google, hace
  un mes). El dueño respondió que los iba a contactar.
- **D7. Un solo WhatsApp** para ventas y afiliados, y horario de oficina (Santa Rosa, de 9 a 14).

## 6. Pistas de interés en voz, WhatsApp e IA

- Pablo ya decidió usar IA en llamadas salientes y entrantes. Lo que busca es el caño, no el agente.
- Pide número argentino y no menciona volumen: preguntar.
- Pregunta dónde se procesan y guardan los audios y la retención. Ahí juega la inferencia y el almacenamiento en Argentina.
- "WhatsApp más adelante": hay interés de segundo paso, y eso ya lo tenemos en producción.

## 7. El mejor caso de uso

### 7.1 La propuesta (para el pedido de Pablo)

Dos caminos, para elegir con él:

- **A. Nuestro agente, con su contexto:** el agente de Atentina con sus instrucciones (definición por la UI o la API).
  Saliente con `POST /api/v1/calls {"phone": ...}`, y resultado y transcripción por `GET /api/v1/calls/{id}`. Si tienen su
  LLM, lo conectan con BYOK (su key de OpenAI compatible o Anthropic) y el turno lo resuelve **su** modelo con nuestra voz,
  STT y número argentino. Es lo más cercano a "asistente propio" que existe hoy.
- **B. Infraestructura para su agente** (lo que pidió literal): número argentino, su agente por SIP o WebSocket de audio,
  softphone para las personas y transferencia. **No existe:** se cotiza como desarrollo, si hay señal (un piloto pago).

### 7.2 Por qué

- El camino A se demuestra hoy y aprovecha lo que nos diferencia: voces argentinas, inferencia y datos locales, y
  terminación local más barata que Twilio a celular.
- El camino B nos pone a competir con Twilio y Telnyx en su terreno (plan, sección 2.3). Conviene aprender por qué no les
  sirve Twilio (¿precio a celular argentino?, ¿números locales?, ¿factura en pesos?) antes de construir.

### 7.3 Guion de la demo (5 minutos)

1. Pablo llama al número de la demo, o se le hace una saliente por API a su celular (con su permiso): el agente lo saluda
   por su nombre con un contexto cargado por API ("seguimiento de su consulta del martes").
2. Corta, y en el panel aparecen la transcripción, los datos capturados y el audio de cada mensaje (con la grabación
   prendida).
3. El mismo resultado por `GET /api/v1/calls/{id}`, en JSON.
4. **Momento wow:** el mismo agente con **su** LLM (BYOK) y una voz argentina, sin cambiar de número.

### 7.4 Qué hay hoy y qué falta (verificado contra los docs, 22-oct-2026)

| Pedido | Estado | Fuente |
|---|---|---|
| Número argentino | Sí, número de Atentina (Anura) | `docs/TELEFONIA_ANURA.md` |
| Portar su línea | **No**: el número es nuestro y Anura prohíbe cederlo (cl. 26). La alternativa es desviar su línea a nuestro número | `docs/proveedores/anura-terminos-2026.md` |
| Varios números | Sí, según el tier (Sucursal: 3; Red: a medida) | `landing/src/data/site.ts` |
| Saliente por API | Sí: `POST /api/v1/calls` con `phone` | `README.md` |
| Campañas de voz (lista, reintentos, webhook) | Implementadas el 19-oct, **sin desplegar**; capacidad con Gemma sin medir | `docs/LLAMADAS_SALIENTES_PLAN.md` |
| Contexto de entrada | Definición del agente y `{{variables}}` | `docs/ARQUITECTURA.md` |
| Resultados y transcripción por API | Sí: `GET /api/v1/calls` y `/calls/{id}`; resumen por email opcional | `README.md`, `AGENTS.md` |
| Grabación, y apagarla | Sí, por agente (`record_audio`, apagada por default), un WAV por mensaje, en el server propio; `GET /calls/{id}/recordings/{n}` | `AGENTS.md` |
| Retención | **Sin política escrita.** La privacidad de la landing dice que no se graba audio: corregir antes de activarla con un cliente | `AGENTS.md` |
| Dónde se procesa | En Argentina, en GPUs propias (LLM, STT y TTS), salvo con BYOK de un proveedor externo | `AGENTS.md` |
| Su propio LLM | Sí: BYOK (fases 1 y 2 desplegadas; la UI, fase 3, sin desplegar) | `docs/BYOK_LLM_PLAN.md` |
| Su agente completo por SIP o streaming | **No existe** | — |
| Personas llamando o atendiendo desde la compu o el celular (softphone) | **No existe** | — |
| Transferir IA ↔ persona | **No existe** (derivación a humano no implementada, plan sección 0) | `plan-salida-al-mercado.md` |
| Llamadas simultáneas | Por tier; con Gemma **sin medir** (no citar los ~32 de CAP-001) | `AGENTS.md` |
| Prueba | Tier Free por registro; la "demo gratis" que ofreció Laureano, a definir | `docs/SUSCRIPCIONES_PLAN.md` |

### 7.5 Fases sugeridas

1. Charla de 20 minutos: confirmar empresa, volumen, para qué son las salientes y si ya tienen el agente armado (y con qué).
2. Prueba del camino A con su contexto, unos días, con un número de Atentina.
3. Si el camino B es condición: estimar la transferencia (SIP REFER o bridge en Asterisk o LiveKit) y el acceso de su agente
   a la room, y ofrecerlo como piloto pago.

### 7.6 La oferta

- **Precio:** el plan Sucursal ($99.000 por mes) como referencia si es el camino A. El camino B queda **pendiente**: no hay
  precio de "telefonía sola" ni de desarrollo.
- **Piloto** (plan, sección 5): 30 días, alcance acotado, precio fijo bajo y métricas (llamadas, contactabilidad,
  duración, resultado capturado).
- **Si es Simepa (alternativa):** un agente que llama a quien pidió cotización antes de las 24 h, avisa autorizaciones
  aprobadas, recuerda cuotas impagas y atiende fuera del horario de 9 a 14.

## 8. Base para el prompt del agente

### 8.1 Rol y tono

Asistente de seguimiento de la empresa de Pablo: formal, breve y en voseo. El contexto lo carga su sistema.

### 8.2 Reglas

- No inventar nada fuera del contexto recibido.
- Pedir confirmación de identidad antes de dar datos.
- Si la persona pide hablar con alguien, tomar el pedido y avisar que la llaman. La transferencia no existe hoy.

### 8.3 Triage y datos

| Salida | Cuándo | Datos |
|---|---|---|
| Resuelto | Respondió lo que el seguimiento pedía | Resultado, fecha y comentario |
| Volver a llamar | No puede ahora | Día y hora |
| Derivar a persona | Pide un humano o un tema fuera del guion | Motivo y teléfono |
| No contactar | Pide no recibir más llamadas | Marca de baja |

### 8.4 Preguntas para la charla

1. ¿Cimepa es la de CABA (Brahim) o Simepa, de La Pampa? ¿Qué rol tenés?
2. ¿A quién llaman en el seguimiento y por qué (clientes, cobranzas, ventas, postventa, salud)? ¿Cuántas llamadas por mes
   y cuántas a la vez?
3. ¿El asistente propio ya existe? ¿Con qué está hecho (Vapi, Retell, OpenAI Realtime, LiveKit, propio)? ¿Qué probaron y
   por qué no les cerró (Twilio, Anura)?
4. ¿Cuántas personas atenderían, y desde dónde? ¿Hace falta que llamen y atiendan con el mismo número desde el día uno?
5. ¿Qué tiene que pasar en 30 días para seguir? ¿Quién decide y con qué presupuesto?

## 9. Fuentes

Leídas el 22-oct-2026:

- **Conversación de WhatsApp:** https://app.atentina.com.ar/calls/4a0e11f1-c20d-436c-9dad-d166c77172fa
- **Sitio de Simepa:**
  - https://simepa.com.ar/
  - /nosotros/, /planes/, /faq/, /app/, /contacto/, /sucursales-y-representantes/, /promo-50/, /3-empresas/
  - /prestadores-duplicado-346/ (solicitudes) y /sitemap_index.xml
- **Google Maps:** https://www.google.com/maps/place/Simepa+-+Sistema+Medico+Pampeano/@-36.62077,-64.2827946,17z (4,6 con
  72 reseñas)
- **Redes de Simepa:** https://www.instagram.com/si.me.pa/ · https://linktr.ee/si.me.pa ·
  https://www.facebook.com/Simepa-494047780744690 (no leída)
- **CIMEPA S.A.:**
  - https://www.boletinoficial.gob.ar/pdf/linkQR/eDlrUW91MFBqOVoreFpJZ1U0d1UwZz09 (constitución, 20-ene-2014)
  - https://www.boletinoficial.gob.ar/pdf/linkQR/bTRvakRVWWVscHQreFpJZ1U0d1UwZz09 (directorio, 11-sep-2019)
  - https://www.indicadores.ar/empresa/33715470379
- **Dabra S.A.:**
  - https://indicadores.ar/empresa/30638485733-dabra
  - https://www.modaes.com/empresas/el-dueno-de-la-argentina-dexter-ficha-al-ex-director-de-netshoes-como-gerente-general
  - https://www.lanacion.com.ar/economia/dexter-debuta-en-el-futbol-con-lotto-nid342136
- **Homónimo sin relación:** https://cimepa.com (pádel, México)
- **Internos:** `docs/proveedores/anura-terminos-2026.md`, `docs/mercado/demanda-y-mercado-local.md`,
  `landing/src/data/site.ts`, `docs/LLAMADAS_SALIENTES_PLAN.md`, `docs/BYOK_LLM_PLAN.md`
