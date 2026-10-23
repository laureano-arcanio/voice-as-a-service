# Axioma IT Solutions: base de conocimiento para la demo técnica y el piloto de integración (22-oct-2026)

Para **Axel Daniel Díaz**, ingeniero, cofundador y CEO de Axioma IT Solutions S.R.L. (CABA): consultora y software
factory, partner Silver de Odoo y partner de Microsoft, con productos SaaS propios (TodoTurnos, Flowery BPM) y una línea de
"Soluciones IA". Les mandamos dos mails (tanda `canales4`: 15-oct y seguimiento el 21-oct, a `axel.diaz@`). El **22-oct-2026**
Axel habló con el agente de la demo de la landing: "estamos evaluando el servicio"; quiere "un agente que llame a ciertos
leads del CRM, en momento determinado"; preguntó por más voces y por que suene menos robot, y no quiere que lo llame un
asesor: quiere probarlo él. Este documento prepara la demo técnica (o el acceso de prueba) y un piloto de integración de
30 días, y alimenta el PDF y el video. Lead **#218** del CRM (`axioma-it`).

- **Fuentes, leídas el 22-oct-2026:**
  - el sitio axiomait.com completo por `curl` (`robots.txt` permite todo): home, `/l` (redirige a `/landing-odoo/`), las 49
    páginas de la API de WordPress y los 29 casos de éxito publicados (posts), con Odoo, IA, planes, soporte, Kit 4.0,
    contacto, cultura, referidos, Power Platform, Flowery, staff augmentation y privacidad;
  - la conversación de Axel con el agente de la demo (base de la app, conversación `e0e4e64d`);
  - la ficha de partner en odoo.com, ERPResearch, Clutch (navegador), Google Maps (navegador), la página de empresa de
    LinkedIn (navegador), YouTube (oEmbed), flowery.ar y todoturnos.com;
  - lo nuestro: README, ARQUITECTURA, LLAMADAS_SALIENTES_PLAN (sección 14), API_INFERENCIA, `tts/finetune/voces.tsv`,
    `landing/src/data/site.ts`, `docs/capacity/` y la base de la app (tiers y campañas, solo lectura).
  - Links en la parte 9.
- **Copia local:** `scratch/prospectos/axiomait/raw/` (HTML y texto del sitio y de las 23 páginas en `pages/`, `posts.txt`
  con los casos, JSON de WordPress, ficha de Odoo, Flowery, TodoTurnos, `resenas.txt`, `linkedin_empresa.txt` y
  `conversacion_demo_2026-10-22.txt`).
- **No se encontró:** CUIT ni fecha de constitución de la SRL (no aparece en el Boletín Oficial por búsqueda; Clutch dice
  "Founded 2017" y el sitio "+10 años"); LinkedIn personal de Axel (no se abrió: el navegador tenía sesión iniciada y la
  visita le habría quedado registrada); prensa o entrevistas; facturación; Instagram y Facebook (requieren sesión).
- **Partes 1 a 5:** datos. Las partes 6 a 8 son nuestras y hay que validarlas con Axel.

## 0. Resumen para la demo y el piloto

- **Quién es:** Ing. Axel Daniel Díaz, **cofundador y CEO** (página de contacto y de cultura del sitio). Equipo "formado
  íntegramente por ingenieros de la U.T.N. F.R.B.A.". Tiene el email de la ficha de partner de Odoo (`axel.diaz@`).
- **Qué hace la empresa:** consultora de sistemas con cuatro líneas:
  1. **Odoo** (partner Silver): implementación con precios publicados (QuickStart desde **$ 1.872.500 + IVA**, 4 semanas;
     Estándar desde **$ 5.928.000 + IVA**, 3 meses), soporte mensual (desde **$ 418.070**, $ 688.866 y $ 877.400 + IVA),
     horas e integraciones (Tienda Nube, Mercado Libre, Andreani, WhatsApp, Instagram, Facebook, SIGEX). Proveedor
     habilitado del **Programa Kit 4.0** (el Estado cofinancia hasta el 50 %).
  2. **Software a medida** y soporte evolutivo (Laravel, Angular, Node, MongoDB; app Android offline para IEB
     Construcciones, sep-2026).
  3. **Soluciones IA**: "Agentes de IA a medida" (ventas, soporte, datos), "Integraciones n8n + IA", diagnóstico de IA sin
     costo, proyectos de 4 a 8 semanas a precio cerrado.
  4. **Microsoft 365 / Power Platform** (SharePoint, Power BI, Power Automate, bots con Virtual Agents) y **staff
     augmentation**.
  - Productos propios: **TodoTurnos** (turnos online para clínicas, odontología y estética, con recordatorios por WhatsApp)
    y **Flowery BPM** (workflows).
