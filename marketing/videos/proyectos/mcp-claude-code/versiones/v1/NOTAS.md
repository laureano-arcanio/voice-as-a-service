Estado: borrador

# MCP en Claude Code v1

## Pedido

El del README del proyecto (tutorial técnico de 90 s: qué es MCP, grupos de herramientas, instalación en Claude
Code con OAuth, demo de cuenta, crear y probar un agente, equipo y derivación, y cierre con el link a la
documentación).

## Qué es

Primera versión. 1920 × 1080, 30 fps, 91,6 s, 10,9 MB. Nueve escenas (guion en el README): intro, grupos,
instalar, autenticar, cuenta, crear, probar, equipo y cierre. Componentes propios en `src/terminal.tsx`
(terminal y sesión de Claude Code simulada, con zoom y resaltado de líneas) y subtítulos en `src/escenas.tsx`.

Herramientas que aparecen (todas reales, de `app/mcp/catalog.py`): `whoami`, `get_plan_tools`,
`list_agent_templates`, `get_agent_template`, `validate_agent_definition`, `create_agent`, `test_agent_start`,
`test_agent_turn`, `create_team_member`, `create_handoff_area`; en la escena de grupos, además, `get_usage`,
`update_agent_definition`, `list_calls`, `get_call`, `start_call`, `create_call_link`, `get_call_link`,
`update_call_link`, `list_whatsapp_accounts`, `set_whatsapp_routes`, `create_whatsapp_template`,
`upsert_contacts`, `import_contacts`, `list_contacts`, `create_campaign`, `start_campaign`,
`get_campaign_stats` y `list_events`.

## Adaptaciones respecto del pedido

- "Probar el agente con una conversación y ver los datos recopilados" existe tal cual: `test_agent_start` y
  `test_agent_turn` (este devuelve la respuesta, `state.fields`, `next_objective` y `status`). Sin adaptación.
- "Lo configura": se muestra dentro de la creación (plantilla → definición con horarios y envíos →
  `validate_agent_definition` → `create_agent`). `update_agent_definition` aparece solo en la escena de grupos.
- La instalación dura 17,2 s (instalar + autenticar) y la creación/configuración de recursos, ~10 s por escena
  (crear y equipo), con la marca ACELERADO en vez de cortes duros.
- Terminal con la ventana de la marca (no la apariencia de Claude Code): el formato de texto sí es el de la
  sesión.

## Locución

- `paula`, 4 tomas por línea, la más fiel según el STT propio: m1 0,99 · m2 0,94 (el STT escribe "87") · m3 1,00
  · m4 0,98 ("ClubeCode", "Authentica") · m5 1,00 · m6 1,00 · m7 1,00 ("de la gente" por "del agente") · m8 1,00
  · m9 0,99. Total 71,8 s.
- Duraciones: m1 8,80 · m2 10,08 · m3 3,92 · m4 8,00 · m5 6,96 · m6 7,92 · m7 7,44 · m8 7,60 · m9 11,04 s.
- Grafía: "M C P" con espacios (candidatas `mcp` y `mcp2`: escrito `MCP`, el STT oyó "MP"/"MTF"; con `M C P`,
  "MCP" en 2 de 2). "Claude Code" escrito normal.

## Controles

- `npx tsc --noEmit` sin errores.
- Cuadros de cada escena (`scratch/videos/mcp/`) y hojas de `make video-revisar`
  (`scratch/videos/revision/mcp-claude-code-v1/`): sin textos cortados ni superposiciones; con zoom, las líneas
  largas de argumentos se cortan a la derecha (a propósito, el foco es el nombre y el resultado).
- **−15,3 LUFS** (referencia −16 ± 1,5), sin `ganancia_db`.
- Transcripción por tramos (cortes en 0, 10,2, 21,8, 29,2, 39,0, 48,0, 57,9, 67,7 y 77,5 s): las nueve líneas se
  entienden; "Cloud Code", "ClubeCode" y "Tentina" son del STT, a confirmar de oído.
- `make video` falló al generar la música: `python3` del sistema no tiene numpy (tampoco `candidatas.py`); se
  generó con `.venv/bin/python scripts/musica.py`. Propuesta: que los targets de video usen `.venv/bin/python`.

## A revisar antes de mostrarlo afuera

- **Menú `/mcp` y mensajes de autenticación de Claude Code:** recreación aproximada (no hubo captura de la sesión
  interactiva). La salida de `claude mcp add` y `claude mcp list` sí es la real (Claude Code 2.1.310).
- **Conexión real desde Claude Code con OAuth:** MCP_PLAN la marca como pendiente ("falta la primera conexión
  real"); la base tiene 4 tokens OAuth desde el 25-oct-2026, pero no consta que alguno sea de Claude Code.
  Conviene hacer el recorrido real una vez y comparar los textos con el video.
- **El badge del consentimiento** ("Identificado por…" o "Registro sin verificar") no se muestra: depende de cómo
  se registre Claude Code.
- **La transferencia a personas no está probada con llamadas reales** (DERIVACIONES_PLAN 13.4). La locución dice
  "el agente transfiere ahí cuando hace falta".
- **Nombres de los planes:** la tabla `tiers` y MCP_HERRAMIENTAS dicen "Central"; `landing/src/data/mcp-tools.json`
  lista "Red". El video solo nombra "Sucursal".
- **Datos ilustrativos:** Ferretería Ejemplo, el email, IDs, consumo, textos del agente, Laura Gómez y su
  teléfono, el área Ventas.
