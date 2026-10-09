export type IconName = "calendar" | "money" | "chat" | "headset";

export interface DemoAgent {
  slug: string;
  title: string;
  summary: string;
  icon: IconName;
  /** Línea real que atiende este agente ("llamá gratis"); sin ella, el widget no ofrece llamar por teléfono. */
  phone?: { tel: string; display: string };
}

// Línea de Atentina (Anura): el 0800 lo atiende el agente comercial; el WhatsApp va por el 351 700-2592.
// El 0800 se marca en formato nacional: con +54 no lo enrutan todas las compañías.
export const contactPhone = { tel: "08002201233", display: "0800-220-1233" };
export const whatsappUrl = `https://wa.me/5493517002592?text=${encodeURIComponent("Hola Atentina, quiero saber más")}`;

// El de la home: el mismo agente que atiende la línea y el WhatsApp de Atentina.
export const atentinaAgent: DemoAgent = {
  slug: "atentina_comercial",
  title: "Asesora de Atentina",
  summary: "Te cuenta cómo funciona y qué plan te conviene",
  icon: "headset",
  phone: contactPhone,
};

export const agents: DemoAgent[] = [
  {
    slug: "turnos",
    title: "Recepción y turnos",
    summary: "Da un turno, lo confirma y toma tus datos",
    icon: "calendar",
  },
  {
    slug: "cobranzas",
    title: "Cobranzas",
    summary: "Te llama por una cuota vencida y acuerda un pago",
    icon: "money",
  },
  {
    slug: "reclamos",
    title: "Consultas y reclamos",
    summary: "Responde preguntas frecuentes y registra un reclamo",
    icon: "chat",
  },
];

export interface Voice {
  id: string;
  name: string;
  gender: "f" | "m";
  tags: string;
  more?: boolean;
}

export const voices: Voice[] = [
  { id: "sofia", name: "Sofía", gender: "f", tags: "Cálida, clara y cercana" },
  { id: "martin", name: "Martín", gender: "m", tags: "Grave, sereno y confiable" },
  { id: "valentina", name: "Valentina", gender: "f", tags: "Joven, alegre y ágil" },
  { id: "lucas", name: "Lucas", gender: "m", tags: "Joven, cordial y dinámico" },
  { id: "carolina", name: "Carolina", gender: "f", tags: "Serena, pausada y formal" },
  { id: "tomas", name: "Tomás", gender: "m", tags: "Claro, formal y atento", more: true },
  { id: "jimena", name: "Jimena", gender: "f", tags: "Firme, nítida y profesional", more: true },
  { id: "diego", name: "Diego", gender: "m", tags: "Cálido, pausado y cercano", more: true },
  { id: "laura", name: "Laura", gender: "f", tags: "Suave, amable y tranquila", more: true },
  { id: "gabriela", name: "Gabriela", gender: "f", tags: "Madura, segura y cordial", more: true },
];

export interface Plan {
  name: string;
  for: string;
  price: string;
  per?: string;
  usd: string;
  items: string[];
  cta: string;
  featured?: boolean;
}

export const plans: Plan[] = [
  {
    name: "Mostrador",
    for: "Consultorios, estudios y locales con una línea.",
    price: "$ 29.000",
    per: "por mes",
    usd: "unos USD 19",
    items: [
      "Telefonía incluida",
      "Todo lo que ofrece Free",
      "<b>300 minutos</b> por mes",
      "1 llamada a la vez",
      "1 número",
      "Minuto adicional <span class=\"tabular-nums\">$ 99</span>",
    ],
    cta: "Empezar",
  },
  {
    name: "Sucursal",
    for: "Clínicas, comercios y servicios con varias líneas.",
    price: "$ 99.000",
    per: "por mes",
    usd: "unos USD 64",
    items: [
      "Telefonía incluida",
      "Todo lo que ofrece Free",
      "<b>1.200 minutos</b> por mes",
      "3 llamadas a la vez",
      "3 números",
      "Llamadas programadas",
      "Minuto adicional <span class=\"tabular-nums\">$ 79</span>",
    ],
    cta: "Empezar",
    featured: true,
  },
  {
    name: "Red",
    for: "Organismos con mucho volumen.",
    price: "A medida",
    usd: "Lo cotizamos según tu volumen",
    items: [
      "<b>Más de 5.000 minutos</b> por mes",
      "Las llamadas a la vez que necesites",
      "Los números que necesites",
      "Llamadas programadas",
    ],
    cta: "Hablemos",
  },
];

