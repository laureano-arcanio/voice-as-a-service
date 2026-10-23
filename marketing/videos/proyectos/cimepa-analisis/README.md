# CIMEPA S.A.: la propuesta técnica en video, con el formato del PDF

- **Pedido (22-oct-2026, agente principal por Laureano, textual):** "Hacé un video nuevo (proyecto cimepa-analisis, v1)
  para CIMEPA siguiendo el formato y contenido del PDF ya hecho: marketing/documentos/proyectos/cimepa-propuesta/versiones/v1/documento.html
  (leelo completo: es la fuente de textos, cifras y tono) y docs/mercado/demos/cimepa.md. [...] Esta propuesta es técnica,
  no del tipo 'qué hacen bien / dónde mejorar': no hay datos del negocio de CIMEPA. Le hablamos a Pablo, que evalúa
  proveedores de telefonía con IA." Con ocho escenas (~60 s, hasta ~65): intro oscura, lo que nos pidieron (cuatro
  tarjetas con ~0,7 s de respiro), entra una llamada, llama un empleado, llama la IA, todo queda registrado, su agente
  (tres vías) y cierre "¿Agendamos la charla técnica?".
- **Reglas del pedido:** narrador `lucas` a 1×, ortografía normal (grafías solo si una palabra sale mal), pausas con
  puntuación, "En CIMEPA..." para nombrarla, el agente es el logo de Atentina (sin robot), sin logo ni marca de CIMEPA,
  material de venta (no dice qué está construido), sin precios, sin nombrar a Anura ni a Asterisk, mismos textos y
  cifras que el PDF.
