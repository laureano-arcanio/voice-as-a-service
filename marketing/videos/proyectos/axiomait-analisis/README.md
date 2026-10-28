# Axioma IT Solutions: la propuesta técnica en video, con el formato del PDF

- **Pedido (22-oct-2026, agente principal por Laureano, textual):** "Hacé un video nuevo (proyecto axiomait-analisis, v1)
  para Axioma IT siguiendo el formato y contenido del PDF ya hecho: marketing/documentos/proyectos/axiomait-propuesta/versiones/v1/documento.html
  (leelo completo: es la fuente de textos, cifras y tono) y comercial/demos/axiomait.md. [...] Pedido del usuario:
  'Propuesta de demo para un integrador, más bien técnica y overview del producto. Voces paula y lucas.' Además:
  'Explicá que las voces pueden sonar mejor, dependiendo de la configuración y ajustando la latencia deseada.'"
  Con escenas de ~60–75 s: intro oscura (2 s antes de la voz), lo que ya hacen bien, dónde encaja Atentina (una
  tarjeta por línea, ~0,7 s de respiro), el producto por dentro, el llamador del CRM, voces y naturalidad (escala
  "responde antes ↔ suena más fluida", cierre "natural, pero honesto"), puesta en marcha y cierre "¿Agendamos una demo
  técnica?".
- **Reglas del pedido:** narradora `paula` a 1× y `lucas` como voz secundaria en algunas líneas (en vez de `pablo`),
  ortografía normal (grafías solo si una palabra sale mal: "Odoo", "API", "webhook", "CRM"), pausas con puntuación,
  "En Axioma..." para nombrarla, el agente es el logo de Atentina, sin logo ni marca de Axioma, material de venta (no
  dice qué está construido), sin precios.
