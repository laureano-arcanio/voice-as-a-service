import dur from "../../../public/proyectos/transcripcion/vo/duraciones.json";
import { armarEscenas, duracionTotal, type Voz } from "../../../src/comun/montaje";

// Escenas (s). La intro se funde con el panel: el panel arranca INTRO_FADE s antes de que termine.
export const INTRO_FADE = 0.6;
const LENS = { intro: 7.6, panel: 11.6, api: 9.2, integracion: 9.0, cierre: 5.6 };
export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);

export const VOICES: Voz[] = [
  { id: "t1", scene: "intro", at: 0.4 },
  { id: "t2", scene: "panel", at: 0.5 },
  { id: "t3", scene: "api", at: 0.3 },
  { id: "t4", scene: "integracion", at: 0.3 },
  { id: "t5", scene: "cierre", at: 0.4 },
];
export const DUR = dur;
