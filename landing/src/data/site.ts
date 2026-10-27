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

/** Catálogo completo servido por el TTS (`multi41`; fuente: tts/finetune/voces.tsv, sin WER ni car/s). Las 10 de arriba traen descripción; el resto, solo el género. */
const restOfVoices: [id: string, name: string, gender: "f" | "m"][] = [
  ["martina", "Martina", "f"],
  ["camila", "Camila", "f"],
  ["lucia", "Lucía", "f"],
  ["julieta", "Julieta", "f"],
  ["florencia", "Florencia", "f"],
  ["agustina", "Agustina", "f"],
  ["mariana", "Mariana", "f"],
  ["paula", "Paula", "f"],
  ["romina", "Romina", "f"],
  ["natalia", "Natalia", "f"],
  ["silvina", "Silvina", "f"],
  ["andrea", "Andrea", "f"],
  ["veronica", "Verónica", "f"],
  ["lorena", "Lorena", "f"],
  ["daniela", "Daniela", "f"],
  ["micaela", "Micaela", "f"],
  ["rocio", "Rocío", "f"],
  ["belen", "Belén", "f"],
  ["milagros", "Milagros", "f"],
  ["antonella", "Antonella", "f"],
  ["carla", "Carla", "f"],
  ["noelia", "Noelia", "f"],
  ["mateo", "Mateo", "m"],
  ["santiago", "Santiago", "m"],
  ["nicolas", "Nicolás", "m"],
  ["facundo", "Facundo", "m"],
  ["joaquin", "Joaquín", "m"],
  ["federico", "Federico", "m"],
  ["gonzalo", "Gonzalo", "m"],
  ["pablo", "Pablo", "m"],
  ["emiliano", "Emiliano", "m"],
];

/** Las 41 voces: las 10 con descripción primero y después el resto, con el género como descripción. */
export const allVoices: Voice[] = [
  ...voices,
  ...restOfVoices.map(([id, name, gender]) => ({ id, name, gender, tags: gender === "f" ? "Voz femenina" : "Voz masculina" })),
];

export const voiceCount = allVoices.length;
export const voiceCountFemale = allVoices.filter((v) => v.gender === "f").length;
export const voiceCountMale = voiceCount - voiceCountFemale;

export interface Plan {
  name: string;
  for: string;
  price: string;
  per?: string;
  usd: string;
  items: string[];
  cta: string;
  featured?: boolean;
  /** false: no se contrata por el registro ("A medida"): el botón va al contacto. */
  signup?: boolean;
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
      "WhatsApp",
      "500 contactos",
      "Derivación a 1 persona",
      "Teléfono del equipo: llamar y atender desde el panel",
      "Reportes completos: resultados, conversiones, transferencias, WhatsApp y campañas, con CSV",
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
      "WhatsApp",
      "Campañas de llamadas y de WhatsApp",
      "5.000 contactos",
      "Derivación a 2 personas",
      "Teléfono del equipo: llamar y atender desde el panel",
      "Reportes completos: resultados, conversiones, transferencias, WhatsApp y campañas, con CSV",
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
      "Campañas de llamadas y de WhatsApp",
      "Contactos y equipo sin tope",
      "Teléfono del equipo: llamar y atender desde el panel",
      "Reportes completos: resultados, conversiones, transferencias, WhatsApp y campañas, con CSV",
    ],
    cta: "Hablemos",
    signup: false,
  },
];

