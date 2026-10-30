// Páginas por canal (`/canales/<slug>`, docs/features/LANDING.md): dejan claro por dónde atiende el agente, sobre
// todo WhatsApp, que se busca mucho. Resumen de lo que ya está en docs/features (WHATSAPP, EQUIPO_TELEFONIA,
// LINK_LLAMADA, HERRAMIENTAS, CAMPANAS): solo lo que está en producción.
import type { Feature, Qa, Step } from "./site";

export interface Channel {
  slug: "whatsapp" | "llamadas-telefonicas" | "llamadas-web";
  /** Nombre en el menú, las tarjetas y el rótulo. */
  name: string;
  /** Una línea en el menú y las tarjetas. */
  short: string;
  icon: "whatsapp" | "phone" | "web";
  metaTitle: string;
  metaDescription: string;
  /** H1: el término de búsqueda de la página. */
  h1: string;
  /** Bajada destacada: el beneficio. */
  headline: string;
  lead: string;
  features: Feature[];
  steps: Step[];
  faq: Qa[];
}

export const channels: Channel[] = [
  {
    slug: "whatsapp",
    name: "WhatsApp",
    short: "Mensajes, audios y llamadas",
    icon: "whatsapp",
    metaTitle: "Atención por WhatsApp con IA: mensajes, audios y llamadas | Atentina",
    metaDescription:
      "Un agente con IA atiende el WhatsApp de tu empresa: responde mensajes, entiende y contesta notas de voz, atiende llamadas de WhatsApp y le pasa la llamada a tu equipo. Todo queda transcripto.",
    h1: "Atención por WhatsApp con inteligencia artificial",
    headline: "Tu WhatsApp responde siempre: mensajes, audios y llamadas",
    lead: "El mismo agente que atiende tu teléfono atiende tu WhatsApp, con la información y las reglas de tu negocio. Contesta mensajes, escucha y responde notas de voz, atiende llamadas de WhatsApp y deja todo registrado.",
    features: [
      { title: "Mensajes de texto", text: "Responde con la información y las reglas de tu negocio, a cualquier hora." },
      { title: "Notas de voz", text: "Transcribe el audio, lo entiende y contesta. Si te mandaron un audio, responde con una nota de voz, con la voz que elegiste." },
      { title: "Llamadas de WhatsApp", text: "Las atiende el mismo agente, igual que una llamada telefónica." },
      { title: "Pasa con una persona", text: "En una llamada de WhatsApp, le pasa la llamada a tu equipo, en tu orden y tu horario.", href: "/canales/llamadas-telefonicas", link: "Ver cómo deriva" },
      { title: "Consulta tu sistema", text: "Turnos, pedidos o saldos, durante la conversación, y registra lo que acordó." },
      { title: "Todo transcripto", text: "Mensajes, audios transcriptos y llamadas quedan en el panel, en una sola conversación." },
      { title: "Campañas por WhatsApp", text: "Enviá plantillas aprobadas por Meta a tu lista; si responden, sigue el agente.", href: "/plataforma/whatsapp", link: "Ver WhatsApp con IA" },
      { title: "Un agente por contacto", text: "Ruteo por contacto: cada cliente con el agente que le corresponde." },
    ],
    steps: [
      { title: "Conectamos tu número", text: "Con la API oficial de WhatsApp de Meta, sin otro proveedor en el medio." },
      { title: "Armamos el agente", text: "Con tus reglas, tu información y la voz que elijas. Es el mismo del teléfono." },
      { title: "Atiende y deja los datos", text: "Cada conversación queda en el panel o llega a tu sistema por API o webhook." },
    ],
    faq: [
      { q: "¿Funciona con la API oficial de WhatsApp?", a: "Sí. Usamos la API oficial de WhatsApp de Meta (Cloud API), sin intermediarios. Te ayudamos a dar de alta tu número." },
      { q: "¿Entiende los audios?", a: "Sí. Transcribe las notas de voz de hasta 2 minutos, las entiende y contesta. Si el cliente mandó un audio, puede responder con una nota de voz." },
      { q: "¿Atiende llamadas de WhatsApp?", a: "Sí. El agente atiende las llamadas de WhatsApp como una llamada telefónica y puede pasarle la llamada a una persona de tu equipo." },
      { q: "¿Qué pasa cuando hace falta una persona?", a: "En una llamada, el agente le pasa la llamada a tu equipo. En los mensajes, toma los datos y la conversación queda en el panel para que tu equipo la siga." },
      { q: "¿Qué plan incluye WhatsApp?", a: "Los planes con telefonía, desde Mostrador. Las campañas por WhatsApp dependen del plan." },
    ],
  },
  {
    slug: "llamadas-telefonicas",
    name: "Llamadas telefónicas",
    short: "Atiende, consulta y deriva",
    icon: "phone",
    metaTitle: "Atención telefónica con IA: agentes que atienden y derivan llamadas | Atentina",
    metaDescription:
      "Un agente con IA atiende las llamadas de tu empresa, consulta tu sistema durante la llamada y le pasa la llamada a tu equipo, en orden o por rotación. Número argentino incluido.",
    h1: "Atención telefónica con inteligencia artificial",
    headline: "Un agente atiende tus llamadas, consulta tu sistema y te pasa lo importante",
    lead: "El agente atiende en tu número argentino o 0800, varias llamadas a la vez y a cualquier hora. Consulta y registra en tu sistema mientras habla, y cuando hace falta una persona le pasa la llamada a tu equipo.",
    features: [
      { title: "Un agente que atiende", text: "Entrantes en tu número o 0800, varias a la vez y a cualquier hora, con la voz que elijas.", href: "/plataforma/voces-argentinas", link: "Escuchar las voces" },
      { title: "Con herramientas", text: "Consulta y registra en tu sistema durante la llamada: turnos, pedidos, saldos o reclamos." },
      { title: "Derivación a tu equipo", text: "Le pasa la llamada a una persona del área, en orden o por rotación, dentro del horario que definas." },
      { title: "Espera con música y aviso", text: "El cliente escucha música mientras el agente le cuenta en pocas palabras el caso a quien atiende, que confirma con 1." },
      { title: "Si nadie atiende", text: "Vuelve con el cliente y le toma el mensaje. No se pierde ninguna llamada." },
      { title: "Llamadas salientes", text: "Confirma turnos, recuerda vencimientos y hace campañas con reintentos." },
      { title: "Tu equipo también llama", text: "Desde el navegador, con el número de la empresa y transcripción en vivo.", href: "/plataforma/telefono-del-equipo", link: "Ver el teléfono del equipo" },
      { title: "Número argentino incluido", text: "Uno nuevo o tu línea de siempre, con los minutos en el plan.", href: "/plataforma/telefonia", link: "Ver la telefonía" },
    ],
    steps: [
      { title: "Atiende la llamada", text: "Entiende qué necesita el cliente, sin menús de opciones." },
      { title: "Resuelve con tu sistema", text: "Consulta, reserva o registra mientras habla." },
      { title: "Deriva o cierra", text: "Le pasa la llamada a tu equipo o termina con todo registrado." },
    ],
    faq: [
      { q: "¿Necesito contratar telefonía aparte?", a: "No. El número argentino, los minutos y las llamadas a la vez vienen en el plan." },
      { q: "¿Cómo pasa la llamada a una persona?", a: "El agente llama a las personas del área en el orden que definas o por rotación, dentro de su horario. El cliente escucha música, quien atiende recibe un resumen y confirma con 1. Si nadie atiende, el agente vuelve y toma el mensaje." },
      { q: "¿Puede consultar mi sistema durante la llamada?", a: "Sí. Con herramientas, el agente consulta y escribe en tu sistema por API mientras habla: turnos, pedidos, deudas o reclamos." },
      { q: "¿Cuántas llamadas atiende a la vez?", a: "Varias; cuántas, según el plan." },
      { q: "¿Queda registro de cada llamada?", a: "Sí. Audio, transcripción, datos tomados y resultado de cada llamada, en el panel o en tu sistema." },
    ],
  },
  {
    slug: "llamadas-web",
    name: "Llamadas web",
    short: "Desde el navegador, con un link",
    icon: "web",
    metaTitle: "Llamadas web con IA: tus clientes hablan con tu agente desde el navegador | Atentina",
    metaDescription:
      "Un link para que tus clientes hablen con tu agente con IA desde el navegador, sin número ni app. Para tu web, Instagram o la firma de mail. Incluido en el plan gratis.",
    h1: "Llamadas web con un agente con inteligencia artificial",
    headline: "Un link y tus clientes hablan con tu agente desde el navegador",
    lead: "Compartís un link con el nombre y el logo de tu empresa, y quien lo abre habla con tu agente desde el celular o la computadora, con una pantalla de llamada. Sin número de teléfono y sin instalar nada.",
    features: [
      { title: "Link para llamar", text: "Una dirección propia para tu web, tu Instagram, la firma de mail o un código QR." },
      { title: "Sin instalar nada", text: "Se abre en el navegador, con una pantalla de llamada como la del teléfono." },
      { title: "El mismo agente", text: "Consulta tu sistema y le pasa la llamada a tu equipo, igual que por teléfono.", href: "/canales/llamadas-telefonicas", link: "Ver llamadas telefónicas" },
      { title: "Con tu marca", text: "El nombre, el logo y una bajada de tu empresa en la pantalla de llamada." },
      { title: "Topes de uso", text: "Duración máxima, llamadas a la vez y minutos por día, por link." },
      { title: "Todo transcripto", text: "Cada llamada queda en el panel con su transcripción y su resultado." },
    ],
    steps: [
      { title: "Creás el link", text: "Desde el panel, para el agente que quieras." },
      { title: "Lo compartís", text: "En tu web, tus redes, un QR o la firma de mail." },
      { title: "Te llaman desde el navegador", text: "Atiende tu agente y la llamada queda en el panel." },
    ],
    faq: [
      { q: "¿Hace falta un número de teléfono?", a: "No. El link funciona solo, desde el navegador del celular o la computadora." },
      { q: "¿Lo puedo poner en mi web?", a: "Sí, como un link o un botón. También en tu Instagram, la firma de mail o un código QR." },
      { q: "¿Está en el plan gratis?", a: "Sí. El plan Free incluye un link para llamar, con sus minutos del mes." },
      { q: "¿Consume minutos?", a: "Sí, los minutos entrantes del plan. Podés poner topes por link: duración, llamadas a la vez y minutos por día." },
    ],
  },
];
