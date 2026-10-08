# Software e IA, partners, tanda 2 (7-oct-2026): consultoras e integradores de toda Argentina, 65 posibles aliados

**S1 a S40 enviados por email el 8-oct-2026; S41 a S65 en borrador. LinkedIn pendiente.** Segunda tanda de canales de software e IA: empresas de software, consultoras tecnológicas e integradores
que ya implementan IA para sus clientes (agentes conversacionales, automatización, datos e IA, ERP/CRM con IA, GovTech, software
vertical con IA), todas de Argentina: CABA, GBA y provincia de Buenos Aires (33: CABA 18, GBA (San Isidro) 1, La Plata 5, Mar del Plata 3, Bahía Blanca 2, Buenos Aires sin dirección publicada 4) e interior (32: Córdoba 11, Santa Fe 9, Mendoza 4, Salta 2, Chaco 2, Corrientes 2, Tucumán 1, Entre Ríos 1).
Propuesta, la misma de la tanda 1: **solución integral con telefonía incluida y agentes de voz con IA** para que la revendan o la
integren: ellos ponen el cliente y la integración; nosotros, la voz y la telefonía (número, SIP, STT/LLM/TTS propio, WhatsApp, API
`/api/v1`, panel multi-cliente). Contactos 139 a 203 de [`../seguimiento.md`](../seguimiento.md). Ficha completa, con
todos los emails, fuentes y links por canal, en [`2026-10-07-software-ia-partners-2.csv`](2026-10-07-software-ia-partners-2.csv). Formato:
[`README.md`](README.md). Notas, fuentes recorridas, reservas y descartes: `scratch/prospectos/software-ia-2/notas_bsas.md` y
`notas_interior.md`. Textos generados por `scratch/prospectos/software-ia-2/tools/gen2.py` con las plantillas de la tanda 1.

- **Emails:** todos publicados y vistos en su fuente: fichas *Next from Argentina* de Cancillería, catálogo de socios del Córdoba
  Technology Cluster (API pública del catálogo), fichas de socio del Polo Tecnológico Rosario, Polo IT Chaco, Polo IT La Plata,
  ATICMA (Mar del Plata), Polo Tecnológico Bahía Blanca, Clúster Tecnológico Salta y CESSI, y los sitios (`curl`; Cloudflare
  `data-cfemail` decodificado). Ninguno deducido por patrón. Todos los dominios de los ★ tienen MX (7-oct-2026). 19 de 65 tienen
  email de una persona; 46 van a una casilla de área (10) o de atención (36), marcada como genérica en el `.csv`. En las fichas
  de Cancillería y de los clusters el email de contacto a veces no dice el cargo: se anota como "persona (cargo no publicado)".
- **Saludo:** nombre y tuteo solo si el ★ es la casilla de esa persona; si no, "Hola, ¿cómo están?".
- **Lo que el texto promete y existe:** teléfono entrante y saliente con número incluido, WhatsApp (texto y llamadas, hoy con el
  número de Atentina; el número propio del cliente, Embedded Signup, está implementado y sin desplegar: no prometerlo en la charla),
  API `/api/v1`, panel multi-cliente, voces argentinas, inferencia propia. No promete marca blanca ni campañas de voz por lista.
- **Precio:** el mail dice que el minuto queda "muy por debajo" de armarlo con Twilio, ElevenLabs y OpenAI, sin cifra. Respaldo para la
  charla (plan, sección 3): todo incluido USD 0,08-0,15 por minuto contra 0,28-0,35 de los agentes de voz locales sobre Vapi + Twilio;
  telefonía saliente ~USD 0,016 por minuto contra 0,35 de Twilio. Mayorista para canales: USD 0,10 por minuto o 20-30 % recurrente.
- **Ganchos para revisar antes de enviar:** salen de cada sitio o ficha (campo "Gancho"), con la fuente.
- Link con UTM `utm_campaign=canales3&utm_content=<empresa>`; registro en "Links con UTM" de `seguimiento.md`.
- Dominio nuevo: 3 o 4 por hora, tandas de ~10 (65 mails son dos o tres días hábiles). Seguimiento: una línea en el mismo hilo ~4 días
  hábiles después de cada envío (el 12-oct es feriado).
- **LinkedIn:** cada empresa trae una nota corta (≤ 300 caracteres, para invitación) y un mensaje largo, por si el usuario prefiere ese
  canal con el CEO; si lo usa, va a la tabla "LinkedIn" de `seguimiento.md` con `utm_source=linkedin`.
- **WhatsApp (buscado el 7-oct-2026):** 29 de 65 publican un número (en "Otros canales" de cada empresa, con fuente); en las otras
  36 no hay WhatsApp en el sitio ni en las fichas (Instagram, Facebook, LinkedIn y Google Business no se pudieron revisar: piden
  sesión). Formato +54 9 ..., salvo donde la empresa lo publica sin el 9. Canal pendiente: no hay mensaje redactado ni se envió nada.

## Para revisar antes de enviar

Avisos de los dos lotes (detalle en `notas_bsas.md` y `notas_interior.md`):

- **iSource y Yugoo (Corrientes):** el sitio devolvió 403 al rastreador (user-agent ClaudeBot, sin `robots.txt` que lo prohíba); los
  datos salen de una lectura con user-agent de navegador y de la ficha del Polo IT Corrientes.
- **Syloper (Rosario):** el sitio bloquea rastreadores; los datos salen de la ficha *Next from Argentina* de Cancillería.
- **Snoop Consulting:** el sitio responde 403 a `curl`; se verificó con WebFetch.
- **Datawise:** sede dudosa, Rosario (ficha del Polo Tecnológico Rosario, Lamadrid 470) o CABA; va en el lote del interior con aviso.
- **Human Tech 4.0:** ★ `pablo.crembil@humantech40.com.ar`; `humantech40.com` no tiene MX ni A, y la ficha del Polo muestra el email
  ofuscado seguido de ". ar". Si rebota, queda la casilla general.
- **Encaje parcial:** Blackfish (Salta) y Nonlinear (Santa Fe), poca IA en el sitio; Efficast (Rosario) es producto industrial, no
  integrador; Asofix (Córdoba) con ★ en una casilla de Grupo Tagle (`grupotagle.com.ar`), el grupo dueño.
- **MINDO (Mar del Plata) y Aoki Tech (Mar del Plata):** venden agentes de IA de texto para pymes y e-commerce; entran como partners
  (como Aionixs en la tanda 1), marcando que no cubren voz. Posible superposición si en algún momento suman voz.
- **Ciudad tomada de directorios externos**, no del sitio: 7Puentes, QActions, Innen y 404 (Clutch y The Manifest), Grupo Kelsoft
  (ficha de ATICMA), Mooving (sociedad inscripta en CABA, indicadores.ar), Eryx (CB Insights), Quilsoft (erpresearch, directorio de
  partners de Odoo).
- **Contactos de fichas de Cancillería sin cargo publicado:** varios ★ de persona salen de la ficha *Next from Argentina* con nombre
  pero sin cargo (campo "Quién" de cada tabla); se saluda por el nombre igual, porque la casilla es de esa persona.

| # | Contacto | Empresa | País, lugar | Web | Email ★ | Tipo | Quién | utm_content |
|---|---|---|---|---|---|---|---|---|
| S1 | 139 | Biwares | Argentina, CABA (Av. del Libertador 1000, piso 13); oficinas en São Paulo, Miami, México, Madrid, Santiago y Bogotá | https://www.biwares.com | drivero@biwares.com | persona | Diego Rivero, New Business Director | biwares |
| S2 | 140 | Duotach | Argentina, CABA (teléfono 11) | https://duotach.com | contact@duotach.com | atención | casilla general | duotach |
| S3 | 141 | Quilsoft | Argentina, CABA (directorio de partners de Odoo vía erpresearch; teléfono 11) | https://www.quilsoft.com | info@quilsoft.com | atención | casilla general | quilsoft |
| S4 | 142 | BamAI | Argentina, CABA | https://bamai.ar | contacto@bamai.ar | atención | casilla general | bamai |
| S5 | 143 | AIViento | Argentina, CABA (Rafaela 3994); oficinas en Miami y Bogotá | https://www.aiviento.com | contacto@aiviento.com | atención | casilla general | aiviento |
| S6 | 144 | Bombieri | Argentina, CABA (25 de Mayo 471) | https://www.bombieri.com.ar | ventas@bombieri.com.ar | área | ventas | bombieri |
| S7 | 145 | booleAr S.A. | Argentina, CABA (Esmeralda 1061) | https://www.boolear.com | info@boolear.com | atención | casilla general | boolear |
| S8 | 146 | Grupo Esfera | Argentina, CABA | https://www.grupoesfera.com.ar | comercial@grupoesfera.com.ar | área | comercial | grupoesfera |
| S9 | 147 | Eryx | Argentina, CABA (Bonpland 1953, según CB Insights) | https://eryx.co | info@eryx.co | atención | casilla general | eryx |
| S10 | 148 | 7Puentes | Argentina, Buenos Aires (sitio) | https://7puentes.com | info@7puentes.com | atención | casilla general | 7puentes |
| S11 | 149 | Accion Point | Argentina, CABA; oficinas en Colombia y EE. UU. | https://accionpoint.com | marketing@accionpoint.com | área | marketing | accionpoint |
| S12 | 150 | Medve | Argentina, CABA (Av. Caseros 3350, 5º B) | https://www.medve.com.ar | info@medve.com.ar | atención | casilla general | medve |
| S13 | 151 | Unitech | Argentina, CABA | https://www.unitech.com.ar | comercial@unitech-corp.com | área | comercial | unitech |
| S14 | 152 | Xelere | Argentina, CABA (Av. Caseros 3392, piso 8, Distrito Tecnológico); oficina en Santiago de Chile | https://www.xelere.com | info@xelere.com | atención | casilla general | xelere |
| S15 | 153 | QActions | Argentina, Buenos Aires (sitio); oficina en Miami | https://qactions.com | info@qactions.com | atención | casilla general | qactions |
| S16 | 154 | Mooving (Mooving Tech S.A.U.) | Argentina, CABA (sociedad inscripta en CABA, indicadores.ar) | https://mooving.ai | hola@moovingtech.com | atención | casilla general | mooving |
| S17 | 155 | OneInfo Consulting | Argentina, CABA (Ricardo Rojas 401, piso 11); oficinas en Chile, España y Paraguay | https://www.oneinfoconsulting.com | info@oneinfoconsulting.com | atención | casilla general | oneinfo |
| S18 | 156 | Kopernicus | Argentina, San Isidro (Buenos Aires) | https://www.kopernicus.com.ar | ramos.gaston@kopernicus.tech | persona | Gastón Alejandro Ramos | kopernicus |
| S19 | 157 | Innen | Argentina, Buenos Aires (Clutch y The Manifest); el sitio no publica dirección | https://innen.io | team@innen.io | atención | casilla general | innen |
| S20 | 158 | Zarego | Argentina, CABA (El Salvador 5707); oficina en Delaware | https://zarego.com | hello@zarego.com | atención | casilla general | zarego |
| S21 | 159 | 404 // Software crafters | Argentina, Buenos Aires (The Manifest y Clutch); el sitio no publica dirección | https://proyecto404.com | info@proyecto404.com | atención | casilla general | 404 |
| S22 | 160 | Grupo Kelsoft | Argentina, CABA (Lavalle 333, ficha ATICMA); presencia en Mar del Plata | https://grupokelsoft.com | negocios@grupokelsoft.com | área | negocios | kelsoft |
| S23 | 161 | Infogestión | Argentina, La Plata (teléfono 221; socio del Polo IT La Plata) | https://infogestion.com.ar | info@infogestion.com.ar | atención | casilla general | infogestion |
| S24 | 162 | Julasoft | Argentina, La Plata (teléfono 221; socio del Polo IT La Plata); también España | https://www.julasoft.com | info@julasoft.com | atención | casilla general | julasoft |
| S25 | 163 | Tecnom | Argentina, La Plata (Diagonal 74 n.º 1463, piso 3) | https://www.tecnom.com.ar | ventas@tecnom.com.ar | área | ventas | tecnom |
| S26 | 164 | Quales Group | Argentina, CABA (Av. del Libertador 8142); socio del Polo IT La Plata; oficinas en Madrid y Montevideo | https://www.qualesgroup.com | info@qualesgroup.com | atención | casilla general | quales |
| S27 | 165 | Snoop Consulting | Argentina, La Plata (socio del Polo IT La Plata) y Buenos Aires (teléfono 11) | https://www.snoopconsulting.com | atencion@snoop.ar | atención | casilla general | snoop |
| S28 | 166 | BlueDraft | Argentina, La Plata (Camino Centenario y 507 bis) y CABA (Cátulo Castillo 2630) | https://www.bluedraft.com.ar | hello@bluedraft.com.ar | atención | casilla general | bluedraft |
| S29 | 167 | Avalith | Argentina, Mar del Plata; oficinas en Miami y Madrid | https://avalith.net | hello@avalith.net | atención | casilla general | avalith |
| S30 | 168 | Aoki Tech | Argentina, Mar del Plata | https://aokitech.com.ar | sofia@aokitech.com.ar | persona | Sofía | aoki |
| S31 | 169 | MINDO | Argentina, Mar del Plata (Av. Constitución 5225) | https://mindosoftware.com | contacto@mindosoftware.com | atención | casilla general | mindo |
| S32 | 170 | NexoSmart | Argentina, Bahía Blanca (Paraguay 18); sede en Valencia (España) | https://www.nexosmart.com.ar | maximo@sales.nexosmart.com.ar | persona | Maximiliano Rodríguez, fundador y director | nexosmart |
| S33 | 171 | VGS | Argentina, Bahía Blanca | https://vgs.com.ar | info@vgs.com.ar | atención | casilla general | vgs |
| S34 | 172 | Vortex | Argentina, Córdoba capital (oficinas en Buenos Aires, San José y Bogotá) | https://vortex-it.com | jorge.nieves@vortex-it.com | persona | Jorge Daniel Nieves Castillo, CEO según el catálogo del Córdoba Cluster | vortex |
| S35 | 173 | Puntonet Tech (Punto Net Soluciones SRL) | Argentina, Villa Carlos Paz (Córdoba) | https://www.puntonet.tech | edutra@puntonet.tech | persona | Enrique Dutra, CEO | puntonet |
| S36 | 174 | BIT S.A. | Argentina, Villa María (Córdoba) | https://www.bit.com.ar | bit@bit.com.ar | atención | casilla general | bit |
| S37 | 175 | AYI Group (BADI S.A.) | Argentina, Córdoba capital (Antonio del Viso 658, Alta Córdoba) | https://ayi.group | hi@ayi.group | atención | casilla general | ayi |
| S38 | 176 | Peperina Software | Argentina, Córdoba capital | https://peperina.io | sergio.maurenzi@peperina.io | persona | Sergio Antonio Maurenzi, contacto de la ficha | peperina |
| S39 | 177 | Skater Elephant (Resolution 8 Software SAS) | Argentina, Córdoba capital | https://skaterelephant.com/es | hello@skaterelephant.com | atención | casilla general | skaterelephant |
| S40 | 178 | Digital Motus | Argentina, Río Ceballos (Córdoba); también EE. UU. | https://www.digitalmotus.io/es | ignacio.lozita@digitalmotus.io | persona | Ignacio Lozita, CEO | digitalmotus |
| S41 | 179 | Vippinn | Argentina, Córdoba capital (sedes en Chile y España) | https://www.vippinn.com | dcarrizo@vippinn.com | persona | Daniel Carrizo, Business Developer | vippinn |
| S42 | 180 | Ascentio Technologies | Argentina, Córdoba capital y Río Cuarto (Córdoba); oficina en Gran Canaria | https://www.ascentio.com.ar | manderson@ascentio.com.ar | persona | María Lucila Anderson, CPO | ascentio |
| S43 | 181 | HMM Global (Home Medical Management) | Argentina, Córdoba capital (también Madrid y Panamá) | https://hmmglobal.com | dgerosa@hmmglobal.com | persona | Diego Gerosa, CEO | hmm |
| S44 | 182 | Asofix (Grupo Tagle) | Argentina, Córdoba capital | https://www.asofix.com | pablo.leoni@grupotagle.com.ar | persona | Pablo Leoni, contacto de la ficha del catálogo | asofix |
| S45 | 183 | Syloper | Argentina, Rosario (Santa Fe) | https://www.syloper.com | agustin@syloper.com | persona | Agustín Garassino, contacto de la ficha | syloper |
| S46 | 184 | Santa Fe Sistemas (Grupo SFS) | Argentina, Santa Fe capital | https://www.sfs.com.ar | comercial@sfs.com.ar | área | comercial | sfs |
| S47 | 185 | EximIA Solutions (Technology Service SAS) | Argentina, Rosario (Santa Fe) | https://eximia.ar | info@eximia.ar | atención | casilla general | eximia |
| S48 | 186 | Human Tech 4.0 (Business Buggers SRL) | Argentina, Rosario (Santa Fe), Lamadrid 470 (Polo Tecnológico) | https://www.humantech40.com.ar | pablo.crembil@humantech40.com.ar | persona | Pablo Crembil, COO y cofundador | humantech |
| S49 | 187 | Autologica | Argentina, Rosario (Santa Fe) | https://www.autologica.com/es | info@autologica.com | atención | casilla general | autologica |
| S50 | 188 | Kodear | Argentina, Rosario (Santa Fe) | https://kodear.dev | dgiovanon@kodear.net | persona | German David Giovanon, contacto de la ficha | kodear |
| S51 | 189 | Efficast | Argentina, Rosario (Santa Fe) | https://efficast.ai | simon@efficast.ai | persona | Simón Carpman, contacto de la ficha | efficast |
| S52 | 190 | Nonlinear Tecnología | Argentina, Santa Fe capital | https://nonlinear.com.ar | contacto@nonlinear.com.ar | atención | casilla general | nonlinear |
| S53 | 191 | Datawise | Argentina, Rosario (Lamadrid 470, Polo Tecnológico) y CABA: sede principal no clara | https://datawise.com.ar | diego.garcia@datawise.com.ar | persona | Diego García, contacto de la ficha del Polo | datawise |
| S54 | 192 | Midas Consultores | Argentina, Mendoza capital | https://midasconsultores.com.ar | comercial@midasconsultores.com.ar | área | comercial | midas |
| S55 | 193 | Merovingian Data | Argentina, Mendoza capital | https://merovingiandata.com | mj@merovingiandata.com | persona | Mario Japaz, contacto de la ficha | merovingian |
| S56 | 194 | Quinto Impacto | Argentina, Luján de Cuyo (Mendoza) | https://quintoimpacto.net | hola@quintoimpacto.net | atención | casilla general | quintoimpacto |
| S57 | 195 | Axis Human (Inamika Interactive S.A.) | Argentina, Mendoza capital | https://axishuman.ai | info@axishuman.ai | atención | casilla general | axishuman |
| S58 | 196 | Griftin (Área Clave Consultoría Estratégica SRL) | Argentina, Yerba Buena (Tucumán) | https://griftin.com.ar | contacto@griftin.com.ar | atención | casilla general | griftin |
| S59 | 197 | MBM Sistemas | Argentina, Salta capital (Maipú 546) | https://www.mbmsistemas.com.ar | ventas@mbmsistemas.com.ar | área | ventas | mbm |
| S60 | 198 | Blackfish Argentina | Argentina, Salta capital (San Luis 1460) | https://www.blackfish.com.ar | info@blackfish.com.ar | atención | casilla general | blackfish |
| S61 | 199 | Devoo | Argentina, Concordia (Entre Ríos) | https://devoo.io | info@devoo.io | atención | casilla general | devoo |
| S62 | 200 | Sudata | Argentina, Chaco (socia del Polo IT Chaco, Resistencia) | https://sudata.co | contacto@sudata.co | atención | casilla general | sudata |
| S63 | 201 | Crenein | Argentina, Chaco (socia del Polo IT Chaco; teléfono con característica 3725) | https://crenein.com | comercial@crenein.com | área | comercial | crenein |
| S64 | 202 | iSource | Argentina, Corrientes capital | https://isource.com.ar | martindebiasi@isource.com.ar | persona | nombre y cargo no publicados en texto | isource |
| S65 | 203 | Yugoo | Argentina, Corrientes capital | https://www.yugoo.com.ar | info@yugoo.com.ar | atención | casilla general | yugoo |

