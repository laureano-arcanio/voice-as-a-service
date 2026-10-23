# sqlamoblamientos-analisis · v4

Estado: cerrada (22-10-2026)

- **Archivo:** `sqlamoblamientos-analisis-v4.mp4` · 71,0 s · −16,1 LUFS (`make video-revisar P=sqlamoblamientos-analisis V=4
  ARGS="--tramos 0,7.4,13.4,20.1,36.7,44.8,53.9,61.75,67.7"`).
- **Pedido (22-oct-2026, el usuario por el coordinador):** cambiar la narradora a la voz `laura` (arf_06136, mujer); mismos
  textos, escenas y visuales que v3, toda la locución regenerada a 1× (mejor de 4 tomas); revisar las grafías con esta
  voz y ajustar los tiempos; tope ~70 s.
- **Qué cambió respecto de v3** (v3 cerrada antes; la locución de `lucas` queda en `v3/fuente/vo/`):
  - Las 12 líneas con `laura` (64,2 s de voz contra 60,5 con `lucas`).
  - **Nivel:** con `laura` la mezcla daba −13,9 LUFS (fuera de −16 ± 1,5). Se agregó `"ganancia_db"` a `scripts/voces.py`
    y `"ganancia_db": -2.2` al guion; se aplicó a las tomas elegidas sin pedirlas de nuevo: −16,1 LUFS.
  - **Escenas:** intro 7,6 → 7,8 s, bien 7,1 → 6,2, cita 5,6 → 6,7, mejorar 16,75 → 16,6 (`GAP` 0,45 → 0,35: laura deja
    ~0,25 s de silencio al final de cada toma; respiro ~0,7 s), clientes 8,0 → 8,1, propuesta 15,5 → 16,95 (a6c a 0,3 s
    de a6a), panel 5,8 → 5,95, cierre 3,6 → 3,3.
  - Momentos de cada animación rehechos con las pausas de las tomas de laura (tarjetas de "bien", palabras de la cita,
    "¿cómo va lo mío?", nombres y ficha en clientes, canales, datos y pase en la propuesta, panel).
- **Locución** (`laura`, mejor de 4 tomas, a 1×; fidelidad con el STT):
  - a1 5,44 s (1,00) · a2 5,84 s (1,00; "SQL") · a3 6,32 s (1,00; "rajatabla" bien en la toma) · a4a 6,48 s (1,00) ·
    a4b 2,72 s (1,00) · a4c 3,60 s (1,00) · a4d 2,24 s (1,00) · a5 7,76 s (1,00) · a6a 8,32 s (0,87, solo por "0800" y
    "vos") · a6c 7,76 s (1,00) · a6b 5,36 s (1,00) · a7 2,32 s (1,00).
- **Grafías con laura** (`scratch/videos/candidatas/sqlamoblamientos-laura/`, dos tomas por texto):
  - Escrito "SQL": el STT oyó "esquel" y "Esquele" (2 de 2, la dice como palabra). Con "Ese Cu Ele": "ese cuele" (2 de 2).
    Se mantiene `Ese Cu Ele`.
  - "cero ochocientos" / "cero ochocientos diez": "0800" y "0810" en las dos tomas. Sin cambios.
  - "con voz": el STT escribe "vos" (no distingue; ver VIDEOS.md). "rajatabla": bien.
- **Controles:**
  - `npx tsc --noEmit` sin errores; hojas en `scratch/videos/revision/sqlamoblamientos-analisis-v4/`: sin textos cortados
    ni superposiciones, las animaciones entran con su frase.
  - Transcripción por escena fiel a la locución. Cada voz termina antes de su corte (a2 0,38 s; a3 0,4; a4d 0,44; a5 0,5;
    a6c 0,43; a6b 0,52; a7 0,62) y a1 deja ~0,4 s antes de a2.
- **A revisar antes de mandarlo:**
  - **Duración 71,0 s: pasa el tope de ~70 por 1 s.** Laura es más lenta (+3,7 s de voz). Para bajar, la opción más
    limpia es recortar un texto (por ejemplo, a3 sin "En palabras de Jorge Urizar:", que va escrito en pantalla).
  - **Entonación:** el STT escribe como pregunta a4a ("¿Dónde podríamos mejorar con Atentina?") y, con laura, también el
    final de a6b ("¿Quién la tomó y cuánto tardó?"). Escuchar si suben; si no gustan, regenerar con
    `make video-voces P=sqlamoblamientos-analisis IDS="a4a a6b" TOMAS=4` (la ganancia se aplica sola).
  - Escuchar "Ese Cu Ele" con laura (el STT oye "ese cuele").
  - Lo de v3: funciones sin construir (0800 propio, conexión a pedidos y catálogo, pase a una persona con la charla y la
    ficha, panel), llamadas de WhatsApp para su número (coexistencia y Embedded Signup) y panel ilustrativo.
