# goldman · v3

Estado: borrador

- **Archivo:** `goldman-v3.mp4` · 36,9 s · −15,9 LUFS (`make video-revisar P=goldman V=3
  ARGS="--tramos 0,5.8,14.1,23.4,31.9"`).
- **Pedido (21-oct-2026, el usuario después de escuchar v2, por el coordinador):** quitar la regla de la tilde en la
  sílaba tónica ("parece que los acentos están mal en general"); "áires" → "aires"; "Clasífica" → "Clasifíca"; "se va
  a otro lado" → "se va con la competencia"; esperar 2 s antes de la voz en la pantalla inicial; el cierre pasa a la
  pregunta "¿Les parece que hagamos un piloto antes de que inicie la temporada?" (y la pantalla acorde); locución a
  1,1× (escrito "1,1%", interpretado como factor); máximo 40 s.
- **Qué cambió respecto de v2:**
  - Locución con la ortografía normal salvo `Clasifíca`; todas las líneas regeneradas (mejor de 4) y aceleradas a
    1,1× con `ffmpeg atempo` (sin cambio de tono). Nuevo campo `"velocidad"` en `guion.json`, leído por
    `scripts/voces.py`.
  - Intro: la voz arranca a los 2,0 s; los chips entran a los 2,2 s.
  - Problema: "Se fue con la competencia" en la tarjeta de la espera.
  - Cierre: "¿Les parece un piloto **antes de que inicie la temporada?**" (reemplaza el título del PDF, "Que cada
    consulta tenga respuesta…", que sigue en el PDF).
  - Escenas: intro 6,4 s, problema 8,3, propuesta 9,3, panel 8,5, cierre 5,0; animaciones resincronizadas con las
    pausas de las tomas nuevas.
- **Locución** (`lucas`, 1,1×; fidelidad de la toma antes de acelerar):
  - g1 "En Isaías Goldman, en temporada de aires, las consultas no paran." (1,00)
  - g2 "Actualmente, un solo número y el local cerrado no alcanzan. La consulta que no se contesta en minutos, se va
    con la competencia." (1,00)
  - g3 "Nuestro agente atiende las veinticuatro horas el cero ochocientos, el WhatsApp y el chat de la web. Clasifíca,
    responde lo general, y deriva a su equipo." (0,85: solo "24" y "0800" en cifras)
  - g4 "Y todo queda en un panel: cada canal, cada tipo de consulta, tiempos de respuesta, fuera de horario y
    derivaciones por vendedor." (1,00)
  - g5 "¿Les parece que hagamos un piloto antes de que inicie la temporada?" (1,00)
- **Controles:** `npx tsc --noEmit` sin errores; cuadros (`scratch/videos/goldman/v3-*.png`) y hojas
  (`scratch/videos/revision/goldman-v3/`): sin textos cortados ni superposiciones. Transcripción del video (ya
  acelerado) por escena: fiel.
- **A revisar antes de mandarlo:** escuchar "Clasifíca" y el ritmo a 1,1×; lo mismo que v1 y v2 sobre la oferta
  (transferencia de la llamada, relay de WhatsApp, chat web y métricas del panel sin construir; panel ilustrativo;
  0800/0810 de ellos a dar de alta con Anura).