## S1. Biwares

- Contacto 139 de `seguimiento.md`
- Rubro: Consultora de negocio y tecnología: IA, chat generativo, biometría de voz, datos, modernización financiera, CABA (Av. del Libertador 1000, piso 13); oficinas en São Paulo, Miami, México, Madrid, Santiago y Bogotá (Argentina)
- Web: https://www.biwares.com
- Tipo: posible aliado (canal)
- Por qué encaja: Consultora con práctica de IA y productos de voz (biometría, VoC) para banca y retail; la atención telefónica con agentes es el eslabón que no tiene, y vende a los clientes que más llaman.
- Gancho: Productos 'Generative Chat', 'Voice of the Customer' y 'Voice Biometrics'; servicios de 'Artificial Intelligence' y 'Financial Modernization'; partner de Oracle, Microsoft, AWS y Google; 20 años (home y /about-us, 7-oct-2026). Tiene un 'Director of Artificial Intelligence' (Carlos Selmo, profesor del ITBA) y un 'New Business Director' (Diego Rivero).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | drivero@biwares.com | persona | Diego Rivero, New Business Director (mailto en /about-us) | https://www.biwares.com/about-us (7-oct-2026) |
|  | cselmo@biwares.com | persona | Carlos Selmo, Director of Artificial Intelligence | https://www.biwares.com/about-us (7-oct-2026) |
|  | eholz@biwares.com | persona | Edilson Holz, CEO | https://www.biwares.com/about-us (7-oct-2026) |
|  | rmanfredi@biwares.com | persona | Rubén Manfredi, fundador y director ejecutivo | https://www.biwares.com/about-us (7-oct-2026) |
|  | glarralde@biwares.com | persona | Gustavo Larralde, Associate Director | https://www.biwares.com/about-us (7-oct-2026) |
|  | dguzman@biwares.com | persona | Diego Guzmán, Associate Director | https://www.biwares.com/about-us (7-oct-2026) |
|  | info@biwares.com | atención | casilla general (Argentina, HQ) | https://www.biwares.com/contacto (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/biwares/; persona https://www.linkedin.com/in/diego-rivero-25b7029/ ; CEO: https://www.linkedin.com/in/eholz/ ; IA: https://ar.linkedin.com/in/carlos-selmo-47a65714a (enlazados en /about-us).

Otros canales: formulario https://www.biwares.com/contacto; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes X: https://twitter.com/eholz (CEO).

Para:

```
drivero@biwares.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Biwares
```

Texto:

```
Hola Diego, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Biwares ya vende chat generativo y biometría de voz a bancos y retailers: un agente que atienda y llame por teléfono, con número incluido, completa esa línea de productos.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=biwares

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (283 caracteres):

```
Hola Diego, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Biwares. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Diego, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Biwares ya vende chat generativo y biometría de voz a bancos y retailers: un agente que atienda y llame por teléfono, con número incluido, completa esa línea de productos.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=biwares

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S2. Duotach

- Contacto 140 de `seguimiento.md`
- Rubro: Consultora de software y automatización con IA: agentes de IA, chatbots de WhatsApp, n8n, desarrollo con Claude, CABA (teléfono 11) (Argentina)
- Web: https://duotach.com
- Tipo: posible aliado (canal)
- Por qué encaja: Ya implementa agentes de IA en WhatsApp para pymes y empresas de software; le falta la voz telefónica, y su producto Vozia es de WhatsApp, no de voz.
- Gancho: 'Consultora de software y automatización con IA. Construimos agentes de IA, automatizaciones y software a medida sobre los sistemas que tu empresa ya usa'; caso 'Agentes de IA en WhatsApp sobre su propio ERP' para una empresa de software de Ecuador; '15+ proyectos entregados, 7 países'; fundada en 2024 por Diego Carrion (CEO) y Tomás Romero (home y /nosotros, 7-oct-2026).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | contact@duotach.com | atención | casilla general | https://duotach.com/contacto (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Diego Carrion, CEO y cofundador; Tomás Romero, cofundador (/nosotros).

Teléfonos: +54 9 11 2516-1395 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/duotach; persona https://www.linkedin.com/in/diego-martin-carrion/ ; https://www.linkedin.com/in/tom%C3%A1s-gonzalo-romero-a01176161/ (enlazados en /nosotros).

Otros canales: formulario https://duotach.com/contacto; WhatsApp +54 9 11 2516-1395: botón https://wa.me/5491125161395 en home y contacto, con mensaje prearmado (7-oct-2026); redes https://www.instagram.com/duotach.

Para:

