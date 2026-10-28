# Presentación para Yoizen: Tu propio agente

Diapositivas 16:9 para compartir pantalla en una videollamada con Yoizen. Laureano explica en vivo cómo los bots
que Yoizen ya tiene se conectan a Atentina con la función **Tu propio agente** (motor `external`): su orquestador
detrás de un endpoint compatible con la API de OpenAI, y Atentina pone el número, las llamadas, WhatsApp, el link
para llamar, la transcripción, los turnos e interrupciones, la voz, la grabación, los minutos, la derivación y el
registro. Primera presentación del proyecto de documentos (la plantilla 16:9 es `plantilla/slides.css`).

- **Pedido (26-oct-2026, Laureano, textual):** "Puedes crear en vez de un video, un slide tipo presentación para la
  demo con yoisen sobre cómo integrar sus agentes? 'Tu propio agente'. Es para mostrar en una llamada en vivo."
  (La empresa es **Yoizen**, con z.)
- **Destinatario:** Juan Stamati (Yoizen, alianzas y producto), su CTO y el responsable de producto. Tratamiento:
  "ustedes" / "Yoizen" en tercera persona.
- **Objetivo:** que entiendan el contrato (un endpoint, un turno, dos herramientas), que vean que encaja con lo que
  pidieron el 20-oct (sus bots deciden qué decir; Atentina pone la voz y la telefonía) y que salgan de la llamada con
  un próximo paso concreto: un endpoint con uno de sus bots y un caso real para el piloto.
- **Contexto:** la reunión del 20-oct y el material que ya recibieron:
  [`yoizen-propuesta`](../yoizen-propuesta/README.md) (PDF de 2 hojas) y el video técnico
  [`videos/proyectos/yoizen`](../../../videos/proyectos/yoizen/README.md). Yoizen tiene omnicanal digital
  (WhatsApp, web chat, bots sin código, IVR, ACD) en Azure EE.UU., su orquestador no maneja voz y están sumando
  Asterisk; quieren voicebots entrantes y salientes que sus equipos configuren sin depender de Atentina.
  Lo nuevo desde el 20-oct es justamente "Tu propio agente" (25-oct).
- **Formato:** 12 diapositivas de 1920 × 1080 (16:9). Se presenta directo en el navegador a pantalla completa y se
  imprime a PDF 16:9. Pocas palabras y tipografía grande: Laureano habla, la diapositiva acompaña.
  Notas del presentador en [`versiones/v1/NOTAS.md`](versiones/v1/NOTAS.md).

| Paso | Comando |
|---|---|
| Presentar (Chrome; flechas para moverse, F pantalla completa, `#n` en la URL va a una diapositiva) | `make slides-abrir P=yoizen-tu-propio-agente V=1` |
| Imprimir el PDF y una PNG por diapositiva, y controlar | `make slides P=yoizen-tu-propio-agente V=1 DIAPOS=12` |
| Cerrar la versión | `make doc-cerrar P=yoizen-tu-propio-agente V=1` |

## Estructura (v1)

| # | Diapositiva | Qué muestra |
|---|---|---|
| 1 | Portada (oscura) | "Atentina × Yoizen", "Tu propio agente", "Sus agentes, nuestra voz." |
| 2 | El punto de partida | Hoy (su omnicanal), lo que falta (voz) y lo nuevo (Tu propio agente) |
| 3 | Quién pone qué | Pone Atentina / Pone Yoizen (la tabla de la documentación) y "no es cambiar el modelo" |
| 4 | Cómo funciona un turno | Diagrama SVG: persona ⇄ Atentina ⇄ endpoint de Yoizen (`POST /chat/completions`, `stream: true`) |
| 5 | El pedido | HTTP con los headers `X-Atentina-*`, `messages` con toda la conversación y `tools`; cuatro puntos |
| 6 | La respuesta | SSE en pedazos, el primero ya sonando mientras llega el segundo; streaming obligatorio |
| 7 | Dos herramientas | `end_call` (con `outcome`) y `transfer_call` (área, música, retoma) |
| 8 | Un endpoint mínimo | `server.py` acortado (FastAPI): prompt, pedido al modelo con `tools`, stream tal cual |
| 9 | Configurarlo | Tres pasos del panel (conexión, Probar el endpoint, switch) y por API / MCP |
| 10 | Latencia | Línea de tiempo hasta el primer texto; más de un segundo se siente lento; "Dame un segundo que me fijo" |
| 11 | Errores | Falla → mensaje configurado → varios seguidos: corta o pasa al equipo; el contador vuelve a cero |
| 12 | Próximos pasos (oscura) | Su endpoint → conexión y prueba → llamadas de prueba → piloto; qué ponemos nosotros; plan Red; SIP en evaluación; contacto |

