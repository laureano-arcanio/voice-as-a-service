# Zennon BI: base de conocimiento para la reunión de alianza (semana del 26-oct-2026) (22-oct-2026)

Para **Cristian Ventura**, fundador y CEO de Zennon S.A.S. ("Zennon Business Intelligence", CABA): consultora partner de
Microsoft que implementa **Dynamics 365 CE** (Sales, Customer Service, Contact Center, Field Service), **Power Platform**
(Power Apps, Power Automate, Power Pages, Copilot Studio) y **Power BI**, y además trabaja como subcontratista técnico de
otros partners. Llegamos en frío: mail de la tanda `canales4` el 15-oct a `contacto@` (asunto "Llamadas de voz", con clic),
llamada de Laureano el 19-oct al móvil del sitio, que atendió Cristian, interesado; quedó una reunión para la semana del
26-oct (fecha a confirmar). El objetivo **no es venderles un agente para su atención**: es encontrar la alianza o la
integración entre sus productos (Dynamics 365, Power Platform, Power BI) y Atentina. Lead **#228** del CRM (`zennon`,
etapa `charla_agendada`). Sirve para preparar la reunión, el PDF y el video de propuesta.

- **Fuentes, leídas el 22-oct-2026:**
  - el sitio zennonbi.com completo por `curl` (`robots.txt` permite todo salvo `/wp-admin/`): home, soluciones, clientes,
    nuestro equipo, contacto, privacidad, capacidades (Sales, Customer Service, Marketing), CRM, RRHH; las 14 páginas y
    los 92 posts de la API de WordPress; el chat guiado del sitio (texto del widget, sin enviar);
  - la ficha de socio de CESSI; la página de empresa de LinkedIn y el perfil público de Cristian (HTML público por `curl`,
    sin sesión);
  - Microsoft: precios de Dynamics 365 Contact Center, números de Azure Communication Services para Argentina, voz en
    Copilot Studio (Microsoft Learn);
  - el CRM (lead, mails y actividad) y lo nuestro: README, ARQUITECTURA, API_INFERENCIA, LLAMADAS_SALIENTES_PLAN (14),
    `landing/src/data/site.ts`, AGENTS.md y la base de la app (tiers, campañas y llamadas, solo lectura).
  - Links en la parte 9.
- **Copia local:** `scratch/prospectos/zennonbi/raw/` (HTML del home, `home.txt`, JSON de WordPress y el texto de las
  106 páginas y posts en `pages/`, `cessi.txt`, `linkedin_empresa.txt`, `linkedin_cristian.txt`,
  `microsoft_acs_argentina.txt`, `crm_lead_228.json`, `crm_timeline_228.json`, `resenas.txt`).
