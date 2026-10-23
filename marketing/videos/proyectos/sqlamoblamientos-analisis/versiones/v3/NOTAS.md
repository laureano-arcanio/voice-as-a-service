# sqlamoblamientos-analisis · v3

Estado: cerrada (22-10-2026)

- **Archivo:** `sqlamoblamientos-analisis-v3.mp4` · 69,4 s · −15,7 LUFS (`make video-revisar P=sqlamoblamientos-analisis V=3
  ARGS="--tramos 0,7.2,14.1,19.7,36.45,44.45,52.4,59.95,65.75"`).
- **Pedido (22-oct-2026, el usuario por el coordinador):** que el video quede igual al PDF v2
  (`sqlamoblamientos-propuesta/versiones/v2/documento.html`): apertura "cliente y empresa saben lo que está pasando"; la
  propuesta incluye un 0800 o 0810; énfasis en la derivación a personal humano; no solo WhatsApp, también llamadas de voz;
  el agente tiene información actualizada de pedidos y de productos. Hasta ~70 s por la escena de la propuesta.
- **Qué cambió respecto de v2** (v2 cerrada antes de tocar el código):
  - **Intro:** a1 y título "Cada consulta atendida. Su cliente y ustedes, siempre al tanto de lo que pasa." (en tres líneas,
    76 px); rótulo "Un asesor de guardia 24/7, al teléfono y en WhatsApp". Intro de 6,7 a 7,6 s (a1 dura 5,12 s).
  - **Mejorar:** oportunidades del PDF v2: fabricación "responderle al instante, con el dato de su pedido, en qué etapa
    está"; red "un número para todo el país que pase cada consulta al local de la zona". La locución no cambia.
  - **Propuesta (nueva escena, 11,2 → 15,5 s):** título "Un asesor de guardia, y una persona cuando hace falta."; canales
    0800 / 0810 (nuevo, para todo el país), Línea de la casa, WhatsApp (mensajes, audios y llamadas) y Su sitio web; "Atiende
    con voz" con onda; caja "SUS DATOS · DE SU SISTEMA O PLANILLA" (Catálogo y Pedidos); a la derecha "Una persona, a un
    paso" (asesores y locales y franquicia de la zona marcados como Ventas, posventa, administración, producción), que es el
    énfasis: se agranda, el enlace se engrosa, viajan una llamada y "charla + ficha", y cierra con "sin que el cliente
    repita nada". Dos líneas de locución (a6a y a6c, nueva). Se sacaron los seis tipos de consulta de esta escena.
  - **Panel:** "310 consultas: llamadas, WhatsApp y web", "189 · 121 resueltas solas · pasadas a una persona", por canal
    con 0800 / 0810 y Llamada WA, y tabla "Pasadas a una persona: quién y cuánto tardó" (columna "Pases"). Titular "Qué
    pasó a una persona: quién la tomó y cuánto tardó." Sigue el rótulo "EJEMPLO CON DATOS ILUSTRATIVOS".
  - Se mantienen "Lo que ya hacen muy bien", el horario reducido y el cierre.
- **Locución nueva** (`lucas`, mejor de 4 tomas, a 1×):
  - a1 "Cada consulta atendida. Su cliente y ustedes, siempre al tanto de lo que pasa." (1,00)
  - a6a "Atiende con voz, en un cero ochocientos, su línea y su WhatsApp. Conoce sus productos, y sabe cómo va cada pedido."
    (0,87, solo porque el STT escribe "0800" y "vos")
  - a6c "Y cuando hace falta, pasa a una persona: al asesor, o a la franquicia de la zona, con la charla y la ficha." (1,00)
  - a6b "Y en el panel, ven qué pasó a una persona, quién la tomó, y cuánto tardó." (1,00)
  - Primeras versiones descartadas por largas (el video daba ~73,5 s): a6a con "Un asesor de guardia que atiende…" (9,4 s),
    a6c con "…El cliente no repite nada." (8,3 s; queda escrito en pantalla) y a6b "…qué resolvió solo, qué pasó a una
    persona…" (6,1 s).
- **"0800":** escrito "cero ochocientos" (números en palabras, como en goldman); el STT lo oye "0800" en las dos tomas
  que se transcribieron. Se dice solo "un cero ochocientos"; "0810" va escrito en pantalla.
- **Controles:**
  - `npx tsc --noEmit` sin errores. Cuadros (`scratch/videos/sqlamoblamientos-analisis/v3-*.png`) y hojas
    (`scratch/videos/revision/sqlamoblamientos-analisis-v3/`): se corrigieron el título de la intro (se salía y pisaba el
    rótulo), el titular de la propuesta (en dos líneas tapaba el primer canal), el rótulo de la caja de datos y el título
    "Una persona, a un paso"; sin textos cortados ni superposiciones.
  - Transcripción por escena fiel a la locución. Márgenes: a1 termina ~0,5 s antes de a2; a6c, 0,56 s antes del corte de
    la propuesta; a6b, 0,78 s.
- **A revisar antes de mandarlo:**
  - Duración 69,4 s: en el borde de los ~70 pedidos.
  - Escuchar "cero ochocientos" y "con voz" en a6a, además de lo de v1 ("Ese Cu Ele", la entonación de a4a).
  - **Sin construir hoy, mostrado como propuesta:** alta de un 0800 o 0810 para ellos, conexión a su sistema o planilla de
    pedidos y a su catálogo, pase de la llamada o el chat a una persona con la charla y la ficha, el panel con
    resueltas/pasadas por canal y por persona. Las llamadas de WhatsApp por SIP están en producción solo con el número de
    Atentina; para su número hacen falta la coexistencia y el Embedded Signup.
  - Panel: ilustrativo (rotulado).
