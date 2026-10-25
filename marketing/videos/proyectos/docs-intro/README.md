# Introducción a la documentación (MCP y API)

Resumen corto para la portada de la documentación (`/desarrolladores/docs`): Atentina se usa desde el panel, desde
tu agente de IA por MCP o desde tu sistema por API; las tres hacen lo mismo con tu cuenta y dentro de tu plan.

## Pedido

> (25-oct-2026, resumido fiel) Un video nuevo y corto que combine MCP y API, para la introducción de la
> documentación (`/desarrolladores/docs`, `landing/src/pages/desarrolladores/docs/index.astro`). Reutilizar lo que
> sirva de `mcp-claude-code` y `api-desarrolladores`. Es un resumen para la portada: Atentina se usa de tres formas
> (panel, tu agente de IA por MCP sin programar, tu sistema por API: agentes, llamadas, campañas, y motores de
> LLM/STT/TTS compatibles con OpenAI), las dos hacen lo mismo con tu cuenta y dentro de tu plan, y al final invita a
> ver la documentación de cada una. Fuente: `landing/src/pages/desarrolladores/docs/{index,mcp,api}.astro`.
> 16:9 1080p, 30–45 s, locución con el TTS propio (`paula`, `gonzalo` secundaria si suma), subtítulos quemados y
> música como en los otros dos. No se sube a YouTube desde acá.

## Público, mensaje y formato

- **Público:** quien entra a la documentación (desarrolladores, usuarios técnicos y clientes que evalúan MCP o API).
- **Mensaje:** tres formas de usar Atentina, con una sola cuenta: elegí la tuya y seguí con su documentación.
- **Publicado (25-oct-2026):** https://www.youtube.com/watch?v=CjHwklFYP0M (público), embebido en la portada de `/desarrolladores/docs`, arriba de los videos de MCP y API.
- **Formato:** 1920 × 1080, 30 fps, 44,8 s. Composición `docs-intro` (`src/Video.tsx`). Subtítulos quemados (abajo
  al centro, con la grafía normal) y música de `scripts/musica.py`.
- **Contexto:** portada de la documentación, arriba de los dos videos largos
  ([`mcp-claude-code`](../mcp-claude-code/README.md) y [`api-desarrolladores`](../api-desarrolladores/README.md)).

## Guion (v1)

| Escena | s | Voz | Qué se dice | Qué se ve |
|---|---|---|---|---|
| `intro` | 7,2 | d1 paula | Atentina se usa de tres formas: desde el panel, desde tu agente de IA, o desde tu sistema. | Fondo oscuro: logo, "DOCUMENTACIÓN · MCP Y API", "Tres formas de usar Atentina, **con una sola cuenta.**" y tres chips que se encienden al nombrarlos: El panel, Tu agente de IA (MCP), Tu sistema (API) |
| `formas` | 7,4 | d2 paula | Las tres hacen lo mismo, con tu cuenta y dentro de tu plan. | "Las tres hacen lo mismo, **con tu cuenta y tu plan.**" Tres tarjetas (panel `app.atentina.com.ar`, MCP `/mcp`, API `/api/v1`) con paquetes `{ }` que llegan a la misma tarjeta "Tu cuenta" (logo del agente): tus agentes, llamadas y campañas; los permisos de tu usuario o tu key; aviso de plan "Minutos, funciones y topes de tu plan" |
| `mcp` | 11,4 | d3 paula | Por M C P, conectás tu agente de IA y le pedís en español lo que necesitás: armar y probar agentes, revisar las llamadas o lanzar una campaña. Sin programar. | "MCP · sin programar", "Tu agente de IA **maneja tu cuenta.**" Tarjeta con la URL `https://app.atentina.com.ar/mcp`, Claude, ChatGPT, Cursor, Claude Code (solo texto), login y "87 herramientas; `get_plan_tools`…". Ventana "tu agente de IA" con el pedido de ejemplo de la doc y las herramientas (`get_agent_template`, `create_agent`, `test_agent_start`, `test_agent_turn`). Tres tarjetas que se encienden con la locución (campaña "según el plan") y la píldora "Sin programar" |
| `api` | 10,4 | d4 gonzalo | Por ápi, tu sistema maneja agentes, llamadas y campañas, y usa los motores de lenguaje, transcripción y voz, compatibles con ópen, ei, ái. | "API · para tu sistema", "Tu sistema, integrado **con una API key.**" Tarjeta de plataforma (`/api/v1`, `calls`: agentes, llamadas, campañas, eventos y webhook; aviso de plan) y de inferencia (`/api/v1/inference`, `llm stt tts`: chat, transcripción, voz con 41 voces, `OpenAI(base_url=…)`; "Todos los planes, Free incluido, con cupo por mes") |
| `cierre` | 9,0 | d5 paula | Elegí la forma que te sirva. La documentación de cada una está en atentina punto com punto ar, barra desarrolladores. | Fondo oscuro: logo, "Elegí la forma **que te sirva.**", tarjetas MCP (`/desarrolladores/docs/mcp`) y API (`/desarrolladores/docs/api`), `atentina.com.ar/desarrolladores/docs` y "Con un video paso a paso de cada una" |

Voces: `paula` narradora y `gonzalo` en la línea de la API (contrapunto: cada forma con su voz). `velocidad` 1,05 y
`ganancia_db` −1,5, como en `api-desarrolladores`.

## Afirmaciones y fuentes

- **Tres formas que hacen lo mismo, con tu cuenta y dentro de tu plan:** `lead` de
  `landing/src/pages/desarrolladores/docs/index.astro`.
- **MCP:** URL, agentes compatibles (Claude, ChatGPT, Cursor, Claude Code), "pedile en español", login con tu
  usuario, "solo tu cuenta" y el pedido de ejemplo (`asks[0]`): `mcp.astro`. 87 herramientas: 90 de
  `landing/src/data/mcp-tools.json` menos las 3 de `inference` (las que van sin `?toolsets=`, como en
  `mcp-claude-code`). Nombres de herramientas: `app/mcp/catalog.py`. Campañas según el plan: tabla de planes de `api.astro`.
- **API:** dos APIs, URL base, alcances (`calls`, `llm`, `stt`, `tts`), rutas, compatibilidad con el SDK de OpenAI,
  41 voces y webhook solo en campañas (`callback_url`) y `/events`: `api.astro` y `docs/API_INFERENCIA.md`.
  "Llamadas telefónicas y campañas, según el plan": `planFeatures` de `api.astro` (Free sin llamadas salientes ni campañas).
  "Free incluido, con cupo por mes": tabla `tiers` (consulta del 25-oct-2026: Free con 262.144 tokens y 20 min de TTS/STT).
- **Ilustrativo:** la sesión del agente de IA (la respuesta "Creé 'Turnos Peluquería'…" y "versión 1"), marcada en
  pantalla como "sesión ilustrativa". No se creó nada en la plataforma.
- **Sin logos de terceros:** los agentes de IA van como texto y la ventana es la genérica de la marca; los íconos
  del panel, MCP y API son propios.

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 25-oct-2026 | 44,8 s | Primera versión | borrador |
