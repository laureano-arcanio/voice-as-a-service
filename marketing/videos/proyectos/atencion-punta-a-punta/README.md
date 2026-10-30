# Atención de punta a punta (publicitario)

Video publicitario de 60 s como máximo: cómo atiende Atentina de punta a punta. El cliente llama, el agente consulta y
registra en el sistema de la empresa, deriva a una o más personas del equipo, toma el mensaje si nadie atiende y todo
queda registrado. Cierra con lo que se puede hacer y configurar, con tildes.

## Pedido

> Hace un video de estilo marketing que muestre cómo funciona end-to-end el sistema de atención con un agente,
> registrar o obtener información de un cliente y hacer derivación a uno o más operarios de una empresa. Enfócate en
> un perfil de marketing y no técnico. Utiliza los avatars que ya creamos para las voces. Cuando te refieras a las
> personas, incluye principalmente un diagrama donde se ve cómo va interactuando la persona con el agente, las
> herramientas y el operario. Utiliza las dos voces en las mismas proporciones. Finalmente, incluso un resumen tipo
> tildes de lo que se puede hacer y configurar. Haz un video de 60 segundos y no más. Enfócate en un perfil marketing
> publicitario.

Requisitos del encargo (30-oct-2026): 60 s máximo, 16:9 1920 × 1080 (landing, vertical de turnos y YouTube), con
locución, música propia y subtítulos; `paula` y `gonzalo` con el mismo tiempo de voz; los retratos de
`web/public/voces/`; sin pantallas del panel ni términos técnicos.

## Público, mensaje y formato

- **Público:** dueños y responsables de atención de empresas (no técnico), en la landing, la página de turnos y YouTube.
- **Mensaje:** el agente atiende, usa tu sistema y, cuando hace falta, te pasa la llamada a tu equipo; nada se pierde.
- **Formato:** 1920 × 1080, 30 fps, 54,7 s. Composición `atencion-punta-a-punta`. Subtítulos quemados (abajo al
  centro, con la grafía normal) y música de `scripts/musica.py`.
- **Estructura:** cuatro escenas. El diagrama es una sola escena de 34,7 s (d2 a d8): los nodos quedan quietos y
  cambian el título, los paquetes y los estados con cada línea; así se sigue la llamada sin cortes (VIDEOS.md pide
  5 a 13 s por escena: acá cada "momento" del diagrama dura 4 a 6 s).

## Guion (v1)

