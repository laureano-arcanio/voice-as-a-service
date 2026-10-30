# La plataforma (home de la landing)

Video de 47 s para la home de la landing: qué hace Atentina, de forma general y orientada a ventas. El agente queda
fijo al centro y cada línea suma algo alrededor (clientes por sus canales, tu sistema, llamadas salientes, tu equipo,
voces y panel), para que se vea que es una sola plataforma. Cierra con todo en uno, una escena para desarrolladores
(API y MCP) y la marca.

## Pedido

> Una animación como la que hicimos para casos de uso (proyecto `atencion-punta-a-punta`), pero para la landing
> page. Abarcativa y general de los servicios que ofrecemos, bien orientada a ventas, sin detalles técnicos. El
> objetivo es mostrar rápidamente cómo funciona la plataforma y qué se puede hacer.

Requisitos del encargo (30-oct-2026): unos 45 s (máximo 48); al final, una escena para desarrolladores con API y MCP;
1920 × 1080, 30 fps; `paula` y `gonzalo` alternados con el mismo tiempo de voz; subtítulos quemados abajo al centro y
música propia; reutilizar `atencion-punta-a-punta` (copiado, no importado); retratos de `web/public/voces/`; un nodo
central fijo; sin pantallas reales del panel, sin código y sin términos técnicos salvo "API" y "MCP".

## Público, mensaje y formato

- **Público:** dueños y responsables de atención de empresas que entran a la home (no técnico); al final, quien
  desarrolla.
- **Mensaje:** un agente con IA atiende, resuelve, llama y deriva por todos tus canales, en un solo servicio con
  precio en pesos.
- **Formato:** 1920 × 1080, 30 fps, 46,9 s. Composición `landing-plataforma`. Subtítulos quemados (abajo al centro,
  grafía normal) y música de `scripts/musica.py`.
- **Estructura:** cinco escenas. `plataforma` es una sola escena de 25,2 s (l2 a l6): el agente no se mueve y cambian
  el título y lo de alrededor con cada línea (cada momento dura 4 a 6 s), como el diagrama de `atencion-punta-a-punta`.

## Guion (v1)

| Escena | Voz | Qué se dice | Qué se ve |
|---|---|---|---|
| `intro` (0–4,8 s) | l1 paula | Atentina: la atención de tu empresa, con inteligencia artificial. | Fondo blanco, logo, "LA PLATAFORMA", "Agentes con IA que atienden **a tus clientes.**"; Tomás, Lucía y Martina → logo del agente → Valentina y Lucas |
| `plataforma` · atiende | l2 gonzalo | Tus clientes llaman, escriben por WhatsApp o desde tu web, y un agente los atiende, a cualquier hora. | "1 · Atiende" / "Llamadas, WhatsApp y web, **a cualquier hora.**" Agente al centro (logo con el aro, "Tu agente"); entran Tomás (Teléfono), Lucía (WhatsApp) y Martina (Web); onda, "Aa" y onda llegan al agente a la vez y cada uno queda con su tilde; "Las 24 horas" |
| · resuelve | l3 paula | Da turnos, responde consultas, toma pedidos, y lo registra en tu sistema. | "2 · Resuelve" / "Turnos, consultas y pedidos, **en tu sistema.**" Paquetes "{ } Turno", "{ } Consulta", "{ } Pedido" viajan a "Tu sistema" (agenda · gestión) y cada fila se tilda |
| · llama | l4 gonzalo | También llama a tus clientes: confirma turnos, recuerda vencimientos y hace campañas. | "3 · Llama" / "También llama **a tus clientes.**" Tarjeta "Llamadas salientes": Mariana (Confirma su turno), Federico (Recordatorio de vencimiento), Agustina (Campaña de novedades); timbres salientes y tildes; "PLAN Llamadas salientes: Sucursal y Red" |
| · deriva | l5 paula | Y cuando hace falta una persona, le pasa la llamada a alguien de tu equipo. | "4 · Deriva" / "Si hace falta una persona, **pasa con tu equipo.**" "Tu equipo" debajo del agente (Valentina y Lucas); un timbre baja y Valentina "Atendió"; Tomás "Con Valentina", su línea en verde |
| · voces y panel | l6 gonzalo | Elegís entre cuarenta y una voces argentinas, y cada conversación queda en tu panel, con los datos y el resultado. | "5 · Voces y panel" / "41 voces argentinas, **todo en tu panel.**" Lo de alrededor se va; ocho retratos giran alrededor del agente y se elige uno ("con la voz de …"); "41 voces argentinas, 28 femeninas · 13 masculinas"; tarjeta "Conversación con Lucía" (WhatsApp), Datos "Turno: jueves 10 h", Resultado "Resuelta", "datos ilustrativos" |
| `todo` (29,4–36,0 s) | l7 paula | Teléfono, WhatsApp e inteligencia artificial, en un solo servicio, con un precio por mes, en pesos. | "TODO EN UNO" / "Un solo servicio, **un precio por mes en pesos.**" El agente al centro y seis tildes: Número argentino incluido · WhatsApp · Voces argentinas · Derivación a tu equipo · Reportes · Precio en pesos; "PLAN Número, llamadas por teléfono y WhatsApp: desde el plan Mostrador" |
| `desarrolladores` (36,0–41,8 s) | l8 gonzalo | Y si desarrollás, conectalo por API, o manejalo desde tu agente de programación con MCP. | "PARA DESARROLLADORES" / "Conectalo a tu sistema **o manejalo con tu agente.**" Tarjetas "API" (Agentes, llamadas y voces desde tu sistema) y "MCP" (Desde Claude, Cursor o tu agente de programación), unidas al agente; sin código |
| `cierre` (41,8–46,9 s) | l9 paula | Probalo gratis en atentina punto com punto ar. | Fondo blanco, logo, "Agentes con IA que atienden **a tus clientes.**", `atentina.com.ar`, "o llamá al 0800-220-1233 y hablá con nuestro agente" |

