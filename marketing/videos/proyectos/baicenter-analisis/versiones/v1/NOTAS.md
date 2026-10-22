# baicenter-analisis · v1

Estado: borrador

- **Archivo:** `baicenter-analisis-v1.mp4` · 65,3 s · −15,8 LUFS (`make video-revisar P=baicenter-analisis V=1
  ARGS="--tramos 0,4.9,11.7,16.1,36.45,43.85,54.85,61.65"`).
- **Pedido (22-oct-2026, Laureano, textual):** "Similar al video que hicimos para isaias goldman, haremos uno igual pero
  con la informacion de BAIC. Cambiamos el enfasis un poco en lo que falla, sino mas bien areas a mejorar. Analiza el
  documento de BAIC luego implementa el video y el PDF como se hizo en Isaias." Con las reglas de goldman-analisis v3
  (ver el README) y, durante el trabajo, la corrección: BAIC Center no ofrece plan de ahorro; va la financiación con
  Bancor, Banco Nación, Santander y Galicia y crédito propio, sin leasing.
- **Retoque del borrador (22-oct-2026, pedido del usuario, textual):** "cambia areas a mejorar por 'Donde podriamos
  mejorar con Atentina' pdf y video." Como v1 no se había entregado, se rehízo sobre ella (VIDEOS.md: un borrador se
  puede volver a renderizar). Cambió el rótulo de la escena de áreas, la sección 2 del índice de la intro y a4a
  ("Dónde podríamos mejorar con Atentina. Dos WhatsApp…"; toma nueva de 5,76 s, +0,96 s; la primera tarjeta entra a los
  2,7 s de a4a). Para no pasar de 65,3 s: respiro entre áreas de 0,3 a 0,2 s (queda ~0,4–0,5 s con el silencio de cada
  toma) y bien 6,8, clientes 7,4, panel 6,8 y cierre 3,6 s (cada uno con ≥ 0,18 s después de su voz).
- **Qué es:** el PDF `baicenter-propuesta` v1 con la estructura de goldman-analisis v3 (mismo código adaptado): las
  tarjetas de lo observado pasan a "Dónde podríamos mejorar con Atentina", azules, con su "Oportunidad:"; la propuesta muestra los cinco
  pasos del asesor, la llamada de vuelta y la ficha al vendedor de la marca; el panel, el del PDF.
- **Locución** (`lucas`, mejor de 4 tomas, a 1×; entre paréntesis, fidelidad con el STT):
  - a1 "El cliente primero, también en el primer minuto." (1,00)
  - a2 "En Báic Center ya hicieron lo difícil. Nueve años, cuatro marcas, y flotas como la de EPEC." (1,00; "Bike")
  - a3 "Y lo resume el lema de la casa: el cliente primero." (1,00; la versión "Y lo dice su lema" dio "Zulema")
  - a4a "Dónde podríamos mejorar con Atentina. Dos WhatsApp y un fijo, para todo el grupo." (1,00; el STT lo escribe como
    pregunta, "¿Dónde podríamos…?": escuchar si la entonación sube)
  - a4b "Ciento nueve horas por semana, el showroom cerrado." (0,82: solo porque el STT escribe "109")
  - a4c "Cuatro bancos y crédito propio: muchas preguntas antes de venir." (1,00)
  - a4d "Y con dos concesionarios en Córdoba, la primera respuesta decide." (1,00)
  - a5 "La mayoría de las reseñas son buenas. Las que piden algo más, piden una respuesta rápida, y un próximo paso." (1,00)
  - a6a "Un asesor de guardia, en sus mismos números. Responde en segundos, califica, llama en menos de un minuto, agenda
    el test drive, y le pasa la ficha al vendedor." (1,00)
  - a6b "Lo que no se mide, no se mejora. En el panel ven cada consulta, cuánto tardó, y quién la tomó." (1,00)
  - a7 "¿Agendamos una reunión personalmente?" (1,00)
- **Grafía nueva:** `Báic` (pruebas en `scratch/videos/candidatas/baicenter*/`, grupo en `scripts/candidatas.py`; en
  `scripts/voces.py`, `"Báic": "Bike"` para medir la fidelidad).
- **Recortes para entrar en ~65 s:** a2 sin "siete años de garantía" (va en la tarjeta); sin "Proponemos" en a6a; escenas
  intro 5,5, bien 6,8, cita 4,4, áreas 20,35, clientes 7,4, propuesta 11,0, panel 6,8, cierre 3,6.
- **Controles:**
  - `npx tsc --noEmit` sin errores.
  - Cuadros de prueba (`scratch/videos/baicenter-analisis/`) y hojas (`scratch/videos/revision/baicenter-analisis-v1/`):
    sin textos cortados ni superposiciones (se acortó el titular de las áreas a una línea y se achicaron las preguntas
    de la tarjeta de financiación).
  - Transcripción por escena fiel a la locución (el STT escribe "Bike", "2", "109" y "4"). Cada voz termina antes de su
    corte (las más justas: a4d, 0,25 s antes del final de las áreas; a2, 0,26 s; panel y clientes, ~0,2 s).
  - Sin "plan de ahorro", "84 cuotas" ni "leasing" en el código ni en la locución.
- **A revisar antes de mandarlo:**
  - Escuchar a4a: el STT la transcribe con signos de pregunta; si suena a pregunta y no gusta, regenerarla.
  - Escuchar "Báic" (es la única grafía forzada), "EPEC" y el ritmo de los respiros entre las áreas (más cortos que en Goldman).
  - Duración 65,3 s: en el borde del margen de ~65.
  - La financiación (cuatro bancos y crédito propio) la verificó el usuario; el PDF v1 todavía dice plan de ahorro (el
    agente de documentos hace la v2).
  - Funciones sin construir que el video muestra como propuesta: llamada en menos de un minuto a cada consulta, agenda de
    test drives y turnos, ficha al vendedor, panel por marca, tipo y vendedor (la tabla no existe hoy en el dashboard).
  - Conectar sus dos WhatsApp y el fijo: coexistencia y Embedded Signup pendientes; desvío del fijo a Anura sin verificar.
  - Releer las dos reseñas en Google Maps (textuales y antigüedad: "hace unos 6 meses", "hace alrededor de un año", al
    20-oct-2026).
  - Panel, test drive y ficha: ilustrativos (rotulado en el panel y en los pies).
