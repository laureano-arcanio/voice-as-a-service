# CIMEPA S.A.: base de conocimiento para la propuesta técnica (22-oct-2026)

**Pablo**, de CIMEPA (sociedad de CABA), nos escribió el 22-oct-2026 a las 10:48 por el WhatsApp de Atentina. Habló con el
agente comercial y después con Laureano. Al principio se lo confundió con SIMEPA, la prepaga de La Pampa
([`simepa.md`](simepa.md)), y el usuario confirmó que es de CIMEPA. Pide **telefonía con número argentino para empleados
remotos, su propio agente de IA en la misma línea, transferencia entre la IA y las personas, y grabación**. Este documento
prepara la charla técnica y la propuesta (PDF y video). La solución está en
[`cimepa-telefonia.md`](cimepa-telefonia.md). En el CRM es el **lead #365**.

- **Fuentes, leídas el 22-oct-2026:**
  - la conversación de WhatsApp con el agente (conversación `4a0e11f1`) y el resumen del usuario de la charla con Laureano;
  - el Boletín Oficial: constitución (2014) y directorio (2019);
  - indicadores.ar: CIMEPA S.A. y Dabra S.A.;
  - prensa sobre Dabra (Modaes y La Nación);
  - cimepa.com, un homónimo sin relación.
  - Los links están en la parte 9.
- **Copia local:** `scratch/prospectos/simepa/raw/cimepa/` (los PDF del Boletín Oficial con su texto, y cimepa.com) y
  `scratch/prospectos/simepa/raw/whatsapp-conversacion-agente.json`.
- **No se encontró:** sitio web de CIMEPA, LinkedIn, prensa, empleados registrados, el apellido y el cargo de Pablo, a qué
  se dedica hoy la "línea de trabajo" que evalúan, y qué herramientas de voz usan.
- **Partes 1 a 5:** datos. Las partes 6 a 8 son nuestras y hay que validarlas con Pablo.

## 0. Resumen para la propuesta

- **Quién es:** Pablo, de CIMEPA S.A. (CABA). Probablemente es **Pablo Kevin Brahim**: socio fundador, presidente de 2014
  a 2024 y hoy director suplente. No está confirmado. Escribe técnico y formal, y quiere las respuestas por escrito.
- **Qué es la empresa:** una sociedad de la familia Brahim, fiduciaria, inmobiliaria y de inversiones, sin empleados
  registrados. Comparte directivos con **Dabra S.A.**, el grupo de Dexter, Stock Center y Moov. "Estamos evaluando una línea
  de trabajo en Argentina": el negocio de las llamadas es nuevo o no está a nombre de CIMEPA.
- **Qué pide** (WhatsApp, 22-oct), en un mismo número argentino o en varios:
  1. empleados remotos y sin teléfono que llamen y atiendan desde la compu o el celular;
  2. un **asistente de IA propio**, que no sea el nuestro, que haga salientes de seguimiento y atienda, por SIP o por audio
     bidireccional;
  3. transferencia IA ↔ persona, en los dos sentidos;
  4. todo grabado, con transcripción por API.

  WhatsApp, más adelante.
- **Dolores:** no tienen telefonía (D1), tienen o arman un agente y no tienen dónde conectarlo (D2), y quieren todo
  registrado y saber dónde queda (D3).
- **Competencia probable:** Twilio, Telnyx o Vonage (todo resuelto, pero caro a celular argentino), Vapi o Retell con SIP
  propio, Aircall, Ringover o Zadarma (softphone), y la central virtual de Anura.
- **Solución** (decidida con Laureano, 7.1):
  - todo en nuestra webapp, sobre rooms de LiveKit, con Anura solo como troncal;
  - las entrantes las atiende el agente y las deriva al celular real del empleado;
  - las salientes de las personas salen desde un cliente web con la agenda;
  - grabación y transcripción por un participante silencioso;
  - 3 números o más y 3 llamadas simultáneas o más.
  - Cómo se integra su agente se define en la charla técnica.
- **Oferta:** propuesta **sin precios**, solo el detalle de la solución. Se ofrece completa y se construye lo que falta si
  avanzan.
- **No verificado:** quién es Pablo y qué rol tiene, el rubro real, el volumen, con qué está hecho su agente, y si Anura
  acepta portabilidad entrante.

## 1. La persona: Pablo