- **No se encontró:** CUIT ni inscripción de Zennon S.A.S. (búsquedas en Boletín Oficial sin resultado); facturación;
  nivel de partner de Microsoft (no aparece en búsquedas del directorio; el sitio dice "Consultoría e implementación
  Microsoft" y LinkedIn "socios estratégicos de Microsoft"); precios de los paquetes CRM KickStart; Google Maps y reseñas
  (la extensión del navegador no estaba conectada); Instagram, Facebook, YouTube (el sitio no enlaza redes); prensa o
  entrevistas de Cristian fuera del caso Federación Patronal.
- **Partes 1 a 5:** datos. Las partes 6 a 8 son nuestras y hay que validarlas con Cristian.

## 0. Resumen para la reunión

- **Quién es:** Cristian Ventura, **"Fundador y CEO de Zennon BI"** (cita en el caso Federación Patronal del blog). En
  LinkedIn: "profesional especializado en Microsoft Business Applications con más de 12 años", UAI, 2 mil seguidores,
  certificaciones de Dynamics CRM desde 2014 y la insignia "Develop AI apps and agents on Azure" (30-jun-2026). Es técnico y
  sigue formándose en arquitectura de Power Platform (badges de jun-2026).
- **Qué hace la empresa:** consultoría e implementación sobre Microsoft:
  1. **Dynamics 365 CE**: Sales, Customer Service, Customer Insights, Field Service, **Contact Center**; paquetes propios
     **"CRM KickStart Zennon"** (Esencial, Crecimiento, Expansión; sin precios publicados).
  2. **Power Platform**: Power Apps, Power Automate, Power Pages, **Copilot Studio** ("agentes de IA") y AI Builder.
  3. **Power BI**, Dataverse, Azure (Functions, Blob, ETL) e integraciones.
  4. **"Para partners"**: "colaboración técnica y funcional en proyectos de Dynamics 365 CE, Power Platform y Power BI".
- **Tamaño y señales:** fundada en **2018** (LinkedIn), 11-50 empleados, **14 en LinkedIn**, 1.421 seguidores; oficina en
  Alicia Moreau de Justo 1150, piso 4, of. 410 (Puerto Madero), trabajo mayormente remoto. Socia de **CESSI**. Muestran
  **32 clientes**, entre ellos Federación Patronal, Tenaris, Pan American Energy, Banco Hipotecario, BICE, Banco de
  Formosa, Universidad Austral, Provincia NET Pagos, Provincia Microcréditos, Ente Regulador de Servicios Públicos de CABA,
  Cooperativa de Luján, Gestión Compartida (BPO) y siete partners o consultoras (Artware, Integra, Lagash, Jonxsoft,
  Nexer, Excelia, Huenei).
- **Caso insignia (blog):** Federación Patronal, "casi 100 años", unificó en Dynamics 365 Sales los datos de **más de
  11.000 productores y organizadores**, con "más de 1.000 empleados y 300 comerciales" y **12 unidades de negocio**;
  Cristian: "El 70% de esta plataforma está personalizada" (FEDPAS 360). El CRM registra "llamados telefónicos
  trascendentes", visitas y mails.
- **En qué están ahora (oct-2026):** relanzaron el sitio el 14-oct y publican sobre **agentes de IA en el CRM** cada 2-4
  días (15, 19 y 21-oct): Sales Qualification Agent, agentes de Contact Center, "cinco decisiones antes de empezar". Su
  discurso: piloto acotado, línea de base, medir antes de ampliar, ojo con licencias y **Copilot Credits**.
- **Dolores y oportunidades, con evidencia (parte 5):**
  - **D1, la voz en el stack de Microsoft es cara y no tiene número argentino:** Contact Center **USD 110** por usuario
    por mes, Voice **USD 95** más el uso de Azure Communication Services; ACS en Argentina solo ofrece **0800 entrante**,
    sin salientes ni SMS, y **solo con facturación fuera de Argentina** (EE. UU., España, etc.). Copilot Studio necesita
    ese número para un agente de voz.
  - **D2, sus agentes de IA son de texto y "Research-only":** el Sales Qualification Agent que promocionan "prepara un
    correo" que no se envía; nada en el sitio sobre llamar al lead.
  - **D3, sus clientes tienen volumen de llamadas:** Provincia NET Pagos ("centros de contacto"), Gestión Compartida (BPO),
    Provincia Microcréditos, Cooperativa de Luján (servicio eléctrico), Ente Regulador de CABA, 11.000 productores de
    Federación Patronal.
  - **D4, su propia entrada de consultas es de texto y sin IA:** chat guiado de 4 pasos que "no utiliza inteligencia
    artificial" y termina en un mail; un solo teléfono (+54 11 5402-0593) para todo.
  - **D5, el costo pesa en la venta:** su blog insiste en licencias, consumos y créditos ("No debe interpretarse como una
    función ilimitada incluida por tener CRM").
- **Competencia para ellos:** la voz nativa de Microsoft (Dynamics 365 Contact Center + ACS + Copilot Studio), integradores
  con Vapi/Retell/ElevenLabs y telefonía de EE. UU., Botmaker o los IVR de los contact centers de sus clientes. Nuestro
  diferencial para un partner de Microsoft: **número argentino (regional, 0800, 0810) incluido, voces argentinas, precio en
  pesos por mes (Sucursal $ 99.000 con 1.200 min) y API/webhooks que se conectan con Power Automate**.
- **Alianza recomendada (parte 7):** **"La línea de voz argentina de Dynamics 365"**: Atentina como capa de teléfono y
  WhatsApp de los proyectos de Zennon. Entrantes: el agente atiende el número del cliente y deja el caso o el lead en
  Dataverse. Salientes: el CRM dispara la llamada (lead nuevo, cobranza, confirmación de visita de Field Service) y el
  resultado vuelve al CRM. Se conecta con un **conector personalizado de Power Automate** sobre `/api/v1` + webhook firmado,
  y se mide con un **tablero de Power BI** que arma Zennon. Zennon lo revende como módulo de sus implementaciones.
- **Oferta:** (a) acceso Free ya (API, panel, llamadas web, 20 min) para que Cristian pruebe; (b) demo técnica de 30 min
  con un Dynamics de prueba de ellos; (c) piloto de integración de 30 días: un caso en Zennon (sus propias consultas) o en
  un cliente, con precio fijo a definir; (d) acuerdo de aliado (margen o comisión, sin exclusividad): **pendiente**, no hay
  precio de partner documentado.
- **Qué no se pudo verificar / riesgos:**
  - las **campañas de voz** están en la base (migración 0022) pero **ningún tier tiene el canal `voice`**, no hay campañas
    y **no hay ninguna llamada saliente** registrada; sin medir con Gemma;
  - **sin webhook por llamada suelta** (solo en campañas) y **sin documentación pública de la API** (OpenAPI solo admin):
    hace falta para el conector de Power Automate;
  - el primer mail les dijo "por API **o MCP**": **no hay un servidor MCP público de Atentina** (el MCP es interno, de las
    apps por cliente). No repetirlo hasta que exista;
  - sin derivación a humano (Contact Center la tiene), sin marca blanca ni panel de reseller;
  - nivel de partner de Microsoft, CUIT, cargos del resto del equipo, reseñas.

## 1. La persona: Cristian Ventura

- **Cargo:** "Cristian Ventura, Fundador y CEO de Zennon BI" (caso Federación Patronal,
  `/microsoft-365/microsoft-viva/microsoft-impulsa-viva-sales-...`, publicado 24-feb-2023, editado 29-oct-2025). En el CRM
  figuraba "a confirmar": **confirmado** por esa cita.
- **LinkedIn** (`/in/venturacristian`, público, sin sesión): "Soy un profesional especializado en Microsoft Business
  Applications con más de 12 años de…"; experiencia actual Zennon Business Intelligence; educación UAI (Universidad Abierta
  Interamericana); Buenos Aires; 2 mil seguidores, más de 500 contactos; un cargo anterior 2012-2017 (texto oculto sin
  sesión). Certificaciones de Microsoft: Dynamics CRM 2011 y 2013 (customización, aplicaciones, preventa técnica, ventas,
  2014), Managing Microsoft Dynamics Implementations (dic-2014), CRM Online Deployment (may-2015), CRM Installation
  (ene-2016).
- **Publicaciones recientes:** insignias de Microsoft Learn: "Develop AI apps and agents on Azure" (30-jun-2026), "Explorar
  la arquitectura de Power Automate" y la "Serie Arquitecto de soluciones" de Power Apps y Power Platform (jun-2026).
- **Con nosotros:** clic en el mail del 15-oct; el 19-oct atendió la llamada al móvil publicado (de 15 llamadas a leads con
  clic fue el único que atendió) y aceptó una reunión; Laureano le mandó el link del calendario a `chventura@zennonbi.com`
  ese día (dirección que usó el usuario; no figura en el sitio). El 22-oct agendó para la semana del 26.
- **Equipo visible en LinkedIn (sin cargos públicos):** Mariano Silveti, Claudio Fabián Olmedo, David Ezequiel Monti y
  Francisco Ventura (este publica sobre jornadas presenciales del equipo; mismo apellido, relación no verificada).
- **No se encontró:** prensa, charlas, participación en cámaras a título personal, otras sociedades.

## 2. La empresa: Zennon S.A.S.

### 2.1 Datos

- **Razón social:** Zennon S.A.S. (aviso de privacidad, 14-oct-2026; página de LinkedIn). Marca: Zennon BI / Zennon
  Business Intelligence. CUIT: no encontrado.
- **Fundación:** 2018 (LinkedIn). El dominio tiene contenido desde ago-2017 (primera página de WordPress) y un bloque viejo
  dice "MÁS DE 10 AÑOS DE EXPERIENCIA" (probablemente la del fundador).
- **Tamaño:** 11-50 empleados y 14 perfiles asociados (LinkedIn). "Gran parte de nuestro día a día en Zennon sucede a
  distancia" (post de Francisco Ventura).
- **Asociaciones:** socia de CESSI: "Socios estratégicos de Microsoft... soluciones basadas en Dynamics 365 y Power
  Platform"; categorías CRM, fuerza de ventas móvil, consultoría de procesos.
- **Especialidades (LinkedIn):** Dynamics 365 CE y CRM, Power Platform, Power BI, Power Apps, Power Automate, **Power
  Virtual Agent** (el nombre anterior de Copilot Studio).
- **Cifras del sitio viejo:** la página `home-blocks` (no enlazada, editada el 14-ene-2026) tiene contadores "7563
  implementaciones", "+350 clientes contentos", "+9688 horas de soporte": parecen valores del tema de WordPress, **no
  usarlos**.

### 2.2 Oficina, horarios y contacto

| Canal | Dato | Dónde figura | Notas |
|---|---|---|---|
| Oficina | Alicia Moreau de Justo 1150, piso 4, oficina 410, Puerto Madero, CABA | contacto, privacidad, LinkedIn | |
| Teléfono | +54 11 5402-0593 (CESSI: +54 9 11 5402-0593, móvil) | contacto, privacidad, CESSI | lo atendió Cristian el 19-oct: es su línea |
| Email general | contacto@zennonbi.com | todo el sitio, CESSI | alojado en Microsoft 365 (privacidad) |
| Email RRHH | rrhh@zennonbi.com | `/rrhh/` (página de 2020) | |
| Email de Cristian | chventura@zennonbi.com | lo usó el usuario el 19-oct (no publicado en el sitio) | ★ en el CRM |
| Formulario | `/contacto/`: nombre, email, asunto, mensaje | | **no se envió** |
| Chat guiado | widget "Asistente de consultas", 4 pasos: servicio (Dynamics 365, Automatizaciones, Datos, Otro), consulta (10 a 2.000 caracteres), contacto, revisión y consentimiento | home | "No utiliza inteligencia artificial ni un proveedor externo de chatbot"; se remite por correo. **No se envió** |
| WhatsApp | no publicado | | |
| Redes | solo LinkedIn (`/company/zennon-business-i`) | | el sitio no enlaza redes |

No se llamó ni se escribió a la empresa para esta investigación.

### 2.3 El sitio

- WordPress 6.0.17 (PHP 7.4), WPBakery, Slider Revolution, LiteSpeed, en GoDaddy. Sin Google Analytics ni píxeles
  detectados en el HTML del home.
- Relanzado el **14-oct-2026** (home, soluciones, clientes, equipo, contacto y privacidad modificados ese día; home otra
  vez el 19-oct). El HTML del home tiene comentarios de armado ("Borrador CRM KickStart Zennon. Insertar una sola vez
  debajo del hero"), señal de un rediseño reciente hecho por partes.
- Mensaje: "Conectamos procesos, datos y equipos." Soluciones en tres capas: relaciones (Dynamics 365 CE), operación
  (Power Apps, Power Automate), información (Power BI); "IA y Copilot: Copilot Studio · AI Builder... Cada caso requiere
  definir permisos, pruebas y supervisión".
- En `/soluciones/` listan **Contact Center**: "Coordiná conversaciones por voz y canales digitales, con herramientas de
  enrutamiento y asistencia". En Customer Service: "Atendé consultas por los canales habilitados, como chat y voz, según el
  plan, las licencias y la configuración contratados".
- Blog: 92 posts (2018-2026). Sobre voz o canales: lanzamiento de Dynamics 365 Contact Center con Nuance (ago-2024), canal
  de WhatsApp nativo en Contact Center por ACS (sep-2024), Contact Center HIPAA (mar-2025), **MCP en Copilot Studio**
  (mar-2025).

### 2.4 Redes, publicaciones y videos

- **LinkedIn** (empresa): 1.421 seguidores. Publican cada pocos días desde sep-2026, con 0 a 4 reacciones: agentes de
  Dynamics 365 (19 y 21-oct), "Automatizar no siempre significa usar un agente de IA" ("El agente interpreta. El riesgo
  define la aprobación. La automatización ejecuta. Todo queda trazado."), "El CRM es oficial... Pero muchas veces, el
  proceso real sigue viviendo en Excel", procesos sin dueño, conocimiento en la cabeza de una persona.
- **Videos:** ninguno propio; en `/soluciones/` incrustan un video de Microsoft sobre Dynamics 365 (21-jul-2026).
- Instagram, Facebook, YouTube, X: no encontrados.

### 2.5 Clientes que muestran (32, `/clientes/`) y lo que tienen de voz

| Cliente | Rubro (según Zennon) | Relevancia para voz y WhatsApp |
|---|---|---|
| Federación Patronal | seguros; 11.000 productores, 300 comerciales | registro de llamadas en el CRM; avisos y seguimiento a productores |
| Provincia NET Pagos | pagos, recaudación y "centros de contacto" | contact center propio |
| Gestión Compartida | tercerización de procesos (BPO) | operación de atención para terceros |
| Provincia Microcréditos | microcréditos a independientes de PBA y CABA | cobranza temprana, recordatorios |
| Cooperativa de Luján | servicio eléctrico | reclamos por cortes, picos de llamadas |
| Ente Único Regulador de Servicios Públicos (CABA) | regulación | reclamos ciudadanos |
| Banco Hipotecario, BICE, Banco de Formosa | bancos | fuera de nuestro foco (bancos) |
| Universidad Austral | educación | admisiones, consultas |
| Désir Salud | salud mental | turnos |
| FitFlow | protección contra incendios | vencimientos y mantenimiento |
| TGLT, Colliers, Newmark, Caputo | inmobiliario y construcción | consultas comerciales, posventa |
| Tenaris, Pan American Energy, FMC, Las Marías, Accinsa, Trytech, ISA Agents, Alot Staples | industria, energía, retail | Field Service, ventas B2B |
| Artware, Integra, Lagash, Jonxsoft, Nexer, Excelia, Huenei, 4LATAM | partners y consultoras | **canal de segundo nivel**: Zennon trabaja "para partners" |

## 3. Productos y precios de referencia

De Zennon: **no publican precios** (los paquetes KickStart Esencial, Crecimiento y Expansión se cotizan: "Te ayudamos a
evaluar cuál se adapta a tu equipo").

De Microsoft (lo que Zennon tendría que vender para tener voz con IA en Dynamics), leído el 22-oct-2026:

| Pieza | Precio publicado | Fuente |
|---|---|---|
| Dynamics 365 Contact Center | USD 110 por usuario por mes (anual) | microsoft.com, pricing de Contact Center |
| Contact Center Voice (agregado) | USD 95 por usuario por mes | ídem |
| Contact Center Digital (agregado) | USD 95 por usuario por mes | ídem |
| Teams Phone Standard | USD 10 por usuario por mes | ídem |
| Voz de Azure Communication Services | aparte, por uso, sin cifra en la página | ídem |
| Copilot Credits | prepago ("Save up to 20%") o pay-as-you-go, sin precio por crédito en la página | ídem |
| Números de ACS en Argentina | **solo 0800 entrante**, sin salientes ni SMS; solo para suscripciones facturadas en Australia, Canadá, Francia, Alemania, Italia, Japón, España, Reino Unido o EE. UU. | Microsoft Learn |

De Atentina (`landing/src/data/site.ts`): Free $ 0 (20 min, llamadas web, panel y API, sin telefonía); Mostrador $ 29.000
por mes (300 min, 1 llamada a la vez, 1 número); Sucursal $ 99.000 (1.200 min, 3 a la vez, 3 números, "Llamadas
programadas"); Red a medida (más de 5.000 min). Telefonía incluida, numeración regional, 0800 y 0810.

Comparación de orden de magnitud (a validar): un Contact Center con voz para 3 puestos son USD 615 por mes en licencias
(3 × (110 + 95)) antes del uso de ACS y de los créditos, y sin número argentino geográfico; Sucursal es ~USD 64 por mes con
números incluidos.

## 4. Competencia y contexto

### 4.1 Alternativas para Zennon (22-oct-2026)

| Opción | Qué le da | Contra |
|---|---|---|
| Dynamics 365 Contact Center + Copilot Studio (voz) + ACS | todo dentro de Microsoft, transferencia a humano, Nuance | USD 110 + 95 por usuario; ACS en Argentina solo 0800 entrante y con facturación en el exterior; créditos por consumo; voces neutras, no argentinas |
| Teams Phone / Direct Routing con un carrier local | número argentino real en Teams | es telefonía, no agente; armar el SBC y el agente aparte |
| Vapi, Retell, ElevenLabs + Twilio | agente de voz por API | USD 0,05-0,24 por minuto en dólares, números de EE. UU.; integrar con Dynamics a mano (`comercial/competencia/vapi/`) |
| Botmaker | WhatsApp y callbots, conector con Teams | plataforma cerrada, foco en grandes cuentas (`comercial/competencia/botmaker/`) |
| El contact center del cliente (Provincia NET, BPOs) | ya existe | humano o IVR de menú |

- **Otros partners de Dynamics en Argentina:** varios aparecen como sus clientes o colegas (Artware, Nexer, Jonxsoft,
  Excelia). No se analizaron.
- No se pudo comparar en Google Maps (sin navegador).

### 4.2 Contexto en 2026

- Microsoft empuja "agentes" en todo Dynamics 365 (anuncios del 8-oct-2026 que cita Zennon); muchos en preview, solo en
  inglés o con requisitos de región e idioma. Zennon lo advierte: "no alcanza con que la interfaz de Sales esté en
  español".
- Mercado argentino de agentes de IA: USD 30-50 M (voz + texto), voz telefónica USD 5-15 M; los que venden voz cobran USD
  0,28-0,35 por minuto (`plan-salida-al-mercado.md`). Los bancos y telcos ya los atienden Microsoft, Google, NICE, Infobip
  y Botmaker: el espacio propio está en medianas, pymes, cooperativas y organismos, que es buena parte de la cartera de
  Zennon.
- **Llamadas salientes comerciales:** rige el Registro No Llame (Ley 26.951); validar con un abogado antes de campañas
  comerciales (pendiente también nuestro).

## 5. Dolores detectados (con evidencia)

- **D1, la voz con IA en Microsoft es cara y sin número argentino.** Contact Center "$110.00" y Voice "$95.00" por usuario
  por mes, con la voz "priced separately" (pricing de Microsoft). ACS en Argentina: solo "Toll-Free", solo "Receive
  Calls", para suscripciones facturadas en nueve países que no incluyen Argentina (Microsoft Learn). Copilot Studio: "you
  need a phone number" para un agente de voz (Microsoft Learn). Para una pyme argentina cliente de Zennon, la voz nativa
  es licencia por puesto en dólares + un 0800 facturado afuera.
- **D2, sus agentes son de texto y dejan la acción en el vendedor.** Sales Qualification Agent en modo Research-only:
  "puede preparar un correo inicial... ese correo no se envía automáticamente" (blog, 21-oct-2026). En el ejemplo de la
  feria industrial, el agente prepara contexto y "el vendedor... decide si corresponde iniciar la conversación". No hay
  llamada.
- **D3, la cartera tiene volumen de llamadas.** Provincia NET Pagos: "Servicios de pagos y recaudación... y centros de
  contacto"; Gestión Compartida: "tercerización de procesos y soporte"; Cooperativa de Luján, "orientada a sus asociados";
  Federación Patronal: "más de 11.000 productores y organizadores", con un módulo que registra "llamados telefónicos
  trascendentes" (`/clientes/`, caso FEDPAS 360).
- **D4, su entrada de consultas es de texto, sin IA y con una sola línea.** El chat guiado "es un recorrido guiado de
  preguntas y respuestas. No utiliza inteligencia artificial" y "la consulta se remite por correo" (privacidad); el mismo
  +54 11 5402-0593 es el teléfono del sitio, de CESSI y el móvil de Cristian.
- **D5, el costo y los créditos frenan los proyectos de IA.** "La configuración requiere licencia de Copilot Studio y
  capacidad asignada... No debe interpretarse como una función ilimitada" (21-oct); "validar región, idioma,
  configuración, licencias y consumo, incluidos los Copilot Credits" (19-oct); "Estimar el costo de la operación
  completa" (15-oct).

## 6. Pistas de interés en voz, WhatsApp e IA

- Atendió el llamado y aceptó la reunión después de un mail que hablaba de "sumar llamadas de voz con IA" a sus agentes
  sobre Dynamics: el interés es de **integrador**, no de usuario.
- Están relanzando su oferta alrededor de agentes de IA (sitio del 14-oct, tres notas en una semana): buscan algo
  concreto que vender en pilotos acotados. Su método (tarea acotada, línea de base, medir, recién después ampliar) es el
  mismo de nuestro piloto de 30 días: hablarles en esos términos.
- Cristian se está formando en "AI apps and agents on Azure" y arquitectura de Power Platform: va a querer ver la API,
  el webhook y el modelo de datos, no un folleto.
- Ya escribieron sobre **MCP en Copilot Studio**: un servidor MCP de Atentina sería la integración más natural para ellos
  (hoy no existe; ver 7.4).
- Clientes regulados y de gobierno (ERSP, bancos públicos, cooperativas): la **inferencia en Argentina** (los datos no salen
  del país) puede pesar frente a Azure en el exterior. A validar: no sabemos si hoy les piden residencia de datos.
- Trabajan para otros partners: si la integración queda como componente reusable, llega a más implementaciones.

## 7. La mejor alianza: "La línea de voz argentina de Dynamics 365"

### 7.1 Las alianzas posibles, por producto

| Producto de Zennon | Qué haría Atentina | Qué gana Zennon | Qué gana Atentina | Cómo se conecta |
|---|---|---|---|---|
| **Dynamics 365 Sales** (KickStart) | el agente **llama al lead** nuevo o calificado (sigue al Sales Qualification Agent: él investiga, nosotros llamamos), confirma interés, agenda la reunión del vendedor | un paso que Microsoft no da en español ni con número local; un agregado de precio fijo para cada KickStart | minutos y números por cliente de Zennon | Power Automate (trigger "fila agregada" en Dataverse) → `POST /api/v1/calls` (llamada suelta con `phone` y `context`) o `POST /api/v1/contacts` + `POST /api/v1/campaigns` (voz, horario, reintentos, `callback_url`) → webhook `contact.finished` → flujo HTTP de Power Automate que crea la actividad de llamada y actualiza el lead |
| **Dynamics 365 Customer Service** | el número del cliente lo atiende el agente: toma el reclamo o la consulta, identifica al cliente, deja el **caso** en Dataverse | mesa de entrada 24/7 sin licencias de Contact Center por puesto | entrantes, el caso de uso con más evidencia | número de Anura asignado al agente; al terminar, hoy: resumen por email (en producción) → Power Automate "cuando llega un correo" crea el caso; a construir: webhook por llamada o acción del agente (`assistant` con herramienta) que escribe en Dataverse |
| **Dynamics 365 Contact Center** | primer nivel de voz con voces argentinas y número local, para clientes que no quieren pagar Voice por puesto | una alternativa barata para pymes; o un complemento para el desborde y fuera de horario | entrada a contact centers medianos | sin derivación a humano no reemplaza el Contact Center: hoy es "fuera de horario y desborde"; la transferencia a la cola del Contact Center es a construir |
| **Field Service** | confirma la visita del técnico el día anterior, avisa demoras, toma la conformidad | menos visitas fallidas (métrica que el cliente entiende) | campañas de voz recurrentes | órdenes de trabajo del día → Power Automate programado → campaña de voz con `{{fecha}}`, `{{franja}}`, `{{direccion}}` → resultado a la orden |
| **Customer Insights – Journeys** | un paso "llamada" o "WhatsApp" dentro del recorrido (recordatorio, cobranza temprana) | recorridos con voz, que Journeys no tiene en Argentina | campañas | segmento → Power Automate → campaña de voz o de WhatsApp (plantilla) por API; resultado al contacto |
| **Power Pages** (portales) | botón "Hablá con un asesor" con el **link para llamar** desde el navegador | atención por voz en el portal sin telefonía | llamadas web | `llamar.atentina.com.ar/<token>` embebido (en producción) |
| **Copilot Studio** | herramienta "llamar a este contacto" para sus agentes, y el agente de Copilot como "cerebro" de texto mientras Atentina pone la voz | sus agentes "también pueden hacer llamadas" | integración visible en el ecosistema | conector personalizado (OpenAPI) a `/api/v1/calls`; a futuro, un servidor MCP de Atentina (Copilot Studio ya consume MCP) |
| **Power BI** | tablero de llamadas, resultados y minutos por cliente | un entregable propio que cobra | retención: el cliente ve el valor | `GET /api/v1/calls`, `/stats`, `/stats/daily`, `/campaigns/{id}/stats` y `report.csv` (conector Web de Power BI con la API key) |
| **Integraciones / Azure** | motores sueltos: STT, TTS con voces argentinas y LLM, compatibles con OpenAI | piezas para sus desarrollos a medida (transcribir llamadas, leer textos en voz) | uso de la API de inferencia | `https://app.atentina.com.ar/api/v1/inference` con key `stt`/`tts`/`llm` (en producción) |
| **"Para partners"** | el mismo componente, ofrecido a los partners con los que trabajan | un producto que llevar a otros partners | canal de segundo nivel | igual, con una cuenta por cliente final |

**La recomendada como principal:** la combinación **Sales + Customer Service** sobre un conector de Power Automate: es lo
que más venden (KickStart), lo que su blog está empujando (agentes en el CRM) y donde la voz de Microsoft es más cara y
menos local. Field Service y Power BI son los siguientes; Contact Center, Copilot Studio y MCP dependen de cosas que no
tenemos (derivación, MCP público).

### 7.2 Diagrama: sus productos y Atentina

```
                         ZENNON (implementa, integra y revende)
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │  Dynamics 365 Sales ─┐   Customer Service ─┐   Field Service ─┐  Journeys ─┐  │
 │                      ▼                     ▼                  ▼            ▼  │
 │                 Dataverse (leads, casos, órdenes, contactos, actividades)     │
 │                      │  ▲                                                     │
 │      Power Automate: │  │ flujo "HTTP recibido" (webhook firmado HMAC)        │
 │      conector        │  │ o "correo recibido" (resumen de la llamada)         │
 │      Atentina        ▼  │                                                     │
 └──────────────────────┼──┼─────────────────────────────────────────────────────┘
                        │  │
   POST /api/v1/calls   │  │  contact.finished / campaign.finished (campañas)
   /contacts /campaigns │  │  resumen por email (entrantes y salientes sueltas)
                        ▼  │
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │  ATENTINA (inferencia propia en Argentina)                                    │
 │  agente versionado ─ STT ─ LLM ─ TTS (41 voces argentinas)                    │
 │  telefonía Anura: números regionales, 0800, 0810  ·  WhatsApp (Cloud API)     │
 │  link para llamar (navegador, Power Pages)  ·  panel por cliente              │
 │  API de inferencia (STT, TTS, LLM) para desarrollos a medida                  │
 └──────────────────────────────────────────────────────────────────────────────┘
                        │
   GET /calls, /stats, /campaigns/{id}/stats, report.csv
                        ▼
                Power BI (tablero que arma Zennon)

 Clientes finales de Zennon: llaman al número (entrante) o reciben la llamada (saliente)
```

### 7.3 Métricas que querrían ver en el panel (y de dónde salen)

| Métrica | Para quién | Fuente hoy |
|---|---|---|
| Llamadas atendidas, por día y por hora; fuera de horario | cliente final, Zennon | `GET /stats`, `/stats/daily`, `by_hour` de campañas |
| % resueltas por el agente / resultado por tipo (caso creado, lead calificado, reunión agendada, no volver a llamar) | cliente final | `outcome` de cada llamada; `goal_rate` en campañas |
| Contactabilidad de salientes (atendidas / intentos), reintentos, buzones | ventas, cobranzas | `contact_rate`, `results` de `/campaigns/{id}/stats` (sin uso real todavía) |
| Tiempo desde que entra el lead hasta el primer llamado | ventas | timestamp del lead en Dataverse vs `started_at` de la llamada (lo calcula Power BI) |
| Duración media y minutos consumidos vs plan | Zennon (margen), cliente | `avg_duration_seconds`, `minutes`, `/usage`; pantalla Plan |
| Latencia por turno | Zennon (calidad) | `call_logs.latency` en el detalle de la llamada |
| Datos capturados por llamada (campos) y link a la transcripción | vendedor, supervisor | `report.csv` (`campos`, `link`), detalle de la conversación |
| Casos o leads creados en Dynamics por el agente | Zennon (valor de la integración) | lo cuenta Dataverse |

### 7.4 Qué hay hoy y qué falta (interno: verificado el 22-oct-2026)

| Pieza | Estado | Fuente |
|---|---|---|
| Agentes por cliente, versionados, motores `classic`/`structured`/`assistant` | **desplegado** | README, ARQUITECTURA |
| 41 voces argentinas (28 mujeres, 13 hombres) | **desplegado** | AGENTS.md, `tts/finetune/voces.tsv` |
| Números argentinos (regionales, 0800, 0810) por Anura, ruteados a un agente | **desplegado** | site.ts, TELEFONIA_ANURA |
| Entrantes atendidas por el agente | **desplegado** (13 entrantes en la base) | base (`call_logs`) |
| API `/api/v1` con keys por alcance (`calls`, `llm`, `stt`, `tts`) | **desplegado** | ARQUITECTURA, API_INFERENCIA |
| Llamada saliente suelta por API (`POST /api/v1/calls` con `phone` y `context`) | **en el código; cero salientes en la base** (nunca se usó con un cliente) | ARQUITECTURA; base |
| Resumen de cada llamada por email (entrantes, salientes sueltas y link) | **desplegado** (20-oct) | AGENTS.md |
| Link para llamar desde el navegador | **desplegado** (19-oct); falta una llamada real de punta a punta | LINK_LLAMADA_PLAN 11 |
| API de inferencia (STT, TTS, LLM compatibles con OpenAI) y pantalla de uso | **desplegado** | API_INFERENCIA |
| Registro autoservicio, plan Free y cobro (Mercado Pago, transferencia) | **desplegado** | SUSCRIPCIONES_PLAN |
| WhatsApp: mensajes, notas de voz, campañas con plantilla, llamadas de WhatsApp | **desplegado** con el número de Atentina; número propio del cliente por Embedded Signup: **falta la aprobación de Meta** | WHATSAPP_PLAN |
| Contactos, campañas de voz programadas, reintentos, contestador, variables, `report.csv`, `stats`, **webhook firmado**, seguimiento por WhatsApp | **código y migración en la base (0022), sin usar**: ningún tier tiene `voice` en `campaign_channels` (los 5 tienen solo `whatsapp`), cero campañas | LLAMADAS_SALIENTES_PLAN 14; base |
| Códigos SIP de Anura y contestador medidos | **no** | ídem |
| Capacidad con Gemma (LLM vigente) | **sin medir**; tope de campañas 8 provisorio | AGENTS.md |
| BYOK de LLM (Azure OpenAI vía compatible con OpenAI, Anthropic, OpenRouter) | backend **desplegado**; UI sin desplegar | BYOK_LLM_PLAN |
| Grabación por mensaje | existe, apagada; la privacidad de la landing dice que no se graba | AGENTS.md |
| Webhook **por llamada suelta** o entrante | **no existe** (solo el de campañas) | ARQUITECTURA |
| Documentación pública de la API / OpenAPI para un conector de Power Automate | **no**: `/api/v1/docs` solo admin | API_INFERENCIA, ARQUITECTURA |
| Conector de Dynamics 365 / Dataverse | **no**: lo arma Zennon con Power Automate; o una app del motor `assistant` con herramientas que escriban en Dataverse (a construir) | APPS.md |
| Servidor MCP público de Atentina (para Copilot Studio) | **no existe** (el mail del 15-oct lo mencionó) | ARQUITECTURA |
| Derivación o transferencia a un humano (o a la cola de Contact Center) | **no existe** | plan, sección 0 |
| Cuentas de partner: subclientes, marca blanca, panel de reseller | **no**: el admin crea un cliente por cada uno | ARQUITECTURA |
| Precio de partner o mayorista | **no definido** | site.ts |

Desajuste a corregir: la landing ofrece "Llamadas programadas" en Sucursal y Red, pero ningún tier tiene el canal `voice`.

Antes de la demo: habilitar `voice` en el tier `Interno`, una campaña de 2-3 números propios (paso 6 de "Cómo desplegar"
de LLAMADAS_SALIENTES_PLAN) y una llamada saliente suelta por API a un celular propio, para no mostrar algo nunca probado.

### 7.5 Guion de la demo (5 minutos, con el "momento wow")

1. **Panel (1 min):** un agente "Calificador de leads" con la voz elegida (escuchar `martin`, `carolina`, `sofia`), sus
   datos a capturar y sus resultados.
2. **Power Automate (1 min):** un flujo de Zennon (en su tenant de prueba) que al crear un lead en Dynamics llama a la
   API de Atentina con nombre, empresa y motivo (`context`).
3. **Momento wow (2 min):** Cristian carga un lead con su celular y a los segundos suena: "Hola, Cristian, te llamo de
   Zennon por la consulta que dejaste sobre Dynamics 365...". Charla real, con interrupciones.
4. **Vuelta al CRM (1 min):** llega el resultado (hoy: el resumen por email, que un flujo convierte en actividad; con
   campañas: el webhook firmado) y se ve la actividad en el lead, con el link a la transcripción y la latencia por turno.

Alternativa sin tocar su tenant: el mismo circuito con `curl` y un receptor de webhooks, o una entrante a un número de
Atentina que deja el caso en el resumen por email.

### 7.6 Fases sugeridas

1. **Semana 0 (la reunión):** acceso Free para Cristian, guía corta de la API (llamada web, voces, agente, llamada
   saliente) y la definición del primer caso.
2. **Semanas 1-2, piloto de integración en Zennon:** sus propias consultas (formulario, chat guiado y KickStart) entran a
   su Dynamics; el agente llama a cada lead nuevo en horario hábil, califica (servicio, tamaño, urgencia) y agenda.
   Zennon arma el flujo de Power Automate; nosotros el agente, el número y el soporte.
3. **Semanas 3-4:** medir contra su línea de base y elegir el primer cliente (entrantes de Customer Service o
   confirmaciones de Field Service).
4. **Después:** acuerdo de aliado (precio mayorista o comisión, cuentas por cliente), conector publicado (OpenAPI), webhook
   por llamada, plantilla de Power BI y, si lo piden, MCP y derivación.

### 7.7 La oferta

- **Incluye:** cuenta con salientes habilitadas (y el canal de campañas de voz si el caso lo pide), un número argentino, el
  agente armado con ellos, la voz que elijan, la especificación de la API para su conector, soporte directo durante el
  piloto.
- **Cómo se mide:** línea de base de Zennon (leads por mes, tiempo al primer contacto, % que llega a reunión) contra el
  piloto: tiempo al primer llamado, contactabilidad, reuniones agendadas, minutos usados y **horas que les llevó la
  integración** (lo que van a cobrar a sus clientes).
- **Precio:** 30 días, precio fijo y bajo, no gratis (plan, sección 5). Referencia publicada: Sucursal $ 99.000 por mes.
  Precio de aliado: **pendiente**, a definir con el usuario.
- **Para el canal:** se les habla de aliados: margen o comisión sobre lo que revendan, sin exclusividad.

## 8. Base para el prompt del agente (piloto: llamador de leads de Zennon)

### 8.1 Rol y tono

Asistente de Zennon que llama a quien dejó una consulta sobre Dynamics 365, Power Platform o Power BI. Voseo, cordial,
técnico sin jerga, frases cortas; el tono del sitio ("Contanos qué necesita tu equipo"). Se presenta como asistente
virtual de Zennon.

### 8.2 Reglas

- Abre con el nombre, la empresa y el motivo ("dejaste una consulta sobre..."); pide permiso para seguir.
- Si le preguntan si es una IA, lo dice. Si piden no ser llamados, resultado "No volver a llamar".
- No da precios ni promete funciones de Microsoft (licencias, idioma, región): "eso lo revisa el consultor con tu entorno".
- No pide contraseñas ni datos sensibles (igual que el chat del sitio).

### 8.3 Triage y datos

| Salida | Cuándo | Datos a pedir |
|---|---|---|
| Reunión agendada (objetivo) | hay un proyecto | empresa, rubro, cantidad de usuarios, qué usan hoy (Dynamics, otro CRM, Excel), qué quieren resolver, urgencia, día y franja |
| Volver a llamar | no puede ahora | día y franja |
| Seguir por email | prefiere escrito | confirmar el email |
| No califica | estudiante, proveedor, búsqueda laboral | motivo (RRHH: rrhh@) |
| No volver a llamar | lo pide | — |

Al vendedor (actividad en el lead): resultado, campos, resumen de 3 líneas, link a la conversación.

### 8.4 Preguntas para la reunión (descubrimiento)

1. ¿Algún cliente les pidió voz, teléfono o WhatsApp con IA? ¿Qué le ofrecieron (Contact Center, otro proveedor) y qué
   pasó con el costo?
2. ¿Cuántos clientes activos de Dynamics 365 tienen y cuántos KickStart venden por año? ¿Cuáles tienen mesa de atención o
   call center (Provincia NET, Gestión Compartida, Cooperativa de Luján)?
3. ¿Cómo integran hoy sistemas externos: Power Automate con conectores personalizados, Azure Functions, plugins? ¿Qué
   necesitan de nosotros: OpenAPI, webhook por llamada, MCP?
4. ¿Les piden que los datos queden en Argentina (gobierno, cooperativas, salud)?
5. ¿Qué modelo prefieren: revender (precio mayorista, ellos facturan) o referir (comisión)? ¿Cuentas por cliente o una
   sola?
6. ¿Qué tendría que pasar en 30 días para seguir?

## 9. Fuentes

Leídas el 22-oct-2026.

- **Sitio:** https://zennonbi.com/ · https://zennonbi.com/soluciones/ · https://zennonbi.com/clientes/ ·
  https://zennonbi.com/nuestro-equipo/ · https://zennonbi.com/contacto/ · https://zennonbi.com/privacidad/ ·
  https://zennonbi.com/capacidades-sales/ · https://zennonbi.com/capacidades-customer-service/ ·
  https://zennonbi.com/capacidades-marketing/ · https://zennonbi.com/crm/ · https://zennonbi.com/rrhh/ ·
  https://zennonbi.com/home-blocks/ · https://zennonbi.com/robots.txt · https://zennonbi.com/wp-sitemap.xml ·
  https://zennonbi.com/wp-json/wp/v2/pages · https://zennonbi.com/wp-json/wp/v2/posts
- **Blog:** https://zennonbi.com/dynamics-365/sales-qualification-agent-investigar-leads-antes-de-decidir-el-proximo-contacto/ ·
  https://zennonbi.com/dynamics-365/agentes-ia-dynamics-365-del-dato-a-la-accion/ ·
  https://zennonbi.com/dynamics-365/agentes-ia-crm-cinco-decisiones/ ·
  https://zennonbi.com/microsoft-365/microsoft-viva/microsoft-impulsa-viva-sales-con-una-nueva-experiencia-de-vendedor-gpt/
  (caso Federación Patronal) · https://zennonbi.com/dynamics-365/nuevo-canal-de-whatsapp-en-dynamics-365-contact-center/ ·
  https://zennonbi.com/dynamics-365/0908202401/ · https://zennonbi.com/power-platform/microsoft-evoluciona-copilot-studio-con-mcp/
- **Cámara:** https://cessi.org.ar/socio/zennon-bi/
- **LinkedIn (público, sin sesión):** https://ar.linkedin.com/company/zennon-business-i · https://www.linkedin.com/in/venturacristian/
- **Microsoft:** https://www.microsoft.com/en-us/dynamics-365/products/contact-center/pricing ·
  https://learn.microsoft.com/en-us/azure/communication-services/concepts/numbers/phone-number-management-for-argentina ·
  https://learn.microsoft.com/en-us/microsoft-copilot-studio/voice-overview
- **CRM:** lead #228 (`zennon`), mails del 15-oct y 19-oct, actividades del 19 y 22-oct.
- **Atentina:** `README.md`, `AGENTS.md`, `docs/ARQUITECTURA.md`, `docs/API_INFERENCIA.md`, `docs/features/CAMPANAS.md`
  (14), `docs/features/LINK_LLAMADA.md`, `docs/features/WHATSAPP.md`, `landing/src/data/site.ts`, `comercial/competencia/`,
  `comercial/plan-salida-al-mercado.md`, base de la app (tiers, campañas, `call_logs`; solo lectura).
