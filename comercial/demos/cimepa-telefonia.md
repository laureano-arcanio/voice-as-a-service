# CIMEPA: cómo resolver la telefonía (humanos + agente propio + transferencia)

22-oct-2026. Contexto comercial en [`cimepa.md`](cimepa.md) (el contacto se confundió al principio con Simepa, de La Pampa).

## Qué piden

1. Empleados remotos, sin teléfono, que llamen y atiendan desde la compu o el celular con el número de la empresa.
2. Un agente de IA **propio** (no el nuestro) que haga salientes de seguimiento y atienda, por SIP o audio en tiempo real.
3. Transferencia IA ↔ persona, en los dos sentidos.
4. Todo grabado, con transcripción accesible por API.
5. WhatsApp más adelante.

## Qué tenemos hoy y qué falta

| Pieza | Estado |
|---|---|
| Número argentino (Anura), entrantes y salientes con ese caller ID | Hecho (Asterisk ↔ LiveKit) |
| Saliente del agente por API (`POST /api/v1/calls`), transcripción y audios por API (`GET /calls/{id}`, `/recordings/{n}`) | Hecho |
| Campañas de llamadas con webhook de resultados | Implementado, sin desplegar |
| Grabación | Por mensaje (WAV por turno), no la llamada entera en estéreo |
| Llamadas de personas (softphone) | **No** |
| Transferencia (herramienta del agente o de la persona) | **No** |
| Agente de un tercero conectado a nuestra línea | **No** (sí pueden usar nuestro LLM/STT/TTS por la API de inferencia) |

## Opciones para que los empleados llamen

| Opción | Cómo | A favor | En contra | Esfuerzo |
|---|---|---|---|---|
| **A. Central virtual de Anura** | Internos de Anura con su WebPhone (navegador), app de escritorio y softphone de celular. El agente (nuestro o de ellos) es un interno o troncal más de la misma central | Ya existe: grabación incluida, hasta 3 dispositivos por interno, transferencia entre internos nativa | Las grabaciones de los humanos quedan en Anura (exporta a Drive/Dropbox/servidor propio); la transcripción la sumamos nosotros leyéndolas | Bajo. **A verificar con Anura:** que un interno o troncal SIP de la central pueda ser nuestro Asterisk y que la transferencia a ese interno funcione |
| **B. Internos en nuestro Asterisk + softphone de terceros** | Un endpoint PJSIP por empleado (TLS + SRTP, ya tenemos el certificado de `sip.atentina.com.ar`), apps Zoiper / Linphone / MicroSIP; salen por Anura con el DID de la empresa; `MixMonitor` graba la llamada entera | Todo pasa por nosotros: grabación y transcripción uniformes; transferencia SIP estándar (ciega y atendida) a la extensión del agente | Abre registro SIP a internet: riesgo de fraude telefónico (claves fuertes, solo TLS, fail2ban, tope de llamadas por endpoint); en celular, para recibir con la app cerrada hace falta push (Zoiper/Linphone lo tienen, a veces pago) | Medio: días |
| **C. Softphone dentro del dashboard** | Página de discado en `web/`, el empleado entra por WebRTC a una room de LiveKit y marcamos al cliente con `create_sip_participant` (como el link para llamar, al revés) | Mejor integración: cada llamada humana queda en el mismo historial, con transcripción de nuestro STT; transferir es mover participantes en la room | Recibir llamadas exige presencia y timbre en el navegador; en el celular solo con la pestaña abierta (iOS no despierta una PWA para una llamada) | Alto: semanas |
| **D. Click-to-call al celular del empleado** | Desde la web: "llamar a X" → llamamos primero al celular del empleado y, cuando atiende, al cliente, con el número de la empresa | Sirve con cualquier teléfono existente, sin instalar nada | Dos patas de minutos por llamada; no resuelve recibir | Bajo-medio |

- **"La webapp accede a los contactos del teléfono":** la Contact Picker API solo anda en Chrome de Android y el usuario elige uno por uno; en iOS no existe. Mejor la agenda `contacts` (ya existe, API `/api/v1/contacts`) cargada desde su CRM por API.
- **"Bridge local" con las líneas existentes (gateway GSM con SIMs):** no recomendado. Las operadoras detectan y bloquean SIMs usadas como "SIM box", la calidad depende de la cobertura del lugar y no se puede usar el número para entrantes de varios a la vez. Si quieren conservar un número, **portabilidad** a Anura (a confirmar con Anura).

## Conectar el agente propio de ellos