export interface Feature {
  title: string;
  text: string;
  /** Link de texto al final (enlazado interno hacia las páginas de `/plataforma`). */
  href?: string;
  link?: string;
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
      { title: "Varias llamadas a la vez", text: "Nadie espera en línea a las 8 de la mañana.", href: "/plataforma/telefonia", link: "Ver la telefonía" },
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
      "Agente de voz con IA que llama a deudores de 1 a 60 días y registra la promesa de pago. Para estudios de cobranza, cooperativas y fintech.",
    eyebrow: "Cobranza de mora temprana",
    headline: "Cada deudor recibe su llamada a tiempo, con buenos modos",
    lead: "El agente llama a toda la cartera en mora temprana, confirma que habla con el titular, ofrece las opciones de pago que definís y deja registrada la promesa con fecha y monto.",
    steps: [
      { title: "Confirma al titular", text: "No da datos de la deuda a terceros: pregunta cuándo encontrarlo." },
      { title: "Ofrece opciones", text: "Pago total o cuotas, solo con las condiciones que vos definís." },
      { title: "Registra la promesa", text: "Fecha, monto o cuotas, y el motivo del atraso, en tu sistema." },
    ],
    features: [
      { title: "Campañas programadas", text: "Toda la cartera llamada en horario permitido, con reintentos.", href: "/plataforma/telefonia", link: "Ver la telefonía" },
      { title: "Dentro de la normativa", text: "Sin amenazas ni presiones; respeta a quien pide no ser llamado." },
      { title: "Link de pago", text: "Envía el medio de pago por WhatsApp o correo al cerrar el acuerdo.", href: "/plataforma/whatsapp", link: "Ver WhatsApp con IA" },
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
      "Agente de voz con IA que atiende a los vecinos las 24 horas: tasas, trámites y reclamos, derivados a cada área. Para municipios y organismos.",
    eyebrow: "Consultas y reclamos de vecinos",
    headline: "La municipalidad atiende las 24 horas, sin esperas",
    lead: "El agente responde las consultas de tasas, trámites y servicios, y registra cada reclamo con categoría, dirección y contacto, listo para derivar a la oficina que corresponde.",
    steps: [
      { title: "Escucha al vecino", text: "Entiende si es una consulta o un reclamo, sin menús de opciones." },
      { title: "Responde o registra", text: "Contesta con la información del municipio o toma los datos del reclamo." },
      { title: "Deriva y avisa", text: "Envía el reclamo al área y le manda el número al vecino." },
    ],
    features: [
      { title: "24 horas, todos los días", text: "Fines de semana y feriados, con muchas llamadas a la vez.", href: "/plataforma/telefonia", link: "Ver la telefonía" },
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
  items: ["<b>20 minutos</b> por mes", "Llamadas web", "Acceso plataforma web", "Acceso a la API", "Reportes básicos: consultas, llamadas y consumo"],
  cta: "Empezar gratis",
};

export interface Capability {
  title: string;
  text: string;
  /** Lo que ya funciona o lo que todavía no. */
  status: "available" | "soon";
  href?: string;
  link?: string;
  /** Links de texto debajo del principal, hacia las páginas de `/plataforma`. */
  more?: { href: string; label: string }[];
}

/** Home: las tres capas de la plataforma, con los desarrolladores primero. */
export const platform: Capability[] = [
  {
    title: "Motores por API",
    text: "Reconocimiento de voz, modelo de lenguaje y síntesis con acento argentino, con una API key. Compatible con el SDK de OpenAI y con streaming.",
    status: "available",
    href: "/desarrolladores#api",
    link: "Ver la API →",
    more: [
      { href: "/plataforma/voces-argentinas", label: "Voces argentinas →" },
      { href: "/plataforma/transcripcion", label: "Transcripción de audio →" },
    ],
  },
  {
    title: "Agentes",
    text: "Definís el agente (datos a tomar, reglas y voz) y lo operamos nosotros. Se versiona, se prueba desde el panel y deja datos ordenados de cada conversación. En Reportes ves cuántas consultas recibís por día, cuántas terminan bien y cuántas pasan a una persona.",
    status: "available",
    href: "/casos-de-uso",
    link: "Ver casos de uso →",
  },
  {
    title: "Telefonía y WhatsApp",
    text: "Números argentinos, llamadas entrantes y salientes, y WhatsApp para el mismo agente. Tu equipo también llama y atiende desde el panel. Todo en un solo servicio, por la app o por API.",
    status: "available",
    href: "#precios",
    link: "Ver planes →",
    more: [
      { href: "/plataforma/telefonia", label: "Telefonía y SIP →" },
      { href: "/plataforma/telefono-del-equipo", label: "Teléfono del equipo →" },
      { href: "/plataforma/whatsapp", label: "WhatsApp con IA →" },
    ],
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
    more: [
      { href: "/plataforma/voces-argentinas", label: "Voces argentinas →" },
      { href: "/plataforma/transcripcion", label: "Transcripción de audio →" },
    ],
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
    text: "Números argentinos, entrantes y salientes, y WhatsApp. Tu equipo también llama y atiende desde el panel. No contratás telefonía aparte: los minutos van en el plan.",
    status: "available",
    href: "#precios",
    link: "Ver planes →",
    more: [
      { href: "/plataforma/telefonia", label: "Telefonía y SIP →" },
      { href: "/plataforma/telefono-del-equipo", label: "Teléfono del equipo →" },
      { href: "/plataforma/whatsapp", label: "WhatsApp con IA →" },
    ],
  },
  {
    title: "Tu agente, nuestra voz",
    text: "¿Ya tenés tu agente de IA? Lo conectás con un endpoint compatible con OpenAI y atiende llamadas y WhatsApp con nuestra voz y nuestros números. Planes Sucursal y Red.",
    status: "available",
    href: "/desarrolladores/docs/tu-propio-agente",
    link: "Conectar tu propio agente →",
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
  a: "20 minutos por mes, llamadas web, acceso a la plataforma web, acceso a la API y reportes básicos (consultas, llamadas y consumo). No incluye telefonía: ni números ni llamadas por teléfono. Cuando la necesites, pasás a un plan con telefonía.",
};
const faqNumbers: Qa = { q: "¿Qué numeración tienen?", a: "Numeración regional argentina, 0800 y 0810." };
const faqMinutes: Qa = {
  q: "¿Cómo se cuentan los minutos?",
  a: "Cada llamada se cuenta por minuto iniciado. Los minutos del plan son por mes y no se acumulan: suman las llamadas que entran y las que hace el agente.",
};
const faqOver: Qa = {
  q: "¿Qué pasa si me paso de los minutos?",
  a: "Al llegar al tope del plan, el agente deja de atender hasta el mes siguiente. Podés pasar a un plan mayor desde el panel, o escribinos y te sumamos minutos para ese mes.",
};
const faqTerms: Qa = {
  q: "¿Cómo se paga? ¿Hay permanencia?",
  a: "Los precios son finales, por mes y en pesos. Te registrás gratis y, cuando elegís un plan, lo pagás por transferencia desde el panel. No hay permanencia: se cancela cuando quieras. Si el precio cambia, avisamos con 15 días de anticipación.",
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

// ---- Páginas de capacidad (`/plataforma/<slug>`, docs/SEO_LANDING.md) ----

const API_BASE = "https://app.atentina.com.ar/api/v1/inference";

export interface CodeExample {
  label: string;
  code: string;
}

export interface TextSection {
  title: string;
  paragraphs: string[];
}

export interface CapabilityPage {
  slug: "voces-argentinas" | "transcripcion" | "whatsapp" | "telefonia" | "telefono-del-equipo";
  /** Nombre corto: tarjetas, migas de pan y footer. */
  title: string;
  /** Texto de la tarjeta en `/plataforma`. */
  summary: string;
  metaTitle: string;
  metaDescription: string;
  ogDescription: string;
  eyebrow: string;
  headline: string;
  /** Parte del `headline` que va en el acento. */
  highlight: string;
  lead: string;
  /** Datos en mono debajo de los botones del hero. */
  facts: string[];
  /** Qué hay a la derecha del hero: un pedido a la API, la llamada de la demo o el botón a WhatsApp. */
  hero: "code" | "call" | "whatsapp" | "phone";
  heroCode?: CodeExample;
  /** Suma la demo de voces (`Voices`) debajo del hero, con otro título y bajada. */
  voices?: { title: string; lead: string; all?: boolean };
  /** Muestra el catálogo completo de voces como texto. */
  catalog?: boolean;
  sections: TextSection[];
  steps: Step[];
  features: Feature[];
  /** Ejemplos de pedidos a la API (`CodeBlock`). */
  code?: { title: string; lead: string; examples: CodeExample[] };
  /** Precios: `free` suma el plan Free (API); sin él, solo los planes con telefonía. */
  pricingFree: boolean;
  faq: Qa[];
  serviceType: string;
  /** Cta del cierre. */
  cta: { subject: string; question: string; placeholder: string };
}

export const capabilities: CapabilityPage[] = [
  {
    slug: "voces-argentinas",
    title: "Voces argentinas",
    summary: "41 voces con acento argentino para agentes, avisos y audios. Por API compatible con OpenAI, con streaming.",
    metaTitle: "Voces argentinas con IA: síntesis de voz (TTS) | Atentina",
    metaDescription:
      "41 voces argentinas con IA para convertir texto en audio, 28 femeninas y 13 masculinas, por API compatible con OpenAI o en tus agentes. Probalas acá.",
    ogDescription: "41 voces con acento argentino, por API y en tus agentes.",
    eyebrow: "Voces argentinas",
    headline: "Voces argentinas con IA, con nuestro acento",
    highlight: "con nuestro acento",
    lead: "41 voces con acento argentino para convertir texto en audio: 28 femeninas y 13 masculinas, entrenadas en servidores propios. Las usan nuestros agentes y las podés usar vos por API.",
    facts: ["41 voces", "28 femeninas, 13 masculinas", "Compatible con OpenAI", "Streaming de audio"],
    hero: "code",
    heroCode: {
      label: "POST /audio/speech",
      code: `curl ${API_BASE}/audio/speech \\
  -H "Authorization: Bearer $ATENTINA_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"voice":"sofia","input":"Hola, ¿en qué te puedo ayudar?"}' \\
  --output respuesta.wav`,
    },
    voices: {
      title: "Escuchá las 41 voces",
      lead: "Elegí una, escribí lo que quieras y escuchala. Es el mismo motor que habla en las llamadas de nuestros agentes.",
      all: true,
    },
    catalog: true,
    sections: [
      {
        title: "Qué son las voces de Atentina",
        paragraphs: [
          "Son voces sintéticas que hablan con acento argentino. Entrenamos el modelo de síntesis con hablantes argentinos, en servidores propios, y hoy sirve 41 voces con nombre propio: 28 femeninas y 13 masculinas. Algunas suenan cálidas y cercanas; otras, más serenas y formales. Cada una se elige por su nombre, como sofia o martin.",
          "Son las mismas voces que usan los agentes de Atentina en las llamadas y en WhatsApp. Lo que escuchás en la demo de esta página sale del mismo motor que atiende a quien recibe una llamada.",
        ],
      },
      {
        title: "Tres formas de usarlas",
        paragraphs: [
          "La primera es un agente: elegís la voz al armarlo y atiende llamadas y mensajes con ella. La segunda es la API de síntesis, POST /audio/speech, compatible con OpenAI: mandás el texto y el nombre de la voz, y recibís el audio. La tercera es la demo de esta página, para escuchar un texto tuyo antes de decidir.",
          "Si ya usás el SDK de OpenAI, solo cambiás la base_url y la API key. El campo model es obligatorio en el SDK, pero la plataforma lo ignora.",
        ],
      },
      {
        title: "Para qué se usan",
        paragraphs: [
          "En agentes que atienden por teléfono y por WhatsApp, donde la voz es lo primero que percibe quien llama. En menús y avisos de telefonía (IVR), con acento local. En audios para WhatsApp, como recordatorios y confirmaciones. Y en la lectura de textos: novedades, avisos de un sistema o contenido para quien prefiere escuchar.",
        ],
      },
      {
        title: "Empieza a sonar enseguida",
        paragraphs: [
          "Con response_format en wav recibís el archivo completo, cuando termina la síntesis. Con pcm recibís el audio crudo (24 kHz, mono, 16 bits) a medida que se genera, y con stream_format en sse, eventos listos para el navegador. En la demo de esta página, el audio empieza a sonar a los 0,5 segundos, sin esperar a que termine la frase.",
        ],
      },
      {
        title: "Para quién es",
        paragraphs: [
          "Para desarrolladores y equipos de producto que necesitan una voz argentina en su aplicación, y para empresas que quieren que su agente, su 0800 o sus avisos suenen locales. También para quien produce audio en español y no quiere una voz neutra.",
        ],
      },
    ],
    steps: [
      { title: "Elegí la voz", text: "Escuchá las 41 con tu propio texto y quedate con la que va con tu marca." },
      { title: "Creá tu cuenta y una key", text: "Gratis, desde el registro. La API key lleva el alcance de síntesis (tts)." },
      { title: "Pedí el audio", text: "Mandás el texto y el nombre de la voz a /audio/speech, y recibís WAV o PCM en streaming." },
    ],
    features: [
      { title: "41 voces con nombre", text: "28 femeninas y 13 masculinas. La lista sale por API en GET /voices." },
      { title: "Streaming de audio", text: "PCM crudo a medida que se sintetiza, o eventos SSE para el navegador." },
      { title: "WAV completo", text: "Un archivo con el encabezado correcto, listo para guardar o reproducir." },
      { title: "Compatible con OpenAI", text: "El SDK que ya usás, con otra base_url y tu API key." },
      { title: "Hasta 1.500 caracteres por pedido", text: "Para textos más largos, mandás varios pedidos." },
      { title: "Consumo a la vista", text: "Se descuentan los segundos de audio generado, y GET /usage dice cuánto te queda del mes." },
    ],
    code: {
      title: "Un pedido, un audio",
      lead: "Los dos ejemplos son pedidos reales a la API. El primero guarda el archivo; el segundo lo escucha mientras se sintetiza.",
      examples: [
        {
          label: "Python con el SDK de OpenAI",
          code: `from openai import OpenAI

client = OpenAI(base_url="${API_BASE}", api_key="vaas_...")
client.audio.speech.create(
    model="atentina",
    voice="sofia",
    input="Hola, ¿en qué te puedo ayudar?",
    response_format="wav",
).write_to_file("respuesta.wav")`,
        },
        {
          label: "curl con streaming (ffplay viene con ffmpeg)",
          code: `curl -sN ${API_BASE}/audio/speech \\
  -H "Authorization: Bearer $ATENTINA_KEY" -H "Content-Type: application/json" \\
  -d '{"voice":"sofia","input":"Hola, ¿en qué te puedo ayudar?","response_format":"pcm"}' \\
  | ffplay -f s16le -ar 24000 -ac 1 -nodisp -autoexit -`,
        },
      ],
    },
    pricingFree: true,
    faq: [
      {
        q: "¿Cuántas voces hay y cuáles son?",
        a: "41, todas con acento argentino: 28 femeninas y 13 masculinas. La lista completa está en esta página y la API la devuelve en GET /voices.",
      },
      {
        q: "¿Puedo tener una voz propia o clonar la mía?",
        a: "Hoy el catálogo es el de las 41 voces. Si necesitás una voz distinta para tu marca, escribinos y lo vemos.",
      },
      {
        q: "¿Recibo el audio completo o en streaming?",
        a: "Las dos. Con wav recibís el archivo al terminar la síntesis; con pcm, el audio llega a medida que se genera, y con sse en eventos para el navegador.",
      },
      {
        q: "¿Qué pasa si pido una voz que no existe?",
        a: "La API responde 422 con el código invalid_voice. Mandá siempre una de las voces de GET /voices: el campo voice es obligatorio.",
      },
      {
        q: "¿Cómo se cuenta el consumo?",
        a: "Se descuentan los segundos de audio generado contra el cupo mensual de síntesis. El plan Free te deja probar la API; si necesitás más volumen, lo armamos a medida.",
      },
      {
        q: "¿Guardan los textos que sintetizo?",
        a: "No. La plataforma guarda cuánto consumiste, por key y por día, pero no los textos ni los audios de la API.",
      },
    ],
    serviceType: "Síntesis de voz con acento argentino",
    cta: {
      subject: "Consulta sobre las voces argentinas de Atentina",
      question: "¿Para qué querés usar las voces?",
      placeholder: "Por ejemplo: avisos grabados para el 0800 de mi empresa",
    },
  },
  {
    slug: "transcripcion",
    title: "Transcripción",
    summary: "Audio en español a texto, por API compatible con OpenAI. Archivos y llamadas, con el consumo a la vista.",
    metaTitle: "Transcripción de audio en español por API | Atentina",
    metaDescription:
      "Transcripción de audio en español por API (speech to text) compatible con OpenAI: archivos, llamadas y notas de voz, con los minutos a la vista.",
    ogDescription: "Audio en español a texto por API compatible con OpenAI.",
    eyebrow: "Transcripción",
    headline: "Transcripción de audio en español por API",
    highlight: "por API",
    lead: "Subís un archivo de audio y recibís el texto en español, con el acento rioplatense de las llamadas y las notas de voz. Es el reconocimiento de voz que usan nuestros agentes.",
    facts: ["POST /audio/transcriptions", "Compatible con OpenAI", "Español rioplatense", "No guardamos tus audios"],
    hero: "code",
    heroCode: {
      label: "POST /audio/transcriptions",
      code: `curl ${API_BASE}/audio/transcriptions \\
  -H "Authorization: Bearer $ATENTINA_KEY" \\
  -F file=@llamada.wav -F language=es

{"text":"Hola, quería confirmar mi turno del martes.",
 "usage":{"type":"duration","seconds":4.0}}`,
    },
    voices: {
      title: "Y en el otro sentido, texto a voz",
      lead: "La transcripción pasa la voz a texto; la síntesis, el texto a voz. Probá las voces argentinas con tu propio texto.",
    },
    sections: [
      {
        title: "Qué hace",
        paragraphs: [
          "Convierte audio en texto. Mandás un archivo (wav, mp3, flac, ogg y más, mono o estéreo, a cualquier frecuencia) a POST /audio/transcriptions y la API devuelve la transcripción en español. La respuesta puede ser json, texto plano o verbose_json, que además trae la duración del audio.",
          "Es el mismo reconocimiento de voz que usan nuestros agentes con el español rioplatense de las llamadas y las notas de voz. En una prueba, 4 segundos de audio se transcribieron en 0,13 segundos.",
        ],
      },
      {
        title: "Para qué se usa",
        paragraphs: [
          "Para pasar a texto las llamadas que grabó tu central o tu sistema y poder buscarlas, resumirlas o analizarlas. Para las notas de voz que te mandan tus clientes o tu equipo. Para entrevistas y reuniones grabadas. Y para cualquier sistema que reciba audio y necesite el texto: un CRM, un formulario por voz o un flujo de trabajo propio.",
        ],
      },
      {
        title: "Cómo se usa",
        paragraphs: [
          "Creás una API key con el alcance de transcripción (stt) y mandás el archivo como multipart/form-data, con language=es. Si ya usás el SDK de OpenAI, cambiás la base_url y la key y llamás a client.audio.transcriptions.create. Cada archivo puede pesar hasta 25 MB: para audios más largos, partilos.",
        ],
      },
      {
        title: "Dentro de los agentes",
        paragraphs: [
          "Cuando un agente de Atentina atiende, transcribe en vivo lo que dice la persona en cada turno de la llamada y cada nota de voz de WhatsApp. El panel guarda la transcripción de cada conversación junto con los datos que el agente tomó, y el resultado llega a tu sistema por API o webhook.",
        ],
      },
      {
        title: "Consumo y privacidad",
        paragraphs: [
          "Se descuentan los segundos de audio que informa el campo usage, contra un cupo de minutos por mes. GET /usage muestra cuánto llevás consumido, y cuando el cupo se agota el pedido responde 429 con un código que dice cuál falta. La plataforma guarda el consumo por key y por día, pero no los audios ni los textos que mandás por la API.",
        ],
      },
      {
        title: "Para quién es",
        paragraphs: [
          "Para desarrolladores y equipos que reciben audio y necesitan el texto: soporte, calidad, cobranzas u operaciones. Y para quien ya usa el SDK de OpenAI y quiere probar un motor en español, en servidores en Argentina, con el consumo a la vista.",
        ],
      },
    ],
    steps: [
      { title: "Creá tu cuenta y una key", text: "Gratis, desde el registro. La API key lleva el alcance de transcripción (stt)." },
      { title: "Mandá el audio", text: "Un archivo por pedido, como multipart/form-data, con language=es." },
      { title: "Recibí el texto", text: "En json, texto plano o verbose_json, con los segundos que se descontaron." },
    ],
    features: [
      { title: "Formatos de audio comunes", text: "wav, mp3, flac, ogg y más; mono o estéreo, a cualquier frecuencia." },
      { title: "Tres formatos de respuesta", text: "json, text o verbose_json, que trae la duración." },
      { title: "Compatible con OpenAI", text: "El SDK que ya usás, con otra base_url y tu API key." },
      { title: "Minutos a la vista", text: "Se descuentan los segundos de audio, y GET /usage muestra el consumo del mes." },
      { title: "Sin guardar tus audios", text: "La plataforma no guarda los audios ni los textos que mandás por la API." },
      { title: "Servidores en Argentina", text: "Corre en servidores propios, los mismos que usan nuestros agentes." },
    ],
    code: {
      title: "Un archivo, un texto",
      lead: "El mismo pedido con el SDK de OpenAI para Python.",
      examples: [
        {
          label: "Python con el SDK de OpenAI",
          code: `from openai import OpenAI

client = OpenAI(base_url="${API_BASE}", api_key="vaas_...")
texto = client.audio.transcriptions.create(
    model="atentina",
    file=open("llamada.wav", "rb"),
    language="es",
).text`,
        },
      ],
    },
    pricingFree: true,
    faq: [
      {
        q: "¿Qué idioma transcribe?",
        a: "Español, que es para lo que lo usamos con nuestros agentes. Indicá language=es en el pedido.",
      },
      {
        q: "¿Qué formatos y tamaños acepta?",
        a: "wav, mp3, flac, ogg y más, mono o estéreo y a cualquier frecuencia, hasta 25 MB por archivo. Un archivo más grande se rechaza: partilo en pedazos.",
      },
      {
        q: "¿Transcribe llamadas en vivo?",
        a: "La API transcribe archivos. Los agentes de Atentina sí transcriben en vivo cada llamada y cada nota de voz de WhatsApp, y guardan la transcripción en el panel.",
      },
      {
        q: "¿Guardan mis audios?",
        a: "No. La plataforma guarda cuánto consumiste, por key y por día, pero no los audios ni los textos que mandás por la API.",
      },
      {
        q: "¿Cómo se cuenta el consumo?",
        a: "Por los segundos de audio de cada archivo, contra el cupo mensual de minutos de transcripción. El plan Free te deja probar la API; si necesitás más volumen, lo armamos a medida.",
      },
    ],
    serviceType: "Transcripción de audio en español",
    cta: {
      subject: "Consulta sobre la transcripción de audio de Atentina",
      question: "¿Qué audios querés transcribir?",
      placeholder: "Por ejemplo: las llamadas grabadas de mi central, unas 500 por día",
    },
  },
  {
    slug: "whatsapp",
    title: "WhatsApp con IA",
    summary: "El mismo agente que atiende el teléfono atiende WhatsApp: texto, notas de voz y llamadas.",
    metaTitle: "WhatsApp con IA para empresas: texto, voz y llamadas | Atentina",
    metaDescription:
      "Un agente con IA que atiende tu WhatsApp con texto, notas de voz y llamadas, y es el mismo que atiende el teléfono. Con campañas salientes y link de pago.",
    ogDescription: "El mismo agente atiende tu teléfono y tu WhatsApp.",
    eyebrow: "WhatsApp con IA",
    headline: "WhatsApp con IA para tu empresa",
    highlight: "con IA",
    lead: "El mismo agente que atiende tu teléfono atiende tu WhatsApp: responde mensajes, entiende notas de voz y atiende llamadas de WhatsApp. Sin sumar otro proveedor ni otro bot.",
    facts: ["Texto, notas de voz y llamadas", "El mismo agente que el teléfono", "Campañas salientes", "Alta del número desde el panel"],
    hero: "whatsapp",
    sections: [
      {
        title: "Un agente, dos canales",
        paragraphs: [
          "Un agente de Atentina no está atado a un canal. Lo definís una vez (los datos que toma, sus reglas y su voz) y atiende por teléfono y por WhatsApp. Vos ves los chats y las llamadas en el mismo panel, con la transcripción y los datos que el agente tomó.",
        ],
      },
      {
        title: "Qué atiende",
        paragraphs: [
          "Mensajes de texto, que el agente contesta con las reglas y la información de tu negocio. Notas de voz, que transcribe, entiende y contesta, incluso con una nota de voz propia, con la voz que elegiste. Y llamadas de WhatsApp: las atiende el agente del número, igual que una llamada telefónica.",
        ],
      },
      {
        title: "Campañas salientes",
        paragraphs: [
          "Para avisar, recordar o cobrar, cargás una lista de contactos, elegís una plantilla aprobada por Meta y la campaña la manda en el horario y al ritmo que definas. Cuando alguien responde, lo atiende el agente. Las campañas respetan a quien pide no recibir más mensajes.",
        ],
      },
      {
        title: "Ruteo por contacto",
        paragraphs: [
          "Cada cuenta de WhatsApp tiene su agente por defecto y reglas: una lista de contactos puede atenderla otro agente. Así, tus clientes habituales, tus proveedores y los que escriben por primera vez pueden tener cada uno el agente que corresponde, desde el mismo número. Se configura en la cuenta, desde el panel.",
        ],
      },
      {
        title: "Qué ve tu equipo",
        paragraphs: [
          "Cada chat y cada llamada queda en el panel con su transcripción, los datos que el agente tomó y el resultado, y el panel marca el origen: WhatsApp o teléfono. Ese resultado también llega a tu sistema por API o webhook, para que no tengas que copiarlo a mano.",
        ],
      },
      {
        title: "Para quién es",
        paragraphs: [
          "Para empresas que ya reciben consultas por WhatsApp y no llegan a contestarlas todas: clínicas y consultorios, estudios de cobranza, comercios y servicios. Y para quienes quieren avisar o recordar algo a su base de clientes sin hacerlo mensaje por mensaje.",
        ],
      },
      {
        title: "Alta del número y link de pago",
        paragraphs: [
          "El número de WhatsApp se da de alta desde el panel. Si querés usar el de tu línea de siempre, consultanos. Cuando el agente cierra un acuerdo, por ejemplo un plan de pago, manda el link de pago por WhatsApp para que la persona lo resuelva ahí mismo.",
        ],
      },
    ],
    steps: [
      { title: "Nos contás qué tiene que atender", text: "Armamos el agente con tus reglas, tus datos y la voz que elijas. Es el mismo del teléfono." },
      { title: "Das de alta tu número", text: "Desde el panel, sin armar otra integración." },
      { title: "El agente atiende y deja los datos", text: "Cada conversación queda en el panel, y el resultado llega a tu sistema por API o webhook." },
    ],
    features: [
      { title: "Mensajes de texto", text: "Responde con las reglas y la información de tu negocio." },
      { title: "Notas de voz", text: "Las transcribe, las entiende y puede contestar con voz." },
      { title: "Llamadas de WhatsApp", text: "Las atiende el agente del número, como una llamada telefónica." },
      { title: "Campañas salientes", text: "Plantillas aprobadas, a una lista de contactos, con horario y ritmo." },
      { title: "Ruteo por contacto", text: "Un agente por defecto y reglas para listas de contactos." },
      { title: "Link de pago", text: "Lo envía por WhatsApp al cerrar el acuerdo." },
      { title: "Panel de conversaciones", text: "Transcripción, datos tomados y resultado de cada chat y cada llamada." },
    ],
    pricingFree: false,
    faq: [
      {
        q: "¿Es el mismo agente que atiende el teléfono?",
        a: "Sí. Lo definís una vez y atiende por llamada y por WhatsApp, con las mismas reglas, los mismos datos y la misma voz.",
      },
      {
        q: "¿Atiende notas de voz y llamadas de WhatsApp?",
        a: "Sí. Transcribe y entiende las notas de voz, y las llamadas de WhatsApp las atiende el agente del número, como una llamada telefónica.",
      },
      {
        q: "¿Puedo mandar campañas por WhatsApp?",
        a: "Sí, con plantillas aprobadas por Meta, a una lista de contactos. Meta solo permite escribir primero con una plantilla; las respuestas las atiende el agente.",
      },
      {
        q: "¿WhatsApp tiene un costo aparte?",
        a: "Meta cobra por los mensajes de plantilla que se envían, según su categoría y el país de destino. Escribinos y te contamos el detalle para tu caso.",
      },
      {
        q: "¿Cómo se da de alta mi número?",
        a: "Desde el panel. Si querés usar el número de tu línea de siempre, consultanos cómo conviene hacerlo.",
      },
    ],
    serviceType: "Atención por WhatsApp con inteligencia artificial",
    cta: {
      subject: "Quiero un agente de WhatsApp con Atentina",
      question: "¿Qué tendría que atender por WhatsApp?",
      placeholder: "Por ejemplo: consultas y turnos de una clínica, unos 100 mensajes por día",
    },
  },
  {
    slug: "telefonia",
    title: "Telefonía",
    summary: "Números argentinos, 0800 y 0810, entrantes y salientes, con los minutos incluidos en el plan. El equipo también llama y atiende desde el panel.",
    metaTitle: "Telefonía en Argentina: números, 0800 y SIP con IA | Atentina",
    metaDescription:
      "Números regionales, 0800 y 0810, llamadas entrantes y salientes con agentes de IA y minutos incluidos. Si tenés central o proveedor SIP propio, consultanos.",
    ogDescription: "Números, 0800 y SIP con agentes de IA. Minutos en el plan.",
    eyebrow: "Telefonía",
    headline: "Telefonía argentina incluida: números, 0800 y SIP",
    highlight: "incluida",
    lead: "Un número argentino, llamadas entrantes y salientes, varias a la vez y los minutos dentro del plan. La plataforma corre sobre SIP: si tenés una línea o una central, consultanos.",
    facts: ["Regionales, 0800 y 0810", "Entrantes y salientes", "Varias llamadas a la vez", "Minutos incluidos"],
    hero: "call",
    sections: [
      {
        title: "Qué incluye la telefonía",
        paragraphs: [
          "No contratás un proveedor de telefonía aparte. Cada plan con telefonía trae sus números, una cantidad de minutos por mes y cuántas llamadas atiende el agente a la vez. Todo en un solo servicio, con un precio por mes en pesos. Podés probarlo ahora: llamá al 0800-220-1233 y te atiende uno de nuestros agentes.",
        ],
      },
      {
        title: "Numeración",
        paragraphs: [
          "Numeración regional argentina, 0800 y 0810. Cada número atiende al agente que elijas, y los planes incluyen uno (Mostrador), tres (Sucursal) o los que necesites (Red). Si querés separar la atención de ventas de la de reclamos, cada una puede tener su número y su agente.",
        ],
      },
      {
        title: "Llamadas entrantes y salientes",
        paragraphs: [
          "En las entrantes, el agente atiende, toma los datos y deja el resultado en el panel y en tu sistema. En las salientes, es el agente el que llama: para confirmar un turno, recordar un vencimiento o acordar un pago. Los planes Sucursal y Red suman campañas de llamadas, y por API o webhook lanzás las llamadas que necesites y recibís el resultado de cada una.",
          "Tu equipo también llama y atiende: desde el panel, con el número de la empresa y sin agente, y cada número se configura para que lo atienda el equipo o el agente. Las llamadas del equipo quedan grabadas y transcriptas en el mismo historial.",
        ],
      },
      {
        title: "Campañas de llamadas",
        paragraphs: [
          "Cargás tus contactos (a mano, desde un CSV o por API), elegís el agente y la campaña llama sola: de a uno o varios a la vez, en el horario y los días que elijas, con reintentos a quien no atendió o daba ocupado. El agente saluda a cada persona por su nombre y ya conoce sus datos, como el monto o el vencimiento. En el panel ves el avance en vivo, cuántos atendieron y cuántos llegaron al objetivo, y al final descargás un reporte con lo que dijo cada uno. Si querés, a quien no atendió le llega un WhatsApp para seguir la conversación por ahí.",
        ],
      },
      {
        title: "SIP y tu central telefónica",
        paragraphs: [
          "La plataforma corre sobre SIP, el protocolo estándar de la telefonía IP, y por ahí conecta la red telefónica argentina con los agentes. Si tenés una central telefónica (PBX) o un proveedor SIP propio y querés usarlo, consultanos: hoy lo armamos con vos, no es algo que se active solo desde el panel.",
        ],
      },
      {
        title: "Cómo se cuentan los minutos",
        paragraphs: [
          "Cada llamada se cuenta por minuto iniciado. Los minutos del plan son por mes, no se acumulan y suman las llamadas que entran y las que hace el agente. Al llegar al tope, el agente deja de atender hasta el mes siguiente: podés pasar a un plan mayor desde el panel, o escribirnos y sumamos minutos para ese mes.",
        ],
      },
      {
        title: "Para quién es",
        paragraphs: [
          "Para consultorios, estudios y locales con una línea (plan Mostrador), clínicas, comercios y servicios con varias (Sucursal) y organismos con mucho volumen (Red). Si ya tenés una central, consultanos cómo conectarla.",
        ],
      },
    ],
    steps: [
      { title: "Elegís el plan", text: "Con los números, los minutos y las llamadas a la vez que necesitás, en pesos." },
      { title: "Armamos el agente con vos", text: "Le definimos las reglas y la voz, y se asigna al número que atiende." },
      { title: "Empieza a atender", text: "Entrantes y salientes, con la transcripción y los datos de cada llamada en el panel." },
    ],
    features: [
      { title: "Numeración argentina", text: "Regional, 0800 y 0810." },
      { title: "Entrantes y salientes", text: "El agente atiende y también llama." },
      { title: "El equipo también llama y atiende", text: "Desde el panel, con el número de la empresa, y todo grabado.", href: "/plataforma/telefono-del-equipo", link: "Ver el teléfono del equipo" },
      { title: "Varias llamadas a la vez", text: "Una, tres o las que necesites, según el plan." },
      { title: "Minutos incluidos", text: "Por mes, entre las llamadas que entran y las que hacen el agente o tu equipo." },
      { title: "Campañas de llamadas", text: "En los planes Sucursal y Red." },
      { title: "Tu línea o tu central", text: "Corre sobre SIP. Si tenés central o proveedor SIP propio, consultanos." },
      { title: "El resultado de cada llamada", text: "Transcripción y datos tomados, en el panel y en tu sistema." },
    ],
    pricingFree: false,
    faq: [
      { q: "¿Qué numeración tienen?", a: "Numeración regional argentina, 0800 y 0810." },
      {
        q: "¿Puedo usar mi número o mi central telefónica?",
        a: "La plataforma corre sobre SIP. Si tenés una central (PBX) o un proveedor SIP propio, consultanos: hoy lo armamos con vos, no se activa solo desde el panel.",
      },
      {
        q: "¿Tengo que contratar telefonía aparte?",
        a: "No. El número argentino, los minutos, las llamadas a la vez y la inteligencia artificial vienen en el plan. Lo contratás y empieza a atender.",
      },
      {
        q: "¿El agente puede llamar a mis clientes?",
        a: "Sí. Hace llamadas salientes para confirmar, recordar o cobrar. Los planes Sucursal y Red suman campañas de llamadas: a una lista de contactos, en el horario que elijas y con reintentos.",
      },
      {
        q: "¿Cómo se cuentan los minutos?",
        a: "Cada llamada se cuenta por minuto iniciado. Los minutos del plan son por mes y no se acumulan: suman las llamadas que entran y las que hace el agente.",
      },
      {
        q: "¿Qué pasa si me paso de los minutos?",
        a: "Al llegar al tope del plan, el agente deja de atender hasta el mes siguiente. Podés pasar a un plan mayor desde el panel, o escribinos y te sumamos minutos para ese mes.",
      },
    ],
    serviceType: "Telefonía con agentes de inteligencia artificial",
    cta: {
      subject: "Consulta sobre la telefonía de Atentina",
      question: "¿Qué línea o central tenés hoy?",
      placeholder: "Por ejemplo: un 0800 y una central con proveedor SIP propio",
    },
  },
  {
    slug: "telefono-del-equipo",
    title: "Teléfono del equipo",
    summary: "Tu equipo llama y atiende desde el navegador con el número de la empresa. Todo grabado y transcripto junto con las llamadas del agente.",
    metaTitle: "Teléfono del equipo: llamá y atendé desde el navegador | Atentina",
    metaDescription:
      "Tu equipo llama a los contactos y atiende las entrantes desde el panel, con el número de la empresa. Cada número lo atiende el equipo o el agente, y las llamadas del equipo quedan grabadas y transcriptas.",
    ogDescription: "Tu equipo llama y atiende desde el navegador, con el número de la empresa.",
    eyebrow: "Teléfono del equipo",
    headline: "Tu equipo llama y atiende con el número de la empresa",
    highlight: "con el número de la empresa",
    lead: "Las personas de tu equipo llaman a tus contactos y atienden las entrantes desde el navegador, sin agente de por medio. Cada número lo atiende el equipo o el agente, y las llamadas del equipo quedan grabadas y transcriptas en el mismo historial que las del agente.",
    facts: ["Desde el navegador", "Atiende el equipo o el agente", "Todo grabado y transcripto", "Planes Mostrador, Sucursal y Red"],
    hero: "phone",
    sections: [
      {
        title: "Llamar desde el panel",
        paragraphs: [
          "En la pantalla Teléfono elegís un contacto de tu agenda, o marcás un número, y apretás Llamar. Hablás desde el navegador, con el micrófono y el parlante de tu computadora, y quien recibe la llamada ve el número de tu empresa. El panel muestra cómo va: llamando, sonando, en curso. Mientras hablás podés seguir navegando el panel, y si recargás la página volvés a entrar a la llamada.",
          "Si tenés varios números, elegís desde cuál sale cada llamada. Si el contacto pidió no recibir llamadas, el panel te lo avisa y tenés que confirmar que querés llamarlo; queda registrado en la llamada. Los números bloqueados no se pueden llamar.",
        ],
      },
      {
        title: "Entrantes: el equipo o el agente, número por número",
        paragraphs: [
          "Cada número de tu cuenta se configura para que lo atienda el equipo o el agente. Con el equipo, suena a las personas que asignaste a ese número, sin agente. Con el agente, atiende como siempre y puede pasar la llamada a una persona cuando hace falta. Así podés dejar el 0800 de reclamos con el agente y la línea de ventas con tu gente.",
        ],
      },
      {
        title: "A quién le suena, en qué orden y qué pasa si nadie atiende",
        paragraphs: [
          "Elegís las personas y el orden en que suenan, cuántos segundos suena cada una y el horario de atención. Elegís también dónde suena primero: en el celular de cada persona (por defecto) o en el panel, y si nadie atiende, pasa al otro. En el celular, la persona escucha de qué línea es la llamada y marca 1 para atender.",
          "Si nadie atiende o es fuera de horario, decidís el respaldo: que siga el agente del número, que quien llama deje un mensaje (queda grabado y transcripto) o que escuche un aviso y se corte.",
        ],
      },
      {
        title: "Disponible para atender",
        paragraphs: [
          "Cada persona tiene un interruptor Disponible en el panel. Mientras está prendido y el panel está abierto, le suenan las entrantes del número con los botones Atender y Rechazar, el número que llama y el contacto si está en tu agenda. La primera persona que atiende se queda con la llamada y a las demás se les corta el timbre. Atender en el panel no gasta minutos salientes.",
        ],
      },
      {
        title: "Todo grabado y transcripto",
        paragraphs: [
          "Las llamadas del equipo se graban y se transcriben siempre. Quedan en Conversaciones junto a las del agente, con la transcripción, el audio de cada mensaje, la duración, el resultado y quién llamó o atendió. Los reportes las cuentan aparte, por tipo y por persona. Por API las filtrás de la misma forma, y también las lanzás, por ejemplo desde tu CRM.",
          "Podés prender un aviso automático, «Esta llamada está siendo grabada», al empezar las llamadas. Informar a quien habla y tener su consentimiento es responsabilidad de tu empresa, como dicen las condiciones del servicio.",
        ],
      },
      {
        title: "Qué esperar",
        paragraphs: [
          "No hay una app de celular: para llamar o atender desde el panel, la pestaña tiene que estar abierta en el navegador, de la computadora o del celular. Para atender sin el panel, la llamada suena en el celular de cada persona, como una llamada común. Las llamadas del equipo gastan los minutos del plan y ocupan una de las llamadas a la vez, igual que las del agente.",
        ],
      },
    ],
    steps: [
      { title: "Cargás a tu equipo", text: "Cada persona con su celular, su usuario del panel o los dos." },
      { title: "Elegís quién atiende cada número", text: "El equipo o el agente, el orden, el horario y el respaldo." },
      { title: "Llaman y atienden", text: "Desde el navegador, con el número de la empresa. Todo queda grabado y transcripto en el panel." },
    ],
    features: [
      { title: "Llamar desde el navegador", text: "Con el micrófono y el parlante de tu computadora, desde el número de la empresa." },
      { title: "Tu agenda de contactos", text: "Elegís a quién llamar, con aviso si pidió no recibir llamadas." },
      { title: "El equipo o el agente, por número", text: "Cada número lo atiende quien vos elijas." },
      { title: "Orden, celular o panel primero, horario y respaldo", text: "El agente, un mensaje o cortar si nadie atiende." },
      { title: "Disponible para atender", text: "Atender o rechazar desde el panel; la primera persona que atiende se queda con la llamada." },
      { title: "Grabada y transcripta", text: "En el mismo historial que las llamadas del agente, con el audio de cada mensaje." },
      { title: "En todos los planes pagos", text: "Mostrador, Sucursal y Red. El plan Free no la incluye." },
    ],
    pricingFree: false,
    faq: [
      {
        q: "¿Necesito instalar una app o comprar teléfonos?",
        a: "No. Se llama y se atiende desde el panel, en el navegador. No hay una app de celular: la pestaña tiene que estar abierta. Si preferís atender en el celular, la llamada suena en el celular de cada persona.",
      },
      {
        q: "¿Se graban las llamadas del equipo?",
        a: "Sí, siempre, y se transcriben. Quedan en Conversaciones con el audio de cada mensaje. Podés prender un aviso que dice «Esta llamada está siendo grabada»; informar y tener el consentimiento de quien habla es responsabilidad de tu empresa.",
      },
      {
        q: "¿Qué pasa si nadie del equipo atiende?",
        a: "Elegís el respaldo para cada número: que siga el agente, que quien llama deje un mensaje o que escuche un aviso y se corte. Lo mismo vale fuera del horario que definas.",
      },
      {
        q: "¿Puedo llamar a alguien que pidió que no lo llamen?",
        a: "El panel te avisa y tenés que confirmarlo. Queda registrado en la llamada. Cumplir con el Registro Nacional No Llame y con quien pidió la baja es responsabilidad de tu empresa.",
      },
      {
        q: "¿Cuánto cuesta?",
        a: "Viene en los planes Mostrador, Sucursal y Red, sin costo aparte. Las llamadas gastan los minutos del plan, igual que las del agente. El plan Free no la incluye.",
      },
      {
        q: "¿Se puede lanzar una llamada desde mi CRM?",
        a: "Sí, por API: indicás el contacto y la persona que va a hablar, y te devuelve un link que esa persona abre para entrar a la llamada con su sesión. También lo puede hacer tu agente de IA por MCP.",
      },
      {
        q: "¿El agente y el equipo pueden convivir?",
        a: "Sí. Elegís por número quién atiende. Un número con agente puede pasar la llamada a una persona (derivación), y uno con el equipo puede pasar al agente si nadie atiende.",
      },
    ],
    serviceType: "Teléfono para equipos de atención, con grabación y transcripción",
    cta: {
      subject: "Consulta sobre el teléfono del equipo de Atentina",
      question: "¿Quiénes atenderían y desde qué números?",
      placeholder: "Por ejemplo: tres vendedoras que atienden la línea de ventas y llaman a sus clientes",
    },
  },
];
