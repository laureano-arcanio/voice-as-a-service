# Isaías Goldman SA: el análisis en video, con el formato del PDF

- **Pedido (21-oct-2026, Laureano, textual):** "hagamos otro video, similar pero que siga el formato del PDF. Con la
  introducción, qué hacen bien y qué observamos. Corto, 60 segundos."
- **Reglas del usuario para este video (21-oct-2026, por el coordinador):** el agente es el logo de Atentina (sin
  robot); probar grafías de "aire" (en v2 el usuario pidió volver a la ortografía normal en toda la locución: "los acentos están mal en general"); "En Isaías
  Goldman..." más que "Isaías" a secas, con pausas por puntuación; nada de "con la temporada" en el cierre (va "antes
  del pico de consultas"); sin el logo ni la marca de Goldman.
- **Contexto:** prospecto Isaías Goldman SA (Córdoba, climatización). Es el PDF
  [`goldman-propuesta`](../../../documentos/proyectos/goldman-propuesta/README.md) v1 en 60 s: misma estructura, textos,
  cifras y estética (tarjetas de datos con borde verde y naranja, citas, maqueta del panel, pie de página). Base:
  [`docs/mercado/demos/isaiasgoldman.md`](../../../../docs/mercado/demos/isaiasgoldman.md). El video corto de 40 s es
  [`goldman`](../goldman/README.md).
- **Público:** Isaías Goldman y sus hijos Jonatan y Carolina. Lo manda Atentina después de la charla, con el PDF.
- **Mensaje:** ya hicieron lo difícil; lo que falta es que cada consulta tenga respuesta y quede a la vista. Piloto en
  noviembre (en el PDF); el video cierra pidiendo una reunión en persona (v3).
- **Formato:** 1920 × 1080, 30 fps, 64,0 s (v3; el pedido era 60 s, con margen hasta ~65). Composición `goldman-analisis` (`src/Video.tsx`). Solo narrador; el agente
  es `AgenteLogo`. Sin logo ni marca de Goldman: su nombre va escrito.
- **Tono:** fáctico y amable. Lo bueno primero (también en las reseñas); las quejas citadas textuales y sin nombres.
  Material de venta: no dice qué está construido (eso va en "A revisar").

## Guion (v3)

Locución de `lucas` a 1× (sin `"velocidad"` en `guion.json`), con la ortografía normal; única grafía forzada:
`Clasifíca` (pedida por el usuario). Lo observado va en cuatro líneas (a4a a a4d) con un respiro de ~0,7 s entre
cada una. El guion de v2 está en `versiones/v2/NOTAS.md` y `versiones/v2/fuente/`; el de v1, en `versiones/v1/`.

| Escena | Tiempo | Locución | Qué se ve |
|---|---|---|---|
| `intro` | 0–5,5 s | a1 (a los 2 s) "Hagamos que cada cliente tenga una respuesta." | Oscura (portada del PDF): logo de Atentina, "PROPUESTA · ISAÍAS GOLDMAN SA · OCTUBRE 2026", "Que cada consulta tenga respuesta, **y que ustedes las vean todas.**", subtítulo e índice de las 4 secciones |
| `bien` | 4,9–14,7 | a2 "En Isaías Goldman ya hicieron lo difícil. Treinta años, unas cincuenta personas, y empresas como Arcor, Georgalos y Mostaza." | "LO QUE YA HACEN BIEN · En Isaías Goldman ya hicieron **lo difícil.**" Tarjetas verdes: 30 años, 4.500 m² (~50 personas), 1.671 reseñas (4,2), Arcor, Georgalos, Mostaza |
| `cita` | 14,7–20,2 | a3 "En palabras de Isaías Goldman: nos gusta hacer cosas donde podemos responder." | La cita grande palabra por palabra, "responder." en el acento; InfoNegocios (2018) y la frase de Jonatan (2021) |
| `observamos` | 20,2–34,4 | a4a "Esto es lo que vimos. Un solo número para todo." · a4b "Doscientos sesenta y seis productos, ninguno con precio." · a4c "Cerrado, ciento veintiuna horas por semana." · a4d "La temporada ya está por arrancar." | "LO QUE OBSERVAMOS · Lo que ve cualquier cliente: **cómo se llega a ustedes.**" Cada tarjeta naranja entra con su frase: un solo número, 266 sin precio, "Cerrado 121 hs por semana", "La temporada ya está por arrancar" (Nov–Feb) |
| `clientes` | 34,4–42,2 | a5 "Sus clientes los valoran. Lo que piden es que les devuelvan el llamado, un presupuesto a tiempo, y un aviso si el técnico se demora." | "LO QUE DICEN SUS CLIENTES · Lo que se repite: **poder comunicarse.**" Lo bueno en verde y las cinco reseñas; se resaltan el llamado, el presupuesto y la visita técnica |
| `propuesta` | 42,2–53,1 | a6a "Proponemos un especialista de guardia en el cero ochocientos, el WhatsApp y la web. Clasifíca cada consulta y la pasa al área que corresponde, sobre todo a Ventas." | "LA PROPUESTA · Un especialista de guardia, **en los tres canales.**" → "Clasifica cada consulta y la pasa **a su área.**" Canales → logo de Atentina; tipos de consulta (Ventas, Precios, Instalaciones, Posventa, Otros); "Su equipo": Ventas (vendedores, con todo lo hablado), Instalaciones, Service y posventa, Empresas y obras. Con "sobre todo a Ventas", Ventas se agranda en el acento y le llegan tres consultas. "Resuelve lo general; lo demás lo pasa a su equipo con la ficha completa." |
| `panel` | 53,1–59,7 | a6b "Y en el panel, ven todo lo que pasa: quién tomó cada consulta, y cuánto tardó." | "EL PANEL · Ven cada consulta: **quién la tomó y cuánto tardó.**" Maqueta "EJEMPLO CON DATOS ILUSTRATIVOS": 812 consultas, 37 % con el local cerrado, 4 s hasta la primera respuesta; tabla por persona (recibió, la tomó en, sin tomar), con Vendedor 2 y Posventa en naranja |
| `cierre` | 59,7–64,0 | a7 "¿Agendamos una reunión personalmente?" | Oscura: solo "¿Agendamos una reunión **personalmente?**"; abajo, chico, el logo y atentina.com.ar · 0800-220-1233 |

