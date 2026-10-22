import dur from "../../../public/proyectos/goldman-analisis/vo/duraciones.json";
import { armarEscenas, duracionTotal, type Voz } from "../../../src/comun/montaje";

// Escenas (s), en el orden del PDF goldman-propuesta v1. La intro se funde con la siguiente (INTRO_FADE s).
export const INTRO_FADE = 0.6;
const LENS = { intro: 5.5, bien: 9.9, cita: 5.5, observamos: 12.3, clientes: 9.1, propuesta: 12.0, cierre: 5.2 };
export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);

// Momento en que arranca cada voz, relativo a su escena (s)
export const AT = { a1: 0.45, a2: 0.3, a3: 0.3, a4: 0.3, a5: 0.3, a6: 0.3, a7: 0.3 };

export const VOICES: Voz[] = [
  { id: "a1", scene: "intro", at: AT.a1 },
  { id: "a2", scene: "bien", at: AT.a2 },
  { id: "a3", scene: "cita", at: AT.a3 },
  { id: "a4", scene: "observamos", at: AT.a4 },
  { id: "a5", scene: "clientes", at: AT.a5 },
  { id: "a6", scene: "propuesta", at: AT.a6 },
  { id: "a7", scene: "cierre", at: AT.a7 },
];
export const DUR = dur;