export interface Feature {
  title: string;
  text: string;
}

export interface Step {
  title: string;
  text: string;
}

export interface SampleField {
  label: string;
  value: string;
}

export interface Vertical {
  slug: "turnos" | "cobranzas" | "municipios";
  agent: string;
  who: string;
  title: string;
  summary: string;
  metaTitle: string;
  metaDescription: string;
  eyebrow: string;
  headline: string;
  lead: string;
  steps: Step[];
  features: Feature[];
  sample: { agent: string; outcome: string; duration: string; fields: SampleField[] };
  voiceLine: { f: string; m: string };
  defaultVoice: string;
}

export const verticals: Vertical[] = [
  {
    slug: "turnos",
    agent: "turnos",
    who: "Clínicas · Consultorios · Centros de diagnóstico",
    title: "Turnos y recordatorios",
    summary:
      "Da turnos por teléfono, llama el día anterior para confirmar y reprograma. Baja el ausentismo y libera la recepción.",
    metaTitle: "Agente de voz para turnos y recordatorios | Atentina",
    metaDescription:
      "Un agente de voz con IA que da turnos por teléfono, confirma el día anterior y reprograma. Para clínicas, consultorios y centros de diagnóstico.",
    eyebrow: "Turnos y recordatorios",
    headline: "Tu recepción atiende todas las llamadas, también las de las 8 de la mañana",
    lead: "El agente da turnos con la agenda de tu centro, toma los datos del paciente y llama el día anterior para confirmar. Si no puede ir, reprograma y libera el horario para otro.",
    steps: [
      { title: "Atiende y da el turno", text: "Pregunta la especialidad, ofrece los horarios libres y confirma el elegido." },
      { title: "Toma los datos", text: "Nombre, DNI y obra social, de a uno y repitiéndolos para no errar." },
      { title: "Recuerda y reprograma", text: "Llama el día anterior; si el paciente no puede, le ofrece otro horario." },
    ],
    features: [
      { title: "Agenda conectada", text: "Consulta y reserva en tu sistema de turnos durante la llamada." },
      { title: "Menos ausentismo", text: "Confirmación el día anterior y reprogramación en la misma llamada." },
      { title: "Respuestas al paciente", text: "Preparación de estudios, sede, horarios y qué llevar." },
      { title: "Varias llamadas a la vez", text: "Nadie espera en línea a las 8 de la mañana." },
    ],
    sample: {
      agent: "Sofía · Clínica del Sol",
      outcome: "Turno dado",
      duration: "1:42",
      fields: [
        { label: "Especialidad", value: "Pediatría" },
        { label: "Turno", value: "Martes 10:00, Dr. Rossi" },
        { label: "Paciente", value: "Ana Paz" },
        { label: "DNI", value: "30111222" },
        { label: "Cobertura", value: "OSDE" },
      ],
    },
    voiceLine: {
      f: "Hola, soy {nombre}, la asistente virtual de la clínica. Te llamo para confirmar tu turno de mañana a las diez.",
      m: "Hola, soy {nombre}, el asistente virtual de la clínica. Te llamo para confirmar tu turno de mañana a las diez.",
    },
    defaultVoice: "sofia",
  },
  {
    slug: "cobranzas",
    agent: "cobranzas",
    who: "Estudios de cobranza · Cooperativas · Fintech",
    title: "Cobranza de mora temprana",
    summary:
      "Llama a los deudores de 1 a 60 días, informa la deuda, acuerda una promesa de pago y la registra. Con buenos modos y dentro de la normativa.",
    metaTitle: "Agente de voz para cobranza de mora temprana | Atentina",
    metaDescription:
      "Un agente de voz con IA que llama a deudores de 1 a 60 días, acuerda una promesa de pago y la registra en tu sistema. Con buenos modos y dentro de la normativa.",
    eyebrow: "Cobranza de mora temprana",
    headline: "Cada deudor recibe su llamada a tiempo, con buenos modos",
    lead: "El agente llama a toda la cartera en mora temprana, confirma que habla con el titular, ofrece las opciones de pago que definís y deja registrada la promesa con fecha y monto.",
    steps: [
      { title: "Confirma al titular", text: "No da datos de la deuda a terceros: pregunta cuándo encontrarlo." },
      { title: "Ofrece opciones", text: "Pago total o cuotas, solo con las condiciones que vos definís." },
      { title: "Registra la promesa", text: "Fecha, monto o cuotas, y el motivo del atraso, en tu sistema." },
    ],
    features: [
      { title: "Campañas programadas", text: "Toda la cartera llamada en horario permitido, con reintentos." },
      { title: "Dentro de la normativa", text: "Sin amenazas ni presiones; respeta a quien pide no ser llamado." },
      { title: "Link de pago", text: "Envía el medio de pago por WhatsApp o correo al cerrar el acuerdo." },
      { title: "Precio por resultado", text: "Para carteras grandes, pagás por promesa lograda." },
    ],
    sample: {
      agent: "Valentina · Fibranet",
      outcome: "Plan en cuotas",
      duration: "2:05",
      fields: [
        { label: "Atendió el titular", value: "Sí" },
        { label: "Compromiso", value: "Cuotas" },
        { label: "Cuotas", value: "3" },
        { label: "Fecha de pago", value: "El viernes" },
        { label: "Motivo del atraso", value: "No le llegó la factura" },
      ],
    },
    voiceLine: {
      f: "Hola, soy {nombre}, la asistente virtual de Fibranet. Te llamo por la factura vencida del mes pasado.",
      m: "Hola, soy {nombre}, el asistente virtual de Fibranet. Te llamo por la factura vencida del mes pasado.",
    },
    defaultVoice: "valentina",
  },
  {
    slug: "municipios",
    agent: "reclamos",
    who: "Municipios · Organismos · Cooperativas de servicios",
    title: "Consultas y reclamos de vecinos",
    summary:
      "Atiende las 24 horas: tasas, turnos, reclamos de servicios. Registra cada gestión y deriva a la oficina que corresponde.",
    metaTitle: "Agente de voz para consultas y reclamos de vecinos | Atentina",
    metaDescription:
      "Un agente de voz con IA que atiende a los vecinos las 24 horas: tasas, trámites y reclamos de servicios, registrados y derivados a cada área.",
    eyebrow: "Consultas y reclamos de vecinos",
    headline: "La municipalidad atiende las 24 horas, sin esperas",
    lead: "El agente responde las consultas de tasas, trámites y servicios, y registra cada reclamo con categoría, dirección y contacto, listo para derivar a la oficina que corresponde.",
    steps: [
      { title: "Escucha al vecino", text: "Entiende si es una consulta o un reclamo, sin menús de opciones." },
      { title: "Responde o registra", text: "Contesta con la información del municipio o toma los datos del reclamo." },
      { title: "Deriva y avisa", text: "Envía el reclamo al área y le manda el número al vecino." },
    ],
    features: [
      { title: "24 horas, todos los días", text: "Fines de semana y feriados, con muchas llamadas a la vez." },
      { title: "Reclamos completos", text: "Categoría, dirección, descripción y contacto en cada uno." },
      { title: "Integración con tu sistema", text: "Cada reclamo entra a tu gestión de expedientes o tickets." },
      { title: "Información al día", text: "Vencimientos, horarios y requisitos que actualizás vos." },
    ],
    sample: {
      agent: "Martín · Municipalidad de San Andrés",
      outcome: "Reclamo registrado",
      duration: "1:28",
      fields: [
        { label: "Gestión", value: "Reclamo" },
        { label: "Categoría", value: "Alumbrado" },
        { label: "Descripción", value: "Poste apagado hace una semana" },
        { label: "Dirección", value: "Belgrano 1450" },
        { label: "Teléfono", value: "1155551234" },
      ],
    },
    voiceLine: {
      f: "Hola, soy {nombre}, la asistente virtual de la municipalidad. Te llamo para avisarte que tu reclamo ya fue resuelto.",
      m: "Hola, soy {nombre}, el asistente virtual de la municipalidad. Te llamo para avisarte que tu reclamo ya fue resuelto.",
    },
    defaultVoice: "martin",
  },
];

