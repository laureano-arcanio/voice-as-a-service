# Isaías Goldman SA: propuesta en video

- **Pedido (21-oct-2026, Laureano, textual):** "Una introducción al problema que vimos. Y luego la propuesta concreta
  que le damos. Simple, elegante y con target a este cliente. 40 segundos máximo."
- **Contexto:** Isaías Goldman SA (Córdoba): aires acondicionados y climatización, venta a público, instaladores y
  empresas, instalación, service y cursos. El usuario habló por teléfono con el dueño, Isaías Goldman, que pidió la
  oferta. Base de conocimiento: [`comercial/demos/isaiasgoldman.md`](../../../../comercial/demos/isaiasgoldman.md)
  (partes 0, 2.2, 5 y 7).
- **Público:** Isaías Goldman (dueño) y sus hijos (dirección comercial). Lo manda Atentina después de la charla.
- **Mensaje:** en temporada, la consulta que no se contesta en minutos se va; un agente atiende 24/7 el 0800, el
  WhatsApp y el chat de la web, clasifica, responde lo general y deriva a su equipo, y todo queda medido en un panel.
  Piloto desde noviembre.
- **Formato:** 1920 × 1080, 30 fps, 36,9 s (v3). Composición `goldman` (`src/Video.tsx`). Solo narrador; el agente es el logo de
  Atentina (sin mascota desde v2) y hay dos bustos genéricos (vendedor, soporte). Sin su logo ni su marca: el video es de
  Atentina; el nombre de la empresa va escrito.
- **Tono:** respetuoso; el problema se cuenta como algo de la temporada, sin citar reseñas ni nombres. Es material de
  venta: todo se presenta como la oferta, sin decir qué está construido (eso va en "A revisar").

## Guion (v3)

Locución a 1,1× (`"velocidad": 1.1` en `guion.json`, time-stretch sin cambiar el tono).

| Escena | Tiempo | Locución | Qué se ve |
|---|---|---|---|
| `intro` | 0–6,4 s | g1 (desde 2,0 s) "En Isaías Goldman, en temporada de aires, las consultas no paran." | Oscura: logo, "PARA ISAÍAS GOLDMAN SA · CÓRDOBA", "En temporada de aires, **las consultas no paran.**", chips Llamadas, WhatsApp, Consultar precio, Instalaciones, Service, Cursos |
| `problema` | 5,8–14,1 | g2 "Actualmente, un solo número y el local cerrado no alcanzan. La consulta que no se contesta en minutos, se va con la competencia." | "EL PROBLEMA · Un solo número y el local cerrado **ya no alcanzan.**" Un solo número (6 consultas sin atender o con el local cerrado), Horario del local, "Sin respuesta en minutos" hasta 18 min y "Se fue con la competencia". Pie: "Lo dicen sus propios clientes: las quejas son de atención, no de producto." |
| `propuesta` | 14,1–23,4 | g3 "Nuestro agente atiende las veinticuatro horas el cero ochocientos, el WhatsApp y el chat de la web. Clasifica, responde lo general, y deriva a su equipo." | "LA PROPUESTA · El especialista de guardia, **en los tres canales.**" Tres canales → logo de Atentina ("Especialista de guardia · 24/7") → clasifica → "Responde lo general" y "Deriva a su equipo" |
| `panel` | 23,4–31,9 | g4 "Y todo queda en un panel: cada canal, cada tipo de consulta, tiempos de respuesta, fuera de horario y derivaciones por vendedor." | "EL CENTRO DE LA PROPUESTA: VER LA ATENCIÓN · Hoy se mide en reseñas. **Con el panel, cada día.**" Panel con los números ilustrativos del PDF; cada bloque se resalta cuando se nombra |
| `cierre` | 31,9–36,9 | g5 "¿Les parece que hagamos un piloto antes de que inicie la temporada?" | Oscura: logo, "PROPUESTA PARA ISAÍAS GOLDMAN SA · PILOTO DE 30 DÍAS DESDE NOVIEMBRE", "¿Les parece un piloto **antes de que inicie la temporada?**", chips de canales y panel, "Coordinemos el piloto", atentina.com.ar · 0800-220-1233 |

La tabla va con la ortografía normal; en `guion.json`, "Clasifíca" (grafía pedida por el usuario). Guiones
anteriores: `versiones/v1/` y `versiones/v2/` (NOTAS y `fuente/`).

Locución en [`guion.json`](guion.json), solo narrador `lucas`. "Isaías Goldman" se dice (el STT lo transcribe bien
en todas las tomas).

## Afirmaciones y de dónde salen

- **Rubro, Córdoba, un solo número para teléfono y WhatsApp, horario (lu a vie 8:30–13 y 14:30–18:30):**
  `isaiasgoldman.md`, 2.2 (horario solo publicado en Google Maps).
- **"La consulta que no se contesta en minutos se va a otro lado":** `isaiasgoldman.md`, 7.2 (argumento nuestro).
- **"Las quejas son de atención, no de producto":** `isaiasgoldman.md`, 0 y 5 (reseñas de Google, sin citar a nadie).
- **Propuesta (tres canales, triage, derivación, panel con métricas por canal, tipo, tiempos, fuera de horario y
  derivaciones por vendedor; piloto desde noviembre):** `isaiasgoldman.md`, 7.1, 7.5 y 7.6. Sin precios.
- **Contacto:** `landing/src/data/site.ts` (0800-220-1233, atentina.com.ar).
- **Alineado con el PDF** [`goldman-propuesta`](../../../documentos/proyectos/goldman-propuesta/README.md) v1: título
  del cierre (el del PDF), "el especialista de guardia" y "Hoy se mide en reseñas. Con el panel, cada día." (página 4).
- **Ilustrativo:** las consultas de la escena del problema (horas, textos), el reloj de 18 min, y todos los números
  del panel, que son los del ejemplo del PDF (812 consultas, 4 s, 37 % con el local cerrado, 61 % resueltas por el
  agente, reparto por canal y tipo, derivaciones por persona); el panel lo dice ("Datos ilustrativos"). La pantalla del panel es una maqueta de lo
  que verían, no la del dashboard actual.
- **No construido hoy (7.4 del documento; el video no lo dice, a propósito):** transferencia de la llamada a un
  vendedor, relay al WhatsApp de un vendedor o de soporte, chat en la web con el contexto de la página, y en el panel
  las métricas por tipo de consulta y por canal (con web), fuera de horario y derivaciones por persona. El 0800/0810
  para Goldman hay que darlo de alta con Anura. Mover su número a la Cloud API tiene costo para ellos (deja de andar
  en la app del celular).

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 21-oct-2026 | 38,4 s | Primera versión | cerrada |
| [v2](versiones/v2/NOTAS.md) | 21-oct-2026 | 39,5 s | Logo en lugar de la mascota; grafías `áires` y `clasífica`; intro "En Isaías Goldman"; problema "un solo número y el local cerrado no alcanzan"; cierre "antes del pico de consultas" | cerrada |
| [v3](versiones/v3/NOTAS.md) | 21-oct-2026 | 36,9 s | Ortografía normal salvo `Clasifíca`; "se va con la competencia"; 2 s antes de la voz en la intro; cierre en pregunta; locución a 1,1× | borrador |