- **Tamaño y señales:** 11-50 empleados (LinkedIn, 2,7 mil seguidores), 10-49 (Clutch, USD 25-49/h, proyecto mínimo USD
  5.000); ISO 9001:2015 (Bureau Veritas) en "Custom Software Development"; "+100 proyectos" / "117+ proyectos"; 30
  referencias en Odoo con **97 % de retención**, proyecto promedio de 14 usuarios y el mayor de 100+; 5,0 en Google con 17
  reseñas y 5,0 en Clutch con 4. Oficina en el Polo Tecnológico de Parque Patricios (Patagones 2665, CABA), equipo 100 %
  remoto. Socios de CESSI y del Polo IT Buenos Aires; Connect Americas (logos del sitio).
- **Clientes que muestran:** ADT, Fresenius Kabi (Fresubin), Veritran, Atlas Renewable Energy, Pampa Films, Sanatorio Santa
  Rosa, Badent, Beleme Laboratorio, Milele, Yukon Matafuegos, Lecen, Neumáticos Olmos, Sysar, Isoterma, Creativa Gloria,
  Path Examinations, Pluviodata, Fundación Scherbovsky, Wolke (partner de Salesforce), entre otros.
- **Lo que dijo Axel (22-oct, demo de voz de la landing, 111 s):** quiere un agente que llame a leads del CRM "en momento
  determinado"; preguntó si hay más voces y "una forma que suene menos robot, que no se dé cuenta que es una IA"; no quiere
  un asesor: "quiero probar desde acá, directo". El bot le dijo "más de treinta voces" (son 41) y lo mandó a la demo web.
- **Dolores y oportunidades, con evidencia (parte 5):**
  - **D1, leads que hay que contactar rápido:** cinco formularios distintos prometen respuesta ("Te contactaremos en menos
    de 24hs"), Kit 4.0 con "Cupos por orden de llegada", anuncios de Meta (Pixel y formularios de Meta Ads en la política
    de privacidad). Es el caso que pidió Axel.
  - **D2, un solo WhatsApp y una persona:** el +54 9 11 4978-4822 sirve para ventas, Kit 4.0 y el botón flotante; el
    formulario del Kit abre WhatsApp "para que Belén, de Axioma IT, ya tenga tu consulta".
  - **D3, sus clientes de salud llaman a mano:** en Badent "la comunicación manual a través de llamadas telefónicas para
    recordar citas o confirmar turnos" era "propensa a errores"; en Sanatorio Santa Rosa, TodoTurnos con WhatsApp bajó 70 %
    las ausencias. TodoTurnos no tiene recordatorio por voz.
  - **D4, soporte con teléfono y guardia:** los planes de soporte Odoo incluyen "Atención telefónica" y "Guardia pasiva"
    24/7 (y feriados en Premium).
  - **D5, venden agentes de IA pero no voz:** "Agentes de IA a medida" e "Integraciones n8n + IA", sin nada de telefonía
    ni voz en el sitio; equipo chico (1 a 5 consultores certificados en Odoo según ERPResearch) para montar infraestructura
    de voz propia.
- **Competencia para ellos:** armar con Vapi o Retell (USD 0,05-0,07 por minuto solo plataforma, más modelos y telefonía de
  EE. UU.), ElevenLabs Agents (USD 0,08-0,24), Botmaker (USD 0,07 por llamada de hasta 2 min) o el VoIP de Odoo (telefonía,
  sin agente). Nuestro diferencial para un integrador: número argentino, voces argentinas, precio en pesos y la misma API
  para voz, WhatsApp, LLM, STT y TTS.
- **Caso de uso propuesto (parte 7):** **"el llamador del CRM"**: Odoo (o el CRM del cliente) → API de Atentina (contactos +
  campaña de voz programada) → el agente llama, califica y agenda → webhook firmado de vuelta al CRM con resultado, datos y
  link a la conversación. Primero para los leads de Axioma (Kit 4.0 y diagnóstico Odoo), después como módulo que Axioma
  revende a sus clientes (TodoTurnos, Odoo).
- **Oferta:** (a) acceso de prueba autoservicio ya: registro Free (API, panel, llamadas web, 20 min), 41 voces; (b) demo
  técnica guiada de 30 minutos; (c) piloto de integración de 30 días con el plan de campañas habilitado y un precio fijo
  a definir (no hay precio de partner documentado).
