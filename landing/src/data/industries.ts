// Páginas por industria y otros usos (`/casos-de-uso/<slug>`, docs/features/LANDING.md): base para posicionar por
// búsqueda y sumar contenido. Las industrias cuentan lo que la plataforma hace hoy; "otros usos" incluye la traducción
// en tiempo real, que se ofrece mientras se termina (pedido del usuario, 30-oct-2026).
import type { Feature, Qa, SampleField, Step, Vertical } from "./site";

export interface Industry {
  slug:
    | "automotriz"
    | "educacion"
    | "inmobiliario"
    | "retail"
    | "salud"
    | "seguros"
    | "servicios"
    | "traduccion-en-tiempo-real"
    | "creadores-de-contenido"
    | "transcripcion-de-llamadas";
  /** Industria (menú "Por industria") u otro uso de la plataforma ("Otros usos"). */
  group: "industria" | "uso";
  /** Nombre en el menú y en el rótulo. */
  name: string;
  /** Una línea en el menú desplegable y en las tarjetas. */
  short: string;
  who: string;
  metaTitle: string;
  metaDescription: string;
  /** H1: el término de búsqueda de la página (sin "agente de voz", que va solo en `metaTitle`). */
  h1: string;
  /** Bajada destacada debajo del H1: el beneficio. */
  headline: string;
  lead: string;
  /** Qué hace el agente en el rubro. */
  uses: Feature[];
  steps: Step[];
  sample: { agent: string; outcome: string; duration: string; fields: SampleField[] };
  voiceLine: { f: string; m: string };
  defaultVoice: string;
  /** Agente de la demo (`agents` en site.ts); sin él, la portada ofrece pedir una demo y escuchar las voces. */
  agent?: string;
  /** Páginas por necesidad que aplican al rubro. */
  related: Vertical["slug"][];
  faq: Qa[];
}