- **Contexto:** Axel Díaz, CEO de Axioma IT (software factory, partner de Odoo y de Microsoft), probó la demo de voz de
  la landing el 22-oct-2026 y pidió un agente que llame a leads del CRM en un momento determinado, más voces y que
  suene menos robot; quiere probarlo solo. Es el PDF
  [`axiomait-propuesta`](../../../documentos/proyectos/axiomait-propuesta/README.md) v1 en ~77 s. Base:
  [`comercial/demos/axiomait.md`](../../../../comercial/demos/axiomait.md) (lead #218).
- **Público:** Axel y su equipo técnico: integradores que ya venden Odoo, agentes de IA con n8n y turnos. Trato de
  "ustedes", como el PDF.
- **Mensaje:** sumen voz a lo que ya venden, por API; el llamador del CRM es el primer caso y la naturalidad se
  configura.
- **Formato:** 1920 × 1080, 30 fps, 77,4 s. Composición `axiomait-analisis` (`src/Video.tsx`). Narradora y voz
  secundaria; el agente es `AgenteLogo`. Los largos de las escenas salen de `vo/duraciones.json` (`src/timeline.ts`) y
  los momentos de cada elemento, de la posición de la palabra en la línea (`en(id, fragmento)`).

## Guion (v1)

Locución de `paula` a 1× y `lucas` en las cuatro líneas de Axioma (b1 a b4, un bloque seguido, como `pablo` en
cimepa-analisis v2). Ortografía normal; única grafía, la de la tabla de VIDEOS.md: `ápi` por API. Respiro entre las
líneas de lucas ~0,7 s (`GAP` 0,38 s + el silencio de cada toma).

| Escena | Tiempo | Locución | Qué se ve |
|---|---|---|---|
| `intro` | 0–6,7 s | a1 (paula, a los 2 s) "Sumen voz a lo que ya venden: Odoo, agentes de IA y turnos." | Oscura (portada del PDF): logo, "PROPUESTA TÉCNICA · AXIOMA IT SOLUTIONS · OCTUBRE 2026", el h1 con el remate en acento (se enciende con la voz), "Voz con IA para un integrador, por API" y "Atentina, en cuatro datos": 41 voces, 0,87 s, 4 en 1, 1 API |
| `bien` | 6,1–13,0 | a2 (paula) "En Axioma ya entregaron más de cien proyectos, con clientes que se quedan, y cinco estrellas en sus reseñas." | "LO QUE YA HACEN BIEN · Más de cien proyectos, y clientes **que se quedan.**" Cuatro tarjetas de la hoja 1: +100, Silver, 5,0, ISO 9001, con su fuente |
| `lineas` | 13,0–30,3 | b1 (lucas) "Odoo y CRM: llamar a cada lead a tiempo." · b2 "Agentes de IA: el mismo agente, también por teléfono." · b3 "TodoTurnos: una llamada para confirmar el turno." · b4 "Soporte Odoo: un primer nivel, a toda hora." | "DÓNDE ENCAJA ATENTINA · Voz para cada línea que ya venden, **sin montar telefonía.**" Las cuatro tarjetas de la hoja 2 (Odoo y CRM, Soluciones IA y n8n, TodoTurnos, Soporte Odoo) con su "Oportunidad:", una por línea |
| `producto` | 30,3–41,4 | a4 (paula) "Por dentro: una llamada, un WhatsApp o el navegador llegan al mismo agente, que escucha, decide y habla, en Argentina. Todo queda en el panel y sale por ápi." | "EL PRODUCTO POR DENTRO · Un agente, tres canales y una API. **La inferencia, en Argentina.**" Diagrama de la hoja 3: canales → logo "El agente" (Escucha / Decide / Habla, que se encienden con la voz; "Inferencia propia, en Argentina") → Panel y API /api/v1 → Su sistema (Odoo, n8n, TodoTurnos, otro CRM) |
| `llamador` | 41,4–50,2 | a5 (paula) "Lo que pidieron: el CRM crea la campaña por ápi, con la hora. El agente llama, califica y agenda, y un webhook devuelve el resultado." | "EL CASO PEDIDO · EL LLAMADOR DEL CRM · El CRM decide cuándo, el agente llama **y devuelve el resultado.**" La cita de Axel; Odoo / CRM → API → el logo llama → el lead; el webhook vuelve punteado al CRM; `POST /api/v1/campaigns` y el webhook `contact.finished` (ilustrativos, abreviados) |
| `voces` | 50,2–66,0 | a6 (paula) "Son cuarenta y una voces argentinas, y pueden sonar mejor: depende de la configuración y de la latencia que elijan." · a7 "Con menos espera, responde antes. Con más, suena más fluida." · a8 "Natural, pero honesto: el agente no niega ser una IA." | "VOCES Y NATURALIDAD · 41 voces argentinas, **y una naturalidad que se configura.**" Las nueve voces de la hoja 5 y "+ 32"; "Qué la hace sonar más natural" (cuatro palancas); la escala "Responde antes ↔ Suena más fluida" con la perilla que va a cada lado con la voz y el dato medido (0,87 s, máx. 1,17 s); la banda verde "Natural, pero honesto" |
| `marcha` | 66,0–73,6 | a9 (paula) "Pueden probarlo hoy, sin hablar con nadie. Después, una demo técnica y un piloto de treinta días con sus leads." | "CÓMO SE PONE EN MARCHA · Primero lo prueban solos. **Después, 30 días con sus leads.**" Las tres tarjetas de la hoja 6 y "Después del piloto: revenderlo" (TodoTurnos, Soporte Odoo, Clientes Odoo, Acuerdo de canal) |
| `cierre` | 73,6–77,4 | a10 (paula) "¿Agendamos una demo técnica?" | Oscura: la pregunta; abajo, chico, el logo y atentina.com.ar · 0800-220-1233 |

## Afirmaciones y de dónde salen

Todo del PDF `axiomait-propuesta` v1 (leído el 22-oct-2026) y de `axiomait.md`:
- **Datos de Axioma** (+100 proyectos, Silver, 30 referencias, 97 % de retención, 5,0 en Google con 17 reseñas y en
  Clutch, ISO 9001 por Bureau Veritas, las cuatro líneas, Kit 4.0, 70 % menos ausencias en Sanatorio Santa Rosa,
  Badent, guardia 24/7): hojas 1 y 2 del PDF; axiomait.md partes 0, 2 y 5. "Clientes que se quedan" es el 97 % de
  retención de la ficha de Odoo.
- **Cita de Axel:** textual de la conversación de la demo (axiomait.md, parte 0), la misma del PDF.
- **Atentina:** 41 voces (28 de mujer, 13 de hombre, `tts/finetune/voces.tsv`; los nueve nombres y sus descripciones,
  de la hoja 5); 0,87 s promedio y 1,17 s máximo en 6 turnos: registro de la llamada de Axel del 22-oct-2026, medido
  en el servidor (axiomait.md 7.4); canales, panel y API: hoja 3.
- **API:** `POST /api/v1/campaigns` con `channel`, `agent_id`, `starts_at`, `window_start`, `window_end`,
  `callback_url` y `contacts[].external_id` (`CampaignIn` y `ContactIn` en `app/api/schemas.py`); el webhook
  `contact.finished` con `contact.external_id`, `outcome`, `campos` y `link` (`app/campaigns/callbacks.py`,
  `app/services/campaign_reports.py`). Valores de ejemplo.
- **Ilustrativo (rotulado en el pie):** el lead, la empresa, los ids, la fecha y los datos de los dos JSON.
- **Contacto:** `landing/src/data/site.ts`.
- **No construido o sin usar hoy (el video no lo dice, a propósito; axiomait.md 7.4):** campañas de voz con webhook
  (código y migración aplicados, ningún tier con el canal `voice`, cero campañas y cero llamadas salientes en la base);
  códigos SIP de Anura y contestador sin medir; capacidad con Gemma sin medir; documentación pública de la API (el
  OpenAPI es solo para admin); multi-cliente para un integrador y marca blanca; voz a medida para un cliente (se
  ofrece, requiere reentrenar el checkpoint). La escala de latencia es conceptual: el "margen" es la espera de fin de
  turno del agente (0,4 a 1 s por defecto, PDF hoja 5), no un control expuesto como tal en el panel.

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 22-oct-2026 | 77,4 s | Primera versión (paula y lucas) | borrador |
