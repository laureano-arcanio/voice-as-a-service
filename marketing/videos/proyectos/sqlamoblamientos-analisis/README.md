# SQL Amoblamientos: el análisis en video, con el formato del PDF

- **Pedido (22-oct-2026, Laureano, por el coordinador, textual):** "el PDF en video, con la introducción, qué hacen bien y
  dónde podríamos mejorar con Atentina. Corto, 60 segundos."
- **Reglas (del coordinador, heredadas de [`goldman-analisis`](../goldman-analisis/README.md) v3 y
  [`baicenter-analisis`](../baicenter-analisis/README.md) v1):** ~60 s (hasta ~65), solo narrador `lucas` a 1×,
  ortografía normal (grafías solo si una palabra sale mal), 2 s de espera antes de la voz en la intro, "En SQL
  Amoblamientos..." para nombrarla y probar cómo dice "SQL" (ellos dicen "ese-cu-ele"), el agente es el logo de Atentina
  (sin robot), sin logo ni marca de SQL (el nombre escrito), una tarjeta por frase con ~0,7 s de respiro, los asesores
  elogiados por nombre y que el agente no los reemplaza, la propuesta con canales → logo → tipos de consulta → su equipo
  con énfasis en Ventas (asesores y locales, franquicia de la zona), panel simple rotulado "EJEMPLO CON DATOS
  ILUSTRATIVOS", cierre oscuro "¿Agendamos una reunión personalmente?" con el contacto chico. Material de venta: no dice
  qué está construido. **Sin el texto oculto del sitio** (parte 2.3 de la base) ni la competencia.
- **Contexto:** prospecto SQL Amoblamientos (Córdoba, muebles a medida). Es el PDF
  [`sqlamoblamientos-propuesta`](../../../documentos/proyectos/sqlamoblamientos-propuesta/README.md) v1 en ~65 s: misma
  estructura, textos, cifras y estética. Base: [`docs/mercado/demos/sqlamoblamientos.md`](../../../../docs/mercado/demos/sqlamoblamientos.md).
- **Público:** Pilar Conte (asistente de marketing, primer contacto), Jorge Urizar y sus hijos. Va con el PDF, en frío
  (lead 364 del CRM, sin llamada previa).
- **Mensaje:** el mueble ya está resuelto; la oportunidad está en la espera: que cada consulta tenga respuesta y cada
  cliente sepa cómo va lo suyo, con el asesor de guardia pasándole la consulta lista a su equipo.
- **Formato:** 1920 × 1080, 30 fps, 69,4 s en v5 (= v3; v1: 65,2 s; v2: 64,1 s; v4: 71,0 s); 62,0 s en v6 (prueba con `paula`).
- **v4 (22-oct-2026, el usuario por el coordinador):** narradora `laura` (arf_06136, mujer) en lugar de `lucas`; mismos
  textos, escenas y visuales que v3, con los tiempos ajustados a su locución.
- **v5 (22-oct-2026):** **`laura` descartada por cómo suena (a juicio del usuario)**; vuelve la v3 tal cual (`lucas` a 1×,
  mismos textos, tiempos, animaciones y respiros), con la locución de `v3/fuente/vo/` sin regenerar y sin `ganancia_db`.
- **v6 (22-oct-2026): PRUEBA DE VOZ** con la narradora `paula` (arf_03853, mujer), pedida por el usuario: mismos textos,
  escenas y visuales que v5, toda la locución regenerada, tiempos y animaciones ajustados y −1,7 dB de nivel. La
  versión de referencia sigue siendo la v5 (`lucas`) hasta que el usuario elija.
- **v3 (22-oct-2026, el usuario por el coordinador):** igual al PDF v2 de la propuesta: apertura "cliente y empresa saben lo
  que está pasando", un 0800 o 0810, llamadas con voz (no solo WhatsApp), pedidos y catálogo al día y énfasis en el pase a
  una persona. Hasta ~70 s por la escena de la propuesta. Composición `sqlamoblamientos-analisis` (`src/Video.tsx`). Solo
  narrador; el agente es `AgenteLogo`.

## Guion (v3, igual en v5; en v4, los mismos textos con `laura`)

Locución de `lucas` a 1×, ortografía normal; única grafía: `Ese Cu Ele` por SQL (escrito "SQL", una de dos tomas de
prueba el STT la oyó "Squell"; con "Ese Cu Ele" se fuerzan los nombres de las letras en español, como lo dicen ellos;
pruebas en `scratch/videos/candidatas/sqlamoblamientos/`). Lo que podríamos mejorar va en cuatro líneas (a4a a a4d) con
~0,65 s de respiro entre cada una (`GAP` 0,45 s + el silencio del final de cada toma).

