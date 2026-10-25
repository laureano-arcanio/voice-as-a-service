# MCP en Claude Code (tutorial técnico)

Cómo conectar el servidor MCP de Atentina a Claude Code y qué se puede hacer con él: instalación, OAuth y una
demo con herramientas reales (cuenta, crear un agente, probarlo por texto, equipo y derivación).

## Pedido

> Video profesional en español, horizontal 16:9 1080p, para YouTube y para la documentación de Atentina.
> Objetivo: explicar de forma práctica y paso a paso cómo integrar el servidor MCP de Atentina con Claude Code y
> demostrar sus capacidades. Duración 1–2 min, idealmente 90 s. Público: desarrolladores y usuarios técnicos;
> tono profesional, claro, directo y dinámico.
>
> Estructura:
> 1. Intro (10 s): qué es MCP (Model Context Protocol) y cómo permite administrar Atentina desde Claude Code con
>    lenguaje natural.
> 2. Capacidades (10–15 s): los principales grupos de herramientas según la documentación (cuenta, agentes,
>    llamadas, WhatsApp, contactos, campañas, equipos y derivaciones, etc.).
> 3. Instalación en Claude Code (15–20 s): terminal ejecutando
>    `claude mcp add --transport http atentina https://app.atentina.com.ar/mcp`, luego `/mcp`, seleccionar
>    atentina y completar la autenticación (OAuth: login del panel y consentimiento).
> 4. Demo práctica (35–45 s): Claude Code consulta la cuenta y las herramientas disponibles; crea rápido un agente
>    de atención al cliente, lo configura y lo prueba; conversación de prueba donde Claude Code le manda preguntas
>    al agente y recibe respuestas y datos recopilados; brevemente cómo se configura un equipo y un área de
>    derivación. La creación/configuración de recursos, máximo 15 s con cortes ágiles.
> 5. Cierre / TL;DR (10 s): con una sola integración Claude Code puede consultar, crear, configurar, probar y
>    administrar recursos de Atentina en lenguaje natural. Mostrar el link a la documentación:
>    https://atentina.com.ar/desarrolladores/docs/mcp
>
> Producción: estética moderna, limpia y técnica, con la marca de Atentina. Simulaciones fieles de terminal y
> Claude Code (comandos, llamadas a herramientas MCP con su nombre real y respuestas concretas). Zooms,
> resaltados y transiciones discretas. Narración en español argentino neutro, natural y profesional. Subtítulos
> breves y precisos. Sin intro comercial larga ni animaciones decorativas. Debe sentirse como una demo técnica
> real, no publicidad.

## Público, mensaje y formato

- **Público:** desarrolladores y usuarios técnicos (YouTube y `/desarrolladores/docs/mcp`).
- **Publicado (25-oct-2026):** https://www.youtube.com/watch?v=uROA76sZ-Mc, embebido en `/desarrolladores/docs/mcp` (Conectar tu agente → Claude Code).
- **Mensaje:** con una sola integración, Claude Code consulta, crea, configura, prueba y administra Atentina en
  lenguaje natural.
- **Formato:** 1920 × 1080, 30 fps, 91,6 s. Una voz (`paula`), música propia y subtítulos quemados.

## Guion

