# Zennon BI: la propuesta de alianza en video, con el formato del PDF

- **Pedido (22-oct-2026, agente principal por Laureano, textual):** "Hacé un video nuevo (proyecto zennonbi-analisis, v1)
  para Zennon BI siguiendo el formato y contenido del PDF ya hecho:
  marketing/documentos/proyectos/zennonbi-propuesta/versiones/v1/documento.html (leelo completo: es la fuente de textos,
  cifras y tono) y docs/mercado/demos/zennonbi.md. [...] Pedido del usuario, textual: 'Investiga la empresa zennonbi,
  identifica posibles alianzas o integraciones a sus productos. Arma un pdf y un video diseñado para ellos, utiliza 2
  voces como hicimos en axiom.'" Con escenas de ~60–75 s: intro oscura (2 s antes de la voz), lo que ya hacen bien, la
  cita de Cristian, dónde encaja Atentina (una tarjeta por línea destacada, dichas por lucas con ~0,7 s de respiro), la
  integración por dentro (Dynamics/Dataverse → Power Automate → API → agente → canales, entrante y saliente, Power BI), el
  modelo de alianza con el panel "EJEMPLO CON DATOS ILUSTRATIVOS", puesta en marcha y cierre "¿Agendamos una demo
  técnica?".
- **Reglas del pedido:** narradora `paula` a 1× y `lucas` como voz secundaria en algunas líneas, como en
  axiomait-analisis; ortografía normal (grafías solo si una palabra sale mal); pausas con puntuación; "En Zennon..." para
  nombrarla; el agente es el logo de Atentina; sin logo ni marca de Zennon ni de Microsoft (los nombres escritos sí);
  material de venta, sin decir qué está construido; sin precios nuestros; sin nombrar MCP.
- **Contexto:** Zennon S.A.S. ("Zennon BI") es partner de Microsoft Dynamics 365 / Power Platform / Power BI; CEO,
  Cristian Ventura. Llamada de Laureano el 19-oct; reunión la semana del 26-oct-2026 (fecha a confirmar). Lead #228 del
  CRM. Es el PDF [`zennonbi-propuesta`](../../../documentos/proyectos/zennonbi-propuesta/README.md) v1 en ~76 s. Base:
  [`docs/mercado/demos/zennonbi.md`](../../../../docs/mercado/demos/zennonbi.md).
- **Público:** Cristian y su equipo (técnico y comercial). Trato de "ustedes" implícito; "Zennon" en tercera persona,
  como el PDF.
- **Mensaje:** Atentina es la línea de voz argentina (y el WhatsApp) de los proyectos Dynamics que Zennon implementa,
  por API vía Power Automate, como un módulo de sus KickStart; el cliente sigue siendo de Zennon.
- **Formato:** 1920 × 1080, 30 fps, 75,6 s. Composición `zennonbi-analisis` (`src/Video.tsx`). Los largos de las
  escenas salen de `vo/duraciones.json` (`src/timeline.ts`) y los momentos de cada elemento, de la posición de la
  palabra en la línea (`en(id, fragmento)`). Estructura y componentes copiados de `axiomait-analisis` v1; el tablero,
  de `baicenter-analisis`.

## Guion (v1)

Locución de `paula` a 1× y `lucas` en las cuatro líneas de producto (b1 a b4, un bloque seguido, como en
axiomait-analisis). Ortografía normal; única grafía, la de la tabla de VIDEOS.md: `ápi` por API. Respiro entre las
líneas de lucas ~0,7 s (`GAP` 0,38 s + el silencio de cada toma).

