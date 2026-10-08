# Software e IA, partners, tanda 3 (7-oct-2026): consultoras e integradores de toda Argentina, 65 posibles aliados

**Borrador, sin enviar.** Tercera tanda de canales de software e IA: empresas de software, consultoras tecnológicas e integradores
que ya implementan IA para sus clientes (agentes conversacionales, automatización, datos e IA, ERP/CRM con IA, GovTech, software
vertical con IA), todas de Argentina: CABA, GBA y provincia de Buenos Aires (30: CABA 15, GBA 6, Mar del Plata 1, Buenos Aires sin dirección publicada 8) e interior (35: Córdoba 11, Santa Fe 7, Mendoza 6, Neuquén 4, Río Negro 2, Entre Ríos 2, Tucumán 1, Salta 1, La Pampa 1).
Propuesta, la misma de las tandas 1 y 2: **solución integral con telefonía incluida y agentes de voz con IA** para que la revendan o la
integren: ellos ponen el cliente y la integración; nosotros, la voz y la telefonía (número, SIP, STT/LLM/TTS propio, WhatsApp, API
`/api/v1`, panel multi-cliente). Contactos 204 a 268 de [`../seguimiento.md`](../seguimiento.md). Ficha completa, con
todos los emails, fuentes y links por canal, en [`2026-10-07-software-ia-partners-3.csv`](2026-10-07-software-ia-partners-3.csv). Formato:
[`README.md`](README.md). Notas, fuentes recorridas, reservas y descartes: `scratch/prospectos/software-ia-3/bsas/notas_bsas.md` y
`scratch/prospectos/software-ia-3/interior/notas_interior.md`. Textos generados por `scratch/prospectos/software-ia-3/tools/gen3.py` con
las plantillas de la tanda 1.

- **Emails:** todos publicados y vistos en su fuente: fichas *Next from Argentina* de Cancillería, fichas de socio de CESSI y de
  ATICMA (Mar del Plata), fichas públicas de partner de odoo.com, catálogo de socios del Córdoba Technology Cluster (API pública del
  catálogo), fichas de socio del Polo Tecnológico Rosario, listado de socios de Infotech Patagonia (Neuquén) y los sitios (`curl`;
  Cloudflare `data-cfemail` decodificado). Ninguno deducido por patrón. Todos los dominios de los ★ tienen MX (7-oct-2026). 15 de 65 tienen
  email de una persona; 50 van a una casilla de área (7) o de atención (43), marcada como genérica en el `.csv`. En las fichas
  de Cancillería, de los clusters y de odoo.com el email de contacto a veces no dice el cargo: se anota como "persona (cargo no publicado)".
- **Saludo:** nombre y tuteo solo si el ★ es la casilla de esa persona; si no, "Hola, ¿cómo están?".
- **Lo que el texto promete y existe:** teléfono entrante y saliente con número incluido, WhatsApp (texto y llamadas, hoy con el
  número de Atentina; el número propio del cliente, Embedded Signup, está implementado y sin desplegar: no prometerlo en la charla),
  API `/api/v1`, panel multi-cliente, voces argentinas, inferencia propia. No promete marca blanca ni campañas de voz por lista.
- **Precio:** el mail dice que el minuto queda "muy por debajo" de armarlo con Twilio, ElevenLabs y OpenAI, sin cifra. Respaldo para la
  charla (plan, sección 3): todo incluido USD 0,08-0,15 por minuto contra 0,28-0,35 de los agentes de voz locales sobre Vapi + Twilio;
  telefonía saliente ~USD 0,016 por minuto contra 0,35 de Twilio. Mayorista para canales: USD 0,10 por minuto o 20-30 % recurrente.
- **Ganchos para revisar antes de enviar:** salen de cada sitio o ficha (campo "Gancho"), con la fuente.
- Link con UTM `utm_campaign=canales4&utm_content=<empresa>`; registro en "Links con UTM" de `seguimiento.md`.
- Dominio nuevo: 3 o 4 por hora, tandas de ~10 (65 mails son dos o tres días hábiles). Seguimiento: una línea en el mismo hilo ~4 días
  hábiles después de cada envío (el 12-oct es feriado).
- **LinkedIn:** cada empresa trae una nota corta (≤ 300 caracteres, para invitación) y un mensaje largo, por si el usuario prefiere ese
  canal con el CEO; si lo usa, va a la tabla "LinkedIn" de `seguimiento.md` con `utm_source=linkedin`. El link de LinkedIn de la
  persona se anota solo cuando está enlazado en el sitio o en la ficha de la fuente.
- **WhatsApp (buscado el 7-oct-2026):** 25 de 65 publican un número (en "Otros canales" de cada empresa, con fuente); en las otras
  40 no hay WhatsApp en el sitio ni en las fichas (Instagram, Facebook, LinkedIn y Google Business no se pudieron revisar: piden
  sesión). Formato +54 9 ..., salvo donde la empresa lo publica sin el 9. Canal pendiente: no hay mensaje redactado ni se envió nada.

## Para revisar antes de enviar

Avisos de los dos lotes (detalle en `notas_bsas.md` y `notas_interior.md`):

Buenos Aires:

- **Cargos no publicados:** Axel Díaz (Axioma IT), "Lucas" (Hitofusion) y `gflores@` (MG Intelligence) salen de las fichas públicas
  de partner de odoo.com, que dan el email pero no el cargo (ni el nombre completo, en los dos últimos). Se saluda por el nombre
  de pila donde lo hay; MG Intelligence va con "Hola, ¿cómo están?".
- **Ciudad sin verificar:** Quantit y Silogik no publican la ciudad en el sitio (solo "Buenos Aires"; la ciudad sale de directorios
  externos, ver el campo lugar).
- **Sin IA publicada** (marcado en "Por qué encaja"): MG Intelligence, Cloud Solutions LATAM y Proda son partners de ERP/CRM sin
  práctica de IA en el sitio; entran como integradores que pueden sumar la voz a sus implementaciones.
- **C&S Informática:** el sitio no tiene texto legible; los datos salen de las fichas de *Next from Argentina* y de CESSI.
- **TGV:** el botón de WhatsApp del sitio lleva a un número de EE. UU. (+1 208 649-0291); se anota tal cual, sin usarlo.
- **Moment of People** quedó en reservas (`notas_bsas.md`): un testimonio municipal menciona "IA de voz"; revisar si venden voz
  antes de tratarla como partner.

Interior:

- **Sitios con 403 al rastreador** (user-agent ClaudeBot, sin `robots.txt` que lo prohíba): Global Think, ERPYCA, GoodComex,
  Patagonian, Grupo Orange y Corpora se leyeron con user-agent de navegador (`dl/ua2_*`); está anotado en el gancho de cada una.
- **Encaje parcial:** Program Consultores (GovTech, sin IA en el sitio); Glowix/Neos, Hexium, Grupo Orange e Inteligencia Analítica
  (partners de Dynamics u Odoo, o BI, con poca IA publicada); Quay e Idear Tech (sitios con texto de plantilla); Grupo Aicon
  (testimonios del sitio pendientes de verificar); GoodComex (sede Mendoza según el sitio, Córdoba según la ficha de Odoo).
- **Nombres incompletos o sin cargo en ★ de persona:** Gaspar (ERPYCA) y Joaquín (Alpardata) sin apellido publicado; Pablo Molla
  (Dynetis) sin cargo; Jorge Burkle (Emser) tomado de la política de calidad publicada en el sitio.
- **LinkedIn de persona:** solo cuando está enlazado en el sitio o en la ficha; en el resto, "—".

| # | Contacto | Empresa | País, lugar | Web | Email ★ | Tipo | Quién | utm_content |
|---|---|---|---|---|---|---|---|---|
| S1 | 204 | Pipe Tech | Argentina, Pilar (Buenos Aires); oficina en Barcelona | https://www.pipe.com.ar | frojas@pipe.com.ar | persona | Federico Rodriguez Rojas, CEO/fundador | pipe-tech |
| S2 | 205 | TGV | Argentina, CABA | https://www.tgv.com.ar | mkt@tgv.com.ar | área | marketing | tgv |
| S3 | 206 | Mutt Data | Argentina, CABA | https://muttdata.ai | sales@muttdata.ai | área | ventas | muttdata |
| S4 | 207 | Pigmalion Software | Argentina, CABA (Av. Pueyrredón 510); oficinas en Barcelona y Ciudad de México | https://pigmalion.co | hello@pigmalion.co | atención | casilla general | pigmalion |
| S5 | 208 | Tekne Data Labs | Argentina, CABA (oficina); sociedad en Delaware (EE. UU.) | https://teknedatalabs.com | info@teknedatalabs.com | atención | contacto de la ficha | tekne-data-labs |
| S6 | 209 | C&S Informática | Argentina, CABA | https://www.cys.com.ar | info@cys.com.ar | atención | casilla general | cys |
| S7 | 210 | Appstract | Argentina, CABA (Virrey Liniers 2384, piso 10) | https://appstract.us | sales@appstract.us | área | ventas | appstract |
| S8 | 211 | IT Maker | Argentina, CABA | https://www.itmaker.com.ar | info@itmaker.com.ar | atención | casilla general | it-maker |
| S9 | 212 | Big Data Estratégico | Argentina, CABA | https://bigdataestrategico.com | info@bigdataestrategico.com | atención | casilla general | big-data-estrategico |
| S10 | 213 | Cloud Solutions LATAM | Argentina, Buenos Aires (el sitio dice 'Operamos desde Buenos Aires, Argentina'); proyectos en Colombia, Chile y México | https://www.cloudsolutionslatam.com | hola@cloudsolutionslatam.com | atención | casilla general | cloud-solutions-latam |
| S11 | 214 | HabSar | Argentina, Buenos Aires (teléfono 11; el sitio dice 'Argentina') | https://www.habsar.com | contact@habsar.com | atención | casilla general | habsar |
| S12 | 215 | Axcelere | Argentina, CABA (Av. del Libertador 7274, Núñez) | https://www.axcelere.com | hola@axcelere.com | atención | casilla general | axcelere |
| S13 | 216 | Blueorange Group | Argentina, San Martín (Buenos Aires), Carrillo 2133 | https://www.blueorange.com.ar | contacto@blueorange.com.ar | atención | comercial | blueorange |
| S14 | 217 | Axioma IT Solutions | Argentina, CABA (Patagones 2665, Polo Tecnológico) | https://axiomait.com | axel.diaz@axiomait.com | persona | Axel Díaz, contacto de la ficha de partner | axioma-it |
| S15 | 218 | Hitofusion (Yügo SAS) | Argentina, Florida, Vicente López (Las Heras 2550) y CABA (Pico 3340); oficina en Luján de Cuyo (Mendoza) | https://www.hitofusion.com | lucas@hitofusion.com | persona | Lucas | hitofusion |
| S16 | 219 | MG Intelligence | Argentina, Lomas de San Isidro (Francisco Berra 3058) | https://www.mgintelligence.com | gflores@mgintelligence.com | persona | contacto de la ficha de partner | mg-intelligence |
| S17 | 220 | Chroma Agency | Argentina, CABA (Olavarría 1150, of. 563); también Medellín y Querétaro | https://chroma.agency | web@chroma.agency | atención | casilla general | chroma |
| S18 | 221 | ITBS Business Solutions | Argentina, CABA (Retiro, Distrito Quartier) | https://www.it-bs.com.ar | contacto@it-bs.com.ar | atención | casilla general | itbs |
| S19 | 222 | Sysmo | Argentina, Buenos Aires (teléfono 11; el sitio no publica dirección) | https://sysmo.com.ar | info@sysmo.com.ar | atención | casilla general | sysmo |
| S20 | 223 | RockingData | Argentina, CABA (Costa Rica 5546, Palermo) | https://rockingdata.ai | hello@rockingdata.com.ar | atención | casilla general | rockingdata |
| S21 | 224 | Accedra | Argentina, CABA (Irala 1950, 2.º piso) | https://www.accedra.com.ar | info@accedra.com.ar | atención | casilla general | accedra |
| S22 | 225 | BGlobal Solutions | Argentina, Buenos Aires (el sitio dice 'Buenos Aires | Argentina'); también Montevideo, Madrid y Miami | https://bglobalsolutions.com | info@bglobalsolutions.com | atención | casilla general | bglobal |
| S23 | 226 | PositiveIT | Argentina, Morón (Cacique Coliqueo 1041); oficina en Santiago de Chile | https://www.positiveit.com.ar | info@positiveit.com.ar | atención | casilla general | positiveit |
| S24 | 227 | Zennon BI | Argentina, CABA (Alicia Moreau de Justo 1150, Puerto Madero) | https://zennonbi.com | contacto@zennonbi.com | atención | casilla general | zennon |
| S25 | 228 | GrowIT | Argentina, Buenos Aires (el sitio dice 'Oficina: Buenos Aires, Argentina') | https://growit.com.ar | contacto@growit.com.ar | atención | casilla general | growit |
| S26 | 229 | Quantit | Argentina, Buenos Aires (ciudad no publicada en el sitio; perfil de LinkedIn de la empresa en Buenos Aires, según snippet de búsqueda) | https://bequantit.com | somos@bequantit.com | atención | casilla general | quantit |
| S27 | 230 | Silogik | Argentina, Buenos Aires (ciudad no publicada en el sitio; elioplus la ubica en Av. Niceto Vega 4736, CABA, según snippet; la página devuelve 403) | https://www.silogik.com | info@silogik.com | atención | casilla general | silogik |
| S28 | 231 | Proda Software | Argentina, Bernal, Quilmes (Chiclana 444) | https://www.prodasoftware.com | german@prodasoftware.com | persona | Germán Gail, fundador | proda |
| S29 | 232 | Datcom Software | Argentina, Mar del Plata (Olavarría 2838, piso 5) | https://www.datcom.io | info@datcom.io | atención | casilla general | datcom |
| S30 | 233 | Potencia Technologies | Argentina, Buenos Aires (el sitio dice 'Buenos Aires - Argentina'; teléfonos 11) | https://www.potenciatech.ar | info@potenciatech.ar | atención | casilla general | potencia-tech |
| S31 | 234 | GiGa Global | Argentina, Córdoba capital | https://www.gigaglobal.com.ar | hola@gigaglobal.com.ar | atención | casilla general | giga-global |
| S32 | 235 | Global Think Technology | Argentina, Córdoba capital | https://globalthink.io | dghione@globalthinktec.com | persona | Diego Néstor Ghione, CEO | global-think |
| S33 | 236 | Mindfactory | Argentina, Córdoba capital | https://www.mindfactory.ar | sebastian.sosa@mindfactory.ar | persona | Sebastián Sosa, CEO | mindfactory |
| S34 | 237 | Program Consultores (PGM) | Argentina, Córdoba capital | https://www.municipalidad.com | agiraudo@municipalidad.com | persona | Alberto Giraudo, CEO | program-consultores |
| S35 | 238 | Emser | Argentina, Córdoba capital | http://www.emser.net | Jburkle@emser.net | persona | Jorge Burkle, Dirección General | emser |
| S36 | 239 | DinoCloud | Argentina, Córdoba capital | https://dinocloud.co | info@dinocloud.co | atención | casilla general del sitio | dinocloud |
| S37 | 240 | Vatrox | Argentina, Córdoba capital | https://vatrox.com | contacto@vatrox.com | atención | casilla general del sitio | vatrox |
| S38 | 241 | Olpa Group | Argentina, Córdoba capital | https://olpagroup.com | info@olpagroup.com | atención | casilla general | olpa-group |
| S39 | 242 | Castelsoft | Argentina, Córdoba capital | https://castelsoft.com | info@castelsoft.com | atención | casilla general | castelsoft |
| S40 | 243 | Dynetis | Argentina, Villa Carlos Paz (Córdoba) | https://www.dynetis.com | pablo.molla@dynetis.com | persona | Pablo Molla | dynetis |
| S41 | 244 | Glowix / Neos Tech | Argentina, Villa María (Córdoba) | https://www.neos.com.ar | ggomezarrufat@neos.com.ar | persona | Gustavo Gómez Arrufat, CEO | glowix-neos |
| S42 | 245 | Psiware | Argentina, Rosario (Santa Fe) | https://www.psiware.com.ar | contact@psiware.com.ar | atención | casilla general | psiware |
| S43 | 246 | Idear Tech | Argentina, Rosario (Santa Fe) | https://ideartechcorp.com | negocios@ideartechcorp.com | área | negocios | idear-tech |
| S44 | 247 | Inteligencia Analítica | Argentina, Rosario (Santa Fe) | https://www.inteligenciaanalitica.com | contacto@inteligenciaanalitica.com | atención | casilla general | inteligencia-analitica |
| S45 | 248 | Grupo Aicon | Argentina, Rosario y Armstrong (Santa Fe) | https://grupoaicon.com.ar | administracion@grupoaicon.com.ar | atención | casilla general | grupo-aicon |
| S46 | 249 | Alchemid | Argentina, Rafaela (Santa Fe) | https://www.alchemid.com | contacto@alchemid.com | atención | casilla general de la ficha de Odoo | alchemid |
| S47 | 250 | M3C Software | Argentina, Rosario (Santa Fe) | https://m3csoftware.com | comercial@m3csoftware.com.ar | área | comercial | m3c |
| S48 | 251 | ERPYCA | Argentina, Rosario (Santa Fe) | https://erpyca.com | gaspar@erpyca.com | persona | Gaspar | erpyca |
| S49 | 252 | devFactory | Argentina, Luján de Cuyo (Mendoza) | https://devfactory.ar | contact@devfactory.ar | atención | casilla general | devfactory |
| S50 | 253 | Solutions Hub / AGP & ROD Servicios | Argentina, Mendoza capital | https://solutionshub.com.ar | rodrigo.lopez@solutionshub.com.ar | persona | Rodrigo López | solutions-hub |
| S51 | 254 | Alpardata | Argentina, Guaymallén (Mendoza) | https://www.alpardata.com.ar | joaquin@alpardata.com.ar | persona | Joaquín | alpardata |
| S52 | 255 | Hexium Software Factory | Argentina, Godoy Cruz (Mendoza) | https://hexium.com.ar | info@hexium.com.ar | atención | casilla general | hexium |
| S53 | 256 | Corpora | Argentina, Maipú (Mendoza) | https://www.somoscorpora.com | gerencia@somoscorpora.com | área | gerencia | corpora |
| S54 | 257 | GoodComex (Full Comex SAS) | Argentina, Mendoza (sitio; la ficha de Odoo da una oficina en Córdoba) | https://goodcomex.com | marcelo.vazquez@goodcomex.com | persona | Marcelo Vázquez | goodcomex |
| S55 | 258 | Solution IT (SIT) | Argentina, Neuquén capital | https://www.solution-it.com.ar | info@solution-it.com.ar | atención | casilla general | solution-it |
| S56 | 259 | PuntoGap | Argentina, Neuquén capital | https://www.puntogap.com | info@puntogap.com | atención | casilla general | puntogap |
| S57 | 260 | Pragmática Consultores | Argentina, Neuquén capital | https://www.pragmaticaconsultores.com | info@pragmaticaconsultores.com | atención | casilla general | pragmatica |
| S58 | 261 | DITyC | Argentina, Neuquén capital | https://www.dityc.com.ar | info@dityc.com.ar | atención | casilla general | dityc |
| S59 | 262 | Patagonian | Argentina, General Roca (Río Negro) | https://patagonian.com | info@patagonian.com | atención | casilla general | patagonian |
| S60 | 263 | Waiki Consultores en Sistemas | Argentina, Cipolletti (Río Negro) | https://waiki.com.ar | info@waiki.com.ar | atención | casilla general | waiki |
| S61 | 264 | Ingenio Solutions | Argentina, Chajarí (Entre Ríos) | https://ingeniosolutions.com.ar | contacto@ingeniosolutions.com.ar | atención | casilla general | ingenio-solutions |
| S62 | 265 | Quay | Argentina, Concordia (Entre Ríos) | https://quay.com.ar | info@quay.com.ar | atención | casilla general | quay |
| S63 | 266 | Tecopens Consulting | Argentina, San Miguel de Tucumán | https://www.tecopensconsulting.com | equipo@tecopensconsulting.com | atención | casilla general | tecopens |
| S64 | 267 | Grupo Orange | Argentina, Salta capital | https://grupoorange.com.ar | info@grupoorange.com.ar | atención | casilla general | grupo-orange |
| S65 | 268 | Grupo Mill | Argentina, Santa Rosa (La Pampa) | https://grupomill.com | comunicacion@grupomill.com | área | comunicación | grupo-mill |

