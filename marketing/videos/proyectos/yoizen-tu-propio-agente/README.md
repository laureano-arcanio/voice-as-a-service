# Presentación para Yoizen con audio: Tu propio agente

La presentación de 12 diapositivas [`documentos/proyectos/yoizen-tu-propio-agente`](../../../documentos/proyectos/yoizen-tu-propio-agente/README.md)
(v1) convertida en video: las mismas diapositivas, en el mismo orden y con el mismo contenido, con una locución por
diapositiva que alterna una voz femenina (`paula`) y una masculina (`gonzalo`), subtítulos y música.

## Pedido

> (26-oct-2026, Laureano, textual) "Ahora crea un video. mismos slides. pero con audio, una voz masculina y femenina
> por slide. Duración total 2 minutos máximo."

## Público, mensaje y formato

- **Público:** Yoizen (Juan Stamati, su CTO y el responsable de producto), como la presentación. Tratamiento
  "ustedes"; **"Yoizen" no se dice** (el TTS lo pronunciaba mal en el video `yoizen` del 20-oct): va escrito en las
  diapositivas y en la voz es "ustedes", "su equipo", "sus bots".
- **Mensaje:** los bots que ya tienen deciden qué decir; Atentina pone la voz y el teléfono. Un endpoint, un turno,
  dos herramientas, tres pasos, y un próximo paso concreto.
- **Formato:** 1920 × 1080, 30 fps, 113,1 s (tope del pedido: 120 s). Composición `yoizen-tu-propio-agente`
  (`src/Video.tsx`). Subtítulos quemados en la línea del pie y música de `scripts/musica.py`.