export const industries: Industry[] = [
  {
    slug: "automotriz",
    group: "industria",
    name: "Automotriz",
    short: "Concesionarias y talleres",
    who: "Concesionarias · Talleres · Agencias de usados",
    metaTitle: "Agente de voz con IA para concesionarias y talleres | Atentina",
    metaDescription:
      "Un agente de voz con IA que atiende las llamadas de tu concesionaria: stock, precios y financiación, test drive y turnos de service. Por teléfono y WhatsApp.",
    h1: "Agentes con IA para concesionarias y talleres",
    headline: "Tu concesionaria atiende cada llamada, también fuera de horario",
    lead: "El agente responde por modelos, stock y financiación, agenda el test drive o el turno del taller y le pasa al vendedor los interesados listos para cerrar.",
    uses: [
      { title: "Stock, precios y financiación", text: "Responde por modelo, versión, colores y planes con la información de tu concesionaria." },
      { title: "Test drive", text: "Ofrece los horarios libres, agenda la prueba de manejo y la recuerda el día anterior." },
      { title: "Turnos de service y taller", text: "Toma patente, kilometraje y el problema, y da el turno en tu agenda." },
      { title: "Interesados de portales y redes", text: "Llama en minutos a quien dejó sus datos, lo califica y lo deriva al vendedor." },
      { title: "Recordatorio de service", text: "Campañas de llamadas a clientes con el service por vencer." },
      { title: "Derivación al vendedor", text: "Si el cliente quiere cerrar, le pasa la llamada a tu equipo, en tu orden y horario.", href: "/plataforma/telefono-del-equipo", link: "Ver derivaciones" },
    ],
    steps: [
      { title: "Atiende y entiende", text: "Venta, usado, plan de ahorro o taller: sin menús de opciones." },
      { title: "Consulta tu sistema", text: "Stock y agenda del taller durante la llamada, por API." },
      { title: "Agenda o deriva", text: "Deja el test drive o el turno, o le pasa la llamada al vendedor." },
    ],
    sample: {
      agent: "Lucas · Autos del Sur",
      outcome: "Test drive agendado",
      duration: "2:10",
      fields: [
        { label: "Modelo", value: "SUV 1.3 turbo, versión full" },
        { label: "Forma de pago", value: "Financiado, con usado" },
        { label: "Usado", value: "Hatchback 2019, 60.000 km" },
        { label: "Test drive", value: "Sábado 11:00" },
        { label: "Cliente", value: "Martín Gómez" },
      ],
    },
    voiceLine: {
      f: "Hola, soy {nombre}, la asistente virtual de la concesionaria. Te llamo para confirmar tu prueba de manejo del sábado a las once.",
      m: "Hola, soy {nombre}, el asistente virtual de la concesionaria. Te llamo para confirmar tu prueba de manejo del sábado a las once.",
    },
    defaultVoice: "lucas",
    agent: "turnos",
    related: ["turnos"],
    faq: [
      { q: "¿El agente puede informar precios y stock reales?", a: "Sí. Responde con la información que cargás o consulta tu sistema de stock por API durante la llamada, así no dice un precio viejo." },
      { q: "¿Puede dar turnos para el taller?", a: "Sí. Toma patente, kilometraje y el motivo, ofrece los horarios libres de tu agenda y deja el turno registrado." },
      { q: "¿Qué pasa cuando el cliente quiere hablar con un vendedor?", a: "Le pasa la llamada a tu equipo, en el orden y el horario que elijas. Si nadie atiende, toma el mensaje y avisa." },
      { q: "¿Sirve para llamar a los interesados que dejan sus datos en la web?", a: "Sí. Tu sistema pide la llamada por API y el agente llama en minutos, califica al interesado y lo deriva." },
    ],
  },
  {
    slug: "educacion",
    group: "industria",
    name: "Educación",
    short: "Institutos, colegios y universidades",
    who: "Institutos · Colegios · Universidades · Academias",
    metaTitle: "Agente de voz con IA para institutos y colegios | Atentina",
    metaDescription:
      "Un agente de voz con IA que responde informes de carreras y cursos, toma inscripciones y recuerda cuotas. Para institutos, colegios, universidades y academias.",
    h1: "Agentes con IA para institutos, colegios y universidades",
    headline: "Cada interesado recibe sus informes en el momento, aunque llame de noche",
    lead: "El agente responde por carreras, cursos, horarios y aranceles, toma los datos del interesado, lo llama para seguir la inscripción y recuerda las cuotas por vencer.",
    uses: [
      { title: "Informes de carreras y cursos", text: "Duración, modalidad, horarios, requisitos y aranceles, con tu información." },
      { title: "Inscripción", text: "Toma los datos del interesado y le envía el formulario o el link de pago por WhatsApp.", href: "/plataforma/whatsapp", link: "Ver WhatsApp con IA" },
      { title: "Seguimiento de interesados", text: "Llama a quien pidió informes y no se inscribió, antes de que empiece la cursada." },
      { title: "Cuotas y vencimientos", text: "Recuerda la cuota por vencer y registra cuándo va a pagar.", href: "/casos-de-uso/cobranzas", link: "Ver cobranzas" },
      { title: "Avisos a familias y alumnos", text: "Campañas de llamadas para reuniones, cambios de horario o fechas de examen." },
    ],
    steps: [
      { title: "Responde la consulta", text: "Carrera, curso o trámite, con la información que vos cargás." },
      { title: "Toma los datos", text: "Nombre, contacto y la carrera de interés, de a uno." },
      { title: "Sigue al interesado", text: "Lo vuelve a llamar o le escribe hasta que se inscribe." },
    ],
    sample: {
      agent: "Carolina · Instituto Horizonte",
      outcome: "Interesado en inscripción",
      duration: "1:55",
      fields: [
        { label: "Carrera", value: "Diseño gráfico" },
        { label: "Modalidad", value: "Virtual, turno noche" },
        { label: "Interesada", value: "Lucía Fernández" },
        { label: "Teléfono", value: "1155552211" },
        { label: "Próximo paso", value: "Link de inscripción por WhatsApp" },
      ],
    },
    voiceLine: {
      f: "Hola, soy {nombre}, la asistente virtual del instituto. Te llamo porque pediste informes de la carrera de diseño gráfico.",
      m: "Hola, soy {nombre}, el asistente virtual del instituto. Te llamo porque pediste informes de la carrera de diseño gráfico.",
    },
    defaultVoice: "carolina",
    agent: "reclamos",
    related: ["cobranzas"],
    faq: [
      { q: "¿El agente sabe los aranceles y horarios de mi institución?", a: "Sí. Responde con la información que cargás en su base de conocimiento y la actualizás cuando cambia." },
      { q: "¿Puede inscribir a un alumno?", a: "Toma los datos y le envía el formulario o el link de pago por WhatsApp. Si tenés un sistema de gestión, los carga por API." },
      { q: "¿Sirve para recordar las cuotas?", a: "Sí. Con una campaña llama a quienes tienen la cuota por vencer o vencida y registra cuándo van a pagar." },
      { q: "¿Atiende en época de inscripciones, cuando entran muchas llamadas?", a: "Sí. Atiende varias llamadas a la vez y nadie queda esperando en línea." },
    ],
  },
  {
    slug: "inmobiliario",
    group: "industria",
    name: "Inmobiliario",
    short: "Inmobiliarias y desarrolladoras",
    who: "Inmobiliarias · Desarrolladoras · Administraciones",
    metaTitle: "Agente de voz con IA para inmobiliarias | Atentina",
    metaDescription:
      "Un agente de voz con IA que atiende a los interesados de tu inmobiliaria: califica por zona y presupuesto, coordina visitas y deriva al corredor. Por teléfono y WhatsApp.",
    h1: "Agentes con IA para inmobiliarias",
    headline: "Cada interesado en una propiedad recibe respuesta, no un teléfono que suena",
    lead: "El agente responde por las propiedades, califica al interesado por zona, presupuesto y operación, coordina la visita y le pasa al corredor los que están listos.",
    uses: [
      { title: "Consultas por propiedades", text: "Precio, expensas, ambientes, ubicación y requisitos de alquiler, con tus datos." },
      { title: "Calificación del interesado", text: "Operación, zona, presupuesto y si necesita vender para comprar." },
      { title: "Visitas", text: "Ofrece horarios, agenda la visita y la confirma el día anterior." },
      { title: "Interesados de portales", text: "Llama en minutos a quien consultó en un portal y lo califica." },
      { title: "Inquilinos y propietarios", text: "Reclamos de mantenimiento con dirección y detalle, y recordatorio de vencimientos." },
      { title: "Derivación al corredor", text: "Si quiere ofertar, le pasa la llamada al corredor de esa propiedad.", href: "/plataforma/telefono-del-equipo", link: "Ver derivaciones" },
    ],
    steps: [
      { title: "Atiende la consulta", text: "Identifica la propiedad y responde con tu información." },
      { title: "Califica", text: "Operación, zona, presupuesto y plazo, en una charla natural." },
      { title: "Agenda o deriva", text: "Deja la visita en la agenda o le pasa la llamada al corredor." },
    ],
    sample: {
      agent: "Paula · Propiedades Norte",
      outcome: "Visita agendada",
      duration: "2:24",
      fields: [
        { label: "Operación", value: "Compra" },
        { label: "Propiedad", value: "3 ambientes, Villa Urquiza" },
        { label: "Presupuesto", value: "Hasta USD 140.000" },
        { label: "Visita", value: "Jueves 18:00" },
        { label: "Interesado", value: "Diego Sosa" },
      ],
    },
    voiceLine: {
      f: "Hola, soy {nombre}, la asistente virtual de la inmobiliaria. Te llamo por tu consulta sobre el tres ambientes en Villa Urquiza.",
      m: "Hola, soy {nombre}, el asistente virtual de la inmobiliaria. Te llamo por tu consulta sobre el tres ambientes en Villa Urquiza.",
    },
    defaultVoice: "paula",
    agent: "turnos",
    related: ["turnos", "municipios"],
    faq: [
      { q: "¿El agente conoce las propiedades que tengo publicadas?", a: "Sí. Responde con la información que cargás o consulta tu sistema por API durante la llamada." },
      { q: "¿Puede coordinar visitas?", a: "Sí. Ofrece los horarios disponibles, agenda la visita y llama el día anterior para confirmarla." },
      { q: "¿Cómo sé qué interesados valen la pena?", a: "Cada llamada termina con operación, zona, presupuesto y plazo registrados, en el panel o en tu sistema." },
      { q: "¿Atiende a inquilinos con reclamos?", a: "Sí. Toma el reclamo con dirección y detalle, y lo envía a quien lo resuelve." },
    ],
  },
  {
    slug: "retail",
    group: "industria",
    name: "Retail",
    short: "Comercios y tiendas online",
    who: "Comercios · Cadenas · Tiendas online",
    metaTitle: "Agente de voz con IA para comercios y tiendas online | Atentina",
    metaDescription:
      "Un agente de voz con IA que atiende a tus clientes: estado del pedido, stock, horarios de sucursales, cambios y devoluciones. Por teléfono y WhatsApp.",
    h1: "Agentes con IA para comercios y tiendas online",
    headline: "Tus clientes saben dónde está su pedido sin esperar en línea",
    lead: "El agente consulta el estado del pedido en tu sistema, responde por stock, sucursales y horarios, y gestiona cambios y devoluciones con tu política.",
    uses: [
      { title: "Estado del pedido", text: "Consulta tu sistema con el número de pedido o el DNI, durante la llamada." },
      { title: "Stock y sucursales", text: "Disponibilidad, horarios y direcciones, con tu información al día." },
      { title: "Cambios y devoluciones", text: "Explica tu política, toma los datos y registra la gestión." },
      { title: "Pedidos por teléfono", text: "Toma el pedido y envía el link de pago por WhatsApp.", href: "/plataforma/whatsapp", link: "Ver WhatsApp con IA" },
      { title: "Reclamos", text: "Registra cada reclamo con número y lo deriva al área.", href: "/casos-de-uso/municipios", link: "Ver reclamos" },
    ],
    steps: [
      { title: "Identifica al cliente", text: "Número de pedido, DNI o teléfono." },
      { title: "Consulta tu sistema", text: "Estado, stock o factura, por API durante la llamada." },
      { title: "Resuelve o registra", text: "Responde, gestiona el cambio o deriva el reclamo." },
    ],
    sample: {
      agent: "Valentina · Casa Bonita",
      outcome: "Cambio registrado",
      duration: "1:36",
      fields: [
        { label: "Pedido", value: "48213" },
        { label: "Gestión", value: "Cambio de talle" },
        { label: "Producto", value: "Zapatillas urbanas, 39 por 40" },
        { label: "Retiro", value: "Sucursal Palermo" },
        { label: "Cliente", value: "Sofía Ruiz" },
      ],
    },
    voiceLine: {
      f: "Hola, soy {nombre}, la asistente virtual de la tienda. Te llamo para avisarte que tu pedido ya está listo para retirar.",
      m: "Hola, soy {nombre}, el asistente virtual de la tienda. Te llamo para avisarte que tu pedido ya está listo para retirar.",
    },
    defaultVoice: "valentina",
    agent: "reclamos",
    related: ["municipios", "cobranzas"],
    faq: [
      { q: "¿El agente puede decir dónde está un pedido?", a: "Sí. Consulta tu sistema o tu plataforma de e-commerce por API durante la llamada y responde con el estado real." },
      { q: "¿Puede tomar pedidos por teléfono?", a: "Sí. Toma el pedido y envía el link de pago por WhatsApp para cerrarlo." },
      { q: "¿Qué pasa en temporada alta, cuando se llena de llamadas?", a: "El agente atiende varias llamadas a la vez; los planes dicen cuántas." },
      { q: "¿Responde también por WhatsApp?", a: "Sí. El mismo agente atiende por teléfono y por WhatsApp, con texto y notas de voz." },
    ],
  },
  {
    slug: "salud",
    group: "industria",
    name: "Salud",
    short: "Clínicas y consultorios",
    who: "Clínicas · Consultorios · Centros de diagnóstico",
    metaTitle: "Agente de voz con IA para clínicas y consultorios | Atentina",
    metaDescription:
      "Un agente de voz con IA que da turnos las 24 horas, confirma el día anterior y responde a los pacientes. Para clínicas, consultorios y centros de diagnóstico.",
    h1: "Agentes con IA para clínicas y consultorios",
    headline: "Tus pacientes sacan turno a cualquier hora, sin esperar en línea",
    lead: "El agente da turnos con tu agenda, toma los datos y la cobertura, confirma el día anterior y responde cómo prepararse para cada estudio.",
    uses: [
      { title: "Turnos las 24 horas", text: "Especialidad, profesional y horario, reservado en tu sistema de turnos.", href: "/casos-de-uso/turnos", link: "Ver turnos y recordatorios" },
      { title: "Confirmación el día anterior", text: "Llama, confirma y, si el paciente no puede, reprograma y libera el horario." },
      { title: "Obra social y datos", text: "Toma nombre, DNI y cobertura, y los repite para no errar." },
      { title: "Preparación de estudios", text: "Ayuno, qué llevar y a qué sede ir, con tus indicaciones." },
      { title: "Derivación a la recepción", text: "Si el caso lo necesita, le pasa la llamada a una persona.", href: "/plataforma/telefono-del-equipo", link: "Ver derivaciones" },
    ],
    steps: [
      { title: "Atiende y da el turno", text: "Pregunta la especialidad y ofrece los horarios libres." },
      { title: "Toma los datos", text: "Nombre, DNI y obra social, repetidos para no errar." },
      { title: "Recuerda y reprograma", text: "Llama el día anterior y libera el horario si no puede ir." },
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
        { label: "Cobertura", value: "Prepaga" },
      ],
    },
    voiceLine: {
      f: "Hola, soy {nombre}, la asistente virtual de la clínica. Te llamo para confirmar tu turno de mañana a las diez.",
      m: "Hola, soy {nombre}, el asistente virtual de la clínica. Te llamo para confirmar tu turno de mañana a las diez.",
    },
    defaultVoice: "sofia",
    agent: "turnos",
    related: ["turnos"],
    faq: [
      { q: "¿El agente puede dar turnos en mi sistema?", a: "Sí. Consulta los horarios libres y reserva el turno por API durante la llamada." },
      { q: "¿Sirve para bajar el ausentismo?", a: "Sí. Llama el día anterior para confirmar y, si el paciente no puede, reprograma en la misma llamada y libera el horario." },
      { q: "¿Da información médica?", a: "No. Responde lo administrativo (turnos, sedes, preparación de estudios con tus indicaciones) y deriva a una persona lo que no le corresponde." },
      { q: "¿Qué pasa con los datos de los pacientes?", a: "La inteligencia artificial corre en nuestros servidores propios, en Argentina. Cada conversación queda en tu panel y solo la ve tu equipo." },
    ],
  },
  {
    slug: "seguros",
    group: "industria",
    name: "Seguros",
    short: "Productores y aseguradoras",
    who: "Productores · Brokers · Aseguradoras",
    metaTitle: "Agente de voz con IA para productores y aseguradoras | Atentina",
    metaDescription:
      "Un agente de voz con IA que toma los datos para cotizar, recibe el primer aviso de siniestro y responde por pólizas y cuotas. Para productores, brokers y aseguradoras.",
    h1: "Agentes con IA para productores y aseguradoras",
    headline: "Cada asegurado tiene respuesta, también cuando el siniestro es un sábado",
    lead: "El agente toma los datos para cotizar, recibe el primer aviso de un siniestro, responde por pólizas y cuotas, y le pasa al productor lo que necesita una persona.",
    uses: [
      { title: "Datos para cotizar", text: "Vehículo, hogar o vida: toma lo que tu cotizador necesita y lo envía por API." },
      { title: "Primer aviso de siniestro", text: "Fecha, lugar, qué pasó y datos de terceros, registrados en orden." },
      { title: "Pólizas y coberturas", text: "Vigencia, qué cubre y cómo pedir la tarjeta o el certificado." },
      { title: "Cuotas y renovaciones", text: "Recuerda cuotas vencidas y renovaciones por vencer.", href: "/casos-de-uso/cobranzas", link: "Ver cobranzas" },
      { title: "Derivación al productor", text: "Si el asegurado lo pide, le pasa la llamada a tu equipo.", href: "/plataforma/telefono-del-equipo", link: "Ver derivaciones" },
    ],
    steps: [
      { title: "Identifica al asegurado", text: "DNI, póliza o patente." },
      { title: "Toma el caso", text: "Cotización, siniestro o consulta, con todos los datos." },
      { title: "Registra y deriva", text: "Lo envía a tu sistema o le pasa la llamada al productor." },
    ],
    sample: {
      agent: "Gonzalo · Seguros del Plata",
      outcome: "Siniestro registrado",
      duration: "3:02",
      fields: [
        { label: "Póliza", value: "Auto 77821" },
        { label: "Tipo", value: "Choque sin lesionados" },
        { label: "Fecha y lugar", value: "Hoy 9:40, Av. Rivadavia 5200" },
        { label: "Tercero", value: "Patente AB123CD" },
        { label: "Asegurado", value: "Federico Díaz" },
      ],
    },
    voiceLine: {
      f: "Hola, soy {nombre}, la asistente virtual de tu productor de seguros. Te llamo porque tu póliza vence el próximo lunes.",
      m: "Hola, soy {nombre}, el asistente virtual de tu productor de seguros. Te llamo porque tu póliza vence el próximo lunes.",
    },
    defaultVoice: "gonzalo",
    agent: "reclamos",
    related: ["cobranzas", "municipios"],
    faq: [
      { q: "¿El agente puede cotizar un seguro?", a: "Toma los datos que tu cotizador necesita y los envía por API; si tu sistema devuelve el precio, lo informa en la llamada." },
      { q: "¿Puede recibir la denuncia de un siniestro?", a: "Recibe el primer aviso con fecha, lugar, qué pasó y datos de terceros, y lo deja registrado para tu equipo." },
      { q: "¿Sirve para cobrar cuotas vencidas?", a: "Sí. Con una campaña llama a los asegurados con cuotas vencidas y registra cuándo van a pagar." },
      { q: "¿Atiende fuera del horario de la oficina?", a: "Sí. Atiende las 24 horas y deja todo registrado para el día hábil siguiente." },
    ],
  },
  {
    slug: "servicios",
    group: "industria",
    name: "Servicios",
    short: "Internet, servicio técnico y más",
    who: "Internet y cable · Servicio técnico · Gimnasios · Estudios profesionales",
    metaTitle: "Agente de voz con IA para empresas de servicios | Atentina",
    metaDescription:
      "Un agente de voz con IA para empresas de servicios: soporte de primer nivel, visitas técnicas, facturación y reclamos. Por teléfono y WhatsApp.",
    h1: "Agentes con IA para empresas de servicios",
    headline: "Tus clientes resuelven lo de siempre sin esperar a un operador",
    lead: "El agente hace el soporte de primer nivel, agenda visitas técnicas, responde por facturas y planes, y registra cada reclamo con número para tu equipo.",
    uses: [
      { title: "Soporte de primer nivel", text: "Los pasos de siempre (reiniciar, revisar la conexión) antes de abrir un reclamo." },
      { title: "Visitas técnicas", text: "Toma dirección y problema, y agenda la visita en tu sistema." },
      { title: "Facturación y planes", text: "Saldo, vencimientos y cambio de plan, consultando tu gestión." },
      { title: "Reclamos con número", text: "Registra cada reclamo y le envía el número al cliente.", href: "/casos-de-uso/municipios", link: "Ver reclamos" },
      { title: "Cobranza de facturas vencidas", text: "Llama a los clientes en mora y registra la promesa de pago.", href: "/casos-de-uso/cobranzas", link: "Ver cobranzas" },
    ],
    steps: [
      { title: "Identifica al cliente", text: "Número de cliente, DNI o dirección." },
      { title: "Resuelve lo simple", text: "Responde o guía los pasos de primer nivel." },
      { title: "Agenda o registra", text: "Visita técnica, reclamo con número o derivación a tu equipo." },
    ],
    sample: {
      agent: "Martín · Fibranet",
      outcome: "Visita técnica agendada",
      duration: "2:38",
      fields: [
        { label: "Cliente", value: "10293" },
        { label: "Problema", value: "Sin conexión desde ayer" },
        { label: "Primer nivel", value: "Reinició el módem, sigue igual" },
        { label: "Visita", value: "Miércoles de 9 a 13" },
        { label: "Reclamo", value: "R-58211" },
      ],
    },
    voiceLine: {
      f: "Hola, soy {nombre}, la asistente virtual de Fibranet. Te llamo para confirmar la visita técnica del miércoles por la mañana.",
      m: "Hola, soy {nombre}, el asistente virtual de Fibranet. Te llamo para confirmar la visita técnica del miércoles por la mañana.",
    },
    defaultVoice: "martin",
    agent: "reclamos",
    related: ["municipios", "cobranzas"],
    faq: [
      { q: "¿Qué tipo de empresas de servicios pueden usarlo?", a: "Proveedores de internet y cable, servicio técnico, mantenimiento, gimnasios y estudios profesionales: cualquier empresa que atienda consultas repetidas por teléfono." },
      { q: "¿El agente puede hacer soporte técnico?", a: "El de primer nivel, con los pasos que vos definís. Si no se resuelve, abre el reclamo o agenda la visita." },
      { q: "¿Se conecta con mi sistema de gestión?", a: "Sí. Consulta y escribe en tu sistema por API durante la llamada: clientes, facturas, reclamos y agenda." },
      { q: "¿Cuánto tarda en estar funcionando?", a: "Lo configuramos con vos con tus reglas y tu información; la plantilla de partida ya funciona y la ajustás desde el panel." },
    ],
  },
  {
    slug: "traduccion-en-tiempo-real",
    group: "uso",
    name: "Traducción en tiempo real",
    short: "Llamadas entre dos idiomas",
    who: "Comercio exterior · Turismo · Soporte internacional",
    metaTitle: "Traducción de llamadas en tiempo real con IA | Atentina",
    metaDescription:
      "Un intérprete con IA en tus llamadas: hablás en español y la otra persona te escucha en su idioma, y su respuesta te llega en español. Por teléfono o desde el navegador.",
    h1: "Traducción de llamadas en tiempo real con IA",
    headline: "Hablá con clientes y proveedores de otros países, cada uno en su idioma",
    lead: "El agente hace de intérprete: escucha lo que decís, lo dice en el idioma de la otra persona y te devuelve su respuesta en español, frase por frase, en la misma llamada.",
    uses: [
      { title: "Proveedores del exterior", text: "Negociá precios, plazos y envíos sin depender de un intérprete." },
      { title: "Clientes que no hablan español", text: "Atendé a turistas y clientes de otros países por teléfono." },
      { title: "Soporte internacional", text: "Tu equipo atiende en español y el cliente escucha en su idioma." },
      { title: "Transcripción de la llamada", text: "Queda lo que dijo cada uno, en los dos idiomas, en el panel." },
      { title: "Desde el navegador o por teléfono", text: "Llamás desde el panel o a un número; la traducción va en el medio.", href: "/plataforma/telefono-del-equipo", link: "Ver el teléfono del equipo" },
    ],
    steps: [
      { title: "Hacés la llamada", text: "Desde el panel o por teléfono, con el intérprete en la línea." },
      { title: "Hablás en español", text: "El agente lo dice en el idioma de la otra persona." },
      { title: "Escuchás la respuesta", text: "Lo que te contestan te llega en español, frase por frase." },
    ],
    sample: {
      agent: "Intérprete · Importadora del Río",
      outcome: "Llamada traducida",
      duration: "6:15",
      fields: [
        { label: "Idiomas", value: "Español e inglés" },
        { label: "Dijiste", value: "¿Pueden enviar la muestra el lunes?" },
        { label: "Escuchó", value: "Can you send the sample on Monday?" },
        { label: "Respondió", value: "Sí, sale el lunes por courier." },
        { label: "Transcripción", value: "En los dos idiomas" },
      ],
    },
    voiceLine: {
      f: "Hola, soy {nombre}. Voy a traducir esta llamada: hablá tranquilo, frase por frase.",
      m: "Hola, soy {nombre}. Voy a traducir esta llamada: hablá tranquilo, frase por frase.",
    },
    defaultVoice: "jimena",
    related: [],
    faq: [
      { q: "¿Cómo funciona la traducción en la llamada?", a: "El agente escucha cada frase, la traduce y la dice en el idioma de la otra persona; la respuesta te llega en español. Hay una pequeña pausa entre frase y frase." },
      { q: "¿Qué idiomas traduce?", a: "Español con inglés y portugués, para empezar. Consultanos por otros idiomas." },
      { q: "¿Queda registro de la conversación?", a: "Sí. La transcripción de lo que dijo cada uno queda en el panel, como cualquier conversación." },
      { q: "¿Necesito instalar algo?", a: "No. Llamás desde el navegador, en el panel, o por teléfono." },
    ],
  },
  {
    slug: "creadores-de-contenido",
    group: "uso",
    name: "Creadores de contenido",
    short: "Locuciones para redes y publicidad",
    who: "Creadores · Agencias · Marcas · Productoras",
    metaTitle: "Voces con IA para publicidad, Instagram y redes | Atentina",
    metaDescription:
      "Locuciones con voces argentinas generadas con IA para publicidad, Instagram, TikTok y YouTube. Escribís el texto, elegís la voz y descargás el audio. También por API.",
    h1: "Voces con IA para publicidad, Instagram y redes",
    headline: "Locuciones con voz argentina para tus videos, en segundos",
    lead: "Escribís el texto, elegís una de las voces con acento argentino y tenés el audio para tu publicidad, tu reel o tu video. Y si el guion está en otro idioma, lo traducimos y lo locutamos en español.",
    uses: [
      { title: "Publicidad", text: "Spots para radio, redes y punto de venta, con la voz que mejor va con tu marca." },
      { title: "Reels, TikTok y YouTube", text: "Narración para tus videos sin grabar ni editar tu voz." },
      { title: "Traducción de videos", text: "Pasás el guion en otro idioma y lo locutamos en español rioplatense." },
      { title: "Varias voces", text: "Diálogos con dos o más voces, femeninas y masculinas.", href: "/plataforma/voces-argentinas", link: "Escuchar las voces" },
      { title: "Por API", text: "Generá cientos de audios desde tu sistema, con una API compatible con OpenAI.", href: "/desarrolladores", link: "Ver la API" },
    ],
    steps: [
      { title: "Escribís el texto", text: "O pegás el guion en otro idioma para traducirlo." },
      { title: "Elegís la voz", text: "41 voces argentinas, cálidas, serenas, jóvenes o formales." },
      { title: "Descargás el audio", text: "Listo para tu editor de video, o por API en tu sistema." },
    ],
    sample: {
      agent: "Valentina · Tienda Bonita",
      outcome: "Audio generado",
      duration: "0:14",
      fields: [
        { label: "Uso", value: "Reel de Instagram" },
        { label: "Voz", value: "Valentina" },
        { label: "Texto", value: "Llegó la temporada de ofertas…" },
        { label: "Idioma del guion", value: "Español" },
        { label: "Formato", value: "WAV" },
      ],
    },
    voiceLine: {
      f: "Llegó la temporada de ofertas: hasta treinta por ciento en toda la tienda, solo este fin de semana.",
      m: "Llegó la temporada de ofertas: hasta treinta por ciento en toda la tienda, solo este fin de semana.",
    },
    defaultVoice: "valentina",
    related: [],
    faq: [
      { q: "¿Puedo usar los audios en publicidad?", a: "Sí. Los audios que generás son para tu contenido y tus campañas." },
      { q: "¿Cuántas voces hay?", a: "41 voces con acento argentino, 28 femeninas y 13 masculinas. Podés escucharlas todas en esta página." },
      { q: "¿Pueden traducir un video?", a: "Sí. Nos pasás el guion o el texto del video en otro idioma, lo traducimos y lo locutamos en español rioplatense con la voz que elijas." },
      { q: "¿Se puede generar en cantidad?", a: "Sí, por API: es compatible con la de OpenAI, así que tu herramienta la usa cambiando la dirección." },
    ],
  },
  {
    slug: "transcripcion-de-llamadas",
    group: "uso",
    name: "Transcripción de llamadas",
    short: "En vivo, sin agente",
    who: "Ventas · Soporte · Equipos que atienden por teléfono",
    metaTitle: "Transcripción de llamadas en vivo con IA | Atentina",
    metaDescription:
      "Tu equipo llama y atiende desde el navegador y cada llamada se transcribe en vivo, sin agente de IA en el medio. Con número argentino y las conversaciones en el panel.",
    h1: "Transcripción de llamadas en vivo con IA",
    headline: "Cada llamada de tu equipo, transcripta en vivo",
    lead: "Tu equipo llama y atiende desde el navegador, con un número argentino, y ve la transcripción mientras habla. Sin un agente con IA en el medio: solo las personas y el texto.",
    uses: [
      { title: "Transcripción en vivo", text: "El texto aparece en pantalla mientras hablan, frase por frase.", href: "/plataforma/telefono-del-equipo", link: "Ver el teléfono del equipo" },
      { title: "Llamadas entrantes y salientes", text: "Desde el navegador, con el número de tu empresa." },
      { title: "Conversaciones guardadas", text: "Cada llamada queda en el panel con quién habló y qué se dijo." },
      { title: "Control de calidad", text: "Revisá lo que se prometió y lo que se acordó, sin escuchar grabaciones." },
      { title: "Transcripción de audios por API", text: "Tus grabaciones o notas de voz a texto, desde tu sistema.", href: "/plataforma/transcripcion", link: "Ver la transcripción por API" },
    ],
    steps: [
      { title: "Llamás o atendés", text: "Desde el panel, en el navegador, con un número argentino." },
      { title: "Se transcribe en vivo", text: "Ves el texto mientras hablás, separado por persona." },
      { title: "Queda en el panel", text: "La conversación completa, para buscarla y revisarla." },
    ],
    sample: {
      agent: "Lucas · Ventas",
      outcome: "Llamada transcripta",
      duration: "4:48",
      fields: [
        { label: "Tipo", value: "Saliente, sin agente" },
        { label: "Cliente", value: "11 5555-1234" },
        { label: "Transcripción", value: "En vivo, por frase" },
        { label: "Acordaron", value: "Enviar la propuesta el jueves" },
        { label: "Dónde queda", value: "Conversaciones del panel" },
      ],
    },
    voiceLine: {
      f: "Hola, soy {nombre}, de ventas. Te llamo por la propuesta que pediste la semana pasada.",
      m: "Hola, soy {nombre}, de ventas. Te llamo por la propuesta que pediste la semana pasada.",
    },
    defaultVoice: "lucas",
    related: [],
    faq: [
      { q: "¿Hace falta un agente con IA para transcribir?", a: "No. Las llamadas de tu equipo desde el panel se transcriben en vivo sin ningún agente en la conversación." },
      { q: "¿Desde dónde se llama?", a: "Desde el navegador, en el panel, con un número argentino. No hace falta un teléfono ni una central." },
      { q: "¿Dónde quedan las transcripciones?", a: "En las conversaciones del panel, con la fecha, quién llamó y lo que dijo cada uno." },
      { q: "¿Puedo transcribir grabaciones que ya tengo?", a: "Sí, por API: subís el audio y recibís el texto en español." },
    ],
  },
];
