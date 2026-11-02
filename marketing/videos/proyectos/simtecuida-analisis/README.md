# SIM Te Cuida: la solución en video, todo en blanco

- **Pedido (2-nov-2026, Laureano, textual):** "con esta información hago un video con el template que venimos usando en
  formato blanco. No utilizamos más el color azul oscuro para los fondos, y que incluya toda la información directamente
  enfocado en la solución que le vamos a dar, con una pequeña introducción de lo que vimos de su empresa y dónde están las
  oportunidades, y luego el diagrama como hemos hecho en otras situaciones, similar a lo que tenemos en la landing page. Unos
  60 segundos de duración máximo."
- **Reglas del encargo (por el coordinador):** fondos blancos o claros en todas las escenas; el azul solo como acento; 60 s
  como tope; intro y oportunidades hasta ~12 s, sin nombrar fallas, competidores ni quejas; emergencias como priorización,
  nunca "detecta todos los casos"; sin piloto, 30 días, SMS, otros idiomas, cifras de redes ni la página `/admin/`; lo "a
  relevar" no se afirma; sin logo ni marca de SIM; material de venta, sin decir qué está construido.
- **Contexto:** SIM Te Cuida, agencia de cuidadoras y acompañantes en sanatorio y domicilio, CABA y GBA (lead entrante, CRM
  #481). Acompaña al PDF [`simtecuida-propuesta`](../../../documentos/proyectos/simtecuida-propuesta/README.md) v2. Base:
  [`comercial/demos/simtecuida.md`](../../../../comercial/demos/simtecuida.md).
- **Público:** los responsables de SIM Te Cuida, todavía sin nombre. En "ustedes".
- **Mensaje:** una línea atendida a toda hora: saber quién llama, y que lo urgente pase primero, por $ 39.000 por mes.
- **Formato:** 1920 × 1080, 30 fps, 59,6 s. Composición `simtecuida-analisis` (`src/Video.tsx`). Estructura de
  [`goldman-analisis`](../goldman-analisis/README.md) v3 y [`baicenter-analisis`](../baicenter-analisis/README.md), copiada
  y sin tocar `src/comun/`. El agente es `AgenteLogo`. Todo en el proyecto: ni `C.ink` ni otro color oscuro como fondo.
- **Diagrama:** la landing no tiene un diagrama fijo. Su lenguaje está en los videos de la home (`landing-plataforma`,
  `atencion-punta-a-punta`: logo con aro de puntos, curvas punteadas, paquetes que viajan, tarjetas blancas, píldora "Las 24
  horas") y en los íconos de `Channels.astro` (baldosas con degradé). De ahí se copió, dentro de `src/diagrama.tsx`.

## Guion (v1)

`paula` a 1× y `gonzalo` en dos líneas a destacar (a4c y a7). Ortografía normal, sin grafías forzadas; "0800" se dice "cero
ochocientos". `ganancia_db` −1 (sin ajuste, −14,5 LUFS).

| Escena | Tiempo | Locución | Qué se ve |
|---|---|---|---|
| `intro` | 0–6,2 s | a1 "En SIM Te Cuida vimos atención a toda hora, en CABA y GBA, y asignación en dos a cuatro horas." | Blanco, logo oscuro, "PROPUESTA · SIM TE CUIDA · NOVIEMBRE 2026", "En SIM Te Cuida, **esto es lo que vimos.**" Tarjetas: 24 h (los 365 días), CABA y GBA, 26 (sanatorios, clínicas y hospitales), 2 a 4 h |
| `oportunidades` | 5,6–12,2 | a2 "Todo entra por un mismo canal. Reconocer al cliente, y separar lo urgente, ayudaría a cumplir esa promesa." | "DÓNDE PODRÍAMOS MEJORAR CON ATENTINA · La oportunidad está en **el primer contacto.**" Canales, Clientes y Prioridad, cada una con su "Oportunidad:"; "Más fácil cumplir lo que prometen: **asignar en 2 a 4 horas.**"; pie: son lecturas nuestras |
| `diagrama` | 12,2–20,9 | a3 "Un agente con IA atiende a toda hora su línea, el cero ochocientos y el WhatsApp. Lo que necesita una persona pasa a su equipo, y todo queda en el panel." | "LA SOLUCIÓN · Un agente en cada canal, **que sabe a quién derivar.**" Línea telefónica, 0800 (opcional, borde punteado) y WhatsApp → logo de Atentina con aro ("Su agente", "Las 24 horas", "Asistente virtual · no da indicaciones médicas") → "Su equipo" (persona de turno; si no atiende, la siguiente; y la siguiente), y agente y equipo → "El panel" |
| `recorrido` | 20,9–35,55 | a4a "Reconoce a quien llama por su teléfono. Si no aparece, pide nombre, DNI u otro dato de contacto." · a4b "Si detecta una posible emergencia, le da prioridad. Y deriva a su equipo, por rotación." · a4c (gonzalo) "Prioriza la atención: no es un servicio de emergencias." | "EL RECORRIDO DE CADA CONSULTA · Saber quién llama, **y que lo urgente pase primero.**" Cuatro pasos que se encienden con la voz (número de ejemplo → "Ya es cliente"; Nombre, DNI, Otro dato; la posible emergencia sube a primera en la cola; la rotación pasa a la siguiente). Banda: "Es priorización de la atención, **no un servicio de emergencias.**", no da indicaciones médicas, puede no reconocer todos los casos |
| `ficha` | 35,55–45,05 | a5a "Sus clientes se cargan en la misma plataforma, con teléfono, suscripción y cuidados." · a5b "Antes de atender, su equipo oye una minuta. Quien llama, no la oye." | "FICHA DE CLIENTES Y MINUTA · Sus clientes en la plataforma, **y su equipo sabe quién es.**" Tabla y minuta, cada una rotulada "EJEMPLO CON DATOS INVENTADOS"; banda "Quien llama **no oye la ficha.**"; pie: datos de salud, sensibles |
| `panel` | 45,05–49,85 | a6 "En el panel ven quién tomó cada consulta, y cuánto tardó." | "PARA QUIEN DIRIGE · Toda la atención a la vista: **quién la tomó y cuánto tardó.**" Maqueta "EJEMPLO CON DATOS ILUSTRATIVOS · UNA SEMANA": 186, 78, 5 y la tabla por persona |
| `presupuesto` | 49,85–56,25 | a7 (gonzalo) "Plan Mostrador, más mantenimiento del CRM: treinta y nueve mil pesos por mes." | "Presupuesto: **$ 39.000 por mes.**" La tabla del PDF, lo que incluye y la aclaración de capacidad |
| `cierre` | 56,25–59,65 | a8 "¿Agendamos una reunión personalmente?" | Blanco: la pregunta; abajo, chico, logo oscuro y atentina.com.ar · 0800-220-1233 · hola@atentina.com.ar |

## Afirmaciones y de dónde salen

- **24 h los 365 días, CABA y GBA con zonas hasta La Plata, 26 (conteo nuestro), 2 a 4 h:** PDF v2, página 1 (sitio de SIM,
  leído el 2-nov-2026); `simtecuida.md`, parte 0.
- **Oportunidades:** hoja "Dónde podríamos mejorar con Atentina" del PDF v1, página 2 (Canales, Clientes, Prioridad), resumida.
  Son lecturas nuestras: no hay quejas de clientes (`simtecuida.md`, parte 5), y el pie lo dice.
- **Solución, canales, recorrido, emergencias:** PDF v2, páginas 2 y 3.
- **Ficha y minuta:** PDF v2, página 3. **Datos inventados** (nombres, teléfonos, minuta), rotulados. Las columnas DNI y "otros
  campos" del PDF pasan a una línea de texto, por espacio.
- **Panel:** PDF v2, página 4. **Números ilustrativos**, rotulados: 186 consultas; 108 resueltas y 78 derivadas; 5 posibles
  emergencias, una persona en 52 s; tabla por persona (recibió suma 78 y emergencias suma 5). No se usa "41 % fuera de
  horario": es una agencia de 24 h.
- **Presupuesto:** PDF v2, página 5, con el mismo texto (lo que incluye, capacidad y minutos del 0800). Sin promesa de llamadas
  simultáneas ni de personas en rotación con un número.
- **Contacto:** `landing/src/data/site.ts`.
- **Retratos del equipo:** ilustraciones de `web/public/voces/` (valentina, lucas, sofia), copiadas a
  `public/proyectos/simtecuida-analisis/voces/`. No representan personas de SIM ni fijan cuántas rotan.
- **No construido hoy (el video no lo dice, a propósito; `simtecuida.md`, 7.4):** fichas con DNI, suscripción y cuidados;
  búsqueda por DNI o nombre; minuta con datos de la ficha; aviso al staff desde WhatsApp; llamadas de WhatsApp en el número de
  un cliente; prioridad de emergencias y su medición; métricas del panel por persona y por motivo.

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 2-nov-2026 | 59,6 s | Primera versión | borrador |