## Afirmaciones y de dónde salen

Todo sale del PDF `goldman-propuesta` v1 y de `isaiasgoldman.md`, leídos el 21-oct-2026:
- **30 años, tres generaciones:** InfoNegocios 2019 (30 años en 2020) y 2021 (Jonatan); `isaiasgoldman.md`, 1.
- **4.500 m² en Bv. Bulnes y Pringles, ~50 personas:** InfoNegocios 2018 y 2021; `isaiasgoldman.md`, 0 y 2.1.
- **1.671 reseñas, 4,2:** ficha de Google Maps; `isaiasgoldman.md`, 0.
- **Arcor, Georgalos, Mostaza:** carrusel de clientes del sitio; `isaiasgoldman.md`, 2.3. Nombres escritos, sin logos.
- **Citas de Isaías (2018) y Jonatan (2021):** InfoNegocios; `isaiasgoldman.md`, 1 y 2.1.
- **Un solo número (351 386 2886) en sitio, Google, Facebook y Linktree:** `isaiasgoldman.md`, 2.2.
- **266 productos sin precio, "Consultar precio" → formulario por email:** sitemap y fichas; `isaiasgoldman.md`, 2.3.
- **Cerrado 121 hs por semana (de 168):** horario de Google Maps (lu a vie 8:30–13 y 14:30–18:30, sáb 8:30–13): 47 h abiertas.
- **Temporada de noviembre a febrero:** PDF, página 1 (`isaiasgoldman.md`, 0).
- **Reseñas citadas:** textuales y sin nombres, las del PDF (página 2); "Excelente atención en el local" y que
  contestan las reseñas, también del PDF.
- **Propuesta (tres canales, deriva a su equipo, panel; piloto de 30 días desde noviembre):** PDF, páginas 3 a 5.
  Tipos de consulta (Ventas, Instalaciones, Productos, Precios, Posventa, Otros) y áreas del equipo (Vendedores,
  Instalaciones, Service y posventa, Empresas y obras): diagrama del PDF, página 3.
- **Ilustrativo:** los números del panel (los del ejemplo del PDF, página 4: 812, 37 %, 4 s y la tabla de derivaciones
  por persona; el panel lo dice: "Ejemplo con datos ilustrativos"). La maqueta del panel no es el dashboard actual. Las fichas de producto son genéricas (no copian su
  sitio). Las barras de Nov a Feb no son datos: solo marcan los meses.
- **Contacto:** `landing/src/data/site.ts`.
- **No construido hoy (el video no lo dice, a propósito):** derivación de la llamada a un vendedor, relay al WhatsApp
  de un vendedor o de soporte, chat en la web, y en el panel las métricas por canal (con web), por tipo, fuera de
  horario y por persona (`isaiasgoldman.md`, 7.4). El 0800/0810 para Goldman hay que darlo de alta con Anura.

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 21-oct-2026 | 58,9 s | Primera versión | cerrada |
| [v2](versiones/v2/NOTAS.md) | 21-oct-2026 | 57,8 s | Locución a 1,1× y sin tildes forzadas; intro con 2 s de espera y "Hagamos que cada cliente tenga una respuesta."; sin "Como dijo" ni "Lo que observamos" en la voz; "Cerrado 121 hs por semana"; a5 sin cortes; cierre con la pregunta del piloto | cerrada |
| [v3](versiones/v3/NOTAS.md) | 21-oct-2026 | 64,0 s | Locución a 1×; respiro entre las observaciones; "La temporada ya está por arrancar."; la propuesta en dos escenas (clasifica y deriva, sobre todo a Ventas; panel simple con quién tomó cada consulta y cuánto tardó); cierre "¿Agendamos una reunión personalmente?"; a2 y a5 más cortos | borrador |
