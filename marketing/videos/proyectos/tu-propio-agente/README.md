# Tu propio agente (custom LLM)

El video de la página `/desarrolladores/docs/tu-propio-agente`: una empresa que ya tiene su agente de IA lo pone
detrás de un endpoint compatible con OpenAI, y Atentina le pone el número, los canales y la voz.

## Pedido

> (25-oct-2026, resumido fiel) Video nuevo, proyecto `tu-propio-agente`, v1, siguiendo marketing/VIDEOS.md. Es el video
> de la página de documentación `/desarrolladores/docs/tu-propio-agente`, hermano de `mcp-claude-code`,
> `api-desarrolladores` y `docs-intro`: mismo estilo, formato y tono, horizontal 16:9, con locución del TTS propio
> y subtítulos, paula narradora y gonzalo en alguna línea secundaria. 60 a 100 s. Qué es la función: el agente
> del cliente (su prompt, sus herramientas, su estado) detrás de un endpoint compatible con la API de OpenAI
> (`POST /chat/completions`, `stream: true`); Atentina pone el número, las llamadas entrantes y salientes,
> WhatsApp, el link para llamar, la transcripción, los turnos e interrupciones, la voz, la grabación, los minutos,
> la derivación y el registro; en cada turno manda toda la conversación (datos en headers `X-Atentina-*`) y dice lo
> que responde a medida que llega. `end_call` (con el resultado) y `transfer_call`. Tres pasos: conexión, "Probar
> el endpoint", switch "Que conteste tu propio agente". Panel, API (key `calls`) o MCP. Mensajes: no hace falta
> construir el pipeline de voz; el primer texto es lo que más pesa (menos de un segundo); si el endpoint falla, el
> agente avisa y corta o deriva (sin respaldo con nuestro modelo). Plan Red. Fuente de verdad:
> `tu-propio-agente.astro` y `docs/features/LLM_CONEXIONES.md`; datos medidos: 1.672 ms en frío y 482 ms con el ejemplo
> y DeepSeek V4.1 Flash por OpenRouter. Cuidar las grafías. Entregar MP4, README, notas, fila en
> `marketing/README.md` y título y descripción para YouTube. No subirlo ni tocar la landing; sin commit.

## Público, mensaje y formato

- **Público:** desarrolladores y equipos que ya tienen su agente de IA (LangGraph, n8n, su backend) y quieren
  atender llamadas y WhatsApp sin armar la parte de voz.
- **Mensaje:** tu agente decide qué decir; Atentina pone la voz, el número y los canales. Tres pasos.
- **Formato:** 1920 × 1080, 30 fps, 93,0 s (v2; v1, 86,0 s). Composición `tu-propio-agente` (`src/Video.tsx`). Subtítulos quemados
  (abajo al centro, con la grafía normal) y música de `scripts/musica.py`.
- **Publicado (v1, 25-oct-2026):** https://youtu.be/Nw2lrBYmEqs. v2 (latencia sin cifras medidas y errores sin
  "sin respaldo"), sin subir.
- **Contexto:** al principio de `/desarrolladores/docs/tu-propio-agente`, como los videos de MCP y API en sus páginas.

## Guion (v2)

| Escena | s | Voz | Qué se dice | Qué se ve |
|---|---|---|---|---|
| `intro` | 8,4 | t1 paula | ¿Ya tenés tu agente de IA? Conectalo a Atentina, y atiende llamadas y WhatsApp con un número argentino, sin armar la parte de voz. | Fondo oscuro: logo, "TU PROPIO AGENTE · CUSTOM LLM", "Tu agente, **nuestra voz.**", `tu endpoint · POST /chat/completions · stream: true`, chips Llamadas, WhatsApp, Link para llamar y Número argentino, "Sin armar el pipeline de voz" |
| `reparto` | 9,8 | t2 paula | Atentina pone el número, los canales, la transcripción, los turnos, la voz y los minutos. Tu agente pone el prompt, las herramientas, la memoria, y qué responder. | "Atentina pone la voz, **tu agente, las respuestas.**" Dos tarjetas con la tabla "Pone Atentina / Pone tu agente" de la página |
| `turno` | 11,0 | t3 paula | En cada turno, Atentina le manda a tu endpoint toda la conversación, en el formato de OpenAI. Tu endpoint contesta en streaming, y cada pedazo de texto pasa a voz apenas llega. | Diagrama persona → Atentina → tu endpoint con paquetes (voz y "Aa"); el pedido con headers `X-Atentina-*`, `messages` y `tools`, y la respuesta SSE en dos pedazos que Atentina dice a medida que llegan |
| `herramientas` | 8,8 | t4 gonzalo | Para cortar o pasar la llamada a una persona, tu agente usa dos herramientas: una corta y elige el resultado, la otra transfiere a tu equipo. | Tarjetas `end_call` (con `outcome`) y `transfer_call` (área, música, retoma); el pedazo SSE con `tool_calls` de la página y "Resultado `turno_dado`" |
| `ejemplo` | 8,2 | t5 paula | Un endpoint mínimo agrega su prompt y le pasa todo a su modelo, en streaming. El resto es tuyo. | `server.py` acortado como en la página, con el prompt, el pedido al LLM y el stream resaltados; tarjeta de `examples/agente-externo/server.py` |
| `configurar` | 14,6 | t6 paula + t7 gonzalo | Se configura en tres pasos… La probás. Y en el agente, prendés que conteste tu propio agente. / También se hace por API, con una API key de llamadas, o desde tu agente de IA por MCP. | Tres pasos con el panel recreado: Nueva conexión (OpenAI compatible, Nombre, URL base, API key), Probar el endpoint con el aviso "Tu agente respondió", el switch y Endpoint/Modelo; "Por API" y "Por MCP" con rutas y herramientas; "Incluido en el plan Red" |
| `latencia` | 15,2 | t8 paula | Lo que más pesa es el tiempo hasta el primer texto: desde que tu endpoint recibe el pedido hasta que manda el primer pedazo. Tu modelo, tus herramientas y tu servidor se notan en la llamada. Si pasa de un segundo, la conversación se siente lenta, con silencios. | "Tiempo hasta el primer texto · time to first token": una barra que crece de "Tu endpoint recibe el pedido" a "Manda el primer pedazo de texto", y "Atentina lo dice en voz"; tarjetas Tu modelo, Tus herramientas, Tu infraestructura; "Más de 1 s: se siente lenta, con silencios"; consejo "Dame un segundo que me fijo". Sin cifras medidas |
| `errores` | 8,2 | t9 paula | Si tu endpoint falla, el agente dice el mensaje que configuraste. Y con varios errores seguidos, corta o pasa la llamada a tu equipo. | Endpoint con error → el agente dice `error_message` ("el mensaje que configuraste") → con `max_errors` seguidos: Corta (`hang_up`, `external_error`) o Pasa a tu equipo (`transfer:<área>`); "Un turno bueno vuelve el contador a cero." |
| `cierre` | 9,4 | t10 paula | Tu agente, con nuestra voz y nuestro teléfono. Está en el plan Red, y la guía completa, en atentina punto com punto ar, barra desarrolladores. | Fondo oscuro: "Tu agente, con nuestra voz **y nuestro teléfono.**", los tres pasos, "Incluido en el plan Red" y `atentina.com.ar/desarrolladores/docs/tu-propio-agente` |

