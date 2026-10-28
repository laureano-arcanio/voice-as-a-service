# Propuesta técnica para CIMEPA S.A.

- **Pedido (22-oct-2026, agente principal por Laureano):** "Armá un PDF de propuesta (proyecto nuevo cimepa-propuesta,
  v1) para CIMEPA S.A. (CABA). Destinatario: Pablo (cargo por confirmar). Lo manda Atentina después de que Pablo
  escribiera por nuestro WhatsApp (habló con el agente IA y después con Laureano, 22-oct-2026). [...] Esta propuesta es
  distinta de Goldman/BAIC: es técnica y de integración, no 'dónde mejorar con Atentina' (no hay datos públicos de su
  negocio ni reseñas: no inventes 'lo que hacen bien'). El tono es para alguien técnico que evalúa proveedores."
  Incluye la solución decidida por Laureano, la estructura sugerida (A4, 4 a 5 hojas) y las reglas: sin precios, sin
  decir qué está construido, sin prometer portabilidad, sin nombrar a Anura ni a LiveKit (salvo LiveKit/WebRTC como
  estándar de integración), sin logo ni marca de CIMEPA, fecha 22-oct-2026.
- **Destinatario:** Pablo, de CIMEPA S.A. (CABA); probablemente Pablo Kevin Brahim, director suplente (sin confirmar).
  Escribe técnico y formal, quiere las respuestas por escrito. Trato: saludo a Pablo y "ustedes" para la empresa.
