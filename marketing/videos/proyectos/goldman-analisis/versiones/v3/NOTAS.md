# goldman-analisis · v3

Estado: borrador

- **Archivo:** `goldman-analisis-v3.mp4` · 64,0 s · −15,5 LUFS (`make video-revisar P=goldman-analisis V=3
  ARGS="--tramos 0,4.9,14.7,20.2,34.4,42.2,53.1,59.7"`).
- **Pedido (21-oct-2026, el usuario después de ver v2, por el coordinador):** locución de vuelta a 1×; en "lo que
  observamos", una pausa entre cada observación ("va todo muy junto"), cada tarjeta con su frase; última observación
  "La temporada ya está por arrancar."; la escena del centro de la propuesta en dos: primero las líneas, el logo y el
  equipo, explicando que las consultas se clasifican y se derivan a las áreas, con énfasis en Ventas; después el
  panel, sencillo, que muestre el control sobre lo que pasa y sobre clientes y vendedores (pocas cifras + quién tomó
  cada consulta y cuánto tardó), ilustrativo y marcado; pantalla final solo "¿Agendamos una reunión personalmente?".
  Se mantiene lo de v2 (voz `lucas`, intro con 2 s, ortografía normal salvo "clasifíca", sin robot ni marca de
  Goldman). Duración: 60 s, hasta ~65 recortando en otras escenas.
- **Qué cambió respecto de v2:**
  - Locución a 1× (sin `"velocidad"` en `guion.json`).
  - Lo observado en cuatro líneas (a4a a a4d): cada tarjeta entra con su frase y entre línea y línea hay 0,4 s más el
    silencio propio de cada toma, ~0,7 s de respiro (`GAP` en `timeline.ts`; los momentos salen de `duraciones.json`).
  - Tarjeta 4: "La temporada ya está por arrancar" (antes "La temporada arranca en noviembre"); el texto de abajo
    sigue diciendo noviembre a febrero.
  - La propuesta en dos escenas: `propuesta` (canales → logo → tipos de consulta → "Su equipo" por área; con "sobre
    todo a Ventas", Ventas se agranda en el acento y le llegan tres consultas; titular que cambia a "Clasifica cada
    consulta y la pasa a su área.") y `panel` (3 cifras + tabla "Quién tomó cada consulta derivada": recibió, la tomó
    en, sin tomar; Vendedor 2 y Posventa en naranja con "cuánto tardó"). Sin la frase "Hoy se mide en reseñas".
  - Cierre: solo la pregunta; abajo, chico, el logo blanco y atentina.com.ar · 0800-220-1233. Sin chips ni botón.
  - **Recortes para entrar en ~64 s (no en lo observado):** a2 sin "en el rubro"; a5 sin "y lo que piden es poder
    comunicarse:" (queda "Sus clientes los valoran. Lo que piden es que les devuelvan el llamado, ..."; el titular
    sigue diciendo "poder comunicarse"); a6a sin "con todo lo hablado" (va escrito en la tarjeta de Ventas).
  - Escenas: intro 5,5 s, bien 9,8, cita 5,5, observamos 14,2, clientes 7,8, propuesta 10,9, panel 6,6, cierre 4,3.
  - Música regenerada a 68 s (`musica_segundos`).
- **Locución** (`lucas`, mejor de 4 tomas, a 1×; entre paréntesis, fidelidad con el STT):
  - a1 "Hagamos que cada cliente tenga una respuesta." (1,00; toma de la sesión anterior, verificada)
  - a2 "En Isaías Goldman ya hicieron lo difícil. Treinta años, unas cincuenta personas, y empresas como Arcor,
    Georgalos y Mostaza." (1,00; la primera tanda dio "Jorgalos" y se regeneró)
  - a3 "En palabras de Isaías Goldman: nos gusta hacer cosas donde podemos responder." (1,00; de la sesión anterior)
  - a4a "Esto es lo que vimos. Un solo número para todo." (1,00; de la sesión anterior)
  - a4b "Doscientos sesenta y seis productos, ninguno con precio." (0,67: solo porque el STT escribe "266")
  - a4c "Cerrado, ciento veintiuna horas por semana." (1,00)
  - a4d "La temporada ya está por arrancar." (1,00)
  - a5 "Sus clientes los valoran. Lo que piden es que les devuelvan el llamado, un presupuesto a tiempo, y un aviso si el
    técnico se demora." (1,00)
  - a6a "Proponemos un especialista de guardia en el cero ochocientos, el WhatsApp y la web. Clasifíca cada consulta y
    la pasa al área que corresponde, sobre todo a Ventas." (0,95: "Cero 800")
  - a6b "Y en el panel, ven todo lo que pasa: quién tomó cada consulta, y cuánto tardó." (1,00)
  - a7 "¿Agendamos una reunión personalmente?" (1,00)
- **Controles:**
  - `npx tsc --noEmit` sin errores.
  - Cuadros de prueba (`scratch/videos/goldman-analisis-v3/`) y hojas (`scratch/videos/revision/goldman-analisis-v3/`):
    sin textos cortados ni superposiciones (los titulares de la propuesta y del panel se acortaron para que entren en
    una línea).
  - Transcripción por escena fiel a la locución (el STT escribe "0800", "266", "121" y "ventas" en minúscula).
  - **Finales de frase:** la cola de cada WAV transcrita sola da la última palabra completa ("sobre todo a ventas",
    "cuánto tardó", "personalmente", "ya está por arrancar", "si el técnico se demora", "Georgalos y Mostaza"). Cada
    voz termina antes de su corte de escena (la más justa, a2: 0,4 s antes; a7 termina 1,2 s antes del final).
- **A revisar antes de mandarlo:**
  - Escuchar "Clasifíca" (grafía pedida), "Georgalos", "Goldman" y el ritmo de los respiros en lo observado.
  - Duración 64 s: 4 s más que el objetivo de 60 por las pausas y la escena nueva del panel.
  - Lo mismo que v2: funciones sin construir (derivación de la llamada a un vendedor, relay de WhatsApp, chat web,
    métricas del panel por canal, tipo, horario y persona: la tabla "quién la tomó y en cuánto" no existe hoy en el
    dashboard); 0800/0810 de ellos con Anura; panel ilustrativo (marcado en la barra y en el pie); reseñas textuales
    con sus faltas.