Voces: `paula` narradora y `gonzalo` en las herramientas y en "por API o MCP" (contrapunto, no línea por línea).
`velocidad` 1,05 y `ganancia_db` −1,5, como en `api-desarrolladores` y `docs-intro`.

## Afirmaciones y fuentes

- **Qué pone cada uno, cómo funciona, pedido y respuesta, headers, herramientas, configurar, errores, latencia y
  plan:** `landing/src/pages/desarrolladores/docs/tu-propio-agente.astro` (secciones que-es, como-funciona, pedido,
  respuesta, herramientas, configurar, latencia, errores y planes) y [`docs/features/LLM_CONEXIONES.md`](../../../../docs/features/LLM_CONEXIONES.md).
- **Pedido y SSE en pantalla:** los ejemplos `request` y `response` de la página, recortados (ids, mensajes del
  medio y el final "¡Que andes bien!", que lleva signo de exclamación). Número `+5493515551234`, "Acme", "Sofía",
  "ventas" y `turno_dado`: ejemplos de la página.
- **`server.py`:** la versión acortada de la página (sin el chequeo de la key ni `or 'desconocido'`); el archivo
  completo es `examples/agente-externo/server.py`.
- **Panel:** recreación de `web/src/features/agents/ExternalSection.tsx` (switch, descripción, Endpoint, Modelo,
  "Probar el endpoint" y el texto de las dos herramientas) y del modal de `web/src/features/llm/LlmConnectionsSection.tsx`
  (Proveedor "OpenAI compatible", Nombre, URL base, API key "Se guarda cifrada y no se vuelve a mostrar."). El
  aviso "Tu agente respondió (…)" es el `notifySuccess` de `ExternalSection`, con el detalle de ejemplo de la página
  (`streaming · primer texto 420 ms · «Hola, ...»`), marcado "Ejemplo de la documentación". "Mi agente" y la URL
  `tu-agente.com/v1`, de la página. Las capturas `scratch/shots/ext-*.png` no se usaron: el texto del panel a 1440 px
  queda chico en 1080p y la de la definición es de un agente de otro cliente (Browix).
- **Por API / MCP:** rutas de la página (`/clients/{id}/llm-connections`, `/test`, `POST /agents`) y herramientas
  `create_llm_connection`, `test_llm_connection`, `create_agent`.
- **Latencia (v2):** solo el concepto de la página (sección "Latencia y turnos"): el primer texto se cuenta desde que
  llega el pedido hasta el primer pedazo; si pasa de un segundo, la conversación se siente lenta; el consejo "Dame un
  segundo que me fijo". Sin las cifras medidas (las de v1), por pedido del usuario. Errores: sección "Errores" de la
  página, sin mencionar el respaldo (pedido del usuario, v2).
- **Plan Red:** sección "Planes" de la página. En la base el tier se llamaba **Central** (como en `api-desarrolladores`); el 26-oct-2026 se borró: Red es a medida, sin tier, y el agente propio está también en Sucursal.
- **Sin logos de terceros:** OpenAI, OpenRouter, DeepSeek, LangGraph y n8n van solo como texto.

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 25-oct-2026 | 86,0 s | Primera versión | reemplazada por v2 (se borra de YouTube) |
| [v2](versiones/v2/NOTAS.md) | 25-oct-2026 | 93,0 s | Latencia: solo el concepto, sin las cifras medidas; errores: sin "no hay respaldo con nuestro modelo" | publicada en [YouTube](https://youtu.be/fJ1PAnvo9yc) y en la documentación |
