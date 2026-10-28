# BAIC Center / Grupo Signature: el análisis en video, con el formato del PDF

- **Pedido (22-oct-2026, Laureano, textual):** "Similar al video que hicimos para isaias goldman, haremos uno igual pero
  con la informacion de BAIC. Cambiamos el enfasis un poco en lo que falla, sino mas bien areas a mejorar. Analiza el
  documento de BAIC luego implementa el video y el PDF como se hizo en Isaias."
- **Reglas (heredadas de [`goldman-analisis`](../goldman-analisis/README.md) v3, por el coordinador):** ~60 s (margen
  hasta ~65), solo narrador `lucas` a 1×, ortografía normal, 2 s de espera antes de la voz en la intro, el agente es el
  logo de Atentina (sin robot), sin logo ni marca de BAIC (el nombre escrito), respiro entre las líneas de la lista,
  cierre "¿Agendamos una reunión personalmente?", material de venta (no dice qué está construido), panel rotulado
  "EJEMPLO CON DATOS ILUSTRATIVOS".
- **Énfasis:** áreas a mejorar y oportunidades, no fallas. Tarjetas azules con su "Oportunidad", como en el PDF. Sin
  citar fallas del sitio (botones de turno y test drive, error 500 de usados) ni a la competencia por nombre. Dos
  reseñas, sin nombres, junto a lo positivo.
- **Corrección del usuario (22-oct-2026, por el coordinador):** BAIC Center **no ofrece plan de ahorro**: fuera todo lo
  del plan y las 84 cuotas. En su lugar, la financiación verificada: Bancor, Banco Nación, Santander y Galicia, y
  crédito propio de la concesionaria (Edgardo en Punto a Punto, jun-2026). Sin leasing.
- **Pedido del usuario (22-oct-2026, textual):** "cambia areas a mejorar por 'Donde podriamos mejorar con Atentina' pdf y
  video." Retoque del borrador v1 (no se había entregado): rótulo de la escena, índice de la intro y a4a.
- **Contexto:** prospecto BAIC Center / Grupo Signature (Córdoba; BAIC, Arcfox, Mitsubishi y Foton). Es el PDF
  [`baicenter-propuesta`](../../../documentos/proyectos/baicenter-propuesta/README.md) en ~65 s: misma estructura, textos,
  cifras y estética. Base: [`comercial/demos/baicenter.md`](../../../../comercial/demos/baicenter.md).
- **Público:** Edgardo Fernández Favaron (presidente de Signature SA) y su equipo. Lo manda Atentina después de la
  reunión del 20-oct-2026, con el PDF.
- **Mensaje:** ya hicieron lo difícil y su lema es "el cliente primero"; la oportunidad es que eso valga también en el
  primer minuto de cada consulta, y que quede medido.
- **Formato:** 1920 × 1080, 30 fps, 65,3 s (65,25). Composición `baicenter-analisis` (`src/Video.tsx`). Solo narrador; el
  agente es `AgenteLogo`.

## Guion (v1)

Locución de `lucas` a 1×, ortografía normal; única grafía: `Báic` por BAIC (escrito "BAIC", el TTS dijo "Bic", "Big"
o "Vice" en la frase; con "Báic", 4 de 4 tomas el STT oye "Bike", que es como se pronuncia). Las áreas a mejorar van en
cuatro líneas (a4a a a4d) con ~0,4–0,5 s de respiro entre cada una (`GAP` 0,2 s + el silencio de cada toma; era 0,3
antes de alargar a4a).

