# Propuesta técnica para Axioma IT Solutions

- **Pedido (22-oct-2026, Laureano, textual):** "Propuesta de demo, no sabemos qué necesitan, así que investigalos como
  integradores de lo nuestro. Más bien técnico y overview del producto." Y además: "Explicá que las voces pueden sonar
  mejor, dependiendo de la configuración y ajustando la latencia deseada."
- **Destinatario:** Ing. Axel Daniel Díaz, cofundador y CEO de Axioma IT Solutions S.R.L. (CABA, Polo Tecnológico de
  Parque Patricios): software factory, partner Silver de Odoo y partner de Microsoft, con TodoTurnos, Flowery BPM y una
  línea de Soluciones IA (n8n). Voseo para Axel en la entrada; "ustedes" para la empresa.
- **Contexto:** Axel probó la demo de voz de la landing el 22-oct-2026 (conversación `e0e4e64d`, 111 s): pidió "un
  agente que llame a ciertos leads del CRM, en momento determinado", preguntó por más voces y por "que suene menos
  robot", y quiere probarlo él antes de hablar con un asesor. Base de conocimiento:
  [`comercial/demos/axiomait.md`](../../../../comercial/demos/axiomait.md) (partes 0, 1, 2, 4, 5 y 7). Lead #218
  del CRM. Formato y estética copiados de [`goldman-propuesta`](../goldman-propuesta/README.md) y
  [`baicenter-propuesta`](../baicenter-propuesta/README.md).
- **Objetivo:** que se registren y prueben solos, y que pidan la demo técnica o el piloto de integración de 30 días.
- **Formato:** A4, 5 a 6 hojas (salió en 6). `make doc P=axiomait-propuesta V=<n> HOJAS=6`.
- **Indicaciones del pedido:** propuesta técnica para un integrador, no la de cliente final. Énfasis en oportunidades;
  sin nombrar fallas del sitio ni competencia. Material de venta: no dice qué está construido (ver "A validar"). Sin
  precios nuestros. Sin logo ni marca de Axioma: el nombre escrito. Sin mencionar el Registro No Llame en el PDF.

## Estructura (v1)

1. **Portada y quiénes son:** h1 "Sumen voz a lo que ya venden: Odoo, agentes de IA y turnos", saludo a Axel, lo que
   ya hacen bien (+100 proyectos, Silver de Odoo con 30 referencias y 97 % de retención, 5,0 en Google y Clutch, ISO
   9001), la cita de Axel en la demo, y Atentina en cuatro datos (41 voces, 0,87 s, 4 en 1, 1 API).
2. **Dónde encaja Atentina:** cuatro líneas (Odoo y CRM, Soluciones IA y n8n, TodoTurnos, soporte Odoo), cada una con
   su oportunidad de voz; el orden (primero sus leads, después revenderlo a sus clientes) y por qué para un integrador.
3. **El producto por dentro:** diagrama de arquitectura (leads → línea, WhatsApp, link → agente que escucha, decide y
   habla, en Argentina → panel y API → su sistema) y tabla de piezas (agentes versionados, motores, API `/api/v1`,
   motores por API, multi-cliente).
4. **El llamador del CRM:** diagrama Odoo/CRM → API → agente → lead, con el webhook de vuelta; cuatro pasos; ejemplo de
   `POST /api/v1/campaigns` y del webhook `contact.finished` (rotulados ilustrativos y abreviados); nota de la llamada
   suelta por `POST /api/v1/calls`.
5. **Voces y naturalidad:** 9 voces con su descripción + 32 más; cuatro palancas (voz, estilo del agente, apertura
   pregenerada, voz a medida); el compromiso con la latencia (escala "responde antes / suena más fluida"); tres cifras
   medidas; la postura "natural, pero honesto".
6. **Puesta en marcha:** acceso para probar hoy, demo técnica de 30 min y piloto de 30 días; seis pasos; quién hace
   qué; después del piloto (TodoTurnos, soporte Odoo, clientes Odoo, acuerdo de canal); nota de precio; contacto.