export const defaultVoiceLine = {
  f: "Hola, soy {nombre}, la asistente virtual de la clínica. Te llamo para confirmar tu turno de mañana a las diez.",
  m: "Hola, soy {nombre}, el asistente virtual de la clínica. Te llamo para confirmar tu turno de mañana a las diez.",
};

export const contactEmail = "hola@atentina.com.ar";

// ---- Home para integradores ----

/** Plan Free: API y panel web, sin telefonía. Mismo formato que los demás planes; se muestra primero en `/` y `/casos-de-uso`. */
export const freePlan: Plan = {
  name: "Free",
  for: "Para probar e integrar: la API y el panel web.",
  price: "$ 0",
  per: "por mes",
  usd: "Sin costo",
  items: ["<b>20 minutos</b> por mes", "Llamadas web", "Acceso plataforma web", "Acceso a la API"],
  cta: "Empezar gratis",
};

export interface Capability {
  title: string;
  text: string;
  /** Lo que ya funciona o lo que todavía no. */
  status: "available" | "soon";
  href?: string;
  link?: string;
}

/** Home: las tres capas de la plataforma, con los desarrolladores primero. */
export const platform: Capability[] = [
  {
    title: "Motores por API",
    text: "Reconocimiento de voz, modelo de lenguaje y síntesis con acento argentino, con una API key. Compatible con el SDK de OpenAI y con streaming.",
    status: "available",
    href: "/desarrolladores#api",
    link: "Ver la API →",
  },
  {
    title: "Agentes",
    text: "Definís el agente (datos a tomar, reglas y voz) y lo operamos nosotros. Se versiona, se prueba desde el panel y deja datos ordenados de cada conversación.",
    status: "available",
    href: "/casos-de-uso",
    link: "Ver casos de uso →",
  },
  {
    title: "Telefonía y WhatsApp",
    text: "Números argentinos, llamadas entrantes y salientes, y WhatsApp para el mismo agente. Todo en un solo servicio, por la app o por API.",
    status: "available",
    href: "#precios",
    link: "Ver planes →",
  },
];