| Escena | Tiempo | Locución | Qué se ve |
|---|---|---|---|
| `intro` | 0–5,5 s | a1 (a los 2 s) "El cliente primero, también en el primer minuto." | Oscura (portada del PDF): logo, "PROPUESTA · BAIC CENTER / GRUPO SIGNATURE · OCTUBRE 2026", "El cliente primero, **también en el primer minuto.**", "Un asesor de guardia 24/7 en sus WhatsApp y su línea" e índice de 4 secciones (la 2, "Dónde podríamos mejorar con Atentina") |
| `bien` | 4,9–11,7 | a2 "En BAIC Center ya hicieron lo difícil. Nueve años, cuatro marcas, y flotas como la de EPEC." | "LO QUE YA HACEN BIEN · En BAIC Center ya hicieron **lo difícil.**" Tarjetas verdes: 9 años (grupo de 2017), 4 marcas (BAIC, Arcfox, Mitsubishi, Foton), 3.300 m² (Av. Colón 800 + Sucursal Norte 2.500), 7 años de garantía y flotas como EPEC |
| `cita` | 11,7–16,1 | a3 "Y lo resume el lema de la casa: el cliente primero." | "El cliente **primero.**" palabra por palabra; "El lema de la casa. Y se ve:" con tres checks: Edgardo contesta en persona las reseñas, trajo el primer Prius y el primer eléctrico homologado, ya atienden por WhatsApp desde sus cuatro sitios |
| `areas` | 16,1–36,45 | a4a "Dónde podríamos mejorar con Atentina. Dos WhatsApp y un fijo, para todo el grupo." · a4b "Ciento nueve horas por semana, el showroom cerrado." · a4c "Cuatro bancos y crédito propio: muchas preguntas antes de venir." · a4d "Y con dos concesionarios en Córdoba, la primera respuesta decide." | "DÓNDE PODRÍAMOS MEJORAR CON ATENTINA · Oportunidades para **vender más con el mismo equipo.**" Cuatro tarjetas azules, cada una con su frase y su "Oportunidad:": CANALES (temas → WhatsApp 1, WhatsApp 2, fijo), HORARIO (semana lu–vi 9–20 y sáb 9–13, contador 109 hs de 168), FINANCIACIÓN (preguntas de ejemplo y Bancor, Banco Nación, Santander, Galicia, crédito propio), MERCADO (el mismo cliente → dos "Concesionario BAIC"; "1ª respuesta" con "la primera respuesta decide") |
| `clientes` | 36,45–43,85 | a5 "La mayoría de las reseñas son buenas. Las que piden algo más, piden una respuesta rápida, y un próximo paso." | "LO QUE PIDEN SUS CLIENTES · No piden otro auto: **una respuesta rápida y un próximo paso.**" Primero lo bueno en verde (4,0 con estrellas, compradores de X35, X55 y BJ30, Edgardo contesta: "sirve para mejorar nuestros procesos de atención"); las dos reseñas del PDF se resaltan con "respuesta rápida" y "próximo paso"; "Lo que tienen en común" en azul |
| `propuesta` | 43,85–54,85 | a6a "Un asesor de guardia, en sus mismos números. Responde en segundos, califica, llama en menos de un minuto, agenda el test drive, y le pasa la ficha al vendedor." | "LA PROPUESTA · Un asesor de guardia, **en sus mismos números.**" Sus clientes → WhatsApp 1, WhatsApp 2, fijo → logo de Atentina ("Asesor de guardia · 24/7") → su equipo (BAIC y Arcfox, Mitsubishi, Foton y flotas, Posventa y taller). Cinco pasos que se encienden con la voz; llamada de vuelta punteada al cliente; "Test drive · sábado 10 h"; la ficha viaja a BAIC y Arcfox; "FICHA DE EJEMPLO: Caliente · BJ30 híbrida · financiación bancaria · permuta Gol 2015, 120.000 km · test drive sábado 10 h" |
| `panel` | 54,85–61,65 | a6b "Lo que no se mide, no se mejora. En el panel ven cada consulta, cuánto tardó, y quién la tomó." | "MEJORA CONTINUA, CON NÚMEROS · Lo que no se mide no se mejora. **El panel lo mide cada día.**" Maqueta "EJEMPLO CON DATOS ILUSTRATIVOS · UNA SEMANA": 540, 5 s, 41 %, 48 s, 63; por marca, por tipo (0 km, Financiación, Posventa, Permuta, Repuestos, Flotas) y por vendedor; con "cuánto tardó" se marcan 5 s, 48 s y "La tomó en"; con "quién la tomó", la fila BAIC 2 |
| `cierre` | 61,65–65,25 | a7 "¿Agendamos una reunión personalmente?" | Oscura: la pregunta; abajo, chico, el logo y atentina.com.ar · 0800-220-1233 |

## Afirmaciones y de dónde salen

Del PDF `baicenter-propuesta` v1 y de `baicenter.md` (leídos el 20 y 22-oct-2026), salvo la financiación:
- **9 años de BAIC Center, grupo de 2017:** base, parte 1. **4 marcas:** parte 2.1. **3.300 m² (800 + 2.500):** parte 2.2.
  **Garantía BAIC de 7 años o 100.000 km:** parte 2.4. **EPEC:** parte 2.5.
- **"El cliente primero", contesta las reseñas en persona, primer Prius (vendió los 4 primeros del país en 2010, en
  Toyota) y primer eléctrico homologado (BAIC EU5), WhatsApp en los cuatro sitios:** partes 0, 1 y 2.2.
- **Dos WhatsApp y un fijo para todo:** parte 2.2. **109 de 168 horas cerrado:** horario de BAIC, Arcfox y MitsuCenter
  (lu a vie 9–20, sáb 9–13) = 59 h abiertas.
- **Financiación: Bancor, Banco Nación, Santander y Galicia, y crédito propio:** verificada por el usuario (Edgardo en
  Punto a Punto, jun-2026; base, parte 2.3). Las preguntas de la tarjeta son ejemplos. **No hay plan de ahorro.**
- **Dos concesionarios BAIC en Córdoba:** parte 4 (el otro no se nombra).
- **Reseñas:** 4,0 con 77 (Google Maps); las dos citas, textuales y sin nombres, de la parte 5 (D1 y D3), las mismas del PDF.
- **"sirve para mejorar nuestros procesos de atención":** respuesta de Edgardo a una reseña (parte 1).
- **Ilustrativo:** el test drive del sábado y la ficha (ejemplo de la parte 7.1, con "financiación bancaria" en lugar del
  plan); todos los números del panel (los del PDF, página 4; "Plan de ahorro 132" pasó a "Financiación 132"), rotulados.
- **Contacto:** `landing/src/data/site.ts`.
- **No construido hoy (el video no lo dice, a propósito; base, parte 7.4):** llamada automática a cada consulta nueva en
  menos de un minuto, agenda real de test drives y turnos, ficha al WhatsApp del vendedor y las métricas del panel por
  marca, tipo, horario y vendedor. Conectar sus WhatsApp y su fijo tiene condiciones (coexistencia, Embedded Signup,
  desvío del fijo a Anura).

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 22-oct-2026 | 65,3 s | Primera versión (sin plan de ahorro: financiación con cuatro bancos y crédito propio); retoque: "Dónde podríamos mejorar con Atentina" en lugar de "Áreas a mejorar" | borrador |