- **Contexto:** escribió el 22-oct-2026 por el WhatsApp de Atentina (lead #365 del CRM), habló con el agente comercial
  y después con Laureano, que quedó en mandar "info de cómo sería la propuesta y la demo". Base:
  [`comercial/demos/cimepa.md`](../../../../comercial/demos/cimepa.md) (partes 0, 2.4, 5 y 7) y la solución en
  [`comercial/demos/cimepa-telefonia.md`](../../../../comercial/demos/cimepa-telefonia.md) ("Diseño elegido" y
  "Decidido con Laureano"; las opciones A-D de antes no van). Formato y estética de
  [`goldman-propuesta`](../goldman-propuesta/README.md) y [`baicenter-propuesta`](../baicenter-propuesta/README.md).
- **Objetivo:** que acepten la charla técnica y la demo, y de ahí un piloto.
- **Formato:** A4, 5 hojas. `make doc P=cimepa-propuesta V=<n> HOJAS=5`.

## Estructura (v1)

1. **Portada:** h1 "Un número de la empresa para su equipo y su IA, todo grabado y transcripto", entrada a Pablo,
   cuatro cifras (3 o más números, 3 o más simultáneas, nada que instalar, todas las llamadas grabadas), sus cuatro
   pedidos con su cita textual y el "cómo" de cada uno, y por qué Atentina.
2. **Sus preguntas, una por una:** tabla pedido → solución en cuatro grupos (números y llamadas; personas; su asistente
   de IA; grabación y datos; comercial), con todas las preguntas de su WhatsApp.
3. **Arquitectura:** diagrama (sus clientes ⇄ números de la empresa → asistente de IA / llamadas de su equipo →
   celular del empleado y app web; grabación y transcripción de toda la llamada; su sistema ⇄ plataforma por API y
   webhooks) y cuatro flujos (entra una llamada, llama un empleado, llama la IA, queda registrado).
4. **Integración de su agente:** tres vías a evaluar en la charla técnica (WebRTC con el estándar LiveKit, SIP, nuestro
   agente con su contexto, herramientas y modelo), nota de la API de inferencia, qué recibe y qué manda su sistema (con
   un ejemplo de `POST /api/v1/calls`) y las preguntas de la charla.
5. **Puesta en marcha:** charla técnica, demo sin costo, piloto de 30 a 60 días, decisión; quién hace qué; después del
   piloto (recibir en la web, WhatsApp, más escala); nota de precio y pie de contacto.

## Afirmaciones y de dónde salen (22-oct-2026)

- **Citas de Pablo** ("Que una persona haga y reciba llamadas desde su computadora o celular", "Conectar un asistente
  propio que gestione la conversación de voz en tiempo real", "¿Permiten transferir llamadas tanto de IA a persona como
  de persona a IA?", "Que las conversaciones queden grabadas"): `cimepa.md`, parte 5 (conversación `4a0e11f1`). La
  segunda está recortada ("Necesitamos..." y "no solamente enviar contexto al agente de ustedes" afuera).
- **3 números o más y 3 simultáneas o más:** "Decidido con Laureano" (`cimepa-telefonia.md`).
- **Entrantes a la IA, derivación al celular real con resumen, vuelta de la IA si nadie atiende, app web para salientes,
  persona → IA con contexto, grabación y transcripción de toda la llamada:** "Diseño elegido" y "Decidido con Laureano".
- **Salientes por API con contexto:** `POST /api/v1/calls` con `agent_id`, `contact_id`, `from_number_id` y `context`
  (`app/api/schemas.py`, `CallIn`, verificado el 22-oct-2026). El `agent_id` "seguimiento" del ejemplo es ilustrativo
  (en la API es un id).
- **Campañas programadas (horario, días, reintentos, en paralelo) y webhook firmado HMAC-SHA256 con reintentos:**
  `docs/features/CAMPANAS.md (implementado, sin desplegar).
- **API keys por sistema, con alcance y revocables; API de inferencia compatible con OpenAI (STT, LLM, TTS):**
  `docs/API_INFERENCIA.md`.
- **Su propio modelo con su API key (BYOK):** `docs/features/LLM_CONEXIONES.md` (fases 1 y 2 desplegadas).
- **Herramientas que consultan su sistema:** motor `assistant` con tools (`docs/APPS.md`); webhooks genéricos a un
  backend del cliente, a validar (ver abajo).
- **Inferencia propia en servidores en Argentina; audios y transcripciones sin proveedores externos:** AGENTS.md
  (inferencia y base locales). Con BYOK o su agente conectado, lo que les manden sale: el documento lo dice.
- **Numeración argentina, terminación local, factura en pesos:** `cimepa.md`, parte 4.2; `site.ts` (numeración).
- **OpenAPI:** `/api/v1/docs` (hoy solo admin): compartir una copia o habilitarla.
- **WhatsApp (mensajes, notas de voz y llamadas):** `docs/features/WHATSAPP.md` (en producción).
- **Contacto:** `landing/src/data/site.ts`, verificado el 22-oct-2026.

## A validar antes de mandarlo

- **Lo que falta construir** (presentado como oferta, `cimepa.md` parte 7.4):
  - **app web de llamadas para empleados** (agenda, click en llamar, salida con el número de la empresa);
  - **herramienta de transferencia / bridge** al celular del empleado con resumen, y la vuelta de la IA si no atiende;
  - **persona → IA** (botón para devolver la llamada a la IA con el contexto);
  - **grabación y transcripción de la llamada entera** (hoy es un WAV por mensaje del agente; falta el participante
    silencioso o Egress para los tramos humanos) y "quién habló en cada tramo, IA o persona";
  - **conexión de un agente externo** (token WebRTC/LiveKit o SIP);
  - **retención configurable** y **aviso de grabación** (además, la privacidad de la landing dice que no se graba audio:
    corregir antes de grabar a un cliente);
  - **desactivar la grabación "por línea"**: hoy es por agente (`record_audio`);
  - **campañas de llamadas y su webhook:** implementadas, sin desplegar;
  - **herramientas con webhooks a su sistema:** hoy las tools del motor `assistant` son de apps por cliente
    (`atentina-apps`); un webhook genérico a su backend es trabajo a definir.
- **Demo:** el documento dice que en la demo "sus personas llaman desde la web con el número de la empresa". Eso
  requiere la app web; si no está para la demo, la demo cubre solo las salientes del agente con transcripción por API
  (`cimepa.md`, 7.3). Ajustar el texto o la fecha de la demo.
- **Promesas comerciales:** demo sin costo (del pedido); piloto de 30 a 60 días con 3 números y 3 simultáneas
  (`cimepa.md` 7.6, propuesta nuestra): confirmar con Laureano. "Charla técnica de una hora" y "soporte técnico durante
  el piloto": a confirmar.
- **3 simultáneas o más con Gemma:** sin CAP vigente; el número es comercial, no medido.
- **Conservar una línea existente:** el documento dice que "hoy no lo podemos asegurar" (portabilidad sin confirmar con
  el proveedor de telefonía).
- **Quién es Pablo:** sin confirmar el apellido ni el cargo; el documento solo dice "Pablo".
- **Caller ID por empleado:** el documento dice que las salientes muestran el número de la empresa y lo deja como
  pregunta ("uno de la empresa o uno por persona").

## Versiones

| Versión | Fecha | Qué cambió | Estado |
|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 22-oct-2026 | Primera versión | borrador |
