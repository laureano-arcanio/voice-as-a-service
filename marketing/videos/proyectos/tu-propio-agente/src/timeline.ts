import dur from "../../../public/proyectos/tu-propio-agente/vo/duraciones.json";
import { armarEscenas, duracionTotal, Voz } from "../../../src/comun/montaje";

export const DUR: Record<string, number> = dur;

// Escenas (s). La intro se funde 0,6 s con la siguiente.
export const INTRO_FADE = 0.6;
const LENS = {
  intro: 8.4,
  reparto: 9.8,
  turno: 11.0,
  herramientas: 8.8,
  ejemplo: 8.2,
  configurar: 14.6,
  latencia: 15.2,
  errores: 8.2,
  cierre: 9.4,
};
export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas<SceneId>(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);

// Cuándo arranca cada voz dentro de su escena (s)
export const AT = {
  t1: 0.6, t2: 0.4, t3: 0.3, t4: 0.3, t5: 0.3, t6: 0.3, t7: 9.4, t8: 0.3, t9: 0.3, t10: 0.4,
} as const;
export type VoId = keyof typeof AT;

export const ESCENA_DE: Record<VoId, SceneId> = {
  t1: "intro", t2: "reparto", t3: "turno", t4: "herramientas", t5: "ejemplo", t6: "configurar", t7: "configurar",
  t8: "latencia", t9: "errores", t10: "cierre",
};

export const VOICES: Voz[] = (Object.keys(AT) as VoId[]).map((id) => ({ id, scene: ESCENA_DE[id], at: AT[id] }));

// Subtítulos: la locución con la grafía normal, en tramos de una línea (se reparten por largo de texto)
export const SUBS: Record<VoId, string[]> = {
  t1: ["¿Ya tenés tu agente de IA? Conectalo a Atentina", "y atiende llamadas y WhatsApp con un número argentino,", "sin armar la parte de voz."],
  t2: ["Atentina pone el número, los canales, la transcripción,", "los turnos, la voz y los minutos.", "Tu agente pone el prompt, las herramientas,", "la memoria y qué responder."],
  t3: ["En cada turno, Atentina le manda a tu endpoint", "toda la conversación, en el formato de OpenAI.", "Tu endpoint contesta en streaming", "y cada pedazo de texto pasa a voz apenas llega."],
  t4: ["Para cortar o pasar la llamada a una persona,", "tu agente usa dos herramientas:", "una corta y elige el resultado, la otra transfiere a tu equipo."],
  t5: ["Un endpoint mínimo agrega su prompt", "y le pasa todo a su modelo, en streaming. El resto es tuyo."],
  t6: ["Se configura en tres pasos.", "Cargás la conexión, con la dirección de tu endpoint y su key.", "La probás.", "Y en el agente, prendés «Que conteste tu propio agente»."],
  t7: ["También se hace por API, con una API key de llamadas,", "o desde tu agente de IA por MCP."],
  t8: ["Lo que más pesa es el tiempo hasta el primer texto:", "desde que tu endpoint recibe el pedido", "hasta que manda el primer pedazo.", "Tu modelo, tus herramientas y tu servidor se notan en la llamada.", "Si pasa de un segundo, la conversación se siente lenta, con silencios."],
  t9: ["Si tu endpoint falla, el agente dice el mensaje que configuraste.", "Y con varios errores seguidos,", "corta o pasa la llamada a tu equipo."],
  t10: ["Tu agente, con nuestra voz y nuestro teléfono.", "Está en el plan Red, y la guía completa,", "en atentina.com.ar/desarrolladores"],
};

/** Momento (s, dentro de la escena) en que arranca el tramo n de la voz, repartido por largo como los subtítulos. */
export const sub = (id: VoId, n: number) => {
  const partes = SUBS[id];
  const total = partes.reduce((s, p) => s + p.length, 0);
  const antes = partes.slice(0, n).reduce((s, p) => s + p.length, 0);
  return AT[id] + (DUR[id] * antes) / total;
};