## Afirmaciones y de dónde salen

Axioma (base de conocimiento, sitio leído el 22-oct-2026):
- **+100 proyectos; ingenieros de la UTN FRBA:** home ("+100 Proyectos") y "quiénes somos" (parte 2.1 y 0).
- **Silver de Odoo, 30 referencias, 97 % de retención; partner de Microsoft:** ficha de partner en odoo.com y logos del
  home (parte 0 y 2.1).
- **5,0 en Google (17 reseñas) y en Clutch (4):** Google Maps y Clutch (parte 0).
- **ISO 9001:2015, Bureau Veritas, "Custom Software Development":** parte 0 y 2.1.
- **Formularios con respuesta en menos de 24 h, Meta Ads, cupos del Kit 4.0 por orden de llegada:** parte 5, D1.
- **Agentes de IA a medida en 4 a 8 semanas, n8n:** `/soluciones-ia/` (parte 0 y 3).
- **TodoTurnos bajó 70 % las ausencias en Sanatorio Santa Rosa; Badent confirmaba turnos llamando a mano:** parte 5, D3.
- **Planes de soporte con atención telefónica y guardia pasiva 24/7 con fines de semana:** parte 5, D4.
- **Programa de partners con comisiones:** `/referidos` (parte 2.1).
- **Cita de Axel** ("Quiero un agente que llame a ciertos leads del CRM. En momento determinado." y "Me gustaría
  probarlo mejor, [...] antes de llamar a un asesor"): `scratch/prospectos/axiomait/raw/conversacion_demo_2026-10-22.txt`.
  En el PDF la primera va con coma en lugar de punto.

Atentina:
- **41 voces, 28 de mujer y 13 de hombre:** `tts/finetune/voces.tsv` (28 `arf_*`, 13 `arm_*`) y `site.ts`. Las 9
  descripciones de la hoja 5 son las de `voices` en `landing/src/data/site.ts` (se omitió Laura).
- **0,87 s promedio y 1,17 s máximo, 6 turnos:** latencia `e2e` del server en la llamada de Axel (0,868 y 1,165 s;
  base, `call_logs.latency`, copiada en la conversación de `raw/`). `e2e` = desde que dejó de hablar hasta que sonó el
  primer audio (`app/voice/latency.py`). Era una llamada desde el navegador, no telefónica.
- **0,4 a 1 s de espera de silencio, más al dictar:** `MIN_ENDPOINTING_DELAY` 0,4, `MAX_ENDPOINTING_DELAY` 1,0 y
  `DICTATION_ENDPOINTING_DELAY` 2,5 en `app/voice/worker.py`.
- **4 en 1; inferencia propia en Argentina; telefonía con Anura:** DOCUMENTOS.md ("Propio") y AGENTS.md.
- **API keys por alcance (`calls`, `llm`, `stt`, `tts`); motores compatibles con el SDK de OpenAI y streaming:**
  ARQUITECTURA, API_INFERENCIA y `site.ts`.
- **Campos del ejemplo de campaña** (`channel`, `agent_id`, `voice`, `starts_at`, `window_start`/`window_end`,
  `weekdays`, `concurrency`, `max_attempts`, `callback_url`, `contacts` con `phone`, `name`, `external_id`,
  `attributes`, `start`): `CampaignIn` y `ContactIn` en `app/api/schemas.py`.
- **Webhook:** header `X-Atentina-Signature: sha256=<hmac>`, eventos `contact.finished` y `campaign.finished`
  (`app/services/campaign_callbacks.py`); campos del contacto de `campaign_reports.report_rows` (`external_id`,
  `resultado`, `intentos`, `duracion_segundos`, `outcome`, `objetivo`, `campos`, `link`). En el real, `campos` viaja como
  texto JSON, no como objeto: el ejemplo lo simplifica.
- **Llamada suelta por `POST /api/v1/calls` con teléfono:** ARQUITECTURA, "Llamada saliente o de prueba".
- **Plan Free (20 minutos por mes, llamadas web, panel y API):** `site.ts` y SUSCRIPCIONES_PLAN.
- **Apertura pregenerada:** AGENTS.md (`conversation.opening_audio`, desde el 19-oct-2026).
- **Motor asistente con herramientas; LLM propio del cliente (BYOK):** APPS.md y BYOK_LLM_PLAN (backend en producción).
- **Contacto:** igual a `landing/src/data/site.ts` (0800-220-1233, hola@atentina.com.ar, WhatsApp +54 9 351 700-2592).

## A validar antes de mandarlo

- **Funciones presentadas como oferta que hoy no están en uso o no existen** (base, parte 7.4):
  - **campañas de voz** (programadas, horario, reintentos, contestador, webhook, `report.csv`): código y migración
    aplicados, pero **ningún tier tiene el canal `voice`, cero campañas y cero llamadas salientes en la base**. Antes de
    la demo técnica: habilitar `voice` en un tier de prueba, correr una campaña con 2-3 números propios y mirar los
    `sip_status`. Los códigos SIP de Anura y el contestador no están medidos;
  - **capacidad con Gemma sin medir**; tope de campañas `CALL_CAMPAIGN_MAX_CONCURRENT` = 8 provisorio. El piloto propone
    1-2 llamadas a la vez;
  - **documentación pública de la API:** no existe (el OpenAPI es solo para admin). La hoja 6 pone "documentación de la
    API" en el acuerdo de canal, y el paso 1 del piloto supone darles algo: hace falta al menos una guía corta;
  - **multi-cliente para un integrador** (subclientes, marca blanca, panel de reseller): no existe; hoy el admin crea un
    cliente por cada uno. El documento dice "cada cliente, con su agente, su número y su panel" y "cuentas por cliente";
  - **derivación o transferencia a un humano:** no existe. El documento no la promete; "deja una actividad al vendedor"
    es trabajo del CRM con el webhook;
  - **voz a medida para un cliente:** se puede entrenar, pero agregar una voz es reentrenar el checkpoint con todas
    (TTS_FINETUNE.md); plazo y costo sin definir;
  - **ajuste de la latencia por agente:** la espera de silencio (0,4 a 1 s) es una constante de la plataforma, no un
    campo del agente; "se ajusta por caso" hoy es un cambio nuestro. El efecto "más margen, frases más completas y
    entonación más pareja" es el pedido de Laureano, sin medición propia;
  - **"Se prueban en el panel"** (escuchar las voces): verificar que el plan Free lo permite desde el editor del agente.
- **Registro No Llame (Ley 26.951):** no se menciona en el PDF. Llamar a leads que dejaron sus datos es distinto de
  llamar en frío, pero hay que validarlo con un abogado antes del piloto; una campaña `purpose: comercial` exige
  confirmar el filtro contra el registro (por eso el ejemplo no lleva `purpose`).
- **Postura sobre la IA:** "no niega ser una IA" responde a "que no se dé cuenta que es una IA" (Axel). Es la posición
  de la base (parte 6), a confirmar por Laureano.
- **Promesas comerciales:** piloto de 30 días, demo técnica de 30 min, soporte directo, revisión semanal, "el precio
  del piloto y las condiciones para revender se acuerdan después de la prueba" y "un componente con margen para
  revender, en un modelo de canal a definir juntos": siguen la base (7.5 y 7.6), a confirmar por Laureano. No hay precio
  de partner ni mayorista.
- **Latencia:** 0,87 s es de una llamada por navegador con 6 turnos; por teléfono suma la red de Anura. El piso medido
  con el cliente en CAP-001 (otro LLM) fue 1,66 s p50.
- **Grabación:** si se activa para el piloto, avisar a quien atiende y corregir la política de privacidad de la landing.
- **Datos de Axioma:** releer el sitio antes de mandarlo (+100 proyectos, 97 %, reseñas), cambian seguido.

## Versiones

| Versión | Fecha | Qué cambió | Estado |
|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 22-oct-2026 | Primera versión | borrador |
