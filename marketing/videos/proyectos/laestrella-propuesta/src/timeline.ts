import dur from "../../../public/proyectos/laestrella-propuesta/vo/duraciones.json";
import guion from "../guion.json";
import { armarEscenas, duracionTotal, type Voz } from "../../../src/comun/montaje";

// Escenas (s). Pedido: 60 a 90 s. El cierre queda ~2,5 s después de a13 y se funde (imagen y sonido) en el último segundo. La intro se funde con la siguiente (INTRO_FADE s).
export const INTRO_FADE = 0.6;
const LENS = { intro: 14.6, propuesta: 15.3, datos: 10.6, etapa1: 13.4, etapa2: 7.5, funciona: 9.4, pasos: 6.6, cierre: 7.8 };
export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);
export const CIERRE_LEN = LENS.cierre;

type Id = keyof typeof dur;
const GAP = 0.25;
// Momento en que arranca cada voz, relativo a su escena (s): paula y gonzalo alternan como diálogo
const a1 = 0.5;
const a2 = a1 + dur.a1 + GAP;
const a3 = 0.3;
const a4 = a3 + dur.a3 + GAP;
const a5 = 0.3;
const a6 = a5 + dur.a5 + 0.35;
const a7 = 0.3;
const a8 = a7 + dur.a7 + GAP;
export const AT: Record<Id, number> = { a1, a2, a3, a4, a5, a6, a7, a8, a9: 0.3, a10: 0.3, a11: 0.3, a12: 0.4, a13: 0.4 + dur.a12 + 0.45 };

const TEXTO = Object.fromEntries(guion.lineas.map((l) => [l.id, l.texto])) as Record<Id, string>;

/** Momento aproximado (s, relativo a la escena) en que la voz `id` dice `frag`: proporcional a los caracteres. */
export const en = (id: Id, frag: string) => {
  const t = TEXTO[id];
  const i = t.indexOf(frag);
  if (i < 0) throw new Error(`"${frag}" no está en ${id}`);
  return AT[id] + (dur[id] * i) / t.length;
};

export const VOICES: Voz[] = [
  { id: "a1", scene: "intro", at: AT.a1 },
  { id: "a2", scene: "intro", at: AT.a2 },
  { id: "a3", scene: "propuesta", at: AT.a3 },
  { id: "a4", scene: "propuesta", at: AT.a4 },
  { id: "a5", scene: "datos", at: AT.a5 },
  { id: "a6", scene: "datos", at: AT.a6 },
  { id: "a7", scene: "etapa1", at: AT.a7 },
  { id: "a8", scene: "etapa1", at: AT.a8 },
  { id: "a9", scene: "etapa2", at: AT.a9 },
  { id: "a10", scene: "funciona", at: AT.a10 },
  { id: "a11", scene: "pasos", at: AT.a11 },
  { id: "a12", scene: "cierre", at: AT.a12 },
  { id: "a13", scene: "cierre", at: AT.a13 },
];
export const DUR = dur;
