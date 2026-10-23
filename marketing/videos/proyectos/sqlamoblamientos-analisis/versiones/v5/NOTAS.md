# sqlamoblamientos-analisis · v5

Estado: cerrada (22-10-2026)

- **Archivo:** `sqlamoblamientos-analisis-v5.mp4` · 69,4 s (igual que v3) · −15,7 LUFS (igual que v3)
  (`make video-revisar P=sqlamoblamientos-analisis V=5 ARGS="--tramos 0,7.2,14.1,19.7,36.45,44.45,52.4,59.95,65.75"`).
- **Pedido (22-oct-2026, el usuario por el coordinador):** laura suena mal; recuperar la versión anterior como versión nueva.
- **Qué es:** la v3 tal cual. **`laura` (v4) se descartó por cómo suena, a juicio del usuario.** Con la v4 cerrada, se
  copiaron `v3/fuente/src`, `v3/fuente/guion.json` y `v3/fuente/vo` al proyecto (la locución de `lucas` a 1×, sin
  regenerar): mismos textos, tiempos de escena, animaciones y respiros. El guion no tiene `ganancia_db` (con `lucas` no
  hace falta); solo cambia la nota del guion. `scripts/voces.py` conserva la opción `ganancia_db` (sin uso acá).
- **Controles:** código y locución idénticos a `v3/fuente` (`diff -r` sin diferencias); duración 69,4 s y −15,7 LUFS, como
  v3; transcripción por escena igual a la de v3. `npx tsc --noEmit` no da errores en este proyecto (el único error es de
  `proyectos/cimepa-analisis`, de otra sesión, que no está en `Root.tsx`).
- **A revisar antes de mandarlo:** lo mismo que v3 (escuchar "Ese Cu Ele", "cero ochocientos" y la entonación de a4a;
  duración en el borde de ~70 s; funciones sin construir: 0800 propio, conexión a pedidos y catálogo, pase a una persona
  con la charla y la ficha, panel; llamadas de WhatsApp para su número; panel ilustrativo).
