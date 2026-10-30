# atencion-punta-a-punta v1

Estado: borrador

- **Archivo:** `atencion-punta-a-punta-v1.mp4` (1920 × 1080, 30 fps, H.264 + AAC), 54,7 s (54,72 s por ffprobe),
  −16,1 LUFS, 6,3 MB.
- **Pedido (30-oct-2026):** el del [README](../../README.md): video publicitario de 60 s como máximo, de punta a
  punta (atiende, consulta y registra, deriva a uno o más operarios, toma el mensaje, queda registrado), con los
  retratos de las voces, el diagrama como protagonista, paula y gonzalo en partes iguales y un cierre con tildes.
- **Qué cambió:** primera versión.

## Locución

Mejor de 4 tomas (`make video-voces P=atencion-punta-a-punta TOMAS=4`), `velocidad` 1,08, `ganancia_db` −1,5.
Alternadas: paula d1, d3, d5, d7, d9 (22,2 s); gonzalo d2, d4, d6, d8, d10 (21,8 s); 44,0 s de voz en 54,7 s.
Fidelidad 1,00 salvo d1 (0,99: el STT escribe "funciona Tentina") y d10 (0,92: escribe "atentina.com.ar" por "atentina
punto com punto ar", y "Empieza" por "Empezá"). Sin grafías forzadas.

Ajustes: d1 era "Así atiende Atentina a tus clientes…" y en el video el STT oyó "atiéndate en Tina": se reescribió.
d2, d8 y d10 se alargaron unas palabras para emparejar el tiempo de las dos voces (de 22,1 / 21,4 s a 22,2 / 21,8 s).

## Reutilizado

- De `docs-intro`: subtítulos (`Subtitulos`, `sub`), `PlanBadge` y la estructura de intro y cierre en fondo oscuro
  (copiados a `src/`, no importados).
- De `landing-agente`: la idea del aro de puntos alrededor del logo (reescrito, más simple).
- De `derivaciones`: el recorrido de la derivación (orden, espera, aviso, si nadie atiende), en otro formato.

## Controles

- `npx tsc --noEmit` sin errores. Cuadros de prueba en `scratch/videos/atencion-punta-a-punta/`: se cortó en dos
  líneas a mano el globo "No pude comunicarte con Ventas. ¿Te tomo el mensaje?", la línea al sistema sigue al chip
  cuando se achica y se acortó "Te armo el precio" (partía en dos líneas).
- `make video-revisar P=atencion-punta-a-punta V=1 ARGS="--tramos 0,4.2,8.1,13.4,18.9,23.9,28.4,32.8,38.68,47.36"`:
  54,7 s, −16,1 LUFS, hojas en `scratch/videos/revision/atencion-punta-a-punta-v1/`, transcripción por tramo igual
  al guion (salvo "Tentina" y "atentina.com.ar", arriba). En la primera hoja los títulos del diagrama se
  superponían al cambiar: ahora el anterior se va antes de que entre el siguiente.
- **Música:** `make video` la genera con el `python3` del sistema, sin numpy; se generó antes con
  `.venv/bin/python scripts/musica.py atencion-punta-a-punta` (62 s), como en `docs-intro`.

## A revisar antes de mostrarlo afuera

- **WhatsApp para clientes:** en producción con el número de Atentina; el número propio del cliente está desplegado
  sin probar y el alta con la app de Atentina espera a Meta (WHATSAPP.md). El video dice "teléfono, WhatsApp y web"
  como la landing.
- **Cuántas personas por plan:** la landing dice Mostrador 1 y Sucursal 2; EQUIPO_TELEFONIA.md dice Sucursal 5
  (`max_team_members`). El video muestra dos personas y lo deja en "según el plan".
- **De oído:** "Así funciona Atentina" (las dos "a" seguidas) y "Empezá hoy".
- **Datos ilustrativos:** Tomás Ríos, pedido 4821, Valentina y Lucas, Ventas "Lun a vie, 9 a 18", 10:42 y 3:12.
