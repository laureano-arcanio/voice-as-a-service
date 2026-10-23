# sqlamoblamientos-analisis · v2

Estado: cerrada (22-10-2026)

- **Archivo:** `sqlamoblamientos-analisis-v2.mp4` · 64,1 s · −15,3 LUFS (`make video-revisar P=sqlamoblamientos-analisis V=2
  ARGS="--tramos 0,6.2,13.2,18.8,35.55,43.55,54.75,60.55"`).
- **Pedido (22-oct-2026, el usuario por el coordinador):** 1. en la escena "bien", "LO QUE YA HACEN BIEN" pasa a "LO QUE
  YA HACEN MUY BIEN"; 2. en "mejorar", la frase "Y una cocina se piensa de noche, con la casa cerrada." se reemplaza por
  una sobre atención en horario reducido (texto del usuario: "Atención en horario reducido"), con la tarjeta de 44 de
  168 h alineada y sin la idea de "la cocina se piensa de noche" en pantalla.
- **Qué cambió respecto de v1** (v1 cerrada antes de tocar el código, con su `fuente/`):
  - Rótulo "LO QUE YA HACEN MUY BIEN" en `bien` y en `cita` (es la misma sección) y "Lo que ya hacen muy bien" en el
    índice de la intro, para que coincidan.
  - a4d: "Y la atención, en horario reducido." (2,48 s; antes 3,60 s). Única línea regenerada.
  - Tarjeta de horario: rótulo "HORARIO REDUCIDO", título "Atención en horario reducido: 44 de las 168 horas",
    oportunidad "responder también fuera de horario y dejar la visita o la medición agendada." (antes "responder en ese
    momento..."). La oportunidad entra 0,5 s antes, porque la frase es más corta.
  - Escena `mejorar` de 17,85 a 16,75 s; el resto, igual. Total 64,1 s.
- **Locución:** igual a v1 salvo a4d (`lucas`, mejor de 4 tomas, a 1×, fidelidad 1,00: "Y la atención en horario reducido.").
- **Controles:**
  - `npx tsc --noEmit` sin errores; cuadros de `bien` y `mejorar` (`scratch/videos/sqlamoblamientos-analisis/v2-*.png`) y
    hojas (`scratch/videos/revision/sqlamoblamientos-analisis-v2/`): sin textos cortados ni superposiciones.
  - Transcripción por escena fiel a la locución; a4d termina 0,38 s antes del corte de `mejorar`; respiro entre tarjetas
    sin cambios (~0,65 s).
  - Sin "cocina se piensa de noche" en el código de las escenas ni en la locución.
- **A revisar antes de mandarlo:** lo mismo que en v1 (escuchar "Ese Cu Ele" y la entonación de a4a; funciones sin
  construir; "¿cómo va lo mío?" como inferencia; panel y mensajes de posventa ilustrativos).
