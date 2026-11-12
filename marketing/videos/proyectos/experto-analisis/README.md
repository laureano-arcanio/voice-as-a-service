# Experto Construcción Inteligente: la propuesta en video, con el formato del PDF

- **Pedido (11-nov-2026, el usuario, por el coordinador, textual):** "crea una propuesta en PDF y en video de cómo
  Atentina podría integrarse en sus operaciones." Es el PDF en video, con la introducción, qué hacen bien y dónde
  podríamos mejorar con Atentina. Corto, ~60 segundos (hasta ~65).
- **Reglas del pedido:** paula a 1× y gonzalo en algunas líneas; ortografía normal; pausas con puntuación; "En
  Experto..." para nombrarla; el agente es el logo de Atentina (sin robot); sin logo ni marca de Experto; material de
  venta, sin decir qué está construido; no prometer fotos por WhatsApp ni llamadas simultáneas; sin precios.
- **Contexto:** prospecto frío (sin contacto), Córdoba, construcción en seco, 4 locales. Es el PDF
  [`experto-propuesta`](../../../documentos/proyectos/experto-propuesta/) v1 en 58 s: misma estructura, textos,
  cifras y estética (tarjetas verdes, "Hoy" en naranja y "Con Atentina" en azul, diagrama, maqueta del panel, pie de
  página). Base: [`comercial/demos/experto.md`](../../../../comercial/demos/experto.md). Plantilla:
  [`goldman-analisis`](../goldman-analisis/README.md) v3 y [`baicenter-analisis`](../baicenter-analisis/README.md).
- **Público:** Federico, Carlos e Ignacio Dadone, los dueños. Va con el PDF, para pedir una reunión.
- **Mensaje:** el valor de Experto está en sus asesores; la propuesta les saca lo repetido y les lleva cada consulta
  lista, y los dueños ven quién tomó cada cotización y cuánto tardó.
- **Formato:** 1920 × 1080, 30 fps, 58,3 s. Composición `experto-analisis` (`src/Video.tsx`). Intro y cierre en blanco
  (VIDEOS.md, desde el 30-oct-2026; el pedido decía "oscura" como en goldman v3, que es anterior a la regla).

## Guion (v2)

Locución de `paula` a 1× y `gonzalo` en dos líneas (la reseña de un cliente y el panel), ortografía normal, sin grafías
forzadas; "En Experto, ya..." con coma (sin ella el STT oyó "En expertos"). Dónde mejorar va en cuatro líneas (a4a a
a4d) con ~0,7 s de respiro (`GAP` 0,4 s + el silencio de cada toma).

| Escena | Tiempo | Locución | Qué se ve |
|---|---|---|---|
| `intro` | 0–6,0 s | a1 (a los 2 s, paula) "Cada consulta atendida en el momento, y lista para su asesor." | Blanca (portada del PDF): logo oscuro, "PROPUESTA · EXPERTO CONSTRUCCIÓN INTELIGENTE · NOVIEMBRE 2026", "Atención 24 horas por WhatsApp, teléfono y web, **con todo a la vista.**", subtítulo e índice de 4 secciones |
| `bien` | 5,4–13,8 | a2 (paula) "En Experto, ya hicieron lo difícil. Veintidós años, cuatro locales, y un asesoramiento que sus clientes recomiendan." | "LO QUE YA HACEN BIEN · En Experto ya hicieron **lo difícil.**" Tarjetas verdes con la voz: 22 años (2004, Punilla), 4 locales (5.300 m²), 752 reseñas (4,3 a 4,5, estrellas), 19 marcas · 331 productos (distribuidor Knauf) |
| `cita` | 13,8–19,8 | a3 (gonzalo) "Lo dicen sus clientes: gran asesoramiento, para quienes justamente no somos expertos." | "LO QUE DICEN SUS CLIENTES": cinco estrellas y la reseña palabra por palabra, "Gran asesoramiento" en el acento (sin el "!" del original); "Un cliente, en una reseña de 5 estrellas en Google Maps" y "En Carlos Paz, cuatro de las cinco reseñas de 5 estrellas que muestra Google nombran a la misma vendedora." (v1 tenía la cita de los dueños: `versiones/v1/fuente/`) |
| `mejorar` | 19,8–35,7 | a4a "Dónde podríamos mejorar. Hoy atienden cuarenta y cinco de las ciento sesenta y ocho horas de la semana." · a4b "Muchos canales, y todo termina en un asesor." · a4c "Cada cotización se arma a mano." · a4d "Y los reclamos van por mail, y esperan a que alguien los retome." (paula) | "DÓNDE PODRÍAMOS MEJORAR CON ATENTINA · Lo que hoy pasa por un asesor, **puede llegarle listo.**" Cuatro tarjetas "HOY" (borde naranja), cada una con su frase y su franja "CON ATENTINA": semana con 45 hs abiertas → "Las 168 horas, atendidas"; 8 canales → "Un asesor, a mano" → "Clasifica y deriva solo"; fichas "Agregar a cotización" y 331 → "La cotización llega completa"; reclamo → ventas@ "espera que alguien lo retome" → "Cada reclamo con dueño y fecha" |
| `propuesta` | 35,7–48,3 | a5 (paula) "Proponemos un agente que atiende su WhatsApp, el cero ochocientos y la web, a toda hora. Responde las preguntas frecuentes, pasa los reclamos a posventa, y cada cotización, completa, al asesor de su sucursal." | "LA SOLUCIÓN PROPUESTA · Un agente con IA, **en todos sus canales.**" → "Resuelve lo general y pasa cada consulta **a su área.**" WhatsApp, 0800 y teléfonos, Su web → logo de Atentina ("Atentina · 24 horas"); tipos que entran con la voz: Preguntas frecuentes ("la responde el agente"), Reclamo (paquete a Posventa), Cotización en el acento; "Su equipo": Ventas · cotizaciones (el asesor de cada sucursal: Punilla, Carlos Paz, Zona Sur, Rivadavia) se agranda y le llegan tres consultas; Posventa · reclamos; Logística · retiros y envíos. "Resuelve lo general; lo demás lo pasa con el resumen escrito." |
| `panel` | 48,3–54,3 | a6 (gonzalo) "Y en el panel, ven quién tomó cada cotización, y cuánto tardó." | "EL PANEL · Ven cada cotización: **quién la tomó y cuánto tardó.**" Maqueta "EJEMPLO CON DATOS ILUSTRATIVOS · UNA SEMANA": 1.180 consultas, 5 s, 236 cotizaciones completas; tabla "Cotizaciones por asesor" (recibió, la tomó en, sin tomar) con Asesor Rivadavia en naranja |
| `cierre` | 54,3–58,3 | a7 (paula) "¿Agendamos una reunión personalmente?" | Blanco: solo la pregunta; abajo, chico, el logo y atentina.com.ar · 0800-220-1233 · hola@atentina.com.ar |