| Escena | s | Voz | Qué se dice | Qué se ve |
|---|---|---|---|---|
| `intro` | 10,8 | m1 | M C P es el protocolo que conecta un agente de IA con otras plataformas. Con el servidor de Atentina, administrás tu cuenta desde Claude Code, en lenguaje natural. | Fondo oscuro: logo, "SERVIDOR MCP · CLAUDE CODE", "Administrá Atentina desde Claude Code, **en lenguaje natural.**" Diagrama Claude Code ↔ MCP (`app.atentina.com.ar/mcp`) ↔ Atentina con paquetes `{ }` de ida y vuelta. |
| `grupos` | 11,6 | m2 | Son ochenta y siete herramientas en ocho grupos: la cuenta y el plan, agentes, llamadas, links para llamar, WhatsApp, contactos, campañas, y el equipo con sus derivaciones. | "87 herramientas en ocho grupos, **según tu plan.**" Ocho tarjetas con la cantidad y tres herramientas reales de cada grupo; las que dependen del plan dicen "según el plan". Nota: `get_plan_tools` y `feature_not_in_plan`. |
| `instalar` | 7,4 | m3 | Se instala con un solo comando, que agrega el servidor con su dirección. | Terminal: se escribe `claude mcp add --transport http atentina https://app.atentina.com.ar/mcp` (zoom), su salida, `claude mcp list` → "Needs authentication". Tarjetas: Streamable HTTP, URL, OAuth 2.1 o API key `mcp`. |
| `autenticar` | 9,8 | m4 | Después, dentro de Claude Code, abrí el menú M C P, elegí Atentina y autenticá. Entrás con tu usuario del panel y permitís el acceso. | Claude Code: `/mcp` → "Manage MCP servers" → atentina → "Authenticate". Navegador: login del panel ("Ingresá a tu cuenta") y consentimiento ("Conectar Claude Code", lo que va a poder hacer, "Permitir acceso"). Terminal: "Authentication successful. Connected to atentina." |
| `cuenta` | 9,0 | m5 | Probemos. Le preguntamos qué incluye el plan: Claude mira la cuenta, las herramientas disponibles y el consumo del mes. | Pedido "¿Qué incluye mi plan y qué herramientas tengo disponibles?" → `whoami` y `get_plan_tools` (resaltado y zoom) → respuesta: plan Sucursal, 87 habilitadas, 312 de 1.200 minutos. |
| `crear` | 9,9 | m6 | Ahora, un agente de atención al cliente. Parte de la plantilla, completa la base de conocimiento, valida la definición y lo crea. | Marca ACELERADO. Pedido → `list_agent_templates` → `get_agent_template(template_id: "asistente")` → `validate_agent_definition` (`valid: true`) → `create_agent` (versión 1, voz sofia). |
| `probar` | 9,8 | m7 | Y lo prueba por texto, como si fuera un cliente. Recibe la respuesta del agente y los datos que tomó, sin llamar a nadie ni gastar minutos. | `test_agent_start` (apertura) → `test_agent_turn` "¿Hacen envíos a Quilmes en el día?" (respuesta y `fields.consulta`) → `test_agent_turn` "No, con eso me alcanza" (`resuelta: true`, `status: "completed"`, resaltado y zoom). |
| `equipo` | 9,8 | m8 | Para derivar a una persona, suma a alguien al equipo y crea un área de ventas, con su horario. El agente transfiere ahí cuando hace falta. | Marca ACELERADO. `create_team_member` (Laura Gómez) → `create_handoff_area` (Ventas, `schedule_text` "de lunes a viernes de 09:00 a 18:00", `fallback: take_message`). |
| `cierre` | 14,1 | m9 | En resumen: con una sola integración, Claude Code consulta, crea, configura, prueba y administra Atentina, en lenguaje natural. La guía completa está en la documentación. | Fondo oscuro: "TL;DR", "Una sola integración, **en lenguaje natural.**", los cinco verbos, `https://atentina.com.ar/desarrolladores/docs/mcp`, el comando y el logo. |

Las escenas de demo llevan los pasos arriba a la derecha (1 Cuenta, 2 Crear, 3 Probar, 4 Equipo). Los
subtítulos son la locución en tramos de una línea, con "MCP" y las cifras escritas.

## Afirmaciones y fuentes

- **URL, transporte, auth, grupos y "87 herramientas":** [`docs/MCP_HERRAMIENTAS.md`](../../../../docs/MCP_HERRAMIENTAS.md)
  y `landing/src/data/mcp-tools.json` (90 herramientas de cliente; sin `?toolsets=` van todas menos las 3 de
  `inference` = 87, en 8 grupos: account 8, agents 19, calls 12, call_links 5, whatsapp 6, contacts 11,
  campaigns 14, team 12). [`docs/MCP_PLAN.md`](../../../../docs/MCP_PLAN.md), secciones 1 y 13.
