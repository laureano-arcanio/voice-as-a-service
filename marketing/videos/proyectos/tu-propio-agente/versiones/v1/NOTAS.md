# tu-propio-agente v1

Estado: cerrada (25-10-2026)

- **Archivo:** `tu-propio-agente-v1.mp4` (1920 × 1080, 30 fps, H.264 + AAC), 86,0 s, −16,7 LUFS, 11 MB.
- **Pedido (25-oct-2026):** ver el [README](../../README.md): el video de `/desarrolladores/docs/tu-propio-agente`,
  hermano de `mcp-claude-code`, `api-desarrolladores` y `docs-intro`, 60–100 s, paula y gonzalo, con subtítulos.
- **Qué cambió:** primera versión.

## Locución

Mejor de 4 tomas (`make video-voces P=tu-propio-agente TOMAS=4`), `velocidad` 1,05, `ganancia_db` −1,5. 68,4 s de voz.
Fidelidad: t2, t4, t5, t6, t7, t8 y t9, 1,00; t1 y t3, 0,99 (el STT oye "a Tentina" y "vos" por "voz"); t10, 0,95
solo porque escribe "atentina.com.ar". t7 se regeneró dos veces: con gonzalo, "una key de llamadas" salió "un aquí"
(0,95) y "la key", "la que" (0,97); quedó "con una ápi key de llamadas" (1,00, el STT oye "API Key").

Grafías: `ápi`, `ópen, ei, ái` y `M C P` (tabla de VIDEOS.md); "endpoint" y "streaming", escritos normal (el STT los
oye bien en todas las tomas). `end_call` y `transfer_call` no se dicen ("una corta y elige el resultado, la otra
transfiere"): van en pantalla, como las herramientas en `mcp-claude-code`. Fila nueva en la tabla de grafías.

## Reutilizado

- De `api-desarrolladores` y `docs-intro`: subtítulos, `PlanBadge`, `Nota`, `Code` (código con líneas resaltadas),
  intro y cierre oscuros (copiados a `src/`, no importados, para que el proyecto se cierre solo).
- De `docs-intro`: el ícono de código (`IconoCodigo`) y los paquetes que viajan entre nodos.
- El panel se recreó (no capturas): ver el README, "Afirmaciones".

## Controles

- `npx tsc --noEmit` sin errores; cuadros de prueba de cada escena (`scratch/videos/tu-propio-agente/`): se acortó el
  título de `reparto` (cortaba en dos líneas), se subió la ventana del pedido en `turno` (rozaba los subtítulos), se
  agrandaron los textos del panel en `configurar` y las tarjetas de `errores`, y la línea de 1 s de `latencia` ya
  no cruza la nota.
- `make video-revisar P=tu-propio-agente V=1 ARGS="--tramos 0,7.8,17.6,28.6,37.4,45.6,60.2,69.0,76.6"`: 86,0 s,
  −16,7 LUFS (dentro de −16 ± 1,5), hojas en `scratch/videos/revision/tu-propio-agente-v1/`, transcripción por
  escena igual al guion salvo errores del STT ("a Tentina", "Tu gente" en la mezcla de t2, que en la toma suelta salió bien).
- **Música:** generada con `.venv/bin/python scripts/musica.py tu-propio-agente` (100 s), como en `docs-intro`.

## Para YouTube (propuesta, sin subir)

**Título:** Tu propio agente de IA con la voz y el teléfono de Atentina (custom LLM)

**Descripción:**

```text
Si ya tenés tu agente de IA, con su prompt, sus herramientas y tus datos, conectalo a Atentina con un endpoint compatible con la API de OpenAI (POST /chat/completions con stream: true) y atiende llamadas y WhatsApp con un número argentino, sin construir el pipeline de voz.

Atentina pone el número, las llamadas entrantes y salientes, WhatsApp, el link para llamar, la transcripción, la detección de turnos e interrupciones, la voz argentina, la grabación, los minutos y la derivación a tu equipo. En cada turno le manda a tu endpoint toda la conversación, con los datos de la llamada en headers X-Atentina-*, y dice lo que responde a medida que llega. Tu agente corta con end_call (eligiendo el resultado) o pasa la llamada a una persona con transfer_call.

Se configura en tres pasos:
1. La conexión: la URL https de tu endpoint y su API key (tipo "OpenAI compatible").
2. Probar el endpoint: mide cuánto tarda el primer texto.
3. En el agente: "Que conteste tu propio agente".
También por API (key calls) o por MCP (create_llm_connection, test_llm_connection, create_agent).

Disponible en el plan Red.

Documentación completa: https://atentina.com.ar/desarrolladores/docs/tu-propio-agente

00:00 Qué es
00:17 Cómo funciona un turno
00:28 end_call, transfer_call y un endpoint de ejemplo
00:45 Configurarlo en tres pasos
01:00 Latencia, errores y plan
```

## A revisar antes de mostrarlo afuera

- **Despliegue:** `AGENTE_EXTERNO_PLAN.md` dice "sin desplegar", pero los contenedores `app` y `agent` (creados el
  25-oct-2026 18:18) ya tienen `app/llm/external.py` y la base está en la migración 0030. La landing con la página
  no está publicada: el video la nombra, así que va junto con ella.
- **Sin llamada real todavía** (plan, sección 10): la latencia es del cliente de la plataforma contra el ejemplo, no
  de una llamada. Se dice "con el endpoint de ejemplo" y en pantalla, "Medido el 25-oct-2026" con el modelo.
- **"OpenAI compatible" vs "Compatible con OpenAI":** el panel dice "OpenAI compatible" (`KIND_LABEL`) y la página,
  "Compatible con OpenAI". En pantalla va el del panel; en la descripción, el de la página.
- **El modal de Nueva conexión dice "Si falla, el agente sigue con el modelo atentina-conversational-v1"**, que no
  vale para un agente propio (no hay respaldo). No se muestra en el video; conviene ajustar el texto del panel.
- **Ilustrativo:** "Mi agente", `tu-agente.com/v1`, "ventas", el aviso "primer texto 420 ms" (ejemplo de la
  página, marcado) y la conversación de Acme.
- **"Red" vs "Central":** la landing dice Red y la base, Central.
- **De oído:** "endpoint", "streaming", "ápi key" (gonzalo) y "M C P".
