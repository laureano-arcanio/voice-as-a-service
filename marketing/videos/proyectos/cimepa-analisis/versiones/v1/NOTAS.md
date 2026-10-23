# cimepa-analisis · v1

Estado: cerrada (22-10-2026)

- **Archivo:** `cimepa-analisis-v1.mp4` · 65,2 s · −15,7 LUFS (`make video-revisar P=cimepa-analisis V=1
  ARGS="--tramos 0,6.35,20.65,27.85,36.5,43.4,52.5,61.8"`).
- **Pedido (22-oct-2026, agente principal por Laureano):** video nuevo con el formato y el contenido del PDF
  `cimepa-propuesta` v1, técnico (sin "qué hacen bien / dónde mejorar"), para Pablo; ocho escenas en ~60 s (hasta ~65).
  Texto completo y reglas en el [README](../../README.md).
- **Qué es:** el PDF en video, con el código de baicenter-analisis v1 adaptado (intro, pie, tarjetas, paquetes que
  viajan, `AgenteLogo`). Escenas: intro 6,95, pedido 14,3, entra 7,2, empleado 8,65, ia 6,9, registro 9,1, agente
  9,3 y cierre 3,4 s.
- **Locución** (`lucas`, mejor de 4 tomas, a 1×; entre paréntesis, fidelidad con el STT):
  - c1 "Un número de la empresa para su equipo y su IA, todo grabado y transcripto." (1,00)
  - c2a "En CIMEPA nos pidieron que su equipo remoto llame sin teléfono." (1,00; "Cimepa")
  - c2b "Que su asistente de IA llame y atienda." (1,00)
  - c2c "Transferir entre la IA y una persona." (1,00)
  - c2d "Y todo grabado y transcripto, por ápi." (1,00)
  - c3 "Entra una llamada, y la atiende la IA. Resuelve, o la deriva al celular del empleado, con un resumen." (1,00)
  - c4 "Un empleado llama desde la app web, en la compu o el celular: elige el contacto, un clic, y sale con el número
    de la empresa." (1,00; con "Llama un empleado: desde la app web..." el STT oyó "Llama a un empleado" en dos
    rondas, y se dio vuelta la frase)
  - c5 "Llama la IA: seguimientos programados por ápi, con su contexto y sus instrucciones." (1,00)
  - c6 "Todo queda registrado: grabación y transcripción de toda la llamada, en el panel y por ápi. Inferencia propia,
    en Argentina." (1,00 sola; en el tramo del video mezclado con la música el STT oyó "en el panel iPhone API")
  - c7 "Su agente: tres vías, para definir en una charla técnica. En tiempo real, por SIP, o nuestro agente, con su
    contexto y su modelo." (1,00; en una toma anterior el STT oyó "por sí" y en otra "por Zip")
  - c8 "¿Agendamos la charla técnica?" (1,00)
- **Pronunciación:** pruebas en `scratch/videos/candidatas/cimepa/` (grupo `cimepa` en `scripts/candidatas.py`): CIMEPA,
  Cimepa y Simepa salen igual ("Cimepa" 6 de 6): va escrito normal. `ápi` es la grafía de la tabla (decisión del
  20-oct-2026); con "API" escrito el STT transcribe lo mismo y no distingue el acento: escuchar.
- **Recortes para entrar en ~65 s** (la primera ronda daba ~68 s): sin "cuatro cosas" en c2a, sin "al número de la
  empresa" en c3, sin "de la agenda" en c4, y escenas con ~0,2 s después de cada voz.
- **Controles:**
  - `npx tsc --noEmit` sin errores.
  - Cuadros de prueba (`scratch/videos/cimepa-analisis/`) y hojas (`scratch/videos/revision/cimepa-analisis-v1/`):
    sin textos cortados ni superposiciones (se acortaron los títulos de "Llama la IA" y del registro a una línea y se
    ensanchó el nodo "Número de la empresa").
  - Transcripción por escena fiel a la locución (salvo "iPhone" en el tramo del registro, ver arriba). Cada voz termina
    antes de su corte: la más justa, c2d, 0,2 s antes del final de `pedido`; entre el final de c1 y c2a quedan ~0,2 s de archivo (~0,5 s de silencio con el de las tomas).
  - Sin precios, sin Anura ni Asterisk, sin logo de CIMEPA; el agente es el logo.
- **A revisar antes de mandarlo:**
  - Escuchar "ápi" (c2d, c5, c6; en c6 el STT del video mezclado oyó "iPhone") y "SIP" en c7.
  - Escuchar el respiro entre c2a y c2b (~0,6 s, un poco más corto que los otros dos).
  - Duración 65,2 s: en el borde del margen de ~65.
  - Funciones que el video muestra y no están construidas (cimepa.md, 7.4): app web para que llame el equipo,
    transferencia IA ↔ persona y derivación al celular con resumen, grabación de la llamada entera con los tramos de
    personas, conexión de un agente propio por WebRTC o SIP. Las campañas con webhook están sin desplegar.
  - "3 o más llamadas simultáneas": es la oferta; con Gemma no hay CAP medido.
  - Ilustrativos (rotulados en los pies): resumen, agenda, horarios, llamada y transcripción de ejemplo, pantalla de la
    app web.