- **Comando y salida de `claude mcp add` / `claude mcp list`:** el comando sale de
  `landing/src/pages/desarrolladores/docs/mcp.astro`; la salida se capturó con Claude Code 2.1.310 en un HOME de
  prueba (`scratch/videos/mcp-cc/`), sin tocar la configuración del usuario. Las rutas `/home/dev/...` son
  ilustrativas.
- **`/mcp` → atentina → Authenticate:** el paso de la landing ("/mcp → atentina → Autenticar"). Los textos del
  menú ("Manage MCP servers", "Atentina MCP Server", "Authenticate", "Authentication successful. Connected to
  atentina.") son una **recreación aproximada** de Claude Code, no una captura.
- **Login y consentimiento:** recreación de `web/src/features/auth/LoginPage.tsx` y
  `web/src/features/oauth/OAuthConsentPage.tsx` (títulos, lista `CAN_DO`, "Permitir acceso"). Flujo OAuth 2.1 en
  MCP_PLAN, fase 3 (emisor `app.atentina.com.ar`, `/oauth/consent`).
- **Herramientas y argumentos:** nombres de `app/mcp/catalog.py`; formas de respuesta de `app/api/schemas.py`
  (`MeOut`, `TemplateOut`, `ValidationOut`, `AgentOut`, `ConversationStartOut`, `TurnOut` con
  `state.fields`/`next_objective`/`status`, `TeamMemberOut`, `HandoffAreaOut` con `schedule_text`) y de
  `app/mcp/server.py` (`_plan_tools`: `plan`, `free`, `tools.available/unavailable/needs_oauth/needs_api_key`,
  `usage`). `schedule_text` con el formato de `services/handoff.describe_schedule`.
- **Plantilla `asistente`** (Sofía, voz `sofia`, campos `consulta`, `resuelta`, `nombre`, `contacto`; termina
  con `resuelta: true`): `app/agents/templates/asistente.json`.
- **"Sin llamar a nadie ni gastar minutos":** descripción de `test_agent_start` en el catálogo.
- **Plan Sucursal con todas las funciones y 1.200 minutos entrantes:** tabla `tiers` (consulta de lectura del
  25-oct-2026) y "Funciones del plan" de MCP_HERRAMIENTAS.

**Ilustrativo:** la empresa "Ferretería Ejemplo", el email, los IDs, el consumo (312 minutos), los textos del
agente y de los pedidos, Laura Gómez y su teléfono (`+5491155551234`, el ejemplo del catálogo), el área Ventas y
su horario. La sesión de Claude Code es una simulación: no se creó nada en la plataforma.

## Decisiones

- **Terminal con la ventana de la marca, no la de Claude Code:** se reproduce el formato de texto de la sesión
  (prompt `>`, `● atentina - <tool> (MCP)(args)`, `⎿` y "… +N lines (ctrl+o to expand)"), pero sin el logo ni
  los colores de Claude Code (VIDEOS.md: nada de interfaces de terceros imitadas).
- **Voz única `paula`**; "M C P" con espacios (escrito `MCP`, el STT oyó "MP" y "MTF"); "Claude Code" escrito
  normal (el STT oye "Cloud Code"). Candidatas en `scratch/videos/candidatas/mcp/` y `mcp2/`.
- **Nombres de herramientas solo en pantalla**, no en la locución (el TTS los diría mal).
- **"ACELERADO"** en crear y equipo: los resultados llegan más rápido que en tiempo real, y se avisa.
- **Subtítulos quemados** (los pidió el pedido). Si se sube a YouTube con subtítulos propios, se pueden sacar.

## Versiones

| Versión | Estado | Qué cambió |
|---|---|---|
| v1 | borrador | Primera versión: 91,6 s, paula, demo con `whoami`, `get_plan_tools`, crear, probar y equipo. |