- Dato que dio él: nombre de pila "Pablo", empresa "Cimepa", WhatsApp **+54 9 11 6163-3436** (celular del AMBA).
- **Candidato: Pablo Kevin Brahim.** DNI 35.726.186, nacido el 24-dic-1990, soltero y estudiante al constituir la sociedad.
  - 2014: socio fundador y presidente, con Melanie Denise Brahim como directora suplente (BO, 20-ene-2014).
  - 2018: presidente por tres ejercicios, con Melanie Denise como directora titular y Cindy Daniela Brahim como directora
    suplente (asamblea del 22-oct-2018, BO del 11-sep-2019).
  - Desde la asamblea del 20-dic-2024 (publicada el 28-ene-2026): **director suplente**. Presidenta: Cindy Daniela Brahim;
    vicepresidenta: Nora Beatriz Chervin (indicadores.ar).
- No se encontraron LinkedIn, prensa ni redes con ese nombre.
- **Cómo escribe:**
  - mandó una lista ordenada de requisitos, con los puntos típicos de una comparación de proveedores (número, portabilidad,
    abono, simultáneas, costo de IA, integración, dónde se guardan los datos, retención, prueba);
  - usa términos técnicos: "SIP", "streaming de audio bidireccional", "documentación técnica";
  - rechazó la reunión dos veces ("Me gustaría que me respondan por este medio si es posible hacer esto") y aceptó a la
    tercera;
  - el agente esquivó las preguntas técnicas tres veces. La propuesta tiene que responderlas una por una.

## 2. La empresa: CIMEPA S.A.

### 2.1 Datos

| Dato | Valor | Fuente |
|---|---|---|
| CUIT · IGJ | 33-71547037-9 · 1.876.473 | BO 2019 |
| Constitución | Escritura 1, 8-ene-2014, escribana María Alejandra Cubas, Registro 111 | BO 2014 |
| Objeto | Fiduciario (salvo fideicomisos financieros), mandataria y administración de bienes y títulos, inversiones y operaciones financieras | BO 2014 |
| Capital inicial | $120.000 | BO 2014 |
| Actividad declarada | Servicios inmobiliarios con bienes propios o arrendados (CIIU 681098) | indicadores.ar |
| Empleados | Ninguno registrado | indicadores.ar |
| Domicilios | Fiscal: Washington 4179, CABA. Sede: Av. Córdoba 817 y luego 836, piso 2, of. 210, CABA (lo comparten 151 sociedades) | BO, indicadores.ar |
| BCRA | $497 mil de deuda (ago-2026), situación 1, sin cheques rechazados | indicadores.ar |
| Directorio vigente | Cindy Daniela Brahim (presidenta), Nora Beatriz Chervin (vice), Pablo Kevin Brahim (suplente) | indicadores.ar |

### 2.2 Vínculos

- Según indicadores.ar comparte 4 personas con **Dabra S.A.** y con **Fabra SA**, 2 con Testai S.A. y 1 con Brahim Hermanos
  S.A. y con Karias S.A.
- **Dabra S.A.** (CUIT 30-63848573-3, desde 1990):
  - retail de calzado deportivo, con capital de $640 M (balance de jun-2025) y deuda bancaria de unos $9.200 M (jul-2026);
  - en 2021 absorbió NS3 Internet S.A.;
  - Modaes la presenta como dueña de Dexter, Stock Center, Moov, Lotto y Tienda River;
  - La Nación cita a Roberto Daniel Brahim como su presidente.
- **Que la "línea de trabajo" sea de Dabra no está verificado.** Si lo fuera, el volumen y el caso cambian (un retailer con
  centro de contacto).

### 2.3 Contacto

- Solo el WhatsApp de Pablo. No hay sitio, email ni teléfono publicados.
- **No confundir:** cimepa.com es el Circuito Mexicano de Pádel (Shopify, México), y SIMEPA es la prepaga de La Pampa.

### 2.4 Lo que contó (canal y pedido)

- **Por WhatsApp, con el agente** (texto en el CRM): las 4 necesidades y estas preguntas:
  - número argentino y portabilidad de una línea existente;
  - abono, alta, minutos, simultáneas y costos de IA;
  - cómo se integra el contexto y cómo se reciben los resultados;
  - dónde se procesan y guardan audios y transcripciones, por cuánto tiempo, y si se puede apagar la grabación;
  - si hay prueba con llamadas humanas y de IA en el mismo número.
- **Con Laureano** (resumen del usuario):
  - Laureano ofreció salientes por API, una herramienta de transferencia (bridge al número que quieran), atender desde la
    plataforma, varios números, todo registrado y una demo;
  - quedó en mandar "info de cómo sería la propuesta y la demo".