```
contact@duotach.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Duotach
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Duotach ya pone agentes de IA en WhatsApp sobre el ERP de sus clientes: el mismo agente puede atender y hacer llamadas, sin que ustedes armen la telefonía.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=duotach

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (277 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Duotach. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Duotach ya pone agentes de IA en WhatsApp sobre el ERP de sus clientes: el mismo agente puede atender y hacer llamadas, sin que ustedes armen la telefonía.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=duotach

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S3. Quilsoft

- Contacto 141 de `seguimiento.md`
- Rubro: Partner Silver de Odoo: ERP, desarrollos a medida e IA (Q-Pilot, 'IA para Ventas'), CABA (directorio de partners de Odoo vía erpresearch; teléfono 11) (Argentina)
- Web: https://www.quilsoft.com
- Tipo: posible aliado (canal)
- Por qué encaja: Vende Odoo con IA a pymes industriales y de distribución, que cobran y confirman por teléfono; un agente de voz integrado al ERP se vende dentro de su suite.
- Gancho: Título del sitio: 'Quilsoft: Desarrollo de IA & Software a Medida'; menú 'Inteligencia Artificial: Q-Pilot, IA para Ventas'; 'Partner Odoo en Argentina', 'Kit 4.0' (home, 7-oct-2026). 'Odoo Silver Partner based in Ciudad Autónoma de Buenos Aires', 12+ años, 6-25 consultores certificados (erpresearch.com/odoo-partners/quilsoft, 7-oct-2026).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@quilsoft.com | atención | casilla general | https://www.quilsoft.com/contacto (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 11 7078-0612 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/quilsoft/; persona —.

Otros canales: formulario https://www.quilsoft.com/contacto (formulario); WhatsApp +54 9 11 7078-0612: https://wa.me/5491170780612 en home y contacto (7-oct-2026); redes https://www.instagram.com/quilsoft.ar.

Para:

```
info@quilsoft.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Quilsoft
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Quilsoft ya vende Odoo con Q-Pilot e IA para ventas: las llamadas de cobranza y confirmación de sus clientes se pueden hacer desde ese mismo ERP, con un agente de voz que ustedes integran.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=quilsoft

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (278 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Quilsoft. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Quilsoft ya vende Odoo con Q-Pilot e IA para ventas: las llamadas de cobranza y confirmación de sus clientes se pueden hacer desde ese mismo ERP, con un agente de voz que ustedes integran.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=quilsoft

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S4. BamAI

- Contacto 142 de `seguimiento.md`
- Rubro: Consultora de automatización con IA para pymes: diagnóstico, implementación, agentes, CABA (Argentina)
- Web: https://bamai.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Agencia que ya implementa automatizaciones con IA en pymes; la voz telefónica es un servicio más para esos clientes.
- Gancho: 'Expertos en implementar IA para que tu negocio pueda escalar con confianza'; 'Agendar mi diagnóstico'; equipo: Pablo Albanese (CEO), Cristian Scaiola (CTO), Sebastián Bricchi (jefe de desarrollo) (/nosotros, 7-oct-2026). 16 personas, CABA (ficha Next from Argentina).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | contacto@bamai.ar | atención | casilla general (también es el email de la ficha de Cancillería) | https://bamai.ar/contacto (7-oct-2026); https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/bamai (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Pablo Albanese, CEO; Cristian Scaiola, CTO; Sebastián Bricchi, jefe de desarrollo (/nosotros).

Teléfonos: +54 9 11 2277-7497 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/ba-minds/; persona CEO: https://www.linkedin.com/in/pablo-albanese ; CTO: https://www.linkedin.com/in/cristian-daniel-scaiola-057b23180/ (enlazados en /nosotros).

Otros canales: formulario https://bamai.ar/contacto; WhatsApp +54 9 11 2277-7497: http://wa.me/5491122777497 en el sitio (7-oct-2026); redes —.

Para:

```
contacto@bamai.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de BamAI
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

BamAI ya automatiza procesos con IA en pymes: las llamadas que esas pymes siguen haciendo a mano son el siguiente proceso, y se integran por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=bamai

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (275 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como BamAI. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

BamAI ya automatiza procesos con IA en pymes: las llamadas que esas pymes siguen haciendo a mano son el siguiente proceso, y se integran por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=bamai

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S5. AIViento

- Contacto 143 de `seguimiento.md`
- Rubro: Consultoría de IA para empresas: agentes de IA, automatización e integración, CABA (Rafaela 3994); oficinas en Miami y Bogotá (Argentina)
- Web: https://www.aiviento.com
- Tipo: posible aliado (canal)
- Por qué encaja: Consultora boutique de IA que ya vende agentes y automatización; puede ofrecer la voz telefónica como módulo.
- Gancho: Título 'Consultoría de IA para empresas'; servicios 'Automatización e integración' y 'Consultoría en IA y tecnología'; dirección Rafaela 3994, CABA; 'Implementar IA desde la estrategia y dirección de las empresas' (home, 7-oct-2026; ficha de CESSI).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | contacto@aiviento.com | atención | casilla general | https://www.aiviento.com/ (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Fabiana Sasia (LinkedIn enlazado en la home; cargo no publicado).

Teléfonos: +54 11 2555-4381 (sitio).

LinkedIn: empresa — (la home enlaza solo un perfil personal); persona https://www.linkedin.com/in/fabianasasia-data-analytics-data-integration/ (enlazado en la home).

Otros canales: formulario https://www.aiviento.com/ (formulario); WhatsApp +54 9 11 2555-4381: widget de WhatsApp (joinchat, phone 5491125554381) en la home (7-oct-2026); redes —.

Para:

```
contacto@aiviento.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de AIViento
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

AIViento ya implementa agentes de IA y automatización en empresas: la atención telefónica con esos agentes, con número incluido, es el canal que les falta.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=aiviento

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (278 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como AIViento. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

AIViento ya implementa agentes de IA y automatización en empresas: la atención telefónica con esos agentes, con número incluido, es el canal que les falta.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=aiviento

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S6. Bombieri

- Contacto 144 de `seguimiento.md`
- Rubro: Consultora de transformación digital: desarrollo, adopción de IA (AI Buddy), automatización; 16 años, CABA (25 de Mayo 471) (Argentina)
- Web: https://www.bombieri.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende adopción de IA y desarrollo a empresas medianas; la voz telefónica es un caso concreto para llevarles.
- Gancho: 'AI Buddy: elevamos la capacidad de tu equipo con inteligencia artificial a través de un programa inmersivo de 4 semanas'; 'más de 16 años siendo el aliado estratégico de organizaciones que necesitan evolucionar' (home, 7-oct-2026). Socio de CESSI.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | ventas@bombieri.com.ar | área | ventas | https://www.bombieri.com.ar/contacto (7-oct-2026) |
|  | info@bombieri.com.ar | atención | casilla general | https://cessi.org.ar/socio/bombieri/ (ficha de socio de CESSI, bajada el 5-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 9 344 268-4457 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/bombieri/; persona —.

Otros canales: formulario https://www.bombieri.com.ar/contacto; WhatsApp +54 9 11 3134-6000 y +54 9 344 268-4457: https://wa.me/5491131346000 y https://wa.me/5493442684457 en el sitio (7-oct-2026); redes https://www.instagram.com/bombieri.ok.

Para:

```
ventas@bombieri.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Bombieri
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Bombieri ya lleva IA a los equipos de sus clientes con AI Buddy: el teléfono de esas empresas es el siguiente proceso para automatizar, y se vende como un proyecto más.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=bombieri

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (278 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Bombieri. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Bombieri ya lleva IA a los equipos de sus clientes con AI Buddy: el teléfono de esas empresas es el siguiente proceso para automatizar, y se vende como un proyecto más.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=bombieri

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S7. booleAr S.A.

- Contacto 145 de `seguimiento.md`
- Rubro: Servicios, SaaS, IA, automatización y modernización de sistemas críticos (finanzas, salud, agro), CABA (Esmeralda 1061) (Argentina)
- Web: https://www.boolear.com
- Tipo: posible aliado (canal)
- Por qué encaja: Consultora 'AI first' con clientes en finanzas y salud, los rubros con más llamadas de cobranza y turnos.
- Gancho: 'AI First & AI Based. Evolución tecnológica con frameworks de IA'; 'compañía especializada en servicios, SaaS, inteligencia artificial, automatización y modernización de sistemas críticos'; sectores 'finanzas, salud, agroindustria' (/es, 7-oct-2026). Socio de CESSI.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@boolear.com | atención | casilla general | https://www.boolear.com/es (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 11 6346-0523 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/boolear/; persona —.

Otros canales: formulario https://www.boolear.com/es (sección Contacto); WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/boolearTech ; https://www.x.com/boolearTech.

Para:

```
info@boolear.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de booleAr S.A.
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

booleAr se define 'AI first' y trabaja con finanzas y salud: en esos clientes la cobranza y los turnos siguen por teléfono, y un agente de voz se integra a lo que ustedes ya construyen.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=boolear

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (282 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como booleAr S.A.. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

booleAr se define 'AI first' y trabaja con finanzas y salud: en esos clientes la cobranza y los turnos siguen por teléfono, y un agente de voz se integra a lo que ustedes ya construyen.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=boolear

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S8. Grupo Esfera

- Contacto 146 de `seguimiento.md`
- Rubro: Desarrollo de software y agilidad organizacional potenciados por IA; agentic engineering, migración de legados, CABA (Argentina)
- Web: https://www.grupoesfera.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Software factory que ya vende desarrollo con IA a empresas; puede integrar la voz en sus proyectos.
- Gancho: Título del sitio: 'Grupo Esfera — Desarrollo de software y agilidad organizacional potenciados por IA' (home, 7-oct-2026). 50 personas, CEO Diego Fontdevila (ficha Next from Argentina). El sitio no publica emails: solo formulario.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | comercial@grupoesfera.com.ar | área | comercial (email de la ficha de Cancillería; el sitio no publica emails) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/grupo-esfera (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Diego Fontdevila, CEO; Claudio Figuerola; Sergio Romano (LinkedIn enlazados en la ficha).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/grupo-esfera; persona CEO: https://ar.linkedin.com/in/diegofontdevila (enlazado en el sitio).

Otros canales: formulario https://www.grupoesfera.com.ar/contacto; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/grupo_esfera.

Para:

```
comercial@grupoesfera.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Grupo Esfera
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Grupo Esfera ya desarrolla software potenciado por IA para sus clientes: la atención telefónica con agentes es un módulo más para esos mismos proyectos.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=grupoesfera

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (282 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Grupo Esfera. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Grupo Esfera ya desarrolla software potenciado por IA para sus clientes: la atención telefónica con agentes es un módulo más para esos mismos proyectos.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=grupoesfera

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S9. Eryx

- Contacto 147 de `seguimiento.md`
- Rubro: Cooperativa de trabajo y software factory: desarrollo a medida, IA y visión por computadora, criptografía, CABA (Bonpland 1953, según CB Insights) (Argentina)
- Web: https://eryx.co
- Tipo: posible aliado (canal)
- Por qué encaja: Cooperativa con proyectos de IA para industria y fintech; la voz es un canal nuevo para sus clientes.
- Gancho: 'Worker cooperative and software factory based in Argentina'; 'We engineered an AI-based system capable of detecting the presence or absence of ceiling components' para Toyota Boshoku; clientes Buenbit, Finaer, NextRoll, Adecoagro (home, 7-oct-2026). Fundada en 2011 (ficha CESSI: 2012). El sitio no publica emails: solo 'Let's talk'.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@eryx.co | atención | casilla general (el sitio no publica emails) | https://cessi.org.ar/socio/eryx-cooperativa-de-trabajo-limitada/ (ficha de socio de CESSI, bajada el 5-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/eryx-soluciones/; persona —.

Otros canales: formulario https://eryx.co/ (sección Let's talk); WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/eryxcoop ; https://twitter.com/eryxcoop.

Para:

```
info@eryx.co
```

Asunto:

```
Voz y telefonía para los agentes de IA de Eryx
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Eryx ya construye sistemas con IA para fintechs e industria: un agente que atienda el teléfono de esos clientes se integra por API a lo que ustedes desarrollan.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=eryx

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (274 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Eryx. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Eryx ya construye sistemas con IA para fintechs e industria: un agente que atienda el teléfono de esos clientes se integra por API a lo que ustedes desarrollan.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=eryx

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S10. 7Puentes

- Contacto 148 de `seguimiento.md`
- Rubro: Consultora de machine learning e IA: IA generativa, LLM, transformación digital, Buenos Aires (sitio) (Argentina)
- Web: https://7puentes.com
- Tipo: posible aliado (canal)
- Por qué encaja: Consultora pura de IA con clientes corporativos; la voz telefónica es un entregable que hoy no tiene.
- Gancho: Título: 'Expert ML & AI Solutions | Digital Transformation Consulting'; el sitio habla de IA generativa y LLM en toda la home (7-oct-2026). 'Diseño y desarrollo de soluciones de Inteligencia Artificial' (ficha de CESSI). El sitio no publica emails: solo formulario.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@7puentes.com | atención | casilla general (el sitio no publica emails) | https://cessi.org.ar/socio/7puentes/ (ficha de socio de CESSI, bajada el 5-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: —.

LinkedIn: empresa https://ar.linkedin.com/company/7puentes; persona —.

Otros canales: formulario https://7puentes.com/contact-short/; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/7pdata ; https://twitter.com/7pdata.

Para:

```
info@7puentes.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de 7Puentes
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

7Puentes ya diseña soluciones de IA y LLM para empresas: la atención y las llamadas por teléfono son un caso de uso que pueden entregar con nuestra API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=7puentes

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (278 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como 7Puentes. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

7Puentes ya diseña soluciones de IA y LLM para empresas: la atención y las llamadas por teléfono son un caso de uso que pueden entregar con nuestra API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=7puentes

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S11. Accion Point

- Contacto 149 de `seguimiento.md`
- Rubro: Software a medida y core bancario (Bantotal) con agentes de IA; 250 personas, más de 600 clientes en Latinoamérica, CABA; oficinas en Colombia y EE. UU. (Argentina)
- Web: https://accionpoint.com
- Tipo: posible aliado (canal)
- Por qué encaja: Integrador grande de banca y seguros en Latinoamérica: puede revender la voz a clientes con mucho volumen de llamadas (cobranza, atención).
- Gancho: 'Desarrollo de software con agentes de IA en el equipo... Así ayudamos a bancos y empresas de Latinoamérica'; 'Inteligencia Artificial' y RPA entre sus soluciones (home, 7-oct-2026). 250 personas, fundada en 1980, ISO 9001 y 27001, 'más de 600 clientes'; CEO Franco Schillagi (ficha Next from Argentina).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | marketing@accionpoint.com | área | marketing (email de la ficha de Cancillería) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/accion-point (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |
|  | info@accionpoint.com | atención | casilla general | https://accionpoint.com/contacto (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Franco Schillagi, CEO; Matías Labombarda; Ramiro Schillagi (LinkedIn enlazados en la ficha).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/accion-point/; persona CEO: https://www.linkedin.com/in/franco-schillagi-a3958014/ (ficha).

Otros canales: formulario https://accionpoint.com/contacto; WhatsApp +54 9 11 3831-4111: botón https://wa.link/51mb83 → api.whatsapp.com/send?phone=5491138314111, mensaje prearmado (7-oct-2026); Colombia +57 310 295-1624 (wa.link/vjnq8r); redes https://www.instagram.com/accionpoint ; https://twitter.com/AccionPoint.

Para:

```
marketing@accionpoint.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Accion Point
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Accion Point ya lleva agentes de IA a bancos y financieras de la región: la cobranza y la atención por teléfono de esos clientes se pueden hacer con un agente de voz que ustedes integran al core.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=accionpoint

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (282 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Accion Point. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Accion Point ya lleva agentes de IA a bancos y financieras de la región: la cobranza y la atención por teléfono de esos clientes se pueden hacer con un agente de voz que ustedes integran al core.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=accionpoint

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S12. Medve

- Contacto 150 de `seguimiento.md`
- Rubro: Software factory: desarrollo .NET a medida, IA aplicada (ML.NET, Azure AI, OpenAI), automatización con n8n y RPA, ERP, CABA (Av. Caseros 3350, 5º B) (Argentina)
- Web: https://www.medve.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Software factory chica que ya integra IA y automatización en sistemas de clientes; la voz es otra integración por API.
- Gancho: 'Inteligencia Artificial Aplicada: ML.NET, Azure AI y modelos custom'; 'Automatización Inteligente: workflows con n8n y RPA'; 'Integraciones sin límites: APIs, ERPs (SAP), CRMs (Salesforce)' (home, 7-oct-2026). 12 personas, fundada en 2012 (ficha Next from Argentina: CEO Bruno Olub).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@medve.com.ar | atención | casilla general (también es el email de la ficha) | https://www.medve.com.ar/ (7-oct-2026); https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/medve (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Bruno Olub, CEO; Sebastián Bidone (LinkedIn enlazados en la ficha).

Teléfonos: +54 9 11 6637-6176 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/medve-software-solutions; persona CEO: https://www.linkedin.com/in/bruno-olub-27911927/ (ficha).

Otros canales: formulario https://www.medve.com.ar/ (formulario); WhatsApp +54 9 11 6637-6176: https://wa.me/5491166376176 en la home, mensaje prearmado (7-oct-2026); redes https://www.instagram.com/medvesoft ; https://twitter.com/MedveSoft.

Para:

```
info@medve.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Medve
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Medve ya integra IA y automatizaciones con n8n en los sistemas de sus clientes: las llamadas de esos clientes son un flujo más, y se conectan por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=medve

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (275 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Medve. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Medve ya integra IA y automatizaciones con n8n en los sistemas de sus clientes: las llamadas de esos clientes son un flujo más, y se conectan por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=medve

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S13. Unitech

- Contacto 151 de `seguimiento.md`
- Rubro: GovTech: Iurix (justicia digital) y Tramix (gobierno electrónico) con IA; más de 30 años, CABA (Argentina)
- Web: https://www.unitech.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Vende a poderes judiciales y gobiernos, que atienden consultas y reclamos por teléfono; es un canal al segmento municipal del plan.
- Gancho: 'Transformación Digital de la Justicia y el Gobierno con Inteligencia Artificial. Nuestras soluciones Iurix y Tramix modernizan los sistemas judiciales y gubernamentales con el poder de la IA'; módulos 'Iurix Mind Flow', 'Tramix MIA Flow'; '+ de 30 años' (home, 7-oct-2026). Socio de CESSI y del Polo IT Buenos Aires.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | comercial@unitech-corp.com | área | comercial | https://www.unitech.com.ar/ (pie del sitio, 7-oct-2026); https://cessi.org.ar/socio/unitech-s-a/ (ficha de socio de CESSI, bajada el 5-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 11 5236-9988 (sitio).

LinkedIn: empresa https://ar.linkedin.com/company/unitechcorp; persona —.

Otros canales: formulario https://www.unitech.com.ar/ (Contáctenos); WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/unitechcorp ; https://twitter.com/UnitechCorp.

Para:

```
comercial@unitech-corp.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Unitech
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Unitech ya digitaliza justicia y gobierno con IA: un agente que atienda el teléfono de un organismo y avise vencimientos o turnos se integra a Tramix e Iurix por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=unitech

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (277 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Unitech. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Unitech ya digitaliza justicia y gobierno con IA: un agente que atienda el teléfono de un organismo y avise vencimientos o turnos se integra a Tramix e Iurix por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=unitech

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S14. Xelere

- Contacto 152 de `seguimiento.md`
- Rubro: Ciberseguridad y gestión de servicios de TI (ITSM) con IA; Distrito Tecnológico, CABA (Av. Caseros 3392, piso 8, Distrito Tecnológico); oficina en Santiago de Chile (Argentina)
- Web: https://www.xelere.com
- Tipo: posible aliado (canal)
- Por qué encaja: Integrador de ITSM con clientes corporativos y práctica de IA conversacional; la mesa de ayuda por teléfono es un caso directo.
- Gancho: Artículo 'IA y Digital Workplace: hacia una experiencia conversacional' (Thiago de Jesús, líder técnico ITSM, jul-2026); socios: Julián Hernández (presidente), Oscar Ojeda (líder comercial y RRHH), Mariano Bonina (gerente de servicios profesionales) (/empresa, 7-oct-2026). Socio del Polo IT Buenos Aires.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@xelere.com | atención | casilla general | https://www.xelere.com/contacto (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Julián Hernández, presidente; Oscar Ojeda, líder del área comercial; Mariano Bonina, gerente de servicios profesionales (/empresa).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/xelere/; persona —.

Otros canales: formulario https://www.xelere.com/contacto; WhatsApp +54 9 11 2306-3378: widget de WhatsApp del sitio (phone 5491123063378, 'Gracias por contactarte con Xelere') (7-oct-2026); redes https://www.instagram.com/xelere_argentina.

Para:

```
info@xelere.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Xelere
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Xelere ya lleva IA conversacional a la gestión de servicios de sus clientes: la mesa de ayuda por teléfono, atendida por el mismo agente, es el paso que sigue.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=xelere

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (276 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Xelere. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Xelere ya lleva IA conversacional a la gestión de servicios de sus clientes: la mesa de ayuda por teléfono, atendida por el mismo agente, es el paso que sigue.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=xelere

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S15. QActions

- Contacto 153 de `seguimiento.md`
- Rubro: QA, RPA e IA para calidad de software; automatización de procesos, Buenos Aires (sitio); oficina en Miami (Argentina)
- Web: https://qactions.com
- Tipo: posible aliado (canal)
- Por qué encaja: Consultora de automatización (RPA + IA) con clientes corporativos; puede sumar la voz a lo que automatiza.
- Gancho: Título: 'QACTIONS | Líderes en QA, RPA e IA para Calidad de Software'; socios fundadores Javier Marchese (CEO, más de 20 años en testing) y Alfonsina Morgavi (directora, representa a Argentina en HASTQB) (/equipo, 7-oct-2026). Socio de CESSI.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@qactions.com | atención | casilla general | https://qactions.com/ (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Javier Marchese, CEO; Alfonsina Morgavi, directora (/equipo).

Teléfonos: +54 9 11 6423-5643 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/qactions-srl/; persona CEO: https://www.linkedin.com/in/javier-marchese/ ; https://www.linkedin.com/in/alfonsinamorgavi/ (enlazados en /equipo).

Otros canales: formulario https://qactions.com/ (formulario); WhatsApp +54 9 11 6423-5643: botones api.whatsapp.com/send?phone=5491164235643 con mensajes 'DEMO', 'reunión' y 'alianza estratégica' (7-oct-2026); redes —.

Para:

```
info@qactions.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de QActions
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

QActions ya automatiza procesos con RPA e IA: las llamadas de atención y cobranza de sus clientes son el proceso que sigue, y hasta tienen un botón de 'alianza estratégica' en el sitio.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=qactions

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (278 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como QActions. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

QActions ya automatiza procesos con RPA e IA: las llamadas de atención y cobranza de sus clientes son el proceso que sigue, y hasta tienen un botón de 'alianza estratégica' en el sitio.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=qactions

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S16. Mooving (Mooving Tech S.A.U.)

- Contacto 154 de `seguimiento.md`
- Rubro: Consultoría estratégica, IA empresarial (Senda, agentes cognitivos) y arquitectura de datos para retail y utilities, CABA (sociedad inscripta en CABA, indicadores.ar) (Argentina)
- Web: https://mooving.ai
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende agentes de atención omnicanal a utilities y retail, los rubros con más llamadas de reclamos y cobranza; la voz telefónica es el canal que le falta a Senda.
- Gancho: 'Senda, IA empresarial: sistema de agentes cognitivos que automatiza la atención omnicanal para absorber picos de demanda'; 'Tramia, la suite retail con IA'; equipo: Patricio Grande (CEO, ex CFO de Camuzzi y EDELAP), Eddie Rodríguez von der Becke (CIO, IA), Julieta Albina (CSO) (/nosotros, 7-oct-2026). Socio de CESSI.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | hola@moovingtech.com | atención | casilla general (Cloudflare data-cfemail, decodificado) | https://mooving.ai/contacto (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Patricio Grande, CEO; Eddie Rodríguez von der Becke, CIO; Julieta Albina, CSO (/nosotros).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/moovingtech/; persona CEO: https://www.linkedin.com/in/patriciogrande/ ; CIO: https://www.linkedin.com/in/erbecke/ ; CSO: https://www.linkedin.com/in/julietaalbina/ (enlazados en /nosotros).

Otros canales: formulario https://mooving.ai/contacto; WhatsApp +54 9 11 5136-1574: https://wa.me/5491151361574 ('Agendar diagnóstico') en el sitio (7-oct-2026); redes —.

Para:

```
hola@moovingtech.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Mooving
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Senda ya automatiza la atención omnicanal de utilities y retailers: el teléfono, que en esos rubros sigue siendo el canal de reclamos y cobranza, es lo que le falta, y se suma con nuestra API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=mooving

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (277 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Mooving. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Senda ya automatiza la atención omnicanal de utilities y retailers: el teléfono, que en esos rubros sigue siendo el canal de reclamos y cobranza, es lo que le falta, y se suma con nuestra API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=mooving

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S17. OneInfo Consulting

- Contacto 155 de `seguimiento.md`
- Rubro: Consultora de CX, CRM e IA: partner de Oracle, Salesforce e IBM; OpenAI Select Partner; más de 20 años, CABA (Ricardo Rojas 401, piso 11); oficinas en Chile, España y Paraguay (Argentina)
- Web: https://www.oneinfoconsulting.com
- Tipo: posible aliado (canal)
- Por qué encaja: Implementa CRM y agentes de IA (Salesforce, OpenAI) en empresas medianas y grandes; la voz telefónica integrada al CRM completa la oferta.
- Gancho: 'Reconocidos como OpenAI Select Partner validamos nuestra capacidad para diseñar e implementar soluciones de IA de forma responsable y a escala'; partners Oracle CX, Salesforce ('agentes de IA'), IBM (home, 7-oct-2026). 'Más de 20 años brindando servicios de consultoría' (ficha CESSI).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@oneinfoconsulting.com | atención | casilla general | https://www.oneinfoconsulting.com/contacto (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/oneinfo-consulting/; persona —.

Otros canales: formulario https://www.oneinfoconsulting.com/contacto; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/oneinfoconsulting.

Para:

```
info@oneinfoconsulting.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de OneInfo Consulting
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

OneInfo ya implementa CRM y agentes de IA como OpenAI Select Partner: la atención y las llamadas por teléfono conectadas a ese CRM son el canal que falta en sus proyectos.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=oneinfo

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (288 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como OneInfo Consulting. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

OneInfo ya implementa CRM y agentes de IA como OpenAI Select Partner: la atención y las llamadas por teléfono conectadas a ese CRM son el canal que falta en sus proyectos.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=oneinfo

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S18. Kopernicus

- Contacto 156 de `seguimiento.md`
- Rubro: Consultoría IT y arquitectura tecnológica para aseguradoras: core insurance, legados, RPA, San Isidro (Buenos Aires) (Argentina)
- Web: https://www.kopernicus.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Consultora especializada en aseguradoras, que atienden siniestros, cobranza y renovaciones por teléfono; es el canal al segmento seguros del plan.
- Gancho: 'Impulsamos la evolución tecnológica de las aseguradoras desde la estrategia hasta la puesta en producción'; 'automatización robótica (RPA) de procesos clave en Argentina, Chile, Brasil, México, Uruguay, Paraguay y España' (home, 7-oct-2026). 30 personas, San Isidro; contacto Gastón Ramos (ficha Next from Argentina). El sitio no publica emails.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | ramos.gaston@kopernicus.tech | persona | Gastón Alejandro Ramos (ficha: 'CEO/Founder'; el sitio no publica emails) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/kopernicus-tech (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/66183725/ (ficha); persona https://www.linkedin.com/in/ramosgaston/ (enlazado en la ficha).

Otros canales: formulario https://www.kopernicus.com.ar/ (Contactanos); WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes —.

Para:

```
ramos.gaston@kopernicus.tech
```

Asunto:

```
Voz y telefonía para los agentes de IA de Kopernicus
```

Texto:

```
Hola Gastón, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Kopernicus ya moderniza el core y automatiza con RPA a aseguradoras: siniestros, cobranza y renovaciones de esos clientes siguen por teléfono, y un agente de voz se integra a ese core.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=kopernicus

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (287 caracteres):

```
Hola Gastón, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Kopernicus. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Gastón, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Kopernicus ya moderniza el core y automatiza con RPA a aseguradoras: siniestros, cobranza y renovaciones de esos clientes siguen por teléfono, y un agente de voz se integra a ese core.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=kopernicus

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S19. Innen

- Contacto 157 de `seguimiento.md`
- Rubro: Estudio de software, automatización e IA 'con foco humano'; low-code, consultoría de IA, Buenos Aires (Clutch y The Manifest); el sitio no publica dirección (Argentina)
- Web: https://innen.io
- Tipo: posible aliado (canal)
- Por qué encaja: Estudio chico que ya vende automatización e IA a empresas; la voz es un servicio más.
- Gancho: Título: 'Innen | Software, automatización e IA con foco humano'; 'Fundados en 2016 por un equipo formado en ciencias sociales'; 'Demos funcionales en 24 horas' (home y /about, 7-oct-2026). Caso con Adecco Argentina (Clutch).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | team@innen.io | atención | casilla general | https://innen.io/ (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/innen-lab/; persona —.

Otros canales: formulario https://innen.io/ ('Hablemos de tu proceso'); WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes —.

Para:

```
team@innen.io
```

Asunto:

```
Voz y telefonía para los agentes de IA de Innen
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Innen ya automatiza procesos con IA observando cómo trabaja cada equipo: las llamadas que esos equipos siguen haciendo a mano son un proceso más para automatizar.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=innen

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (275 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Innen. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Innen ya automatiza procesos con IA observando cómo trabaja cada equipo: las llamadas que esos equipos siguen haciendo a mano son un proceso más para automatizar.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=innen

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S20. Zarego

- Contacto 158 de `seguimiento.md`
- Rubro: Desarrollo de software a medida e ingeniería de IA (nearshore para EE. UU.), CABA (El Salvador 5707); oficina en Delaware (Argentina)
- Web: https://zarego.com
- Tipo: posible aliado (canal)
- Por qué encaja: Software factory con práctica de IA; puede integrar la voz en productos de sus clientes de EE. UU. y Argentina.
- Gancho: Título: 'Custom Software Development & AI Engineering'; 'AI-powered tech solutions'; dirección El Salvador 5707, CABA (/contact-us, 7-oct-2026). 16 reseñas en Clutch (4,8).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | hello@zarego.com | atención | casilla general | https://zarego.com/contact-us (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 11 5588-2330 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/2575535; persona —.

Otros canales: formulario https://zarego.com/contact-us; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/zarego_ ; https://twitter.com/zarego_.

Para:

```
hello@zarego.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Zarego
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Zarego ya hace ingeniería de IA a medida: un agente de voz con número incluido es un componente más que pueden integrar en los productos de sus clientes.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=zarego

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (276 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Zarego. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Zarego ya hace ingeniería de IA a medida: un agente de voz con número incluido es un componente más que pueden integrar en los productos de sus clientes.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=zarego

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S21. 404 // Software crafters

- Contacto 159 de `seguimiento.md`
- Rubro: Estudio de software: productos digitales, IA aplicada, agentes de IA, IA conversacional con LLM (MCP, RAG), Buenos Aires (The Manifest y Clutch); el sitio no publica dirección (Argentina)
- Web: https://proyecto404.com
- Tipo: posible aliado (canal)
- Por qué encaja: Ya construye IA conversacional y agentes integrados a sistemas de clientes; la voz por teléfono es el canal que no construyen.
- Gancho: 'IA aplicada: diseñamos automatizaciones con IA y agentes de IA que se integran con tus sistemas... Construimos soluciones de IA conversacional e integraciones con LLMs mediante MCP, RAG' (/es, 7-oct-2026). Desde 2011; clientes Greenpeace, Coca-Cola, Disney, Veritran; apps del G20 2018 (The Manifest).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@proyecto404.com | atención | casilla general | https://proyecto404.com/es (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/404-web-&-mobile-development/; persona —.

Otros canales: formulario https://proyecto404.com/es (Contacto); WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/404crafters.

Para:

```
info@proyecto404.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de 404 // Software crafters
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

404 ya construye IA conversacional con RAG y MCP para sus clientes: ese mismo agente puede atender y hacer llamadas, sin que ustedes armen la telefonía.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=404

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (294 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como 404 // Software crafters. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

404 ya construye IA conversacional con RAG y MCP para sus clientes: ese mismo agente puede atender y hacer llamadas, sin que ustedes armen la telefonía.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=404

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S22. Grupo Kelsoft

- Contacto 160 de `seguimiento.md`
- Rubro: Servicios y consultoría de IT + IA: desarrollo, IA, consultoría y automatización; +250 profesionales, 9 países, CABA (Lavalle 333, ficha ATICMA); presencia en Mar del Plata (Argentina)
- Web: https://grupokelsoft.com
- Tipo: posible aliado (canal)
- Por qué encaja: Consultora de IT e IA con escala para revender a clientes corporativos de varios países.
- Gancho: '+250 profesionales. Contamos con un equipo especializado en desarrollo, IA, consultoría y automatización'; '+9 países', '+50 proyectos' (home, 7-oct-2026). 'Empresa de servicios y consultoría de IT + AI', Lavalle 333, Buenos Aires (ficha de socio de ATICMA).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | negocios@grupokelsoft.com | área | negocios (el sitio no publica emails) | https://www.aticma.org.ar/nuestros-socios/ (ficha de socio de ATICMA, Mar del Plata; vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 11 3489-8385 (ficha ATICMA).

LinkedIn: empresa https://www.linkedin.com/company/grupo-kelsoft/; persona —.

Otros canales: formulario https://grupokelsoft.com/ ('Trabajemos juntos'); WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/grupo_kelsoft.

Para:

```
negocios@grupokelsoft.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Grupo Kelsoft
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Grupo Kelsoft ya vende desarrollo, IA y automatización en nueve países: la atención telefónica con agentes, con inferencia en Argentina, es un servicio más para esa cartera.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=kelsoft

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (283 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Grupo Kelsoft. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Grupo Kelsoft ya vende desarrollo, IA y automatización en nueve países: la atención telefónica con agentes, con inferencia en Argentina, es un servicio más para esa cartera.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=kelsoft

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S23. Infogestión

- Contacto 161 de `seguimiento.md`
- Rubro: Consultoría digital para pymes: IA, ERP, BI, CRM, e-commerce, RRHH, La Plata (teléfono 221; socio del Polo IT La Plata) (Argentina)
- Web: https://infogestion.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Implementa IA, ERP y CRM en pymes platenses; las llamadas de esas pymes son el siguiente proceso.
- Gancho: Título: 'Infogestión – Transformamos PyMEs desordenadas en empresas inteligentes impulsadas por IA'; menú 'Inteligencia artificial | IA', 'Gestión integral | ERP', 'Gestión de clientes | CRM'; 'Hacer diagnóstico' (home y /quienes-somos, 7-oct-2026).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@infogestion.com.ar | atención | casilla general (Cloudflare data-cfemail, decodificado) | https://infogestion.com.ar/contacto (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 9 221 567-6685 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/infogesti-n-sur/; persona —.

Otros canales: formulario https://infogestion.com.ar/contacto; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/infogestionsur.

Para:

```
info@infogestion.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Infogestión
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Infogestión ya convierte pymes en 'empresas inteligentes impulsadas por IA': el teléfono de esas pymes, atendido por un agente conectado al ERP y al CRM que ustedes implementan, es el paso que sigue.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=infogestion

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (281 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Infogestión. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Infogestión ya convierte pymes en 'empresas inteligentes impulsadas por IA': el teléfono de esas pymes, atendido por un agente conectado al ERP y al CRM que ustedes implementan, es el paso que sigue.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=infogestion

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S24. Julasoft

- Contacto 162 de `seguimiento.md`
- Rubro: Software a medida, IA y machine learning, automatización inteligente para empresas y organismos, La Plata (teléfono 221; socio del Polo IT La Plata); también España (Argentina)
- Web: https://www.julasoft.com
- Tipo: posible aliado (canal)
- Por qué encaja: Software factory con IA y clientes en organismos públicos y empresas; la voz se suma a sus automatizaciones.
- Gancho: 'Inteligencia Artificial y Machine Learning... Brindamos soluciones avanzadas que permiten a las empresas y organismos automatizar procesos'; 'Intelligent automation' (home, 7-oct-2026). Socio activo del Polo IT La Plata.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@julasoft.com | atención | casilla general | https://www.julasoft.com/contacto (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 9 221 570-6102 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/julasoft/; persona —.

Otros canales: formulario https://www.julasoft.com/contacto; WhatsApp +54 9 221 570-6102: https://wa.me/5492215706102 en el sitio (7-oct-2026); España +34 600 350 833; redes https://www.instagram.com/julasoft_it.

Para:

```
info@julasoft.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Julasoft
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Julasoft ya automatiza procesos con IA en empresas y organismos: las llamadas de atención y aviso de esos clientes son un proceso más, y se integran por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=julasoft

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (278 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Julasoft. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Julasoft ya automatiza procesos con IA en empresas y organismos: las llamadas de atención y aviso de esos clientes son un proceso más, y se integran por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=julasoft

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S25. Tecnom

- Contacto 163 de `seguimiento.md`
- Rubro: CRM automotriz con IA (Tecna) para concesionarios: leads, atención 24/7, campañas, postventa; México, Colombia, Perú, Chile, La Plata (Diagonal 74 n.º 1463, piso 3) (Argentina)
- Web: https://www.tecnom.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Software vertical para concesionarias, donde el teléfono es el canal de turnos de taller, seguimiento de leads y postventa; canal directo al rubro.
- Gancho: 'Somos el primer CRM con IA para la Industria Automotriz en LATAM'; producto 'Tecna (IA)'; 'Implementamos herramientas para calificar prospectos automáticamente y brindar atención 24/7'; 'Unificamos leads de redes sociales, portales y WhatsApp' (home y /nosotros, 7-oct-2026). Socio del Polo IT La Plata.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | ventas@tecnom.com.ar | área | ventas | https://www.tecnom.com.ar/ (pie del sitio, 7-oct-2026) |
|  | soporte@tecnom.com.ar | área | soporte | https://www.tecnom.com.ar/ (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/tecnom/; persona —.

Otros canales: formulario https://www.tecnom.com.ar/ ('Agendar demo'); WhatsApp +54 9 2241 52-7982: api.whatsapp.com/send/?phone=5492241527982 en el sitio (7-oct-2026); México +52 44 0205-4951; redes https://www.instagram.com/tecnom_latam.

Para:

```
ventas@tecnom.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Tecnom
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Tecna ya califica leads y atiende 24/7 por WhatsApp a concesionarios: el teléfono, que en el rubro sigue siendo el canal de turnos de taller y seguimiento, es lo que le falta al CRM.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=tecnom

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (276 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Tecnom. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Tecna ya califica leads y atiende 24/7 por WhatsApp a concesionarios: el teléfono, que en el rubro sigue siendo el canal de turnos de taller y seguimiento, es lo que le falta al CRM.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=tecnom

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S26. Quales Group

- Contacto 164 de `seguimiento.md`
- Rubro: Consultora de datos e IA: estrategia de datos, BI, analítica avanzada, 'Plataforma Agéntica' con agentes de IA, CABA (Av. del Libertador 8142); socio del Polo IT La Plata; oficinas en Madrid y Montevideo (Argentina)
- Web: https://www.qualesgroup.com
- Tipo: posible aliado (canal)
- Por qué encaja: Consultora de datos e IA con plataforma de agentes; la voz telefónica es un canal más para esos agentes.
- Gancho: 'Agentes AI is the new BI: agentes de IA que te permiten chatear con tus datos... Disponibles 7×24'; 'Plataforma Agéntica'; 'Data | AI: implementamos soluciones de Analítica Avanzada, Ciencia de Datos e Inteligencia Artificial' (home, 7-oct-2026). Fundada en 2013 (ficha CESSI). El sitio no publica emails.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@qualesgroup.com | atención | casilla general (el sitio no publica emails) | https://cessi.org.ar/socio/qg-s-r-l-quales-group/ (ficha de socio de CESSI, bajada el 5-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/quales-group/; persona —.

Otros canales: formulario https://www.qualesgroup.com/contacto; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/qualesgroup.

Para:

```
info@qualesgroup.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Quales Group
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Quales ya tiene una plataforma agéntica para que las empresas hablen con sus datos: hablar por teléfono con los clientes de esas empresas es el canal que falta, y se integra por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=quales

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (282 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Quales Group. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Quales ya tiene una plataforma agéntica para que las empresas hablen con sus datos: hablar por teléfono con los clientes de esas empresas es el canal que falta, y se integra por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=quales

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S27. Snoop Consulting

- Contacto 165 de `seguimiento.md`
- Rubro: Servicios de software y transformación digital con IA: consultoría de IA, interfaces conversacionales; 26 años, La Plata (socio del Polo IT La Plata) y Buenos Aires (teléfono 11) (Argentina)
- Web: https://www.snoopconsulting.com
- Tipo: posible aliado (canal)
- Por qué encaja: Consultora con 26 años, práctica de IA e interfaces conversacionales; la voz telefónica completa esa práctica.
- Gancho: 'Consultoría de IA para empresas'; 'enfocados en la mejora de procesos y productividad mediante la implementación de Inteligencia Artificial'; 'interfaces conversacionales' entre sus herramientas; 26 años; Sergio Candelo, Entrepreneur of the Year y CEO del Año en los Premios Sadosky (home y /contacto, vistos con WebFetch el 7-oct-2026; el sitio responde 403 a curl).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | atencion@snoop.ar | atención | casilla general | https://www.snoopconsulting.com/contacto (WebFetch, 7-oct-2026) |
|  | atencion@snoopconsulting.com | atención | casilla general (ficha vieja) | https://cessi.org.ar/socio/snoop-consulting/ (ficha de socio de CESSI, bajada el 5-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Sergio Candelo (CEO según los premios citados en el sitio).

Teléfonos: +54 11 5263-2521 ; +54 9 11 6997-1830 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/snoop-consulting/; persona —.

Otros canales: formulario https://www.snoopconsulting.com/contacto; WhatsApp +54 9 11 6997-1830: botón de WhatsApp del sitio (+5491169971830) (WebFetch, 7-oct-2026); redes YouTube: https://www.youtube.com/user/SnoopMarketing.

Para:

```
atencion@snoop.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Snoop Consulting
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Snoop ya vende consultoría de IA e interfaces conversacionales: la atención telefónica con esos mismos agentes es el canal que falta en su catálogo.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=snoop

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (286 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Snoop Consulting. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Snoop ya vende consultoría de IA e interfaces conversacionales: la atención telefónica con esos mismos agentes es el canal que falta en su catálogo.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=snoop

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S28. BlueDraft

- Contacto 166 de `seguimiento.md`
- Rubro: Consultora de analítica de datos, modelos financieros e IA; agnóstica (AWS, Microsoft, Google), La Plata (Camino Centenario y 507 bis) y CABA (Cátulo Castillo 2630) (Argentina)
- Web: https://www.bluedraft.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Consultora de datos con IA y clientes financieros; la voz es un canal para los procesos que modela (cobranza, atención).
- Gancho: 'Diseñamos soluciones analíticas a medida para distintas industrias'; 'Trabajamos con AWS, Microsoft, Google, plataformas analíticas e inteligencia artificial'; oficinas en La Plata y CABA (/nosotros, 7-oct-2026). Socio activo del Polo IT La Plata.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | hello@bluedraft.com.ar | atención | casilla general | https://www.bluedraft.com.ar/nosotros (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 11 5263-7100 ; +54 9 11 7060-5146 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/bluedraft/; persona —.

Otros canales: formulario https://www.bluedraft.com.ar/contacto; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/bluedraft.analytics.

Para:

```
hello@bluedraft.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de BlueDraft
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

BlueDraft ya modela datos y finanzas con IA para sus clientes: las llamadas de cobranza y atención que salen de esos modelos las puede hacer un agente de voz integrado por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=bluedraft

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (279 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como BlueDraft. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

BlueDraft ya modela datos y finanzas con IA para sus clientes: las llamadas de cobranza y atención que salen de esos modelos las puede hacer un agente de voz integrado por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=bluedraft

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S29. Avalith

- Contacto 167 de `seguimiento.md`
- Rubro: Software 'human-led, AI-accelerated': equipos senior con agentes de IA; desde 2011, Mar del Plata; oficinas en Miami y Madrid (Argentina)
- Web: https://avalith.net
- Tipo: posible aliado (canal)
- Por qué encaja: Software factory marplatense de 15 años con IA en el centro; puede integrar la voz en productos de sus clientes.
- Gancho: 'Human-led software. AI-accelerated'; 'EST_2011 · MAR_DEL_PLATA · MIAMI · MADRID'; 'AI agents write the code, under human direction'; equipo: Agustín Antonino (cofundador y CEO), Joaquín Antonino (cofundador), José Bergues (CTO), Ana Szlapelis (CFO) (home y /about-us, 7-oct-2026).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | hello@avalith.net | atención | casilla general | https://avalith.net/contact (7-oct-2026) |
|  | hola@avalith.net | atención | casilla general (es) | https://avalith.net/contact (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Agustín Antonino, CEO; José Bergues, CTO; Joaquín Antonino, cofundador; Ana Szlapelis, CFO (/about-us).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/avalith-net/; persona CEO: https://www.linkedin.com/in/agustin-antonino/ ; CFO: https://www.linkedin.com/in/ana-szlapelis-1b827933/ (enlazados en /about-us).

Otros canales: formulario https://avalith.net/contact; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/avalithar.

Para:

```
hello@avalith.net
```

Asunto:

```
Voz y telefonía para los agentes de IA de Avalith
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Avalith ya entrega software acelerado con agentes de IA: un agente que atienda y llame por teléfono, con número incluido, es un componente más para los productos de sus clientes.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=avalith

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (277 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Avalith. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Avalith ya entrega software acelerado con agentes de IA: un agente que atienda y llame por teléfono, con número incluido, es un componente más para los productos de sus clientes.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=avalith

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S30. Aoki Tech

- Contacto 168 de `seguimiento.md`
- Rubro: Agentes de IA, ERP y gestión para pymes; automatización de tareas, Mar del Plata (Argentina)
- Web: https://aokitech.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende agentes de IA y un asistente virtual a pymes; el canal de voz telefónica es lo que le falta a ese asistente.
- Gancho: Título del sitio: 'Aoki | Agentes de IA, ERP y gestión para PyMEs Argentina' (el contenido se carga por JavaScript, 7-oct-2026). 'Desarrollo de Software y robótica avanzada. Disminuimos tiempos y errores en las tareas de empresas a través de la automatización' (ficha de socio de ATICMA). 'Desarrollo de IA para automatizar tareas... principal producto asistente virtual' (ficha CESSI).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | sofia@aokitech.com.ar | persona | Sofía (apellido y cargo no publicados; es el contacto de la ficha de ATICMA) | https://www.aticma.org.ar/nuestros-socios/ (ficha de socio de ATICMA, Mar del Plata; vista el 7-oct-2026) |
|  | info@aokitech.com.ar | atención | casilla general | https://aokitech.com.ar/ (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: 230 260-9947 (ficha ATICMA).

LinkedIn: empresa —; persona —.

Otros canales: formulario https://aokitech.com.ar/contacto; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes https://www.instagram.com/ia.aoki.

Para:

```
sofia@aokitech.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Aoki Tech
```

Texto:

```
Hola Sofía, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Aoki ya vende agentes de IA y ERP a pymes: el mismo asistente puede atender la línea telefónica de esas pymes, con número incluido.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=aoki

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (285 caracteres):

```
Hola Sofía, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Aoki Tech. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Sofía, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Aoki ya vende agentes de IA y ERP a pymes: el mismo asistente puede atender la línea telefónica de esas pymes, con número incluido.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=aoki

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S31. MINDO

- Contacto 169 de `seguimiento.md`
- Rubro: Agentes de IA para e-commerce en WhatsApp e Instagram; CRM; programa de partners, Mar del Plata (Av. Constitución 5225) (Argentina)
- Web: https://mindosoftware.com
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende agentes de IA de texto a e-commerces y tiene programa de partners; la voz telefónica es el canal que no cubre.
- Gancho: Título: 'MINDO | Agentes de IA para Ecommerce en WhatsApp e Instagram'; botones de WhatsApp 'quiero ser partner de MINDO' y 'información sobre MINDO CRM' (home, 7-oct-2026). 'Agentes de IA para ecommerce', Av. Constitución 5225, Mar del Plata (ficha de socio de ATICMA). El sitio no publica emails.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | contacto@mindosoftware.com | atención | casilla general (el sitio no publica emails) | https://www.aticma.org.ar/nuestros-socios/ (ficha de socio de ATICMA, Mar del Plata; vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 9 223 535-1858 (ficha ATICMA).

LinkedIn: empresa https://www.linkedin.com/company/mindo-software/; persona —.

Otros canales: formulario https://mindosoftware.com/ (botones de WhatsApp); WhatsApp +54 9 223 535-1858: https://wa.me/5492235351858 en la home; también +54 9 11 6275-2880 (wa.me/5491162752880, 'quiero ser partner de MINDO') (7-oct-2026); redes https://www.instagram.com/mindo.ai.

Para:

```
contacto@mindosoftware.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de MINDO
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

MINDO ya atiende e-commerces con agentes de IA en WhatsApp e Instagram: con nosotros esos agentes pueden además atender y hacer llamadas, con número incluido.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=mindo

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (275 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como MINDO. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

MINDO ya atiende e-commerces con agentes de IA en WhatsApp e Instagram: con nosotros esos agentes pueden además atender y hacer llamadas, con número incluido.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=mindo

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S32. NexoSmart

- Contacto 170 de `seguimiento.md`
- Rubro: Software factory y company builder: desarrollo, soluciones de IA, automatizaciones con IA, chatbots, e-commerce, apps; desde 2014, Bahía Blanca (Paraguay 18); sede en Valencia (España) (Argentina)
- Web: https://www.nexosmart.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Software factory bahiense que ya vende automatizaciones y chatbots con IA a pymes; la voz es otro canal para esos mismos clientes.
- Gancho: Título: 'Desarrollo de plataformas Web y Apps, Automatizaciones con AI'; menú 'Soluciones de IA', 'Posicionamiento IA'; 'Fundador y Director Maximiliano Rodríguez; CEO Juan Carlos Rodríguez; sede Argentina: Paraguay 18, Bahía Blanca; +50 proyectos, 8 países' (/sobre-nosotros, 7-oct-2026). Socio del Polo Tecnológico Bahía Blanca.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | maximo@sales.nexosmart.com.ar | persona | Maximiliano Rodríguez, fundador y director (casilla publicada en home, contacto y /sobre-nosotros) | https://www.nexosmart.com.ar/contacto (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada. Sin email: Juan Carlos Rodríguez, CEO (/sobre-nosotros).

Teléfonos: +54 9 291 507-8136 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/nexosmart; persona https://www.linkedin.com/in/maximiliano-rodr%C3%ADguez-93626273/ (enlazado en el sitio).

Otros canales: formulario https://www.nexosmart.com.ar/contacto; WhatsApp +54 9 291 507-8136: https://wa.me/5492915078136 en el sitio (7-oct-2026); redes https://www.instagram.com/nexosmart.

Para:

```
maximo@sales.nexosmart.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de NexoSmart
```

Texto:

```
Hola Maximiliano, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

NexoSmart ya vende automatizaciones y chatbots con IA a pymes de Bahía Blanca y España: el teléfono de esas pymes, atendido por el mismo agente, es el canal que falta.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=nexosmart

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (291 caracteres):

```
Hola Maximiliano, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como NexoSmart. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Maximiliano, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

NexoSmart ya vende automatizaciones y chatbots con IA a pymes de Bahía Blanca y España: el teléfono de esas pymes, atendido por el mismo agente, es el canal que falta.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=nexosmart

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S33. VGS

- Contacto 171 de `seguimiento.md`
- Rubro: Desarrollo de software, ERP propio y 'AI con VGS Labs'; más de 30 años, operaciones en 5 países, Bahía Blanca (Argentina)
- Web: https://vgs.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Proveedor de ERP con laboratorio de IA y clientes comerciales e industriales; la voz se integra a su ERP.
- Gancho: Menú 'AI con VGS LABS'; 'Con más de 30 años de experiencia en el desarrollo de software y consultoría informática, tenemos operaciones en 5 países'; 'Elegimos estratégicamente Bahía Blanca como sede'; 'Guillermo, Founder & CEO' (home y /nosotros, 7-oct-2026). Socio del Polo Tecnológico Bahía Blanca.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@vgs.com.ar | atención | casilla general | https://vgs.com.ar/contacto (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Guillermo (apellido no publicado), fundador y CEO (/nosotros).

Teléfonos: +54 291 517-4011 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/vgs_consultoria_informatica/; persona —.

Otros canales: formulario https://vgs.com.ar/contacto; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio, 7-oct-2026); redes —.

Para:

```
info@vgs.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de VGS
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

VGS ya suma IA (VGS Labs) a su ERP y a sus desarrollos: las llamadas de cobranza y confirmación de sus clientes se pueden hacer desde ese ERP con un agente de voz que ustedes integran.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=vgs

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (273 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como VGS. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

VGS ya suma IA (VGS Labs) a su ERP y a sus desarrollos: las llamadas de cobranza y confirmación de sus clientes se pueden hacer desde ese ERP con un agente de voz que ustedes integran.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=vgs

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S34. Vortex

- Contacto 172 de `seguimiento.md`
- Rubro: Consultora de plataformas digitales AI-First: integración de apps y datos, CX y automatización, Córdoba capital (oficinas en Buenos Aires, San José y Bogotá) (Argentina)
- Web: https://vortex-it.com
- Tipo: posible aliado (canal)
- Por qué encaja: Ya integra IA en los canales de bancos y medios de pago; puede sumar la voz telefónica como canal más en esas plataformas.
- Gancho: 'Adoptamos un enfoque AI-First: integramos inteligencia artificial desde el inicio de cada solución' (catálogo del Córdoba Cluster); servicios 'CX & Automation' e 'Integración de Apps y Datos'; +100 clientes activos, +300 proyectos, +12 países; clientes Banco Galicia (back-end de canales), Pago Fácil - Western Union, Naranja X, Prosegur, DirecTV, Arcor (sitio y catálogo). Fundada en 2017, 101-200 empleados.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | jorge.nieves@vortex-it.com | persona | Jorge Daniel Nieves Castillo, CEO según el catálogo del Córdoba Cluster ('Director de innovación' en /nosotros del sitio) | https://catalogo.cordobacluster.com/nuestros-socios (catálogo público de socios del Córdoba Technology Cluster, ficha de la empresa; visto el 7-oct-2026) |
|  | info@vortex-it.com | atención | casilla general (sitio, home y /contacto) | https://vortex-it.com/contacto/ (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada. Sin email: Ariel Castro, Director Ejecutivo; Matías Cortes, cofundador; Guillermo Bellini, Director de Proyectos (https://vortex-it.com/nosotros/, LinkedIn enlazados).

Teléfonos: +54 9 351 510-4734 (Córdoba) y +54 9 11 6472-1000 (Buenos Aires), sitio /contacto; 351 715-2232 (catálogo).

LinkedIn: empresa https://www.linkedin.com/company/vortex-it-ok/; persona https://www.linkedin.com/in/jorgedanielnieves (enlazado en /nosotros); https://www.linkedin.com/in/jdnievescastillo/ (catálogo).

Otros canales: formulario https://vortex-it.com/contacto/; WhatsApp +54 9 351 510-4734: botón de WhatsApp del sitio (api.whatsapp.com/send?phone=5493515104734, home y /contacto, 7-oct-2026); también 351 715-2232 y los números de Buenos Aires, Costa Rica y Colombia; redes https://www.instagram.com/vortex.it.

Para:

```
jorge.nieves@vortex-it.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Vortex
```

Texto:

```
Hola Jorge, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Vortex ya integra IA desde el diseño en los canales de bancos y medios de pago: la atención y las llamadas de esos mismos clientes pueden salir de un agente de voz integrado por API, con la telefonía resuelta.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=vortex

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (282 caracteres):

```
Hola Jorge, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Vortex. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Jorge, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Vortex ya integra IA desde el diseño en los canales de bancos y medios de pago: la atención y las llamadas de esos mismos clientes pueden salir de un agente de voz integrado por API, con la telefonía resuelta.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=vortex

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S35. Puntonet Tech (Punto Net Soluciones SRL)

- Contacto 173 de `seguimiento.md`
- Rubro: Consultora tecnológica: RPA, asistentes virtuales con IA, ciberseguridad, DBA; productos LinA Fiscal y LinA Med, Villa Carlos Paz (Córdoba) (Argentina)
- Web: https://www.puntonet.tech
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende asistentes virtuales con IA y RPA a empresas y salud; le falta el canal de voz telefónica.
- Gancho: Servicios de 'Automatización de procesos (RPA)' y 'Asistentes virtuales: diseñado para combinar la funcionalidad de los chats tradicionales con el poder de la inteligencia artificial, tanto tradicional como generativa'; +40 especialistas (IA, RPA, DBA, ciberseguridad), +20 años, página 'Partners' y producto LinA Med para salud (sitio). Fundada en 2001, 21-50 empleados (catálogo del Córdoba Cluster).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | edutra@puntonet.tech | persona | Enrique Dutra, CEO | https://catalogo.cordobacluster.com/nuestros-socios (catálogo público de socios del Córdoba Technology Cluster, ficha de la empresa; visto el 7-oct-2026) |
|  | dlanghi@puntonet.tech | persona | Daniel Langhi, CEO (socio) | https://catalogo.cordobacluster.com/nuestros-socios (catálogo público de socios del Córdoba Technology Cluster, ficha de la empresa; visto el 7-oct-2026) |
|  | administracion@puntonet.tech | área | administración; Silvana Martino, CFO | https://catalogo.cordobacluster.com/nuestros-socios (catálogo público de socios del Córdoba Technology Cluster, ficha de la empresa; visto el 7-oct-2026) |
|  | comercial@puntonet.tech | área | comercial (sitio, home y contacto) | https://www.puntonet.tech/ (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: +54 351 592-1883 / 351 648-1183 (sitio); +54 351 751-9670 (catálogo).

LinkedIn: empresa https://ar.linkedin.com/company/punto-net-soluciones-s-r-l-; persona https://www.linkedin.com/in/enriquedutra/ ; https://www.linkedin.com/in/daniel-langhi-3553a512/ (catálogo).

Otros canales: formulario https://www.puntonet.tech/ (formulario de contacto); WhatsApp — (sin WhatsApp publicado: revisados home y contacto del sitio y el catálogo, 7-oct-2026); redes https://www.instagram.com/puntonettech ; https://twitter.com/puntonettech.

Para:

```
edutra@puntonet.tech
```

Asunto:

```
Voz y telefonía para los agentes de IA de Puntonet Tech
```

Texto:

```
Hola Enrique, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Puntonet ya vende asistentes virtuales con IA y RPA para procesos críticos, y tiene un producto para salud: el teléfono es el canal que falta para que esos asistentes atiendan y llamen.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=puntonet

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (291 caracteres):

```
Hola Enrique, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Puntonet Tech. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Enrique, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Puntonet ya vende asistentes virtuales con IA y RPA para procesos críticos, y tiene un producto para salud: el teléfono es el canal que falta para que esos asistentes atiendan y llamen.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=puntonet

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S36. BIT S.A.

- Contacto 174 de `seguimiento.md`
- Rubro: Software y agentes de IA para agro, logística y empresas (Agrobit, SAP Agro, Admis ERP), Villa María (Córdoba) (Argentina)
- Web: https://www.bit.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende agentes de IA que operan sobre el ERP de 140 empresas; la voz telefónica entra como un canal más de esos agentes.
- Gancho: Solución 'Agentes IA': 'Tu agente agro inteligente... para analizar, decidir y ejecutar procesos en tiempo real, directamente sobre tus sistemas' (sitio, /agentes-ia.html); 46 años, 140 empresas operando sus soluciones, 14 mil usuarios, +20 países y +20 partners (sitio); 101-200 empleados, cliente BrasilAgro (catálogo del Córdoba Cluster).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | bit@bit.com.ar | atención | casilla general (único email publicado; el sitio solo tiene formulario de HubSpot) | https://catalogo.cordobacluster.com/nuestros-socios (catálogo público de socios del Córdoba Technology Cluster, ficha de la empresa; visto el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: El sitio no publica nombres.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/bit-s-a/; persona —.

Otros canales: formulario https://www.bit.com.ar/contacto.html; WhatsApp — (sin WhatsApp publicado: revisados home, contacto, sobre-nosotros y agentes-ia del sitio y el catálogo, 7-oct-2026); redes https://www.instagram.com/bit__.

Para:

```
bit@bit.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de BIT S.A.
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

BIT ya vende agentes de IA que operan sobre el ERP y los sistemas de sus 140 clientes: un agente de voz integrado por API les sumaría atención y llamadas con número propio.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=bit

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (278 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como BIT S.A.. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

BIT ya vende agentes de IA que operan sobre el ERP y los sistemas de sus 140 clientes: un agente de voz integrado por API les sumaría atención y llamadas con número propio.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=bit

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S37. AYI Group (BADI S.A.)

- Contacto 175 de `seguimiento.md`
- Rubro: Servicios IT: desarrollo, integración, servicios gestionados, Data & AI y AI Engineering, Córdoba capital (Antonio del Viso 658, Alta Córdoba) (Argentina)
- Web: https://ayi.group
- Tipo: posible aliado (canal)
- Por qué encaja: Integrador grande con práctica de IA y clientes en salud, seguros y gobierno; puede revender o integrar la voz telefónica.
- Gancho: 'AI Engineering: diseñamos e implementamos soluciones de inteligencia artificial para generar impacto medible'; ofrece '50 horas de consultoría gratuitas' y tiene página 'Nuestros Vendors' (sitio). 225 personas, fundada en 2000, industrias salud, gobierno, seguros, financieras; CEO Carlos Ayi (ficha Next from Argentina).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | hi@ayi.group | atención | casilla general (ficha; también en /hablemos del sitio, data-cfemail decodificado) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/ayi-group (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Carlos Ayi, CEO (ficha); Germán Gazzoni (LinkedIn enlazado en la ficha).

Teléfonos: +54 9 351 471-1900 ; +54 9 3518 92-5460 (sitio, /hablemos).

LinkedIn: empresa https://www.linkedin.com/company/ayigroup; persona CEO: https://www.linkedin.com/in/carlos-ayi-2531b96/ ; https://www.linkedin.com/in/gazzoni/ (ficha).

Otros canales: formulario https://ayi.group/hablemos/; WhatsApp — (sin WhatsApp publicado: revisados home y /hablemos del sitio y la ficha de Cancillería, 7-oct-2026); redes https://www.instagram.com/ayi.group.

Para:

```
hi@ayi.group
```

Asunto:

```
Voz y telefonía para los agentes de IA de AYI Group
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

AYI Group ya hace ingeniería de IA para salud, seguros y gobierno: la atención y las llamadas de esos clientes pueden salir de un agente de voz integrado a lo que ya construyen.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=ayi

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (279 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como AYI Group. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

AYI Group ya hace ingeniería de IA para salud, seguros y gobierno: la atención y las llamadas de esos clientes pueden salir de un agente de voz integrado a lo que ya construyen.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=ayi

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S38. Peperina Software

- Contacto 176 de `seguimiento.md`
- Rubro: Modernización de sistemas críticos con agentes de IA (GovTech y empresas), Córdoba capital (Argentina)
- Web: https://peperina.io
- Tipo: posible aliado (canal)
- Por qué encaja: Ya construye agentes de IA sobre sistemas de empresas y gobiernos; la voz telefónica es un canal que puede integrar a esos agentes.
- Gancho: 'Moderniza tus aplicaciones, con agentes de IA confiables: modernizamos sistemas complejos, diseñando y construyendo agentes de inteligencia artificial que garantizan estabilidad, rendimiento y resultados a escala empresarial' (sitio). 15 personas, fundada en 2021, 'Agentic-Driven Modernization for Complex Systems' (ficha Next from Argentina).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | sergio.maurenzi@peperina.io | persona | Sergio Antonio Maurenzi, contacto de la ficha (LinkedIn in/sergiomaurenzi; cargo no publicado) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/peperina-software (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada. Sin email: Lucila Maurenzi (LinkedIn enlazado en la ficha). El sitio no publica emails (formulario).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/peperinasoftware/; persona https://www.linkedin.com/in/sergiomaurenzi/ (ficha).

Otros canales: formulario https://peperina.io/contacto; WhatsApp — (sin WhatsApp publicado: revisados home, quienes-somos y contacto del sitio y la ficha, 7-oct-2026); redes —.

Para:

```
sergio.maurenzi@peperina.io
```

Asunto:

```
Voz y telefonía para los agentes de IA de Peperina Software
```

Texto:

```
Hola Sergio, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Peperina ya construye agentes de IA sobre sistemas críticos de empresas y gobiernos: con nosotros esos agentes pueden además atender y hacer llamadas, con número incluido.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=peperina

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (294 caracteres):

```
Hola Sergio, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Peperina Software. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Sergio, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Peperina ya construye agentes de IA sobre sistemas críticos de empresas y gobiernos: con nosotros esos agentes pueden además atender y hacer llamadas, con número incluido.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=peperina

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S39. Skater Elephant (Resolution 8 Software SAS)

- Contacto 177 de `seguimiento.md`
- Rubro: Consultora de IA: AI Discovery, agentes de IA y transformación IA first, Córdoba capital (Argentina)
- Web: https://skaterelephant.com/es
- Tipo: posible aliado (canal)
- Por qué encaja: Ya diseña agentes de IA para clientes de muchos rubros; puede sumar el canal de voz telefónica.
- Gancho: 'Agentes de IA: diseñamos agentes que trabajan con tus datos y sistemas para resolver tareas, coordinar acciones y asistir a tus equipos'; servicios 'AI Discovery' y 'Transformación IA first' (sitio). 50 personas, fundada en 2023 (ficha Next from Argentina).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | hello@skaterelephant.com | atención | casilla general (sitio, home) | https://skaterelephant.com/es (7-oct-2026) |
|  | info@skaterelephant.com | atención | casilla general de la ficha (contacto Fabio Farchetto, cargo no publicado) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/skater-elephant (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Fabio Farchetto (contacto de la ficha); LinkedIn in/dfhirsch e in/francoberardo enlazados en la ficha.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/skaterelephant; persona https://www.linkedin.com/in/dfhirsch/ ; https://www.linkedin.com/in/francoberardo/ (ficha).

Otros canales: formulario https://skaterelephant.com/es (botón 'Hablemos'); WhatsApp — (sin WhatsApp publicado: revisados home del sitio y la ficha, 7-oct-2026); redes https://www.instagram.com/skater.elephant.

Para:

```
hello@skaterelephant.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Skater Elephant
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Skater Elephant ya diseña agentes de IA que operan sobre los datos y sistemas de sus clientes: el teléfono es el canal que falta para que esos agentes atiendan y llamen.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=skaterelephant

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (285 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Skater Elephant. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Skater Elephant ya diseña agentes de IA que operan sobre los datos y sistemas de sus clientes: el teléfono es el canal que falta para que esos agentes atiendan y llamen.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=skaterelephant

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S40. Digital Motus

- Contacto 178 de `seguimiento.md`
- Rubro: Software a medida, nube y DevOps; plataforma inmobiliaria FluIA con agente de IA en WhatsApp, Río Ceballos (Córdoba); también EE. UU. (Argentina)
- Web: https://www.digitalmotus.io/es
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende un agente de IA por WhatsApp a inmobiliarias; el teléfono es el canal que le falta y sale del mismo agente.
- Gancho: 'Desarrollamos FluIA, una plataforma de gestión inmobiliaria con Inteligencia Artificial... cuenta con un agente IA en tu WhatsApp para brindar información sobre propiedades y tomar reclamos 24/7' (catálogo del Córdoba Cluster); 15 personas, fundada en 2017, base en Argentina y EE. UU. (ficha Next from Argentina). Era reserva de la tanda anterior; ahora con el email del CEO.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | ignacio.lozita@digitalmotus.io | persona | Ignacio Lozita, CEO | https://catalogo.cordobacluster.com/nuestros-socios (catálogo público de socios del Córdoba Technology Cluster, ficha de la empresa; visto el 7-oct-2026) |
|  | jose.maria@digitalmotus.io | persona | José María Infanzón, CTO | https://catalogo.cordobacluster.com/nuestros-socios (catálogo público de socios del Córdoba Technology Cluster, ficha de la empresa; visto el 7-oct-2026) |
|  | candelaria.maspero@digitalmotus.io | persona | Candelaria Máspero Castro, CPO | https://catalogo.cordobacluster.com/nuestros-socios (catálogo público de socios del Córdoba Technology Cluster, ficha de la empresa; visto el 7-oct-2026) |
|  | carolina.baravalle@digitalmotus.io | persona | contacto del catálogo (nombre Carolina Baravalle según la casilla; cargo no publicado) | https://catalogo.cordobacluster.com/nuestros-socios (catálogo público de socios del Córdoba Technology Cluster, ficha de la empresa; visto el 7-oct-2026) |
|  | contact@digitalmotus.io | atención | casilla general (ficha y catálogo) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/digital-motus (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/digital-motus/; persona https://www.linkedin.com/in/ignaciolozita/ (catálogo y ficha).

Otros canales: formulario https://www.digitalmotus.io/es (formulario); WhatsApp +54 9 351 591-4862: botón de WhatsApp del sitio (wa.me/5493515914862, 7-oct-2026); redes https://www.instagram.com/digitalmotus.

Para:

```
ignacio.lozita@digitalmotus.io
```

Asunto:

```
Voz y telefonía para los agentes de IA de Digital Motus
```

Texto:

```
Hola Ignacio, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

FluIA ya atiende consultas y reclamos de inmobiliarias por WhatsApp con un agente de IA: el teléfono es el canal que le falta, y con nosotros sale del mismo agente, con número incluido.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=digitalmotus

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (291 caracteres):

```
Hola Ignacio, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Digital Motus. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Ignacio, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

FluIA ya atiende consultas y reclamos de inmobiliarias por WhatsApp con un agente de IA: el teléfono es el canal que le falta, y con nosotros sale del mismo agente, con número incluido.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=digitalmotus

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S41. Vippinn

- Contacto 179 de `seguimiento.md`
- Rubro: Partner Gold de Odoo y servicios SAP, software a medida e IA en procesos de negocio, Córdoba capital (sedes en Chile y España) (Argentina)
- Web: https://www.vippinn.com
- Tipo: posible aliado (canal)
- Por qué encaja: Ya lleva agentes y asistentes de IA adentro de Odoo y SAP de sus clientes; la voz telefónica es un módulo más para esos ERP.
- Gancho: 'Inteligencia artificial en Vippinn: transversal a todo lo que hacemos', con 'Agentes y asistentes: responden con el contexto real de tu negocio y operan sobre tus datos' e 'IA sobre tu ERP: adentro de Odoo y SAP'; +50 clientes en LATAM y Europa, 3 certificaciones ISO, Gold Partner de Odoo (sitio); clientes Coca-Cola, Telefónica y Bancor (catálogo del Córdoba Cluster); 101-200 empleados.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | dcarrizo@vippinn.com | persona | Daniel Carrizo, Business Developer ('Tu contacto', home del sitio) | https://www.vippinn.com/ (7-oct-2026) |
|  | hola@vippinn.com | atención | casilla general (sitio y catálogo) | https://catalogo.cordobacluster.com/nuestros-socios (catálogo público de socios del Córdoba Technology Cluster, ficha de la empresa; visto el 7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: +54 351 809-4455 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/vippinn; persona —.

Otros canales: formulario https://www.vippinn.com/ ('Agendá una call'); WhatsApp +54 9 351 809-4455: botón del sitio (wa.me/5493518094455, home y página de partners, 7-oct-2026); redes https://www.instagram.com/vippinn.ok.

Para:

```
dcarrizo@vippinn.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Vippinn
```

Texto:

```
Hola Daniel, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Vippinn ya lleva agentes y asistentes de IA adentro de Odoo y SAP de sus clientes: el teléfono es el canal que falta para que esos asistentes atiendan y llamen.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=vippinn

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (284 caracteres):

```
Hola Daniel, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Vippinn. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Daniel, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Vippinn ya lleva agentes y asistentes de IA adentro de Odoo y SAP de sus clientes: el teléfono es el canal que falta para que esos asistentes atiendan y llamen.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=vippinn

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S42. Ascentio Technologies

- Contacto 180 de `seguimiento.md`
- Rubro: Ingeniería de sistemas: espacio, software y hardware, comunicaciones unificadas sobre VoIP, IA, Córdoba capital y Río Cuarto (Córdoba); oficina en Gran Canaria (Argentina)
- Web: https://www.ascentio.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Ya instala comunicaciones unificadas sobre VoIP en organismos; un agente de voz telefónico encaja en esas mismas centrales.
- Gancho: Según el catálogo del Córdoba Cluster, hace 'Soluciones de Comunicaciones Unificadas sobre VoIP', robótica e 'inteligencia artificial', además de ingeniería espacial para CONAE (SAC-D, SAOCOM 1A y 1B, SABIA-Mar) y OHB Italia; 18 años, cliente Prefectura Naval Argentina (sitio); 21-50 empleados, fundada en 2008.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | manderson@ascentio.com.ar | persona | María Lucila Anderson, CPO (también es el email de contacto de la ficha del catálogo) | https://catalogo.cordobacluster.com/nuestros-socios (catálogo público de socios del Córdoba Technology Cluster, ficha de la empresa; visto el 7-oct-2026) |
|  | contacto@ascentio.com.ar | atención | casilla general (sitio, home) | https://www.ascentio.com.ar/ (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: +54 9 358 402-3515 (sitio); 03543 409100 (catálogo).

LinkedIn: empresa https://www.linkedin.com/company/ascentio/; persona https://www.linkedin.com/in/mar%C3%ADa-lucila-anderson-20393862/ (catálogo).

Otros canales: formulario https://www.ascentio.com.ar/ (formulario); WhatsApp — (sin WhatsApp publicado: revisados home del sitio y el catálogo, 7-oct-2026); redes https://www.instagram.com/ascentio.technologies.

Para:

```
manderson@ascentio.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Ascentio Technologies
```

Texto:

```
Hola María Lucila, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Ascentio ya instala comunicaciones unificadas sobre VoIP y aplica IA en organismos públicos: un agente de voz con telefonía incluida encaja en esas mismas centrales.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=ascentio

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (291 caracteres):

```
Hola María Lucila, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Ascentio. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola María Lucila, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Ascentio ya instala comunicaciones unificadas sobre VoIP y aplica IA en organismos públicos: un agente de voz con telefonía incluida encaja en esas mismas centrales.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=ascentio

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S43. HMM Global (Home Medical Management)

- Contacto 181 de `seguimiento.md`
- Rubro: Software vertical: gestión de salud domiciliaria para financiadores, aseguradoras y prestadores, con IA generativa, Córdoba capital (también Madrid y Panamá) (Argentina)
- Web: https://hmmglobal.com
- Tipo: posible aliado (canal)
- Por qué encaja: Software vertical de salud domiciliaria: coordinar y confirmar visitas y atender pacientes pasa por el teléfono; canal a financiadores y prestadores.
- Gancho: 'Software para la gestión de salud domiciliaria' que integra pacientes, familias, financiadores, aseguradoras y profesionales, con 'Visitas médicas agendadas' como métrica de la home; 'Integramos Inteligencia Artificial Generativa, Big Data e Internet de los dispositivos médicos' (catálogo del Córdoba Cluster); clientes OMINT, AXA España, Panamá y Colombia (catálogo); 21-50 empleados, fundada en 2019.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | dgerosa@hmmglobal.com | persona | Diego Gerosa, CEO | https://catalogo.cordobacluster.com/nuestros-socios (catálogo público de socios del Córdoba Technology Cluster, ficha de la empresa; visto el 7-oct-2026) |
|  | dpicatto@hmmglobal.com | persona | Diego Picatto, CPO | https://catalogo.cordobacluster.com/nuestros-socios (catálogo público de socios del Córdoba Technology Cluster, ficha de la empresa; visto el 7-oct-2026) |
|  | jpaba@hmmglobal.com | persona | Jorge Paba, CPO (SVP Business Development en su LinkedIn) | https://catalogo.cordobacluster.com/nuestros-socios (catálogo público de socios del Córdoba Technology Cluster, ficha de la empresa; visto el 7-oct-2026) |
|  | jhellin@hmmglobal.com | persona | Juan José Hellín Callejo, CPO | https://catalogo.cordobacluster.com/nuestros-socios (catálogo público de socios del Córdoba Technology Cluster, ficha de la empresa; visto el 7-oct-2026) |
|  | info@hmmglobal.com | atención | casilla general (sitio y catálogo) | https://hmmglobal.com/contacto/ (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/hmm-global/; persona https://www.linkedin.com/in/diego-gerosa-39a08815/ (catálogo).

Otros canales: formulario https://hmmglobal.com/contacto/; WhatsApp — (sin WhatsApp publicado: revisados home y contacto del sitio y el catálogo, 7-oct-2026); redes https://www.instagram.com/hmmglobal.

Para:

```
dgerosa@hmmglobal.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de HMM Global
```

Texto:

```
Hola Diego, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

HMM ya gestiona las visitas médicas domiciliarias de financiadores como OMINT y AXA: confirmar y coordinar esas visitas por teléfono puede hacerlo un agente de voz integrado a su plataforma.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=hmm

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (286 caracteres):

```
Hola Diego, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como HMM Global. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Diego, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

HMM ya gestiona las visitas médicas domiciliarias de financiadores como OMINT y AXA: confirmar y coordinar esas visitas por teléfono puede hacerlo un agente de voz integrado a su plataforma.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=hmm

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S44. Asofix (Grupo Tagle)

- Contacto 182 de `seguimiento.md`
- Rubro: Software vertical SaaS con IA para la gestión comercial de concesionarios, fabricantes y agencias de usados, Córdoba capital (Argentina)
- Web: https://www.asofix.com
- Tipo: posible aliado (canal)
- Por qué encaja: Software vertical para concesionarios, que atienden consultas, confirman turnos de taller y hacen seguimiento por teléfono; canal al rubro.
- Gancho: 'A través de plataformas propias basadas en modelos SaaS, datos estratégicos e inteligencia artificial, impulsa la transformación digital de fabricantes, distribuidores, concesionarios y agentes en Latinoamérica' (catálogo del Córdoba Cluster); clientes M. Tagle (H) y Cía. y Motcor (catálogo); 'la plataforma donde vive todo el proceso comercial, desde la primera consulta hasta el cierre y la posventa' (sitio). Fundada en 2019, 0-20 empleados.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | pablo.leoni@grupotagle.com.ar | persona | Pablo Leoni, contacto de la ficha del catálogo (cargo no publicado; casilla de Grupo Tagle, dueño de Asofix) | https://catalogo.cordobacluster.com/nuestros-socios (catálogo público de socios del Córdoba Technology Cluster, ficha de la empresa; visto el 7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada. Sin email: El sitio no publica emails (formulario y WhatsApp).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/asofix/; persona —.

Otros canales: formulario https://www.asofix.com/contacto; WhatsApp +54 351 345-5100: botón del sitio (api.whatsapp.com/send/?phone=3513455100, home y contacto, 7-oct-2026); redes https://www.instagram.com/asofix.software.

Para:

```
pablo.leoni@grupotagle.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Asofix
```

Texto:

```
Hola Pablo, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Asofix ya es la plataforma comercial de concesionarios como Tagle y Motcor: el teléfono es el canal que falta para que esos concesionarios atiendan consultas y confirmen turnos con un agente de voz integrado.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=asofix

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (282 caracteres):

```
Hola Pablo, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Asofix. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Pablo, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Asofix ya es la plataforma comercial de concesionarios como Tagle y Motcor: el teléfono es el canal que falta para que esos concesionarios atiendan consultas y confirmen turnos con un agente de voz integrado.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=asofix

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S45. Syloper

- Contacto 183 de `seguimiento.md`
- Rubro: Software factory: apps, plataformas web, e-commerce y sistemas de gestión con IA, Rosario (Santa Fe) (Argentina)
- Web: https://www.syloper.com
- Tipo: posible aliado (canal)
- Por qué encaja: Software factory con IA y clientes en salud, gobierno y financieras; puede integrar la voz telefónica en lo que construye.
- Gancho: Software factory con 15 años que 'impulsa la transformación digital de empresas y organizaciones mediante metodologías ágiles e inteligencia artificial'; 28 personas, fundada en 2009; industrias salud, hospitales, gobierno, servicios públicos, financieras (ficha Next from Argentina). Socia del Polo Tecnológico Rosario. El sitio bloquea rastreadores ('Checking search engine crawler', 403): todo sale de la ficha. Puede estar también en la lista del agente de Buenos Aires (figuraba en su lote de dominios).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | agustin@syloper.com | persona | Agustín Garassino, contacto de la ficha (LinkedIn in/agarassino; cargo no publicado) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/syloper (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada. Sin email: Julián Butti (LinkedIn enlazado en la ficha).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/syloper/; persona https://www.linkedin.com/in/agarassino/ (ficha).

Otros canales: formulario https://www.syloper.com (no recorrido: el sitio bloquea rastreadores); WhatsApp — (sitio no recorrido por bloqueo a rastreadores; la ficha de Cancillería no publica WhatsApp, 7-oct-2026); redes —.

Para:

```
agustin@syloper.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Syloper
```

Texto:

```
Hola Agustín, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Syloper ya integra IA en los sistemas que hace para hospitales, gobiernos y financieras: la atención y las llamadas de esos clientes pueden salir de un agente de voz integrado por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=syloper

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (285 caracteres):

```
Hola Agustín, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Syloper. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Agustín, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Syloper ya integra IA en los sistemas que hace para hospitales, gobiernos y financieras: la atención y las llamadas de esos clientes pueden salir de un agente de voz integrado por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=syloper

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S46. Santa Fe Sistemas (Grupo SFS)

- Contacto 184 de `seguimiento.md`
- Rubro: Software vertical de salud: sistema hospitalario HealthCare (turnos, pacientes, facturación), HealthTrack y Care AI, Santa Fe capital (Argentina)
- Web: https://www.sfs.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Software vertical de salud con IA: sus clínicas confirman turnos y atienden pacientes por teléfono; canal al rubro.
- Gancho: 'Software Médico y Sistema Hospitalario en Argentina': HealthCare ('turnos, pacientes, evoluciones y facturación organizados en un único sistema'), HealthTrack y 'Care AI te ayuda a resumir historias clínicas' (sitio); 51 personas, fundada en 2019, clientes hospitales, clínicas y aseguradoras (ficha Next from Argentina).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | comercial@sfs.com.ar | área | comercial (email de contacto de la ficha; contacto Gustavo Andrés Lavatiatta, LinkedIn in/gustavo-lavatiatta, cargo no publicado) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/santa-fe-sistemas (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |
|  | info@sfs.com.ar | atención | casilla general (sitio) | https://www.sfs.com.ar/ (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/santafesistemas; persona https://www.linkedin.com/in/gustavo-lavatiatta-8a047235/ (ficha).

Otros canales: formulario https://www.sfs.com.ar/ ('Solicitar Presentación'); WhatsApp +54 9 342 479-0990: botón del sitio (wa.me/5493424790990, 7-oct-2026); redes https://www.instagram.com/santafesistemas.

Para:

```
comercial@sfs.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Santa Fe Sistemas
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

SFS ya gestiona turnos y pacientes de hospitales y clínicas, con Care AI adentro: confirmar turnos y atender llamadas puede hacerlo un agente de voz integrado a HealthCare.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=sfs

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (287 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Santa Fe Sistemas. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

SFS ya gestiona turnos y pacientes de hospitales y clínicas, con Care AI adentro: confirmar turnos y atender llamadas puede hacerlo un agente de voz integrado a HealthCare.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=sfs

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S47. EximIA Solutions (Technology Service SAS)

- Contacto 185 de `seguimiento.md`
- Rubro: Automatización con RPA, agentes de IA y machine learning para bancos, utilities, salud y retail, Rosario (Santa Fe) (Argentina)
- Web: https://eximia.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende agentes de IA y RPA a bancos, utilities y salud; le falta la voz telefónica.
- Gancho: 'Integramos RPA, agentes de IA, Ingeniería de datos y Machine Learning para optimizar operaciones'; sectores bancos, petroquímicas, siderúrgicas, farmacéuticas, retail, utilities y salud; producto LexIA (sitio). 'Servicios de IA + RPA', socia del Polo Tecnológico Rosario desde mar-2026 (ficha del Polo).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@eximia.ar | atención | casilla general (sitio y ficha del Polo) | https://polotecnologico.net/eximia-solutions-2/ (ficha de socio del Polo Tecnológico Rosario, Cloudflare data-cfemail decodificado; vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: El sitio no publica nombres.

Teléfonos: +54 9 3417 20-3719 (sitio y Polo).

LinkedIn: empresa — (no publicado en el sitio); persona —.

Otros canales: formulario https://eximia.ar/ ('Envianos un mensaje'); WhatsApp — (sin WhatsApp publicado: revisados home del sitio y la ficha del Polo, 7-oct-2026); redes —.

Para:

```
info@eximia.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de EximIA Solutions
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

EximIA ya vende agentes de IA y RPA a bancos, utilities y salud: el teléfono es el canal que falta para que esos agentes atiendan y llamen.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=eximia

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (286 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como EximIA Solutions. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

EximIA ya vende agentes de IA y RPA a bancos, utilities y salud: el teléfono es el canal que falta para que esos agentes atiendan y llamen.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=eximia

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S48. Human Tech 4.0 (Business Buggers SRL)

- Contacto 186 de `seguimiento.md`
- Rubro: Consultoría tecnológica, talento y capacitación para industria 4.0, con IA aplicada y consorcios de innovación, Rosario (Santa Fe), Lamadrid 470 (Polo Tecnológico) (Argentina)
- Web: https://www.humantech40.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Arma proyectos de IA para industrias de Rosario; un agente de voz con telefonía es una pieza más para esos proyectos.
- Gancho: 'Consultoría · Talento · Tecnología · Capacitación para organizaciones que apuestan por la industria 4.0'; arma 'consorcios privados para acceder a los nuevos subsidios de IA' y trabaja junto a Colloquia en IoT e IA; especialista en IA aplicada Flavio Spetale (sitio). Socia del Polo Tecnológico Rosario desde nov-2025.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | pablo.crembil@humantech40.com.ar | persona | Pablo Crembil, COO y cofundador (cargo en el sitio). La ficha del Polo muestra la casilla ofuscada seguida de '. ar'; humantech40.com no tiene MX y humantech40.com.ar sí | https://polotecnologico.net/human-tech-4-0-2/ (ficha de socio del Polo Tecnológico Rosario, Cloudflare data-cfemail decodificado; vista el 7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada. Sin email: Victoria Passadore, cofundadora; Flavio Spetale, Tech Specialist IA; Paolo Cacchiarelli (sitio, LinkedIn enlazados).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/humantech40; persona https://www.linkedin.com/in/pablocrembil/ (sitio).

Otros canales: formulario https://www.humantech40.com.ar/ ('Escribinos'); WhatsApp +54 9 11 5853-3333: botón 'Hola Human Tech 4.0' del sitio (wa.me/5491158533333, 7-oct-2026); +54 9 341 682-7800 solo para CVs; redes —.

Para:

```
pablo.crembil@humantech40.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Human Tech 4.0
```

Texto:

```
Hola Pablo, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Human Tech 4.0 ya arma proyectos de IA y consorcios con industrias de Rosario: un agente de voz con telefonía incluida es una pieza más para esos proyectos.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=humantech

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (290 caracteres):

```
Hola Pablo, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Human Tech 4.0. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Pablo, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Human Tech 4.0 ya arma proyectos de IA y consorcios con industrias de Rosario: un agente de voz con telefonía incluida es una pieza más para esos proyectos.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=humantech

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S49. Autologica

- Contacto 187 de `seguimiento.md`
- Rubro: Software vertical: DMS con IA (Autologica Sky DMS) para concesionarios de vehículos y maquinaria, Rosario (Santa Fe) (Argentina)
- Web: https://www.autologica.com/es
- Tipo: posible aliado (canal)
- Por qué encaja: Software vertical con IA para concesionarias (ventas, taller, repuestos), que confirman turnos y hacen seguimiento por teléfono; canal al rubro con programa de partners.
- Gancho: 'DMS.IA nativo para concesionarios de vehículos', suite de IA 'AVA', webinar 'Concesionarios e IA: Insights de la Primera Encuesta Regional sobre IA' y 'Red de Partners Autologica' con consultores; 30 años (sitio); 80 personas, CEO Alfredo McClymont (ficha Next from Argentina). Era reserva de la tanda anterior ('otra tanda').

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@autologica.com | atención | casilla general (sitio y ficha) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/autologica (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Alfredo McClymont, CEO; Sandra Calligaro (LinkedIn enlazados en la ficha).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/autologica/; persona CEO: https://www.linkedin.com/in/almcclymont/ (ficha).

Otros canales: formulario https://www.autologica.com/es/contacto/; WhatsApp — (sin WhatsApp publicado: revisados home, contacto, sobre-nosotros y red de partners del sitio y la ficha, 7-oct-2026); redes https://www.instagram.com/autologicadms.

Para:

```
info@autologica.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Autologica
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Autologica ya pone IA en el DMS de concesionarias de toda la región: el teléfono es el canal que falta para que esas concesionarias confirmen turnos de taller y atiendan consultas con un agente integrado al DMS.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=autologica

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (280 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Autologica. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Autologica ya pone IA en el DMS de concesionarias de toda la región: el teléfono es el canal que falta para que esas concesionarias confirmen turnos de taller y atiendan consultas con un agente integrado al DMS.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=autologica

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S50. Kodear

- Contacto 188 de `seguimiento.md`
- Rubro: Desarrollo de soluciones digitales a medida, automatización y e-commerce, Rosario (Santa Fe) (Argentina)
- Web: https://kodear.dev
- Tipo: posible aliado (canal)
- Por qué encaja: Automatiza la operación de comercios y servicios con software a medida; puede integrar la atención telefónica de esos clientes.
- Gancho: 'Somos socios tecnológicos estratégicos de nuestros clientes'; soluciones digitales a medida con proceso certificado (sitio); 10 personas, fundada en 2016, industrias retail, farmacias, laboratorios, hoteles, supermercados (ficha Next from Argentina, dominio kodear.net).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | dgiovanon@kodear.net | persona | German David Giovanon, contacto de la ficha (LinkedIn in/david-giovanon-kodear; cargo no publicado) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/kodear (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |
|  | info@kodear.dev | atención | casilla general (sitio, /contacto, data-cfemail decodificado) | https://kodear.dev/contacto (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: +54 9 341 563-4579 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/kodear/; persona https://www.linkedin.com/in/david-giovanon-kodear/ (ficha).

Otros canales: formulario https://kodear.dev/contacto; WhatsApp +54 9 11 7143-9021: botón del sitio (wa.me/5491171439021, home, nosotros y contacto, 7-oct-2026); redes https://www.instagram.com/kodear.dev.

Para:

```
dgiovanon@kodear.net
```

Asunto:

```
Voz y telefonía para los agentes de IA de Kodear
```

Texto:

```
Hola David, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Kodear ya automatiza la operación de comercios, farmacias y hoteles con software a medida: la atención telefónica de esos clientes puede salir de un agente de voz integrado por API.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=kodear

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (282 caracteres):

```
Hola David, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Kodear. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola David, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Kodear ya automatiza la operación de comercios, farmacias y hoteles con software a medida: la atención telefónica de esos clientes puede salir de un agente de voz integrado por API.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=kodear

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S51. Efficast

- Contacto 189 de `seguimiento.md`
- Rubro: Plataforma industrial IoT con agentes de IA (monitoreo de planta, reportes, supervisor de IA en WhatsApp), Rosario (Santa Fe) (Argentina)
- Web: https://efficast.ai
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende agentes de IA a fábricas y los pone en WhatsApp; la voz telefónica (avisos y consultas) completa el producto. Es producto, no integrador: encaje parcial.
- Gancho: 'Tu empleado de IA industrial 24/7'; módulo 'Agentes AI' que 'arman reportes, cierran OTs, avisan cuellos de botella' y 'Tu supervisor de IA en WhatsApp: te avisa, te escribe el cierre de turno y contesta a las 3 AM' (sitio); 12 personas, fundada en 2023, contacto Simón Carpman (ficha Next from Argentina).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | simon@efficast.ai | persona | Simón Carpman, contacto de la ficha (LinkedIn in/simoncarpman; cargo no publicado) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/efficast-ia (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |
|  | info@efficast.ai | atención | casilla general (sitio) | https://efficast.ai/ (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/efficast; persona https://www.linkedin.com/in/simoncarpman/ (ficha).

Otros canales: formulario https://efficast.ai/ ('Contactá un asesor'); WhatsApp +54 9 341 655-5097: botón del sitio (wa.me/5493416555097; también números de Uruguay, Paraguay y EE. UU., 7-oct-2026); redes —.

Para:

```
simon@efficast.ai
```

Asunto:

```
Voz y telefonía para los agentes de IA de Efficast
```

Texto:

```
Hola Simón, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Efficast ya tiene un supervisor de IA que avisa por WhatsApp lo que pasa en la planta: por teléfono, con voces argentinas y número incluido, ese mismo agente puede llamar y atender.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=efficast

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (284 caracteres):

```
Hola Simón, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Efficast. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Simón, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Efficast ya tiene un supervisor de IA que avisa por WhatsApp lo que pasa en la planta: por teléfono, con voces argentinas y número incluido, ese mismo agente puede llamar y atender.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=efficast

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S52. Nonlinear Tecnología

- Contacto 190 de `seguimiento.md`
- Rubro: Optimización de cadenas de suministro, logística de última milla y analítica predictiva, Santa Fe capital (Argentina)
- Web: https://nonlinear.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Optimiza con datos la logística de sus clientes; avisar entregas y atender consultas por teléfono puede integrarse a esas plataformas. Encaje parcial (poca IA conversacional).
- Gancho: Soluciones de 'cadenas de suministro', 'logística de última milla', 'transporte público' y 'analítica de datos y predicción' para oil & gas, manufactura, logística y gobierno (sitio); 13 personas, fundada en 2021, contacto Agustín Montagna (ficha Next from Argentina).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | contacto@nonlinear.com.ar | atención | casilla general (sitio y ficha; contacto de la ficha Agustín Montagna, LinkedIn in/agumontagna) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/nonlinear-tecnologia (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/nonlinear-tecnologia; persona https://www.linkedin.com/in/agumontagna/ (ficha).

Otros canales: formulario https://nonlinear.com.ar/contacto/; WhatsApp +54 9 342 487-6180: botón del sitio (wa.me/5493424876180, 7-oct-2026); redes —.

Para:

```
contacto@nonlinear.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Nonlinear Tecnología
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Nonlinear ya optimiza con datos la logística y la última milla de sus clientes: avisar entregas y atender consultas por teléfono puede hacerlo un agente de voz integrado a esas plataformas.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=nonlinear

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (290 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Nonlinear Tecnología. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Nonlinear ya optimiza con datos la logística y la última milla de sus clientes: avisar entregas y atender consultas por teléfono puede hacerlo un agente de voz integrado a esas plataformas.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=nonlinear

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S53. Datawise

- Contacto 191 de `seguimiento.md`
- Rubro: Servicios IT: inteligencia artificial, nube, seguridad e infraestructura, Rosario (Lamadrid 470, Polo Tecnológico) y CABA: sede principal no clara (Argentina)
- Web: https://datawise.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Ofrece IA e infraestructura a sus clientes; un agente de voz con telefonía incluida es un servicio más sobre esa base.
- Gancho: Servicios de 'Inteligencia artificial: modelos avanzados, datos confiables y especialistas en IA', nube, seguridad y 'pago por uso' (sitio); socia del Polo Tecnológico Rosario desde oct-2025, contacto Diego García (ficha del Polo). El sitio lista primero la dirección de CABA y después la de Rosario: confirmar la sede antes de enviar (puede ser zona del otro agente).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | diego.garcia@datawise.com.ar | persona | Diego García, contacto de la ficha del Polo (cargo no publicado) | https://polotecnologico.net/datawise/ (ficha de socio del Polo Tecnológico Rosario, Cloudflare data-cfemail decodificado; vista el 7-oct-2026) |
|  | info@datawise.com.ar | atención | casilla general (sitio) | https://datawise.com.ar/contacto/ (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: +54 11 2152-6300 (sitio); 341 211-8737 (Polo).

LinkedIn: empresa https://ar.linkedin.com/company/datawise; persona —.

Otros canales: formulario https://datawise.com.ar/contacto/; WhatsApp — (sin WhatsApp publicado: revisados home, contacto y nosotros del sitio y la ficha del Polo, 7-oct-2026); redes https://www.instagram.com/datawiseit ; https://x.com/datawisesa.

Para:

```
diego.garcia@datawise.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Datawise
```

Texto:

```
Hola Diego, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Datawise ya ofrece IA e infraestructura a sus clientes: un agente de voz con telefonía incluida es un servicio más para vender sobre esa base.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=datawise

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (284 caracteres):

```
Hola Diego, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Datawise. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Diego, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Datawise ya ofrece IA e infraestructura a sus clientes: un agente de voz con telefonía incluida es un servicio más para vender sobre esa base.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=datawise

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S54. Midas Consultores

- Contacto 192 de `seguimiento.md`
- Rubro: Consultora tecnológica: software a medida, Data & AI, QA y modernización (ISO 9001), Mendoza capital (Argentina)
- Web: https://midasconsultores.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Consultora grande de Mendoza con práctica de Data & AI y clientes financieros; puede integrar o revender la voz telefónica.
- Gancho: Consultora con 18 años y 120 personas que 'diseña y construye software a medida, Data & AI, QA y modernización de aplicaciones', equipos ágiles certificados ISO 9001, clientes en LATAM, EE. UU. y Europa; industrias bancos, seguros, financieras, logística; CEO Fernando Santanciero (ficha Next from Argentina). Proyectos Vaypol, Crowdi y Peña Asociados (sitio).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | comercial@midasconsultores.com.ar | área | comercial (email de contacto de la ficha) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/midas-consultores (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |
|  | info@midasconsultores.com.ar | atención | casilla general (sitio) | https://midasconsultores.com.ar/home/ (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Fernando Santanciero, CEO; Margarita Solivellas (LinkedIn enlazados en la ficha).

Teléfonos: —.

LinkedIn: empresa https://ar.linkedin.com/company/midas-consultores; persona CEO: https://www.linkedin.com/in/fsantanciero/ (ficha).

Otros canales: formulario https://midasconsultores.com.ar/home/ (formulario); WhatsApp — (sin WhatsApp publicado: revisados home del sitio y la ficha, 7-oct-2026); redes https://www.instagram.com/midas_consultores.

Para:

```
comercial@midasconsultores.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Midas Consultores
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Midas ya hace Data & AI y software para bancos, seguros y financieras: la atención y las llamadas de esos clientes pueden salir de un agente de voz integrado por API, con la telefonía resuelta.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=midas

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (287 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Midas Consultores. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Midas ya hace Data & AI y software para bancos, seguros y financieras: la atención y las llamadas de esos clientes pueden salir de un agente de voz integrado por API, con la telefonía resuelta.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=midas

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S55. Merovingian Data

- Contacto 193 de `seguimiento.md`
- Rubro: Consultora de datos, analítica e IA (dashboards, arquitectura de datos, ML), Mendoza capital (Argentina)
- Web: https://merovingiandata.com
- Tipo: posible aliado (canal)
- Por qué encaja: Implementa IA y analítica en retail, salud y servicios públicos; la voz telefónica es un canal más para esos clientes.
- Gancho: 'Transforma tu negocio con soluciones de datos, analítica e IA'; casos de uso por sector, por rol y 'por dolor'; nació en 2020, superó las 20 personas en 2024, clientes en EE. UU., Argentina, Brasil y España (sitio); 26 personas, contacto Mario Japaz; industrias retail, hospitales, servicios públicos, financieras (ficha Next from Argentina).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | mj@merovingiandata.com | persona | Mario Japaz, contacto de la ficha (LinkedIn in/mariojapaz; cargo no publicado) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/merovingian-data (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |
|  | info@merovingiandata.com | atención | casilla general (sitio, /contacto) | https://merovingiandata.com/contacto (7-oct-2026) |

★ porque es la casilla de la persona con más potencial publicada. Sin email: LinkedIn in/gtacchini e in/marcos-bruno enlazados en la ficha.

Teléfonos: +54 9 261 650-8040 (sitio).

LinkedIn: empresa https://www.linkedin.com/company/merovingiandata/; persona https://www.linkedin.com/in/mariojapaz/ (ficha).

Otros canales: formulario https://merovingiandata.com/contacto; WhatsApp +54 9 261 650-8040: botón del sitio (wa.me/5492616508040, home, nosotros y contacto, 7-oct-2026); redes https://www.instagram.com/merovingiandata.

Para:

```
mj@merovingiandata.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Merovingian Data
```

Texto:

```
Hola Mario, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Merovingian ya implementa IA y analítica en retail, salud y servicios públicos: un agente de voz con telefonía incluida les suma un canal para esos mismos clientes.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=merovingian

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (292 caracteres):

```
Hola Mario, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Merovingian Data. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola Mario, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Merovingian ya implementa IA y analítica en retail, salud y servicios públicos: un agente de voz con telefonía incluida les suma un canal para esos mismos clientes.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=merovingian

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S56. Quinto Impacto

- Contacto 194 de `seguimiento.md`
- Rubro: Transformación digital e IA: automatización, integración de sistemas e implementación de Odoo (Empresa B, ISO 9001), Luján de Cuyo (Mendoza) (Argentina)
- Web: https://quintoimpacto.net
- Tipo: posible aliado (canal)
- Por qué encaja: Implementa IA y Odoo en financieras, mineras y energéticas; la voz telefónica es un módulo más sobre ese ERP.
- Gancho: 'La IA no es magia. Es ingeniería para hacer tu negocio más eficiente. Implementamos tecnología que automatiza tareas, reduce costos'; implementa Odoo e integra sistemas; casos en servicios financieros (garantías), minería y energía; Empresa B, ISO 9001, carbono neutral (sitio); 11 personas, fundada en 2017, contacto Rafael Kemelmajer (ficha Next from Argentina).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | hola@quintoimpacto.net | atención | casilla general (sitio) | https://quintoimpacto.net/ (7-oct-2026) |
|  | info@quintoimpacto.net | atención | casilla general de la ficha (contacto Rafael Kemelmajer, cargo no publicado) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/quinto-impacto (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Rafael Kemelmajer (contacto de la ficha); Sebastián Arbona (LinkedIn enlazado en el sitio y en la ficha).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/quinto-impacto; persona https://www.linkedin.com/in/sebastianarbona (sitio); https://www.linkedin.com/in/rafakemelmajer/ (ficha).

Otros canales: formulario https://quintoimpacto.net/ (formulario); WhatsApp — (sin WhatsApp publicado: revisados home del sitio y la ficha, 7-oct-2026); redes https://www.instagram.com/quintoimpacto ; https://twitter.com/quintoimpacto.

Para:

```
hola@quintoimpacto.net
```

Asunto:

```
Voz y telefonía para los agentes de IA de Quinto Impacto
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Quinto Impacto ya implementa IA y Odoo en financieras, mineras y energéticas: el teléfono es el canal que falta para que esos clientes atiendan y llamen desde el mismo sistema.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=quintoimpacto

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (284 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Quinto Impacto. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Quinto Impacto ya implementa IA y Odoo en financieras, mineras y energéticas: el teléfono es el canal que falta para que esos clientes atiendan y llamen desde el mismo sistema.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=quintoimpacto

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S57. Axis Human (Inamika Interactive S.A.)

- Contacto 195 de `seguimiento.md`
- Rubro: Integración de IA y software a medida, Mendoza capital (Argentina)
- Web: https://axishuman.ai
- Tipo: posible aliado (canal)
- Por qué encaja: Integra IA en el software de sus clientes mendocinos; un agente de voz con telefonía es una integración más.
- Gancho: 'Integración de IA & Software a Medida: más de treinta años pensando, diseñando y desarrollando tecnología para organizaciones' (sitio, 1995-2026). Inamika 'inicia actividad en el año 2008 en la ciudad de Mendoza' (ficha de socio de CESSI, email info@axishuman.ai); figura entre las primeras compradoras de lote del Parque TIC Mendoza (prensa provincial).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@axishuman.ai | atención | casilla general (sitio y ficha de CESSI de Inamika) | https://axishuman.ai/contact (7-oct-2026); https://cessi.org.ar/socio/inamika-s-a/ (ficha de CESSI, bajada el 5-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Equipo con LinkedIn en el sitio: Bautista Ithurburu, Juan Bidondo, César Pantuso, Gustavo Riesgo, Juan Pedro Gaischuk, Lucas Pistoia, Matías Camiletti (cargos no legibles sin JavaScript).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/axis-h/; persona https://www.linkedin.com/in/gustavoriesgo/ ; https://www.linkedin.com/in/bidondojuan/ (sitio).

Otros canales: formulario https://axishuman.ai/contact; WhatsApp — (sin WhatsApp publicado: revisados home, about y contact del sitio, 7-oct-2026); redes https://www.instagram.com/axis_human.

Para:

```
info@axishuman.ai
```

Asunto:

```
Voz y telefonía para los agentes de IA de Axis Human
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Axis Human ya integra IA en el software de sus clientes: un agente de voz con telefonía incluida es una integración más para esos mismos proyectos.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=axishuman

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (280 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Axis Human. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Axis Human ya integra IA en el software de sus clientes: un agente de voz con telefonía incluida es una integración más para esos mismos proyectos.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=axishuman

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S58. Griftin (Área Clave Consultoría Estratégica SRL)

- Contacto 196 de `seguimiento.md`
- Rubro: Outsourcing IT, experiencias inmersivas y agentes de IA para WhatsApp Business (Meta Tech Provider), Yerba Buena (Tucumán) (Argentina)
- Web: https://griftin.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende agentes de IA en WhatsApp a empresas del NOA; el teléfono es el canal que le falta y sale del mismo agente.
- Gancho: 'Agente de IA para WhatsApp Business: empleados IA en WhatsApp, el nuevo cerebro operativo de tu empresa, disponible 24/7', implementado como 'Meta Tech Provider' sobre la Cloud API (agentes.griftin.com.ar); el botón de WhatsApp del sitio ya dice 'estoy interesado en Agentes IA'. 17 personas, fundada en 2021, CEO Gustavo Maigua (ficha Next from Argentina).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | contacto@griftin.com.ar | atención | casilla general (sitio y ficha) | https://www.cancilleria.gob.ar/en/new-technologies/next-from-argentina-en/griftin (ficha Next from Argentina, Cancillería; vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Gustavo Maigua, CEO; Rosana Hadad Salomón; Naum Alperovich; Giselle Medina (LinkedIn enlazados en el sitio y la ficha).

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/griftin; persona CEO: https://www.linkedin.com/in/gustavo-gabriel-maigua/ (sitio y ficha).

Otros canales: formulario https://griftin.com.ar/contacto/; WhatsApp +54 9 381 369-3980: botón del sitio con mensaje 'estoy interesado en Agentes IA y servicios tecnológicos' (wa.me/5493813693980, 7-oct-2026); redes https://www.instagram.com/griftin_it.

Para:

```
contacto@griftin.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Griftin
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Griftin ya vende empleados de IA en WhatsApp como Meta Tech Provider: el teléfono es el canal que les falta, y con nosotros sale del mismo agente, con número incluido.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=griftin

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (277 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Griftin. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Griftin ya vende empleados de IA en WhatsApp como Meta Tech Provider: el teléfono es el canal que les falta, y con nosotros sale del mismo agente, con número incluido.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=griftin

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S59. MBM Sistemas

- Contacto 197 de `seguimiento.md`
- Rubro: Software vertical para laboratorios bioquímicos (mbm Lab, en la nube, con IA), Salta capital (Maipú 546) (Argentina)
- Web: https://www.mbmsistemas.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Software vertical para laboratorios: los pacientes llaman por turnos y resultados; canal al rubro.
- Gancho: '20 años caminando junto a los profesionales bioquímicos'; lanzamiento 'mbm Lab, Gestión Inteligente en la Nube' con 'Precisión con IA' ('IA para valores normales'), envío automático de resultados por email y 'demo gratis' (sitio). Socia del Clúster Tecnológico Salta (enlace en el sitio del clúster).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | ventas@mbmsistemas.com.ar | área | ventas (sitio, pie de página) | https://www.mbmsistemas.com.ar/ (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: El sitio no publica nombres.

Teléfonos: +54 9 387 406-0585 ; 387 242-7498 (sitio).

LinkedIn: empresa — (no publicado); persona —.

Otros canales: formulario https://www.mbmsistemas.com.ar/ (formulario); WhatsApp +54 9 387 406-0585: botón del sitio (wa.me/5493874060585, 7-oct-2026); redes —.

Para:

```
ventas@mbmsistemas.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de MBM Sistemas
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

MBM ya pone IA en la gestión de laboratorios bioquímicos: atender llamadas de pacientes por turnos y resultados puede hacerlo un agente de voz integrado a mbm Lab.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=mbm

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (282 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como MBM Sistemas. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

MBM ya pone IA en la gestión de laboratorios bioquímicos: atender llamadas de pacientes por turnos y resultados puede hacerlo un agente de voz integrado a mbm Lab.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=mbm

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S60. Blackfish Argentina

- Contacto 198 de `seguimiento.md`
- Rubro: Software factory e implementadora de Odoo, Salta capital (San Luis 1460) (Argentina)
- Web: https://www.blackfish.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Implementa ERP en empresas del norte; canal para sumar voz y WhatsApp a esos clientes.
- Gancho: 'Software factory con más de 17 años de experiencia' (sitio del Clúster Tecnológico Salta, donde su CEO Luis Yoroslav es vicepresidente y su socio gerente Mario Solis, tesorero); 'Olvídate de las limitaciones de Excel y abraza... un sistema de gestión ERP como Odoo' (sitio). Sin IA visible: encaje parcial, como implementador de ERP.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@blackfish.com.ar | atención | casilla general (sitio) | https://www.blackfish.com.ar/ (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: Luis Yoroslav, CEO y fundador; Mario Solis, socio gerente (https://clustertecnologicosalta.com/, 7-oct-2026).

Teléfonos: —.

LinkedIn: empresa — (no publicado); persona —.

Otros canales: formulario https://www.blackfish.com.ar/ ('Contáctenos'); WhatsApp — (sin WhatsApp publicado: revisados home del sitio y el sitio del clúster, 7-oct-2026); redes —.

Para:

```
info@blackfish.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Blackfish Argentina
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Blackfish ya implementa Odoo en empresas del norte: un agente de voz con telefonía incluida, integrado a ese ERP, es un módulo más para vender.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=blackfish

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (289 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Blackfish Argentina. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Blackfish ya implementa Odoo en empresas del norte: un agente de voz con telefonía incluida, integrado a ese ERP, es un módulo más para vender.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=blackfish

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S61. Devoo

- Contacto 199 de `seguimiento.md`
- Rubro: Implementadora de Odoo, desarrollo web y chatbots de WhatsApp con ChatGPT, Concordia (Entre Ríos) (Argentina)
- Web: https://devoo.io
- Tipo: posible aliado (canal)
- Por qué encaja: Ya vende chatbots de WhatsApp con IA sobre Odoo a pymes; el teléfono es el canal que le falta.
- Gancho: 'Chatbot para Whatsapp: potencia tu atención al cliente con la combinación perfecta: Odoo, WhatsApp y ChatGPT'; Odoo (contabilidad, POS, e-commerce) y 'descuentos para proyectos PyME' (sitio); sede 'Entre Ríos 467, Concordia' (sitio). Socia del Clúster Tecnológico Salta (enlace en el sitio del clúster).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@devoo.io | atención | casilla general (sitio) | https://devoo.io/contactus (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención. Sin email: El sitio no publica nombres.

Teléfonos: —.

LinkedIn: empresa — (no publicado); persona —.

Otros canales: formulario https://devoo.io/contactus; WhatsApp — (sin WhatsApp publicado: revisados home y contactus del sitio, 7-oct-2026); redes —.

Para:

```
info@devoo.io
```

Asunto:

```
Voz y telefonía para los agentes de IA de Devoo
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Devoo ya vende chatbots de WhatsApp con ChatGPT sobre Odoo: el teléfono es el canal que falta, y con nosotros sale del mismo agente, con número incluido.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=devoo

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (275 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Devoo. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Devoo ya vende chatbots de WhatsApp con ChatGPT sobre Odoo: el teléfono es el canal que falta, y con nosotros sale del mismo agente, con número incluido.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=devoo

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S62. Sudata

- Contacto 200 de `seguimiento.md`
- Rubro: Consultora de BI, modelos predictivos y automatización con IA para pymes, Chaco (socia del Polo IT Chaco, Resistencia) (Argentina)
- Web: https://sudata.co
- Tipo: posible aliado (canal)
- Por qué encaja: Automatiza con IA la administración de pymes del NEA; un agente de voz con telefonía es otro servicio para esos clientes.
- Gancho: 'Tu PYME en Datos': BI, 'modelos predictivos' y automatización con IA como 'FacturasIA (lectura de facturas con IA y carga automática)' (ficha del Polo IT Chaco); página 'Partners' y 'Autodiagnóstico gratuito' (sitio).

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | contacto@sudata.co | atención | casilla general (ficha del Polo IT Chaco) | https://poloitchaco.org.ar/empresas/sudata/ (ficha del Polo IT Chaco, Cloudflare data-cfemail decodificado; vista el 7-oct-2026) |
|  | jmfernandez@sudata.co | persona | sin nombre ni cargo publicados; figura en la carpeta de Google Drive 'Equipo Sudata - CVs' enlazada desde el menú 'Equipo' del sitio | https://sudata.co/ → enlace 'Equipo' a Drive (7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: —.

LinkedIn: empresa https://www.linkedin.com/company/sudataglobal; persona —.

Otros canales: formulario https://sudata.co/ (Contacto); WhatsApp — (sin WhatsApp publicado: revisados home del sitio y la ficha del Polo, 7-oct-2026); redes https://www.instagram.com/sudata.ar.

Para:

```
contacto@sudata.co
```

Asunto:

```
Voz y telefonía para los agentes de IA de Sudata
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Sudata ya automatiza con IA la carga de facturas y los tableros de pymes del NEA: un agente de voz con telefonía incluida es otro servicio para esos mismos clientes.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=sudata

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (276 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Sudata. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Sudata ya automatiza con IA la carga de facturas y los tableros de pymes del NEA: un agente de voz con telefonía incluida es otro servicio para esos mismos clientes.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=sudata

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S63. Crenein

- Contacto 201 de `seguimiento.md`
- Rubro: Software vertical para ISP (C-Network, C-Stock, C-Bills) y consultoría de IA con orquestación de agentes, Chaco (socia del Polo IT Chaco; teléfono con característica 3725) (Argentina)
- Web: https://crenein.com
- Tipo: posible aliado (canal)
- Por qué encaja: Software vertical para proveedores de internet, que atienden reclamos y cobran por teléfono; ya ofrece agentes de IA.
- Gancho: 'Software y servicios para ISP': C-Bills ('facturación, cobranzas y administración completa del negocio ISP') y 'Consultoría IA: desarrollo de software con IA y orquestación de agentes para empresas'; 'desde Argentina para toda Latinoamérica' (sitio). Socia del Polo IT Chaco.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | comercial@crenein.com | área | comercial (sitio, home) | https://crenein.com/ (7-oct-2026) |
|  | info@crenein.com | atención | casilla general (ficha del Polo IT Chaco) | https://poloitchaco.org.ar/empresas/crenein/ (ficha del Polo IT Chaco, Cloudflare data-cfemail decodificado; vista el 7-oct-2026) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: +54 3725 15-409044 (ficha del Polo).

LinkedIn: empresa https://www.linkedin.com/company/crenein/; persona —.

Otros canales: formulario https://crenein.com/ (Contacto); WhatsApp +54 9 372 548-2757: botón del sitio (wa.me/5493725482757, home y empresa, 7-oct-2026); redes https://www.instagram.com/crenein.ok.

Para:

```
comercial@crenein.com
```

Asunto:

```
Voz y telefonía para los agentes de IA de Crenein
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Crenein ya factura y cobra para ISPs y ofrece orquestación de agentes de IA: atender reclamos y avisar vencimientos por teléfono puede salir de un agente de voz integrado a C-Bills.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=crenein

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (277 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Crenein. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Crenein ya factura y cobra para ISPs y ofrece orquestación de agentes de IA: atender reclamos y avisar vencimientos por teléfono puede salir de un agente de voz integrado a C-Bills.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=crenein

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S64. iSource

- Contacto 202 de `seguimiento.md`
- Rubro: Software vertical de gestión para clínicas, sanatorios y obras sociales, Corrientes capital (Argentina)
- Web: https://isource.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Software vertical de salud en Corrientes: sus clínicas confirman turnos y atienden pacientes por teléfono; canal al rubro.
- Gancho: 'Empresa Argentina de desarrollo de productos de base tecnológica, orientados a mejorar la calidad de gestión de las organizaciones' (meta del sitio); la home muestra logos de Clínica El Modelo, Sanatorio San Juan, IOSCOR, Clínica del Sol, Clínica Mayo, Mediccis y Centro Médico (sitio); socia del Polo IT Corrientes. AVISO: el sitio no tiene robots.txt, pero el servidor devolvió 403 al user-agent que incluye 'ClaudeBot'; estos datos salieron de una primera lectura con user-agent de navegador (7-oct-2026). Revisar antes de enviar.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | martindebiasi@isource.com.ar | persona | nombre y cargo no publicados en texto (la casilla sugiere Martín De Biasi); página /contacto del sitio | https://isource.com.ar/contacto/ (7-oct-2026, lectura con user-agent de navegador) |

★ porque es la casilla de la persona con más potencial publicada.

Teléfonos: —.

LinkedIn: empresa — (no publicado); persona —.

Otros canales: formulario https://isource.com.ar/contacto/; WhatsApp +54 379 470-1566: botones del sitio (wa.me/543794701566, home, nosotros y contacto, 7-oct-2026); redes —.

Para:

```
martindebiasi@isource.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de iSource
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

iSource ya gestiona clínicas y sanatorios de Corrientes: confirmar turnos y atender pacientes por teléfono puede hacerlo un agente de voz integrado a su sistema.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=isource

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (277 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como iSource. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

iSource ya gestiona clínicas y sanatorios de Corrientes: confirmar turnos y atender pacientes por teléfono puede hacerlo un agente de voz integrado a su sistema.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=isource

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```

## S65. Yugoo

- Contacto 203 de `seguimiento.md`
- Rubro: ERP propio e implementación de Odoo, logística e IA (agentes conectados al ERP), Corrientes capital (Argentina)
- Web: https://www.yugoo.com.ar
- Tipo: posible aliado (canal)
- Por qué encaja: Ya conecta agentes de IA a los ERP de empresas del NEA; el teléfono es el canal que le falta.
- Gancho: 'ERP, logística e inteligencia artificial para empresas, desde 2007'; 'Workflows y agentes que ejecutan tareas y responden sin intervención manual', 'Modelos de OpenAI conectados a tu ERP y tus sistemas'; +800 proyectos; implementa Odoo y tiene ERP propio; cliente Fábrica de Velas El Litoral ('Hecho en Corrientes') (sitio); socia del Polo IT Corrientes. AVISO: robots.txt permite todo, pero el WAF bloqueó ('Your request was blocked') al user-agent con 'ClaudeBot'; datos de una primera lectura con user-agent de navegador (7-oct-2026). Revisar antes de enviar.

Emails encontrados (verificados el 7-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | info@yugoo.com.ar | atención | casilla general (sitio, home) | https://www.yugoo.com.ar/ (7-oct-2026, lectura con user-agent de navegador) |

★ porque no hay email de persona publicado: va a la casilla de área o de atención.

Teléfonos: —.

LinkedIn: empresa — (no publicado); persona —.

Otros canales: formulario https://www.yugoo.com.ar/ ('Solicitar demo'); WhatsApp — (sin WhatsApp publicado: revisados home del sitio, 7-oct-2026); redes —.

Para:

```
info@yugoo.com.ar
```

Asunto:

```
Voz y telefonía para los agentes de IA de Yugoo
```

Texto:

```
Hola, ¿cómo están?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: agentes que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. Tiene API y panel multi-cliente para integrarla en sus soluciones.

Yugoo ya conecta agentes de IA a los ERP de sus clientes: el teléfono es el canal que falta para que esos agentes atiendan y llamen, con número incluido.

https://atentina.com.ar/?utm_source=email&utm_campaign=canales3&utm_content=yugoo

¿Lo vemos como aliados? Ustedes ponen el cliente y la integración; nosotros, la voz y la telefonía a un precio mayorista que deja margen. Podemos empezar con un piloto.

Saludos,
Laureano
laureano@atentina.com.ar
```

LinkedIn, nota de invitación (275 caracteres):

```
Hola, soy Laureano, de Atentina: agentes de IA que atienden y llaman por teléfono y WhatsApp, con número incluido y voces argentinas. Inferencia propia, sin Twilio ni ElevenLabs: mucho más barato por minuto. Lo ofrecemos por API a empresas como Yugoo. ¿Lo vemos como aliados?
```

LinkedIn, mensaje:

```
Hola, ¿cómo estás?

Soy Laureano, de Atentina. Somos una plataforma que resuelve telefonía e IA con precios argentinos: número incluido, voces argentinas. Como no dependemos de Twilio, ElevenLabs ni OpenAI, el costo por minuto queda muy por debajo del de armarlo con esos proveedores, y en pesos. API y panel multi-cliente.

Yugoo ya conecta agentes de IA a los ERP de sus clientes: el teléfono es el canal que falta para que esos agentes atiendan y llamen, con número incluido.

https://atentina.com.ar/?utm_source=linkedin&utm_campaign=linkedin&utm_content=yugoo

¿Lo vemos como aliados, con un piloto? Ustedes el cliente y la integración; nosotros la voz y la telefonía a un precio mayorista que deja margen.
```