- **Visual:** las PNG `vista-01.png` … `vista-12.png` de la presentación (1920 × 1080, la resolución del video),
  copiadas a `public/proyectos/yoizen-tu-propio-agente/slides/`, con fundido de 8 cuadros entre escenas, una
  entrada suave (sube 14 px) y un zoom muy leve (1,2 %) a lo largo de cada escena. No se recreó ninguna
  diapositiva: texto y diseño son los de la presentación. El título del pie ("Atentina × Yoizen · Tu propio
  agente", abajo a la izquierda) se tapa con el fondo para que los subtítulos no lo pisen; el contador ("n / 12")
  queda a la vista.

## Guion (v1)

Una voz por diapositiva: `paula` en las impares y `gonzalo` en las pares. La locución dice lo que la diapositiva
muestra, con las notas del presentador de la presentación como guía; no agrega afirmaciones.

| # | Escena (s) | Voz | Locución | Qué se ve (diapositiva) |
|---|---|---|---|---|
| 1 | 0,0–8,8 (8,8) | `paula` | Tu propio agente. Una sola función: los bots que ustedes ya tienen deciden qué decir, y Atentina pone la voz y el teléfono. | Portada (oscura): "Atentina × Yoizen", "Tu propio agente", "Sus agentes, nuestra voz." |
| 2 | 8,8–18,3 (9,5) | `gonzalo` | Su omnicanal ya atiende WhatsApp y web chat, y su orquestador decide qué responder. Falta la voz: llamadas entrantes y salientes, con esos mismos bots. | El punto de partida: Hoy (su omnicanal), Lo que falta (voz) y Lo nuevo (Tu propio agente) |
| 3 | 18,3–28,3 (10) | `paula` | Atentina pone el número, las llamadas, la transcripción, la voz y los minutos. Ustedes ponen el prompt, las herramientas, la memoria y qué responder. | Quién pone qué: Pone Atentina / Pone Yoizen y "No es cambiar el modelo" |
| 4 | 28,3–37,2 (8,9) | `gonzalo` | La persona habla. Atentina transcribe, le manda la conversación a su endpoint en el formato de ópen, ei, ái, y dice cada pedazo de la respuesta apenas llega. | Cómo funciona un turno: diagrama persona ⇄ Atentina ⇄ su endpoint (`POST /chat/completions`, `stream: true`) |
| 5 | 37,2–46,2 (9) | `paula` | Sin estado de su lado: el historial que mandamos es el que vale. Los datos de la llamada van en headers, y varios bots pueden compartir un endpoint. | El pedido: HTTP con los headers `X-Atentina-*`, `messages` y `tools`; cuatro puntos |
| 6 | 46,2–55,2 (9) | `gonzalo` | La respuesta vuelve en pedazos: el primero ya suena en el teléfono mientras llega el segundo. Streaming obligatorio: una respuesta entera cuenta como error. | La respuesta: SSE en pedazos, el primero ya sonando; streaming obligatorio |
| 7 | 55,2–64,3 (9,1) | `paula` | Dos herramientas que ejecuta Atentina. Con una, su bot corta la llamada y elige el resultado. Con la otra, la pasa a una persona de su equipo. | Dos herramientas: `end_call` (con `outcome`) y `transfer_call` (área, música, retoma) |
| 8 | 64,3–73,6 (9,3) | `gonzalo` | Un endpoint mínimo son veinte líneas: agrega su prompt, le pasa la conversación a su modelo y devuelve la respuesta tal cual. El resto ya lo tienen. | Un endpoint mínimo: `server.py` acortado (FastAPI) con las tres partes resaltadas |
| 9 | 73,6–84,7 (11,1) | `paula` | Tres pasos en el panel: la conexión, con la dirección de su endpoint y su key; probar el endpoint; y prender que conteste su propio agente. También por ápi y M C P. | Configurarlo: tres pasos del panel y por API / MCP |
| 10 | 84,7–93,6 (8,9) | `gonzalo` | Lo que más pesa es el tiempo hasta el primer texto. Más de un segundo se siente lento, y su modelo y su infraestructura se notan. Texto primero, herramientas después. | Latencia: línea de tiempo hasta el primer texto; más de un segundo se siente lento; "Dame un segundo que me fijo" |
| 11 | 93,6–103,1 (9,5) | `paula` | Si su endpoint falla, la llamada no se queda muda: el agente dice el mensaje configurado. Con varios errores seguidos, corta o pasa la llamada a su equipo. | Errores: falla → mensaje configurado → varios seguidos: corta o pasa al equipo; el contador vuelve a cero |
| 12 | 103,1–113,1 (10) | `gonzalo` | Próximos pasos: un endpoint con uno de sus bots y un caso real. Lo conectamos, hacemos llamadas de prueba y vamos a un piloto, en el plan Red. El resto lo ponemos nosotros. | Próximos pasos (oscura): su endpoint → conexión y prueba → llamadas de prueba → piloto; plan Red; SIP en evaluación; contacto |

`velocidad` 1,05 y `ganancia_db` −1,5, como en `tu-propio-agente`. Grafías: `ápi`, `ópen, ei, ái` y `M C P`
(VIDEOS.md); `endpoint`, `streaming`, `headers`, `key` y `prompt` escritos normal; `end_call` y `transfer_call` no se
dicen (van en pantalla).

## Afirmaciones y fuentes

Todo lo que se dice está en las diapositivas, y las diapositivas salen de la documentación publicada: ver
"Afirmaciones y de dónde salen" en el [README de la presentación](../../../documentos/proyectos/yoizen-tu-propio-agente/README.md)
(`landing/src/pages/desarrolladores/docs/tu-propio-agente.astro` y `docs/features/LLM_CONEXIONES.md,
10, 11 y 12). En particular:

- **Lo que ya tienen (2):** "omnicanal, WhatsApp, web chat, orquestador" y "Asterisk en camino", de la reunión del
  20-oct (README del video `yoizen` y de la presentación). En la voz solo WhatsApp y web chat.
- **Quién pone qué (3), el turno (4), el pedido (5), la respuesta (6), las herramientas (7), el endpoint mínimo (8),
  los tres pasos y API/MCP (9), los errores (11):** la página de documentación. "Varios bots pueden compartir un
  endpoint" es el punto "Varios bots, un endpoint: cada agente manda su `model`" de la diapositiva 5.
- **Latencia (10):** solo el concepto de la página (tiempo hasta el primer texto; más de un segundo se siente lento;
  "texto primero, herramientas después"). **Sin cifras**: ni los 0,9 s del motor propio ni los ms del ejemplo.
- **Errores (11):** sin "no hay respaldo con nuestro modelo".
- **Próximos pasos (12):** los cuatro pasos de la diapositiva y "plan Red" (en la base el tier se llamaba Central; borrado el 26-oct-2026: Red es a medida, sin tier).
  **No se dice "sin costo"** ni se promete una cantidad de llamadas simultáneas (sin CAP con Gemma). "La conexión SIP
  con su Asterisk sigue en evaluación" queda escrito en la diapositiva, no en la voz.
- **Ilustrativo (en pantalla, como en la presentación):** `agente.yoizen.com`, los números `+5493515551234` y
  `+541152630861`, "ventas", "Sofía", el turno del jueves y `turno_dado`.
- **Sin logos de terceros:** OpenAI, FastAPI, Azure y Asterisk, solo como texto en las diapositivas.

## Estado de la función (26-oct-2026)

El motor `external` está desplegado y la página publicada, pero **todavía no hubo una llamada real de punta a punta
con un endpoint externo** (ver el README de la presentación). El video no lo afirma ni lo niega: la "primera llamada
real" sería con el endpoint de Yoizen en el paso 2.

## Para YouTube (propuesta, sin subir; si se publica, como video no listado para Yoizen)

**Título:** Tu propio agente: sus bots, con la voz y el teléfono de Atentina (presentación para Yoizen)

**Descripción:**

```text
Cómo los bots que Yoizen ya tiene atienden y hacen llamadas con Atentina poniendo la voz y el teléfono: la función "Tu propio agente".

Su orquestador queda detrás de un endpoint compatible con la API de OpenAI (POST /chat/completions con stream: true). En cada turno, Atentina transcribe lo que dice la persona, le manda toda la conversación al endpoint, con los datos de la llamada en headers X-Atentina-*, y dice cada pedazo de la respuesta apenas llega. Dos herramientas: end_call (con el resultado de la conversación) y transfer_call (a una persona del equipo).

Atentina pone el número, las llamadas entrantes y salientes, WhatsApp, el link para llamar, la transcripción, los turnos y las interrupciones, la voz argentina, la grabación, los minutos, la derivación y el registro. Yoizen pone el prompt, las herramientas, la memoria y qué responder.

Se configura en tres pasos en el panel (la conexión, probar el endpoint y prender "Que conteste tu propio agente"), o por API y MCP. Lo que más pesa es el tiempo hasta el primer texto. Si el endpoint falla, el agente dice el mensaje configurado y, con varios errores seguidos, corta o pasa la llamada al equipo.

Próximos pasos: un endpoint con uno de sus bots y un caso real; conexión y prueba, llamadas de prueba y piloto. Plan Red.

Guía: https://atentina.com.ar/desarrolladores/docs/tu-propio-agente
Contacto: 0800-220-1233 · hola@atentina.com.ar
```

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 26-oct-2026 | 113,1 s | Primera versión: las 12 diapositivas de la presentación v1 con locución alternada | borrador |
