# goldman · v1

Estado: cerrada (21-10-2026)

- **Archivo:** `goldman-v1.mp4` · 38,4 s · −15,0 LUFS (`make video-revisar P=goldman V=1
  ARGS="--tramos 0,3.8,13.4,24.0,33.2"`).
- **Pedido:** "Una introducción al problema que vimos. Y luego la propuesta concreta que le damos. Simple, elegante y
  con target a este cliente. 40 segundos máximo." (con el detalle del contenido: problema, tres canales, observabilidad
  con peso visual, cierre con piloto desde noviembre, sin precios). Primera versión.
- **Decisiones:** solo narrador `lucas` (sin diálogo, para entrar en 40 s); se nombra a "Isaías" en la primera frase y
  "Goldman" va solo escrito; "su equipo" / "su web" en tercera persona (la empresa), sin voseo directo al dueño; el
  panel es la escena más cargada; títulos del cierre, la propuesta y el panel, y los números del panel, alineados con el
  PDF `goldman-propuesta` v1, que va junto al video; el panel resalta cada métrica cuando se nombra. Se agregó el ícono `chart` a
  `src/comun/ui.tsx` (no cambia los otros videos).
- **Locución:** g1–g5 con `lucas`, mejor de 4 tomas. Fidelidad 1,00 salvo g3 (0,88), que es solo por
  "veinticuatro" y "cero ochocientos" transcritos en cifras: la toma dice el texto completo. Transcripción por
  escena: fiel.
- **Controles:** `npx tsc --noEmit` sin errores; cuadros de cada escena (`scratch/videos/goldman/`) y hojas de
  revisión (`scratch/videos/revision/goldman-v1/`): sin textos cortados ni superposiciones.
- **A revisar antes de mandarlo** (detalle en el README, "Afirmaciones"):
  - Se presenta como oferta lo que falta construir: transferencia de la llamada, relay de WhatsApp a vendedor o
    soporte, chat en la web con el contexto de la página, y en el panel las métricas por tipo, por canal (con web),
    fuera de horario y derivaciones por persona. El piloto de noviembre depende de eso (7.5 del documento propone
    arrancar con derivación por ficha si no llega).
  - Todos los números del panel son ilustrativos (los del ejemplo del PDF, y el panel lo dice), y la pantalla es una
    maqueta.
  - El 0800/0810 de ellos no existe todavía (alta con Anura).
