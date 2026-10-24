// Video de la landing: un solo plano, sin locución. Tiempos en segundos.
// Ilustrativo: personas, consultas, respuestas y el contador (cuenta lo que se ve en el video, no es una medición).

export type Canal = "wa" | "phone" | "web";
export type Cliente = { nombre: string; canal: Canal; cast: "cliente" | "cliente2" | "cliente3" | "otro" | "integrador" | "mayor" };
export type Mensaje = { fila: number; q: string; r: string; qAt: number; derivada?: { titulo: string; detalle: string } };

export const W = 1920;
export const H = 1080;

// Centro: el logo con el aro de puntos
export const CX = 960;
export const CY = 540;
export const R = 190;
export const N_PUNTOS = 40;

// Tiempos del arco
export const T = {
  aroIn: 0.5, // los puntos aparecen uno por uno (0,8 s)
  logoIn: 1.1,
  palabraIn: 1.5,
  palabraOut: 3.2,
  operadorIn: 10.6,
  salida: 18.6, // se van clientes y operadora
  cierreIn: 19.2,
  cierreOut: 23.4,
  palabraFinalIn: 23.7,
  palabraFinalOut: 25.9,
  aroOut: 26.0, // los puntos se van en orden inverso
  logoOut: 26.6,
  fin: 27.6, // termina en blanco, como empieza: el loop empalma
};

export const VIAJE = 0.7; // cliente → aro y aro → cliente
export const VUELTA = 1.8; // una vuelta en el aro
export const VUELTA_EQUIPO = 1.3; // de la operadora al cliente

export const FILA_AT = [3.4, 4.2, 5.0, 5.8, 6.6, 7.4];
export const filaY = (i: number) => 120 + i * 168;

export const CLIENTES: Cliente[] = [
  { nombre: "Carolina", canal: "wa", cast: "cliente" },
  { nombre: "Martín", canal: "phone", cast: "cliente2" },
  { nombre: "Ana", canal: "web", cast: "cliente3" },
  { nombre: "Diego", canal: "wa", cast: "otro" },
  { nombre: "Javier", canal: "phone", cast: "integrador" },
  { nombre: "Jorge", canal: "phone", cast: "mayor" },
];

export const CANAL: Record<Canal, string> = { wa: "WhatsApp", phone: "Llamada", web: "Web" };

export const MENSAJES: Mensaje[] = [
  // Primera ronda: cada cliente al aparecer
  { fila: 0, q: "¿Hasta qué hora abren hoy?", r: "Hoy, hasta las 20.", qAt: FILA_AT[0] + 0.3 },
  { fila: 1, q: "Quiero un turno para el jueves.", r: "Listo, jueves a las 10:30.", qAt: FILA_AT[1] + 0.3 },
  { fila: 2, q: "¿Cuánto sale el plan mensual?", r: "$ 18.500 por mes.", qAt: FILA_AT[2] + 0.3 },
  { fila: 3, q: "¿Hacen envíos a Rosario?", r: "Sí, llegan en 48 horas.", qAt: FILA_AT[3] + 0.3 },
  {
    fila: 4, q: "Necesito 200 unidades para mi empresa.", r: "Te armo la cotización hoy.", qAt: FILA_AT[4] + 0.3,
    derivada: { titulo: "Venta grande", detalle: "Javier · 200 unidades" },
  },
  {
    fila: 5, q: "Me cobraron dos veces este mes.", r: "Lo reviso con vos ahora.", qAt: FILA_AT[5] + 0.3,
    derivada: { titulo: "Reclamo", detalle: "Jorge · cobro doble" },
  },
  // Segunda ronda: repreguntas que el agente también resuelve
  { fila: 0, q: "¿Tienen estacionamiento?", r: "Sí, en la esquina.", qAt: 11.2 },
  { fila: 1, q: "¿Qué tengo que llevar?", r: "Solo tu DNI.", qAt: 12.0 },
  { fila: 2, q: "¿Puedo pagar con tarjeta?", r: "Sí, en hasta 3 cuotas.", qAt: 12.8 },
  { fila: 3, q: "¿Cuánto sale el envío?", r: "Es gratis desde $ 50.000.", qAt: 13.6 },
];

export const OPERADORA = { nombre: "Lucía", rol: "Tu equipo" };

// Títulos de arriba: rótulo + frase con el remate en el acento
export const TITULOS = [
  { de: 3.4, a: 6.9, rotulo: "Tus clientes", texto: "Consultan por teléfono,", acento: "WhatsApp o la web." },
  { de: 7.0, a: 10.4, rotulo: "El agente", texto: "Entiende cada consulta", acento: "y la resuelve." },
  { de: 10.6, a: 18.5, rotulo: "Tu equipo", texto: "Le llega", acento: "solo lo importante." },
  { de: T.cierreIn, a: T.cierreOut, rotulo: "Agentes con IA que atienden a tus clientes", texto: "Resuelven el día a día.", acento: "Te pasan lo importante." },
];
