import dur from "../../../public/proyectos/goldman/vo/duraciones.json";
import { armarEscenas, duracionTotal, type Voz } from "../../../src/comun/montaje";

// Escenas (s). La intro se funde con el problema: el problema arranca INTRO_FADE s antes de que termine.
export const INTRO_FADE = 0.6;
const LENS = { intro: 5.5, problema: 9.4, propuesta: 11.3, panel: 9.0, cierre: 4.9 };
export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);

// Momento en que arranca cada voz, relativo a su escena (s)
export const AT = { g1: 0.3, g2: 0.35, g3: 0.3, g4: 0.3, g5: 0.3 };

export const VOICES: Voz[] = [
  { id: "g1", scene: "intro", at: AT.g1 },
  { id: "g2", scene: "problema", at: AT.g2 },
  { id: "g3", scene: "propuesta", at: AT.g3 },
  { id: "g4", scene: "panel", at: AT.g4 },
  { id: "g5", scene: "cierre", at: AT.g5 },
];
export const DUR = dur;