| Escena | Voz | Qué se dice | Qué se ve |
|---|---|---|---|
| `intro` (4,6 s) | d1 paula | Así funciona Atentina: atiende a tus clientes de punta a punta. | Fondo oscuro, logo, "ATENCIÓN DE PUNTA A PUNTA", "Tu cliente llama, el agente resuelve **y tu equipo suma cuando hace falta.**", Tomás → logo → Valentina y Lucas |
| `diagrama` · atiende | d2 gonzalo | Tomás llama a tu empresa, y el agente lo atiende, a cualquier hora. | "1 · Atiende" / "Tu cliente llama y el agente atiende, **a cualquier hora.**" Tomás (Llamando → En llamada), onda que viaja al agente (logo con el aro, "con la voz de Sofía"); globo "¿Cómo viene mi pedido?" |
| · consulta y registra | d3 paula | Mientras hablan, consulta tu sistema: encuentra su pedido, y registra lo que necesita. | "2 · Consulta y registra" / "Usa tu sistema **durante la llamada.**" Paquetes `{ }` al sistema (agenda · CRM · gestión): Cliente Tomás Ríos y Pedido 4821 (consulta), Suma 10 unidades (registra) |
| · deriva | d4 gonzalo | Tomás pide hablar con Ventas. El agente llama a tu equipo, en el orden y el horario que elegiste. | "3 · Deriva a tu equipo" / "Llama a tu gente, **en tu orden y tu horario.**" El sistema queda como chip; entra "Tu equipo · Ventas" con "Lun a vie, 9 a 18" y Valentina (1) y Lucas (2); globos "¿Me pasás con Ventas?" y "Te paso con Ventas, un momento." |
| · espera | d5 paula | Tomás escucha música. Suena Valentina; si no atiende, suena Lucas. | "Tu cliente espera con música **y suena el siguiente.**" Tomás en Música de espera (notas); Valentina Sonando → No atiende; Lucas Sonando |
| · conecta | d6 gonzalo | A Lucas, el agente le cuenta en pocas palabras de qué se trata, y los conecta. | "Le cuenta de qué se trata **y los conecta.**" Aviso solo a Lucas ("Derivación de Ventas: Tomás quiere sumar 10 unidades. Marcá 1 para atender."), tecla 1; líneas en verde, "Tomás y Lucas, conectados" |
| · si nadie atiende | d7 paula | ¿Y si nadie atiende? El agente vuelve con Tomás y le toma el mensaje. | "SI NADIE ATIENDE" / "El agente vuelve **y toma el mensaje.**" Valentina y Lucas No atiende; globo "No pude comunicarte con Ventas. ¿Te tomo el mensaje?"; Tomás Deja su mensaje |
| · registro | d8 gonzalo | Al final, todo queda registrado en tu panel: la conversación, los datos y el resultado. | "4 · Queda registrado" / "Cada conversación, **de punta a punta.**" El diagrama queda atrás; tarjeta "Conversación con Tomás Ríos" con Conversación, Datos y Resultado (Derivada a Ventas · atendió Lucas, Resuelta) |
| `checklist` (8,7 s) | d9 paula | Teléfono, WhatsApp y web, con voces argentinas. Tu sistema, tu equipo y tus horarios. Lo configurás vos. | "LO QUE HACE · LO QUE CONFIGURÁS" / "Todo esto, **a la medida de tu empresa.**" Diez tildes (ver abajo) y el aviso de plan "Telefonía, WhatsApp, herramientas, equipo y llamadas a la vez, según el plan" |
| `cierre` (6,8 s) | d10 gonzalo | Atentina. Agentes con IA que atienden a tus clientes. Empezá hoy, en atentina punto com punto ar. | Fondo oscuro, logo, "Agentes con IA que atienden **a tus clientes.**", `atentina.com.ar`, "o llamá al 0800-220-1233 y hablá con nuestro agente" |

**Tildes:** Atiende las 24 horas · Por teléfono, WhatsApp y la web · Voces argentinas: elegís la tuya · Consulta y
registra en tu sistema · Deriva a tu equipo, en tu orden y horario · Música de espera y aviso a quien atiende · Si
nadie atiende, toma el mensaje · Varias llamadas a la vez · Transcripción, datos y resultado de cada una · Reportes
de consultas y derivaciones.

## Reparto de avatares (`web/public/voces/`, copiados a `public/proyectos/atencion-punta-a-punta/voces/`)

| Papel | Retrato | Por qué |
|---|---|---|
| Tomás, el cliente que llama | `tomas` | Uno solo, fijo en todo el diagrama |
| El agente | logo (`AgenteLogo`) con el aro, más un chip con `sofia` ("con la voz de Sofía") | El agente es el logo (VIDEOS.md); el chip muestra que el agente habla con una voz que se elige |
| Valentina, Ventas, primera en el orden | `valentina` | Operaria 1: suena y no atiende |
| Lucas, Ventas, segundo en el orden | `lucas` | Operario 2: atiende, recibe el aviso y se conecta |

`paula` y `gonzalo` no aparecen como personajes porque son los narradores (que no se confunda la voz que narra con
alguien del diagrama).

## Afirmaciones y fuentes