## S1. Pipe Tech

- Contacto 204 de `seguimiento.md`
- Rubro: Software a medida, IA aplicada, automatización de procesos y bots conversacionales, Pilar (Buenos Aires); oficina en Barcelona (Argentina)
- Web: https://www.pipe.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende agentes y bots conversacionales a pymes de muchos rubros (agro, salud, logística, gobierno, según la ficha); la voz por teléfono es el canal que no construye.
- Gancho: 'Software · Inteligencia Artificial · Automatización': 'Agentes, copilotos y modelos que entienden tu negocio y trabajan junto a tu equipo todos los días'; socio tecnológico desde 2009 (home, 7-oct-2026). Ficha de Cancillería: 'bots conversacionales', consultas a bases de datos en lenguaje natural; 20 personas, SAS fundada en 2018, Pilar; CEO/fundador Federico Rodriguez Rojas.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | frojas@pipe.com.ar | persona | Federico Rodriguez Rojas, CEO/fundador (ficha: 'CEO/FOUNDER') | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/pipe-tech (ficha Next from Argentina, Cancillería; bajada el 7-oct-2026) |
|  | info@pipe.com.ar | atención | casilla general | https://www.pipe.com.ar/contacto (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/pipe-tech-sas/; persona https://www.linkedin.com/in/rrojasfederico/ (enlazado en la ficha); también https://www.linkedin.com/in/adrian-tavella.

Otros canales: formulario https://www.pipe.com.ar/contacto; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/pipetech.ok.

Para:

```
frojas@pipe.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Pipe Tech
```

Texto:

```
Hola Federico, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Pipe Tech ya arma agentes y bots conversacionales que automatizan procesos de sus clientes: el teléfono, con número incluido, es el canal que le falta a esos mismos agentes.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=pipe-tech

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (288 caracteres):

```
Hola Federico, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Pipe Tech. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Federico, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Pipe Tech ya arma agentes y bots conversacionales que automatizan procesos de sus clientes: el teléfono, con número incluido, es el canal que le falta a esos mismos agentes.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=pipe-tech

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S2. TGV

- Contacto 205 de `seguimiento.md`
- Rubro: Software a medida e implementación de SAP y JD Edwards; soluciones de IA empresarial, CABA (Argentina)
- Web: https://www.tgv.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Implementador de ERP con práctica de IA y cientos de clientes medianos que cobran y atienden por teléfono; puede integrar el agente de voz a SAP o JDE.
- Gancho: 'Soluciones de Inteligencia Artificial Empresarial'; 'Melissa, nuestro agente de IA junto a Oracle sobre OCI, que ya responde en tiempo real dentro del ERP JD Edwards' (home, 7-oct-2026). Fundó el Polo IT de Buenos Aires y es socia de CESSI; 300 personas, fundada en 1992, CMMI (ficha de Cancillería).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | mkt@tgv.com.ar | área | marketing (contacto de la ficha; el sitio no publica emails) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/tgv (ficha Next from Argentina, Cancillería; bajada el 7-oct-2026) |
|  | info@tgv.com.ar | atención | casilla general | https://cessi.org.ar/socio/tgv/ (ficha de socio de CESSI, bajada el 5-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Ernesto Galíndez, CEO/fundador (ficha de Cancillería; LinkedIn enlazado en /nuestro-equipo).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/tgv/; persona https://www.linkedin.com/in/ernesto-galindez-817799/ (enlazado en /nuestro-equipo).

Otros canales: formulario https://www.tgv.com.ar/contactanos; WhatsApp wa.me/12086490291 ('Hola TGV cuentame mas'), botón del sitio con un número de EE. UU. (7-oct-2026); redes https://www.instagram.com/tgvgroup.

Para:

```
mkt@tgv.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de TGV
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

TGV ya vende IA empresarial dentro del ERP, como Melissa en JD Edwards: un agente que atienda y llame por teléfono a los clientes de esas empresas es la pieza que sigue, integrada por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=tgv

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (273 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como TGV. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

TGV ya vende IA empresarial dentro del ERP, como Melissa en JD Edwards: un agente que atienda y llame por teléfono a los clientes de esas empresas es la pieza que sigue, integrada por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=tgv

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S3. Mutt Data

- Contacto 206 de `seguimiento.md`
- Rubro: Consultora de datos e IA: plataformas de datos (Databricks, AWS) y soluciones de ML y GenAI, CABA (Argentina)
- Web: https://muttdata.ai
- Tipo: posible aliado (canal)
- Por qué encaja: Consultora de IA de 100 personas con clientes de banca, fintech y retail: puede sumar la voz telefónica a los proyectos que ya hace.
- Gancho: 'Modern Data Platform & AI Consulting'; 'AI Enterprise Partner of the Year' de Databricks, 'más de 90 expertos certificados por Databricks', partner de AWS (home, 7-oct-2026). 108 personas, fundada en 2018; CEO/fundador Juan Martín Pampliega; clientes en banca, fintech, retail y marketing (ficha de Cancillería).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | sales@muttdata.ai | área | ventas (contacto de la ficha; el sitio no publica emails) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/muttdata (ficha Next from Argentina, Cancillería; bajada el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Juan Martín Pampliega, CEO/fundador (ficha de Cancillería).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/mutt-data/; persona https://www.linkedin.com/in/juan-martin-pampliega/ (enlazado en la ficha).

Otros canales: formulario https://muttdata.ai/contact; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/mutt.data ; https://x.com/mutt_data.

Para:

```
sales@muttdata.ai
```

Asunto:

```
Voz y telefonía para los agentes de IA de Mutt Data
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Mutt Data ya construye plataformas de datos e IA para bancos, fintechs y retailers: un agente de voz que atienda y llame a los clientes de esas empresas se conecta a esa misma plataforma por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=muttdata

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (279 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Mutt Data. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Mutt Data ya construye plataformas de datos e IA para bancos, fintechs y retailers: un agente de voz que atienda y llame a los clientes de esas empresas se conecta a esa misma plataforma por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=muttdata

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S4. Pigmalion Software

- Contacto 207 de `seguimiento.md`
- Rubro: Desarrollo de software y productos digitales; datos, analítica e IA para industria y finanzas, CABA (Av. Pueyrredón 510); oficinas en Barcelona y Ciudad de México (Argentina)
- Web: https://pigmalion.co
- Tipo: posible aliado (canal)
- Por qué encaja: Construye modelos de IA y software para industria y finanzas; la voz telefónica es un canal más para esos clientes.
- Gancho: Servicios de 'IA y Ciencia de Datos', desarrollo a medida y equipos dedicados; 'Data, analytics, and AI solutions' para empresas industriales y financieras (sitio, leído el 7-oct-2026; ficha de Cancillería). 35 personas, fundada en 2010; CEO/fundador Diego Martiniano.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | hello@pigmalion.co | atención | casilla general | https://pigmalion.co/home/ (7-oct-2026) |
|  | hi@pigmalion.co | atención | contacto de la ficha | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/pigmalion-software (ficha Next from Argentina, Cancillería; bajada el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Diego Martiniano, CEO/fundador (ficha de Cancillería).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/pigmalion-software/; persona https://www.linkedin.com/in/dmartiniano/ (enlazado en la ficha).

Otros canales: formulario https://pigmalion.co/home/ (formulario de contacto); WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes —.

Para:

```
hello@pigmalion.co
```

Asunto:

```
Voz y telefonía para los agentes de IA de Pigmalion Software
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Pigmalion ya entrega modelos de IA y software a empresas industriales y financieras: el teléfono es el canal que esas empresas siguen atendiendo a mano, y un agente de voz se integra a lo que ustedes construyen.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=pigmalion

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (288 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Pigmalion Software. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Pigmalion ya entrega modelos de IA y software a empresas industriales y financieras: el teléfono es el canal que esas empresas siguen atendiendo a mano, y un agente de voz se integra a lo que ustedes construyen.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=pigmalion

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S5. Tekne Data Labs

- Contacto 208 de `seguimiento.md`
- Rubro: Consultora de datos e IA: plataformas de datos, agentes y automatización inteligente, CABA (oficina); sociedad en Delaware (EE. UU.) (Argentina)
- Web: https://teknedatalabs.com
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende agentes de IA y automatización a seguros, energía y fintech; la voz por teléfono completa esos agentes.
- Gancho: 'Data, IA y Automatización Inteligente'; 'Agentes y flujos que conectan la IA a tu operación y ejecutan trabajo real'; clientes Experta ART, DirecTV, Pan American Energy (sitio, leído el 7-oct-2026). 23 personas, fundada en 2020, CABA; CEO/fundador Rigoberto Malca La Rosa (ficha de Cancillería). Socia de CESSI.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@teknedatalabs.com | atención | contacto de la ficha (el sitio no publica emails) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/teknedatalabs (ficha Next from Argentina, Cancillería; bajada el 7-oct-2026) |
|  | admin@teknedatalabs.com | área | administración | https://cessi.org.ar/socio/teknedatalabs/ (ficha de socio de CESSI, bajada el 5-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Rigoberto Malca La Rosa, CEO/cofundador; Axel García Giménez, cofundador (sitio y ficha).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/teknedatalabs/; persona https://www.linkedin.com/in/rigoxu/ ; https://www.linkedin.com/in/agarciagimenez/ (enlazados en la ficha).

Otros canales: formulario https://teknedatalabs.com/ (formulario); WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes —.

Para:

```
info@teknedatalabs.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Tekne Data Labs
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Tekne ya despliega agentes y flujos de IA que ejecutan trabajo real en aseguradoras y energéticas: atender y hacer llamadas por teléfono es el flujo que sigue, y se conecta por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=tekne-data-labs

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (285 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Tekne Data Labs. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Tekne ya despliega agentes y flujos de IA que ejecutan trabajo real en aseguradoras y energéticas: atender y hacer llamadas por teléfono es el flujo que sigue, y se conecta por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=tekne-data-labs

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S6. C&S Informática

- Contacto 209 de `seguimiento.md`
- Rubro: Soluciones tecnológicas a medida con IA, automatización y analítica de datos, CABA (Argentina)
- Web: https://www.cys.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Software factory grande con práctica de IA y clientes de gobierno y logística: puede integrar la voz en sus proyectos y revenderla.
- Gancho: 'C&S develops custom technology solutions by integrating software, artificial intelligence, automation and data analytics to optimize processes'; 116 personas, fundada en 1985; CEO/fundador Norberto César Caniggia; industrias: gobierno, logística, manufactura, educación (ficha de Cancillería). Socia de CESSI (categoría IA y BI). El sitio es una aplicación sin texto legible: los datos salen de las fichas.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@cys.com.ar | atención | casilla general (ficha de Cancillería y de CESSI) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/cs-informatica-sa (ficha Next from Argentina, Cancillería; bajada el 7-oct-2026); https://cessi.org.ar/socio/cs/ (ficha de socio de CESSI, bajada el 5-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Norberto César Caniggia, CEO/fundador; Franco Boette (LinkedIn enlazados en la ficha).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/c&s-informatica-s.a. (ficha); persona https://www.linkedin.com/in/norberto-caniggia-cys/ ; https://www.linkedin.com/in/franco-boette-cys/ (ficha).

Otros canales: formulario https://www.cys.com.ar/ (sitio en Angular; no se pudo leer el formulario); WhatsApp — (sin WhatsApp publicado: el sitio no tiene texto legible; las fichas no lo publican; 7-oct-2026); redes —.

Para:

```
info@cys.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de C&S Informática
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

C&S ya integra IA, automatización y analítica en software a medida para gobierno y logística: un agente que atienda y llame por teléfono es una pieza más de esos proyectos, con número incluido.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=cys

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (285 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como C&S Informática. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

C&S ya integra IA, automatización y analítica en software a medida para gobierno y logística: un agente que atienda y llame por teléfono es una pieza más de esos proyectos, con número incluido.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=cys

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S7. Appstract

- Contacto 210 de `seguimiento.md`
- Rubro: Software a medida, automatización de procesos e integración de sistemas con IA, CABA (Virrey Liniers 2384, piso 10) (Argentina)
- Web: https://appstract.us
- Tipo: posible aliado (canal)
- Por qué encaja: Automatiza procesos con IA para clientes de varios rubros; las llamadas de atención y cobranza son un proceso más para automatizar.
- Gancho: 'AI-Powered Business Process Automation': 'helps organizations improve operational efficiency through custom software, process automation, systems integration and artificial intelligence'; 20 personas, fundada en 2016; CEO/fundador Pablo Telmo; industrias: construcción, finanzas, gobierno, logística (ficha de Cancillería). La home dice solo 'We transform your ideas into apps' (7-oct-2026).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | sales@appstract.us | área | ventas (contacto de la ficha; el sitio no publica emails) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/appstract (ficha Next from Argentina, Cancillería; bajada el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Pablo Telmo, CEO/fundador; Andrés Sosto (LinkedIn enlazados en la ficha).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/appstractweb/; persona https://www.linkedin.com/in/ptelmo/ ; https://www.linkedin.com/in/andres-sosto-ab36944/ (ficha).

Otros canales: formulario https://appstract.us/ (formulario 'Let's work together'); WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/appstract.us.

Para:

```
sales@appstract.us
```

Asunto:

```
Voz y telefonía para los agentes de IA de Appstract
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Appstract ya automatiza procesos de negocio con IA e integra sistemas para sus clientes: las llamadas de atención y cobranza son el proceso que sigue, y se suman por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=appstract

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (279 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Appstract. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Appstract ya automatiza procesos de negocio con IA e integra sistemas para sus clientes: las llamadas de atención y cobranza son el proceso que sigue, y se suman por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=appstract

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S8. IT Maker

- Contacto 211 de `seguimiento.md`
- Rubro: Consultora de integración y analítica de datos, gobierno de datos e IA, CABA (Argentina)
- Web: https://www.itmaker.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Consultora de datos de 60 personas con clientes en servicios públicos (mucho teléfono); puede sumar la voz a sus integraciones.
- Gancho: 'Data Hub Services'; 'Data Governance, Integration, Analytics, and AI'; 'data integration and analytics consulting firm capable of working with any platform'; 60 personas, fundada en 2011; CEO/fundador Flavio Fazzano; industrias: empresas en general y servicios públicos (ficha de Cancillería; home, 7-oct-2026).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@itmaker.com.ar | atención | casilla general | https://www.itmaker.com.ar/ (7-oct-2026); https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/it-maker (ficha Next from Argentina, Cancillería; bajada el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Flavio Fazzano, CEO/fundador (ficha de Cancillería).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/itmakerarg; persona https://www.linkedin.com/in/flaviofazzano/ (ficha).

Otros canales: formulario https://www.itmaker.com.ar/ (formulario); WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://x.com/ITMakerArg.

Para:

```
info@itmaker.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de IT Maker
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

IT Maker ya integra datos y analítica con IA para empresas y servicios públicos: un agente de voz que atienda y llame a los usuarios de esas empresas se alimenta de esas mismas integraciones.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=it-maker

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (278 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como IT Maker. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

IT Maker ya integra datos y analítica con IA para empresas y servicios públicos: un agente de voz que atienda y llame a los usuarios de esas empresas se alimenta de esas mismas integraciones.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=it-maker

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S9. Big Data Estratégico

- Contacto 212 de `seguimiento.md`
- Rubro: Consultora chica de transformación digital, datos e IA: chats con IA por WhatsApp y Telegram, automatizaciones, BI, CABA (Argentina)
- Web: https://bigdataestrategico.com
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende chats con IA por WhatsApp a organizaciones; el teléfono es el canal que no cubre. Muy chica (5 personas).
- Gancho: 'Creamos chats con IA para hablar con los datos de la empresa preguntando con lenguaje natural a través de WhatsApp y Telegram'; soluciones con 'automatizaciones, bases de datos, APIs, inteligencia artificial, OCR, tableros' (home, 7-oct-2026). 5 personas, fundada en 2022; CEO Ignacio Bruera (ficha de Cancillería). Reserva de la tanda 2 por tamaño.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@bigdataestrategico.com | atención | casilla general (ficha; el sitio no publica emails) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/big-data-estrategico (ficha Next from Argentina, Cancillería; bajada el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Ignacio Bruera, CEO/fundador; Pablo Rey (LinkedIn enlazados en la ficha).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/big-data-estrategico/; persona https://www.linkedin.com/in/ignaciobruera/ (ficha).

Otros canales: formulario https://bigdataestrategico.com/ (formulario); WhatsApp +54 9 11 5920-3837: https://wa.me/5491159203837 ('Hola, quiero mas informacion'), botón de la home (7-oct-2026); redes https://www.instagram.com/bigdataestrategico_.

Para:

```
info@bigdataestrategico.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Big Data Estratégico
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Big Data Estratégico ya arma chats con IA por WhatsApp y Telegram para hablar con los datos de la empresa: el mismo asistente puede atender la línea telefónica de esos clientes, con número incluido.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=big-data-estrategico

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (290 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Big Data Estratégico. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Big Data Estratégico ya arma chats con IA por WhatsApp y Telegram para hablar con los datos de la empresa: el mismo asistente puede atender la línea telefónica de esos clientes, con número incluido.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=big-data-estrategico

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S10. Cloud Solutions LATAM

- Contacto 213 de `seguimiento.md`
- Rubro: Zoho Advanced Partner: consultoría e implementación de Zoho (CRM, BI, Creator) para empresas de LATAM, Buenos Aires (el sitio dice 'Operamos desde Buenos Aires, Argentina'); proyectos en Colombia, Chile y México (Argentina)
- Web: https://www.cloudsolutionslatam.com
- Tipo: posible aliado (canal)
- Por qué encaja: Implementa Zoho CRM en empresas medianas de la región; el agente telefónico que registra cada contacto en el CRM es un producto para su cartera. Sin IA publicada.
- Gancho: 'Consultoría e implementación de Zoho para empresas en LATAM. Ordená procesos, mejorá decisiones y adoptá tecnología con criterio'; 'Zoho Advanced Partner certificado para Argentina y LATAM'; participó del encuentro global de partners de Zoho en India 2025 (home y /nosotros, 7-oct-2026). No menciona IA.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | hola@cloudsolutionslatam.com | atención | casilla general | https://www.cloudsolutionslatam.com/contacto (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/cloudsolutionslatam/; persona —.

Otros canales: formulario https://www.cloudsolutionslatam.com/contacto; WhatsApp — (el pie dice 'WhatsApp — Diagnóstico gratuito' pero no publica número ni link; revisados home, contacto y nosotros, 7-oct-2026); redes https://www.instagram.com/cloudsolutionslatam.

Para:

```
hola@cloudsolutionslatam.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Cloud Solutions LATAM
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Cloud Solutions ya implementa Zoho CRM en empresas de toda la región: un agente que atienda y llame por teléfono y deje cada contacto en el CRM es el módulo que esos clientes siguen cubriendo con personas.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=cloud-solutions-latam

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (291 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Cloud Solutions LATAM. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Cloud Solutions ya implementa Zoho CRM en empresas de toda la región: un agente que atienda y llame por teléfono y deje cada contacto en el CRM es el módulo que esos clientes siguen cubriendo con personas.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=cloud-solutions-latam

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S11. HabSar

- Contacto 214 de `seguimiento.md`
- Rubro: Agencia técnica y HubSpot Solutions Provider: implementación de CRM, integraciones y automatizaciones para pymes, Buenos Aires (teléfono 11; el sitio dice 'Argentina') (Argentina)
- Web: https://www.habsar.com
- Tipo: posible aliado (canal)
- Por qué encaja: Integra WhatsApp y automatizaciones en HubSpot para pymes; la voz telefónica es una integración más que puede revender.
- Gancho: 'Implementación de CRM, integraciones y automatizaciones para PYMEs'; 'Conectamos tu web con CRM, WhatsApp, pagos, automatizaciones y todo lo que uses' (home, 7-oct-2026). En el directorio de HubSpot: 'agencia técnica especializada en migraciones, arquitectura de procesos y automatizaciones a medida'.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | contact@habsar.com | atención | casilla general | https://www.habsar.com/contacto (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 11 3934-2834 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/habsar; persona —.

Otros canales: formulario https://www.habsar.com/contacto; WhatsApp +54 11 3934-2834: https://api.whatsapp.com/send/?phone=541139342834 ('Hola, quiero saber más de sus servicios'), botón del sitio (7-oct-2026); redes https://www.instagram.com/habsar.it.

Para:

```
contact@habsar.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de HabSar
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

HabSar ya conecta WhatsApp, pagos y automatizaciones al CRM de sus clientes: el teléfono atendido por un agente y registrado en HubSpot es la integración que les falta.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=habsar

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (276 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como HabSar. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

HabSar ya conecta WhatsApp, pagos y automatizaciones al CRM de sus clientes: el teléfono atendido por un agente y registrado en HubSpot es la integración que les falta.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=habsar

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S12. Axcelere

- Contacto 215 de `seguimiento.md`
- Rubro: Partner Gold de Odoo: tecnología de gestión y consultoría de negocios 'para la transformación digital con inteligencia artificial', CABA (Av. del Libertador 7274, Núñez) (Argentina)
- Web: https://www.axcelere.com
- Tipo: posible aliado (canal)
- Por qué encaja: Implementador de Odoo para medianas que cobran y atienden por teléfono; el agente de voz se integra al ERP y entra en su catálogo.
- Gancho: 'potencia tu empresa con tecnología de gestión y consultoría de negocios para la transformación digital con inteligencia artificial' (descripción del sitio, 7-oct-2026). Partner Gold de Odoo con 92 referencias, proyecto más grande de 500+ usuarios, 91 % de retención; industrias: mayorista/minorista, construcción, manufactura (ficha de odoo.com).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | hola@axcelere.com | atención | casilla general | https://www.axcelere.com/contacto (7-oct-2026); https://www.odoo.com/es/partners/axcelere-1758871?country_id=11 (ficha de partner en odoo.com, bajada el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 9 11 5141-1716 (ficha de odoo.com).

LinkedIn: empresa https://ar.linkedin.com/company/axcelere; persona —.

Otros canales: formulario https://www.axcelere.com/contacto; WhatsApp https://wa.me/message/YCAWZZM6FW5KN1 (botón 'Envía un WhatsApp' de /contacto, número no visible; 7-oct-2026); redes —.

Para:

```
hola@axcelere.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Axcelere
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Axcelere ya implementa Odoo con IA en empresas de distribución y construcción: un agente que atienda y llame por teléfono, conectado al ERP, es el módulo que sus clientes siguen resolviendo a mano.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=axcelere

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (278 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Axcelere. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Axcelere ya implementa Odoo con IA en empresas de distribución y construcción: un agente que atienda y llame por teléfono, conectado al ERP, es el módulo que sus clientes siguen resolviendo a mano.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=axcelere

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S13. Blueorange Group

- Contacto 216 de `seguimiento.md`
- Rubro: Partner Gold de Odoo con localización argentina propia; WhatsApp Bot desde Odoo, San Martín (Buenos Aires), Carrillo 2133 (Argentina)
- Web: https://www.blueorange.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende un bot de WhatsApp dentro de Odoo a pymes; el teléfono atendido por un agente, integrado al mismo ERP, es el paso siguiente.
- Gancho: 'Partner Gold de Odoo · ISO 9001'; producto 'WhatsApp Bot: Atendé y notificá a tus clientes desde Odoo por WhatsApp' (home, 7-oct-2026). 134 referencias, 95 % de retención, 'los mayores desarrolladores de Odoo en Argentina y Uruguay' (ficha de odoo.com y erpresearch).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | contacto@blueorange.com.ar | atención | comercial (casilla general) | https://www.blueorange.com.ar/contacto (7-oct-2026); https://www.odoo.com/es/partners/blueorange-group-s-r-l-1635129?country_id=11 (ficha de partner en odoo.com, bajada el 7-oct-2026) |
|  | odoo@blueorange.com.ar | área | soporte | https://www.blueorange.com.ar/contacto (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 9 11 7078-7090 (ficha de odoo.com).

LinkedIn: empresa https://www.linkedin.com/company/blueorangegroupsrl; persona —.

Otros canales: formulario https://www.blueorange.com.ar/contacto; WhatsApp Comercial +54 9 11 3058-1769 (texto del pie); soporte https://wa.me/5491130015820 (botón 'Hablemos por WhatsApp'; 7-oct-2026); redes —.

Para:

```
contacto@blueorange.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Blueorange Group
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Blueorange ya vende un bot de WhatsApp que atiende y notifica desde Odoo: un agente que haga lo mismo por teléfono, con número incluido y conectado al ERP, completa esa oferta.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=blueorange

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (286 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Blueorange Group. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Blueorange ya vende un bot de WhatsApp que atiende y notifica desde Odoo: un agente que haga lo mismo por teléfono, con número incluido y conectado al ERP, completa esa oferta.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=blueorange

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S14. Axioma IT Solutions

- Contacto 217 de `seguimiento.md`
- Rubro: Software factory y staff augmentation; partner de Odoo y Microsoft 365; soluciones de IA, CABA (Patagones 2665, Polo Tecnológico) (Argentina)
- Web: https://axiomait.com
- Tipo: posible aliado (canal)
- Por qué encaja: Vende IA, Odoo y desarrollo a medida a pymes; la voz telefónica se integra a esos ERP y a sus desarrollos.
- Gancho: 'Soluciones IA: Potenciamos tu negocio con soluciones de inteligencia artificial que automatizan procesos y mejoran la toma de decisiones'; 'consultoría e implementación de las plataformas de Microsoft 365 y Odoo, de las cuales somos partners oficiales' (home, 7-oct-2026). Partner Silver de Odoo, 30 referencias, 97 % de retención (ficha de odoo.com).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | axel.diaz@axiomait.com | persona | Axel Díaz, contacto de la ficha de partner (cargo no publicado) | https://www.odoo.com/es/partners/axioma-it-solutions-s-r-l-5854088?country_id=11 (ficha de partner en odoo.com, bajada el 7-oct-2026) |
|  | contacto@axiomait.com | atención | casilla general | https://axiomait.com/contacto (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: +54 11 4978-4822 (sitio y ficha de odoo.com).

LinkedIn: empresa https://ar.linkedin.com/company/axioma-it-solutions; persona —.

Otros canales: formulario https://axiomait.com/contacto; WhatsApp +54 9 11 4978-4822: https://api.whatsapp.com/send/?phone=5491149784822 ('Hola! Quisiera más info sobre sus servicios'), botón del sitio (7-oct-2026); redes https://www.instagram.com/axiomaitsolutions.

Para:

```
axel.diaz@axiomait.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Axioma IT Solutions
```

Texto:

```
Hola Axel, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Axioma ya vende soluciones de IA que automatizan procesos e implementa Odoo y Microsoft 365: un agente que atienda y llame por teléfono, conectado a esos sistemas, es el servicio que le falta al catálogo.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=axioma-it

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (294 caracteres):

```
Hola Axel, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Axioma IT Solutions. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Axel, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Axioma ya vende soluciones de IA que automatizan procesos e implementa Odoo y Microsoft 365: un agente que atienda y llame por teléfono, conectado a esos sistemas, es el servicio que le falta al catálogo.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=axioma-it

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S15. Hitofusion (Yügo SAS)

- Contacto 218 de `seguimiento.md`
- Rubro: Partner Gold de Odoo; Jinzo, plataforma de agentes de IA integrada a Odoo, Florida, Vicente López (Las Heras 2550) y CABA (Pico 3340); oficina en Luján de Cuyo (Mendoza) (Argentina)
- Web: https://www.hitofusion.com
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende agentes de IA dentro de Odoo (Jinzo) y la integración con WhatsApp; el teléfono es el canal que esos agentes no tienen.
- Gancho: 'JINZO + ODOO, IA empresarial: Agentes de inteligencia artificial conectados con tus procesos, permisos y datos reales'; 'Su integración nativa con Odoo permite que los agentes consulten información y ejecuten tareas dentro del ERP'; integraciones 'Odoo + WhatsApp/IG/FB' (home, 7-oct-2026). Partner Gold como Yügo SAS, 71 referencias, 96 % de retención (ficha de odoo.com).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | lucas@hitofusion.com | persona | Lucas (apellido y cargo no publicados), contacto de la ficha de partner | https://www.odoo.com/es/partners/yugo-sas-24338942?country_id=11 (ficha de partner en odoo.com, bajada el 7-oct-2026) |
|  | hola@hitofusion.com | atención | casilla general | https://www.hitofusion.com/ (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: +54 9 11 7100-6160 (ficha de odoo.com); administración +54 9 11 2174-9985 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/hitofusion; persona — (una búsqueda web asocia a 'Lucas G. Burgos', https://ar.linkedin.com/in/lucasburgos, con Hitofusion; no verificado en el sitio).

Otros canales: formulario https://www.hitofusion.com/ (formulario); WhatsApp +54 9 11 7100-6160: https://wa.me/5491171006160 ('Buen día, me interesa el soporte'), botón 'Hablemos por whatsapp' (7-oct-2026); redes https://www.instagram.com/hitofusion.odoo.arg.

Para:

```
lucas@hitofusion.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Hitofusion
```

Texto:

```
Hola Lucas, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Hitofusion ya vende Jinzo, agentes de IA que trabajan dentro de Odoo, y la integración con WhatsApp: el mismo agente atendiendo y llamando por teléfono, con número incluido, es el canal que falta.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=hitofusion

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (286 caracteres):

```
Hola Lucas, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Hitofusion. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Lucas, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Hitofusion ya vende Jinzo, agentes de IA que trabajan dentro de Odoo, y la integración con WhatsApp: el mismo agente atendiendo y llamando por teléfono, con número incluido, es el canal que falta.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=hitofusion

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S16. MG Intelligence

- Contacto 219 de `seguimiento.md`
- Rubro: Partner de Odoo: ERP, automatización y consultoría tecnológica para empresas en crecimiento, Lomas de San Isidro (Francisco Berra 3058) (Argentina)
- Web: https://www.mgintelligence.com
- Tipo: posible aliado (canal)
- Por qué encaja: Implementa ERP y automatización en medianas de distribución, manufactura y servicios públicos; el agente de voz es una automatización más conectada a Odoo.
- Gancho: 'Socios tecnológicos de empresas en desarrollo que buscan escalar, automatizar y tomar decisiones basadas en datos reales'; 'Automatización: Reducimos tareas manuales, errores y tiempos operativos'; '+15 años' (home, 7-oct-2026). Partner de Odoo con 6 consultores certificados en la v19, proyecto más grande de 300+ usuarios, 100 % de retención (ficha de odoo.com). No menciona IA.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | gflores@mgintelligence.com | persona | contacto de la ficha de partner (nombre y cargo no publicados) | https://www.odoo.com/es/partners/mg-intelligence-s-r-l-13441990?country_id=11 (ficha de partner en odoo.com, bajada el 7-oct-2026) |
|  | comercial@mgintelligence.com | área | comercial | https://www.mgintelligence.com/ (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: +54 11 6613-5566 (ficha de odoo.com).

LinkedIn: empresa — (no enlazado en el sitio); persona —.

Otros canales: formulario https://www.mgintelligence.com/ (formulario 'Diagnóstico operativo'); WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes —.

Para:

```
gflores@mgintelligence.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de MG Intelligence
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

MG Intelligence ya automatiza la operación de empresas medianas sobre Odoo: las llamadas de cobranza, pedidos y atención son la tarea manual que sigue, y un agente de voz las toma conectado al ERP.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=mg-intelligence

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (285 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como MG Intelligence. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

MG Intelligence ya automatiza la operación de empresas medianas sobre Odoo: las llamadas de cobranza, pedidos y atención son la tarea manual que sigue, y un agente de voz las toma conectado al ERP.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=mg-intelligence

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S17. Chroma Agency

- Contacto 220 de `seguimiento.md`
- Rubro: Implementación de Odoo ERP y consultoría de negocios; desarrollo de chatbots con IA, CABA (Olavarría 1150, of. 563); también Medellín y Querétaro (Argentina)
- Web: https://chroma.agency
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende chatbots con IA junto con Odoo; el canal de voz telefónica integrado al ERP completa su oferta.
- Gancho: 'Desarrollos: Página WEB | Chatbots con IA | Aplicaciones webs y nativas'; 'Implementamos Odoo ERP, revisamos tus procesos y te ayudamos a digitalizar tu empresa' (home, 7-oct-2026). Partner de Odoo con certificaciones v18 y v19, proyecto más grande de 100+ usuarios (ficha de odoo.com).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | web@chroma.agency | atención | casilla general | https://chroma.agency/contact-us (7-oct-2026) |
|  | odoo@chroma.agency | área | Odoo (contacto de la ficha de partner) | https://www.odoo.com/es/partners/chroma-agency-3377991?country_id=11 (ficha de partner en odoo.com, bajada el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 11 7079-0150 (ficha de odoo.com).

LinkedIn: empresa https://www.linkedin.com/company/chroma-agency-soft/; persona —.

Otros canales: formulario https://chroma.agency/contact-us; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/chroma_agency_.

Para:

```
web@chroma.agency
```

Asunto:

```
Voz y telefonía para los agentes de IA de Chroma Agency
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Chroma ya vende chatbots con IA e implementa Odoo: el mismo asistente atendiendo y llamando por teléfono, con número incluido y conectado al ERP, es el canal que le falta a sus clientes.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=chroma

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (283 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Chroma Agency. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Chroma ya vende chatbots con IA e implementa Odoo: el mismo asistente atendiendo y llamando por teléfono, con número incluido y conectado al ERP, es el canal que le falta a sus clientes.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=chroma

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S18. ITBS Business Solutions

- Contacto 221 de `seguimiento.md`
- Rubro: Partner Silver de Odoo y canal oficial de Buenos Aires Software (BAS); evolución hacia la IA, CABA (Retiro, Distrito Quartier) (Argentina)
- Web: https://www.it-bs.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Implementador de ERP para pymes en crecimiento que suma IA a su catálogo; el agente de voz integrado a Odoo o BAS es un producto que puede revender.
- Gancho: 'Con más de 20 años de trayectoria implementando soluciones informáticas, nuestra evolución hacia la Inteligencia Artificial es el paso natural para multiplicar tus resultados'; 'implementa Odoo y BAS para empresas argentinas en proceso de escalar', 'soporte con SLA menor a 2 horas' (home, 7-oct-2026). Fundador y director: Lic. Fernando Bernain (datos estructurados del sitio).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | contacto@it-bs.com.ar | atención | casilla general (contacto comercial) | https://www.it-bs.com.ar/contacto (7-oct-2026); https://www.odoo.com/es/partners/itbs-business-solutions-523?country_id=11 (ficha de partner en odoo.com, bajada el 7-oct-2026) |
|  | administracion@it-bs.com.ar | área | administración | https://www.it-bs.com.ar/contacto (7-oct-2026) |
|  | soporte@it-bs.com.ar | área | soporte | https://www.it-bs.com.ar/contacto (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Fernando Bernain, fundador y director (JSON-LD del sitio; LinkedIn enlazado).

Teléfonos: +54 11 3985-0010 (ficha de odoo.com).

LinkedIn: empresa https://www.linkedin.com/company/itbs-business-solutions; persona https://www.linkedin.com/in/fernandobernain/ (enlazado en el sitio).

Otros canales: formulario https://www.it-bs.com.ar/contacto; WhatsApp +54 9 11 7547-3844: https://wa.me/5491175473844 ('Hola, me interesa conocer más sobre los servicios de ITBS'), botón del sitio (7-oct-2026); redes —.

Para:

```
contacto@it-bs.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de ITBS Business Solutions
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

ITBS ya implementa Odoo y BAS en pymes que escalan y dice que su paso natural es la IA: un agente que atienda y llame por teléfono, conectado a esos ERP, es un producto concreto para ese paso.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=itbs

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (293 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como ITBS Business Solutions. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

ITBS ya implementa Odoo y BAS en pymes que escalan y dice que su paso natural es la IA: un agente que atienda y llame por teléfono, conectado a esos ERP, es un producto concreto para ese paso.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=itbs

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S19. Sysmo

- Contacto 222 de `seguimiento.md`
- Rubro: Consultora de software a medida para empresas y gobiernos: automatizaciones e IA, chatbots, apps para municipios, Buenos Aires (teléfono 11; el sitio no publica dirección) (Argentina)
- Web: https://sysmo.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende chatbots con IA y software a municipios y empresas; el teléfono es el canal de atención ciudadana que no cubre.
- Gancho: 'Automatizaciones e Inteligencia Artificial: Optimizamos tus procesos con soluciones de automatización e inteligencia artificial'; 'Atención 24/7 con IA conversacional: Chatbots y asistentes virtuales que responden de forma natural e integrada a tu sistema'; proyecto 'Aplicación móvil para municipios' (home, 7-oct-2026). Una nota de LinkedIn la vincula con la gestión documental con IA del Municipio de Tigre (snippet de búsqueda, no verificado).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@sysmo.com.ar | atención | casilla general | https://sysmo.com.ar/contact (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 9 11 6577-7390 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/sysmo; persona — (la página /team es una plantilla con nombres de relleno).

Otros canales: formulario https://sysmo.com.ar/contact; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://x.com/sysmosrl.

Para:

```
info@sysmo.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Sysmo
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Sysmo ya vende chatbots con IA y aplicaciones a municipios y empresas: la línea telefónica de atención, atendida por el mismo asistente y con número incluido, es el canal que falta en esos proyectos.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=sysmo

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (275 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Sysmo. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Sysmo ya vende chatbots con IA y aplicaciones a municipios y empresas: la línea telefónica de atención, atendida por el mismo asistente y con número incluido, es el canal que falta en esos proyectos.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=sysmo

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S20. RockingData

- Contacto 223 de `seguimiento.md`
- Rubro: Consultora de IA, machine learning y datos; adopción de GenAI, CABA (Costa Rica 5546, Palermo) (Argentina)
- Web: https://rockingdata.ai
- Tipo: posible aliado (canal)
- Por qué encaja: Consultora de IA con clientes en banca, seguros y salud, los rubros que más llaman; puede integrar la voz en sus proyectos.
- Gancho: 'Creamos algoritmos de inteligencia artificial y machine learning para tu negocio'; servicio 'GenAI Strategic Adoption'; casos de segmentación de clientes y campañas personalizadas (home, 7-oct-2026). CEO y fundador Fredi Vivas; clientes en banca, seguros, salud, telecomunicaciones y retail (innovaciondigital360.com, entrevista).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | hello@rockingdata.com.ar | atención | casilla general | https://rockingdata.ai/contactanos (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Fredi Vivas, CEO y fundador (prensa: innovaciondigital360.com; no enlazado en el sitio).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/rockingdata/; persona —.

Otros canales: formulario https://rockingdata.ai/contactanos; WhatsApp +54 11 3172-2737: https://api.whatsapp.com/send?phone=541131722737, botón del sitio (7-oct-2026); redes https://www.instagram.com/rockingdata ; https://twitter.com/rockingdata.

Para:

```
hello@rockingdata.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de RockingData
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

RockingData ya lleva IA y GenAI a bancos, aseguradoras y empresas de salud: un agente de voz que atienda y llame a los clientes de esas empresas se apoya en los modelos que ustedes ya construyen.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=rockingdata

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (281 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como RockingData. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

RockingData ya lleva IA y GenAI a bancos, aseguradoras y empresas de salud: un agente de voz que atienda y llame a los clientes de esas empresas se apoya en los modelos que ustedes ya construyen.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=rockingdata

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S21. Accedra

- Contacto 224 de `seguimiento.md`
- Rubro: Infraestructura IT, ciberseguridad, consultoría Microsoft y 'Software & AI' para empresas, CABA (Irala 1950, 2.º piso) (Argentina)
- Web: https://www.accedra.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Integrador con 400 clientes empresa que ya vende IA aplicada y consultoría Microsoft; puede revender la voz como un servicio más.
- Gancho: 'Software & AI: Software a medida e inteligencia artificial aplicada a tus procesos'; Copilot; '17 años y +400 proyectos en Argentina'; 'Partner certificado y distribuidor autorizado de cada fabricante' (home, 7-oct-2026).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@accedra.com.ar | atención | casilla general | https://www.accedra.com.ar/ (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 11 5365-9887 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/accedra-s.a.; persona —.

Otros canales: formulario https://www.accedra.com.ar/ (formulario 'Contanos tu caso'); WhatsApp +54 11 3300-1233: https://wa.me/541133001233 (mensaje prearmado 'Hola, soy [nombre] de [empresa]...'), botón 'Hablar por WhatsApp' (7-oct-2026); redes https://www.instagram.com/accedra_sa.

Para:

```
info@accedra.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Accedra
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Accedra ya vende software a medida e IA aplicada a más de 400 empresas: un agente que atienda y llame por teléfono, con número incluido, es un servicio más para esa base de clientes.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=accedra

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (277 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Accedra. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Accedra ya vende software a medida e IA aplicada a más de 400 empresas: un agente que atienda y llame por teléfono, con número incluido, es un servicio más para esa base de clientes.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=accedra

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S22. BGlobal Solutions

- Contacto 225 de `seguimiento.md`
- Rubro: Premier Partner de Creatio (CRM y BPM no-code con agentes de IA); implementación de CRM, add-ons y servicios IT, Buenos Aires (el sitio dice 'Buenos Aires | Argentina'); también Montevideo, Madrid y Miami (Argentina)
- Web: https://bglobalsolutions.com
- Tipo: posible aliado (canal)
- Por qué encaja: Implementa CRM y BPM con agentes de IA en 200 clientes de la región; el agente telefónico conectado al CRM es lo que no tiene.
- Gancho: 'Crea aplicaciones y agentes de IA con diseñadores visuales y de lenguaje natural' (Creatio); 'En 2025 hemos sido distinguidos como Premier Partner, convirtiéndonos en los únicos en la región'; 'más de 200 clientes de diversas industrias' (home, 7-oct-2026).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@bglobalsolutions.com | atención | casilla general | https://bglobalsolutions.com/contacto (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/bglobal-solutions/; persona —.

Otros canales: formulario https://bglobalsolutions.com/contacto; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/bglobalsolutions ; https://twitter.com/BglobalSolution.

Para:

```
info@bglobalsolutions.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de BGlobal Solutions
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

BGlobal ya implementa Creatio con agentes de IA en más de 200 clientes: un agente que atienda y llame por teléfono y deje todo en el CRM es el canal que esos procesos todavía no tienen.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=bglobal

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (287 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como BGlobal Solutions. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

BGlobal ya implementa Creatio con agentes de IA en más de 200 clientes: un agente que atienda y llame por teléfono y deje todo en el CRM es el canal que esos procesos todavía no tienen.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=bglobal

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S23. PositiveIT

- Contacto 226 de `seguimiento.md`
- Rubro: Integradora de CRM (Salesforce, SugarCRM, Zoho), marketing automation, agentes de IA y bots, Morón (Cacique Coliqueo 1041); oficina en Santiago de Chile (Argentina)
- Web: https://www.positiveit.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende agentes de IA y bots junto con CRM a pymes y organismos; la voz telefónica integrada al CRM es el canal que no ofrece.
- Gancho: 'Diseñamos e integramos soluciones de CRM, agentes de IA y automatización de procesos'; 'Agentic AI y Bots: Diseñamos agentes inteligentes y bots conversacionales'; tecnologías Salesforce, SugarCRM, Zoho, Botmaker, SALESmanago, Bird (home, 7-oct-2026). Equipo: Guillermo Hindi (CEO), Germán Perrone (CTO), Mirian Taboada (CDO) (/nuestro-equipo). Socia de CESSI.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@positiveit.com.ar | atención | casilla general (Cloudflare data-cfemail, decodificado) | https://www.positiveit.com.ar/ (7-oct-2026); https://cessi.org.ar/socio/positive-it/ (ficha de socio de CESSI, bajada el 5-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Guillermo Hindi, CEO; Germán Perrone, CTO; Mirian Taboada, CDO (/nuestro-equipo, con botones de LinkedIn).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/positive-information-technology; persona — (botones de LinkedIn por persona en /nuestro-equipo, sin URL legible).

Otros canales: formulario https://www.positiveit.com.ar/ (formulario 'Ponte en contacto'); WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/positiveit.

Para:

```
info@positiveit.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de PositiveIT
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

PositiveIT ya integra agentes de IA y bots conversacionales con Salesforce, Zoho y SugarCRM: el mismo agente atendiendo y llamando por teléfono, con todo registrado en el CRM, es el canal que falta.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=positiveit

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (280 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como PositiveIT. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

PositiveIT ya integra agentes de IA y bots conversacionales con Salesforce, Zoho y SugarCRM: el mismo agente atendiendo y llamando por teléfono, con todo registrado en el CRM, es el canal que falta.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=positiveit

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S24. Zennon BI

- Contacto 227 de `seguimiento.md`
- Rubro: Partner de Microsoft Dynamics 365 y Power Platform; agentes de IA y copilots con Copilot Studio, CABA (Alicia Moreau de Justo 1150, Puerto Madero) (Argentina)
- Web: https://zennonbi.com
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende agentes de IA para atención y soporte sobre Dynamics; el teléfono atendido por un agente, con número incluido, es lo que Copilot Studio no le da.
- Gancho: 'IA & COPILOT, COPILOT STUDIO: Agentes de IA y copilots conectados a datos y procesos para atención, soporte y automatización, con experiencias conversacionales'; 'socios estratégicos de Microsoft Dynamics 365' (home y /nuestro-equipo, 7-oct-2026). Socia de CESSI (Dynamics 365, Power Platform, IA).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | contacto@zennonbi.com | atención | casilla general | https://zennonbi.com/contacto (7-oct-2026); https://cessi.org.ar/socio/zennon-bi/ (ficha de socio de CESSI, bajada el 5-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 11 5402-0593 (sitio).

LinkedIn: empresa — (no enlazado en el sitio); persona —.

Otros canales: formulario https://zennonbi.com/contacto; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes —.

Para:

```
contacto@zennonbi.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Zennon BI
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Zennon ya vende agentes de IA y copilots para atención y soporte sobre Dynamics 365: un agente que atienda y llame por teléfono, con número incluido y conectado al CRM, es el canal que esos copilots no cubren.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=zennon

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (279 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Zennon BI. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Zennon ya vende agentes de IA y copilots para atención y soporte sobre Dynamics 365: un agente que atienda y llame por teléfono, con número incluido y conectado al CRM, es el canal que esos copilots no cubren.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=zennon

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S25. GrowIT

- Contacto 228 de `seguimiento.md`
- Rubro: Transformación digital: CRM (SugarCRM), marketing automation, omnicanalidad y customer experience, con IA, Buenos Aires (el sitio dice 'Oficina: Buenos Aires, Argentina') (Argentina)
- Web: https://growit.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Integra CRM, automatización y omnicanalidad con IA en sus clientes; la voz telefónica es el canal que le falta a esa omnicanalidad.
- Gancho: 'identificar las estrategias, medios, canales y tecnologías adecuadas ... utilizando IA donde resulte necesario'; soluciones 'CRM, Marketing Automation, Omnicanalidad' y 'Customer Experience (CX)'; partner de Sugar (home y /contacto, 7-oct-2026). Partner de Zoho según elioplus (no verificado: la página devuelve 403).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | contacto@growit.com.ar | atención | casilla general | https://growit.com.ar/contacto (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/growit/; persona —.

Otros canales: formulario https://growit.com.ar/contacto; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes —.

Para:

```
contacto@growit.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de GrowIT
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

GrowIT ya arma CRM, marketing automation y omnicanalidad con IA para sus clientes: el teléfono atendido por un agente y registrado en el CRM es el canal que completa esa omnicanalidad.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=growit

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (276 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como GrowIT. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

GrowIT ya arma CRM, marketing automation y omnicanalidad con IA para sus clientes: el teléfono atendido por un agente y registrado en el CRM es el canal que completa esa omnicanalidad.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=growit

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S26. Quantit

- Contacto 229 de `seguimiento.md`
- Rubro: Desarrollo de IA a medida y ciencia de datos: PLN, chatbots, visión por computadora, GenAI, Buenos Aires (ciudad no publicada en el sitio; perfil de LinkedIn de la empresa en Buenos Aires, según snippet de búsqueda) (Argentina)
- Web: https://bequantit.com
- Tipo: posible aliado (canal)
- Por qué encaja: Ya desarrolla chatbots e IA de lenguaje a medida para empresas; la voz por teléfono, con inferencia local, es el canal que no construye.
- Gancho: 'Custom AI solutions'; 'Desarrollo de chatbots personalizados, motores de búsqueda basados en IA, análisis de opiniones de clientes, clasificación automática de documentos'; 'Chat GPT y otras herramientas de IA generativa' (home, 7-oct-2026). Socia de CESSI: 'Expertise en procesamiento de lenguaje natural, ... procesamiento de audio, Chatbots y Big Data'. Equipo con LinkedIn: Carla Felcher, Edgar Altszyler (PhD).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | somos@bequantit.com | atención | casilla general | https://bequantit.com/contactanos (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Carla Felcher y Edgar Altszyler (LinkedIn enlazados en el sitio, sin cargo publicado).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/quantitdata/; persona https://www.linkedin.com/in/carla-felcher-087326104/ ; https://www.linkedin.com/in/edgar-altszyler/ (enlazados en el sitio).

Otros canales: formulario https://bequantit.com/contactanos; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/bequantit.

Para:

```
somos@bequantit.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Quantit
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Quantit ya desarrolla chatbots y procesamiento de lenguaje a medida para empresas: el mismo asistente atendiendo y llamando por teléfono, con número incluido, es el canal que le falta a esos proyectos.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=quantit

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (277 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Quantit. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Quantit ya desarrolla chatbots y procesamiento de lenguaje a medida para empresas: el mismo asistente atendiendo y llamando por teléfono, con número incluido, es el canal que le falta a esos proyectos.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=quantit

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S27. Silogik

- Contacto 230 de `seguimiento.md`
- Rubro: Aceleración de procesos de negocio (BPA), RPA, integración de sistemas, analítica y desarrollo web y mobile, Buenos Aires (ciudad no publicada en el sitio; elioplus la ubica en Av. Niceto Vega 4736, CABA, según snippet; la página devuelve 403) (Argentina)
- Web: https://www.silogik.com
- Tipo: posible aliado (canal)
- Por qué encaja: Automatiza procesos con RPA e integra sistemas para sus clientes; las llamadas de atención y cobranza son el proceso que sigue.
- Gancho: 'Business Process Acceleration ... Robotic Process Automation ... Systems Integration'; 'Revolutionize your workflow with Business Process Automation (BPA)' (home, 7-oct-2026). Partner de Zoho según elioplus (no verificado).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@silogik.com | atención | casilla general | https://www.silogik.com/contactanos (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/silogik/; persona —.

Otros canales: formulario https://www.silogik.com/contactanos; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://twitter.com/Silogik.

Para:

```
info@silogik.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Silogik
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Silogik ya automatiza procesos con RPA e integra sistemas para sus clientes: las llamadas de atención, confirmación y cobranza son el proceso que sigue, y un agente de voz las toma por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=silogik

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (277 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Silogik. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Silogik ya automatiza procesos con RPA e integra sistemas para sus clientes: las llamadas de atención, confirmación y cobranza son el proceso que sigue, y un agente de voz las toma por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=silogik

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S28. Proda Software

- Contacto 231 de `seguimiento.md`
- Rubro: Partner de Zoho (Zoho One, CRM, Creator, Analytics); CRM B2B propio y plataforma no-code JRapid, Bernal, Quilmes (Chiclana 444) (Argentina)
- Web: https://www.prodasoftware.com
- Tipo: posible aliado (canal)
- Por qué encaja: Implementa Zoho CRM en pymes de la región; el agente telefónico conectado al CRM es un producto para su cartera. Sin IA publicada.
- Gancho: 'Fundada en 2005 en Buenos Aires'; '20 años brindando soluciones a empresas de todo Latinoamérica'; equipo: Germán Gail, Founder, 'JEE Architect - Zoho Expert' (/nosotros, 7-oct-2026). Ficha de CESSI: 'diseñando soluciones en la nube con la Suite Zoho One, con foco en las apps CRM, Creator y Analytics'. No menciona IA.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | german@prodasoftware.com | persona | Germán Gail, fundador (cargo en /nosotros; email en la ficha de CESSI) | https://cessi.org.ar/socio/proda-software/ (ficha de socio de CESSI, bajada el 5-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: +54 9 11 2395-3156 (sitio y ficha de CESSI).

LinkedIn: empresa https://www.linkedin.com/company/proda-software/; persona https://www.linkedin.com/in/germangail/ (enlazado en /nosotros).

Otros canales: formulario https://www.prodasoftware.com/contacto; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes —.

Para:

```
german@prodasoftware.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Proda Software
```

Texto:

```
Hola Germán, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Proda ya implementa Zoho CRM y Creator en pymes de toda la región: un agente que atienda y llame por teléfono, dejando cada contacto en el CRM, es el módulo que esos clientes siguen cubriendo con personas.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=proda

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (291 caracteres):

```
Hola Germán, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Proda Software. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Germán, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Proda ya implementa Zoho CRM y Creator en pymes de toda la región: un agente que atienda y llame por teléfono, dejando cada contacto en el CRM, es el módulo que esos clientes siguen cubriendo con personas.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=proda

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S29. Datcom Software

- Contacto 232 de `seguimiento.md`
- Rubro: Software para logística, trazabilidad y almacenaje (Dettron WMS) con IA y BI; industria 4.0, Mar del Plata (Olavarría 2838, piso 5) (Argentina)
- Web: https://www.datcom.io
- Tipo: posible aliado (canal)
- Por qué encaja: Software vertical de logística con IA para operadores y distribuidoras, que confirman entregas y pedidos por teléfono; canal al rubro logístico.
- Gancho: Solución 'Inteligencia Artificial' en el menú de productos junto a control de stock, picking y planificación logística; ISO 9001 (sitio, 7-oct-2026). Gastón Paradiso expuso 'IA en logística (predicción y control en tiempo real)' en ATICMA IA Talks (luma.com/h97t703i). Socia de ATICMA: 'soluciones de software vinculado a procesos de logística, trazabilidad, almacenaje, comercialización, administración y business intelligence'.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@datcom.io | atención | casilla general (ficha de ATICMA, entrada Dettron WMS) | https://www.aticma.org.ar/nuestros-socios/ (ficha de socio de ATICMA, Mar del Plata; bajada el 7-oct-2026) |
|  | info@datcomsoftware.com | atención | casilla general (ficha de ATICMA, entrada DATCOM Software S.A.; dominio viejo, MX en Plesk) | https://www.aticma.org.ar/nuestros-socios/ (ficha de socio de ATICMA, Mar del Plata; bajada el 7-oct-2026) |
|  | soporte@datcom.io | área | soporte | https://www.datcom.io/ (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Gastón Paradiso (orador por Datcom en ATICMA IA Talks; cargo no publicado).

Teléfonos: +54 223 559-9009 (ficha de ATICMA).

LinkedIn: empresa — (no enlazado en el sitio); persona —.

Otros canales: formulario https://www.datcom.io/ ('Solicitar Demo'); WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes —.

Para:

```
info@datcom.io
```

Asunto:

```
Voz y telefonía para los agentes de IA de Datcom Software
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Datcom ya vende un WMS con IA y tableros a operadores logísticos y distribuidoras: confirmar entregas y pedidos por teléfono con un agente, integrado a Dettron, es el canal que esos clientes siguen cubriendo a mano.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=datcom

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (285 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Datcom Software. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Datcom ya vende un WMS con IA y tableros a operadores logísticos y distribuidoras: confirmar entregas y pedidos por teléfono con un agente, integrado a Dettron, es el canal que esos clientes siguen cubriendo a mano.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=datcom

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S30. Potencia Technologies

- Contacto 233 de `seguimiento.md`
- Rubro: Productos SaaS nativos en IA para RRHH (SITA, selector de talentos) con WhatsApp Bot; CAIO on-demand, Buenos Aires (el sitio dice 'Buenos Aires - Argentina'; teléfonos 11) (Argentina)
- Web: https://www.potenciatech.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende IA y un bot de WhatsApp a áreas de RRHH y consultoras; llamar a candidatos y atender consultas por teléfono es el canal que no tiene. Vertical de RRHH: encaje por explorar.
- Gancho: SITA, 'Selector Inteligente de Talentos Automatizada', con 'ingesta omnicanal (WhatsApp, portales web, carga masiva)', 'WhatsApp Bot' y servicio 'CAIO (Chief AI Officer) On-Demand'; clientes CONA Consultores, Tradefood, Comfort Health (sitio, leído el 7-oct-2026). Socia de CESSI: 'Desarrollos de productos SaaS nativos en IA y a medida para empresas'.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@potenciatech.ar | atención | casilla general | https://www.potenciatech.ar/ (7-oct-2026) |
|  | soporte@potenciatech.ar | área | soporte | https://www.potenciatech.ar/ (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 9 11 6181-5415 ; +54 9 11 5723-9257 (sitio).

LinkedIn: empresa — (el pie menciona LinkedIn sin URL legible); persona —.

Otros canales: formulario https://www.potenciatech.ar/ (formulario); WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes —.

Para:

```
info@potenciatech.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Potencia Technologies
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Potencia ya vende SITA, selección de talentos con IA y bot de WhatsApp: llamar a los candidatos para confirmar entrevistas y atender sus consultas por teléfono es el canal que ese producto todavía no tiene.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=potencia-tech

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (291 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Potencia Technologies. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Potencia ya vende SITA, selección de talentos con IA y bot de WhatsApp: llamar a los candidatos para confirmar entrevistas y atender sus consultas por teléfono es el canal que ese producto todavía no tiene.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=potencia-tech

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S31. GiGa Global

- Contacto 234 de `seguimiento.md`
- Rubro: Partner Gold de Odoo; soluciones de IA, agentes y automatizaciones para empresas, Córdoba capital (Argentina)
- Web: https://www.gigaglobal.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende IA y agentes a sus clientes de Odoo; el teléfono es un canal que no construye y se integra al ERP.
- Gancho: 'Implementamos Odoo, desarrollamos soluciones de Inteligencia Artificial e integramos tecnología… Diseñamos soluciones de Inteligencia Artificial, agentes y automatizaciones' (home, 7-oct-2026). Partner Gold de Odoo con 43 referencias y 7 expertos certificados (ficha de Odoo). Fundada en 2012, 0-20 personas; clientes en Córdoba, Buenos Aires, Santa Fe, Neuquén y Chaco (catálogo CCT).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | hola@gigaglobal.com.ar | atención | casilla general (catálogo CCT, ficha de Odoo y home) | https://catalogo.cordobacluster.com/nuestros-socios (catálogo de socios del Córdoba Technology Cluster, API pública cordobatechnology.space:8443/empresas, bajada el 7-oct-2026); https://www.odoo.com/partners/giga-global-2824185 (ficha de partner oficial de Odoo, vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 9 351 612-7500 (ficha de Odoo; es el mismo número del WhatsApp del sitio).

LinkedIn: empresa https://www.linkedin.com/company/giga-global; persona —.

Otros canales: formulario https://www.gigaglobal.com.ar/ (formulario de la home); WhatsApp +54 9 351 612-7500: https://wa.me/5493516127500 en la home (7-oct-2026); redes https://www.instagram.com/giga.global.

Para:

```
hola@gigaglobal.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de GiGa Global
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

GiGa ya implementa Odoo y vende agentes de IA y automatizaciones a esos mismos clientes: el teléfono, con número incluido y conectado al ERP, es el canal que les falta.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=giga-global

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (281 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como GiGa Global. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

GiGa ya implementa Odoo y vende agentes de IA y automatizaciones a esos mismos clientes: el teléfono, con número incluido y conectado al ERP, es el canal que les falta.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=giga-global

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S32. Global Think Technology

- Contacto 235 de `seguimiento.md`
- Rubro: Consultora tecnológica AI-first: agentes de IA, automatización, outsourcing y producto propio, Córdoba capital (Argentina)
- Web: https://globalthink.io
- Tipo: posible aliado (canal)
- Por qué encaja: Ya despliega agentes de IA para atención en aseguradoras y telcos; la voz telefónica es el canal que falta en esos agentes.
- Gancho: 'Tecnología e inteligencia artificial para transformar negocios. Agentes que piensan, deciden y ejecutan… Aseguradoras: aplicamos IA para agilizar la atención, coordinar prestadores, automatizar procesos'; 'Más de 20 años diseñando y construyendo tecnología. Hoy, AI First' (sitio, 7-oct-2026). Fundada en 2002, 21-50 personas; clientes Telecom, Telefónica, Vittal, SOS y Banco Guayaquil (catálogo CCT). El sitio devuelve 403 al user-agent con 'ClaudeBot' sin prohibirlo en robots.txt: se leyó con user-agent de navegador (dl/ua2_globalthink.io.html).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | dghione@globalthinktec.com | persona | Diego Néstor Ghione, CEO | https://catalogo.cordobacluster.com/nuestros-socios (catálogo de socios del Córdoba Technology Cluster, API pública cordobatechnology.space:8443/empresas, bajada el 7-oct-2026) |
|  | fmorales@globalthinktec.com | persona | contacto de la ficha (nombre y cargo no publicados) | https://catalogo.cordobacluster.com/nuestros-socios (catálogo de socios del Córdoba Technology Cluster, API pública cordobatechnology.space:8443/empresas, bajada el 7-oct-2026) |
|  | talents@globalthink.io | área | talentos (RRHH), pie del sitio (Cloudflare data-cfemail, decodificado) | https://globalthink.io/ (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: +54 351 522-5148 (catálogo CCT).

LinkedIn: empresa https://www.linkedin.com/company/globalthinktechnolology (así, con la errata, en el catálogo y en el sitio); persona https://www.linkedin.com/in/diego-ghione-249259 (catálogo CCT).

Otros canales: formulario https://globalthink.io/ (formulario 'Hablemos'); WhatsApp — (sin WhatsApp publicado: revisados el sitio (home, contacto, nosotros) y las fichas de la fuente, 7-oct-2026); redes https://www.instagram.com/globalthinktechnology.

Para:

```
dghione@globalthinktec.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Global Think Technology
```

Texto:

```
Hola Diego, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Global Think ya despliega agentes de IA que atienden y coordinan prestadores para aseguradoras y telcos: con nosotros esos agentes pueden además atender y hacer llamadas, con número incluido.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=global-think

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (299 caracteres):

```
Hola Diego, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Global Think Technology. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Diego, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Global Think ya despliega agentes de IA que atienden y coordinan prestadores para aseguradoras y telcos: con nosotros esos agentes pueden además atender y hacer llamadas, con número incluido.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=global-think

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S33. Mindfactory

- Contacto 236 de `seguimiento.md`
- Rubro: GovTech: ingeniería de software para la modernización de organismos públicos y empresas, Córdoba capital (Argentina)
- Web: https://www.mindfactory.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Vende a gobiernos y empresas de salud y servicios públicos, que atienden y cobran por teléfono; es canal al segmento municipal del plan.
- Gancho: 'Especializados en la modernización de organismos gubernamentales y empresas de alta complejidad… ISO 9001 y 27001'; clientes Ministerio de Finanzas y Catastro de Córdoba, EPEC, Facultad de Ciencias Médicas (UNC) (catálogo CCT). 'Nuestra experiencia: Gobierno, Salud, Servicios Públicos, Turismo' (sitio, 7-oct-2026). Tecnologías declaradas: IA, automatización, machine learning (ficha Next from Argentina). El catálogo dice 51-100 personas; la ficha, 10.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | sebastian.sosa@mindfactory.ar | persona | Sebastián Sosa, CEO | https://catalogo.cordobacluster.com/nuestros-socios (catálogo de socios del Córdoba Technology Cluster, API pública cordobatechnology.space:8443/empresas, bajada el 7-oct-2026) |
|  | martin.mendez@mindfactory.ar | persona | Martín Méndez, CEO (así en el catálogo) | https://catalogo.cordobacluster.com/nuestros-socios (catálogo de socios del Córdoba Technology Cluster, API pública cordobatechnology.space:8443/empresas, bajada el 7-oct-2026) |
|  | info@mindfactory.ar | atención | casilla general (sitio y catálogo) | https://www.mindfactory.ar/ (7-oct-2026) |
|  | rrhh@mindfactory.ar | área | RRHH | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/mindfactory (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: +54 9 351 651-2556 (catálogo CCT, Sebastián Sosa).

LinkedIn: empresa https://www.linkedin.com/company/mindfactoryarg; persona https://www.linkedin.com/in/sebastian-sosa-14947b3a/ (catálogo); https://www.linkedin.com/in/martin-mendez-b5941819/ (ficha).

Otros canales: formulario https://www.mindfactory.ar/ (formulario 'Contáctenos'); WhatsApp — (sin WhatsApp publicado: revisados el sitio (home, contacto, nosotros) y las fichas de la fuente, 7-oct-2026); redes https://www.instagram.com/mindfactory.ar.

Para:

```
sebastian.sosa@mindfactory.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Mindfactory
```

Texto:

```
Hola Sebastián, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Mindfactory moderniza organismos de gobierno y empresas de salud y servicios públicos: un agente que atienda el teléfono del organismo y llame por vencimientos o turnos se integra a esas plataformas por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=mindfactory

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (291 caracteres):

```
Hola Sebastián, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Mindfactory. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Sebastián, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Mindfactory moderniza organismos de gobierno y empresas de salud y servicios públicos: un agente que atienda el teléfono del organismo y llame por vencimientos o turnos se integra a esas plataformas por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=mindfactory

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S34. Program Consultores (PGM)

- Contacto 237 de `seguimiento.md`
- Rubro: Software de gestión para municipios, comunas y cooperativas de servicios públicos; gobierno electrónico, Córdoba capital (Argentina)
- Web: https://www.municipalidad.com
- Tipo: posible aliado (canal)
- Por qué encaja: Es proveedor de software de municipios y cooperativas, dos segmentos del plan (tasas, reclamos, vencimientos por teléfono); canal, no cliente final.
- Gancho: '35 años de experiencia desarrollando tecnologías para el sector público'; plataforma eGov PGM y 'Mi Muni'; integraciones con Cobro Express, Banelco, cajas de jubilaciones, CIDI, ANSES (sitio, 7-oct-2026). 'Desde 1990 a la informatización integral… en Municipios, Comunas, Entes Regionales, Empresas y Cooperativas de Servicios Públicos'; 21-50 personas (catálogo CCT).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | agiraudo@municipalidad.com | persona | Alberto Giraudo, CEO | https://catalogo.cordobacluster.com/nuestros-socios (catálogo de socios del Córdoba Technology Cluster, API pública cordobatechnology.space:8443/empresas, bajada el 7-oct-2026) |
|  | info@municipalidad.com | atención | casilla general (Cloudflare data-cfemail, decodificado) | https://www.municipalidad.com/ (7-oct-2026) |
|  | info@pgmtools.com | atención | casilla general de la ficha | https://catalogo.cordobacluster.com/nuestros-socios (catálogo de socios del Córdoba Technology Cluster, API pública cordobatechnology.space:8443/empresas, bajada el 7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: (0351) 447-4200 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/program-consultores-s-a/; persona —.

Otros canales: formulario https://www.municipalidad.com/ (formulario 'Solicitar información'); WhatsApp — (sin WhatsApp publicado: revisados el sitio (home, contacto, nosotros) y las fichas de la fuente, 7-oct-2026); redes —.

Para:

```
agiraudo@municipalidad.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Program Consultores
```

Texto:

```
Hola Alberto, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

PGM gestiona la recaudación y la atención ciudadana de municipios y cooperativas: un agente que atienda el teléfono del municipio y llame por vencimientos de tasas se integra a esa plataforma, y ustedes lo venden dentro de su suite.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=program-consultores

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (297 caracteres):

```
Hola Alberto, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Program Consultores. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Alberto, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

PGM gestiona la recaudación y la atención ciudadana de municipios y cooperativas: un agente que atienda el teléfono del municipio y llame por vencimientos de tasas se integra a esa plataforma, y ustedes lo venden dentro de su suite.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=program-consultores

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S35. Emser

- Contacto 238 de `seguimiento.md`
- Rubro: Consultora tecnológica: automatización e IA aplicadas a logística, distribución, servicios públicos y ciudades digitales, Córdoba capital (Argentina)
- Web: http://www.emser.net
- Tipo: posible aliado (canal)
- Por qué encaja: Consultora de 100+ personas que ya vende automatización e IA a distribuidoras y servicios públicos, rubros con mucho teléfono (reclamos, cobranza).
- Gancho: 'Consultoría tecnológica especializada en desarrollos innovadores aplicados a logística, distribución, consumo masivo, agricultura, servicios públicos y ciudades digitales'; clientes Gasnea, Aysa, Ecogas, Syngenta, Corteva; fundada en 1993, 101-200 personas (catálogo CCT). El sitio menciona automatización (7 veces), inteligencia artificial (5) y machine learning (7-oct-2026). Su política de calidad, publicada en el sitio, está 'aprobada por Jorge Burkle / Dirección general'.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | Jburkle@emser.net | persona | Jorge Burkle, Dirección General (email en el catálogo; nombre y cargo en la política de calidad del sitio) | https://catalogo.cordobacluster.com/nuestros-socios (catálogo de socios del Córdoba Technology Cluster, API pública cordobatechnology.space:8443/empresas, bajada el 7-oct-2026); http://www.emser.net/ (política de calidad, 7-oct-2026) |
|  | info@emser.net | atención | casilla general | http://www.emser.net/ (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/emser/ (catálogo CCT); persona —.

Otros canales: formulario http://www.emser.net/ (formulario de contacto); WhatsApp — (sin WhatsApp publicado: revisados el sitio (home, contacto, nosotros) y las fichas de la fuente, 7-oct-2026); redes https://www.instagram.com/emser.software/ ; https://twitter.com/Emser_SA (catálogo CCT).

Para:

```
Jburkle@emser.net
```

Asunto:

```
Voz y telefonía para los agentes de IA de Emser
```

Texto:

```
Hola Jorge, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Emser ya automatiza con IA la operación de distribuidoras y servicios públicos como Ecogas o Aysa: las llamadas de reclamos, cobranza y confirmación son el proceso que sigue, y se integran por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=emser

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (281 caracteres):

```
Hola Jorge, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Emser. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Jorge, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Emser ya automatiza con IA la operación de distribuidoras y servicios públicos como Ecogas o Aysa: las llamadas de reclamos, cobranza y confirmación son el proceso que sigue, y se integran por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=emser

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S36. DinoCloud

- Contacto 239 de `seguimiento.md`
- Rubro: AWS Premier Partner: migración, DevOps, datos e IA generativa en AWS, Córdoba capital (Argentina)
- Web: https://dinocloud.co
- Tipo: posible aliado (canal)
- Por qué encaja: Implementa IA generativa para clientes de banca, logística y salud; la voz telefónica con inferencia local es un componente que no tienen en AWS.
- Gancho: 'Servicios de IA/ML, IA Generativa en AWS… Integra modelos avanzados de lenguaje y automatiza procesos'; 'AWS Premier Partner', '10 years leading the cloud journey' (sitio, 7-oct-2026). 201-300 personas, fundada en 2017; oficina Humberto 1° 630, Córdoba (catálogo CCT). Reserva de la tanda 1.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@dinocloud.co | atención | casilla general del sitio | https://dinocloud.co/contact-us/ (7-oct-2026) |
|  | info@dinocloudconsulting.com | atención | casilla general de la ficha | https://catalogo.cordobacluster.com/nuestros-socios (catálogo de socios del Córdoba Technology Cluster, API pública cordobatechnology.space:8443/empresas, bajada el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/dinocloud/ (sitio); https://www.linkedin.com/company/dinocloud-arg/ (catálogo); persona —.

Otros canales: formulario https://dinocloud.co/contact-us/; WhatsApp — (sin WhatsApp publicado: revisados el sitio (home, contacto, nosotros) y las fichas de la fuente, 7-oct-2026); redes https://www.instagram.com/dinocloud_ ; https://twitter.com/dinocloud_.

Para:

```
info@dinocloud.co
```

Asunto:

```
Voz y telefonía para los agentes de IA de DinoCloud
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

DinoCloud ya integra modelos de lenguaje y automatiza procesos para bancos, logística y salud en AWS: un agente que atienda y llame por teléfono, con número incluido, es la pieza de voz que esos proyectos no tienen.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=dinocloud

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (279 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como DinoCloud. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

DinoCloud ya integra modelos de lenguaje y automatiza procesos para bancos, logística y salud en AWS: un agente que atienda y llame por teléfono, con número incluido, es la pieza de voz que esos proyectos no tienen.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=dinocloud

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S37. Vatrox

- Contacto 240 de `seguimiento.md`
- Rubro: Integración de plataformas y datos, DevOps y procesos apoyados por IA aplicada (banca, seguros, retail), Córdoba capital (Argentina)
- Web: https://vatrox.com
- Tipo: posible aliado (canal)
- Por qué encaja: Integrador con proyectos de IA en banca y seguros: puede sumar la voz telefónica como un canal más de esas integraciones.
- Gancho: 'Integramos legacy con arquitectura moderna sin detener el negocio… procesos de negocio apoyados por IA aplicada'; menciona MCP y '+10 años en integración empresarial' (sitio, 7-oct-2026). Fundada en 2014, 0-20 personas; proyectos 'Banca / Seguros (IA)', 'Banca Digital (Open Banking)', 'Consumo Masivo' (catálogo CCT).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | contacto@vatrox.com | atención | casilla general del sitio | https://vatrox.com/contacto (7-oct-2026) |
|  | info@vatrox.com | atención | casilla general de la ficha | https://catalogo.cordobacluster.com/nuestros-socios (catálogo de socios del Córdoba Technology Cluster, API pública cordobatechnology.space:8443/empresas, bajada el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/vatrox/ (catálogo CCT); persona —.

Otros canales: formulario https://vatrox.com/contacto ('Solicitar diagnóstico'); WhatsApp — (sin WhatsApp publicado: revisados el sitio (home, contacto, nosotros) y las fichas de la fuente, 7-oct-2026); redes —.

Para:

```
contacto@vatrox.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Vatrox
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Vatrox ya integra datos y procesos con IA aplicada en banca, seguros y retail: un agente que atienda y llame por teléfono se conecta a esas mismas integraciones por API, sin que ustedes armen la telefonía.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=vatrox

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (276 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Vatrox. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Vatrox ya integra datos y procesos con IA aplicada en banca, seguros y retail: un agente que atienda y llame por teléfono se conecta a esas mismas integraciones por API, sin que ustedes armen la telefonía.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=vatrox

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S38. Olpa Group

- Contacto 241 de `seguimiento.md`
- Rubro: Consultora AI-native: Odoo, automatización con n8n, agentes de IA y marketing para pymes, Córdoba capital (Argentina)
- Web: https://olpagroup.com
- Tipo: posible aliado (canal)
- Por qué encaja: Agencia de automatización con n8n y agentes de IA para pymes: el agente de voz es un nodo más de sus flujos.
- Gancho: 'Consultora AI-native en Córdoba… Marketing + Odoo + IA en 27 PyMEs argentinas'; servicios 'Automatización, Agentes de IA, Asistentes inteligentes a medida, n8n' (sitio, 7-oct-2026). Partner de Odoo con 10 referencias (ficha de Odoo). Oficina en Gregorio Vélez 3472, Córdoba (sitio).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@olpagroup.com | atención | casilla general (sitio y ficha de Odoo) | https://olpagroup.com/contacto (7-oct-2026); https://www.odoo.com/partners/olpa-group-19510487 (ficha de partner oficial de Odoo, vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 9 351 753-2299 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/olpagroup; persona —.

Otros canales: formulario https://olpagroup.com/contacto; WhatsApp +54 9 351 753-2299: https://wa.me/5493517532299 en el sitio (7-oct-2026); redes https://www.instagram.com/olpagroup.

Para:

```
info@olpagroup.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Olpa Group
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Olpa ya arma agentes de IA y flujos en n8n sobre Odoo para 27 pymes: el agente que atiende y llama por teléfono es un nodo más de esos flujos, con número incluido.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=olpa-group

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (280 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Olpa Group. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Olpa ya arma agentes de IA y flujos en n8n sobre Odoo para 27 pymes: el agente que atiende y llama por teléfono es un nodo más de esos flujos, con número incluido.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=olpa-group

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S39. Castelsoft

- Contacto 242 de `seguimiento.md`
- Rubro: Implementación de Odoo con IA ('implementación aumentada'); experiencia desde partners Gold, Córdoba capital (Argentina)
- Web: https://castelsoft.com
- Tipo: posible aliado (canal)
- Por qué encaja: Implementador de Odoo que ya vende IA a sus clientes; el teléfono conectado al ERP es un módulo más.
- Gancho: 'Implementación aumentada para Odoo… Inteligencia Artificial para acelerar. Consultores expertos para decidir bien… Experiencia desde Partners Gold' (sitio, 7-oct-2026). Partner oficial de Odoo, Montevideo 78, Córdoba (ficha de Odoo).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@castelsoft.com | atención | casilla general (sitio y ficha de Odoo) | https://castelsoft.com/ (7-oct-2026); https://www.odoo.com/partners/castelsoft-33875346 (ficha de partner oficial de Odoo, vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 9 11 3877-0855 (sitio y ficha de Odoo).

LinkedIn: empresa — (no publicado en el sitio ni en la ficha); persona —.

Otros canales: formulario https://castelsoft.com/ ('Conversemos sobre tu empresa'); WhatsApp — (sin WhatsApp publicado: revisados el sitio (home, contacto, nosotros) y las fichas de la fuente, 7-oct-2026); redes —.

Para:

```
info@castelsoft.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Castelsoft
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Castelsoft ya implementa Odoo con IA para acelerar: un agente que atienda y llame por teléfono, con número incluido y conectado al ERP, es el módulo que falta en esas implementaciones.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=castelsoft

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (280 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Castelsoft. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Castelsoft ya implementa Odoo con IA para acelerar: un agente que atienda y llame por teléfono, con número incluido y conectado al ERP, es el módulo que falta en esas implementaciones.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=castelsoft

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S40. Dynetis

- Contacto 243 de `seguimiento.md`
- Rubro: Consultoría en Odoo, integraciones (pagos, logística, BI) y datos, Villa Carlos Paz (Córdoba) (Argentina)
- Web: https://www.dynetis.com
- Tipo: posible aliado (canal)
- Por qué encaja: Integrador de Odoo con foco en conectores: la voz telefónica es un conector más para sus clientes.
- Gancho: 'Odoo · Integraciones · Datos… Integraciones APIs & conectores: facturación, medios de pago, logística, BI y más' (sitio, 7-oct-2026). Partner de Odoo con 18 referencias; Leandro N. Alem 655, Villa Carlos Paz (ficha de Odoo). Aviso: el sitio no respondió al rastreo sin 'www.'.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | pablo.molla@dynetis.com | persona | Pablo Molla (cargo no publicado; es el contacto de la ficha de Odoo y figura en el pie del sitio) | https://www.odoo.com/partners/dynetis-6934713 (ficha de partner oficial de Odoo, vista el 7-oct-2026); https://www.dynetis.com/ (7-oct-2026) |
|  | cristian.salas@dynetis.com | persona | Cristian Salas (cargo no publicado) | https://www.dynetis.com/ (7-oct-2026) |
|  | info@dynetis.com | atención | casilla general | https://www.dynetis.com/ (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: +54 9 3576 46-2503 (sitio y ficha de Odoo); +54 9 3515 73-9439 (sitio, Cristian Salas).

LinkedIn: empresa — (no publicado); persona —.

Otros canales: formulario https://www.dynetis.com/ ('Contáctenos'); WhatsApp — (sin WhatsApp publicado: revisados el sitio (home, contacto, nosotros) y las fichas de la fuente, 7-oct-2026); redes —.

Para:

```
pablo.molla@dynetis.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Dynetis
```

Texto:

```
Hola Pablo, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Dynetis conecta Odoo con pagos, logística y BI para sus clientes: un agente que atienda y llame por teléfono es un conector más, con número incluido.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=dynetis

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (283 caracteres):

```
Hola Pablo, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Dynetis. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Pablo, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Dynetis conecta Odoo con pagos, logística y BI para sus clientes: un agente que atienda y llame por teléfono es un conector más, con número incluido.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=dynetis

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S41. Glowix / Neos Tech

- Contacto 244 de `seguimiento.md`
- Rubro: Plataforma comercial B2B y partner de Microsoft Dynamics GP; automatización de procesos comerciales de distribuidoras, Villa María (Córdoba) (Argentina)
- Web: https://www.neos.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Partner de Dynamics con clientes distribuidoras que venden y cobran por teléfono; es canal, aunque no venda IA todavía.
- Gancho: 'Desarrollamos tecnología que integra y automatiza procesos comerciales… Especialistas en distribución'; Dynamics GP aparece 14 veces en el sitio (7-oct-2026). 15 personas, fundada en 2019, CEO Gustavo Gómez Arrufat (ficha Next from Argentina). Reserva de las tandas 1 y 2: poca IA.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | ggomezarrufat@neos.com.ar | persona | Gustavo Gómez Arrufat, CEO | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/glowix (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |
|  | ventas@neos.com.ar | área | ventas | https://www.neos.com.ar/contacto (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/neos-tecnologia-sas (sitio); https://www.linkedin.com/company/glowix/ (ficha); persona https://www.linkedin.com/in/gustavo-g%C3%B3mez-arrufat/ (ficha).

Otros canales: formulario https://www.neos.com.ar/contacto; WhatsApp — (sin WhatsApp publicado: revisados el sitio (home, contacto, nosotros) y las fichas de la fuente, 7-oct-2026); redes https://www.instagram.com/neostecnologia.

Para:

```
ggomezarrufat@neos.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Glowix / Neos Tech
```

Texto:

```
Hola Gustavo, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Neos automatiza los procesos comerciales de distribuidoras sobre Glowix y Dynamics: las llamadas de pedidos, cobranza y confirmación son el siguiente proceso, y se integran por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=glowix-neos

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (296 caracteres):

```
Hola Gustavo, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Glowix / Neos Tech. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Gustavo, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Neos automatiza los procesos comerciales de distribuidoras sobre Glowix y Dynamics: las llamadas de pedidos, cobranza y confirmación son el siguiente proceso, y se integran por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=glowix-neos

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S42. Psiware

- Contacto 245 de `seguimiento.md`
- Rubro: Desarrollo de software con IA, automatización y datos; sede en Rosario con oficinas en EE. UU. y Croacia, Rosario (Santa Fe) (Argentina)
- Web: https://www.psiware.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Software factory con práctica de IA y clientes corporativos; puede integrar la voz telefónica en sus proyectos.
- Gancho: 'Socios tecnológicos de tus proyectos de software'; inteligencia artificial (14 menciones), 'agentes inteligentes', automatización; 'desde 2003'; HQ y Delivery Center en Tucumán 1463, piso 11, Rosario; cliente Nestlé Purina Latam (sitio, 7-oct-2026). Socio del Polo Tecnológico Rosario.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | contact@psiware.com.ar | atención | casilla general (sede Rosario) | https://www.psiware.com.ar/contacto (7-oct-2026) |
|  | north-america@psiware.com.ar | área | oficina de EE. UU. (Todd Levering) | https://www.psiware.com.ar/contacto (7-oct-2026) |
|  | europe@psiware.com.ar | área | oficina de Europa (Darko Vindiš) | https://www.psiware.com.ar/contacto (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 9 341 343-9451 (sitio).

LinkedIn: empresa — (no publicado en el sitio); persona —.

Otros canales: formulario https://www.psiware.com.ar/contacto; WhatsApp — (sin WhatsApp publicado: revisados el sitio (home, contacto, nosotros) y las fichas de la fuente, 7-oct-2026); redes —.

Para:

```
contact@psiware.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Psiware
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Psiware ya construye agentes inteligentes y automatizaciones para clientes como Nestlé Purina: con nuestra API esos agentes también pueden atender y llamar por teléfono, sin que ustedes armen la telefonía.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=psiware

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (277 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Psiware. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Psiware ya construye agentes inteligentes y automatizaciones para clientes como Nestlé Purina: con nuestra API esos agentes también pueden atender y llamar por teléfono, sin que ustedes armen la telefonía.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=psiware

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S43. Idear Tech

- Contacto 246 de `seguimiento.md`
- Rubro: Software para gobiernos y empresas (GovTech, FinTech) con low-code e IA, Rosario (Santa Fe) (Argentina)
- Web: https://ideartechcorp.com
- Tipo: posible aliado (canal)
- Por qué encaja: Vende a gobiernos y financieras, dos segmentos del plan; ya usa IA en sus desarrollos.
- Gancho: 'Soluciones a medida que transforman la gestión de gobiernos y empresas… apoyadas en tecnologías low-code e Inteligencia Artificial'; 28 personas, fundada en 2020 (ficha Next from Argentina). 'Más de 30 clientes, equipos en 3 países, más de 100 proyectos'; Bulevar Oroño 1580, Rosario (sitio, 7-oct-2026). Aviso: el sitio conserva texto de plantilla (TemplateMo, lorem ipsum) en la home. Reserva de la tanda 2.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | negocios@ideartechcorp.com | área | negocios (contacto de la ficha: Héctor Rossetto) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/idear-tech (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |
|  | contacto@ideartechcorp.com | atención | casilla general | https://ideartechcorp.com/ (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Héctor Rossetto (contacto de la ficha, cargo no publicado).

Teléfonos: (54) 341 665-6506 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/idear-tech/; persona https://www.linkedin.com/in/hrossetto/ (ficha).

Otros canales: formulario https://ideartechcorp.com/ (formulario de la home); WhatsApp +54 9 341 665-6506: api.whatsapp.com/send/?phone=+5493416656506 en la home (7-oct-2026); redes https://www.instagram.com/ideartech ; https://x.com/IdearTech.

Para:

```
negocios@ideartechcorp.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Idear Tech
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Idear Tech ya desarrolla con IA para gobiernos y financieras: un agente que atienda el teléfono del organismo y llame por vencimientos o cobranzas se integra a esas soluciones por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=idear-tech

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (280 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Idear Tech. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Idear Tech ya desarrolla con IA para gobiernos y financieras: un agente que atienda el teléfono del organismo y llame por vencimientos o cobranzas se integra a esas soluciones por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=idear-tech

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S44. Inteligencia Analítica

- Contacto 247 de `seguimiento.md`
- Rubro: Consultora de Business Intelligence y Data Analytics, Rosario (Santa Fe) (Argentina)
- Web: https://www.inteligenciaanalitica.com
- Tipo: posible aliado (canal)
- Por qué encaja: Consultora de datos con clientes de varias industrias; la voz telefónica es un canal de captura y salida de datos para esos mismos clientes.
- Gancho: 'Soluciones de inteligencia de negocios… más de 10 años de experiencia… BI & Data Analytics' (sitio, 7-oct-2026). Socio del Polo Tecnológico Rosario, categoría Data Analytics. Aviso: BI, poca IA en el sitio.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | contacto@inteligenciaanalitica.com | atención | casilla general | https://www.inteligenciaanalitica.com/ (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/inteligencia-analitica/; persona —.

Otros canales: formulario https://www.inteligenciaanalitica.com/ (formulario 'Contactanos'); WhatsApp — (sin WhatsApp publicado: revisados el sitio (home, contacto, nosotros) y las fichas de la fuente, 7-oct-2026); redes https://www.instagram.com/inteligencia.analitica.

Para:

```
contacto@inteligenciaanalitica.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Inteligencia Analítica
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Inteligencia Analítica ya ordena los datos de sus clientes en tableros de BI: las llamadas de cobranza, confirmación y atención generan y consumen esos mismos datos, y se integran por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=inteligencia-analitica

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (292 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Inteligencia Analítica. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Inteligencia Analítica ya ordena los datos de sus clientes en tableros de BI: las llamadas de cobranza, confirmación y atención generan y consumen esos mismos datos, y se integran por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=inteligencia-analitica

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S45. Grupo Aicon

- Contacto 248 de `seguimiento.md`
- Rubro: ERP especializado por rubro (sindicatos, obras sociales, mutuales, financieras, mayoristas, droguerías) con IA, Rosario y Armstrong (Santa Fe) (Argentina)
- Web: https://grupoaicon.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Software vertical de mutuales, sindicatos y financieras, segmentos del plan (cobranza de cuotas, atención de afiliados): canal a 200 clientes.
- Gancho: 'ERP especializado por rubro… sindicatos, mutuales, financieras, droguerías… +20 años, +200 clientes, +500 implementaciones, ISO 9001'; menciona inteligencia artificial y Power BI; fundada en 2005 en Rosario, oficinas en Donado 239 (Fisherton) y Armstrong (sitio, 7-oct-2026). Socio del Polo Tecnológico Rosario. Aviso: los testimonios del sitio figuran como '[Pendiente — Cliente Sindicato]'.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | administracion@grupoaicon.com.ar | atención | casilla general ('Escribinos… te respondemos el mismo día') | https://grupoaicon.com.ar/ (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 341 451-0595 / 451-7721 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/grupoaiconsrl; persona —.

Otros canales: formulario https://grupoaicon.com.ar/ ('Pedir una demo'); WhatsApp +54 9 341 690-6680: https://wa.me/5493416906680 en la home (7-oct-2026); redes https://www.instagram.com/grupo_aiconsrl.

Para:

```
administracion@grupoaicon.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Grupo Aicon
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Aicon gestiona afiliados, cuotas y cobranzas de más de 200 mutuales, sindicatos y financieras: un agente de voz conectado a su ERP puede llamar por vencimientos y atender a los afiliados, y ustedes lo venden dentro de su suite.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=grupo-aicon

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (281 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Grupo Aicon. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Aicon gestiona afiliados, cuotas y cobranzas de más de 200 mutuales, sindicatos y financieras: un agente de voz conectado a su ERP puede llamar por vencimientos y atender a los afiliados, y ustedes lo venden dentro de su suite.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=grupo-aicon

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S46. Alchemid

- Contacto 249 de `seguimiento.md`
- Rubro: Partner Silver de Odoo: automatización, e-commerce y desarrollos a medida para distribuidoras y mayoristas, Rafaela (Santa Fe) (Argentina)
- Web: https://www.alchemid.com
- Tipo: posible aliado (canal)
- Por qué encaja: Implementador de Odoo con 50 pymes del interior que venden y cobran por teléfono; el agente se integra al ERP.
- Gancho: 'Odoo, automatización, e-commerce y desarrollos a medida para distribuidoras, mayoristas y empresas en crecimiento. Más de 50 empresas del interior del país ya trabajan con Alchemid'; 'Implementamos con vos, no para vos' (sitio, 7-oct-2026). Partner Silver con 52 referencias; Jorge Newbery 405, Rafaela (ficha de Odoo). El sitio no publica email, solo WhatsApp.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | contacto@alchemid.com | atención | casilla general de la ficha de Odoo (el sitio solo publica WhatsApp) | https://www.odoo.com/partners/alchemid-14900590 (ficha de partner oficial de Odoo, vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 9 3492 21-9294 (ficha de Odoo; mismo número del WhatsApp).

LinkedIn: empresa — (no publicado); persona —.

Otros canales: formulario https://www.alchemid.com/contacto; WhatsApp +54 9 3492 21-9294: https://wa.me/5493492219294 en la home (7-oct-2026); redes https://www.instagram.com/alchemid.servicios.

Para:

```
contacto@alchemid.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Alchemid
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Alchemid ya automatiza la operación de más de 50 distribuidoras y mayoristas sobre Odoo: las llamadas de pedidos, cobranza y confirmación son el siguiente proceso, y se integran al ERP por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=alchemid

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (278 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Alchemid. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Alchemid ya automatiza la operación de más de 50 distribuidoras y mayoristas sobre Odoo: las llamadas de pedidos, cobranza y confirmación son el siguiente proceso, y se integran al ERP por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=alchemid

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S47. M3C Software

- Contacto 250 de `seguimiento.md`
- Rubro: ERP de gestión integral para pymes con programa de partners (#M3Cpartner), Rosario (Santa Fe) (Argentina)
- Web: https://m3csoftware.com
- Tipo: posible aliado (canal)
- Por qué encaja: ERP con programa de partners y clientes pymes de retail y mayoristas; el agente de voz es un módulo revendible.
- Gancho: 'Convertite en #M3Cpartner y aumentá tus ganancias recomendando nuestro sistema de gestión… Tenemos un tipo de partner para cada socio' (sitio, 7-oct-2026). ERP que 'automatiza tareas… integración con e-commerce'; tecnologías declaradas: IA, big data; 10 personas, fundada en 2013, contacto Ariel Pablo Pistarino (ficha Next from Argentina). Reserva de la tanda 2. El sitio no publica emails.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | comercial@m3csoftware.com.ar | área | comercial (contacto de la ficha: Ariel Pablo Pistarino) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/m3c (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Ariel Pablo Pistarino (contacto de la ficha); Santiago Conti (LinkedIn enlazado en la ficha).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/m3c-software/ (ficha); persona https://www.linkedin.com/in/ariel-pistarino-161a9514b/ (ficha).

Otros canales: formulario https://m3csoftware.com/ (formulario de contacto); WhatsApp — (sin WhatsApp publicado: revisados el sitio (home, contacto, nosotros) y las fichas de la fuente, 7-oct-2026); redes —.

Para:

```
comercial@m3csoftware.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de M3C Software
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

M3C ya tiene un programa de partners para revender su ERP: un agente de voz que atienda y llame por pedidos y cobranzas, conectado a M3C Gestión, es un módulo más para esa red.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=m3c

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (282 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como M3C Software. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

M3C ya tiene un programa de partners para revender su ERP: un agente de voz que atienda y llame por pedidos y cobranzas, conectado a M3C Gestión, es un módulo más para esa red.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=m3c

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S48. ERPYCA

- Contacto 251 de `seguimiento.md`
- Rubro: Partner oficial de Odoo con conectores propios (pagos, logística, control horario), Rosario (Santa Fe) (Argentina)
- Web: https://erpyca.com
- Tipo: posible aliado (canal)
- Por qué encaja: Partner de Odoo que vende conectores: el agente de voz es otro conector para sus clientes.
- Gancho: 'Partner oficial de Odoo · Rosario'; conectores propios para pagos con tarjeta, OCA y Hikvision; 'Equipo activo · respondiendo ahora Rosario' (sitio, 7-oct-2026). 'Partner de Odoo joven, técnico y pragmático', 14 referencias (ficha de Odoo). El sitio devuelve 403 al user-agent con 'ClaudeBot' sin prohibirlo en robots.txt: se leyó con user-agent de navegador (dl/ua2_erpyca.com__*.html).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | gaspar@erpyca.com | persona | Gaspar (apellido y cargo no publicados; contacto de la ficha de Odoo) | https://www.odoo.com/partners/erpyca-25919791 (ficha de partner oficial de Odoo, vista el 7-oct-2026) |
|  | hola@erpyca.com | atención | casilla general | https://erpyca.com/ (7-oct-2026, leído con user-agent de navegador) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: +54 341 318-8105 (ficha de Odoo).

LinkedIn: empresa — (no publicado); persona —.

Otros canales: formulario https://erpyca.com/ ('Agendar reunión'); WhatsApp +54 9 341 563-4579: https://wa.me/5493415634579 en el sitio (7-oct-2026); redes —.

Para:

```
gaspar@erpyca.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de ERPYCA
```

Texto:

```
Hola Gaspar, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

ERPYCA ya vende conectores de pagos y logística para Odoo: un agente que atienda y llame por teléfono, conectado al pedido y la cobranza de Odoo, es un conector más, con número incluido.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=erpyca

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (283 caracteres):

```
Hola Gaspar, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como ERPYCA. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Gaspar, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

ERPYCA ya vende conectores de pagos y logística para Odoo: un agente que atienda y llame por teléfono, conectado al pedido y la cobranza de Odoo, es un conector más, con número incluido.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=erpyca

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S49. devFactory

- Contacto 252 de `seguimiento.md`
- Rubro: ERP SaaS con asistente de IA para pymes; programa de partners y referidos, Luján de Cuyo (Mendoza) (Argentina)
- Web: https://devfactory.ar
- Tipo: posible aliado (canal)
- Por qué encaja: ERP con IA y programa de partners para pymes: el agente de voz es un módulo que pueden ofrecer; muy chica (5 personas).
- Gancho: 'Plataforma impulsada por IA para PyMEs… +2000 usuarios, +50 PyMEs en vivo'; página 'Programa de Referidos · devFactory Partners' (sitio, 7-oct-2026). 'Su asistente de IA registra asientos, proyecta el flujo de caja'; 5 personas, fundada en 2025, CEO Matías Armani (ficha Next from Argentina). Reserva de las tandas 1 y 2.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | contact@devfactory.ar | atención | casilla general (sitio y ficha) | https://devfactory.ar/ (7-oct-2026); https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/devfactory (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Matías Armani, CEO (ficha).

Teléfonos: +54 261 525-0354 (sitio, link tel:).

LinkedIn: empresa https://www.linkedin.com/company/devfactory-official/ (ficha); persona https://www.linkedin.com/in/matiasarmani/ (ficha).

Otros canales: formulario https://devfactory.ar/ ('Solicitar propuesta'); WhatsApp +54 261 525-0354: https://wa.me/542615250354 en la home (7-oct-2026); redes https://instagram.com/devFactory_.

Para:

```
contact@devfactory.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de devFactory
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

devFactory ya pone un asistente de IA dentro del ERP de 50 pymes: un agente que atienda y llame por teléfono, con número incluido, es un módulo más de esa plataforma y de su programa de partners.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=devfactory

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (280 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como devFactory. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

devFactory ya pone un asistente de IA dentro del ERP de 50 pymes: un agente que atienda y llame por teléfono, con número incluido, es un módulo más de esa plataforma y de su programa de partners.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=devfactory

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S50. Solutions Hub / AGP & ROD Servicios

- Contacto 253 de `seguimiento.md`
- Rubro: Consultoría SAP (S/4HANA, SuccessFactors, BTP), Mendoza capital (Argentina)
- Web: https://solutionshub.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Partner de SAP (BTP) para empresas de energía, minería y banca; es canal, con integración al ERP.
- Gancho: 'Con SAP Business Technology Platform (BTP) ofrecemos soluciones personalizadas… +8 años de experiencia, +14 proyectos' (sitio, 7-oct-2026). 'Soporte y mantenimiento de SAP en SuccessFactors, S4HANA y BTP'; tecnologías declaradas incluyen IA; 8 personas, fundada en 2024, contacto Rodrigo López (ficha Next from Argentina). Reserva de la tanda 2: SAP, poca IA.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | rodrigo.lopez@solutionshub.com.ar | persona | Rodrigo López (contacto de la ficha, cargo no publicado) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/agp-rod-servicios (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |
|  | info@agprodservicios.com | atención | casilla general | https://solutionshub.com.ar/ (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/agp-rod-servicios/; persona https://www.linkedin.com/in/rodrigolopez/ (ficha).

Otros canales: formulario https://solutionshub.com.ar/ (formulario de contacto); WhatsApp +54 9 261 501-8054: https://wa.me/5492615018054 en la home (7-oct-2026); redes https://www.instagram.com/agp.rod.

Para:

```
rodrigo.lopez@solutionshub.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Solutions Hub / AGP & ROD Servicios
```

Texto:

```
Hola Rodrigo, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Solutions Hub ya integra procesos de sus clientes sobre SAP BTP: un agente que atienda y llame por teléfono se conecta a esos procesos por API, y ustedes lo venden dentro del proyecto SAP.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=solutions-hub

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (291 caracteres):

```
Hola Rodrigo, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Solutions Hub. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Rodrigo, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Solutions Hub ya integra procesos de sus clientes sobre SAP BTP: un agente que atienda y llame por teléfono se conecta a esos procesos por API, y ustedes lo venden dentro del proyecto SAP.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=solutions-hub

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S51. Alpardata

- Contacto 254 de `seguimiento.md`
- Rubro: Partner Silver de Odoo: implementación, módulos propios y automatizaciones, Guaymallén (Mendoza) (Argentina)
- Web: https://www.alpardata.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Implementador de Odoo con 35 pymes mendocinas; el agente de voz se integra al ERP que ya administran.
- Gancho: 'Partner Silver de Odoo… Más de 35 empresas de Mendoza y de todo el país, en ocho sectores… Módulos propios, reportes y automatizaciones' (sitio, 7-oct-2026). 52 referencias; La Barraca Mall, Las Cañas 1833, Guaymallén (ficha de Odoo).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | joaquin@alpardata.com.ar | persona | Joaquín (apellido y cargo no publicados; pie del sitio y contacto de la ficha de Odoo) | https://www.alpardata.com.ar/ (7-oct-2026); https://www.odoo.com/partners/alpardata-10782602 (ficha de partner oficial de Odoo, vista el 7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: +54 9 261 685-3970 (sitio y ficha de Odoo).

LinkedIn: empresa https://www.linkedin.com/company/alpardata/; persona —.

Otros canales: formulario https://www.alpardata.com.ar/ ('Agendá una reunión'); WhatsApp +54 9 261 685-3970: https://wa.me/+5492616853970 en la home (7-oct-2026); redes https://www.instagram.com/alpardata.

Para:

```
joaquin@alpardata.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Alpardata
```

Texto:

```
Hola Joaquín, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Alpardata ya automatiza la operación de 35 empresas sobre Odoo: las llamadas de cobranza, pedidos y confirmación son la siguiente automatización, y se integran al ERP por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=alpardata

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (287 caracteres):

```
Hola Joaquín, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Alpardata. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Joaquín, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Alpardata ya automatiza la operación de 35 empresas sobre Odoo: las llamadas de cobranza, pedidos y confirmación son la siguiente automatización, y se integran al ERP por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=alpardata

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S52. Hexium Software Factory

- Contacto 255 de `seguimiento.md`
- Rubro: Software factory y partner oficial de Odoo; producto LIRA (historia clínica oncológica), Godoy Cruz (Mendoza) (Argentina)
- Web: https://hexium.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Partner de Odoo con producto de salud (clínicas, turnos): canal a dos segmentos del plan.
- Gancho: 'Software Factory & Partner Oficial Odoo en Argentina… LIRA - Historia clínica oncológica'; 'surgió a fines de 2018 en una reunión en un café del centro de Mendoza' (sitio, 7-oct-2026). 24 referencias; Almirante Brown 1096, Godoy Cruz (ficha de Odoo). Aviso: sin IA en el sitio.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@hexium.com.ar | atención | casilla general (sitio y ficha de Odoo) | https://hexium.com.ar/contact-us (7-oct-2026); https://www.odoo.com/partners/hexium-software-17098796 (ficha de partner oficial de Odoo, vista el 7-oct-2026) |
|  | info@hexium.com | atención | casilla general alternativa | https://hexium.com.ar/ (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 9 261 248-6994 (ficha de Odoo; mismo número del WhatsApp).

LinkedIn: empresa — (no publicado); persona —.

Otros canales: formulario https://hexium.com.ar/contact-us; WhatsApp +54 9 261 248-6994: https://wa.me/5492612486994 en el sitio (7-oct-2026); redes —.

Para:

```
info@hexium.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Hexium Software Factory
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Hexium implementa Odoo y vende LIRA a centros oncológicos, donde el teléfono sigue siendo el canal de turnos y seguimiento: un agente de voz integrado a esos sistemas puede atender esas llamadas.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=hexium

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (293 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Hexium Software Factory. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Hexium implementa Odoo y vende LIRA a centros oncológicos, donde el teléfono sigue siendo el canal de turnos y seguimiento: un agente de voz integrado a esos sistemas puede atender esas llamadas.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=hexium

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S53. Corpora

- Contacto 256 de `seguimiento.md`
- Rubro: IA generativa accesible y automatización no-code para pymes, con mentoría, Maipú (Mendoza) (Argentina)
- Web: https://www.somoscorpora.com
- Tipo: posible aliado (canal)
- Por qué encaja: Agencia de automatización con IA para pymes de gastronomía, retail y logística; el agente de voz es una automatización más que puede revender.
- Gancho: 'IA generativa accesible y automatización no-code, acompañando a las empresas con mentoría continua… integra datos en tableros, optimiza procesos internos'; 8 personas, fundada en 2024, fundadora Ariadna Luján Martínez (ficha Next from Argentina). Reserva de las tandas 1 y 2. Aviso: el sitio no tiene contenido legible (2,8 KB, aplicación de página única; 403 al bot).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | gerencia@somoscorpora.com | área | gerencia (contacto de la ficha: Ariadna Luján Martínez) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/corpora (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Ariadna Luján Martínez, fundadora (ficha); Sol Pino (LinkedIn enlazado en la ficha).

Teléfonos: —.

LinkedIn: empresa https://ar.linkedin.com/company/somoscorpora (ficha); persona https://ar.linkedin.com/in/ariadna-lujan-martinez-7a01731ab (ficha).

Otros canales: formulario https://www.somoscorpora.com (sin formulario legible); WhatsApp — (sitio sin contenido legible; la ficha de Cancillería no publica WhatsApp, 7-oct-2026); redes —.

Para:

```
gerencia@somoscorpora.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Corpora
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Corpora ya lleva IA generativa y automatización no-code a pymes de gastronomía, retail y logística: el agente que atiende y llama por teléfono es una automatización más, con número incluido.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=corpora

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (277 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Corpora. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Corpora ya lleva IA generativa y automatización no-code a pymes de gastronomía, retail y logística: el agente que atiende y llama por teléfono es una automatización más, con número incluido.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=corpora

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S54. GoodComex (Full Comex SAS)

- Contacto 257 de `seguimiento.md`
- Rubro: Partner Silver de Odoo: consultoría, implementación y soporte, Mendoza (sitio; la ficha de Odoo da una oficina en Córdoba) (Argentina)
- Web: https://goodcomex.com
- Tipo: posible aliado (canal)
- Por qué encaja: Implementador de Odoo con 35 clientes; el agente de voz se integra al ERP.
- Gancho: 'Implementación de Odoo en Argentina… Full Comex SAS - Mendoza' (sitio, 7-oct-2026). Partner Silver con 35 referencias; dirección Avenida Patria 560, Córdoba y teléfono de Mendoza (ficha de Odoo). El sitio devuelve 403 al user-agent con 'ClaudeBot' sin prohibirlo en robots.txt: se leyó la home con user-agent de navegador (dl/ua2_goodcomex.com__home.html); las subpáginas dieron 503.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | marcelo.vazquez@goodcomex.com | persona | Marcelo Vázquez (contacto de la ficha de Odoo, cargo no publicado) | https://www.odoo.com/partners/goodcomex-sas-1656197 (ficha de partner oficial de Odoo, vista el 7-oct-2026) |
|  | hola@goodcomex.com | atención | casilla general | https://goodcomex.com/ (7-oct-2026, leído con user-agent de navegador) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: +54 9 261 415-8198 (sitio y ficha de Odoo).

LinkedIn: empresa — (no publicado); persona —.

Otros canales: formulario https://goodcomex.com/ ('Agendá una reunión'); WhatsApp — (sin WhatsApp publicado: revisados el sitio (home, contacto, nosotros) y las fichas de la fuente, 7-oct-2026); redes —.

Para:

```
marcelo.vazquez@goodcomex.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de GoodComex
```

Texto:

```
Hola Marcelo, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

GoodComex ya implementa Odoo en 35 empresas que cobran y confirman por teléfono a mano: un agente de voz conectado al ERP puede hacerlo, y ustedes lo venden dentro de la implementación.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=goodcomex

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (287 caracteres):

```
Hola Marcelo, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como GoodComex. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Marcelo, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

GoodComex ya implementa Odoo en 35 empresas que cobran y confirman por teléfono a mano: un agente de voz conectado al ERP puede hacerlo, y ustedes lo venden dentro de la implementación.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=goodcomex

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S55. Solution IT (SIT)

- Contacto 258 de `seguimiento.md`
- Rubro: Desarrollo de software e IA (GPT, LLM) para empresas de Neuquén; socio del cluster Infotech, Neuquén capital (Argentina)
- Web: https://www.solution-it.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Desarrolladora de IA de Neuquén con clientes de energía y comercio; puede sumar la voz telefónica.
- Gancho: 'Solution IT SIT IA desarrollo de software'; inteligencia artificial (30 menciones), GPT (9), LLM (3); dirección Ministro Amancio Alcorta 30, Neuquén; equipo con 'Luis, CO-CEO' y 'Daniel, CO-CEO' (solo nombres de pila) (sitio, 7-oct-2026). Figura en el listado de socios de Infotech Patagonia.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@solution-it.com.ar | atención | casilla general | https://www.solution-it.com.ar/contacto (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Luis y Daniel, co-CEOs (solo nombre de pila en el sitio).

Teléfonos: +54 9 2994 13-2208 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/solutionit; persona —.

Otros canales: formulario https://www.solution-it.com.ar/contacto; WhatsApp — (sin WhatsApp publicado: revisados el sitio (home, contacto, nosotros) y las fichas de la fuente, 7-oct-2026); redes https://www.instagram.com/solutionit_nqn.

Para:

```
info@solution-it.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Solution IT
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

SIT ya desarrolla con GPT y LLM para empresas neuquinas: con nuestra API esos desarrollos también pueden atender y llamar por teléfono, con número incluido, sin armar la telefonía.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=solution-it

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (281 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Solution IT. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

SIT ya desarrolla con GPT y LLM para empresas neuquinas: con nuestra API esos desarrollos también pueden atender y llamar por teléfono, con número incluido, sin armar la telefonía.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=solution-it

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S56. PuntoGap

- Contacto 259 de `seguimiento.md`
- Rubro: Software a medida y consultoría de IA para Oil & Gas y retail; socio fundador de Infotech, Neuquén capital (Argentina)
- Web: https://www.puntogap.com
- Tipo: posible aliado (canal)
- Por qué encaja: Consultora de IA con clientes de energía y retail en Neuquén, provincia sin contactos hasta ahora.
- Gancho: 'Consultoría AI… Prueba nuestra IA… Asesoramiento, consultoría y desarrollos de soluciones basadas en IA' para 'Oil & Gas y Retail'; 'socios fundadores del Clúster Infotech Patagonia, Proveedor Neuquino Certificado'; desde 2005; Sargento Cabral 963, Neuquén (sitio, 7-oct-2026).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@puntogap.com | atención | casilla general | https://www.puntogap.com/ (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 9 299 621-9528 (sitio).

LinkedIn: empresa — (no publicado en el sitio); persona —.

Otros canales: formulario https://www.puntogap.com/ (formulario de contacto); WhatsApp — (sin WhatsApp publicado: revisados el sitio (home, contacto, nosotros) y las fichas de la fuente, 7-oct-2026); redes —.

Para:

```
info@puntogap.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de PuntoGap
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

PuntoGap ya asesora y desarrolla soluciones de IA para empresas de Oil & Gas y retail: el agente que atiende y llama por teléfono es una solución más para esos mismos clientes, con número incluido.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=puntogap

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (278 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como PuntoGap. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

PuntoGap ya asesora y desarrolla soluciones de IA para empresas de Oil & Gas y retail: el agente que atiende y llama por teléfono es una solución más para esos mismos clientes, con número incluido.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=puntogap

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S57. Pragmática Consultores

- Contacto 260 de `seguimiento.md`
- Rubro: Partner de SAP Business One para Oil & Gas y minería, Neuquén capital (Argentina)
- Web: https://www.pragmaticaconsultores.com
- Tipo: posible aliado (canal)
- Por qué encaja: Partner de SAP Business One con 40 clientes industriales; es canal con integración al ERP.
- Gancho: 'SAP Business One para Oil & Gas y Minería… 40+ clientes SAP Business One, 9 provincias… desde 2001 en Neuquén'; equipo publicado con cargos y LinkedIn: Cecilia Casanova (Socia Gerente), Benjamín Moll (Gerente Unidad de Negocio Oil & Gas), Luciano Busso (Gerente Coordinación Operativa); oficina central Ing. Silvio Tosello 1531 (sitio, 7-oct-2026). Menciona inteligencia artificial dos veces. Socio de Infotech Patagonia.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@pragmaticaconsultores.com | atención | casilla general | https://www.pragmaticaconsultores.com/contacto (7-oct-2026) |
|  | asesoramiento_sap@pragmaticaconsultores.com | área | comercial | https://www.pragmaticaconsultores.com/contacto (7-oct-2026) |
|  | administracion@pragmaticaconsultores.com | área | administración | https://www.pragmaticaconsultores.com/contacto (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Cecilia Casanova, Socia Gerente; Benjamín Moll, Gerente UN Oil & Gas; Luciano Busso, Gerente Coordinación Operativa (sitio, /nosotros, con LinkedIn enlazado).

Teléfonos: +54 299 546-1483 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/pragmatica-consultores/; persona https://www.linkedin.com/in/benjamin-moll-796a6917/ (sitio, /nosotros).

Otros canales: formulario https://www.pragmaticaconsultores.com/contacto; WhatsApp +54 299 546-1483: https://wa.me/542995461483 en el sitio (7-oct-2026); redes —.

Para:

```
info@pragmaticaconsultores.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Pragmática Consultores
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Pragmática ya integra la gestión de 40 empresas sobre SAP Business One: un agente que atienda y llame por teléfono se conecta a ese ERP por API, y ustedes lo venden dentro de la implementación.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=pragmatica

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (292 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Pragmática Consultores. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Pragmática ya integra la gestión de 40 empresas sobre SAP Business One: un agente que atienda y llame por teléfono se conecta a ese ERP por API, y ustedes lo venden dentro de la implementación.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=pragmatica

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S58. DITyC

- Contacto 261 de `seguimiento.md`
- Rubro: Consultora de tecnología: software a medida y partner de Odoo y Finnegans, Neuquén capital (Argentina)
- Web: https://www.dityc.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Partner de Odoo y Finnegans en Neuquén; el agente de voz se integra a los ERP que implementa.
- Gancho: 'Consultora de desarrollos informáticos con más de 15 años de experiencia… Plataforma Odoo, plataforma Finnegans'; 'Habla con un asesor' por WhatsApp (sitio, 7-oct-2026). Partner de Odoo con 14 referencias; Dr. Luis Federico Leloir 261, Neuquén (ficha de Odoo). Socio de Infotech Patagonia.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@dityc.com.ar | atención | casilla general (sitio y ficha de Odoo) | https://www.dityc.com.ar/contact (7-oct-2026); https://www.odoo.com/partners/dityc-srl-14057248 (ficha de partner oficial de Odoo, vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 9 299 633-2007 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/DITyC; persona —.

Otros canales: formulario https://www.dityc.com.ar/contact; WhatsApp +54 9 299 633-2007: api.whatsapp.com/send?phone=5492996332007 en la home (7-oct-2026); redes https://www.instagram.com/DITyCsoftware ; https://www.x.com/DITyC.

Para:

```
info@dityc.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de DITyC
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

DITyC ya implementa Odoo y Finnegans en empresas neuquinas que cobran y confirman por teléfono a mano: un agente de voz conectado al ERP puede hacerlo, y ustedes lo venden dentro de la implementación.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=dityc

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (275 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como DITyC. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

DITyC ya implementa Odoo y Finnegans en empresas neuquinas que cobran y confirman por teléfono a mano: un agente de voz conectado al ERP puede hacerlo, y ustedes lo venden dentro de la implementación.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=dityc

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S59. Patagonian

- Contacto 262 de `seguimiento.md`
- Rubro: Software factory con práctica de IA agéntica; sede en General Roca y oficinas en Neuquén, Mendoza, Colombia y Austin, General Roca (Río Negro) (Argentina)
- Web: https://patagonian.com
- Tipo: posible aliado (canal)
- Por qué encaja: Software factory grande del Alto Valle que ya vende agentes de IA; puede integrar la voz telefónica en sus proyectos.
- Gancho: 'Headquarters: Isidro Lobo 472, General Roca, Río Negro'; línea de tiempo 2013 fundación, 2016 oficina Neuquén, 2021 Mendoza, 2024 Austin; directorio: Pedro Mones (CEO), Rodrigo Falcó (CTO), Eugenio Díaz Lis (CBO); notas 'IA agéntica en oil & gas' y 'Agente IA Monitoreo activo' (1-oct-2026) (sitio, 7-oct-2026). Clutch la lista entre las empresas de IA de Argentina con sede en General Roca. El sitio devuelve 403 al user-agent con 'ClaudeBot' sin prohibirlo en robots.txt: se leyó con user-agent de navegador (dl/ua2_patagonian.com__*.html).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@patagonian.com | atención | casilla general | https://patagonian.com/contact (7-oct-2026, leído con user-agent de navegador) |
|  | jobs@patagonian.com | área | empleos (RRHH) | https://patagonian.com/contact (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Pedro Mones, CEO; Rodrigo Falcó, CTO; Eugenio Díaz Lis, CBO (sitio, /about).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/patagonian/; persona https://www.linkedin.com/in/pedromonescazon/ (CEO, enlazado en /about); https://www.linkedin.com/in/rodrigofalco/ (CTO).

Otros canales: formulario https://patagonian.com/contact; WhatsApp — (sin WhatsApp publicado: revisados el sitio (home, contacto, nosotros) y las fichas de la fuente, 7-oct-2026); redes https://www.instagram.com/patagoniantech.

Para:

```
info@patagonian.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Patagonian
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Patagonian ya construye agentes de IA para oil & gas y otras industrias: con nuestra API esos agentes también pueden atender y hacer llamadas, con número incluido, sin que ustedes armen la telefonía.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=patagonian

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (280 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Patagonian. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Patagonian ya construye agentes de IA para oil & gas y otras industrias: con nuestra API esos agentes también pueden atender y hacer llamadas, con número incluido, sin que ustedes armen la telefonía.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=patagonian

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S60. Waiki Consultores en Sistemas

- Contacto 263 de `seguimiento.md`
- Rubro: Implementación de Odoo con módulos propios (sueldos argentinos, tableros, suscripciones), Cipolletti (Río Negro) (Argentina)
- Web: https://waiki.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Implementador de Odoo con 70 empresas del Alto Valle; el agente de voz se integra al ERP que ya administran.
- Gancho: 'Odoo, y todo lo que Odoo no trae de fábrica… +70 empresas trabajando con nosotros, +30 soluciones'; automatización y tableros de BI (sitio, 7-oct-2026). Partner de Odoo con 8 referencias; 25 de Mayo 71, Cipolletti (ficha de Odoo).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@waiki.com.ar | atención | casilla general (sitio y ficha de Odoo) | https://waiki.com.ar/ (7-oct-2026); https://www.odoo.com/partners/waiki-consultores-en-sistemas-13247044 (ficha de partner oficial de Odoo, vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 9 299 502-1110 (sitio).

LinkedIn: empresa — (no publicado); persona —.

Otros canales: formulario https://waiki.com.ar/ ('Contáctanos'); WhatsApp — (sin WhatsApp publicado: revisados el sitio (home, contacto, nosotros) y las fichas de la fuente, 7-oct-2026); redes —.

Para:

```
info@waiki.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Waiki Consultores en Sistemas
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Waiki ya extiende Odoo con módulos propios para 70 empresas: un agente que atienda y llame por teléfono, conectado a ventas y cobranzas de Odoo, es un módulo más, con número incluido.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=waiki

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (299 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Waiki Consultores en Sistemas. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Waiki ya extiende Odoo con módulos propios para 70 empresas: un agente que atienda y llame por teléfono, conectado a ventas y cobranzas de Odoo, es un módulo más, con número incluido.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=waiki

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S61. Ingenio Solutions

- Contacto 264 de `seguimiento.md`
- Rubro: Partner Silver de Odoo para fábricas de alimentos, distribuidoras y minería, Chajarí (Entre Ríos) (Argentina)
- Web: https://ingeniosolutions.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Partner de Odoo con clientes industriales y concesionarias en Entre Ríos, provincia con un solo contacto hasta ahora.
- Gancho: 'Implementación de Odoo ERP en Argentina… Especializaciones: fábricas de alimentos, distribuidoras, minería'; testimonios de Meta S.A., Tres Marías y Omar Vaccari Automotores; Yrigoyen 3280, Chajarí (sitio, 7-oct-2026). Partner Silver con 25 referencias y 3 expertos certificados (ficha de Odoo).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | contacto@ingeniosolutions.com.ar | atención | casilla general (Cloudflare data-cfemail en el sitio, decodificado; también en la ficha de Odoo) | https://ingeniosolutions.com.ar/ (7-oct-2026); https://www.odoo.com/partners/ingenio-solutions-13761187 (ficha de partner oficial de Odoo, vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 9 3456 50-8201 (ficha de Odoo).

LinkedIn: empresa https://www.linkedin.com/company/ingeniosolutions1; persona —.

Otros canales: formulario https://ingeniosolutions.com.ar/ (formulario 'Contactanos'); WhatsApp +54 9 11 4038-1050: https://wa.me/5491140381050 en el sitio (7-oct-2026); redes https://www.instagram.com/ingenio.solutions.

Para:

```
contacto@ingeniosolutions.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Ingenio Solutions
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Ingenio ya implementa Odoo en distribuidoras y concesionarias que confirman pedidos y cobran por teléfono: un agente de voz conectado al ERP puede hacerlo, y ustedes lo venden dentro de la implementación.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=ingenio-solutions

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (287 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Ingenio Solutions. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Ingenio ya implementa Odoo en distribuidoras y concesionarias que confirman pedidos y cobran por teléfono: un agente de voz conectado al ERP puede hacerlo, y ustedes lo venden dentro de la implementación.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=ingenio-solutions

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S62. Quay

- Contacto 265 de `seguimiento.md`
- Rubro: Transformación digital: automatización de procesos y de atención a clientes; partner de Odoo, Concordia (Entre Ríos) (Argentina)
- Web: https://quay.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Automatiza atención a clientes para empresas del litoral; el agente de voz es la automatización que falta.
- Gancho: 'Aportamos soluciones que permiten optimizar y automatizar los procesos de negocio, la toma de decisiones y los servicios de atención a clientes' (sitio, 7-oct-2026). Partner de Odoo con 12 referencias; Gendarmería Nacional 1633, Concordia (ficha de Odoo). Aviso: el sitio es una plantilla con poco contenido propio; otros emails que aparecen son de aliados (W5 Solutions, Ban Training, Ilinesa).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@quay.com.ar | atención | casilla general (sitio y ficha de Odoo) | https://quay.com.ar/contacto (7-oct-2026); https://www.odoo.com/partners/quay-12468590 (ficha de partner oficial de Odoo, vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 11 2059-2165 (sitio y ficha de Odoo).

LinkedIn: empresa — (no publicado); persona —.

Otros canales: formulario https://quay.com.ar/contacto; WhatsApp — (sin WhatsApp publicado: revisados el sitio (home, contacto, nosotros) y las fichas de la fuente, 7-oct-2026); redes —.

Para:

```
info@quay.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Quay
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Quay ya automatiza procesos y servicios de atención a clientes para empresas del litoral: el teléfono, con un agente que atiende y llama con número incluido, es el canal que falta en esa automatización.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=quay

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (274 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Quay. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Quay ya automatiza procesos y servicios de atención a clientes para empresas del litoral: el teléfono, con un agente que atiende y llama con número incluido, es el canal que falta en esa automatización.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=quay

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S63. Tecopens Consulting

- Contacto 266 de `seguimiento.md`
- Rubro: Consultoría de transformación digital para pymes del NOA: ERP (partner de Odoo), finanzas, procesos y marketing, San Miguel de Tucumán (Argentina)
- Web: https://www.tecopensconsulting.com
- Tipo: posible aliado (canal)
- Por qué encaja: Consultora y partner de Odoo en Tucumán, provincia con un solo contacto hasta ahora; canal a pymes del NOA.
- Gancho: 'Consultoría estratégica para optimizar tu negocio. Acompañamos a PyMEs del NOA'; 'Tecnología del Pensamiento: soluciones que no solo automatizan procesos, sino que piensan junto'; co-fundadores Santiago Andrés Vega Pedicone y Leandro Ariel Salinas Clemente (sitio, /sobre-nosotros, 7-oct-2026). Partner de Odoo con 8 referencias; Lamadrid 257, Tucumán (ficha de Odoo).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | equipo@tecopensconsulting.com | atención | casilla general (sitio y ficha de Odoo) | https://www.tecopensconsulting.com/ (7-oct-2026); https://www.odoo.com/partners/tecopens-consulting-25016482 (ficha de partner oficial de Odoo, vista el 7-oct-2026) |
|  | tecopens@outlook.com | atención | casilla alternativa (página 'sobre nosotros') | https://www.tecopensconsulting.com/sobre-nosotros (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Santiago Andrés Vega Pedicone y Leandro Ariel Salinas Clemente, co-fundadores; Joaquín Tomás Pérez Ale (LinkedIn enlazados en el sitio).

Teléfonos: +54 9 381 680-2681 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/tecopens-consulting; persona https://www.linkedin.com/in/santiago-andr%C3%A9s-vega-pedicone/ ; https://www.linkedin.com/in/leandro-ariel-salinas-clemente-aa9b8b115/ (sitio).

Otros canales: formulario https://www.tecopensconsulting.com/ (formulario 'Contáctanos'); WhatsApp — (sin WhatsApp publicado: revisados el sitio (home, contacto, nosotros) y las fichas de la fuente, 7-oct-2026); redes —.

Para:

```
equipo@tecopensconsulting.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Tecopens Consulting
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Tecopens ya ordena procesos y ERP de pymes del NOA: las llamadas de cobranza, pedidos y confirmación son el proceso que sigue, y se integran a Odoo por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=tecopens

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (289 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Tecopens Consulting. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Tecopens ya ordena procesos y ERP de pymes del NOA: las llamadas de cobranza, pedidos y confirmación son el proceso que sigue, y se integran a Odoo por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=tecopens

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S64. Grupo Orange

- Contacto 267 de `seguimiento.md`
- Rubro: Soluciones tecnológicas integrales en Salta y el norte: infraestructura IT, seguridad electrónica y partner de Odoo, Salta capital (Argentina)
- Web: https://grupoorange.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Único integrador con Odoo encontrado en Salta; canal a empresas del NOA, aunque no venda IA todavía.
- Gancho: 'Más de 15 años de experiencia brindando soluciones tecnológicas integrales en Salta y el norte de Argentina… Partner Odoo'; Martín Cornejo 427, Salta (sitio, 7-oct-2026). Partner de Odoo con 15 referencias (ficha). Aviso: sin IA en el sitio. El sitio devuelve 403 al user-agent con 'ClaudeBot' sin prohibirlo en robots.txt: se leyó con user-agent de navegador (dl/ua2_grupoorange.com.ar__*.html).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@grupoorange.com.ar | atención | casilla general (sitio) | https://grupoorange.com.ar/ (7-oct-2026, leído con user-agent de navegador) |
|  | info@grupoorange.ar | atención | casilla alternativa (sitio) | https://grupoorange.com.ar/ (7-oct-2026) |
|  | mtg@grupoorange.com.ar | área | contacto de la ficha de Odoo (sin nombre) | https://www.odoo.com/partners/grupo-orange-srl-20399975 (ficha de partner oficial de Odoo, vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 9 3875 11-6943 y +54 387 464-9626 (sitio).

LinkedIn: empresa — (no publicado); persona —.

Otros canales: formulario https://grupoorange.com.ar/ ('Contáctenos'); WhatsApp +54 9 387 464-0626: https://wa.me/5493874640626 en el sitio (7-oct-2026); redes —.

Para:

```
info@grupoorange.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Grupo Orange
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Grupo Orange ya integra la tecnología de empresas de Salta y el norte, incluido Odoo: un agente que atienda y llame por teléfono, con número incluido, es un servicio más para esos mismos clientes.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=grupo-orange

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (282 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Grupo Orange. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Grupo Orange ya integra la tecnología de empresas de Salta y el norte, incluido Odoo: un agente que atienda y llame por teléfono, con número incluido, es un servicio más para esos mismos clientes.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=grupo-orange

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S65. Grupo Mill

- Contacto 268 de `seguimiento.md`
- Rubro: Consultora de profesionalización de pymes con servicios de inteligencia artificial, datos y agro, Santa Rosa (La Pampa) (Argentina)
- Web: https://grupomill.com
- Tipo: posible aliado (canal)
- Por qué encaja: Consultora que ya vende IA a pymes de La Pampa, provincia sin contactos; canal a pymes agro y comerciales.
- Gancho: Menú de servicios 'Inteligencia Artificial, Consultoría, Agro, Marketing'; 'Profesionalizamos pymes para mejorar rendimiento y trascender… Reemplazamos los mandos medios'; equipo: Franco A. Frontoni (CEO, fundador), Joaquín Sánchez (CMO, fundador), Augusto A. Bueno (COO) (sitio, 7-oct-2026). 'IA para procesos estratégicos, automatización de procesos'; 15 personas, fundada en 2018 (ficha Next from Argentina). Reserva de la tanda 2.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | comunicacion@grupomill.com | área | comunicación (contacto de la ficha: Franco A. Frontoni) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/grupo-mill (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |
|  | info@grupomill.com | atención | casilla general | https://grupomill.com/contacto (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Franco A. Frontoni, CEO y fundador; Joaquín Sánchez, CMO; Augusto A. Bueno, COO (sitio, /nosotros).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/grupomill/; persona https://www.linkedin.com/in/francofrontoni/ (ficha).

Otros canales: formulario https://grupomill.com/contacto; WhatsApp +54 9 2954 33-0420: api.whatsapp.com/send?phone=5492954330420 en el sitio (7-oct-2026); redes https://instagram.com/grupomillsr.

Para:

```
comunicacion@grupomill.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Grupo Mill
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Grupo Mill ya lleva inteligencia artificial y automatización a pymes pampeanas: el agente que atiende y llama por teléfono, con número incluido, es una automatización más para esos mismos clientes.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales4&utm_content=grupo-mill

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (280 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Grupo Mill. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Grupo Mill ya lleva inteligencia artificial y automatización a pymes pampeanas: el agente que atiende y llama por teléfono, con número incluido, es una automatización más para esos mismos clientes.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=grupo-mill

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```
