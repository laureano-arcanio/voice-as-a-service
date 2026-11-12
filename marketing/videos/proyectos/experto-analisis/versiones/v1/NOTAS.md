# experto-analisis · v1

Estado: cerrada (11-11-2026)

- **Archivo:** `experto-analisis-v1.mp4` · 58,3 s · −16,1 LUFS (`make video-revisar P=experto-analisis V=1
  ARGS="--tramos 0,5.4,13.8,19.8,35.7,48.3,54.3"`).
- **Pedido (11-nov-2026, el usuario, por el coordinador):** "crea una propuesta en PDF y en video de cómo Atentina
  podría integrarse en sus operaciones." El PDF en video: introducción, qué hacen bien y dónde podríamos mejorar con
  Atentina, ~60 s (hasta ~65). Escenas pedidas: intro como la portada (2 s antes de la voz), lo que hacen bien
  (22 años, 4 locales, 752 reseñas 4,3–4,5, 19 marcas/331 productos), la cita de los dueños, dónde mejorar con una
  tarjeta por frase y ~0,7 s de respiro, la propuesta (canales → logo → tipos de consulta → su equipo por área, con
  énfasis en las cotizaciones), el panel simple ilustrativo y el cierre "¿Agendamos una reunión personalmente?".
- **Qué cambió:** primera versión. **Intro y cierre en blanco**, no oscuros como decía el pedido: lo manda VIDEOS.md
  (todo video empieza y termina en blanco desde el 30-oct-2026).
- **Locución** (mejor de 4 tomas, a 1×, `ganancia_db` −1,5; TTS y STT de server2 por el proxy
  `http://192.168.1.98:8100/{tts,stt}/v1`, el TTS local de .99 está parado; entre paréntesis, fidelidad con el STT).
  paula 37,8 s, gonzalo 7,9 s:
  - a1 paula "Cada consulta atendida en el momento, y lista para su asesor." (1,00)
  - a2 paula "En Experto, ya hicieron lo difícil. Veintidós años, cuatro locales, y un asesoramiento que sus clientes
    recomiendan." (0,94: el STT escribe "22"; sin la coma después de "Experto" oyó "En expertos" y se regeneró)
  - a3 gonzalo "En palabras de sus dueños: con esta última inversión, quintuplicamos nuestra capacidad productiva." (1,00)
  - a4a paula "Dónde podríamos mejorar. Hoy atienden cuarenta y cinco de las ciento sesenta y ocho horas de la semana."
    (0,74: solo porque el STT escribe "45" y "168")
  - a4b paula "Muchos canales, y todo termina en un asesor." (1,00; antes "Siete canales", ver "A revisar")
  - a4c paula "Cada cotización se arma a mano." (1,00)
  - a4d paula "Y los reclamos van por mail, y esperan a que alguien los retome." (1,00)
  - a5 paula "Proponemos un agente que atiende su WhatsApp, el cero ochocientos y la web, a toda hora. Responde las
    preguntas frecuentes, pasa los reclamos a posventa, y cada cotización, completa, al asesor de su sucursal."
    (0,94: "0800" y "postventa")
  - a6 gonzalo "Y en el panel, ven quién tomó cada cotización, y cuánto tardó." (1,00)
  - a7 paula "¿Agendamos una reunión personalmente?" (1,00)
- **Controles:**
  - `npx tsc --noEmit` sin errores.
  - Cuadros de prueba (`scratch/videos/experto-analisis-v1/`) y hojas cada 2 s
    (`scratch/videos/revision/experto-analisis-v1/`): sin textos cortados ni superposiciones (se acortó el subtítulo
    de Ventas y el botón "Agregar a cotización" quedó en una línea).
  - Transcripción por escena igual al guion (el STT escribe los números en cifras, "0800" y "postventa", y oye "¿Dónde
    podríamos mejorar?" como pregunta).
  - **Finales de frase:** la cola de cada WAV transcrita sola da la última palabra completa ("lista para su asesor",
    "clientes recomiendan", "capacidad productiva", "horas de la semana", "termina en un asesor", "se arma a mano",
    "alguien los retome", "asesor de su sucursal", "y cuánto tardó", "reunión personalmente"). Cada voz termina antes
    de su corte de escena (la más justa, a1: termina en 5,44 s y la intro se funde desde 5,4).
- **A revisar antes de mandarlo:**
  - **Canales: 7 u 8.** `experto.md` lista WhatsApp central, 4 teléfonos de sucursal con WhatsApp, 0800, mail y
    formulario: son 8, y el PDF dice "7 canales" (página 2 y tabla de la página 4). El video dice "Muchos canales" y
    muestra los 8 en la tarjeta. Corregir el PDF o confirmar cómo se cuentan.
  - Escuchar "En Experto, ya..." (el STT oyó "En expertos" sin la coma), "quintuplicamos" y "posventa" (gonzalo y
    paula) y el ritmo de los respiros en "Dónde podríamos mejorar".
  - **Funciones (el video no dice qué está construido):** la derivación por WhatsApp al asesor está implementada sin
    desplegar; el WhatsApp con su número propio no está probado con un número real; el 0800 de ellos requiere el desvío
    con su operador (sin verificar que el 0800 lo permita); en el panel no existen hoy la tabla "quién tomó cada
    cotización y en cuánto", las métricas por sucursal ni la clasificación por tipo como en la maqueta. Derivar llamadas
    al equipo, WhatsApp con el agente y el link para llamar desde la web sí están en producción.
  - "La cotización llega completa" y "cada cotización, completa": depende de cómo se arme el agente en el relevamiento.
  - Panel ilustrativo (marcado en la barra y en el pie); sin precios, sin fotos por WhatsApp, sin llamadas simultáneas.
