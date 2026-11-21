# v1 · Prueba del pipeline de imágenes

Estado: borrador

- **Pedido (21-nov-2026, textual):** "produci un video de prueba con imagenes, de atentina."
- **Qué prueba:** el pipeline recuperado de punta a punta: `make imagenes-up` (API Qwen-Image-2.1 en :8210) →
  `make video-imagen` → escenas de Remotion → render.
- **Imágenes:** tres, con `imagen.py` (Qwen-Image-2.1, 1024x576, 12 pasos, ~10,3–10,5 s c/u, semillas
  5201–5203; prompts y tiempos en `imagenes.json`): `01-cafe` y `02-oficina` en estilo `foto` de día y
  `03-marca` en estilo `marca` (placa blanca con grilla de puntos).
- **Estructura:** intro blanca (logo + "Atendé cada llamada, a cualquier hora."), `cafe` ("El teléfono suena
  mientras atendés."), `equipo` ("Lo importante le llega a tu equipo."), `marca` ("La conversación, los datos y
  el resultado.") y cierre blanco con logo, `atentina.com.ar` y el 0800-220-1233. Sin locución (el TTS del
  entorno está apagado); música determinística de `scripts/musica.py` (23 s).
- **Cambio en lo común:** `Montaje` suma el prop opcional `musicVolume` (default 0,32; sin cambios para el resto).
  Sin locución, la música a 0,32 dejaba el video en −23,4 LUFS; con `musicVolume 0.75` queda en el estándar.
- **Controles:** `npx tsc --noEmit` sin errores; cuadros por escena en `scratch/videos/prueba-*.png`; hoja cada
  2 s en `scratch/videos/revision/prueba-imagenes-v1/` (arranca en blanco puro, fotos expuestas, placa blanca,
  cierre en blanco); duración 21,8 s; volumen integrado **−16,0 LUFS** (LRA 2,1); 5,7 MB.
- **Exposición de las fotos** verificada por estadística (media 137–139, p99 ≤ 248, quemado ≤ 0,01 %) con la
  fórmula de prompt de exposición balanceada medida el 19-nov.
- **Sin revisar (esta sesión no puede ver imágenes):** la composición visual fina de los tres PNG y su lectura
  sobre el velo blanco. Mirar `public/proyectos/prueba-imagenes/img/` y la hoja de cuadros antes de dar por
  buena la prueba; si una imagen no convence, regenerarla con otra semilla y `make video P=prueba-imagenes V=1`.