## 3. Productos y precios de referencia

- **La propuesta va sin precios** (decidido con Laureano).
- Nuestros planes publicados, como referencia interna (`landing/src/data/site.ts`):
  - Sucursal: $99.000 por mes, 1.200 min, 3 llamadas a la vez, 3 números;
  - Red: a medida.
  - El pedido de CIMEPA (3 números o más, 3 simultáneas o más, humanos, agente externo) cae en Red.
- **Mercado** (`comercial/demanda-y-mercado-local.md`):
  - Twilio a celular argentino, USD 0,353/min; DID, USD 6-8 por mes;
  - plataformas BYOK: Vapi USD 0,05/min, Retell 0,07 y Twilio ConversationRelay 0,07, sin telefonía.

## 4. Competencia y contexto

### 4.1 Lo que evaluaría Pablo

Hipótesis:

| Alternativa | Qué le resuelve | Contra |
|---|---|---|
| Twilio (Elastic SIP, Media Streams, Voice SDK) | Todo: softphone web y móvil, agente propio por streaming, transferencia y grabación | Caro a celular argentino; números locales con trámite; se paga en USD |
| Telnyx, Vonage, Plivo | Igual que Twilio | Terminación internacional |
| Vapi o Retell con SIP propio | Agente, transferencia y grabación | El agente es de ellos, pero sobre su plataforma; pagan en USD y aparte la telefonía |
| Aircall, Ringover, Zadarma | Softphone, números y grabación | El agente de IA externo es secundario |
| Central virtual de Anura | Número argentino, WebPhone, app de celular, grabación y transferencia entre internos | Conectar el agente lo resuelven ellos |

### 4.2 Contexto

- **Nuestra ventaja frente a Twilio:** terminación local, inferencia y datos en Argentina (preguntó dónde se guardan), y
  factura en pesos.
- **Riesgo:** es el segmento "plataforma para desarrolladores" donde el plan dice no invertir todavía (sección 2.3). Vale si
  hay un piloto pago o si el caso aparece en 3 conversaciones (sección 0).

## 5. Dolores detectados (con evidencia)

- **D1. Sin telefonía para el equipo:** "Que una persona haga y reciba llamadas desde su computadora o celular", con
  empleados remotos y sin teléfono.
- **D2. Agente propio sin línea:** "Necesitamos conectar un asistente propio que gestione la conversación de voz en tiempo
  real, no solamente enviar contexto al agente de ustedes".
- **D3. Registro y datos:** "que las conversaciones queden grabadas". También preguntó dónde se procesan, la retención y si
  se puede apagar la grabación.
- **D4. Pasar la llamada en los dos sentidos:** "¿Permiten transferir llamadas tanto de IA a persona como de persona a IA?".
- **D5. Quiere respuestas concretas:** pidió "documentación técnica y costos" y que le respondan por WhatsApp.

## 6. Pistas de interés en voz, WhatsApp e IA

- Ya decidió usar IA de voz en salientes de seguimiento y entrantes: no hay que convencerlo de la IA, sino de la
  integración.
- No dijo para qué son las salientes (ventas, cobranzas, postventa). Es la primera pregunta de la charla.
- WhatsApp "más adelante": lo tenemos en producción (texto, notas de voz, plantillas y llamadas).
- El usuario anotó "probó la demo, quiere reunión" (nota del 22-oct). No se encontró una llamada de la demo atribuible a
  Pablo: puede referirse a la charla por WhatsApp.

## 7. El mejor caso de uso: un número de la empresa para personas y para su agente

### 7.1 La propuesta (diseño elegido, de [`cimepa-telefonia.md`](cimepa-telefonia.md))

Todo en nuestra webapp, sin la central de Anura: Anura queda solo como troncal (números y caller ID) y todo pasa por rooms
de LiveKit.

- **Saliente de un empleado:**
  1. el empleado entra al cliente web (como `web/src/llamar/`, con sesión), busca en la agenda `contacts` y aprieta "Llamar";
  2. el backend crea la room, suma al empleado por WebRTC y marca al contacto con `create_sip_participant`, desde el número
     de la empresa o el del empleado.
- **Entrante:**
  1. la atiende el agente;
  2. para derivar usa la herramienta `transferir`: suma a la persona a la room (al cliente web si está en línea, o a su
     celular por PSTN), le pasa un resumen y sale;
  3. si no atiende nadie, vuelve el agente y toma el mensaje.