- **Atiende a cualquier hora / las 24 horas:** `landing/src/data/site.ts` (vertical municipios: "Atiende las 24
  horas", "24 horas, todos los días").
- **Teléfono, WhatsApp y web:** `site.ts` (`platform`: "Números argentinos, llamadas entrantes y salientes, y
  WhatsApp para el mismo agente"; Free: "Llamadas web"); [`WHATSAPP.md`](../../../../docs/features/WHATSAPP.md).
- **Voces argentinas, elegís la tuya:** `site.ts` (41 voces; `sofia` está en el catálogo). Los retratos son los del
  asistente de primera vez ([`PRIMERA_VEZ.md`](../../../../docs/features/PRIMERA_VEZ.md), hecho el 30-oct-2026 y
  sin desplegar): en el video son solo personajes, no se muestra el asistente.
- **Consulta y registra en tu sistema durante la llamada:** [`HERRAMIENTAS.md`](../../../../docs/features/HERRAMIENTAS.md)
  (en producción desde el 26-oct-2026; Free 0, Mostrador 3, Sucursal 10); `site.ts`, turnos: "Consulta y reserva
  en tu sistema de turnos durante la llamada".
- **Deriva a tu equipo en orden y horario; música de espera solo al cliente; aviso a la persona con un resumen y
  conexión con el 1; si nadie atiende, vuelve y toma el mensaje:** [`EQUIPO_TELEFONIA.md`](../../../../docs/features/EQUIPO_TELEFONIA.md),
  "Derivación (`transfer_call`)", y `landing/src/pages/desarrolladores/docs/api.astro` `#derivaciones`. Los textos
  en pantalla son los default de `DEFAULT_MESSAGES` (`transfer`, `whisper`, `no_answer`), recortados; el resumen
  del aviso es ilustrativo. Tomar el mensaje es regla de la plantilla, no del código (el doc lo dice).
- **Dos personas en un área:** según la landing, Mostrador deriva a 1 persona y Sucursal a 2 (`site.ts`, planes);
  por eso el aviso de plan en la checklist.
- **Varias llamadas a la vez:** `site.ts` (Mostrador 1, Sucursal 3, Red a medida): va con el aviso de plan.
- **Transcripción, datos y resultado de cada conversación:** `site.ts` (`costsIncluded`: "Panel con la
  transcripción y los datos de cada conversación"). El tramo con la persona queda transcripto (EQUIPO_TELEFONIA,
  paso 6; `api.astro`).
- **Reportes de consultas y derivaciones:** [`REPORTES.md`](../../../../docs/features/REPORTES.md) (Resumen en todos;
  transferencias con `advanced_reports`, Mostrador y Sucursal según `site.ts`).
- **Contacto:** `atentina.com.ar` y el 0800-220-1233, que atiende el agente comercial (`site.ts`, `contactPhone`).
- **Sin cifras** de latencia ni de capacidad: "a cualquier hora" y "varias llamadas a la vez" no prometen números.

**Ilustrativo:** Tomás Ríos, el pedido 4821, las 10 unidades, Valentina y Lucas, el área Ventas con "Lun a vie, 9 a
18", la hora y duración de la conversación (10:42, 3:12) y los diálogos (marcado "datos ilustrativos" en la tarjeta
del registro). El sistema de la empresa es genérico ("agenda · CRM · gestión"), sin marcas de terceros.

## Decisiones

- **Voces:** `paula` y `gonzalo` alternadas línea por línea (pedido explícito: partes iguales, aunque VIDEOS.md dice
  que `gonzalo` es secundario). 22,2 s de `paula` y 21,8 s de `gonzalo`. `velocidad` 1,08 (ritmo publicitario) y
  `ganancia_db` −1,5 (como `docs-intro`).
- **Sin grafías forzadas.** d1 decía "Así atiende Atentina…": el STT oyó "atiéndate en Tina" (las dos "a" se
  pegan); se cambió a "Así funciona Atentina: atiende…".
- **El diagrama en una sola escena** para que los nodos no parpadeen entre fundidos.
- **Fuera:** horario del agente (no hay), "al instante" o tiempos de respuesta, cifras de llamadas simultáneas,
  campañas y teléfono del equipo (otro tema).

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 30-oct-2026 | 54,7 s | Primera versión | borrador; [en YouTube](https://youtu.be/k-Fpnre1rd0), público y en /casos-de-uso |
