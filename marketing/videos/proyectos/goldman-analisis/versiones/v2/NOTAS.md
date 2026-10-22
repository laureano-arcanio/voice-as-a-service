# goldman-analisis · v2

Estado: cerrada (21-10-2026)

- **Archivo:** `goldman-analisis-v2.mp4` · 57,8 s · −16,2 LUFS (`make video-revisar P=goldman-analisis V=2
  ARGS="--tramos 0,4.9,14.0,19.6,30.8,41.2,52.2"`).
- **Pedido (21-oct-2026, el usuario después de escuchar v1, por el coordinador):** sin tildes forzadas ("los acentos
  están mal en general"; solo "clasifíca" si se usa); 2 s de espera en la pantalla inicial y la locución "Hagamos que
  cada cliente tenga una respuesta."; "Como dijo" sonaba "Cómmo"; "Lo que observamos" mal pronunciado; "Cerrado 121
  hs por semana"; "se va con la competencia" si aparece "se va a otro lado"; el audio de la visita técnica se corta;
  cierre con "¿Les parece que hagamos un piloto antes de que inicie la temporada?"; locución a 1,1×; máximo 60 s.
- **Qué cambió respecto de v1:**
  - Locución a 1,1× sin cambiar el tono (`"velocidad": 1.1` en `guion.json`, que `scripts/voces.py` aplica con ffmpeg
    `atempo` a la mejor toma). Ortografía normal: `Georgalos` sin tilde.
  - Intro: la voz arranca a los 2 s (`AT.a1 = 2.0`); la pantalla sigue con el título del PDF.
  - a3 "En palabras de Isaías Goldman: ..." (sin "Como"); a4 arranca "Esto es lo que vimos." y dice "Cerrado, ciento
    veintiuna horas por semana."; tarjeta "Cerrado 121 hs por semana" con "121 hs · de las 168 de la semana".
  - **Corte de la visita técnica:** en v1 la toma de a5 terminaba en "un aviso" y el TTS recortó la última sílaba (la
    "-so" duraba 0,12 s y quedaba a 0,15 s del final del archivo); no era el montaje (la voz no se pisaba con la
    escena siguiente ni con el fundido). En v2 la línea termina en una frase larga ("y un aviso si el técnico se
    demora"), la escena dura 10,4 s con 0,6 s libres después de la voz, y se verificó: la cola de cada WAV transcrita
    sola da la última palabra completa, y en el MP4 la voz decae suave en 40,4 s, antes del corte de escena (41,2 s).
  - Cierre: "¿Les parece que hagamos un piloto **antes de que inicie la temporada?**"; rótulo "PROPUESTA PARA ISAÍAS
    GOLDMAN SA · PILOTO DE 30 DÍAS".
  - "Se va a otro lado" no aparece en este video.
  - Escenas: intro 5,5 s, bien 9,1, cita 5,6, observamos 11,2, clientes 10,4, propuesta 11,0, cierre 5,6.
- **Locución** (`lucas`, mejor de 4 a 6 tomas, a 1,1×):
  - a1 "Hagamos que cada cliente tenga una respuesta." (1,00)
  - a2 "En Isaías Goldman ya hicieron lo difícil. Treinta años en el rubro, unas cincuenta personas, y empresas como
    Arcor, Georgalos y Mostaza." (1,00; la primera tanda dio "Islaías" y "Giorgalos" y se regeneró)
  - a3 "En palabras de Isaías Goldman: nos gusta hacer cosas donde podemos responder." (1,00)
  - a4 "Esto es lo que vimos. Un solo número para todo. Doscientos sesenta y seis productos, ninguno con precio.
    Cerrado, ciento veintiuna horas por semana. Y en noviembre, arranca la temporada." (0,84: solo por las cifras)
  - a5 "Sus clientes los valoran, y lo que piden es poder comunicarse: que les devuelvan el llamado, un presupuesto a
    tiempo, y un aviso si el técnico se demora." (1,00)
  - a6 "Proponemos un especialista de guardia en el cero ochocientos, el WhatsApp y la web, que deriva a su equipo. Y
    un panel. Hoy, la atención se mide en reseñas. Con el panel, cada día." (0,95, "Cero 800"; dos tandas dieron
    "Cero 200" y se regeneró)
  - a7 "¿Les parece que hagamos un piloto antes de que inicie la temporada?" (1,00)
- **Controles:** `npx tsc --noEmit` sin errores; cuadros (`scratch/videos/goldman-analisis/v2-*.png`) y hojas
  (`scratch/videos/revision/goldman-analisis-v2/`) sin textos cortados ni superposiciones; transcripción por escena fiel
  (en el tramo de la propuesta el STT del video entero oyó "C800"; la línea sola, "Cero 800").
- **A revisar antes de mandarlo:** escuchar "Georgalos", "Goldman", "En palabras de" y "Esto es lo que vimos"; lo
  mismo que v1 (funciones sin construir: derivación de la llamada, relay de WhatsApp, chat web, métricas del panel por
  canal, tipo, horario y persona; 0800/0810 de ellos con Anura; panel ilustrativo; reseñas textuales con sus faltas).