- **Qué no se pudo verificar / riesgos:**
  - las **campañas de voz** están en el código y la base (migración 0022 aplicada, `app` recreado el 22-oct) pero **ningún
    tier tiene el canal `voice`**, no se corrió ninguna campaña y en la base **no hay ninguna llamada saliente registrada**;
    faltan los códigos SIP de Anura, el contestador medido y la capacidad con Gemma;
  - el OpenAPI (`/api/v1/docs`) es **solo para admin**: un integrador no tiene documentación pública de la API de llamadas;
  - no hay **marca blanca** ni panel de reseller: un cliente no crea subclientes (solo el admin);
  - **"que no se dé cuenta que es una IA"**: no lo ofrecemos (ver 6 y 8.2);
  - CUIT, año de fundación exacto y cargo en LinkedIn de Axel.

## 1. La persona: Axel Daniel Díaz

- **Cargo:** "Ing. Axel Díaz, Cofundador & CEO" (página de contacto, bajo el horario "Lunes a viernes de 9 a 18 hs");
  "Ing. Axel Daniel Díaz, Cofundador & CEO" firma la cita de la página de cultura.
- **Formación:** ingeniero; el equipo "formado íntegramente por ingenieros de la U.T.N F.R.B.A" (quiénes somos).
- **Frase propia (cultura):** "nos esforzamos cada día por ser técnicamente buenos y mejores humanos".
- **Contacto:** `axel.diaz@axiomait.com`, en la ficha de partner de odoo.com (junto al +54 11 4978-4822).
- **Cómo se comportó con nosotros:** recibió dos mails (15 y 21-oct, sin clics registrados en el CRM) y al día siguiente
  del seguimiento probó la demo de voz. Directo, técnico, prefiere probar solo antes de hablar con ventas. Preguntó lo que
  preguntaría un integrador: voces, naturalidad, llamadas programadas desde un CRM.
- **No se encontró:** su perfil de LinkedIn (no se abrió), prensa, charlas o participación en cámaras a título personal.

## 2. La empresa: Axioma IT Solutions S.R.L.

### 2.1 Datos

- **Razón social:** Axioma IT Solutions S.R.L. (política de privacidad, ficha de Odoo, LinkedIn). CUIT: no encontrado.
- **Fundación:** "+10 años" (home, IA) y "a lo largo de la última década" (cultura); Clutch: "Founded 2017". Sin confirmar.
- **Tamaño:** 11-50 empleados y 5 % de crecimiento (LinkedIn), 10-49 (Clutch). Equipo "100% remoto" con beneficios
  (cultura). Odoo: 2 consultores certificados (v18 y v17); ERPResearch: "1–5 certified Odoo consultants".
- **Certificaciones y alianzas:** ISO 9001:2015 (Bureau Veritas), Odoo Silver Partner, Microsoft Partner, CESSI, Polo IT
  Buenos Aires, Connect Americas (logos del home).
- **Números que publican:** "+100 Proyectos", "+10 Años", "LATAM Expert" (home); "117+ Proyectos entregados con metodología
  ISO 9001", "3X más velocidad", "40% reducción en tiempos de desarrollo con IA" (Soluciones IA); "+50 empresas confían en
  nosotros" (Odoo) y "Más de 100 empresas" (contacto). Odoo: 30 referencias, 97 % de retención, proyecto promedio de 14
  usuarios, el mayor de 100+.
- **Programa de referidos y partners** (`/referidos`): comisión del 5 al 15 %; un "Programa de Partners" para consultores y
  agencias con "comisiones más altas"; valor promedio por proyecto "$8,000 – $15,000" (implementación Odoo). Les resulta
  natural el modelo de canal.

### 2.2 Oficina, horarios y contacto

| Canal | Dato | Dónde figura | Notas |
|---|---|---|---|
| Oficina | Patagones 2665, CABA (Polo Tecnológico, Parque Patricios) | home, contacto, Odoo, Maps | Maps: "Abierto · Cierra a las 6 p. m." |
| Horario | Lunes a viernes de 9 a 18 h | contacto | |
| Teléfono | (+54 11) 4978-4822 | home, contacto, landing, Odoo | también es el WhatsApp |
| Teléfono 2 | (+54 11) 5263-3187 | pie del home, Google Maps | |
| WhatsApp | +54 9 11 4978-4822 (`wa.me/5491149784822`) | Odoo, Kit 4.0, botón flotante (Joinchat) | mensajes precargados por página; el del Kit va a "Belén" |
| Email general | contacto@axiomait.com | todo el sitio | |
| Email de Axel | axel.diaz@axiomait.com | ficha de partner de odoo.com | ★ en el CRM |
| Formularios | contacto, landing Odoo, Soluciones IA, Kit 4.0, planes (form1/form2), referidos, CV | | **no se enviaron**; el de contacto pide nombre, email, teléfono y "¿Qué necesitás?" con "Automatizaciones / IA" |

