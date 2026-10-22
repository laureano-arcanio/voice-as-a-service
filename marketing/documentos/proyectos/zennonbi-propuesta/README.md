# Propuesta de alianza e integración para Zennon BI

- **Pedido (22-oct-2026, Laureano, textual):** "Investiga la empresa zennonbi, identifica posibles alianzas o
  integraciones a sus productos. Arma un pdf y un video diseñado para ellos."
- **Destinatario:** Cristian Ventura, fundador y CEO de Zennon S.A.S. ("Zennon BI", Puerto Madero, CABA): consultora
  partner de Microsoft que implementa Dynamics 365 CE, Power Platform y Power BI, y trabaja también para otros partners.
  Saludo a Cristian en la entrada; "Zennon" en tercera persona para la empresa.
- **Contexto:** llegamos en frío. Mail de la tanda `canales4` el 15-oct-2026 (con clic); el 19-oct Laureano llamó, atendió
  Cristian, se interesó y quedó una reunión para la semana del 26-oct-2026 (fecha a confirmar). Lead #228 del CRM.
  Base de conocimiento: [`docs/mercado/demos/zennonbi.md`](../../../../docs/mercado/demos/zennonbi.md) (partes 0, 1,
  2, 4, 5 y 7; la 7.4 para lo desplegado). Formato y estética copiados de
  [`axiomait-propuesta`](../axiomait-propuesta/README.md); panel y tabla "hoy / con Atentina" de
  [`baicenter-propuesta`](../baicenter-propuesta/README.md). Video relacionado: lo arma el agente de videos a partir de
  este documento.
- **Objetivo:** que Cristian llegue a la reunión con la alianza entendida y pida la demo técnica con su Dynamics de
  prueba y un piloto de integración de 30 días (en Zennon o con un cliente de su cartera).
- **Formato:** A4, 4 a 6 hojas (salió en 5). `make doc P=zennonbi-propuesta V=<n> HOJAS=6`.
- **Indicaciones del pedido:** alianza, no un agente para su atención: Atentina dentro de lo que Zennon vende. La voz
  nativa de Microsoft se menciona como dato del mercado, sin atacar. Material de venta: no dice qué está construido (ver
  "A validar"). Sin precios nuestros (el del aliado se acuerda en la reunión). Sin logo ni marca de Zennon (el nombre
  escrito); Microsoft, Dynamics, Power Platform y Power BI nombrados como productos, sin logos ni pantallas.

## Estructura (v1)

1. **Portada y quiénes son:** h1 "La línea de voz argentina de cada proyecto Dynamics 365 que implementan", saludo a
   Cristian, lo que hacen bien (2018, 32 clientes, +11.000 productores de Federación Patronal, 12 unidades de negocio en
   FEDPAS 360), la cita de Cristian ("El 70% de esta plataforma está personalizada..."), Atentina en cuatro datos (41
   voces, 0800 · 0810 y regional, 4 en 1, 1 API) y cuatro puntos (inferencia en Argentina, mismo método de piloto,
   se conecta con Power Automate y Power BI, Zennon conserva al cliente).
2. **Dónde encaja Atentina:** ocho tarjetas en el orden de la 7.1 (Sales/KickStart y Customer Service destacadas;
   Contact Center como fuera de horario y desborde; Field Service; Customer Insights Journeys; Power Pages; Copilot
   Studio y Power BI; para partners e integraciones), cada una con su oportunidad, y el recuadro "Un dato del mercado"
   (licencias de Contact Center y números de ACS en Argentina).
3. **La integración por dentro:** diagrama SVG Dynamics 365/Dataverse (gris) ↔ Power Automate con el conector (gris, lo
   arma Zennon) ↔ API y agente de Atentina (azul) ↔ canales (línea argentina, WhatsApp, link en el navegador) ↔ sus
   clientes, con Power BI abajo; recorrido numerado 1-6. Debajo, saliente (5 pasos) y entrante (3 pasos) y la tabla "qué
   viaja" (de Dynamics a Atentina, de vuelta y a Power BI).
4. **El modelo de alianza y el panel:** el módulo de voz junto a los tres KickStart (rotulado como ejemplo), qué gana
   Zennon, Atentina y el cliente final, el tablero con datos ilustrativos (rotulado) y la tabla "Hoy / Con Atentina".
