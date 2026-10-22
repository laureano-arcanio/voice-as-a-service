# transcripcion · v1

Estado: borrador

- **Archivo:** `transcripcion-v1.mp4` · 42,4 s · −16,0 LUFS (`make video-revisar P=transcripcion V=1
  ARGS="--tramos 0,7.0,18.6,27.8,36.8"`).
- **Pedido:** el del README del proyecto (textual). Primera versión.
- **Decisiones:** se suelta un audio (`llamada-0142.wav`), no un `.txt` (para transcribir hace falta audio); lo que
  se descarga es el `.txt`. Solo narrador `lucas`, sin diálogo con audio ni personajes, para que quede limpio.
- **Locución:** t1–t5 con `lucas`, mejor de 4 tomas. Fidelidad 0,99–1,00 salvo t3 (0,92), que es solo por "41"
  en cifras y "API"/"OpenAI" escritos en inglés: la toma dice el texto completo. Transcripción por escena: fiel
  (la única diferencia es "voz"/"vos", que el STT no distingue).
- **Controles:** `npx tsc --noEmit` sin errores; cuadros de cada escena (`scratch/videos/transcripcion/`) y hojas de
  revisión (`scratch/videos/revision/transcripcion-v1/`): sin textos cortados ni superposiciones.
- **A revisar antes de mostrarlo afuera** (detalle en el README, "Afirmaciones"):
  - La pantalla del panel (soltar la grabación, transcripción por turnos, Descargar TXT / JSON) **no existe** en
    `web/`: hoy la transcripción es por API. Mostrarla como lo que se arma para el cliente, o construirla.
  - La separación Agente / Cliente sale de grabaciones estéreo (un canal por lado); el STT no separa hablantes.
  - Tiempo real, sentimiento y extracción de datos sobre llamadas de su central: "integración a medida", sin
    producto listo (el sentimiento no existe hoy como función).
  - "Al instante": medido con audios cortos (4 s en 0,13 s); no con una llamada de 3 minutos.
