import dur from "../../../public/proyectos/atencion-punta-a-punta/vo/duraciones.json";
import { armarEscenas, duracionTotal, Voz } from "../../../src/comun/montaje";

export const DUR: Record<string, number> = dur;
export type VoId = "d1" | "d2" | "d3" | "d4" | "d5" | "d6" | "d7" | "d8" | "d9" | "d10";

// El diagrama es una sola escena (d2 a d8): los nodos quedan quietos y cambia lo que pasa entre ellos.
// Cada voz arranca GAP s después de la anterior; las animaciones se atan a esos momentos.
const GAP = 0.65;
const encadenar = (ids: VoId[], start: number) => {
  const at: Partial<Record<VoId, number>> = {};
  let t = start;
  for (const id of ids) {
    at[id] = t;
    t += DUR[id] + GAP;
  }
  return { at, end: t - GAP };
};
const diag = encadenar(["d2", "d3", "d4", "d5", "d6", "d7", "d8"], 0.5);

export const INTRO_FADE = 0.6;
const LENS = {
  intro: 0.5 + DUR.d1 + 0.9,
  diagrama: diag.end + 1.2,
  checklist: 0.4 + DUR.d9 + 2.0,
  cierre: 0.5 + DUR.d10 + 1.4,
};
export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas<SceneId>(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);

export const AT: Record<VoId, number> = { d1: 0.5, ...diag.at, d9: 0.4, d10: 0.5 } as Record<VoId, number>;
export const ESCENA_DE: Record<VoId, SceneId> = {
  d1: "intro", d2: "diagrama", d3: "diagrama", d4: "diagrama", d5: "diagrama", d6: "diagrama", d7: "diagrama",
  d8: "diagrama", d9: "checklist", d10: "cierre",
};
export const VOICES: Voz[] = (Object.keys(AT) as VoId[]).map((id) => ({ id, scene: ESCENA_DE[id], at: AT[id] }));

// Subtítulos: la locución con la grafía normal, en tramos de una línea (se reparten por largo de texto)
export const SUBS: Record<VoId, string[]> = {
  d1: ["Así funciona Atentina: atiende a tus clientes de punta a punta."],
  d2: ["Tomás llama a tu empresa,", "y el agente lo atiende, a cualquier hora."],
  d3: ["Mientras hablan, consulta tu sistema:", "encuentra su pedido y registra lo que necesita."],
  d4: ["Tomás pide hablar con Ventas.", "El agente llama a tu equipo, en el orden y el horario que elegiste."],
  d5: ["Tomás escucha música.", "Suena Valentina; si no atiende, suena Lucas."],
  d6: ["A Lucas, el agente le cuenta en pocas palabras", "de qué se trata, y los conecta."],
  d7: ["¿Y si nadie atiende?", "El agente vuelve con Tomás y le toma el mensaje."],
  d8: ["Al final, todo queda registrado en tu panel:", "la conversación, los datos y el resultado."],
  d9: ["Teléfono, WhatsApp y web, con voces argentinas.", "Tu sistema, tu equipo y tus horarios. Lo configurás vos."],
  d10: ["Atentina. Agentes con IA que atienden a tus clientes.", "Empezá hoy, en atentina.com.ar"],
};

/** Momento (s, dentro de la escena) en que arranca el tramo n de la voz, repartido por largo como los subtítulos. */
export const sub = (id: VoId, n: number) => {
  const partes = SUBS[id];
  const total = partes.reduce((s, p) => s + p.length, 0);
  const antes = partes.slice(0, n).reduce((s, p) => s + p.length, 0);
  return AT[id] + (DUR[id] * antes) / total;
};