/** `/desarrolladores`: lo que se puede construir. */
export const devCapabilities: Capability[] = [
  {
    title: "Motores sueltos",
    text: "LLM, transcripción y síntesis con una API key por sistema. Usás solo el motor que necesitás, con streaming de texto y de audio.",
    status: "available",
    href: "#api",
    link: "Ver la API →",
  },
  {
    title: "Agentes y llamadas",
    text: "Creás el agente, lanzás las llamadas y recibís el resultado de cada una en tu sistema, por API o webhook.",
    status: "available",
    href: "#agentes",
    link: "Integrarlo con tu agente de programación →",
  },
  {
    title: "Telefonía incluida",
    text: "Números argentinos, entrantes y salientes, y WhatsApp. No contratás telefonía aparte: los minutos van en el plan.",
    status: "available",
    href: "#precios",
    link: "Ver planes →",
  },
];

/** Home: lo que normalmente se contrata por separado, contra lo que incluye el plan. */
export const costsSeparate: string[] = [
  "Telefonía: línea, numeración y minutos con un proveedor",
  "Reconocimiento de voz, cobrado por minuto de audio",
  "Modelo de lenguaje, cobrado por token",
  "Síntesis de voz, cobrada por carácter o por segundo",
  "WhatsApp, con su propio alta y proveedor",
  "Servidores y plataforma para unirlo todo",
];

export const costsIncluded: string[] = [
  "Número argentino, entrante y saliente",
  "Minutos de llamada, a la vez y por mes",
  "Reconocimiento de voz, LLM y voces con acento argentino",
  "WhatsApp para el mismo agente",
  "Panel con la transcripción y los datos de cada conversación",
  "Un precio por mes, en pesos, sin permanencia",
];

export const apiFeatures: Feature[] = [
  { title: "LLM con streaming", text: "Chat completions: los tokens llegan mientras se generan, y se cobra solo lo entregado." },
  { title: "Síntesis con voces argentinas", text: "WAV completo, o PCM en streaming: empieza a sonar en medio segundo, sin esperar toda la frase." },
  { title: "Transcripción", text: "Subís el audio y recibís el texto, con los segundos que se descontaron." },
  { title: "Keys con alcance", text: "Una key para el LLM y otra para las llamadas: cada una hace solo lo que le diste." },
  { title: "Límites y consumo a la vista", text: "Tokens, minutos y pedidos por minuto por plan, y un endpoint que dice cuánto te queda." },
];

export interface Endpoint {
  path: string;
  scope: string;
  text: string;
}

