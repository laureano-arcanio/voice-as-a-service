# cimepa-analisis · v2

Estado: borrador

- **Archivo:** `cimepa-analisis-v2.mp4` · 64,6 s · −16,3 LUFS con `"ganancia_db": -1.5` (sin ajuste, −14,7)
  (`make video-revisar P=cimepa-analisis V=2 ARGS="--tramos 0,6.3,20.3,30.9,38.5,45.0,53.2,61.3"`).
- **Pedido (22-oct-2026, coordinador, por decisión del usuario sobre las voces):** "Hacé cimepa-analisis v2 (versión
  nueva, sin tocar v1) cambiando las voces: narradora principal `paula`, y `pablo` como voz secundaria en algunas
  líneas. [...] Elegí 2 o 3 líneas para `pablo` donde un cambio de voz sume [...]. No alternes línea por línea. Mismos
  textos y escenas que v1, salvo lo que haga falta por duración." Y, en la misma v2: "rehacé la escena 'entra' [...]
  nodos más grandes, con texto legible, bien separados [...]. A la salida tienen que verse también el dashboard (la
  llamada que aparece en el panel) y la transcripción (unas líneas IA / Cliente / Empleado con la marca de la
  derivación), rotulados como ejemplo con datos ilustrativos. [...] cuidá que no repita lo de la escena 'registro'."
- **v1 cerrada** antes de tocar el código (`make video-cerrar P=cimepa-analisis V=1`).
- **Voces:**
  - `paula` narra todo, salvo los pedidos.
  - `pablo` dice los cuatro pedidos de CIMEPA (c2a a c2d), un solo bloque seguido: es "la voz de lo que nos
    pidieron", un contrapunto que separa lo que piden ellos de lo que respondemos nosotros. Son cuatro archivos
    cortos (uno por tarjeta, para el respiro) pero una sola intervención; no hay alternancia en el resto del video.
    Para eso c2a de v1 se partió: `paula` abre con c2 "En CIMEPA nos pidieron cuatro cosas." y `pablo` sigue con
    "Que su equipo remoto llame sin teléfono."
- **Qué cambió además:**
  - **Escena `entra` rehecha** (10,6 s): nodos grandes y separados (Su cliente, Número de la empresa, el logo,
    Resuelve, Celular del empleado), y abajo el panel "PANEL · LLAMADAS" con la llamada nueva resaltada ("IA → Martín ·
    Derivada") y su transcripción (IA / Cliente / "deriva a Martín, con un resumen" / Empleado), rotulados
    "EJEMPLO · DATOS ILUSTRATIVOS". Sale la tarjeta de resumen y la nota "si no atiende nadie". c3 suma "Y queda en el
    panel, con su transcripción."
  - **Escena `registro`, sin repetir:** el panel y la transcripción de ejemplo pasaron a `entra`; ahora es "Por cada
    llamada, su sistema recibe **todo por API.**", con la lista "Lo que recibe, por cada llamada" de la hoja 4 del PDF
    (audio, transcripción, resumen y resultado, datos de la llamada) y `GET /api/v1/calls/{id}` (suma `fields`, campo
    real). c6 nuevo: "Y por ápi, su sistema recibe todo: el audio de la llamada, la transcripción, el resumen y el
    resultado. Inferencia propia, en Argentina."
  - c5 pasa a "Y la IA llama: ..." (con "Llama la IA:" `paula` sonó "Llama a la IA" en 2 rondas de 4 tomas).
  - Escenas: intro 6,9, pedido 14,0, entra 10,6, empleado 7,6, ia 6,5, registro 8,2, agente 8,1, cierre 3,3 s.
    Respiros entre pedidos ~0,6–0,7 s (`GAP` 0,35 s + silencios de las tomas).
- **Locución** (mejor de 4 tomas; fidelidad con el STT):
  - c1 paula "Un número de la empresa para su equipo y su IA, todo grabado y transcripto." (1,00)
  - c2 paula "En CIMEPA nos pidieron cuatro cosas." (1,00; "Cimepa")
  - c2a pablo "Que su equipo remoto llame sin teléfono." (1,00)
  - c2b pablo "Que su asistente de IA llame y atienda." (1,00)
  - c2c pablo "Transferir entre la IA y una persona." (1,00)
  - c2d pablo "Y todo grabado y transcripto, por ápi." (1,00)
  - c3 paula "Entra una llamada, y la atiende la IA. Resuelve, o la deriva al celular del empleado, con un resumen. Y queda
    en el panel, con su transcripción." (0,99: el STT oye "la deriva el celular" en las 2 rondas)
  - c4 paula "Un empleado llama desde la app web, en la compu o el celular: elige el contacto, un clic, y sale con el
    número de la empresa." (1,00)
  - c5 paula "Y la IA llama: seguimientos programados por ápi, con su contexto y sus instrucciones." (1,00)
  - c6 paula (texto nuevo, arriba) (1,00)
  - c7 paula "Su agente: tres vías, para definir en una charla técnica. En tiempo real, por SIP, o nuestro agente, con
    su contexto y su modelo." (1,00 la toma sola; en el video mezclado el STT oyó "por ZIP"; en candidatas, "Sip"/"Zip" y
    "nuestra gente" en 2 de 2)
  - c8 paula "¿Agendamos la charla técnica?" (1,00)
- **Pronunciación:** grupo `cimepa-v2` en `scripts/candidatas.py`, tomas en `scratch/videos/candidatas/cimepa-v2/`
  ("CIMEPA" con paula, "ápi" y "API" con paula y pablo, "SIP" con paula). "CIMEPA" sale "Cimepa" 2 de 2.
- **Nivel:** `ganancia_db` −1,5 en `guion.json`; se aplicó a los WAV ya elegidos (la misma cuenta que hace
  `voces.py` al regenerar), sin pedir tomas nuevas.
- **Controles:**
  - `npx tsc --noEmit` sin errores.
  - Cuadros de `entra` al inicio, a la mitad y al final (`scratch/videos/cimepa-analisis/v2-*.png`) antes del render:
    se ensanchó el nodo "Número de la empresa"; sin textos cortados ni superposiciones. Hojas en
    `scratch/videos/revision/cimepa-analisis-v2/`.
  - Transcripción por escena fiel a la locución, salvo "deriva el celular" (c3) y "ZIP" (c7). Cada voz termina antes
    de su corte (la más justa, c2d, ~0,3 s antes del final de `pedido`).
- **A revisar antes de mandarlo:**
  - Escuchar "SIP" y "o nuestro agente" en c7 (riesgo de "Zip" y "nuestra gente"), "al celular" en c3 y "ápi" (c2d con
    pablo; c5 y c6 con paula).
  - Escuchar el cambio de voz paula → pablo → paula en los pedidos y los respiros.
  - Lo mismo que v1: funciones mostradas sin construir (app web del equipo, transferencia y derivación al celular,
    grabación de la llamada entera con tramos de personas, panel con quién atendió, agente propio por WebRTC o SIP),
    "3 o más simultáneas" sin CAP con Gemma, y los datos de ejemplo (rotulados).