5. **Puesta en marcha:** acceso para probar, demo técnica de 30 min con su Dynamics de prueba (destacada) y piloto de 30
   días; seis pasos; quién hace qué; después del piloto (primer cliente, conector y tablero, Copilot Studio, acuerdo de
   aliado); nota de condiciones; contacto.

## Afirmaciones y de dónde salen

Zennon (base de conocimiento, fuentes leídas el 22-oct-2026; copia en `scratch/prospectos/zennonbi/raw/`):
- **2018:** año de fundación en la página de empresa de LinkedIn (`linkedin_empresa.txt`). "Como socios de Microsoft":
  CESSI ("Socios estratégicos de Microsoft") y el sitio ("Consultoría e implementación Microsoft"). El nivel de partner
  no se encontró.
- **32 clientes que muestran, con siete partners:** `/clientes/` (base, 2.5). Rubros del texto: los de la tabla 2.5.
- **+11.000 productores y organizadores, 12 unidades de negocio, más de 1.000 empleados, FEDPAS 360 sobre Dynamics 365
  Sales:** caso Federación Patronal del blog (`pages/posts_5524_...txt`, líneas 5, 6 y 10).
- **Cita de Cristian:** misma página, línea 10, textual ("El 70% de esta plataforma está personalizada con el
  conocimiento y experiencia que el área comercial tenía"), atribuida a "Cristian Ventura, Fundador y CEO de Zennon BI".
- **"Conectamos procesos, datos y equipos"; CRM KickStart Esencial, Crecimiento y Expansión:** home (`home.txt`). Qué
  incluye cada paquete no está publicado: la hoja 4 lo rotula "Un ejemplo de cómo sumarlo".
- **Sales Qualification Agent: investiga y prepara un correo que no se envía (Research-only):** nota del 21-oct-2026
  (base, D2).
- **Cartera con volumen de llamadas** (pagos, cooperativa de servicios, microcréditos, BPO): `/clientes/` (base, D3).
- **Trabajan para otros partners; desarrollos sobre Azure:** sitio, "Para partners" y soluciones (base, 0 y 2.3).
- **Método: tarea acotada, línea de base, medir antes de ampliar:** notas del 15, 19 y 21-oct (base, 0 y 6).

Microsoft (base, parte 3 y 5, D1; leído el 22-oct-2026):
- **Contact Center USD 110 y Voice USD 95 por usuario por mes, más el uso de ACS:** página de precios de Dynamics 365
  Contact Center en microsoft.com.
- **ACS en Argentina: solo toll-free, solo entrantes, sin salientes ni SMS, facturación en nueve países que no incluyen
  Argentina:** Microsoft Learn (`microsoft_acs_argentina.txt`).

Atentina:
- **41 voces, 28 de mujer y 13 de hombre:** AGENTS.md y `tts/finetune/voces.tsv`.
- **Numeración regional, 0800 y 0810; entrantes y salientes; minutos en el plan; precio en pesos; 4 en 1:**
  `landing/src/data/site.ts` (`faqNumbers`, capacidades de telefonía) y DOCUMENTOS.md ("Propio").
- **Inferencia propia en Argentina, sin proveedores externos:** AGENTS.md (con BYOK desactivado, que es el default).
- **API `/api/v1`: llamadas (`POST /calls` con `phone`, `context` hasta 2.000 caracteres, `voice`), contactos, campañas
  (horario, días, concurrencia, reintentos, `callback_url`, `external_id`), `/stats`, `/stats/daily`,
  `/campaigns/{id}/stats` y `report.csv`; webhook con HMAC-SHA256:** `app/api/routers/{calls,campaigns,contacts}.py`,
  `CallIn` y `CampaignIn` en `app/api/schemas.py`, `app/services/campaign_callbacks.py`.
- **Link para llamar desde el navegador:** LINK_LLAMADA_PLAN (desplegado el 19-oct-2026).
- **WhatsApp: mensajes y llamadas:** WHATSAPP_PLAN (con el número de Atentina).
- **Motores sueltos (transcripción, voz y lenguaje) por API:** API_INFERENCIA.
- **Plan Free: 20 minutos por mes, llamadas web, panel y API:** `freePlan` en `site.ts`.
- **Contacto:** igual a `landing/src/data/site.ts` (0800-220-1233, hola@atentina.com.ar, WhatsApp +54 9 351 700-2592).

## A validar antes de mandarlo

- **Presentado como oferta, hoy no existe o no se usó** (base, 7.4):
  - **conector de Power Automate:** no existe; lo arma Zennon sobre la API. Para eso hace falta la **especificación de
    la API**, que hoy no es pública (`/api/v1/docs` solo admin). La hoja 5 promete entregarla en el paso 2: preparar al
    menos un OpenAPI filtrado o una guía corta antes del piloto;
  - **webhook por llamada suelta o entrante:** no existe (solo el de campañas, `contact.finished`). La hoja 3 dice que el
    resultado "vuelve firmado" también en la entrante y en la saliente suelta. Hoy, para eso, está el resumen por email
    (desplegado), que Power Automate puede leer ("cuando llega un correo"): usarlo en la demo o construir el webhook por
    llamada antes del piloto;
  - **llamadas salientes y campañas de voz:** en el código, **cero salientes en la base** y ningún tier con el canal
    `voice`. Antes de la demo: habilitar `voice` en `Interno`, una saliente suelta por API a un celular propio y una
    campaña de 2-3 números propios. Códigos SIP de Anura y contestador sin medir;
  - **"Llama al lead apenas entra / en minutos" y el "suena a los segundos" de la demo:** depende de la saliente sin
    probar; la mediana de 4 min del tablero es ilustrativa;
  - **Copilot Studio ("llamar a este contacto"):** sería un conector personalizado sobre la misma API; no hay **servidor
    MCP** público (el mail del 15-oct lo mencionó). El PDF no nombra MCP; si Cristian lo pregunta, es a construir;
  - **Contact Center "primer nivel, fuera de horario y desborde":** no hay derivación ni transferencia a un humano o a la
    cola del Contact Center. La tarjeta no promete derivar, pero un cliente de Contact Center lo va a pedir;
  - **Journeys (paso "llamada" o "WhatsApp"):** campañas de WhatsApp desplegadas; de voz, sin uso. El número propio del
    cliente en WhatsApp depende de la aprobación de Meta (Embedded Signup);
  - **Power Pages:** el link para llamar está desplegado, pero falta una llamada real de punta a punta (LINK_LLAMADA_PLAN 11);
  - **cuentas por cliente para un aliado** (subclientes, panel de reseller): no existe; hoy el admin crea un cliente por
    cada uno. El título de la hoja 4 dice "el cliente sigue siendo de Zennon" (la relación comercial), no marca blanca:
    el agente se presenta con el nombre que se le configure, pero el panel y los mails son de Atentina;
  - **identificar a quien llama en la entrante:** el agente tiene el número de quien llama; cruzarlo con Dataverse en la
    charla requiere el motor `assistant` con una herramienta (a construir) o pedir los datos;
  - **capacidad con Gemma sin medir:** el piloto tiene que ir con pocas llamadas a la vez.
- **Precios de Microsoft:** releerlos antes de mandarlo (cambian); son precios de lista anuales en dólares y no incluyen
  el uso de ACS ni los créditos.
- **Promesas comerciales:** demo técnica de 30 min con su Dynamics de prueba, piloto de 30 días, soporte directo,
  revisión semanal, "precio fijo por mes" del módulo, "margen o comisión, sin exclusividad", "una cuenta por cada
  cliente" y "probar el acceso no tiene costo": siguen la base (7.5 a 7.7), a confirmar por Laureano. No hay precio de
  aliado ni mayorista: la nota dice que se acuerda en la reunión.
- **Datos ilustrativos:** todo el tablero de la hoja 4 (KPI, resultados y campañas) está rotulado así; los KickStart con
  su contenido, como ejemplo.
- **Grabación:** si se activa en el piloto, avisar a quien atiende y corregir la política de privacidad de la landing.
- **Registro No Llame (Ley 26.951):** no se menciona en el PDF; validar con un abogado antes de campañas comerciales
  salientes con clientes de Zennon.
- **Datos de Zennon:** releer el sitio antes de mandarlo (lo relanzaron el 14-oct y lo siguen cambiando); la fecha de la
  reunión, a confirmar.

## Versiones

| Versión | Fecha | Qué cambió | Estado |
|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 22-oct-2026 | Primera versión | borrador |