- **Contexto:** Pablo escribió el 22-oct-2026 por el WhatsApp de Atentina (lead #365 del CRM). Es el PDF
  [`cimepa-propuesta`](../../../documentos/proyectos/cimepa-propuesta/README.md) v1 en ~65 s. Base:
  [`docs/mercado/demos/cimepa.md`](../../../../docs/mercado/demos/cimepa.md).
- **Público:** Pablo, de CIMEPA S.A. (CABA), técnico, que compara proveedores (Twilio, Vapi, centrales virtuales).
  Trato de "ustedes" / "su", como el PDF.
- **Mensaje:** un número de la empresa para su equipo y su IA, todo grabado y transcripto; la integración de su agente
  se define en una charla técnica.
- **Formato:** 1920 × 1080, 30 fps, 65,2 s. Composición `cimepa-analisis` (`src/Video.tsx`). Solo narrador; el agente
  es `AgenteLogo`.

## Guion (v1; los cambios de v2, en sus [NOTAS](versiones/v2/NOTAS.md))

Locución de `lucas` a 1×, ortografía normal. "CIMEPA" escrito así se dice bien (4 de 4 tomas el STT oye "Cimepa";
`Simepa` no hizo falta). Única grafía, la de la tabla de VIDEOS.md: `ápi` por API. Los pedidos van en cuatro líneas
(c2a a c2d) con ~0,6–0,7 s de respiro (`GAP` 0,35 s + el silencio de cada toma).

| Escena | Tiempo | Locución | Qué se ve |
|---|---|---|---|
| `intro` | 0–6,95 s | c1 (a los 2 s) "Un número de la empresa para su equipo y su IA, todo grabado y transcripto." | Oscura (portada del PDF): logo, "PROPUESTA TÉCNICA · CIMEPA S.A. · OCTUBRE 2026", el h1 del PDF con el remate en acento (se enciende con la voz), "Telefonía con IA para un equipo remoto" y las cuatro cifras: 3 o más números argentinos, 3 o más llamadas simultáneas, nada que instalar, todas grabadas y transcriptas |
| `pedido` | 6,35–20,65 | c2a "En CIMEPA nos pidieron que su equipo remoto llame sin teléfono." · c2b "Que su asistente de IA llame y atienda." · c2c "Transferir entre la IA y una persona." · c2d "Y todo grabado y transcripto, por ápi." | "LO QUE NOS PIDIERON · En sus palabras, **y cómo lo resolvemos.**" Cuatro tarjetas (una por línea), cada una con su cita textual del WhatsApp y su "Cómo:" del PDF |
| `entra` | 20,65–27,85 | c3 "Entra una llamada, y la atiende la IA. Resuelve, o la deriva al celular del empleado, con un resumen." | "ENTRA UNA LLAMADA · La atiende la IA: **resuelve, o deriva con un resumen.**" Su cliente → número de la empresa → logo de Atentina ("Asistente de IA · el suyo o el nuestro") → "Resuelve" o "Celular del empleado" (viaja el "resumen"); tarjeta "RESUMEN PARA EL EMPLEADO" de ejemplo; "Si no atiende nadie, la IA vuelve a la llamada y toma el mensaje." |
| `empleado` | 27,85–36,5 | c4 "Un empleado llama desde la app web, en la compu o el celular: elige el contacto, un clic, y sale con el número de la empresa." | "LLAMA UN EMPLEADO · Desde la app web, **con el número de la empresa.**" Ventana "PANTALLA DE EJEMPLO" con la agenda; el cursor elige un contacto y hace clic en "Llamar"; barra "Llamando a Marina Sosa · sale con el número de la empresa"; la misma app en un celular; su cliente recibe "TE LLAMA · Número de la empresa" |
| `ia` | 36,5–43,4 | c5 "Llama la IA: seguimientos programados por ápi, con su contexto y sus instrucciones." | "LLAMA LA IA: SEGUIMIENTOS PROGRAMADOS · Por API, **con su contexto y sus instrucciones.**" `POST /api/v1/calls` con el cuerpo del PDF (hoja 4), lista "PROGRAMADOS · HOY" de ejemplo ("Una a una o en campañas: horario, reintentos y llamadas en paralelo."), el pedido viaja al logo, que llama al contacto; chips CONTEXTO e INSTRUCCIONES |
| `registro` | 43,4–52,5 | c6 "Todo queda registrado: grabación y transcripción de toda la llamada, en el panel y por ápi. Inferencia propia, en Argentina." | "TODO QUEDA REGISTRADO · Personas e IA en la misma llamada, **con un solo registro.**" (hoja 3). Llamada de ejemplo: audio de toda la llamada coloreado por quién habla, transcripción con IA, Cliente y Persona, "la IA transfiere a Martín, con un resumen"; "En el panel" y `GET /api/v1/calls/{id}` con campos reales; banda "INFERENCIA PROPIA · SERVIDORES EN ARGENTINA" (reconocimiento de voz, modelo de lenguaje, voz) |
| `agente` | 52,5–61,8 | c7 "Su agente: tres vías, para definir en una charla técnica. En tiempo real, por SIP, o nuestro agente, con su contexto y su modelo." | "INTEGRACIÓN DE SU AGENTE · Su agente en la línea de la empresa: **la vía la elegimos juntos.**" Las tres tarjetas de la hoja 4 (En tiempo real, por WebRTC · Por SIP · Nuestro agente, con lo suyo), que se encienden con la voz; "En las tres, la llamada pasa por la plataforma: [...] hable quien hable." |
| `cierre` | 61,8–65,2 | c8 "¿Agendamos la charla técnica?" | Oscura: la pregunta; abajo, chico, el logo y atentina.com.ar · 0800-220-1233 |

## Afirmaciones y de dónde salen

Todo del PDF `cimepa-propuesta` v1 (leído el 22-oct-2026) y de `cimepa.md`:
- **Portada (h1, bajada y las cuatro cifras):** hoja 1. "3 o más números" y "3 o más simultáneas": decidido con
  Laureano (cimepa.md, 7.1).
- **Las cuatro citas:** textuales del WhatsApp del 22-oct (cimepa.md, parte 5), las mismas del PDF; los "Cómo:", de la
  hoja 1, un poco recortados para entrar en dos líneas.
- **Los tres flujos y el registro:** hoja 3 (diagrama y tarjetas 1 a 4) y hoja 2 (tabla). "Inferencia propia en
  Argentina": hojas 1 y 2.
- **Las tres vías:** hoja 4, con sus textos (LiveKit aparece como estándar de integración, como en el PDF).
- **API:** `POST /api/v1/calls` con `agent_id`, `contact_id`, `from_number_id` y `context` (`CallIn` en
  `app/api/schemas.py`); `GET /api/v1/calls/{id}` con `outcome.label`, `messages[].role/text/recording` y
  `call.duration_seconds` (`CallDetail`). Los valores son de ejemplo.
- **Ilustrativo (rotulado en los pies):** el resumen, la agenda y sus nombres, los horarios programados, la llamada de
  ejemplo con su transcripción y duración, la pantalla de la app web.
- **Contacto:** `landing/src/data/site.ts`.
- **No construido hoy (el video no lo dice, a propósito; cimepa.md, 7.4):** app web para que llamen las personas,
  herramienta de transferencia y derivación al celular, vuelta de persona a IA, grabación de la llamada entera
  (hoy es un WAV por mensaje y opcional) con los tramos de personas, agente de un tercero por WebRTC o SIP. Campañas
  con webhook: implementadas, sin desplegar. Capacidad con Gemma sin medir ("3 o más simultáneas" es la oferta, no
  una medición).

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 22-oct-2026 | 65,2 s | Primera versión (narrador lucas) | cerrada (22-oct-2026) |
| [v2](versiones/v2/NOTAS.md) | 22-oct-2026 | 64,6 s | Voces paula (narradora) y pablo (los cuatro pedidos); escena entra rehecha con el panel y la transcripción; registro pasa a lo que recibe su sistema por API | borrador |
