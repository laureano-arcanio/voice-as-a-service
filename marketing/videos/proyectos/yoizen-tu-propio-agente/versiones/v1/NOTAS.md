# yoizen-tu-propio-agente v1

Estado: borrador

- **Archivo:** `yoizen-tu-propio-agente-v1.mp4` (1920 × 1080, 30 fps, H.264 + AAC), 113,1 s, −16,0 LUFS, 42,8 MB.
- **Pedido (26-oct-2026, Laureano, textual):** "Ahora crea un video. mismos slides. pero con audio, una voz
  masculina y femenina por slide. Duración total 2 minutos máximo."
- **Qué es:** las 12 diapositivas de [`documentos/proyectos/yoizen-tu-propio-agente`](../../../../documentos/proyectos/yoizen-tu-propio-agente/README.md)
  v1 (`vista-01.png` … `vista-12.png`, copiadas a `public/proyectos/yoizen-tu-propio-agente/slides/`), una escena por
  diapositiva, con una locución por diapositiva: `paula` en las impares y `gonzalo` en las pares.
- **Decisiones:**
  - Las diapositivas se usan tal cual (PNG a la resolución del video); no se recreó ninguna en React. Movimiento:
    fundido de 8 cuadros entre escenas (el de la casa), entrada suave (sube 14 px en 0,6 s) y zoom muy leve (1,2 %)
    a lo largo de cada escena.
  - Subtítulos quemados, centrados en la línea del pie (27 px, pastilla oscura). Para que no pisen el pie, el título
    de la izquierda ("Atentina × Yoizen · Tu propio agente", medido en x 112–616, y 998–1019) se tapa con el fondo
    de la diapositiva; el contador "n / 12" de la derecha queda a la vista. En la 9, la tapa roza 3 px del borde
    inferior de la tarjeta "Por API" (la tarjeta llega a y 999): no se nota en el cuadro de prueba.
  - Cada escena dura 0,5 s + su locución + 0,8 s: 97,4 s de voz, 113,1 s en total (tope del pedido: 120 s).
  - "Yoizen" no se dice: "ustedes", "su equipo", "sus bots". Sin cifras de latencia, sin "sin respaldo con nuestro
    modelo", sin "sin costo", sin cantidad de llamadas simultáneas; "plan Red" en la 12. La conexión SIP con su
    Asterisk queda escrita en la 12 ("sigue en evaluación"), no en la voz.
  - `velocidad` 1,05 y `ganancia_db` −1,5 (como `tu-propio-agente`); música de `scripts/musica.py` (125 s).

## Locución

`make video-voces P=yoizen-tu-propio-agente TOMAS=4`: fidelidad 1,00 en 11 de 12 líneas; s08 0,97 porque el STT
escribió "20 líneas" en cifras (no es un error de la toma). Lo que oyó el STT en las tomas elegidas: "Open, AI"
(s04, `ópen, ei, ái`), "headers" (s05), "key" y "API y MCP" (s09, `ápi` y `M C P`), "Streaming" (s06), "plan red"
(s12). Log en `scratch/videos/yoizen-tu-propio-agente/voces-v1.log`.

| Línea | Voz | s |
|---|---|---|
| s01 | paula | 7,47 |
| s02 | gonzalo | 8,21 |
| s03 | paula | 8,73 |
| s04 | gonzalo | 7,63 |
| s05 | paula | 7,73 |
| s06 | gonzalo | 7,69 |
| s07 | paula | 7,78 |
| s08 | gonzalo | 7,96 |
| s09 | paula | 9,76 |
| s10 | gonzalo | 7,59 |
| s11 | paula | 8,24 |
| s12 | gonzalo | 8,65 |

## Controles

- `npx tsc --noEmit` sin errores.
- Cuadros de prueba (`scratch/videos/yoizen-tu-propio-agente/v1-*.png`): portada con subtítulo, la 6 con el
  subtítulo más largo (62 caracteres, 840 px: no llega al contador), la 9 (tarjetas del pie enteras después de achicar
  la tapa), la 12 y una transición (el fundido oscuro → blanco de la 1 a la 2 pasa por el fondo de puntos durante 8
  cuadros, como en los demás videos).
- `make video-revisar P=yoizen-tu-propio-agente V=1 ARGS="--tramos 0,8.8,18.3,28.3,37.2,46.2,55.2,64.3,73.6,84.7,93.6,103.1"`:
  113,1 s, −16,0 LUFS; hojas en `scratch/videos/revision/yoizen-tu-propio-agente-v1/` (las 12 diapositivas
  enteras, subtítulos en la línea del pie, contador visible); la transcripción por escena coincide con el guion
  (ninguna locución cortada ni pisada por la siguiente).
- Afirmaciones: las de la presentación (README del proyecto de documentos, 26-oct-2026).

## A revisar antes de mostrarlo afuera

- **De oído:** "endpoint", "streaming", "headers", "key" (paula), "ópen, ei, ái" y "M C P" (el STT no distingue el
  acento); y que "plan Red" no suene a "plan red" de internet (es el nombre del plan).
- **Estado de la función:** el motor `external` está desplegado y la página publicada, pero no hubo todavía una
  llamada real de punta a punta con un endpoint externo (README de la presentación). El video no lo afirma.
- **"Red" vs "Central":** la landing dice Red y la base, Central.
- **Ilustrativo (en las diapositivas):** `agente.yoizen.com`, `+5493515551234`, `+541152630861`, "ventas", "Sofía",
  el turno del jueves, `turno_dado` y `gpt-4.1-mini` del ejemplo.
- **Fundido oscuro ↔ blanco** (1 → 2 y 11 → 12): pasa por el fondo de puntos claro durante 8 cuadros. Si molesta,
  en una v2 se puede hacer que la entrante se funda sobre la saliente sin que esta desaparezca.
- **Si cambia la presentación** (v2 de las diapositivas), hay que copiar las PNG nuevas a `public/.../slides/` y
  hacer una versión nueva del video.