## Afirmaciones y de dónde salen

- **Qué pone cada uno, el turno, el pedido, la respuesta, los headers, las herramientas, los tres pasos, API y MCP,
  latencia, errores y plan:** `landing/src/pages/desarrolladores/docs/tu-propio-agente.astro` (publicada en
  atentina.com.ar/desarrolladores/docs/tu-propio-agente, leída el 26-oct-2026) y
  [`docs/features/LLM_CONEXIONES.md`](../../../../docs/features/LLM_CONEXIONES.md).
- **Esqueleto de 9 escenas y qué no se dice:** el guion v2 de
  [`videos/proyectos/tu-propio-agente`](../../../videos/proyectos/tu-propio-agente/README.md): latencia sin cifras
  medidas (ni los 1.672 / 482 ms del ejemplo con DeepSeek, ni los 0,9 s de la propuesta: esa mediana es del motor
  propio, no del externo), errores sin "no hay respaldo con nuestro modelo".
- **Pedido y SSE en pantalla (5 y 6):** los ejemplos `request` y `response` de la página, recortados y con los
  mensajes acortados para que entren a 23 px (`"Hola, soy Sofía. ¿Qué necesitás?"`, host `agente.yoizen.com`
  ilustrativo). Números `+5493515551234` y `+541152630861`, "ventas" y `turno_dado`: los de la página. Sin signos de
  exclamación ("Que andes bien.").
- **`server.py` (8):** la versión acortada de la página (sin el chequeo de la key ni `or 'desconocido'`), con una
  línea partida; el completo es `examples/agente-externo/server.py`. `model="gpt-4.1-mini"` queda como en el
  ejemplo (texto, sin logos).
- **Textos del panel (9):** "Configuración › Modelos › Nueva conexión", "OpenAI compatible", "La key queda cifrada y
  no se vuelve a mostrar", "Probar el endpoint" y "Que conteste tu propio agente", de la página. La línea
  `Tu agente respondió · streaming · «Hola, …»` reproduce el aviso del panel sin la cifra de ejemplo de la documentación (420 ms), para que no se tome por una medición.
- **Latencia (10):** solo el concepto de la página. "Desde Azure EE.UU. se suma la red: a medir en el piloto" sale
  del README del video de Yoizen (20-oct).
- **Plan Red (9 y 12):** sección "Planes" de la página; en la base el tier se llamaba **Central**
  (`tiers.external_agent = true` en Central e Interno, consultado el 26-oct-2026; ese mismo día Central se borró:
  Red es a medida, sin tier, y la función está en Sucursal e Interno). Precio "a medida"
  (`landing/src/data/site.ts`).
- **"La conexión SIP con su Asterisk sigue en evaluación" (12):** como en la propuesta y el video del 20-oct.
- **Contacto (12):** `landing/src/data/site.ts` (0800-220-1233, atentina.com.ar, hola@atentina.com.ar,
  WhatsApp +54 9 351 700-2592, Laureano Arcanio), verificado el 26-oct-2026.
- **Sin logos de terceros:** OpenAI, FastAPI, Azure y Asterisk van solo como texto.

## Estado de la función al 26-oct-2026 (para no prometer de más)

- **Desplegado:** la base está en la migración 0031 (incluye la 0030, `tiers.external_agent`); la imagen de `app`
  del 26-oct trae `app/llm/external.py` (se recreó `app` y `agent` con el despliegue de Términos, commit `7dad845`);
  Central e Interno tienen la función; la página de la landing está publicada. `docs/features/LLM_CONEXIONES.md` y
  `AGENTS.md` todavía dicen "sin desplegar": quedaron desactualizados, no la función.
- **Sin hacer:** la **llamada real de punta a punta** con un endpoint externo (fase 1: solo hay tests con un endpoint
  simulado y el `smoke.py` del ejemplo contra DeepSeek por OpenRouter) y la medición de latencia contra `classic`.
  En la llamada con Yoizen, el endpoint de prueba sería la primera llamada real: decirlo así, no mostrarlo como
  rutina.
- **MCP:** las herramientas `create_llm_connection` y `test_llm_connection` están en el catálogo; falta `make mcp-eval`
  con ellas.
- **A validar con Laureano:** "piloto con un caso real" como en la propuesta (lo ofreció sin costo el 20-oct; la
  diapositiva 12 no dice "sin costo"); "las llamadas a la vez que necesiten" no se afirma (sin CAP con Gemma).

## Versiones

| Versión | Fecha | Qué cambió | Estado |
|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 26-oct-2026 | Primera versión, 12 diapositivas | borrador |