| Escena | Tiempo | Locución | Qué se ve |
|---|---|---|---|
| `intro` | 0–7,6 s | a1 (a los 2 s) "Cada consulta atendida. Su cliente y ustedes, siempre al tanto de lo que pasa." (v3) | Oscura (portada del PDF v2): logo, "PROPUESTA · SQL AMOBLAMIENTOS · OCTUBRE 2026", "Cada consulta atendida. **Su cliente y ustedes, siempre al tanto de lo que pasa.**", "Un asesor de guardia 24/7, al teléfono y en WhatsApp" e índice de 4 secciones |
| `bien` | 7,0–14,1 | a2 "En SQL Amoblamientos ya hicieron lo difícil: veinte locales, en nueve provincias." | "LO QUE YA HACEN MUY BIEN (v2) · En SQL Amoblamientos ya hicieron **lo difícil.**" Tarjetas verdes: Desde 1981, 4.000 m² (San Roque, 10 máquinas, 70 personas), 20 locales (9 provincias, propios y franquicias, showroom de 400 m²), 183 reseñas (4,3, asesores elogiados por su nombre) |
| `cita` | 14,1–19,7 | a3 "En palabras de Jorge Urizar: cumplimos a rajatabla con los tiempos estipulados." | La cita palabra por palabra con la voz, "**tiempos estipulados.**" en el acento; "Jorge Urizar, fundador, en Punto a Punto (noviembre de 2021)"; "Esta propuesta quiere ayudar a que el cliente **vea esa promesa día a día.**" |
| `mejorar` | 19,7–36,45 | a4a "Dónde podríamos mejorar con Atentina. Mientras espera, el cliente pregunta cómo va lo suyo." · a4b "La posventa entra como un mensaje más." · a4c "Un solo WhatsApp, para consultas de todo el país." · a4d "Y la atención, en horario reducido." (v2; en v1, "Y una cocina se piensa de noche, con la casa cerrada.") | "DÓNDE PODRÍAMOS MEJORAR CON ATENTINA · El mueble ya está resuelto. **La oportunidad está en la espera.**" Cuatro tarjetas azules con su "Oportunidad:" (las seis del PDF condensadas): PRESUPUESTOS Y FABRICACIÓN (Presupuesto → Seña → Fabricación · 90 a 100 días → Instalación, y "¿cómo va lo mío?"; v3: "responderle al instante, con el dato de su pedido, en qué etapa está"), POSVENTA (cuatro mensajes de ejemplo en el mismo WhatsApp; se resalta "Faltan colocar los zócalos"), CANALES Y RED (sitio, Instagram, Linktree y showroom → un solo WhatsApp; 20 puntos de venta; v3: "un número para todo el país que pase cada consulta al local de la zona"), HORARIO REDUCIDO (v2: "Atención en horario reducido: 44 de las 168 horas"; semana con lu–vi 9–13 y 14–18 y sáb 9–13; contador a 44 hs abierto de 168; oportunidad: "responder también fuera de horario y dejar la visita o la medición agendada") |
| `clientes` | 36,45–44,45 | a5 "Sus clientes elogian a sus asesores, por su nombre. El asesor de guardia no los reemplaza: les pasa cada consulta lista." | "LO QUE VALORAN SUS CLIENTES · Lo que más se elogia: **sus asesores, por su nombre.**" Martín, Fernando (casa central), Micaela (Villa Carlos Paz), Arq. Inés (Río Cuarto), en verde con "por su nombre"; la reseña de Martín; a la derecha, el logo ("Asesor de guardia") le pasa la ficha a "Su asesor": "No los reemplaza: **les pasa cada consulta lista.**" |
| `propuesta` | 44,45–59,95 | a6a "Atiende con voz, en un cero ochocientos, su línea y su WhatsApp. Conoce sus productos, y sabe cómo va cada pedido." · a6c (0,4 s después) "Y cuando hace falta, pasa a una persona: al asesor, o a la franquicia de la zona, con la charla y la ficha." | "LA PROPUESTA · Un asesor de guardia, **y una persona cuando hace falta.**" Canales: 0800 / 0810 (nuevo, para todo el país), Línea de la casa (casa central), WhatsApp (mensajes, audios y llamadas), Su sitio web (llamar desde la página) → logo ("Asesor de guardia · 24/7", con "Atiende con voz" y onda) ← "SUS DATOS · DE SU SISTEMA O PLANILLA": Catálogo y Pedidos, que se encienden con la voz. Con a6c, "Una persona, a un paso" (su equipo: Asesores y locales y Franquicia de la zona, marcados VENTAS y encendidos con la voz; Posventa, Administración, Producción) se agranda en el acento, el enlace se engrosa ("pasa a una persona con la charla y la ficha"), viaja una llamada y después "charla + ficha"; abajo, "Resuelve lo que puede; lo demás lo atiende su equipo, **sin que el cliente repita nada.**" |
| `panel` | 59,95–65,75 | a6b "Y en el panel, ven qué pasó a una persona, quién la tomó, y cuánto tardó." | "EL PANEL · Qué pasó a una persona: **quién la tomó y cuánto tardó.**" Maqueta "EJEMPLO CON DATOS ILUSTRATIVOS · UNA SEMANA": 310 consultas (llamadas, WhatsApp y web), 189 · 121 (resueltas solas · pasadas a una persona, se marca con la voz), por canal (WhatsApp chat 151, 0800 / 0810 72, Línea 41, Sitio web 28, Llamada WA 18) y la tabla "PASADAS A UNA PERSONA: QUIÉN Y CUÁNTO TARDÓ" (pases, la tomó en, presupuestos +7 días; en naranja Central 2, Carlos Paz y Franquicias) |
| `cierre` | 65,75–69,35 | a7 "¿Agendamos una reunión personalmente?" | Oscura: la pregunta; abajo, chico, el logo y atentina.com.ar · 0800-220-1233 |

