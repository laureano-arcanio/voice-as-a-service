export type IconName = "calendar" | "money" | "chat";

export interface DemoAgent {
  slug: string;
  title: string;
  summary: string;
  icon: IconName;
}

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
      "<b>300 minutos</b> por mes",
      "<b>1 llamada</b> a la vez",
      "1 número",
      "Minuto adicional <b class=\"tabular-nums\">$ 99</b>",
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
      "<b>1.200 minutos</b> por mes",
      "<b>5 llamadas</b> a la vez",
      "1 número",
      "Llamadas programadas",
      "Minuto adicional <b class=\"tabular-nums\">$ 79</b>",
    ],
    cta: "Empezar",
    featured: true,
  },
  {
    name: "Central",
    for: "Empresas medianas y municipios.",
    price: "$ 399.000",
    per: "por mes",
    usd: "unos USD 258",
    items: [
      "<b>5.000 minutos</b> por mes",
      "<b>10 llamadas</b> a la vez",
      "1 número",
      "Llamadas programadas",
      "Minuto adicional <b class=\"tabular-nums\">$ 69</b>",
    ],
    cta: "Empezar",
  },
  {
    name: "Red",
    for: "Organismos con mucho volumen.",
    price: "A medida",
    usd: "Lo cotizamos según tu volumen",
    items: [
      "<b>Más de 5.000 minutos</b> por mes",
      "<b>Las llamadas</b> a la vez que necesites",
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