## Afirmaciones y de dónde salen

Todo sale del PDF `experto-propuesta` v1 y de `comercial/demos/experto.md` (leídos el 11-nov-2026; fuentes: sitio,
Google Maps, Infonegocios):
- **22 años, maderera en Santa María de Punilla en 2004:** constitución 31-oct-2004 (indicadores.ar); `experto.md`, 1.
- **4 locales y centro de distribución de 5.300 m²:** sitio; `experto.md`, 1.
- **752 reseñas, 4,3 a 4,5:** las cuatro fichas de Google Maps; `experto.md`, 1.
- **19 marcas, 331 productos, distribuidor Knauf:** sitio (catálogo); `experto.md`, 1. Knauf va escrito, sin logo.
- **Reseña "Gran asesoramiento para quienes justamente no somos expertos!":** reseña de 5 estrellas de la ficha de Carlos Paz, textual y sin nombre (`experto.md`, D; PDF, página 2). Cuatro de las cinco reseñas de 5 estrellas que muestra esa ficha nombran a la misma vendedora (ídem).
- **45 de 168 horas:** lunes a viernes de 8 a 13 y de 14 a 18 en los cuatro locales (sitio y Maps).
- **Canales:** WhatsApp central, 4 teléfonos de sucursal con WhatsApp, 0800, mail y formulario (`experto.md`, 1).
  Son 8 puntos de contacto; el PDF dice "7 canales". El video dice "Muchos canales" y muestra los 8 (ver "A revisar").
- **331 productos con "Agregar a cotización", sin precio:** modo catálogo del sitio.
- **Reclamos por mail a ventas con pedido, motivo y fotos:** PDF, página 2.
- **Propuesta (canales, tipos de consulta, áreas, resumen escrito):** PDF, página 3. "Logística" resume "Logística y
  administración: retiros, pagos y envíos".
- **Ilustrativo:** los números del panel (los del ejemplo del PDF, página 4: 1.180, 5 s, 236 y la tabla de
  cotizaciones por asesor), marcado en la barra y en el pie. La maqueta no es el dashboard actual. Las fichas de
  producto son genéricas (no copian su sitio).
- **Contacto:** `landing/src/data/site.ts`.
- **No se dice a propósito:** fotos por WhatsApp (el agente no las ve: `docs/features/WHATSAPP.md`), llamadas
  simultáneas (sin CAP vigente), precios, ni qué está construido. Ver "A revisar" en las notas de cada versión.

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 11-nov-2026 | 58,3 s | Primera versión | cerrada |
| [v2](versiones/v2/NOTAS.md) | 11-nov-2026 | 58,3 s | La cita de los dueños (quintuplicar la capacidad) se cambia por una reseña de 5 estrellas, en la voz de gonzalo | borrador |
