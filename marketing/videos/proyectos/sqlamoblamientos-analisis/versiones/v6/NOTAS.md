# sqlamoblamientos-analisis · v6

Estado: borrador

**Prueba de voz** (pedido del usuario): la v5 con la narradora `paula`. La versión de referencia sigue siendo la v5
(`lucas`) hasta que el usuario elija.

- **Archivo:** `sqlamoblamientos-analisis-v6.mp4` · 62,0 s · −15,7 LUFS (`make video-revisar P=sqlamoblamientos-analisis V=6
  ARGS="--tramos 0,6.6,12.0,17.0,31.7,38.9,46.8,53.5,58.7"`).
- **Pedido (22-oct-2026, el usuario por el coordinador):** versión de prueba con la voz `paula` (arf_03853, mujer):
  mismos textos, escenas y visuales que la v5, toda la locución regenerada a 1× (mejor de 4 tomas), grafías revisadas,
  tiempos y animaciones ajustados, volumen en rango, tope ~70 s.
- **Qué cambió respecto de v5** (v5 cerrada antes):
  - Las 12 líneas con `paula`: 54,3 s de voz (60,5 con `lucas`). Paula es más rápida (17,1 car/s en el catálogo).
  - **Nivel:** sin ajuste daba −14,3 LUFS (fuera de −16 ± 1,5); `"ganancia_db": -1.7` en el guion: −15,7 LUFS.
  - **Escenas:** intro 7,6 → 7,0 s, bien 7,1 → 5,6, cita 5,6 → 5,0, mejorar 16,75 → 14,7 (`GAP` 0,45, respiro ~0,7 s),
    clientes 8,0 → 7,2, propuesta 15,5 → 14,6 (a6c a 0,3 s de a6a), panel 5,8 → 5,2, cierre 3,6 → 3,3.
  - Momentos de cada animación rehechos con las pausas de sus tomas (comentarios `v6 (paula)` en `src/`).
- **Locución** (`paula`, mejor de 4 tomas, a 1×; fidelidad con el STT):
  a1 4,72 s (1,00; la primera tanda dio 0,99, "atendía", y se regeneró) · a2 5,04 s (0,99; regenerada: la primera, 0,97,
  "ese Q el amoblamiento") · a3 4,56 s (1,00) · a4a 5,12 s (1,00) · a4b 2,56 s (1,00) · a4c 2,96 s (1,00) · a4d 2,48 s
  (1,00; regenerada, en la mezcla el STT oía "Viene atención") · a5 6,80 s (1,00) · a6a 7,60 s (0,87, solo por "0800" y
  "vos") · a6c 6,08 s (1,00) · a6b 4,16 s (1,00) · a7 2,24 s (1,00; regenerada, en la mezcla el STT oía "Ajedendamos").
- **Grafías con paula** (`scratch/videos/candidatas/sqlamoblamientos-paula/`, dos tomas por texto):
  - Escrito "SQL": "Esquivel" y "Esquel" (2 de 2: la lee como palabra). Con "Ese Cu Ele": "SQL" y "ese Q, el". Se
    mantiene `Ese Cu Ele`. En la toma elegida el STT oye "SQL amoblamiento" (puede comerse la "s" final: escuchar).
  - "cero ochocientos" / "cero ochocientos diez": "0800" y "0810", 2 de 2. "rajatabla": bien (el STT la escribe con mayúscula).
  - Entonación: a4a la transcribe como pregunta ("¿Dónde podríamos mejorar con Atentina?"), como con lucas y laura; el
    final del panel (a6b) sale como afirmación, y el final de a5 ("¿Les pasa cada consulta lista?") como pregunta.
- **Controles:** `npx tsc --noEmit` sin errores en el proyecto (el error de `proyectos/cimepa-analisis` es de otra sesión);
  hojas en `scratch/videos/revision/sqlamoblamientos-analisis-v6/` sin textos cortados ni superposiciones; transcripción
  por escena fiel; cada voz termina antes de su corte (la más justa, a5, 0,34 s) y a1 deja ~0,5 s antes de a2.
- **A revisar:**
  - Escuchar paula entera y decidir si reemplaza a `lucas` (a juicio del usuario: laura se descartó por cómo sonaba).
  - Escuchar "Ese Cu Ele Amoblamientos" (la "s" final), la entonación de a4a y el final de a5, que puede sonar a pregunta.
  - Lo de v3/v5: funciones sin construir (0800 propio, conexión a pedidos y catálogo, pase a una persona con la charla y
    la ficha, panel), llamadas de WhatsApp para su número y panel ilustrativo.