En `guion.json` la API va como `ápi` y MCP como `M C P` (tabla de grafías de VIDEOS.md); los subtítulos, con la grafía
normal.

## Reparto de retratos (`web/public/voces/`, copiados a `public/proyectos/landing-plataforma/voces/`)

| Papel | Retrato |
|---|---|
| Clientes que entran (Teléfono, WhatsApp, Web) | `tomas`, `lucia`, `martina` |
| Contactos de las llamadas salientes | `mariana`, `federico`, `agustina` |
| Tu equipo | `valentina` (atiende la derivación), `lucas` |
| Voces que se eligen | `sofia`, `martin`, `carolina`, `diego`, `jimena`, `mateo`, `gabriela`, `camila` |
| El agente | logo (`AgenteLogo`) con el aro |

`paula` y `gonzalo` no aparecen porque son los narradores. Tomás no está entre las voces (ya es un cliente).

## Afirmaciones y fuentes

- **Teléfono, WhatsApp y web:** `landing/src/data/site.ts` (`platform`: "Números argentinos, llamadas entrantes y
  salientes, y WhatsApp para el mismo agente"; Free: "Llamadas web"); [`WHATSAPP.md`](../../../../docs/features/WHATSAPP.md)
  (en producción desde el 1-oct-2026); [`LINK_LLAMADA.md`](../../../../docs/features/LINK_LLAMADA.md).
- **A cualquier hora / las 24 horas:** `site.ts` ("Atiende las 24 horas", vertical municipios). Sin "al instante":
  no se promete un tiempo de respuesta.
- **Turnos, consultas y pedidos registrados en tu sistema:** [`HERRAMIENTAS.md`](../../../../docs/features/HERRAMIENTAS.md)
  (en producción desde el 26-oct-2026; Free 0 herramientas, Mostrador 3, Sucursal 10). El sistema es genérico
  ("agenda · gestión").
- **Llama: confirma turnos, recuerda vencimientos y hace campañas:** [`CAMPANAS.md`](../../../../docs/features/CAMPANAS.md)
  (voz en producción desde el 19-oct-2026; hoy en Sucursal y Red según `site.ts`: "Campañas de llamadas y de
  WhatsApp"). Por eso el aviso de plan en la escena.
- **Pasa la llamada a tu equipo:** [`EQUIPO_TELEFONIA.md`](../../../../docs/features/EQUIPO_TELEFONIA.md) (en
  producción desde el 23-oct-2026, probada con llamadas reales); Mostrador deriva a 1 persona, Sucursal a 2 (`site.ts`).
- **41 voces argentinas, 28 femeninas y 13 masculinas:** `site.ts` y `tts/finetune/voces.tsv`.
- **Cada conversación en tu panel, con los datos y el resultado:** `site.ts` (`costsIncluded`: "Panel con la
  transcripción y los datos de cada conversación"); [`REPORTES.md`](../../../../docs/features/REPORTES.md).
- **Número argentino incluido, un solo servicio, precio por mes en pesos:** `site.ts` (`costsIncluded`, FAQ "Los
  planes con telefonía incluyen el número argentino… Es un solo servicio con un precio por mes en pesos"). El Free no
  tiene telefonía: por eso el aviso "desde el plan Mostrador".
- **Reportes:** `REPORTES.md` (en producción); Free con reportes básicos, los pagos completos (`site.ts`).
- **API:** [`ARQUITECTURA.md`](../../../../docs/ARQUITECTURA.md) (`/api/v1`: agentes, llamadas) y voces por API
  (`site.ts`, página de voces: "GET /voices"; [`API_INFERENCIA.md`](../../../../docs/API_INFERENCIA.md)).
- **MCP desde Claude, Cursor o tu agente de programación:** [`MCP.md`](../../../../docs/features/MCP.md) (en
  producción desde el 24-oct-2026, todos los planes; "Claude.ai, ChatGPT, Claude Code y Cursor sí"). Los nombres van
  escritos, sin logos.
- **Probalo gratis:** plan Free, "Empezar gratis" (`site.ts`, `freePlan`: 20 minutos, llamadas web, API).
- **Contacto:** `atentina.com.ar` y 0800-220-1233, que atiende el agente comercial (`site.ts`, `contactPhone`).

**Ilustrativo:** los nombres de clientes, contactos y equipo, el turno del jueves a las 10, los horarios y precios,
el pedido de 2 cajas, los motivos de las llamadas salientes, la conversación con Lucía y la hora 10:42 (marcado
"datos ilustrativos" en la tarjeta).

## Decisiones

- **Voces:** `paula` y `gonzalo` alternadas línea por línea (pedido: mismo tiempo): 19,6 s y 19,7 s. `velocidad` 1,08
  y `ganancia_db` −1,5, como `atencion-punta-a-punta`.
- **Grafías:** `ápi` y `M C P` (tabla de VIDEOS.md); el resto con la ortografía normal.
- **Ajustes al borrador del guion:** l2 sin "al instante" (no hay una cifra que lo respalde en este video); l4 suma "a
  tus clientes" y l5 "a alguien de" para emparejar los tiempos; l6 vuelve a llevar "con los datos y el resultado"; l8
  "conectalo por API" (sin "a tu sistema", que queda en pantalla) para que entre en 48 s.
- **Una sola escena para la plataforma**, como el diagrama de `atencion-punta-a-punta`: los nodos no parpadean entre
  fundidos y se ve que todo sale del mismo agente.

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 30-oct-2026 | 46,9 s | Primera versión | borrador |
