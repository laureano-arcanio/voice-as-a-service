# tu-propio-agente v2

Estado: borrador

- **Archivo:** `tu-propio-agente-v2.mp4` (1920 × 1080, 30 fps, H.264 + AAC), 93,0 s, −16,5 LUFS, 11,3 MB.
- **Pedido (25-oct-2026, por el coordinador, resumido fiel):** cambios como versión nueva (v1 publicada en
  https://youtu.be/Nw2lrBYmEqs). 1) Latencia: explicar solo el concepto de tiempo hasta el primer texto (time to first
  token), desde que tu endpoint recibe el pedido hasta que manda el primer pedazo; que el rendimiento de su agente
  (modelo, herramientas, infraestructura) impacta en la latencia de la llamada y en cómo se percibe (lenta, con
  silencios); sin los números de nuestras pruebas (1.672 ms, 482 ms, DeepSeek, OpenRouter, "medido el 25-oct",
  cronómetro); se puede dar la orientación de la doc (más de un segundo se siente lenta) y el consejo de mandar el
  texto apenas lo tenga. 2) Errores: sin "no hay respaldo con nuestro modelo" (ni la línea ni el recuadro); queda que
  el agente avisa con el mensaje configurado y, con varios errores seguidos, corta o deriva. Revisar la descripción y
  los capítulos de YouTube. El resto igual.
- **Qué cambió respecto de v1:**
  - `latencia` (8,8 → 15,2 s): locución t8 nueva; sin cronómetro, barras ni cifras. Se ve "Tiempo hasta el primer
    texto · time to first token" como una barra que crece de "Tu endpoint recibe el pedido" a "Manda el primer pedazo
    de texto", seguida de "Atentina lo dice en voz"; las tarjetas Tu modelo, Tus herramientas y Tu infraestructura;
    "Más de 1 s: se siente lenta, con silencios", y el consejo "Dame un segundo que me fijo".
  - `errores` (7,6 → 8,2 s): locución t9 nueva, sin el respaldo; sin el recuadro "Sin respaldo…". La nota del globo
    dice "error_message · el mensaje que configuraste" y se suma "Un turno bueno vuelve el contador a cero." (página,
    sección Errores).
  - El resto de las escenas, las voces y el estilo, iguales.

## Locución

Solo t8 y t9 nuevas (`make video-voces P=tu-propio-agente TOMAS=4 IDS="t8 t9"`), con paula; fidelidad 1,00 en las
dos. El resto, las tomas de v1. 76,4 s de voz.

## Controles

- v1 cerrada antes de tocar el código (`make video-cerrar P=tu-propio-agente V=1`).
- `npx tsc --noEmit` sin errores; cuadros de prueba de `latencia`, `errores` y `cierre`
  (`scratch/videos/tu-propio-agente/v2-*.png`): se agrandó la tarjeta de la línea de tiempo (los rótulos tocaban el
  borde).
- `make video-revisar P=tu-propio-agente V=2 ARGS="--tramos 0,7.8,17.6,28.6,37.4,45.6,60.2,75.4,83.6"`: 93,0 s,
  −16,5 LUFS, hojas en `scratch/videos/revision/tu-propio-agente-v2/`, transcripción por escena igual al guion (los
  mismos errores del STT de v1: "a Tentina", "vos").

## Para YouTube (propuesta, sin subir)

**Título:** Tu propio agente de IA con la voz y el teléfono de Atentina (custom LLM)

**Descripción:**

```text
Si ya tenés tu agente de IA, con su prompt, sus herramientas y tus datos, conectalo a Atentina con un endpoint compatible con la API de OpenAI (POST /chat/completions con stream: true) y atiende llamadas y WhatsApp con un número argentino, sin construir el pipeline de voz.

Atentina pone el número, las llamadas entrantes y salientes, WhatsApp, el link para llamar, la transcripción, la detección de turnos e interrupciones, la voz argentina, la grabación, los minutos y la derivación a tu equipo. En cada turno le manda a tu endpoint toda la conversación, con los datos de la llamada en headers X-Atentina-*, y dice lo que responde a medida que llega. Tu agente corta con end_call (eligiendo el resultado) o pasa la llamada a una persona con transfer_call.

Se configura en tres pasos:
1. La conexión: la URL https de tu endpoint y su API key (tipo "OpenAI compatible").
2. Probar el endpoint: mide cuánto tarda el primer texto.
3. En el agente: "Que conteste tu propio agente".
También por API (key calls) o por MCP (create_llm_connection, test_llm_connection, create_agent).

Lo que más pesa es el tiempo hasta el primer texto: tu modelo, tus herramientas y tu infraestructura se notan en la llamada. Si tu endpoint falla, el agente dice el mensaje que configuraste y, con varios errores seguidos, corta o pasa la llamada a tu equipo.

Disponible en el plan Red.

Documentación completa: https://atentina.com.ar/desarrolladores/docs/tu-propio-agente

00:00 Qué es
00:17 Cómo funciona un turno
00:28 end_call, transfer_call y un endpoint de ejemplo
00:45 Configurarlo en tres pasos
01:00 Latencia: el tiempo hasta el primer texto
01:15 Errores y resumen
```

Cambios respecto de la de v1: el tipo de conexión dice "OpenAI compatible" (la página y el panel ya lo dicen así),
se suma un párrafo de latencia y errores (sin cifras ni respaldo) y los capítulos siguen la duración nueva (cada uno
de 10 s o más).

## A revisar antes de mostrarlo afuera

- **Reemplazo en YouTube:** YouTube no deja cambiar el archivo de un video publicado: v2 va como un video nuevo, y
  hay que cambiar el id en `tu-propio-agente.astro` (hoy embebe `Nw2lrBYmEqs`).
- **De oído:** "endpoint", "streaming", "ápi key" (gonzalo) y "M C P", como en v1.
- **Ilustrativo:** "Mi agente", `tu-agente.com/v1`, "ventas", el aviso "primer texto 420 ms" de la escena
  `configurar` (ejemplo de la página, marcado como tal; no es una medición nuestra) y la conversación de Acme.
- **"Red" vs "Central":** la landing dice Red y la base, Central.