- **Persona → IA:** un botón en el cliente web vuelve a sumar al agente con el contexto.
- **Grabación y transcripción:**
  - un participante silencioso (el worker en modo escucha) sigue en la room después de la transferencia;
  - graba y transcribe cada pista con el STT propio, con el mismo historial y la misma API que las llamadas del agente;
  - la alternativa es LiveKit Egress, que hoy no está en el compose.

**Decidido con Laureano (22-oct-2026):**
- **Entrantes:** las atiende el agente y las deriva a los **teléfonos reales** de los empleados (bridge por PSTN), no al
  cliente web. Recibir en la web se puede sumar después.
- **Salientes de las personas:** desde el cliente web, con la agenda.
- **3 números o más** para la empresa y **3 llamadas simultáneas o más**.
- **Agente propio:** cómo se integra (token de LiveKit, SIP u otro) se define en una charla técnica.
- **Propuesta sin precios**, solo con el detalle de la solución.
- **Por definir:** aviso de grabación y retención, y caller ID por empleado o compartido.

Opciones para conectar su agente, para la charla técnica (de `cimepa-telefonia.md`):

| Vía | Cómo | Para qué plataforma |
|---|---|---|
| SIP | Endpoint en Asterisk para su plataforma (IP fija y clave). El DID o una extensión rutea a su SIP URI, y las salientes salen por el mismo trunk con el caller ID de la empresa | Vapi, Retell, Twilio, LiveKit, Pipecat |
| Participante de LiveKit | Un token para que su worker (LiveKit Agents o Pipecat) entre a la room | Si construyen el agente ellos |
| Audio por WebSocket | AudioSocket o WebSocket de Asterisk, como Twilio Media Streams | Si su agente ya habla eso |
| Nuestro motor con sus herramientas | Motor `assistant` con tools o webhooks a su backend; también nuestra API de inferencia | Si todavía no tienen agente |

En las tres primeras la llamada pasa por nuestro lado: grabación y transcripción quedan nuestras aunque hable su agente.

### 7.2 Por qué es el mejor caso

- Responde las 4 necesidades con un solo número y un solo historial, para personas y agente.
- Usa lo que ya tenemos: número argentino, LiveKit, Asterisk, salientes por API, transcripción y audios por API, y STT
  propio.
- La derivación al celular real evita que los empleados instalen nada para recibir (el punto débil de un softphone en
  iOS).
- Datos e inferencia en Argentina: responde la pregunta de dónde se guardan.

### 7.3 Guion de la demo (5 minutos)

1. **Lo que ya existe:** nuestro agente hace una saliente de seguimiento por API al celular de Pablo, con un contexto que
   nos pase él ("seguimiento de tu consulta del martes").
2. Al cortar, la transcripción y los audios aparecen por `GET /api/v1/calls/{id}` y en el panel.
3. Pablo llama al número: atiende el agente y él dice "quiero hablar con una persona". **Momento wow:** suena el celular de
   Laureano, que recibe el resumen y sigue la charla, mientras la transcripción sigue en el mismo historial. Requiere tener
   antes la herramienta `transferir` y el participante silencioso. Si no están, la demo cubre solo los pasos 1 y 2.
4. Explicar con el diagrama cómo entra su agente (SIP o participante de LiveKit).

### 7.4 Qué hay hoy y qué falta (verificado contra los docs, 22-oct-2026)

| Pieza | Estado |
|---|---|
| Número argentino (Anura); entrantes y salientes con ese caller ID | Hecho |
| Saliente del agente por API, transcripción y audios por API | Hecho |
| Campañas de llamadas con webhook de resultados | Implementado el 19-oct, sin desplegar |
| Grabación | Por mensaje (un WAV por turno, opcional por agente), no la llamada entera |
| Retención y aviso de grabación | Sin política; la privacidad de la landing dice que no se graba audio: corregir antes de grabar a un cliente |
| Cliente web para que llamen las personas | No existe (base: `web/src/llamar/`) |
| Herramienta `transferir` y derivación al celular | No existe |
| Participante silencioso que graba y transcribe después de transferir | No existe |
| Agente de un tercero en la línea (SIP, token de LiveKit o WebSocket) | No existe (sí la API de inferencia y BYOK de LLM) |
| Portabilidad de una línea existente | No: Anura no deja ceder números (cl. 26). Confirmar con Anura la portabilidad entrante |
| Llamadas simultáneas | Por tier; con Gemma **sin medir** (no citar CAP-001) |

