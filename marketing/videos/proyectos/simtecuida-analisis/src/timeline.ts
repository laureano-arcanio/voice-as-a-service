import dur from "../../../public/proyectos/simtecuida-analisis/vo/duraciones.json";
import { armarEscenas, duracionTotal, type Voz } from "../../../src/comun/montaje";

// Escenas (s). Tope del pedido: 60 s en total. La intro se funde con la siguiente (INTRO_FADE s).
export const INTRO_FADE = 0.6;
const LENS = { intro: 6.2, oportunidades: 6.6, diagrama: 8.7, recorrido: 14.65, ficha: 9.5, panel: 4.8, presupuesto: 6.4, cierre: 3.4 };
export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);

// Momento en que arranca cada voz, relativo a su escena (s)
const a4a = 0.25;
const a4b = a4a + dur.a4a + 0.02;
const a4c = a4b + dur.a4b + 0.03;
const a5a = 0.25;
const a5b = a5a + dur.a5a + 0.02;
export const AT = { a1: 0.4, a2: 0.2, a3: 0.25, a4a, a4b, a4c, a5a, a5b, a6: 0.25, a7: 0.25, a8: 0.3 };

export const VOICES: Voz[] = [
  { id: "a1", scene: "intro", at: AT.a1 },
  { id: "a2", scene: "oportunidades", at: AT.a2 },
  { id: "a3", scene: "diagrama", at: AT.a3 },
  { id: "a4a", scene: "recorrido", at: AT.a4a },
  { id: "a4b", scene: "recorrido", at: AT.a4b },
  { id: "a4c", scene: "recorrido", at: AT.a4c },
  { id: "a5a", scene: "ficha", at: AT.a5a },
  { id: "a5b", scene: "ficha", at: AT.a5b },
  { id: "a6", scene: "panel", at: AT.a6 },
  { id: "a7", scene: "presupuesto", at: AT.a7 },
  { id: "a8", scene: "cierre", at: AT.a8 },
];
export const DUR = dur;
