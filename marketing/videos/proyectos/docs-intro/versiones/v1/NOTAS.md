# docs-intro v1

Estado: cerrada (25-10-2026)

- **Archivo:** `docs-intro-v1.mp4` (1920 × 1080, 30 fps, H.264 + AAC), 44,8 s, −17,0 LUFS, 5,3 MB.
- **Pedido (25-oct-2026):** ver el [README](../../README.md): video corto (30–45 s) que combine MCP y API para la
  portada de la documentación, con locución, subtítulos y música como en `mcp-claude-code` y `api-desarrolladores`.
- **Qué cambió:** primera versión.

## Locución

Mejor de 4 tomas (`make video-voces P=docs-intro TOMAS=4`), `velocidad` 1,05, `ganancia_db` −1,5. Fidelidad 1,00 en
d1 a d4; d5, 0,94 solo porque el STT escribe "atentina.com.ar" por "atentina punto com punto ar". 33,9 s de voz.
Grafías: `M C P`, `ápi` y `ópen, ei, ái` (tabla de VIDEOS.md); el STT oye "MCP", "API" y "OpenAI". Los nombres de
los agentes de IA (Claude, ChatGPT, Cursor) no se dicen: van en pantalla.

## Reutilizado

- De `api-desarrolladores`: subtítulos, aviso de plan (`PlanBadge`), tarjetas de las dos APIs y la línea del SDK de
  OpenAI (copiados a `src/`, no importados, para que cada proyecto se cierre solo).
- De `mcp-claude-code`: el formato `● atentina · <herramienta>` y los paquetes `{ }` entre nodos.
- No se reutilizaron locuciones: las de los dos videos son largas y explican pasos; acá cada línea resume.

## Controles

- `npx tsc --noEmit` sin errores; cuadros de prueba de cada escena (`scratch/videos/docs-intro/`): se acortaron las
  filas de "Tu cuenta" (cortaban en dos líneas) y se achicaron las tarjetas de la API.
- `make video-revisar P=docs-intro V=1 ARGS="--tramos 0,6.6,14,25.4,35.8"`: 44,8 s, −17,0 LUFS (dentro de −16 ± 1,5),
  hojas en `scratch/videos/revision/docs-intro-v1/`, transcripción por escena igual al guion (el STT escribe
  "agente de I" en un tramo; la toma suelta dio "IA").
- **Música:** `make video` corre `scripts/musica.py` con el `python3` del sistema, que no tiene numpy; se generó con
  `.venv/bin/python scripts/musica.py docs-intro` (50 s). Para que `make video` ande en un proyecto nuevo, el target
  debería usar `.venv/bin/python` (no se tocó el Makefile).

## A revisar antes de mostrarlo afuera

- **De oído:** "M C P", "ápi" y "ópen, ei, ái" con paula y gonzalo.
- **Sesión ilustrativa** en la escena MCP (marcada en pantalla).
- **"87 herramientas":** cambia si cambia el catálogo (`make mcp-docs`).