| Vía | Cómo | Para qué plataforma |
|---|---|---|
| **SIP** | Endpoint en Asterisk para su plataforma (IP fija + clave); el DID o una extensión rutea a su SIP URI y ellos sacan salientes por el mismo trunk con el caller ID de la empresa | Vapi, Retell, Twilio, LiveKit, Pipecat, cualquiera con SIP |
| **Participante de LiveKit** | Les damos un token para unirse a la room de la llamada (su worker de LiveKit Agents o Pipecat) | Si construyen el agente ellos mismos |
| **Audio por WebSocket** | AudioSocket / WebSocket de Asterisk, estilo Twilio Media Streams | Solo si su agente ya habla eso |
| **Nuestro motor con sus herramientas** | Motor `assistant` con tools/webhooks a su backend: el contexto y las reglas los ponen ellos | Si no tienen agente propio todavía. Pueden usar además nuestra API de inferencia (LLM/STT/TTS) |

En las tres primeras la llamada sigue pasando por Asterisk: grabación y transcripción quedan de nuestro lado aunque el que habla sea su agente.

## Transferencia

- **IA → persona:** herramienta `transferir` en el agente. Transferencia atendida: el agente suma al empleado a la room (`create_sip_participant` a su interno o celular), le pasa un resumen y sale. La ciega (SIP REFER) depende de que Anura la acepte: mejor resolverla en Asterisk.
- **Persona → IA:** transferencia del softphone a la extensión del agente (opciones A y B) o botón en el dashboard (opción C). El agente arranca con el contexto de la llamada (número, contacto, notas) por variables.
- Con agente propio por SIP, la transferencia es SIP estándar entre su endpoint y los internos.

## Recomendación

1. **Demo (esta semana):** un número de Anura, nuestro agente haciendo salientes de seguimiento por API con el contexto que nos pasen, transcripciones y audios por API. Lo que ya existe.
2. **Humanos:** proponer **A** si Anura confirma que el agente puede ser un interno de la central (lo más rápido y robusto, incluye app de celular); si no, **B**. La **C** queda como evolución.
3. **Su agente:** por **SIP** contra nuestro Asterisk, con grabación y transcripción nuestras.
4. **A construir antes del piloto:** grabación de la llamada entera (estéreo, `MixMonitor`), herramienta de transferencia, endpoint SIP para su agente, y (con B) los internos con su seguridad.

## Pendientes a preguntar

- A Anura: central virtual + troncal o interno SIP hacia un Asterisk propio en la misma cuenta; API o export de las grabaciones; precio por interno; portabilidad entrante de un número existente (la cláusula 26 de su contrato no deja ceder números: confirmar qué cubre).
- A CIMEPA (charla técnica): cuántos empleados y llamadas por día; con qué está hecho su agente (plataforma, si habla SIP); qué CRM usan; si necesitan quedarse con las grabaciones en su infraestructura; retención.

Fuentes Anura: [central virtual](https://www.anura.com.ar/soluciones/central-virtual/), [funcionalidades](https://www.anura.com.ar/telefonia-ip/funcionalidades/), [integrar plataformas](https://www.anura.com.ar/partners/integrar-plataformas/).

## Diseño elegido (22-oct-2026): todo en nuestra webapp

Sin central de Anura: Anura queda solo como troncal (números y caller ID). Todo pasa por rooms de LiveKit.

- **Saliente de un empleado:** web client (como `web/src/llamar/`, logueado) con la agenda `contacts` → "Llamar" → el backend crea la room, suma al empleado por WebRTC y marca al contacto con `create_sip_participant` desde el número de la empresa (o el del empleado).
- **Entrante:** la atiende el agente. Para derivar, usa la herramienta `transferir`: suma a la persona a la room (al web client si está en línea, o a su celular por PSTN), le pasa un resumen y sale. Si no atiende nadie, vuelve el agente y toma el mensaje.
- **Persona → IA:** botón en el web client que vuelve a sumar al agente con el contexto.
- **Grabación y transcripción:** un participante silencioso (el worker en modo escucha) sigue en la room después de la transferencia. Graba y transcribe cada pista con el STT propio, con el mismo historial y la misma API que las llamadas del agente. La alternativa es LiveKit Egress, que hoy no está en el compose.

Decidido con Laureano el 22-oct-2026:

- **Entrantes:** las atiende el agente y las deriva a los **teléfonos reales** de los empleados (bridge por PSTN), no al web client. Recibir en la web se puede sumar después.
- **Salientes de las personas:** desde el web client, con la agenda.
- **3 números o más** para la empresa y **3 llamadas simultáneas o más**.
- **Agente propio de ellos:** a definir en una charla técnica (cómo se integra: token de LiveKit, SIP u otro).
- **Propuesta sin precios**, solo el detalle de la solución.

Por definir: aviso de grabación y retención; caller ID por empleado o compartido.
