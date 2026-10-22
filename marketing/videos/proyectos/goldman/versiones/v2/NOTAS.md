# goldman · v2

Estado: cerrada (21-10-2026)

- **Archivo:** `goldman-v2.mp4` · 39,5 s · −14,6 LUFS (`make video-revisar P=goldman V=2
  ARGS="--tramos 0,4.9,14.3,25.6,34.6"`).
- **Pedido (21-oct-2026, el usuario después de ver v1, por el coordinador):** sacar el robot y usar el logo de
  Atentina; "aire" se pronuncia mal (probar "áire", "áires"); la intro con "En Isaías Goldman..." y pausas por
  puntuación; en el problema, la idea "Actualmente, un solo número y el local cerrado no alcanzan."; escribir
  "clasífica"; el cierre "con la temporada" suena raro (algo como "Empecemos un piloto en noviembre, antes del pico de
  consultas."). Máximo 40 s, alineado con el PDF.
- **Qué cambió respecto de v1:**
  - El agente es el logo de Atentina (`AgenteLogo`, nuevo en `src/comun/characters.tsx`), con las barras que se
    mueven con la voz. La mascota no aparece más.
  - Problema: título "Un solo número y el local cerrado **ya no alcanzan.**"; la tarjeta de la espera dice "Sin
    respuesta en minutos" y "Se fue a otro lado". Animaciones resincronizadas con la locución nueva.
  - Escenas: intro 5,5 s, problema 9,4, propuesta 11,3, panel 9,0, cierre 4,9.
  - `tsconfig.json` excluye `proyectos/*/versiones` (las fuentes cerradas rompían `tsc`).
- **Locución** (`lucas`, mejor de 4 tomas; g4 igual a v1):
  - g1 "En Isaías Goldman, en temporada de áires, las consultas no paran." (1,00)
  - g2 "Actualmente, un solo número y el local cerrado no alcanzan. La consulta que no se contesta en minutos, se va
    a otro lado." (1,00)
  - g3 "Nuestro agente atiende las veinticuatro horas el cero ochocientos, el WhatsApp y el chat de la web. Clasífica,
    responde lo general, y deriva a su equipo." (0,85: solo por "24" y "0800" en cifras)
  - g4 "Y todo queda en un panel: cada canal, cada tipo de consulta, tiempos de respuesta, fuera de horario y
    derivaciones por vendedor." (1,00)
  - g5 "Empecemos un piloto en noviembre, antes del pico de consultas." (1,00)
- **Grafías probadas** (`scripts/candidatas.py goldman`, dos tomas por texto, en
  `scratch/videos/candidatas/goldman/`): `aires` / `áires` / `aire acondicionado`; `Goldman` / `Góldman` /
  `Gold man`; `clasifica` / `clasífica`; dos cierres. El STT transcribe igual todas (no oye el acento), salvo
  `Góldman`, que en una toma salió "Colman". Elegidas: `áires` y `clasífica` (las que pidió el usuario), `Goldman` sin
  tilde y "Empecemos un piloto en noviembre, antes del pico de consultas.". **Falta escucharlas:** no pude
  verificar de oído dónde cae el acento.
- **Controles:** `npx tsc --noEmit` sin errores; cuadros de cada escena (`scratch/videos/goldman/v2-*.png`) y hojas
  (`scratch/videos/revision/goldman-v2/`): sin textos cortados ni superposiciones. Transcripción por escena fiel.
- **A revisar antes de mandarlo:** lo mismo que v1 (funciones de la oferta sin construir: transferencia de la
  llamada, relay de WhatsApp, chat web, métricas del panel por tipo, canal, horario y persona; panel ilustrativo;
  0800/0810 de ellos a dar de alta con Anura) y escuchar "áires", "clasífica" y "Goldman".