### 7.5 Fases sugeridas

1. **Demo (esta semana):** un número, nuestro agente con salientes por API y su contexto, y transcripciones y audios por API.
2. **Charla técnica:** con qué está hecho su agente, cuántos empleados y llamadas por día, qué CRM usan, retención, si
   quieren las grabaciones en su infraestructura y el caller ID.
3. **Antes del piloto:**
   - herramienta `transferir` con derivación al celular;
   - participante silencioso (grabación de la llamada entera y transcripción);
   - cliente web de salientes;
   - integración de su agente por la vía elegida.
4. **Después:** recibir en la web y WhatsApp.

### 7.6 La oferta

- Propuesta técnica sin precios: el diseño de 7.1, qué existe hoy y qué se construye con plazo, y la demo.
- Piloto de 30 a 60 días con 3 números y 3 simultáneas, con alcance acotado y métricas (llamadas, transferencias,
  contactabilidad y resultado capturado), según la sección 5 del plan.
- El precio queda pendiente: lo define Laureano después de la charla técnica.

## 8. Base para el prompt del agente

### 8.1 Rol y tono

Si usan nuestro motor: asistente de seguimiento de la empresa, formal, breve y en voseo, con el contexto que carga su
sistema por variables. Si usan su agente, esta parte es de ellos.

### 8.2 Reglas

- No inventar nada fuera del contexto recibido. Confirmar la identidad antes de dar datos.
- Si piden una persona: herramienta `transferir`. Si nadie atiende, tomar el mensaje.
- Si piden no recibir más llamadas, marcar la baja.
- Avisar que la llamada se graba (texto por definir con ellos).

### 8.3 Triage y datos

| Salida | Cuándo | Datos |
|---|---|---|
| Resuelto | Respondió lo que el seguimiento pedía | Resultado, fecha y comentario |
| Volver a llamar | No puede ahora | Día y hora |
| Transferir | Pide una persona o un tema fuera del guion | Motivo y resumen para el empleado |
| No contactar | Pide no recibir más llamadas | Marca de baja |

El resumen y el resultado van por API (y por webhook cuando estén las campañas).

### 8.4 Preguntas para la charla técnica

1. ¿Cuál es la línea de trabajo y a quién llaman en el seguimiento? ¿Cuántas llamadas por día y cuántas a la vez?
2. ¿El agente ya existe? ¿Con qué está hecho y qué protocolo habla (SIP, WebSocket, LiveKit)? ¿Qué probaron antes (Twilio,
   Vapi, Anura) y por qué no les cerró?
3. ¿Cuántos empleados? ¿Derivamos a su celular o quieren atender en la web? ¿Caller ID compartido o uno por persona?
4. ¿Dónde tienen que quedar las grabaciones y por cuánto tiempo? ¿Qué CRM o sistema recibe los resultados?
5. ¿Qué tiene que pasar en 30 días para seguir? ¿Quién decide?

## 9. Fuentes

Leídas el 22-oct-2026:

- **Conversación de WhatsApp:** https://app.atentina.com.ar/calls/4a0e11f1-c20d-436c-9dad-d166c77172fa
- **Boletín Oficial:**
  - https://www.boletinoficial.gob.ar/pdf/linkQR/eDlrUW91MFBqOVoreFpJZ1U0d1UwZz09 (constitución, 20-ene-2014)
  - https://www.boletinoficial.gob.ar/pdf/linkQR/bTRvakRVWWVscHQreFpJZ1U0d1UwZz09 (directorio, 11-sep-2019)
- **indicadores.ar:** https://www.indicadores.ar/empresa/33715470379 · https://indicadores.ar/empresa/30638485733-dabra
- **Prensa sobre Dabra:**
  - https://www.modaes.com/empresas/el-dueno-de-la-argentina-dexter-ficha-al-ex-director-de-netshoes-como-gerente-general
  - https://www.lanacion.com.ar/economia/dexter-debuta-en-el-futbol-con-lotto-nid342136
- **Homónimo sin relación:** https://cimepa.com
- **Internos:** [`cimepa-telefonia.md`](cimepa-telefonia.md), `comercial/proveedores/anura-terminos-2026.md`,
  `comercial/demanda-y-mercado-local.md`, `landing/src/data/site.ts`, `docs/features/CAMPANAS.md`,
  `docs/features/LLM_CONEXIONES.md`
