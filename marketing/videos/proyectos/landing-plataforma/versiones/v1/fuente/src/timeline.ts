import dur from "../../../public/proyectos/landing-plataforma/vo/duraciones.json";
import { armarEscenas, duracionTotal, Voz } from "../../../src/comun/montaje";

export const DUR: Record<string, number> = dur;
export type VoId = "l1" | "l2" | "l3" | "l4" | "l5" | "l6" | "l7" | "l8" | "l9";

// La plataforma es una sola escena (l2 a l6): el agente queda fijo al centro y cada línea suma algo alrededor.
// Cada voz arranca GAP s después de la anterior; las animaciones se atan a esos momentos.
const GAP = 0.4;
const encadenar = (ids: VoId[], start: number) => {
  const at: Partial<Record<VoId, number>> = {};
  let t = start;
  for (const id of ids) {
    at[id] = t;
    t += DUR[id] + GAP;
  }
  return { at, end: t - GAP };
};
const plat = encadenar(["l2", "l3", "l4", "l5", "l6"], 0.3);

export const INTRO_FADE = 0.6;
const LENS = {
  intro: 0.4 + DUR.l1 + 0.5,
  plataforma: plat.end + 0.6,
  todo: 0.3 + DUR.l7 + 0.8,
  desarrolladores: 0.3 + DUR.l8 + 1.0,
  cierre: 0.3 + DUR.l9 + 2.0,
};
export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas<SceneId>(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);

export const AT: Record<VoId, number> = { l1: 0.4, ...plat.at, l7: 0.3, l8: 0.3, l9: 0.3 } as Record<VoId, number>;
export const ESCENA_DE: Record<VoId, SceneId> = {
  l1: "intro", l2: "plataforma", l3: "plataforma", l4: "plataforma", l5: "plataforma", l6: "plataforma",
  l7: "todo", l8: "desarrolladores", l9: "cierre",
};
export const VOICES: Voz[] = (Object.keys(AT) as VoId[]).map((id) => ({ id, scene: ESCENA_DE[id], at: AT[id] }));

// Subtítulos: la locución con la grafía normal, en tramos de una línea (se reparten por largo de texto)
export const SUBS: Record<VoId, string[]> = {
  l1: ["Atentina: la atención de tu empresa, con inteligencia artificial."],
  l2: ["Tus clientes llaman, escriben por WhatsApp o desde tu web,", "y un agente los atiende, a cualquier hora."],
  l3: ["Da turnos, responde consultas, toma pedidos,", "y lo registra en tu sistema."],
  l4: ["También llama a tus clientes:", "confirma turnos, recuerda vencimientos y hace campañas."],
  l5: ["Y cuando hace falta una persona,", "le pasa la llamada a alguien de tu equipo."],
  l6: ["Elegís entre 41 voces argentinas,", "y cada conversación queda en tu panel, con los datos y el resultado."],
  l7: ["Teléfono, WhatsApp e inteligencia artificial, en un solo servicio,", "con un precio por mes, en pesos."],
  l8: ["Y si desarrollás, conectalo por API,", "o manejalo desde tu agente de programación con MCP."],
  l9: ["Probalo gratis en atentina.com.ar"],
};

/** Momento (s, dentro de la escena) en que arranca el tramo n de la voz, repartido por largo como los subtítulos. */
export const sub = (id: VoId, n: number) => {
  const partes = SUBS[id];
  const total = partes.reduce((s, p) => s + p.length, 0);
  const antes = partes.slice(0, n).reduce((s, p) => s + p.length, 0);
  return AT[id] + (DUR[id] * antes) / total;
};