/** Los endpoints de la API de inferencia (docs/API_INFERENCIA.md), sobre `/api/v1/inference`. */
export const endpoints: Endpoint[] = [
  { path: "POST /chat/completions", scope: "llm", text: "Chat con el LLM, con o sin streaming" },
  { path: "POST /audio/transcriptions", scope: "stt", text: "Transcribe un archivo de audio" },
  { path: "POST /audio/speech", scope: "tts", text: "Sintetiza texto con una de las voces" },
  { path: "GET /voices", scope: "tts", text: "Voces disponibles" },
  { path: "GET /models", scope: "cualquiera", text: "Modelos que sirve la plataforma" },
  { path: "GET /usage", scope: "cualquiera", text: "Tu consumo del mes contra el plan" },
];

export interface Qa {
  q: string;
  a: string;
}

const faqFree: Qa = {
  q: "¿Qué incluye el plan Free?",
  a: "20 minutos por mes, llamadas web, acceso a la plataforma web y acceso a la API. No incluye telefonía: ni números ni llamadas por teléfono. Cuando la necesites, pasás a un plan con telefonía.",
};
const faqNumbers: Qa = { q: "¿Qué numeración tienen?", a: "Numeración regional argentina, 0800 y 0810." };
const faqMinutes: Qa = {
  q: "¿Cómo se cuentan los minutos?",
  a: "Cada llamada se cuenta por minuto iniciado. Los minutos del plan son por mes y no se acumulan: suman las llamadas que entran y las que hace el agente.",
};
const faqOver: Qa = { q: "¿Qué pasa si me paso de los minutos?", a: "Podés comprar packs de minutos por adelantado, o cuando los necesites." };
const faqTerms: Qa = {
  q: "¿Los precios llevan IVA? ¿Hay permanencia?",
  a: "Los precios son en pesos y no incluyen IVA. No hay permanencia: se cancela cuando quieras. Si el precio cambia, avisamos con 15 días de anticipación.",
};

/** Home. */
export const faqGeneral: Qa[] = [
  {
    q: "¿Tengo que contratar telefonía aparte?",
    a: "No. Los planes con telefonía incluyen el número argentino, los minutos y las llamadas a la vez, junto con la inteligencia artificial y las voces. Es un solo servicio con un precio por mes en pesos.",
  },
  faqFree,
  faqNumbers,
  faqMinutes,
  faqTerms,
];

/** `/casos-de-uso`. */
export const faqBusiness: Qa[] = [
  {
    q: "¿Tengo que contratar telefonía aparte?",
    a: "No. El número argentino, los minutos, las llamadas a la vez y la inteligencia artificial vienen en el plan. Lo contratás y empieza a atender.",
  },
  faqNumbers,
  faqMinutes,
  faqOver,
  faqTerms,
];

/** `/desarrolladores`. */
export const faqDev: Qa[] = [
  faqFree,
  {
    q: "¿Cómo accedo a la API?",
    a: "Pedí acceso con el formulario y te creamos la cuenta. Desde el panel generás tus API keys, cada una con el alcance que elijas (LLM, transcripción, síntesis o llamadas), y ves cuánto consumiste en el mes.",
  },
  {
    q: "¿Puedo usar el SDK de OpenAI?",
    a: "Sí. Cambiás la base_url y la API key y usás el SDK que ya tenés. El modelo lo fija la plataforma: el campo model es obligatorio en los SDK pero se ignora.",
  },
  {
    q: "¿Qué pasa cuando se agota un cupo?",
    a: "Los cupos de tokens y minutos son por mes y separados por motor: agotar uno no afecta a los otros. El pedido que no entra responde 429 con un código que dice qué cupo falta, y no llega al motor ni se cobra.",
  },
  {
    q: "¿Guardan los textos y los audios que mando?",
    a: "No. La plataforma guarda cuánto consumiste, por key y por día, pero no los prompts, los audios ni los textos de la API.",
  },
  faqMinutes,
  faqTerms,
];

/** Integración agéntica: lo que un agente de programación puede hacer con la plataforma. */
export const agenticFeatures: Feature[] = [
  { title: "Crear y probar agentes", text: "Define el agente, lo versiona y lo prueba con una conversación de texto antes de publicarlo." },
  { title: "Campañas desde un CSV", text: "Lee tu lista de números, llama a todos y te devuelve un CSV con lo que dijo cada persona." },
  { title: "Usar los motores de IA", text: "Chat, transcripción y síntesis con voces argentinas, desde el mismo agente de programación." },
  { title: "Controlar el consumo", text: "Consulta cuánto se usó en el mes contra el plan, antes de que se agote." },
];

/** Agentes de programación con skills. */
export const skillTools = ["Claude Code", "Cursor", "Codex"];