| Escena | Tiempo | Locución | Qué se ve |
|---|---|---|---|
| `intro` | 0–6,5 s | a1 (paula, a los 2 s) "La línea de voz argentina de cada proyecto Dynamics que implementan." | Oscura (portada del PDF): logo, "PROPUESTA DE ALIANZA · ZENNON BI · OCTUBRE 2026", "La línea de voz argentina **de cada proyecto Dynamics 365.**", "Voz con IA para sus proyectos de Dynamics 365 y Power Platform" y "Atentina, en cuatro datos": 41 voces, 0800 · 0810, 4 en 1, 1 API |
| `bien` | 5,9–17,8 | a2 (paula) "En Zennon implementan Dynamics desde dos mil dieciocho, con treinta y dos clientes que lo muestran." · a3 "Con la voz pasa lo mismo: el agente se arma con el conocimiento de cada cliente." | "LO QUE YA HACEN BIEN · Desde 2018 con Dynamics 365, **y clientes que lo muestran.**" Cuatro tarjetas de la hoja 1 (2018, 32, +11.000, 12); la cita de Cristian sobre FEDPAS 360 y la banda "Con la voz, lo mismo: ... la integración es el oficio de Zennon." |
| `lineas` | 17,8–36,9 | b1 (lucas) "Dynamics Sales: el agente llama al lead apenas entra." · b2 "Customer Service: el número del cliente atiende a toda hora." · b3 "Field Service: las visitas, confirmadas el día anterior." · b4 "Customer Insights: un paso de llamada o de WhatsApp en el recorrido." | "DÓNDE ENCAJA ATENTINA · Voz en cada línea que venden, **sin montar telefonía.**" Cuatro tarjetas de la hoja 2 (Sales/CRM KickStart y Customer Service destacadas, como en el PDF; Field Service; Customer Insights · Journeys), cada una con su "Oportunidad:"; abajo, "Y TAMBIÉN": Contact Center, Power Pages, Copilot Studio, Power BI, Para partners |
| `integracion` | 36,9–51,0 | a4 (paula) "Por dentro: Power Automate pide la llamada por ápi, el agente habla con el cliente, y el resultado vuelve a Dataverse." · a5 "Si el cliente llama, atiende el mismo agente y deja el caso. Y Power BI lo mide." | "LA INTEGRACIÓN POR DENTRO · Dynamics decide, Atentina habla **y el resultado vuelve a Dataverse.**" Diagrama de la hoja 3: Dynamics 365 (Sales, Customer Service, Field Service) y Dataverse (gris) → Power Automate con el conector (gris, "lo arma Zennon") → API /api/v1 → el agente (logo) → línea argentina, WhatsApp, link en el navegador → sus clientes; pasos 1 a 4; la vuelta punteada a Dataverse (que se enciende); la entrante desde "Sus clientes"; la banda de Power BI |
| `alianza` | 51,0–64,0 | a6 (paula) "La alianza: un módulo de voz en cada KickStart. Zennon lo diseña y lo conecta, y el cliente sigue siendo de Zennon." · a7 "Atentina pone el número, la voz y el soporte, y cada llamada queda medida." | "EL MODELO DE ALIANZA · Un módulo de voz para cada KickStart. **El cliente sigue siendo de Zennon.**" Los tres KickStart y el "Módulo de voz Atentina" (rotulado "Un ejemplo de cómo sumarlo"); qué pone Zennon y qué pone Atentina; el tablero "CLIENTE DE ZENNON · EJEMPLO CON DATOS ILUSTRATIVOS · UN MES" (cinco KPI, por resultado y salientes por campaña) |
| `marcha` | 64,0–71,8 | a8 (paula) "Primero, una demo técnica con un Dynamics de prueba. Después, un piloto de treinta días con un caso real." | "CÓMO SE PONE EN MARCHA · Primero la demo técnica. **Después, 30 días de piloto.**" Las tres tarjetas de la hoja 5 (acceso para probar, demo técnica destacada, piloto de 30 días) y "Después del piloto" (primer cliente, conector y tablero, Copilot Studio, acuerdo de aliado) |
| `cierre` | 71,8–75,6 | a9 (paula) "¿Agendamos una demo técnica?" | Oscura: la pregunta; abajo, chico, el logo y atentina.com.ar · 0800-220-1233 · hola@atentina.com.ar |

## Afirmaciones y de dónde salen

Todo del PDF `zennonbi-propuesta` v1 (leído el 22-oct-2026) y de `zennonbi.md`:
- **Datos de Zennon** (2018, 32 clientes que muestran con sus rubros, +11.000 productores y organizadores y 12 unidades
  de negocio de Federación Patronal en FEDPAS 360 sobre Dynamics 365 Sales, "como socios de Microsoft", CRM KickStart
  Esencial / Crecimiento / Expansión, Sales Qualification Agent): hojas 1 y 2 del PDF; fuentes en el README del PDF
  (zennonbi.com, LinkedIn, CESSI, leídos el 22-oct-2026). "Con clientes que lo muestran" = los 32 de `/clientes/`.
- **Cita de Cristian:** textual del caso Federación Patronal del blog de Zennon, la misma del PDF.
- **Las cuatro líneas y sus oportunidades:** hoja 2 (zennonbi.md 7.1), recortadas. "Tercerizadas" abrevia "operaciones
  tercerizadas" del PDF.
- **Atentina:** 41 voces (28 de mujer y 13 de hombre, `tts/finetune/voces.tsv`); 0800, 0810 y regional, entrantes y
  salientes (`landing/src/data/site.ts`); canales, API y panel: hoja 3.
- **Integración:** el diagrama y los recorridos de la hoja 3; "/api/v1" es la base real de la API.
- **Modelo de alianza:** hoja 4; los KickStart con su contenido son un ejemplo (rotulado como en el PDF).
- **Ilustrativo (rotulado en la barra del tablero y en el pie):** todo el tablero (KPI, resultados y campañas), con las
  cifras del PDF.
- **Contacto:** `landing/src/data/site.ts`.
- **No construido o sin usar hoy (el video no lo dice, a propósito; zennonbi.md 7.4 y "A validar" del PDF):** conector de
  Power Automate (lo arma Zennon; falta una especificación pública de la API); webhook por llamada suelta o entrante (solo
  existe el de campañas; hoy está el resumen por email); llamadas salientes y campañas de voz (cero salientes en la base,
  ningún tier con `voice`); "llama al lead apenas entra"; identificar a quien llama contra Dataverse; Customer Insights
  con voz; Copilot Studio; cuentas por cliente para un aliado; capacidad con Gemma sin medir.

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 22-oct-2026 | 75,6 s | Primera versión (paula y lucas) | borrador |