## Afirmaciones y de dónde salen

Del PDF `sqlamoblamientos-propuesta` v1 y de `sqlamoblamientos.md` (fuentes leídas el 22-oct-2026; ver el README del PDF):
- **Desde 1981:** D&F Muebles (2015) y Container (2020). **4.000 m², San Roque, 10 máquinas, 70 personas, showroom de
  400 m²:** InfoNegocios, abr-2025. **20 puntos de venta en 9 provincias:** página de sucursales del sitio.
  **183 reseñas, 4,3:** Google Maps de la casa central.
- **Cita de Jorge Urizar:** Punto a Punto, 17-nov-2021, textual (primera parte de la frase).
- **Fabricación de 90 a 100 días, presupuesto con idas y vueltas:** InfoNegocios, abr-2025. **"¿Cómo va lo mío?" por el
  mismo WhatsApp:** inferencia de la base (partes 5 y 2.2), a confirmar en la reunión.
- **Posventa como un mensaje más:** parte 5, D4. Los cuatro mensajes de la tarjeta son **de ejemplo** ("Faltan colocar
  los zócalos" se inspira en una reseña, sin citarla).
- **Un solo WhatsApp en sitio, Instagram, Linktree y showroom; consultas de todo el país:** partes 2.2 y D5.
- **44 de 168 horas abierto (lu a vie 9–13 y 14–18, sáb 9–13):** horario de casa central en el sitio y Maps. En v2 se
  dice "horario reducido" (pedido del usuario); "una cocina se piensa de noche" (inferencia nuestra, parte 0) salió.
- **Asesores elogiados:** Martín y Fernando (casa central), Micaela (Carlos Paz), Arq. Inés (Río Cuarto). Reseña de
  Martín, textual (casa central, 5★, hace 4 meses al 22-oct-2026).
- **Tipos de consulta y áreas del equipo:** diagrama del PDF, página 3. En v3, los canales (0800 o 0810 nuevo, línea de
  casa central, WhatsApp con mensajes, audios y llamadas, sitio), "Sus datos: pedidos y catálogo" y el pase a una persona
  salen del PDF v2, página 3; el panel v3, de su página 4 (cifras ilustrativas). Sin los seis tipos de consulta en la
  escena de la propuesta (no entraban junto a los datos y el pase).
- **Ilustrativo:** los números del panel (los del PDF, página 4; asesores sin nombres reales) y los mensajes de la
  tarjeta de posventa; rotulado en el panel y en los pies.
- **Contacto:** `landing/src/data/site.ts`.
- **No construido hoy (el video no lo dice, a propósito):** clasificación y derivación con ficha al asesor o la
  franquicia de la zona, estado del pedido y avisos al cliente, reclamos con número de caso, panel por asesor con
  demoras y presupuestos pendientes. Conectar su WhatsApp central y su línea tiene condiciones (coexistencia, Embedded
  Signup, desvío de la línea). En v3 se suman: alta de un 0800 o 0810 para ellos, conexión a su sistema o planilla de
  pedidos y a su catálogo, y el pase de una llamada o un chat en curso a una persona de su equipo con la charla y la ficha.

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 22-oct-2026 | 65,2 s | Primera versión | cerrada |
| [v2](versiones/v2/NOTAS.md) | 22-oct-2026 | 64,1 s | "Lo que ya hacen muy bien"; a4d y la tarjeta de horario, sobre la atención en horario reducido | cerrada |
| [v3](versiones/v3/NOTAS.md) | 22-oct-2026 | 69,4 s | Igual al PDF v2: apertura nueva, 0800 / 0810, llamadas con voz, pedidos y catálogo, pase a una persona y panel con resueltas y pasadas | cerrada |
| [v4](versiones/v4/NOTAS.md) | 22-oct-2026 | 71,0 s | Narradora `laura`; tiempos de escena según su locución y −2,2 dB de nivel (descartada: suena mal, a juicio del usuario) | cerrada |
| [v5](versiones/v5/NOTAS.md) | 22-oct-2026 | 69,4 s | Vuelta a la v3: `lucas`, con su locución, tiempos y animaciones | cerrada |
| [v6](versiones/v6/NOTAS.md) | 22-oct-2026 | 62,0 s | Prueba de voz: narradora `paula`; tiempos según su locución y −1,7 dB de nivel | borrador |
