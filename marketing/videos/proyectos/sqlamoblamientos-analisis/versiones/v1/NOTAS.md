# sqlamoblamientos-analisis · v1

Estado: cerrada (22-10-2026)

- **Archivo:** `sqlamoblamientos-analisis-v1.mp4` · 65,2 s · −15,2 LUFS (`make video-revisar P=sqlamoblamientos-analisis V=1
  ARGS="--tramos 0,6.2,13.2,18.8,36.65,44.65,55.85,61.65"`).
- **Pedido (22-oct-2026, Laureano, por el coordinador, textual):** "el PDF en video, con la introducción, qué hacen bien
  y dónde podríamos mejorar con Atentina. Corto, 60 segundos." Con las reglas y escenas que listó el coordinador (ver
  el README).
- **Qué es:** el PDF `sqlamoblamientos-propuesta` v1 con la estructura de goldman-analisis v3 y baicenter-analisis v1
  (código adaptado): intro, lo que hacen bien, la cita de Jorge Urizar, dónde podríamos mejorar (seis tarjetas del PDF
  condensadas en cuatro, una por frase), lo que valoran sus clientes (los asesores por nombre; el asesor de guardia no
  los reemplaza), la propuesta (canales → logo → tipos → su equipo, con Ventas: asesores y locales, franquicia de la
  zona), el panel simple y el cierre.
- **Locución** (`lucas`, mejor de 4 tomas, a 1×; entre paréntesis, fidelidad con el STT):
  - a1 "Cada consulta con respuesta, cada cliente al tanto de lo suyo." (1,00)
  - a2 "En Ese Cu Ele Amoblamientos ya hicieron lo difícil: veinte locales, en nueve provincias." (1,00; el STT oye "SQL")
  - a3 "En palabras de Jorge Urizar: cumplimos a rajatabla con los tiempos estipulados." (1,00; en el video el STT escribe "Rajatabla")
  - a4a "Dónde podríamos mejorar con Atentina. Mientras espera, el cliente pregunta cómo va lo suyo." (1,00; el STT la
    escribe como pregunta, igual que en baicenter)
  - a4b "La posventa entra como un mensaje más." (1,00)
  - a4c "Un solo WhatsApp, para consultas de todo el país." (1,00)
  - a4d "Y una cocina se piensa de noche, con la casa cerrada." (1,00)
  - a5 "Sus clientes elogian a sus asesores, por su nombre. El asesor de guardia no los reemplaza: les pasa cada consulta lista." (1,00)
  - a6a "Un asesor de guardia en su WhatsApp, su línea y su sitio. Clasifica cada consulta y la pasa a su equipo, sobre
    todo a Ventas: al asesor, o a la franquicia de la zona." (1,00)
  - a6b "Y en el panel, ven todo lo que pasa: quién tomó cada consulta, y cuánto tardó." (1,00)
  - a7 "¿Agendamos una reunión personalmente?" (1,00)
- **Grafía nueva: `Ese Cu Ele` por SQL.** Pruebas (`scratch/videos/candidatas/sqlamoblamientos/`, grupo en
  `scripts/candidatas.py`, dos tomas por texto): escrito "SQL", una toma el STT la oyó "Squell" y la otra "SQL"; "S Q L",
  "SQL El" en una; "ese cu ele" y "Ese Cu Ele", "SQL" o "ese QL" (las letras en español). El STT no distingue "ese-cu-ele"
  de "es-kiu-el", así que se eligió la grafía que fuerza las letras en español. En `scripts/voces.py`,
  `"Ese Cu Ele": "SQL"` para medir la fidelidad.
- **Recortes para entrar en ~65 s:** a2 sin "Fábrica propia" (va en la tarjeta de 4.000 m²; la primera toma duraba 7,6 s);
  a6a sin coma después de "guardia" (12,0 → 10,6 s con el texto final); escenas intro 6,7 (a1 termina a los 6,16 s),
  bien 7,1, cita 5,6, mejorar 17,85, clientes 8,0, propuesta 11,2, panel 5,8, cierre 3,6.
- **Controles:**
  - `npx tsc --noEmit` sin errores.
  - Cuadros de prueba (`scratch/videos/sqlamoblamientos-analisis/`) y hojas (`scratch/videos/revision/sqlamoblamientos-analisis-v1/`):
    sin textos cortados ni superposiciones (se corrigió un doble espacio en la firma de la cita y se marcaron como
    píldoras "Asesores y locales" y "Franquicia de la zona").
  - Transcripción por escena fiel a la locución (el STT escribe "SQL", "20", "9", "Rajatabla", "postventa" y "ventas").
  - Cada voz termina antes de su corte: a2 a 0,16 s del final de `bien`; a3, 0,18 s; a4d, 0,36 s; a5, 0,18 s; a6a,
    0,26 s; a6b, 0,38 s. Respiro entre las tarjetas de mejorar: ~0,65 s (0,45 s + el silencio de cada toma).
  - Sin el texto oculto del sitio, sin la competencia, sin logo de SQL y sin el robot.
- **A revisar antes de mandarlo:**
  - **Escuchar "Ese Cu Ele"** en a2 (la única grafía): que suene "ese-cu-ele" y natural. Si prefieren la ortografía
    normal, las tomas de "SQL" están en `scratch/videos/candidatas/sqlamoblamientos/00-` y `01-lucas.wav`.
  - Escuchar a4a: el STT la transcribe como pregunta; si la entonación sube y no gusta, regenerarla.
  - Duración 65,2 s: en el borde del margen de ~65.
  - Funciones que el video muestra como propuesta y no están construidas: clasificación y derivación al asesor o la
    franquicia de la zona con la ficha, estado del pedido, reclamos con número de caso, panel por asesor. Conectar su
    WhatsApp central y la línea: coexistencia y Embedded Signup pendientes; desvío de la línea sin verificar.
  - "¿Cómo va lo mío?" por el mismo WhatsApp es una inferencia (a confirmar en la reunión), como en el PDF.
  - Releer la reseña de Martín y los nombres de los asesores en Google Maps (antigüedades al 22-oct-2026).
  - Panel y mensajes de la tarjeta de posventa: ilustrativos (rotulado en el panel y en los pies).