No se llamó ni se escribió a la empresa.

### 2.3 El sitio

- WordPress 7.1.3 + Elementor Pro, tema Hello Elementor; Joinchat (WhatsApp flotante), PixelYourSite (Pixel de Meta),
  MonsterInsights (Google Analytics). Español e inglés.
- Muy activo: home modificado el 15-oct-2026, `/odoo/` el 20-oct, Kit 4.0 y soporte el 9-oct (API de WordPress).
- Promesas de respuesta: "Te contactaremos en menos de 24hs" (landing Odoo), "Respondemos en menos de 24 horas hábiles"
  (IA), "Cupos por orden de llegada" (Kit 4.0).
- **Integraciones de Odoo que venden:** Tienda Nube, Andreani, Mercado Libre, WhatsApp ("Atención y notificaciones desde el
  CRM"), Instagram, Facebook ("Leads y mensajes en tu pipeline"); en casos: SIGEX (3 endpoints, Milele), ARCA, Salesforce
  (API PDM ↔ Salesforce en Atlas).

### 2.4 Redes, publicaciones y videos

- **LinkedIn** (empresa): 2,7 mil seguidores; publican casos de éxito y Odoo cada 1-3 meses (10-sep-2026 IEB Construcciones;
  20-ago Mercado Libre y Tiendanube; nov-2025 Beleme, Lecen y Tienda Nube) con 2 a 6 reacciones.
- **YouTube:** "Video Institucional - Axioma IT", 55 s, 256 vistas, 28-dic-2023.
- **Instagram** (`axiomaitsolutions`) y **Facebook** (`AxiomaITSolutionsSRL`): enlazados, no leídos (piden sesión).
- **Blog:** 24 notas (2024-2026): Odoo vs otros ERP, integración con Tienda Nube y SIGEX, sobreventa en Mercado Libre, ROI
  del software, staff augmentation, MVP para startups. Nada sobre voz o telefonía.

### 2.5 Casos de éxito (29 publicados) y lo que tienen de voz

| Cliente | Rubro | Qué hicieron | Relevancia para voz |
|---|---|---|---|
| Badent | odontología | TodoTurnos (Angular, Node, MongoDB) + API de WhatsApp | antes: llamadas manuales para recordar y confirmar turnos |
| Sanatorio Santa Rosa (1944) | salud | TodoTurnos + API de WhatsApp | "Se redujeron en un 70% las ausencias de pacientes imprevistas" |
| ADT | seguridad | intranet SharePoint; áreas de Monitoreo, Atención al cliente, Cobranzas | gran usuario de call center (no es cliente de voz) |
| Milele, Yukon/MatafuegosYa | matafuegos | Odoo + SIGEX, comisiones | mantenimiento preventivo: vencimientos y recordatorios |
| Neumáticos Olmos, Sysar (FATE) | neumáticos | Odoo + Tienda Nube + Mercado Libre | ventas por varios canales |
| Path Examinations | certificación de inglés | 80 h/mes de soporte evolutivo con Cursor | usan IA en desarrollo |
| Veritran, Fresenius Kabi | fintech, salud | staff augmentation | |

## 3. Productos y precios de referencia (de Axioma)

| Producto | Precio publicado (ARS + IVA) | Fuente |
|---|---|---|
| Odoo QuickStart (1-6 usuarios, 4 semanas) | desde $ 1.872.500 | `/odoo-planes/` |
| Odoo Estándar (6-50 usuarios, 3 meses) | desde $ 5.928.000 | `/odoo-planes/` |
| Odoo Corporativo (50+) | a medida | `/odoo-planes/` |
| Soporte Esencial / Avanzado / Premium | $ 418.070 / $ 688.866 / $ 877.400 por mes | `/soporte-odoo/` |
| Soluciones IA | precio cerrado, 4 a 8 semanas, diagnóstico sin costo | `/soluciones-ia/` |
| Software a medida (Clutch) | USD 25-49 por hora, mínimo USD 5.000 | Clutch |

Un recordatorio por voz para un cliente de TodoTurnos o de soporte Odoo se suma a abonos de $ 400 a 900 mil por mes: el
costo de nuestros planes ($ 29.000 y $ 99.000) entra holgado como componente revendido.

## 4. Competencia y contexto

### 4.1 Local y alternativas para un integrador (22-oct-2026)

- **Consultoras vecinas** (Maps, "otras personas también buscan"): DirMOD 4,9 (11), Voolkia 4,7 (53), Agnostic IT 4,2 (13).
  Ninguna se revisó a fondo.
- **Cómo armaría voz hoy un integrador** (de `docs/competencia/` y `demanda-y-mercado-local.md`):

| Opción | Precio | Para Axioma |
|---|---|---|
| Vapi | USD 0,05/min de plataforma + STT/LLM/TTS + telefonía; ~USD 0,08-0,13/min total | números de EE. UU.; SIP propio para Argentina; costo variable en dólares |
| Retell | USD 0,07/min de plataforma | ídem |
| ElevenLabs Agents | USD 0,08-0,24/min | voces muy buenas; telefonía aparte |
| Botmaker Callbots | USD 0,07 por llamada de hasta 2 min, 0,30 hasta 60 | plataforma cerrada, foco en grandes cuentas |
| Odoo VoIP | app de Odoo (telefonía) | sin agente de IA |
| n8n + Twilio + modelos | por uso, en dólares | lo saben hacer, pero es armar y mantener infraestructura |

### 4.2 Contexto en 2026

- Mercado argentino de agentes de IA: USD 30-50 M (voz + texto), voz telefónica USD 5-15 M; los que venden voz cobran USD
  0,28-0,35 por minuto (`plan-salida-al-mercado.md`).
- Los partners de Odoo compiten por precio y por integraciones; el Kit 4.0 (hasta 50 % cofinanciado) genera una ola de
  leads pyme con plazo.
- **Llamadas comerciales salientes:** rige el Registro No Llame (Ley 26.951). Llamar a leads que pidieron contacto por un
  formulario es distinto de llamar en frío: hay que validarlo con un abogado antes de lanzar (pendiente también en nuestro
  plan de campañas).

## 5. Dolores detectados (con evidencia)

- **D1, velocidad de contacto a leads entrantes.** "Te contactaremos en menos de 24hs" (`/landing-odoo/`); "Respondemos en
  menos de 24 horas hábiles" (`/soluciones-ia/`); "Cupos por orden de llegada" (home, Kit 4.0); la política de privacidad
  cuenta "Formularios de contacto generados mediante campañas publicitarias en plataformas como Meta Ads". Con 5+
  formularios y pauta, el cuello es llamar a tiempo. Axel lo pidió: "un agente que llame a ciertos leads del CRM".
- **D2, todo pasa por un número y una persona.** El mismo +54 9 11 4978-4822 en la ficha de Odoo, el botón de WhatsApp y
  el Kit 4.0; el formulario del Kit dice "Te abrimos WhatsApp para que Belén, de Axioma IT, ya tenga tu consulta" (`/kit-4-0/`).
  Horario de 9 a 18 h de lunes a viernes.
- **D3, sus clientes de salud confirman turnos por teléfono.** Badent: "La comunicación manual a través de llamadas
  telefónicas para recordar citas o confirmar turnos era propensa a errores" (`/badent/`). Sanatorio Santa Rosa: "Se
  redujeron en un 70% las ausencias" con TodoTurnos y WhatsApp (`/sanatorio-proyecto/`). TodoTurnos no ofrece voz.
- **D4, soporte con teléfono y guardia 24/7.** Los tres planes de soporte Odoo incluyen "Atención telefónica" y "Guardia
  pasiva 24/7 con fines de semana" (`/soporte-odoo/`): un primer nivel que toma el caso y lo carga como ticket.
- **D5, venden agentes de IA pero no voz, con un equipo chico.** "Agentes de IA a medida" e "Integraciones n8n + IA"
  (`/soluciones-ia/`), sin telefonía ni voz en el sitio; 11-50 personas y 1-5 consultores Odoo certificados.

## 6. Pistas de interés en voz, WhatsApp e IA

- Axel ya probó la demo y lo dijo con todas las letras: "estamos evaluando el servicio". Llegó al día siguiente del
  seguimiento por mail.
- Quiere probar solo, sin asesor: la respuesta tiene que ser **acceso** (registro Free + guía de 1 página + key), no una
  reunión de ventas. La demo técnica guiada se ofrece como opción.
- Sus preguntas son de integrador: voces, naturalidad, disparo programado desde un CRM.
- **"Que no se dé cuenta que es una IA":** nuestra posición (a validar con el usuario): voces naturales y argentinas sí;
  ocultar que es una IA no. El agente se presenta como asistente y, si le preguntan, dice la verdad. Es también lo que
  protege a Axioma frente a sus clientes y al No Llame. Lo que sí ayuda a que "no suene robot": elegir la voz (41), apertura
  pregenerada, frases cortas, y el nombre de la empresa en la apertura.
- Ya integran WhatsApp con la API de Meta (TodoTurnos) y CRMs (Odoo, Salesforce): les va a resultar natural el webhook.
- Programa de partners propio con comisiones: entienden reventa y margen.

## 7. El mejor caso de uso: "el llamador del CRM"

### 7.1 La propuesta

Un agente de voz que llama a los leads del CRM en el momento que el CRM decide, los califica y deja el resultado en el CRM:

```
Odoo / CRM del cliente
  │ 1. evento: lead nuevo o etapa "llamar" (acción automatizada de Odoo, n8n o código propio)
  ▼
API de Atentina (Bearer vaas_..., alcance calls)
  │ 2. POST /api/v1/contacts          (upsert por teléfono, con datos: nombre, empresa, rubro, origen, external_id)
  │ 3. POST /api/v1/campaigns         (channel=voice, agente, número de origen, voz, horario y días, starts_at,
  │                                    concurrencia, reintentos, purpose, callback_url) y /start
  ▼
Agente de Atentina (número argentino, voz elegida)
  │ 4. llama dentro del horario, abre con {{nombre}} y {{empresa}}, califica, agenda o deriva por WhatsApp
  │    reintentos si no atiende o es un buzón; baja si pide no ser llamado
  ▼
Webhook firmado (X-Atentina-Signature: HMAC-SHA256)
  │ 5. contact.finished: resultado, outcome, objetivo cumplido, campos capturados, duración, link a la conversación
  │    contact.followup (WhatsApp de seguimiento) y campaign.finished (stats)
  ▼
Odoo / CRM: actualiza la oportunidad (etapa, nota con el resumen, actividad para el vendedor)
  + polling (GET /campaigns/{id}, /stats) y reporte (GET /campaigns/{id}/report.csv)
```

Dos usos, en orden:
1. **Para Axioma** (piloto): los leads del Kit 4.0, la landing de Odoo y Meta Ads. El agente llama en minutos (dentro del
   horario), confirma tamaño, rubro, si tienen certificado MiPyME y qué quieren ordenar, y agenda el diagnóstico.
2. **Para sus clientes** (canal): confirmación de turnos de TodoTurnos (Badent, Sanatorio Santa Rosa), avisos de
   mantenimiento y vencimientos (matafuegos: Milele, Yukon), primer nivel de soporte Odoo, cobranza temprana en clientes
   Odoo.

### 7.2 Por qué es el mejor caso

- Es lo que pidió Axel, con sus palabras.
- Se mide en 30 días con números de su propio CRM: contactabilidad, tiempo hasta el primer contacto, diagnósticos agendados.
- Usa lo que Axioma ya sabe hacer (acciones de Odoo, n8n, webhooks) y le deja un módulo revendible a 30 clientes Odoo con
  97 % de retención y a los de TodoTurnos.
- Salida corta, con guion: es donde menos pesa nuestra latencia.

### 7.3 Guion de la demo (5 minutos, con el "momento wow")

1. **Panel (1 min):** el agente "Calificador Kit 4.0" de la demo, la voz elegida entre 41 (escuchar 3: `sofia`, `martin`,
   `carolina`), sus datos a capturar y sus resultados.
2. **API (1 min):** `curl` que crea el contacto con los datos de un lead de prueba y una campaña de voz con `starts_at` en 1
   minuto y `callback_url` a un receptor de webhooks.
3. **Momento wow (2 min):** suena el celular de Axel: "Hola, Axel, te llamo de Axioma por la consulta del Kit 4.0...". Charla
   real, con interrupciones.
4. **Vuelta al CRM (1 min):** llega el webhook con resultado, campos (empresa, empleados, MiPyME sí/no, interés) y link a la
   transcripción; se ve la conversación en el panel con la latencia por turno.

Alternativa sin campañas habilitadas: la misma demo con una llamada única por API (`POST /api/v1/calls` con `phone`) o por
el link para llamar, y el resultado por el resumen por email.

### 7.4 Qué hay hoy y qué falta (interno: verificado el 22-oct-2026)

| Pieza | Estado | Fuente |
|---|---|---|
| Agentes por cliente, versionados, motor `classic`/`structured`/`assistant` | en producción | README, ARQUITECTURA |
| 41 voces argentinas (28 mujeres, 13 hombres), elegibles por agente o por llamada | en producción | `tts/finetune/voces.tsv` |
| Números argentinos (regionales, 0800, 0810) por Anura | en producción | site.ts, TELEFONIA_ANURA |
| API `/api/v1` con API keys por alcance (`calls`, `llm`, `stt`, `tts`) | en producción | ARQUITECTURA |
| Registro autoservicio y plan Free (20 min, API, llamadas web, sin telefonía) | en producción | site.ts, SUSCRIPCIONES_PLAN |
| API de inferencia compatible con OpenAI (LLM, STT, TTS) | en producción | API_INFERENCIA |
| Contactos, campañas de voz programadas, reintentos, contestador, variables, `report.csv`, `stats`, webhook firmado, seguimiento por WhatsApp | **código y migración aplicados (base en 0022, `app` recreado el 22-oct), sin usar**: ningún tier tiene el canal `voice`, cero campañas, cero llamadas salientes en la base | LLAMADAS_SALIENTES_PLAN 14; base |
| Códigos SIP de Anura y contestador medidos | **no** | ídem |
| Capacidad con Gemma (LLM vigente) | **sin medir**; tope de campañas `CALL_CAMPAIGN_MAX_CONCURRENT` = 8 provisorio | AGENTS.md, capacity |
| Latencia | en la llamada de Axel, e2e del server prom. **0,87 s** (máx. 1,17) en 6 turnos; el piso medido con el cliente en CAP-001 (Qwen) fue 1,66 s p50 | base (`call_logs.latency`), capacity |
| Campañas y mensajes de WhatsApp, llamadas de WhatsApp | en producción (número propio del cliente: falta la aprobación de Meta del Embedded Signup) | WHATSAPP_PLAN |
| BYOK de LLM (OpenAI compatible, OpenRouter, Anthropic) | backend en producción; UI sin desplegar | BYOK_LLM_PLAN |
| Link para llamar (navegador) y resumen de cada llamada por email | en producción | LINK_LLAMADA_PLAN, AGENTS.md |
| Grabación por mensaje | existe, apagada por default; la privacidad de la landing dice que no se graba | AGENTS.md |
| Derivación o transferencia a un humano | **no existe** | plan, sección 0 |
| Documentación pública de la API | **no**: OpenAPI solo para admin | ARQUITECTURA |
| Multi-cliente para un integrador (subclientes, marca blanca, panel de reseller) | **no**: el admin crea un cliente por cada uno; el integrador necesita un usuario por cliente | ARQUITECTURA (permisos) |
| Conector de Odoo | **no**: es por API y webhook (lo hace Axioma) | — |

Antes de la demo con campañas: habilitar `voice` en el tier `Interno` (o en uno de prueba), una campaña con 2-3 números
propios (paso 6 de "Cómo desplegar") y mirar los `sip_status`.

### 7.5 Fases sugeridas

1. **Semana 0 (ya):** registro Free para Axel, guía corta de la API (llamada web, voces, agente) y la demo técnica de 30 min
   si la quiere.
2. **Semanas 1-2:** piloto con sus leads: un agente calificador, un número de origen, campaña con webhook a su Odoo (lo
   integra Axioma), horario de 9 a 18 h, 1-2 llamadas a la vez.
3. **Semanas 3-4:** medir contra la línea de base y elegir el primer caso para un cliente suyo (recordatorio de TodoTurnos o
   soporte Odoo).
4. **Después:** acuerdo de canal (precio mayorista, cuentas por cliente, documentación pública de la API, marca blanca si la
   piden).

### 7.6 La oferta

- **Incluye:** cuenta con el canal de campañas de voz habilitado, un número argentino, el agente armado con ellos, la voz
  que elijan, webhook a su sistema, soporte directo durante el piloto.
- **Cómo se mide:** línea de base de Axioma (cuántos leads por mes, cuánto tardan hoy en el primer contacto, % que agenda
  diagnóstico) contra el piloto: contactabilidad (`contact_rate`), tiempo al primer intento, `goal_rate` (diagnóstico
  agendado), minutos usados, y su opinión sobre la integración (horas que les llevó).
- **Precio:** 30 días, precio fijo y bajo, no gratis (plan, sección 5). Referencia publicada: Sucursal $ 99.000 por mes
  (1.200 min, 3 llamadas a la vez, 3 números, "Llamadas programadas"). Precio de partner o mayorista: **pendiente**, a
  definir con el usuario.
- **Para el canal:** se les habla de aliados: margen o comisión sobre lo que revendan, sin exclusividad.

## 8. Base para el prompt del agente

### 8.1 Rol y tono

Asistente de Axioma IT que llama a quienes dejaron sus datos para el Kit 4.0 o una implementación de Odoo. Voseo, cordial,
técnico sin jerga, frases cortas. Se presenta como asistente virtual de Axioma; no se hace pasar por una persona.

### 8.2 Reglas

- Abre con el nombre, la empresa y el motivo ("dejaste tus datos para el Kit 4.0"); pide permiso para seguir.
- Si le preguntan si es una IA, lo dice. Si piden no ser llamados, resultado "No volver a llamar" (baja por voz).
- No da precios cerrados ni promete el cofinanciamiento: explica que se define en el diagnóstico.
- Una pregunta por vez; si la persona está ocupada, ofrece otro horario y lo registra.

### 8.3 Triage y datos

| Salida | Cuándo | Datos a pedir |
|---|---|---|
| Diagnóstico agendado (objetivo) | califica e interesa | empresa, rubro, empleados, MiPyME (sí/no/no sabe), años de actividad, qué ordenar primero, día y franja |
| Volver a llamar | no puede ahora | día y franja |
| Seguir por WhatsApp | prefiere escrito | confirmar el número |
| No califica | sin certificado MiPyME o menos de 2 años (Kit) | motivo; ofrecer implementación sin Kit |
| No volver a llamar | lo pide | — |

Al vendedor (webhook a Odoo): resultado, campos, resumen de 3 líneas, link a la conversación.

### 8.4 Preguntas para la charla (descubrimiento)

1. ¿Qué CRM es el de los leads: el Odoo de Axioma o el de un cliente? ¿Cuántos leads entran por mes y por qué canal?
2. ¿Quién los llama hoy, cuánto tardan y qué pasa con los que no atienden?
3. ¿El "momento determinado" es un evento (lead nuevo, etapa) o una agenda (fecha y hora por lead)?
4. ¿Lo quieren para Axioma, para clientes, o las dos? ¿Qué clientes tienen hoy con llamadas a mano (TodoTurnos, soporte,
   cobranzas)?
5. ¿Qué necesitan de nosotros para revender: documentación pública, cuentas por cliente, marca blanca, precio mayorista?
6. ¿Qué tendría que pasar en 30 días para seguir?

## 9. Fuentes

Leídas el 22-oct-2026.

- **Sitio:** https://axiomait.com/ · https://axiomait.com/l (→ https://axiomait.com/landing-odoo/) ·
  https://axiomait.com/contacto/ · https://axiomait.com/cultura/ · https://axiomait.com/quienes-somos/ ·
  https://axiomait.com/soluciones-ia/ · https://axiomait.com/odoo/ · https://axiomait.com/odoo-planes/ ·
  https://axiomait.com/soporte-odoo/ · https://axiomait.com/kit-4-0/ · https://axiomait.com/referidos/ ·
  https://axiomait.com/microsoft-power-platform/ · https://axiomait.com/staff-augmentation/ ·
  https://axiomait.com/flowery-bpm/ · https://axiomait.com/politica-de-privacidad/ · https://axiomait.com/politica-de-calidad/ ·
  https://axiomait.com/wp-json/wp/v2/pages · https://axiomait.com/wp-json/wp/v2/posts
- **Casos:** https://axiomait.com/badent/ · https://axiomait.com/sanatorio-proyecto/ · https://axiomait.com/proyecto-milele/ ·
  https://axiomait.com/neumaticos-olmos/ · https://axiomait.com/proyecto-path-examinations/ · https://axiomait.com/adt-proyecto/ ·
  https://axiomait.com/wolke/ · https://axiomait.com/atlas-renewable-energy/
- **Productos:** https://todoturnos.com/ · https://flowery.ar/
- **Directorios y reseñas:** https://www.odoo.com/es/partners/axioma-it-solutions-s-r-l-5854088?country_id=11 ·
  https://erpresearch.com/odoo-partners/axioma-it-solutions-s-r-l · https://clutch.co/profile/axioma-it-solutions ·
  Google Maps "Axioma IT Solutions, Patagones 2665"
- **Redes:** https://www.linkedin.com/company/axioma-it-solutions/ · https://www.youtube.com/watch?v=ADMS6Z3-hbg ·
  https://www.instagram.com/axiomaitsolutions (no leída) · https://www.facebook.com/AxiomaITSolutionsSRL (no leída)
- **Conversación:** base de la app, `conversations.id = e0e4e64d-0ad8-4e25-ac4d-1f717be51985` (copia en `raw/`).
- **Atentina:** `README.md`, `docs/ARQUITECTURA.md`, `docs/LLAMADAS_SALIENTES_PLAN.md` (14), `docs/API_INFERENCIA.md`,
  `tts/finetune/voces.tsv`, `landing/src/data/site.ts`, `docs/capacity/README.md`, `docs/competencia/`,
  `docs/mercado/demanda-y-mercado-local.md`.
