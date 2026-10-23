# primeros-pasos · v1

Estado: cerrada (23-10-2026)

- **Archivo:** `primeros-pasos-v1.mp4` · 1080 × 1920 · 69,8 s · −16,7 LUFS · 12,3 MB.
- **Pedido que la originó (23-oct-2026, textual):** "Crea un nuevo video sobre como crear un Agente basico como
  cliente. - formato vertical para mobiles - Voz por defecto (1 sola) - zoom in cuando escriba (sin abusar del
  recurso) - Empieza con gracias por probar Atentina, te cuento como empezar. - que explique los pasos a seguir
  y como hacer una llamada de prueba desde la web."
- **Qué es:** tutorial de primeros pasos para un cliente nuevo, en vertical: crear un agente con el asistente
  básico, elegir voz, completar apertura y base de conocimiento, guardar una versión, y probarlo con una llamada
  desde el navegador (modo prueba), que después queda en Conversaciones. El guion completo está en el
  [`README`](../../README.md).
- **Decisiones:**
  - Una sola voz, `paula`, a 1× (la narradora por defecto de VIDEOS.md). Sin voz secundaria, por pedido.
  - El panel se recrea a 390 px de ancho (vista de cliente) y se muestra dentro de un marco de celular; en los
    tres momentos de tipeo (nombre, apertura y conocimiento) hay un zoom suave de 1,5×, y vuelve. No hay zoom
    en el resto del video.
  - El agente de Atentina se representa con el logo (`AgenteLogo`), no con la mascota.
  - "Casa Norte" y sus datos son ilustrativos; la pantalla de la llamada es genérica.
- **Locución:** 11 líneas en `guion.json`, voz `paula`, `ganancia_db` −1,5. La línea p6 se regeneró con cuatro
  tomas: la primera decía "en base a conocimiento" (el TTS cambiaba el "de" por "a"); con "En la base de
  conocimiento" quedó fiel (1,00). El total de voz es 47,6 s.
- **Controles hechos:**
  - `make video-voces` con fidelidad por STT en todas las líneas (la p6, 1,00 con cuatro tomas).
  - `make video-revisar`: duración, −16,7 LUFS y transcripción por tramos en los 11 cortes de escena.
  - Hojas de cuadros cada 2 s y cuadros sueltos de las escenas de zoom: sin texto cortado ni superposiciones.
- **A revisar antes de mostrarlo afuera:**
  - La grilla de voces muestra seis de las 41 (la UI muestra hasta nueve antes de "Ver todas"); es una
    simplificación para que entre en la pantalla del video.
  - La pantalla de la llamada es una recreación genérica: el link real abre la sala de prueba (LiveKit).
  - "Casa Norte", el nombre del agente, los horarios y la conversación son ilustrativos.
  - Las funciones que se muestran están desplegadas; no se afirma latencia, capacidad ni precios.
